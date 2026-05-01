# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import os
import sys
import subprocess
import shutil
from pathlib import Path

def build():
    print("Iniciando build do TorvixTracker...")
    
    # 1. Limpar pastas de build anteriores
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"Limpando {folder}...")
            shutil.rmtree(folder)
            
    # 2. Definir caminhos
    project_root = Path(__file__).parent.parent
    main_script = project_root / "main.py"
    models_dir = project_root / "models"
    assets_dir = project_root / "assets"
    
    if not main_script.exists():
        print(f"ERRO: {main_script} não encontrado!")
        return

    # 3. Montar comando do PyInstaller
    # --collect-all mediapipe: garante que todas as DLLs e dados do mediapipe sejam incluídos
    # --add-data "models;models": inclui a pasta de modelos
    # --noconsole: não abre janela de terminal ao rodar o .exe
    # --onefile: empacota tudo em um único .exe (opcional, mas o usuário prefere)
    
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "TorvixTracker",
        f"--add-data={models_dir};models",
        f"--add-data={assets_dir};assets",
        "--icon", "assets/icon.ico",
        "--collect-all", "mediapipe",
        "--collect-all", "PySide6",
        "--hidden-import", "mediapipe.python.solutions.face_mesh",
        "--hidden-import", "mediapipe.python.solutions.drawing_utils",
        "--hidden-import", "mediapipe.python.solutions.drawing_styles",
        str(main_script)
    ]
    
    print(f"Executando: {' '.join(command)}")
    
    try:
        subprocess.run(command, check=True)
        print("\n" + "="*30)
        print("BUILD CONCLUÍDO COM SUCESSO!")
        print(f"O executável está em: {project_root / 'dist' / 'TorvixTracker.exe'}")
        print("="*30)
    except subprocess.CalledProcessError as e:
        print(f"ERRO no build: {e}")

if __name__ == "__main__":
    build()
