# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QSlider, QToolButton, QWidget


class FloatSlider(QWidget):
    valueChanged = Signal(float)

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        decimals: int = 2,
        step: float = 0.01,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._factor = 10**decimals
        self._minimum = minimum
        self._maximum = maximum

        self.label = QLabel(label)
        self.help_button = QToolButton()
        self.help_button.setObjectName("helpIconButton")
        self.help_button.setText("?")
        self.help_button.setCursor(Qt.PointingHandCursor)
        self.help_button.setFixedSize(18, 18)
        self.help_button.setFocusPolicy(Qt.NoFocus)
        self.help_button.hide()

        self.label_container = QWidget()
        self.label_container.setMinimumWidth(245)
        self.label_row = QHBoxLayout(self.label_container)
        self.label_row.setContentsMargins(0, 0, 0, 0)
        self.label_row.setSpacing(6)
        self.label_row.addWidget(self.label)
        self.label_row.addWidget(self.help_button)
        self.label_row.addStretch(1)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(self._to_slider(minimum), self._to_slider(maximum))
        self.slider.setSingleStep(max(1, self._to_slider(step)))

        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step)
        self.spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin.setMinimumWidth(86)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.label_container)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spin.valueChanged.connect(self._on_spin_changed)
        self.set_value(value)

    def value(self) -> float:
        return self.spin.value()

    def set_value(self, value: float) -> None:
        bounded = max(self._minimum, min(self._maximum, float(value)))
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(bounded)
        self.slider.setValue(self._to_slider(bounded))
        self.slider.blockSignals(False)
        self.spin.blockSignals(False)

    def set_help_tooltip(self, text: str) -> None:
        tooltip = str(text or "").strip()
        self.help_button.setToolTip(tooltip)
        self.help_button.setVisible(bool(tooltip))

    def _on_slider_changed(self, slider_value: int) -> None:
        value = self._from_slider(slider_value)
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self.valueChanged.emit(value)

    def _on_spin_changed(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(self._to_slider(value))
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)

    def _to_slider(self, value: float) -> int:
        return int(round(value * self._factor))

    def _from_slider(self, value: int) -> float:
        return value / self._factor
