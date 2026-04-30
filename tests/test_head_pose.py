# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
import time
from types import SimpleNamespace

import pytest

from eye_drive_tracker.tracking.models import PoseSample
from eye_drive_tracker.tracking.head_pose import HeadPoseTracker


def _landmarks(
    *,
    nose_x: float,
    eye_left_x: float = 0.40,
    eye_right_x: float = 0.60,
    mouth_left_x: float = 0.43,
    mouth_right_x: float = 0.57,
    eye_left_z: float = 0.0,
    eye_right_z: float = 0.0,
):
    landmarks = [SimpleNamespace(x=0.0, y=0.0, z=0.0) for _ in range(292)]
    landmarks[1] = SimpleNamespace(x=nose_x, y=0.0, z=0.0)
    landmarks[33] = SimpleNamespace(x=eye_left_x, y=0.0, z=eye_left_z)
    landmarks[263] = SimpleNamespace(x=eye_right_x, y=0.0, z=eye_right_z)
    landmarks[61] = SimpleNamespace(x=mouth_left_x, y=0.0, z=0.0)
    landmarks[291] = SimpleNamespace(x=mouth_right_x, y=0.0, z=0.0)
    return landmarks


def test_landmark_yaw_is_centered_for_symmetric_face_points() -> None:
    yaw = HeadPoseTracker._estimate_landmark_yaw(_landmarks(nose_x=0.50))

    assert yaw == pytest.approx(0.0)


def test_landmark_yaw_tracks_nose_offset_without_camera_center_bias() -> None:
    left_yaw = HeadPoseTracker._estimate_landmark_yaw(_landmarks(nose_x=0.56))
    right_yaw = HeadPoseTracker._estimate_landmark_yaw(_landmarks(nose_x=0.44))

    assert left_yaw < 0.0
    assert right_yaw > 0.0
    assert abs(left_yaw) == pytest.approx(abs(right_yaw))


def test_landmark_yaw_blend_pulls_biased_pnp_yaw_toward_face_geometry() -> None:
    blended = HeadPoseTracker._blend_pnp_and_landmark_yaw(40.0, 5.0)

    assert blended < 15.0


def test_stabilize_pose_limits_single_frame_yaw_jump() -> None:
    tracker = HeadPoseTracker.__new__(HeadPoseTracker)
    tracker._last_pose = PoseSample(yaw=5.0)
    tracker._has_last_pose = True
    tracker._last_pose_timestamp = time.monotonic() - 0.2

    stabilized = tracker._stabilize_pose(PoseSample(yaw=17.0))

    assert stabilized.yaw == pytest.approx(11.0)


def test_stabilize_pose_holds_raw_yaw_when_stationary_jitter_continues() -> None:
    tracker = HeadPoseTracker.__new__(HeadPoseTracker)
    tracker._last_pose = PoseSample()
    tracker._has_last_pose = True
    tracker._last_pose_timestamp = time.monotonic()
    tracker._pose_ema_enabled = False
    tracker._reset_pose_stillness(PoseSample())

    outputs = []
    for yaw in (0.24, -0.18, 0.29, -0.20, 0.19, -0.16, 0.22):
        tracker._last_pose_timestamp = time.monotonic() - (1.0 / 60.0)
        outputs.append(tracker._stabilize_pose(PoseSample(yaw=yaw)).yaw)

    assert tracker._pose_stillness_yaw.locked is True
    assert outputs[-1] == pytest.approx(outputs[-2])


def test_stabilize_pose_releases_after_sustained_real_yaw_movement() -> None:
    tracker = HeadPoseTracker.__new__(HeadPoseTracker)
    tracker._last_pose = PoseSample()
    tracker._has_last_pose = True
    tracker._last_pose_timestamp = time.monotonic()
    tracker._pose_ema_enabled = False
    tracker._reset_pose_stillness(PoseSample())

    for yaw in (0.24, -0.18, 0.29, -0.20, 0.19):
        tracker._last_pose_timestamp = time.monotonic() - (1.0 / 60.0)
        tracker._stabilize_pose(PoseSample(yaw=yaw))

    held = tracker._stabilize_pose(PoseSample(yaw=2.0))
    tracker._last_pose_timestamp = time.monotonic() - (1.0 / 60.0)
    tracker._stabilize_pose(PoseSample(yaw=2.0))
    tracker._last_pose_timestamp = time.monotonic() - (1.0 / 60.0)
    released = tracker._stabilize_pose(PoseSample(yaw=2.0))

    assert held.yaw == pytest.approx(2.0)
    assert released.yaw == pytest.approx(2.0)
    assert tracker._pose_stillness_yaw.locked is False


def test_short_detection_loss_keeps_last_pose_for_reacquisition_ramp() -> None:
    tracker = HeadPoseTracker.__new__(HeadPoseTracker)
    tracker._missed_detections = 0
    tracker._last_rotation_vector = object()
    tracker._last_translation_vector = object()
    tracker._last_face_box = (1, 2, 3, 4)
    tracker._box_tracker = object()
    tracker._last_pose = PoseSample(yaw=5.0)
    tracker._has_last_pose = True
    tracker._last_pose_timestamp = time.monotonic()

    for _ in range(HeadPoseTracker._TRACKING_RESET_MISSED_DETECTIONS):
        tracker._mark_detection_lost()

    assert tracker._last_rotation_vector is None
    assert tracker._last_translation_vector is None
    assert tracker._last_face_box is None
    assert tracker._box_tracker is None
    assert tracker._has_last_pose is True
    assert tracker._last_pose.yaw == pytest.approx(5.0)


def test_long_detection_loss_resets_last_pose() -> None:
    tracker = HeadPoseTracker.__new__(HeadPoseTracker)
    tracker._missed_detections = 0
    tracker._last_rotation_vector = object()
    tracker._last_translation_vector = object()
    tracker._last_face_box = (1, 2, 3, 4)
    tracker._box_tracker = object()
    tracker._last_pose = PoseSample(yaw=5.0)
    tracker._has_last_pose = True
    tracker._last_pose_timestamp = time.monotonic()

    for _ in range(HeadPoseTracker._POSE_RESET_MISSED_DETECTIONS):
        tracker._mark_detection_lost()

    assert tracker._has_last_pose is False
    assert tracker._last_pose == PoseSample()
    assert tracker._last_pose_timestamp is None


def test_face_zoom_roi_expands_small_face_without_leaving_frame() -> None:
    roi = HeadPoseTracker._face_roi_for_zoom((300, 160, 80, 90), 640, 480)

    assert roi is not None
    x, y, w, h = roi
    assert x >= 0
    assert y >= 0
    assert x + w <= 640
    assert y + h <= 480
    assert w > 80
    assert h > 90


def test_zoom_landmarks_are_remapped_to_original_frame_coordinates() -> None:
    roi = (100, 50, 200, 100)
    landmarks = [
        SimpleNamespace(x=0.25, y=0.50, z=-0.10),
        SimpleNamespace(x=0.75, y=0.25, z=0.05),
    ]

    remapped = HeadPoseTracker._remap_landmarks_from_roi(landmarks, roi, 800, 400)

    assert remapped[0].x == pytest.approx((100 + 0.25 * 200) / 800)
    assert remapped[0].y == pytest.approx((50 + 0.50 * 100) / 400)
    assert remapped[0].z == pytest.approx(-0.10 * (200 / 800))
    assert remapped[1].x == pytest.approx((100 + 0.75 * 200) / 800)
