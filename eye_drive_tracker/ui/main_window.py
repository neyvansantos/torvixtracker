from __future__ import annotations

import html
import ctypes
import os
import sys
import time
import webbrowser
from ctypes import wintypes
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, QEvent, QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QImage, QKeyEvent, QKeySequence, QPainter, QPixmap, QResizeEvent, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from eye_drive_tracker import __app_name__, __version__
from eye_drive_tracker.camera import CameraDevice, CameraEnumerator, Webcam
from eye_drive_tracker.filters import PipelineOutput, PoseFilter
from eye_drive_tracker.output import OUTPUT_MODE_LABELS, OutputManager
from eye_drive_tracker.profiles import ProfileManager, TrackingConfig
from eye_drive_tracker.tracking import AsyncHeadPoseWorker, GazeSample, PoseSample, TrackingResult
from eye_drive_tracker.updater import UpdateChecker

from .controls import FloatSlider
from .camera_settings_dialog import CameraSettingsDialog
from .calibration_wizard import CalibrationWizard
from .i18n import LANGUAGES, translate


HELP_KEYS = {
    "profile_name": "help_profile_name",
    "camera_index": "help_camera_index",
    "tracking_context": "help_tracking_context",
    "input_deadzone": "help_input_deadzone",
    "head_view_responsiveness": "help_head_view_responsiveness",
    "head_view_smoothing": "help_head_view_smoothing",
    "head_yaw_sensitivity_cabin": "help_head_yaw_sensitivity_cabin",
    "head_pitch_sensitivity_cabin": "help_head_pitch_sensitivity_cabin",
    "head_yaw_sensitivity_walk": "help_head_yaw_sensitivity_walk",
    "head_pitch_sensitivity_walk": "help_head_pitch_sensitivity_walk",
    "head_roll_sensitivity": "help_head_roll_sensitivity",
    "head_tracking_exponent": "help_head_tracking_exponent",
    "head_tracking_inflection_point": "help_head_tracking_inflection_point",
    "head_tracking_start_point": "help_head_tracking_start_point",
    "head_tracking_end_point": "help_head_tracking_end_point",
    "max_head_angle": "help_max_head_angle",
    "invert_yaw": "help_invert_yaw",
    "invert_pitch": "help_invert_pitch",
    "invert_roll": "help_invert_roll",
    "translation_deadzone": "help_translation_deadzone",
    "translation_smoothing": "help_translation_smoothing",
    "translation_x_sensitivity": "help_translation_x_sensitivity",
    "translation_y_sensitivity": "help_translation_y_sensitivity",
    "translation_z_sensitivity": "help_translation_z_sensitivity",
    "invert_x": "help_invert_x",
    "invert_y": "help_invert_y",
    "invert_z": "help_invert_z",
    "enable_simulated_gaze": "help_enable_simulated_gaze",
    "gaze_view_responsiveness": "help_gaze_view_responsiveness",
    "gaze_view_smoothing": "help_gaze_view_smoothing",
    "gaze_tracking_exponent": "help_gaze_tracking_exponent",
    "gaze_tracking_inflection_point": "help_gaze_tracking_inflection_point",
    "gaze_tracking_start_point": "help_gaze_tracking_start_point",
    "gaze_tracking_end_point": "help_gaze_tracking_end_point",
    "max_gaze_angle": "help_max_gaze_angle",
    "gaze_strength": "help_gaze_strength",
    "invert_gaze_yaw": "help_invert_gaze_yaw",
    "invert_gaze_pitch": "help_invert_gaze_pitch",
    "enable_extended_view": "help_enable_extended_view",
    "debug_extended_view": "help_debug_extended_view",
    "extended_view_strength": "help_extended_view_strength",
    "extended_view_blend": "help_extended_view_blend",
    "extended_view_exponent": "help_extended_view_exponent",
    "extended_view_inflection_point": "help_extended_view_inflection_point",
    "extended_view_start_point": "help_extended_view_start_point",
    "extended_view_end_point": "help_extended_view_end_point",
    "extended_view_acceleration": "help_extended_view_acceleration",
    "extended_view_max_angle": "help_extended_view_max_angle",
    "extended_view_smoothing": "help_extended_view_smoothing",
    "output_smoothing": "help_output_smoothing",
    "output_micro_jitter": "help_output_micro_jitter",
    "output_max_step": "help_output_max_step",
    "recenter_hotkey": "help_recenter_hotkey",
    "output_mode": "help_output_mode",
    "connection_status": "help_connection_status",
}


GAME_FUNCTION_HELP_SECTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Head Tracking",
        (
            ("Tracking context", "game_help_tracking_context"),
            ("Deadzone", "game_help_input_deadzone"),
            ("Head view responsiveness", "game_help_head_view_responsiveness"),
            ("Head view smoothing", "game_help_head_view_smoothing"),
            ("Head tracking yaw sensitivity (in cabin)", "game_help_head_yaw_sensitivity_cabin"),
            ("Head tracking pitch sensitivity (in cabin)", "game_help_head_pitch_sensitivity_cabin"),
            ("Head tracking yaw sensitivity (in walk mode)", "game_help_head_yaw_sensitivity_walk"),
            ("Head tracking pitch sensitivity (in walk mode)", "game_help_head_pitch_sensitivity_walk"),
            ("Head tracking roll sensitivity", "game_help_head_roll_sensitivity"),
            ("Head tracking exponent", "game_help_head_tracking_exponent"),
            ("Head tracking inflection point", "game_help_head_tracking_inflection_point"),
            ("Head tracking start point", "game_help_head_tracking_start_point"),
            ("Head tracking end point", "game_help_head_tracking_end_point"),
            ("Head angle scale", "game_help_max_head_angle"),
            ("Invert yaw", "game_help_invert_yaw"),
            ("Invert pitch", "game_help_invert_pitch"),
            ("Invert roll", "game_help_invert_roll"),
        ),
    ),
    (
        "Translation Tracking Settings",
        (
            ("Translation deadzone", HELP_KEYS["translation_deadzone"]),
            ("Translation smoothing", HELP_KEYS["translation_smoothing"]),
            ("Translation X sensitivity", HELP_KEYS["translation_x_sensitivity"]),
            ("Translation Y sensitivity", HELP_KEYS["translation_y_sensitivity"]),
            ("Translation Z sensitivity", HELP_KEYS["translation_z_sensitivity"]),
            ("Invert X", HELP_KEYS["invert_x"]),
            ("Invert Y", HELP_KEYS["invert_y"]),
            ("Invert Z", HELP_KEYS["invert_z"]),
        ),
    ),
    (
        "Iris Settings",
        (
            ("Enable iris gaze", HELP_KEYS["enable_simulated_gaze"]),
            ("Gaze view responsiveness", HELP_KEYS["gaze_view_responsiveness"]),
            ("Gaze view smoothing", HELP_KEYS["gaze_view_smoothing"]),
            ("Gaze tracking exponent", HELP_KEYS["gaze_tracking_exponent"]),
            ("Gaze tracking inflection point", HELP_KEYS["gaze_tracking_inflection_point"]),
            ("Gaze tracking start point", HELP_KEYS["gaze_tracking_start_point"]),
            ("Gaze tracking end point", HELP_KEYS["gaze_tracking_end_point"]),
            ("Gaze angle scale", HELP_KEYS["max_gaze_angle"]),
            ("Gaze strength", HELP_KEYS["gaze_strength"]),
            ("Invert gaze yaw", HELP_KEYS["invert_gaze_yaw"]),
            ("Invert gaze pitch", HELP_KEYS["invert_gaze_pitch"]),
        ),
    ),
    (
        "Extended View Settings",
        (
            ("Enable Extended View", HELP_KEYS["enable_extended_view"]),
            ("Debug Extended View", HELP_KEYS["debug_extended_view"]),
            ("Extended View strength", HELP_KEYS["extended_view_strength"]),
            ("Extended View blend", HELP_KEYS["extended_view_blend"]),
            ("Extended View exponent", HELP_KEYS["extended_view_exponent"]),
            ("Extended View inflection point", HELP_KEYS["extended_view_inflection_point"]),
            ("Extended View start point", HELP_KEYS["extended_view_start_point"]),
            ("Extended View end point", HELP_KEYS["extended_view_end_point"]),
            ("Extended View acceleration", HELP_KEYS["extended_view_acceleration"]),
            ("Extended View angle scale", HELP_KEYS["extended_view_max_angle"]),
            ("Extended View smoothing", HELP_KEYS["extended_view_smoothing"]),
        ),
    ),
    (
        "Sensitivity & Curves",
        (
            ("Output smoothing", HELP_KEYS["output_smoothing"]),
            ("Micro jitter threshold", HELP_KEYS["output_micro_jitter"]),
            ("Max output step per frame", HELP_KEYS["output_max_step"]),
        ),
    ),
    (
        "Focus Settings",
        (
            ("Recenter hotkey", HELP_KEYS["recenter_hotkey"]),
        ),
    ),
    (
        "Track",
        (
            ("Output mode", HELP_KEYS["output_mode"]),
            ("Connection status", HELP_KEYS["connection_status"]),
        ),
    ),
)


def _runtime_asset_path(filename: str) -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base_path = Path(__file__).resolve().parents[2]
    return base_path / "assets" / filename


def _wrap_angle(value: float) -> float:
    wrapped = (float(value) + 180.0) % 360.0 - 180.0
    return 180.0 if abs(wrapped + 180.0) <= 1e-9 else wrapped


def _normalize_pitch_delta(value: float) -> float:
    pitch = _wrap_angle(value)
    if pitch < -90.0:
        pitch += 180.0
    elif pitch > 90.0:
        pitch -= 180.0
    return pitch


def _center_pose_to_reference(pose: PoseSample, center: PoseSample) -> PoseSample:
    return PoseSample(
        yaw=_wrap_angle(pose.yaw - center.yaw),
        pitch=_normalize_pitch_delta(pose.pitch - center.pitch),
        roll=_wrap_angle(pose.roll - center.roll),
        x=pose.x - center.x,
        y=pose.y - center.y,
        z=pose.z - center.z,
    )


_HOTKEY_CTRL = 1
_HOTKEY_ALT = 2
_HOTKEY_SHIFT = 4
_HOTKEY_META = 8
_HOTKEY_POLL_MS = 20
_JOY_RETURNBUTTONS = 0x80
_VK_PRESSED = 0x8000
_ERROR_SUCCESS = 0

_VK_CONTROL = 0x11
_VK_SHIFT = 0x10
_VK_MENU = 0x12
_VK_LCONTROL = 0xA2
_VK_RCONTROL = 0xA3
_VK_LSHIFT = 0xA0
_VK_RSHIFT = 0xA1
_VK_LMENU = 0xA4
_VK_RMENU = 0xA5
_VK_LWIN = 0x5B
_VK_RWIN = 0x5C

_XINPUT_BUTTON_LABELS = {
    0x0001: "DPad Up",
    0x0002: "DPad Down",
    0x0004: "DPad Left",
    0x0008: "DPad Right",
    0x0010: "Start",
    0x0020: "Back",
    0x0040: "LStick",
    0x0080: "RStick",
    0x0100: "LB",
    0x0200: "RB",
    0x1000: "A",
    0x2000: "B",
    0x4000: "X",
    0x8000: "Y",
}

_QT_KEY_TO_VK = {
    int(Qt.Key_Backspace): 0x08,
    int(Qt.Key_Tab): 0x09,
    int(Qt.Key_Return): 0x0D,
    int(Qt.Key_Enter): 0x0D,
    int(Qt.Key_Escape): 0x1B,
    int(Qt.Key_Space): 0x20,
    int(Qt.Key_PageUp): 0x21,
    int(Qt.Key_PageDown): 0x22,
    int(Qt.Key_End): 0x23,
    int(Qt.Key_Home): 0x24,
    int(Qt.Key_Left): 0x25,
    int(Qt.Key_Up): 0x26,
    int(Qt.Key_Right): 0x27,
    int(Qt.Key_Down): 0x28,
    int(Qt.Key_Insert): 0x2D,
    int(Qt.Key_Delete): 0x2E,
    int(Qt.Key_Shift): _VK_SHIFT,
    int(Qt.Key_Control): _VK_CONTROL,
    int(Qt.Key_Alt): _VK_MENU,
    int(Qt.Key_Meta): _VK_LWIN,
    int(Qt.Key_Minus): 0xBD,
    int(Qt.Key_Equal): 0xBB,
    int(Qt.Key_BracketLeft): 0xDB,
    int(Qt.Key_BracketRight): 0xDD,
    int(Qt.Key_Backslash): 0xDC,
    int(Qt.Key_Semicolon): 0xBA,
    int(Qt.Key_Apostrophe): 0xDE,
    int(Qt.Key_Comma): 0xBC,
    int(Qt.Key_Period): 0xBE,
    int(Qt.Key_Slash): 0xBF,
    int(Qt.Key_QuoteLeft): 0xC0,
}
for _function_key_index in range(1, 25):
    _QT_KEY_TO_VK[int(getattr(Qt, f"Key_F{_function_key_index}"))] = 0x6F + _function_key_index


class _JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),
        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", _XINPUT_GAMEPAD),
    ]


_USER32 = None
_WINMM = None
_XINPUT = None


def _user32():
    global _USER32
    if os.name != "nt":
        return None
    if _USER32 is None:
        windll = getattr(ctypes, "WinDLL", None)
        if windll is None:
            return None
        try:
            _USER32 = windll("user32", use_last_error=True)
        except OSError:
            return None
    return _USER32


def _winmm():
    global _WINMM
    if os.name != "nt":
        return None
    if _WINMM is None:
        windll = getattr(ctypes, "WinDLL", None)
        if windll is None:
            return None
        try:
            winmm = windll("winmm")
            winmm.joyGetNumDevs.restype = wintypes.UINT
            winmm.joyGetPosEx.argtypes = [wintypes.UINT, ctypes.POINTER(_JOYINFOEX)]
            winmm.joyGetPosEx.restype = wintypes.UINT
            _WINMM = winmm
        except OSError:
            return None
    return _WINMM


def _xinput():
    global _XINPUT
    if os.name != "nt":
        return None
    if _XINPUT is None:
        windll = getattr(ctypes, "WinDLL", None)
        if windll is None:
            return None
        for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                xinput = windll(dll_name)
                xinput.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(_XINPUT_STATE)]
                xinput.XInputGetState.restype = wintypes.DWORD
                _XINPUT = xinput
                break
            except OSError:
                continue
        else:
            return None
    return _XINPUT


def _async_key_down(vk: int) -> bool:
    user32 = _user32()
    if user32 is None or vk <= 0:
        return False
    return bool(user32.GetAsyncKeyState(int(vk)) & _VK_PRESSED)


def _any_async_key_down(*vks: int) -> bool:
    return any(_async_key_down(vk) for vk in vks)


