# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

from dataclasses import dataclass

import cv2
from PySide6.QtMultimedia import QMediaDevices


@dataclass(frozen=True)
class CameraDevice:
    index: int
    name: str


@dataclass(frozen=True)
class CameraResolution:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width} x {self.height}"


@dataclass(frozen=True)
class CameraMode:
    width: int
    height: int
    fps: float


_camera_modes_cache: dict[int, list[CameraMode]] = {}

class CameraEnumerator:
    @staticmethod
    def list_cameras() -> list[CameraDevice]:
        devices: list[CameraDevice] = []
        try:
            # Usar QMediaDevices para obter nomes reais
            qt_cameras = QMediaDevices.videoInputs()
            for index, camera in enumerate(qt_cameras):
                name = camera.description()
                if not name:
                    name = f"Webcam {index}"
                # Remover o prefixo do índice se o nome já for descritivo
                devices.append(CameraDevice(index=index, name=name))
                
            if not devices:
                # Fallback direto via OpenCV para garantir que ao menos uma apareça se conectada
                for i in range(3):
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        devices.append(CameraDevice(index=i, name=f"Webcam {i}"))
                        cap.release()
            return devices
        except Exception:
            return [CameraDevice(index=0, name="Webcam 0")]

    @staticmethod
    def list_resolutions(index: int) -> list[CameraResolution]:
        found: dict[tuple[int, int], CameraResolution] = {}
        for mode in CameraEnumerator.list_modes(index):
            if mode.width > 0 and mode.height > 0:
                found[(mode.width, mode.height)] = CameraResolution(mode.width, mode.height)
        return sorted(found.values(), key=lambda item: (item.width * item.height, item.width))

    @staticmethod
    def list_fps(index: int, width: int = 0, height: int = 0) -> list[float]:
        found: set[float] = set()
        for mode in CameraEnumerator.list_modes(index):
            if width > 0 and height > 0 and (mode.width != width or mode.height != height):
                continue
            if mode.fps > 0:
                found.add(round(float(mode.fps), 2))
        return sorted(found)

    @staticmethod
    def list_modes(index: int) -> list[CameraMode]:
        if index in _camera_modes_cache:
            return _camera_modes_cache[index]
            
        modes = []
        try:
            qt_cameras = QMediaDevices.videoInputs()
            if 0 <= index < len(qt_cameras):
                camera = qt_cameras[index]
                found: set[tuple[int, int, float]] = set()
                for fmt in camera.videoFormats():
                    res = fmt.resolution()
                    width, height = res.width(), res.height()
                    fps = fmt.maxFrameRate()
                    if width > 0 and height > 0 and fps > 0:
                        found.add((width, height, round(float(fps), 2)))
                modes = [CameraMode(w, h, f) for w, h, f in sorted(found)]
        except Exception:
            pass
            
        if not modes:
            # Fallback
            current = _current_camera_mode(index)
            modes = [current] if current else []
            
        _camera_modes_cache[index] = modes
        return modes


def _current_camera_mode(index: int) -> CameraMode | None:
    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not capture.isOpened():
        capture.release()
        capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        return None
    width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
    height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    capture.release()
    if width <= 0 or height <= 0:
        return None
    return CameraMode(width=width, height=height, fps=round(fps, 2))
