# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cv2
import numpy as np

from .head_pose import HeadPoseTracker
from .models import TrackingResult


@dataclass
class AsyncTrackingResult:
    result: TrackingResult
    scale_x: float
    scale_y: float
    backend_name: str
    processing_ms: float = 0.0
    tracking_fps: float = 0.0
    dropped_frames: int = 0


_PERFORMANCE_LOGGER: logging.Logger | None = None


def _performance_logger() -> logging.Logger:
    global _PERFORMANCE_LOGGER
    if _PERFORMANCE_LOGGER is not None:
        return _PERFORMANCE_LOGGER

    logger = logging.getLogger("eye_drive_tracker.tracking.performance")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        log_path = Path(os.environ.get("TORVIX_TRACKING_LOG", "logs/tracking_performance.log"))
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        except OSError:
            logger.addHandler(logging.NullHandler())
    _PERFORMANCE_LOGGER = logger
    return logger


class AsyncHeadPoseWorker:
    def __init__(self) -> None:
        self.backend_name = "Starting tracker"
        self._condition = threading.Condition()
        self._thread: threading.Thread | None = None
        self._running = False
        self._processing = False
        self._pending_frame: np.ndarray | None = None
        self._pending_max_width: int = 0
        self._latest_result: AsyncTrackingResult | None = None
        self._dropped_frames = 0
        self._tracking_fps = 0.0
        self._last_completed_at = 0.0
        self._last_perf_log_at = 0.0

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        with self._condition:
            self.backend_name = "Starting tracker"
            self._running = True
            self._processing = False
            self._pending_frame = None
            self._latest_result = None
            self._dropped_frames = 0
            self._tracking_fps = 0.0
            self._last_completed_at = 0.0
            self._last_perf_log_at = 0.0
        self._thread = threading.Thread(target=self._run, name="TorvixHeadPoseWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._condition:
            self._running = False
            self._processing = False
            self._pending_frame = None
            self._latest_result = None
            self._condition.notify_all()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def wants_frame(self) -> bool:
        with self._condition:
            return self._running

    def submit(self, frame: np.ndarray, max_width: int = 0) -> bool:
        with self._condition:
            if not self._running:
                return False
            if self._pending_frame is not None:
                self._dropped_frames += 1
            self._pending_frame = frame
            self._pending_max_width = max_width
            self._condition.notify()
            return True

    def take_result(self) -> AsyncTrackingResult | None:
        with self._condition:
            result = self._latest_result
            self._latest_result = None
            return result

    def _run(self) -> None:
        tracker = HeadPoseTracker()
        with self._condition:
            self.backend_name = tracker.backend_name

        try:
            while True:
                with self._condition:
                    while self._running and self._pending_frame is None:
                        self._condition.wait()
                    if not self._running:
                        break
                    frame = self._pending_frame
                    max_width = self._pending_max_width
                    self._pending_frame = None
                    self._processing = True

                if frame is None:
                    continue

                detection_frame, scale_x, scale_y = self._resize_for_detection(frame, max_width)
                started_at = time.monotonic()
                result = tracker.detect(detection_frame)
                completed_at = time.monotonic()
                processing_ms = (completed_at - started_at) * 1000.0
                if self._last_completed_at > 0.0:
                    instant_fps = 1.0 / max(completed_at - self._last_completed_at, 1e-3)
                    self._tracking_fps = (
                        instant_fps
                        if self._tracking_fps <= 0.0
                        else (self._tracking_fps * 0.85) + (instant_fps * 0.15)
                    )
                self._last_completed_at = completed_at
                with self._condition:
                    self._processing = False
                    self.backend_name = tracker.backend_name
                    dropped_frames = self._dropped_frames
                    result.processing_ms = processing_ms
                    result.tracking_fps = self._tracking_fps
                    result.dropped_frames = dropped_frames
                    self._latest_result = AsyncTrackingResult(
                        result=result,
                        scale_x=scale_x,
                        scale_y=scale_y,
                        backend_name=tracker.backend_name,
                        processing_ms=processing_ms,
                        tracking_fps=self._tracking_fps,
                        dropped_frames=dropped_frames,
                    )
                self._log_performance(tracker.backend_name, processing_ms, self._tracking_fps, dropped_frames)
        finally:
            with self._condition:
                self._processing = False
            tracker.close()

    def _log_performance(
        self,
        backend_name: str,
        processing_ms: float,
        tracking_fps: float,
        dropped_frames: int,
    ) -> None:
        now = time.monotonic()
        if now - self._last_perf_log_at < 3.0:
            return
        self._last_perf_log_at = now
        _performance_logger().info(
            "backend=%s tracking_fps=%.2f processing_ms=%.2f dropped_frames=%d",
            backend_name,
            tracking_fps,
            processing_ms,
            dropped_frames,
        )

    @staticmethod
    def _resize_for_detection(
        frame: np.ndarray, max_width: int
    ) -> tuple[np.ndarray, float, float]:
        height, width = frame.shape[:2]
        if max_width <= 0 or width <= max_width:
            return frame, 1.0, 1.0
        scale = max_width / max(width, 1)
        target_width = max_width
        target_height = max(1, int(round(height * scale)))
        resized = cv2.resize(
            frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR
        )
        return resized, width / target_width, height / target_height
