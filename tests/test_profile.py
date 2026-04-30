# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from eye_drive_tracker.profiles.profile import TrackingConfig


def test_tracking_config_defaults_to_user_preferred_inversions() -> None:
    config = TrackingConfig()

    assert config.invert_yaw is True
    assert config.invert_pitch is True
    assert config.invert_roll is False
    assert config.invert_z is True
