# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

import json
from pathlib import Path

from eye_drive_tracker import __app_name__, __version__

from .profile import TrackingConfig
from .viewtracker import import_viewtracker_ini


class ProfileManager:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "profiles"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def default_path(self, name: str = "profile") -> Path:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name).strip("_")
        return self.base_dir / f"{safe or 'profile'}.json"

    def save(self, path: str | Path, config: TrackingConfig, name: str | None = None) -> None:
        profile_name = name or config.profile_name or Path(path).stem
        payload = {
            "app": __app_name__,
            "version": __version__,
            "name": profile_name,
            "config": config.to_dict(),
        }
        payload["config"]["profile_name"] = profile_name
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: str | Path) -> TrackingConfig:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if "config" in payload:
            data = dict(payload["config"])
            data.setdefault("profile_name", payload.get("name", Path(path).stem))
            return TrackingConfig.from_dict(data)
        return TrackingConfig.from_dict(payload)

    def import_viewtracker_ini(self, path: str | Path, base_config: TrackingConfig | None = None) -> TrackingConfig:
        return import_viewtracker_ini(path, base_config)
