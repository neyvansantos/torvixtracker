# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from eye_drive_tracker.filters.motion_stabilizer import AccelaVectorStabilizer, MotionAxisStabilizer


def _update(axis: MotionAxisStabilizer, value: float):
    return axis.update(
        value,
        1.0 / 60.0,
        micro_jitter=0.0,
        smoothing=0.96,
        max_step=30.0,
        threshold_scale=1.18,
        threshold_floor=0.10,
        alpha_still=0.08,
        alpha_moving=0.82,
        confidence=1.0,
        distance_stability=1.0,
        still_frames_required=8,
        release_frames_required=5,
        still_deadzone_multiplier=1.15,
        release_multiplier=3.2,
        spike_multiplier=2.5,
        one_euro_beta=0.24,
    )


def test_accela_target_anchor_settles_side_hold_jitter() -> None:
    axis = MotionAxisStabilizer()
    axis.initialize(0.0)

    for value in (10.0, 16.0, 20.2, 19.8, 20.1, 19.9, 20.0):
        result = _update(axis, value)

    assert axis.target_quiet_frames == axis._ACCELA_STABLE_FRAMES
    assert abs(result.prefiltered - axis.target_anchor) < 0.35


def test_accela_target_anchor_releases_for_real_movement() -> None:
    axis = MotionAxisStabilizer()
    axis.initialize(0.0)

    for value in (10.0, 16.0, 20.2, 19.8, 20.1, 19.9, 20.0):
        _update(axis, value)
    _update(axis, 23.0)

    assert axis.target_quiet_frames == 0
    assert axis.target_anchor == 23.0


def test_accela_vector_holds_micro_jitter_across_rotation_axes() -> None:
    filter_ = AccelaVectorStabilizer(3)
    filter_.initialize((0.0, 0.0, 0.0))

    results = filter_.update(
        (0.05, 0.08, 0.04),
        1.0 / 60.0,
        micro_jitter=0.20,
        smoothing=0.10,
        max_step=18.0,
        threshold_scales=(1.18, 1.9, 1.28),
        threshold_floors=(0.10, 0.20, 0.12),
        confidence=1.0,
        distance_stability=1.0,
        still_frames_required=4,
        spike_multiplier=2.5,
    )

    assert [result.value for result in results] == [0.0, 0.0, 0.0]
    assert all(result.jitter_detected for result in results)


def test_accela_vector_moves_as_vector_without_waiting_for_release_frames() -> None:
    filter_ = AccelaVectorStabilizer(3)
    filter_.initialize((0.0, 0.0, 0.0))

    results = filter_.update(
        (3.0, 2.0, 0.0),
        1.0 / 60.0,
        micro_jitter=0.20,
        smoothing=0.12,
        max_step=18.0,
        threshold_scales=(1.18, 1.9, 1.28),
        threshold_floors=(0.10, 0.20, 0.12),
        confidence=1.0,
        distance_stability=1.0,
        still_frames_required=4,
        spike_multiplier=2.5,
    )

    assert results[0].value > 0.5
    assert results[1].value > 0.2
    assert results[0].value < 3.0
    assert results[1].value < 2.0
    assert {result.state for result in results} == {"MOVING"}