def _current_modifier_mask() -> int:
    mask = 0
    if _any_async_key_down(_VK_CONTROL, _VK_LCONTROL, _VK_RCONTROL):
        mask |= _HOTKEY_CTRL
    if _any_async_key_down(_VK_MENU, _VK_LMENU, _VK_RMENU):
        mask |= _HOTKEY_ALT
    if _any_async_key_down(_VK_SHIFT, _VK_LSHIFT, _VK_RSHIFT):
        mask |= _HOTKEY_SHIFT
    if _any_async_key_down(_VK_LWIN, _VK_RWIN):
        mask |= _HOTKEY_META
    return mask


def _qt_key_to_vk(key: int) -> int:
    key = int(key)
    if 0x30 <= key <= 0x39 or 0x41 <= key <= 0x5A:
        return key
    return _QT_KEY_TO_VK.get(key, 0)


def _modifier_mask_for_key(key: int) -> int:
    key = int(key)
    if key == int(Qt.Key_Control):
        return _HOTKEY_CTRL
    if key == int(Qt.Key_Alt):
        return _HOTKEY_ALT
    if key == int(Qt.Key_Shift):
        return _HOTKEY_SHIFT
    if key == int(Qt.Key_Meta):
        return _HOTKEY_META
    return 0


def _modifiers_to_hotkey_mask(modifiers: Qt.KeyboardModifiers, key: int | None = None) -> int:
    key_mask = _modifier_mask_for_key(key) if key is not None else 0
    mask = 0
    if modifiers & Qt.ControlModifier and key_mask != _HOTKEY_CTRL:
        mask |= _HOTKEY_CTRL
    if modifiers & Qt.AltModifier and key_mask != _HOTKEY_ALT:
        mask |= _HOTKEY_ALT
    if modifiers & Qt.ShiftModifier and key_mask != _HOTKEY_SHIFT:
        mask |= _HOTKEY_SHIFT
    if modifiers & Qt.MetaModifier and key_mask != _HOTKEY_META:
        mask |= _HOTKEY_META
    return mask | key_mask


def _keyboard_modifier_labels(mask: int, key: int | None = None) -> list[str]:
    key_mask = _modifier_mask_for_key(key) if key is not None else 0
    labels = []
    if mask & _HOTKEY_CTRL and key_mask != _HOTKEY_CTRL:
        labels.append("Ctrl")
    if mask & _HOTKEY_ALT and key_mask != _HOTKEY_ALT:
        labels.append("Alt")
    if mask & _HOTKEY_SHIFT and key_mask != _HOTKEY_SHIFT:
        labels.append("Shift")
    if mask & _HOTKEY_META and key_mask != _HOTKEY_META:
        labels.append("Win")
    return labels


def _key_label_from_event(event: QKeyEvent) -> str:
    key = int(event.key())
    label = QKeySequence(key).toString(QKeySequence.NativeText)
    if not label and event.text():
        label = event.text().upper()
    if not label:
        label = f"VK {event.nativeVirtualKey() or _qt_key_to_vk(key)}"
    return label


def _make_keyboard_hotkey_spec(vk: int, modifiers: Qt.KeyboardModifiers, key: int, label: str) -> str:
    mod_mask = _modifiers_to_hotkey_mask(modifiers, key)
    parts = _keyboard_modifier_labels(mod_mask, key)
    parts.append(label)
    display = "+".join(part for part in parts if part)
    return f"kb:{int(vk)}:{mod_mask}:{display}"


def _make_joystick_hotkey_spec(device_id: int, button_index: int) -> str:
    label = f"Controle {device_id + 1} Botao {button_index + 1}"
    return f"joy:{device_id}:{button_index}:{label}"


def _make_xinput_hotkey_spec(user_index: int, button_bit: int) -> str:
    button_label = _XINPUT_BUTTON_LABELS.get(button_bit, f"Botao {button_bit}")
    label = f"Controle XInput {user_index + 1} {button_label}"
    return f"xinput:{user_index}:{button_bit}:{label}"


def _is_structured_hotkey(spec: str) -> bool:
    spec = (spec or "").strip()
    return spec.startswith(("kb:", "joy:", "xinput:"))


def _hotkey_label(spec: str) -> str:
    spec = (spec or "").strip()
    if not spec:
        return ""
    if spec.startswith("kb:"):
        parts = spec.split(":", 3)
        if len(parts) == 4:
            return parts[3] or f"VK {parts[1]}"
    if spec.startswith("joy:"):
        parts = spec.split(":", 3)
        if len(parts) == 4:
            if parts[3]:
                return parts[3]
            try:
                return f"Controle {int(parts[1]) + 1} Botao {int(parts[2]) + 1}"
            except ValueError:
                return spec
    if spec.startswith("xinput:"):
        parts = spec.split(":", 3)
        if len(parts) == 4:
            if parts[3]:
                return parts[3]
            try:
                return f"Controle XInput {int(parts[1]) + 1} Botao {parts[2]}"
            except ValueError:
                return spec
    return spec


def _parse_keyboard_hotkey_spec(spec: str) -> tuple[int, int] | None:
    parts = (spec or "").strip().split(":", 3)
    if len(parts) != 4 or parts[0] != "kb":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _parse_joystick_hotkey_spec(spec: str) -> tuple[int, int] | None:
    parts = (spec or "").strip().split(":", 3)
    if len(parts) != 4 or parts[0] != "joy":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _parse_xinput_hotkey_spec(spec: str) -> tuple[int, int] | None:
    parts = (spec or "").strip().split(":", 3)
    if len(parts) != 4 or parts[0] != "xinput":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _legacy_hotkey_to_keyboard_spec(hotkey: str) -> str:
    hotkey = (hotkey or "").strip()
    if not hotkey or _is_structured_hotkey(hotkey):
        return hotkey
    sequence = QKeySequence(hotkey)
    if sequence.isEmpty() or sequence.count() < 1:
        return ""
    combo = sequence[0]
    key = int(combo.key())
    vk = _qt_key_to_vk(key)
    if not vk:
        return ""
    label = QKeySequence(combo).toString(QKeySequence.NativeText) or hotkey.split(",", 1)[0].strip()
    return f"kb:{vk}:{_modifiers_to_hotkey_mask(combo.keyboardModifiers(), key)}:{label}"


def _joystick_device_count() -> int:
    winmm = _winmm()
    if winmm is None:
        return 0
    try:
        return max(0, min(int(winmm.joyGetNumDevs()), 16))
    except (OSError, ValueError):
        return 0


def _joystick_button_mask(device_id: int) -> int:
    winmm = _winmm()
    if winmm is None:
        return 0
    info = _JOYINFOEX()
    info.dwSize = ctypes.sizeof(_JOYINFOEX)
    info.dwFlags = _JOY_RETURNBUTTONS
    try:
        if int(winmm.joyGetPosEx(int(device_id), ctypes.byref(info))) != 0:
            return 0
    except OSError:
        return 0
    return int(info.dwButtons)


def _joystick_button_down(device_id: int, button_index: int) -> bool:
    if device_id < 0 or button_index < 0:
        return False
    return bool(_joystick_button_mask(device_id) & (1 << button_index))


def _poll_joystick_masks() -> dict[int, int]:
    return {device_id: _joystick_button_mask(device_id) for device_id in range(_joystick_device_count())}


def _xinput_button_mask(user_index: int) -> int:
    xinput = _xinput()
    if xinput is None:
        return 0
    state = _XINPUT_STATE()
    try:
        result = int(xinput.XInputGetState(int(user_index), ctypes.byref(state)))
    except OSError:
        return 0
    if result != _ERROR_SUCCESS:
        return 0
    return int(state.Gamepad.wButtons)


def _xinput_button_down(user_index: int, button_bit: int) -> bool:
    if user_index < 0 or button_bit <= 0:
        return False
    return bool(_xinput_button_mask(user_index) & button_bit)


def _poll_xinput_masks() -> dict[int, int]:
    return {user_index: _xinput_button_mask(user_index) for user_index in range(4)}


class HotkeyCaptureEdit(QLineEdit):
    hotkeyChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._hotkey_spec = ""
        self._joystick_baseline: dict[int, int] = {}
        self._xinput_baseline: dict[int, int] = {}
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)

        self._joystick_timer = QTimer(self)
        self._joystick_timer.setTimerType(Qt.PreciseTimer)
        self._joystick_timer.setInterval(_HOTKEY_POLL_MS)
        self._joystick_timer.timeout.connect(self._poll_joystick_capture)

    def set_hotkey(self, spec: str) -> None:
        self._hotkey_spec = (spec or "").strip()
        self.setText(_hotkey_label(self._hotkey_spec))

    def hotkey(self) -> str:
        return self._hotkey_spec

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.selectAll()
        self._joystick_baseline = _poll_joystick_masks()
        self._xinput_baseline = _poll_xinput_masks()
        self._joystick_timer.start()

    def focusOutEvent(self, event) -> None:
        self._joystick_timer.stop()
        self.setText(_hotkey_label(self._hotkey_spec))
        super().focusOutEvent(event)

    def event(self, event) -> bool:
        if event.type() == QEvent.KeyPress:
            self.keyPressEvent(event)
            return event.isAccepted()
        return super().event(event)

    def focusNextPrevChild(self, _next: bool) -> bool:
        return False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = int(event.key())
        vk = int(event.nativeVirtualKey()) or _qt_key_to_vk(key)
        if vk <= 0:
            event.ignore()
            return
        spec = _make_keyboard_hotkey_spec(vk, event.modifiers(), key, _key_label_from_event(event))
        self.set_hotkey(spec)
        self.hotkeyChanged.emit(spec)
        event.accept()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.setFocus(Qt.MouseFocusReason)
        self.selectAll()

    def _poll_joystick_capture(self) -> None:
        for device_id, mask in _poll_joystick_masks().items():
            previous = self._joystick_baseline.get(device_id, 0)
            pressed = mask & ~previous
            if not pressed:
                self._joystick_baseline[device_id] = mask
                continue
            button_index = int(pressed & -pressed).bit_length() - 1
            spec = _make_joystick_hotkey_spec(device_id, button_index)
            self.set_hotkey(spec)
            self.hotkeyChanged.emit(spec)
            self.clearFocus()
            return

        for user_index, mask in _poll_xinput_masks().items():
            previous = self._xinput_baseline.get(user_index, 0)
            pressed = mask & ~previous
            if not pressed:
                self._xinput_baseline[user_index] = mask
                continue
            button_bit = pressed & -pressed
            spec = _make_xinput_hotkey_spec(user_index, button_bit)
            self.set_hotkey(spec)
            self.hotkeyChanged.emit(spec)
            self.clearFocus()
            return


class RecenterHotkeyMonitor(QObject):
    activated = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._spec = ""
        self._was_down = False
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(_HOTKEY_POLL_MS)
        self._timer.timeout.connect(self._poll)

    def set_hotkey(self, spec: str) -> None:
        self._spec = _legacy_hotkey_to_keyboard_spec(spec)
        self._was_down = self._is_down()
        if self._spec:
            self._timer.start()
        else:
            self._timer.stop()

    def _is_down(self) -> bool:
        keyboard_hotkey = _parse_keyboard_hotkey_spec(self._spec)
        if keyboard_hotkey is not None:
            vk, mod_mask = keyboard_hotkey
            return _async_key_down(vk) and _current_modifier_mask() == mod_mask

        joystick_hotkey = _parse_joystick_hotkey_spec(self._spec)
        if joystick_hotkey is not None:
            device_id, button_index = joystick_hotkey
            return _joystick_button_down(device_id, button_index)

        xinput_hotkey = _parse_xinput_hotkey_spec(self._spec)
        if xinput_hotkey is not None:
            user_index, button_bit = xinput_hotkey
            return _xinput_button_down(user_index, button_bit)

        return False

    def _poll(self) -> None:
        is_down = self._is_down()
        if is_down and not self._was_down:
            self.activated.emit()
        self._was_down = is_down


class CollapsibleSection(QWidget):
    """Uma seção de acordeão personalizada para organizar as configurações."""
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Botão do Cabeçalho
        self.toggle_button = QPushButton(title)
        self.toggle_button.setObjectName("sectionHeader")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setFixedHeight(40)
        self.toggle_button.clicked.connect(self.toggle)

        # Conteúdo
        self.content_container = QGroupBox()
        self.content_container.setObjectName("sectionContent")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_container.setVisible(False)

        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_container)

    def setTitle(self, title: str):
        """Atualiza o título do cabeçalho."""
        self.toggle_button.setText(title)

    def toggle(self):
        is_checked = self.toggle_button.isChecked()
        self.content_container.setVisible(is_checked)
        # Sincroniza o estado visual se necessário

    def addWidget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout: QVBoxLayout | QGridLayout):
        if isinstance(layout, QGridLayout):
            temp_widget = QWidget()
            temp_widget.setLayout(layout)
            self.content_layout.addWidget(temp_widget)
        else:
            self.content_layout.addLayout(layout)


