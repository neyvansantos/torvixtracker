# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from eye_drive_tracker.tracking.models import PoseSample


AXIS_COUNT = 6
TX, TY, TZ, YAW, PITCH, ROLL = range(AXIS_COUNT)

EULER_CLASSIC = "EulerClassic"
QUATERNION_HAMILTON = "QuaternionHamilton"

ROTATION_GAIN_CURVE: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.5, 0.4),
    (1.0, 1.5),
    (1.5, 8.0),
    (2.5, 35.0),
    (5.0, 100.0),
    (8.0, 200.0),
    (9.0, 300.0),
)

POSITION_GAIN_CURVE: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.33, 0.375),
    (0.66, 0.75),
    (1.33, 2.25),
    (1.66, 4.5),
    (2.0, 7.5),
    (3.0, 24.0),
    (5.0, 60.0),
    (7.0, 110.0),
    (8.0, 150.0),
    (9.0, 200.0),
)

SMART_MOTION_PRESET_LABELS = {
    "ultra_smooth": "Ultra Smooth",
    "balanced": "Balanced",
    "fast_response": "Fast Response",
    "cinematic": "Cinematic",
    "custom": "Custom",
}

SMART_MOTION_PRESETS: dict[str, dict[str, float | str | bool]] = {
    "ultra_smooth": {
        "motion_rotation_smoothing": 2.10,
        "motion_position_smoothing": 1.35,
        "motion_rotation_deadzone": 0.055,
        "motion_position_deadzone": 0.18,
        "motion_max_zoomed_smoothing": 1.90,
        "motion_max_confidence_smoothing_boost": 2.40,
        "motion_stillness_smoothing_boost": 2.00,
        "motion_stillness_deadzone_boost": 1.65,
        "motion_rotation_snap_threshold": 11.0,
        "motion_position_snap_threshold": 18.0,
        "motion_snap_enabled": False,
        "motion_snap_alpha": 0.60,
    },
    "balanced": {
        "motion_rotation_smoothing": 1.50,
        "motion_position_smoothing": 1.00,
        "motion_rotation_deadzone": 0.03,
        "motion_position_deadzone": 0.10,
        "motion_max_zoomed_smoothing": 1.20,
        "motion_max_confidence_smoothing_boost": 2.00,
        "motion_stillness_smoothing_boost": 1.50,
        "motion_stillness_deadzone_boost": 1.20,
        "motion_rotation_snap_threshold": 8.0,
        "motion_position_snap_threshold": 15.0,
        "motion_snap_enabled": False,
        "motion_snap_alpha": 0.60,
    },
    "fast_response": {
        "motion_rotation_smoothing": 0.85,
        "motion_position_smoothing": 0.55,
        "motion_rotation_deadzone": 0.018,
        "motion_position_deadzone": 0.055,
        "motion_max_zoomed_smoothing": 0.70,
        "motion_max_confidence_smoothing_boost": 1.40,
        "motion_stillness_smoothing_boost": 1.18,
        "motion_stillness_deadzone_boost": 1.05,
        "motion_rotation_snap_threshold": 5.5,
        "motion_position_snap_threshold": 10.0,
        "motion_snap_enabled": True,
        "motion_snap_alpha": 0.82,
    },
    "cinematic": {
        "motion_rotation_smoothing": 2.35,
        "motion_position_smoothing": 1.45,
        "motion_rotation_deadzone": 0.04,
        "motion_position_deadzone": 0.14,
        "motion_max_zoomed_smoothing": 2.60,
        "motion_max_confidence_smoothing_boost": 2.60,
        "motion_stillness_smoothing_boost": 2.30,
        "motion_stillness_deadzone_boost": 1.45,
        "motion_rotation_snap_threshold": 13.0,
        "motion_position_snap_threshold": 21.0,
        "motion_snap_enabled": False,
        "motion_snap_alpha": 0.55,
    },
}


@dataclass(frozen=True)
class TorvixSmartMotionAxisDebug:
    raw: float = 0.0
    filtered: float = 0.0
    delta: float = 0.0
    gain: float = 0.0
    smoothing: float = 0.0
    deadzone: float = 0.0
    alpha: float = 0.0
    snap: bool = False
    held: bool = False


