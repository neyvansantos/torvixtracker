# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import shutil
import subprocess
import sys
from pathlib import Path


def build() -> bool:
    print("Iniciando build do TorvixTracker...")

    project_root = Path(__file__).parent.parent
    for folder in (project_root / "build", project_root / "dist"):
        if folder.exists():
            print(f"Limpando {folder}...")
            shutil.rmtree(folder)

    main_script = project_root / "main.py"
    models_dir = project_root / "models"
    assets_dir = project_root / "assets"
    profiles_dir = project_root / "profiles"
    version_file = project_root / "version.json"
    output_dir = project_root / "dist" / "TorvixTracker"

    if not main_script.exists():
        print(f"ERRO: {main_script} nao encontrado!")
        return False

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onedir",
        "--name",
        "TorvixTracker",
        f"--add-data={models_dir};models",
        f"--add-data={assets_dir};assets",
        "--icon",
        str(assets_dir / "icon.ico"),
        "--collect-all",
        "mediapipe",
        "--collect-all",
        "PySide6",
        "--hidden-import",
        "mediapipe.python.solutions.face_mesh",
        "--hidden-import",
        "mediapipe.python.solutions.drawing_utils",
        "--hidden-import",
        "mediapipe.python.solutions.drawing_styles",
        str(main_script),
    ]

    print(f"Executando: {' '.join(command)}")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"ERRO no build: {exc}")
        return False

    if assets_dir.exists():
        shutil.copytree(assets_dir, output_dir / "assets", dirs_exist_ok=True)
    if models_dir.exists():
        shutil.copytree(models_dir, output_dir / "models", dirs_exist_ok=True)
    if profiles_dir.exists():
        shutil.copytree(profiles_dir, output_dir / "profiles", dirs_exist_ok=True)
    if version_file.exists():
        shutil.copy2(version_file, output_dir / "version.json")

    print("\n" + "=" * 30)
    print("BUILD CONCLUIDO COM SUCESSO!")
    print(f"Pasta do app: {output_dir}")
    print(f"Executavel: {output_dir / 'TorvixTracker.exe'}")
    print("=" * 30)
    return True


if __name__ == "__main__":
    raise SystemExit(0 if build() else 1)
