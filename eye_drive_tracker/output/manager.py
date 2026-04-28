from __future__ import annotations

import math
import time
from enum import Enum

from eye_drive_tracker.tracking.models import PoseSample

from .freetrack import FreeTrackOutput
from .mouse_look import MouseLookOutput
from .npclient import find_npclient_bridge


class OutputMode(str, Enum):
    FREETRACK = "freetrack"
    TRACKIR = "trackir"
    VJOY = "vjoy"
    MOUSE_LOOK = "mouse_look"


OUTPUT_MODE_LABELS = {
    OutputMode.FREETRACK: "FreeTrack",
    OutputMode.TRACKIR: "TrackIR compatible",
    OutputMode.VJOY: "vJoy",
    OutputMode.MOUSE_LOOK: "Mouse Look fallback",
}


def _copy_pose(pose: PoseSample | None) -> PoseSample:
    if pose is None:
        return PoseSample()
    return PoseSample(
        yaw=pose.yaw,
        pitch=pose.pitch,
        roll=pose.roll,
        x=pose.x,
        y=pose.y,
        z=pose.z,
    )


def _blend_pose(current: PoseSample, target: PoseSample, alpha: float) -> PoseSample:
    return PoseSample(
        yaw=current.yaw + (target.yaw - current.yaw) * alpha,
        pitch=current.pitch + (target.pitch - current.pitch) * alpha,
        roll=current.roll + (target.roll - current.roll) * alpha,
        x=current.x + (target.x - current.x) * alpha,
        y=current.y + (target.y - current.y) * alpha,
        z=current.z + (target.z - current.z) * alpha,
    )


def _velocity_pose(current: PoseSample, previous: PoseSample, delta_seconds: float) -> PoseSample:
    safe_delta = max(float(delta_seconds), 1e-3)
    return PoseSample(
        yaw=(current.yaw - previous.yaw) / safe_delta,
        pitch=(current.pitch - previous.pitch) / safe_delta,
        roll=(current.roll - previous.roll) / safe_delta,
        x=(current.x - previous.x) / safe_delta,
        y=(current.y - previous.y) / safe_delta,
        z=(current.z - previous.z) / safe_delta,
    )


def _project_pose(pose: PoseSample, velocity: PoseSample, lead_seconds: float) -> PoseSample:
    lead = max(0.0, float(lead_seconds))

    def projected(value: float, axis_velocity: float, max_extra: float) -> float:
        extra = max(-max_extra, min(axis_velocity * lead, max_extra))
        return value + extra

    return PoseSample(
        yaw=projected(pose.yaw, velocity.yaw, 2.8),
        pitch=projected(pose.pitch, velocity.pitch, 2.8),
        roll=projected(pose.roll, velocity.roll, 2.0),
        x=projected(pose.x, velocity.x, 0.8),
        y=projected(pose.y, velocity.y, 0.8),
        z=projected(pose.z, velocity.z, 1.0),
    )


def sendOutputToGame(
    pose: PoseSample,
    mode: str | OutputMode,
    running: bool,
    freetrack_backend: FreeTrackOutput | None = None,
    mouse_backend: MouseLookOutput | None = None,
    raw_pose: PoseSample | None = None,
    trackir_status: str | None = None,
) -> str:
    if not running:
        return "Stopped"

    try:
        selected_mode = OutputMode(mode)
    except ValueError:
        selected_mode = OutputMode.FREETRACK

    if selected_mode in (OutputMode.FREETRACK, OutputMode.TRACKIR):
        if freetrack_backend is None:
            return "FreeTrack backend unavailable"
        status = freetrack_backend.send(pose, raw_pose)
        if selected_mode == OutputMode.TRACKIR and status == "FreeTrack shared memory active":
            return trackir_status or trackir_bridge_status()
        return status

    if selected_mode == OutputMode.MOUSE_LOOK:
        if mouse_backend is None:
            return "Mouse Look backend unavailable"
        return mouse_backend.send(pose)

    if selected_mode == OutputMode.VJOY:
        return "vJoy selected; driver backend pending"

    return "Output mode unavailable"


def trackir_bridge_status() -> str:
    bridge = find_npclient_bridge()
    if bridge.found:
        return "TrackIR shared memory active; NPClient bridge found"
    return "TrackIR shared memory active; NPClient bridge may be required"