@dataclass(frozen=True)
class TorvixSmartMotionDebug:
    enabled: bool = True
    rotation_mode: str = QUATERNION_HAMILTON
    state: str = "Moving"
    confidence: float = 1.0
    delta_time: float = 1.0 / 60.0
    fps: float = 60.0
    rotation_magnitude: float = 0.0
    position_magnitude: float = 0.0
    rotation_gain: float = 0.0
    position_gain: float = 0.0
    rotation_smoothing: float = 0.0
    position_smoothing: float = 0.0
    rotation_deadzone: float = 0.0
    position_deadzone: float = 0.0
    zoom_extra_smoothing: float = 0.0
    confidence_smoothing_boost: float = 0.0
    stillness_boost: float = 0.0
    snap_active: bool = False
    low_confidence_hold: bool = False
    axes: tuple[TorvixSmartMotionAxisDebug, ...] = field(
        default_factory=lambda: tuple(TorvixSmartMotionAxisDebug() for _ in range(AXIS_COUNT))
    )


def apply_smart_motion_preset(config: Any, preset: str) -> None:
    key = str(preset or "balanced")
    values = SMART_MOTION_PRESETS.get(key)
    if values is None:
        key = "balanced"
        values = SMART_MOTION_PRESETS[key]
    for field_name, value in values.items():
        setattr(config, field_name, value)
    setattr(config, "motion_filter_preset", key)


def Clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, SafeNumber(value, minimum)))


def safeClamp(value: float, minimum: float, maximum: float) -> float:
    return Clamp(value, minimum, maximum)


def Sign(value: float) -> float:
    number = SafeNumber(value)
    if number < 0.0:
        return -1.0
    if number > 0.0:
        return 1.0
    return 0.0


