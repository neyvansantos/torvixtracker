from __future__ import annotations

import math
from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QStackedWidget, QWidget, QHBoxLayout,
    QMessageBox, QSizePolicy,
)
from eye_drive_tracker.tracking import PoseSample

# Minimum number of valid pose samples required per calibration step.
MIN_SAMPLES = 15
# Duration of the recording phase in milliseconds.
RECORD_DURATION_MS = 3500


class _CountdownWidget(QWidget):
    """Circular SVG-style countdown timer drawn with QPainter."""

    def __init__(self, total_ms: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._total_ms = max(1, total_ms)
        self._elapsed_ms = 0
        self._sample_count = 0
        self.setFixedSize(140, 140)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def update_state(self, elapsed_ms: int, sample_count: int) -> None:
        self._elapsed_ms = elapsed_ms
        self._sample_count = sample_count
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(10, 10, 120, 120)
        progress = min(1.0, self._elapsed_ms / self._total_ms)
        remaining_s = max(0.0, (self._total_ms - self._elapsed_ms) / 1000.0)

        # Background ring
        bg_pen = QPen(QColor("#1E1E1E"), 8)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Progress arc (cyan)
        arc_pen = QPen(QColor("#00F2FF"), 8)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        span = -int(progress * 360 * 16)  # QPainter uses 1/16th degrees
        painter.drawArc(rect, 90 * 16, span)

        # Center text — remaining seconds
        painter.setPen(QColor("#FFFFFF"))
        font_big = QFont("Segoe UI", 28, QFont.Bold)
        painter.setFont(font_big)
        painter.drawText(QRectF(10, 20, 120, 70), Qt.AlignCenter, f"{remaining_s:.1f}")

        # Sub-text — sample count
        painter.setPen(QColor("#888888"))
        font_small = QFont("Segoe UI", 8)
        painter.setFont(font_small)
        painter.drawText(QRectF(10, 80, 120, 40), Qt.AlignCenter, f"{self._sample_count} amostras")


class CalibrationWizard(QDialog):
    """Step-by-step auto-calibration wizard.

    Emits ``finished_calibration`` with a result dict on success.
    """

    finished_calibration = Signal(dict)

    # Step definitions: (title, description, result_key_hint)
    _STEPS = [
        (
            "Passo 1: Posição Central",
            "Olhe diretamente para o centro do monitor numa posição confortável.\n"
            "Isso define o seu 'Ponto Zero'.",
            "center",
        ),
        (
            "Passo 2: Amplitude Horizontal",
            "Vire a cabeça lentamente para a esquerda e depois para a direita "
            "até onde for confortável ao olhar os retrovisores.",
            "yaw",
        ),
        (
            "Passo 3: Amplitude Vertical",
            "Olhe para cima e para baixo "
            "(ex: para o painel do caminhão e para o para-sol).",
            "pitch",
        ),
        (
            "Passo 4: Estabilidade",
            "Mantenha a cabeça o mais parada possível por alguns segundos.\n"
            "Isso calibrará o filtro de tremor da câmera.",
            "noise",
        ),
    ]

    def __init__(self, is_tracking_active: bool, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Calibrar ⚡ — Torvix Tracker")
        self.setFixedSize(520, 440)
        self.setWindowModality(Qt.WindowModal)

        self._is_tracking_active = is_tracking_active
        self.samples: list[PoseSample] = []
        self.current_step = 0  # 0 = intro; 1..4 = calibration steps
        self.is_recording = False
        self.results: dict = {}

        # Countdown timer state
        self._elapsed_ms = 0
        self._tick_interval_ms = 50

        self._record_timer = QTimer(self)
        self._record_timer.setInterval(self._tick_interval_ms)
        self._record_timer.timeout.connect(self._on_tick)

        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # Progress bar (steps 0–4)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self._STEPS))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        root.addWidget(self.progress_bar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_intro_page())
        for title, desc, _ in self._STEPS:
            self.stack.addWidget(self._create_step_page(title, desc))
        root.addWidget(self.stack)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_back = QPushButton("← Voltar")
        self.btn_back.setObjectName("backButton")
        self.btn_back.clicked.connect(self._prev_step)
        self.btn_back.setEnabled(False)

        self.btn_next = QPushButton("Iniciar")
        self.btn_next.setObjectName("primaryButton")
        self.btn_next.clicked.connect(self._next_step)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_back)
        btn_row.addWidget(self.btn_next)
        root.addLayout(btn_row)

    def _create_intro_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        title = QLabel("Assistente de Calibração Automática")
        title.setObjectName("wizardTitle")

        desc = QLabel(
            "Este assistente configura automaticamente o Torvix Tracker "
            "para o seu rosto e ambiente.\n\n"
            "Serão <b>4 passos</b> de ~3,5 segundos cada.\n\n"
            "⚡ Certifique-se de que o tracking está ativo e seu rosto está detectado "
            "antes de iniciar cada passo."
        )
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.RichText)
        desc.setObjectName("wizardDesc")

        if not self._is_tracking_active:
            warn = QLabel("⚠️  O tracking não está ativo! Inicie a câmera primeiro.")
            warn.setObjectName("warnLabel")
            layout.addWidget(warn)

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def _create_step_page(self, title_text: str, desc_text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("stepTitle")

        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setObjectName("stepDesc")

        # Countdown widget (shown only while recording)
        countdown = _CountdownWidget(RECORD_DURATION_MS)
        countdown.setVisible(False)

        # Status label
        status = QLabel("▶  Pronto — clique em Capturar para iniciar")
        status.setAlignment(Qt.AlignCenter)
        status.setObjectName("statusLabel")

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        layout.addWidget(countdown, alignment=Qt.AlignCenter)
        layout.addWidget(status)
        layout.addStretch()

        # Store references on page for easy retrieval
        page._countdown = countdown  # type: ignore[attr-defined]
        page._status = status  # type: ignore[attr-defined]
        return page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _next_step(self) -> None:
        if self.is_recording:
            return

        if self.current_step == 0:
            # Intro → first step
            if not self._is_tracking_active:
                QMessageBox.warning(
                    self,
                    "Tracking inativo",
                    "O tracking de cabeça não está ativo.\n"
                    "Inicie a câmera na janela principal antes de calibrar.",
                )
                self.reject()
                return
            self._go_to_step(1)
        else:
            self._start_recording()

    def _prev_step(self) -> None:
        if self.is_recording:
            return
        if self.current_step > 1:
            self._go_to_step(self.current_step - 1)
        elif self.current_step == 1:
            self._go_to_step(0)

    def _go_to_step(self, step: int) -> None:
        self.current_step = step
        self.stack.setCurrentIndex(step)
        self.progress_bar.setValue(step)

        self.btn_back.setEnabled(step > 0)
        # Garante que o botão principal nunca fica preso como desabilitado
        # ao avançar de passo (pode ter sido desabilitado durante gravação).
        self.btn_next.setEnabled(True)

        if step == 0:
            self.btn_next.setText("Iniciar")
        elif step <= len(self._STEPS):
            label = "Capturar Centro" if step == 1 else f"Capturar Passo {step}"
            self.btn_next.setText(label)

        if step > 0:
            self._reset_step_ui(step)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _start_recording(self) -> None:
        self.is_recording = True
        self.samples = []
        self._elapsed_ms = 0

        self.btn_next.setEnabled(False)
        self.btn_back.setEnabled(False)

        page = self.stack.currentWidget()
        page._countdown.update_state(0, 0)
        page._countdown.setVisible(True)
        page._status.setText("🔴  Capturando…")

        self._record_timer.start()

    def _on_tick(self) -> None:
        self._elapsed_ms += self._tick_interval_ms
        page = self.stack.currentWidget()
        page._countdown.update_state(self._elapsed_ms, len(self.samples))

        if self._elapsed_ms >= RECORD_DURATION_MS:
            self._record_timer.stop()
            self._stop_recording()

    def _stop_recording(self) -> None:
        self.is_recording = False
        page = self.stack.currentWidget()
        page._countdown.setVisible(False)

        sample_count = len(self.samples)

        if sample_count < MIN_SAMPLES:
            page._status.setText(
                f"⚠️  Apenas {sample_count} amostra(s) capturada(s) — face não detectada!\n"
                "Verifique o tracking e tente novamente."
            )
            self.btn_next.setEnabled(True)
            self.btn_back.setEnabled(self.current_step > 1)
            QMessageBox.warning(
                self,
                "Poucas amostras",
                f"Só {sample_count} amostra(s) foram capturadas (mínimo: {MIN_SAMPLES}).\n\n"
                "Certifique-se de que seu rosto está bem iluminado e visível para a câmera, "
                "então repita este passo.",
            )
            return

        # Process and advance
        self._process_samples()
        page._status.setText(f"✅  {sample_count} amostras capturadas com sucesso!")

        if self.current_step < len(self._STEPS):
            next_step = self.current_step + 1
            QTimer.singleShot(600, lambda: self._go_to_step(next_step))
        else:
            QTimer.singleShot(600, self._finish)

    # ------------------------------------------------------------------
    # Sample ingestion (called by main window on each tracking frame)
    # ------------------------------------------------------------------

    def update_pose(self, pose: PoseSample) -> None:
        if self.is_recording:
            self.samples.append(pose)

    # ------------------------------------------------------------------
    # Sample processing
    # ------------------------------------------------------------------

    def _process_samples(self) -> None:
        if not self.samples:
            return

        yaws = [s.yaw for s in self.samples]
        pitches = [s.pitch for s in self.samples]
        rolls = [s.roll for s in self.samples]
        xs = [s.x for s in self.samples]
        ys = [s.y for s in self.samples]
        zs = [s.z for s in self.samples]

        step = self.current_step

        if step == 1:  # Center
            self.results["center_yaw"] = _mean(yaws)
            self.results["center_pitch"] = _mean(pitches)
            self.results["center_roll"] = _mean(rolls)
            self.results["center_x"] = _mean(xs)
            self.results["center_y"] = _mean(ys)
            self.results["center_z"] = _mean(zs)

        elif step == 2:  # Horizontal amplitude
            center_yaw = self.results.get("center_yaw", 0.0)
            yaw_deltas = [yaw - center_yaw for yaw in yaws]
            negative_yaw = min(yaw_deltas)
            positive_yaw = max(yaw_deltas)
            self.results["negative_yaw"] = negative_yaw
            self.results["positive_yaw"] = positive_yaw
            self.results["max_yaw"] = max(abs(negative_yaw), abs(positive_yaw))

        elif step == 3:  # Vertical amplitude
            center_pitch = self.results.get("center_pitch", 0.0)
            pitch_deltas = [pitch - center_pitch for pitch in pitches]
            negative_pitch = min(pitch_deltas)
            positive_pitch = max(pitch_deltas)
            self.results["negative_pitch"] = negative_pitch
            self.results["positive_pitch"] = positive_pitch
            self.results["max_pitch"] = max(abs(negative_pitch), abs(positive_pitch))

        elif step == 4:  # Stability / noise
            mean_yaw = _mean(yaws)
            variance = _mean([(x - mean_yaw) ** 2 for x in yaws])
            self.results["noise"] = math.sqrt(variance)

    # ------------------------------------------------------------------
    # Finish
    # ------------------------------------------------------------------

    def _finish(self) -> None:
        self.finished_calibration.emit(self.results)
        self.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_step_ui(self, step: int) -> None:
        if step == 0 or step > len(self._STEPS):
            return
        page = self.stack.widget(step)
        page._countdown.setVisible(False)
        page._status.setText("▶  Pronto — clique em Capturar para iniciar")

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #0A0A0A;
                color: #D1D1D1;
                font-family: 'Segoe UI', sans-serif;
            }
            QWidget {
                background-color: transparent;
                color: #D1D1D1;
            }
            QLabel#wizardTitle {
                font-size: 16px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QLabel#stepTitle {
                font-size: 14px;
                font-weight: 700;
                color: #00F2FF;
            }
            QLabel#stepDesc {
                font-size: 12px;
                color: #AAAAAA;
                line-height: 1.5;
            }
            QLabel#wizardDesc {
                font-size: 12px;
                color: #AAAAAA;
            }
            QLabel#statusLabel {
                font-size: 12px;
                font-weight: 600;
                color: #CCCCCC;
                padding: 6px;
            }
            QLabel#warnLabel {
                font-size: 12px;
                font-weight: 700;
                color: #FF6B35;
                background-color: #2A1500;
                border: 1px solid #FF6B35;
                border-radius: 6px;
                padding: 8px;
            }
            QProgressBar {
                background-color: #1E1E1E;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00F2FF;
                border-radius: 2px;
            }
            QPushButton#primaryButton {
                background-color: #00F2FF;
                color: #000000;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
                padding: 8px 24px;
                min-width: 140px;
            }
            QPushButton#primaryButton:hover {
                background-color: #80FFFF;
            }
            QPushButton#primaryButton:disabled {
                background-color: #333333;
                color: #666666;
            }
            QPushButton#backButton {
                background-color: transparent;
                color: #888888;
                border: 1px solid #333333;
                border-radius: 6px;
                font-size: 12px;
                padding: 8px 16px;
            }
            QPushButton#backButton:hover {
                color: #CCCCCC;
                border-color: #555555;
            }
            QPushButton#backButton:disabled {
                color: #444444;
                border-color: #222222;
            }
        """)


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
