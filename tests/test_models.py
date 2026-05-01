# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from eye_drive_tracker.tracking.models import GazeSample, PoseSample, TrackingResult

def test_pose_sample_defaults():
    pose = PoseSample()
    assert pose.yaw == 0.0
    assert pose.pitch == 0.0
    assert pose.roll == 0.0
    assert pose.x == 0.0
    assert pose.y == 0.0
    assert pose.z == 0.0

def test_tracking_result_defaults():
    result = TrackingResult()
    assert result.detected is False
    assert isinstance(result.pose, PoseSample)
    assert isinstance(result.gaze, GazeSample)
    assert result.method == "none"
    assert result.face_box is None
    assert result.gaze.confidence == 0.0
    assert result.left_eye_points == []
    assert result.right_eye_points == []
    assert result.eye_boxes == []

def test_pose_sample_custom_values():
    pose = PoseSample(yaw=10.5, pitch=-5.2, roll=1.0, x=100, y=200, z=300)
    assert pose.yaw == 10.5
    assert pose.pitch == -5.2
    assert pose.roll == 1.0
    assert pose.x == 100
    assert pose.y == 200
    assert pose.z == 300
