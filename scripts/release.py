import sys
import json
import subprocess
from pathlib import Path

def update_version_in_init(new_version):
    init_path = Path(__file__).parent.parent / "eye_drive_tracker/__init__.py"
    if not init_path.exists():
        print(f"Erro: {init_path} não encontrado!")
        return False
    
    lines = init_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("__version__ ="):
            new_lines.append(f'__version__ = "{new_version}"')
        else:
            new_lines.append(line)
    
    init_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[OK] Versao atualizada no {init_path} para {new_version}")
    return True

def update_version_json(new_version, changelog):
    json_path = Path(__file__).parent.parent / "version.json"
    if not json_path.exists():
        print(f"Erro: {json_path} não encontrado!")
        return False
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['version'] = new_version
    data['changelog'] = changelog
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] version.json atualizado para {new_version}")
    return True

def run_build():
    print("Iniciando build do executavel...")
    try:
        # Usa o python do venv se disponível, senão o global
        python_exe = sys.executable
        build_script = Path(__file__).parent / "build_exe.py"
        subprocess.run([python_exe, str(build_script)], check=True)
        return True
    except Exception as e:
        print(f"[ERRO] Erro durante o build: {e}")
        return False

def run_installer_build():
    print("Criando instalador do Windows...")
    try:
        python_exe = sys.executable
        installer_script = Path(__file__).parent / "build_installer.py"
        subprocess.run([python_exe, str(installer_script)], check=True)
        return True
    except Exception as e:
        print(f"Aviso: Nao foi possivel criar o instalador. Certifique-se de que o Inno Setup esta instalado.")
        return True # Não trava o release se o instalador falhar

def git_sync(version):
    print("Sincronizando com GitHub...")
    root_dir = Path(__file__).parent.parent
    try:
        subprocess.run(["git", "add", "."], check=True, cwd=str(root_dir))
        subprocess.run(["git", "commit", "-m", f"Release {version}"], check=True, cwd=str(root_dir))
        subprocess.run(["git", "push"], check=True, cwd=str(root_dir))
        print("[OK] Codigo enviado para o GitHub com sucesso!")
        return True
    except Exception as e:
        print(f"[ERRO] Erro no Git: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Uso: python release.py <versao> \"<changelog>\"")
        print("Exemplo: python release.py 0.1.2 \"Melhoria no rastreamento\"")
        return

    version = sys.argv[1]
    changelog = sys.argv[2]

    print(f"\n--- INICIANDO RELEASE {version} ---")
    
    if not update_version_in_init(version):
        return
    if not update_version_json(version, changelog):
        return
    if not run_build():
        return
    if not run_installer_build():
        return
    if not git_sync(version):
        return

    print("\n" + "="*40)
    print(f"RELEASE {version} CONCLUIDA!")
    print("O executavel esta em /dist e o GitHub esta atualizado.")
    print("="*40)

if __name__ == "__main__":
    main()
