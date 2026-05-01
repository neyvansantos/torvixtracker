# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from types import SimpleNamespace

import pytest

from eye_drive_tracker.tracking.gaze import estimate_iris_gaze, reset_iris_gaze_filter


@pytest.fixture(autouse=True)
def _reset_gaze_filter() -> None:
    reset_iris_gaze_filter()


def _landmarks(
    *,
    iris_dx: float = 0.0,
    iris_dy: float = 0.0,
    eye_height: float = 0.030,
    right_eye_height: float | None = None,
):
    landmarks = [SimpleNamespace(x=0.0, y=0.0, z=0.0) for _ in range(478)]

    def set_point(index: int, x: float, y: float) -> None:
        landmarks[index] = SimpleNamespace(x=x, y=y, z=0.0)

    for outer, inner, top_indices, bottom_indices, iris_indices, center_x in (
        (33, 133, (159, 158, 160), (145, 144, 153), range(468, 473), 0.40),
        (263, 362, (386, 385, 387), (374, 380, 373), range(473, 478), 0.60),
    ):
        current_eye_height = right_eye_height if outer == 263 and right_eye_height is not None else eye_height
        set_point(outer, center_x - 0.05, 0.50)
        set_point(inner, center_x + 0.05, 0.50)
        for offset, top_index in zip((-0.02, 0.0, 0.02), top_indices):
            set_point(top_index, center_x + offset, 0.50 - current_eye_height * 0.5)
        for offset, bottom_index in zip((-0.02, 0.0, 0.02), bottom_indices):
            set_point(bottom_index, center_x + offset, 0.50 + current_eye_height * 0.5)
        for iris_index in iris_indices:
            set_point(iris_index, center_x + iris_dx, 0.50 + iris_dy)

    return landmarks


def test_iris_gaze_is_centered_for_centered_iris() -> None:
    gaze = estimate_iris_gaze(_landmarks(), 640, 480)

    assert gaze.source == "iris"
    assert gaze.confidence > 0.5
    assert gaze.yaw == pytest.approx(0.0, abs=0.01)
    assert gaze.pitch == pytest.approx(0.0, abs=0.01)
    assert gaze.left_iris is not None
    assert gaze.right_iris is not None


def test_iris_gaze_tracks_horizontal_iris_offset() -> None:
    gaze = estimate_iris_gaze(_landmarks(iris_dx=0.025), 640, 480)

    assert gaze.confidence > 0.5
    assert gaze.yaw > 0.4


def test_iris_gaze_lowers_confidence_when_eye_is_closed() -> None:
    gaze = estimate_iris_gaze(_landmarks(eye_height=0.004), 640, 480)

    assert gaze.source == "iris"
    assert gaze.confidence < 0.24


def test_iris_gaze_keeps_tracking_with_one_valid_eye() -> None:
    gaze = estimate_iris_gaze(_landmarks(iris_dx=0.018, right_eye_height=0.004), 640, 480)

    assert gaze.source == "iris"
    assert gaze.valid_eye_count == 1
    assert gaze.confidence > 0.24
    assert gaze.yaw > 0.2


def test_iris_gaze_reports_normalized_coordinates_across_resolutions() -> None:
    landmarks = _landmarks(iris_dx=0.015, iris_dy=-0.006)

    small = estimate_iris_gaze(landmarks, 640, 480)
    large = estimate_iris_gaze(landmarks, 1920, 1080)

    assert small.yaw == pytest.approx(large.yaw)
    assert small.pitch == pytest.approx(large.pitch)
    assert small.normalized_x == pytest.approx(large.normalized_x)
    assert small.normalized_y == pytest.approx(large.normalized_y)
    assert 0.0 <= small.normalized_x <= 1.0
    assert 0.0 <= small.normalized_y <= 1.0


def test_iris_gaze_smooths_subsequent_angle_changes() -> None:
    centered = estimate_iris_gaze(_landmarks(), 640, 480)
    shifted = estimate_iris_gaze(_landmarks(iris_dx=0.025), 640, 480)

    assert centered.yaw == pytest.approx(0.0, abs=0.01)
    assert 0.0 < shifted.yaw < 0.4
