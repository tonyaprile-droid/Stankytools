from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

ACCENTS = {
    "green": "#59D37A", "gold": "#D9B45D", "purple": "#A06BFF", "red": "#E25555",
    "atreides": "#59D37A", "dune": "#D9B45D", "spice": "#A06BFF", "harkonnen": "#E25555",
}

class CommandBanner(QFrame):
    def __init__(self, title: str, subtitle: str = "", kicker: str = "COMMAND OVERVIEW", theme: str = "gold", parent: QWidget | None = None):
        super().__init__(parent)
        self.theme = theme
        self.phase = 0
        self.setMinimumHeight(150)
        self.setObjectName("CommandBanner")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(4)
        self.kicker = QLabel(kicker.upper())
        self.kicker.setObjectName("BannerKicker")
        self.title = QLabel(title.upper())
        self.title.setObjectName("BannerTitle")
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("BannerSubtitle")
        layout.addStretch()
        layout.addWidget(self.kicker)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addStretch()
        self.apply_theme(theme)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(120)

    def _accent(self) -> QColor:
        return QColor(ACCENTS.get((self.theme or "gold").lower(), "#D9B45D"))

    def _tick(self):
        self.phase = (self.phase + 1) % 240
        self.update()

    def apply_theme(self, theme: str) -> None:
        self.theme = theme
        accent = self._accent()
        rgba = f"rgba({accent.red()}, {accent.green()}, {accent.blue()}, 0.72)"
        self.kicker.setStyleSheet(f"color:{rgba}; font-family:Rajdhani; font-size:13px; font-weight:800; letter-spacing:3px; background:transparent;")
        self.title.setStyleSheet("color:#ECECEC; font-family:Orbitron; font-size:28px; font-weight:700; letter-spacing:3px; background:transparent;")
        self.subtitle.setStyleSheet("color:#B9B9B9; font-family:Rajdhani; font-size:14px; font-weight:600; letter-spacing:1px; background:transparent;")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        accent = self._accent()
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, QColor("#17191C"))
        grad.setColorAt(0.55, QColor("#111214"))
        grad.setColorAt(1, QColor("#1C2024"))
        path = QPainterPath(); path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, grad)
        painter.setPen(QPen(accent, 1.2))
        painter.drawPath(path)
        # tactical corner brackets
        pen = QPen(accent, 2)
        painter.setPen(pen)
        l, t, r, b = rect.left()+16, rect.top()+16, rect.right()-16, rect.bottom()-16
        s = 34
        painter.drawLine(l, t, l+s, t); painter.drawLine(l, t, l, t+s)
        painter.drawLine(r, t, r-s, t); painter.drawLine(r, t, r, t+s)
        painter.drawLine(l, b, l+s, b); painter.drawLine(l, b, l, b-s)
        painter.drawLine(r, b, r-s, b); painter.drawLine(r, b, r, b-s)
        # scan line
        a = 24 + int(20 * (self.phase / 240))
        scan = QColor(accent); scan.setAlpha(a)
        painter.fillRect(rect.left()+2, rect.top()+20+(self.phase % max(1, rect.height()-40)), rect.width()-4, 1, scan)
        super().paintEvent(event)
