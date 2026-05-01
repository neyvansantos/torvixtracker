# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

import socket
import struct

from eye_drive_tracker.tracking.models import PoseSample


class OpenTrackUdpOutput:
    _ADDRESS = ("127.0.0.1", 4242)
    _PACKET = struct.Struct("<6d")

    def __init__(self) -> None:
        self.running = False
        self._socket: socket.socket | None = None

    def start(self) -> str:
        self.stop()
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except OSError as exc:
            self.running = False
            return f"OpenTrack UDP failed: {exc}"
        self.running = True
        return "OpenTrack UDP active"

    def stop(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._socket = None
        self.running = False

    def send(self, pose: PoseSample) -> str:
        if not self.running or self._socket is None:
            return "Stopped"

        packet = self._PACKET.pack(
            float(pose.x),
            float(pose.y),
            float(pose.z),
            float(pose.yaw),
            float(pose.pitch),
            float(pose.roll),
        )
        try:
            self._socket.sendto(packet, self._ADDRESS)
        except OSError as exc:
            return f"OpenTrack UDP failed: {exc}"
        return "OpenTrack UDP active"
