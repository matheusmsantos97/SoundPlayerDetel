#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diálogos da interface do usuário para o aplicativo de rádio.
"""

from PyQt6.QtWidgets import (QDialog, QFormLayout, QSpinBox, 
                            QHBoxLayout, QPushButton, QLabel,
                            QFileDialog, QMessageBox, QVBoxLayout, QListWidget, QListWidgetItem, QComboBox)
from PyQt6.QtCore import Qt, QPoint
from datetime import datetime, timedelta

class MicDeviceDialog(QDialog):
    """
    Diálogo para selecionar o dispositivo de microfone a ser usado.
    """
    
    def __init__(self, microphone_service, parent=None):
        """
        Inicializa o diálogo.
        
        Args:
            microphone_service: Serviço de microfone para obter a lista de dispositivos
            parent: Widget pai
        """
        super().__init__(parent)
        self.setWindowTitle("Selecionar Dispositivo de Microfone")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.microphone_service = microphone_service
        self.selected_device = None
        
        self.init_ui()
        self.load_devices()
    
    def init_ui(self):
        """Inicializa a interface do diálogo."""
        layout = QVBoxLayout()
        
        # Título
        title_label = QLabel("Selecione o dispositivo de microfone:")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Lista de dispositivos
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.device_list)
        
        # Botões
        button_layout = QHBoxLayout()
        
        select_button = QPushButton("Selecionar")
        select_button.clicked.connect(self.select_device)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(select_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_devices(self):
        """Carrega a lista de dispositivos disponíveis."""
        try:
            devices = self.microphone_service.get_device_list()
            
            for device in devices:
                # Adiciona apenas dispositivos com entradas (microfones)
                if device['inputs'] > 0:
                    item_text = f"{device['name']} "
                    if device['default_input']:
                        item_text += "(Padrão)"
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, device['index'])
                    self.device_list.addItem(item)
                    
                    # Seleciona o dispositivo padrão
                    if device['default_input']:
                        self.device_list.setCurrentItem(item)
        
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar dispositivos: {str(e)}")
    
    def select_device(self):
        """Seleciona o dispositivo atual e fecha o diálogo."""
        current_item = self.device_list.currentItem()
        if current_item:
            self.selected_device = current_item.data(Qt.ItemDataRole.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "Erro", "Selecione um dispositivo!")

class AddMessageDialog(QDialog):
    """
    Diálogo para adicionar uma mensagem à fila de reprodução.
    Permite configurar prioridade, tempo até primeira reprodução
    e intervalo entre repetições.
    """
    
    def __init__(self, parent=None):
        """
        Inicializa o diálogo.
        
        Args:
            parent: Widget pai (normalmente a janela principal)
        """
        super().__init__(parent)
        self.setWindowTitle("Adicionar Mensagem à Fila")
        self.setModal(True)
        self.setMinimumWidth(350)
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa a interface do diálogo."""
        layout = QFormLayout()
        
        # Título
        title_label = QLabel("Configurações de Reprodução")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addRow(title_label)
        
        # Prioridade (1 é a mais alta)
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setValue(5)
        self.priority_spin.setToolTip("Prioridade da mensagem (1 é a mais alta)")
        layout.addRow("Prioridade (1-10):", self.priority_spin)
        
        # Intervalo entre repetições
        interval_layout = QHBoxLayout()
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 999)
        self.interval_spin.setValue(5)
        self.interval_spin.setToolTip("Valor do intervalo entre repetições")
        interval_layout.addWidget(self.interval_spin)
        
        # Opção para selecionar entre minutos e segundos
        self.interval_unit_combo = QComboBox()
        self.interval_unit_combo.addItem("Minutos")
        self.interval_unit_combo.addItem("Segundos")
        self.interval_unit_combo.setToolTip("Unidade de tempo para o intervalo")
        interval_layout.addWidget(self.interval_unit_combo)
        
        # NOVA ADIÇÃO: Label para mostrar o valor convertido
        self.interval_display = QLabel()
        self.interval_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        interval_layout.addWidget(self.interval_display)
        
        layout.addRow("Intervalo de repetição:", interval_layout)
        
        # Atualiza o display inicialmente
        self.update_interval_display()
        
        # Conecta os sinais para atualizar o display
        self.interval_spin.valueChanged.connect(self.update_interval_display)
        self.interval_unit_combo.currentTextChanged.connect(self.update_interval_display)

        # Label explicativo sobre a primeira execução
        first_play_label = QLabel("🎵 A primeira execução será imediata!")
        first_play_label.setStyleSheet("color: green; font-weight: bold; margin-top: 5px;")
        layout.addRow(first_play_label)
        
        # Informações adicionais
        info_label = QLabel(
            "• Prioridade 1 é a mais alta\n"
            "• A mensagem tocará imediatamente na primeira vez\n"
            "• O intervalo de repetição começa a contar após o término da primeira execução"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic; font-size: 11px;")
        layout.addRow(info_label)
        
        # Botões
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def update_interval_display(self):
        """Atualiza o display mostrando o intervalo real."""
        value = self.interval_spin.value()
        unit = self.interval_unit_combo.currentText()
        
        if unit == "Segundos":
            self.interval_display.setText(f"= {value} segundos entre repetições")
            self.interval_display.setStyleSheet("color: blue; font-weight: bold;")
        else:
            total_seconds = value * 60
            self.interval_display.setText(f"= {total_seconds} segundos entre repetições")
            self.interval_display.setStyleSheet("color: blue; font-weight: bold;")
    
    def get_interval_in_minutes(self):
        """
        Retorna o intervalo convertido para minutos.
        Mantém precisão para intervalos em segundos.
        
        Returns:
            float: Intervalo em minutos
        """
        interval_value = self.interval_spin.value()
        is_seconds = self.interval_unit_combo.currentText() == "Segundos"
        
        if is_seconds:
            # Converte segundos para minutos com precisão
            return interval_value / 60.0
        else:
            return float(interval_value)
        
    def get_interval_unit(self):
        """
        Retorna a unidade de tempo selecionada.
        
        Returns:
            str: "minutos" ou "segundos"
        """
        return self.interval_unit_combo.currentText().lower()
        
    def update_time_label(self):
        """Atualiza o rótulo com o horário estimado de reprodução."""
        minutes = self.first_play_spin.value()
        future_time = datetime.now() + timedelta(minutes=minutes)
        self.time_label.setText(future_time.strftime("%H:%M:%S"))


class MessageImportDialog(QDialog):
    """
    Diálogo para importar novas mensagens para a pasta de mensagens.
    """
    
    def __init__(self, messages_path, parent=None):
        """
        Inicializa o diálogo de importação.
        
        Args:
            messages_path (Path): Caminho para a pasta de mensagens
            parent: Widget pai
        """
        super().__init__(parent)
        self.setWindowTitle("Importar Mensagem")
        self.setModal(True)
        
        self.messages_path = messages_path
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa a interface do diálogo."""
        layout = QFormLayout()
        
        # Mensagem informativa
        info_label = QLabel("Selecione um arquivo de áudio para importar para a pasta de mensagens:")
        info_label.setWordWrap(True)
        layout.addRow(info_label)
        
        # Botões
        button_layout = QHBoxLayout()
        
        browse_button = QPushButton("Procurar...")
        browse_button.clicked.connect(self.browse_files)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(browse_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def browse_files(self):
        """Abre o diálogo de seleção de arquivo e importa o arquivo selecionado."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Áudio",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.aac *.ogg)"
        )
        
        if file_path:
            try:
                from pathlib import Path
                src_path = Path(file_path)
                dst_path = self.messages_path / src_path.name
                
                # Verifica se o arquivo já existe
                if dst_path.exists():
                    reply = QMessageBox.question(
                        self,
                        "Arquivo Existente",
                        f"O arquivo {src_path.name} já existe. Substituir?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.No:
                        return
                
                # Copia o arquivo
                import shutil
                shutil.copy2(src_path, dst_path)
                
                QMessageBox.information(
                    self,
                    "Importação Concluída",
                    f"Arquivo {src_path.name} importado com sucesso!"
                )
                
                self.accept()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erro",
                    f"Erro ao importar arquivo: {str(e)}"
                )