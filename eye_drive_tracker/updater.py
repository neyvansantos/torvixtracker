import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal


class UpdateChecker(QThread):
    """
    Thread para verificar atualizações sem travar a UI.
    """
    finished = Signal(dict)  # Retorna o resultado (dict com dados da atualização ou erro)

    def __init__(self, current_version: str, update_url: str):
        super().__init__()
        self.current_version = current_version
        self.update_url = update_url

    def run(self):
        try:
            # Tenta baixar o arquivo de versão
            with urllib.request.urlopen(self.update_url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                latest_version = str(data.get("version", "0.0.0")).strip()
                has_update = self._is_newer(latest_version, self.current_version)
                download_url = str(data.get("download_url", "")).strip()

                result = {
                    "success": True,
                    "has_update": has_update,
                    "latest_version": latest_version,
                    "download_url": download_url,
                    "changelog": data.get("changelog", "")
                }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        self.finished.emit(result)

    def _is_newer(self, latest: str, current: str) -> bool:
        """Compara versões semânticas simples (ex: 1.2.3 > 1.2.0)"""
        try:
            l_parts = [int(p) for p in latest.split(".")]
            c_parts = [int(p) for p in current.split(".")]
            
            # Pad com zeros se as versões tiverem tamanhos diferentes
            max_len = max(len(l_parts), len(c_parts))
            l_parts += [0] * (max_len - len(l_parts))
            c_parts += [0] * (max_len - len(c_parts))
            
            return l_parts > c_parts
        except Exception:
            # Fallback para comparação de string se o formato for estranho
            return latest > current


class UpdateInstallerDownloader(QThread):
    """
    Baixa o instalador de atualizacao sem travar a UI.
    """

    finished = Signal(dict)

    def __init__(self, download_url: str, version: str):
        super().__init__()
        self.download_url = download_url
        self.version = version

    def run(self):
        try:
            target = update_installer_path(self.download_url, self.version)
            target.parent.mkdir(parents=True, exist_ok=True)

            request = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "TorvixTracker-Updater"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                with target.open("wb") as file:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        file.write(chunk)

            if target.stat().st_size <= 0:
                raise OSError("Downloaded installer is empty")

            self.finished.emit({"success": True, "installer_path": str(target)})
        except Exception as exc:
            self.finished.emit({"success": False, "error": str(exc)})


def update_installer_path(download_url: str, version: str) -> Path:
    safe_version = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(version).strip() or "latest")
    parsed = urlparse(download_url)
    name = Path(parsed.path).name
    suffix = Path(name).suffix if Path(name).suffix.lower() == ".exe" else ".exe"
    return Path(tempfile.gettempdir()) / "TorvixTrackerUpdates" / f"TorvixTracker_Setup_{safe_version}{suffix}"


def launch_update_installer(installer_path: str | Path) -> None:
    path = Path(installer_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    subprocess.Popen([str(path), "/CLOSEAPPLICATIONS"], close_fds=True)
