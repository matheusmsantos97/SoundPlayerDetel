#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gerenciador principal da fila de mensagens com loop de verificação automática.
CORRIGIDO: Agora respeita a ordem de prioridades corretamente.
"""

import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from services.audio_fade_manager import AudioFadeManager

class MessageQueueManager:
    """
    Gerenciador principal que coordena a reprodução automática das mensagens.
    Executa em thread separada e verifica constantemente a fila.
    """
    
    def __init__(self, queue_service, player_service):
        """
        Inicializa o gerenciador.
        
        Args:
            queue_service: Serviço de gerenciamento da fila
            player_service: Serviço de reprodução de áudio
        """
        self.queue_service = queue_service
        self.player_service = player_service
        
        # Thread de controle
        self.manager_thread = None
        self.running = False
        
        # Estado atual
        self.current_playing_message = None
        self.last_check_time = datetime.now()
        
        # Configurações
        self.check_interval = 1.0  # Verifica a fila a cada 1 segundo
        
        # Sistema de fade suave
        self.fade_manager = AudioFadeManager(player_service)
        
        print("📋 MessageQueueManager inicializado")
        print("🎵 Sistema de fade suave ativado")
    
    def start(self):
        """Inicia o gerenciador em thread separada."""
        if self.running:
            print("⚠️ MessageQueueManager já está em execução")
            return
            
        self.running = True
        self.manager_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.manager_thread.start()
        print("🚀 MessageQueueManager iniciado")
    
    def stop(self):
        """Para o gerenciador."""
        if not self.running:
            return
            
        self.running = False
        if self.manager_thread and self.manager_thread.is_alive():
            self.manager_thread.join(timeout=2.0)
        print("⏹️ MessageQueueManager parado")
    
    def _main_loop(self):
        """Loop principal que verifica e processa a fila."""
        print("🔄 Loop principal do MessageQueueManager iniciado")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Debug periódico
                if int(current_time.second) % 5 == 0:
                    self._show_debug_status(current_time)
                
                # VERIFICAÇÃO 1: Mensagem em reprodução
                if self.current_playing_message:
                    if self.player_service.is_media_ended():
                        self._handle_message_end()
                
                # VERIFICAÇÃO 2: Nova mensagem para tocar
                if not self.current_playing_message:
                    next_message = self._get_next_priority_message()
                    if next_message:
                        self._start_message_playback(next_message)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"\n❌ ERRO: {str(e)}")
                import traceback
                traceback.print_exc()
                time.sleep(5.0)
    
    def _show_debug_status(self, current_time):
        """Mostra status de debug das mensagens."""
        active_messages = [m for m in self.queue_service.message_queue if not m.is_pending]
        pending_messages = [m for m in self.queue_service.message_queue if m.is_pending]
        
        if active_messages or pending_messages:
            print(f"\n📊 STATUS ({current_time.strftime('%H:%M:%S')}):")
            
            # Mostra mensagens ativas (prontas para tocar)
            if active_messages:
                print("   🟢 ATIVAS (prontas para tocar):")
                for msg in sorted(active_messages, key=lambda x: x.priority):
                    remaining = self._get_remaining_time(msg, current_time)
                    if remaining > 0:
                        print(f"      P{msg.priority} - {msg.filename}: aguardando {int(remaining)}s")
                    else:
                        print(f"      P{msg.priority} - {msg.filename}: ⭐ PRONTA!")
            
            # Mostra mensagens pendentes (aguardando vez)
            if pending_messages:
                print("   🟡 PENDENTES (aguardando vez):")
                for msg in sorted(pending_messages, key=lambda x: x.priority):
                    print(f"      P{msg.priority} - {msg.filename}: aguardando prioridade")
    
    def _get_remaining_time(self, msg, current_time):
        """Calcula tempo restante para uma mensagem."""
        if hasattr(msg, 'last_played') and msg.last_played:
            time_since_last = (current_time - msg.last_played).total_seconds()
            return msg.interval_seconds - time_since_last
        else:
            return (msg.next_play_time - current_time).total_seconds()
    
    def _get_next_priority_message(self):
        current_time = datetime.now()

        # Filtrar mensagens que estão ativas e podem tocar
        ready_messages = [
            msg for msg in self.queue_service.message_queue
            if not msg.is_pending and msg.next_play_time <= current_time
        ]

        # Se todas já tocaram uma vez, reinicia o ciclo
        all_played = all(
            msg.last_played is not None for msg in self.queue_service.message_queue
        )

        # Se todas tocaram, podemos reativar a de prioridade 1
        if all_played and not ready_messages:
            self.queue_service._activate_next_priority_message()
            return None

        # Ordena por prioridade (menor número primeiro)
        ready_messages.sort(key=lambda x: x.priority)
        if ready_messages:
            selected_message = ready_messages[0]
            selected_message.is_pending = True  # Marcar como pendente
            return selected_message

        return None
    
    def _start_message_playback(self, message):
        """Inicia a reprodução de uma mensagem - VERSÃO CORRIGIDA."""
        print(f"\n{'='*60}")
        print(f"🎵 INICIANDO REPRODUÇÃO DE MENSAGEM")
        print(f"{'='*60}")
        print(f"Arquivo: '{message.filename}'")
        print(f"Prioridade: {message.priority}")
        print(f"Horário: {datetime.now().strftime('%H:%M:%S')}")
        
        # Registra que a mensagem está começando
        self.queue_service.register_message_start(message)
        
        # Fade da rádio para a mensagem
        print("🎵 Iniciando fade para mensagem...")
        self.fade_manager.start_message_transition()

        # Aguarda a conclusão do fade antes de começar a mensagem
        time.sleep(self.fade_manager.fade_duration + 0.2)   
        
        # Reproduz a mensagem
        if self.player_service.play_message(message.filename, message):
            self.current_playing_message = message
            print(f"✅ Mensagem iniciada com sucesso")
        else:
            print(f"❌ Falha ao reproduzir mensagem")
            # Se falhou, volta para a rádio (mas não fecha ela)
            self.player_service.switch_to_radio()
            # Limpa o registro de reprodução
            self.queue_service.currently_playing = None
        
        print(f"{'='*60}\n")
    
    def _handle_message_end(self):
        """Processa o término de uma mensagem."""
        print(f"\n{'*'*60}")
        print(f"🏁 MENSAGEM TERMINOU!")
        print(f"{'*'*60}")
        print(f"Mensagem: '{self.current_playing_message.filename}'")
        print(f"Horário: {datetime.now().strftime('%H:%M:%S')}")
        
        # Define o horário de término (incluindo o fade)
        fade_end_time = datetime.now() + timedelta(seconds=self.fade_manager.fade_duration)
        self.current_playing_message.end_time = fade_end_time
        
        # Fade de volta para a rádio
        print("🎵 Iniciando fade de volta para rádio...")
        self.fade_manager.end_message_transition()
        
        print(f"   Fade terminará em: {fade_end_time.strftime('%H:%M:%S')}")
        
        # Registra o término usando o fade_end_time como referência
        self.queue_service.register_message_end(self.current_playing_message, fade_end_time)
        
        # Volta para a rádio
        self.player_service.switch_to_radio()
        
        # Limpa a referência
        self.current_playing_message = None
        print(f"{'*'*60}\n")
    
    def debug_status(self):
        """Retorna informações de debug sobre o estado atual."""
        status = {
            'running': self.running,
            'current_message': self.current_playing_message.filename if self.current_playing_message else None,
            'queue_length': self.queue_service.get_queue_length(),
            'player_mode': 'radio' if self.player_service.is_radio_mode else 'message',
            'player_state': self.player_service.get_state()
        }
        return status
    
    def force_check(self):
        """Força uma verificação imediata da fila (útil para debug)."""
        if not self.running:
            print("⚠️ MessageQueueManager não está em execução")
            return
            
        print("🔍 Forçando verificação da fila...")
        
        # Mostra estado atual da fila
        current_time = datetime.now()
        active_messages = [m for m in self.queue_service.message_queue if not m.is_pending]
        pending_messages = [m for m in self.queue_service.message_queue if m.is_pending]
        
        print(f"\n📋 ESTADO DA FILA ({current_time.strftime('%H:%M:%S')}):")
        
        if active_messages:
            print("🟢 MENSAGENS ATIVAS:")
            for msg in sorted(active_messages, key=lambda x: x.priority):
                remaining = self._get_remaining_time(msg, current_time)
                status = "PRONTA!" if remaining <= 0 else f"aguardando {int(remaining)}s"
                print(f"   P{msg.priority} - {msg.filename}: {status}")
        
        if pending_messages:
            print("🟡 MENSAGENS PENDENTES:")
            for msg in sorted(pending_messages, key=lambda x: x.priority):
                print(f"   P{msg.priority} - {msg.filename}: aguardando vez")
        
        if not active_messages and not pending_messages:
            print("📭 Fila vazia")
        
        # Verifica próxima mensagem
        next_message = self._get_next_priority_message()
        if next_message:
            print(f"\n🎯 PRÓXIMA A TOCAR: P{next_message.priority} - {next_message.filename}")
        else:
            print(f"\n⏰ Nenhuma mensagem pronta no momento")