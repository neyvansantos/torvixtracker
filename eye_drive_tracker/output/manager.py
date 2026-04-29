from __future__ import annotations

import ctypes
import math
import os
import threading
import time
from enum import Enum

from eye_drive_tracker.filters.smart_motion import (
    QUATERNION_HAMILTON,
    QuatFromYawPitchRoll,
    Slerp,
    YawPitchRollFromQuat,
)
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
    OutputMode.TRACKIR: "TrackIR compatible (Recommended)",
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
    amount = max(0.0, min(float(alpha), 1.0))
    return PoseSample(
        yaw=current.yaw + (_angle_delta(target.yaw, current.yaw) * amount),
        pitch=current.pitch + (_angle_delta(target.pitch, current.pitch) * amount),
        roll=current.roll + (_angle_delta(target.roll, current.roll) * amount),
        x=current.x + (target.x - current.x) * amount,
        y=current.y + (target.y - current.y) * amount,
        z=current.z + (target.z - current.z) * amount,
    )


def _angle_delta(value: float, previous: float) -> float:
    delta = float(value) - float(previous)
    if abs(delta) > 180.0:
        delta -= math.copysign(360.0, delta)
    return delta


def _wrap_angle(value: float) -> float:
    wrapped = (float(value) + 180.0) % 360.0 - 180.0
    return 180.0 if math.isclose(wrapped, -180.0) else wrapped


def _blend_pose_quaternion(current: PoseSample, target: PoseSample, alpha: float) -> PoseSample:
    amount = max(0.0, min(float(alpha), 1.0))
    current_quat = QuatFromYawPitchRoll(current.yaw, current.pitch, current.roll)
    target_quat = QuatFromYawPitchRoll(target.yaw, target.pitch, target.roll)
    yaw, pitch, roll = YawPitchRollFromQuat(Slerp(current_quat, target_quat, amount))
    return PoseSample(
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        x=current.x + (target.x - current.x) * amount,
        y=current.y + (target.y - current.y) * amount,
        z=current.z + (target.z - current.z) * amount,
    )


def _interpolate_pose(current: PoseSample, target: PoseSample, alpha: float, rotation_mode: str) -> PoseSample:
    if rotation_mode == QUATERNION_HAMILTON:
        return _blend_pose_quaternion(current, target, alpha)
    return _blend_pose(current, target, alpha)


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


def _pose_delta(current: PoseSample, previous: PoseSample) -> PoseSample:
    return PoseSample(
        yaw=current.yaw - previous.yaw,
        pitch=current.pitch - previous.pitch,
        roll=current.roll - previous.roll,
        x=current.x - previous.x,
        y=current.y - previous.y,
        z=current.z - previous.z,
    )


def _suppress_velocity_noise(velocity: PoseSample, delta: PoseSample) -> PoseSample:
    angle_deadzone = OutputManager._TARGET_ANGLE_NOISE_DEADZONE
    translation_deadzone = OutputManager._TARGET_TRANSLATION_NOISE_DEADZONE

    def kept(value: float, movement: float, threshold: float) -> float:
        return 0.0 if abs(movement) <= threshold else value

    return PoseSample(
        yaw=kept(velocity.yaw, delta.yaw, angle_deadzone),
        pitch=kept(velocity.pitch, delta.pitch, angle_deadzone),
        roll=kept(velocity.roll, delta.roll, angle_deadzone),
        x=kept(velocity.x, delta.x, translation_deadzone),
        y=kept(velocity.y, delta.y, translation_deadzone),
        z=kept(velocity.z, delta.z, translation_deadzone),
    )


