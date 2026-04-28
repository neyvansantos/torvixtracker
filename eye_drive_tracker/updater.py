import json
import urllib.request
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
                
                latest_version = data.get("version", "0.0.0")
                has_update = self._is_newer(latest_version, self.current_version)
                
                result = {
                    "success": True,
                    "has_update": has_update,
                    "latest_version": latest_version,
                    "download_url": data.get("download_url", ""),
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