def SafeNumber(value: float, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return number if math.isfinite(number) else float(fallback)


def safeDeltaTime(delta_time: float | None) -> float:
    if delta_time is None:
        return 1.0 / 60.0
    return Clamp(delta_time, 1.0 / 240.0, 1.0 / 20.0)


def safeAngleWrap(value: float) -> float:
    wrapped = (SafeNumber(value) + 180.0) % 360.0 - 180.0
    return 180.0 if math.isclose(wrapped, -180.0) else wrapped


def safeNormalize(values: Iterable[float]) -> list[float]:
    prepared = [SafeNumber(value) for value in values]
    magnitude = math.sqrt(sum(value * value for value in prepared))
    if magnitude <= 1e-9:
        return [0.0 for _ in prepared]
    return [value / magnitude for value in prepared]


def NormalizeQuat(quat: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    w, x, y, z = (SafeNumber(component) for component in quat)
    magnitude = math.sqrt((w * w) + (x * x) + (y * y) + (z * z))
    if magnitude <= 1e-9:
        return (1.0, 0.0, 0.0, 0.0)
    return (w / magnitude, x / magnitude, y / magnitude, z / magnitude)


def DotQuat(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    return sum(SafeNumber(a) * SafeNumber(b) for a, b in zip(first, second, strict=True))


def QuatFromYawPitchRoll(yaw: float, pitch: float, roll: float) -> tuple[float, float, float, float]:
    yaw_rad = math.radians(SafeNumber(yaw))
    pitch_rad = math.radians(SafeNumber(pitch))
    roll_rad = math.radians(SafeNumber(roll))

    cy = math.cos(yaw_rad * 0.5)
    sy = math.sin(yaw_rad * 0.5)
    cp = math.cos(pitch_rad * 0.5)
    sp = math.sin(pitch_rad * 0.5)
    cr = math.cos(roll_rad * 0.5)
    sr = math.sin(roll_rad * 0.5)

    return NormalizeQuat(
        (
            (cr * cp * cy) + (sr * sp * sy),
            (sr * cp * cy) - (cr * sp * sy),
            (cr * sp * cy) + (sr * cp * sy),
            (cr * cp * sy) - (sr * sp * cy),
        )
    )


def YawPitchRollFromQuat(quat: tuple[float, float, float, float]) -> tuple[float, float, float]:
    w, x, y, z = NormalizeQuat(quat)

    sinr_cosp = 2.0 * ((w * x) + (y * z))
    cosr_cosp = 1.0 - (2.0 * ((x * x) + (y * y)))
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * ((w * y) - (z * x))
    if abs(sinp) >= 1.0:
        pitch = math.copysign(math.pi / 2.0, sinp)
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2.0 * ((w * z) + (x * y))
    cosy_cosp = 1.0 - (2.0 * ((y * y) + (z * z)))
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (safeAngleWrap(math.degrees(yaw)), safeAngleWrap(math.degrees(pitch)), safeAngleWrap(math.degrees(roll)))


def AngleBetweenQuats(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    dot = abs(Clamp(DotQuat(NormalizeQuat(first), NormalizeQuat(second)), -1.0, 1.0))
    return math.degrees(2.0 * math.acos(dot))


def Slerp(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    alpha: float,
) -> tuple[float, float, float, float]:
    start = NormalizeQuat(first)
    end = NormalizeQuat(second)
    amount = Clamp(alpha, 0.0, 1.0)
    dot = DotQuat(start, end)
    if dot < 0.0:
        end = tuple(-component for component in end)
        dot = -dot
    dot = Clamp(dot, -1.0, 1.0)
    if dot > 0.9995:
        return NormalizeQuat(tuple(a + ((b - a) * amount) for a, b in zip(start, end, strict=True)))
    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)
    if abs(sin_theta_0) <= 1e-9:
        return start
    theta = theta_0 * amount
    sin_theta = math.sin(theta)
    scale_start = math.cos(theta) - (dot * sin_theta / sin_theta_0)
    scale_end = sin_theta / sin_theta_0
    return NormalizeQuat(tuple((a * scale_start) + (b * scale_end) for a, b in zip(start, end, strict=True)))


class TorvixSmartMotionFilter:
    def __init__(self, config: Any | None = None) -> None:
        self.config = config
        self.firstRun = True
        self.lastPosition = [0.0, 0.0, 0.0]
        self.lastRotation = [0.0, 0.0, 0.0]
        self.lastRotationQuat = (1.0, 0.0, 0.0, 0.0)
        self.lastOutput = [0.0] * AXIS_COUNT
        self.lastRawInput = [0.0] * AXIS_COUNT
        self.lastDelta = [0.0] * AXIS_COUNT
        self.filteredOutput = [0.0] * AXIS_COUNT
        self.lastTimestamp = 0.0
        self.trackingConfidence = 1.0
        self.debugInfo = TorvixSmartMotionDebug()
        self._position_window: deque[list[float]] = deque(maxlen=12)
        self._rotation_window: deque[list[float]] = deque(maxlen=12)
        self._bad_tracking_frames = 0

    def initialize(self, config: Any | None = None) -> None:
        if config is not None:
            self.config = config
        self.reset()

    def reset(self) -> None:
        self.firstRun = True
        self.lastPosition = [0.0, 0.0, 0.0]
        self.lastRotation = [0.0, 0.0, 0.0]
        self.lastRotationQuat = (1.0, 0.0, 0.0, 0.0)
        self.lastOutput = [0.0] * AXIS_COUNT
        self.lastRawInput = [0.0] * AXIS_COUNT
        self.lastDelta = [0.0] * AXIS_COUNT
        self.filteredOutput = [0.0] * AXIS_COUNT
        self.lastTimestamp = 0.0
        self.trackingConfidence = 1.0
        self.debugInfo = TorvixSmartMotionDebug()
        self._position_window.clear()
        self._rotation_window.clear()
        self._bad_tracking_frames = 0

    def center(self, rawInput: PoseSample | Iterable[float] | None = None) -> None:
        values = self._to_values(rawInput) if rawInput is not None else self.filteredOutput
        self.lastPosition = values[TX : TZ + 1]
        self.lastRotation = values[YAW : ROLL + 1]
        self.lastRotationQuat = QuatFromYawPitchRoll(*self.lastRotation)
        self.lastOutput = values.copy()
        self.lastRawInput = values.copy()
        self.lastDelta = [0.0] * AXIS_COUNT
        self.filteredOutput = values.copy()
        self.firstRun = False
        self._position_window.clear()
        self._rotation_window.clear()
        self.debugInfo = TorvixSmartMotionDebug()

    def update(
        self,
        rawInput: PoseSample | Iterable[float],
        deltaTime: float | None,
        confidence: float,
        config: Any | None = None,
    ) -> PoseSample:
        if config is not None:
            self.config = config
        cfg = self.config
        raw = self._to_values(rawInput)
        dt = safeDeltaTime(deltaTime)
        self.lastTimestamp += dt
        self.trackingConfidence = Clamp(confidence, 0.0, 1.0)

        if not self._get_bool(cfg, "motion_filter_enabled", True):
            self._accept_raw(raw, dt, enabled=False)
            return self.getFilteredPose()

        if self.firstRun:
            self._accept_raw(raw, dt, enabled=True)
            self.firstRun = False
            return self.getFilteredPose()

        self.lastDelta = [
            raw[index] - self.lastOutput[index] if index <= TZ else self._angle_delta(raw[index], self.lastOutput[index])
            for index in range(AXIS_COUNT)
        ]
        self.updateJitterWindow(raw)
        position_still = self.detectStillness("position")
        rotation_still = self.detectStillness("rotation")
        confidence_boost, confidence_deadzone, hold_low_confidence = self.calculateConfidenceSmoothing(
            self.trackingConfidence,
            cfg,
        )
        zoom_extra = self.calculateZoomSmoothing(cfg)

        if hold_low_confidence:
            self._bad_tracking_frames += 1
        else:
            self._bad_tracking_frames = 0
        hold_output = hold_low_confidence and self._bad_tracking_frames <= self._get_int(cfg, "motion_hold_frames_on_bad_tracking", 3)

        position_output, position_debug = self.updatePosition(
            raw,
            dt,
            cfg,
            still=position_still,
            confidence_boost=confidence_boost,
            confidence_deadzone=confidence_deadzone,
            hold_output=hold_output,
        )
        rotation_output, rotation_debug = self.updateRotation(
            raw,
            dt,
            cfg,
            still=rotation_still,
            zoom_extra_smoothing=zoom_extra,
            confidence_boost=confidence_boost,
            confidence_deadzone=confidence_deadzone,
            hold_output=hold_output,
        )

        self.filteredOutput = position_output + rotation_output
        self.lastOutput = self.filteredOutput.copy()
        self.lastPosition = position_output.copy()
        self.lastRotation = rotation_output.copy()
        self.lastRotationQuat = QuatFromYawPitchRoll(*self.lastRotation)
        self.lastRawInput = raw.copy()

        axes = tuple(position_debug["axes"] + rotation_debug["axes"])
        snap_active = bool(position_debug["snap"] or rotation_debug["snap"])
        if hold_output:
            state = "Low Confidence"
        elif snap_active:
            state = "Snapping"
        elif position_still and rotation_still:
            state = "Still"
        else:
            state = "Moving"
        self.debugInfo = TorvixSmartMotionDebug(
            enabled=True,
            rotation_mode=self._rotation_mode(cfg),
            state=state,
            confidence=self.trackingConfidence,
            delta_time=dt,
            fps=1.0 / dt if dt > 0.0 else 0.0,
            rotation_magnitude=rotation_debug["magnitude"],
            position_magnitude=position_debug["magnitude"],
            rotation_gain=rotation_debug["gain"],
            position_gain=position_debug["gain"],
            rotation_smoothing=rotation_debug["smoothing"],
            position_smoothing=position_debug["smoothing"],
            rotation_deadzone=rotation_debug["deadzone"],
            position_deadzone=position_debug["deadzone"],
            zoom_extra_smoothing=zoom_extra,
            confidence_smoothing_boost=confidence_boost - 1.0,
            stillness_boost=max(position_debug["still_boost"], rotation_debug["still_boost"]),
            snap_active=snap_active,
            low_confidence_hold=hold_output,
            axes=axes,
        )
        return self.getFilteredPose()

    def updatePosition(
        self,
        raw: list[float],
        deltaTime: float,
        config: Any | None = None,
        *,
        still: bool = False,
        confidence_boost: float = 1.0,
        confidence_deadzone: float = 1.0,
        hold_output: bool = False,
    ) -> tuple[list[float], dict[str, Any]]:
        cfg = config or self.config
        if hold_output or not self._get_bool(cfg, "motion_position_enabled", True):
            axes = [
                self._axis_debug(raw[index], self.lastOutput[index], 0.0, 0.0, 0.0, held=hold_output)
                for index in (TX, TY, TZ)
            ]
            return self.lastOutput[TX : TZ + 1], self._group_debug(axes, 0.0, 0.0, 0.0, 0.0, False, 0.0)

        smoothing = Clamp(self._get_float(cfg, "motion_position_smoothing", 1.0), 0.05, 1.5)
        deadzone = Clamp(self._get_float(cfg, "motion_position_deadzone", 0.1), 0.0, 1.0)
        if still and self._get_bool(cfg, "motion_stillness_detection_enabled", True):
            smoothing *= max(1.0, self._get_float(cfg, "motion_stillness_smoothing_boost", 1.5))
            deadzone *= max(1.0, self._get_float(cfg, "motion_stillness_deadzone_boost", 1.2))
        smoothing *= confidence_boost
        deadzone *= confidence_deadzone

        deltas = [raw[index] - self.lastOutput[index] for index in (TX, TY, TZ)]
        output, group = self._update_vector(
            raw_values=raw[TX : TZ + 1],
            previous_values=self.lastOutput[TX : TZ + 1],
            deltas=deltas,
            delta_time=deltaTime,
            smoothing=smoothing,
            deadzone=deadzone,
            responsiveness=self._get_float(cfg, "motion_position_responsiveness", 1.0),
            gain_curve_strength=self._get_float(cfg, "motion_position_gain_curve_strength", 1.0),
            max_speed=self._get_float(cfg, "motion_position_max_speed_snap", 220.0),
            snap_threshold=self._get_float(cfg, "motion_position_snap_threshold", 15.0),
            curve_points=POSITION_GAIN_CURVE,
            snap_enabled=self._get_bool(cfg, "motion_snap_enabled", True),
            snap_alpha=self._get_float(cfg, "motion_snap_alpha", 0.85),
        )
        group["smoothing"] = smoothing
        group["deadzone"] = deadzone
        group["still_boost"] = self._get_float(cfg, "motion_stillness_smoothing_boost", 1.5) if still else 0.0
        return output, group

    def updateRotation(
        self,
        raw: list[float],
        deltaTime: float,
        config: Any | None = None,
        *,
        still: bool = False,
        zoom_extra_smoothing: float = 0.0,
        confidence_boost: float = 1.0,
        confidence_deadzone: float = 1.0,
        hold_output: bool = False,
    ) -> tuple[list[float], dict[str, Any]]:
        cfg = config or self.config
        if hold_output or not self._get_bool(cfg, "motion_rotation_enabled", True):
            axes = [
                self._axis_debug(raw[index], self.lastOutput[index], 0.0, 0.0, 0.0, held=hold_output)
                for index in (YAW, PITCH, ROLL)
            ]
            return self.lastOutput[YAW : ROLL + 1], self._group_debug(axes, 0.0, 0.0, 0.0, 0.0, False, 0.0)

        smoothing = Clamp(self._get_float(cfg, "motion_rotation_smoothing", 1.5), 0.05, 2.5)
        deadzone = Clamp(self._get_float(cfg, "motion_rotation_deadzone", 0.03), 0.0, 0.2)
        smoothing += max(0.0, zoom_extra_smoothing)
        if still and self._get_bool(cfg, "motion_stillness_detection_enabled", True):
            smoothing *= max(1.0, self._get_float(cfg, "motion_stillness_smoothing_boost", 1.5))
            deadzone *= max(1.0, self._get_float(cfg, "motion_stillness_deadzone_boost", 1.2))
        smoothing *= confidence_boost
        deadzone *= confidence_deadzone

        if self._rotation_mode(cfg) == QUATERNION_HAMILTON:
            output, group = self._update_rotation_quaternion(raw, deltaTime, cfg, smoothing, deadzone)
        else:
            deltas = [
                self._angle_delta(raw[index], self.lastOutput[index])
                for index in (YAW, PITCH, ROLL)
            ]
            output, group = self._update_vector(
                raw_values=raw[YAW : ROLL + 1],
                previous_values=self.lastOutput[YAW : ROLL + 1],
                deltas=deltas,
                delta_time=deltaTime,
                smoothing=smoothing,
                deadzone=deadzone,
                responsiveness=self._get_float(cfg, "motion_rotation_responsiveness", 1.0),
                gain_curve_strength=self._get_float(cfg, "motion_rotation_gain_curve_strength", 1.0),
                max_speed=self._get_float(cfg, "motion_rotation_max_speed_snap", 360.0),
                snap_threshold=self._get_float(cfg, "motion_rotation_snap_threshold", 8.0),
                curve_points=ROTATION_GAIN_CURVE,
                snap_enabled=self._get_bool(cfg, "motion_snap_enabled", True),
                snap_alpha=self._get_float(cfg, "motion_snap_alpha", 0.85),
                wrap_angles=True,
            )
        group["smoothing"] = smoothing
        group["deadzone"] = deadzone
        group["still_boost"] = self._get_float(cfg, "motion_stillness_smoothing_boost", 1.5) if still else 0.0
        return output, group

    def applyDeadzone(self, value: float, deadzone: float) -> float:
        delta = SafeNumber(value)
        threshold = max(0.0, SafeNumber(deadzone))
        if abs(delta) <= threshold:
            return 0.0
        return delta - (Sign(delta) * threshold)

    def evaluateGainCurve(
        self,
        value: float,
        curvePoints: Iterable[tuple[float, float]],
        clampOutput: bool = True,
    ) -> float:
        x = max(0.0, SafeNumber(value))
        points = sorted((SafeNumber(px), SafeNumber(py)) for px, py in curvePoints)
        if not points:
            return 0.0
        if x <= points[0][0]:
            return max(0.0, points[0][1])
        for (left_x, left_y), (right_x, right_y) in zip(points, points[1:], strict=False):
            if x <= right_x:
                span = max(right_x - left_x, 1e-9)
                t = Clamp((x - left_x) / span, 0.0, 1.0)
                smooth_t = t * t * (3.0 - (2.0 * t))
                return max(0.0, left_y + ((right_y - left_y) * smooth_t))
        return max(0.0, points[-1][1] if clampOutput else points[-1][1] + ((x - points[-1][0]) * 10.0))

    def calculateZoomSmoothing(self, config: Any | None = None) -> float:
        cfg = config or self.config
        if not self._get_bool(cfg, "motion_zoom_smoothing_enabled", True):
            return 0.0
        max_z = Clamp(self._get_float(cfg, "motion_max_z", 20.0), 10.0, 30.0)
        max_added = Clamp(self._get_float(cfg, "motion_max_zoomed_smoothing", 1.2), 0.0, 10.0)
        z_amount = Clamp(abs(self.filteredOutput[TZ]), 0.0, max_z)
        return max_added * (z_amount / max_z)

    def calculateConfidenceSmoothing(self, confidence: float, config: Any | None = None) -> tuple[float, float, bool]:
        cfg = config or self.config
        if not self._get_bool(cfg, "motion_confidence_smoothing_enabled", True):
            return 1.0, 1.0, False
        value = Clamp(confidence, 0.0, 1.0)
        low = Clamp(self._get_float(cfg, "motion_low_confidence_threshold", 0.45), 0.0, 1.0)
        critical = Clamp(self._get_float(cfg, "motion_critical_confidence_threshold", 0.25), 0.0, low)
        max_boost = max(1.0, self._get_float(cfg, "motion_max_confidence_smoothing_boost", 2.0))
        if value < critical:
            return max_boost, 1.85, True
        if value < low:
            t = (low - value) / max(low - critical, 1e-6)
            return 1.0 + ((max_boost - 1.0) * t), 1.0 + (0.55 * t), False
        return 1.0, 1.0, False

    def getFilteredOutput(self) -> list[float]:
        return self.filteredOutput.copy()

    def getFilteredPose(self) -> PoseSample:
        return self._to_pose(self.filteredOutput)

    def getDebugData(self) -> TorvixSmartMotionDebug:
        return self.debugInfo

    def updateJitterWindow(self, raw: PoseSample | Iterable[float]) -> None:
        values = self._to_values(raw)
        position_delta = [values[index] - self.lastRawInput[index] for index in (TX, TY, TZ)]
        rotation_delta = [self._angle_delta(values[index], self.lastRawInput[index]) for index in (YAW, PITCH, ROLL)]
        self._position_window.append(position_delta)
        self._rotation_window.append(rotation_delta)

    def detectStillness(self, group: str = "rotation") -> bool:
        cfg = self.config
        if not self._get_bool(cfg, "motion_stillness_detection_enabled", True):
            return False
        window = self._rotation_window if group == "rotation" else self._position_window
        if len(window) < max(3, min(window.maxlen or 12, self._get_int(cfg, "motion_stillness_window", 12)) // 2):
            return False
        threshold = (
            self._get_float(cfg, "motion_stillness_rotation_threshold", 0.08)
            if group == "rotation"
            else self._get_float(cfg, "motion_stillness_position_threshold", 0.05)
        )
        return self.calculateMicroMovement(group) <= max(0.0, threshold)

    def calculateMicroMovement(self, group: str = "rotation") -> float:
        window = self._rotation_window if group == "rotation" else self._position_window
        if not window:
            return 0.0
        magnitudes = [math.sqrt(sum(value * value for value in frame)) for frame in window]
        return sum(magnitudes) / max(len(magnitudes), 1)

    def _update_vector(
        self,
        *,
        raw_values: list[float],
        previous_values: list[float],
        deltas: list[float],
        delta_time: float,
        smoothing: float,
        deadzone: float,
        responsiveness: float,
        gain_curve_strength: float,
        max_speed: float,
        snap_threshold: float,
        curve_points: Iterable[tuple[float, float]],
        snap_enabled: bool,
        snap_alpha: float,
        wrap_angles: bool = False,
    ) -> tuple[list[float], dict[str, Any]]:
        adjusted_deltas = [self.applyDeadzone(delta, deadzone) for delta in deltas]
        normalized = [delta / max(smoothing, 1e-6) for delta in adjusted_deltas]
        magnitude = math.sqrt(sum(delta * delta for delta in normalized))
        raw_magnitude = math.sqrt(sum(delta * delta for delta in deltas))
        gain = self.evaluateGainCurve(magnitude, curve_points)
        gain *= max(0.0, SafeNumber(gain_curve_strength, 1.0)) * max(0.0, SafeNumber(responsiveness, 1.0))
        if max_speed > 0.0:
            gain = min(gain, max_speed)
        snap = bool(snap_enabled and raw_magnitude >= max(0.0, snap_threshold))
        if magnitude <= 1e-9 or gain <= 0.0:
            axes = [
                self._axis_debug(raw, previous, delta, 0.0, deadzone, held=True)
                for raw, previous, delta in zip(raw_values, previous_values, deltas, strict=True)
            ]
            return previous_values.copy(), self._group_debug(axes, magnitude, gain, smoothing, deadzone, False, 0.0)

        output = []
        axes = []
        alpha = 0.0
        for raw, previous, delta, adjusted in zip(raw_values, previous_values, deltas, adjusted_deltas, strict=True):
            axis_weight = abs(adjusted / max(math.sqrt(sum(value * value for value in adjusted_deltas)), 1e-9))
            movement = Sign(adjusted) * gain * axis_weight * delta_time
            if snap:
                movement = self._snap_movement(movement, delta, snap_alpha)
            target = previous + movement
            if wrap_angles:
                target = safeAngleWrap(target)
            output.append(target)
            axis_alpha = 0.0 if abs(delta) <= 1e-9 else Clamp(abs(movement / delta), 0.0, 1.0)
            alpha = max(alpha, axis_alpha)
            axes.append(self._axis_debug(raw, target, delta, gain, deadzone, smoothing, axis_alpha, snap=snap))
        return output, self._group_debug(axes, magnitude, gain, smoothing, deadzone, snap, alpha)

    def _update_rotation_quaternion(
        self,
        raw: list[float],
        delta_time: float,
        config: Any,
        smoothing: float,
        deadzone: float,
    ) -> tuple[list[float], dict[str, Any]]:
        raw_rotation = raw[YAW : ROLL + 1]
        current_quat = QuatFromYawPitchRoll(*raw_rotation)
        angle = AngleBetweenQuats(self.lastRotationQuat, current_quat)
        adjusted_angle = self.applyDeadzone(angle, deadzone)
        normalized = adjusted_angle / max(smoothing, 1e-6)
        gain = self.evaluateGainCurve(normalized, ROTATION_GAIN_CURVE)
        gain *= max(0.0, self._get_float(config, "motion_rotation_gain_curve_strength", 1.0))
        gain *= max(0.0, self._get_float(config, "motion_rotation_responsiveness", 1.0))
        max_speed = self._get_float(config, "motion_rotation_max_speed_snap", 360.0)
        if max_speed > 0.0:
            gain = min(gain, max_speed)
        snap = bool(
            self._get_bool(config, "motion_snap_enabled", True)
            and angle >= max(0.0, self._get_float(config, "motion_rotation_snap_threshold", 8.0))
        )
        if angle <= 1e-9 or adjusted_angle <= 0.0:
            axes = [
                self._axis_debug(raw[index], self.lastOutput[index], 0.0, gain, deadzone, smoothing, held=True)
                for index in (YAW, PITCH, ROLL)
            ]
            return self.lastRotation.copy(), self._group_debug(axes, normalized, gain, smoothing, deadzone, False, 0.0)

        step_angle = gain * delta_time
        alpha = Clamp(step_angle / max(angle, 1e-9), 0.0, 1.0)
        if snap:
            alpha = max(alpha, Clamp(self._get_float(config, "motion_snap_alpha", 0.85), 0.0, 1.0))
        output_quat = Slerp(self.lastRotationQuat, current_quat, alpha)
        yaw, pitch, roll = YawPitchRollFromQuat(output_quat)
        output = [yaw, pitch, roll]
        deltas = [self._angle_delta(raw_value, previous) for raw_value, previous in zip(raw_rotation, self.lastRotation, strict=True)]
        axes = [
            self._axis_debug(raw_value, filtered, delta, gain, deadzone, smoothing, alpha, snap=snap)
            for raw_value, filtered, delta in zip(raw_rotation, output, deltas, strict=True)
        ]
        return output, self._group_debug(axes, normalized, gain, smoothing, deadzone, snap, alpha)

    def _snap_movement(self, movement: float, delta: float, snap_alpha: float) -> float:
        snap_target = delta * Clamp(snap_alpha, 0.0, 1.0)
        if abs(snap_target) > abs(movement):
            return snap_target
        return movement

    def _group_debug(
        self,
        axes: list[TorvixSmartMotionAxisDebug],
        magnitude: float,
        gain: float,
        smoothing: float,
        deadzone: float,
        snap: bool,
        alpha: float,
    ) -> dict[str, Any]:
        return {
            "axes": axes,
            "magnitude": SafeNumber(magnitude),
            "gain": SafeNumber(gain),
            "smoothing": SafeNumber(smoothing),
            "deadzone": SafeNumber(deadzone),
            "snap": bool(snap),
            "alpha": SafeNumber(alpha),
            "still_boost": 0.0,
        }

    def _axis_debug(
        self,
        raw: float,
        filtered: float,
        delta: float,
        gain: float,
        deadzone: float,
        smoothing: float = 0.0,
        alpha: float = 0.0,
        *,
        snap: bool = False,
        held: bool = False,
    ) -> TorvixSmartMotionAxisDebug:
        return TorvixSmartMotionAxisDebug(
            raw=SafeNumber(raw),
            filtered=SafeNumber(filtered),
            delta=SafeNumber(delta),
            gain=SafeNumber(gain),
            smoothing=SafeNumber(smoothing),
            deadzone=SafeNumber(deadzone),
            alpha=SafeNumber(alpha),
            snap=bool(snap),
            held=bool(held),
        )

    def _accept_raw(self, raw: list[float], delta_time: float, *, enabled: bool) -> None:
        self.lastPosition = raw[TX : TZ + 1]
        self.lastRotation = raw[YAW : ROLL + 1]
        self.lastRotationQuat = QuatFromYawPitchRoll(*self.lastRotation)
        self.lastOutput = raw.copy()
        self.lastRawInput = raw.copy()
        self.lastDelta = [0.0] * AXIS_COUNT
        self.filteredOutput = raw.copy()
        self.debugInfo = TorvixSmartMotionDebug(
            enabled=enabled,
            rotation_mode=self._rotation_mode(self.config),
            confidence=self.trackingConfidence,
            delta_time=delta_time,
            fps=1.0 / delta_time if delta_time > 0.0 else 0.0,
            axes=tuple(
                self._axis_debug(value, value, 0.0, 0.0, 0.0)
                for value in raw
            ),
        )

    def _rotation_mode(self, config: Any | None = None) -> str:
        mode = str(self._get_value(config or self.config, "motion_rotation_mode", QUATERNION_HAMILTON))
        return EULER_CLASSIC if mode == EULER_CLASSIC else QUATERNION_HAMILTON

    def _angle_delta(self, value: float, previous: float) -> float:
        delta = SafeNumber(value) - SafeNumber(previous)
        if abs(delta) > 180.0:
            delta -= Sign(delta) * 360.0
        return delta

    def _to_values(self, raw: PoseSample | Iterable[float]) -> list[float]:
        if isinstance(raw, PoseSample):
            return [
                SafeNumber(raw.x),
                SafeNumber(raw.y),
                SafeNumber(raw.z),
                SafeNumber(raw.yaw),
                SafeNumber(raw.pitch),
                SafeNumber(raw.roll),
            ]
        values = [SafeNumber(value) for value in raw]
        if len(values) < AXIS_COUNT:
            values.extend([0.0] * (AXIS_COUNT - len(values)))
        return values[:AXIS_COUNT]

    def _to_pose(self, values: list[float]) -> PoseSample:
        prepared = values[:AXIS_COUNT] + [0.0] * max(0, AXIS_COUNT - len(values))
        return PoseSample(
            yaw=prepared[YAW],
            pitch=prepared[PITCH],
            roll=prepared[ROLL],
            x=prepared[TX],
            y=prepared[TY],
            z=prepared[TZ],
        )

    def _get_value(self, config: Any | None, name: str, default: Any) -> Any:
        if config is None:
            return default
        return getattr(config, name, default)

    def _get_float(self, config: Any | None, name: str, default: float) -> float:
        return SafeNumber(self._get_value(config, name, default), default)

    def _get_int(self, config: Any | None, name: str, default: int) -> int:
        return max(0, int(round(self._get_float(config, name, float(default)))))

    def _get_bool(self, config: Any | None, name: str, default: bool) -> bool:
        return bool(self._get_value(config, name, default))
