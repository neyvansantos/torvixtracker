# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

import math
from dataclasses import dataclass


_DEFAULT_FRAME_RATE = 60.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _frame_delta_scale(delta_seconds: float | None) -> float:
    if delta_seconds is None:
        return 1.0
    delta = _clamp(float(delta_seconds), 1.0 / 240.0, 0.25)
    return _clamp(delta * _DEFAULT_FRAME_RATE, 0.25, 6.0)


def _time_adjusted_alpha(base_alpha: float, delta_seconds: float | None) -> float:
    alpha = _clamp(float(base_alpha), 0.001, 1.0)
    if delta_seconds is None:
        return alpha
    scale = _frame_delta_scale(delta_seconds)
    return _clamp(1.0 - ((1.0 - alpha) ** scale), 0.001, 1.0)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 0.85, beta: float = 0.22, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._value: float | None = None
        self._derivative = 0.0

    def reset(self) -> None:
        self._value = None
        self._derivative = 0.0

    def filter(self, value: float, delta_seconds: float | None, *, min_cutoff: float | None = None, beta: float | None = None) -> float:
        raw = float(value)
        if self._value is None:
            self._value = raw
            return raw

        dt = _clamp(float(delta_seconds or (1.0 / _DEFAULT_FRAME_RATE)), 1.0 / 240.0, 0.25)
        derivative = (raw - self._value) / dt
        derivative_alpha = self._alpha(dt, self.d_cutoff)
        self._derivative += (derivative - self._derivative) * derivative_alpha

        active_min_cutoff = self.min_cutoff if min_cutoff is None else float(min_cutoff)
        active_beta = self.beta if beta is None else float(beta)
        cutoff = max(0.001, active_min_cutoff + active_beta * abs(self._derivative))
        value_alpha = self._alpha(dt, cutoff)
        self._value += (raw - self._value) * value_alpha
        return self._value

    @staticmethod
    def _alpha(delta_seconds: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 0.001))
        return 1.0 / (1.0 + tau / max(delta_seconds, 1e-6))


@dataclass
class AxisStabilizerResult:
    value: float
    raw: float
    prefiltered: float
    threshold: float
    alpha: float
    state: str
    still_frames: int
    jitter_detected: bool
    spike_rejected: bool


