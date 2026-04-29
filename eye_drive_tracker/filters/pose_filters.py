from __future__ import annotations

import logging
import math
import os
import time
from collections import deque
from dataclasses import dataclass, field, replace

from eye_drive_tracker.profiles.profile import TrackingConfig
from eye_drive_tracker.tracking.models import GazeSample, PoseSample

from .extended_view import clamp
from .motion_stabilizer import AccelaVectorStabilizer, AxisStabilizerResult, MotionAxisStabilizer
from .smart_motion import TorvixSmartMotionDebug, TorvixSmartMotionFilter


@dataclass
class ExtendedAxisDebug:
    normalized_input: float = 0.0
    curve_value: float = 0.0
    before_smoothing: float = 0.0
    after_smoothing: float = 0.0


@dataclass
class ExtendedViewDebug:
    yaw: ExtendedAxisDebug = field(default_factory=ExtendedAxisDebug)
    pitch: ExtendedAxisDebug = field(default_factory=ExtendedAxisDebug)
    final: PoseSample = field(default_factory=PoseSample)


@dataclass
class GazeDebug:
    raw_yaw: float = 0.0
    raw_pitch: float = 0.0
    confidence: float = 0.0
    source: str = "disabled"
    missing_frames: int = 0
    face_confidence: float = 0.0
    iris_confidence: float = 0.0
    head_confidence: float = 0.0
    final_confidence: float = 0.0
    head_weight: float = 1.0
    gaze_weight: float = 0.0
    user_distance: float = 0.0
    iris_lost: bool = False


@dataclass
class FinalAxisDebug:
    state: str = "MOVING"
    raw: float = 0.0
    previous: float = 0.0
    prefiltered: float = 0.0
    filtered: float = 0.0
    delta: float = 0.0
    threshold: float = 0.0
    alpha: float = 1.0
    still_frames: int = 0
    jitter_detected: bool = False
    spike_rejected: bool = False


@dataclass
class OutputStabilizationDebug:
    yaw: FinalAxisDebug = field(default_factory=FinalAxisDebug)
    pitch: FinalAxisDebug = field(default_factory=FinalAxisDebug)
    roll: FinalAxisDebug = field(default_factory=FinalAxisDebug)


@dataclass(frozen=True)
class ExtendedViewSettings:
    strength: float
    exponent: float
    inflection_point: float
    start_point: float
    end_point: float
    acceleration: float
    max_angle: float
    smoothing: float
    previous: float = 0.0
    delta_seconds: float | None = None


@dataclass
class PipelineOutput:
    head: PoseSample
    gaze: PoseSample
    extended: PoseSample
    final: PoseSample
    gaze_debug: GazeDebug = field(default_factory=GazeDebug)
    extended_debug: ExtendedViewDebug = field(default_factory=ExtendedViewDebug)
    stabilization_debug: OutputStabilizationDebug = field(default_factory=OutputStabilizationDebug)
    motion_debug: TorvixSmartMotionDebug = field(default_factory=TorvixSmartMotionDebug)


@dataclass
class _FinalAxisState:
    filtered: float = 0.0
    last_raw: float = 0.0
    still_frames: int = 0
    release_frames: int = 0
    state: str = "MOVING"
    initialized: bool = False


def _sign(value: float) -> float:
    if value < 0.0:
        return -1.0
    if value > 0.0:
        return 1.0
    return 0.0


_DEFAULT_FRAME_RATE = 60.0
_STABILIZATION_LOGGER: logging.Logger | None = None


