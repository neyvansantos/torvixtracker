# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import pytest

from eye_drive_tracker.filters.pose_filters import PoseFilter
from eye_drive_tracker.profiles.profile import TrackingConfig
from eye_drive_tracker.tracking.models import GazeSample, PoseSample


def _calibrated_config() -> TrackingConfig:
    config = TrackingConfig()
    config.calibration_center_set = True
    config.calibration_center_yaw = 0.0
    config.input_deadzone = 0.0
    config.head_view_responsiveness = 1.0
    config.head_view_smoothing = 0.0
    config.head_yaw_sensitivity_cabin = 1.0
    config.max_head_angle = 100.0
    config.invert_yaw = False
    config.invert_pitch = False
    config.enable_simulated_gaze = False
    config.enable_extended_view = False
    config.motion_filter_enabled = False
    config.output_smoothing = 0.0
    config.output_micro_jitter = 0.0
    config.output_max_step = 0.0
    return config


def _filtered_yaw(raw_yaw: float, config: TrackingConfig) -> float:
    return PoseFilter().process(PoseSample(yaw=raw_yaw), config).final.yaw


def test_yaw_calibration_uses_reference_with_matching_raw_sign() -> None:
    config = _calibrated_config()
    config.calibration_left_set = True
    config.calibration_left_yaw = 40.0
    config.calibration_right_set = True
    config.calibration_right_yaw = -20.0

    assert _filtered_yaw(20.0, config) == pytest.approx(50.0)
    assert _filtered_yaw(-10.0, config) == pytest.approx(-50.0)


def test_inverted_yaw_does_not_swap_calibrated_side_references() -> None:
    config = _calibrated_config()
    config.invert_yaw = True
    config.calibration_left_set = True
    config.calibration_left_yaw = -40.0
    config.calibration_right_set = True
    config.calibration_right_yaw = 20.0

    assert _filtered_yaw(10.0, config) == pytest.approx(-50.0)
    assert _filtered_yaw(-20.0, config) == pytest.approx(50.0)


def test_real_iris_gaze_contributes_without_head_movement() -> None:
    config = _calibrated_config()
    config.enable_simulated_gaze = True
    config.gaze_strength = 1.0
    config.max_gaze_angle = 12.0
    config.gaze_tracking_start_point = 0.0
    config.gaze_tracking_exponent = 1.0
    config.gaze_tracking_inflection_point = 0.5
    config.gaze_view_responsiveness = 1.0
    config.gaze_view_smoothing = 0.0

    output = PoseFilter().process(
        PoseSample(),
        config,
        GazeSample(yaw=0.5, pitch=-0.25, confidence=1.0, source="iris"),
    )

    assert output.gaze.yaw == pytest.approx(6.0)
    assert output.gaze.pitch == pytest.approx(-3.0)
    assert output.final.yaw == pytest.approx(6.0)
    assert output.gaze_debug.source == "iris"


def test_low_confidence_iris_gaze_holds_previous_value_briefly() -> None:
    config = _calibrated_config()
    config.enable_simulated_gaze = True
    config.gaze_strength = 1.0
    config.max_gaze_angle = 12.0
    config.gaze_tracking_start_point = 0.0
    config.gaze_view_responsiveness = 1.0
    config.gaze_view_smoothing = 0.0
    filter_ = PoseFilter()
    first = filter_.process(
        PoseSample(),
        config,
        GazeSample(yaw=0.5, pitch=0.0, confidence=1.0, source="iris"),
    )

    held = filter_.process(
        PoseSample(),
        config,
        GazeSample(yaw=0.0, pitch=0.0, confidence=0.05, source="iris"),
    )

    assert 0.0 < held.gaze.yaw < first.gaze.yaw
    assert held.gaze_debug.source == "iris-hold-head"


def test_low_confidence_iris_gaze_blends_to_head_fallback_instead_of_zeroing() -> None:
    config = _calibrated_config()
    config.enable_simulated_gaze = True
    config.gaze_strength = 1.0
    config.max_gaze_angle = 12.0
    config.gaze_tracking_start_point = 0.0
    config.gaze_view_responsiveness = 1.0
    config.gaze_view_smoothing = 0.0
    filter_ = PoseFilter()
    filter_.process(
        PoseSample(),
        config,
        GazeSample(yaw=0.5, pitch=0.0, confidence=1.0, source="iris"),
    )

    output = None
    for _ in range(PoseFilter._GAZE_HOLD_FRAMES + 2):
        output = filter_.process(
            PoseSample(yaw=10.0),
            config,
            GazeSample(yaw=0.0, pitch=0.0, confidence=0.02, source="iris", face_size_normalized=0.08),
        )

    assert output is not None
    assert output.gaze_debug.source == "iris-head-fallback"
    assert output.gaze.yaw > 0.0