class MotionAxisStabilizer:
    _ACCELA_STABLE_FRAMES = 4

    def __init__(self) -> None:
        self.filtered = 0.0
        self.last_raw = 0.0
        self.target_anchor = 0.0
        self.target_quiet_frames = 0
        self.still_frames = 0
        self.release_frames = 0
        self.state = "MOVING"
        self.initialized = False
        self.one_euro = OneEuroFilter()

    def reset(self) -> None:
        self.filtered = 0.0
        self.last_raw = 0.0
        self.target_anchor = 0.0
        self.target_quiet_frames = 0
        self.still_frames = 0
        self.release_frames = 0
        self.state = "MOVING"
        self.initialized = False
        self.one_euro.reset()

    def initialize(self, value: float) -> None:
        self.filtered = float(value)
        self.last_raw = float(value)
        self.target_anchor = float(value)
        self.target_quiet_frames = 0
        self.still_frames = 0
        self.release_frames = 0
        self.state = "MOVING"
        self.initialized = True
        self.one_euro.reset()
        self.one_euro.filter(value, None)

    def update(
        self,
        raw_value: float,
        delta_seconds: float | None,
        *,
        micro_jitter: float,
        smoothing: float,
        max_step: float,
        threshold_scale: float,
        threshold_floor: float,
        alpha_still: float,
        alpha_moving: float,
        confidence: float,
        distance_stability: float,
        still_frames_required: int,
        release_frames_required: int,
        still_deadzone_multiplier: float,
        release_multiplier: float,
        spike_multiplier: float,
        one_euro_beta: float,
    ) -> AxisStabilizerResult:
        raw = float(raw_value)
        base_threshold = max(max(0.0, float(micro_jitter)) * max(0.0, float(threshold_scale)), max(0.0, float(threshold_floor)))

        if not math.isfinite(raw):
            return AxisStabilizerResult(
                value=self.filtered,
                raw=self.last_raw,
                prefiltered=self.filtered,
                threshold=base_threshold,
                alpha=0.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=True,
                spike_rejected=True,
            )

        if not self.initialized:
            self.initialize(raw)
            return AxisStabilizerResult(
                value=raw,
                raw=raw,
                prefiltered=raw,
                threshold=base_threshold,
                alpha=1.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=False,
                spike_rejected=False,
            )

        confidence_factor = 1.0 + ((1.0 - _clamp(confidence, 0.0, 1.0)) * 0.80)
        distance_factor = 1.0 + ((1.0 - _clamp(distance_stability, 0.0, 1.0)) * 0.55)
        dynamic_threshold = base_threshold * confidence_factor * distance_factor
        movement_gate = max(dynamic_threshold, threshold_floor)

        filtered_delta_before = raw - self.filtered
        frame_delta = raw - self.last_raw
        self.last_raw = raw

        scaled_max_step = max(0.0, float(max_step)) * _frame_delta_scale(delta_seconds)
        spike_limit = max(max(0.0, float(max_step)) * max(1.0, float(spike_multiplier)), movement_gate * 7.5, 3.0)
        spike_rejected = scaled_max_step > 0.0 and abs(frame_delta) > spike_limit and abs(filtered_delta_before) > spike_limit
        if spike_rejected:
            self.still_frames = min(self.still_frames + 1, still_frames_required)
            if self.still_frames >= still_frames_required:
                self.state = "STILL"
            return AxisStabilizerResult(
                value=self.filtered,
                raw=raw,
                prefiltered=self.filtered,
                threshold=movement_gate,
                alpha=0.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=True,
                spike_rejected=True,
            )

        raw_for_filter = self._accela_target(raw, frame_delta, movement_gate)
        if self.state == "STILL":
            min_cutoff = 0.55 + (float(smoothing) * 0.45)
            filtered_input = self.one_euro.filter(
                raw_for_filter,
                delta_seconds,
                min_cutoff=min_cutoff,
                beta=one_euro_beta * 0.45,
            )
        else:
            min_cutoff = 0.85 + (float(smoothing) * 0.55)
            filtered_input = self.one_euro.filter(raw_for_filter, delta_seconds, min_cutoff=min_cutoff, beta=one_euro_beta)

        raw_output_delta = raw - self.filtered
        filtered_delta = filtered_input - self.filtered
        quiet_frame = abs(frame_delta) <= movement_gate and abs(filtered_delta) <= (movement_gate * still_deadzone_multiplier)
        release_gate = max(movement_gate * release_multiplier, movement_gate + 0.20)
        released_now = False
        if self.state == "MOVING" and (abs(raw_output_delta) > release_gate * 0.90 or float(smoothing) <= 0.05):
            filtered_input = raw
            filtered_delta = raw_output_delta
        if quiet_frame:
            self.still_frames = min(self.still_frames + 1, still_frames_required)
            self.release_frames = 0
            if self.still_frames >= still_frames_required:
                self.state = "STILL"
        else:
            if self.state == "STILL":
                if abs(raw_output_delta) <= release_gate:
                    self.release_frames = 0
                    self.still_frames = still_frames_required
                else:
                    self.release_frames += 1
                    if self.release_frames >= release_frames_required:
                        self.state = "MOVING"
                        self.still_frames = 0
                        self.release_frames = 0
                        released_now = True
            else:
                self.still_frames = 0
                self.release_frames = 0

        if released_now:
            filtered_input = raw
            filtered_delta = raw_output_delta

        if quiet_frame and abs(filtered_delta) <= release_gate:
            return AxisStabilizerResult(
                value=self.filtered,
                raw=raw,
                prefiltered=filtered_input,
                threshold=movement_gate,
                alpha=0.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=True,
                spike_rejected=False,
            )

        if self.state == "STILL" and abs(raw_output_delta) <= release_gate:
            return AxisStabilizerResult(
                value=self.filtered,
                raw=raw,
                prefiltered=filtered_input,
                threshold=movement_gate,
                alpha=0.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=True,
                spike_rejected=False,
            )

        movement_ratio = 1.0 if movement_gate <= 0.0 else _clamp(abs(filtered_delta) / max(movement_gate * 6.0, 0.001), 0.0, 1.0)
        smooth_factor = 1.0 - (_clamp(float(smoothing), 0.0, 1.0) * 0.45)
        if self.state == "STILL" and abs(raw_output_delta) <= release_gate:
            return AxisStabilizerResult(
                value=self.filtered,
                raw=raw,
                prefiltered=filtered_input,
                threshold=movement_gate,
                alpha=0.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=True,
                spike_rejected=False,
            )
        if self.state == "STILL":
            return AxisStabilizerResult(
                value=self.filtered,
                raw=raw,
                prefiltered=filtered_input,
                threshold=movement_gate,
                alpha=0.0,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=True,
                spike_rejected=False,
            )

        moving_alpha = alpha_still + ((alpha_moving - alpha_still) * movement_ratio)
        alpha = _time_adjusted_alpha(moving_alpha * smooth_factor, delta_seconds)

        output = self.filtered + (filtered_input - self.filtered) * alpha
        if scaled_max_step > 0.0:
            output = _clamp(output, self.filtered - scaled_max_step, self.filtered + scaled_max_step)
        self.filtered = output
        return AxisStabilizerResult(
            value=output,
            raw=raw,
            prefiltered=filtered_input,
            threshold=movement_gate,
            alpha=alpha,
            state=self.state,
            still_frames=self.still_frames,
            jitter_detected=False,
            spike_rejected=False,
        )

    def _accela_target(self, raw: float, frame_delta: float, movement_gate: float) -> float:
        target_gate = max(float(movement_gate) * 4.0, 0.55)
        anchor_release = max(target_gate * 2.2, float(movement_gate) * 7.0, 1.25)

        if abs(frame_delta) <= target_gate and abs(raw - self.target_anchor) <= anchor_release:
            self.target_quiet_frames = min(self.target_quiet_frames + 1, self._ACCELA_STABLE_FRAMES)
            if self.target_quiet_frames >= self._ACCELA_STABLE_FRAMES:
                self.target_anchor += (raw - self.target_anchor) * 0.12
                return self.target_anchor
        else:
            self.target_anchor = raw
            self.target_quiet_frames = 0

        return raw


