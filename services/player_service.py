#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Serviço de reprodução de áudio usando VLC para rádio e Pygame para mensagens.
Suporta integração com microfone.
"""

import vlc
import time
import os
import pygame
import threading
from datetime import datetime, timedelta
from pathlib import Path
from models.message_item import MessageQueueItem
from services.microphone_service import MicrophoneService
from services.radio_source_manager import RadioSourceManager, RadioSource

class PlayerService:
    """
    Serviço que gerencia a reprodução de áudio:
    - VLC para streaming de rádio e dispositivos
    - Pygame para mensagens locais (mais compatível com arquivos locais)
    - Suporte para microfone
    - Múltiplas fontes de rádio
    """
    
    # Estados possíveis da reprodução
    class PlayerState:
        PLAYING = "Reproduzindo"
        PAUSED = "Pausado"  
        STOPPED = "Parado"
        CONNECTING = "Conectando..."
        BUFFERING = "Carregando buffer..."
        ERROR = "Erro"
        MIC_ACTIVE = "Microfone Ativo"
    
    def __init__(self, config_dir, messages_path):
        """
        Inicializa o serviço de reprodução.
        
        Args:
            config_dir (Path): Diretório de configuração
            messages_path (Path): Caminho para a pasta de mensagens
        """
        # Inicializa o gerenciador de fontes de rádio
        self.source_manager = RadioSourceManager(config_dir)
        
        # Inicializa VLC para a rádio
        self.vlc_instance = vlc.Instance("--no-video")
        self.radio_player = self.vlc_instance.media_player_new()
        
        # Para captura de dispositivos de áudio
        self.device_capture = None
        
        # Inicializa Pygame para mensagens - Modificar para incluir frequência adequada
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.set_num_channels(8)  # Aumenta o número de canais disponíveis
        
        self.microphone_service = None
        
        # Caminho para mensagens
        self.messages_path = Path(messages_path)
        
        # Estado de reprodução
        self.is_playing = False
        self.is_radio_mode = True
        
        # Propriedade para armazenar a mensagem atual
        self.current_message = None
        
        # Flag para verificar se a mensagem está tocando
        self.message_playing = False
        
        # Tempo de término da mensagem atual
        self.end_time = None
        
        # Volume original antes de ativar o microfone
        self.original_volume = 100
        self.mic_active = False
        
        # Inicializa a rádio
        self.init_radio()
        
        # Timer para monitorar o estado do Pygame
        self.last_check_time = datetime.now()
    
    def init_radio(self):
        """Inicializa o player de rádio com a fonte atual - VERSÃO CORRIGIDA."""
        try:
            # Obtém a fonte atual
            source = self.source_manager.get_current_source()
            
            print(f"Inicializando rádio: {source.name}")
            
            # Configura a reprodução com base no tipo de fonte
            if source.source_type == RadioSource.TYPE_STREAM:
                # Para streaming, usa o link diretamente
                self._init_radio_stream(source.url)
            else:
                # Para dispositivos, usa o índice do dispositivo
                self._init_radio_device(source.device_index)
            
            # Define volume máximo
            self.radio_player.audio_set_volume(100)
            
            # Inicia reprodução
            self.radio_player.play()
            self.is_playing = True
            
            # Aguarda um momento para inicialização
            time.sleep(1)
            
            print(f"Rádio iniciada: {source.name}")
        
        except Exception as e:
            print(f"Erro ao inicializar rádio: {str(e)}")

    def _init_radio_stream(self, url):
        """
        Inicializa o player para streaming - VERSÃO CORRIGIDA.
        
        Args:
            url (str): URL da rádio
        """
        # Se havia um dispositivo de captura, libera recursos
        if self.device_capture:
            # Parar qualquer captura em andamento
            self._stop_device_capture()
            
        # Configura a mídia para streaming com pts_delay aumentado
        media = self.vlc_instance.media_new(url)
        media.add_option(":network-caching=3000")
        media.add_option(":live-caching=3000")
        # Adiciona pts-delay para evitar o erro
        media.add_option(":pts-delay=3000")
        self.radio_player.set_media(media)
    
    def _init_radio_device(self, device_index):
        """
        Inicializa o player para dispositivo físico.
        
        Args:
            device_index (int): Índice do dispositivo
        """
        # Implementação da captura de áudio do dispositivo usando VLC
        # Usa a API do VLC para captura de dispositivos
        
        # O método exato pode variar dependendo da plataforma e versão do VLC
        # Aqui está uma implementação genérica:
        
        # Primeiro, para qualquer captura existente
        self._stop_device_capture()
        
        try:
            # Dependendo da plataforma, os métodos para capturar dispositivo são diferentes
            import platform
            system = platform.system()
            
            if system == "Windows":
                # No Windows, usa o DirectShow
                device_str = f"dshow://@ :dshow-vdev=none :dshow-adev=:{device_index}"
                media = self.vlc_instance.media_new(device_str)
            elif system == "Darwin":  # macOS
                # No macOS, usa o AVFoundation
                device_str = f"qtsound://{device_index}"
                media = self.vlc_instance.media_new(device_str)
            else:  # Linux e outros
                # No Linux, usa ALSA
                device_str = f"alsa://hw:{device_index},0"
                media = self.vlc_instance.media_new(device_str)
            
            # Configura o player com o novo dispositivo
            self.radio_player.set_media(media)
            
            # Marca que estamos usando captura de dispositivo
            self.device_capture = device_index
            
            print(f"Dispositivo de rádio configurado: {device_index}")
            
        except Exception as e:
            print(f"Erro ao configurar dispositivo de rádio: {str(e)}")
            # Fallback para streaming padrão em caso de erro
            default_source = self.source_manager.get_current_source()
            if default_source.source_type == RadioSource.TYPE_STREAM:
                self._init_radio_stream(default_source.url)
    
    def _stop_device_capture(self):
        """Para a captura de dispositivo de rádio, se ativa."""
        if self.device_capture is not None:
            # Para a reprodução atual
            self.radio_player.stop()
            # Limpa a referência
            self.device_capture = None
            print("Captura de dispositivo de rádio parada")
    
    def change_radio_source(self, source_index):
        """
        Muda a fonte de rádio.
        
        Args:
            source_index (int): Índice da fonte
            
        Returns:
            bool: True se mudou com sucesso
        """
        try:
            # Obtém a nova fonte
            new_source = self.source_manager.set_current_source(source_index)
            
            if new_source:
                # Se estamos no modo rádio, atualiza imediatamente
                if self.is_radio_mode:
                    # Para a reprodução atual
                    self.radio_player.stop()
                    
                    # Inicializa com a nova fonte
                    if new_source.source_type == RadioSource.TYPE_STREAM:
                        self._init_radio_stream(new_source.url)
                    else:
                        self._init_radio_device(new_source.device_index)
                    
                    # Inicia a reprodução
                    self.radio_player.play()
                    self.is_playing = True
                
                return True
            else:
                print("Falha ao mudar fonte de rádio: fonte inválida")
                return False
                
        except Exception as e:
            print(f"Erro ao mudar fonte de rádio: {str(e)}")
            return False
    
    def get_current_source_name(self):
        """
        Obtém o nome da fonte atual.
        
        Returns:
            str: Nome da fonte atual
        """
        source = self.source_manager.get_current_source()
        return source.name if source else "Desconhecida"                                                                                                                                                                                    
    
    def play(self):
        """
        Inicia ou retoma a reprodução.
        
        Returns:
            bool: True se começou a reproduzir, False caso contrário
        """
        try:
            # Se o microfone estiver ativo, não permite reproduzir
            if self.mic_active:
                print("Não é possível iniciar reprodução com microfone ativo")
                return False
                
            if self.is_radio_mode:
                if not self.radio_player.is_playing():
                    self.radio_player.play()
            else:
                # Se estiver no modo mensagem e pygame estiver pausado
                if pygame.mixer.get_busy() == 0 and hasattr(self, 'current_sound'):
                    pygame.mixer.unpause()
                    
                    # MODIFICAÇÃO CRÍTICA: Forçar volume máximo ao retomar
                    self.current_sound.set_volume(1.0)
                    print("VOLUME MÁXIMO GARANTIDO AO RETOMAR REPRODUÇÃO")
                    
                    self.message_playing = True
            
            self.is_playing = True
            return True
        except Exception as e:
            print(f"Erro ao iniciar reprodução: {str(e)}")
            return False
    
    def pause(self):
        """Pausa a reprodução atual."""
        if self.is_radio_mode:
            self.radio_player.pause()
        else:
            # Pausa o Pygame apenas se estiver tocando
            if pygame.mixer.get_busy():
                pygame.mixer.pause()
                self.message_playing = False
            
        self.is_playing = False

    def toggle_playback(self):
        """
        Alterna entre play e pause do player.
        
        Returns:
            bool: True se agora está reproduzindo, False se pausado
        """
        try:
            # Se o microfone estiver ativo, não permite alternar
            if self.mic_active:
                print("Não é possível alterar reprodução com microfone ativo")
                return False
                
            if self.is_playing:
                # Se está reproduzindo, pausa
                self.pause()
                return False
            else:
                # Se está pausado, retoma a reprodução
                success = self.play()
                return success
                
        except Exception as e:
            print(f"Erro ao alternar reprodução: {str(e)}")
            return False
    
    def toggle_microphone(self):
        """
        Versão modificada que desabilita a funcionalidade do microfone.
        
        Returns:
            bool: Sempre False (microfone desativado)
        """
        print("Funcionalidade de microfone desativada")
        return False
    
    def stop(self):
        """Para a reprodução."""
        self.radio_player.stop()
        pygame.mixer.stop()
        self.message_playing = False
        self.is_playing = False
    
    def set_radio_volume(self, volume, fade_duration=0):
        """
        Define o volume apenas do player de rádio.
        Utilizado para abaixar o volume da rádio durante a reprodução de mensagens.
        Suporta fade gradual se fade_duration > 0.
        
        Args:
            volume (int): Volume de 0 a 100
            fade_duration (float): Duração do fade em segundos (0 para imediato)
        """
        if fade_duration <= 0:
            # Aplicação imediata de volume
            print(f"Definindo volume da rádio para {volume}%")
            self.radio_player.audio_set_volume(volume)
            return
            
        # Aplicação gradual (fade)
        current_volume = self.radio_player.audio_get_volume()
        steps = int(fade_duration * 10)  # 10 passos por segundo
        if steps < 1:
            steps = 1
            
        volume_step = (volume - current_volume) / steps
        
        def fade_thread():
            temp_volume = current_volume
            for i in range(steps):
                temp_volume += volume_step
                vol = int(round(temp_volume))
                # Limita o volume entre 0 e 100
                vol = max(0, min(100, vol))
                self.radio_player.audio_set_volume(vol)
                print(f"Fade: ajustando volume para {vol}%")
                time.sleep(fade_duration / steps)
            
            # Garante que o volume final seja exatamente o solicitado
            self.radio_player.audio_set_volume(volume)
            print(f"Fade concluído: volume final {volume}%")
        
        # Inicia o fade em uma thread separada para não bloquear
        fade_thread = threading.Thread(target=fade_thread)
        fade_thread.daemon = True
        fade_thread.start()
        print(f"Iniciando fade de volume de {current_volume}% para {volume}% em {fade_duration} segundos")
    
    def switch_to_radio(self):
        """
        Muda a reprodução para a rádio - VERSÃO CORRIGIDA.
        NÃO fecha a rádio, apenas restaura o volume.
        """
        try:
            print("📻 Mudando para modo rádio...")
            
            # Para qualquer reprodução de mensagem
            pygame.mixer.stop()
            self.message_playing = False
            
            # Define modo rádio
            self.is_radio_mode = True
            
            # Não para e reinicia a rádio, apenas ajusta o volume
            # A rádio continua tocando em segundo plano
            if self.radio_player:
                # Apenas garante que o volume está restaurado
                # (o fade manager já cuida disso, mas por segurança)
                current_volume = self.radio_player.audio_get_volume()
                if current_volume < 100:
                    print(f"📻 Volume atual: {current_volume}%, aguardando fade...")
                
                self.is_playing = True
                print("✅ Modo rádio ativo (rádio continuou tocando em segundo plano)")
                return True
                
        except Exception as e:
            print(f"❌ Erro ao trocar para rádio: {str(e)}")
            return False



    def play_message(self, filename, message=None, fade_in_duration=0.0):
        """
        Reproduz uma mensagem usando Pygame.
        
        Args:
            filename (str): Nome do arquivo da mensagem
            message (MessageQueueItem, optional): Objeto de mensagem completo
            fade_in_duration (float): Duração do fade in em segundos
                    
        Returns:
            bool: True se a mensagem começou a tocar
        """
        # Se o microfone estiver ativo, não permite tocar mensagem
        if self.mic_active:
            print("Não é possível reproduzir mensagem com microfone ativo")
            return False
            
        try:
            # Verifica se o arquivo existe
            file_path = self.messages_path / filename
            if not file_path.exists():
                print(f"Arquivo de mensagem não encontrado: {file_path}")
                return False
            
            # Caminho absoluto para o arquivo
            abs_path = str(file_path.absolute())
            print(f"Tentando reproduzir mensagem com Pygame: {abs_path}")
            
            # Para qualquer reprodução atual do Pygame
            pygame.mixer.stop()
            
            # Limpa qualquer referência anterior ao som
            if hasattr(self, 'current_sound'):
                del self.current_sound
                
            # Tenta recarregar o mixer se necessário
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                pygame.mixer.set_num_channels(8)
            except Exception as e:
                print(f"Erro ao reiniciar mixer: {str(e)}")
            
            # Carrega o arquivo de som
            try:
                print(f"Carregando som de: {abs_path}")
                self.current_sound = pygame.mixer.Sound(abs_path)
                print(f"Duração do som: {self.current_sound.get_length()} segundos")
                
                # MODIFICAÇÃO CRÍTICA: Define o volume para máximo (1.0 = 100%)
                # e desabilita qualquer fade-in
                self.current_sound.set_volume(1.0)
                print("VOLUME DA MENSAGEM DEFINIDO PARA 100%")
                
            except pygame.error as e:
                print(f"Erro ao carregar som: {str(e)}")
                # Tenta imprimir mais informações sobre o arquivo
                import os
                if os.path.exists(abs_path):
                    print(f"Arquivo existe, tamanho: {os.path.getsize(abs_path)} bytes")
                else:
                    print(f"Arquivo não existe no caminho especificado")
                return False
            
            # Inicia a reprodução
            print("Reproduzindo o som...")
            channel = self.current_sound.play(fade_ms = 10000)
            if channel is None:
                print("Falha ao iniciar reprodução - nenhum canal disponível")
            
            self.message_playing = True
            self.is_playing = True
            self.is_radio_mode = False
            
            # Armazena a mensagem atual
            self.current_message = message
            
            # Calcula o tempo de término
            duration = self.current_sound.get_length()
            if duration <= 0:
                # Se não conseguir obter a duração, usa um valor padrão
                file_size = os.path.getsize(abs_path)
                # Estima aproximadamente 1 segundo por 10KB
                estimated_duration = max(10, file_size / 10000)
                print(f"Duração estimada: {estimated_duration}s baseado no tamanho do arquivo")
                duration = estimated_duration
            
            # Define o tempo de término estimado
            self.end_time = datetime.now() + timedelta(seconds=duration)
            
            # Se temos uma mensagem atual, atualiza seu tempo de término
            if self.current_message is not None:
                self.current_message.end_time = self.end_time
                print(f"Mensagem '{filename}' com duração de {duration}s, término estimado: {self.end_time.strftime('%H:%M:%S')}")
            
            # Reinicia o timer de verificação
            self.last_check_time = datetime.now()
            # Reset flag de fadeout
            self._fadeout_applied = False
            
            return True
                
        except Exception as e:
            print(f"Erro ao reproduzir mensagem: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def toggle_microphone(self):
        """
        Ativa ou desativa o microfone.
        Quando ativado, abaixa o volume da mensagem/rádio mas continua a reprodução.
        Quando desativado, restaura o volume original.
        
        Returns:
            bool: Novo estado do microfone (True para ativo)
        """
        try:
            # Se estiver desativando o microfone
            if self.mic_active:
                # Desativa o microfone
                self.microphone_service.stop_microphone()
                
                # Restaura o volume original
                if self.is_radio_mode:
                    # Restaura o volume da rádio ao original
                    self.set_radio_volume(self.original_volume, fade_duration=1.0)
                else:
                    # Se estamos no modo mensagem, restauramos o volume da mensagem
                    if hasattr(self, 'current_sound'):
                        # Imediatamente restaura o volume para 1.0 (100%)
                        self.current_sound.set_volume(1.0)
                        print("Volume da mensagem restaurado para 100% após desativação do microfone")
                
                # Atualiza as flags
                self.mic_active = False
                
                print("Microfone desativado, volume de áudio restaurado")
                return False
                
            # Se estiver ativando o microfone
            else:
                # Salva o estado atual e o modo
                was_playing = self.is_playing
                was_radio_mode = self.is_radio_mode
                
                # Salva o volume original e reduz o volume para um nível baixo (mas não zero)
                LOW_VOLUME = 0.05  # 5% do volume para ainda ser audível em segundo plano
                
                if self.is_radio_mode:
                    self.original_volume = self.radio_player.audio_get_volume()
                    # Baixa o volume da rádio para um nível baixo
                    self.set_radio_volume(int(self.original_volume * LOW_VOLUME), fade_duration=0.5)
                else:
                    # Estamos no modo mensagem
                    if hasattr(self, 'current_sound'):
                        # Salvamos o volume original da mensagem (que deve ser 1.0)
                        self.original_message_volume = 1.0
                        
                        # Imediatamente abaixa o volume da mensagem
                        self.current_sound.set_volume(LOW_VOLUME)
                        print(f"Volume da mensagem reduzido para {LOW_VOLUME * 100}% devido à ativação do microfone")
                
                # Ativa o microfone
                if self.microphone_service.start_microphone():
                    self.mic_active = True
                    # Preservamos o estado de reprodução e o modo atual
                    self.is_playing = was_playing
                    self.is_radio_mode = was_radio_mode
                    print("Microfone ativado, volume de áudio reduzido")
                    return True
                else:
                    # Se falhar, restaura o áudio original
                    if self.is_radio_mode:
                        self.set_radio_volume(self.original_volume, fade_duration=0.5)
                    else:
                        # Restaura o volume da mensagem
                        if hasattr(self, 'current_sound'):
                            self.current_sound.set_volume(1.0)
                    print("Falha ao ativar microfone")
                    return False
                    
        except Exception as e:
            print(f"Erro ao alternar microfone: {str(e)}")
            # Em caso de erro, tenta restaurar o estado anterior
            if hasattr(self, 'is_radio_mode') and not self.is_radio_mode and hasattr(self, 'original_message_volume'):
                # Tenta restaurar o volume da mensagem
                if hasattr(self, 'current_sound'):
                    self.current_sound.set_volume(1.0)
            elif hasattr(self, 'is_radio_mode') and self.is_radio_mode and hasattr(self, 'original_volume'):
                # Tenta restaurar o volume da rádio
                self.set_radio_volume(self.original_volume)
            return False
    
    def get_state(self):
        """
        Obtém o estado atual da reprodução de forma amigável.
        
        Returns:
            str: Estado atual como string legível
        """
        try:
            # Se o microfone estiver ativo, retorna esse estado
            if self.mic_active:
                return self.PlayerState.MIC_ACTIVE
                
            if self.is_radio_mode:
                # Verifica o estado do VLC
                if self.radio_player.is_playing():
                    return self.PlayerState.PLAYING
                elif self.radio_player.get_state() == vlc.State.Paused:
                    return self.PlayerState.PAUSED
                elif self.radio_player.get_state() == vlc.State.Opening:
                    return self.PlayerState.CONNECTING
                elif self.radio_player.get_state() == vlc.State.Buffering:
                    return self.PlayerState.BUFFERING
                elif self.radio_player.get_state() == vlc.State.Error:
                    return self.PlayerState.ERROR
                else:
                    return self.PlayerState.STOPPED
            else:
                # Verifica o estado do Pygame
                if pygame.mixer.get_busy():
                    return self.PlayerState.PLAYING
                else:
                    return self.PlayerState.STOPPED
                
        except Exception as e:
            print(f"Erro ao obter estado: {str(e)}")
            return self.PlayerState.ERROR
    
    def is_media_ended(self):
        """
        Verifica se a mídia atual terminou de tocar.
        
        Returns:
            bool: True se a mídia terminou
        """
        # Se o microfone estiver ativo, não verificamos
        if self.mic_active:
            return False
            
        # Se estamos no modo rádio, nunca termina
        if self.is_radio_mode:
            return False
        
        try:
            # Verificação pelo tempo decorrido
            now = datetime.now()
            
            # Verifica se o Pygame ainda está reproduzindo
            is_playing = pygame.mixer.get_busy()
            
            # Se o Pygame indica que não está tocando, mas a flag message_playing está True
            if not is_playing and self.message_playing:
                print("DETECÇÃO: Mensagem terminou (pygame parou)")
                self.message_playing = False
                return True
            
            # Se temos um horário de término definido
            if self.end_time:
                # MODIFICAÇÃO: Não aplicar fadeout, para evitar redução do volume da mensagem
                
                # Verificação de término pelo tempo
                if now >= self.end_time:
                    print(f"DETECÇÃO: Mensagem terminou por tempo esgotado")
                    self.message_playing = False
                    return True
                    
                # ADICIONAR: Verificação precisa do estado atual
                if not is_playing and now < self.end_time:
                    print(f"DETECÇÃO: Mensagem terminou antes do previsto (parou antes do tempo)")
                    self.message_playing = False
                    return True
                    
                # Verificação periódica do tempo decorrido (a cada 5 segundos)
                time_since_last_check = (now - self.last_check_time).total_seconds()
                if time_since_last_check >= 5:
                    self.last_check_time = now
                    # Imprime informação sobre o andamento
                remaining = (self.end_time - now).total_seconds()
                if not hasattr(self, '_fadeout_applied'):
                    self._fadeout_applied = False
                    
                if not self._fadeout_applied and remaining < 1.0 and is_playing:
                    print(f"FADEOUT: Aplicando fadeout da mensagem (restam {remaining:.2f}s)")
                    # Fade gradual de 800ms
                    pygame.mixer.fadeout(800)  # fadeout suave de 800ms
                    self._fadeout_applied = True
                                
                # Verificação de término pelo tempo
                if now >= self.end_time:
                    print(f"DETECÇÃO: Mensagem terminou por tempo esgotado")
                    self.message_playing = False
                    return True
            else:
                # Se não temos horário de término, mas estamos no modo mensagem
                # é possível que a mensagem não tenha sido inicializada corretamente
                if not self.is_radio_mode and hasattr(self, 'current_message') and not is_playing:
                    print("DETECÇÃO: Mensagem sem horário de término definido e não está tocando")
                    self.message_playing = False
                    return True
            
            return False
                
        except Exception as e:
            print(f"Erro ao verificar fim da mídia: {str(e)}")
            return True  # Em caso de erro, considera que terminou
    
    def get_playback_info(self):
        """
        Obtém informações sobre a reprodução atual.
        
        Returns:
            tuple: (posição atual em ms, duração total em ms, porcentagem)
        """
        try:
            if self.is_radio_mode:
                # Para a rádio, usamos o VLC
                duration = self.radio_player.get_length()  # em ms
                position = self.radio_player.get_time()  # em ms
                
                if duration > 0:
                    percentage = (position / duration) * 100
                else:
                    percentage = 0
                    
                return position, duration, percentage
            else:
                # Para mensagens, calculamos com base no tempo
                if hasattr(self, 'current_sound') and self.end_time:
                    duration_ms = int(self.current_sound.get_length() * 1000)
                    
                    # Calcula a posição com base no tempo
                    if self.message_playing:
                        now = datetime.now()
                        total_time = (self.end_time - now).total_seconds() * 1000
                        position_ms = max(0, duration_ms - int(total_time))
                    else:
                        position_ms = 0
                    
                    if duration_ms > 0:
                        percentage = (position_ms / duration_ms) * 100
                    else:
                        percentage = 0
                        
                    return position_ms, duration_ms, percentage
                    
                return 0, 0, 0
            
        except Exception as e:
            print(f"Erro ao obter informações de reprodução: {str(e)}")
            return 0, 0, 0
    
    def has_error(self):
        """
        Verifica se ocorreu um erro na reprodução.
        
        Returns:
            bool: True se ocorreu um erro
        """
        try:
            if self.is_radio_mode:
                return self.radio_player.get_state() == vlc.State.Error
            else:
                # Pygame não tem estado de erro explícito
                return False
                
        except Exception as e:
            print(f"Erro ao verificar status de erro: {str(e)}")
            return True  # Em caso de exceção, considera que há erro
            
    def cleanup(self):
        """
        Libera todos os recursos utilizados pelo serviço de reprodução.
        Deve ser chamado ao encerrar a aplicação.
        """
        # Para todas as reproduções
        self.stop()
        
        # Garante que o microfone está desativado e libera recursos do microfone, se existir
        if hasattr(self, 'mic_active') and self.mic_active and self.microphone_service is not None:
            self.microphone_service.stop_microphone()
        
        # Libera recursos do microfone, se existir
        if hasattr(self, 'microphone_service') and self.microphone_service is not None:
            self.microphone_service.cleanup()
        
        # Libera recursos do gerenciador de fontes
        if hasattr(self, 'source_manager'):
            self.source_manager.cleanup()