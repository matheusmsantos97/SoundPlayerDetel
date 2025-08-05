#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Definição da classe MessageQueueItem que representa um item na fila de reprodução.
"""

from datetime import datetime, timedelta

class MessageQueueItem:
    """
    Representa uma mensagem na fila de reprodução.
    
    Armazena informações sobre a mensagem, incluindo:
    - Nome do arquivo
    - Prioridade (1-10, onde 1 é mais alta)
    - Intervalo de repetição em minutos (pode ser fracionário para representar segundos)
    - Horário da próxima reprodução
    - Último horário em que foi reproduzida
    """
    
    def __init__(self, filename, priority, interval):
            self.filename = filename
            self.priority = priority
            self.interval = float(interval)  # Intervalo em minutos
            self.interval_seconds = int(float(interval) * 60)  # Converte para segundos
            self.next_play_time = datetime.now()
            self.end_time = None
            self.is_pending = priority > 1  # Mensagens com prioridade >1 começam pendentes
            self.last_played = None
        
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
        Atualiza o horário da próxima reprodução baseado no intervalo.
        O intervalo começa a contar APÓS o término completo (incluindo fade).
        """
        if self.interval <= 0:
            return False
        
        # Garante que temos um tempo de término válido
        if not self.end_time:
            self.end_time = datetime.now()
            
        # Calcula o próximo horário baseado no término + intervalo
        self.next_play_time = self.end_time + timedelta(seconds=self.interval_seconds)
        
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