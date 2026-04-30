from __future__ import annotations

import configparser
import string
import struct
from pathlib import Path

from .profile import TrackingConfig


def import_viewtracker_ini(path: str | Path, base_config: TrackingConfig | None = None) -> TrackingConfig:
    source = Path(path)
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(source.read_text(encoding="utf-8", errors="replace"))

    config = TrackingConfig.from_dict(base_config.to_dict()) if base_config is not None else TrackingConfig()
    config.profile_name = f"ViewTracker Smooth ({source.stem})"

    modules = _section(parser, "modules")
    filter_name = modules.get("filter-dll", "").strip().lower()
    protocol_name = modules.get("protocol-dll", "").strip().lower()

    if "accela" in filter_name:
        _apply_accela_like_defaults(config, _accela_slider_values(parser))

    if parser.has_section("spline-yaw") or parser.has_section("spline-pitch"):
        _apply_spline_like_curve(config)

    if "freetrack" in protocol_name:
        config.output_mode = "opentrack_udp"

    return config


def _section(parser: configparser.ConfigParser, name: str) -> dict[str, str]:
    if not parser.has_section(name):
        return {}
    return {key: value for key, value in parser.items(name)}


def _apply_accela_like_defaults(config: TrackingConfig, sliders: dict[str, float]) -> None:
    rotation_deadzone = sliders.get("rotation-deadzone", 0.02)
    rotation_sensitivity = sliders.get("rotation-sensitivity", 1.20)
    rotation_nonlinearity = sliders.get("rotation-nonlinearity", 1.08)

    config.input_deadzone = _clamp(rotation_deadzone * 18.0, 0.12, 0.70)
    config.head_view_responsiveness = 1.45
    config.head_view_smoothing = 0.08
    config.head_yaw_sensitivity_cabin = _clamp(rotation_sensitivity, 0.75, 1.65)
    config.head_pitch_sensitivity_cabin = _clamp(rotation_sensitivity * 0.95, 0.75, 1.55)
    config.head_roll_sensitivity = 0.42
    config.head_tracking_exponent = _clamp(rotation_nonlinearity, 0.85, 1.30)
    config.output_smoothing = 0.12
    config.output_micro_jitter = 0.10
    config.output_max_step = 18.00


def _apply_spline_like_curve(config: TrackingConfig) -> None:
    config.head_tracking_exponent = max(config.head_tracking_exponent, 1.08)
    config.head_tracking_inflection_point = 0.50
    config.head_tracking_start_point = 0.01
    config.head_tracking_end_point = 1.00


def _accela_slider_values(parser: configparser.ConfigParser) -> dict[str, float]:
    if not parser.has_section("accela-sliders"):
        return {}
    values: dict[str, float] = {}
    for key, value in parser.items("accela-sliders"):
        parsed = _qt_variant_slider_value(value)
        if parsed is not None:
            values[key] = parsed
    return values


def _qt_variant_slider_value(value: str) -> float | None:
    if not value.startswith("@Variant(") or not value.endswith(")"):
        return None
    payload = _decode_qt_escaped_bytes(value[len("@Variant(") : -1])
    marker = b"::options::slider_value\x00"
    marker_index = payload.find(marker)
    if marker_index < 0:
        return None
    start = marker_index + len(marker)
    if len(payload) < start + 8:
        return None
    return struct.unpack(">d", payload[start : start + 8])[0]


def _decode_qt_escaped_bytes(value: str) -> bytes:
    output = bytearray()
    index = 0
    hex_digits = set(string.hexdigits)
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            output.append(ord(char) & 0xFF)
            index += 1
            continue

        marker = value[index + 1]
        if marker == "x":
            digits = []
            cursor = index + 2
            while cursor < len(value) and len(digits) < 2 and value[cursor] in hex_digits:
                digits.append(value[cursor])
                cursor += 1
            output.append(int("".join(digits) or "0", 16))
            index = cursor
            continue

        if marker in "01234567":
            digits = [marker]
            cursor = index + 2
            while cursor < len(value) and len(digits) < 3 and value[cursor] in "01234567":
                digits.append(value[cursor])
                cursor += 1
            output.append(int("".join(digits), 8))
            index = cursor
            continue

        output.append(ord(marker) & 0xFF)
        index += 2
    return bytes(output)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))
