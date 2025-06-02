#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Janela principal do aplicativo de rádio.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QListWidget,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QMenu)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint
from PyQt6.QtGui import QFont, QIcon, QAction, QColor

from services.player_service import PlayerService
from services.queue_service import QueueService
from ui.dialogs import AddMessageDialog, MessageImportDialog
from ui.radio_source_dialog import RadioSourceDialog



class RadioPlayerWindow(QMainWindow):
    """
    Janela principal do aplicativo de rádio.
    Contém a interface completa e coordena os serviços.
    """
    
    def __init__(self):
        """Inicializa a janela principal."""
        super().__init__()
        
        # Configurações da janela
        self.setWindowTitle("Player de Rádio com Mensagens")
        self.setMinimumSize(800, 600)
        
        # Define o diretório das mensagens
        self.messages_path = Path(os.path.expanduser(
            r"C:\Users\mathe\OneDrive\Área de Trabalho\radio\mensagens"
        ))
        
        # Define o diretório de configuração
        self.config_dir = Path(os.path.expanduser(
            r"C:\Users\mathe\OneDrive\Área de Trabalho\radio\config"
        ))
        
        # Define o arquivo de persistência da fila
        self.queue_file_path = self.config_dir / "queue_state.json"
        
        # Cria o diretório se não existir
        self.messages_path.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Volume normal da rádio (100%)
        self.normal_radio_volume = 100
        # Volume baixo para quando as mensagens estiverem tocando (5%)
        self.lowered_radio_volume = 5
        
        # Inicializa serviços
        self.player_service = PlayerService(self.config_dir, self.messages_path)
        self.queue_service = QueueService(self.queue_file_path)  # Passa o caminho para persistência
        
        # Configura a interface - DEVE SER EXECUTADO ANTES de load_messages()
        self.init_ui()
        
        # Configurar o callback para atualizar a interface
        self.queue_service.update_callback = self.update_queue_table
        
        # Timer para atualização
        self.update_timer = QTimer()
        self.update_timer.setInterval(1000)  # 1 segundo
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start()
        
        # Carrega a lista de mensagens - DEVE SER EXECUTADO APÓS init_ui()
        self.load_messages()
        
        # Atualiza a tabela da fila para mostrar as mensagens carregadas
        self.update_queue_table()
    
    def init_ui(self):
        """Inicializa a interface da janela principal."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # ===== Cabeçalho com informações de status =====
        header_layout = QVBoxLayout()
        
        # Título com configuração de fonte
        title_layout = QHBoxLayout()
        
        title_label = QLabel("JB FM Player")
        title_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label, 1)  # Adicionado stretch factor 1
        
        # Botão de configuração de fonte - MANTIDO
        self.source_button = QPushButton("Configurar Fonte")
        self.source_button.setToolTip("Configurar fonte de rádio (Internet/Tunner)")
        self.source_button.clicked.connect(self.configure_radio_source)
        title_layout.addWidget(self.source_button)
        
        header_layout.addLayout(title_layout)
        
        # Mostrar a fonte atual
        self.source_label = QLabel()
        self.source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_source_label()
        header_layout.addWidget(self.source_label)
        
        # Status
        self.mode_label = QLabel("Modo: Rádio")
        self.mode_label.setFont(QFont('Arial', 12))
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.mode_label)
        
        self.status_label = QLabel("Status: Parado")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # ===== Área central - Mensagens e Fila =====
        central_layout = QHBoxLayout()
        
        # ----- Painel de mensagens disponíveis -----
        messages_panel = QVBoxLayout()
        
        messages_panel.addWidget(QLabel("Mensagens Disponíveis:"))
        
        # Lista de mensagens
        self.messages_list = QListWidget()
        self.messages_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.messages_list.itemDoubleClicked.connect(self.play_selected_message)
        messages_panel.addWidget(self.messages_list)
        
        # Botões de gerenciamento de mensagens
        messages_buttons = QHBoxLayout()
        
        add_queue_button = QPushButton("Adicionar à Fila")
        add_queue_button.clicked.connect(self.add_to_queue)
        messages_buttons.addWidget(add_queue_button)
        
        import_button = QPushButton("Importar Mensagem")
        import_button.clicked.connect(self.import_message)
        messages_buttons.addWidget(import_button)
        
        remove_file_button = QPushButton("Remover Arquivo")
        remove_file_button.clicked.connect(self.remove_message_file)
        messages_buttons.addWidget(remove_file_button)
        
        messages_panel.addLayout(messages_buttons)
        
        central_layout.addLayout(messages_panel)
        
        # ----- Painel da fila de reprodução -----
        queue_panel = QVBoxLayout()
        
        queue_panel.addWidget(QLabel("Fila de Reprodução:"))
        
        # Tabela da fila
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Arquivo", "Prioridade", "Intervalo", "Próxima Execução"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        queue_panel.addWidget(self.queue_table)
        
        # Botões da fila
        queue_buttons = QHBoxLayout()
        
        remove_queue_button = QPushButton("Remover da Fila")
        remove_queue_button.clicked.connect(self.remove_from_queue)
        queue_buttons.addWidget(remove_queue_button)
        
        clear_queue_button = QPushButton("Limpar Fila")
        clear_queue_button.clicked.connect(self.clear_queue)
        queue_buttons.addWidget(clear_queue_button)
        
        queue_panel.addLayout(queue_buttons)
        
        central_layout.addLayout(queue_panel)
        
        main_layout.addLayout(central_layout)
        
        # ===== Controles de reprodução =====
        playback_layout = QHBoxLayout()
        
        self.play_button = QPushButton("▶ Play")
        self.play_button.setFixedSize(100, 40)
        self.play_button.clicked.connect(self.toggle_playback)
        playback_layout.addWidget(self.play_button)
        
        # Botão "Voltar para Rádio" removido
        
        # Botões de microfone removidos
        
        main_layout.addLayout(playback_layout)
        
        # Define o layout na janela principal
        central_widget.setLayout(main_layout)
    
    def load_messages(self):
        """Carrega a lista de mensagens da pasta configurada."""
        self.messages_list.clear()
        try:
            for file in self.messages_path.glob("*"):
                if file.suffix.lower() in ['.mp3', '.wav', '.aac', '.ogg']:
                    self.messages_list.addItem(file.name)
            
            # Ordena por nome
            self.messages_list.sortItems()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar mensagens: {str(e)}")
    
    def update_queue_table(self):
        """
        Atualiza a tabela da fila de reprodução.
        """
        items = self.queue_service.get_queue_items()
        
        if not items:
            # Limpa a tabela se não houver itens
            self.queue_table.setRowCount(0)
            return
        
        # Define o número de linhas da tabela
        self.queue_table.setRowCount(len(items))
        
        # Identifica a próxima prioridade a ser executada
        next_priority = None
        for item in items:
            if not item.is_pending:
                next_priority = item.priority
                break
        
        # Se não encontrou próxima prioridade, assume a menor prioridade
        if next_priority is None and items:
            next_priority = min(item.priority for item in items)
        
        # Preenche a tabela
        for i, message in enumerate(items):
            # Coluna Arquivo
            file_item = QTableWidgetItem(message.filename)
            self.queue_table.setItem(i, 0, file_item)
            
            # Coluna Prioridade
            self.queue_table.setItem(i, 1, QTableWidgetItem(str(message.priority)))
            
            # Coluna Intervalo - mostra em segundos se for menor que 1 minuto
            if message.interval < 1.0:
                # Converte para segundos
                seconds = int(message.interval * 60)
                self.queue_table.setItem(i, 2, QTableWidgetItem(f"{seconds} seg"))
            else:
                # Arredonda para o minuto mais próximo se for um valor não inteiro
                minutes = round(message.interval)
                self.queue_table.setItem(i, 2, QTableWidgetItem(f"{minutes} min"))
            
            # Coluna Próxima Execução
            delta = message.next_play_time - datetime.now()
            delta_seconds = delta.total_seconds()
            
            # Formatação especial para cada estado
            if message.is_pending:
                status_item = QTableWidgetItem("Aguardando...")
                # Cor cinza para mensagens pendentes
                status_item.setForeground(QColor(128, 128, 128))
                self.queue_table.setItem(i, 3, status_item)
            elif delta_seconds < 0:
                # Mensagem pronta para tocar
                status_item = QTableWidgetItem("Pronta!")
                # Cor verde para mensagens prontas
                status_item.setForeground(QColor(0, 128, 0))
                self.queue_table.setItem(i, 3, status_item)
            else:
                # Mensagem com tempo restante
                minutes, seconds = divmod(int(delta_seconds), 60)
                time_str = f"{minutes}m {seconds}s"
                status_item = QTableWidgetItem(f"{message.get_next_play_time_str()} ({time_str})")
                # Cor azul para mensagens ativas com tempo
                status_item.setForeground(QColor(0, 0, 255))
                self.queue_table.setItem(i, 3, status_item)
            
            # Destaque visual para a mensagem que será tocada em seguida
            if message.priority == next_priority and not message.is_pending:
                # Fundo amarelo claro para a próxima mensagem
                for col in range(4):
                    self.queue_table.item(i, col).setBackground(QColor(255, 255, 200))

    def configure_radio_source(self):
        """Abre o diálogo para configurar a fonte de rádio."""
        dialog = RadioSourceDialog(self.player_service, self)
        dialog.exec()
        
        # Atualiza o label com a fonte atual
        self.update_source_label()

    def update_source_label(self):
        """Atualiza o label com a fonte atual de rádio."""
        try:
            source_name = self.player_service.get_current_source_name()
            self.source_label.setText(f"Fonte: {source_name}")
        except Exception as e:
            print(f"Erro ao atualizar label de fonte: {str(e)}")
            self.source_label.setText("Fonte: Desconhecida")

    def update_status(self):
        """
        Atualiza o status do player e verifica a fila.
        Chamado periodicamente pelo timer.
        """
        # Atualiza estado do player
        state = self.player_service.get_state()
        self.status_label.setText(f"Status: {state}")
        
        # Atualiza o label da fonte atual
        self.update_source_label()
        
        # Atualiza botão de play/pause
        if self.player_service.is_playing:
            self.play_button.setText("⏸ Pause")
        else:
            self.play_button.setText("▶ Play")
        
        # Força o volume da mensagem para o máximo a cada verificação
        if not self.player_service.is_radio_mode:
            self.force_message_volume_to_max()
        
        # Atualiza o modo se não estiver no modo de microfone
        if not hasattr(self.player_service, 'mic_active') or not self.player_service.mic_active:
            if self.player_service.is_radio_mode:
                self.mode_label.setText("Modo: Rádio")
            else:
                if hasattr(self.player_service, 'current_message') and self.player_service.current_message:
                    self.mode_label.setText(f"Modo: Mensagem - {self.player_service.current_message.filename}")
                else:
                    self.mode_label.setText("Modo: Mensagem")
        
        # Verifica erros
        if self.player_service.has_error():
            if self.player_service.is_radio_mode:
                print("Erro detectado na rádio. Tentando reconectar...")
                self.player_service.switch_to_radio()  # Tenta reconectar
        
        # Se está tocando uma mensagem e ela terminou
        if not self.player_service.is_radio_mode and self.player_service.is_media_ended():
            print("Mensagem terminou, processando fim...")
            # Chamamos o método específico para tratar o fim da mensagem
            self.on_message_ended()
        
        # Verificar se há mensagens na fila prontas para tocar
        # Verificamos A CADA SEGUNDO para maior precisão do intervalo
        if self.player_service.is_radio_mode and (not hasattr(self.player_service, 'mic_active') or not self.player_service.mic_active):
            # Verificamos no início do segundo
            current_time = datetime.now()
            current_second = current_time.second
            
            if not hasattr(self, '_last_check_second') or self._last_check_second != current_second:
                self._last_check_second = current_second
                # Se encontrar uma mensagem para tocar, interrompe a rádio
                print(f"VERIFICAÇÃO DE FILA ({current_time.strftime('%H:%M:%S')})")
                self.check_queue()
        
        # Atualiza a tabela da fila a cada 5 segundos para não sobrecarregar a interface
        current_time = datetime.now()
        current_second = current_time.second
        if current_second % 5 == 0:
            if not hasattr(self, '_last_update_second') or self._last_update_second != current_second:
                self._last_update_second = current_second
                self.update_queue_table()
                
                # Debug da fila a cada 5 segundos
                items = self.queue_service.get_queue_items()
                if items:
                    print("\nEstado atual da fila:")
                    for i, msg in enumerate(items):
                        delta = msg.next_play_time - datetime.now()
                        minutes, seconds = divmod(delta.total_seconds(), 60)
                        state = "PRONTA" if not msg.is_pending and delta.total_seconds() <= 0 else ("Ativa" if not msg.is_pending else "Pendente")
                        print(f"{i+1}. {msg.filename} - Prioridade: {msg.priority}, Próxima: {msg.get_next_play_time_str()}, Estado: {state}")
                        print(f"   Tempo: {int(minutes)}m {int(seconds)}s")
                    print()
    
    def check_queue(self):
        """
        Verifica a fila e reproduz próxima mensagem se necessário.
        """
        # Verifica se há mensagem para tocar
        next_message = self.queue_service.get_next_message()
        
        if next_message:    
            # Imprime mensagem detalhada para debug
            print(f"REPRODUZINDO MENSAGEM: {next_message.filename}")
            print(f"Prioridade: {next_message.priority}, Horário: {next_message.get_next_play_time_str()}")
            
            # Salva a mensagem no player service para referência futura
            self.player_service.current_message = next_message
            
            # Abaixa o volume da rádio com fade (2 segundos)
            self.player_service.set_radio_volume(self.lowered_radio_volume, fade_duration=5.0)
            
            # Pequena pausa para iniciar o fade antes de tocar a mensagem
            QTimer.singleShot(500, lambda: self._play_message_with_fade(next_message))
            
            return True  # Mensagem será reproduzida
        else:
            return False  # Nenhuma mensagem pronta
        
    def force_message_volume_to_max(self):
        """
        Força o volume da mensagem atual para o máximo (100%).
        Deve ser chamado periodicamente enquanto uma mensagem estiver tocando.
        """
        # Só aplica se estiver no modo mensagem
        if not self.player_service.is_radio_mode and not self.player_service.mic_active:
            if hasattr(self.player_service, 'current_sound'):
                # Força o volume para 100%
                current_vol = self.player_service.current_sound.get_volume()
                if current_vol < 1.0:
                    self.player_service.current_sound.set_volume(1.0)
                    print(f"VOLUME FORÇADO: Aumentado de {current_vol*100:.0f}% para 100%")
    
    def _play_message_with_fade(self, next_message):
        """Função auxiliar para tocar mensagem com fade após timer."""
        # Verificação adicional se o arquivo existe
        file_path = self.messages_path / next_message.filename
        if not file_path.exists():
            print(f"ERRO: Arquivo de mensagem não encontrado: {file_path}")
            QMessageBox.warning(
                self, 
                "Erro", 
                f"Arquivo da mensagem não encontrado: {next_message.filename}"
            )
            # Restaura o volume da rádio
            self.player_service.set_radio_volume(self.normal_radio_volume, fade_duration=1.0)
            return False
            
        print(f"Tentando reproduzir: {file_path}")
        
        # Tenta reproduzir a mensagem com fade in
        success = self.player_service.play_message(next_message.filename, next_message, fade_in_duration=0)
        
        if success:
            print(f"Mensagem começou a tocar: {next_message.filename}")
            self.mode_label.setText(f"Modo: Mensagem - {next_message.filename}")
            
            # Verificar e imprimir informações do tempo de término
            if hasattr(self.player_service, 'end_time') and self.player_service.end_time:
                duration = (self.player_service.end_time - datetime.now()).total_seconds()
                print(f"DURAÇÃO CALCULADA: {duration:.1f} segundos")
                print(f"TÉRMINO PREVISTO: {self.player_service.end_time.strftime('%H:%M:%S')}")
            
            # Aplicar força máxima de volume
            if hasattr(self.player_service, 'current_sound'):
                self.player_service.current_sound.set_volume(1.0)
                print("VOLUME MÁXIMO garantido para a mensagem")
            
            # Se for mensagem recorrente, recoloca na fila com o intervalo
            if next_message.interval > 0:
                # Define o horário de término da mensagem atual
                next_message.end_time = self.player_service.end_time
                print(f"TÉRMINO PREVISTO DA MENSAGEM: {next_message.end_time.strftime('%H:%M:%S')}")
            
            self.update_queue_table()
        else:
            # Se falhou ao reproduzir, remove da fila e restaura o volume da rádio
            print(f"ERRO: Falha ao reproduzir a mensagem: {next_message.filename}")
            self.player_service.set_radio_volume(self.normal_radio_volume, fade_duration=4.0)
            QMessageBox.warning(
                self, 
                "Erro", 
                f"Não foi possível reproduzir: {next_message.filename}"
            )
            # Checar se há mais mensagens prontas
            QTimer.singleShot(500, self.check_queue)
            
        return success
    
    def on_message_ended(self):
        """
        Chamado quando uma mensagem termina de tocar.
        """
        print("TÉRMINO: Mensagem terminou de tocar")
        
        if hasattr(self.player_service, 'current_message') and self.player_service.current_message:
            # Registra o término da mensagem atual
            current_message = self.player_service.current_message
            
            # Usa o tempo exato de término (agora)
            current_message.end_time = datetime.now()
            print(f"TÉRMINO: Mensagem {current_message.filename} terminou às {current_message.end_time.strftime('%H:%M:%S')}")
            
            # Notifica o serviço de fila
            self.queue_service.register_message_end(current_message)
            
            # Limpa a referência da mensagem atual
            self.player_service.current_message = None
        
        # Restaura o volume da rádio ao valor normal com fade
        self.player_service.set_radio_volume(self.normal_radio_volume, fade_duration=5.0)
        
        # Voltar IMEDIATAMENTE para a rádio
        self.switch_to_radio()
        
        # Atualiza a interface
        self.update_queue_table()
    
    def process_next_after_ended(self):
        """
        Processa a próxima mensagem após o término de uma.
        """
        # Verificar se há mais mensagens prontas para reproduzir imediatamente
        if not self.check_queue():
            # Se não houver mais mensagens prontas, volta para a rádio
            print("Não há mais mensagens prontas, voltando para a rádio")
            self.switch_to_radio()

    def toggle_playback(self):
        """Alterna entre play e pause."""
        self.player_service.toggle_playback()
        
        if self.player_service.is_playing:
            self.play_button.setText("⏸ Pause")
        else:
            self.play_button.setText("▶ Play")
    
    def switch_to_radio(self):
        """Muda para o modo de rádio e garante que a reprodução comece."""
        success = self.player_service.switch_to_radio()
        
        if success:
            # Restaura o volume normal da rádio
            self.player_service.set_radio_volume(self.normal_radio_volume)
            
            self.mode_label.setText("Modo: Rádio")
            self.status_label.setText("Status: Reproduzindo")
            # Garante que o botão indique status correto
            self.play_button.setText("⏸ Pause")
        else:
            self.status_label.setText("Status: Erro ao conectar à rádio")
            # Tentar reconectar novamente
            QTimer.singleShot(3000, self.retry_radio_connection)
    
    def retry_radio_connection(self):
        """Tenta reconectar à rádio após um erro."""
        self.status_label.setText("Status: Tentando reconectar...")
        success = self.player_service.switch_to_radio()
        
        if success:
            self.mode_label.setText("Modo: Rádio")
            self.status_label.setText("Status: Reproduzindo")
            self.play_button.setText("⏸ Pause")
    
    def play_selected_message(self, item):
        """Reproduz a mensagem selecionada diretamente."""
        filename = item.text()
        
        # Abaixa o volume da rádio com fade
        self.player_service.set_radio_volume(self.lowered_radio_volume, fade_duration=5.0)
        
        # Pequena pausa para iniciar o fade antes de tocar a mensagem
        QTimer.singleShot(500, lambda: self._play_selected_with_fade(filename))

    def _play_selected_with_fade(self, filename):
        """Função auxiliar para tocar mensagem selecionada com fade."""
        success = self.player_service.play_message(filename, None)
        
        if success:
            self.mode_label.setText(f"Modo: Mensagem - {filename}")
        else:
            # Restaura o volume da rádio se falhar
            self.player_service.set_radio_volume(self.normal_radio_volume, fade_duration=4.0)
            QMessageBox.warning(self, "Erro", f"Não foi possível reproduzir: {filename}")
    
    def add_to_queue(self):
        """Adiciona a mensagem selecionada à fila."""
        current_item = self.messages_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Erro", "Selecione uma mensagem para adicionar à fila.")
            return
        
        # Verifica se já existe esta mensagem na fila antes de prosseguir
        filename = current_item.text()
        items = self.queue_service.get_queue_items()
        
        for item in items:
            if item.filename == filename:
                QMessageBox.warning(self, "Aviso", 
                    f"A mensagem '{filename}' já está na fila. Remova a existente antes de adicionar novamente.")
                return
        
        dialog = AddMessageDialog(self)
        if dialog.exec():
            priority = dialog.priority_spin.value()
            
            # Obter o intervalo e a unidade selecionada
            interval_value = dialog.interval_spin.value()
            interval_unit = dialog.get_interval_unit()
            interval_minutes = dialog.get_interval_in_minutes()
            
            # Adiciona a mensagem à fila (usando o valor em minutos para compatibilidade)
            message = self.queue_service.add_message(
                filename,
                priority,
                interval_minutes
            )
            
            # Informa o usuário com a unidade correta
            play_time = message.get_next_play_time_str()
            if interval_unit == "segundos":
                QMessageBox.information(
                    self,
                    "Mensagem Agendada",
                    f"A mensagem será reproduzida às {play_time}\n" +
                    f"e repetirá a cada {interval_value} segundos"
                )
            else:
                QMessageBox.information(
                    self,
                    "Mensagem Agendada",
                    f"A mensagem será reproduzida às {play_time}\n" +
                    f"e repetirá a cada {interval_value} minutos"
                )
            
            self.update_queue_table()
    
    def remove_from_queue(self):
        """Remove a mensagem selecionada da fila."""
        current_row = self.queue_table.currentRow()
        if current_row >= 0:
            filename = self.queue_table.item(current_row, 0).text()
            self.queue_service.remove_message(filename)
            self.update_queue_table()
    
    def clear_queue(self):
        """Limpa toda a fila de mensagens."""
        reply = QMessageBox.question(
            self,
            "Limpar Fila",
            "Tem certeza que deseja remover todas as mensagens da fila?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.queue_service.clear_queue()
            self.update_queue_table()
    
    def import_message(self):
        """Abre o diálogo para importar novas mensagens."""
        dialog = MessageImportDialog(self.messages_path, self)
        if dialog.exec():
            self.load_messages()
    
    def remove_message_file(self):
        """Remove o arquivo de mensagem selecionado."""
        current_item = self.messages_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Erro", "Selecione uma mensagem para remover.")
            return
        
        filename = current_item.text()
        
        reply = QMessageBox.question(
            self,
            "Remover Arquivo",
            f"Tem certeza que deseja excluir permanentemente o arquivo '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                file_path = self.messages_path / filename
                file_path.unlink()
                self.load_messages()
                
                # Verifica se está na fila e remove
                self.queue_service.remove_message(filename)
                self.update_queue_table()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao remover arquivo: {str(e)}")
    
    def closeEvent(self, event):
        """Trata o evento de fechamento da janela."""
        # Salvar o estado da fila já está implementado na classe QueueService
        # Será chamado automaticamente quando qualquer alteração for feita na fila
        
        # Limpa recursos corretamente
        self.player_service.cleanup()  # Novo método para limpar todos os recursos
        self.update_timer.stop()
        event.accept()