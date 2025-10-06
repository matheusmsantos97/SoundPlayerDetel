#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Janela principal do aplicativo de rádio.
CORRIGIDO: Caminho da pasta AUDIO para usar RadioTeste diretamente.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QListWidget,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QMenu,QApplication)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint
from PyQt6.QtGui import QFont, QIcon, QAction, QColor

from services.player_service import PlayerService
from services.queue_service import QueueService
from ui.dialogs import AddMessageDialog, MessageImportDialog


# Importação condicional para evitar erro se não existir
try:
    from ui.radio_source_dialog import RadioSourceDialog
except ImportError:
    print("⚠ Arquivo radio_source_dialog.py não encontrado - função de configuração de fonte desabilitada")
    RadioSourceDialog = None




class RadioPlayerWindow(QMainWindow):
    """
    Janela principal do aplicativo de rádio.
    Contém a interface completa e coordena os serviços.
    """
    
    def __init__(self):
        """Inicializa a janela principal."""
        super().__init__()

        self._updating_status = False
        self._updating_table = False
        self._is_closing = False
        
        # Configurações da janela
        self.setWindowTitle("Player de Rádio com Mensagens")
        self.setMinimumSize(800, 600)
        
        # Determina o caminho correto da pasta atual
        # Se estivermos em ui/, volta para a pasta pai (RadioTeste)
        # Se estivermos em RadioTeste/, usa diretamente
        current_file_dir = Path(__file__).resolve().parent
        
        if current_file_dir.name == "ui":
            # Estamos na pasta ui/, volta para RadioTeste
            project_dir = current_file_dir.parent
        else:
            # Estamos diretamente na pasta do projeto
            project_dir = current_file_dir
        
        self.messages_path = project_dir / "AUDIO"
        self.config_dir = project_dir / "config"
        
        # Define o arquivo de persistência da fila
        def get_queue_file_path():
            try:
                base = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser("~")
                app_data_dir = Path(base) / "JB_FM_Player"
                app_data_dir.mkdir(parents=True, exist_ok=True)
                return app_data_dir / "queue_state.json"
            except Exception as e:
                print(f"⚠ Erro ao definir pasta segura: {e}")
                return Path("queue_state.json")  # fallback

        self.queue_file_path = get_queue_file_path()
        print(f"💾 Fila será salva em: {self.queue_file_path}")
        
        # Cria os diretórios se não existirem
        self.messages_path.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Informa qual pasta está sendo usada
        print(f"📂 Pasta do projeto: {project_dir}")
        print(f"📁 Pasta de mensagens: {self.messages_path}")
        print(f"⚙️ Pasta de configuração: {self.config_dir}")
        
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
        
        # MODIFICADO: Timer de atualização mais rápido para tempo real
        self.update_timer = QTimer()
        self.update_timer.setInterval(250)  # 100ms = 10x por segundo para atualização suave
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start()
        
        # Timer específico para atualização da tabela (ainda mais frequente)
        self.table_timer = QTimer()
        self.table_timer.setInterval(500)  # 200ms = 5x por segundo só para a tabela
        self.table_timer.timeout.connect(self.update_queue_table_realtime)
        self.table_timer.start()

         # Inicializa o gerenciador da fila
        from services.message_queue_manager import MessageQueueManager
        self.queue_manager = MessageQueueManager(self.queue_service, self.player_service)
        
        # Inicia o gerenciador
        self.queue_manager.start()
        print("🎯 Sistema de fila automática ativado")
        
        # Carrega a lista de mensagens - DEVE SER EXECUTADO APÓS init_ui()
        self.load_messages()
        
        # Atualiza a tabela da fila para mostrar as mensagens carregadas
        self.update_queue_table()

    def safe_update_status(self):
        """
        NOVA FUNÇÃO: Atualização segura do status evitando concorrência.
        """
        if self._is_closing or self._updating_status:
            return
            
        self._updating_status = True
        try:
            self.update_status()
        finally:
            self._updating_status = False

    def safe_update_table(self):
        """
        NOVA FUNÇÃO: Atualização segura da tabela evitando concorrência.
        """
        if self._is_closing or self._updating_table:
            return
            
        self._updating_table = True
        try:
            self.update_queue_table_realtime()
        finally:
            self._updating_table = False

    def update_queue_table_realtime(self):
        """
        Atualização em tempo real apenas da coluna de tempo - VERSÃO CORRIGIDA.
        """
        # Verificar se estamos fechando ou se a tabela está sendo modificada
        if self._is_closing or not hasattr(self, 'queue_table'):
            return
            
        if self.queue_table.rowCount() == 0:
            return
        
        # Usar blockSignals para evitar eventos durante atualização
        self.queue_table.blockSignals(True)
        
        try:
            items = self.queue_service.get_queue_items()
            if not items or len(items) != self.queue_table.rowCount():
                # Se a estrutura mudou, faz atualização completa
                self.update_queue_table()
                return
            
            current_time = datetime.now()
            
            # Atualiza apenas a coluna de tempo (coluna 3)
            for i, message in enumerate(items):
                if i >= self.queue_table.rowCount():
                    break
                    
                delta = message.next_play_time - current_time
                delta_seconds = delta.total_seconds()
                
                # Cria o item de status atualizado
                if message.is_pending:
                    status_text = "⏳ Aguardando vez"
                    color = QColor(128, 128, 128)  # Cinza
                elif delta_seconds <= 0:
                    # Já passou da hora ou está na hora
                    if abs(delta_seconds) < 5:  # Dentro de 5 segundos
                        status_text = "🔴 TOCANDO AGORA!"
                        color = QColor(255, 0, 0)  # Vermelho
                    else:
                        status_text = "🟢 PRONTA!"
                        color = QColor(0, 180, 0)  # Verde
                else:
                    # Ainda não chegou a hora - CONTAGEM REGRESSIVA
                    if delta_seconds < 60:
                        # Menos de 1 minuto - só segundos
                        time_str = f"⏰ {int(delta_seconds)}s"
                        color = QColor(255, 140, 0)  # Laranja
                    elif delta_seconds < 3600:
                        # Menos de 1 hora - minutos e segundos
                        minutes = int(delta_seconds // 60)
                        seconds = int(delta_seconds % 60)
                        time_str = f"⏰ {minutes}m {seconds}s"
                        color = QColor(0, 100, 255)  # Azul
                    else:
                        # Mais de 1 hora - só horário
                        time_str = f"🕐 {message.next_play_time.strftime('%H:%M:%S')}"
                        color = QColor(100, 100, 100)  # Cinza escuro
                    
                    status_text = time_str
                
                # Atualiza apenas se o texto mudou (otimização)
                current_item = self.queue_table.item(i, 3)
                if current_item and current_item.text() != status_text:
                    current_item.setText(status_text)
                    current_item.setForeground(color)
                    
        finally:
            # Sempre reativar sinais
            self.queue_table.blockSignals(False)
    
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
        
        title_label = QLabel("Sound Player Detel")
        title_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label, 1)  # Adicionado stretch factor 1
        
        # Botão de configuração de fonte - só aparece se arquivo existir
        if RadioSourceDialog is not None:
            self.source_button = QPushButton("Configurar Fonte")
            self.source_button.setToolTip("Configurar fonte de rádio (Internet/Tunner)")
            self.source_button.clicked.connect(self.configure_radio_source)
            title_layout.addWidget(self.source_button)
        else:
            # Botão desabilitado se não houver o arquivo
            self.source_button = QPushButton("Configurar Fonte (Indisponível)")
            self.source_button.setEnabled(False)
            self.source_button.setToolTip("Arquivo radio_source_dialog.py não encontrado")
            title_layout.addWidget(self.source_button)
        
        header_layout.addLayout(title_layout)
        
        # Mostrar a fonte atual
        self.source_label = QLabel()
        self.source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_source_label()
        header_layout.addWidget(self.source_label)
        
        # MODIFICADO: Mostra a pasta AUDIO sendo usada
        self.messages_path_label = QLabel(f"📁 Pasta de áudios: {self.messages_path}")
        self.messages_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.messages_path_label.setStyleSheet("color: blue; font-weight: bold;")
        header_layout.addWidget(self.messages_path_label)
        
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
        
        # MODIFICADO: Título mostra a pasta sendo usada
        messages_title = QLabel(f"Mensagens Disponíveis (Pasta: {self.messages_path.name}):")
        messages_title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        messages_panel.addWidget(messages_title)
        
        # Lista de mensagens
        self.messages_list = QListWidget()
        self.messages_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.messages_list.itemDoubleClicked.connect(self.play_selected_message)
        messages_panel.addWidget(self.messages_list)
        
        # ADICIONADO: Label com contagem de arquivos
        self.file_count_label = QLabel("Carregando...")
        self.file_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_count_label.setStyleSheet("color: gray; font-style: italic;")
        messages_panel.addWidget(self.file_count_label)
        
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
        
        # MODIFICADO: Botão para abrir especificamente a pasta AUDIO
        open_folder_button = QPushButton("Abrir Pasta AUDIO")
        open_folder_button.setToolTip(f"Abrir pasta {self.messages_path} no explorador")
        open_folder_button.clicked.connect(self.open_messages_folder)
        open_folder_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        messages_buttons.addWidget(open_folder_button)
        
        messages_panel.addLayout(messages_buttons)
        
        # ADICIONADO: Botão para atualizar lista
        refresh_layout = QHBoxLayout()
        refresh_button = QPushButton("🔄 Atualizar Lista")
        refresh_button.setToolTip("Recarregar arquivos da pasta AUDIO")
        refresh_button.clicked.connect(self.refresh_messages)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()  # Empurra o botão para a esquerda
        messages_panel.addLayout(refresh_layout)
        
        central_layout.addLayout(messages_panel)
        
        # ----- Painel da fila de reprodução -----
        queue_panel = QVBoxLayout()
        
        queue_panel.addWidget(QLabel("Fila de Reprodução:"))
        
        # CORRIGIDO: Configuração aprimorada da tabela
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)

        # Define os cabeçalhos das colunas
        headers = ["Arquivo", "Prioridade", "Intervalo", "Próxima Execução"]
        self.queue_table.setHorizontalHeaderLabels(headers)

        # NOVA ABORDAGEM: Configuração mais inteligente das colunas
        header = self.queue_table.horizontalHeader()

        # Coluna 0 (Arquivo) - Tamanho mínimo garantido, pode expandir
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.queue_table.setColumnWidth(0, 250)  # Largura inicial generosa

        # Coluna 1 (Prioridade) - Tamanho fixo pequeno
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.queue_table.setColumnWidth(1, 80)

        # Coluna 2 (Intervalo) - Tamanho fixo médio
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.queue_table.setColumnWidth(2, 100)

        # Coluna 3 (Próxima Execução) - Tamanho fixo largo
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.queue_table.setColumnWidth(3, 180)  # Espaço para contagem regressiva

        # MELHORIAS: Configurações visuais e funcionais
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.queue_table.verticalHeader().setVisible(False)

        # Altura adequada do cabeçalho
        self.queue_table.horizontalHeader().setMinimumHeight(32)

        # Fonte do cabeçalho
        header_font = QFont('Arial', 10, QFont.Weight.Bold)
        self.queue_table.horizontalHeader().setFont(header_font)

        # Altura das linhas
        self.queue_table.verticalHeader().setDefaultSectionSize(28)

        # Permite redimensionar colunas manualmente
        header.setSectionsClickable(True)
        header.setHighlightSections(True)

        # Scroll horizontal quando necessário
        self.queue_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # NOVO: Largura mínima da tabela
        self.queue_table.setMinimumWidth(650)

        # NOVO: Tooltip para ajudar o usuário
        self.queue_table.setToolTip("💡 Dica: Você pode redimensionar as colunas arrastando as bordas dos cabeçalhos")
                
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
        
        fade_layout = QHBoxLayout()

        fade_label = QLabel("🎵 Fade:")
        fade_layout.addWidget(fade_label)

        # Botões de preset
        btn_prof = QPushButton("Profissional")
        btn_prof.clicked.connect(lambda: self.apply_fade_preset("professional"))
        fade_layout.addWidget(btn_prof)

        btn_fast = QPushButton("Rápido")
        btn_fast.clicked.connect(lambda: self.apply_fade_preset("fast"))
        fade_layout.addWidget(btn_fast)

        btn_smooth = QPushButton("Suave")
        btn_smooth.clicked.connect(lambda: self.apply_fade_preset("smooth"))
        fade_layout.addWidget(btn_smooth)

        fade_layout.addStretch()

        main_layout.addLayout(fade_layout)
        
        # Define o layout na janela principal
        central_widget.setLayout(main_layout)

    def apply_fade_preset(self, preset_name):
        """Aplica preset de fade."""
        if hasattr(self, 'queue_manager') and hasattr(self.queue_manager, 'fade_manager'):
            self.queue_manager.fade_manager.apply_preset(preset_name)
            QMessageBox.information(self, "Fade", f"Preset '{preset_name}' aplicado!")
        else:
            QMessageBox.warning(self, "Erro", "Sistema de fade não disponível")

    
    def optimize_table_columns(self):
            """
            Otimiza automaticamente o tamanho das colunas baseado no conteúdo.
            Chama este método após preencher a tabela.
            """
            if self.queue_table.rowCount() == 0:
                return
                
            # Ajusta a coluna "Arquivo" para o conteúdo
            self.queue_table.resizeColumnToContents(0)
            
            # Garante uma largura mínima para a coluna "Arquivo"
            current_width = self.queue_table.columnWidth(0)
            min_width = 150  # Largura mínima
            max_width = 300  # Largura máxima
            
            if current_width < min_width:
                self.queue_table.setColumnWidth(0, min_width)
            elif current_width > max_width:
                self.queue_table.setColumnWidth(0, max_width)
            
            # Força atualização visual
            self.queue_table.updateGeometry()
            self.queue_table.repaint()
    
    def open_messages_folder(self):

        try:
            import subprocess
            import platform
            
            # Garante que a pasta existe
            if not self.messages_path.exists():
                self.messages_path.mkdir(parents=True, exist_ok=True)
                print(f"Pasta AUDIO criada: {self.messages_path}")
            
            # Converte para caminho absoluto correto
            folder_path = str(self.messages_path.resolve())
            
            print(f"Tentando abrir pasta: {folder_path}")
            
            system = platform.system()
            
            if system == "Windows":
                # Tenta diferentes métodos no Windows
                try:
                    # Método 1: Explorer direto
                    result = subprocess.run(['explorer', folder_path], 
                                          capture_output=True, text=True, timeout=3)
                    if result.returncode == 0:
                        print(f"✅ Pasta aberta com sucesso: {folder_path}")
                        return
                except subprocess.TimeoutExpired:
                    # Timeout é normal - o explorer abre em background
                    print(f"✅ Pasta aberta (timeout normal): {folder_path}")
                    return
                except Exception as e:
                    print(f"Método 1 falhou: {e}")
                
                try:
                    # Método 2: Com /select
                    subprocess.run(['explorer', '/select,', folder_path], 
                                 capture_output=True, text=True, timeout=3)
                    print(f"✅ Pasta aberta com /select: {folder_path}")
                    return
                except subprocess.TimeoutExpired:
                    print(f"✅ Pasta aberta com /select (timeout normal): {folder_path}")
                    return
                except Exception as e:
                    print(f"Método 2 falhou: {e}")
                
                try:
                    # Método 3: Usando start
                    subprocess.run(['cmd', '/c', 'start', folder_path], 
                                 capture_output=True, text=True, timeout=3)
                    print(f"✅ Pasta aberta com start: {folder_path}")
                    return
                except Exception as e:
                    print(f"Método 3 falhou: {e}")
                    
            elif system == "Darwin":  # macOS
                subprocess.run(['open', folder_path], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', folder_path], check=True)
            
            print(f"✅ Comando de abertura enviado para: {folder_path}")
                
        except subprocess.TimeoutExpired:
            # Timeout é normal para o explorer
            print(f"✅ Pasta AUDIO aberta (timeout normal): {self.messages_path}")
        except FileNotFoundError:
            QMessageBox.information(
                self,
                "Pasta AUDIO",
                f"Explorador não encontrado, mas a pasta existe em:\n\n{self.messages_path}\n\nAbra manualmente no explorador de arquivos."
            )
        except Exception as e:
            QMessageBox.information(
                self,
                "Pasta AUDIO", 
                f"Pasta AUDIO localizada em:\n\n{self.messages_path}\n\nCopie este caminho e abra manualmente no explorador.\n\nDetalhes técnicos: {str(e)}"
            )
    
    def refresh_messages(self):
        """Atualiza a lista de mensagens manualmente."""
        print("Atualizando lista de mensagens...")
        self.load_messages()
        QMessageBox.information(
            self,
            "Lista Atualizada", 
            f"Lista de mensagens atualizada!\nPasta: {self.messages_path}"
        )
    
    def load_messages(self):
        """Carrega a lista de mensagens da pasta AUDIO."""
        self.messages_list.clear()
        
        try:
            # Verifica se a pasta AUDIO existe
            if not self.messages_path.exists():
                self.messages_path.mkdir(parents=True, exist_ok=True)
                print(f"Pasta AUDIO criada: {self.messages_path}")
                
                # Cria arquivo de exemplo/instruções
                self.create_audio_folder_info()
            
            # Extensões de áudio suportadas
            audio_extensions = ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a']
            found_files = []
            
            print(f"Procurando arquivos de áudio em: {self.messages_path}")
            
            # Busca por arquivos de áudio
            for ext in audio_extensions:
                # Minúscula
                for file in self.messages_path.glob(f"*{ext}"):
                    if file.is_file():
                        found_files.append(file)
                        self.messages_list.addItem(file.name)
                
                # Maiúscula
                for file in self.messages_path.glob(f"*{ext.upper()}"):
                    if file.is_file() and file not in found_files:
                        found_files.append(file)
                        self.messages_list.addItem(file.name)
            
            # Ordena por nome
            self.messages_list.sortItems()
            
            # Atualiza o label de contagem
            if found_files:
                self.file_count_label.setText(f"📊 {len(found_files)} arquivo(s) encontrado(s)")
                self.file_count_label.setStyleSheet("color: green; font-weight: bold;")
                print(f"✅ {len(found_files)} arquivo(s) de áudio carregado(s)")
                
                # Lista os primeiros arquivos encontrados
                print("Arquivos encontrados:")
                for i, file in enumerate(found_files[:5], 1):
                    print(f"  {i}. {file.name}")
                if len(found_files) > 5:
                    print(f"  ... e mais {len(found_files) - 5} arquivo(s)")
            else:
                self.file_count_label.setText("📂 Pasta vazia - Adicione arquivos de áudio")
                self.file_count_label.setStyleSheet("color: orange; font-style: italic;")
                print(f"⚠ Nenhum arquivo de áudio encontrado em: {self.messages_path}")
                print("Extensões suportadas: .mp3, .wav, .aac, .ogg, .flac, .m4a")
                
        except Exception as e:
            error_msg = f"Erro ao carregar mensagens: {str(e)}"
            print(f"❌ {error_msg}")
            self.file_count_label.setText("❌ Erro ao carregar")
            self.file_count_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.warning(self, "Erro", error_msg)
    
    def create_audio_folder_info(self):
        """Cria um arquivo informativo na pasta AUDIO se ela estiver vazia."""
        try:
            info_file = self.messages_path / "COMO_USAR.txt"
            
            if not info_file.exists():
                info_content = f"""PASTA DE ÁUDIO - SOUND PLAYER DETEL
========================================

Esta é a pasta onde você deve colocar seus arquivos de áudio.

LOCALIZAÇÃO: {self.messages_path}

FORMATOS SUPORTADOS:
• MP3 (.mp3)
• WAV (.wav)  
• AAC (.aac)
• OGG (.ogg)
• FLAC (.flac)
• M4A (.m4a)

COMO USAR:
1. Copie seus arquivos de áudio para esta pasta
2. No aplicativo, clique "🔄 Atualizar Lista" para recarregar
3. Ou use "Importar Mensagem" para copiar arquivos
4. Adicione as mensagens à fila de reprodução

COMANDOS PARA EXECUTAR (Windows):
• python main.py
• py main.py

DICAS:
• Use nomes descritivos para seus arquivos
• Evite caracteres especiais nos nomes
• Organize por categorias se necessário

Criado automaticamente pelo Sound Player Detel
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
                
                with open(info_file, 'w', encoding='utf-8') as f:
                    f.write(info_content)
                print(f"✅ Arquivo de instruções criado: {info_file}")
                
        except Exception as e:
            print(f"⚠ Erro ao criar arquivo de instruções: {str(e)}")
    
    def configure_radio_source(self):
        """CORRIGIDO: Abre o diálogo para configurar a fonte de rádio."""
        if RadioSourceDialog is None:
            QMessageBox.warning(
                self,
                "Função Indisponível",
                "O arquivo radio_source_dialog.py não foi encontrado.\n\n"
                "Esta função está temporariamente indisponível."
            )
            return
            
        try:
            dialog = RadioSourceDialog(self.player_service, self)
            dialog.exec()
            
            # Atualiza o label com a fonte atual
            self.update_source_label()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao abrir configuração de fonte:\n{str(e)}"
            )

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
        Atualiza o status do player.
        OTIMIZADO: Separou a atualização da tabela para ser mais eficiente.
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
        
        # Atualiza o modo se não estiver no modo de microfone
        if not hasattr(self.player_service, 'mic_active') or not self.player_service.mic_active:
            if self.player_service.is_radio_mode:
                self.mode_label.setText("Modo: Rádio")
            else:
                if hasattr(self.player_service, 'current_message') and self.player_service.current_message:
                    self.mode_label.setText(f"Modo: Mensagem - {self.player_service.current_message.filename}")
                else:
                    self.mode_label.setText("Modo: Mensagem")

    def update_queue_table(self):
        """
        Atualização completa da tabela da fila - VERSÃO CORRIGIDA.
        """
        # Verificar se estamos fechando
        if self._is_closing or not hasattr(self, 'queue_table'):
            return
            
        items = self.queue_service.get_queue_items()
        
        # Usar blockSignals durante atualização completa
        self.queue_table.blockSignals(True)
        
        try:
            if not items:
                # Limpa a tabela se não houver itens
                self.queue_table.setRowCount(0)
                return
            
            # Define o número de linhas da tabela
            self.queue_table.setRowCount(len(items))
            
            # Hora atual para cálculos
            current_time = datetime.now()
            
            # Preenche a tabela com informações atualizadas
            for i, message in enumerate(items):
                # Coluna Arquivo - NOME COMPLETO
                file_item = QTableWidgetItem(message.filename)
                # Destaca mensagens ativas com negrito
                if not message.is_pending:
                    font = file_item.font()
                    font.setBold(True)
                    file_item.setFont(font)
                    file_item.setForeground(QColor(0, 100, 0))  # Verde escuro
                # Tooltip com nome completo
                file_item.setToolTip(f"📁 {message.filename}")
                self.queue_table.setItem(i, 0, file_item)
                
                # Coluna Prioridade
                priority_item = QTableWidgetItem(f"P{message.priority}")
                # Cor baseada na prioridade
                if message.priority == 1:
                    priority_item.setForeground(QColor(255, 0, 0))  # Vermelho para P1
                elif message.priority == 2:
                    priority_item.setForeground(QColor(255, 140, 0))  # Laranja para P2
                else:
                    priority_item.setForeground(QColor(0, 100, 255))  # Azul para P3+
                self.queue_table.setItem(i, 1, priority_item)
                
                # Coluna Intervalo
                if message.interval < 1.0:
                    seconds = int(message.interval * 60)
                    interval_text = f"{seconds} seg"
                else:
                    minutes = round(message.interval)
                    interval_text = f"{minutes} min"
                interval_item = QTableWidgetItem(interval_text)
                self.queue_table.setItem(i, 2, interval_item)
                
                # Coluna Próxima Execução - COM CONTAGEM REGRESSIVA
                delta = message.next_play_time - current_time
                delta_seconds = delta.total_seconds()
                
                if message.is_pending:
                    status_text = "⏳ Aguardando vez"
                    color = QColor(128, 128, 128)  # Cinza
                elif delta_seconds <= 0:
                    # Já passou da hora ou está na hora
                    if abs(delta_seconds) < 5:  # Dentro de 5 segundos
                        status_text = "🔴 TOCANDO AGORA!"
                        color = QColor(255, 0, 0)  # Vermelho
                    else:
                        status_text = "🟢 PRONTA!"
                        color = QColor(0, 180, 0)  # Verde
                else:
                    # Ainda não chegou a hora - CONTAGEM REGRESSIVA
                    if delta_seconds < 60:
                        # Menos de 1 minuto - só segundos
                        status_text = f"⏰ {int(delta_seconds)}s"
                        color = QColor(255, 140, 0)  # Laranja
                    elif delta_seconds < 3600:
                        # Menos de 1 hora - minutos e segundos
                        minutes = int(delta_seconds // 60)
                        seconds = int(delta_seconds % 60)
                        status_text = f"⏰ {minutes}m {seconds}s"
                        color = QColor(0, 100, 255)  # Azul
                    else:
                        # Mais de 1 hora - só horário
                        status_text = f"🕐 {message.next_play_time.strftime('%H:%M:%S')}"
                        color = QColor(100, 100, 100)  # Cinza escuro
                
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(color)
                self.queue_table.setItem(i, 3, status_item)
            
            # Não chamar optimize_table_columns a cada atualização
            # Chamar apenas quando necessário (primeira vez ou mudança significativa)
            if not hasattr(self, '_table_optimized'):
                self.optimize_table_columns()
                self._table_optimized = True
                
        finally:
            # Sempre reativar sinais
            self.queue_table.blockSignals(False)
            
        # Usar update() em vez de repaint()
        self.queue_table.viewport().update()


    def toggle_playback(self):
        """Alterna entre play e pause."""
        try:
            self.player_service.toggle_playback()
            
            if self.player_service.is_playing:
                self.play_button.setText("⏸ Pause")
            else:
                self.play_button.setText("▶ Play")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro na reprodução: {str(e)}")

    def paintEvent(self, event):
        """
        Override seguro do paintEvent se houver algum em suas classes.
        """
        # Verificar se estamos fechando
        if hasattr(self, '_is_closing') and self._is_closing:
            return
        
        # Usar super() para chamar implementação pai
        super().paintEvent(event)
    
    def play_selected_message(self, item):
        """Reproduz a mensagem selecionada diretamente."""
        try:
            filename = item.text()
            success = self.player_service.play_message(filename, None)
            
            if success:
                self.mode_label.setText(f"Modo: Mensagem - {filename}")
            else:
                QMessageBox.warning(self, "Erro", f"Não foi possível reproduzir: {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao reproduzir mensagem: {str(e)}")
    
    def add_to_queue(self):
        """Adiciona a mensagem selecionada à fila."""
        current_item = self.messages_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Erro", "Selecione uma mensagem para adicionar à fila.")
            return
        
        try:
            filename = current_item.text()
            
            # Verifica duplicatas
            items = self.queue_service.get_queue_items()
            for item in items:
                if item.filename == filename:
                    QMessageBox.warning(self, "Aviso", 
                        f"A mensagem '{filename}' já está na fila.")
                    return
            
            dialog = AddMessageDialog(self)
            if dialog.exec():
                priority = dialog.priority_spin.value()
                interval_minutes = dialog.get_interval_in_minutes()
                
                # Adiciona a mensagem à fila
                message = self.queue_service.add_message(filename, priority, interval_minutes)
                
                if message:
                    # Mostra informação sobre o agendamento usando o intervalo definido
                    interval_seconds = int(interval_minutes * 60)
                    
                    QMessageBox.information(
                        self,
                        "Mensagem Agendada",
                        f"Mensagem '{filename}' adicionada à fila!\n\n"
                        f"Primeira execução: em {interval_seconds} segundos\n"
                        f"Intervalo entre mensagens: {interval_seconds} segundos"
                    )
                    
                    self.update_queue_table()
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Erro", f"Erro ao adicionar à fila: {str(e)}")

    
    def remove_from_queue(self):
        """Remove a mensagem selecionada da fila."""
        current_row = self.queue_table.currentRow()
        if current_row >= 0:
            try:
                filename = self.queue_table.item(current_row, 0).text()
                self.queue_service.remove_message(filename)
                self.update_queue_table()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao remover da fila: {str(e)}")
    
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
            try:
                self.queue_service.clear_queue()
                self.update_queue_table()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao limpar fila: {str(e)}")
    
    def import_message(self):
        """Abre o diálogo para importar novas mensagens."""
        try:
            dialog = MessageImportDialog(self.messages_path, self)
            if dialog.exec():
                self.load_messages()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao importar mensagem: {str(e)}")
    
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
            f"Tem certeza que deseja excluir permanentemente o arquivo '{filename}'?\n\nPasta: {self.messages_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                file_path = self.messages_path / filename
                file_path.unlink()
                
                # Recarrega a lista após remover
                self.load_messages()
                
                # Verifica se está na fila e remove
                self.queue_service.remove_message(filename)
                self.update_queue_table()
                
                QMessageBox.information(
                    self,
                    "Arquivo Removido",
                    f"Arquivo '{filename}' removido com sucesso!"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao remover arquivo: {str(e)}")
    
    def closeEvent(self, event):
        """
        Trata o evento de fechamento da janela - VERSÃO CORRIGIDA.
        """
        # Sinalizar que estamos fechando PRIMEIRO
        self._is_closing = True
        
        try:
            print("🔄 Encerrando aplicação...")
            
            # Para os timers PRIMEIRO
            if hasattr(self, 'update_timer'):
                print("⏰ Parando timer principal...")
                self.update_timer.stop()
                
            if hasattr(self, 'table_timer'):
                print("📊 Parando timer da tabela...")
                self.table_timer.stop()
            
            # Aguardar um momento para garantir que threads terminem
            QApplication.processEvents()
            
            # Para o gerenciador da fila
            if hasattr(self, 'queue_manager'):
                print("⏹️ Parando gerenciador da fila...")
                self.queue_manager.stop()
            
            # NOVO: Salva o estado final com flag de encerramento
            if hasattr(self, 'queue_service') and self.queue_service:
                print("💾 Salvando estado final com flag de ENCERRAMENTO...")
                self.queue_service.shutdown_save()
            
            # Limpa recursos do player
            if hasattr(self, 'player_service'):
                print("🔧 Limpando recursos do player...")
                self.player_service.cleanup()
            
            # Limpa recursos do queue_service
            if hasattr(self, 'queue_service'):
                print("🧹 Limpando recursos do queue_service...")
                self.queue_service.cleanup()
            
            print("✅ Aplicação encerrada com sucesso - intervalos serão resetados na próxima inicialização")
            event.accept()
            
        except Exception as e:
            print(f"❌ Erro ao fechar aplicação: {str(e)}")
            event.accept()  # Aceita o fechamento mesmo com erro