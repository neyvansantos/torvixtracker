# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import pytest

from eye_drive_tracker.tracking.models import PoseSample
from eye_drive_tracker.ui.main_window import (
    _center_pose_to_reference,
    _hotkey_label,
    _is_structured_hotkey,
    _legacy_hotkey_to_keyboard_spec,
    _parse_joystick_hotkey_spec,
    _parse_keyboard_hotkey_spec,
    _parse_xinput_hotkey_spec,
)


def test_center_pose_to_reference_zeroes_current_center() -> None:
    pose = PoseSample(yaw=-12.5, pitch=4.0, roll=2.5, x=1.0, y=-2.0, z=3.0)

    centered = _center_pose_to_reference(pose, pose)

    assert centered == PoseSample()


def test_center_pose_to_reference_wraps_rotation_deltas() -> None:
    centered = _center_pose_to_reference(
        PoseSample(yaw=-179.0, pitch=-100.0, roll=179.0),
        PoseSample(yaw=179.0, pitch=0.0, roll=-179.0),
    )

    assert centered.yaw == pytest.approx(2.0)
    assert centered.pitch == pytest.approx(80.0)
    assert centered.roll == pytest.approx(-2.0)


def test_keyboard_hotkey_spec_keeps_display_label_and_modifiers() -> None:
    spec = "kb:82:3:Ctrl+Alt+R"

    assert _is_structured_hotkey(spec)
    assert _hotkey_label(spec) == "Ctrl+Alt+R"
    assert _parse_keyboard_hotkey_spec(spec) == (82, 3)


def test_joystick_hotkey_spec_keeps_device_and_button() -> None:
    spec = "joy:1:4:Controle 2 Botao 5"

    assert _is_structured_hotkey(spec)
    assert _hotkey_label(spec) == "Controle 2 Botao 5"
    assert _parse_joystick_hotkey_spec(spec) == (1, 4)


def test_joystick_hotkey_spec_supports_any_controller_button() -> None:
    spec = "joy:any:4:Controle Botao 5"

    assert _is_structured_hotkey(spec)
    assert _hotkey_label(spec) == "Controle Botao 5"
    assert _parse_joystick_hotkey_spec(spec) == (None, 4)


def test_xinput_hotkey_spec_keeps_device_and_button_bit() -> None:
    spec = "xinput:0:4096:Controle XInput 1 A"

    assert _is_structured_hotkey(spec)
    assert _hotkey_label(spec) == "Controle XInput 1 A"
    assert _parse_xinput_hotkey_spec(spec) == (0, 4096)


def test_legacy_hotkey_is_converted_for_global_polling() -> None:
    spec = _legacy_hotkey_to_keyboard_spec("Ctrl+Alt+R")

    assert _hotkey_label(spec) == "Ctrl+Alt+R"
    assert _parse_keyboard_hotkey_spec(spec) == (82, 3)
