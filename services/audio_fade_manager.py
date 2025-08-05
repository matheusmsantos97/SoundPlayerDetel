"""
Sistema de Fade Suave para JB FM Player
Gerencia transições suaves entre rádio e mensagens
"""

import threading
import time
import math
from datetime import datetime

class AudioFadeManager:
    """
    Gerenciador de fades suaves para transições de áudio.
    Proporciona transições profissionais entre rádio e mensagens.
    """
    
    def __init__(self, player_service):
        """
        Inicializa o gerenciador de fade.
        
        Args:
            player_service: Serviço de reprodução de áudio
        """
        self.player_service = player_service
        
        # Configurações de fade
        self.fade_duration = 4.0  # segundos
        self.fade_steps = 100  # passos por segundo (suavidade)
        self.background_volume = 2  # Volume da rádio durante mensagem (%)
        self.normal_volume = 100  # Volume normal da rádio (%)
        
        # Estado atual
        self.fade_threads = []
        self.current_radio_volume = 100
        
        # Tipos de curva de fade
        self.FADE_LINEAR = "linear"
        self.FADE_EXPONENTIAL = "exponential" 
        self.FADE_LOGARITHMIC = "logarithmic"
        self.FADE_SMOOTH = "smooth"  # Curva S suave
        
        self.fade_curve = self.FADE_SMOOTH  # Padrão mais suave
        
        print(f"🎵 AudioFadeManager inicializado:")
        print(f"   Duração: {self.fade_duration}s")
        print(f"   Curva: {self.fade_curve}")
        print(f"   Volume de fundo: {self.background_volume}%")
    
    def calculate_fade_value(self, progress, curve_type=None):
        """
        Calcula o valor do fade baseado na curva selecionada.
        
        Args:
            progress (float): Progresso de 0.0 a 1.0
            curve_type (str): Tipo de curva
            
        Returns:
            float: Valor do fade de 0.0 a 1.0
        """
        if curve_type is None:
            curve_type = self.fade_curve
            
        # Garante que progress está no range correto
        progress = max(0.0, min(1.0, progress))
            
        if curve_type == self.FADE_LINEAR:
            return progress
            
        elif curve_type == self.FADE_EXPONENTIAL:
            return progress ** 2
            
        elif curve_type == self.FADE_LOGARITHMIC:
            return math.sqrt(progress)
            
        elif curve_type == self.FADE_SMOOTH:
            # Curva S suave (ease-in-out)
            return 0.5 * (1 + math.sin(math.pi * (progress - 0.5)))
        
        return progress  # Fallback para linear
    
    def fade_radio_volume(self, start_volume, end_volume, duration=None, fade_type=None):
        """
        Realiza fade suave no volume da rádio - VERSÃO CORRIGIDA.
        NUNCA zera o volume completamente.
        """
        if duration is None:
            duration = self.fade_duration
            
        if fade_type is None:
            fade_type = self.fade_curve
        
        # Garantir volume mínimo para evitar fechamento
        if end_volume < self.background_volume:
            end_volume = self.background_volume
        
        # Para threads anteriores
        self._stop_fade_threads()
        
        def fade_thread():
            try:
                steps = int(duration * self.fade_steps)
                if steps < 1:
                    steps = 1
                    
                step_delay = duration / steps
                
                print(f"🎵 FADE RÁDIO: {start_volume}% → {end_volume}% em {duration:.1f}s")
                
                for i in range(steps + 1):
                    if not hasattr(self, 'fade_threads') or len(self.fade_threads) == 0:
                        break
                        
                    progress = i / steps
                    fade_value = self.calculate_fade_value(progress, fade_type)
                    
                    # Interpola entre volumes
                    current_volume = int(start_volume + (end_volume - start_volume) * fade_value)
                    current_volume = max(self.background_volume, min(100, current_volume))  # NUNCA abaixo do mínimo
                    
                    # Aplica o volume
                    if hasattr(self.player_service, 'radio_player') and self.player_service.radio_player:
                        self.player_service.radio_player.audio_set_volume(current_volume)
                        self.current_radio_volume = current_volume
                    
                    time.sleep(step_delay)
                
                # Garante volume final exato (mas nunca zero)
                final_volume = max(self.background_volume, end_volume)
                self.player_service.radio_player.audio_set_volume(final_volume)
                print(f"✅ Fade concluído: volume final {final_volume}%")
                
            except Exception as e:
                print(f"❌ Erro no fade: {str(e)}")
        
        # Inicia fade em thread separada
        thread = threading.Thread(target=fade_thread, daemon=True)
        self.fade_threads.append(thread)
        thread.start()
        
        def fade_thread():
            try:
                steps = int(duration * self.fade_steps)
                if steps < 1:
                    steps = 1
                    
                step_delay = duration / steps
                
                print(f"🎵 FADE RÁDIO: {start_volume}% → {end_volume}% em {duration:.1f}s ({fade_type})")
                
                for i in range(steps + 1):
                    if not hasattr(self, 'fade_threads') or len(self.fade_threads) == 0:
                        # Thread foi cancelada
                        break
                        
                    progress = i / steps
                    fade_value = self.calculate_fade_value(progress, fade_type)
                    
                    # Interpola entre volumes
                    current_volume = int(start_volume + (end_volume - start_volume) * fade_value)
                    current_volume = max(0, min(100, current_volume))
                    
                    # Aplica o volume
                    if hasattr(self.player_service, 'radio_player'):
                        self.player_service.radio_player.audio_set_volume(current_volume)
                        self.current_radio_volume = current_volume
                    
                    # Debug a cada 20% do progresso
                    if i % max(1, steps // 5) == 0:
                        print(f"   Fade: {current_volume}% (progresso: {int(progress * 100)}%)")
                    
                    time.sleep(step_delay)
                
                print(f"✅ Fade da rádio concluído: volume final {end_volume}%")
                
            except Exception as e:
                print(f"❌ Erro no fade da rádio: {str(e)}")
        
        # Inicia fade em thread separada
        thread = threading.Thread(target=fade_thread, daemon=True)
        self.fade_threads.append(thread)
        thread.start()
    
    def _stop_fade_threads(self):
        """Para todas as threads de fade ativas."""
        # Limpa a lista, o que sinaliza às threads para pararem
        self.fade_threads.clear()
    
    def start_message_transition(self):
        """
        Inicia transição suave para reprodução de mensagem.
        
        Returns:
            bool: True se iniciou com sucesso
        """
        try:
            print("🎵 INICIANDO TRANSIÇÃO: Rádio → Mensagem")
            
            # Obtém o volume atual da rádio
            try:
                current_volume = self.player_service.radio_player.audio_get_volume()
                if current_volume <= 0:
                    current_volume = self.normal_volume
                self.current_radio_volume = current_volume
            except:
                current_volume = self.normal_volume
                self.current_radio_volume = current_volume
            
            print(f"   Volume atual da rádio: {current_volume}%")
            print(f"   Reduzindo para: {self.background_volume}%")
            
            # Fade out da rádio de forma suave
            if current_volume > self.background_volume:
                self.fade_radio_volume(
                    start_volume=current_volume,
                    end_volume=self.background_volume,
                    duration=self.fade_duration,
                    fade_type=self.fade_curve
                )
            else:
                print("⚠️ Volume da rádio já está baixo, pulando fade.")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro na transição para mensagem: {str(e)}")
            return False
    
    def end_message_transition(self):
        """
        Finaliza transição suave após reprodução de mensagem.
        
        Returns:
            bool: True se finalizou com sucesso
        """
        try:
            print("🎵 FINALIZANDO TRANSIÇÃO: Mensagem → Rádio")
            
            # Aguarda um pouco para a mensagem terminar completamente
            time.sleep(0.5)
            
            # Obtém o volume atual
            try:
                current_volume = self.player_service.radio_player.audio_get_volume()
                self.current_radio_volume = current_volume
            except:
                current_volume = self.background_volume
            
            print(f"   Volume atual da rádio: {current_volume}%")
            print(f"   Restaurando para: {self.normal_volume}%")
            
            # Fade in da rádio de volta ao volume normal
            self.fade_radio_volume(
                start_volume=current_volume,
                end_volume=self.normal_volume,
                duration=self.fade_duration,
                fade_type=self.fade_curve
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Erro na transição de volta à rádio: {str(e)}")
            return False
    
    def set_fade_settings(self, duration=None, curve=None, background_vol=None):
        """
        Configura parâmetros do fade.
        
        Args:
            duration (float): Duração do fade em segundos
            curve (str): Tipo de curva (linear, exponential, logarithmic, smooth)
            background_vol (int): Volume da rádio durante mensagem (0-100)
        """
        if duration is not None:
            self.fade_duration = max(0.5, min(5.0, duration))
            print(f"⚙️ Duração do fade: {self.fade_duration}s")
            
        if curve is not None and curve in [self.FADE_LINEAR, self.FADE_EXPONENTIAL, 
                                          self.FADE_LOGARITHMIC, self.FADE_SMOOTH]:
            self.fade_curve = curve
            print(f"⚙️ Curva do fade: {self.fade_curve}")
            
        if background_vol is not None:
            self.background_volume = max(0, min(50, background_vol))
            print(f"⚙️ Volume de fundo: {self.background_volume}%")
    
    def apply_preset(self, preset_name):
        """
        Aplica preset de configuração.
        
        Args:
            preset_name (str): Nome do preset (professional, fast, smooth, dramatic)
        """
        presets = {
            "professional": {
                "duration": 2.5,
                "curve": self.FADE_SMOOTH,
                "background_vol": 5
            },
            "fast": {
                "duration": 1.0,
                "curve": self.FADE_EXPONENTIAL, 
                "background_vol": 10
            },
            "smooth": {
                "duration": 3.0,
                "curve": self.FADE_LOGARITHMIC,
                "background_vol": 8
            },
            "dramatic": {
                "duration": 4.0,
                "curve": self.FADE_EXPONENTIAL,
                "background_vol": 2
            }
        }
        
        if preset_name in presets:
            preset = presets[preset_name]
            self.set_fade_settings(
                duration=preset["duration"],
                curve=preset["curve"],
                background_vol=preset["background_vol"]
            )
            print(f"✅ Preset '{preset_name}' aplicado")
        else:
            print(f"❌ Preset '{preset_name}' não encontrado")
    
    def cleanup(self):
        """Limpa recursos do gerenciador de fade."""
        print("🧹 Limpando recursos do AudioFadeManager")
        self._stop_fade_threads()
        
        # Restaura volume normal se necessário
        try:
            if hasattr(self.player_service, 'radio_player'):
                self.player_service.radio_player.audio_set_volume(self.normal_volume)
        except:
            pass