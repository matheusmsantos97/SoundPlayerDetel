import json
from datetime import datetime
from pathlib import Path

class MessageQueueSerializer:
    """
    Classe responsável por serializar e desserializar a fila de mensagens.
    Permite salvar a fila em um arquivo JSON e carregá-la novamente.
    """
    
    def __init__(self, queue_file_path):
        """
        Inicializa o serializador.
        
        Args:
            queue_file_path (str ou Path): Caminho para o arquivo de persistência da fila
        """
        self.queue_file_path = Path(queue_file_path)
    
    def save_queue(self, queue_items):
        """
        Salva a fila de mensagens em um arquivo JSON.
        
        Args:
            queue_items (list): Lista de objetos MessageQueueItem
            
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            # Cria o diretório pai se não existir
            self.queue_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Converte a lista de itens para um formato serializável
            serializable_items = []
            for item in queue_items:
                serializable_item = {
                    'filename': item.filename,
                    'priority': item.priority,
                    'interval': item.interval,
                    'next_play_time': item.next_play_time.isoformat(),
                    'is_pending': getattr(item, 'is_pending', False)
                }
                
                # Adiciona end_time se existir
                if hasattr(item, 'end_time') and item.end_time:
                    serializable_item['end_time'] = item.end_time.isoformat()
                
                serializable_items.append(serializable_item)
            
            # Salva no arquivo
            with open(self.queue_file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_items, f, indent=2)
            
            print(f"Fila salva com sucesso em: {self.queue_file_path}")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar a fila: {str(e)}")
            return False
    
    def load_queue(self, message_queue_class):
        """
        Carrega a fila de mensagens de um arquivo JSON.
        
        Args:
            message_queue_class: Classe MessageQueueItem para instanciar os itens
            
        Returns:
            list: Lista de objetos MessageQueueItem ou lista vazia se houver erro
        """
        if not self.queue_file_path.exists():
            print(f"Arquivo de fila não encontrado: {self.queue_file_path}")
            return []
        
        try:
            with open(self.queue_file_path, 'r', encoding='utf-8') as f:
                serialized_items = json.load(f)
            
            # Converte os itens serializados de volta para objetos MessageQueueItem
            queue_items = []
            for item_data in serialized_items:
                # Cria um novo item com os dados básicos
                item = message_queue_class(
                    item_data['filename'],
                    item_data['priority'],
                    item_data['interval']
                )
                
                # Define o horário de próxima reprodução
                item.next_play_time = datetime.fromisoformat(item_data['next_play_time'])
                
                # Define se está pendente
                item.is_pending = item_data.get('is_pending', False)
                
                # Define o horário de término se existir
                if 'end_time' in item_data and item_data['end_time']:
                    item.end_time = datetime.fromisoformat(item_data['end_time'])
                
                queue_items.append(item)
            
            print(f"Fila carregada com sucesso: {len(queue_items)} itens")
            return queue_items
            
        except Exception as e:
            print(f"Erro ao carregar a fila: {str(e)}")
            return []