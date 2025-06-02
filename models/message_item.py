#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Definição da classe MessageQueueItem que representa um item na fila de reprodução.
"""

from datetime import datetime, timedelta

# No arquivo message_item.py, modifique a classe MessageQueueItem para suportar intervalos fracionários:

class MessageQueueItem:
    """
    Representa uma mensagem na fila de reprodução.
    
    Armazena informações sobre a mensagem, incluindo:
    - Nome do arquivo
    - Prioridade (1-10, onde 1 é mais alta)
    - Intervalo de repetição em minutos (pode ser fracionário para representar segundos)
    - Horário da próxima reprodução
    """
    
    def __init__(self, filename, priority, interval):
        self.filename = filename
        self.priority = priority
        self.interval = float(interval)  # Converte para float para suportar valores fracionários
        self.next_play_time = datetime.now()
        self.end_time = None
        self.is_pending = priority > 1  # Mensagens de prioridade > 1 começam pendentes
        
    def __lt__(self, other):
        """
        Comparação para ordenação na fila de prioridade.
        Ordena primeiro por prioridade, depois por próximo horário.
        
        Args:
            other (MessageQueueItem): Outro item a comparar
            
        Returns:
            bool: True se este item tiver maior prioridade ou mesma prioridade 
                 e horário mais cedo que o outro
        """
        return (self.priority, self.next_play_time) < (other.priority, other.next_play_time)
    
    def update_next_play_time(self):
        """
        Atualiza o próximo horário de reprodução baseado no horário de término da mensagem anterior.
        
        Returns:
            bool: True se a mensagem deve ser repetida, False caso contrário
        """
        if self.interval <= 0:
            # Se intervalo é 0, não repete
            return False
        
        # Calcula o próximo horário de reprodução com base no horário de término
        # MODIFICAÇÃO IMPORTANTE: Garante a precisão do cálculo do intervalo
        if self.end_time:
            # Cálculo preciso para suportar segundos
            seconds = self.interval * 60  # Converte minutos para segundos
            self.next_play_time = self.end_time + timedelta(seconds=seconds)
            print(f"INTERVALO: Horário de término definido para {self.end_time.strftime('%H:%M:%S')}")
            print(f"INTERVALO: Próxima reprodução em {seconds} segundos")
            print(f"INTERVALO: Agendado para {self.next_play_time.strftime('%H:%M:%S')}")
        else:
            # Se não houver horário de término, usa o horário atual
            seconds = self.interval * 60
            current_time = datetime.now()
            self.next_play_time = current_time + timedelta(seconds=seconds)
            print(f"INTERVALO: Sem horário de término, usando hora atual {current_time.strftime('%H:%M:%S')}")
            print(f"INTERVALO: Próxima reprodução em {seconds} segundos")
            print(f"INTERVALO: Agendado para {self.next_play_time.strftime('%H:%M:%S')}")
        
        # Formata a exibição de acordo com o intervalo
        if self.interval < 1.0:
            seconds = int(self.interval * 60)
            print(f"Próxima reprodução de '{self.filename}' agendada para: {self.get_next_play_time_str()} (a cada {seconds} segundos)")
        else:
            print(f"Próxima reprodução de '{self.filename}' agendada para: {self.get_next_play_time_str()} (a cada {self.interval:.1f} minutos)")
        
        return True
    
    def get_next_play_time_str(self):
        """
        Retorna o próximo horário de reprodução como string formatada.
        
        Returns:
            str: Horário formatado (ex: "14:30:00")
        """
        return self.next_play_time.strftime("%H:%M:%S")
    
    def time_until_play(self):
        """
        Calcula o tempo restante até a próxima reprodução.
        
        Returns:
            timedelta: Diferença de tempo até a reprodução
        """
        return self.next_play_time - datetime.now()