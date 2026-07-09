from __future__ import annotations

import math
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Property, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QFont, QPolygonF
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QWidget

from .tactical_theme import theme_colors

class TacticalBanner(QFrame):
    """Programmatic banner: no background image assets."""
    def __init__(self, title: str = "STANKYTOOLS", subtitle: str = "COMMAND CENTER", theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.theme_key = theme_key
        self.setMinimumHeight(122)
        self.setObjectName("TacticalBanner")

    def set_theme(self, theme_key: str):
        self.theme_key = theme_key
        self.update()

    def set_text(self, title: str, subtitle: str = ""):
        self.title = title
        self.subtitle = subtitle
        self.update()

    def paintEvent(self, event):
        c = theme_colors(self.theme_key)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        accent = QColor(c["accent"])
        bg = QColor(c["bg"])
        panel = QColor(c["panel"])
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0, bg.lighter(105))
        grad.setColorAt(0.45, panel)
        grad.setColorAt(1, bg.darker(125))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(accent, 1.4))
        p.drawRoundedRect(r, 14, 14)
        # subtle tactical grid lines
        grid_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 38), 1)
        p.setPen(grid_pen)
        step = 42
        for x in range(0, self.width(), step):
            p.drawLine(x, 0, x + 34, self.height())
        # corner brackets
        p.setPen(QPen(accent, 2))
        pad = 14; ln = 34
        for sx, sy in [(pad,pad), (self.width()-pad,pad), (pad,self.height()-pad), (self.width()-pad,self.height()-pad)]:
            dx = ln if sx == pad else -ln
            dy = ln if sy == pad else -ln
            p.drawLine(sx, sy, sx + dx, sy)
            p.drawLine(sx, sy, sx, sy + dy)
        # geometric worm/orb accent
        p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 70), 2))
        for i in range(5):
            rr = QRectF(self.width() - 230 + i*24, 28 + math.sin(i)*5, 58, 58)
            p.drawEllipse(rr)
        p.setPen(QPen(QColor(c["text"]), 1))
        font = QFont("Orbitron", 18, QFont.Weight.DemiBold)
        p.setFont(font)
        p.drawText(QRectF(32, 28, self.width()-64, 34), Qt.AlignLeft | Qt.AlignVCenter, self.title.upper())
        font = QFont("Rajdhani", 12, QFont.Weight.Medium)
        p.setFont(font)
        p.setPen(QPen(QColor(c["muted"]), 1))
        p.drawText(QRectF(34, 65, self.width()-68, 26), Qt.AlignLeft | Qt.AlignVCenter, self.subtitle.upper())
        super().paintEvent(event)

class HexIcon(QFrame):
    def __init__(self, glyph: str = "◇", theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.glyph = glyph
        self.theme_key = theme_key
        self.setFixedSize(42, 42)

    def set_theme(self, theme_key: str):
        self.theme_key = theme_key
        self.update()

    def paintEvent(self, event):
        c = theme_colors(self.theme_key)
        accent = QColor(c["accent"])
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        poly = QPolygonF([
            (w*0.50, 2), (w-6, h*0.25), (w-6, h*0.75),
            (w*0.50, h-2), (6, h*0.75), (6, h*0.25)
        ])
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(c["panel_hover"]))
        grad.setColorAt(1, QColor(c["panel"]))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(accent, 1.3))
        p.drawPolygon(poly)
        p.setPen(QPen(accent, 1))
        font = QFont("Segoe UI Symbol", 16, QFont.Weight.DemiBold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignCenter, self.glyph)

class TacticalNavButton(QFrame):
    def __init__(self, glyph: str, title: str, subtitle: str, page_index: int, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.theme_key = theme_key
        self.page_index = page_index
        self._active = False
        self._hover = 0.0
        self.setObjectName("TacticalNavButton")
        self.setMinimumHeight(68)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        self.icon = HexIcon(glyph, theme_key)
        layout.addWidget(self.icon)
        text = QVBoxLayout(); text.setSpacing(1)
        self.title_label = QLabel(title.upper()); self.title_label.setObjectName("NavTitle")
        self.subtitle_label = QLabel(subtitle); self.subtitle_label.setObjectName("NavSub")
        text.addWidget(self.title_label); text.addWidget(self.subtitle_label)
        layout.addLayout(text, 1)
        self.arrow = QLabel("›"); self.arrow.setObjectName("NavChevron")
        layout.addWidget(self.arrow)
        self.anim = QPropertyAnimation(self, b"hoverAmount", self)
        self.anim.setDuration(140)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def getHoverAmount(self): return self._hover
    def setHoverAmount(self, v): self._hover = v; self.update()
    hoverAmount = Property(float, getHoverAmount, setHoverAmount)

    def set_theme(self, theme_key: str):
        self.theme_key = theme_key; self.icon.set_theme(theme_key); self.update()

    def set_active(self, active: bool):
        self._active = bool(active); self.update()

    def enterEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._hover); self.anim.setEndValue(1.0); self.anim.start(); super().enterEvent(e)
    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._hover); self.anim.setEndValue(0.0); self.anim.start(); super().leaveEvent(e)

    def paintEvent(self, event):
        c = theme_colors(self.theme_key)
        accent = QColor(c["accent"])
        base = QColor(c["panel_hover"] if self._active or self._hover > 0 else c["panel"])
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width()-1, self.height()-1)
        p.setBrush(QBrush(base))
        alpha = 190 if self._active else int(80 + self._hover * 90)
        p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), alpha), 1.2 if not self._active else 1.8))
        p.drawRoundedRect(r, 11, 11)
        bar_w = 8 if self._active else 3 + self._hover * 5
        p.fillRect(QRectF(0, 10, bar_w, self.height()-20), accent)
        if self._active:
            p.fillRect(QRectF(14, 0, self.width()-28, 2), accent)
            p.fillRect(QRectF(14, self.height()-2, self.width()-28, 2), accent)
        super().paintEvent(event)
