# -*- coding: utf-8 -*-

"""
Aplicativo de Reprodução de Rádio com Fila de Mensagens
Ponto de entrada principal do aplicativo.
"""

import sys  
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from ui.main_window import RadioPlayerWindow

def ensure_app_directories():
    """
    Garante que todos os diretórios necessários para o aplicativo existam.
    """
    # Diretório base do aplicativo (onde o usuário está executando)
    base_dir = Path(os.path.expanduser(
        r"C:\Users\mathe\OneDrive\Área de Trabalho\radio"
    ))
    
    # Diretórios necessários
    dirs = [
        base_dir / "mensagens",  # Para arquivos de áudio
        base_dir / "config",     # Para arquivos de configuração
        base_dir / "logs"        # Para logs (opcional, para futuras expansões)
    ]
    
    # Cria todos os diretórios
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Diretório verificado: {dir_path}")
    
    return base_dir

def main():
    """Função principal do aplicativo."""
    # Garante que os diretórios existam
    app_dir = ensure_app_directories()
    
    # Inicia a aplicação Qt
    app = QApplication(sys.argv)
    
    # Configuração de estilo global
    style_path = Path(__file__).parent / "resources" / "style.qss"
    if style_path.exists():
        with open(style_path, "r") as style_file:
            app.setStyleSheet(style_file.read())
    
    # Cria e exibe a janela principal
    window = RadioPlayerWindow()
    window.show()
    
    # Executa o loop principal da aplicação
    sys.exit(app.exec())

if __name__ == "__main__":
    main()