# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import math

import pytest

from eye_drive_tracker.filters.smart_motion import (
    EULER_CLASSIC,
    POSITION_GAIN_CURVE,
    QUATERNION_HAMILTON,
    ROTATION_GAIN_CURVE,
    AngleBetweenQuats,
    QuatFromYawPitchRoll,
    Slerp,
    TorvixSmartMotionFilter,
)
from eye_drive_tracker.profiles.profile import TrackingConfig
from eye_drive_tracker.tracking.models import PoseSample


def _config() -> TrackingConfig:
    config = TrackingConfig()
    config.motion_filter_enabled = True
    config.motion_rotation_mode = QUATERNION_HAMILTON
    config.motion_rotation_smoothing = 1.5
    config.motion_rotation_deadzone = 0.03
    config.motion_position_smoothing = 1.0
    config.motion_position_deadzone = 0.1
    return config


def _angle_delta(value: float, previous: float) -> float:
    delta = value - previous
    if abs(delta) > 180.0:
        delta -= math.copysign(360.0, delta)
    return delta


def test_first_frame_copies_raw_input_without_filtering() -> None:
    filter_ = TorvixSmartMotionFilter(_config())

    output = filter_.update(PoseSample(yaw=3.0, pitch=-2.0, roll=1.0, x=1.0, y=2.0, z=3.0), 1 / 60, 1.0)

    assert output == PoseSample(yaw=3.0, pitch=-2.0, roll=1.0, x=1.0, y=2.0, z=3.0)
    assert filter_.firstRun is False
    assert filter_.lastTimestamp == pytest.approx(1 / 60)


def test_filter_tracks_last_delta_state() -> None:
    filter_ = TorvixSmartMotionFilter(_config())
    filter_.update(PoseSample(yaw=179.0, x=1.0), 1 / 60, 1.0)
    filter_.update(PoseSample(yaw=-179.0, x=2.0), 1 / 60, 1.0)

    assert filter_.lastDelta[0] == pytest.approx(1.0)
    assert filter_.lastDelta[3] == pytest.approx(2.0)


def test_gain_curves_interpolate_without_nan() -> None:
    filter_ = TorvixSmartMotionFilter(_config())

    assert filter_.evaluateGainCurve(0.0, ROTATION_GAIN_CURVE) == pytest.approx(0.0)
    assert 0.4 < filter_.evaluateGainCurve(0.75, ROTATION_GAIN_CURVE) < 1.5
    assert 0.75 < filter_.evaluateGainCurve(1.0, POSITION_GAIN_CURVE) < 2.25
    assert math.isfinite(filter_.evaluateGainCurve(float("nan"), ROTATION_GAIN_CURVE))


def test_still_jitter_is_held_without_drift() -> None:
    config = _config()
    config.motion_rotation_deadzone = 0.08
    filter_ = TorvixSmartMotionFilter(config)
    filter_.update(PoseSample(yaw=0.0), 1 / 60, 1.0)

    output = None
    for yaw in (0.03, -0.04, 0.05, -0.02, 0.04, -0.03, 0.02, -0.01, 0.03, -0.02, 0.01, 0.0):
        output = filter_.update(PoseSample(yaw=yaw), 1 / 60, 1.0)

    assert output is not None
    assert output.yaw == pytest.approx(0.0)
    assert filter_.getDebugData().state == "Still"


def test_fast_rotation_uses_controlled_snap() -> None:
    config = _config()
    config.motion_snap_enabled = True
    config.motion_rotation_snap_threshold = 8.0
    config.motion_snap_alpha = 0.85
    filter_ = TorvixSmartMotionFilter(config)
    filter_.update(PoseSample(yaw=0.0), 1 / 60, 1.0)

    output = filter_.update(PoseSample(yaw=12.0), 1 / 60, 1.0)

    assert 8.0 < output.yaw < 12.0
    assert filter_.getDebugData().snap_active is True


def test_low_confidence_holds_last_output_briefly() -> None:
    config = _config()
    config.motion_critical_confidence_threshold = 0.25
    config.motion_hold_frames_on_bad_tracking = 3
    filter_ = TorvixSmartMotionFilter(config)
    filter_.update(PoseSample(yaw=0.0), 1 / 60, 1.0)

    output = filter_.update(PoseSample(yaw=20.0), 1 / 60, 0.10)

    assert output.yaw == pytest.approx(0.0)
    assert filter_.getDebugData().state == "Low Confidence"


def test_yaw_wrap_does_not_create_large_jump() -> None:
    config = _config()
    config.motion_rotation_mode = EULER_CLASSIC
    filter_ = TorvixSmartMotionFilter(config)
    filter_.update(PoseSample(yaw=179.0), 1 / 60, 1.0)

    output = filter_.update(PoseSample(yaw=-179.0), 1 / 60, 1.0)

    assert abs(_angle_delta(output.yaw, 179.0)) < 2.0


def test_quaternion_slerp_moves_along_short_arc() -> None:
    start = QuatFromYawPitchRoll(0.0, 0.0, 0.0)
    end = QuatFromYawPitchRoll(90.0, 0.0, 0.0)

    halfway = Slerp(start, end, 0.5)

    assert AngleBetweenQuats(start, halfway) == pytest.approx(45.0)
    assert AngleBetweenQuats(halfway, end) == pytest.approx(45.0)


def test_filter_is_similar_across_variable_fps() -> None:
    config = _config()
    low_fps = TorvixSmartMotionFilter(config)
    high_fps = TorvixSmartMotionFilter(config)
    low_fps.update(PoseSample(yaw=0.0), 1 / 60, 1.0)
    high_fps.update(PoseSample(yaw=0.0), 1 / 60, 1.0)

    low_output = PoseSample()
    for _ in range(30):
        low_output = low_fps.update(PoseSample(yaw=6.0), 1 / 30, 1.0)

    high_output = PoseSample()
    for _ in range(120):
        high_output = high_fps.update(PoseSample(yaw=6.0), 1 / 120, 1.0)

    assert abs(low_output.yaw - high_output.yaw) < 1.0
