# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NPClientBridge:
    found: bool = False
    path: str = ""


def find_npclient_bridge() -> NPClientBridge:
    if os.name != "nt":
        return NPClientBridge()

    candidates = _registry_candidates()
    candidates.extend(_common_candidates())

    for candidate in candidates:
        dll_path = _normalize_candidate(candidate)
        if dll_path and dll_path.exists():
            return NPClientBridge(found=True, path=str(dll_path))

    return NPClientBridge()


def _registry_candidates() -> list[str]:
    try:
        import winreg
    except ImportError:
        return []

    keys = (
        (winreg.HKEY_CURRENT_USER, r"Software\NaturalPoint\NATURALPOINT\NPClient Location"),
        (winreg.HKEY_CURRENT_USER, r"Software\NaturalPoint\NATURALPOINT\NPClient"),
        (winreg.HKEY_CURRENT_USER, r"Software\Freetrack\FreetrackClient"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\NaturalPoint\NATURALPOINT\NPClient Location"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\NaturalPoint\NATURALPOINT\NPClient Location"),
    )

    candidates: list[str] = []
    for root, key_path in keys:
        try:
            with winreg.OpenKey(root, key_path) as key:
                for value_name in ("Path", ""):
                    try:
                        value, _value_type = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if isinstance(value, str) and value.strip():
                        candidates.append(value.strip())
        except OSError:
            continue
    return candidates


def _common_candidates() -> list[str]:
    return [
        r"C:\Program Files (x86)\opentrack\modules",
        r"C:\Program Files\opentrack\modules",
        r"C:\Program Files (x86)\TrackIR5",
        r"C:\Program Files (x86)\NaturalPoint\TrackIR5",
    ]


def _normalize_candidate(candidate: str) -> Path | None:
    path = Path(candidate.strip().strip('"')).expanduser()
    if path.name.lower() == "npclient64.dll":
        return path
    return path / "NPClient64.dll"
