#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Serviço para gerenciar o microfone.
Permite capturar áudio do microfone e enviá-lo para a saída.
"""

import pyaudio
import threading
import time

class MicrophoneService:
    """
    Serviço que gerencia a captura e reprodução do áudio do microfone.
    """
    
    def __init__(self):
        """
        Inicializa o serviço de microfone.
        """
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.is_active = False
        self.stop_event = threading.Event()
        self.thread = None
        
        # Parâmetros de áudio
        # Essas configurações podem precisar ser ajustadas para o seu hardware
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100  # Alguns dispositivos funcionam melhor com 48000 ou 16000
        self.chunk = 1024
        self.input_device_index = None  # None = dispositivo padrão
        self.output_device_index = None  # None = dispositivo padrão
        
        # Tenta encontrar o melhor dispositivo de entrada
        self._find_best_devices()
    
    def _find_best_devices(self):
        """
        Tenta identificar os melhores dispositivos de entrada e saída.
        """
        try:
            # Imprime informações de todos os dispositivos para diagnóstico
            info = self.audio.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            
            print("\nDispositivos de áudio disponíveis:")
            for i in range(0, numdevices):
                device_info = self.audio.get_device_info_by_index(i)
                name = device_info.get('name')
                max_input_channels = device_info.get('maxInputChannels')
                max_output_channels = device_info.get('maxOutputChannels')
                
                print(f"Dispositivo {i}: {name}")
                print(f"   Canais de entrada: {max_input_channels}")
                print(f"   Canais de saída: {max_output_channels}")
                
                # Encontrar um bom dispositivo de entrada (microfone)
                if max_input_channels > 0 and self.input_device_index is None:
                    # Tentativa de encontrar um microfone por nome
                    if 'mic' in name.lower() or 'input' in name.lower():
                        self.input_device_index = i
                        print(f"   SELECIONADO COMO DISPOSITIVO DE ENTRADA")
            
            # Se nenhum dispositivo específico foi encontrado, mantenha como None para usar o padrão
            print(f"\nDispositivo de entrada selecionado: {self.input_device_index if self.input_device_index is not None else 'Padrão'}")
            print(f"Dispositivo de saída selecionado: {self.output_device_index if self.output_device_index is not None else 'Padrão'}")
        
        except Exception as e:
            print(f"Erro ao buscar dispositivos de áudio: {str(e)}")
    
    def start_microphone(self):
        """
        Inicia a captura do microfone e envia para a saída de áudio.
        
        Returns:
            bool: True se o microfone foi iniciado com sucesso
        """
        if self.is_active:
            print("Microfone já está ativo")
            return True
            
        try:
            # Configura o stream de entrada (microfone)
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=self.input_device_index,
                stream_callback=None  # Sem callback para permitir leitura manual
            )
            
            # Configura o stream de saída (alto-falantes)
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk,
                output_device_index=self.output_device_index
            )
            
            # Reseta o evento de parada
            self.stop_event.clear()
            
            # Inicia a thread de processamento
            self.thread = threading.Thread(target=self._process_audio)
            self.thread.daemon = True
            self.thread.start()
            
            self.is_active = True
            print("Microfone ativado com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro ao iniciar microfone: {str(e)}")
            self.stop_microphone()
            return False
    
    def stop_microphone(self):
        """
        Para a captura do microfone.
        
        Returns:
            bool: True se o microfone foi parado com sucesso
        """
        if not self.is_active:
            return True
            
        try:
            # Sinaliza para a thread parar
            self.stop_event.set()
            
            # Espera a thread terminar (com timeout)
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
            
            # Fecha os streams
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None
                
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None
            
            self.is_active = False
            print("Microfone desativado")
            return True
            
        except Exception as e:
            print(f"Erro ao parar microfone: {str(e)}")
            return False
    
    def toggle_microphone(self):
        """
        Alterna o estado do microfone (ligado/desligado).
        
        Returns:
            bool: O novo estado do microfone (True para ativo)
        """
        if self.is_active:
            self.stop_microphone()
            return False
        else:
            return self.start_microphone()
    
    def _process_audio(self):
        """
        Processa o áudio do microfone em tempo real.
        Esta função executa em uma thread separada.
        """
        try:
            print("Iniciando processamento de áudio do microfone...")
            while not self.stop_event.is_set():
                # Lê dados do microfone
                try:
                    data = self.input_stream.read(self.chunk)
                    # Mostra atividade de áudio (para diagnóstico)
                    level = sum(abs(int.from_bytes(data[i:i+2], byteorder='little', signed=True)) 
                               for i in range(0, len(data), 2)) / (self.chunk)
                    if level > 500:  # Valor arbitrário para detecção de som
                        print(f"Atividade de áudio detectada: {level:.0f}")
                        
                    # Envia para a saída
                    self.output_stream.write(data)
                except IOError as e:
                    # Erro comum quando o buffer está cheio ou vazio - podemos ignorar
                    pass
                except Exception as e:
                    print(f"Erro na leitura/escrita de áudio: {str(e)}")
                    
                # Pequena pausa para não sobrecarregar o CPU
                time.sleep(0.001)
                
        except Exception as e:
            print(f"Erro no processamento de áudio: {str(e)}")
            self.stop_event.set()
    
    def set_input_device(self, device_index):
        """
        Define o dispositivo de entrada manualmente.
        
        Args:
            device_index (int): Índice do dispositivo a ser usado
            
        Returns:
            bool: True se o dispositivo foi alterado com sucesso
        """
        was_active = self.is_active
        
        # Para o microfone se estiver ativo
        if was_active:
            self.stop_microphone()
        
        # Define o novo dispositivo
        self.input_device_index = device_index
        print(f"Dispositivo de entrada alterado para: {device_index}")
        
        # Reinicia o microfone se estava ativo
        if was_active:
            return self.start_microphone()
        
        return True
    
    def cleanup(self):
        """
        Libera recursos e encerra o PyAudio.
        Deve ser chamado quando a aplicação estiver sendo encerrada.
        """
        self.stop_microphone()
        self.audio.terminate()
        print("Recursos do microfone liberados")
        
    def get_device_list(self):
        """
        Retorna uma lista de todos os dispositivos de áudio disponíveis.
        
        Returns:
            list: Lista de dicionários com informações dos dispositivos
        """
        devices = []
        info = self.audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        for i in range(0, numdevices):
            device_info = self.audio.get_device_info_by_index(i)
            devices.append({
                'index': i,
                'name': device_info.get('name'),
                'inputs': device_info.get('maxInputChannels'),
                'outputs': device_info.get('maxOutputChannels'),
                'default_input': i == self.audio.get_default_input_device_info().get('index'),
                'default_output': i == self.audio.get_default_output_device_info().get('index')
            })
            
        return devices