from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout

from eye_drive_tracker.camera import CameraEnumerator
from eye_drive_tracker.profiles import TrackingConfig

from .i18n import translate


class CameraSettingsDialog(QDialog):
    def __init__(self, config: TrackingConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.language = config.language
        self.setWindowTitle(self._tr("Camera settings"))
        self.resize(420, 180)

        self.resolution_combo = QComboBox()
        self.fps_combo = QComboBox()
        self.status_label = QLabel("")
        self.refresh_button = QPushButton(self._tr("Refresh modes"))
        self.refresh_button.clicked.connect(self._load_resolutions)

        form = QFormLayout()
        form.addRow(self._tr("Resolution"), self.resolution_combo)
        form.addRow(self._tr("FPS"), self.fps_combo)
        form.addRow("", self.refresh_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addWidget(buttons)

        self.resolution_combo.currentIndexChanged.connect(self._load_fps)
        self._load_resolutions()

    @property
    def selected_width(self) -> int:
        width, _height = self.resolution_combo.currentData() or (0, 0)
        return int(width)

    @property
    def selected_height(self) -> int:
        _width, height = self.resolution_combo.currentData() or (0, 0)
        return int(height)

    @property
    def selected_fps(self) -> float:
        return float(self.fps_combo.currentData() or 0.0)

    def _tr(self, key: str) -> str:
        return translate(self.language, key)

    def _load_resolutions(self) -> None:
        self.resolution_combo.blockSignals(True)
        self.resolution_combo.clear()
        self.resolution_combo.addItem(self._tr("Auto"), (0, 0))

        resolutions = CameraEnumerator.list_resolutions(self.config.camera_index)
        for resolution in resolutions:
            self.resolution_combo.addItem(resolution.label, (resolution.width, resolution.height))

        target = (self.config.camera_width, self.config.camera_height)
        index = self.resolution_combo.findData(target)
        self.resolution_combo.setCurrentIndex(index if index >= 0 else 0)
        self.resolution_combo.blockSignals(False)

        if resolutions:
            self.status_label.setText(self._tr("Detected camera modes"))
        else:
            self.status_label.setText(self._tr("No camera modes detected"))
        self._load_fps()

    def _load_fps(self) -> None:
        width, height = self.resolution_combo.currentData() or (0, 0)
        self.fps_combo.clear()
        self.fps_combo.addItem(self._tr("Auto"), 0.0)

        for fps in CameraEnumerator.list_fps(self.config.camera_index, width, height):
            label = f"{fps:g} FPS"
            self.fps_combo.addItem(label, fps)

        index = self.fps_combo.findData(float(self.config.camera_fps))
        self.fps_combo.setCurrentIndex(index if index >= 0 else 0)
