# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class CameraInfo:
    index: int
    name: str


@dataclass(frozen=True)
class CameraRuntimeSettings:
    width: int = 0
    height: int = 0
    fps: float = 0.0
    fourcc: str = "----"

    @property
    def label(self) -> str:
        resolution = f"{self.width}x{self.height}" if self.width > 0 and self.height > 0 else "Auto"
        fps = f"{self.fps:.2f} FPS" if self.fps > 0 else "Auto FPS"
        codec = self.fourcc if self.fourcc.strip("-") else "unknown"
        return f"{resolution} @ {fps} ({codec})"


class Webcam:
    def __init__(self) -> None:
        self._capture: Optional[cv2.VideoCapture] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_running = False
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_frame_id = 0
        self._state_lock = threading.Lock()
        self._frame_ready = threading.Condition(self._state_lock)
        self.index = 0

    @property
    def is_open(self) -> bool:
        with self._state_lock:
            return bool(self._capture and self._capture.isOpened())

    def open(
        self,
        index: int = 0,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
    ) -> bool:
        self.release()
        self.index = int(index)
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, 0):
            capture = cv2.VideoCapture(self.index, backend) if backend else cv2.VideoCapture(self.index)
            if not capture.isOpened():
                capture.release()
                continue

            self._configure_capture(capture, width, height, fps)
            with self._state_lock:
                self._capture = capture
                self._latest_frame = None
                self._latest_frame_id = 0
            self._start_reader()
            self._wait_for_first_frame(timeout=0.8)
            return True

        with self._state_lock:
            self._capture = None
        return False

    def read(self):
        ok, frame, _frame_id = self.read_with_id()
        return ok, frame

    def read_with_id(self):
        with self._state_lock:
            if self._latest_frame is None:
                return False, None, self._latest_frame_id
            return True, self._latest_frame, self._latest_frame_id

    def actual_settings(self) -> CameraRuntimeSettings:
        with self._state_lock:
            capture = self._capture
            if capture is None or not capture.isOpened():
                return CameraRuntimeSettings()
            width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0))
            height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0))
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            fourcc = _decode_fourcc(capture.get(cv2.CAP_PROP_FOURCC) or 0)
        return CameraRuntimeSettings(width=width, height=height, fps=fps, fourcc=fourcc)

    def release(self) -> None:
        self._stop_reader()
        with self._state_lock:
            capture = self._capture
            self._capture = None
            self._latest_frame = None
            self._latest_frame_id = 0
        if capture:
            capture.release()

    def __enter__(self) -> "Webcam":
        self.open(self.index)
        return self

    def __exit__(self, *_exc) -> None:
        self.release()

    def _start_reader(self) -> None:
        with self._state_lock:
            if self._reader_thread is not None and self._reader_thread.is_alive():
                return
            self._reader_running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, name="TorvixCameraReader", daemon=True)
        self._reader_thread.start()

    def _stop_reader(self) -> None:
        thread = None
        with self._state_lock:
            self._reader_running = False
            self._frame_ready.notify_all()
            thread = self._reader_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
        with self._state_lock:
            self._reader_thread = None

    def _wait_for_first_frame(self, timeout: float) -> None:
        deadline = time.monotonic() + max(timeout, 0.0)
        with self._state_lock:
            while self._reader_running and self._latest_frame is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._frame_ready.wait(timeout=remaining)

    def _reader_loop(self) -> None:
        while True:
            with self._state_lock:
                capture = self._capture
                running = self._reader_running and capture is not None and capture.isOpened()
            if not running or capture is None:
                return

            try:
                ok, frame = capture.read()
            except Exception:
                return
            if not ok or frame is None:
                time.sleep(0.002)
                continue

            with self._state_lock:
                if not self._reader_running:
                    return
                self._latest_frame = frame
                self._latest_frame_id += 1
                self._frame_ready.notify_all()

    @staticmethod
    def _configure_capture(
        capture: cv2.VideoCapture,
        width: int | None,
        height: int | None,
        fps: float | None,
    ) -> None:
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        if width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        if height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        if fps:
            capture.set(cv2.CAP_PROP_FPS, float(fps))
        capture.set(cv2.CAP_PROP_CONVERT_RGB, 1)


def _decode_fourcc(value: float) -> str:
    code = int(round(value))
    if code <= 0:
        return "----"
    chars = []
    for shift in (0, 8, 16, 24):
        char_code = (code >> shift) & 0xFF
        chars.append(chr(char_code) if 32 <= char_code <= 126 else "-")
    return "".join(chars)
