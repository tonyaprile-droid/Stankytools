
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QPixmap, QPolygonF, QLinearGradient
from PySide6.QtWidgets import QAbstractButton, QFrame, QLabel, QVBoxLayout, QWidget, QSizePolicy

from .tactical_theme import normalize_theme_key

SIDEBAR_WIDTH = 300
NAV_BUTTON_HEIGHT = 50
NAV_BUTTON_SPACING = 12
NAV_ICON_BADGE_SIZE = 38
USER_PANEL_HEIGHT = 58
SETTINGS_PANEL_RADIUS = 16
SETTINGS_CARD_HEIGHT = 68
SETTINGS_CARD_SPACING = 18

# Background art opacity is intentionally code-only. Adjust these values (0.0-1.0) here.
SIDEBAR_BACKGROUND_IMAGE_OPACITY = 0.15
SETTINGS_BACKGROUND_IMAGE_OPACITY = 0.15

THEME_VISUALS = {
    "dune": {
        "label": "Dune",
        "primary": "#F5B928",
        "secondary": "#8C5B00",
        "border": "#F5B928",
        "glow": "rgba(245,185,40,150)",
        "panel": "rgba(15,13,9,222)",
        "background": "#0E0B07",
        "muted": "#B9A987",
    },
    "harkonnen": {
        "label": "Harkonnen Red",
        "primary": "#FF332B",
        "secondary": "#7A0909",
        "border": "#FF332B",
        "glow": "rgba(255,35,30,150)",
        "panel": "rgba(18,7,7,224)",
        "background": "#100606",
        "muted": "#B99A96",
    },
    "atreides": {
        "label": "Atreides Green",
        "primary": "#8DFF00",
        "secondary": "#325F00",
        "border": "#8DFF00",
        "glow": "rgba(120,255,0,150)",
        "panel": "rgba(7,16,5,224)",
        "background": "#071005",
        "muted": "#A7B99B",
    },
    "spice": {
        "label": "Spice Purple",
        "primary": "#C53DFF",
        "secondary": "#561080",
        "border": "#C53DFF",
        "glow": "rgba(190,45,255,150)",
        "panel": "rgba(14,6,20,224)",
        "background": "#0B0610",
        "muted": "#B7A0C9",
    },
    "spiced_up": {
        "label": "Psychedelic",
        "primary": "#21EAF2",
        "secondary": "#FF3DCD",
        "border": "#21EAF2",
        "accent": "#D9FF3C",
        "glow": "rgba(30,230,240,150)",
        "panel": "rgba(7,9,17,226)",
        "background": "#060812",
        "muted": "#BDEFF2",
    },
}

THEME_ORDER = ["dune", "harkonnen", "atreides", "spice", "spiced_up"]

ICON_TYPES = {
    "dashboard": "compass",
    "guild_admin": "shield",
    "guild": "tools",
    "tools": "tools",
    "target": "compass",
    "tweaks": "sliders",
    "database": "catalog",
    "settings": "gear",
    "game_manager": "sliders",
}


def visual_key(theme_key: str | None) -> str:
    return normalize_theme_key(theme_key)


def visual(theme_key: str | None) -> dict[str, str]:
    return THEME_VISUALS[visual_key(theme_key)]


def qcolor(value: str, fallback: QColor | None = None) -> QColor:
    c = QColor(value)
    return c if c.isValid() else (fallback or QColor("#F5B928"))


def with_alpha(color: QColor, alpha: int) -> QColor:
    c = QColor(color)
    c.setAlpha(max(0, min(255, alpha)))
    return c


def _first_existing(*paths: Path) -> Path:
    for candidate in paths:
        if candidate.exists():
            return candidate
    return paths[0]


def sidebar_asset_path(theme_key: str | None) -> Path:
    key = visual_key(theme_key)
    base = Path(__file__).resolve().parents[2] / "assets" / "sidebar"
    return _first_existing(base / f"sidebar_{key}.webp", base / f"sidebar_{key}.png")