def test_output_micro_jitter_threshold_freezes_still_output() -> None:
    config = _calibrated_config()
    config.output_micro_jitter = 0.20
    config.output_smoothing = 0.0
    config.output_max_step = 0.0
    filter_ = PoseFilter()
    filter_.process(PoseSample(yaw=0.0), config)

    output = None
    for _ in range(PoseFilter._FINAL_STILL_FRAMES):
        output = filter_.process(PoseSample(yaw=0.10), config)

    assert output is not None
    assert output.final.yaw == pytest.approx(0.0)
    assert output.stabilization_debug.yaw.state == "STILL"
    assert output.stabilization_debug.yaw.jitter_detected is True


def test_output_filter_releases_real_movement_after_still_state() -> None:
    config = _calibrated_config()
    config.output_micro_jitter = 0.20
    config.output_smoothing = 0.35
    config.output_max_step = 0.0
    filter_ = PoseFilter()
    filter_.process(PoseSample(yaw=0.0), config)
    for _ in range(PoseFilter._FINAL_STILL_FRAMES):
        filter_.process(PoseSample(yaw=0.10), config)

    moved = filter_.process(PoseSample(yaw=3.0), config)

    assert moved.final.yaw > 0.20
    assert moved.final.yaw < 3.0
    assert moved.stabilization_debug.yaw.state == "MOVING"
    assert moved.stabilization_debug.yaw.alpha > 0.0


def test_pitch_filter_holds_slow_resting_drift() -> None:
    config = _calibrated_config()
    config.output_micro_jitter = 0.10
    config.output_smoothing = 0.0
    config.output_max_step = 0.0
    filter_ = PoseFilter()
    filter_.process(PoseSample(pitch=0.0), config)

    output = None
    for pitch in (0.04, 0.09, 0.14, 0.20, 0.25, 0.31, 0.36, 0.42):
        output = filter_.process(PoseSample(pitch=pitch), config)

    assert output is not None
    assert output.final.pitch == pytest.approx(0.0)
    assert output.stabilization_debug.pitch.state == "STILL"
    assert output.stabilization_debug.pitch.jitter_detected is True

    moved = filter_.process(PoseSample(pitch=2.0), config)

    assert moved.final.pitch > 0.2
    assert moved.stabilization_debug.pitch.state == "MOVING"


def test_output_filter_rejects_isolated_spike() -> None:
    config = _calibrated_config()
    config.output_micro_jitter = 0.20
    config.output_smoothing = 0.0
    config.output_max_step = 1.0
    filter_ = PoseFilter()
    filter_._motion_yaw.initialize(0.0)

    filtered, debug = filter_._stabilize_final_axis(
        20.0,
        config,
        None,
        axis=filter_._motion_yaw,
        confidence=1.0,
        distance_stability=1.0,
    )

    assert filtered == pytest.approx(0.0)
    assert debug.spike_rejected is True


def test_output_filter_clamps_max_step_per_frame() -> None:
    config = _calibrated_config()
    config.output_micro_jitter = 0.0
    config.output_smoothing = 0.0
    config.output_max_step = 1.0
    filter_ = PoseFilter()
    filter_._motion_yaw.initialize(0.0)

    filtered, debug = filter_._stabilize_final_axis(
        2.0,
        config,
        None,
        axis=filter_._motion_yaw,
        confidence=1.0,
        distance_stability=1.0,
    )

    assert filtered == pytest.approx(1.0)
    assert debug.spike_rejected is False


def test_recenter_uses_stable_average_instead_of_single_frame() -> None:
    filter_ = PoseFilter()
    for yaw in (0.0, 0.1, -0.1, 0.05, -0.05, 12.0):
        filter_._recenter_samples.append(PoseSample(yaw=yaw, pitch=0.0, roll=0.0))

    center = filter_.estimate_stable_center(PoseSample(yaw=15.0))

    assert abs(center.yaw) < 1.0


def test_head_roll_output_is_clamped_to_physical_tilt_range() -> None:
    config = _calibrated_config()
    config.calibration_center_set = True
    config.calibration_center_roll = 0.0
    config.head_roll_sensitivity = 5.0
    config.max_head_angle = 180.0
    config.invert_roll = False

    output = PoseFilter().process(PoseSample(roll=90.0), config)

    assert output.head.roll == pytest.approx(PoseFilter._HEAD_ROLL_OUTPUT_LIMIT)
    assert output.final.roll == pytest.approx(PoseFilter._HEAD_ROLL_OUTPUT_LIMIT)