def _hold_output_micro_jitter(current: PoseSample, target: PoseSample) -> PoseSample:
    angle_deadzone = OutputManager._OUTPUT_ANGLE_HOLD_DEADZONE
    translation_deadzone = OutputManager._OUTPUT_TRANSLATION_HOLD_DEADZONE

    def held(current_value: float, target_value: float, threshold: float) -> float:
        return current_value if abs(target_value - current_value) <= threshold else target_value

    return PoseSample(
        yaw=held(current.yaw, current.yaw + _angle_delta(target.yaw, current.yaw), angle_deadzone),
        pitch=held(current.pitch, current.pitch + _angle_delta(target.pitch, current.pitch), angle_deadzone),
        roll=held(current.roll, current.roll + _angle_delta(target.roll, current.roll), angle_deadzone),
        x=held(current.x, target.x, translation_deadzone),
        y=held(current.y, target.y, translation_deadzone),
        z=held(current.z, target.z, translation_deadzone),
    )


def _normalize_output_pose(pose: PoseSample) -> PoseSample:
    return PoseSample(
        yaw=_wrap_angle(pose.yaw),
        pitch=_wrap_angle(pose.pitch),
        roll=_wrap_angle(pose.roll),
        x=pose.x,
        y=pose.y,
        z=pose.z,
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
    _DEFAULT_OUTPUT_HZ = 120.0
    _MIN_OUTPUT_HZ = 60.0
    _MAX_OUTPUT_HZ = 240.0
    _RESAMPLE_TIME_CONSTANT = 0.012
    _MAX_PREDICTION_LEAD = 0.003
    _VELOCITY_TIME_CONSTANT = 0.022
    _TARGET_ANGLE_NOISE_DEADZONE = 0.18
    _TARGET_TRANSLATION_NOISE_DEADZONE = 0.025
    _OUTPUT_ANGLE_HOLD_DEADZONE = 0.03
    _OUTPUT_TRANSLATION_HOLD_DEADZONE = 0.02
    _DELTA_SMOOTHING_ALPHA = 0.10
    _DT_MIN = 1.0 / 240.0
    _DT_MAX = 1.0 / 20.0

    def __init__(self) -> None:
        self.mode = OutputMode.TRACKIR
        self.running = False
        self.last_pose = PoseSample()
        self.status = "Stopped"
        self._freetrack = FreeTrackOutput()
        self._mouse = MouseLookOutput()
        self._previous_target_pose = PoseSample()
        self._previous_raw_pose = PoseSample()
        self._target_pose = PoseSample()
        self._target_velocity = PoseSample()
        self._raw_pose = PoseSample()
        self._has_target = False
        self._previous_target_time = 0.0
        self._last_target_time = 0.0
        self._last_tick_time = 0.0
        self._smooth_tick_delta = 0.0
        self._sample_interval = self._DEFAULT_SAMPLE_INTERVAL
        self._target_output_hz = self._DEFAULT_OUTPUT_HZ
        self._target_output_delta = 1.0 / self._DEFAULT_OUTPUT_HZ
        self._rotation_interpolation_mode = QUATERNION_HAMILTON
        self._trackir_status = "TrackIR shared memory active; NPClient bridge may be required"
        self._state_lock = threading.RLock()
        self._output_stop_event = threading.Event()
        self._output_thread: threading.Thread | None = None

    def set_mode(self, mode: str | OutputMode) -> None:
        with self._state_lock:
            was_running = self.running
        if was_running:
            self.stop()
        with self._state_lock:
            try:
                self.mode = OutputMode(mode)
            except ValueError:
                self.mode = OutputMode.FREETRACK
        if was_running:
            self.start()

    def configure(self, *, update_hz: float | None = None, rotation_mode: str | None = None) -> None:
        if update_hz is not None:
            self.set_update_rate(update_hz)
        if rotation_mode:
            self.set_rotation_interpolation_mode(rotation_mode)

    def set_update_rate(self, update_hz: float) -> None:
        value = max(self._MIN_OUTPUT_HZ, min(float(update_hz), self._MAX_OUTPUT_HZ))
        with self._state_lock:
            self._target_output_hz = value
            self._target_output_delta = 1.0 / value

    def set_rotation_interpolation_mode(self, rotation_mode: str) -> None:
        with self._state_lock:
            self._rotation_interpolation_mode = QUATERNION_HAMILTON if rotation_mode == QUATERNION_HAMILTON else "EulerClassic"

    def start(self) -> None:
        with self._state_lock:
            if self.running:
                return
            self.running = True
            self._reset_runtime_state()
            mode = self.mode

        if mode in (OutputMode.FREETRACK, OutputMode.TRACKIR):
            status = self._freetrack.start()
            if mode == OutputMode.TRACKIR and status == "FreeTrack shared memory active":
                self._trackir_status = trackir_bridge_status()
                status = self._trackir_status
        elif mode == OutputMode.MOUSE_LOOK:
            status = self._mouse.start()
        elif mode == OutputMode.VJOY:
            status = "vJoy selected; driver backend pending"
        else:
            status = "Output mode unavailable"

        with self._state_lock:
            self.status = status
        self._start_output_thread()

    def stop(self) -> None:
        with self._state_lock:
            self.running = False
        self._stop_output_thread()
        self._freetrack.stop()
        self._mouse.stop()
        with self._state_lock:
            self._reset_runtime_state()
            self.status = "Stopped"

    def update_pose(self, pose: PoseSample, raw_pose: PoseSample | None = None) -> None:
        self.push_target_pose(pose, raw_pose)

    def push_target_pose(
        self,
        pose: PoseSample,
        raw_pose: PoseSample | None = None,
        now: float | None = None,
    ) -> None:
        timestamp = time.perf_counter() if now is None else float(now)
        target = _copy_pose(pose)
        raw = _copy_pose(raw_pose or pose)

        with self._state_lock:
            if self._has_target:
                delta_seconds = min(max(timestamp - self._last_target_time, 1e-3), 0.25)
                self._sample_interval = (self._sample_interval * 0.7) + (delta_seconds * 0.3)
                target_delta = _pose_delta(target, self._target_pose)
                instant_velocity = _suppress_velocity_noise(
                    _velocity_pose(target, self._target_pose, delta_seconds),
                    target_delta,
                )
                velocity_alpha = 1.0 - math.exp(-delta_seconds / self._VELOCITY_TIME_CONSTANT)
                self._target_velocity = _blend_pose(self._target_velocity, instant_velocity, velocity_alpha)
                self._previous_target_pose = _copy_pose(self._target_pose)
                self._previous_raw_pose = _copy_pose(self._raw_pose)
                self._previous_target_time = self._last_target_time
            else:
                self.last_pose = target
                self._previous_target_pose = target
                self._previous_raw_pose = raw
                self._previous_target_time = timestamp - self._sample_interval
                self._sample_interval = self._DEFAULT_SAMPLE_INTERVAL
                self._target_velocity = PoseSample()

            self._target_pose = target
            self._raw_pose = raw
            self._has_target = True
            self._last_target_time = timestamp

    def tick(self, now: float | None = None) -> None:
        timestamp = time.perf_counter() if now is None else float(now)
        with self._state_lock:
            if not self.running:
                return

            if self._last_tick_time <= 0.0:
                self._last_tick_time = timestamp

            raw_delta = min(max(timestamp - self._last_tick_time, self._DT_MIN), self._DT_MAX)
            self._last_tick_time = timestamp
            if self._smooth_tick_delta <= 0.0:
                self._smooth_tick_delta = raw_delta
            else:
                self._smooth_tick_delta += (raw_delta - self._smooth_tick_delta) * self._DELTA_SMOOTHING_ALPHA
            delta_seconds = min(max(self._smooth_tick_delta, self._DT_MIN), self._DT_MAX)

            pose_to_send = self.last_pose
            if self._has_target:
                interpolated_target = self._interpolated_target_locked(timestamp)
                lead = min(self._sample_interval * 0.20, self._MAX_PREDICTION_LEAD)
                projected_target = _project_pose(interpolated_target, self._target_velocity, lead)
                projected_target = _hold_output_micro_jitter(self.last_pose, projected_target)
                alpha = 1.0 - math.exp(-delta_seconds / self._RESAMPLE_TIME_CONSTANT)
                pose_to_send = _interpolate_pose(
                    self.last_pose,
                    projected_target,
                    alpha,
                    self._rotation_interpolation_mode,
                )
                pose_to_send = _hold_output_micro_jitter(self.last_pose, pose_to_send)
                pose_to_send = _normalize_output_pose(pose_to_send)
                self.last_pose = pose_to_send

            mode = self.mode
            running = self.running
            raw_pose = self._raw_pose if self._has_target else pose_to_send
            trackir_status = self._trackir_status

        status = sendOutputToGame(
            pose_to_send,
            mode,
            running,
            freetrack_backend=self._freetrack,
            mouse_backend=self._mouse,
            raw_pose=raw_pose,
            trackir_status=trackir_status,
        )

        with self._state_lock:
            if self.running:
                self.status = status

    def _interpolated_target_locked(self, timestamp: float) -> PoseSample:
        interval = max(self._last_target_time - self._previous_target_time, 1e-3)
        interval = min(max(interval, self._DT_MIN), self._DT_MAX)
        elapsed = timestamp - self._last_target_time
        # Allow slight extrapolation (up to 1.2x) for smoother bridging
        alpha = min(max(elapsed / interval, 0.0), 1.2)
        return _interpolate_pose(
            self._previous_target_pose,
            self._target_pose,
            alpha,
            self._rotation_interpolation_mode,
        )

    def _reset_runtime_state(self) -> None:
        self.last_pose = PoseSample()
        self._previous_target_pose = PoseSample()
        self._previous_raw_pose = PoseSample()
        self._target_pose = PoseSample()
        self._target_velocity = PoseSample()
        self._raw_pose = PoseSample()
        self._has_target = False
        self._previous_target_time = 0.0
        self._last_target_time = 0.0
        self._last_tick_time = 0.0
        self._smooth_tick_delta = 0.0
        self._sample_interval = self._DEFAULT_SAMPLE_INTERVAL

    def _start_output_thread(self) -> None:
        self._stop_output_thread()
        self._output_stop_event.clear()
        self._output_thread = threading.Thread(target=self._run_output_loop, name="TorvixOutputLoop", daemon=True)
        self._output_thread.start()

    def _stop_output_thread(self) -> None:
        self._output_stop_event.set()
        thread = self._output_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._output_thread = None

    def _run_output_loop(self) -> None:
        self._raise_output_thread_priority()
        next_tick = time.perf_counter()
        try:
            while not self._output_stop_event.is_set():
                with self._state_lock:
                    target_delta = self._target_output_delta
                    running = self.running
                if not running:
                    break

                now = time.perf_counter()
                wait_seconds = next_tick - now

                if wait_seconds > 0.002:
                    # Sleep for most of the wait, then spin-wait for precision
                    if self._output_stop_event.wait(wait_seconds - 0.001):
                        break
                elif wait_seconds > 0.0:
                    # Spin-wait for sub-millisecond precision
                    while time.perf_counter() < next_tick:
                        pass

                self.tick(time.perf_counter())
                next_tick += target_delta
                # If we fell behind by more than one frame, reset schedule
                late_by = time.perf_counter() - next_tick
                if late_by > target_delta:
                    next_tick = time.perf_counter() + target_delta
        finally:
            self._restore_timer_resolution()

    @staticmethod
    def _raise_output_thread_priority() -> None:
        if os.name != "nt":
            return
        try:
            # THREAD_PRIORITY_TIME_CRITICAL = 15
            ctypes.windll.kernel32.SetThreadPriority(
                ctypes.windll.kernel32.GetCurrentThread(),
                15,
            )
        except (AttributeError, OSError):
            pass
        # Also request 1ms timer resolution for precise sleeps
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)
        except (AttributeError, OSError):
            pass

    @staticmethod
    def _restore_timer_resolution() -> None:
        if os.name != "nt":
            return
        try:
            ctypes.windll.winmm.timeEndPeriod(1)
        except (AttributeError, OSError):
            pass