def settings_asset_path(theme_key: str | None) -> Path:
    key = visual_key(theme_key)
    base = Path(__file__).resolve().parents[2] / "assets" / "settings"
    return _first_existing(base / f"settings_{key}.webp", base / f"settings_{key}.png")


class CoverImageMixin:
    _pixmap_cache: dict[str, QPixmap] = {}

    def _cover_pixmap(self, path: Path, size: QSize) -> QPixmap | None:
        if size.width() <= 0 or size.height() <= 0 or not path.exists():
            return None
        cache_key = f"{path}|{size.width()}x{size.height()}"
        cached = self._pixmap_cache.get(cache_key)
        if cached is not None and not cached.isNull():
            return cached
        pix = QPixmap(str(path))
        if pix.isNull():
            return None
        scaled = pix.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._pixmap_cache[cache_key] = scaled
        return scaled

    def _draw_cover(self, painter: QPainter, rect: QRectF, path: Path) -> None:
        pix = self._cover_pixmap(path, rect.size().toSize())
        if pix is None:
            return
        x = rect.x() + (rect.width() - pix.width()) / 2
        y = rect.y() + (rect.height() - pix.height()) / 2
        painter.drawPixmap(int(x), int(y), pix)


class ThemedSidebar(QFrame, CoverImageMixin):
    def __init__(self, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.theme_key = visual_key(theme_key)
        self.setObjectName("ImmersiveSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_theme(self, theme_key: str | None) -> None:
        self.theme_key = visual_key(theme_key)
        self.update()

    def refresh_theme_assets(self, theme_key: str | None = None) -> None:
        self.set_theme(theme_key)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect())
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        painter.fillRect(r, qcolor(v["background"]))
        painter.save()
        painter.setOpacity(SIDEBAR_BACKGROUND_IMAGE_OPACITY)
        self._draw_cover(painter, r, sidebar_asset_path(self.theme_key))
        painter.restore()
        # Tame the vivid art so the mascot and navigation remain readable.
        veil = QLinearGradient(r.topLeft(), r.bottomLeft())
        veil.setColorAt(0.0, QColor(0, 0, 0, 120))
        veil.setColorAt(0.34, QColor(0, 0, 0, 92))
        veil.setColorAt(0.74, QColor(0, 0, 0, 102))
        veil.setColorAt(1.0, QColor(0, 0, 0, 142))
        painter.fillRect(r, veil)
        panel = QRectF(12, 24, self.width() - 24, min(430, self.height() - 48))
        painter.fillRect(panel, QColor(0, 0, 0, 70))
        painter.setPen(QPen(with_alpha(accent, 105), 1))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        super().paintEvent(event)



class NavGlyph(QWidget):
    def __init__(self, glyph_type: str, parent=None):
        super().__init__(parent)
        self.glyph_type = glyph_type
        self.theme_key = "dune"
        self.active = False
        self.hover = False
        self.setFixedSize(NAV_ICON_BADGE_SIZE, NAV_ICON_BADGE_SIZE)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_state(self, theme_key: str | None = None, *, active: bool | None = None, hover: bool | None = None):
        if theme_key is not None:
            self.theme_key = visual_key(theme_key)
        if active is not None:
            self.active = active
        if hover is not None:
            self.hover = hover
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        secondary = qcolor(v.get("accent", v.get("secondary", v["primary"]))) if self.theme_key == "spiced_up" else accent
        badge = QPolygonF([
            QPointF(r.center().x(), r.top()), QPointF(r.right() - 9, r.top() + 7), QPointF(r.right(), r.center().y()),
            QPointF(r.right() - 9, r.bottom() - 7), QPointF(r.center().x(), r.bottom()), QPointF(r.left() + 9, r.bottom() - 7),
            QPointF(r.left(), r.center().y()), QPointF(r.left() + 9, r.top() + 7),
        ])
        fill = QColor(0, 0, 0, 136 if self.active else 104)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(with_alpha(accent, 220 if self.active or self.hover else 150), 1.25))
        painter.drawPolygon(badge)
        pen = QPen(secondary if self.theme_key == "spiced_up" else accent, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        self._draw_icon(painter, QRectF(14, 14, self.width() - 28, self.height() - 28))

    def _draw_icon(self, p: QPainter, r: QRectF) -> None:
        cx, cy = r.center().x(), r.center().y()
        t = self.glyph_type
        if t == "compass":
            p.drawEllipse(r.adjusted(2, 2, -2, -2))
            needle = QPolygonF([QPointF(cx, r.top() + 2), QPointF(cx + 4, cy + 3), QPointF(cx, cy + 1), QPointF(cx - 4, cy + 3)])
            p.drawPolygon(needle)
            p.drawLine(QPointF(cx, cy + 4), QPointF(cx, r.bottom() - 2))
        elif t == "cube":
            top = QPolygonF([QPointF(cx, r.top()), QPointF(r.right(), cy - 5), QPointF(cx, cy), QPointF(r.left(), cy - 5)])
            left = QPolygonF([QPointF(r.left(), cy - 5), QPointF(cx, cy), QPointF(cx, r.bottom()), QPointF(r.left(), cy + 5)])
            right = QPolygonF([QPointF(r.right(), cy - 5), QPointF(cx, cy), QPointF(cx, r.bottom()), QPointF(r.right(), cy + 5)])
            p.drawPolygon(top); p.drawPolygon(left); p.drawPolygon(right)
        elif t == "swords":
            p.drawLine(QPointF(r.left()+2, r.bottom()-2), QPointF(r.right()-2, r.top()+2))
            p.drawLine(QPointF(r.left()+2, r.top()+2), QPointF(r.right()-2, r.bottom()-2))
            p.drawLine(QPointF(cx-8, cy+8), QPointF(cx-2, cy+14)); p.drawLine(QPointF(cx+8, cy+8), QPointF(cx+2, cy+14))
        elif t == "tools":
            p.drawLine(QPointF(r.left()+2, r.bottom()-3), QPointF(r.right()-3, r.top()+3))
            p.drawLine(QPointF(r.left()+3, r.top()+4), QPointF(r.right()-2, r.bottom()-4))
            p.drawEllipse(QRectF(r.left(), r.bottom()-7, 7, 7)); p.drawEllipse(QRectF(r.right()-7, r.bottom()-7, 7, 7))
        elif t == "catalog":
            p.drawRoundedRect(r.adjusted(2, 3, -2, -3), 3, 3)
            p.drawLine(QPointF(r.left()+7, r.top()+7), QPointF(r.right()-5, r.top()+7))
            p.drawLine(QPointF(r.left()+7, cy), QPointF(r.right()-5, cy))
            p.drawLine(QPointF(r.left()+7, r.bottom()-7), QPointF(r.right()-5, r.bottom()-7))
        elif t == "game":
            p.drawRoundedRect(r.adjusted(0, 5, 0, -4), 7, 7)
            p.drawLine(QPointF(r.left()+5, cy), QPointF(r.left()+13, cy)); p.drawLine(QPointF(r.left()+9, cy-4), QPointF(r.left()+9, cy+4))
            p.drawEllipse(QRectF(r.right()-13, cy-5, 4, 4)); p.drawEllipse(QRectF(r.right()-7, cy+1, 4, 4))
        elif t == "refresh":
            p.drawArc(r.adjusted(2,2,-2,-2), 35*16, 250*16); p.drawArc(r.adjusted(2,2,-2,-2), 215*16, 250*16)
            p.drawLine(QPointF(r.right()-4, cy-9), QPointF(r.right()-1, cy-1)); p.drawLine(QPointF(r.right()-4, cy-9), QPointF(r.right()-12, cy-8))
        elif t == "shield":
            path=QPainterPath(); path.moveTo(cx,r.top()+1); path.lineTo(r.right()-2,r.top()+6); path.lineTo(r.right()-5,cy+8); path.lineTo(cx,r.bottom()-1); path.lineTo(r.left()+5,cy+8); path.lineTo(r.left()+2,r.top()+6); path.closeSubpath(); p.drawPath(path)
        elif t == "sliders":
            for y, knob_x in ((r.top() + 4, cx + 5), (cy, cx - 5), (r.bottom() - 4, cx + 2)):
                p.drawLine(QPointF(r.left() + 2, y), QPointF(r.right() - 2, y))
                p.drawEllipse(QRectF(knob_x - 3, y - 3, 6, 6))
        elif t == "bulb":
            p.drawEllipse(QRectF(cx-8,r.top()+1,16,16)); p.drawLine(QPointF(cx-5,cy+7),QPointF(cx+5,cy+7)); p.drawLine(QPointF(cx-4,cy+12),QPointF(cx+4,cy+12))
        elif t == "heart":
            path=QPainterPath(); path.moveTo(cx, r.bottom()-2); path.cubicTo(r.left()-2, cy, r.left()+2, r.top(), cx, cy-3); path.cubicTo(r.right()-2, r.top(), r.right()+2, cy, cx, r.bottom()-2); p.drawPath(path)
        else:
            p.drawEllipse(r.adjusted(3, 3, -3, -3))


class AngularNavButton(QAbstractButton):
    clicked = Signal(bool)

    def __init__(self, icon_name: str, title: str, subtitle: str, page_index: int, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.theme_key = visual_key(theme_key)
        self.icon_name = ICON_TYPES.get(icon_name, icon_name)
        self.page_index = page_index
        self.active = False
        self.hover = False
        self.pressed_inside = False
        self.setText(title)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(NAV_BUTTON_HEIGHT)
        self.setMinimumWidth(270)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.icon = NavGlyph(self.icon_name, self)
        self.icon.move(12, 6)

    def resizeEvent(self, event):
        self.icon.move(14, max(0, (self.height() - NAV_ICON_BADGE_SIZE) // 2))
        super().resizeEvent(event)

    def set_active(self, active: bool):
        self.active = bool(active)
        self.setProperty("active", self.active)
        self.icon.set_state(self.theme_key, active=self.active, hover=self.hover)
        self.update()

    def set_theme_accent(self, accent_color: str):
        self.update()

    def set_theme(self, theme_key: str | None):
        self.theme_key = visual_key(theme_key)
        self.icon.set_state(self.theme_key, active=self.active, hover=self.hover)
        self.update()

    def enterEvent(self, event):
        self.hover = True
        self.icon.set_state(hover=True)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover = False
        self.pressed_inside = False
        self.icon.set_state(hover=False)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed_inside = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.pressed_inside = False
        self.update()
        super().mouseReleaseEvent(event)

    def _shape(self) -> QPainterPath:
        r = QRectF(22, 5, self.width() - 32, self.height() - 10)
        path = QPainterPath()
        path.moveTo(r.left() + 18, r.top())
        path.lineTo(r.right() - 19, r.top())
        path.lineTo(r.right(), r.center().y())
        path.lineTo(r.right() - 19, r.bottom())
        path.lineTo(r.left() + 10, r.bottom())
        path.lineTo(r.left(), r.center().y())
        path.closeSubpath()
        return path

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        secondary = qcolor(v.get("secondary", v["primary"]))
        shape = self._shape()

        if self.active or self.hover:
            p.setPen(QPen(with_alpha(accent, 78 if self.active else 52), 8))
            p.drawPath(shape)

        fill = QLinearGradient(QPointF(30, 0), QPointF(self.width() - 10, 0))
        fill.setColorAt(0.0, QColor(0, 0, 0, 194 if self.active else 148))
        fill.setColorAt(0.55, QColor(0, 0, 0, 156 if self.active else 118))
        fill.setColorAt(1.0, QColor(0, 0, 0, 118 if self.active else 82))
        if self.hover:
            fill.setColorAt(1.0, with_alpha(accent, 38))
        if self.pressed_inside:
            fill.setColorAt(0.0, QColor(0, 0, 0, 210))
        p.setBrush(QBrush(fill))
        p.setPen(QPen(with_alpha(accent, 240 if self.active else (208 if self.hover else 152)), 1.3))
        p.drawPath(shape)

        if self.theme_key == "spiced_up":
            p.setPen(QPen(with_alpha(secondary, 145), 1.0))
            p.drawPath(shape.translated(0, 1))

        dx = 2 if self.hover else 0
        yoff = 1 if self.pressed_inside else 0
        font = QFont("Rajdhani", 13, QFont.Bold)
        font.setLetterSpacing(QFont.PercentageSpacing, 104)
        p.setFont(font)
        p.setPen(QColor("#FFFFFF"))
        text_rect = QRectF(72 + dx, yoff, self.width() - 86, self.height())
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


class SidebarUserPanel(QFrame):
    def __init__(self, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.theme_key = visual_key(theme_key)
        self.name = "PLAYER"
        self.online = True
        self.setFixedHeight(USER_PANEL_HEIGHT)
        self.setMinimumWidth(248)
        self.setMaximumWidth(260)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_theme(self, theme_key: str | None):
        self.theme_key = visual_key(theme_key)
        self.update()

    def set_user(self, name: str, online: bool = True):
        self.name = (name or "PLAYER").upper()
        self.online = bool(online)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        v = visual(self.theme_key); accent = qcolor(v["primary"])
        r = QRectF(3, 5, self.width()-6, self.height()-10)
        p.setPen(QPen(with_alpha(accent, 75), 8)); p.drawRoundedRect(r, 23, 23)
        p.setBrush(QColor(0,0,0,150)); p.setPen(QPen(with_alpha(accent,190),1.2)); p.drawRoundedRect(r,23,23)
        icon_r = QRectF(r.left()+18, r.top()+13, 22, 22)
        p.setPen(QPen(accent, 2)); p.setBrush(with_alpha(accent, 50)); p.drawEllipse(icon_r.adjusted(5,0,-5,-10)); p.drawRoundedRect(icon_r.adjusted(1,12,-1,3),5,5)
        font=QFont("Rajdhani",17,QFont.Bold); font.setLetterSpacing(QFont.PercentageSpacing,105); p.setFont(font); p.setPen(accent)
        p.drawText(QRectF(r.left()+66,r.top(),r.width()-110,r.height()), Qt.AlignVCenter|Qt.AlignLeft, self.name)
        p.setBrush(QColor("#35D35D") if self.online else QColor("#777777")); p.setPen(Qt.NoPen); p.drawEllipse(QRectF(r.right()-36,r.center().y()-7,14,14))
        super().paintEvent(event)


class SettingsBackdrop(QWidget, CoverImageMixin):
    def __init__(self, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.theme_key = visual_key(theme_key)
        self.background_opacity = SETTINGS_BACKGROUND_IMAGE_OPACITY
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_theme(self, theme_key: str | None):
        self.theme_key = visual_key(theme_key)
        self.update()

    def refresh_theme_assets(self, theme_key: str | None = None):
        self.set_theme(theme_key)

    def set_background_opacity(self, value: float | int):
        try:
            numeric = float(value)
        except Exception:
            numeric = SETTINGS_BACKGROUND_IMAGE_OPACITY
        if numeric > 1.0:
            numeric /= 100.0
        self.background_opacity = max(0.0, min(1.0, numeric))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect())
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        p.fillRect(r, qcolor(v["background"]))
        p.save()
        p.setOpacity(self.background_opacity)
        self._draw_cover(p, r, settings_asset_path(self.theme_key))
        p.restore()
        wash = QLinearGradient(r.topLeft(), r.bottomRight())
        wash.setColorAt(0.0, QColor(0, 0, 0, 138))
        wash.setColorAt(0.48, QColor(0, 0, 0, 170))
        wash.setColorAt(1.0, QColor(0, 0, 0, 205))
        p.fillRect(r, wash)
        p.setPen(QPen(with_alpha(accent, 46), 1))
        p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
        super().paintEvent(event)


class SettingsPanel(QFrame):
    def __init__(self, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.theme_key = visual_key(theme_key)
        self.background_opacity = 0.70
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_theme(self, theme_key: str | None):
        self.theme_key = visual_key(theme_key)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        p.setPen(QPen(with_alpha(accent, 34), 12))
        p.drawRoundedRect(r, SETTINGS_PANEL_RADIUS, SETTINGS_PANEL_RADIUS)
        fill = QLinearGradient(r.topLeft(), r.bottomRight())
        fill.setColorAt(0.0, QColor(24, 22, 17, 214))
        fill.setColorAt(0.54, QColor(13, 13, 12, 224))
        fill.setColorAt(1.0, QColor(30, 26, 18, 204))
        if self.theme_key != "dune":
            fill.setColorAt(0.0, with_alpha(qcolor(v["background"]), 226))
            fill.setColorAt(1.0, QColor(5, 5, 7, 218))
        p.setBrush(QBrush(fill))
        p.setPen(QPen(with_alpha(accent, 170), 1.15))
        p.drawRoundedRect(r, SETTINGS_PANEL_RADIUS, SETTINGS_PANEL_RADIUS)
        super().paintEvent(event)


class SettingsHeaderIcon(QWidget):
    def __init__(self, icon_type: str, theme_key: str = "dune", parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.theme_key = visual_key(theme_key)
        self.setFixedSize(30, 30)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_theme(self, theme_key: str | None):
        self.theme_key = visual_key(theme_key)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        accent = qcolor(visual(self.theme_key)["primary"])
        r = QRectF(4, 4, self.width() - 8, self.height() - 8)
        p.setPen(QPen(accent, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        cx, cy = r.center().x(), r.center().y()
        if self.icon_type == "palette":
            p.drawEllipse(r.adjusted(1, 1, -1, -1))
            for x, y in ((cx - 7, cy - 5), (cx, cy - 8), (cx + 7, cy - 3), (cx - 2, cy + 6)):
                p.drawEllipse(QRectF(x - 1.8, y - 1.8, 3.6, 3.6))
            p.drawArc(QRectF(cx + 3, cy + 5, 7, 7), 20 * 16, 230 * 16)
        else:
            p.drawLine(QPointF(r.left() + 4, r.bottom() - 3), QPointF(r.right() - 3, r.top() + 4))
            p.drawLine(QPointF(r.left() + 6, r.top() + 6), QPointF(r.right() - 5, r.bottom() - 5))
            p.drawLine(QPointF(r.left() + 2, r.top() + 12), QPointF(r.left() + 10, r.top() + 4))
            p.drawLine(QPointF(r.right() - 12, r.bottom() - 2), QPointF(r.right() - 4, r.bottom() - 10))


class ThemeSelectionCard(QAbstractButton):
    selectedTheme = Signal(str)
    def __init__(self, key: str, label: str, active_key: str = "dune", parent=None):
        super().__init__(parent)
        self.key=visual_key(key); self.active_key=visual_key(active_key); self.hover=False; self.pressed_inside=False
        self.setText(label); self.setCursor(Qt.PointingHandCursor); self.setFixedHeight(54); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

    def set_active_theme(self, key: str | None): self.active_key=visual_key(key); self.update()
    def enterEvent(self,e): self.hover=True; self.update(); super().enterEvent(e)
    def leaveEvent(self,e): self.hover=False; self.pressed_inside=False; self.update(); super().leaveEvent(e)
    def mousePressEvent(self,e): self.pressed_inside=True; self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self,e):
        self.pressed_inside=False; self.update()
        if e.button()==Qt.LeftButton and self.rect().contains(e.pos()): self.selectedTheme.emit(self.key)
        super().mouseReleaseEvent(e)
    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        vv = visual(self.key)
        accent = qcolor(vv["primary"])
        selected = self.key == self.active_key
        r = QRectF(1, 2, self.width() - 2, self.height() - 4)
        if selected:
            p.setPen(QPen(with_alpha(accent, 42), 8))
            p.drawRoundedRect(r, 8, 8)
        fill = QLinearGradient(r.topLeft(), r.bottomRight())
        fill.setColorAt(0, QColor(21, 19, 15, 178 if selected else 132))
        fill.setColorAt(1, QColor(5, 5, 5, 168 if selected else 116))
        p.setBrush(QBrush(fill))
        p.setPen(QPen(with_alpha(accent, 230 if selected else (150 if self.hover else 78)), 1.25))
        p.drawRoundedRect(r, 7, 7)

        p.setFont(QFont("Rajdhani", 14, QFont.Bold))
        p.setPen(accent)
        p.drawText(QRectF(r.left() + 16, r.top(), r.width() - 54, r.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        ind = QRectF(r.right() - 31, r.center().y() - 9, 18, 18)
        p.setBrush(with_alpha(accent, 52 if selected else 0))
        p.setPen(QPen(with_alpha(accent, 225 if selected else 112), 2))
        p.drawEllipse(ind)
        if selected:
            p.drawLine(QPointF(ind.left() + 4, ind.center().y()), QPointF(ind.center().x() - 1, ind.bottom() - 4))
            p.drawLine(QPointF(ind.center().x() - 1, ind.bottom() - 4), QPointF(ind.right() - 4, ind.top() + 4))



class SettingsActionCard(QAbstractButton):
    def __init__(self, title: str, description: str, icon_type: str, theme_key: str = "dune", parent=None):
        super().__init__(parent); self.theme_key=visual_key(theme_key); self.description=description; self.icon_type=icon_type; self.hover=False; self.busy=False; self.pressed_inside=False
        self.setText(title); self.setCursor(Qt.PointingHandCursor); self.setFixedHeight(SETTINGS_CARD_HEIGHT); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
    def set_theme(self,key): self.theme_key=visual_key(key); self.update()
    def set_busy(self,busy:bool,text:str|None=None): self.busy=bool(busy); self.setEnabled(not busy); self.update()
    def enterEvent(self,e): self.hover=True; self.update(); super().enterEvent(e)
    def leaveEvent(self,e): self.hover=False; self.pressed_inside=False; self.update(); super().leaveEvent(e)
    def mousePressEvent(self,e): self.pressed_inside=True; self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self,e): self.pressed_inside=False; self.update(); super().mouseReleaseEvent(e)
    def _draw_action_icon(self, p: QPainter, rect: QRectF, accent: QColor) -> None:
        p.setPen(QPen(accent, 2.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        cx, cy = rect.center().x(), rect.center().y()
        if self.icon_type == "refresh":
            p.drawArc(rect.adjusted(7, 7, -7, -7), 35 * 16, 245 * 16)
            p.drawArc(rect.adjusted(7, 7, -7, -7), 215 * 16, 245 * 16)
            p.drawLine(QPointF(rect.right() - 12, cy - 16), QPointF(rect.right() - 3, cy - 5))
            p.drawLine(QPointF(rect.right() - 12, cy - 16), QPointF(rect.right() - 23, cy - 13))
        elif self.icon_type == "shield":
            path = QPainterPath(); path.moveTo(cx, rect.top() + 8); path.lineTo(rect.right() - 10, rect.top() + 16); path.lineTo(rect.right() - 15, cy + 17); path.lineTo(cx, rect.bottom() - 7); path.lineTo(rect.left() + 15, cy + 17); path.lineTo(rect.left() + 10, rect.top() + 16); path.closeSubpath(); p.drawPath(path)
        elif self.icon_type == "bulb":
            p.drawEllipse(QRectF(cx - 14, rect.top() + 7, 28, 28)); p.drawLine(QPointF(cx - 9, cy + 15), QPointF(cx + 9, cy + 15)); p.drawLine(QPointF(cx - 6, cy + 22), QPointF(cx + 6, cy + 22))
        elif self.icon_type == "heart":
            path = QPainterPath(); path.moveTo(cx, rect.bottom() - 10); path.cubicTo(rect.left() + 3, cy, rect.left() + 8, rect.top() + 8, cx, cy - 5); path.cubicTo(rect.right() - 8, rect.top() + 8, rect.right() - 3, cy, cx, rect.bottom() - 10); p.drawPath(path)
        else:
            NavGlyph(self.icon_type)._draw_icon(p, rect.adjusted(16, 16, -16, -16))

    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        r = QRectF(1, 3, self.width() - 2, self.height() - 6)
        if self.hover:
            p.setPen(QPen(with_alpha(accent, 38), 8)); p.drawRoundedRect(r, 9, 9)
        fill = QLinearGradient(r.topLeft(), r.bottomRight())
        fill.setColorAt(0, QColor(24, 22, 18, 150 if not self.pressed_inside else 122))
        fill.setColorAt(1, QColor(8, 8, 8, 138 if not self.pressed_inside else 112))
        p.setBrush(QBrush(fill))
        p.setPen(QPen(with_alpha(accent, 178 if self.hover else 96), 1.05))
        p.drawRoundedRect(r, 9, 9)

        dx = 4 if self.hover else 0
        yoff = 1 if self.pressed_inside else 0
        p.setPen(accent)
        # Match the ThemeSelectionCard link typography exactly.
        p.setFont(QFont("Rajdhani", 14, QFont.Bold))
        title_rect = QRectF(r.left() + 18 + dx, r.top() + yoff, r.width() - 76, r.height())
        p.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, "Working..." if self.busy else self.text())
        p.setPen(QPen(accent, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        cx = r.right() - 26 + (3 if self.hover else 0)
        cy = r.center().y()
        p.drawLine(QPointF(cx - 5, cy - 7), QPointF(cx + 5, cy))
        p.drawLine(QPointF(cx + 5, cy), QPointF(cx - 5, cy + 7))



class UpdateStatusCard(QAbstractButton):
    def __init__(self, theme_key: str = "dune", parent=None):
        super().__init__(parent); self.theme_key=visual_key(theme_key); self.status_text="You are up to date"; self.hover=False; self.setCursor(Qt.PointingHandCursor); self.setFixedHeight(28); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
    def set_theme(self,key): self.theme_key=visual_key(key); self.update()
    def setText(self,text:str): self.status_text=str(text or ""); self.update()
    def text(self): return self.status_text
    def enterEvent(self,e): self.hover=True; self.update(); super().enterEvent(e)
    def leaveEvent(self,e): self.hover=False; self.update(); super().leaveEvent(e)
    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        v = visual(self.theme_key)
        accent = qcolor(v["primary"])
        r = QRectF(0, 3, self.width(), self.height() - 6)
        p.setBrush(QColor(0, 0, 0, 78))
        p.setPen(QPen(with_alpha(accent, 130 if self.hover else 78), 1.0))
        p.drawRoundedRect(r, 8, 8)
        p.setPen(QPen(accent, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        cx = r.left() + 20
        cy = r.center().y()
        p.drawLine(QPointF(cx, cy - 10), QPointF(cx, cy + 5))
        p.drawLine(QPointF(cx - 7, cy - 1), QPointF(cx, cy + 7))
        p.drawLine(QPointF(cx + 7, cy - 1), QPointF(cx, cy + 7))
        p.drawLine(QPointF(cx - 10, cy + 11), QPointF(cx + 10, cy + 11))
        p.setFont(QFont("Rajdhani", 11, QFont.Bold))
        p.setPen(accent if "available" in self.status_text.lower() or "checking" in self.status_text.lower() else QColor("#B9B0A4"))
        p.drawText(QRectF(r.left() + 36, r.top(), r.width() - 44, r.height()), Qt.AlignVCenter | Qt.AlignLeft, self.status_text)