def _stabilization_debug_enabled() -> bool:
    return os.environ.get("TORVIX_STABILIZATION_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _stabilization_logger() -> logging.Logger:
    global _STABILIZATION_LOGGER
    if _STABILIZATION_LOGGER is not None:
        return _STABILIZATION_LOGGER
    logger = logging.getLogger("eye_drive_tracker.filters.stabilization")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    _STABILIZATION_LOGGER = logger
    return logger


class _AxisKalman:
    def __init__(self, process_noise: float = 0.010, measurement_noise: float = 0.035) -> None:
        self.process_noise = float(process_noise)
        self.measurement_noise = float(measurement_noise)
        self.position = 0.0
        self.velocity = 0.0
        self.p00 = 1.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 1.0
        self.initialized = False

    def reset(self) -> None:
        self.position = 0.0
        self.velocity = 0.0
        self.p00 = 1.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 1.0
        self.initialized = False

    def update(self, measurement: float, delta_seconds: float | None, confidence: float) -> float:
        value = float(measurement)
        if not self.initialized:
            self.position = value
            self.velocity = 0.0
            self.initialized = True
            return value

        dt = clamp(float(delta_seconds or (1.0 / _DEFAULT_FRAME_RATE)), 1.0 / 240.0, 0.25)

        self.position += self.velocity * dt
        q = self.process_noise * _frame_delta_scale(dt)
        p00 = self.p00 + dt * (self.p10 + self.p01) + (dt * dt * self.p11) + q
        p01 = self.p01 + dt * self.p11
        p10 = self.p10 + dt * self.p11
        p11 = self.p11 + q * 0.25

        confidence = clamp(float(confidence), 0.05, 1.0)
        r = self.measurement_noise / confidence
        residual = value - self.position
        s = max(p00 + r, 1e-6)
        k0 = p00 / s
        k1 = p10 / s

        self.position += k0 * residual
        self.velocity += k1 * residual
        self.p00 = (1.0 - k0) * p00
        self.p01 = (1.0 - k0) * p01
        self.p10 = p10 - k1 * p00
        self.p11 = p11 - k1 * p01
        return self.position


def _wrap_angle(value: float) -> float:
    wrapped = (float(value) + 180.0) % 360.0 - 180.0
    return 180.0 if math.isclose(wrapped, -180.0) else wrapped


def _normalize_pitch(value: float) -> float:
    pitch = _wrap_angle(value)
    if pitch < -90.0:
        pitch += 180.0
    elif pitch > 90.0:
        pitch -= 180.0
    return pitch


def _signed_curve(value: float, transform) -> float:
    sign = _sign(value)
    return sign * transform(abs(value))


def applyDeadzone(value: float, deadzone: float) -> float:
    threshold = max(0.0, float(deadzone))
    magnitude = abs(float(value))
    if magnitude <= threshold:
        return 0.0
    return _sign(value) * (magnitude - threshold)


def normalizeInput(
    value: float,
    max_angle: float,
    positive_reference: float | None = None,
    negative_reference: float | None = None,
) -> float:
    reference = positive_reference if value >= 0.0 else negative_reference
    if reference is None or abs(reference) <= 0.001:
        reference = max_angle
    reference = max(abs(reference), 0.001)
    return float(value) / reference


def _reference_for_signed_value(value: float, references: tuple[float | None, ...]) -> float | None:
    value_sign = _sign(value)
    if value_sign == 0.0:
        return None

    matching = [
        float(reference)
        for reference in references
        if reference is not None and abs(float(reference)) > 0.001 and _sign(float(reference)) == value_sign
    ]
    if not matching:
        return None
    return max(matching, key=lambda reference: abs(reference))


def _normalize_calibrated_input(
    value: float,
    max_angle: float,
    positive_reference: float | None = None,
    negative_reference: float | None = None,
) -> float:
    reference = _reference_for_signed_value(value, (positive_reference, negative_reference))
    if reference is None:
        reference = max_angle
    return float(value) / max(abs(float(reference)), 0.001)


def applyStartEndPoint(value: float, start_point: float, end_point: float) -> float:
    start = clamp(float(start_point), 0.0, 0.999)
    end = clamp(float(end_point), 0.001, 1.0)
    if end <= start:
        end = min(1.0, start + 0.001)

    def transform(magnitude: float) -> float:
        if magnitude <= start:
            return 0.0
        return (magnitude - start) / (end - start)

    return _signed_curve(value, transform)


def applyExponentCurve(value: float, exponent: float) -> float:
    power = max(0.05, float(exponent))
    return _signed_curve(value, lambda magnitude: magnitude**power)


def applyInflectionCurve(value: float, inflection_point: float) -> float:
    inflection = clamp(float(inflection_point), 0.001, 0.999)

    def transform(magnitude: float) -> float:
        if magnitude <= inflection:
            return 0.5 * (magnitude / inflection)
        return 0.5 + 0.5 * ((magnitude - inflection) / (1.0 - inflection))

    return _signed_curve(value, transform)


def _frame_delta_scale(delta_seconds: float | None) -> float:
    if delta_seconds is None:
        return 1.0
    delta = clamp(float(delta_seconds), 1.0 / 240.0, 0.25)
    return clamp(delta * _DEFAULT_FRAME_RATE, 0.25, 6.0)


def _time_adjusted_alpha(base_alpha: float, delta_seconds: float | None, velocity_factor: float = 1.0) -> float:
    if delta_seconds is None:
        return clamp(float(base_alpha) * velocity_factor, 0.001, 1.0)
    
    # Ajusta o alpha com base no tempo decorrido e na velocidade do movimento
    # Quanto maior a velocidade, maior o alpha (menos suavização)
    scaled_base = clamp(float(base_alpha) * velocity_factor, 0.001, 1.0)
    scale = _frame_delta_scale(delta_seconds)
    return clamp(1.0 - ((1.0 - scaled_base) ** scale), 0.001, 1.0)


def applyResponsiveness(
    value: float,
    previous: float,
    responsiveness: float,
    smoothing: float,
    delta_seconds: float | None = None,
) -> float:
    response = max(0.0, float(responsiveness))
    if response <= 0.0:
        return previous

    delta = abs(float(value) - previous)
    
    # Fator de velocidade dinâmico: 
    # Se o movimento for muito pequeno (jitter), o fator diminui drasticamente.
    # Se o movimento for grande, o fator aumenta para 1.0 (resposta total).
    jitter_threshold = 0.005 # Valor normalizado (0-1)
    velocity_factor = clamp(delta / jitter_threshold, 0.35, 1.0) if delta < jitter_threshold else 1.0

    smooth = clamp(float(smoothing), 0.0, 1.0)
    # Suavização base: quanto mais 'smooth', menor o alpha inicial
    base_alpha = clamp((1.0 - smooth * 0.98) * response, 0.001, 1.0)
    
    alpha = _time_adjusted_alpha(base_alpha, delta_seconds, velocity_factor)
    return previous + (float(value) - previous) * alpha


def applyAxisMultiplier(value: float, multiplier: float, _max_angle: float = 180.0) -> float:
    return float(value) * float(multiplier)


def applyExtendedView(inputAngle: float, maxInputAngle: float, settings: ExtendedViewSettings) -> float:
    return _calculate_extended_axis(inputAngle, maxInputAngle, settings).after_smoothing


def combineHeadAndGaze(
    head_pose: PoseSample,
    gaze_pose: PoseSample,
    extended_pose: PoseSample,
    config: TrackingConfig,
) -> PoseSample:
    return PoseSample(
        yaw=head_pose.yaw + gaze_pose.yaw + extended_pose.yaw,
        pitch=head_pose.pitch + gaze_pose.pitch + extended_pose.pitch,
        roll=head_pose.roll,
        x=head_pose.x,
        y=head_pose.y,
        z=head_pose.z,
    )


def _calculate_extended_axis(
    input_angle: float,
    max_input_angle: float,
    settings: ExtendedViewSettings,
) -> ExtendedAxisDebug:
    max_input = max(abs(float(max_input_angle)), 0.001)
    max_output = max(float(settings.max_angle), 0.0)
    strength = max(float(settings.strength), 0.0)
    normalized = clamp(float(input_angle) / max_input, -1.0, 1.0)
    sign = _sign(normalized)
    abs_value = abs(normalized)

    start = clamp(float(settings.start_point), 0.0, 0.999)
    end = clamp(float(settings.end_point), 0.001, 1.0)
    if end <= start:
        end = min(1.0, start + 0.001)

    range_value = 0.0
    if abs_value >= start:
        range_value = clamp((abs_value - start) / (end - start), 0.0, 1.0)

    exponent = max(float(settings.exponent), 0.05)
    inflection = clamp(float(settings.inflection_point), 0.001, 0.999)
    acceleration = max(float(settings.acceleration), 0.05)

    if range_value <= 0.0 or strength <= 0.0 or max_output <= 0.0:
        curved = 0.0
    elif range_value < inflection:
        curved = (range_value / inflection) ** exponent * inflection
    else:
        t = (range_value - inflection) / (1.0 - inflection)
        curved = inflection + (t**acceleration) * (1.0 - inflection)

    signed_curve = sign * clamp(curved, 0.0, 1.0)
    before_smoothing = clamp(signed_curve * max_output * strength, -max_output, max_output)
    after_smoothing = _smooth_value(
        settings.previous,
        before_smoothing,
        settings.smoothing,
        settings.delta_seconds,
    )
    after_smoothing = clamp(after_smoothing, -max_output, max_output)
    return ExtendedAxisDebug(
        normalized_input=normalized,
        curve_value=signed_curve,
        before_smoothing=before_smoothing,
        after_smoothing=after_smoothing,
    )


def _smooth_value(
    previous: float,
    target: float,
    smoothing: float,
    delta_seconds: float | None = None,
) -> float:
    smooth = clamp(float(smoothing), 0.0, 1.0)
    alpha = _time_adjusted_alpha(1.0 - smooth * 0.95, delta_seconds)
    return float(previous) + (float(target) - float(previous)) * alpha


class PoseFilter:
    _TRANSLATION_MAX_CM = 30.0
    _TRANSLATION_MIN_RESPONSIVENESS = 0.45
    _TRANSLATION_MIN_SMOOTHING = 0.10
    _OUTPUT_TRANSLATION_JITTER_CM = 0.04
    _OUTPUT_TRANSLATION_MAX_STEP_CM = 0.90
    _FINAL_STILL_FRAMES = 8
    _FINAL_SPIKE_MULTIPLIER = 2.5
    _FINAL_STILL_RELEASE_FRAMES = 2
    _FINAL_STILL_RELEASE_MULTIPLIER = 3.2
    _GAZE_CONFIDENCE_THRESHOLD = 0.18
    _GAZE_HOLD_FRAMES = 10
    _RECENTER_SAMPLE_WINDOW = 15

    def __init__(self) -> None:
        self.center = PoseSample()
        self.previous_raw = PoseSample()
        self.previous_head_normalized = PoseSample()
        self.previous_head_translation = PoseSample()
        self.previous_gaze = PoseSample()
        self._gaze_missing_frames = 0
        self._gaze_yaw_kalman = _AxisKalman()
        self._gaze_pitch_kalman = _AxisKalman()
        self._gaze_distance_reference = 0.0
        self._gaze_distance_smoothed = 0.0
        self.previous_extended = PoseSample()
        self.previous_final = PoseSample()
        self._blend_head_weight = 1.0
        self._blend_gaze_weight = 0.0
        self._recenter_samples: deque[PoseSample] = deque(maxlen=self._RECENTER_SAMPLE_WINDOW)
        self._has_center = False
        self._has_raw_previous = False
        self._has_head_previous = False
        self._has_final_previous = False
        self._last_process_time: float | None = None
        self._last_stabilization_log_time = 0.0
        self._final_yaw_state = _FinalAxisState()
        self._final_pitch_state = _FinalAxisState()
        self._final_roll_state = _FinalAxisState()
        self._motion_yaw = MotionAxisStabilizer()
        self._motion_pitch = MotionAxisStabilizer()
        self._motion_roll = MotionAxisStabilizer()
        self._motion_rotation = AccelaVectorStabilizer(3)
        self.smart_motion_filter = TorvixSmartMotionFilter()

    def reset(self) -> None:
        self.center = PoseSample()
        self.previous_raw = PoseSample()
        self.previous_head_normalized = PoseSample()
        self.previous_head_translation = PoseSample()
        self.previous_gaze = PoseSample()
        self._gaze_missing_frames = 0
        self._reset_gaze_signal_state()
        self.previous_extended = PoseSample()
        self.previous_final = PoseSample()
        self._blend_head_weight = 1.0
        self._blend_gaze_weight = 0.0
        self._recenter_samples.clear()
        self._has_center = False
        self._has_raw_previous = False
        self._has_head_previous = False
        self._has_final_previous = False
        self._last_process_time = None
        self._last_stabilization_log_time = 0.0
        self._reset_final_stabilization()

    def recenter(self, raw_pose: PoseSample | None = None) -> None:
        self.center = self.estimate_stable_center(raw_pose)
        self.previous_head_normalized = PoseSample()
        self.previous_head_translation = PoseSample()
        self.previous_gaze = PoseSample()
        self._gaze_missing_frames = 0
        self._reset_gaze_signal_state()
        self.previous_extended = PoseSample()
        self.previous_final = PoseSample()
        self._blend_head_weight = 1.0
        self._blend_gaze_weight = 0.0
        self._has_center = raw_pose is not None or bool(self._recenter_samples)
        self._has_head_previous = False
        self._has_final_previous = False
        self._has_raw_previous = False
        self._last_process_time = None
        self._last_stabilization_log_time = 0.0
        self._reset_final_stabilization()

    def _reset_gaze_signal_state(self) -> None:
        self._gaze_yaw_kalman.reset()
        self._gaze_pitch_kalman.reset()
        self._gaze_distance_reference = 0.0
        self._gaze_distance_smoothed = 0.0

    def _reset_final_stabilization(self) -> None:
        self._final_yaw_state = _FinalAxisState()
        self._final_pitch_state = _FinalAxisState()
        self._final_roll_state = _FinalAxisState()
        self._motion_yaw.reset()
        self._motion_pitch.reset()
        self._motion_roll.reset()
        self._motion_rotation.reset()
        self.smart_motion_filter.reset()

    def estimate_stable_center(self, raw_pose: PoseSample | None = None) -> PoseSample:
        if self._recenter_samples:
            samples = list(self._recenter_samples)
            if raw_pose is not None:
                samples.append(raw_pose)
            samples = samples[-self._RECENTER_SAMPLE_WINDOW :]
            samples.sort(key=lambda pose: abs(pose.yaw) + abs(pose.pitch) + abs(pose.roll))
            stable = samples[: max(5, len(samples) // 2)] if len(samples) >= 5 else samples
            count = max(len(stable), 1)
            return PoseSample(
                yaw=sum(sample.yaw for sample in stable) / count,
                pitch=sum(sample.pitch for sample in stable) / count,
                roll=sum(sample.roll for sample in stable) / count,
                x=sum(sample.x for sample in stable) / count,
                y=sum(sample.y for sample in stable) / count,
                z=sum(sample.z for sample in stable) / count,
            )
        return replace(raw_pose) if raw_pose is not None else PoseSample()

    def process(
        self,
        raw_pose: PoseSample,
        config: TrackingConfig,
        raw_gaze: GazeSample | None = None,
    ) -> PipelineOutput:
        now = time.monotonic()
        delta_seconds = None if self._last_process_time is None else max(0.0, now - self._last_process_time)
        self._last_process_time = now

        # ------------------------------------------------------------------
        # Rejeicao de spike: descarta frames onde o MediaPipe emite valores
        # absurdos em um unico frame (ex: yaw salta de 3° para 15° de uma vez).
        # O limiar e calculado em graus brutos (antes de qualquer normalizacao).
        # ------------------------------------------------------------------
        if self._has_raw_previous:
            raw_pose = self._reject_spike(raw_pose, self.previous_raw, delta_seconds)
        self.previous_raw = raw_pose
        self._recenter_samples.append(replace(raw_pose))
        self._has_raw_previous = True

        if not self._has_center:
            if config.calibration_center_set:
                self.center = PoseSample(
                    yaw=config.calibration_center_yaw,
                    pitch=_normalize_pitch(config.calibration_center_pitch),
                    roll=config.calibration_center_roll,
                    x=raw_pose.x if config.calibration_center_x is None else config.calibration_center_x,
                    y=raw_pose.y if config.calibration_center_y is None else config.calibration_center_y,
                    z=raw_pose.z if config.calibration_center_z is None else config.calibration_center_z,
                )
                self._has_center = True
            else:
                self.recenter(raw_pose)

        delta = PoseSample(
            yaw=raw_pose.yaw - self.center.yaw,
            pitch=raw_pose.pitch - self.center.pitch,
            roll=raw_pose.roll - self.center.roll,
            x=raw_pose.x - self.center.x,
            y=raw_pose.y - self.center.y,
            z=raw_pose.z - self.center.z,
        )

        smart_confidence = self._smart_motion_confidence(raw_gaze)
        filtered_delta = self.smart_motion_filter.update(delta, delta_seconds, smart_confidence, config)

        head = self._process_head(filtered_delta, config, delta_seconds)
        gaze, gaze_debug = self._process_gaze(head, raw_gaze, config, delta_seconds)
        extended, extended_debug = self._process_extended(head, config, delta_seconds)
        combined = self._combine_head_and_gaze(head, gaze, extended, gaze_debug, config, delta_seconds)
        final, stabilization_debug = self._stabilize_output(combined, config, delta_seconds)
        self._maybe_log_stabilization(combined, final, stabilization_debug)
        extended_debug.final = final
        return PipelineOutput(
            head=head,
            gaze=gaze,
            extended=extended,
            final=final,
            gaze_debug=gaze_debug,
            extended_debug=extended_debug,
            stabilization_debug=stabilization_debug,
            motion_debug=self.smart_motion_filter.getDebugData(),
        )

    @staticmethod
    def _reject_spike(
        current: PoseSample,
        previous: PoseSample,
        delta_seconds: float | None,
    ) -> tuple[PoseSample, OutputStabilizationDebug]:
        """Descarta/limita frames com saltos angulares impossíveis.

        Um salto e considerado spike se o valor bruto mudar mais do que
        `max_step_deg` graus em um unico frame. Nesse caso, o valor e
        substituido pelo anterior (frame congelado), evitando o repasse
        do erro para o filtro de suavizacao.

        O limiar de 18° por frame (a 30fps) corresponde a 540°/s — velocidade
        de rotacao de cabeca fisicamente impossivel de manter.
        """
        # Limiar adaptativo ao frame rate: 540 graus/segundo maximo
        # A 30fps → 18°/frame; a 60fps → 9°/frame
        fps = 1.0 / max(delta_seconds, 1.0 / 240.0) if delta_seconds and delta_seconds > 0 else 30.0
        max_step_deg = 540.0 / max(fps, 1.0)

        yaw_ok   = abs(current.yaw   - previous.yaw)   <= max_step_deg
        pitch_ok = abs(current.pitch - previous.pitch) <= max_step_deg
        roll_ok  = abs(current.roll  - previous.roll)  <= max_step_deg * 2.0  # roll e mais volátil

        if yaw_ok and pitch_ok and roll_ok:
            return current  # frame normal, nao alterado

        # Spike detectado: usa o valor anterior para o eixo que saltou
        return PoseSample(
            yaw=current.yaw   if yaw_ok   else previous.yaw,
            pitch=current.pitch if pitch_ok else previous.pitch,
            roll=current.roll  if roll_ok  else previous.roll,
            x=current.x,
            y=current.y,
            z=current.z,
        )

    def apply(self, raw_pose: PoseSample, config: TrackingConfig, raw_gaze: GazeSample | None = None) -> PoseSample:
        return self.process(raw_pose, config, raw_gaze).final

    def _process_head(
        self,
        delta: PoseSample,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> PoseSample:
        yaw_multiplier = (
            config.head_yaw_sensitivity_walk
            if config.tracking_context == "walk"
            else config.head_yaw_sensitivity_cabin
        )
        pitch_multiplier = (
            config.head_pitch_sensitivity_walk
            if config.tracking_context == "walk"
            else config.head_pitch_sensitivity_cabin
        )

        normalized = PoseSample(
            yaw=self._process_axis_to_normalized(
                delta.yaw,
                config,
                exponent=config.head_tracking_exponent,
                inflection_point=config.head_tracking_inflection_point,
                start_point=config.head_tracking_start_point,
                end_point=config.head_tracking_end_point,
                responsiveness=config.head_view_responsiveness,
                smoothing=config.head_view_smoothing,
                previous=self.previous_head_normalized.yaw,
                positive_reference=self._positive_yaw_reference(config),
                negative_reference=self._negative_yaw_reference(config),
                invert=config.invert_yaw,
                delta_seconds=delta_seconds,
            ),
            pitch=self._process_axis_to_normalized(
                delta.pitch,
                config,
                exponent=config.head_tracking_exponent,
                inflection_point=config.head_tracking_inflection_point,
                start_point=config.head_tracking_start_point,
                end_point=config.head_tracking_end_point,
                responsiveness=config.head_view_responsiveness,
                smoothing=config.head_view_smoothing,
                previous=self.previous_head_normalized.pitch,
                positive_reference=self._positive_pitch_reference(config),
                negative_reference=self._negative_pitch_reference(config),
                invert=config.invert_pitch,
                delta_seconds=delta_seconds,
            ),
            roll=self._process_axis_to_normalized(
                delta.roll,
                config,
                exponent=config.head_tracking_exponent,
                inflection_point=config.head_tracking_inflection_point,
                start_point=config.head_tracking_start_point,
                end_point=config.head_tracking_end_point,
                responsiveness=config.head_view_responsiveness,
                smoothing=config.head_view_smoothing,
                previous=self.previous_head_normalized.roll,
                positive_reference=None,
                negative_reference=None,
                invert=config.invert_roll,
                delta_seconds=delta_seconds,
            ),
        )
        self.previous_head_normalized = normalized
        translation = PoseSample(
            x=self._process_translation_axis(
                delta.x,
                self.previous_head_translation.x,
                sensitivity=config.translation_x_sensitivity,
                config=config,
                invert=config.invert_x,
                delta_seconds=delta_seconds,
            ),
            y=self._process_translation_axis(
                delta.y,
                self.previous_head_translation.y,
                sensitivity=config.translation_y_sensitivity,
                config=config,
                invert=config.invert_y,
                delta_seconds=delta_seconds,
            ),
            z=self._process_translation_axis(
                delta.z,
                self.previous_head_translation.z,
                sensitivity=config.translation_z_sensitivity,
                config=config,
                invert=config.invert_z,
                delta_seconds=delta_seconds,
            ),
        )
        self.previous_head_translation = translation
        self._has_head_previous = True

        return PoseSample(
            yaw=applyAxisMultiplier(normalized.yaw * config.max_head_angle, yaw_multiplier, config.max_head_angle),
            pitch=applyAxisMultiplier(normalized.pitch * config.max_head_angle, pitch_multiplier, config.max_head_angle),
            roll=applyAxisMultiplier(normalized.roll * config.max_head_angle, config.head_roll_sensitivity, config.max_head_angle),
            x=translation.x,
            y=translation.y,
            z=translation.z,
        )

    def _process_gaze(
        self,
        head: PoseSample,
        raw_gaze: GazeSample | None,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> tuple[PoseSample, GazeDebug]:
        if not config.enable_simulated_gaze or config.gaze_strength <= 0.0 or config.max_gaze_angle <= 0.0:
            self.previous_gaze = PoseSample()
            self._gaze_missing_frames = 0
            self._reset_gaze_signal_state()
            return PoseSample(), GazeDebug(source="disabled")

        if raw_gaze is not None and raw_gaze.source.startswith("iris"):
            return self._process_iris_gaze(head, raw_gaze, config, delta_seconds)

        max_input = max(min(config.max_head_angle, config.max_gaze_angle), 0.001)
        gaze = PoseSample(
            yaw=self._apply_gaze_axis(head.yaw, max_input, self.previous_gaze.yaw, config, delta_seconds),
            pitch=self._apply_gaze_axis(head.pitch, max_input, self.previous_gaze.pitch, config, delta_seconds),
            roll=0.0,
        )
        self.previous_gaze = gaze
        self._gaze_missing_frames = 0
        face_confidence = 0.0 if raw_gaze is None else self._face_confidence(raw_gaze)
        return gaze, GazeDebug(
            raw_yaw=head.yaw,
            raw_pitch=head.pitch,
            confidence=0.0,
            source="head-fallback",
            face_confidence=face_confidence,
            iris_confidence=0.0,
            head_confidence=1.0,
            final_confidence=max(0.55, face_confidence),
            user_distance=0.0 if raw_gaze is None else float(raw_gaze.distance_scale or 0.0),
            iris_lost=True,
        )

    def _smart_motion_confidence(self, raw_gaze: GazeSample | None) -> float:
        if raw_gaze is None:
            return 1.0
        face_confidence = self._face_confidence(raw_gaze)
        if raw_gaze.source.startswith("iris"):
            return self._tracking_confidence(face_confidence, raw_gaze.confidence, head_confidence=1.0)
        if face_confidence <= 0.0 and raw_gaze.face_size_normalized <= 0.0:
            return 1.0
        return clamp(0.45 + (face_confidence * 0.55), 0.35, 1.0)

    def _process_iris_gaze(
        self,
        head: PoseSample,
        raw_gaze: GazeSample,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> tuple[PoseSample, GazeDebug]:
        if raw_gaze.confidence < self._GAZE_CONFIDENCE_THRESHOLD:
            self._gaze_missing_frames += 1
            return self._process_low_confidence_gaze(head, raw_gaze, config, delta_seconds)

        self._gaze_missing_frames = 0
        filtered_yaw, filtered_pitch = self._filter_raw_gaze(raw_gaze, delta_seconds)
        distance_gain = self._gaze_distance_gain(raw_gaze, delta_seconds)
        yaw_input = (filtered_yaw - (
            config.gaze_calibration_center_yaw if config.gaze_calibration_center_set else 0.0
        )) * distance_gain
        pitch_input = (filtered_pitch - (
            config.gaze_calibration_center_pitch if config.gaze_calibration_center_set else 0.0
        )) * distance_gain
        gaze = PoseSample(
            yaw=self._apply_real_gaze_axis(
                yaw_input,
                self.previous_gaze.yaw,
                config,
                delta_seconds,
                positive_reference=config.gaze_calibration_right_yaw if config.gaze_calibration_right_set else None,
                negative_reference=config.gaze_calibration_left_yaw if config.gaze_calibration_left_set else None,
                invert=config.invert_gaze_yaw,
            ),
            pitch=self._apply_real_gaze_axis(
                pitch_input,
                self.previous_gaze.pitch,
                config,
                delta_seconds,
                positive_reference=config.gaze_calibration_down_pitch if config.gaze_calibration_down_set else None,
                negative_reference=config.gaze_calibration_up_pitch if config.gaze_calibration_up_set else None,
                invert=config.invert_gaze_pitch,
            ),
            roll=0.0,
        )
        self.previous_gaze = gaze
        face_confidence = self._face_confidence(raw_gaze)
        final_confidence = self._tracking_confidence(face_confidence, raw_gaze.confidence, head_confidence=1.0)
        return gaze, GazeDebug(
            raw_yaw=raw_gaze.yaw,
            raw_pitch=raw_gaze.pitch,
            confidence=raw_gaze.confidence,
            source=raw_gaze.source,
            face_confidence=face_confidence,
            iris_confidence=raw_gaze.confidence,
            head_confidence=1.0,
            final_confidence=final_confidence,
            user_distance=float(raw_gaze.distance_scale or 0.0),
            iris_lost=False,
        )

    def _process_low_confidence_gaze(
        self,
        head: PoseSample,
        raw_gaze: GazeSample,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> tuple[PoseSample, GazeDebug]:
        distance_gain = self._gaze_distance_gain(raw_gaze, delta_seconds)
        fallback = self._head_fallback_gaze(head, config, delta_seconds, distance_gain)
        blend = clamp(self._gaze_missing_frames / max(self._GAZE_HOLD_FRAMES, 1), 0.12, 1.0)
        gaze = PoseSample(
            yaw=self.previous_gaze.yaw + (fallback.yaw - self.previous_gaze.yaw) * blend,
            pitch=self.previous_gaze.pitch + (fallback.pitch - self.previous_gaze.pitch) * blend,
            roll=0.0,
        )
        self.previous_gaze = gaze
        face_confidence = self._face_confidence(raw_gaze)
        final_confidence = self._tracking_confidence(face_confidence, raw_gaze.confidence, head_confidence=1.0)
        return gaze, GazeDebug(
            raw_yaw=raw_gaze.yaw,
            raw_pitch=raw_gaze.pitch,
            confidence=raw_gaze.confidence,
            source="iris-head-fallback" if self._gaze_missing_frames > self._GAZE_HOLD_FRAMES else "iris-hold-head",
            missing_frames=self._gaze_missing_frames,
            face_confidence=face_confidence,
            iris_confidence=raw_gaze.confidence,
            head_confidence=1.0,
            final_confidence=final_confidence,
            user_distance=float(raw_gaze.distance_scale or 0.0),
            iris_lost=True,
        )

    def _head_fallback_gaze(
        self,
        head: PoseSample,
        config: TrackingConfig,
        delta_seconds: float | None,
        distance_gain: float = 1.0,
    ) -> PoseSample:
        max_input = max(min(config.max_head_angle, config.max_gaze_angle), 0.001)
        gain = clamp(distance_gain, 0.85, 1.25)
        return PoseSample(
            yaw=self._apply_gaze_axis(head.yaw * gain, max_input, self.previous_gaze.yaw, config, delta_seconds),
            pitch=self._apply_gaze_axis(head.pitch * gain, max_input, self.previous_gaze.pitch, config, delta_seconds),
            roll=0.0,
        )

    def _filter_raw_gaze(
        self,
        raw_gaze: GazeSample,
        delta_seconds: float | None,
    ) -> tuple[float, float]:
        yaw = self._gaze_yaw_kalman.update(raw_gaze.yaw, delta_seconds, raw_gaze.confidence)
        pitch = self._gaze_pitch_kalman.update(raw_gaze.pitch, delta_seconds, raw_gaze.confidence)
        return yaw, pitch

    def _gaze_distance_gain(self, raw_gaze: GazeSample, delta_seconds: float | None) -> float:
        span = float(raw_gaze.face_size_normalized or raw_gaze.eye_span or 0.0)
        if span <= 0.001:
            return 1.0

        if self._gaze_distance_smoothed <= 0.0:
            self._gaze_distance_smoothed = span
        else:
            alpha = _time_adjusted_alpha(0.08, delta_seconds)
            self._gaze_distance_smoothed += (span - self._gaze_distance_smoothed) * alpha

        if self._gaze_distance_reference <= 0.0:
            self._gaze_distance_reference = self._gaze_distance_smoothed

        gain = (self._gaze_distance_reference / max(self._gaze_distance_smoothed, 0.001)) ** 0.35
        return clamp(gain, 0.82, 1.28)

    @staticmethod
    def _face_confidence(raw_gaze: GazeSample) -> float:
        face_size = float(raw_gaze.face_size_normalized or 0.0)
        eye_count = clamp(float(raw_gaze.valid_eye_count) / 2.0, 0.0, 1.0)
        face_score = clamp((face_size - 0.08) / 0.24, 0.0, 1.0)
        return clamp((face_score * 0.75) + (eye_count * 0.25), 0.0, 1.0)

    @staticmethod
    def _tracking_confidence(face_confidence: float, iris_confidence: float, head_confidence: float) -> float:
        return clamp((head_confidence * 0.45) + (face_confidence * 0.25) + (iris_confidence * 0.30), 0.0, 1.0)

    def _combine_head_and_gaze(
        self,
        head_pose: PoseSample,
        gaze_pose: PoseSample,
        extended_pose: PoseSample,
        gaze_debug: GazeDebug,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> PoseSample:
        distance_stability = clamp(max(gaze_debug.face_confidence, gaze_debug.iris_confidence * 0.75), 0.0, 1.0)
        iris_reliability = clamp(gaze_debug.iris_confidence, 0.0, 1.0)
        if gaze_debug.iris_lost:
            iris_reliability *= 0.35

        if gaze_debug.user_distance <= 0.0 or gaze_debug.user_distance <= 1.5:
            distance_bias = 1.0
        elif gaze_debug.user_distance <= 3.2:
            distance_bias = 0.80
        else:
            distance_bias = 0.55

        gaze_target = clamp(
            iris_reliability
            * (0.55 + distance_stability * 0.45)
            * distance_bias,
            0.0,
            1.0,
        )
        if gaze_debug.face_confidence <= 0.05 and iris_reliability >= 0.90 and not gaze_debug.iris_lost:
            gaze_target = 1.0
        
        # Só aplica o bias de cabeça se o gaze estiver realmente habilitado e sendo usado
        if gaze_debug.source == "disabled" or config.gaze_strength <= 0.0:
            head_target = 1.0
        else:
            head_target = clamp(1.0 + ((1.0 - gaze_target) * 0.08), 1.0, 1.08)
        if not self._has_final_previous and self._blend_gaze_weight == 0.0 and self._blend_head_weight == 1.0:
            self._blend_gaze_weight = gaze_target
            self._blend_head_weight = head_target
        else:
            weight_alpha = _time_adjusted_alpha(0.18, delta_seconds)
            self._blend_gaze_weight += (gaze_target - self._blend_gaze_weight) * weight_alpha
            self._blend_head_weight += (head_target - self._blend_head_weight) * weight_alpha
        gaze_debug.gaze_weight = self._blend_gaze_weight
        gaze_debug.head_weight = self._blend_head_weight

        return PoseSample(
            yaw=(head_pose.yaw * self._blend_head_weight) + (gaze_pose.yaw * self._blend_gaze_weight) + extended_pose.yaw,
            pitch=(head_pose.pitch * self._blend_head_weight) + (gaze_pose.pitch * self._blend_gaze_weight) + extended_pose.pitch,
            roll=head_pose.roll,
            x=head_pose.x,
            y=head_pose.y,
            z=head_pose.z,
        )

    def _apply_gaze_axis(
        self,
        input_angle: float,
        max_input_angle: float,
        previous: float,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> float:
        normalized = normalizeInput(input_angle, max_input_angle)
        normalized = clamp(normalized, -1.0, 1.0)
        normalized = applyStartEndPoint(
            normalized,
            config.gaze_tracking_start_point,
            config.gaze_tracking_end_point,
        )
        normalized = applyExponentCurve(normalized, config.gaze_tracking_exponent)
        normalized = applyInflectionCurve(normalized, config.gaze_tracking_inflection_point)
        target = clamp(
            normalized * config.max_gaze_angle * config.gaze_strength,
            -config.max_gaze_angle,
            config.max_gaze_angle,
        )
        return applyResponsiveness(
            target,
            previous,
            responsiveness=config.gaze_view_responsiveness,
            smoothing=config.gaze_view_smoothing,
            delta_seconds=delta_seconds,
        )

    def _apply_real_gaze_axis(
        self,
        input_value: float,
        previous: float,
        config: TrackingConfig,
        delta_seconds: float | None,
        *,
        positive_reference: float | None,
        negative_reference: float | None,
        invert: bool,
    ) -> float:
        normalized = _normalize_calibrated_input(
            input_value,
            1.0,
            positive_reference=positive_reference,
            negative_reference=negative_reference,
        )
        normalized = clamp(normalized, -1.0, 1.0)
        if invert:
            normalized = -normalized
        normalized = applyStartEndPoint(
            normalized,
            config.gaze_tracking_start_point,
            config.gaze_tracking_end_point,
        )
        normalized = applyExponentCurve(normalized, config.gaze_tracking_exponent)
        normalized = applyInflectionCurve(normalized, config.gaze_tracking_inflection_point)
        target = clamp(
            normalized * config.max_gaze_angle * config.gaze_strength,
            -config.max_gaze_angle,
            config.max_gaze_angle,
        )
        return applyResponsiveness(
            target,
            previous,
            responsiveness=config.gaze_view_responsiveness,
            smoothing=config.gaze_view_smoothing,
            delta_seconds=delta_seconds,
        )

    def _process_extended(
        self,
        head: PoseSample,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> tuple[PoseSample, ExtendedViewDebug]:
        if (
            not config.enable_extended_view
            or config.extended_view_strength <= 0.0
            or config.extended_view_max_angle <= 0.0
        ):
            self.previous_extended = PoseSample()
            return PoseSample(), ExtendedViewDebug()

        effective_strength = config.extended_view_strength * clamp(config.extended_view_blend, 0.0, 1.0)
        max_input = max(min(config.max_head_angle, config.extended_view_max_angle), 0.001)
        yaw_settings = ExtendedViewSettings(
            strength=effective_strength,
            exponent=config.extended_view_exponent,
            inflection_point=config.extended_view_inflection_point,
            start_point=config.extended_view_start_point,
            end_point=config.extended_view_end_point,
            acceleration=config.extended_view_acceleration,
            max_angle=config.extended_view_max_angle,
            smoothing=config.extended_view_smoothing,
            previous=self.previous_extended.yaw,
            delta_seconds=delta_seconds,
        )
        pitch_settings = ExtendedViewSettings(
            strength=effective_strength,
            exponent=config.extended_view_exponent,
            inflection_point=config.extended_view_inflection_point,
            start_point=config.extended_view_start_point,
            end_point=config.extended_view_end_point,
            acceleration=config.extended_view_acceleration,
            max_angle=config.extended_view_max_angle,
            smoothing=config.extended_view_smoothing,
            previous=self.previous_extended.pitch,
            delta_seconds=delta_seconds,
        )
        yaw_debug = _calculate_extended_axis(head.yaw, max_input, yaw_settings)
        pitch_debug = _calculate_extended_axis(head.pitch, max_input, pitch_settings)
        extended = PoseSample(yaw=yaw_debug.after_smoothing, pitch=pitch_debug.after_smoothing, roll=0.0)
        self.previous_extended = extended
        return extended, ExtendedViewDebug(yaw=yaw_debug, pitch=pitch_debug)

    def _process_axis_to_normalized(
        self,
        value: float,
        config: TrackingConfig,
        exponent: float,
        inflection_point: float,
        start_point: float,
        end_point: float,
        responsiveness: float,
        smoothing: float,
        previous: float,
        positive_reference: float | None,
        negative_reference: float | None,
        invert: bool,
        delta_seconds: float | None,
    ) -> float:
        value = applyDeadzone(value, config.input_deadzone)
        value = _normalize_calibrated_input(value, config.max_head_angle, positive_reference, negative_reference)
        if invert:
            value = -value
        value = applyStartEndPoint(value, start_point, end_point)
        value = applyExponentCurve(value, exponent)
        value = applyInflectionCurve(value, inflection_point)
        value = applyResponsiveness(value, previous, responsiveness, smoothing, delta_seconds)
        return value

    def _process_translation_axis(
        self,
        value: float,
        previous: float,
        sensitivity: float,
        config: TrackingConfig,
        invert: bool,
        delta_seconds: float | None,
    ) -> float:
        translated = applyDeadzone(value, config.translation_deadzone)
        if invert:
            translated = -translated
        translated = clamp(
            translated * sensitivity,
            -self._TRANSLATION_MAX_CM,
            self._TRANSLATION_MAX_CM,
        )
        responsiveness = max(self._TRANSLATION_MIN_RESPONSIVENESS, float(config.head_view_responsiveness))
        smoothing = max(self._TRANSLATION_MIN_SMOOTHING, float(config.translation_smoothing))
        return applyResponsiveness(
            translated,
            previous,
            responsiveness=responsiveness,
            smoothing=smoothing,
            delta_seconds=delta_seconds,
        )

    def _stabilize_output(
        self,
        pose: PoseSample,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> tuple[PoseSample, OutputStabilizationDebug]:
        if config.motion_filter_enabled:
            self.previous_final = pose
            self._has_final_previous = True
            return pose, self._smart_motion_stabilization_debug()

        if not self._has_final_previous:
            self.previous_final = pose
            self._has_final_previous = True
            self._motion_yaw.initialize(pose.yaw)
            self._motion_pitch.initialize(pose.pitch)
            self._motion_roll.initialize(pose.roll)
            self._motion_rotation.initialize((pose.yaw, pose.pitch, pose.roll))
            return pose, OutputStabilizationDebug(
                yaw=FinalAxisDebug(raw=pose.yaw, previous=pose.yaw, prefiltered=pose.yaw, filtered=pose.yaw),
                pitch=FinalAxisDebug(raw=pose.pitch, previous=pose.pitch, prefiltered=pose.pitch, filtered=pose.pitch),
                roll=FinalAxisDebug(raw=pose.roll, previous=pose.roll, prefiltered=pose.roll, filtered=pose.roll),
            )

        yaw, pitch, roll, rotation_debug = self._stabilize_rotation_axes(pose, config, delta_seconds)

        stabilized = PoseSample(
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            x=self._stabilize_translation_axis(pose.x, self.previous_final.x, config, delta_seconds),
            y=self._stabilize_translation_axis(pose.y, self.previous_final.y, config, delta_seconds),
            z=self._stabilize_translation_axis(pose.z, self.previous_final.z, config, delta_seconds),
        )
        self.previous_final = stabilized
        return stabilized, rotation_debug

    def _smart_motion_stabilization_debug(self) -> OutputStabilizationDebug:
        debug = self.smart_motion_filter.getDebugData()

        def axis(index: int) -> FinalAxisDebug:
            if index >= len(debug.axes):
                return FinalAxisDebug()
            source = debug.axes[index]
            return FinalAxisDebug(
                state=debug.state.upper().replace(" ", "_"),
                raw=source.raw,
                previous=source.filtered - source.delta,
                prefiltered=source.raw,
                filtered=source.filtered,
                delta=source.delta,
                threshold=source.deadzone,
                alpha=source.alpha,
                still_frames=0,
                jitter_detected=source.held or debug.state == "Still",
                spike_rejected=False,
            )

        return OutputStabilizationDebug(yaw=axis(3), pitch=axis(4), roll=axis(5))

    def _stabilize_rotation_axes(
        self,
        pose: PoseSample,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> tuple[float, float, float, OutputStabilizationDebug]:
        previous = self._motion_rotation.filtered.copy()
        results = self._motion_rotation.update(
            (pose.yaw, pose.pitch, pose.roll),
            delta_seconds,
            micro_jitter=config.output_micro_jitter,
            smoothing=config.output_smoothing,
            max_step=config.output_max_step,
            threshold_scales=(1.18, 1.9, 1.28),
            threshold_floors=(0.10, 0.20, 0.12),
            confidence=max(0.7, self._tracking_confidence_for_output()),
            distance_stability=self._distance_stability_for_output(),
            still_frames_required=self._FINAL_STILL_FRAMES,
            spike_multiplier=self._FINAL_SPIKE_MULTIPLIER,
        )
        debug = OutputStabilizationDebug(
            yaw=self._final_axis_debug(results[0], previous[0]),
            pitch=self._final_axis_debug(results[1], previous[1]),
            roll=self._final_axis_debug(results[2], previous[2]),
        )
        return results[0].value, results[1].value, results[2].value, debug

    @staticmethod
    def _final_axis_debug(result: AxisStabilizerResult, previous: float) -> FinalAxisDebug:
        return FinalAxisDebug(
            state=result.state,
            raw=result.raw,
            previous=previous,
            prefiltered=result.prefiltered,
            filtered=result.value,
            delta=result.raw - previous,
            threshold=result.threshold,
            alpha=result.alpha,
            still_frames=result.still_frames,
            jitter_detected=result.jitter_detected,
            spike_rejected=result.spike_rejected,
        )

    def _stabilize_final_axis(
        self,
        value: float,
        config: TrackingConfig,
        delta_seconds: float | None,
        *,
        axis: MotionAxisStabilizer,
        confidence: float,
        distance_stability: float,
        threshold_scale: float = 1.0,
        threshold_floor: float = 0.0,
    ) -> tuple[float, FinalAxisDebug]:
        previous = axis.filtered
        result = axis.update(
            value,
            delta_seconds,
            micro_jitter=config.output_micro_jitter,
            smoothing=config.output_smoothing,
            max_step=config.output_max_step,
            threshold_scale=threshold_scale,
            threshold_floor=threshold_floor,
            alpha_still=0.12,
            alpha_moving=0.92,
            confidence=confidence,
            distance_stability=distance_stability,
            still_frames_required=self._FINAL_STILL_FRAMES,
            release_frames_required=self._FINAL_STILL_RELEASE_FRAMES,
            still_deadzone_multiplier=1.15,
            release_multiplier=self._FINAL_STILL_RELEASE_MULTIPLIER,
            spike_multiplier=self._FINAL_SPIKE_MULTIPLIER,
            one_euro_beta=0.24,
        )
        return result.value, FinalAxisDebug(
            state=result.state,
            raw=result.raw,
            previous=previous,
            prefiltered=result.prefiltered,
            filtered=result.value,
            delta=result.raw - previous,
            threshold=result.threshold,
            alpha=result.alpha,
            still_frames=result.still_frames,
            jitter_detected=result.jitter_detected,
            spike_rejected=result.spike_rejected,
        )

    def _tracking_confidence_for_output(self) -> float:
        return clamp((self._blend_head_weight * 0.40) + (self._blend_gaze_weight * 0.60), 0.45, 1.0)

    def _distance_stability_for_output(self) -> float:
        if self._gaze_distance_reference <= 0.0 or self._gaze_distance_smoothed <= 0.0:
            return 1.0
        ratio = self._gaze_distance_smoothed / max(self._gaze_distance_reference, 0.001)
        return clamp(ratio, 0.35, 1.0)

    def _maybe_log_stabilization(
        self,
        raw: PoseSample,
        filtered: PoseSample,
        debug: OutputStabilizationDebug,
    ) -> None:
        if not _stabilization_debug_enabled():
            return
        now = time.monotonic()
        if now - self._last_stabilization_log_time < 0.5:
            return
        self._last_stabilization_log_time = now
        _stabilization_logger().info(
            "final_filter yaw=%s raw=%.3f filtered=%.3f jitter=%s spike=%s | "
            "pitch=%s raw=%.3f filtered=%.3f jitter=%s spike=%s | "
            "roll=%s raw=%.3f filtered=%.3f jitter=%s spike=%s",
            debug.yaw.state,
            raw.yaw,
            filtered.yaw,
            debug.yaw.jitter_detected,
            debug.yaw.spike_rejected,
            debug.pitch.state,
            raw.pitch,
            filtered.pitch,
            debug.pitch.jitter_detected,
            debug.pitch.spike_rejected,
            debug.roll.state,
            raw.roll,
            filtered.roll,
            debug.roll.jitter_detected,
            debug.roll.spike_rejected,
        )

    @staticmethod
    def _stabilize_axis(
        value: float,
        previous: float,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> float:
        delta = value - previous
        # Histerese adaptativa: ignora variações minúsculas
        threshold = max(0.0, config.output_micro_jitter)
        
        # Se o movimento for menor que o threshold, mantemos o valor anterior (travado)
        target = value
        
        # Suavização adicional na saída para transições mais fluidas
        target = value
        
        # Se a suavização de saída estiver ativa, aplicamos um EMA extra
        if abs(delta) <= threshold and threshold > 0.0:
            return previous

        if config.output_smoothing > 0:
            target = applyResponsiveness(
                target,
                previous,
                responsiveness=1.0,
                smoothing=config.output_smoothing,
                delta_seconds=delta_seconds,
            )

        max_step = max(0.0, config.output_max_step) * _frame_delta_scale(delta_seconds)
        if max_step > 0.0:
            target = clamp(target, previous - max_step, previous + max_step)
        return target

    @classmethod
    def _stabilize_translation_axis(
        cls,
        value: float,
        previous: float,
        config: TrackingConfig,
        delta_seconds: float | None,
    ) -> float:
        delta = value - previous
        if abs(delta) <= cls._OUTPUT_TRANSLATION_JITTER_CM:
            return previous
        
        target = value - _sign(delta) * cls._OUTPUT_TRANSLATION_JITTER_CM

        target = applyResponsiveness(
            target,
            previous,
            responsiveness=1.0,
            smoothing=max(cls._TRANSLATION_MIN_SMOOTHING, float(config.translation_smoothing), float(config.output_smoothing)),
            delta_seconds=delta_seconds,
        )
        max_step = cls._OUTPUT_TRANSLATION_MAX_STEP_CM * _frame_delta_scale(delta_seconds)
        return clamp(
            target,
            previous - max_step,
            previous + max_step,
        )

    @staticmethod
    def _positive_yaw_reference(config: TrackingConfig) -> float | None:
        return config.calibration_right_yaw if config.calibration_right_set else None

    @staticmethod
    def _negative_yaw_reference(config: TrackingConfig) -> float | None:
        return config.calibration_left_yaw if config.calibration_left_set else None

    @staticmethod
    def _positive_pitch_reference(config: TrackingConfig) -> float | None:
        return config.calibration_down_pitch if config.calibration_down_set else None

    @staticmethod
    def _negative_pitch_reference(config: TrackingConfig) -> float | None:
        return config.calibration_up_pitch if config.calibration_up_set else None
