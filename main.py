# -*- coding: utf-8 -*-

"""
Sound Player Detel - Sistema de Rádio com Mensagens
CONFIGURAÇÃO PARA WINDOWS: Usa pasta RadioTeste/AUDIO
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from datetime import datetime
from PyQt6.QtCore import Qt



if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    os.environ['PATH'] = os.pathsep.join([
        os.path.join(base_path),
        os.path.join(base_path, 'plugins'),
        os.environ['PATH'],
    ])

def setup_audio_folder():
    """
    Configura e verifica a pasta AUDIO.
    
    Returns:
        Path: Caminho da pasta AUDIO
    """
    # Usa a pasta RadioTeste atual
    current_dir = Path(__file__).parent  # Pasta onde está o main.py
    audio_folder = current_dir / "AUDIO"
    config_folder = current_dir / "config"
    
    # Cria as pastas se não existirem
    audio_folder.mkdir(parents=True, exist_ok=True)
    config_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Pasta AUDIO: {audio_folder}")
    print(f"⚙️ Pasta Config: {config_folder}")
    
    # Verifica arquivos de áudio existentes
    audio_extensions = ['*.mp3', '*.wav', '*.aac', '*.ogg', '*.flac', '*.m4a']
    audio_files = []
    
    for pattern in audio_extensions:
        audio_files.extend(list(audio_folder.glob(pattern)))
        audio_files.extend(list(audio_folder.glob(pattern.upper())))
    
    # Remove duplicatas
    audio_files = list(set(audio_files))
    
    if audio_files:
        print(f"🎵 Encontrados {len(audio_files)} arquivo(s) de áudio:")
        for i, file in enumerate(audio_files[:5], 1):
            print(f"   {i}. {file.name}")
        if len(audio_files) > 5:
            print(f"   ... e mais {len(audio_files) - 5} arquivo(s)")
    else:
        print("📂 Pasta AUDIO está vazia")
        print("💡 Adicione seus arquivos de áudio na pasta para começar")
        
        # Cria arquivo de exemplo
        create_info_file(audio_folder)
    
    return audio_folder

def debug_timing(self):
    """Mostra informações detalhadas de timing."""
    print("\n" + "="*70)
    print("⏱️ DEBUG DE TIMING")
    print("="*70)
    
    now = datetime.now()
    
    # Info do fade
    if hasattr(self.queue_manager, 'fade_manager'):
        fade_duration = self.queue_manager.fade_manager.fade_duration
        print(f"Duração do fade: {fade_duration}s")
    
    # Info da fila
    items = self.queue_service.get_queue_items()
    for msg in sorted(items, key=lambda x: x.next_play_time):
        time_diff = (msg.next_play_time - now).total_seconds()
        
        print(f"\n{msg.filename}:")
        print(f"   Status: {'PENDENTE' if msg.is_pending else 'ATIVA'}")
        print(f"   Intervalo: {getattr(msg, 'interval_seconds', '?')}s")
        print(f"   Próxima: {msg.next_play_time.strftime('%H:%M:%S')}")
        
        if time_diff > 0:
            print(f"   Aguardar: {time_diff:.1f}s")
        else:
            print(f"   PRONTA! (atraso: {-time_diff:.1f}s)")
    
    print("\n" + "="*70)

def debug_intervals_detail(self):
        """Debug detalhado dos intervalos."""
        print("\n" + "="*70)
        print("🔍 DEBUG DETALHADO DE INTERVALOS")
        print("="*70)
        
        items = self.queue_service.get_queue_items()
        
        if not items:
            print("Fila vazia!")
            return
        
        for i, msg in enumerate(items):
            print(f"\n{i+1}. {msg.filename}")
            print(f"   Prioridade: {msg.priority}")
            print(f"   interval (minutos): {msg.interval}")
            print(f"   interval_seconds: {getattr(msg, 'interval_seconds', 'NÃO DEFINIDO')}")
            
            # Verifica se está correto
            expected = int(msg.interval * 60)
            actual = getattr(msg, 'interval_seconds', None)
            
            if actual != expected:
                print(f"   ⚠️ ERRO: Deveria ser {expected}s, mas está {actual}")
            else:
                print(f"   ✅ Correto: {actual} segundos")
            
            print(f"   Pendente: {msg.is_pending}")
            print(f"   Próxima execução: {msg.next_play_time.strftime('%H:%M:%S')}")
        
        print("\n" + "="*70)

def create_info_file(audio_folder):
    """
    Cria arquivo informativo na pasta AUDIO.
    
    Args:
        audio_folder (Path): Pasta AUDIO
    """
    try:
        info_file = audio_folder / "INSTRUCOES.txt"
        
        if not info_file.exists():
            from datetime import datetime
            
            info_content = f"""Sound Player Detel - PASTA DE ÁUDIO
