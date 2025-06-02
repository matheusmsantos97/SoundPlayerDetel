# -*- coding: utf-8 -*-

"""
Serviço de gerenciamento da fila de mensagens.
Gerencia a ordenação das mensagens por prioridade e tempo.
"""

import heapq
from datetime import datetime, timedelta
from pathlib import Path
from models.message_item import MessageQueueItem
from services.message_queue_serializer import MessageQueueSerializer

class QueueService:
    """
    Serviço que gerencia a fila de mensagens com prioridade.
    Usa um heap para manter a ordem ideal baseada em prioridade e horário.
    """
    
    def __init__(self, queue_file_path=None):
        """
        Inicializa o serviço de fila.
        
        Args:
            queue_file_path (str ou Path, optional): Caminho para o arquivo de persistência
        """
        self.message_queue = []  # Heap queue
        # Dicionário para armazenar o último horário de término por prioridade
        self.last_end_time_by_priority = {}
        # Último horário de término global (qualquer mensagem)
        self.last_global_end_time = None
        
        # NOVA LINHA: Rastreamento da mensagem atualmente em reprodução
        self.currently_playing = None
        
        # Configura o tempo de intervalo mínimo entre mensagens (em minutos)
        self.min_interval_between_messages = 1
        
        # Configurar serializador de persistência, se fornecido
        if queue_file_path:
            self.serializer = MessageQueueSerializer(queue_file_path)
            # Carrega a fila salva anteriormente
            saved_items = self.serializer.load_queue(MessageQueueItem)
            
            # Verifica e ajusta os horários que já passaram e remove duplicatas
            self._reset_expired_times(saved_items)
            
            # Adiciona os itens ao heap
            self.message_queue = saved_items
            # Reordena o heap
            if self.message_queue:
                heapq.heapify(self.message_queue)
                print("Fila de mensagens carregada do arquivo de persistência")
        else:
            self.serializer = None
    
    def _reset_expired_times(self, items):
        """
        Verifica e redefine os horários de reprodução que já passaram.
        Configura a sequência inicial de prioridades sem duplicar mensagens.
        """
        if not items:
            return
            
        now = datetime.now()
        
        # SOLUÇÃO MAIS RADICAL: usar um dicionário para garantir que não há duplicatas
        unique_items = {}
        
        # Identifica e elimina mensagens duplicadas
        for item in items[:]:  # Cria uma cópia da lista para iterar
            key = (item.filename, item.priority)
            if key in unique_items:
                # Se já temos um item com este arquivo e prioridade, 
                # mantenha apenas o mais recente
                if item.next_play_time > unique_items[key].next_play_time:
                    unique_items[key] = item
            else:
                unique_items[key] = item
        
        # Limpa a lista original e adiciona apenas os itens únicos
        items.clear()
        items.extend(unique_items.values())
        
        # Ordena por prioridade
        items.sort(key=lambda x: x.priority)
        
        # Configura as prioridades
        if items:
            lowest_priority = min(item.priority for item in items)
            
            for item in items:
                # Verifica se o horário de reprodução já passou
                if item.next_play_time <= now:
                    # Se for a menor prioridade, programa para tocar em breve
                    if item.priority == lowest_priority:
                        item.is_pending = False
                        item.next_play_time = now + timedelta(seconds=10)  # Alterado para 10 segundos
                        print(f"Mensagem '{item.filename}' (prioridade {item.priority}) configurada para tocar às {item.get_next_play_time_str()}")
                    else:
                        item.is_pending = True
                        print(f"Mensagem '{item.filename}' (prioridade {item.priority}) marcada como pendente")
                else:
                    # Se ainda não chegou o momento de tocar
                    if item.priority == lowest_priority:
                        item.is_pending = False
                    else:
                        item.is_pending = True
    
    def add_message(self, filename, priority, interval):
        """
        Adiciona uma mensagem à fila.
        CORREÇÃO COMPLETA: Implementa a configuração correta de horário e prioridade
        """
        # Verifica se já existe uma mensagem com este nome
        for item in self.message_queue:
            if item.filename == filename:
                print(f"ADIÇÃO: Mensagem '{filename}' já está na fila. Não será adicionada novamente.")
                return None

        # Cria o item da fila
        message = MessageQueueItem(filename, priority, interval)
        
        # Hora atual
        now = datetime.now()
        
        # ETAPA 1: Verificar se existem mensagens com prioridade mais alta (número menor)
        existing_priorities = [item.priority for item in self.message_queue]
        
        # Se não houver outras mensagens OU esta mensagem tiver a maior prioridade
        if not existing_priorities or priority <= min(existing_priorities):
            # MAIOR PRIORIDADE: programa para tocar em breve (10 segundos)
            message.next_play_time = now + timedelta(seconds=10)
            message.is_pending = False
            print(f"ADIÇÃO: Mensagem '{filename}' (prioridade {priority}) é a mais prioritária")
            print(f"  Programada para tocar em 10 segundos")
            
            # Se existirem outras mensagens, marca todas com prioridade menor como pendentes
            for item in self.message_queue:
                if item.priority > priority:
                    item.is_pending = True
                    print(f"  Mensagem '{item.filename}' (prioridade {item.priority}) marcada como pendente")
        else:
            # PRIORIDADE MENOR: aguarda a mensagem de maior prioridade terminar
            
            # Encontra a última mensagem de maior prioridade
            higher_priority = min(existing_priorities)
            
            if higher_priority in self.last_end_time_by_priority:
                # Se já temos um registro de término para a prioridade superior
                last_end = self.last_end_time_by_priority[higher_priority]
                
                # Programa para tocar após o intervalo a partir do último término
                seconds_interval = interval * 60  # Converte minutos para segundos
                message.next_play_time = last_end + timedelta(seconds=seconds_interval)
                
                print(f"ADIÇÃO: Mensagem '{filename}' (prioridade {priority}) programada após prioridade {higher_priority}")
                print(f"  Último término da prioridade {higher_priority}: {last_end.strftime('%H:%M:%S')}")
                print(f"  Intervalo: {seconds_interval} segundos")
                print(f"  Programada para: {message.next_play_time.strftime('%H:%M:%S')}")
            else:
                # Se não temos registro de término, programa para futuro próximo (30 segundos)
                message.next_play_time = now + timedelta(seconds=30)
                print(f"ADIÇÃO: Mensagem '{filename}' (prioridade {priority}) programada para daqui a 30 segundos")
                print(f"  (Não há registro de término da prioridade {higher_priority})")
            
            # Marca como pendente pois há prioridade maior
            message.is_pending = True
        
        # Adiciona à fila e reorganiza
        heapq.heappush(self.message_queue, message)
        
        # Log do intervalo configurado
        if interval < 1.0:
            seconds = int(interval * 60)
            print(f"ADIÇÃO: Mensagem '{filename}' configurada para repetir a cada {seconds} segundos")
        else:
            print(f"ADIÇÃO: Mensagem '{filename}' configurada para repetir a cada {interval:.1f} minutos")
        
        # Salva a fila atualizada
        self._save_queue()
        
        # Retorna a mensagem criada
        return message

    def register_message_end(self, message):
        """
        Registra que uma mensagem terminou de tocar e agenda a próxima na sequência.
        CORREÇÃO: Atualiza a mensagem na fila em vez de removê-la e adicioná-la novamente
        """
        # Registra o término desta mensagem
        end_time = message.end_time
        print(f"TÉRMINO REGISTRADO: Mensagem '{message.filename}' (prioridade {message.priority}) terminou às {end_time.strftime('%H:%M:%S')}")
        
        # Armazena o tempo de término para esta prioridade
        self.last_end_time_by_priority[message.priority] = end_time
        self.last_global_end_time = end_time
        
        # ETAPA 1: Localizar a mensagem na fila e atualizar seus valores
        original_message_found = False
        
        for msg in self.message_queue:
            if msg.filename == message.filename and msg.priority == message.priority:
                original_message_found = True
                
                # Se tiver intervalo, atualiza o próximo horário de reprodução
                if message.interval > 0:
                    # Calcula o próximo horário com base no intervalo
                    seconds_interval = message.interval * 60  # Converte minutos para segundos
                    msg.next_play_time = end_time + timedelta(seconds=seconds_interval)
                    msg.end_time = end_time
                    
                    # Registra o reagendamento
                    if message.interval < 1.0:
                        seconds = int(message.interval * 60)
                        print(f"REAGENDAMENTO: '{msg.filename}' reagendada para {msg.next_play_time.strftime('%H:%M:%S')} (a cada {seconds} segundos)")
                    else:
                        print(f"REAGENDAMENTO: '{msg.filename}' reagendada para {msg.next_play_time.strftime('%H:%M:%S')} (a cada {message.interval:.1f} minutos)")
                else:
                    # Se não tiver intervalo, remove da fila
                    self.message_queue.remove(msg)
                    print(f"REMOÇÃO: Mensagem '{msg.filename}' removida da fila (sem intervalo)")
                    
                break
        
        # Se não encontrou a mensagem original e tem intervalo, adiciona-a de volta
        if not original_message_found and message.interval > 0:
            # Calcula o próximo horário de reprodução
            seconds_interval = message.interval * 60  # Converte minutos para segundos
            message.next_play_time = end_time + timedelta(seconds=seconds_interval)
            message.is_pending = True  # Marca como pendente
            
            # Adiciona de volta à fila
            heapq.heappush(self.message_queue, message)
            print(f"NOVA ADIÇÃO: Mensagem '{message.filename}' adicionada à fila para próxima reprodução")
        
        # ETAPA 2: Encontra a próxima prioridade na sequência
        next_priority = self._find_next_priority(message.priority)
        
        if next_priority is not None:
            print(f"PRÓXIMA PRIORIDADE: {next_priority}")
            
            # Encontra as mensagens da próxima prioridade
            next_messages = [msg for msg in self.message_queue if msg.priority == next_priority]
            
            if next_messages:
                # CORREÇÃO CRUCIAL: Programa a próxima mensagem para tocar após o intervalo específico
                for msg in next_messages:
                    # Calcula o próximo horário com base no intervalo da mensagem
                    seconds_interval = msg.interval * 60  # Converte minutos para segundos
                    msg.next_play_time = end_time + timedelta(seconds=seconds_interval)
                    
                    # Ativa a mensagem (não pendente)
                    msg.is_pending = False
                    
                    # Registra a programação
                    print(f"ATIVAÇÃO: Mensagem '{msg.filename}' (prioridade {msg.priority}) programada para {msg.next_play_time.strftime('%H:%M:%S')}")
                    print(f"  Intervalo após término: {seconds_interval} segundos")
                
                # Outras prioridades maiores permanecem pendentes
                for msg in self.message_queue:
                    if msg.priority > next_priority:
                        msg.is_pending = True
        
        # Limpa a referência à mensagem atualmente em reprodução
        self.currently_playing = None
        
        # Reorganiza o heap
        heapq.heapify(self.message_queue)
        print("Fila reorganizada após término da mensagem")
        self.debug_queue_state()
        
        # Salva a fila atualizada
        self._save_queue()
        
        # Atualiza a interface
        if hasattr(self, 'update_callback') and callable(self.update_callback):
            self.update_callback()

    def identify_duplicates(self):
        """
        Identifica duplicatas na fila, mas não as remove.
        Apenas marca a mais recente como ativa e as outras como pendentes.
        """
        if not self.message_queue:
            return
        
        # Dicionário para armazenar a mensagem mais recente por nome de arquivo
        latest_messages = {}
        
        # Identifica a mensagem mais recente de cada nome de arquivo
        for item in self.message_queue:
            key = item.filename
            
            if key in latest_messages:
                # Compara os horários e mantém o mais recente
                if item.next_play_time < latest_messages[key].next_play_time:
                    latest_messages[key] = item
            else:
                # Primeira ocorrência deste filename
                latest_messages[key] = item
        
        # Atualiza o estado de pendência - apenas a mais recente fica não-pendente
        duplicates_found = False
        for item in self.message_queue:
            if item.filename in latest_messages:
                latest_item = latest_messages[item.filename]
                
                # Se este item não for o mais recente para este nome, marca como pendente
                if item != latest_item and not item.is_pending:
                    item.is_pending = True
                    duplicates_found = True
                    print(f"DUPLICATA: Mensagem '{item.filename}' marcada como pendente (duplicata)")
        
        if duplicates_found:
            # Reorganiza o heap
            heapq.heapify(self.message_queue)
            print("Fila reorganizada após identificação de duplicatas")
            
            # Salva a fila atualizada
            self._save_queue()
            
            # Notifica a interface
            if hasattr(self, 'update_callback') and callable(self.update_callback):
                self.update_callback()

    def remove_message(self, filename):
        """
        Remove uma mensagem específica da fila.
        
        Args:
            filename (str): Nome do arquivo a remover
            
        Returns:
            bool: True se removido com sucesso
        """
        # Encontra o item na lista
        for index, item in enumerate(self.message_queue):
            if item.filename == filename:
                # Remover elemento do heap
                self.message_queue[index] = self.message_queue[-1]
                self.message_queue.pop()
                # Reordenar o heap
                heapq.heapify(self.message_queue)
                # Salva a fila atualizada
                self._save_queue()
                return True
        return False
    
    def clear_queue(self):
        """Limpa toda a fila de mensagens."""
        self.message_queue = []
        self.last_end_time_by_priority = {}
        self.last_global_end_time = None
        
        # Garante que o arquivo de persistência também seja limpo
        if self.serializer:
            self.serializer.save_queue([])
        
        print("Fila de mensagens completamente limpa")
    
    def get_next_message(self):
        """
        Obtém a próxima mensagem a ser reproduzida.
        CORREÇÃO: Identifica duplicatas sem removê-las
        """
        # Identifica duplicatas sem removê-las
        self.identify_duplicates()
        
        if not self.message_queue:
            return None
        
        # Hora atual para comparações
        current_time = datetime.now()
        
        # ETAPA 1: Encontrar todas as mensagens NÃO PENDENTES
        active_messages = [msg for msg in self.message_queue if not msg.is_pending]
        
        if not active_messages:
            print("SELEÇÃO: Não há mensagens ativas na fila")
            return None
        
        # ETAPA 2: Verificar quais mensagens já passaram do horário programado
        ready_messages = []
        
        for msg in active_messages:
            time_diff = (current_time - msg.next_play_time).total_seconds()
            
            # Considera "pronta" se a hora atual já passou da hora programada
            if time_diff >= 0:
                # Está na hora ou já passou da hora de tocar
                ready_messages.append(msg)
                print(f"SELEÇÃO: Mensagem '{msg.filename}' (prioridade {msg.priority}) está PRONTA para tocar")
                print(f"  Horário programado: {msg.next_play_time.strftime('%H:%M:%S')}")
                print(f"  Horário atual: {current_time.strftime('%H:%M:%S')}")
                print(f"  Atraso: {time_diff:.1f} segundos")
            else:
                # Ainda não chegou a hora
                seconds_remaining = -time_diff
                print(f"SELEÇÃO: Mensagem '{msg.filename}' (prioridade {msg.priority}) ainda não está pronta")
                print(f"  Faltam {seconds_remaining:.1f} segundos")
        
        if not ready_messages:
            print("SELEÇÃO: Nenhuma mensagem está pronta para tocar agora")
            return None
        
        # ETAPA 3: Agora temos as mensagens prontas, selecionar por PRIORIDADE
        # Encontrar a menor prioridade (número menor = prioridade maior)
        min_priority = min(msg.priority for msg in ready_messages)
        
        # Filtrar apenas as mensagens com essa prioridade mais alta
        highest_priority_messages = [msg for msg in ready_messages if msg.priority == min_priority]
        
        # ETAPA 4: Se tiver mais de uma mensagem na mesma prioridade, pegar a mais antiga
        if len(highest_priority_messages) > 1:
            highest_priority_messages.sort(key=lambda m: m.next_play_time)
        
        # Seleciona a mensagem a ser reproduzida
        selected_message = highest_priority_messages[0]
        
        print(f"SELEÇÃO FINAL: Mensagem '{selected_message.filename}' selecionada para reprodução")
        print(f"  Prioridade: {selected_message.priority}")
        print(f"  Horário programado: {selected_message.next_play_time.strftime('%H:%M:%S')}")
        
        # CORREÇÃO IMPORTANTE: Não remover da fila, apenas clonar e marcar como em reprodução
        
        # Cria uma cópia da mensagem selecionada
        import copy
        message_copy = copy.deepcopy(selected_message)
        
        # Marca a mensagem original como "pendente" para que não seja selecionada novamente
        for msg in self.message_queue:
            if msg.filename == selected_message.filename and msg.priority == selected_message.priority and msg.next_play_time == selected_message.next_play_time:
                msg.is_pending = True
                print(f"MANUTENÇÃO DA FILA: Mensagem '{msg.filename}' marcada como pendente durante reprodução")
        
        # Atualiza a referência à mensagem atualmente em reprodução
        self.currently_playing = message_copy
        
        # Retorna a cópia da mensagem
        return message_copy
    
    def update_waiting_messages(self, completed_priority, end_time):
        """
        Atualiza os horários de próxima execução para mensagens que estavam esperando
        por uma mensagem de prioridade maior.
        """
        # Procura por mensagens com prioridade imediatamente menor
        next_priority = completed_priority + 1
        
        # Encontra todas as mensagens com essa prioridade
        for i, msg in enumerate(self.message_queue):
            if msg.priority == next_priority and hasattr(msg, 'waiting_for_higher_priority') and msg.waiting_for_higher_priority:
                # Atualiza o horário de próxima execução
                msg.next_play_time = end_time + timedelta(minutes=msg.interval)
                msg.waiting_for_higher_priority = False
                
                print(f"Atualizado horário de '{msg.filename}': {msg.get_next_play_time_str()}")
        
        # Reordena o heap, pois modificamos seus elementos
        heapq.heapify(self.message_queue)
        
        # Salva a fila atualizada
        self._save_queue()

    def _find_next_priority(self, current_priority):
        """
        Encontra a próxima prioridade na sequência cíclica.
        
        Args:
            current_priority: Prioridade atual
            
        Returns:
            int: Próxima prioridade ou None se não houver
        """
        available_priorities = set()
        for msg in self.message_queue:
            available_priorities.add(msg.priority)
        
        # Se não há outras prioridades, retorna None
        if not available_priorities:
            return None
        
        # Encontra a próxima prioridade maior
        next_higher = None
        for p in sorted(available_priorities):
            if p > current_priority:
                next_higher = p
                break
        
        # Se não encontrou uma maior, volta para a menor (ciclo)
        if next_higher is None:
            next_higher = min(available_priorities)
        
        return next_higher
        
    def put_back_message(self, message):
        """
        Recoloca uma mensagem na fila após atualizar seu horário.
        CORREÇÃO: Garantir intervalo preciso após o término da mensagem
        """
        # Remove qualquer mensagem duplicada antes de adicionar de volta
        for i in range(len(self.message_queue) - 1, -1, -1):
            if self.message_queue[i].filename == message.filename and self.message_queue[i].priority == message.priority:
                # Remove esta mensagem do heap
                del self.message_queue[i]
        
        # Reconstruir o heap após as remoções
        heapq.heapify(self.message_queue)
        
        # CORREÇÃO CRÍTICA: Garantir cálculo preciso do intervalo
        # Usamos o horário de término real da mensagem e adicionamos o intervalo exato
        current_time = datetime.now()
        
        # Calcula o próximo horário de reprodução com base no intervalo definido pelo usuário
        if message.end_time:
            # Calculamos precisamente o número de segundos a partir do intervalo em minutos
            seconds_interval = message.interval * 60
            
            # O próximo horário é exatamente o horário de término + o intervalo em segundos
            message.next_play_time = message.end_time + timedelta(seconds=seconds_interval)
            
            print(f"INTERVALO RECALCULADO:")
            print(f"  - Horário de término: {message.end_time.strftime('%H:%M:%S')}")
            print(f"  - Intervalo: {seconds_interval} segundos")
            print(f"  - Próximo horário: {message.next_play_time.strftime('%H:%M:%S')}")
        else:
            # Se não tiver tempo de término registrado (não deveria acontecer), usa o tempo atual
            seconds_interval = message.interval * 60
            message.next_play_time = current_time + timedelta(seconds=seconds_interval)
            print(f"ATENÇÃO: Sem registro de término. Usando hora atual: {current_time.strftime('%H:%M:%S')}")
            print(f"  - Intervalo: {seconds_interval} segundos")
            print(f"  - Próximo horário: {message.next_play_time.strftime('%H:%M:%S')}")
        
        # Verifica se é a mensagem de maior prioridade na fila
        min_priority = None
        for msg in self.message_queue:
            if min_priority is None or msg.priority < min_priority:
                min_priority = msg.priority
        
        # Define se a mensagem deve ficar pendente com base na prioridade
        if min_priority is None or message.priority <= min_priority:
            message.is_pending = False
            print(f"Mensagem '{message.filename}' definida como ATIVA (prioridade {message.priority})")
        else:
            message.is_pending = True
            print(f"Mensagem '{message.filename}' definida como PENDENTE (menor prioridade: {min_priority})")
        
        # Adiciona de volta à fila
        heapq.heappush(self.message_queue, message)
        
        # Log formatado do intervalo
        if message.interval < 1.0:
            seconds = int(message.interval * 60)
            print(f"Mensagem '{message.filename}' readicionada à fila (a cada {seconds} segundos)")
        else:
            print(f"Mensagem '{message.filename}' readicionada à fila (a cada {message.interval:.1f} minutos)")
        
        # Salva a fila atualizada
        self._save_queue()
        
        # Notifica a interface se houver callback
        if hasattr(self, 'update_callback') and callable(self.update_callback):
            self.update_callback()
        
        return True
    
    def debug_queue_state(self):
        """
        Imprime o estado atual da fila para debug.
        """
        if not self.message_queue:
            print("Fila vazia")
            return
            
        print("\nEstado da fila de mensagens:")
        sorted_queue = sorted(self.message_queue)
        for i, msg in enumerate(sorted_queue):
            delta = msg.next_play_time - datetime.now()
            minutes, seconds = divmod(delta.total_seconds(), 60)
            print(f"{i+1}. {msg.filename} - Prioridade: {msg.priority}, Próxima execução: {msg.get_next_play_time_str()}")
            print(f"   Tempo restante: {int(minutes)}m {int(seconds)}s, Pendente: {msg.is_pending}")
        print()
        
        # Exibe os tempos de término por prioridade
        print("\nHorários de término por prioridade:")
        for p, time in sorted(self.last_end_time_by_priority.items()):
            print(f"Prioridade {p}: {time.strftime('%H:%M:%S')}")
        print()
    
    def get_queue_items(self):
        """
        Obtém todos os itens da fila em ordem de prioridade.
        Útil para exibição na interface.
        
        Returns:
            list: Lista ordenada de todos os itens
        """
        return sorted(self.message_queue)
    
    def get_queue_length(self):
        """
        Retorna o número de mensagens na fila.
        
        Returns:
            int: Quantidade de mensagens
        """
        return len(self.message_queue)
    
    def _save_queue(self):
        """
        Salva a fila no arquivo de persistência, se configurado.
        
        Returns:
            bool: True se salvou com sucesso, False caso contrário ou se não configurado
        """
        if not self.serializer:
            return False
        
        return self.serializer.save_queue(self.message_queue)