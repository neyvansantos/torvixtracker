import os
import sys
import json
import subprocess
from pathlib import Path

def update_version_in_init(new_version):
    init_path = Path("eye_drive_tracker/__init__.py")
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
    print(f"✅ Versão atualizada no {init_path} para {new_version}")
    return True

def update_version_json(new_version, changelog):
    json_path = Path("version.json")
    if not json_path.exists():
        print(f"Erro: {json_path} não encontrado!")
        return False
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['version'] = new_version
    data['changelog'] = changelog
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ version.json atualizado para {new_version}")
    return True

def run_build():
    print("🚀 Iniciando build do executável...")
    try:
        # Usa o python do venv se disponível, senão o global
        python_exe = sys.executable
        subprocess.run([python_exe, "build_exe.py"], check=True)
        return True
    except Exception as e:
        print(f"❌ Erro durante o build: {e}")
        return False

def git_sync(version):
    print("📡 Sincronizando com GitHub...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Release {version}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"✅ Código enviado para o GitHub com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro no Git: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Uso: python release.py <versao> \"<changelog>\"")
        print("Exemplo: python release.py 0.1.2 \"Melhoria no rastreamento\"")
        return

    version = sys.argv[1]
    changelog = sys.argv[2]

    print(f"\n--- INICIANDO RELEASE {version} ---")
    
    if not update_version_in_init(version): return
    if not update_version_json(version, changelog): return
    if not run_build(): return
    if not git_sync(version): return

    print("\n" + "="*40)
    print(f"🎉 RELEASE {version} CONCLUÍDA!")
    print("O executável está em /dist e o GitHub está atualizado.")
    print("="*40)

if __name__ == "__main__":
    main()
