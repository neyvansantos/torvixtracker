# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

import ctypes
import os

from eye_drive_tracker.tracking.models import PoseSample


class MouseLookOutput:
    _PIXELS_PER_DEGREE = 2.0
    _MAX_PIXELS_PER_TICK = 24

    def __init__(self) -> None:
        self.running = False
        self.previous = PoseSample()
        self._residual_x = 0.0
        self._residual_y = 0.0

    def start(self) -> str:
        if os.name != "nt":
            self.running = False
            return "Mouse Look fallback is Windows-only"
        self.running = True
        self.previous = PoseSample()
        self._residual_x = 0.0
        self._residual_y = 0.0
        return "Mouse Look fallback active"

    def stop(self) -> None:
        self.running = False
        self.previous = PoseSample()
        self._residual_x = 0.0
        self._residual_y = 0.0

    def send(self, pose: PoseSample) -> str:
        if not self.running:
            return "Stopped"
        dx_float = ((pose.yaw - self.previous.yaw) * self._PIXELS_PER_DEGREE) + self._residual_x
        dy_float = ((pose.pitch - self.previous.pitch) * self._PIXELS_PER_DEGREE) + self._residual_y
        dx = self._bounded_pixel_delta(dx_float)
        dy = self._bounded_pixel_delta(dy_float)
        self._residual_x = dx_float - dx
        self._residual_y = dy_float - dy
        self.previous = PoseSample(
            yaw=pose.yaw, pitch=pose.pitch, roll=pose.roll,
            x=pose.x, y=pose.y, z=pose.z,
        )
        if dx or dy:
            ctypes.windll.user32.mouse_event(0x0001, dx, dy, 0, 0)
        return "Mouse Look fallback active"

    @classmethod
    def _bounded_pixel_delta(cls, value: float) -> int:
        delta = int(round(value))
        return max(-cls._MAX_PIXELS_PER_TICK, min(cls._MAX_PIXELS_PER_TICK, delta))
