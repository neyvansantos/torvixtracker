# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

import math
import mmap
import os
import struct
from dataclasses import dataclass

from eye_drive_tracker.tracking.models import PoseSample


@dataclass
class FreeTrackState:
    active: bool = False
    status: str = "Stopped"
    frame_id: int = 0


class FreeTrackOutput:
    _STRUCT = struct.Struct("<iii20fi8si")
    _MAP_NAMES = ("FT_SharedMem", "FreeTrackSharedMem")

    def __init__(self) -> None:
        self.state = FreeTrackState()
        self._maps: list[mmap.mmap] = []
        self._payload = bytearray(self._STRUCT.size)

    def start(self) -> str:
        self.stop()
        if os.name != "nt":
            self.state = FreeTrackState(active=False, status="FreeTrack output is Windows-only")
            return self.state.status

        try:
            self._maps = [
                mmap.mmap(-1, self._STRUCT.size, tagname=name, access=mmap.ACCESS_WRITE)
                for name in self._MAP_NAMES
            ]
        except Exception as exc:
            self.stop()
            self.state = FreeTrackState(active=False, status=f"FreeTrack shared memory failed: {exc}")
            return self.state.status

        self.state.active = True
        self.state.status = "FreeTrack shared memory active"
        return self.state.status

    def stop(self) -> None:
        for memory in self._maps:
            try:
                memory.close()
            except Exception:
                pass
        self._maps = []
        self.state.active = False
        self.state.status = "Stopped"

    def send(self, pose: PoseSample, raw_pose: PoseSample | None = None) -> str:
        if not self.state.active:
            return self.state.status

        raw_pose = raw_pose or pose
        self.state.frame_id = (self.state.frame_id + 1) & 0x7FFFFFFF
        self._pack_pose(pose, raw_pose)

        try:
            for memory in self._maps:
                memory.seek(0)
                memory.write(self._payload)
        except Exception as exc:
            self.state.status = f"FreeTrack write failed: {exc}"
            return self.state.status

        self.state.status = "FreeTrack shared memory active"
        return self.state.status

    def _pack_pose(self, pose: PoseSample, raw_pose: PoseSample) -> None:
        yaw = self._yaw_to_radians(pose.yaw)
        pitch = self._pitch_to_radians(pose.pitch)
        roll = self._roll_to_radians(pose.roll)
        x = self._cm_to_mm(pose.x)
        y = self._cm_to_mm(pose.y)
        z = self._cm_to_mm(pose.z)
        raw_yaw = self._yaw_to_radians(raw_pose.yaw)
        raw_pitch = self._pitch_to_radians(raw_pose.pitch)
        raw_roll = self._roll_to_radians(raw_pose.roll)
        raw_x = self._cm_to_mm(raw_pose.x)
        raw_y = self._cm_to_mm(raw_pose.y)
        raw_z = self._cm_to_mm(raw_pose.z)

        floats = (
            yaw,
            pitch,
            roll,
            x,
            y,
            z,
            raw_yaw,
            raw_pitch,
            raw_roll,
            raw_x,
            raw_y,
            raw_z,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
        self._STRUCT.pack_into(
            self._payload,
            0,
            self.state.frame_id,
            640,
            480,
            *floats,
            0,
            b"\x00" * 8,
            0,
        )

    @staticmethod
    def _yaw_to_radians(value: float) -> float:
        return math.radians(value)

    @staticmethod
    def _pitch_to_radians(value: float) -> float:
        return -math.radians(value)

    @staticmethod
    def _roll_to_radians(value: float) -> float:
        return math.radians(value)

    @staticmethod
    def _cm_to_mm(value: float) -> float:
        return float(value) * 10.0
