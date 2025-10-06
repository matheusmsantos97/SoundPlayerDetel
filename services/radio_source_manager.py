#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gerenciador de fontes de rádio.
Suporta fontes de streaming online e dispositivos físicos.
"""

import json
from pathlib import Path
import pyaudio
import time
import threading

class RadioSource:
    """Representa uma fonte de rádio (streaming ou dispositivo)"""
    
    TYPE_STREAM = "stream"
    TYPE_DEVICE = "device"
    
    def __init__(self, name, source_type, url=None, device_index=None):
        """
        Inicializa uma fonte de rádio.
        
        Args:
            name (str): Nome amigável da fonte
            source_type (str): Tipo da fonte (stream ou device)
            url (str, optional): URL do streaming (apenas para tipo stream)
            device_index (int, optional): Índice do dispositivo (apenas para tipo device)
        """
        self.name = name
        self.source_type = source_type
        self.url = url
        self.device_index = device_index
    
    def to_dict(self):
        """Converte a fonte para um dicionário para serialização"""
        return {
            'name': self.name,
            'source_type': self.source_type,
            'url': self.url,
            'device_index': self.device_index
        }
    
    @classmethod
    def from_dict(cls, data):
        """Cria uma fonte a partir de um dicionário (desserialização)"""
        return cls(
            name=data.get('name', 'Sem Nome'),
            source_type=data.get('source_type', cls.TYPE_STREAM),
            url=data.get('url'),
            device_index=data.get('device_index')
        )
    
    def __str__(self):
        """Representação string da fonte"""
        if self.source_type == self.TYPE_STREAM:
            return f"{self.name} (Streaming)"
        else:
            return f"{self.name} (Dispositivo)"


class RadioSourceManager:
    """
    Gerencia diferentes fontes de rádio.
    Suporta salvar/carregar as configurações.
    """
    
    def __init__(self, config_dir):
        """
        Inicializa o gerenciador de fontes.
        
        Args:
            config_dir (str ou Path): Diretório de configuração
        """
        self.config_dir = Path(config_dir)
        self.sources_file = self.config_dir / "radio_sources.json"
        self.sources = []
        self.current_source_index = 0
        
        # Carrega fontes salvas ou cria padrões
        self.load_sources()
        
        # Inicializa pyaudio para listar dispositivos
        self.audio = pyaudio.PyAudio()
    
    def load_sources(self):
        """Carrega as fontes do arquivo de configuração"""
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Carrega as fontes
                    self.sources = [RadioSource.from_dict(src) for src in data.get('sources', [])]
                    
                    # Carrega a fonte atual
                    self.current_source_index = data.get('current_source_index', 0)
                    # Garantir que o índice é válido
                    if self.current_source_index >= len(self.sources):
                        self.current_source_index = 0
                    
                    print(f"Fontes de rádio carregadas: {len(self.sources)} fontes")
                    
            except Exception as e:
                print(f"Erro ao carregar fontes: {str(e)}")
                self._create_default_sources()
        else:
            self._create_default_sources()
    
    def _create_default_sources(self):
        """Cria fontes padrão se não existirem configurações"""
        # Fonte padrão de streaming - JB FM
        default_stream = RadioSource(
            name="SOUND PLAYER DETEL",
            source_type=RadioSource.TYPE_STREAM,
            url="https://24233.live.streamtheworld.com/JBFMAAC.aac"
        )
        
        self.sources = [default_stream]
        self.current_source_index = 0
        
        # Salva imediatamente as fontes padrão
        self.save_sources()
        
        print("Fontes padrão criadas")
    
    def save_sources(self):
        """Salva as fontes no arquivo de configuração"""
        try:
            # Cria o diretório se não existir
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Serializa as fontes
            data = {
                'sources': [src.to_dict() for src in self.sources],
                'current_source_index': self.current_source_index
            }
            
            # Salva no arquivo
            with open(self.sources_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            print(f"Fontes de rádio salvas: {len(self.sources)} fontes")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar fontes: {str(e)}")
            return False
    
    def add_source(self, name, source_type, url=None, device_index=None):
        """
        Adiciona uma nova fonte de rádio.
        
        Args:
            name (str): Nome amigável da fonte
            source_type (str): Tipo da fonte (stream ou device)
            url (str, optional): URL do streaming (apenas para tipo stream)
            device_index (int, optional): Índice do dispositivo (apenas para tipo device)
            
        Returns:
            RadioSource: A fonte criada ou None em caso de erro
        """
        try:
            # Validações básicas
            if source_type == RadioSource.TYPE_STREAM and not url:
                print("URL é obrigatória para fontes de streaming")
                return None
                
            if source_type == RadioSource.TYPE_DEVICE and device_index is None:
                print("Índice do dispositivo é obrigatório para fontes de dispositivo")
                return None
            
            # Cria a nova fonte
            new_source = RadioSource(name, source_type, url, device_index)
            
            # Adiciona à lista
            self.sources.append(new_source)
            
            # Salva as alterações
            self.save_sources()
            
            return new_source
            
        except Exception as e:
            print(f"Erro ao adicionar fonte: {str(e)}")
            return None
    
    def remove_source(self, index):
        """
        Remove uma fonte pelo índice.
        
        Args:
            index (int): Índice da fonte a remover
            
        Returns:
            bool: True se removido com sucesso
        """
        if 0 <= index < len(self.sources):
            # Não permitir remover a última fonte
            if len(self.sources) <= 1:
                print("Não é possível remover a última fonte")
                return False
            
            # Remove a fonte
            del self.sources[index]
            
            # Ajusta o índice atual se necessário
            if self.current_source_index >= len(self.sources):
                self.current_source_index = 0
            
            # Salva as alterações
            self.save_sources()
            
            return True
        else:
            print("Índice de fonte inválido")
            return False
    
    def set_current_source(self, index):
        """
        Define a fonte atual por índice.
        
        Args:
            index (int): Índice da fonte
            
        Returns:
            RadioSource: A fonte atual ou None se o índice for inválido
        """
        if 0 <= index < len(self.sources):
            self.current_source_index = index
            self.save_sources()
            return self.get_current_source()
        else:
            print("Índice de fonte inválido")
            return None
    
    def get_current_source(self):
        """
        Obtém a fonte atual.
        
        Returns:
            RadioSource: A fonte atual
        """
        if self.sources and 0 <= self.current_source_index < len(self.sources):
            return self.sources[self.current_source_index]
        elif self.sources:
            # Ajusta para um índice válido
            self.current_source_index = 0
            return self.sources[0]
        else:
            # Não deveria acontecer, mas por precaução
            self._create_default_sources()
            return self.sources[0]
    
    def get_audio_devices(self):
        """
        Obtém a lista de dispositivos de áudio disponíveis.
        
        Returns:
            list: Lista de dispositivos de áudio de entrada
        """
        devices = []
        try:
            info = self.audio.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            
            for i in range(0, numdevices):
                device_info = self.audio.get_device_info_by_index(i)
                # Filtra apenas dispositivos de entrada que podem ser tuners de rádio
                if device_info.get('maxInputChannels') > 0:
                    # Corrigir nome do dispositivo com problema de codificação
                    device_name = device_info.get('name')
                    
                    # Função específica para corrigir problemas de codificação em português
                    def fix_portuguese_encoding(text):
                        # Correções específicas para caracteres problemáticos comuns
                        replacements = {
                            'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
                            'Ã£': 'ã', 'Ãµ': 'õ', 'Ã¢': 'â', 'Ãª': 'ê', 'Ã´': 'ô',
                            'Ã§': 'ç', 'Ã‰': 'É', 'Ãƒ': 'Ã', 'Ã‡': 'Ç',
                            'estÃ©reo': 'estéreo', 'SaÃ­da': 'Saída', 'Ãudio': 'Áudio',
                            'MicrofoneÃ': 'Microfone'
                        }
                        
                        result = text
                        for wrong, correct in replacements.items():
                            result = result.replace(wrong, correct)
                        
                        return result
                    
                    # Aplica a correção
                    device_name = fix_portuguese_encoding(device_name)
                    
                    devices.append({
                        'index': i,
                        'name': device_name,
                        'channels': device_info.get('maxInputChannels')
                    })
            
            return devices
        except Exception as e:
            print(f"Erro ao listar dispositivos: {str(e)}")
            return []
    
    def cleanup(self):
        """Libera recursos"""
        if hasattr(self, 'audio'):
            self.audio.terminate()