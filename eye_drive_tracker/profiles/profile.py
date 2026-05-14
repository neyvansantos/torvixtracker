# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

from dataclasses import asdict, dataclass, fields


@dataclass
class TrackingConfig:
    profile_name: str = "Manual Profile"
    language: str = "ENG"
    camera_index: int = 0
    camera_width: int = 0
    camera_height: int = 0
    camera_fps: float = 0.0

    input_deadzone: float = 1.35

    tracking_context: str = "cabin"
    head_view_responsiveness: float = 1.00
    head_view_smoothing: float = 0.24
    head_yaw_sensitivity_cabin: float = 1.00
    head_pitch_sensitivity_cabin: float = 1.00
    head_yaw_sensitivity_walk: float = 1.0
    head_pitch_sensitivity_walk: float = 1.0
    head_roll_sensitivity: float = 0.55
    head_tracking_exponent: float = 1.0
    head_tracking_inflection_point: float = 0.5
    head_tracking_start_point: float = 0.0
    head_tracking_end_point: float = 1.0
    max_head_angle: float = 180.0
    invert_yaw: bool = True
    invert_pitch: bool = True
    invert_roll: bool = False
    translation_deadzone: float = 0.55
    translation_smoothing: float = 0.36
    translation_x_sensitivity: float = 0.90
    translation_y_sensitivity: float = 0.50
    translation_z_sensitivity: float = 1.10
    invert_x: bool = False
    invert_y: bool = False
    invert_z: bool = True

    gaze_view_responsiveness: float = 0.82
    gaze_view_smoothing: float = 0.48
    gaze_tracking_exponent: float = 1.10
    gaze_tracking_inflection_point: float = 0.55
    gaze_tracking_start_point: float = 0.08
    gaze_tracking_end_point: float = 1.0
    max_gaze_angle: float = 12.0
    gaze_strength: float = 0.35
    enable_simulated_gaze: bool = True
    invert_gaze_yaw: bool = False
    invert_gaze_pitch: bool = False
    gaze_calibration_center_set: bool = False
    gaze_calibration_center_yaw: float = 0.0
    gaze_calibration_center_pitch: float = 0.0
    gaze_calibration_left_set: bool = False
    gaze_calibration_left_yaw: float = 0.0
    gaze_calibration_right_set: bool = False
    gaze_calibration_right_yaw: float = 0.0
    gaze_calibration_up_set: bool = False
    gaze_calibration_up_pitch: float = 0.0
    gaze_calibration_down_set: bool = False
    gaze_calibration_down_pitch: float = 0.0

    enable_extended_view: bool = False
    debug_extended_view: bool = False
    extended_view_strength: float = 0.18
    extended_view_blend: float = 0.35
    extended_view_exponent: float = 1.20
    extended_view_inflection_point: float = 0.60
    extended_view_start_point: float = 0.35
    extended_view_end_point: float = 1.0
    extended_view_acceleration: float = 1.25
    extended_view_max_angle: float = 18.0
    extended_view_smoothing: float = 0.48

    output_smoothing: float = 0.30
    output_micro_jitter: float = 0.06
    output_max_step: float = 6.00

    motion_filter_enabled: bool = True
    motion_filter_preset: str = "balanced"
    motion_rotation_enabled: bool = True
    motion_position_enabled: bool = True
    motion_rotation_mode: str = "QuaternionHamilton"
    motion_rotation_smoothing: float = 1.50
    motion_rotation_deadzone: float = 0.03
    motion_rotation_responsiveness: float = 1.00
    motion_rotation_snap_threshold: float = 8.00
    motion_rotation_max_speed_snap: float = 360.0
    motion_rotation_gain_curve_strength: float = 1.00
    motion_position_smoothing: float = 1.00
    motion_position_deadzone: float = 0.10
    motion_position_responsiveness: float = 1.00
    motion_position_snap_threshold: float = 15.00
    motion_position_max_speed_snap: float = 220.0
    motion_position_gain_curve_strength: float = 1.00
    motion_zoom_smoothing_enabled: bool = True
    motion_max_zoomed_smoothing: float = 1.20
    motion_max_z: float = 20.0
    motion_confidence_smoothing_enabled: bool = True
    motion_low_confidence_threshold: float = 0.45
    motion_critical_confidence_threshold: float = 0.25
    motion_max_confidence_smoothing_boost: float = 2.00
    motion_hold_frames_on_bad_tracking: int = 3
    motion_stillness_detection_enabled: bool = True
    motion_stillness_window: int = 12
    motion_stillness_rotation_threshold: float = 0.08
    motion_stillness_position_threshold: float = 0.05
    motion_stillness_smoothing_boost: float = 1.50
    motion_stillness_deadzone_boost: float = 1.20
    motion_snap_enabled: bool = False
    motion_snap_alpha: float = 0.60
    motion_debug_enabled: bool = False

    recenter_hotkey: str = "Ctrl+Alt+R"
    calibration_center_set: bool = False
    calibration_center_yaw: float = 0.0
    calibration_center_pitch: float = 0.0
    calibration_center_roll: float = 0.0
    calibration_center_x: float | None = None
    calibration_center_y: float | None = None
    calibration_center_z: float | None = None
    calibration_left_set: bool = False
    calibration_left_yaw: float = 0.0
    calibration_right_set: bool = False
    calibration_right_yaw: float = 0.0
    calibration_up_set: bool = False
    calibration_up_pitch: float = 0.0
    calibration_down_set: bool = False
    calibration_down_pitch: float = 0.0

    output_mode: str = "opentrack_udp"

    onboarding_completed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TrackingConfig":
        allowed = {field.name for field in fields(cls)}
        cleaned = dict(data or {})
        cleaned = cls._upgrade_legacy_keys(cleaned)
        if cleaned.get("language") not in {"ENG", "POR", "ESP"}:
            cleaned["language"] = "ENG"
        cleaned = {key: value for key, value in cleaned.items() if key in allowed}
        return cls(**cleaned)

    @staticmethod
    def _upgrade_legacy_keys(data: dict) -> dict:
        legacy_map = {
            "deadzone": "input_deadzone",
            "responsiveness": "head_view_responsiveness",
            "smoothing": "head_view_smoothing",
            "yaw_multiplier": "head_yaw_sensitivity_cabin",
            "pitch_multiplier": "head_pitch_sensitivity_cabin",
            "roll_multiplier": "head_roll_sensitivity",
            "max_yaw": "max_head_angle",
            "max_pitch": "max_head_angle",
        }
        upgraded = dict(data)
        for old_key, new_key in legacy_map.items():
            if old_key in upgraded and new_key not in upgraded:
                upgraded[new_key] = upgraded[old_key]
        if upgraded.get("output_mode") == "disabled":
            upgraded["output_mode"] = "trackir"
        return upgraded
