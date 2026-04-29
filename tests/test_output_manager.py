import pytest

import eye_drive_tracker.output.manager as manager_module
from eye_drive_tracker.output.manager import OutputManager
from eye_drive_tracker.tracking.models import PoseSample


def _capture_sent_poses(monkeypatch):
    sent: list[PoseSample] = []

    def capture(pose, *_args, **_kwargs):
        sent.append(pose)
        return "sent"

    monkeypatch.setattr(manager_module, "sendOutputToGame", capture)
    return sent


def test_output_manager_holds_tiny_side_jitter_before_game_send(monkeypatch) -> None:
    sent = _capture_sent_poses(monkeypatch)
    output = OutputManager()
    output.running = True
    output.last_pose = PoseSample(yaw=20.0)
    output._target_pose = PoseSample(yaw=20.0)
    output._has_target = True
    output._last_target_time = 1.000
    output._last_tick_time = 1.000

    output.push_target_pose(PoseSample(yaw=20.04), now=1.016)
    output.tick(now=1.024)

    assert sent[-1].yaw == pytest.approx(20.0)


def test_output_manager_still_moves_for_real_side_change(monkeypatch) -> None:
    sent = _capture_sent_poses(monkeypatch)
    output = OutputManager()
    output.running = True
    output.last_pose = PoseSample(yaw=20.0)
    output._target_pose = PoseSample(yaw=20.0)
    output._has_target = True
    output._last_target_time = 1.000
    output._last_tick_time = 1.000

    output.push_target_pose(PoseSample(yaw=20.6), now=1.016)
    output.tick(now=1.024)

    assert sent[-1].yaw > 20.0
