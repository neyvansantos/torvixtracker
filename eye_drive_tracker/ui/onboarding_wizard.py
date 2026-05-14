# Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QComboBox, QProgressBar,
    QFrame, QGridLayout
)
import cv2

from eye_drive_tracker.camera import CameraEnumerator, Webcam
from eye_drive_tracker.profiles import TrackingConfig
from eye_drive_tracker.ui.i18n import translate, LANGUAGES
from eye_drive_tracker.tracking import PoseSample, AsyncHeadPoseWorker
from eye_drive_tracker.filters import apply_smart_motion_preset

class OnboardingWizard(QDialog):
    """
    Assistente de introdução para novos usuários.
    """
    
    finished_onboarding = Signal(TrackingConfig)

    def __init__(self, config: TrackingConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Torvix Tracker — Setup 🚀")
        self.setFixedSize(640, 520)
        self.setWindowModality(Qt.WindowModal)
        
        # Clone do config para não alterar o original até o fim
        self.config = config
        self.current_step = 0
        self.camera = Webcam()
        self.worker = AsyncHeadPoseWorker()
        
        # Estado de calibração
        self.last_pose: PoseSample | None = None
        self.is_calibrating = False
        
        # Timer para Preview e Tracking
        self._timer = QTimer(self)
        self._timer.setInterval(33) # ~30 FPS
        self._timer.timeout.connect(self._on_timer_tick)

        self._build_ui()
        self._apply_style()
        self._load_camera_devices()
        self._update_navigation()

    def _tr(self, key: str) -> str:
        return translate(self.config.language, key)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 5)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        header_layout.addWidget(self.progress_bar)
        layout.addWidget(header)

        # Conteúdo
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())      # 0
        self.stack.addWidget(self._page_webcam())       # 1
        self.stack.addWidget(self._page_resolution())   # 2
        self.stack.addWidget(self._page_filter())       # 3
        self.stack.addWidget(self._page_calibration())  # 4
        self.stack.addWidget(self._page_summary())      # 5
        layout.addWidget(self.stack)

        # Rodapé
        footer = QFrame()
        footer.setObjectName("footerFrame")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 15, 20, 15)

        self.btn_back = QPushButton(self._tr("Back"))
        self.btn_back.setObjectName("backButton")
        self.btn_back.clicked.connect(self._prev_step)

        self.btn_next = QPushButton(self._tr("Next"))
        self.btn_next.setObjectName("primaryButton")
        self.btn_next.clicked.connect(self._next_step)

        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_back)
        footer_layout.addWidget(self.btn_next)
        layout.addWidget(footer)

    def _page_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(15)

        title = QLabel("Torvix Tracker")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        img_path = Path(__file__).parent.parent / "resources" / "astronaut.png"
        if img_path.exists():
            pix = QPixmap(str(img_path)).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
        
        self.welcome_desc = QLabel(
            "Bem-vindo! Vamos configurar seu rastreador em poucos segundos.\n"
            "Primeiro, escolha o seu idioma:"
        )
        self.welcome_desc.setWordWrap(True)
        self.welcome_desc.setAlignment(Qt.AlignCenter)
        self.welcome_desc.setObjectName("pageDesc")

        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.lang_btns = []
        for lang in LANGUAGES:
            btn = QPushButton(lang)
            btn.setCheckable(True)
            btn.setChecked(self.config.language == lang)
            btn.setFixedSize(70, 40)
            btn.setObjectName("filterButton")
            btn.clicked.connect(lambda checked, l=lang: self._change_language(l))
            lang_layout.addWidget(btn)
            self.lang_btns.append(btn)
        lang_layout.addStretch()

        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(self.welcome_desc)
        layout.addLayout(lang_layout)
        layout.addStretch()
        return page

    def _change_language(self, lang: str) -> None:
        self.config.language = lang
        for btn in self.lang_btns:
            btn.setChecked(btn.text() == lang)
        
        # Atualizar strings estáticas
        self.btn_back.setText(self._tr("Back"))
        self.btn_next.setText(self._tr("Next") if self.current_step < 5 else self._tr("Finish"))
        self.welcome_desc.setText(self._tr("Bem-vindo! Vamos configurar seu rastreador em poucos segundos.\nPrimeiro, escolha o seu idioma:"))

    def _page_webcam(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        self.cam_title = QLabel("1. Escolha sua Câmera")
        self.cam_title.setObjectName("pageTitle")
        
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_selected)
        
        self.preview_label = QLabel("Iniciando câmera...")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setFixedSize(480, 270)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #000; border-radius: 8px; border: 2px solid #333;")

        layout.addWidget(self.cam_title)
        layout.addWidget(self.camera_combo)
        layout.addSpacing(10)
        layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)
        layout.addStretch()
        return page

    def _page_resolution(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        self.res_title = QLabel("2. Resolução e FPS")
        self.res_title.setObjectName("pageTitle")
        
        self.res_desc = QLabel("Escolha o modo de melhor performance. 60 FPS é recomendado.")
        self.res_desc.setWordWrap(True)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setMaxVisibleItems(10)
        self.mode_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mode_combo.setStyleSheet("QComboBox QAbstractItemView { background-color: #1A1A1A; color: white; selection-background-color: #004040; }")
        
        self.res_info = QLabel("Dica: Resoluções menores poupam CPU e são mais rápidas.")
        self.res_info.setObjectName("infoLabel")

        layout.addWidget(self.res_title)
        layout.addWidget(self.res_desc)
        layout.addSpacing(15)
        layout.addWidget(self.mode_combo)
        layout.addSpacing(15)
        layout.addWidget(self.res_info)
        layout.addStretch()
        return page

    def _page_filter(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        self.filter_title = QLabel("3. Estilo de Movimento")
        self.filter_title.setObjectName("pageTitle")
        
        grid = QGridLayout()
        self.btn_smooth = QPushButton("Ultra Suave")
        self.btn_balanced = QPushButton("Balanceado")
        self.btn_fast = QPushButton("Resposta Rápida")
        
        for btn in [self.btn_smooth, self.btn_balanced, self.btn_fast]:
            btn.setObjectName("filterButton")
            btn.setCheckable(True)
            btn.setFixedHeight(50)

        self.btn_smooth.clicked.connect(lambda: self._select_filter("cinematic"))
        self.btn_balanced.clicked.connect(lambda: self._select_filter("balanced"))
        self.btn_fast.clicked.connect(lambda: self._select_filter("fast_response"))
        
        grid.addWidget(self.btn_smooth, 0, 0)
        grid.addWidget(self.btn_balanced, 0, 1)
        grid.addWidget(self.btn_fast, 1, 0, 1, 2)
        
        self.filter_desc = QLabel("Selecione um estilo.")
        self.filter_desc.setWordWrap(True)
        self.filter_desc.setMinimumHeight(60)

        layout.addWidget(self.filter_title)
        layout.addLayout(grid)
        layout.addSpacing(10)
        layout.addWidget(self.filter_desc)
        layout.addStretch()
        
        self.filter_buttons = [self.btn_smooth, self.btn_balanced, self.btn_fast]
        return page

    def _page_calibration(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        self.cal_title = QLabel("4. Calibração Central")
        self.cal_title.setObjectName("pageTitle")
        
        self.cal_desc = QLabel("Olhe para o centro da tela e clique no botão.")
        self.cal_desc.setWordWrap(True)
        
        self.btn_calib = QPushButton("Calibrar Agora")
        self.btn_calib.setObjectName("primaryButton")
        self.btn_calib.clicked.connect(self._start_calibration)
        
        self.calib_status = QLabel("")
        self.calib_status.setAlignment(Qt.AlignCenter)
        self.calib_status.setStyleSheet("font-weight: bold; color: #00F2FF;")

        layout.addWidget(self.cal_title)
        layout.addWidget(self.cal_desc)
        layout.addStretch()
        layout.addWidget(self.btn_calib, alignment=Qt.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.calib_status)
        layout.addStretch()
        return page

    def _page_summary(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        self.sum_title = QLabel("Pronto para decolar!")
        self.sum_title.setObjectName("pageTitle")
        self.sum_title.setAlignment(Qt.AlignCenter)
        
        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(self.sum_title)
        layout.addWidget(self.summary_label)
        layout.addStretch()
        return page

    # --- LÓGICA ---

    def _load_camera_devices(self) -> None:
        devices = CameraEnumerator.list_cameras()
        self.camera_devices = devices
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        for dev in devices:
            self.camera_combo.addItem(dev.name, dev.index)
        
        # Seleciona a atual se existir
        idx = self.camera_combo.findData(self.config.camera_index)
        if idx >= 0:
            self.camera_combo.setCurrentIndex(idx)
        elif self.camera_combo.count() > 0:
            self.camera_combo.setCurrentIndex(0)
        self.camera_combo.blockSignals(False)

        if self.camera_combo.currentIndex() >= 0:
            cam_idx = self.camera_combo.currentData()
            self.config.camera_index = cam_idx
            self._update_modes(cam_idx)
        else:
            self.preview_label.clear()
            self.preview_label.setText("Nenhuma c\u00e2mera encontrada")

    def _on_camera_selected(self, index: int) -> None:
        if index < 0:
            return
        cam_idx = self.camera_combo.itemData(index)
        if cam_idx is None:
            return
        self.config.camera_index = cam_idx
        
        # Abrir câmera e carregar modos
        self._timer.stop()
        self.preview_label.clear()
        self.preview_label.setText("Iniciando c\u00e2mera...")
        self.camera.release()
        if self.camera.open(cam_idx):
            self._update_modes(cam_idx)
            # Iniciar timer se estivermos na página de preview ou calibração
            if self.current_step in (1, 4):
                self._timer.start()
        else:
            self.preview_label.clear()
            self.preview_label.setText("Câmera ocupada ou não encontrada")

    def _update_modes(self, cam_idx: int) -> None:
        modes = CameraEnumerator.list_modes(cam_idx)
        self.mode_combo.clear()
        for m in modes:
            label = f"{m.width}x{m.height} @ {m.fps} FPS"
            self.mode_combo.addItem(label, m)
        
        # Seleciona o melhor match ou o primeiro
        for i in range(self.mode_combo.count()):
            m = self.mode_combo.itemData(i)
            if m.width == self.config.camera_width and m.height == self.config.camera_height:
                self.mode_combo.setCurrentIndex(i)
                break

    def _on_timer_tick(self) -> None:
        ok, frame, _ = self.camera.read_with_id()
        if not ok or frame is None:
            return
            
        # Preview na Página 1
        if self.current_step == 1:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb.shape
            qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.preview_label.setPixmap(pix)
            
        # Tracking/Calibração na Página 4
        if self.current_step == 4:
            if self.worker.wants_frame():
                self.worker.submit(frame, 640)
            
            res = self.worker.take_result()
            if res and res.result.detected:
                self.last_pose = res.result.pose
                if self.is_calibrating:
                    # Captura imediata ao detectar rosto se estiver no modo calib
                    pass
                else:
                    self.calib_status.setText("✅ Rosto detectado. Pronto para calibrar.")
            elif not self.is_calibrating:
                self.calib_status.setText("❌ Rosto não detectado. Ajuste sua posição.")

    def _next_step(self) -> None:
        # Salva dados da página atual antes de mudar
        if self.current_step == 2: # Resolução
            m = self.mode_combo.currentData()
            if m:
                self.config.camera_width = m.width
                self.config.camera_height = m.height
                self.config.camera_fps = m.fps
        
        if self.current_step < 5:
            self.current_step += 1
            self._update_navigation()
        else:
            self._finish()

    def _prev_step(self) -> None:
        if self.current_step > 0:
            self.current_step -= 1
            self._update_navigation()

    def _update_navigation(self) -> None:
        self.stack.setCurrentIndex(self.current_step)
        self.progress_bar.setValue(self.current_step)
        self.btn_back.setVisible(self.current_step > 0)
        self.btn_next.setText(self._tr("Next") if self.current_step < 5 else self._tr("Finish"))
        
        # Gestão de Câmera/Worker conforme a página
        if self.current_step in (1, 4):
            if not self.camera.is_open:
                self._on_camera_selected(self.camera_combo.currentIndex())
            if self.camera.is_open:
                self._timer.start()
            if self.current_step == 4 and self.camera.is_open:
                self.worker.start()
        else:
            self._timer.stop()
            self.worker.stop()
            
        if self.current_step == 3: # Filtros: marcar o atual
            self._select_filter(self.config.motion_filter_preset)
        
        if self.current_step == 5:
            self._prepare_summary()

    def _select_filter(self, preset: str) -> None:
        apply_smart_motion_preset(self.config, preset)
        self.config.motion_filter_preset = preset
        
        for btn in self.filter_buttons:
            btn.setChecked(False)
            if preset == "cinematic" and btn == self.btn_smooth: btn.setChecked(True)
            if preset == "balanced" and btn == self.btn_balanced: btn.setChecked(True)
            if preset == "fast_response" and btn == self.btn_fast: btn.setChecked(True)

        descs = {
            "cinematic": "Ultra Suave: Ideal para voo e simulação lenta.",
            "balanced": "Balanceado: Recomendado para Euro Truck / Corrida.",
            "fast_response": "Rápido: Resposta instantânea para combate/ação."
        }
        self.filter_desc.setText(descs.get(preset, ""))

    def _start_calibration(self) -> None:
        if not self.last_pose:
            self.calib_status.setText("⚠️ Posicione-se na frente da câmera primeiro.")
            return
            
        self.is_calibrating = True
        self.btn_calib.setEnabled(False)
        self.calib_status.setText("🔴 Calibrando em 3s... Mantenha-se imóvel.")
        
        QTimer.singleShot(3000, self._finalize_calibration)

    def _finalize_calibration(self) -> None:
        self.is_calibrating = False
        if self.last_pose:
            self.config.calibration_center_set = True
            self.config.calibration_center_yaw = self.last_pose.yaw
            self.config.calibration_center_pitch = self.last_pose.pitch
            self.config.calibration_center_roll = self.last_pose.roll
            self.config.calibration_center_x = self.last_pose.x
            self.config.calibration_center_y = self.last_pose.y
            self.config.calibration_center_z = self.last_pose.z
            self.calib_status.setText("✅ Calibração Salva!")
        else:
            self.calib_status.setText("❌ Falha: Rosto perdido.")
            
        self.btn_calib.setEnabled(True)
        self.btn_calib.setText("Recalibrar")

    def _prepare_summary(self) -> None:
        sum_text = f"Câmera: {self.camera_combo.currentText()}\n"
        sum_text += f"Resolução: {self.config.camera_width}x{self.config.camera_height} @ {self.config.camera_fps} FPS\n"
        sum_text += f"Estilo: {self.config.motion_filter_preset}\n"
        sum_text += f"Calibração: {'OK' if self.config.calibration_center_set else 'Não realizada'}"
        self.summary_label.setText(sum_text)

    def _finish(self) -> None:
        self.config.onboarding_completed = True
        self.camera.release()
        self.worker.stop()
        self.finished_onboarding.emit(self.config)
        self.accept()

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog { background-color: #0A0A0A; color: #D1D1D1; font-family: 'Segoe UI', sans-serif; }
            QFrame#headerFrame, QFrame#footerFrame { background-color: #111; }
            QLabel#pageTitle { font-size: 20px; font-weight: 700; color: #FFFFFF; margin-bottom: 10px; }
            QLabel#pageDesc, QLabel#infoLabel { font-size: 13px; color: #AAAAAA; }
            QPushButton#primaryButton { background-color: #00F2FF; color: #000; border: none; border-radius: 6px; font-weight: 700; padding: 10px 30px; min-width: 140px; }
            QPushButton#primaryButton:hover { background-color: #80FFFF; }
            QPushButton#backButton { background-color: transparent; color: #888; border: 1px solid #333; border-radius: 6px; padding: 8px 20px; }
            QPushButton#filterButton { background-color: #1A1A1A; border: 1px solid #333; border-radius: 8px; color: #DDD; }
            QPushButton#filterButton:checked { background-color: #004040; border-color: #00F2FF; color: #00F2FF; }
            QComboBox { background-color: #1A1A1A; border: 1px solid #333; border-radius: 4px; padding: 5px; color: white; }
            QProgressBar { background-color: #222; border: none; }
            QProgressBar::chunk { background-color: #00F2FF; }
        """)

    def closeEvent(self, event) -> None:
        self.camera.release()
        self.worker.stop()
        super().closeEvent(event)