class WelcomeSplashDialog(QDialog):
    def __init__(self, video_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._capture = cv2.VideoCapture(str(video_path))
        self._available = self._capture.isOpened()
        self._started = False
        self._closing = False
        self._geometry_animation: QPropertyAnimation | None = None
        self._opacity_animation: QPropertyAnimation | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next_frame)

        if not self._available:
            return

        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 1.0 or fps > 120.0:
            fps = 30.0
        self._frame_interval_ms = max(8, int(1000.0 / fps))

        video_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        video_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)
        target_width, target_height = self._target_size(video_width, video_height)

        self.setObjectName("welcomeSplash")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.resize(target_width, target_height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._frame_label = QLabel()
        self._frame_label.setObjectName("welcomeVideo")
        self._frame_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._frame_label)

        self.setStyleSheet(
            """
            QDialog#welcomeSplash {
                background-color: #050505;
            }
            QLabel#welcomeVideo {
                background-color: #000000;
                border: 1px solid #00F2FF;
                border-radius: 10px;
            }
            """
        )

    @property
    def is_available(self) -> bool:
        return self._available

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._started or not self._available:
            return
        self._started = True
        self._start_pop_animation()
        self._show_next_frame()
        self._timer.start(self._frame_interval_ms)

    def done(self, result: int) -> None:
        self._timer.stop()
        if self._capture is not None:
            self._capture.release()
        super().done(result)

    def accept(self) -> None:
        if self._available and self._started and not self._closing:
            self._start_exit_animation()
            return
        super().accept()

    def reject(self) -> None:
        if self._available and self._started and not self._closing:
            self._start_exit_animation()
            return
        super().reject()

    def _show_next_frame(self) -> None:
        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._start_exit_animation()
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        image = QImage(rgb.data, width, height, channels * width, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image)
        self._frame_label.setPixmap(
            pixmap.scaled(
                self._frame_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _start_pop_animation(self) -> None:
        target = self._centered_rect(self.width(), self.height())
        start = self._centered_rect(int(target.width() * 0.84), int(target.height() * 0.84))
        self.setGeometry(start)
        self.setWindowOpacity(0.0)

        self._geometry_animation = QPropertyAnimation(self, b"geometry", self)
        self._geometry_animation.setDuration(260)
        self._geometry_animation.setStartValue(start)
        self._geometry_animation.setEndValue(target)
        self._geometry_animation.setEasingCurve(QEasingCurve.OutBack)
        self._geometry_animation.start()

        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_animation.setDuration(180)
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._opacity_animation.start()

    def _start_exit_animation(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._timer.stop()

        start = self.geometry()
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        end = QRect(start)
        end.moveTop(available.bottom() + 24)

        self._geometry_animation = QPropertyAnimation(self, b"geometry", self)
        self._geometry_animation.setDuration(340)
        self._geometry_animation.setStartValue(start)
        self._geometry_animation.setEndValue(end)
        self._geometry_animation.setEasingCurve(QEasingCurve.InCubic)
        self._geometry_animation.finished.connect(self._finish_exit_animation)
        self._geometry_animation.start()

        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_animation.setDuration(220)
        self._opacity_animation.setStartValue(self.windowOpacity())
        self._opacity_animation.setEndValue(0.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.InCubic)
        self._opacity_animation.start()

    def _finish_exit_animation(self) -> None:
        super().accept()

    def _centered_rect(self, width: int, height: int) -> QRect:
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        rect = QRect(0, 0, width, height)
        rect.moveCenter(available.center())
        return rect

    @staticmethod
    def _target_size(video_width: int, video_height: int) -> tuple[int, int]:
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        max_width = min(760, int(available.width() * 0.72))
        max_height = min(520, int(available.height() * 0.72))
        scale = min(1.0, max_width / max(video_width, 1), max_height / max(video_height, 1))
        return max(1, int(video_width * scale)), max(1, int(video_height * scale))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        
        # Correção para o ícone aparecer na barra de tarefas do Windows
        if sys.platform == "win32":
            import ctypes
            myappid = u"torvix.tracker.eye.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.setWindowTitle(__app_name__)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent
            
        self.assets_path = str(base_path / "assets")
        
        icon_path = base_path / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            # Tenta o .png se o .ico falhar
            icon_png = base_path / "assets" / "icon.png"
            if icon_png.exists():
                self.setWindowIcon(QIcon(str(icon_png)))
                
        self.resize(1180, 820)

        self.config = TrackingConfig()
        self.camera = Webcam()
        self.tracking_worker = AsyncHeadPoseWorker()
        self.pose_filter = PoseFilter()
        self.output_manager = OutputManager()
        self.profile_manager = ProfileManager()
        self.camera_devices = [CameraDevice(index=self.config.camera_index, name=f"{self.config.camera_index} - Webcam")]
        QTimer.singleShot(10, self._load_camera_devices_async)

        self.last_raw_pose: PoseSample | None = None
        self.last_pipeline = PipelineOutput(PoseSample(), PoseSample(), PoseSample(), PoseSample())
        self.last_tracking_result = TrackingResult(detected=False)
        self.tracking_frame_max_width = 1280
        self.preview_max_fps = 60.0
        self._preview_frame_count = 0
        self._preview_fps_started_at = time.monotonic()
        self._preview_fps = 0.0
        self._last_preview_presented_at = 0.0
        self._last_camera_frame_id = 0
        self._syncing_controls = False

        # Rastreamento da area do rosto para estimar profundidade no mascote
        # (invariante a resolucao e ao backend de rastreamento)
        self._mascot_face_area_ref: float = 0.0   # area de referencia (centro)
        self._mascot_face_area_current: float = 0.0  # area atual suavizada

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setInterval(5)
        self.timer.timeout.connect(self._on_frame)

        self.output_timer = QTimer(self)
        self.output_timer.setTimerType(Qt.PreciseTimer)
        self.output_timer.setInterval(8)
        self.output_timer.timeout.connect(self._on_output_tick)

        self.controls: dict[str, FloatSlider] = {}
        self.check_boxes: dict[str, QCheckBox] = {}
        self._localized_widgets: list[tuple[object, str, str]] = []
        self._menu_actions: dict[str, QAction] = {}
        self._language_buttons: dict[str, QPushButton] = {}
        self._language_button_group: QButtonGroup | None = None
        self._debug_extended_widgets: list[QWidget] = []
        self.output_mascot_pixmap: QPixmap | None = None
        self.output_mascot_pose = PoseSample()
        self.recenter_shortcut: QShortcut | None = None
        self.recenter_hotkey_monitor = RecenterHotkeyMonitor(self)
        self.recenter_hotkey_monitor.activated.connect(self._recenter)
        self._game_functions_dialog: QDialog | None = None
        self._update_url = "https://raw.githubusercontent.com/NeyvanSantos/TorvixTracker/main/version.json"
        self._update_checker: UpdateChecker | None = None

        self._build_ui()
        self._build_menu()
        self._sync_controls_from_config()
        self._update_recenter_shortcut()

    def _load_camera_devices_async(self) -> None:
        self.camera_devices = CameraEnumerator.list_cameras()
        if hasattr(self, "camera_combo"):
            self._populate_camera_combo()
        # Pre-warm the cache for the current camera so settings dialog is instant
        CameraEnumerator.list_modes(self.config.camera_index)

    def closeEvent(self, event) -> None:
        self._stop_tracking()
        super().closeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "output_mascot_label"):
            self._refresh_output_mascot()

    def _build_menu(self) -> None:
        self.file_menu = self.menuBar().addMenu(self._tr("File"))
        load_action = QAction(self._tr("Load Profile"), self)
        load_action.triggered.connect(self._load_profile)
        save_action = QAction(self._tr("Save Profile"), self)
        save_action.triggered.connect(self._save_profile)
        self.file_menu.addAction(load_action)
        self.file_menu.addAction(save_action)
        self._menu_actions["Load Profile"] = load_action
        self._menu_actions["Save Profile"] = save_action

        self.help_menu = self.menuBar().addMenu(self._tr("Help"))
        game_functions_action = QAction(self._tr("Game Functions"), self)
        game_functions_action.triggered.connect(self._show_game_functions_dialog)
        self.help_menu.addAction(game_functions_action)
        self._menu_actions["Game Functions"] = game_functions_action

        self.about_menu = self.menuBar().addMenu(self._tr("About"))

        about_action = QAction(self._tr("About & Credits"), self)
        about_action.triggered.connect(self._show_about_dialog)
        self.about_menu.addAction(about_action)
        self._menu_actions["About & Credits"] = about_action

        changelog_action = QAction(self._tr("Changelog"), self)
        changelog_action.triggered.connect(self._show_changelog)
        self.about_menu.addAction(changelog_action)
        self._menu_actions["Changelog"] = changelog_action

        update_action = QAction(self._tr("Check for Updates"), self)
        update_action.triggered.connect(self._check_for_updates)
        self.about_menu.addAction(update_action)
        self._menu_actions["Check for Updates"] = update_action

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("centralWidget")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        # Branding (Logo + Nome)
        branding_container = QWidget()
        branding_layout = QHBoxLayout(branding_container)
        branding_layout.setContentsMargins(5, 0, 5, 10)
        branding_layout.setSpacing(12)
        
        logo_mini = QLabel()
        logo_pix = QPixmap(os.path.join(self.assets_path, "icon.png"))
        if not logo_pix.isNull():
            logo_mini.setPixmap(logo_pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        app_title = QLabel("Torvix Tracker")
        app_title.setObjectName("mainAppTitle")
        
        branding_layout.addWidget(logo_mini)
        branding_layout.addWidget(app_title)
        
        top_bar.addWidget(branding_container)
        top_bar.addStretch(1)
        top_bar.addWidget(self._build_language_selector())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        left_container = QWidget()
        left_container.setMaximumWidth(640)
        left_container.setMinimumWidth(460)
        left_panel = QVBoxLayout(left_container)
        left_panel.setSpacing(10)
        self.video_label = self._label("Camera stopped")
        self.video_label.setObjectName("videoPreview")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(480, 288)
        self.video_label.setMaximumWidth(620)
        self.video_label.setMaximumHeight(360)
        self.video_label.setScaledContents(False)
        left_panel.addWidget(self.video_label, 1)
        left_panel.addWidget(self._build_telemetry_panel())
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(500)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(self._build_settings_panel())

        content_layout.addWidget(left_container, 2)
        content_layout.addWidget(scroll, 3)
        root_layout.addLayout(top_bar)
        root_layout.addLayout(content_layout, 1)
        
        # Footer Credit
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.footer_label = self._label("Developed by")
        self.footer_label.setObjectName("footerCredit")
        self.footer_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px; margin-top: 5px;")
        footer.addWidget(self.footer_label)
        root_layout.addLayout(footer)

        self.setCentralWidget(root)
        self._apply_style()

    def _build_language_selector(self) -> QWidget:
        container = QWidget()
        container.setObjectName("languageSelector")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)
        self.language_label = self._label("Language")
        self.language_label.setObjectName("languageSelectorLabel")
        layout.addWidget(self.language_label)
        layout.addSpacing(10)

        self._language_button_group = QButtonGroup(self)
        self._language_button_group.setExclusive(True)
        for language in LANGUAGES:
            button = QPushButton(language)
            button.setObjectName("languageOption")
            button.setCheckable(True)
            button.setMinimumWidth(48)
            button.clicked.connect(lambda _checked=False, value=language: self._on_language_changed(value))
            self._language_buttons[language] = button
            self._language_button_group.addButton(button)
            layout.addWidget(button)
        return container

    def _tr(self, key: str) -> str:
        return translate(self.config.language, key)

    def _localize(self, widget, key: str, setter: str = "setText"):
        self._localized_widgets.append((widget, key, setter))
        getattr(widget, setter)(self._tr(key))
        return widget

    def _label(self, key: str) -> QLabel:
        return self._localize(QLabel(), key)

    def _button(self, key: str) -> QPushButton:
        return self._localize(QPushButton(), key)

    def _set_localized_tooltip(self, widget, key: str) -> None:
        self._localized_widgets.append((widget, key, "setToolTip"))
        widget.setToolTip(self._tr(key))

    def _help_button(self, help_key: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("helpIconButton")
        button.setText("?")
        button.setCursor(Qt.PointingHandCursor)
        button.setAutoRaise(True)
        button.setFixedSize(18, 18)
        button.setFocusPolicy(Qt.NoFocus)
        self._set_localized_tooltip(button, help_key)
        return button

    def _label_with_help(self, key: str, help_key: str | None = None) -> QWidget:
        label = self._label(key)
        if not help_key:
            return label

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(label)
        layout.addWidget(self._help_button(help_key))
        layout.addStretch(1)
        return container

    def _group(self, key: str) -> QGroupBox:
        return self._localize(QGroupBox(), key, "setTitle")

    def _build_telemetry_panel(self) -> QWidget:
        group = self._group("Realtime Values")
        group.setObjectName("telemetryPanel")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        self.status_label = QLabel(self._tr("Stopped"))
        self.backend_label = QLabel(self.tracking_worker.backend_name)
        self.connection_status_label = QLabel(self._tr("Stopped"))
        self.camera_mode_label = QLabel("--")
        self.preview_fps_label = QLabel("--")

        self.raw_yaw_label = QLabel("--")
        self.raw_pitch_label = QLabel("--")
        self.raw_roll_label = QLabel("--")
        self.head_yaw_label = QLabel("--")
        self.head_pitch_label = QLabel("--")
        self.head_roll_label = QLabel("--")
        self.gaze_yaw_label = QLabel("--")
        self.gaze_pitch_label = QLabel("--")
        self.gaze_confidence_label = QLabel("--")
        self.gaze_source_label = QLabel("--")
        self.extended_yaw_label = QLabel("--")
        self.extended_pitch_label = QLabel("--")
        self.final_yaw_label = QLabel("--")
        self.final_pitch_label = QLabel("--")
        self.final_roll_label = QLabel("--")
        self.debug_extended_normalized_yaw_label = QLabel("--")
        self.debug_extended_normalized_pitch_label = QLabel("--")
        self.debug_extended_curve_yaw_label = QLabel("--")
        self.debug_extended_curve_pitch_label = QLabel("--")
        self.debug_extended_before_yaw_label = QLabel("--")
        self.debug_extended_before_pitch_label = QLabel("--")
        self.debug_extended_after_yaw_label = QLabel("--")
        self.debug_extended_after_pitch_label = QLabel("--")
        self.debug_extended_final_yaw_label = QLabel("--")
        self.debug_extended_final_pitch_label = QLabel("--")
        self.debug_extended_final_roll_label = QLabel("--")

        row = 0
        layout.addWidget(self._label("Tracking status"), row, 0)
        layout.addWidget(self.status_label, row, 1)
        layout.addWidget(self._label("Detection backend"), row, 2)
        layout.addWidget(self.backend_label, row, 3)
        row += 1
        layout.addWidget(self._label("Output status"), row, 0)
        layout.addWidget(self.connection_status_label, row, 1, 1, 3)
        row += 1
        layout.addWidget(self._label("Camera mode"), row, 0)
        layout.addWidget(self.camera_mode_label, row, 1)
        layout.addWidget(self._label("Preview FPS"), row, 2)
        layout.addWidget(self.preview_fps_label, row, 3)
        row += 1
        self._add_pose_row(layout, row, "Raw", self.raw_yaw_label, self.raw_pitch_label, self.raw_roll_label)
        row += 1
        self._add_pose_row(layout, row, "Head", self.head_yaw_label, self.head_pitch_label, self.head_roll_label)
        row += 1
        self._add_pose_row(layout, row, "Iris gaze", self.gaze_yaw_label, self.gaze_pitch_label, QLabel("0.00"))
        row += 1
        layout.addWidget(self._label("Gaze confidence"), row, 0)
        layout.addWidget(self.gaze_confidence_label, row, 1)
        layout.addWidget(self._label("Gaze source"), row, 2)
        layout.addWidget(self.gaze_source_label, row, 3, 1, 4)
        row += 1
        self._add_pose_row(layout, row, "Extended", self.extended_yaw_label, self.extended_pitch_label, QLabel("0.00"))
        row += 1
        self._add_pose_row(layout, row, "Final output", self.final_yaw_label, self.final_pitch_label, self.final_roll_label)
        row += 1
        self._add_extended_debug_row(
            layout,
            row,
            "Debug normalized input",
            self.debug_extended_normalized_yaw_label,
            self.debug_extended_normalized_pitch_label,
        )
        row += 1
        self._add_extended_debug_row(
            layout,
            row,
            "Debug curve value",
            self.debug_extended_curve_yaw_label,
            self.debug_extended_curve_pitch_label,
        )
        row += 1
        self._add_extended_debug_row(
            layout,
            row,
            "Debug before smoothing",
            self.debug_extended_before_yaw_label,
            self.debug_extended_before_pitch_label,
        )
        row += 1
        self._add_extended_debug_row(
            layout,
            row,
            "Debug after smoothing",
            self.debug_extended_after_yaw_label,
            self.debug_extended_after_pitch_label,
        )
        row += 1
        self._add_extended_debug_pose_row(
            layout,
            row,
            "Debug final output",
            self.debug_extended_final_yaw_label,
            self.debug_extended_final_pitch_label,
            self.debug_extended_final_roll_label,
        )

        row += 1
        # Adiciona um pequeno espaçador antes do mascote
        layout.setRowStretch(row, 0)
        
        row += 1
        self.output_mascot_label = QLabel()
        self.output_mascot_label.setObjectName("outputMascot")
        self.output_mascot_label.setAlignment(Qt.AlignCenter)
        self.output_mascot_label.setMinimumHeight(240)
        layout.addWidget(self.output_mascot_label, row, 0, 1, 7)
        self._load_output_mascot()

        for column in range(7):
            layout.setColumnStretch(column, 1)
        return group

    def _add_pose_row(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        yaw_label: QLabel,
        pitch_label: QLabel,
        roll_label: QLabel,
    ) -> None:
        layout.addWidget(self._label(label), row, 0)
        layout.addWidget(self._label("Yaw"), row, 1)
        layout.addWidget(yaw_label, row, 2)
        layout.addWidget(self._label("Pitch"), row, 3)
        layout.addWidget(pitch_label, row, 4)
        layout.addWidget(self._label("Roll"), row, 5)
        layout.addWidget(roll_label, row, 6)

    def _add_extended_debug_row(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        yaw_label: QLabel,
        pitch_label: QLabel,
    ) -> None:
        widgets = [
            self._label(label),
            self._label("Yaw"),
            yaw_label,
            self._label("Pitch"),
            pitch_label,
        ]
        positions = ((row, 0), (row, 1), (row, 2), (row, 3), (row, 4))
        for widget, (row_index, column_index) in zip(widgets, positions):
            layout.addWidget(widget, row_index, column_index)
            self._debug_extended_widgets.append(widget)

    def _add_extended_debug_pose_row(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        yaw_label: QLabel,
        pitch_label: QLabel,
        roll_label: QLabel,
    ) -> None:
        widgets = [
            self._label(label),
            self._label("Yaw"),
            yaw_label,
            self._label("Pitch"),
            pitch_label,
            self._label("Roll"),
            roll_label,
        ]
        positions = ((row, 0), (row, 1), (row, 2), (row, 3), (row, 4), (row, 5), (row, 6))
        for widget, (row_index, column_index) in zip(widgets, positions):
            layout.addWidget(widget, row_index, column_index)
            self._debug_extended_widgets.append(widget)

    def _build_settings_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Categorias de Acordeão Industriais (Sem Emojis, Localizadas)
        self.sec_profile = self._localize(CollapsibleSection(""), "User Profile/Webcam", "setTitle")
        self.sec_head = self._localize(CollapsibleSection(""), "Head Tracking", "setTitle")
        self.sec_translation = self._localize(CollapsibleSection(""), "Translation Tracking Settings", "setTitle")
        self.sec_gaze = self._localize(CollapsibleSection(""), "Iris Settings", "setTitle")
        self.sec_extended = self._localize(CollapsibleSection(""), "Extended View Settings", "setTitle")
        self.sec_stabilization = self._localize(CollapsibleSection(""), "Sensitivity & Curves", "setTitle")
        self.sec_calibration = self._localize(CollapsibleSection(""), "Focus Settings", "setTitle")
        self.sec_output = self._localize(CollapsibleSection(""), "Track", "setTitle")

        # Preenchimento das sessões (adaptando retorno de layouts)
        self.sec_profile.addLayout(self._build_profile_content())
        self.sec_head.addLayout(self._build_head_content())
        self.sec_translation.addLayout(self._build_translation_content())
        self.sec_gaze.addLayout(self._build_gaze_content())
        self.sec_extended.addLayout(self._build_extended_content())
        self.sec_stabilization.addLayout(self._build_stabilization_content())
        self.sec_calibration.addLayout(self._build_calibration_content())
        self.sec_output.addLayout(self._build_output_content())

        layout.addWidget(self.sec_profile)
        layout.addWidget(self.sec_head)
        layout.addWidget(self.sec_translation)
        layout.addWidget(self.sec_gaze)
        layout.addWidget(self.sec_extended)
        layout.addWidget(self.sec_stabilization)
        layout.addWidget(self.sec_calibration)
        layout.addWidget(self.sec_output)
        layout.addStretch(1)
        
        # Crédito de desenvolvedor sutil no rodapé do scroll
        footer_credit = QLabel(f"Torvix Tracker - {self._tr('Developed by')} Neyvan Santos")
        footer_credit.setStyleSheet("color: #444; font-size: 10px; margin-top: 20px;")
        footer_credit.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer_credit)
        
        return container

    def _build_profile_content(self) -> QGridLayout:
        layout = QGridLayout()
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.textChanged.connect(self._on_profile_name_changed)
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        self.camera_settings_button = QPushButton("⚙")
        self.camera_settings_button.setObjectName("iconButton")
        self.camera_settings_button.setFixedWidth(38)
        self._set_localized_tooltip(self.camera_settings_button, "Open camera settings")
        self.camera_settings_button.clicked.connect(self._open_camera_settings)

        load_button = self._button("Load Profile")
        save_button = self._button("Save Profile")
        load_button.clicked.connect(self._load_profile)
        save_button.clicked.connect(self._save_profile)

        layout.addWidget(self._label_with_help("Profile name", HELP_KEYS["profile_name"]), 0, 0)
        layout.addWidget(self.profile_name_edit, 0, 1, 1, 2)
        layout.addWidget(self._label_with_help("Webcam", HELP_KEYS["camera_index"]), 1, 0)
        camera_row = QHBoxLayout()
        camera_row.setContentsMargins(0, 0, 0, 0)
        camera_row.setSpacing(6)
        camera_row.addWidget(self.camera_combo, 1)
        camera_row.addWidget(self.camera_settings_button)
        layout.addLayout(camera_row, 1, 1, 1, 2)
        layout.addWidget(load_button, 2, 1)
        layout.addWidget(save_button, 2, 2)
        self._populate_camera_combo()
        return layout

    def _build_head_content(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        mode_row = QHBoxLayout()
        mode_row.addWidget(self._label_with_help("Tracking context", HELP_KEYS["tracking_context"]))
        self.context_combo = QComboBox()
        self._populate_context_combo()
        self.context_combo.currentIndexChanged.connect(self._on_context_changed)
        mode_row.addWidget(self.context_combo, 1)
        layout.addLayout(mode_row)

        self._add_slider(layout, "input_deadzone", "Deadzone", 0.0, 45.0, 2, 0.1)
        self._add_slider(layout, "head_view_responsiveness", "Head view responsiveness", 0.0, 2.0, 2, 0.01)
        self._add_slider(layout, "head_view_smoothing", "Head view smoothing", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "head_yaw_sensitivity_cabin", "Head tracking yaw sensitivity (in cabin)", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "head_pitch_sensitivity_cabin", "Head tracking pitch sensitivity (in cabin)", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "head_yaw_sensitivity_walk", "Head tracking yaw sensitivity (in walk mode)", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "head_pitch_sensitivity_walk", "Head tracking pitch sensitivity (in walk mode)", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "head_roll_sensitivity", "Head tracking roll sensitivity", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "head_tracking_exponent", "Head tracking exponent", 0.10, 5.0, 2, 0.01)
        self._add_slider(layout, "head_tracking_inflection_point", "Head tracking inflection point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "head_tracking_start_point", "Head tracking start point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "head_tracking_end_point", "Head tracking end point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "max_head_angle", "Head angle scale", 1.0, 720.0, 1, 0.5)

        invert_row = QHBoxLayout()
        self._add_check(invert_row, "invert_yaw", "Invert yaw")
        self._add_check(invert_row, "invert_pitch", "Invert pitch")
        self._add_check(invert_row, "invert_roll", "Invert roll")
        invert_row.addStretch(1)
        layout.addLayout(invert_row)
        return layout

    def _build_translation_content(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self._add_slider(layout, "translation_deadzone", "Translation deadzone", 0.0, 10.0, 2, 0.01)
        self._add_slider(layout, "translation_smoothing", "Translation smoothing", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "translation_x_sensitivity", "Translation X sensitivity", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "translation_y_sensitivity", "Translation Y sensitivity", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "translation_z_sensitivity", "Translation Z sensitivity", 0.0, 5.0, 2, 0.01)
        invert_row = QHBoxLayout()
        self._add_check(invert_row, "invert_x", "Invert X")
        self._add_check(invert_row, "invert_y", "Invert Y")
        self._add_check(invert_row, "invert_z", "Invert Z")
        invert_row.addStretch(1)
        layout.addLayout(invert_row)
        return layout

    def _build_gaze_content(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self._add_check(layout, "enable_simulated_gaze", "Enable iris gaze")
        self._add_slider(layout, "gaze_view_responsiveness", "Gaze view responsiveness", 0.0, 2.0, 2, 0.01)
        self._add_slider(layout, "gaze_view_smoothing", "Gaze view smoothing", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "gaze_tracking_exponent", "Gaze tracking exponent", 0.10, 5.0, 2, 0.01)
        self._add_slider(layout, "gaze_tracking_inflection_point", "Gaze tracking inflection point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "gaze_tracking_start_point", "Gaze tracking start point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "gaze_tracking_end_point", "Gaze tracking end point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "max_gaze_angle", "Gaze angle scale", 0.0, 720.0, 1, 0.5)
        self._add_slider(layout, "gaze_strength", "Gaze strength", 0.0, 5.0, 2, 0.01)
        invert_row = QHBoxLayout()
        self._add_check(invert_row, "invert_gaze_yaw", "Invert gaze yaw")
        self._add_check(invert_row, "invert_gaze_pitch", "Invert gaze pitch")
        invert_row.addStretch(1)
        layout.addLayout(invert_row)
        return layout

    def _build_extended_content(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self._add_check(layout, "enable_extended_view", "Enable Extended View")
        self._add_check(layout, "debug_extended_view", "Debug Extended View")
        self._add_slider(layout, "extended_view_strength", "Extended View strength", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "extended_view_blend", "Extended View blend", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "extended_view_exponent", "Extended View exponent", 0.10, 5.0, 2, 0.01)
        self._add_slider(layout, "extended_view_inflection_point", "Extended View inflection point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "extended_view_start_point", "Extended View start point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "extended_view_end_point", "Extended View end point", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "extended_view_acceleration", "Extended View acceleration", 0.10, 5.0, 2, 0.01)
        self._add_slider(layout, "extended_view_max_angle", "Extended View angle scale", 0.0, 720.0, 1, 0.5)
        self._add_slider(layout, "extended_view_smoothing", "Extended View smoothing", 0.0, 1.0, 2, 0.01)
        return layout

    def _build_stabilization_content(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self._add_slider(layout, "output_smoothing", "Output smoothing", 0.0, 1.0, 2, 0.01)
        self._add_slider(layout, "output_micro_jitter", "Micro jitter threshold", 0.0, 5.0, 2, 0.01)
        self._add_slider(layout, "output_max_step", "Max output step per frame", 0.0, 30.0, 2, 0.1)
        return layout

    def _build_calibration_content(self) -> QGridLayout:
        layout = QGridLayout()
        self.hotkey_edit = HotkeyCaptureEdit()
        self.hotkey_edit.set_hotkey(self.config.recenter_hotkey)
        self.hotkey_edit.hotkeyChanged.connect(self._on_hotkey_changed)
        clear_hotkey_button = QPushButton("✕")
        clear_hotkey_button.setFixedWidth(28)
        clear_hotkey_button.setToolTip(self._tr("Clear hotkey"))
        clear_hotkey_button.clicked.connect(lambda: self._set_recenter_hotkey(""))
        self.calibration_status_label = QLabel(self._tr("No saved calibration"))
        self.recenter_button = self._button("Recenter")
        self.calibrate_center_button = self._button("Calibrate center")
        self.calibrate_left_button = self._button("Calibrate left")
        self.calibrate_right_button = self._button("Calibrate right")
        self.calibrate_up_button = self._button("Calibrate up")
        self.calibrate_down_button = self._button("Calibrate down")
        self.calibrate_gaze_center_button = self._button("Calibrate gaze center")
        self.calibrate_gaze_left_button = self._button("Calibrate gaze left")
        self.calibrate_gaze_right_button = self._button("Calibrate gaze right")
        self.calibrate_gaze_up_button = self._button("Calibrate gaze up")
        self.calibrate_gaze_down_button = self._button("Calibrate gaze down")
        self.recenter_button.clicked.connect(self._recenter)
        self.calibrate_center_button.clicked.connect(self._calibrate_center)
        self.calibrate_left_button.clicked.connect(lambda: self._calibrate_direction("left"))
        self.calibrate_right_button.clicked.connect(lambda: self._calibrate_direction("right"))
        self.calibrate_up_button.clicked.connect(lambda: self._calibrate_direction("up"))
        self.calibrate_down_button.clicked.connect(lambda: self._calibrate_direction("down"))
        self.calibrate_gaze_center_button.clicked.connect(self._calibrate_gaze_center)
        self.calibrate_gaze_left_button.clicked.connect(lambda: self._calibrate_gaze_direction("left"))
        self.calibrate_gaze_right_button.clicked.connect(lambda: self._calibrate_gaze_direction("right"))
        self.calibrate_gaze_up_button.clicked.connect(lambda: self._calibrate_gaze_direction("up"))
        self.calibrate_gaze_down_button.clicked.connect(lambda: self._calibrate_gaze_direction("down"))
        layout.addWidget(self._label_with_help("Recenter hotkey", HELP_KEYS["recenter_hotkey"]), 0, 0)
        hotkey_layout = QHBoxLayout()
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_layout.addWidget(self.hotkey_edit, 1)
        hotkey_layout.addWidget(clear_hotkey_button)
        layout.addLayout(hotkey_layout, 0, 1, 1, 2)
        layout.addWidget(self.recenter_button, 1, 0)
        layout.addWidget(self.calibrate_center_button, 1, 1)
        layout.addWidget(self.calibrate_left_button, 2, 0)
        layout.addWidget(self.calibrate_right_button, 2, 1)
        layout.addWidget(self.calibrate_up_button, 3, 0)
        layout.addWidget(self.calibrate_down_button, 3, 1)
        self.auto_calibrate_button = self._button("Auto Calibrar ⚡")
        self.auto_calibrate_button.setStyleSheet("background-color: #2D5A27; color: white; font-weight: bold; height: 32px;")
        self.auto_calibrate_button.clicked.connect(self._open_auto_calibrate)
        layout.addWidget(self.auto_calibrate_button, 4, 0, 1, 2)
        layout.addWidget(self._label("Iris calibration"), 5, 0, 1, 2)
        layout.addWidget(self.calibrate_gaze_center_button, 6, 0, 1, 2)
        layout.addWidget(self.calibrate_gaze_left_button, 7, 0)
        layout.addWidget(self.calibrate_gaze_right_button, 7, 1)
        layout.addWidget(self.calibrate_gaze_up_button, 8, 0)
        layout.addWidget(self.calibrate_gaze_down_button, 8, 1)
        layout.addWidget(self.calibration_status_label, 9, 0, 1, 3)
        return layout

    def _build_output_content(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(12)

        settings_layout = QGridLayout()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setHorizontalSpacing(16)
        settings_layout.setVerticalSpacing(8)
        settings_layout.setColumnStretch(0, 0)
        settings_layout.setColumnStretch(1, 1)

        self.output_mode_combo = QComboBox()
        self.output_mode_combo.setMinimumWidth(190)
        self.output_mode_combo.setMaximumWidth(260)
        self._populate_output_mode_combo()
        self.output_mode_combo.currentIndexChanged.connect(self._on_output_mode_changed)
        self.output_connection_label = QLabel(self._tr("Stopped"))
        self.output_connection_label.setObjectName("outputStatusValue")
        self.output_connection_label.setMinimumHeight(32)
        self.start_button = self._button("Start Tracking")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumWidth(220)
        self.stop_button = self._button("Stop Tracking")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setMinimumWidth(220)
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_tracking)
        self.stop_button.clicked.connect(self._stop_tracking)
        settings_layout.addWidget(self._label_with_help("Output mode", HELP_KEYS["output_mode"]), 0, 0)
        settings_layout.addWidget(self.output_mode_combo, 0, 1, alignment=Qt.AlignRight)
        settings_layout.addWidget(self._label_with_help("Connection status", HELP_KEYS["connection_status"]), 1, 0)
        settings_layout.addWidget(self.output_connection_label, 1, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 2, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addWidget(self.start_button, 1)
        btn_layout.addWidget(self.stop_button, 1)

        layout.addLayout(settings_layout)
        layout.addLayout(btn_layout)
        return layout

    def _load_output_mascot(self) -> None:
        # Tenta carregar do diretório de assets resolvido no __init__
        asset_path = Path(self.assets_path) / "octopus.png"
        
        pixmap = QPixmap(str(asset_path))
        if pixmap.isNull():
            # Backup: tenta no diretório atual de execução
            asset_path = Path.cwd() / "eye_drive_tracker" / "ui" / "assets" / "octopus.png"
            pixmap = QPixmap(str(asset_path))

        if pixmap.isNull():
            print(f"ERRO: Não foi possível carregar o mascote. Verifique se octopus.png existe em: {self.assets_path}")
            self.output_mascot_label.hide()
            self.output_mascot_pixmap = None
            return

        self.output_mascot_pixmap = pixmap
        self.output_mascot_label.show()
        self._refresh_output_mascot()

    def _set_output_mascot_pose(self, pose: PoseSample | None) -> None:
        self.output_mascot_pose = (
            PoseSample()
            if pose is None
            else PoseSample(pose.yaw, pose.pitch, pose.roll, pose.x, pose.y, pose.z)
        )
        self._refresh_output_mascot()

    def _refresh_output_mascot(self) -> None:
        import math
        from PySide6.QtGui import QTransform as _QTransform

        if self.output_mascot_pixmap is None:
            self.output_mascot_label.clear()
            return

        label_width = max(1, self.output_mascot_label.width())
        label_height = max(1, self.output_mascot_label.height())

        # Tamanho do mascote (quadrado para facilitar a projecao)
        target_size = max(140, min(200, min(label_width, label_height) - 40))
        scaled = self.output_mascot_pixmap.scaled(
            target_size,
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        sw = scaled.width()
        sh = scaled.height()

        # --- Normalizacao dos eixos ------------------------------------------
        # Usa angulos tipicos de rastreamento: yaw+-45 pitch+-30 roll+-30
        yaw_norm   = self._clamp(self.output_mascot_pose.yaw   / 45.0, -1.0, 1.0)
        pitch_norm = self._clamp(self.output_mascot_pose.pitch / 30.0, -1.0, 1.0)
        roll_norm  = self._clamp(self.output_mascot_pose.roll  / 30.0, -1.0, 1.0)

        # Profundidade baseada no tamanho relativo do rosto detectado:
        # face_area maior que a referencia = mais perto = z_norm positivo (mascote maior)
        # Isso e invariante a resolucao da camera e ao backend de rastreamento.
        ref = self._mascot_face_area_ref
        cur = self._mascot_face_area_current
        if ref > 0 and cur > 0:
            # ratio > 1 = mais perto; ratio < 1 = mais longe
            # log2: ratio=0.5 -> -1; ratio=1.0 -> 0; ratio=2.0 -> +1
            z_norm = self._clamp(math.log2(cur / ref), -1.0, 1.0)
        else:
            z_norm = 0.0

        # --- Parametros de perspectiva 3D falsa ------------------------------
        # Quando o yaw aumenta, a largura do mascote e comprimida (lado que se
        # afasta) e uma perspectiva horizontal e adicionada, dando a ilusao de
        # rotacao real -- igual ao robo do OpenTrack.
        SQUEEZE_YAW   = 0.55   # compressao maxima de largura para yaw=+-1
        SQUEEZE_PITCH = 0.30   # compressao maxima de altura para pitch=+-1
        PERSP_H       = 0.0028 # perspectiva horizontal (m13 do QTransform)
        PERSP_V       = 0.0020 # perspectiva vertical   (m23 do QTransform)

        h_scale = 1.0 - abs(yaw_norm)   * SQUEEZE_YAW
        v_scale = 1.0 - abs(pitch_norm) * SQUEEZE_PITCH
        h_persp = yaw_norm   * PERSP_H   # m13
        v_persp = pitch_norm * PERSP_V   # m23

        # Escala Z (aproximacao/afastamento)
        z_scale = 1.0 + z_norm * 0.22

        # Roll: rotacao 2D pura (inclina o mascote como a cabeca)
        roll_deg = -roll_norm * 22.0
        angle_rad = math.radians(roll_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # --- Monta QTransform com perspectiva --------------------------------
        # QTransform.setMatrix(m11, m12, m13,
        #                      m21, m22, m23,
        #                      m31, m32, m33)
        # m13/m23 = perspectiva projetiva (divide coordenadas pelo "W")
        t = _QTransform()
        t.setMatrix(
            cos_a * h_scale * z_scale,   sin_a * z_scale,   h_persp,
            -sin_a * z_scale,             cos_a * v_scale * z_scale,   v_persp,
            0.0,                          0.0,               1.0,
        )

        # --- Renderiza no canvas ---------------------------------------------
        canvas = QPixmap(label_width, label_height)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Translada para o centro do label e aplica a transformacao
        painter.translate(label_width / 2.0, label_height / 2.0)
        painter.setTransform(t, combine=True)
        painter.drawPixmap(-sw // 2, -sh // 2, scaled)
        painter.end()

        self.output_mascot_label.setPixmap(canvas)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _add_slider(
        self,
        layout: QVBoxLayout,
        field: str,
        label: str,
        minimum: float,
        maximum: float,
        decimals: int,
        step: float,
    ) -> None:
        control = FloatSlider(label, minimum, maximum, getattr(self.config, field), decimals, step)
        self._localized_widgets.append((control.label, label, "setText"))
        control.label.setText(self._tr(label))
        help_key = HELP_KEYS.get(field)
        if help_key:
            self._localized_widgets.append((control, help_key, "set_help_tooltip"))
            control.set_help_tooltip(self._tr(help_key))
        control.valueChanged.connect(lambda value, name=field: self._on_slider_changed(name, value))
        self.controls[field] = control
        layout.addWidget(control)

    def _add_check(self, layout, field: str, label: str) -> None:
        box = QCheckBox(label)
        self._localized_widgets.append((box, label, "setText"))
        box.setText(self._tr(label))
        box.toggled.connect(lambda checked, name=field: self._on_check_changed(name, checked))
        self.check_boxes[field] = box
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        row_layout.addWidget(box)
        help_key = HELP_KEYS.get(field)
        if help_key:
            row_layout.addWidget(self._help_button(help_key))
        row_layout.addStretch(1)
        layout.addWidget(row)

    def _apply_style(self) -> None:
        """Aplica o tema Neon Cyber Blue (Anti-Clichê)."""
        self.setStyleSheet("""
            #centralWidget {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #050505, stop:0.6 #050505, stop:1 #003038);
            }
            
            QMainWindow {
                background-color: #050505;
            }
            
            QWidget {
                background-color: transparent;
                color: #D1D1D1;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            
            /* Acordeões Industriais */
            QPushButton#sectionHeader {
                background-color: #121212;
                border: 1px solid #222222;
                border-left: 3px solid #00F2FF;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 11px;
                text-align: left;
                padding: 10px 15px;
                margin-top: 8px;
            }
            QPushButton#sectionHeader:hover {
                background-color: #1A1A1A;
                border-left-color: #00F2FF;
            }
            
            QLabel#languageSelectorLabel {
                color: #00F2FF;
                font-weight: 700;
                text-transform: uppercase;
                font-size: 10px;
                letter-spacing: 1px;
            }
            QPushButton#sectionHeader:checked {
                background-color: #1A1A1A;
                border-left-color: #00F2FF;
                border-bottom: none;
            }
            
            QGroupBox#sectionContent {
                background-color: #0D0D0D;
                border: 1px solid #222222;
                border-top: none;
                border-radius: 8px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                margin-bottom: 4px;
                padding: 15px;
            }

            QGroupBox#telemetryPanel {
                background-color: #0D0D0D;
                border: 1px solid #222222;
                border-radius: 12px;
                padding: 10px;
            }

            /* Sliders Minimalistas */
            QSlider::groove:horizontal {
                height: 2px;
                background: #333333;
            }
            QSlider::sub-page:horizontal {
                background: #00F2FF;
            }
            QSlider::handle:horizontal {
                background: #00F2FF;
                border: 1px solid #00F2FF;
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 7px; /* Circular handle */
            }
            QSlider::handle:horizontal:hover {
                background: #FFFFFF;
            }

            /* Inputs Engineering Style */
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #121212;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 6px;
                color: #FFFFFF;
                font-family: 'Arial', sans-serif;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border-color: #00F2FF;
            }
            
            /* Botões de Ação de Alta Visibilidade */
            QPushButton#primaryButton {
                background-color: #00F2FF;
                color: #000000;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                min-height: 40px;
                padding: 5px 25px;
            }
            QPushButton#primaryButton:hover {
                background-color: #80FFFF;
            }
            QPushButton#primaryButton:pressed {
                background-color: #00B8CC;
            }
            QPushButton#secondaryButton {
                background-color: #121212;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 8px;
                font-family: 'Arial', sans-serif;
                font-weight: 600;
                min-height: 40px;
                padding: 5px 22px;
            }
            QPushButton#secondaryButton:hover {
                border-color: #00F2FF;
                color: #00F2FF;
                background-color: #1A1A1A;
            }
            QPushButton#secondaryButton:disabled {
                color: #777777;
                border-color: #242424;
                background-color: #0D0D0D;
            }

            QLabel#outputStatusValue {
                background-color: #121212;
                border: 1px solid #333333;
                border-left: 3px solid #00F2FF;
                border-radius: 6px;
                color: #FFFFFF;
                font-family: 'Arial', sans-serif;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 10px;
            }

            QDialog#gameFunctionsDialog {
                background-color: #050505;
            }
            QLabel#dialogTitle {
                color: #FFFFFF;
                font-family: 'Arial', sans-serif;
                font-size: 18px;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QLabel#dialogSubtitle {
                color: #A8A8A8;
                font-family: 'Arial', sans-serif;
                font-size: 11px;
                line-height: 1.4;
            }
            QTextBrowser#gameFunctionsText {
                background-color: #0D0D0D;
                border: 1px solid #222222;
                border-left: 3px solid #00F2FF;
                border-radius: 8px;
                color: #D1D1D1;
                font-family: 'Arial', sans-serif;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton#dialogCloseButton {
                background-color: #00F2FF;
                color: #000000;
                border: none;
                border-radius: 6px;
                font-family: 'Arial', sans-serif;
                font-weight: 700;
                min-width: 110px;
                min-height: 30px;
                padding: 4px 16px;
            }
            QPushButton#dialogCloseButton:hover {
                background-color: #80FFFF;
            }
            
            /* Menus e Barra de Menu */
            QMenuBar {
                background-color: #080808;
                border-bottom: 1px solid #222222;
                padding: 2px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 4px 10px;
                margin: 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #1A1A1A;
                color: #00F2FF;
            }
            
            QMenu {
                background-color: #121212;
                border: 1px solid #222222;
                border-radius: 8px;
                padding: 1px; /* Minimalista: 1px */
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QMenu::item:selected {
                background-color: #00F2FF;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background: #222222;
                margin: 5px 10px;
            }
            QLabel#videoPreview {
                background: #000000;
                border: 1px solid #222222;
                border-radius: 12px;
            }

            QLabel#mainAppTitle {
                color: #FFFFFF;
                font-family: 'Arial', sans-serif;
                font-size: 18px;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 2px;
            }

            /* Scrollbar Industrial */
            QScrollBar:vertical {
                border: none;
                background: #080808;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #222222;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00F2FF;
            }

            QToolTip {
                background: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid #00F2FF;
                border-radius: 0px;
                padding: 10px;
            }

            /* Seletor de Idioma Industrial */
            QPushButton#languageOption {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 6px;
                color: #D1D1D1;
                font-weight: 500;
                font-size: 11px;
                padding: 4px 12px;
                margin-left: 4px;
                text-transform: uppercase;
            }
            QPushButton#languageOption:hover {
                background-color: #1A1A1A;
                border-color: #555555;
            }
            QPushButton#languageOption:checked {
                background-color: #00F2FF;
                color: #000000;
                border-color: #00F2FF;
                font-weight: 700;
            }
        """)

    def _start_tracking(self) -> None:
        if self.camera.is_open:
            return
        if not self.camera.open(
            self.config.camera_index,
            width=self.config.camera_width or None,
            height=self.config.camera_height or None,
            fps=self.config.camera_fps or None,
        ):
            QMessageBox.warning(
                self,
                __app_name__,
                f"{self._tr('Could not open camera index')} {self.config.camera_index}.",
            )
            return

        camera_settings = self.camera.actual_settings()
        self._configure_runtime_timing(camera_settings)
        self.pose_filter.reset()
        self.last_raw_pose = None
        self.last_pipeline = PipelineOutput(PoseSample(), PoseSample(), PoseSample(), PoseSample())
        self.last_tracking_result = TrackingResult(detected=False)
        self._mascot_face_area_ref = 0.0
        self._mascot_face_area_current = 0.0
        self._set_output_mascot_pose(None)
        self._reset_preview_metrics()
        self.tracking_worker.start()
        self.output_manager.set_mode(self.config.output_mode)
        self.output_manager.start()
        self.output_timer.start()
        self.timer.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText(self._tr("Tracking"))
        self._update_camera_mode_label(camera_settings)
        self._update_output_status()

    def _stop_tracking(self) -> None:
        self.timer.stop()
        self.timer.setInterval(5)
        self.output_timer.stop()
        self.tracking_worker.stop()
        self.camera.release()
        self.output_manager.stop()
        self.last_raw_pose = None
        self.last_pipeline = PipelineOutput(PoseSample(), PoseSample(), PoseSample(), PoseSample())
        self.last_tracking_result = TrackingResult(detected=False)
        if hasattr(self, "start_button"):
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        if hasattr(self, "status_label"):
            self.status_label.setText(self._tr("Stopped"))
        if hasattr(self, "camera_mode_label"):
            self.camera_mode_label.setText("--")
        if hasattr(self, "preview_fps_label"):
            self.preview_fps_label.setText("--")
        if hasattr(self, "video_label"):
            self.video_label.clear()
            self.video_label.setStyleSheet("background-color: #050505; border: 1px solid #1A1A1A;")
            self.video_label.setText(self._tr("SYSTEM_OFFLINE"))
        self._set_output_mascot_pose(None)
        self._update_output_status()

    def _recenter(self) -> None:
        self.pose_filter.recenter(self.last_raw_pose)
        self.last_pipeline = PipelineOutput(PoseSample(), PoseSample(), PoseSample(), PoseSample())
        self._update_pipeline_labels(self.last_pipeline)
        self._set_output_mascot_pose(PoseSample())
        self.calibration_status_label.setText(self._tr("Runtime center updated"))

    def _calibrate_center(self) -> None:
        if self.last_raw_pose is None:
            self._warn_no_pose()
            return
        center_pose = self.pose_filter.estimate_stable_center(self.last_raw_pose)
        self.config.calibration_center_set = True
        self.config.calibration_center_yaw = center_pose.yaw
        self.config.calibration_center_pitch = center_pose.pitch
        self.config.calibration_center_roll = center_pose.roll
        self.config.calibration_center_x = center_pose.x
        self.config.calibration_center_y = center_pose.y
        self.config.calibration_center_z = center_pose.z
        self.pose_filter.recenter(center_pose)
        self.calibration_status_label.setText(self._tr("Center calibration saved"))

    def _calibrate_direction(self, direction: str) -> None:
        if self.last_raw_pose is None:
            self._warn_no_pose()
            return
        center = self.pose_filter.center
        delta_yaw = self.last_raw_pose.yaw - center.yaw
        delta_pitch = self.last_raw_pose.pitch - center.pitch

        if direction == "left":
            self.config.calibration_left_set = True
            self.config.calibration_left_yaw = delta_yaw
            label = f"{self._tr('Calibrate left')} ({delta_yaw:.2f})"
        elif direction == "right":
            self.config.calibration_right_set = True
            self.config.calibration_right_yaw = delta_yaw
            label = f"{self._tr('Calibrate right')} ({delta_yaw:.2f})"
        elif direction == "up":
            self.config.calibration_up_set = True
            self.config.calibration_up_pitch = delta_pitch
            label = f"{self._tr('Calibrate up')} ({delta_pitch:.2f})"
        else:
            self.config.calibration_down_set = True
            self.config.calibration_down_pitch = delta_pitch
            label = f"{self._tr('Calibrate down')} ({delta_pitch:.2f})"
        self.calibration_status_label.setText(label)

    def _current_gaze_for_calibration(self) -> GazeSample | None:
        gaze = self.last_tracking_result.gaze
        if not self.last_tracking_result.detected or gaze.source != "iris" or gaze.confidence < 0.24:
            return None
        return gaze

    def _calibrate_gaze_center(self) -> None:
        gaze = self._current_gaze_for_calibration()
        if gaze is None:
            self._warn_no_gaze()
            return
        self.config.enable_simulated_gaze = True
        self.config.gaze_calibration_center_set = True
        self.config.gaze_calibration_center_yaw = gaze.yaw
        self.config.gaze_calibration_center_pitch = gaze.pitch
        self.pose_filter.previous_gaze = PoseSample()
        self._sync_controls_from_config()
        self.calibration_status_label.setText(
            f"{self._tr('Calibrate gaze center')} ({gaze.yaw:.2f}, {gaze.pitch:.2f})"
        )

    def _calibrate_gaze_direction(self, direction: str) -> None:
        gaze = self._current_gaze_for_calibration()
        if gaze is None:
            self._warn_no_gaze()
            return

        center_yaw = self.config.gaze_calibration_center_yaw if self.config.gaze_calibration_center_set else 0.0
        center_pitch = self.config.gaze_calibration_center_pitch if self.config.gaze_calibration_center_set else 0.0
        delta_yaw = gaze.yaw - center_yaw
        delta_pitch = gaze.pitch - center_pitch

        if direction == "left":
            self.config.gaze_calibration_left_set = True
            self.config.gaze_calibration_left_yaw = delta_yaw
            label = f"{self._tr('Calibrate gaze left')} ({delta_yaw:.2f})"
        elif direction == "right":
            self.config.gaze_calibration_right_set = True
            self.config.gaze_calibration_right_yaw = delta_yaw
            label = f"{self._tr('Calibrate gaze right')} ({delta_yaw:.2f})"
        elif direction == "up":
            self.config.gaze_calibration_up_set = True
            self.config.gaze_calibration_up_pitch = delta_pitch
            label = f"{self._tr('Calibrate gaze up')} ({delta_pitch:.2f})"
        else:
            self.config.gaze_calibration_down_set = True
            self.config.gaze_calibration_down_pitch = delta_pitch
            label = f"{self._tr('Calibrate gaze down')} ({delta_pitch:.2f})"

        self.config.enable_simulated_gaze = True
        self.pose_filter.previous_gaze = PoseSample()
        self._sync_controls_from_config()
        self.calibration_status_label.setText(label)

    def _warn_no_pose(self) -> None:
        QMessageBox.information(
            self,
            __app_name__,
            self._tr("Start tracking and keep your face detected before calibrating."),
        )

    def _warn_no_gaze(self) -> None:
        QMessageBox.information(
            self,
            __app_name__,
            self._tr("Keep both eyes open and visible before calibrating iris gaze."),
        )

    def _on_frame(self) -> None:
        ok, frame, frame_id = self.camera.read_with_id()
        if not ok or frame is None:
            return
        has_new_frame = frame_id != self._last_camera_frame_id
        if has_new_frame:
            self._last_camera_frame_id = frame_id

        async_result = self.tracking_worker.take_result()
        if async_result is not None:
            result = self._scale_tracking_result(async_result.result, async_result.scale_x, async_result.scale_y)
            self.last_tracking_result = result
            self._handle_tracking_result(result)
        else:
            result = self.last_tracking_result

        if has_new_frame and self.tracking_worker.wants_frame():
            self.tracking_worker.submit(frame, self.tracking_frame_max_width)

        self.backend_label.setText(result.method or self.tracking_worker.backend_name)
        now = time.monotonic()
        
        if has_new_frame:
            interval = 1.0 / max(self.preview_max_fps, 1.0)
            # Use interval * 0.5 as tolerance to handle camera timing jitter,
            # ensuring we don't accidentally drop valid frames if they arrive slightly early.
            if now - self._last_preview_presented_at >= (interval * 0.5):
                self._last_preview_presented_at = now
                preview_frame, preview_scale_x, preview_scale_y = self._resize_frame_for_preview(frame)
                preview_result = self._scale_tracking_result(result, preview_scale_x, preview_scale_y)
                self._draw_overlay(preview_frame, preview_result)
                self._show_frame(preview_frame)
                self._update_preview_fps()

    def _handle_tracking_result(self, result: TrackingResult) -> None:
        if result.detected:
            self.last_raw_pose = result.pose

            # Alimenta o assistente de calibracao se estiver aberto
            if hasattr(self, "_wizard_instance") and self._wizard_instance and self._wizard_instance.isVisible():
                self._wizard_instance.update_pose(result.pose)

            self.last_pipeline = self.pose_filter.process(result.pose, self.config, result.gaze)
            centered_raw_pose = _center_pose_to_reference(result.pose, self.pose_filter.center)
            self.output_manager.push_target_pose(self.last_pipeline.final, self.last_pipeline.final)
            self.status_label.setText(self._tr("Face detected"))
            self._update_raw_labels(centered_raw_pose)
            self._update_pipeline_labels(self.last_pipeline)

            # Estima profundidade pelo tamanho do face_box (invariante a resolucao)
            if result.face_box:
                _x, _y, w, h = result.face_box
                area = float(w * h)
                if area > 0:
                    # Suavizacao EMA para evitar jitter
                    if self._mascot_face_area_current <= 0:
                        self._mascot_face_area_current = area
                    else:
                        self._mascot_face_area_current = (
                            self._mascot_face_area_current * 0.85 + area * 0.15
                        )
                    # Define referencia na primeira deteccao estavel
                    if self._mascot_face_area_ref <= 0:
                        self._mascot_face_area_ref = self._mascot_face_area_current

            self._set_output_mascot_pose(self.last_pipeline.final)
            self._update_output_status()
        else:
            self.status_label.setText(self._tr("No face"))
            self._update_output_status()

    def _on_output_tick(self) -> None:
        if not self.output_manager.running:
            return
        if not self.camera.is_open:
            return
        previous_status = self.output_manager.status
        self.output_manager.tick()
        if self.output_manager.status != previous_status:
            self._update_output_status()

    def _tracking_frame_for_detection(self, frame):
        height, width = frame.shape[:2]
        if width <= self.tracking_frame_max_width:
            return frame.copy(), 1.0, 1.0

        scale = self.tracking_frame_max_width / max(width, 1)
        target_width = self.tracking_frame_max_width
        target_height = max(1, int(round(height * scale)))
        resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
        return resized, width / target_width, height / target_height

    def _scale_tracking_result(self, result: TrackingResult, scale_x: float, scale_y: float) -> TrackingResult:
        if scale_x == 1.0 and scale_y == 1.0:
            return result

        def scale_point(point: tuple[int, int]) -> tuple[int, int]:
            return (int(round(point[0] * scale_x)), int(round(point[1] * scale_y)))

        def scale_box(box: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
            if box is None:
                return None
            x, y, w, h = box
            return (
                int(round(x * scale_x)),
                int(round(y * scale_y)),
                int(round(w * scale_x)),
                int(round(h * scale_y)),
            )

        def scale_optional_point(point: tuple[int, int] | None) -> tuple[int, int] | None:
            if point is None:
                return None
            return scale_point(point)

        eye_boxes = []
        for box in result.eye_boxes:
            scaled = scale_box(box)
            if scaled is not None:
                eye_boxes.append(scaled)

        gaze = GazeSample(
            yaw=result.gaze.yaw,
            pitch=result.gaze.pitch,
            confidence=result.gaze.confidence,
            source=result.gaze.source,
            normalized_x=result.gaze.normalized_x,
            normalized_y=result.gaze.normalized_y,
            eye_span=result.gaze.eye_span,
            face_size_normalized=result.gaze.face_size_normalized,
            distance_scale=result.gaze.distance_scale,
            valid_eye_count=result.gaze.valid_eye_count,
            left_confidence=result.gaze.left_confidence,
            right_confidence=result.gaze.right_confidence,
            left_iris=scale_optional_point(result.gaze.left_iris),
            right_iris=scale_optional_point(result.gaze.right_iris),
            left_eye_center=scale_optional_point(result.gaze.left_eye_center),
            right_eye_center=scale_optional_point(result.gaze.right_eye_center),
            left_ratio=result.gaze.left_ratio,
            right_ratio=result.gaze.right_ratio,
        )

        return TrackingResult(
            detected=result.detected,
            pose=result.pose,
            method=result.method,
            face_box=scale_box(result.face_box),
            gaze=gaze,
            frame_size=(
                int(round(result.frame_size[0] * scale_x)),
                int(round(result.frame_size[1] * scale_y)),
            ) if result.frame_size != (0, 0) else (0, 0),
            face_center_normalized=result.face_center_normalized,
            face_size_normalized=result.face_size_normalized,
            user_distance=result.user_distance,
            tracking_fps=result.tracking_fps,
            processing_ms=result.processing_ms,
            dropped_frames=result.dropped_frames,
            left_eye_points=[scale_point(point) for point in result.left_eye_points],
            right_eye_points=[scale_point(point) for point in result.right_eye_points],
            eye_boxes=eye_boxes,
        )

    def _draw_overlay(self, frame, result: TrackingResult) -> None:
        """Desenha o HUD Técnico Industrial v3.0."""
        height, width = frame.shape[:2]
        
        # Cores Industriais (BGR)
        color_amber = (0, 184, 255) 
        color_white = (220, 220, 220)
        color_green = (80, 220, 120)
        color_red = (0, 0, 200)
        
        # 1. Cantoneiras Minimalistas (Corner Brackets)
        m = 15 # margem
        length = 25 # comprimento
        t = 1  # espessura
        cv2.line(frame, (m, m), (m + length, m), color_amber, t)
        cv2.line(frame, (m, m), (m, m + length), color_amber, t)
        cv2.line(frame, (width - m, m), (width - m - length, m), color_amber, t)
        cv2.line(frame, (width - m, m), (width - m, m + length), color_amber, t)
        cv2.line(frame, (m, height - m), (m + length, height - m), color_amber, t)
        cv2.line(frame, (m, height - m), (m, height - m - length), color_amber, t)
        cv2.line(frame, (width - m, height - m), (width - m - length, height - m), color_amber, t)
        cv2.line(frame, (width - m, height - m), (width - m, height - m - length), color_amber, t)

        if not result.detected:
            # Texto de Status sóbrio
            cv2.putText(frame, "> SEARCHING_FOR_PILOT...", (m + 20, height // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_red, 1)
            return

        # 2. Caixa do Rosto (Technical Reticle)
        if result.face_box:
            x, y, w, h = result.face_box
            # Desenha apenas cantos para o rosto, não o box inteiro
            cl = 10
            cv2.line(frame, (x, y), (x + cl, y), color_amber, 1)
            cv2.line(frame, (x, y), (x, y + cl), color_amber, 1)
            cv2.line(frame, (x + w, y), (x + w - cl, y), color_amber, 1)
            cv2.line(frame, (x + w, y), (x + w, y + cl), color_amber, 1)
            cv2.line(frame, (x, y + h), (x + cl, y + h), color_amber, 1)
            cv2.line(frame, (x, y + h), (x, y + h - cl), color_amber, 1)
            cv2.line(frame, (x + w, y + h), (x + w - cl, y + h), color_amber, 1)
            cv2.line(frame, (x + w, y + h), (x + w, y + h - cl), color_amber, 1)
            
            cv2.putText(frame, "STATUS: TRACKING_LOCK", (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color_amber, 1)

        # 3. Crosshairs nos Olhos
        def draw_crosshair(p, size=4):
            cv2.line(frame, (p[0] - size, p[1]), (p[0] + size, p[1]), color_white, 1)
            cv2.line(frame, (p[0], p[1] - size), (p[0], p[1] + size), color_white, 1)

        # Íris (primeiro ponto na lista se refine_landmarks estiver ON)
        def draw_eye_outline(points: list[tuple[int, int]]) -> None:
            for point in points:
                cv2.circle(frame, point, 1, color_white, -1)

        def draw_iris(iris: tuple[int, int] | None, center: tuple[int, int] | None) -> None:
            if iris is None:
                return
            cv2.circle(frame, iris, 5, color_green, 1)
            draw_crosshair(iris, size=3)
            if center is not None:
                cv2.line(frame, center, iris, color_green, 1)

        draw_eye_outline(result.left_eye_points)
        draw_eye_outline(result.right_eye_points)
        draw_iris(result.gaze.left_iris, result.gaze.left_eye_center)
        draw_iris(result.gaze.right_iris, result.gaze.right_eye_center)

        iris_points = [point for point in (result.gaze.left_iris, result.gaze.right_iris) if point is not None]
        if iris_points:
            origin = (
                int(round(sum(point[0] for point in iris_points) / len(iris_points))),
                int(round(sum(point[1] for point in iris_points) / len(iris_points))),
            )
            length = 28
            target = (
                int(round(origin[0] + result.gaze.yaw * length)),
                int(round(origin[1] - result.gaze.pitch * length)),
            )
            cv2.arrowedLine(frame, origin, target, color_green, 1, tipLength=0.25)

        # 4. Barra de Telemetria (Flight Data Style)
        final = self.last_pipeline.final
        text = f"YAW:{final.yaw: >6.1f} | PIT:{final.pitch: >6.1f} | ROL:{final.roll: >6.1f}"
        
        # Fundo semi-transparente escuro para a barra
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, 30), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        cv2.putText(frame, text, (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_white, 1)
        
        # Indicador de FPS na barra superior (lado direito)
        tracking_fps = result.tracking_fps if result.tracking_fps > 0.0 else 0.0
        fps_text = f"TRACK:{tracking_fps:.1f} PREVIEW:{self._preview_fps:.1f}"
        cv2.putText(frame, fps_text, (max(20, width - 205), 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color_amber, 1)

        gaze_text = f"IRIS:{result.gaze.confidence:.2f} {self.last_pipeline.gaze_debug.source}"
        cv2.putText(frame, gaze_text, (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color_green, 1)

    def _show_frame(self, frame_bgr) -> None:
        height, width, channels = frame_bgr.shape
        bytes_per_line = channels * width
        image = QImage(frame_bgr.data, width, height, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(image)
        self._preview_frame_ref = frame_bgr
        self.video_label.setPixmap(pixmap)

    def _resize_frame_for_preview(self, frame_bgr):
        height, width = frame_bgr.shape[:2]
        target = self.video_label.contentsRect().size()
        target_width = max(1, target.width())
        target_height = max(1, target.height())
        scale = min(target_width / max(width, 1), target_height / max(height, 1))
        if scale <= 0:
            return frame_bgr, 1.0, 1.0

        next_width = max(1, int(round(width * scale)))
        next_height = max(1, int(round(height * scale)))
        if next_width == width and next_height == height:
            return frame_bgr, 1.0, 1.0

        resized = cv2.resize(frame_bgr, (next_width, next_height), interpolation=cv2.INTER_LINEAR)
        return resized, next_width / max(width, 1), next_height / max(height, 1)

    def _reset_preview_metrics(self) -> None:
        self._preview_frame_count = 0
        self._preview_fps = 0.0
        self._preview_fps_started_at = time.monotonic()
        self._last_preview_presented_at = 0.0
        self._last_camera_frame_id = 0
        if hasattr(self, "preview_fps_label"):
            self.preview_fps_label.setText("--")

    def _update_preview_fps(self) -> None:
        self._preview_frame_count += 1
        now = time.monotonic()
        elapsed = now - self._preview_fps_started_at
        if elapsed >= 1.0:
            current_fps = self._preview_frame_count / elapsed
            if self._preview_fps > 0:
                self._preview_fps = (self._preview_fps * 0.5) + (current_fps * 0.5)
            else:
                self._preview_fps = current_fps
                
            self._preview_frame_count = 0
            self._preview_fps_started_at = now
            # Prevent showing 59.9 as 59 if it's very close to 60
            display_fps = round(self._preview_fps) if abs(self._preview_fps - round(self._preview_fps)) < 0.2 else self._preview_fps
            self.preview_fps_label.setText(f"{display_fps:.1f}")

    def _update_camera_mode_label(self, settings=None) -> None:
        settings = settings or self.camera.actual_settings()
        if settings.width <= 0 or settings.height <= 0:
            self.camera_mode_label.setText("--")
            return
        self.camera_mode_label.setText(settings.label)

    def _configure_runtime_timing(self, settings) -> None:
        camera_fps = float(settings.fps or self.config.camera_fps or 60.0)
        self.preview_max_fps = max(30.0, min(camera_fps, 60.0))
        if camera_fps >= 50.0:
            self.tracking_frame_max_width = 384 if settings.width >= 1600 else 448
        else:
            self.tracking_frame_max_width = 512 if settings.width >= 1600 else 640
        self.timer.setInterval(2 if self.preview_max_fps >= 50.0 else 6)

    def _update_raw_labels(self, pose: PoseSample) -> None:
        self.raw_yaw_label.setText(f"{pose.yaw:.2f}")
        self.raw_pitch_label.setText(f"{pose.pitch:.2f}")
        self.raw_roll_label.setText(f"{pose.roll:.2f}")

    def _update_pipeline_labels(self, pipeline: PipelineOutput) -> None:
        self._set_pose_labels(pipeline.head, self.head_yaw_label, self.head_pitch_label, self.head_roll_label)
        self._set_pose_labels(pipeline.gaze, self.gaze_yaw_label, self.gaze_pitch_label, None)
        self.gaze_confidence_label.setText(f"{pipeline.gaze_debug.confidence:.2f}")
        self.gaze_source_label.setText(pipeline.gaze_debug.source)
        self._set_pose_labels(pipeline.extended, self.extended_yaw_label, self.extended_pitch_label, None)
        self._set_pose_labels(pipeline.final, self.final_yaw_label, self.final_pitch_label, self.final_roll_label)
        self._update_extended_debug_labels(pipeline)

    def _set_pose_labels(
        self,
        pose: PoseSample,
        yaw_label: QLabel,
        pitch_label: QLabel,
        roll_label: QLabel | None,
    ) -> None:
        yaw_label.setText(f"{pose.yaw:.2f}")
        pitch_label.setText(f"{pose.pitch:.2f}")
        if roll_label is not None:
            roll_label.setText(f"{pose.roll:.2f}")

    def _update_extended_debug_labels(self, pipeline: PipelineOutput) -> None:
        debug = pipeline.extended_debug
        self.debug_extended_normalized_yaw_label.setText(f"{debug.yaw.normalized_input:.3f}")
        self.debug_extended_normalized_pitch_label.setText(f"{debug.pitch.normalized_input:.3f}")
        self.debug_extended_curve_yaw_label.setText(f"{debug.yaw.curve_value:.3f}")
        self.debug_extended_curve_pitch_label.setText(f"{debug.pitch.curve_value:.3f}")
        self.debug_extended_before_yaw_label.setText(f"{debug.yaw.before_smoothing:.2f}")
        self.debug_extended_before_pitch_label.setText(f"{debug.pitch.before_smoothing:.2f}")
        self.debug_extended_after_yaw_label.setText(f"{debug.yaw.after_smoothing:.2f}")
        self.debug_extended_after_pitch_label.setText(f"{debug.pitch.after_smoothing:.2f}")
        self.debug_extended_final_yaw_label.setText(f"{debug.final.yaw:.2f}")
        self.debug_extended_final_pitch_label.setText(f"{debug.final.pitch:.2f}")
        self.debug_extended_final_roll_label.setText(f"{debug.final.roll:.2f}")

    def _update_debug_extended_visibility(self) -> None:
        visible = bool(getattr(self.config, "debug_extended_view", False))
        for widget in self._debug_extended_widgets:
            widget.setVisible(visible)

    def _update_output_status(self) -> None:
        status = self.output_manager.status
        if hasattr(self, "output_connection_label"):
            self.output_connection_label.setText(self._tr(status))
        if hasattr(self, "connection_status_label"):
            self.connection_status_label.setText(self._tr(status))

    def _populate_context_combo(self) -> None:
        current = self.context_combo.currentData() if self.context_combo.count() else self.config.tracking_context
        self.context_combo.blockSignals(True)
        self.context_combo.clear()
        self.context_combo.addItem(self._tr("In cabin"), "cabin")
        self.context_combo.addItem(self._tr("Walk mode"), "walk")
        self._set_combo_by_data(self.context_combo, current or self.config.tracking_context)
        self.context_combo.blockSignals(False)

    def _populate_output_mode_combo(self) -> None:
        current = self.output_mode_combo.currentData() if self.output_mode_combo.count() else self.config.output_mode
        self.output_mode_combo.blockSignals(True)
        self.output_mode_combo.clear()
        for mode, label in OUTPUT_MODE_LABELS.items():
            self.output_mode_combo.addItem(self._tr(label), mode.value)
        self._set_combo_by_data(self.output_mode_combo, current or self.config.output_mode)
        self.output_mode_combo.blockSignals(False)

    def _populate_camera_combo(self) -> None:
        current = self.config.camera_index
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        known_indexes = {device.index for device in self.camera_devices}
        for device in self.camera_devices:
            self.camera_combo.addItem(device.name, device.index)
        if current not in known_indexes:
            webcam_label = f"{current} - {self._tr('Webcam')}"
            self.camera_combo.addItem(webcam_label, current)
        self._set_combo_by_data(self.camera_combo, current)
        self.camera_combo.blockSignals(False)

    def _on_language_changed(self, language: str) -> None:
        if language not in LANGUAGES:
            return
        self.config.language = language
        self._apply_language()

    def _apply_language(self) -> None:
        if self.config.language not in LANGUAGES:
            self.config.language = "ENG"

        for language, button in self._language_buttons.items():
            button.blockSignals(True)
            button.setChecked(language == self.config.language)
            button.blockSignals(False)

        # Atualiza os menus principais
        if hasattr(self, "file_menu"):
            self.file_menu.setTitle(self._tr("File"))
        if hasattr(self, "help_menu"):
            self.help_menu.setTitle(self._tr("Help"))
        if hasattr(self, "about_menu"):
            self.about_menu.setTitle(self._tr("About"))
        for key, action in self._menu_actions.items():
            action.setText(self._tr(key))
        for widget, key, setter in self._localized_widgets:
            getattr(widget, setter)(self._tr(key))
        if hasattr(self, "context_combo"):
            self._populate_context_combo()
        if hasattr(self, "output_mode_combo"):
            self._populate_output_mode_combo()
        if hasattr(self, "camera_combo"):
            self._populate_camera_combo()
        if hasattr(self, "calibration_status_label"):
            self._update_calibration_status_from_config()
        self._update_output_status()

    def _on_slider_changed(self, name: str, value: float) -> None:
        if self._syncing_controls:
            return
        setattr(self.config, name, value)

    def _on_check_changed(self, name: str, checked: bool) -> None:
        if self._syncing_controls:
            return
        setattr(self.config, name, bool(checked))
        if name == "debug_extended_view":
            self._update_debug_extended_visibility()

    def _on_context_changed(self, _index: int = -1) -> None:
        if self._syncing_controls:
            return
        self.config.tracking_context = self.context_combo.currentData()

    def _on_output_mode_changed(self, _index: int = -1) -> None:
        if self._syncing_controls:
            return
        self.config.output_mode = self.output_mode_combo.currentData()
        self.output_manager.set_mode(self.config.output_mode)
        self._update_output_status()

    def _on_profile_name_changed(self, value: str) -> None:
        if self._syncing_controls:
            return
        self.config.profile_name = value.strip() or "Manual Profile"

    def _on_camera_changed(self, _index: int = -1) -> None:
        if self._syncing_controls:
            return
        value = self.camera_combo.currentData()
        if value is None:
            return
        self.config.camera_index = int(value)

    def _open_camera_settings(self) -> None:
        was_running = self.camera.is_open
        if was_running:
            self._stop_tracking()

        dialog = CameraSettingsDialog(self.config, self)
        if dialog.exec():
            self.config.camera_width = dialog.selected_width
            self.config.camera_height = dialog.selected_height
            self.config.camera_fps = dialog.selected_fps

        if was_running:
            self._start_tracking()

    def _on_hotkey_changed(self, hotkey_spec: str) -> None:
        if self._syncing_controls:
            return
        self._set_recenter_hotkey(hotkey_spec)

    def _set_recenter_hotkey(self, hotkey_spec: str) -> None:
        self.config.recenter_hotkey = (hotkey_spec or "").strip()
        if hasattr(self, "hotkey_edit"):
            self.hotkey_edit.set_hotkey(self.config.recenter_hotkey)
        self._update_recenter_shortcut()

    def _update_recenter_shortcut(self) -> None:
        if self.recenter_shortcut is not None:
            self.recenter_shortcut.setEnabled(False)
            self.recenter_shortcut.deleteLater()
            self.recenter_shortcut = None

        hotkey = self.config.recenter_hotkey
        self.recenter_hotkey_monitor.set_hotkey(hotkey)

        # Fallback para sequencias antigas que o monitor global nao consegue converter.
        if hotkey and not _is_structured_hotkey(hotkey) and not _legacy_hotkey_to_keyboard_spec(hotkey):
            sequence = QKeySequence(hotkey)
            if not sequence.isEmpty():
                self.recenter_shortcut = QShortcut(sequence, self)
                self.recenter_shortcut.setContext(Qt.ApplicationShortcut)
                self.recenter_shortcut.activated.connect(self._recenter)

    def _sync_controls_from_config(self) -> None:
        self._syncing_controls = True
        try:
            self.profile_name_edit.setText(self.config.profile_name)
            self._populate_camera_combo()
            self.hotkey_edit.set_hotkey(self.config.recenter_hotkey)
            self._set_combo_by_data(self.context_combo, self.config.tracking_context)
            self._set_combo_by_data(self.output_mode_combo, self.config.output_mode)
            for field, control in self.controls.items():
                control.set_value(getattr(self.config, field))
            for field, box in self.check_boxes.items():
                box.setChecked(bool(getattr(self.config, field)))
            self._update_calibration_status_from_config()
            self.output_manager.set_mode(self.config.output_mode)
            self._update_output_status()
            self._apply_language()
            self._update_debug_extended_visibility()
        finally:
            self._syncing_controls = False
        self._update_recenter_shortcut()

    def _set_combo_by_data(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _update_calibration_status_from_config(self) -> None:
        saved = []
        if self.config.calibration_center_set:
            saved.append("center")
        if self.config.calibration_left_set:
            saved.append("left")
        if self.config.calibration_right_set:
            saved.append("right")
        if self.config.calibration_up_set:
            saved.append("up")
        if self.config.calibration_down_set:
            saved.append("down")
        if self.config.gaze_calibration_center_set:
            saved.append("gaze center")
        if self.config.gaze_calibration_left_set:
            saved.append("gaze left")
        if self.config.gaze_calibration_right_set:
            saved.append("gaze right")
        if self.config.gaze_calibration_up_set:
            saved.append("gaze up")
        if self.config.gaze_calibration_down_set:
            saved.append("gaze down")
        localized = [self._tr(item) for item in saved]
        self.calibration_status_label.setText(
            self._tr("Saved: ") + ", ".join(localized) if localized else self._tr("No saved calibration")
        )

    def _save_profile(self) -> None:
        self.config.profile_name = self.profile_name_edit.text().strip() or "Manual Profile"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            self._tr("Save Profile"),
            str(self.profile_manager.default_path(self.config.profile_name)),
            "Torvix Tracker profile (*.json)",
        )
        if not path:
            return
        self.profile_manager.save(Path(path), self.config, self.config.profile_name)

    def _load_profile(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self,
            self._tr("Load Profile"),
            str(self.profile_manager.base_dir),
            "Torvix Tracker profile (*.json)",
        )
        if not path:
            return
        try:
            self.config = self.profile_manager.load(Path(path))
            self.output_manager.set_mode(self.config.output_mode)
            self.pose_filter.reset()
            self._sync_controls_from_config()
        except Exception as exc:
            QMessageBox.warning(self, __app_name__, f"{self._tr('Could not load profile')}:\n{exc}")

    def _open_auto_calibrate(self):
        is_active = self.camera.is_open
        wizard = CalibrationWizard(is_tracking_active=is_active, parent=self)
        self._wizard_instance = wizard
        wizard.finished_calibration.connect(self._apply_auto_calibration)
        wizard.show()

    def _apply_auto_calibration(self, results: dict):
        self._syncing_controls = True
        applied: list[str] = []

        # 1. Center (Recenter filter to captured neutral position)
        if "center_yaw" in results:
            center_pose = PoseSample(
                yaw=results["center_yaw"],
                pitch=results.get("center_pitch", 0.0),
                roll=results.get("center_roll", 0.0),
                x=results.get("center_x", 0.0),
                y=results.get("center_y", 0.0),
                z=results.get("center_z", 0.0),
            )
            self.config.calibration_center_set = True
            self.config.calibration_center_yaw = center_pose.yaw
            self.config.calibration_center_pitch = center_pose.pitch
            self.config.calibration_center_roll = center_pose.roll
            self.config.calibration_center_x = center_pose.x
            self.config.calibration_center_y = center_pose.y
            self.config.calibration_center_z = center_pose.z
            self.pose_filter.recenter(center_pose)
            applied.append("Centro")

        # 2. Horizontal amplitude -> signed yaw references + sensitivity.
        if "max_yaw" in results:
            max_yaw = max(1.0, results["max_yaw"])
            negative_yaw = results.get("negative_yaw")
            positive_yaw = results.get("positive_yaw")
            if negative_yaw is not None and abs(negative_yaw) >= 1.0:
                self.config.calibration_left_set = True
                self.config.calibration_left_yaw = negative_yaw
            if positive_yaw is not None and abs(positive_yaw) >= 1.0:
                self.config.calibration_right_set = True
                self.config.calibration_right_yaw = positive_yaw

            if self.config.calibration_left_set or self.config.calibration_right_set:
                yaw_sensitivity = 45.0 / max(self.config.max_head_angle, 1.0)
                self.config.head_yaw_sensitivity_cabin = self._clamp(yaw_sensitivity, 0.05, 3.5)
                self.config.head_tracking_end_point = 1.0
            else:
                yaw_sensitivity = 45.0 / max_yaw
                self.config.head_yaw_sensitivity_cabin = self._clamp(yaw_sensitivity, 0.5, 3.5)
                self.config.head_tracking_end_point = self._clamp(max_yaw / 45.0, 0.3, 1.0)
            applied.append("Sensibilidade Horizontal")

        # 3. Vertical amplitude -> signed pitch references + sensitivity.
        if "max_pitch" in results:
            max_pitch = max(1.0, results["max_pitch"])
            negative_pitch = results.get("negative_pitch")
            positive_pitch = results.get("positive_pitch")
            if negative_pitch is not None and abs(negative_pitch) >= 1.0:
                self.config.calibration_up_set = True
                self.config.calibration_up_pitch = negative_pitch
            if positive_pitch is not None and abs(positive_pitch) >= 1.0:
                self.config.calibration_down_set = True
                self.config.calibration_down_pitch = positive_pitch

            if self.config.calibration_up_set or self.config.calibration_down_set:
                pitch_sensitivity = 30.0 / max(self.config.max_head_angle, 1.0)
                self.config.head_pitch_sensitivity_cabin = self._clamp(pitch_sensitivity, 0.05, 3.5)
            else:
                pitch_sensitivity = 30.0 / max_pitch
                self.config.head_pitch_sensitivity_cabin = self._clamp(pitch_sensitivity, 0.5, 3.5)
            applied.append("Sensibilidade Vertical")

        # 4. Noise (stability) → micro-jitter threshold + output smoothing
        if "noise" in results:
            noise_val = results["noise"]
            # Jitter threshold: proportional to measured noise floor.
            self.config.output_micro_jitter = self._clamp(noise_val * 2.5, 0.05, 0.6)
            # Smoothing: more noise → more smoothing needed.
            self.config.output_smoothing = self._clamp(0.2 + (noise_val * 0.4), 0.1, 0.85)
            applied.append("Filtro de Ruído")

        self._sync_controls_from_config()
        self._syncing_controls = False

        summary = ", ".join(applied) if applied else "Nenhum"
        QMessageBox.information(
            self,
            self._tr("Success"),
            f"{self._tr('Auto calibration applied successfully! Sliders have been adjusted to your profile.')}\n\n"
            f"Ajustados: {summary}",
        )


    def _check_for_updates(self):
        # Evita múltiplas instâncias
        if self._update_checker and self._update_checker.isRunning():
            return

        # Mostra feedback inicial (opcional, pode ser apenas visual)
        self.statusBar().showMessage(self._tr("Checking for updates..."), 5000)
        
        self._update_checker = UpdateChecker(__version__, self._update_url)
        self._update_checker.finished.connect(self._on_update_check_finished)
        self._update_checker.start()

    def _on_update_check_finished(self, result: dict):
        if not result.get("success", False):
            QMessageBox.warning(
                self, 
                self._tr("Update Check Failed"), 
                f"{self._tr('Could not check for updates')}:\n{result.get('error', 'Unknown error')}"
            )
            return

        if result.get("has_update"):
            latest = result.get("latest_version")
            download_url = result.get("download_url")
            changelog = result.get("changelog")

            msg = f"<h3>{self._tr('New version available!')}</h3>"
            msg += f"<p>{self._tr('Current version')}: {__version__}</p>"
            msg += f"<p><b>{self._tr('Latest version')}: {latest}</b></p>"
            
            if changelog:
                msg += f"<p><b>{self._tr('What\'s new')}:</b><br>{changelog}</p>"

            dialog = QMessageBox(self)
            dialog.setWindowTitle(self._tr("Check for Updates"))
            dialog.setIcon(QMessageBox.Information)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText(msg)
            
            # Botões customizados
            btn_download = dialog.addButton(self._tr("Download Now"), QMessageBox.ActionRole)
            btn_close = dialog.addButton(self._tr("Close"), QMessageBox.RejectRole)
            
            dialog.exec()
            
            if dialog.clickedButton() == btn_download:
                import webbrowser
                webbrowser.open(download_url)
        else:
            QMessageBox.information(
                self, 
                self._tr("Check for Updates"), 
                self._tr("You are using the latest version.")
            )

    def _show_game_functions_dialog(self) -> None:
        if self._game_functions_dialog is not None:
            self._game_functions_dialog.show()
            self._game_functions_dialog.raise_()
            self._game_functions_dialog.activateWindow()
            return

        dialog = QDialog(self)
        dialog.setObjectName("gameFunctionsDialog")
        dialog.setWindowTitle(self._tr("Game Functions"))
        dialog.setWindowModality(Qt.NonModal)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.destroyed.connect(lambda: setattr(self, "_game_functions_dialog", None))
        dialog.setMinimumSize(640, 480)
        dialog.resize(760, 620)
        dialog.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)

        title = QLabel(self._tr("Game Functions"))
        title.setObjectName("dialogTitle")
        subtitle = QLabel(self._tr("game_functions_intro"))
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)

        text = QTextBrowser()
        text.setObjectName("gameFunctionsText")
        text.setOpenExternalLinks(False)
        text.setHtml(self._game_functions_help_html())

        close_button = QPushButton(self._tr("Close"))
        close_button.setObjectName("dialogCloseButton")
        close_button.clicked.connect(dialog.close)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(close_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(text, 1)
        layout.addLayout(button_row)

        self._game_functions_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _game_functions_help_html(self) -> str:
        sections_html: list[str] = []
        for section_key, items in GAME_FUNCTION_HELP_SECTIONS:
            section_title = html.escape(self._tr(section_key))
            entries = []
            for label_key, help_key in items:
                label = html.escape(self._tr(label_key))
                description = html.escape(self._tr(help_key))
                entries.append(
                    f"""
                    <div class="item">
                        <div class="item-title">{label}</div>
                        <div class="item-text">{description}</div>
                    </div>
                    """
                )
            sections_html.append(f"<h2>{section_title}</h2>{''.join(entries)}")

        return f"""
        <!doctype html>
        <html>
        <head>
            <style>
                body {{
                    background: #0D0D0D;
                    color: #D1D1D1;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    line-height: 1.45;
                    margin: 0;
                }}
                h2 {{
                    color: #00F2FF;
                    font-size: 14px;
                    font-weight: 700;
                    margin: 18px 0 8px 0;
                    text-transform: uppercase;
                }}
                h2:first-child {{
                    margin-top: 0;
                }}
                .item {{
                    border-bottom: 1px solid #222222;
                    padding: 8px 0;
                }}
                .item-title {{
                    color: #FFFFFF;
                    font-weight: 700;
                    margin-bottom: 3px;
                }}
                .item-text {{
                    color: #B8B8B8;
                }}
            </style>
        </head>
        <body>
            {''.join(sections_html)}
        </body>
        </html>
        """

    def _show_changelog(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self._tr("Changelog"))
        
        # Histórico de mudanças com estilo
        content = f"""
        <div style='font-family: sans-serif; min-width: 400px;'>
            <h3 style='color: #2196F3;'>v1.3.0 - {self._tr("Precision Improvement (Iris Update)")}</h3>
            <ul style='line-height: 1.4;'>
                <li><b>{self._tr("Iris Tracking: MediaPipe refinement enabled for millimeter precision.")}</b></li>
                <li><b>{self._tr("Adaptive Filters: New smoothing logic eliminates resting jitter.")}</b></li>
                <li><b>{self._tr("Confidence Optimization: Detection thresholds adjusted for stability.")}</b></li>
            </ul>

            <h3 style='color: #666;'>v1.2.0 - {self._tr("Stability Update")}</h3>
            <ul style='line-height: 1.4;'>
                <li><b>{self._tr("Hysteresis Filter: Eliminated data jitter when head is still.")}</b></li>
                <li><b>{self._tr("Shortcut Interface: New clear button (✕) and improved key capture.")}</b></li>
                <li><b>{self._tr("New Help Menu: Added About, Credits, Changelog and Updates.")}</b></li>
                <li><b>{self._tr("Auto Calibration: Smart sensitivity adjustment based on your movement.")}</b></li>
            </ul>
            
            <h3 style='color: #666;'>v1.1.0</h3>
            <ul style='line-height: 1.4;'>
                <li>{self._tr("Implemented multi-language support (ENG, POR, ESP).")}</li>
                <li>{self._tr("Added experimental support for simulated gaze.")}</li>
            </ul>
        </div>
        """
        
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(content)
        dialog.setStandardButtons(QMessageBox.Ok)
        
        ok_button = dialog.button(QMessageBox.Ok)
        if ok_button:
            ok_button.setText(self._tr("Close"))
            
        dialog.exec()

    def _show_about_dialog(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self._tr("About & Credits"))
        
        # Estilo premium com HTML
        content = f"""
        <div style='font-family: sans-serif; min-width: 350px;'>
            <h2 style='color: #2196F3; margin-bottom: 0px;'>Torvix Tracker</h2>
            <p style='color: #666; margin-top: 4px; margin-bottom: 15px;'>{self._tr("Version")} {__version__}</p>
            
            <p><b>{self._tr("Developed by")}</b></p>
            <p style='margin-bottom: 20px;'>{self._tr("This project is powered by open source software:")}</p>
            
            <ul style='line-height: 1.6;'>
                <li><a href='https://google.github.io/mediapipe/' style='color: #2196F3;'>MediaPipe</a> - AI Hand & Face tracking</li>
                <li><a href='https://www.qt.io/' style='color: #2196F3;'>PySide6 (Qt)</a> - Professional UI framework</li>
                <li><a href='https://opencv.org/' style='color: #2196F3;'>OpenCV</a> - Computer vision</li>
                <li><a href='https://numpy.org/' style='color: #2196F3;'>NumPy</a> - Mathematical processing</li>
            </ul>
        </div>
        """
        
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(content)
        dialog.setStandardButtons(QMessageBox.Ok)
        
        # Traduzir o botão OK
        ok_button = dialog.button(QMessageBox.Ok)
        if ok_button:
            ok_button.setText(self._tr("Close"))
            
        dialog.exec()


def _show_welcome_splash() -> None:
    video_path = _runtime_asset_path("welcome_animation.mp4")
    if not video_path.exists():
        return

    dialog = WelcomeSplashDialog(video_path)
    if dialog.is_available:
        dialog.exec()


def run_app() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
