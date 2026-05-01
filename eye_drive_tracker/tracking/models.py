# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PoseSample:
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class GazeSample:
    yaw: float = 0.0
    pitch: float = 0.0
    confidence: float = 0.0
    source: str = "none"
    normalized_x: float = 0.5
    normalized_y: float = 0.5
    eye_span: float = 0.0
    face_size_normalized: float = 0.0
    distance_scale: float = 1.0
    valid_eye_count: int = 0
    left_confidence: float = 0.0
    right_confidence: float = 0.0
    left_iris: Optional[tuple[int, int]] = None
    right_iris: Optional[tuple[int, int]] = None
    left_eye_center: Optional[tuple[int, int]] = None
    right_eye_center: Optional[tuple[int, int]] = None
    left_ratio: tuple[float, float] = (0.0, 0.0)
    right_ratio: tuple[float, float] = (0.0, 0.0)


@dataclass
class TrackingResult:
    detected: bool = False
    pose: PoseSample = field(default_factory=PoseSample)
    method: str = "none"
    face_box: Optional[tuple[int, int, int, int]] = None
    gaze: GazeSample = field(default_factory=GazeSample)
    frame_size: tuple[int, int] = (0, 0)
    face_center_normalized: Optional[tuple[float, float]] = None
    face_size_normalized: float = 0.0
    user_distance: float = 0.0
    tracking_fps: float = 0.0
    processing_ms: float = 0.0
    dropped_frames: int = 0
    left_eye_points: list[tuple[int, int]] = field(default_factory=list)
    right_eye_points: list[tuple[int, int]] = field(default_factory=list)
    eye_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
