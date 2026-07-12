from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
import threading
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QImage, QKeySequence, QPixmap, QShortcut

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # Keep the reticle page usable in minimal Qt builds.
    QAudioOutput = None
    QMediaPlayer = None

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class DetectionResult:
    status: str = "NO TARGET"
    detected_color: str = "NONE"
    yellow_pixels: int = 0
    green_pixels: int = 0
    cyan_pixels: int = 0
    orange_pixels: int = 0
    purple_pixels: int = 0
    confidence: float = 0.0
    shape_confidence: float = 0.0
    crosshair_present: bool = False


class EmergencyHotkey(QObject):
    """Windows global Ctrl+Alt+F12 hotkey with an in-app fallback elsewhere."""

    activated = Signal()

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    VK_F12 = 0x7B
    HOTKEY_ID = 0x5354

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._stop_event = threading.Event()
        self._fallback: QShortcut | None = None

    def start(self, owner: QWidget) -> bool:
        self.stop()
        if sys.platform != "win32":
            self._fallback = QShortcut(QKeySequence("Ctrl+Alt+F12"), owner)
            self._fallback.setContext(Qt.ApplicationShortcut)
            self._fallback.activated.connect(self.activated.emit)
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_windows, daemon=True, name="ReticleEmergencyHotkey")
        self._thread.start()
        return True

    def _run_windows(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = int(kernel32.GetCurrentThreadId())
        registered = bool(user32.RegisterHotKey(None, self.HOTKEY_ID, self.MOD_CONTROL | self.MOD_ALT, self.VK_F12))
        if not registered:
            self._thread_id = 0
            return
        try:
            msg = ctypes.wintypes.MSG()
            while not self._stop_event.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result <= 0:
                    break
                if msg.message == self.WM_HOTKEY and msg.wParam == self.HOTKEY_ID:
                    self.activated.emit()
        finally:
            user32.UnregisterHotKey(None, self.HOTKEY_ID)
            self._thread_id = 0

    def stop(self) -> None:
        if self._fallback is not None:
            self._fallback.setEnabled(False)
            self._fallback.deleteLater()
            self._fallback = None
        self._stop_event.set()
        if sys.platform == "win32" and self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, self.WM_QUIT, 0, 0)
            except Exception:
                pass
        self._thread = None


