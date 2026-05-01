# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import os
import subprocess
import json
from pathlib import Path

def get_version():
    json_path = Path(__file__).parent.parent / "version.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("version", "0.1.0")

def update_iss_version(version):
    iss_path = Path(__file__).parent / "installer.iss"
    lines = iss_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.startswith('#define AppVersion'):
            new_lines.append(f'#define AppVersion "{version}"')
        else:
            new_lines.append(line)
    iss_path.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"[OK] Versao no instalador.iss atualizada para {version}")

def find_iscc():
    # Caminhos comuns do Inno Setup
    common_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        "ISCC.exe" # Se estiver no PATH
    ]
    
    for path in common_paths:
        if os.path.exists(path) or subprocess.run(["where", "ISCC.exe"], capture_output=True).returncode == 0:
            return path
    return None

def build_installer():
    version = get_version()
    update_iss_version(version)
    
    iscc_path = find_iscc()
    if not iscc_path:
        print("[ERRO] Inno Setup (ISCC.exe) nao encontrado!")
        print("Por favor, instale o Inno Setup 6: https://jrsoftware.org/isdl.php")
        return False
    
    print(f"Iniciando compilacao do instalador com {iscc_path}...")
    iss_file = Path(__file__).parent / "installer.iss"
    
    try:
        subprocess.run([iscc_path, str(iss_file)], check=True)
        print("\n" + "="*40)
        print("INSTALADOR CRIADO COM SUCESSO!")
        print("Arquivo: dist/TorvixTracker_Setup.exe")
        print("="*40)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao compilar instalador: {e}")
        return False

if __name__ == "__main__":
    build_installer()
