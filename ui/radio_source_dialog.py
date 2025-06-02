#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diálogo para configuração de fontes de rádio.
Permite selecionar entre streaming e dispositivos físicos.
"""

from PyQt6.QtWidgets import (QDialog, QFormLayout, QLabel, QVBoxLayout, QHBoxLayout,
                            QPushButton, QComboBox, QListWidget, QListWidgetItem,
                            QLineEdit, QMessageBox, QTabWidget, QWidget, QRadioButton,
                            QButtonGroup)
from PyQt6.QtCore import Qt, QSize
from services.radio_source_manager import RadioSource

class RadioSourceDialog(QDialog):
    """
    Diálogo para configurar fontes de rádio.
    Permite adicionar, remover e selecionar diferentes fontes.
    """
    
    def __init__(self, player_service, parent=None):
        """
        Inicializa o diálogo.
        
        Args:
            player_service: Serviço de reprodução para acessar o gerenciador de fontes
            parent: Widget pai
        """
        super().__init__(parent)
        self.setWindowTitle("Configurar Fonte de Rádio")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.player_service = player_service
        self.source_manager = player_service.source_manager
        
        self.source_changed = False  # Flag para saber se algo foi alterado
        
        self.init_ui()
        self.load_sources()
    
    def init_ui(self):
        """Inicializa a interface do diálogo."""
        layout = QVBoxLayout()
        
        # Título
        title_label = QLabel("Configuração de Fontes de Rádio")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Cria as abas
        tab_widget = QTabWidget()
        
        # Aba de seleção de fonte
        select_tab = self._create_select_tab()
        tab_widget.addTab(select_tab, "Selecionar Fonte")
        
        # Aba de adicionar nova fonte
        add_tab = self._create_add_tab()
        tab_widget.addTab(add_tab, "Adicionar Nova Fonte")
        
        layout.addWidget(tab_widget)
        
        # Botões inferiores
        button_layout = QHBoxLayout()
        
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_select_tab(self):
        """Cria a aba para selecionar/remover fontes."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Instruções
        instruction_label = QLabel("Selecione a fonte de áudio para a rádio:")
        layout.addWidget(instruction_label)
        
        # Lista de fontes
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.source_list)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        
        select_button = QPushButton("Usar Esta Fonte")
        select_button.clicked.connect(self.select_source)
        action_layout.addWidget(select_button)
        
        remove_button = QPushButton("Remover Fonte")
        remove_button.clicked.connect(self.remove_source)
        action_layout.addWidget(remove_button)
        
        test_button = QPushButton("Testar")
        test_button.clicked.connect(self.test_source)
        action_layout.addWidget(test_button)
        
        layout.addLayout(action_layout)
        
        # Informações da fonte atual
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Fonte atual:"))
        
        self.current_source_label = QLabel()
        self.current_source_label.setStyleSheet("font-weight: bold;")
        current_layout.addWidget(self.current_source_label)
        
        current_layout.addStretch()
        
        layout.addLayout(current_layout)
        
        tab.setLayout(layout)
        return tab
    
    def _create_add_tab(self):
        """Cria a aba para adicionar novas fontes."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Nome da fonte
        name_layout = QFormLayout()
        self.name_edit = QLineEdit()
        name_layout.addRow("Nome da fonte:", self.name_edit)
        layout.addLayout(name_layout)
        
        # Tipo de fonte (Radio Buttons)
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo de fonte:"))
        
        self.type_group = QButtonGroup()
        
        self.stream_radio = QRadioButton("Streaming (Internet)")
        self.stream_radio.setChecked(True)
        self.stream_radio.toggled.connect(self.toggle_source_type)
        self.type_group.addButton(self.stream_radio)
        type_layout.addWidget(self.stream_radio)
        
        self.device_radio = QRadioButton("Dispositivo (Tunner)")
        self.type_group.addButton(self.device_radio)
        type_layout.addWidget(self.device_radio)
        
        layout.addLayout(type_layout)
        
        # Área de configuração de streaming
        self.stream_widget = QWidget()
        stream_layout = QFormLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://exemplo.com/stream.aac")
        stream_layout.addRow("URL do streaming:", self.url_edit)
        self.stream_widget.setLayout(stream_layout)
        layout.addWidget(self.stream_widget)
        
        # Área de configuração de dispositivo
        self.device_widget = QWidget()
        device_layout = QFormLayout()
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)
        device_layout.addRow("Dispositivo:", self.device_combo)
        self.device_widget.setLayout(device_layout)
        self.device_widget.setVisible(False)  # Inicialmente oculto
        layout.addWidget(self.device_widget)
        
        # Botão para carregar dispositivos
        self.refresh_button = QPushButton("Atualizar Lista de Dispositivos")
        self.refresh_button.clicked.connect(self.load_devices)
        self.refresh_button.setVisible(False)  # Inicialmente oculto
        layout.addWidget(self.refresh_button)
        
        # Botão para adicionar
        add_layout = QHBoxLayout()
        add_layout.addStretch()
        
        add_button = QPushButton("Adicionar Fonte")
        add_button.clicked.connect(self.add_source)
        add_layout.addWidget(add_button)
        
        layout.addLayout(add_layout)
        
        # Espaço flexível
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
    
    def toggle_source_type(self):
        """Alterna entre os tipos de fonte (streaming/dispositivo)."""
        is_stream = self.stream_radio.isChecked()
        
        self.stream_widget.setVisible(is_stream)
        self.device_widget.setVisible(not is_stream)
        self.refresh_button.setVisible(not is_stream)
        
        # Se mudar para dispositivo, carrega a lista
        if not is_stream:
            self.load_devices()
    
    def load_sources(self):
        """Carrega a lista de fontes disponíveis."""
        self.source_list.clear()
        
        # Obtém as fontes do gerenciador
        sources = self.source_manager.sources
        
        # Obtém o índice da fonte atual
        current_index = self.source_manager.current_source_index
        
        for i, source in enumerate(sources):
            # Cria o texto do item
            type_str = "Streaming" if source.source_type == RadioSource.TYPE_STREAM else "Dispositivo"
            item_text = f"{source.name} ({type_str})"
            
            if i == current_index:
                item_text += " [ATUAL]"
            
            # Adiciona à lista
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Armazena o índice
            self.source_list.addItem(item)
            
            # Se for a fonte atual, seleciona
            if i == current_index:
                self.source_list.setCurrentItem(item)
                self.current_source_label.setText(item_text)
    
    def load_devices(self):
        """Carrega a lista de dispositivos de áudio disponíveis."""
        self.device_combo.clear()
        
        devices = self.source_manager.get_audio_devices()
        
        if not devices:
            self.device_combo.addItem("Nenhum dispositivo encontrado")
            return
        
        for device in devices:
            device_text = f"{device['name']} (Canais: {device['channels']})"
            self.device_combo.addItem(device_text, device['index'])
    
    def select_source(self):
        """Seleciona a fonte de rádio atual."""
        current_item = self.source_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Erro", "Selecione uma fonte de rádio!")
            return
        
        # Obtém o índice da fonte selecionada
        source_index = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Se for a mesma fonte atual, não precisa mudar
        if source_index == self.source_manager.current_source_index:
            QMessageBox.information(self, "Info", "Esta já é a fonte atual.")
            return
        
        # Muda a fonte de rádio
        success = self.player_service.change_radio_source(source_index)
        
        if success:
            self.source_changed = True
            QMessageBox.information(
                self,
                "Fonte Alterada",
                f"Fonte de rádio alterada para {self.source_manager.get_current_source().name}"
            )
            # Atualiza a lista
            self.load_sources()
        else:
            QMessageBox.warning(
                self,
                "Erro",
                "Erro ao alterar fonte de rádio!"
            )
    
    def remove_source(self):
        """Remove a fonte selecionada."""
        current_item = self.source_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Erro", "Selecione uma fonte para remover!")
            return
        
        # Obtém o índice da fonte selecionada
        source_index = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Confirmação
        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            "Tem certeza que deseja remover esta fonte?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Tenta remover a fonte
            success = self.source_manager.remove_source(source_index)
            
            if success:
                self.source_changed = True
                QMessageBox.information(
                    self,
                    "Fonte Removida",
                    "Fonte de rádio removida com sucesso!"
                )
                # Atualiza a lista
                self.load_sources()
            else:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Não é possível remover a última fonte ou fonte atual está em uso!"
                )
    
    def test_source(self):
        """Testa a fonte selecionada."""
        current_item = self.source_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Erro", "Selecione uma fonte para testar!")
            return
        
        # Obtém o índice da fonte selecionada
        source_index = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Obtém a fonte correspondente
        if 0 <= source_index < len(self.source_manager.sources):
            source = self.source_manager.sources[source_index]
            
            # Mensagem informativa
            info_text = f"Testando: {source.name}\n"
            
            if source.source_type == RadioSource.TYPE_STREAM:
                info_text += f"URL: {source.url}"
            else:
                info_text += f"Dispositivo: índice {source.device_index}"
            
            QMessageBox.information(
                self,
                "Teste de Fonte",
                info_text + "\n\nA reprodução será alterada temporariamente para testar."
            )
            
            # Salva o índice atual
            original_index = self.source_manager.current_source_index
            
            # Testa a fonte selecionada
            success = self.player_service.change_radio_source(source_index)
            
            if success:
                QMessageBox.information(
                    self,
                    "Teste de Fonte",
                    "Fonte conectada com sucesso!\nOuça por alguns segundos para verificar."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Erro ao testar fonte. Verifique as configurações."
                )
                
            # Pergunta se quer manter a fonte
            reply = QMessageBox.question(
                self,
                "Manter Fonte?",
                "Deseja manter esta fonte como atual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                # Volta para a fonte original
                self.player_service.change_radio_source(original_index)
                self.load_sources()
            else:
                self.source_changed = True
                self.load_sources()
    
    def add_source(self):
        """Adiciona uma nova fonte de rádio."""
        # Validação básica
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Erro", "Informe um nome para a fonte!")
            return
        
        is_stream = self.stream_radio.isChecked()
        
        if is_stream:
            # Para streaming, validar URL
            url = self.url_edit.text().strip()
            if not url:
                QMessageBox.warning(self, "Erro", "Informe a URL do streaming!")
                return
            
            # Adiciona a fonte
            new_source = self.source_manager.add_source(
                name=name,
                source_type=RadioSource.TYPE_STREAM,
                url=url
            )
            
            if new_source:
                self.source_changed = True
                QMessageBox.information(
                    self,
                    "Fonte Adicionada",
                    f"Fonte de streaming '{name}' adicionada com sucesso!"
                )
                # Limpa os campos
                self.name_edit.clear()
                self.url_edit.clear()
                # Atualiza a lista
                self.load_sources()
            else:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Erro ao adicionar fonte de streaming!"
                )
        else:
            # Para dispositivo, validar seleção
            if self.device_combo.count() == 0:
                QMessageBox.warning(self, "Erro", "Nenhum dispositivo disponível!")
                return
            
            # Obtém o índice do dispositivo selecionado
            device_index = self.device_combo.currentData()
            
            if device_index is None:
                QMessageBox.warning(self, "Erro", "Selecione um dispositivo válido!")
                return
            
            # Adiciona a fonte
            new_source = self.source_manager.add_source(
                name=name,
                source_type=RadioSource.TYPE_DEVICE,
                device_index=device_index
            )
            
            if new_source:
                self.source_changed = True
                QMessageBox.information(
                    self,
                    "Fonte Adicionada",
                    f"Fonte de dispositivo '{name}' adicionada com sucesso!"
                )
                # Limpa os campos
                self.name_edit.clear()
                # Atualiza a lista
                self.load_sources()
            else:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Erro ao adicionar fonte de dispositivo!"
                )
    
    def accept(self):
        """Sobrescreve o método de aceitar para informar mudanças."""
        if self.source_changed:
            QMessageBox.information(
                self,
                "Configuração Salva",
                "As configurações de fonte de rádio foram alteradas com sucesso!"
            )
        
        super().accept()