class ReticleOverlay(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("StankyTools Reticle Status")
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._display_mode = "text"
        self.setFixedSize(116, 32)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.set_status("NO TARGET")

    def set_display_mode(self, mode: str) -> None:
        self._display_mode = "bar" if str(mode).lower() == "bar" else "text"
        if self._display_mode == "bar":
            self.setFixedSize(88, 8)
        else:
            self.setFixedSize(116, 32)

    def set_status(self, status: str, detected_color: str = "NONE") -> None:
        if status != "FRIENDLY":
            self.label.clear()
            return

        if self._display_mode == "bar":
            self.label.setText("")
            self.label.setStyleSheet(
                "QLabel {"
                "background:rgba(74, 226, 125, 210);"
                "border:0px;"
                "border-radius:2px;"
                "}"
            )
            return

        self.label.setText("HOMEBOY")
        self.label.setStyleSheet(
            "QLabel {"
            "color:rgba(221,255,232,235);"
            "background:rgba(8,24,14,150);"
            "border:1px solid rgba(80,220,125,130);"
            "border-radius:5px;"
            "font-size:13px; font-weight:800; letter-spacing:1px;"
            "padding:3px 8px;"
            "}"
        )

    def place_on_screen(self, screen, y_offset: int = 90) -> None:
        area = screen.geometry()
        self.move(area.center().x() - self.width() // 2, area.center().y() + y_offset)


class ReticleMonitorPage(QWidget):
    """Passive screen-pixel monitor. It never opens or inspects the game process."""

    def __init__(self, setting_get: Callable[[str, str], str], setting_set: Callable[[str, str], None], parent=None):
        super().__init__(parent)
        self._get = setting_get
        self._set = setting_set
        self._last_status = "NO TARGET"
        self._pending_state = "NO TARGET:NONE"
        self._pending_frames = 0
        self._overlay = ReticleOverlay()
        self._media_player = None
        self._audio_output = None
        if QMediaPlayer is not None and QAudioOutput is not None:
            self._audio_output = QAudioOutput(self)
            self._audio_output.setVolume(1.0)
            self._media_player = QMediaPlayer(self)
            self._media_player.setAudioOutput(self._audio_output)
            self._media_player.errorOccurred.connect(self._media_error)
        self._hotkey = EmergencyHotkey(self)
        self._hotkey.activated.connect(self.emergency_stop)

        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_frame)

        self._build_ui()
        self._load_settings()
        self._hotkey.start(self)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)
        self.refresh_monitors()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(14)

        header = QLabel("RETICLE MONITOR")
        header.setStyleSheet("font-size:28px; font-weight:900; letter-spacing:2px;")
        sub = QLabel(
            "Passive screen-color detection only. No game memory, process injection, targeting, or automatic input. "
            "Emergency disable: Ctrl+Alt+F12."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#BDB4A5; font-size:13px;")
        root.addWidget(header)
        root.addWidget(sub)

        controls = QFrame()
        controls.setObjectName("Card")
        grid = QGridLayout(controls)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(12)

        form = QFormLayout()
        self.monitor_combo = QComboBox()
        self.monitor_combo.currentIndexChanged.connect(self._monitor_changed)
        self.refresh_button = QPushButton("Refresh Monitors")
        self.refresh_button.clicked.connect(self.refresh_monitors)
        monitor_row = QHBoxLayout()
        monitor_row.addWidget(self.monitor_combo, 1)
        monitor_row.addWidget(self.refresh_button)
        monitor_wrap = QWidget()
        monitor_wrap.setLayout(monitor_row)
        form.addRow("Game monitor", monitor_wrap)

        self.box_size = QSpinBox()
        self.box_size.setRange(20, 300)
        self.box_size.setSuffix(" px")
        form.addRow("Center capture box", self.box_size)

        self.capture_fps = QSpinBox()
        self.capture_fps.setRange(5, 30)
        self.capture_fps.setSuffix(" FPS")
        form.addRow("Capture rate", self.capture_fps)

        self.minimum_pixels = QSpinBox()
        self.minimum_pixels.setRange(2, 3000)
        form.addRow("Minimum reticle pixels", self.minimum_pixels)

        self.shape_confidence = QSpinBox()
        self.shape_confidence.setRange(40, 95)
        self.shape_confidence.setSuffix(" %")
        form.addRow("Crosshair shape confidence", self.shape_confidence)

        self.center_tolerance = QSpinBox()
        self.center_tolerance.setRange(2, 30)
        self.center_tolerance.setSuffix(" px")
        form.addRow("Center tolerance", self.center_tolerance)

        self.required_frames = QSpinBox()
        self.required_frames.setRange(1, 5)
        form.addRow("Required consecutive frames", self.required_frames)

        self.green_slider, self.green_value = self._make_slider(20, 100)
        form.addRow("Friendly-color sensitivity", self._slider_row(self.green_slider, self.green_value))

        self.calibration = QCheckBox("Calibration mode")
        self.calibration.setToolTip("Continuously shows the center capture region and pixel counts.")
        self.overlay_enabled = QCheckBox("Transparent click-through overlay")
        self.overlay_style = QComboBox()
        self.overlay_style.addItem("Text — HOMEBOY", "text")
        self.overlay_style.addItem("Green bar", "bar")
        self.overlay_style.currentIndexChanged.connect(self._overlay_style_changed)
        self.sound_enabled = QCheckBox("Play sound when targeting a friendly")

        self.sound_path = QLineEdit()
        self.sound_path.setReadOnly(True)
        self.sound_path.setPlaceholderText("Default Windows beep")
        self.sound_path.setToolTip(
            "Select a common audio or video media file. The audio track will play; "
            "actual format support depends on Windows codecs. Leave empty for the default beep."
        )
        self.sound_browse = QPushButton("Choose…")
        self.sound_browse.clicked.connect(self._choose_sound)
        self.sound_test = QPushButton("Test")
        self.sound_test.clicked.connect(self._test_sound)
        self.sound_clear = QPushButton("Clear")
        self.sound_clear.clicked.connect(self._clear_sound)
        sound_row = QHBoxLayout()
        sound_row.setContentsMargins(0, 0, 0, 0)
        sound_row.addWidget(self.sound_path, 1)
        sound_row.addWidget(self.sound_browse)
        sound_row.addWidget(self.sound_test)
        sound_row.addWidget(self.sound_clear)
        sound_wrap = QWidget()
        sound_wrap.setLayout(sound_row)

        form.addRow(self.calibration)
        form.addRow(self.overlay_enabled)
        form.addRow("Overlay style", self.overlay_style)
        form.addRow(self.sound_enabled)
        form.addRow("Friendly sound", sound_wrap)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start Monitor")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.clicked.connect(self.start_monitor)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.clicked.connect(self.stop_monitor)
        self.stop_button.setEnabled(False)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        form.addRow(buttons)

        grid.addLayout(form, 0, 0)

        output_box = QVBoxLayout()
        self.status_label = QLabel("NO TARGET")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(108)
        output_box.addWidget(self.status_label)

        self.preview = QLabel("Preview appears while monitoring")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(300, 300)
        self.preview.setStyleSheet("background:#050505; border:1px solid #6b6257; border-radius:10px;")
        output_box.addWidget(self.preview, 1)

        self.metrics = QLabel("Crosshair: No | Shape: 0% | Yellow: 0 | Green: 0 | Light Blue: 0 | Orange: 0 | Purple: 0")
        self.metrics.setAlignment(Qt.AlignCenter)
        self.metrics.setStyleSheet("color:#BDB4A5; font-weight:700;")
        output_box.addWidget(self.metrics)
        grid.addLayout(output_box, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addWidget(controls, 1)

        self.state_note = QLabel("Monitor stopped")
        self.state_note.setStyleSheet("color:#BDB4A5;")
        root.addWidget(self.state_note)
        self._apply_status(DetectionResult())

    def _make_slider(self, low: int, high: int):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        value = QLabel("0")
        value.setMinimumWidth(34)
        slider.valueChanged.connect(lambda v, label=value: label.setText(str(v)))
        return slider, value

    @staticmethod
    def _slider_row(slider: QSlider, value: QLabel) -> QWidget:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(slider, 1)
        row.addWidget(value)
        wrap = QWidget()
        wrap.setLayout(row)
        return wrap

    def _load_settings(self) -> None:
        self.box_size.setValue(int(self._get("reticle_box_size", "96") or 96))
        self.capture_fps.setValue(int(self._get("reticle_capture_fps", "15") or 15))
        self.minimum_pixels.setValue(int(self._get("reticle_min_pixels", "18") or 18))
        self.shape_confidence.setValue(int(self._get("reticle_shape_confidence", "68") or 68))
        self.center_tolerance.setValue(int(self._get("reticle_center_tolerance", "12") or 12))
        self.required_frames.setValue(int(self._get("reticle_required_frames", "2") or 2))
        self.green_slider.setValue(int(self._get("reticle_green_sensitivity", "58") or 58))
        self.calibration.setChecked((self._get("reticle_calibration", "1") or "1") == "1")
        self.overlay_enabled.setChecked((self._get("reticle_overlay", "0") or "0") == "1")
        overlay_mode = (self._get("reticle_overlay_style", "text") or "text").lower()
        overlay_index = self.overlay_style.findData(overlay_mode)
        self.overlay_style.setCurrentIndex(overlay_index if overlay_index >= 0 else 0)
        self._overlay.set_display_mode(self.overlay_style.currentData() or "text")
        self.sound_enabled.setChecked((self._get("reticle_sound", "0") or "0") == "1")
        stored_sound = self._get("reticle_sound_path", "") or ""
        self.sound_path.setText(stored_sound if os.path.isfile(stored_sound) else "")

    def _save_settings(self) -> None:
        values = {
            "reticle_box_size": self.box_size.value(),
            "reticle_capture_fps": self.capture_fps.value(),
            "reticle_min_pixels": self.minimum_pixels.value(),
            "reticle_shape_confidence": self.shape_confidence.value(),
            "reticle_center_tolerance": self.center_tolerance.value(),
            "reticle_required_frames": self.required_frames.value(),
            "reticle_green_sensitivity": self.green_slider.value(),
            "reticle_calibration": int(self.calibration.isChecked()),
            "reticle_overlay": int(self.overlay_enabled.isChecked()),
            "reticle_overlay_style": self.overlay_style.currentData() or "text",
            "reticle_sound": int(self.sound_enabled.isChecked()),
            "reticle_sound_path": self.sound_path.text().strip(),
            "reticle_monitor_index": self.monitor_combo.currentIndex(),
        }
        for key, value in values.items():
            self._set(key, str(value))

    def refresh_monitors(self) -> None:
        selected = int(self._get("reticle_monitor_index", "0") or 0)
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()
        for index, screen in enumerate(QApplication.screens()):
            geometry = screen.geometry()
            primary = " (Primary)" if screen is QApplication.primaryScreen() else ""
            self.monitor_combo.addItem(
                f"{index + 1}: {screen.name()} — {geometry.width()}×{geometry.height()}{primary}",
                index,
            )
        if self.monitor_combo.count():
            self.monitor_combo.setCurrentIndex(max(0, min(selected, self.monitor_combo.count() - 1)))
        self.monitor_combo.blockSignals(False)
        self._monitor_changed()

    def selected_screen(self):
        screens = QApplication.screens()
        index = self.monitor_combo.currentData()
        if index is None or not screens:
            return QApplication.primaryScreen()
        return screens[max(0, min(int(index), len(screens) - 1))]

    def _monitor_changed(self, *_args) -> None:
        if self._overlay.isVisible():
            screen = self.selected_screen()
            if screen:
                self._overlay.place_on_screen(screen)

    def _overlay_style_changed(self, *_args) -> None:
        mode = self.overlay_style.currentData() or "text"
        self._overlay.set_display_mode(mode)
        if self._overlay.isVisible():
            screen = self.selected_screen()
            if screen:
                self._overlay.place_on_screen(screen)
        self._set("reticle_overlay_style", str(mode))

    def _choose_sound(self) -> None:
        start_dir = os.path.dirname(self.sound_path.text().strip()) if self.sound_path.text().strip() else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select friendly-target sound",
            start_dir,
            "Media files (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.wma *.aiff *.aif "
            "*.mp4 *.m4v *.mov *.avi *.mkv *.webm *.wmv *.mpeg *.mpg);;"
            "Audio files (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.wma *.aiff *.aif);;"
            "Video files (*.mp4 *.m4v *.mov *.avi *.mkv *.webm *.wmv *.mpeg *.mpg);;"
            "All files (*.*)",
        )
        if not path:
            return
        self.sound_path.setText(path)
        self._set("reticle_sound_path", path)

    def _clear_sound(self) -> None:
        self.sound_path.clear()
        self._set("reticle_sound_path", "")

    def _test_sound(self) -> None:
        self._play_friendly_sound()

    def _media_error(self, _error, error_string: str = "") -> None:
        message = error_string or "The selected media format could not be played."
        self.state_note.setText(f"Media playback error: {message}")

    def _play_friendly_sound(self) -> None:
        path = self.sound_path.text().strip()
        if path and os.path.isfile(path):
            # QMediaPlayer supports common audio formats and the audio tracks of
            # common video containers through the codecs available on Windows.
            if self._media_player is not None:
                self._media_player.stop()
                self._media_player.setSource(QUrl.fromLocalFile(path))
                self._media_player.play()
                return

            # Minimal-build fallback: Windows can still play uncompressed WAV.
            if sys.platform == "win32" and path.lower().endswith(".wav"):
                try:
                    import winsound
                    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                    return
                except Exception as exc:
                    self.state_note.setText(f"Could not play selected WAV: {exc}")
            else:
                self.state_note.setText(
                    "Qt Multimedia is unavailable in this build; only WAV fallback playback is supported."
                )
        QApplication.beep()

    def start_monitor(self) -> None:
        screen = self.selected_screen()
        if screen is None:
            self.state_note.setText("No monitor is available for capture.")
            return
        self._save_settings()
        interval = max(33, round(1000 / self.capture_fps.value()))
        self.capture_timer.start(interval)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.state_note.setText("Monitoring visible center-screen pixels only — Ctrl+Alt+F12 stops immediately")
        # The overlay remains hidden until a visible friendly reticle is detected.
        self._overlay.hide()
        self.capture_frame()

    def stop_monitor(self) -> None:
        self.capture_timer.stop()
        self._overlay.hide()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.state_note.setText("Monitor stopped")
        self._apply_status(DetectionResult())

    def emergency_stop(self) -> None:
        self.stop_monitor()
        self.overlay_enabled.setChecked(False)
        self._save_settings()
        self.state_note.setText("EMERGENCY DISABLED — press Start Monitor to enable again")

    def capture_frame(self) -> None:
        screen = self.selected_screen()
        if screen is None:
            self.stop_monitor()
            return
        size = self.box_size.value()
        geometry = screen.geometry()
        center = geometry.center()
        # QScreen.grabWindow uses screen-local coordinates.
        local_center = QPoint(center.x() - geometry.x(), center.y() - geometry.y())
        x = local_center.x() - size // 2
        y = local_center.y() - size // 2
        pixmap = screen.grabWindow(0, x, y, size, size)
        if pixmap.isNull():
            self.state_note.setText("Screen capture failed. Try borderless-windowed mode or another monitor.")
            return

        image = pixmap.toImage().convertToFormat(QImage.Format_RGB32)
        result = self._detect(image)
        self._apply_status(result)

        if self.calibration.isChecked():
            preview = pixmap.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
            self.preview.setPixmap(preview)
        else:
            self.preview.clear()
            self.preview.setText("Enable Calibration mode to show the capture region")

    def _detect(self, image: QImage) -> DetectionResult:
        """Detect a centered crosshair shape first, then classify only its pixels.

        The detector deliberately rejects large scenery/UI color regions. A candidate
        must be compact, centered, sparse/hollow, reasonably symmetric, and occupy
        several angular sectors around the screen center.
        """
        width, height = image.width(), image.height()
        total = max(1, width * height)
        friendly_sensitivity = self.green_slider.value() / 100.0
        friendly_sat_floor = max(45, int(165 - friendly_sensitivity * 100))
        friendly_val_floor = max(65, int(180 - friendly_sensitivity * 105))

        def in_hue(hue: int, low: int, high: int) -> bool:
            return low <= hue <= high if low <= high else hue >= low or hue <= high

        color_at: dict[tuple[int, int], str] = {}
        for y in range(height):
            for x in range(width):
                hue, saturation, value, _alpha = QColor(image.pixel(x, y)).getHsv()
                if hue < 0:
                    continue
                color = None
                if saturation >= friendly_sat_floor and value >= friendly_val_floor:
                    if 49 <= hue <= 74:
                        color = "YELLOW"
                    elif 75 <= hue <= 165:
                        color = "GREEN"
                    elif 166 <= hue <= 215:
                        color = "CYAN"
                    elif 16 <= hue <= 48:
                        color = "ORANGE"
                    elif 250 <= hue <= 325:
                        color = "PURPLE"
                if color:
                    color_at[(x, y)] = color

        raw_counts = {name: 0 for name in ("YELLOW", "GREEN", "CYAN", "ORANGE", "PURPLE")}
        for color in color_at.values():
            raw_counts[color] += 1
        if len(color_at) < self.minimum_pixels.value():
            return DetectionResult(
                yellow_pixels=raw_counts["YELLOW"], green_pixels=raw_counts["GREEN"],
                cyan_pixels=raw_counts["CYAN"], orange_pixels=raw_counts["ORANGE"],
                purple_pixels=raw_counts["PURPLE"],
            )

        # Connected components keep unrelated scenery colors out of the candidate.
        remaining = set(color_at)
        components: list[set[tuple[int, int]]] = []
        while remaining:
            seed = remaining.pop()
            component = {seed}
            stack = [seed]
            while stack:
                x, y = stack.pop()
                for nx in (x - 1, x, x + 1):
                    for ny in (y - 1, y, y + 1):
                        if (nx, ny) in remaining:
                            remaining.remove((nx, ny))
                            component.add((nx, ny))
                            stack.append((nx, ny))
            if len(component) >= max(3, self.minimum_pixels.value() // 3):
                components.append(component)

        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        tolerance = float(self.center_tolerance.value())
        best_component = None
        best_score = 0.0

        for component in components:
            xs = [p[0] for p in component]
            ys = [p[1] for p in component]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            box_w, box_h = max_x - min_x + 1, max_y - min_y + 1
            if box_w < 6 or box_h < 6:
                continue
            if box_w > width * 0.92 or box_h > height * 0.92:
                continue

            comp_cx = sum(xs) / len(xs)
            comp_cy = sum(ys) / len(ys)
            center_distance = ((comp_cx - cx) ** 2 + (comp_cy - cy) ** 2) ** 0.5
            center_score = max(0.0, 1.0 - center_distance / max(1.0, tolerance))
            if center_score <= 0:
                continue

            fill_ratio = len(component) / max(1, box_w * box_h)
            # Reticles are line art: neither tiny noise nor a solid colored block.
            sparsity_score = 1.0 - min(1.0, abs(fill_ratio - 0.20) / 0.32)
            if fill_ratio > 0.62:
                continue

            # Angular coverage recognizes rings, crosses, brackets, and hexagonal forms.
            sectors = [0] * 8
            radii = []
            for x, y in component:
                dx, dy = x - cx, y - cy
                radius = (dx * dx + dy * dy) ** 0.5
                if radius < 2:
                    continue
                radii.append(radius)
                import math
                sector = int(((math.atan2(dy, dx) + math.pi) / (2 * math.pi)) * 8) % 8
                sectors[sector] += 1
            active_sectors = sum(1 for value in sectors if value >= max(2, len(component) * 0.025))
            sector_score = min(1.0, active_sectors / 5.0)

            # Approximate horizontal/vertical symmetry; tolerate intentionally open reticles.
            mirrored = 0
            checks = 0
            comp_lookup = component
            for x, y in component:
                mx = int(round(2 * cx - x))
                my = int(round(2 * cy - y))
                checks += 2
                if any((mx + ox, y + oy) in comp_lookup for ox in (-1, 0, 1) for oy in (-1, 0, 1)):
                    mirrored += 1
                if any((x + ox, my + oy) in comp_lookup for ox in (-1, 0, 1) for oy in (-1, 0, 1)):
                    mirrored += 1
            symmetry_score = mirrored / max(1, checks)

            size_score = min(1.0, len(component) / max(1.0, self.minimum_pixels.value() * 2.5))
            score = (center_score * 0.30 + sector_score * 0.25 + symmetry_score * 0.20 +
                     sparsity_score * 0.15 + size_score * 0.10)
            if score > best_score:
                best_score = score
                best_component = component

        required_score = self.shape_confidence.value() / 100.0
        if best_component is None or best_score < required_score:
            return DetectionResult(
                yellow_pixels=raw_counts["YELLOW"], green_pixels=raw_counts["GREEN"],
                cyan_pixels=raw_counts["CYAN"], orange_pixels=raw_counts["ORANGE"],
                purple_pixels=raw_counts["PURPLE"], shape_confidence=best_score,
                crosshair_present=False,
            )

        # Classify only pixels belonging to the matched crosshair component.
        counts = {name: 0 for name in raw_counts}
        for point in best_component:
            counts[color_at[point]] += 1
        friendly_counts = {name: counts[name] for name in ("YELLOW", "GREEN", "CYAN", "ORANGE", "PURPLE")}
        dominant_friendly_color = max(friendly_counts, key=friendly_counts.get)
        dominant_friendly = friendly_counts[dominant_friendly_color]
        total_friendly = sum(friendly_counts.values())
        minimum_pixels = self.minimum_pixels.value()

        status, detected_color, dominant = "NO TARGET", "NONE", 0
        if total_friendly >= minimum_pixels and dominant_friendly >= max(1, minimum_pixels // 2):
            status, detected_color, dominant = "FRIENDLY", dominant_friendly_color, total_friendly

        color_confidence = dominant / max(1, len(best_component)) if dominant else 0.0
        return DetectionResult(
            status=status, detected_color=detected_color,
            yellow_pixels=counts["YELLOW"], green_pixels=counts["GREEN"],
            cyan_pixels=counts["CYAN"], orange_pixels=counts["ORANGE"],
            purple_pixels=counts["PURPLE"], confidence=min(1.0, color_confidence),
            shape_confidence=best_score, crosshair_present=True,
        )

    def _apply_status(self, result: DetectionResult) -> None:
        status_text = result.status
        self.status_label.setText("HOMEBOY" if status_text == "FRIENDLY" else status_text)
        if status_text == "FRIENDLY":
            self.status_label.setStyleSheet(
                "color:#DFFFE8; background:rgba(8,24,14,150);"
                "border:1px solid rgba(80,220,125,130); border-radius:8px;"
                "font-size:26px; font-weight:800; letter-spacing:2px;"
            )
        else:
            self.status_label.setStyleSheet(
                "color:#8D877D; background:rgba(12,12,12,0.72); border:1px solid rgba(255,255,255,20);"
                "border-radius:14px; font-size:28px; font-weight:800; letter-spacing:2px;"
            )
        self.metrics.setText(
            f"Crosshair: {'Yes' if result.crosshair_present else 'No'} | "
            f"Shape: {round(result.shape_confidence * 100)}% | "
            f"Yellow: {result.yellow_pixels} | Green: {result.green_pixels} | Light Blue: {result.cyan_pixels} | "
            f"Orange: {result.orange_pixels} | Purple: {result.purple_pixels} | "
            f"Color: {round(result.confidence * 100)}%"
        )
        state_key = f"{result.status}:{result.detected_color}"
        if state_key == self._pending_state:
            self._pending_frames += 1
        else:
            self._pending_state = state_key
            self._pending_frames = 1

        confirmed = self._pending_frames >= self.required_frames.value()
        visible_status = result.status if confirmed else "NO TARGET"
        visible_color = result.detected_color if confirmed else "NONE"
        self._overlay.set_status(visible_status, visible_color)
        should_show_overlay = (
            self.overlay_enabled.isChecked()
            and self.capture_timer.isActive()
            and confirmed
            and visible_status == "FRIENDLY"
        )
        if should_show_overlay:
            screen = self.selected_screen()
            if screen:
                self._overlay.place_on_screen(screen)
                if not self._overlay.isVisible():
                    self._overlay.show()
                self._overlay.raise_()
        else:
            self._overlay.hide()

        if confirmed and state_key != self._last_status and visible_status == "FRIENDLY" and self.sound_enabled.isChecked():
            self._play_friendly_sound()
        if confirmed:
            self._last_status = state_key

    def shutdown(self) -> None:
        self.capture_timer.stop()
        if self._media_player is not None:
            self._media_player.stop()
        self._overlay.close()
        self._hotkey.stop()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