===============================

📁 LOCALIZAÇÃO: {audio_folder}

🎵 FORMATOS SUPORTADOS:
   • MP3 (.mp3)
   • WAV (.wav)
   • AAC (.aac)
   • OGG (.ogg)
   • FLAC (.flac)
   • M4A (.m4a)

📋 COMO USAR:
   1. Copie seus arquivos de áudio para esta pasta
   2. Abra o Sound Player Detel
   3. Os arquivos aparecerão em "Mensagens Disponíveis"
   4. Use "🔄 Atualizar Lista" se adicionar arquivos com o programa aberto
   5. Adicione mensagens à fila de reprodução conforme necessário

💡 DICAS:
   • Use nomes descritivos para seus arquivos
   • Evite caracteres especiais nos nomes dos arquivos
   • Clique em "Abrir Pasta AUDIO" no aplicativo para acessar rapidamente

⚡ INÍCIO RÁPIDO:
   1. Coloque alguns arquivos .mp3 ou .wav nesta pasta
   2. Execute no PowerShell: python main.py
   3. Seus arquivos aparecerão automaticamente!

📂 ESTRUTURA DE PASTAS:
   RadioTeste/
   ├── main.py
   ├── AUDIO/          ← Seus arquivos de áudio aqui
   ├── config/         ← Configurações automáticas
   └── ui/             ← Arquivos da interface

Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Sound Player Detel v1.0
"""
            
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(info_content)
            print(f"📄 Arquivo de instruções criado: {info_file.name}")
            
    except Exception as e:
        print(f"⚠️ Erro ao criar arquivo de instruções: {str(e)}")
def show_queue_timeline(self):
    """Mostra visualmente a linha do tempo da fila."""
    items = self.queue_service.get_queue_items()
    if not items:
        print("Fila vazia")
        return
        
    print("\n" + "="*60)
    print("📅 LINHA DO TEMPO DA FILA")
    print("="*60)
    
    now = datetime.now()
    
    # Ordena por próximo horário de execução
    timeline = sorted(items, key=lambda x: x.next_play_time)
    
    for i, msg in enumerate(timeline):
        time_diff = (msg.next_play_time - now).total_seconds()
        status = "⏸️ PENDENTE" if msg.is_pending else "✅ ATIVA"
        
        print(f"\n{i+1}. {msg.filename} - {status}")
        print(f"   Prioridade: {msg.priority}")
        print(f"   Intervalo: {getattr(msg, 'interval_seconds', '?')}s")
        print(f"   Toca às: {msg.next_play_time.strftime('%H:%M:%S')}", end="")
        
        if time_diff > 0:
            print(f" (em {int(time_diff)}s)")
        else:
            print(f" (atrasada {int(-time_diff)}s)")
    
    print("\n" + "="*60)

def check_requirements():
    """
    Verifica se os requisitos básicos estão instalados.
    
    Returns:
        bool: True se tudo está OK
    """
    print("🔍 Verificando requisitos...")
    
    missing = []
    
    try:
        import PyQt6
        print("✅ PyQt6 - OK")
    except ImportError:
        missing.append("PyQt6")
        print("❌ PyQt6 - Não encontrado")
    
    try:
        import vlc
        print("✅ VLC - OK")
    except ImportError:
        missing.append("python-vlc")
        print("❌ VLC - Não encontrado")
    
    try:
        import pygame
        print("✅ Pygame - OK")
    except ImportError:
        missing.append("pygame")
        print("❌ Pygame - Não encontrado")
    
    try:
        import pyaudio
        print("✅ PyAudio - OK")
    except ImportError:
        missing.append("pyaudio")
        print("❌ PyAudio - Não encontrado")
    
    if missing:
        print(f"\n⚠️ Requisitos em falta: {', '.join(missing)}")
        print("Para instalar, execute no PowerShell:")
        for req in missing:
            print(f"   pip install {req}")
        print("\n💡 COMANDOS COMPLETOS:")
        print("   pip install PyQt6")
        print("   pip install python-vlc")
        print("   pip install pygame")
        print("   pip install pyaudio")
        return False
    else:
        print("✅ Todos os requisitos estão instalados!")
        return True

def show_windows_help():
    """
    Mostra ajuda específica para Windows.
    """
    print("\n" + "="*50)
    print("🪟 EXECUTANDO NO WINDOWS")
    print("="*50)
    print("Para executar este programa, use APENAS:")
    print("   python main.py")
    print("\nOu se não funcionar:")
    print("   py main.py")
    print("   python3 main.py")
    print("\n❌ NÃO use: /usr/bin/env python3")
    print("   (Isso é comando do Linux/Unix)")
    print("="*50)

def main():
    """
    Função principal simplificada.
    """
    print("=" * 60)
    print("🎵 SOUND PLAYER DETEL - SISTEMA DE RÁDIO COM MENSAGENS")
    print("=" * 60)
    print(f"📂 Pasta do projeto: {Path(__file__).parent}")
    print()
    
    # Mostra ajuda do Windows
    show_windows_help()
    
    try:
        # 1. Verificar requisitos
        print("\n" + "="*30)
        print("🔧 VERIFICAÇÃO DE REQUISITOS")
        print("="*30)
        
        if not check_requirements():
            print("\n❌ Instale os requisitos necessários antes de continuar.")
            print("\n📥 INSTALAÇÃO RÁPIDA:")
            print("Copie e cole no PowerShell:")
            print("pip install PyQt6 python-vlc pygame pyaudio")
            input("\nPressione Enter para sair...")
            return
        
        print("\n" + "="*30)
        print("📁 CONFIGURAÇÃO DE PASTAS")
        print("="*30)
        
        # 2. Configurar pasta AUDIO
        audio_folder = setup_audio_folder()
        
        print("\n" + "=" * 60)
        print("🚀 INICIANDO APLICATIVO...")
        print("=" * 60)
        
        # 3. Iniciar aplicação Qt
        app = QApplication(sys.argv)
        app.setApplicationName("Sound Player Detel")
        app.setApplicationVersion("1.0")
        
        # 4. Importar e criar janela principal
        try:
            from ui.main_window import RadioPlayerWindow
        except ImportError as e:
            print(f"❌ Erro ao importar interface: {str(e)}")
            print("\n🔍 Verifique se estes arquivos existem:")
            current_dir = Path(__file__).parent
            required_files = [
                "ui/main_window.py",
                "services/player_service.py", 
                "services/queue_service.py",
                "models/message_item.py"
            ]
            
            for file_path in required_files:
                full_path = current_dir / file_path
                status = "✅" if full_path.exists() else "❌"
                print(f"   {status} {file_path}")
            
            input("\nPressione Enter para sair...")
            return
        
        window = RadioPlayerWindow()
        window.setWindowTitle("🎵 Sound Player Detel")
        window.show()
        
        # 5. Mensagem de sucesso
        print("✅ Aplicativo iniciado com sucesso!")
        print(f"📁 Pasta de áudio: {audio_folder}")
        print("🎯 Interface gráfica aberta")
        print()
        print("Para sair: Feche a janela ou pressione Ctrl+C")
        print("=" * 60)
        
        # 6. Executar loop principal
        exit_code = app.exec()
        
        print("\n👋 Sound Player Detel encerrado. Até mais!")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Aplicativo interrompido pelo usuário")
        sys.exit(0)
        
    except ImportError as e:
        print(f"\n❌ Erro de importação: {str(e)}")
        print("\n🔍 Arquivos necessários não encontrados!")
        print("Certifique-se de que estes arquivos estão na pasta:")
        print("   - ui/main_window.py")
        print("   - services/player_service.py")
        print("   - services/queue_service.py")
        print("   - models/message_item.py")
        print("   - ui/dialogs.py")
        print("   - ui/radio_source_dialog.py")
        input("\nPressione Enter para sair...")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n💥 Erro inesperado: {str(e)}")
        
        # Tenta mostrar erro em janela se possível
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            QMessageBox.critical(
                None,
                "Erro do Sound Player Detel",
                f"Erro inesperado:\n\n{str(e)}\n\n"
                "Verifique o console para mais detalhes."
            )
        except:
            pass
        
        import traceback
        traceback.print_exc()
        input("\nPressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()