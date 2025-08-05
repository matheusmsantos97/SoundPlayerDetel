import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class MessageQueueSerializer:
    """
    Classe responsável por serializar e desserializar a fila de mensagens.
    CORRIGIDO: Agora detecta reinicialização do programa de forma mais confiável.
    """
    
    def __init__(self, queue_file_path):
        """
        Inicializa o serializador.
        
        Args:
            queue_file_path (str ou Path): Caminho para o arquivo de persistência da fila
        """
        self.queue_file_path = Path(queue_file_path)
        # Arquivo para indicar que o programa está rodando
        self.session_lock_file = self.queue_file_path.parent / "session.lock"
        
        # Cria o arquivo de sessão ativa
        self._create_session_lock()
    
    def _create_session_lock(self):
        """Cria arquivo indicando que o programa está rodando."""
        try:
            self.session_lock_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_lock_file, 'w', encoding='utf-8') as f:
                f.write(datetime.now().isoformat())
            print(f"🔒 Sessão ativa registrada: {self.session_lock_file}")
        except Exception as e:
            print(f"⚠ Erro ao criar lock de sessão: {e}")
    
    def _remove_session_lock(self):
        """Remove arquivo de sessão ativa."""
        try:
            if self.session_lock_file.exists():
                self.session_lock_file.unlink()
                print(f"🔓 Sessão finalizada: {self.session_lock_file}")
        except Exception as e:
            print(f"⚠ Erro ao remover lock de sessão: {e}")
    
    def save_queue(self, queue_items, is_shutdown=False):
        """
        Salva a fila incluindo informação se é um save de encerramento.
        
        Args:
            queue_items: Lista de itens da fila
            is_shutdown (bool): True se está salvando por causa do encerramento
        """
        try:
            self.queue_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            serializable_items = []
            for item in queue_items:
                # SEMPRE inclui interval_seconds
                interval_sec = getattr(item, 'interval_seconds', None)
                if interval_sec is None:
                    interval_sec = int(item.interval * 60)
                
                serializable_item = {
                    'filename': item.filename,
                    'priority': item.priority,
                    'interval': item.interval,
                    'interval_seconds': interval_sec,
                    'next_play_time': item.next_play_time.isoformat(),
                    'is_pending': getattr(item, 'is_pending', False)
                }
                
                if hasattr(item, 'end_time') and item.end_time:
                    serializable_item['end_time'] = item.end_time.isoformat()
                
                if hasattr(item, 'last_played') and item.last_played:
                    serializable_item['last_played'] = item.last_played.isoformat()
                
                serializable_items.append(serializable_item)
            
            # Metadata da sessão
            save_data = {
                'version': '1.2',
                'save_timestamp': datetime.now().isoformat(),
                'is_shutdown_save': is_shutdown,
                'messages': serializable_items
            }
            
            with open(self.queue_file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
            
            # Se é um save de encerramento, remove o lock
            if is_shutdown:
                self._remove_session_lock()
                print(f"✅ Fila salva (ENCERRAMENTO) - intervalos serão resetados na próxima inicialização")
            else:
                print(f"✅ Fila salva (durante execução)")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar: {str(e)}")
            return False

    def load_queue(self, message_queue_class):
        """
        Carrega a fila detectando se houve reinicialização do programa.
        CORRIGIDO: Método mais confiável de detecção.
        """
        if not self.queue_file_path.exists():
            print("📄 Nenhum arquivo de fila encontrado - iniciando fila vazia")
            return []
        
        try:
            with open(self.queue_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Compatibilidade com formato antigo
            if isinstance(data, list):
                print("📁 Formato antigo detectado - RESETANDO intervalos")
                serialized_items = data
                is_restart = True
            else:
                # Formato novo com metadata
                serialized_items = data.get('messages', [])
                
                # NOVA LÓGICA: Detecta reinicialização de forma mais confiável
                is_restart = self._detect_program_restart_v2(data)
            
            queue_items = []
            now = datetime.now()
            
            for item_data in serialized_items:
                item = message_queue_class(
                    item_data['filename'],
                    item_data['priority'],
                    item_data['interval']
                )
                
                # Restaura interval_seconds
                item.interval_seconds = item_data.get('interval_seconds', int(item.interval * 60))
                
                if is_restart:
                    # RESETAR TUDO: Programa foi reiniciado
                    print(f"🔄 RESET: P{item.priority} - {item.filename}")
                    
                    # Reset completo dos tempos
                    item.next_play_time = now + timedelta(seconds=item.interval_seconds)
                    item.is_pending = item.priority > 1  # Só P1 fica ativa
                    item.last_played = None
                    item.end_time = None
                    
                    print(f"   ⏰ Novo agendamento: {item.next_play_time.strftime('%H:%M:%S')}")
                    print(f"   📊 Status: {'ATIVA' if not item.is_pending else 'PENDENTE'}")
                    
                else:
                    # MANTER ESTADO: Carregamento durante execução
                    item.next_play_time = datetime.fromisoformat(item_data['next_play_time'])
                    item.is_pending = item_data.get('is_pending', False)
                    
                    if 'end_time' in item_data and item_data['end_time']:
                        item.end_time = datetime.fromisoformat(item_data['end_time'])
                    
                    if 'last_played' in item_data and item_data['last_played']:
                        item.last_played = datetime.fromisoformat(item_data['last_played'])
                    
                    print(f"📝 MANTIDO: P{item.priority} - {item.filename}")
                
                queue_items.append(item)
            
            if is_restart:
                print(f"\n🚀 PROGRAMA REINICIADO - Todos os intervalos foram RESETADOS")
                print(f"⏰ Mensagens reagendadas a partir de: {now.strftime('%H:%M:%S')}")
            else:
                print(f"\n📋 Carregamento durante execução - Estado mantido")
            
            return queue_items
            
        except Exception as e:
            print(f"❌ Erro ao carregar: {str(e)}")
            return []
    
    def _detect_program_restart_v2(self, save_data):
        """
        Nova versão melhorada da detecção de reinicialização.
        
        Args:
            save_data (dict): Dados salvos do arquivo
            
        Returns:
            bool: True se detectou reinicialização
        """
        try:
            # MÉTODO 1: Verifica se o arquivo de sessão existe
            session_was_active = self.session_lock_file.exists()
            
            # MÉTODO 2: Verifica se foi um save de encerramento
            is_shutdown_save = save_data.get('is_shutdown_save', False)
            
            # MÉTODO 3: Verifica timestamp (backup)
            save_timestamp = save_data.get('save_timestamp')
            time_gap = 0
            if save_timestamp:
                try:
                    last_save = datetime.fromisoformat(save_timestamp)
                    time_gap = (datetime.now() - last_save).total_seconds()
                except:
                    time_gap = 999999  # Força restart em caso de erro
            
            print(f"🔍 DETECÇÃO DE REINICIALIZAÇÃO:")
            print(f"   Sessão anterior ativa: {session_was_active}")
            print(f"   Foi save de encerramento: {is_shutdown_save}")
            print(f"   Gap de tempo: {int(time_gap)}s")
            
            # LÓGICA DE DECISÃO:
            if is_shutdown_save:
                # Se foi um save de encerramento, definitivamente é reinício
                print(f"   → REINICIALIZAÇÃO (save de encerramento)")
                return True
            elif not session_was_active:
                # Se não havia sessão ativa, é reinício
                print(f"   → REINICIALIZAÇÃO (sem sessão anterior)")
                return True
            elif time_gap > 60:
                # Se passou mais de 1 minuto, provavelmente é reinício
                print(f"   → REINICIALIZAÇÃO (gap de tempo)")
                return True
            else:
                # Carregamento durante execução
                print(f"   → CONTINUAÇÃO (carregamento durante execução)")
                return False
                
        except Exception as e:
            print(f"   → REINICIALIZAÇÃO (erro na detecção: {e})")
            return True  # Em caso de erro, assume reinício
    
    def cleanup(self):
        """Limpa recursos e remove arquivo de sessão."""
        print("🧹 Limpando recursos do serializador")
        self._remove_session_lock()