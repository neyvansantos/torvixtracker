from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from eye_drive_tracker.filters.extended_view import curve_points
from eye_drive_tracker.profiles.profile import TrackingConfig


class CurveWidget(QWidget):
    def __init__(self, config: TrackingConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setMinimumHeight(150)

    def set_config(self, config: TrackingConfig) -> None:
        self.config = config
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.fillRect(self.rect(), QColor("#fbfbf8"))
        painter.setPen(QPen(QColor("#d7d8d1"), 1))
        painter.drawRect(rect)

        painter.setPen(QPen(QColor("#e5e6df"), 1))
        for index in range(1, 4):
            x = rect.left() + rect.width() * index / 4
            y = rect.top() + rect.height() * index / 4
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        points = list(curve_points(self.config, count=120))
        if not points:
            return

        path = QPainterPath()
        for index, (x_value, y_value) in enumerate(points):
            point = QPointF(
                rect.left() + x_value * rect.width(),
                rect.bottom() - y_value * rect.height(),
            )
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)

        painter.setPen(QPen(QColor("#1f7a5c"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

        painter.setPen(QPen(QColor("#777b73"), 1, Qt.DashLine))
        start_x = rect.left() + self.config.extended_view_start_point * rect.width()
        end_x = rect.left() + self.config.extended_view_end_point * rect.width()
        inflect_x = rect.left() + self.config.extended_view_inflection_point * rect.width()
        painter.drawLine(int(start_x), rect.top(), int(start_x), rect.bottom())
        painter.drawLine(int(end_x), rect.top(), int(end_x), rect.bottom())
        painter.drawLine(int(inflect_x), rect.top(), int(inflect_x), rect.bottom())