class AccelaVectorStabilizer:
    def __init__(self, axis_count: int = 3) -> None:
        self.axis_count = max(1, int(axis_count))
        self.filtered = [0.0] * self.axis_count
        self.last_raw = [0.0] * self.axis_count
        self.still_frames = 0
        self.state = "MOVING"
        self.initialized = False

    def reset(self) -> None:
        self.filtered = [0.0] * self.axis_count
        self.last_raw = [0.0] * self.axis_count
        self.still_frames = 0
        self.state = "MOVING"
        self.initialized = False

    def initialize(self, values: list[float] | tuple[float, ...]) -> None:
        prepared = [float(value) for value in values[: self.axis_count]]
        if len(prepared) < self.axis_count:
            prepared.extend([0.0] * (self.axis_count - len(prepared)))
        self.filtered = prepared.copy()
        self.last_raw = prepared.copy()
        self.still_frames = 0
        self.state = "MOVING"
        self.initialized = True

    def update(
        self,
        raw_values: list[float] | tuple[float, ...],
        delta_seconds: float | None,
        *,
        micro_jitter: float,
        smoothing: float,
        max_step: float,
        threshold_scales: list[float] | tuple[float, ...],
        threshold_floors: list[float] | tuple[float, ...],
        confidence: float,
        distance_stability: float,
        still_frames_required: int,
        spike_multiplier: float,
    ) -> list[AxisStabilizerResult]:
        raw = [float(value) for value in raw_values[: self.axis_count]]
        if len(raw) < self.axis_count:
            raw.extend([0.0] * (self.axis_count - len(raw)))

        scales = self._expanded(threshold_scales, 1.0)
        floors = self._expanded(threshold_floors, 0.0)
        thresholds = self._thresholds(micro_jitter, scales, floors, confidence, distance_stability)

        if not all(math.isfinite(value) for value in raw):
            return [
                AxisStabilizerResult(
                    value=self.filtered[index],
                    raw=self.last_raw[index],
                    prefiltered=self.filtered[index],
                    threshold=thresholds[index],
                    alpha=0.0,
                    state=self.state,
                    still_frames=self.still_frames,
                    jitter_detected=True,
                    spike_rejected=True,
                )
                for index in range(self.axis_count)
            ]

        if not self.initialized:
            self.initialize(raw)
            return [
                AxisStabilizerResult(
                    value=raw[index],
                    raw=raw[index],
                    prefiltered=raw[index],
                    threshold=thresholds[index],
                    alpha=1.0,
                    state=self.state,
                    still_frames=self.still_frames,
                    jitter_detected=False,
                    spike_rejected=False,
                )
                for index in range(self.axis_count)
            ]

        dt = _clamp(float(delta_seconds or (1.0 / _DEFAULT_FRAME_RATE)), 1.0 / 240.0, 0.25)
        frame_scale = _frame_delta_scale(delta_seconds)
        filtered_before = self.filtered.copy()
        raw_deltas = [self._angle_delta(raw[index], self.filtered[index]) for index in range(self.axis_count)]
        frame_deltas = [self._angle_delta(raw[index], self.last_raw[index]) for index in range(self.axis_count)]
        self.last_raw = raw.copy()

        spike_rejected = [False] * self.axis_count
        active_deltas = [0.0] * self.axis_count
        for index in range(self.axis_count):
            threshold = thresholds[index]
            spike_limit = max(max(0.0, float(max_step)) * max(1.0, float(spike_multiplier)), threshold * 7.5, 3.0)
            if max_step > 0.0 and abs(frame_deltas[index]) > spike_limit and abs(raw_deltas[index]) > spike_limit:
                spike_rejected[index] = True
                continue
            if abs(raw_deltas[index]) > threshold:
                active_deltas[index] = raw_deltas[index] - math.copysign(threshold, raw_deltas[index])

        distance = math.sqrt(sum(delta * delta for delta in active_deltas))
        if distance <= 1e-6:
            self.still_frames = min(self.still_frames + 1, still_frames_required)
            if self.still_frames >= still_frames_required:
                self.state = "STILL"
            return [
                AxisStabilizerResult(
                    value=self.filtered[index],
                    raw=raw[index],
                    prefiltered=self.filtered[index],
                    threshold=thresholds[index],
                    alpha=0.0,
                    state=self.state,
                    still_frames=self.still_frames,
                    jitter_detected=True,
                    spike_rejected=spike_rejected[index],
                )
                for index in range(self.axis_count)
            ]

        self.state = "MOVING"
        self.still_frames = 0
        mean_threshold = max(sum(thresholds) / len(thresholds), 0.001)
        normalized_distance = distance / max(mean_threshold * 5.0, 0.10)
        curve = self._gain_curve(normalized_distance)
        smooth = _clamp(float(smoothing), 0.0, 1.0)
        response = 1.0 - (smooth * 0.42)
        max_speed = (max(0.0, float(max_step)) * _DEFAULT_FRAME_RATE) if max_step > 0.0 else 900.0
        min_speed = 36.0 * response
        speed = (min_speed + (max_speed - min_speed) * curve) * response
        step = min(distance, speed * dt)
        if max_step > 0.0:
            step = min(step, max(0.0, float(max_step)) * frame_scale)
        alpha = 1.0 if distance <= 1e-6 else _clamp(step / distance, 0.0, 1.0)

        for index in range(self.axis_count):
            self.filtered[index] += active_deltas[index] * alpha
            self.filtered[index] = self._wrap_angle(self.filtered[index])

        return [
            AxisStabilizerResult(
                value=self.filtered[index],
                raw=raw[index],
                prefiltered=filtered_before[index] + active_deltas[index],
                threshold=thresholds[index],
                alpha=alpha,
                state=self.state,
                still_frames=self.still_frames,
                jitter_detected=False,
                spike_rejected=spike_rejected[index],
            )
            for index in range(self.axis_count)
        ]

    def _expanded(self, values: list[float] | tuple[float, ...], default: float) -> list[float]:
        prepared = [float(value) for value in values[: self.axis_count]]
        if len(prepared) < self.axis_count:
            prepared.extend([float(default)] * (self.axis_count - len(prepared)))
        return prepared

    def _thresholds(
        self,
        micro_jitter: float,
        threshold_scales: list[float],
        threshold_floors: list[float],
        confidence: float,
        distance_stability: float,
    ) -> list[float]:
        confidence_factor = 1.0 + ((1.0 - _clamp(confidence, 0.0, 1.0)) * 0.80)
        distance_factor = 1.0 + ((1.0 - _clamp(distance_stability, 0.0, 1.0)) * 0.55)
        return [
            max(max(0.0, float(micro_jitter)) * max(0.0, threshold_scales[index]), max(0.0, threshold_floors[index]))
            * confidence_factor
            * distance_factor
            for index in range(self.axis_count)
        ]

    @staticmethod
    def _gain_curve(value: float) -> float:
        normalized = max(0.0, float(value))
        curved = normalized * normalized
        return _clamp(curved / (1.0 + curved), 0.0, 1.0)

    @staticmethod
    def _angle_delta(value: float, previous: float) -> float:
        delta = float(value) - float(previous)
        if abs(delta) > 180.0:
            delta -= math.copysign(360.0, delta)
        return delta

    @staticmethod
    def _wrap_angle(value: float) -> float:
        wrapped = (float(value) + 180.0) % 360.0 - 180.0
        return 180.0 if math.isclose(wrapped, -180.0) else wrapped
