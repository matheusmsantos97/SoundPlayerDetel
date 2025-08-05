# -*- coding: utf-8 -*-

"""
Serviço de gerenciamento da fila de mensagens.
CORRIGIDO: Agora funciona com o novo sistema de detecção de reinicialização.
"""

import heapq
from datetime import datetime, timedelta
from pathlib import Path
from models.message_item import MessageQueueItem
from services.message_queue_serializer import MessageQueueSerializer

class QueueService:
    """
    Serviço que gerencia a fila de mensagens com prioridade.
    CORRIGIDO: Sistema de prioridades funciona corretamente com reset confiável.
    """
    
    def __init__(self, queue_file_path=None):
        """
        Inicializa o serviço de fila.
        
        Args:
            queue_file_path (str ou Path, optional): Caminho para o arquivo de persistência
        """
        self.message_queue = []  # Lista de mensagens
        self.currently_playing = None
        
        # Configurar serializador de persistência, se fornecido
        if queue_file_path:
            self.serializer = MessageQueueSerializer(queue_file_path)
            # Carrega a fila salva anteriormente
            saved_items = self.serializer.load_queue(MessageQueueItem)
            
            # Processa as mensagens carregadas
            self._process_loaded_messages(saved_items)
        else:
            self.serializer = None
    
    def _process_loaded_messages(self, items):
        """
        Processa mensagens carregadas do arquivo.
        CORRIGIDO: Não precisa mais fazer ajustes, o serializer já cuida do reset.
        """
        if not items:
            return
        
        # Remove duplicatas mantendo apenas uma instância por arquivo
        unique_items = {}
        for item in items:
            key = item.filename
            if key not in unique_items:
                unique_items[key] = item
        
        # Adiciona à fila
        self.message_queue = list(unique_items.values())
        
        # Ordena por prioridade
        self.message_queue.sort(key=lambda x: x.priority)
        
        # Mostra o status das mensagens carregadas
        print(f"\n📋 MENSAGENS CARREGADAS:")
        for msg in self.message_queue:
            status = "ATIVA" if not msg.is_pending else "PENDENTE"
            next_time = msg.next_play_time.strftime('%H:%M:%S')
            print(f"   P{msg.priority} - {msg.filename}: {status} (próxima: {next_time})")
    
    def add_message(self, filename, priority, interval):
        """
        Adiciona mensagem à fila - VERSÃO CORRIGIDA.
        Não inicia contagem se há mensagem tocando.
        """
        # Verifica duplicatas
        for item in self.message_queue:
            if item.filename == filename:
                print(f"❌ Mensagem '{filename}' já está na fila.")
                return None

        # Cria mensagem
        message = MessageQueueItem(filename, priority, interval)
        message.interval_seconds = int(interval * 60)
        
        print(f"\n📌 NOVA MENSAGEM ADICIONADA:")
        print(f"   Arquivo: {filename}")
        print(f"   Prioridade: {priority}")
        print(f"   Intervalo: {message.interval_seconds} segundos")
        
        now = datetime.now()
        
        # Verifica se há mensagem tocando atualmente
        is_message_playing = False
        if hasattr(self, 'currently_playing') and self.currently_playing:
            is_message_playing = True
            print(f"   ⚠️ Mensagem '{self.currently_playing.filename}' está tocando agora")
        
        # Verifica se já existe mensagem ativa
        active_messages = [m for m in self.message_queue if not m.is_pending]
        
        if not active_messages and not is_message_playing:
            # Se não há mensagens ativas E não está tocando nada, esta fica ativa
            message.next_play_time = now + timedelta(seconds=message.interval_seconds)
            message.is_pending = False
            print(f"   ✅ ATIVA - tocará às {message.next_play_time.strftime('%H:%M:%S')}")
        else:
            # Se está tocando algo, a nova mensagem sempre fica pendente
            if is_message_playing:
                message.is_pending = True
                # Não define next_play_time ainda - será definido quando a atual terminar
                message.next_play_time = now  # Temporário
                print(f"   ⏸️ PENDENTE - aguardará término da mensagem atual")
            else:
                # Lógica original para quando não está tocando
                # Verifica se esta mensagem tem prioridade maior que as ativas
                min_active_priority = min(msg.priority for msg in active_messages)
                
                if priority < min_active_priority:
                    # Esta mensagem tem prioridade maior - desativa as outras
                    print(f"   🔄 PRIORIDADE MAIOR - desativando mensagens de menor prioridade")
                    for msg in self.message_queue:
                        if not msg.is_pending:
                            msg.is_pending = True
                            print(f"      P{msg.priority} - {msg.filename} → PENDENTE")
                    
                    # Ativa esta mensagem
                    message.next_play_time = now + timedelta(seconds=message.interval_seconds)
                    message.is_pending = False
                    print(f"   ✅ ATIVA - tocará às {message.next_play_time.strftime('%H:%M:%S')}")
                else:
                    # Esta mensagem tem prioridade menor - fica pendente
                    message.is_pending = True
                    print(f"   ⏸️ PENDENTE - aguardará sua vez")
        
        # Adiciona à fila
        self.message_queue.append(message)
        self._save_queue()
        
        return message
    
    def register_message_start(self, message):
        """
        NOVO MÉTODO: Registra o início de uma mensagem.
        """
        self.currently_playing = message
        print(f"🎵 Registrado início de: {message.filename}")
    
    def register_message_end(self, message, fade_end_time=None):
        """
        Registra término de mensagem - VERSÃO CORRIGIDA.
        """
        # Usa o tempo final com fade como referência
        end_time = fade_end_time if fade_end_time else datetime.now()
        
        print(f"\n{'='*60}")
        print(f"⏹️ TÉRMINO DE MENSAGEM")
        print(f"{'='*60}")
        print(f"Arquivo: '{message.filename}'")
        print(f"Prioridade: {message.priority}")
        print(f"Intervalo: {getattr(message, 'interval_seconds', 'NÃO DEFINIDO')} segundos")
        print(f"Tempo de referência (com fade): {end_time.strftime('%H:%M:%S')}")
        
        # Atualiza a mensagem na fila
        for msg in self.message_queue:
            if msg.filename == message.filename and msg.priority == message.priority:
                msg.last_played = end_time
                msg.is_pending = True
                msg.end_time = end_time
                
                # Calcula o próximo horário baseado no término + intervalo
                msg.next_play_time = end_time + timedelta(seconds=msg.interval_seconds)
                print(f"✅ Reagendada para: {msg.next_play_time.strftime('%H:%M:%S')}")
                break
        
        # Limpa a referência de mensagem tocando
        self.currently_playing = None
        
        # Atualiza horários de mensagens pendentes que foram adicionadas durante reprodução
        for msg in self.message_queue:
            if msg.is_pending and msg.next_play_time <= datetime.now():
                # Esta mensagem foi adicionada enquanto outra tocava
                # Recalcula seu horário baseado no término da atual
                if not hasattr(msg, 'last_played') or msg.last_played is None:
                    # Nunca tocou - agenda baseado no término atual
                    msg.next_play_time = end_time + timedelta(seconds=msg.interval_seconds)
                    print(f"   📅 Reagendando pendente: P{msg.priority} - {msg.filename} para {msg.next_play_time.strftime('%H:%M:%S')}")
        
        # Ativa a próxima mensagem na sequência
        self._activate_next_priority_message()
        
        self._save_queue()
        
        if hasattr(self, 'update_callback'):
            self.update_callback()
        
        print(f"{'='*60}\n")

    def _activate_next_priority_message(self):
        """
        Ativa a próxima mensagem na sequência: P1 → P2 → P3... → P1
        """
        print("\n🔍 ATIVANDO PRÓXIMA MENSAGEM NA SEQUÊNCIA:")
        
        now = datetime.now()
        
        # Ordena todas as mensagens por prioridade
        all_messages = sorted(self.message_queue, key=lambda x: x.priority)
        
        # Encontra a última mensagem tocada
        last_played = None
        for msg in self.message_queue:
            if hasattr(msg, 'last_played') and msg.last_played:
                if not last_played or msg.last_played > last_played.last_played:
                    last_played = msg
        
        # Se não há histórico ou a última foi P1, tenta P2
        if not last_played or last_played.priority == 1:
            next_priority = 2
        else:
            # Próxima prioridade na sequência
            next_priority = last_played.priority + 1
        
        # Procura mensagem com a próxima prioridade
        next_message = None
        for msg in all_messages:
            if msg.priority == next_priority:
                next_message = msg
                break
        
        # Se não encontrou, volta para P1
        if not next_message:
            # Reinicia ciclo a partir da prioridade mais alta
            for msg in all_messages:
                if msg.priority == 1:
                    next_message = msg
                    break

        if next_message:
            next_message.is_pending = False

            # Verifica a última mensagem que tocou (completamente)
            last_end_time = None
            for msg in self.message_queue:
                if msg.end_time:
                    if not last_end_time or msg.end_time > last_end_time:
                        last_end_time = msg.end_time

            # Se houver término anterior, agenda a próxima a partir dele + intervalo
            if last_end_time:
                next_message.next_play_time = last_end_time + timedelta(seconds=next_message.interval_seconds)
            else:
                # Nunca tocou nada, pode tocar agora
                next_message.next_play_time = now

            print(f"   ✅ ATIVADA: P{next_message.priority} - {next_message.filename}")
            print(f"   📅 Tocará às: {next_message.next_play_time.strftime('%H:%M:%S')}")
    
    def get_next_message(self):
        """
        Obtém a próxima mensagem a ser reproduzida (apenas mensagens ativas).
        """
        if not self.message_queue:
            return None
        
        current_time = datetime.now()
        
        # Filtra apenas mensagens ativas (não pendentes)
        active_messages = [msg for msg in self.message_queue if not msg.is_pending]
        
        if not active_messages:
            return None
        
        # Verifica quais estão prontas para tocar
        ready_messages = [msg for msg in active_messages if msg.next_play_time <= current_time]
        
        if not ready_messages:
            return None
        
        # Ordena por prioridade (menor número = maior prioridade)
        ready_messages.sort(key=lambda x: (x.priority, x.next_play_time))
        selected_message = ready_messages[0]
        
        # Marca como pendente enquanto toca
        for msg in self.message_queue:
            if msg.filename == selected_message.filename and msg.priority == selected_message.priority:
                msg.is_pending = True
                break
        
        # Cria cópia para reprodução
        import copy
        message_copy = copy.deepcopy(selected_message)
        if hasattr(selected_message, 'interval_seconds'):
            message_copy.interval_seconds = selected_message.interval_seconds
        
        print(f"🎵 SELECIONADA: P{message_copy.priority} - {message_copy.filename}")
        return message_copy
    
    def remove_message(self, filename):
        """Remove uma mensagem específica da fila."""
        for index, item in enumerate(self.message_queue):
            if item.filename == filename:
                del self.message_queue[index]
                self._save_queue()
                print(f"✅ Mensagem '{filename}' removida da fila")
                return True
        return False
    
    def clear_queue(self):
        """Limpa toda a fila de mensagens."""
        self.message_queue = []
        self.currently_playing = None
        
        if self.serializer:
            self.serializer.save_queue([])
        
        print("✅ Fila completamente limpa")
    
    def debug_queue_state(self):
        """Mostra o estado atual da fila para debug."""
        if not self.message_queue:
            print("📭 Fila vazia")
            return
        
        print(f"\n📋 ESTADO DA FILA ({datetime.now().strftime('%H:%M:%S')}):")
        
        # Separa mensagens por estado
        active_messages = [msg for msg in self.message_queue if not msg.is_pending]
        pending_messages = [msg for msg in self.message_queue if msg.is_pending]
        
        if active_messages:
            print("🟢 MENSAGENS ATIVAS:")
            for msg in sorted(active_messages, key=lambda x: x.priority):
                remaining = (msg.next_play_time - datetime.now()).total_seconds()
                status = "PRONTA!" if remaining <= 0 else f"em {int(remaining)}s"
                print(f"   P{msg.priority} - {msg.filename}: {status}")
        
        if pending_messages:
            print("🟡 MENSAGENS PENDENTES:")
            for msg in sorted(pending_messages, key=lambda x: x.priority):
                print(f"   P{msg.priority} - {msg.filename}: aguardando vez")
        
        print()
    
    def get_queue_items(self):
        """Retorna todos os itens da fila ordenados por prioridade."""
        return sorted(self.message_queue, key=lambda x: x.priority)
    
    def get_queue_length(self):
        """Retorna o número de mensagens na fila."""
        return len(self.message_queue)
    
    def _save_queue(self, is_shutdown=False):
        """
        Salva a fila no arquivo de persistência.
        
        Args:
            is_shutdown (bool): True se está salvando por causa do encerramento
        """
        if not self.serializer:
            return False
        
        return self.serializer.save_queue(self.message_queue, is_shutdown)
    
    def shutdown_save(self):
        """
        Salva a fila marcando como save de encerramento.
        Garante que na próxima inicialização os intervalos sejam resetados.
        """
        print("💾 Salvando estado final com flag de encerramento...")
        return self._save_queue(is_shutdown=True)
    
    def cleanup(self):
        """Limpa recursos do serviço."""
        print("🧹 Limpando recursos do QueueService")
        if hasattr(self, 'serializer') and self.serializer:
            self.serializer.cleanup()