# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .models import GazeSample


LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144, 145, 159]
RIGHT_EYE_INDICES = [263, 387, 385, 362, 380, 373, 374, 386]
LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]


@dataclass(frozen=True)
class _EyeGeometry:
    yaw: float
    pitch: float
    confidence: float
    iris_center: tuple[int, int]
    eye_center: tuple[int, int]
    iris_normalized: tuple[float, float]
    eye_width: float
    eye_height: float


def estimate_iris_gaze(landmarks: Any, width: int, height: int) -> GazeSample:
    if len(landmarks) <= max(*LEFT_IRIS_INDICES, *RIGHT_IRIS_INDICES):
        return GazeSample()

    left = _estimate_eye(
        landmarks,
        width,
        height,
        outer_idx=33,
        inner_idx=133,
        top_indices=(159, 158, 160),
        bottom_indices=(145, 144, 153),
        iris_indices=LEFT_IRIS_INDICES,
    )
    right = _estimate_eye(
        landmarks,
        width,
        height,
        outer_idx=263,
        inner_idx=362,
        top_indices=(386, 385, 387),
        bottom_indices=(374, 380, 373),
        iris_indices=RIGHT_IRIS_INDICES,
    )

    valid = [eye for eye in (left, right) if eye is not None and eye.confidence > 0.0]
    if not valid:
        return GazeSample(
            source="iris",
            eye_span=_interocular_span(landmarks),
            distance_scale=_distance_scale_from_span(_interocular_span(landmarks)),
            left_confidence=0.0 if left is None else left.confidence,
            right_confidence=0.0 if right is None else right.confidence,
        )

    total_confidence = sum(eye.confidence for eye in valid)
    yaw = sum(eye.yaw * eye.confidence for eye in valid) / total_confidence
    pitch = sum(eye.pitch * eye.confidence for eye in valid) / total_confidence
    average_confidence = total_confidence / len(valid)
    stereo_factor = 1.0 if len(valid) >= 2 else 0.72
    confidence = _clamp(average_confidence * stereo_factor, 0.0, 1.0)
    normalized_x = sum(eye.iris_normalized[0] * eye.confidence for eye in valid) / total_confidence
    normalized_y = sum(eye.iris_normalized[1] * eye.confidence for eye in valid) / total_confidence
    eye_span = _interocular_span(landmarks)

    return GazeSample(
        yaw=_clamp(yaw, -1.5, 1.5),
        pitch=_clamp(pitch, -1.5, 1.5),
        confidence=confidence,
        source="iris",
        normalized_x=_clamp(normalized_x, 0.0, 1.0),
        normalized_y=_clamp(normalized_y, 0.0, 1.0),
        eye_span=eye_span,
        distance_scale=_distance_scale_from_span(eye_span),
        valid_eye_count=len(valid),
        left_confidence=0.0 if left is None else left.confidence,
        right_confidence=0.0 if right is None else right.confidence,
        left_iris=None if left is None else left.iris_center,
        right_iris=None if right is None else right.iris_center,
        left_eye_center=None if left is None else left.eye_center,
        right_eye_center=None if right is None else right.eye_center,
        left_ratio=(0.0, 0.0) if left is None else (left.yaw, left.pitch),
        right_ratio=(0.0, 0.0) if right is None else (right.yaw, right.pitch),
    )


def _estimate_eye(
    landmarks: Any,
    width: int,
    height: int,
    *,
    outer_idx: int,
    inner_idx: int,
    top_indices: tuple[int, ...],
    bottom_indices: tuple[int, ...],
    iris_indices: list[int],
) -> _EyeGeometry | None:
    outer = _point(landmarks, outer_idx, width, height)
    inner = _point(landmarks, inner_idx, width, height)
    top = _mean_point([_point(landmarks, idx, width, height) for idx in top_indices])
    bottom = _mean_point([_point(landmarks, idx, width, height) for idx in bottom_indices])
    iris = _mean_point([_point(landmarks, idx, width, height) for idx in iris_indices])

    left_corner, right_corner = sorted((outer, inner), key=lambda point: point[0])
    eye_axis = (right_corner[0] - left_corner[0], right_corner[1] - left_corner[1])
    eye_width = math.hypot(*eye_axis)
    if eye_width <= 6.0:
        return None

    horizontal_unit = (eye_axis[0] / eye_width, eye_axis[1] / eye_width)
    vertical_axis = (bottom[0] - top[0], bottom[1] - top[1])
    eye_height = math.hypot(*vertical_axis)
    if eye_height <= 1.0:
        return None

    vertical_unit = (vertical_axis[0] / eye_height, vertical_axis[1] / eye_height)
    horizontal_center = ((left_corner[0] + right_corner[0]) * 0.5, (left_corner[1] + right_corner[1]) * 0.5)
    vertical_center = ((top[0] + bottom[0]) * 0.5, (top[1] + bottom[1]) * 0.5)
    eye_center = (
        int(round((horizontal_center[0] + vertical_center[0]) * 0.5)),
        int(round((horizontal_center[1] + vertical_center[1]) * 0.5)),
    )

    yaw = _dot((iris[0] - horizontal_center[0], iris[1] - horizontal_center[1]), horizontal_unit) / (eye_width * 0.5)
    pitch = -_dot((iris[0] - vertical_center[0], iris[1] - vertical_center[1]), vertical_unit) / (eye_height * 0.5)

    openness = eye_height / eye_width
    size_confidence = _clamp((eye_width - 8.0) / 28.0, 0.0, 1.0)
    open_confidence = _clamp((openness - 0.055) / 0.105, 0.0, 1.0)
    centered_confidence = _clamp(1.35 - max(abs(yaw), abs(pitch)) * 0.35, 0.0, 1.0)
    confidence = size_confidence * open_confidence * centered_confidence

    return _EyeGeometry(
        yaw=_clamp(yaw, -1.5, 1.5),
        pitch=_clamp(pitch, -1.5, 1.5),
        confidence=confidence,
        iris_center=(int(round(iris[0])), int(round(iris[1]))),
        eye_center=eye_center,
        iris_normalized=(
            _clamp(iris[0] / max(float(width), 1.0), 0.0, 1.0),
            _clamp(iris[1] / max(float(height), 1.0), 0.0, 1.0),
        ),
        eye_width=eye_width,
        eye_height=eye_height,
    )


def _point(landmarks: Any, index: int, width: int, height: int) -> tuple[float, float]:
    landmark = landmarks[index]
    return (float(landmark.x) * width, float(landmark.y) * height)


def _mean_point(points: list[tuple[float, float]]) -> tuple[float, float]:
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _dot(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _interocular_span(landmarks: Any) -> float:
    try:
        left = landmarks[33]
        right = landmarks[263]
        dx = float(right.x) - float(left.x)
        dy = float(right.y) - float(left.y)
        return _clamp(math.hypot(dx, dy), 0.0, 1.0)
    except (AttributeError, IndexError, TypeError, ValueError):
        return 0.0


def _distance_scale_from_span(span: float) -> float:
    if span <= 0.001:
        return 1.0
    return 1.0 / span


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))
