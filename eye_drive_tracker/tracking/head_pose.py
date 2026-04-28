from __future__ import annotations

import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import cv2
import numpy as np

from .gaze import LEFT_EYE_INDICES, RIGHT_EYE_INDICES, estimate_iris_gaze
from .models import PoseSample, TrackingResult


@dataclass(frozen=True)
class _ZoomLandmarks:
    roi_landmarks: Any
    original_landmarks: Any
    roi: tuple[int, int, int, int]
    zoom_size: tuple[int, int]


class HeadPoseTracker:
    _LANDMARK_YAW_BLEND = 0.78
    _LANDMARK_NOSE_YAW_SCALE = 68.0
    _LANDMARK_DEPTH_YAW_SCALE = 40.0
    _LANDMARK_YAW_LIMIT = 55.0
    _YAW_MAX_STEP_PER_FRAME = 3.0
    _TRACKING_RESET_MISSED_DETECTIONS = 8
    _POSE_RESET_MISSED_DETECTIONS = 90
    _IRIS_ZOOM_CONFIDENCE_TRIGGER = 0.34
    _FACE_ZOOM_SIZE_TRIGGER = 0.30
    _ZOOM_TARGET_SIZE = 512
    _ZOOM_MAX_SCALE = 3.4
    _ZOOM_PADDING_RATIO = 0.58

    def __init__(self) -> None:
        self._enable_runtime_acceleration()
        self._face_mesh: Optional[Any] = None
        self._face_landmarker: Optional[Any] = None
        self._mp_tasks: Optional[Any] = None
        self._last_timestamp_ms = 0
        self._mp_error: Optional[str] = None
        self._face_cascade: Optional[cv2.CascadeClassifier] = None
        self._face_alt_cascade: Optional[cv2.CascadeClassifier] = None
        self._face_alt2_cascade: Optional[cv2.CascadeClassifier] = None
        self._profile_cascade: Optional[cv2.CascadeClassifier] = None
        self._eye_cascade: Optional[cv2.CascadeClassifier] = None
        self._frontal_cascades: list[cv2.CascadeClassifier] = []
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._box_tracker: Optional[Any] = None
        self._last_face_box: Optional[tuple[int, int, int, int]] = None
        self._last_pose = PoseSample()
        self._has_last_pose = False
        self._last_rotation_vector: Optional[np.ndarray] = None
        self._last_translation_vector: Optional[np.ndarray] = None
        self._missed_detections = 0
        self._tracker_misses = 0
        self._max_tracker_misses = 45
        self._model_points = np.array(
            [
                (0.0, 0.0, 0.0),
                (0.0, -63.6, -12.5),
                (-43.3, 32.7, -26.0),
                (43.3, 32.7, -26.0),
                (-28.9, -28.9, -24.1),
                (28.9, -28.9, -24.1),
            ],
            dtype=np.float64,
        )
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        self._camera_matrix: Optional[np.ndarray] = None
        self._camera_matrix_size: Optional[tuple[int, int]] = None
        self._last_pose_timestamp: Optional[float] = None
        self._pose_ema_enabled = True
        self._init_mediapipe()
        self._init_haar()

    @staticmethod
    def _enable_runtime_acceleration() -> None:
        try:
            cv2.setUseOptimized(True)
            if hasattr(cv2, "ocl"):
                cv2.ocl.setUseOpenCL(True)
        except cv2.error:
            pass

    @property
    def backend_name(self) -> str:
        if self._face_mesh is not None:
            return "MediaPipe Face Mesh"
        if self._face_landmarker is not None:
            return "MediaPipe Face Landmarker"
        return "OpenCV Haar fallback"

    @property
    def mediapipe_error(self) -> Optional[str]:
        return self._mp_error

    def detect(self, frame_bgr: np.ndarray) -> TrackingResult:
        if frame_bgr is None:
            return TrackingResult(detected=False)

        if self._face_mesh is not None:
            result = self._detect_with_mediapipe(frame_bgr)
            if result.detected:
                self._missed_detections = 0
                return result

        if self._face_landmarker is not None:
            result = self._detect_with_tasks(frame_bgr)
            if result.detected:
                self._missed_detections = 0
                return result

        result = self._detect_with_haar(frame_bgr)
        if result.detected:
            self._missed_detections = 0
            return result

        self._mark_detection_lost()
        return result

    def close(self) -> None:
        if self._face_mesh is not None:
            self._face_mesh.close()
        if self._face_landmarker is not None:
            self._face_landmarker.close()
        self._face_mesh = None
        self._face_landmarker = None
        self._last_rotation_vector = None
        self._last_translation_vector = None
        self._last_pose_timestamp = None

    def _init_mediapipe(self) -> None:
        os.environ.setdefault("GLOG_minloglevel", "2")
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        errors: list[str] = []
        try:
            import mediapipe as mp

            solutions = getattr(mp, "solutions")
            self._face_mesh = solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.35,
                min_tracking_confidence=0.35,
            )
            return
        except Exception as exc:  # pragma: no cover - depends on local install
            errors.append(f"solutions: {exc}")
            self._face_mesh = None

        try:
            import mediapipe as mp

            model_path = self._face_landmarker_model_path()
            if not model_path.exists():
                raise FileNotFoundError(f"model not found: {model_path}")

            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=0.35,
                min_face_presence_confidence=0.35,
                min_tracking_confidence=0.35,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
            )
            self._face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
            self._mp_tasks = mp
            return
        except Exception as exc:  # pragma: no cover - depends on local install/model
            errors.append(f"tasks: {exc}")
            self._face_landmarker = None
            self._mp_tasks = None

        self._mp_error = " | ".join(errors)

    def _init_haar(self) -> None:
        face_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_alt_path = cv2.data.haarcascades + "haarcascade_frontalface_alt.xml"
        face_alt2_path = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
        profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        eye_path = cv2.data.haarcascades + "haarcascade_eye.xml"
        self._face_cascade = cv2.CascadeClassifier(face_path)
        self._face_alt_cascade = cv2.CascadeClassifier(face_alt_path)
        self._face_alt2_cascade = cv2.CascadeClassifier(face_alt2_path)
        self._profile_cascade = cv2.CascadeClassifier(profile_path)
        self._eye_cascade = cv2.CascadeClassifier(eye_path)
        self._frontal_cascades = [
            cascade
            for cascade in (self._face_cascade, self._face_alt_cascade, self._face_alt2_cascade)
            if cascade is not None and not cascade.empty()
        ]

    def _face_landmarker_model_path(self) -> Path:
        env_path = os.environ.get("TORVIX_FACE_LANDMARKER_MODEL")
        if env_path:
            return Path(env_path)

        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
            candidates.append(base_path / "models" / "face_landmarker.task")
            candidates.append(Path(sys.executable).resolve().parent / "models" / "face_landmarker.task")

        candidates.append(Path.cwd() / "models" / "face_landmarker.task")
        candidates.append(Path(__file__).resolve().parents[2] / "models" / "face_landmarker.task")

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[0]

    def _detect_with_mediapipe(self, frame_bgr: np.ndarray) -> TrackingResult:
        height, width = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        try:
            results = self._face_mesh.process(rgb)
        except Exception as exc:  # pragma: no cover - defensive runtime fallback
            self._mp_error = str(exc)
            return TrackingResult(detected=False, method="MediaPipe Face Mesh")

        if not results.multi_face_landmarks:
            seed_box = self._last_face_box or self._detect_face_box(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY))
            zoom = self._detect_zoomed_mediapipe_landmarks(frame_bgr, seed_box)
            if zoom is None:
                return TrackingResult(detected=False, method="MediaPipe Face Mesh")
            return self._result_from_landmarks(
                zoom.original_landmarks,
                width,
                height,
                method="MediaPipe Face Mesh + face zoom",
                gaze=self._gaze_from_zoom(zoom, width, height),
            )

        landmarks = results.multi_face_landmarks[0].landmark
        face_box = self._landmark_box(landmarks, width, height)
        metadata = self._tracking_metadata(face_box, width, height, landmarks)

        # Pontos da pálpebra + ponto central da íris (468/473) para maior precisão visual
        gaze = estimate_iris_gaze(landmarks, width, height)
        self._apply_distance_metadata_to_gaze(gaze, metadata)

        if self._should_try_face_zoom(gaze, metadata):
            zoom = self._detect_zoomed_mediapipe_landmarks(frame_bgr, face_box)
            if zoom is not None:
                zoom_gaze = self._gaze_from_zoom(zoom, width, height)
                if self._is_zoom_gaze_better(zoom_gaze, gaze):
                    return self._result_from_landmarks(
                        zoom.original_landmarks,
                        width,
                        height,
                        method="MediaPipe Face Mesh + face zoom",
                        gaze=zoom_gaze,
                    )

        return self._result_from_landmarks(landmarks, width, height, method="MediaPipe Face Mesh", gaze=gaze)

    def _detect_with_tasks(self, frame_bgr: np.ndarray) -> TrackingResult:
        height, width = frame_bgr.shape[:2]
        rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        timestamp_ms = self._next_timestamp_ms()

        try:
            image = self._mp_tasks.Image(image_format=self._mp_tasks.ImageFormat.SRGB, data=rgb)
            results = self._face_landmarker.detect_for_video(image, timestamp_ms)
        except Exception as exc:  # pragma: no cover - defensive runtime fallback
            self._mp_error = str(exc)
            return TrackingResult(detected=False, method="MediaPipe Face Landmarker")

        if not results.face_landmarks:
            seed_box = self._last_face_box or self._detect_face_box(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY))
            zoom = self._detect_zoomed_tasks_landmarks(frame_bgr, seed_box)
            if zoom is None:
                return TrackingResult(detected=False, method="MediaPipe Face Landmarker")
            return self._result_from_landmarks(
                zoom.original_landmarks,
                width,
                height,
                method="MediaPipe Face Landmarker + face zoom",
                gaze=self._gaze_from_zoom(zoom, width, height, source="iris-zoom-tasks"),
            )

        landmarks = results.face_landmarks[0]
        face_box = self._landmark_box(landmarks, width, height)
        metadata = self._tracking_metadata(face_box, width, height, landmarks)
        gaze = estimate_iris_gaze(landmarks, width, height)
        self._apply_distance_metadata_to_gaze(gaze, metadata)

        if self._should_try_face_zoom(gaze, metadata):
            zoom = self._detect_zoomed_tasks_landmarks(frame_bgr, face_box)
            if zoom is not None:
                zoom_gaze = self._gaze_from_zoom(zoom, width, height, source="iris-zoom-tasks")
                if self._is_zoom_gaze_better(zoom_gaze, gaze):
                    return self._result_from_landmarks(
                        zoom.original_landmarks,
                        width,
                        height,
                        method="MediaPipe Face Landmarker + face zoom",
                        gaze=zoom_gaze,
                    )

        return self._result_from_landmarks(landmarks, width, height, method="MediaPipe Face Landmarker", gaze=gaze)

    def _result_from_landmarks(
        self,
        landmarks: Any,
        width: int,
        height: int,
        *,
        method: str,
        gaze: Any | None = None,
    ) -> TrackingResult:
        pose = self._stabilize_pose(self._solve_head_pose(landmarks, width, height))
        face_box = self._landmark_box(landmarks, width, height)
        metadata = self._tracking_metadata(face_box, width, height, landmarks)
        gaze = estimate_iris_gaze(landmarks, width, height) if gaze is None else gaze
        self._apply_distance_metadata_to_gaze(gaze, metadata)
        left_eye = self._points_for_indices(landmarks, width, height, LEFT_EYE_INDICES)
        right_eye = self._points_for_indices(landmarks, width, height, RIGHT_EYE_INDICES)
        self._last_face_box = face_box

        return TrackingResult(
            detected=True,
            pose=pose,
            method=method,
            face_box=face_box,
            gaze=gaze,
            frame_size=(width, height),
            **metadata,
            left_eye_points=left_eye,
            right_eye_points=right_eye,
        )

    def _detect_zoomed_mediapipe_landmarks(
        self,
        frame_bgr: np.ndarray,
        face_box: tuple[int, int, int, int] | None,
    ) -> _ZoomLandmarks | None:
        zoomed = self._zoomed_face_frame(frame_bgr, face_box)
        if zoomed is None:
            return None
        zoom_frame, roi = zoomed
        rgb = cv2.cvtColor(zoom_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        try:
            results = self._face_mesh.process(rgb)
        except Exception as exc:  # pragma: no cover - defensive runtime fallback
            self._mp_error = str(exc)
            return None
        if not results.multi_face_landmarks:
            return None
        roi_landmarks = results.multi_face_landmarks[0].landmark
        return _ZoomLandmarks(
            roi_landmarks=roi_landmarks,
            original_landmarks=self._remap_landmarks_from_roi(roi_landmarks, roi, frame_bgr.shape[1], frame_bgr.shape[0]),
            roi=roi,
            zoom_size=(zoom_frame.shape[1], zoom_frame.shape[0]),
        )

    def _detect_zoomed_tasks_landmarks(
        self,
        frame_bgr: np.ndarray,
        face_box: tuple[int, int, int, int] | None,
    ) -> _ZoomLandmarks | None:
        if self._face_landmarker is None or self._mp_tasks is None:
            return None
        zoomed = self._zoomed_face_frame(frame_bgr, face_box)
        if zoomed is None:
            return None
        zoom_frame, roi = zoomed
        rgb = np.ascontiguousarray(cv2.cvtColor(zoom_frame, cv2.COLOR_BGR2RGB))
        try:
            image = self._mp_tasks.Image(image_format=self._mp_tasks.ImageFormat.SRGB, data=rgb)
            results = self._face_landmarker.detect_for_video(image, self._next_timestamp_ms())
        except Exception as exc:  # pragma: no cover - defensive runtime fallback
            self._mp_error = str(exc)
            return None
        if not results.face_landmarks:
            return None
        roi_landmarks = results.face_landmarks[0]
        return _ZoomLandmarks(
            roi_landmarks=roi_landmarks,
            original_landmarks=self._remap_landmarks_from_roi(roi_landmarks, roi, frame_bgr.shape[1], frame_bgr.shape[0]),
            roi=roi,
            zoom_size=(zoom_frame.shape[1], zoom_frame.shape[0]),
        )

    def _zoomed_face_frame(
        self,
        frame_bgr: np.ndarray,
        face_box: tuple[int, int, int, int] | None,
    ) -> tuple[np.ndarray, tuple[int, int, int, int]] | None:
        height, width = frame_bgr.shape[:2]
        roi = self._face_roi_for_zoom(face_box, width, height)
        if roi is None:
            return None
        x, y, w, h = roi
        crop = frame_bgr[y : y + h, x : x + w]
        if crop.size <= 0:
            return None

        largest = max(w, h, 1)
        scale = min(self._ZOOM_MAX_SCALE, self._ZOOM_TARGET_SIZE / largest)
        if scale <= 1.05:
            return None
        target_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
        interpolation = cv2.INTER_CUBIC if scale >= 1.0 else cv2.INTER_AREA
        return cv2.resize(crop, target_size, interpolation=interpolation), roi

    @classmethod
    def _face_roi_for_zoom(
        cls,
        face_box: tuple[int, int, int, int] | None,
        width: int,
        height: int,
    ) -> tuple[int, int, int, int] | None:
        if face_box is None or width <= 0 or height <= 0:
            return None
        x, y, w, h = face_box
        if w <= 0 or h <= 0:
            return None

        center_x = x + w * 0.5
        center_y = y + h * 0.48
        side = max(w, h) * (1.0 + cls._ZOOM_PADDING_RATIO * 2.0)
        side = min(max(side, 96.0), float(max(width, height)))
        x0 = int(round(center_x - side * 0.5))
        y0 = int(round(center_y - side * 0.5))
        x0 = max(0, min(width - 1, x0))
        y0 = max(0, min(height - 1, y0))
        x1 = max(x0 + 1, min(width, int(round(x0 + side))))
        y1 = max(y0 + 1, min(height, int(round(y0 + side))))
        return (x0, y0, x1 - x0, y1 - y0)

    @staticmethod
    def _remap_landmarks_from_roi(
        landmarks: Any,
        roi: tuple[int, int, int, int],
        frame_width: int,
        frame_height: int,
    ) -> list[Any]:
        x, y, w, h = roi
        frame_width = max(1, int(frame_width))
        frame_height = max(1, int(frame_height))
        z_scale = w / frame_width
        return [
            SimpleNamespace(
                x=(x + float(landmark.x) * w) / frame_width,
                y=(y + float(landmark.y) * h) / frame_height,
                z=float(getattr(landmark, "z", 0.0)) * z_scale,
            )
            for landmark in landmarks
        ]

    def _gaze_from_zoom(
        self,
        zoom: _ZoomLandmarks,
        width: int,
        height: int,
        *,
        source: str = "iris-zoom",
    ):
        zoom_width, zoom_height = zoom.zoom_size
        zoom_gaze = estimate_iris_gaze(zoom.roi_landmarks, zoom_width, zoom_height)
        original_gaze = estimate_iris_gaze(zoom.original_landmarks, width, height)

        def remap_point(point: tuple[int, int] | None) -> tuple[int, int] | None:
            if point is None:
                return None
            x, y, w, h = zoom.roi
            return (
                int(round(x + point[0] * (w / max(zoom_width, 1)))),
                int(round(y + point[1] * (h / max(zoom_height, 1)))),
            )

        zoom_gaze.source = source
        zoom_gaze.normalized_x = original_gaze.normalized_x
        zoom_gaze.normalized_y = original_gaze.normalized_y
        zoom_gaze.eye_span = original_gaze.eye_span
        zoom_gaze.distance_scale = original_gaze.distance_scale
        zoom_gaze.left_iris = remap_point(zoom_gaze.left_iris)
        zoom_gaze.right_iris = remap_point(zoom_gaze.right_iris)
        zoom_gaze.left_eye_center = remap_point(zoom_gaze.left_eye_center)
        zoom_gaze.right_eye_center = remap_point(zoom_gaze.right_eye_center)
        metadata = self._tracking_metadata(self._landmark_box(zoom.original_landmarks, width, height), width, height, zoom.original_landmarks)
        self._apply_distance_metadata_to_gaze(zoom_gaze, metadata)
        return zoom_gaze

    @classmethod
    def _should_try_face_zoom(cls, gaze: Any, metadata: dict[str, Any]) -> bool:
        return (
            float(getattr(gaze, "confidence", 0.0)) < cls._IRIS_ZOOM_CONFIDENCE_TRIGGER
            or float(metadata.get("face_size_normalized") or 0.0) < cls._FACE_ZOOM_SIZE_TRIGGER
        )

    @staticmethod
    def _is_zoom_gaze_better(zoom_gaze: Any, current_gaze: Any) -> bool:
        return (
            zoom_gaze.confidence >= current_gaze.confidence + 0.03
            or (current_gaze.confidence < 0.24 and zoom_gaze.confidence > current_gaze.confidence)
        )

    @staticmethod
    def _apply_distance_metadata_to_gaze(gaze: Any, metadata: dict[str, Any]) -> None:
        face_size = float(metadata.get("face_size_normalized") or 0.0)
        if face_size > 0.0:
            gaze.face_size_normalized = face_size
        if float(getattr(gaze, "eye_span", 0.0) or 0.0) <= 0.001 and face_size > 0.0:
            gaze.distance_scale = 1.0 / face_size

    def _next_timestamp_ms(self) -> int:
        now = int(time.monotonic() * 1000)
        if now <= self._last_timestamp_ms:
            now = self._last_timestamp_ms + 1
        self._last_timestamp_ms = now
        return now

    def _solve_head_pose(self, landmarks: Any, width: int, height: int) -> PoseSample:
        landmark_ids = [1, 152, 33, 263, 61, 291]
        image_points = np.array(
            [[landmarks[idx].x * width, landmarks[idx].y * height] for idx in landmark_ids],
            dtype=np.float64,
        )
        camera_matrix, dist_coeffs = self._camera_parameters(width, height)

        try:
            rotation_vector = None if self._last_rotation_vector is None else self._last_rotation_vector.copy()
            translation_vector = None if self._last_translation_vector is None else self._last_translation_vector.copy()
            success, rotation_vector, translation_vector = cv2.solvePnP(
                self._model_points,
                image_points,
                camera_matrix,
                dist_coeffs,
                rvec=rotation_vector,
                tvec=translation_vector,
                useExtrinsicGuess=rotation_vector is not None and translation_vector is not None,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not success:
                return PoseSample()

            self._last_rotation_vector = rotation_vector
            self._last_translation_vector = translation_vector
            rotation_matrix, _jacobian = cv2.Rodrigues(rotation_vector)
            angles = cv2.RQDecomp3x3(rotation_matrix)[0]
            pitch, yaw, roll = (float(angles[0]), float(angles[1]), float(angles[2]))
            yaw = self._blend_pnp_and_landmark_yaw(yaw, self._estimate_landmark_yaw(landmarks))
            return PoseSample(
                yaw=self._wrap_angle(yaw),
                pitch=self._normalize_pitch(pitch),
                roll=self._wrap_angle(roll),
                x=float(translation_vector[0][0]) / 10.0,
                y=-float(translation_vector[1][0]) / 10.0,
                z=-float(translation_vector[2][0]) / 10.0,
            )
        except cv2.error:
            return PoseSample()

    @classmethod
    def _blend_pnp_and_landmark_yaw(cls, pnp_yaw: float, landmark_yaw: float | None) -> float:
        if landmark_yaw is None:
            return pnp_yaw
        pnp_yaw = cls._wrap_angle(pnp_yaw)
        landmark_yaw = cls._wrap_angle(landmark_yaw)
        delta = cls._wrap_angle(landmark_yaw - pnp_yaw)
        return cls._wrap_angle(pnp_yaw + delta * cls._LANDMARK_YAW_BLEND)

    @classmethod
    def _estimate_landmark_yaw(cls, landmarks: Any) -> float | None:
        try:
            nose = landmarks[1]
            eye_a = landmarks[33]
            eye_b = landmarks[263]
            mouth_a = landmarks[61]
            mouth_b = landmarks[291]
            eye_width = abs(float(eye_b.x) - float(eye_a.x))
            mouth_width = abs(float(mouth_b.x) - float(mouth_a.x))
            if eye_width <= 0.001:
                return None

            eye_mid_x = (float(eye_a.x) + float(eye_b.x)) * 0.5
            nose_eye_offset = (float(nose.x) - eye_mid_x) / eye_width

            offset = nose_eye_offset
            if mouth_width > 0.001:
                mouth_mid_x = (float(mouth_a.x) + float(mouth_b.x)) * 0.5
                nose_mouth_offset = (float(nose.x) - mouth_mid_x) / mouth_width
                offset = (nose_eye_offset * 0.65) + (nose_mouth_offset * 0.35)

            nose_yaw = -offset * cls._LANDMARK_NOSE_YAW_SCALE
            depth_yaw = ((float(eye_a.z) - float(eye_b.z)) / eye_width) * cls._LANDMARK_DEPTH_YAW_SCALE
            yaw = (nose_yaw * 0.65) + (depth_yaw * 0.35)
            return float(max(-cls._LANDMARK_YAW_LIMIT, min(cls._LANDMARK_YAW_LIMIT, yaw)))
        except (AttributeError, IndexError, TypeError, ValueError):
            return None

    def _camera_parameters(self, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
        size = (int(width), int(height))
        if self._camera_matrix is not None and self._camera_matrix_size == size:
            return self._camera_matrix, self._dist_coeffs

        focal_length = float(width)
        self._camera_matrix = np.array(
            [
                [focal_length, 0.0, width / 2.0],
                [0.0, focal_length, height / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        self._camera_matrix_size = size
        return self._camera_matrix, self._dist_coeffs

    def _detect_with_haar(self, frame_bgr: np.ndarray) -> TrackingResult:
        if not self._frontal_cascades:
            return TrackingResult(detected=False, method="OpenCV Haar fallback")

        height, width = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        eye_gray = self._clahe.apply(gray)
        face_box = self._detect_face_box(gray)
        method = "OpenCV Haar/profile fallback"

        if face_box is None:
            tracked = self._track_last_face(frame_bgr)
            if tracked is None:
                return TrackingResult(detected=False, method=method)
            face_box = tracked
            method = "OpenCV CSRT tracker fallback"
        else:
            self._init_box_tracker(frame_bgr, face_box)

        x, y, w, h = face_box
        center_x = x + w / 2.0
        center_y = y + h / 2.0
        yaw = ((center_x - width / 2.0) / max(width / 2.0, 1.0)) * 30.0
        pitch = -((center_y - height / 2.0) / max(height / 2.0, 1.0)) * 20.0
        eye_boxes = self._detect_eye_boxes(eye_gray, x, y, w, h)
        roll = self._estimate_roll_from_eye_boxes(eye_boxes) if eye_boxes else self._last_pose.roll
        pose = self._stabilize_pose(PoseSample(yaw=yaw, pitch=pitch, roll=roll))
        self._last_face_box = (int(x), int(y), int(w), int(h))

        return TrackingResult(
            detected=True,
            pose=pose,
            method=method,
            face_box=self._last_face_box,
            frame_size=(width, height),
            **self._tracking_metadata(self._last_face_box, width, height),
            eye_boxes=eye_boxes,
        )

    def _detect_face_box(self, gray: np.ndarray) -> Optional[tuple[int, int, int, int]]:
        height, width = gray.shape[:2]
        min_size = (max(48, width // 20), max(48, height // 20))
        candidates: list[tuple[int, int, int, int]] = []
        search_variants = self._face_search_variants(gray)

        for search_gray, scale in search_variants:
            scaled_min_size = (
                max(32, int(round(min_size[0] * scale))),
                max(32, int(round(min_size[1] * scale))),
            )
            candidates.extend(self._detect_with_cascades(search_gray, scale, scaled_min_size))

        if self._profile_cascade is not None and not self._profile_cascade.empty():
            for search_gray, scale in search_variants:
                scaled_min_size = (
                    max(32, int(round(min_size[0] * scale))),
                    max(32, int(round(min_size[1] * scale))),
                )
                flipped = cv2.flip(search_gray, 1)
                boxes = self._profile_cascade.detectMultiScale(
                    flipped,
                    scaleFactor=1.05,
                    minNeighbors=2,
                    minSize=scaled_min_size,
                )
                variant_width = flipped.shape[1]
                for x, y, w, h in boxes:
                    candidates.append(
                        (
                            int(round((variant_width - x - w) / scale)),
                            int(round(y / scale)),
                            int(round(w / scale)),
                            int(round(h / scale)),
                        )
                    )

        if not candidates:
            return None
        box = self._clip_box(self._choose_best_box(candidates), width, height)
        if not self._is_plausible_detection(box):
            return None
        return box

    def _face_search_variants(self, gray: np.ndarray) -> list[tuple[np.ndarray, float]]:
        variants = [
            (gray, 1.0),
            (cv2.equalizeHist(gray), 1.0),
            (self._clahe.apply(gray), 1.0),
        ]
        height, width = gray.shape[:2]
        if width < 900 and height < 900:
            upscale = 1.35
            interpolation = cv2.INTER_CUBIC
            variants.extend(
                (
                    cv2.resize(image, None, fx=upscale, fy=upscale, interpolation=interpolation),
                    upscale,
                )
                for image, _scale in variants[:3]
            )
        return variants

    def _detect_with_cascades(
        self,
        gray: np.ndarray,
        scale: float,
        min_size: tuple[int, int],
    ) -> list[tuple[int, int, int, int]]:
        candidates: list[tuple[int, int, int, int]] = []
        for cascade in self._frontal_cascades:
            boxes = cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=min_size,
            )
            for x, y, w, h in boxes:
                candidates.append(
                    (
                        int(round(x / scale)),
                        int(round(y / scale)),
                        int(round(w / scale)),
                        int(round(h / scale)),
                    )
                )
        return candidates

    @staticmethod
    def _clip_box(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
        x, y, w, h = box
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        w = max(1, min(width - x, w))
        h = max(1, min(height - y, h))
        return (x, y, w, h)

    def _choose_best_box(self, boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
        if self._last_face_box is None:
            return max(boxes, key=lambda item: item[2] * item[3])

        last_cx = self._last_face_box[0] + self._last_face_box[2] / 2.0
        last_cy = self._last_face_box[1] + self._last_face_box[3] / 2.0

        def score(box: tuple[int, int, int, int]) -> float:
            x, y, w, h = box
            cx = x + w / 2.0
            cy = y + h / 2.0
            distance = math.hypot(cx - last_cx, cy - last_cy)
            return (w * h) - distance * 8.0

        return max(boxes, key=score)

    def _is_plausible_detection(self, box: tuple[int, int, int, int]) -> bool:
        x, y, w, h = box
        if w <= 0 or h <= 0:
            return False
        aspect = w / max(h, 1)
        if aspect < 0.45 or aspect > 1.8:
            return False

        if self._last_face_box is None:
            return True

        last_x, last_y, last_w, last_h = self._last_face_box
        cx = x + w / 2.0
        cy = y + h / 2.0
        last_cx = last_x + last_w / 2.0
        last_cy = last_y + last_h / 2.0
        distance = math.hypot(cx - last_cx, cy - last_cy)
        allowed = max(last_w, last_h, w, h) * 1.8
        return distance <= allowed

    def _init_box_tracker(self, frame_bgr: np.ndarray, box: tuple[int, int, int, int]) -> None:
        tracker = self._create_box_tracker()
        if tracker is None:
            return
        try:
            tracker.init(frame_bgr, tuple(float(value) for value in box))
            self._box_tracker = tracker
            self._tracker_misses = 0
        except cv2.error:
            self._box_tracker = None

    def _track_last_face(self, frame_bgr: np.ndarray) -> Optional[tuple[int, int, int, int]]:
        if self._box_tracker is None:
            return None

        try:
            ok, box = self._box_tracker.update(frame_bgr)
        except cv2.error:
            ok = False
            box = None

        if not ok or box is None:
            self._tracker_misses += 1
            if self._tracker_misses > self._max_tracker_misses:
                self._box_tracker = None
                self._last_face_box = None
            return self._last_face_box if self._tracker_misses <= self._max_tracker_misses else None

        self._tracker_misses = 0
        x, y, w, h = (int(round(value)) for value in box)
        frame_h, frame_w = frame_bgr.shape[:2]
        x = max(0, min(frame_w - 1, x))
        y = max(0, min(frame_h - 1, y))
        w = max(1, min(frame_w - x, w))
        h = max(1, min(frame_h - y, h))
        self._last_face_box = (x, y, w, h)
        return self._last_face_box

    @staticmethod
    def _create_box_tracker() -> Optional[Any]:
        for factory in (
            getattr(cv2, "TrackerCSRT_create", None),
            getattr(cv2, "TrackerKCF_create", None),
            getattr(getattr(cv2, "legacy", None), "TrackerCSRT_create", None),
            getattr(getattr(cv2, "legacy", None), "TrackerKCF_create", None),
        ):
            if factory is None:
                continue
            try:
                return factory()
            except cv2.error:
                continue
        return None

    def _estimate_roll_from_eye_boxes(self, boxes: list[tuple[int, int, int, int]]) -> float:
        if len(boxes) < 2:
            return 0.0
        boxes = sorted(boxes, key=lambda box: box[0])[:2]
        left = boxes[0]
        right = boxes[1]
        left_center = (left[0] + left[2] / 2.0, left[1] + left[3] / 2.0)
        right_center = (right[0] + right[2] / 2.0, right[1] + right[3] / 2.0)
        return math.degrees(math.atan2(right_center[1] - left_center[1], right_center[0] - left_center[0]))

    def _detect_eye_boxes(self, gray: np.ndarray, x: int, y: int, w: int, h: int) -> list[tuple[int, int, int, int]]:
        if self._eye_cascade is None or self._eye_cascade.empty():
            return []

        roi = gray[y : y + h, x : x + w]
        eyes = self._eye_cascade.detectMultiScale(roi, scaleFactor=1.1, minNeighbors=8, minSize=(20, 20))
        boxes: list[tuple[int, int, int, int]] = []
        for ex, ey, ew, eh in eyes[:4]:
            boxes.append((int(x + ex), int(y + ey), int(ew), int(eh)))
        return boxes

    @staticmethod
    def _points_for_indices(landmarks: Any, width: int, height: int, indices: list[int]) -> list[tuple[int, int]]:
        return [(int(landmarks[idx].x * width), int(landmarks[idx].y * height)) for idx in indices]

    @staticmethod
    def _landmark_box(landmarks: Any, width: int, height: int) -> tuple[int, int, int, int]:
        xs = [lm.x * width for lm in landmarks]
        ys = [lm.y * height for lm in landmarks]
        x0 = max(0, int(min(xs)))
        y0 = max(0, int(min(ys)))
        x1 = min(width - 1, int(max(xs)))
        y1 = min(height - 1, int(max(ys)))
        return (x0, y0, max(0, x1 - x0), max(0, y1 - y0))

    @classmethod
    def _tracking_metadata(
        cls,
        face_box: tuple[int, int, int, int] | None,
        width: int,
        height: int,
        landmarks: Any | None = None,
    ) -> dict[str, Any]:
        if face_box is None or width <= 0 or height <= 0:
            return {
                "face_center_normalized": None,
                "face_size_normalized": 0.0,
                "user_distance": 0.0,
            }

        x, y, w, h = face_box
        face_size = math.sqrt(max(w, 0) * max(h, 0)) / max(math.sqrt(width * height), 1.0)
        face_size = max(0.0, min(1.0, face_size))
        landmark_span = cls._interocular_span(landmarks) if landmarks is not None else 0.0
        distance = (1.0 / landmark_span) if landmark_span > 0.001 else (1.0 / face_size if face_size > 0.001 else 0.0)
        return {
            "face_center_normalized": (
                max(0.0, min(1.0, (x + w * 0.5) / max(width, 1))),
                max(0.0, min(1.0, (y + h * 0.5) / max(height, 1))),
            ),
            "face_size_normalized": face_size,
            "user_distance": distance,
        }

    @staticmethod
    def _interocular_span(landmarks: Any | None) -> float:
        if landmarks is None:
            return 0.0
        try:
            left = landmarks[33]
            right = landmarks[263]
            return math.hypot(float(right.x) - float(left.x), float(right.y) - float(left.y))
        except (AttributeError, IndexError, TypeError, ValueError):
            return 0.0

    def _mark_detection_lost(self) -> None:
        self._missed_detections += 1
        if self._missed_detections < self._TRACKING_RESET_MISSED_DETECTIONS:
            return
        self._last_rotation_vector = None
        self._last_translation_vector = None
        self._last_face_box = None
        self._box_tracker = None
        if self._missed_detections < self._POSE_RESET_MISSED_DETECTIONS:
            return
        self._last_pose = PoseSample()
        self._has_last_pose = False
        self._last_pose_timestamp = None

    def _stabilize_pose(self, pose: PoseSample) -> PoseSample:
        now = time.monotonic()
        delta_seconds = None if self._last_pose_timestamp is None else max(0.0, now - self._last_pose_timestamp)
        self._last_pose_timestamp = now
        pose = PoseSample(
            yaw=self._wrap_angle(pose.yaw),
            pitch=self._normalize_pitch(pose.pitch),
            roll=self._wrap_angle(pose.roll),
            x=pose.x,
            y=pose.y,
            z=pose.z,
        )
        if not self._has_last_pose:
            self._last_pose = pose
            self._has_last_pose = True
            return pose

        stabilized = PoseSample(
            yaw=self._guard_axis(
                pose.yaw,
                self._last_pose.yaw,
                jitter=0.18,
                max_step=self._YAW_MAX_STEP_PER_FRAME,
            ),
            pitch=self._guard_axis(pose.pitch, self._last_pose.pitch, jitter=0.18, max_step=self._scaled_step(10.0, delta_seconds)),
            roll=self._guard_axis(pose.roll, self._last_pose.roll, jitter=0.15, max_step=self._scaled_step(10.0, delta_seconds)),
            x=self._guard_axis(pose.x, self._last_pose.x, jitter=0.05, max_step=self._scaled_step(1.25, delta_seconds)),
            y=self._guard_axis(pose.y, self._last_pose.y, jitter=0.05, max_step=self._scaled_step(1.25, delta_seconds)),
            z=self._guard_axis(pose.z, self._last_pose.z, jitter=0.07, max_step=self._scaled_step(1.75, delta_seconds)),
        )
        if getattr(self, "_pose_ema_enabled", False):
            stabilized = self._adaptive_ema_pose(stabilized, self._last_pose, delta_seconds)
        self._last_pose = stabilized
        return stabilized

    @staticmethod
    def _guard_axis(value: float, previous: float, jitter: float, max_step: float) -> float:
        delta = value - previous
        if abs(delta) <= jitter:
            if jitter <= 0.0:
                return value
            blend = 0.30 + 0.70 * (abs(delta) / jitter)
            return previous + delta * blend
        if abs(delta) > max_step:
            return previous + math.copysign(max_step, delta)
        return value

    @classmethod
    def _adaptive_ema_pose(
        cls,
        target: PoseSample,
        previous: PoseSample,
        delta_seconds: float | None,
    ) -> PoseSample:
        return PoseSample(
            yaw=cls._adaptive_ema_axis(target.yaw, previous.yaw, delta_seconds, slow_alpha=0.46, fast_alpha=0.88),
            pitch=cls._adaptive_ema_axis(target.pitch, previous.pitch, delta_seconds, slow_alpha=0.48, fast_alpha=0.90),
            roll=cls._adaptive_ema_axis(target.roll, previous.roll, delta_seconds, slow_alpha=0.42, fast_alpha=0.82),
            x=cls._adaptive_ema_axis(target.x, previous.x, delta_seconds, slow_alpha=0.50, fast_alpha=0.86),
            y=cls._adaptive_ema_axis(target.y, previous.y, delta_seconds, slow_alpha=0.50, fast_alpha=0.86),
            z=cls._adaptive_ema_axis(target.z, previous.z, delta_seconds, slow_alpha=0.48, fast_alpha=0.84),
        )

    @classmethod
    def _adaptive_ema_axis(
        cls,
        value: float,
        previous: float,
        delta_seconds: float | None,
        *,
        slow_alpha: float,
        fast_alpha: float,
    ) -> float:
        delta = abs(float(value) - float(previous))
        velocity = delta / max(delta_seconds or (1.0 / 60.0), 1.0 / 240.0)
        velocity_factor = velocity / (velocity + 22.0)
        alpha = slow_alpha + (fast_alpha - slow_alpha) * max(0.0, min(1.0, velocity_factor))
        alpha = cls._time_adjusted_alpha(alpha, delta_seconds)
        return previous + (value - previous) * alpha

    @staticmethod
    def _time_adjusted_alpha(alpha: float, delta_seconds: float | None) -> float:
        alpha = max(0.001, min(1.0, float(alpha)))
        if delta_seconds is None:
            return alpha
        scale = min(max(float(delta_seconds) * 60.0, 0.25), 6.0)
        return max(0.001, min(1.0, 1.0 - ((1.0 - alpha) ** scale)))

    @staticmethod
    def _scaled_step(base_step: float, delta_seconds: float | None) -> float:
        if delta_seconds is None:
            return base_step
        scale = min(max(delta_seconds * 60.0, 0.25), 6.0)
        return base_step * scale

    @staticmethod
    def _wrap_angle(value: float) -> float:
        wrapped = (float(value) + 180.0) % 360.0 - 180.0
        return 180.0 if math.isclose(wrapped, -180.0) else wrapped

    @classmethod
    def _normalize_pitch(cls, value: float) -> float:
        pitch = cls._wrap_angle(value)
        if pitch < -90.0:
            pitch += 180.0
        elif pitch > 90.0:
            pitch -= 180.0
        return pitch
