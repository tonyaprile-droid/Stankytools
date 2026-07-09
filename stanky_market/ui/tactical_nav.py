from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QPoint, Property, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget


@dataclass(frozen=True)
class TacticalTheme:
    name: str
    accent: str
    glow: str
    icon: str


TACTICAL_THEMES: dict[str, TacticalTheme] = {
    "green": TacticalTheme("Green", "#59D37A", "#59D37A", "#59D37A"),
    "gold": TacticalTheme("Gold", "#D9B45D", "#D9B45D", "#D9B45D"),
    "purple": TacticalTheme("Purple", "#A06BFF", "#A06BFF", "#A06BFF"),
    "red": TacticalTheme("Red", "#E25555", "#E25555", "#E25555"),
}

NAV_ITEMS = [
    ("dashboard", "Dashboard", "Command Overview", "dashboard"),
    ("guild", "Guild Admin", "Roster & Operations", "guild"),
    ("database", "Database", "Item Intelligence", "database"),
    ("auction", "Auction House", "Market Watch", "auction"),
    ("deep_desert", "Deep Desert", "Tactical Map", "map"),
    ("hagga", "Hagga Basin", "Base Network", "base"),
    ("settings", "Settings", "System Control", "settings"),
]

SVG_ICONS: dict[str, str] = {
    "dashboard": "<svg viewBox='0 0 24 24'><path d='M4 13h7V4H4v9zm9 7h7V4h-7v16zM4 20h7v-5H4v5z'/></svg>",
    "guild": "<svg viewBox='0 0 24 24'><path d='M12 3l7 4v5c0 4.5-2.8 7.8-7 9-4.2-1.2-7-4.5-7-9V7l7-4z'/></svg>",
    "database": "<svg viewBox='0 0 24 24'><ellipse cx='12' cy='5' rx='7' ry='3'/><path d='M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6'/></svg>",
    "auction": "<svg viewBox='0 0 24 24'><path d='M4 19h16M7 15l5-5M10 18l5-5M6 8l4-4 10 10-4 4L6 8z'/></svg>",
    "map": "<svg viewBox='0 0 24 24'><path d='M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2V6zM9 4v14M15 6v14'/></svg>",
    "base": "<svg viewBox='0 0 24 24'><path d='M3 20h18M5 20V9l7-5 7 5v11M9 20v-7h6v7'/></svg>",
    "settings": "<svg viewBox='0 0 24 24'><path d='M12 8a4 4 0 100 8 4 4 0 000-8z'/><path d='M4 12h2m12 0h2M12 4v2m0 12v2M6.3 6.3l1.4 1.4m8.6 8.6l1.4 1.4M17.7 6.3l-1.4 1.4m-8.6 8.6l-1.4 1.4'/></svg>",
}


def recolored_svg(name: str, color: str) -> bytes:
    raw = SVG_ICONS.get(name, SVG_ICONS["dashboard"])
    raw = raw.replace("<path", f"<path fill='none' stroke='{color}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'")
    raw = raw.replace("<ellipse", f"<ellipse fill='none' stroke='{color}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'")
    return raw.encode("utf-8")