class OutputManager:
    _DEFAULT_SAMPLE_INTERVAL = 1.0 / 60.0
    _RESAMPLE_TIME_CONSTANT = 0.018
    _MAX_PREDICTION_LEAD = 0.008

    def __init__(self) -> None:
        self.mode = OutputMode.TRACKIR
        self.running = False
        self.last_pose = PoseSample()
        self.status = "Stopped"
        self._freetrack = FreeTrackOutput()
        self._mouse = MouseLookOutput()
        self._target_pose = PoseSample()
        self._target_velocity = PoseSample()
        self._raw_pose = PoseSample()
        self._has_target = False
        self._last_target_time = 0.0
        self._last_tick_time = 0.0
        self._sample_interval = self._DEFAULT_SAMPLE_INTERVAL
        self._trackir_status = "TrackIR shared memory active; NPClient bridge may be required"

    def set_mode(self, mode: str | OutputMode) -> None:
        was_running = self.running
        if was_running:
            self.stop()
        try:
            self.mode = OutputMode(mode)
        except ValueError:
            self.mode = OutputMode.FREETRACK
        if was_running:
            self.start()

    def start(self) -> None:
        self.running = True
        self._reset_runtime_state()
        if self.mode in (OutputMode.FREETRACK, OutputMode.TRACKIR):
            status = self._freetrack.start()
            if self.mode == OutputMode.TRACKIR and status == "FreeTrack shared memory active":
                self._trackir_status = trackir_bridge_status()
                self.status = self._trackir_status
            else:
                self.status = status
        elif self.mode == OutputMode.MOUSE_LOOK:
            self.status = self._mouse.start()
        elif self.mode == OutputMode.VJOY:
            self.status = "vJoy selected; driver backend pending"
        else:
            self.status = "Output mode unavailable"

    def stop(self) -> None:
        self.running = False
        self._freetrack.stop()
        self._mouse.stop()
        self._reset_runtime_state()
        self.status = "Stopped"

    def update_pose(self, pose: PoseSample, raw_pose: PoseSample | None = None) -> None:
        self.push_target_pose(pose, raw_pose)
        self.tick()

    def push_target_pose(
        self,
        pose: PoseSample,
        raw_pose: PoseSample | None = None,
        now: float | None = None,
    ) -> None:
        timestamp = time.monotonic() if now is None else float(now)
        target = _copy_pose(pose)
        raw = _copy_pose(raw_pose or pose)

        if self._has_target:
            delta_seconds = min(max(timestamp - self._last_target_time, 1e-3), 0.25)
            self._sample_interval = (self._sample_interval * 0.7) + (delta_seconds * 0.3)
            self._target_velocity = _velocity_pose(target, self._target_pose, delta_seconds)
        else:
            self.last_pose = target
            self._sample_interval = self._DEFAULT_SAMPLE_INTERVAL
            self._target_velocity = PoseSample()

        self._target_pose = target
        self._raw_pose = raw
        self._has_target = True
        self._last_target_time = timestamp

    def tick(self, now: float | None = None) -> None:
        if not self.running:
            return

        timestamp = time.monotonic() if now is None else float(now)
        if self._last_tick_time <= 0.0:
            self._last_tick_time = timestamp

        delta_seconds = min(max(timestamp - self._last_tick_time, 1.0 / 240.0), 0.1)
        self._last_tick_time = timestamp

        pose_to_send = self.last_pose
        if self._has_target:
            lead = min(self._sample_interval * 0.35, self._MAX_PREDICTION_LEAD)
            projected_target = _project_pose(self._target_pose, self._target_velocity, lead)
            alpha = 1.0 - math.exp(-delta_seconds / self._RESAMPLE_TIME_CONSTANT)
            pose_to_send = _blend_pose(self.last_pose, projected_target, alpha)
            self.last_pose = pose_to_send

        self.status = sendOutputToGame(
            pose_to_send,
            self.mode,
            self.running,
            freetrack_backend=self._freetrack,
            mouse_backend=self._mouse,
            raw_pose=self._raw_pose if self._has_target else pose_to_send,
            trackir_status=self._trackir_status,
        )

    def _reset_runtime_state(self) -> None:
        self.last_pose = PoseSample()
        self._target_pose = PoseSample()
        self._target_velocity = PoseSample()
        self._raw_pose = PoseSample()
        self._has_target = False
        self._last_target_time = 0.0
        self._last_tick_time = 0.0
        self._sample_interval = self._DEFAULT_SAMPLE_INTERVAL
