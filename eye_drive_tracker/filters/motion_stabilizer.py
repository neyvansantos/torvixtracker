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
    def __init__(self) -> None:
        self.filtered = 0.0
        self.last_raw = 0.0
        self.still_frames = 0
        self.release_frames = 0
        self.state = "MOVING"
        self.initialized = False
        self.one_euro = OneEuroFilter()

    def reset(self) -> None:
        self.filtered = 0.0
        self.last_raw = 0.0
        self.still_frames = 0
        self.release_frames = 0
        self.state = "MOVING"
        self.initialized = False
        self.one_euro.reset()

    def initialize(self, value: float) -> None:
        self.filtered = float(value)
        self.last_raw = float(value)
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

        if self.state == "STILL":
            min_cutoff = 0.55 + (float(smoothing) * 0.45)
            filtered_input = self.one_euro.filter(raw, delta_seconds, min_cutoff=min_cutoff, beta=one_euro_beta * 0.45)
        else:
            min_cutoff = 0.85 + (float(smoothing) * 0.55)
            filtered_input = self.one_euro.filter(raw, delta_seconds, min_cutoff=min_cutoff, beta=one_euro_beta)

        raw_output_delta = raw - self.filtered
        filtered_delta = filtered_input - self.filtered
        quiet_frame = abs(frame_delta) <= movement_gate and abs(filtered_delta) <= (movement_gate * still_deadzone_multiplier)
        release_gate = max(movement_gate * release_multiplier, movement_gate + 0.20)
        if self.state == "MOVING" and (abs(raw_output_delta) > release_gate * 1.25 or float(smoothing) <= 0.05):
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
            else:
                self.still_frames = 0
                self.release_frames = 0

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
        smooth_factor = 1.0 - (_clamp(float(smoothing), 0.0, 1.0) * 0.65)
        if self.state == "STILL":
            alpha = _time_adjusted_alpha(alpha_still * smooth_factor, delta_seconds)
        else:
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