class HexIcon(QFrame):
    def __init__(self, icon_name: str, theme: TacticalTheme, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.theme = theme
        self.setFixedSize(42, 42)
        self.svg = QSvgWidget(self)
        self.svg.setGeometry(9, 9, 24, 24)
        self.svg.load(recolored_svg(icon_name, theme.icon))
        self._glow = 0

    def set_theme(self, theme: TacticalTheme) -> None:
        self.theme = theme
        self.svg.load(recolored_svg(self.icon_name, theme.icon))
        self.update()

    def set_glow(self, value: int) -> None:
        self._glow = value
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        accent = QColor(self.theme.accent)
        if self._glow:
            accent = accent.lighter(120)
        points = [
            QPoint(21, 2), QPoint(38, 11), QPoint(38, 31),
            QPoint(21, 40), QPoint(4, 31), QPoint(4, 11),
        ]
        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
        path.closeSubpath()
        bg = QColor("#17191C")
        bg = bg.lighter(108 if self._glow else 100)
        painter.fillPath(path, bg)
        painter.setPen(QPen(accent, 1.2))
        painter.drawPath(path)


class TacticalNavItem(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, title: str, subtitle: str, icon: str, theme: TacticalTheme, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.key = key
        self.theme = theme
        self._selected = False
        self._hover_amount = 0
        self._arrow_offset = 0
        self.setFixedHeight(70)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("TacticalNavItem")

        self.hover_anim = QPropertyAnimation(self, b"hoverAmount", self)
        self.hover_anim.setDuration(135)
        self.hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.arrow_anim = QPropertyAnimation(self, b"arrowOffset", self)
        self.arrow_anim.setDuration(135)
        self.arrow_anim.setEasingCurve(QEasingCurve.OutCubic)

        row = QHBoxLayout(self)
        row.setContentsMargins(18, 8, 14, 8)
        row.setSpacing(14)

        self.hex_icon = HexIcon(icon, theme)
        row.addWidget(self.hex_icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("NavTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("NavSubtitle")
        text_col.addStretch()
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.subtitle_label)
        text_col.addStretch()
        row.addLayout(text_col, 1)

        self.arrow = QLabel(">")
        self.arrow.setObjectName("NavArrow")
        self.arrow.setFixedWidth(18)
        self.arrow.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.arrow)
        self._apply_text_styles()

    def _apply_text_styles(self) -> None:
        accent = self.theme.accent
        subtitle_color = QColor(accent)
        subtitle = f"rgba({subtitle_color.red()}, {subtitle_color.green()}, {subtitle_color.blue()}, 0.60)"
        subtitle_hover = f"rgba({subtitle_color.red()}, {subtitle_color.green()}, {subtitle_color.blue()}, 0.88)"
        sub = subtitle_hover if self._hover_amount or self._selected else subtitle
        self.title_label.setStyleSheet("color:#ECECEC; font-family:Orbitron; font-size:18px; font-weight:600; letter-spacing:1px; background:transparent;")
        self.subtitle_label.setStyleSheet(f"color:{sub}; font-family:Rajdhani; font-size:12px; font-weight:500; background:transparent;")
        self.arrow.setStyleSheet(f"color:{accent}; font-size:18px; font-weight:900; background:transparent; padding-left:{self._arrow_offset}px;")

    def set_theme(self, theme: TacticalTheme) -> None:
        self.theme = theme
        self.hex_icon.set_theme(theme)
        self._apply_text_styles()
        self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_text_styles()
        self.update()

    def enterEvent(self, event):
        self.hover_anim.stop(); self.arrow_anim.stop()
        self.hover_anim.setStartValue(self._hover_amount); self.hover_anim.setEndValue(1)
        self.arrow_anim.setStartValue(self._arrow_offset); self.arrow_anim.setEndValue(3)
        self.hover_anim.start(); self.arrow_anim.start()
        self.hex_icon.set_glow(1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.stop(); self.arrow_anim.stop()
        self.hover_anim.setStartValue(self._hover_amount); self.hover_anim.setEndValue(0)
        self.arrow_anim.setStartValue(self._arrow_offset); self.arrow_anim.setEndValue(0)
        self.hover_anim.start(); self.arrow_anim.start()
        self.hex_icon.set_glow(0)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)

    def get_hover_amount(self) -> int:
        return self._hover_amount

    def set_hover_amount(self, value: int) -> None:
        self._hover_amount = value
        self._apply_text_styles()
        self.update()

    hoverAmount = Property(int, get_hover_amount, set_hover_amount)

    def get_arrow_offset(self) -> int:
        return self._arrow_offset

    def set_arrow_offset(self, value: int) -> None:
        self._arrow_offset = value
        self._apply_text_styles()

    arrowOffset = Property(int, get_arrow_offset, set_arrow_offset)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3, 2, -3, -2)
        accent = QColor(self.theme.accent)
        bg = QColor("#1C2024") if self._hover_amount else QColor("#17191C")
        if self._selected:
            bg = QColor("#202429")
        path = QPainterPath()
        path.addRoundedRect(r, 11, 11)
        painter.fillPath(path, bg)
        painter.setPen(QPen(accent.lighter(125 if self._hover_amount else 105), 1.0))
        painter.drawPath(path)

        bar_w = 8 if self._hover_amount else 3
        if self._selected:
            bar_w = 8
        bar = QRect(r.left(), r.top() + 10, bar_w, r.height() - 20)
        painter.fillRect(bar, accent)

        if self._selected:
            painter.setPen(QPen(accent, 2))
            painter.drawLine(r.left() + 12, r.top(), r.right() - 12, r.top())
            painter.drawLine(r.left() + 12, r.bottom(), r.right() - 12, r.bottom())
        super().paintEvent(event)


class TacticalSidebar(QFrame):
    pageRequested = Signal(str)

    def __init__(self, theme_key: str = "gold", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme_key = self._normalize_theme(theme_key)
        self.theme = TACTICAL_THEMES[self.theme_key]
        self.items: dict[str, TacticalNavItem] = {}
        self.selected_key = "dashboard"
        self.setObjectName("TacticalSidebar")
        self.setMinimumWidth(330)
        self.setMaximumWidth(365)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(10)

        self.header = QLabel("STANKYTOOLS")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("color:#ECECEC; font-family:Orbitron; font-size:19px; font-weight:700; letter-spacing:3px; background:transparent;")
        layout.addWidget(self.header)

        self.subheader = QLabel("COMMAND SYSTEM")
        self.subheader.setAlignment(Qt.AlignCenter)
        self.subheader.setStyleSheet(f"color:{self.theme.accent}; font-family:Rajdhani; font-size:13px; font-weight:700; letter-spacing:2px; background:transparent;")
        layout.addWidget(self.subheader)
        layout.addSpacing(8)

        for key, title, subtitle, icon in NAV_ITEMS:
            item = TacticalNavItem(key, title, subtitle, icon, self.theme)
            item.clicked.connect(self._on_item_clicked)
            self.items[key] = item
            layout.addWidget(item)

        layout.addStretch()
        self.status = QLabel("●")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:#59D37A; font-size:18px; background:transparent;")
        layout.addWidget(self.status)
        self.set_selected("dashboard")

    def _normalize_theme(self, key: str) -> str:
        key = (key or "gold").strip().lower()
        aliases = {"dune": "gold", "atreides": "green", "harkonnen": "red", "spice": "purple"}
        return aliases.get(key, key if key in TACTICAL_THEMES else "gold")

    def _on_item_clicked(self, key: str) -> None:
        self.set_selected(key)
        self.pageRequested.emit(key)

    def set_selected(self, key: str) -> None:
        self.selected_key = key
        for item_key, item in self.items.items():
            item.set_selected(item_key == key)

    def set_theme(self, theme_key: str) -> None:
        self.theme_key = self._normalize_theme(theme_key)
        self.theme = TACTICAL_THEMES[self.theme_key]
        self.subheader.setStyleSheet(f"color:{self.theme.accent}; font-family:Rajdhani; font-size:13px; font-weight:700; letter-spacing:2px; background:transparent;")
        for item in self.items.values():
            item.set_theme(self.theme)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111214"))
        accent = QColor(self.theme.accent)
        painter.setPen(QPen(QColor("#25282C"), 1))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        painter.setPen(QPen(accent.darker(115), 2))
        painter.drawLine(1, 18, 1, self.height() - 18)
        super().paintEvent(event)
