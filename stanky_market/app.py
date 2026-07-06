from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Any
import json
import uuid
import urllib.request
import urllib.parse
import random
import string
import base64
import time

from PySide6.QtCore import Qt, QSize, QTimer, QPointF, QThread, Signal
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QBrush, QPen, QFont, QWheelEvent, QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsPixmapItem,
    QInputDialog,
    QCheckBox,
    QMenu,
    QFileDialog,
    QProgressBar,
)

from . import db, deep_desert, guild_config, updater

APP_TITLE = "StankyTools"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"

def asset_path(*parts: str) -> Path:
    return ASSETS_DIR.joinpath(*parts)

def qss_path(path: Path) -> str:
    return path.resolve().as_posix()


def format_app_date(value: str) -> str:
    """Format timestamps like 2026-07-06T12:34:56 as 7-6-2026."""
    raw = str(value or "").strip()
    if not raw:
        return "—"
    date_part = raw.split("T", 1)[0].split(" ", 1)[0]
    try:
        year, month, day = date_part.split("-")[:3]
        return f"{int(month)}-{int(day)}-{int(year)}"
    except Exception:
        return raw[:10] or "—"


def resolve_local_path(value: str) -> Path:
    """Resolve a path saved by StankyTools, handling absolute and project-relative values."""
    raw = (value or "").strip()
    if not raw:
        return Path()
    p = Path(raw)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


CATALOG_PIXMAP_CACHE: dict[tuple[str, int], QPixmap] = {}

def catalog_image_pixmap(image_path: str, size: int = 64) -> QPixmap:
    """Return a square thumbnail pixmap for catalog rows, with a fallback placeholder.

    Thumbnails are cached because repeatedly decoding hundreds of images was a
    major source of UI lag when switching tabs or searching the catalog.
    """
    cache_key = (str(image_path or ""), int(size))
    cached = CATALOG_PIXMAP_CACHE.get(cache_key)
    if cached is not None and not cached.isNull():
        return cached

    candidates = []
    if image_path:
        candidates.append(resolve_local_path(image_path))
    candidates.append(asset_path("icons", "default_item.png"))
    for candidate in candidates:
        try:
            if candidate and candidate.exists():
                pix = QPixmap(str(candidate))
                if not pix.isNull():
                    thumb = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    CATALOG_PIXMAP_CACHE[cache_key] = thumb
                    return thumb
        except Exception:
            pass
    fallback = QPixmap(size, size)
    fallback.fill(QColor("#1e1710"))
    CATALOG_PIXMAP_CACHE[cache_key] = fallback
    return fallback

DUNE_QSS = f"""
* {{
    font-family: 'Segoe UI Variable', 'Segoe UI', Arial;
    color: #f0dfb5;
    font-size: 14px;
}}
QMainWindow, QWidget#Root {{
    background: #080706;
}}
QFrame#SideBar {{
    background-image: url("{qss_path(asset_path('backgrounds','sidebar_texture.png'))}");
    background-position: center;
    background-repeat: no-repeat;
    background-color: #0b0a08;
    border-right: 1px solid #59D4AE63;
}}
QLabel#Brand {{
    color: #f3d58b;
    font-size: 30px;
    font-weight: 800;
    letter-spacing: 5px;
}}
QLabel#BrandSub {{
    color: #b9944b;
    font-size: 11px;
    letter-spacing: 3px;
}}
QPushButton#NavButton {{
    text-align: left;
    padding: 18px 20px;
    border: 1px solid transparent;
    border-radius: 16px;
    background: #59080706;
    color: #e8d4a2;
    font-size: 17px;
    font-weight: 800;
}}
QPushButton#NavButton:hover {{
    background: #23D4AE63;
    border: 1px solid #72D4AE63;
}}
QPushButton#NavButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6BD4AE63, stop:1 #387452D8);
    border: 1px solid #d4ae63;
    color: #fff2c9;
}}
QFrame#Hero {{
    background-color: #1b1209;
    border: 1px solid #8CF4CD7A;
    border-radius: 22px;
}}
QLabel#HeroTitle {{
    font-size: 46px;
    font-weight: 900;
    letter-spacing: 12px;
    color: #fff0bf;
}}
QLabel#HeroKicker {{
    font-size: 13px;
    letter-spacing: 6px;
    color: #f0c76c;
}}
QLabel#HeroSub {{
    font-size: 14px;
    letter-spacing: 4px;
    color: #e0b65c;
}}
QFrame#Card, QFrame#Panel {{
    background: #E8120E0A;
    border: 1px solid #5CD4AE63;
    border-radius: 18px;
}}
QFrame#Card:hover {{
    border: 1px solid #f0c76c;
    background: #F5241B11;
}}
QLabel#CardTitle {{
    font-size: 12px;
    letter-spacing: 2px;
    color: #d4ae63;
}}
QLabel#CardValue {{
    font-size: 34px;
    font-weight: 800;
    color: #fff0bf;
}}
QLabel#SectionTitle {{
    font-size: 25px;
    font-weight: 800;
    color: #f1d78f;
    letter-spacing: 2px;
}}
QPushButton {{
    background: #EA20170F;
    border: 1px solid #5CD4AE63;
    border-radius: 12px;
    padding: 10px 16px;
    color: #f4dea9;
    font-weight: 650;
}}
QPushButton:hover {{
    background: #F4352512;
    border: 1px solid #f0c76c;
}}
QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f4d27f, stop:1 #a96c28);
    color: #160e08;
    font-weight: 900;
    border: 1px solid #ffe0a1;
}}
QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background: #EA090807;
    border: 1px solid #5CD4AE63;
    border-radius: 10px;
    padding: 9px;
    color: #f4dfa9;
    selection-background-color: #7452d8;
}}
QTableWidget {{
    background: #E5090807;
    alternate-background-color: #EA1C150E;
    gridline-color: #19D4AE63;
    border: 1px solid #52D4AE63;
    border-radius: 14px;
    color: #f1dfb5;
}}
QTableWidget::item {{
    padding: 10px;
    border-bottom: 1px solid #19D4AE63;
}}
QTableWidget::item:selected {{
    background: #607452D8;
    color: #fff5d7;
    border: 0px;
}}
QTableWidget::item:focus {{
    border: 0px;
    outline: none;
}}
QHeaderView::section {{
    background: #F41C1221;
    color: #f4d072;
    padding: 11px;
    border: none;
    border-right: 1px solid #2DD4AE63;
    font-weight: 900;
}}
QScrollBar:vertical {{ background: #0f0e0d; width: 12px; }}
QScrollBar::handle:vertical {{ background: #7c5a26; border-radius: 6px; }}
"""


def fmt_price(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


def make_item(text: Any, numeric: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(fmt_price(text) if numeric else ("—" if text is None or text == "" else str(text)))
    if numeric:
        try:
            item.setData(Qt.UserRole, int(text or 0))
        except Exception:
            item.setData(Qt.UserRole, 0)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    else:
        item.setData(Qt.UserRole, item.text().lower())
    return item


class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        return int(self.data(Qt.UserRole) or 0) < int(other.data(Qt.UserRole) or 0)


class PriceItem(NumericTableWidgetItem):
    pass


class StankyTable(QTableWidget):
    def __init__(self, columns: list[str]):
        super().__init__(0, len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setShowGrid(False)

    def add_row(self, values: list[Any], numeric_cols: set[int] | None = None):
        numeric_cols = numeric_cols or set()
        row = self.rowCount()
        self.insertRow(row)
        for col, value in enumerate(values):
            if col in numeric_cols:
                item = PriceItem(fmt_price(value))
                try:
                    item.setData(Qt.UserRole, int(value or 0))
                except Exception:
                    item.setData(Qt.UserRole, 0)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                item = QTableWidgetItem("—" if value is None or value == "" else str(value))
                item.setData(Qt.UserRole, item.text().lower())
            self.setItem(row, col, item)
        self.resizeRowsToContents()


class StatCard(QFrame):
    def __init__(self, title: str, value: str, hint: str = ""):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        title_label = QLabel(title.upper())
        title_label.setObjectName("CardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("CardValue")
        hint_label = QLabel(hint)
        hint_label.setStyleSheet("color:#9f8150; font-size:12px;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        if hint:
            layout.addWidget(hint_label)
        layout.addStretch()


class PriceDialog(QDialog):
    def __init__(self, parent: QWidget, item_id: int, item_name: str):
        super().__init__(parent)
        self.setWindowTitle(f"Record Price — {item_name}")
        self.item_id = item_id
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        title = QLabel(f"Record price for {item_name}")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        form = QFormLayout()
        self.price = QSpinBox()
        self.price.setRange(1, 2_000_000_000)
        self.price.setSingleStep(1000)
        self.grade = QComboBox()
        self.grade.addItems(["No Grade", "Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5"])
        self.note = QLineEdit()
        form.addRow("Price", self.price)
        form.addRow("Grade", self.grade)
        form.addRow("Note", self.note)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("Cancel")
        save = QPushButton("Save Price")
        save.setObjectName("PrimaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _save(self):
        grade_text = self.grade.currentText()
        grade = None if grade_text == "No Grade" else int(grade_text.split()[-1])
        db.record_price(self.item_id, int(self.price.value()), grade, self.note.text())
        self.accept()




class CatalogImportWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            from . import catalog_importer
            result = catalog_importer.import_catalog(progress=self.progress.emit)
            self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

class GuildJoinDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle('Join Guild — StankyTools')
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        title = QLabel('STANKYTOOLS GUILD SETUP')
        title.setObjectName('SectionTitle')
        layout.addWidget(title)
        help_text = QLabel('Enter the name you want your guild to see, then join with the shared guild code. You only need to do this once.')
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        form = QFormLayout()
        self.display_name = QLineEdit(db.get_setting('display_name', ''))
        self.display_name.setPlaceholderText('Example: Tony')
        self.guild_code = QLineEdit(db.get_setting('guild_code', ''))
        self.guild_code.setPlaceholderText('Example: STNK-8X2K')
        form.addRow('Display Name', self.display_name)
        form.addRow('Guild Code', self.guild_code)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton('Later')
        join = QPushButton('Join Guild')
        join.setObjectName('PrimaryButton')
        cancel.clicked.connect(self.reject)
        join.clicked.connect(self._accept_if_ready)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(join)
        layout.addLayout(buttons)

    def _accept_if_ready(self):
        if not self.display_name.text().strip() or not self.guild_code.text().strip():
            QMessageBox.information(self, 'Guild Setup', 'Enter both Display Name and Guild Code.')
            return
        self.accept()


class DeepDesertMapView(QGraphicsView):
    """Built-in map viewer with wheel zoom, drag pan, POI drawing, and click-to-add POIs."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self.poi_items: list[Any] = []
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setStyleSheet("background:#0d0b08; border:1px solid #43321a; border-radius:14px;")
        self.scale_factor = 1.0
        self.add_poi_callback = None

    def set_map(self, image_path: str) -> bool:
        pix = QPixmap(image_path)
        if pix.isNull():
            return False
        self.scene.clear()
        self.poi_items = []
        self.pixmap_item = self.scene.addPixmap(pix)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.reset_view()
        return True

    def reset_view(self):
        self.resetTransform()
        self.scale_factor = 1.0
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        if not self.pixmap_item:
            return super().wheelEvent(event)
        zoom_in = event.angleDelta().y() > 0
        factor = 1.20 if zoom_in else 1 / 1.20
        new_scale = self.scale_factor * factor
        if 0.25 <= new_scale <= 8.0:
            self.scale_factor = new_scale
            self.scale(factor, factor)

    def mouseDoubleClickEvent(self, event):
        if self.add_poi_callback and self.pixmap_item:
            scene_pos = self.mapToScene(event.pos())
            if self.scene.sceneRect().contains(scene_pos):
                self.add_poi_callback(float(scene_pos.x()), float(scene_pos.y()))
                return
        super().mouseDoubleClickEvent(event)

    def draw_pois(self, pois, selected_poi_id: int | None = None):
        """Draw Deep Desert POIs with a tactical highlight only on selection."""
        for item in self.poi_items:
            self.scene.removeItem(item)
        self.poi_items = []
        for poi in pois:
            try:
                poi_id = int(poi['id'])
            except Exception:
                poi_id = -1
            selected = selected_poi_id is not None and poi_id == int(selected_poi_id)
            x, y = float(poi['x']), float(poi['y'])
            defeated = bool(poi['pooped_on']) if 'pooped_on' in poi.keys() else False
            poi_type = poi['poi_type'] if 'poi_type' in poi.keys() else poi['label']
            note = poi['note'] if 'note' in poi.keys() else ''
            tactical_status = poi_tactical_status(str(poi_type), defeated)
            base_color = poi_status_color(tactical_status)
            tooltip = f"{poi_type}\nStatus: {poi_status_label(tactical_status)}\n{note or ''}"
            if not selected:
                marker = self.scene.addEllipse(
                    x - 8, y - 8, 16, 16,
                    QPen(QColor('#fff0bf'), 2),
                    QBrush(base_color),
                )
                marker.setToolTip(tooltip)
                self.poi_items.append(marker)
                continue

            glow = self.scene.addEllipse(
                x - 40, y - 40, 80, 80,
                QPen(QColor(247, 210, 122, 135), 3),
                QBrush(QColor(247, 210, 122, 30)),
            )
            ring = self.scene.addEllipse(
                x - 28, y - 28, 56, 56,
                QPen(QColor('#f7d27a'), 5),
                QBrush(Qt.NoBrush),
            )
            marker = self.scene.addEllipse(
                x - 16, y - 16, 32, 32,
                QPen(QColor('#fff0bf'), 3),
                QBrush(base_color),
            )
            status_text = poi_status_label(tactical_status)
            label_text = f"{poi_type} • {status_text}"
            width = max(190, min(360, 34 + (len(label_text) * 7)))
            label_bg = self.scene.addRect(
                x + 24, y - 28, width, 56,
                QPen(QColor('#f7d27a'), 2),
                QBrush(QColor(15, 14, 13, 235)),
            )
            stripe = self.scene.addRect(x + 24, y - 28, 7, 56, QPen(base_color, 0), QBrush(base_color))
            label = self.scene.addText(label_text)
            label.setDefaultTextColor(QColor('#fff4ce'))
            label.setFont(QFont('Segoe UI', 9, QFont.Bold))
            label.setPos(x + 38, y - 26)
            short_note = (note or '').replace('\n', ' ')
            if len(short_note) > 42:
                short_note = short_note[:39] + '...'
            sub = self.scene.addText(short_note or 'No note')
            sub.setDefaultTextColor(QColor('#d4ae63'))
            sub.setFont(QFont('Segoe UI', 8))
            sub.setPos(x + 38, y - 5)
            for obj in (glow, ring, marker, label_bg, stripe, label, sub):
                obj.setToolTip(tooltip)
            self.poi_items.extend([glow, ring, marker, label_bg, stripe, label, sub])

    def draw_bases(self, bases, selected_base_id: int | None = None):
        """Draw Hagga Basin guild bases.

        Default markers stay small and clean so the map does not become cluttered.
        Only the base selected from the list gets the large tactical highlight and label.
        """
        for item in self.poi_items:
            self.scene.removeItem(item)
        self.poi_items = []
        current_user = db.get_setting('display_name', '')

        for base in bases:
            try:
                base_id = int(base['id'])
            except Exception:
                base_id = -1
            selected = selected_base_id is not None and base_id == int(selected_base_id)
            x, y = float(base['x']), float(base['y'])
            creator = base['created_by'] if 'created_by' in base.keys() else 'Unknown'
            name = base['base_name'] if 'base_name' in base.keys() else 'Guild Base'
            seitch = base['seitch'] if 'seitch' in base.keys() else ''
            profile = profile_color(creator)
            status = normalize_base_status(base['status'] if 'status' in base.keys() else 'friendly')
            color = base_status_color(status)
            is_mine = (creator or '').strip().lower() == (current_user or '').strip().lower()

            tooltip = (
                f"Member: {creator or 'Unknown'}\n"
                f"Base: {name or 'Guild Base'}\n"
                f"Seitch: {seitch or 'Unknown'}\n"
                f"Status: {base_status_label(status)}"
            )

            if not selected:
                # Small profile marker by default. Your own bases use a subtle shield/square center.
                marker = self.scene.addEllipse(
                    x - 9, y - 9, 18, 18,
                    QPen(QColor('#fff0bf'), 2),
                    QBrush(color),
                )
                if is_mine:
                    inner = self.scene.addRect(
                        x - 4, y - 4, 8, 8,
                        QPen(QColor('#120f0c'), 1),
                        QBrush(QColor('#fff0bf')),
                    )
                    inner.setToolTip(tooltip)
                    self.poi_items.append(inner)
                marker.setToolTip(tooltip)
                self.poi_items.append(marker)
                continue

            # Selected base: gold tactical objective highlight.
            glow = self.scene.addEllipse(
                x - 42, y - 42, 84, 84,
                QPen(QColor(247, 210, 122, 130), 3),
                QBrush(QColor(247, 210, 122, 28)),
            )
            ring = self.scene.addEllipse(
                x - 30, y - 30, 60, 60,
                QPen(QColor('#f7d27a'), 5),
                QBrush(Qt.NoBrush),
            )
            marker = self.scene.addEllipse(
                x - 18, y - 18, 36, 36,
                QPen(QColor('#fff0bf'), 3),
                QBrush(color),
            )
            initial = (creator or '?').strip()[:1].upper() or '?'
            letter = self.scene.addText(initial)
            letter.setDefaultTextColor(readable_text_color(profile))
            letter.setFont(QFont('Segoe UI', 13, QFont.Bold))
            letter.setPos(x - 7, y - 13)

            label_text = f"{creator or 'Unknown'} • {name or 'Guild Base'}"
            sub_text = f"{seitch or 'Unknown Seitch'} • {base_status_label(status)}"
            width = max(190, min(330, 34 + (len(label_text) * 7)))
            label_bg = self.scene.addRect(
                x + 26, y - 30, width, 58,
                QPen(QColor('#f7d27a'), 2),
                QBrush(QColor(15, 14, 13, 235)),
            )
            stripe = self.scene.addRect(x + 26, y - 30, 7, 58, QPen(color, 0), QBrush(color))
            label = self.scene.addText(label_text)
            label.setDefaultTextColor(QColor('#fff4ce'))
            label.setFont(QFont('Segoe UI', 9, QFont.Bold))
            label.setPos(x + 40, y - 28)
            sub = self.scene.addText(f"Seitch: {sub_text}")
            sub.setDefaultTextColor(QColor('#d4ae63'))
            sub.setFont(QFont('Segoe UI', 8))
            sub.setPos(x + 40, y - 7)

            for obj in (glow, ring, marker, letter, label_bg, stripe, label, sub):
                obj.setToolTip(tooltip)
            self.poi_items.extend([glow, ring, marker, letter, label_bg, stripe, label, sub])

    def center_on(self, x: float, y: float):
        self.centerOn(float(x), float(y))
        if self.scale_factor < 1.5:
            self.resetTransform()
            self.scale_factor = 1.25
            self.scale(1.25, 1.25)
            self.centerOn(float(x), float(y))


def parse_price_text(text: str) -> int | None:
    cleaned = ''.join(ch for ch in text if ch.isdigit())
    if not cleaned:
        return None
    try:
        value = int(cleaned)
        return value if value > 0 else None
    except Exception:
        return None


def ocr_price_from_image(path: str) -> int | None:
    """Optional OCR hook. Works if pytesseract + Tesseract are installed; otherwise returns None."""
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance
        img = Image.open(path).convert('L')
        img = ImageOps.autocontrast(img)
        img = ImageEnhance.Contrast(img).enhance(2.0)
        text = pytesseract.image_to_string(img, config='--psm 7 -c tessedit_char_whitelist=0123456789,')
        return parse_price_text(text)
    except Exception:
        return None


def normalize_supabase_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return url.rstrip("/")


def supabase_request(method: str, url: str, anon_key: str, endpoint: str, payload: Any | None = None) -> Any:
    """Small Supabase REST helper.

    Use ONLY the public/anon key in the desktop app. Never use the service-role/secret key here.
    """
    base_url = normalize_supabase_url(url)
    base = base_url + '/rest/v1/' + endpoint.lstrip('/')
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(base, data=data, method=method.upper())
    req.add_header('apikey', anon_key)
    req.add_header('Authorization', f'Bearer {anon_key}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    # Needed for POST upserts with ?on_conflict=id.
    req.add_header('Prefer', 'return=representation,resolution=merge-duplicates')
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read().decode('utf-8')
        return json.loads(raw) if raw else []


def active_supabase() -> tuple[str, str]:
    """Return the built-in Supabase project URL and public anon key.

    Guild members should never need to enter these. Edit stanky_market/guild_config.py
    before building/distributing the app. Never put the secret/service key there.
    """
    url = normalize_supabase_url(getattr(guild_config, 'SUPABASE_URL', ''))
    key = getattr(guild_config, 'SUPABASE_ANON_KEY', '').strip()
    # Backward-compatible fallback for older local settings while developing.
    if not url:
        url = normalize_supabase_url(db.get_setting('supabase_url', ''))
    if not key:
        key = db.get_setting('supabase_key', '')
    return url, key


def make_guild_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return 'STNK-' + ''.join(random.choice(alphabet) for _ in range(4)) + '-' + ''.join(random.choice(alphabet) for _ in range(4))


PROFILE_COLORS = [
    '#7b4dff', '#2ecc71', '#3498db', '#f39c12', '#e74c3c',
    '#1abc9c', '#e056fd', '#f1c40f', '#00d2d3', '#ff6b6b',
    '#9b59b6', '#27ae60', '#2980b9', '#d35400', '#c0392b',
    '#16a085', '#be2edd', '#f9ca24', '#48dbfb', '#ff9f43',
]


def profile_color(display_name: str) -> QColor:
    """Deterministic guild profile color based on display name.

    This keeps each member visually consistent across app sessions and guild members
    without needing a color picker or another Supabase column.
    """
    name = (display_name or 'Unknown').strip().lower()
    if not name:
        name = 'unknown'
    score = 0
    for ch in name:
        score = (score * 31 + ord(ch)) % 10_000_000
    return QColor(PROFILE_COLORS[score % len(PROFILE_COLORS)])


def readable_text_color(bg: QColor) -> QColor:
    # Basic luminance check so labels remain readable on bright profile colors.
    lum = (0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue())
    return QColor('#120f0c') if lum > 165 else QColor('#fff4ce')


BASE_STATUS_COLORS = {
    "friendly": "#2ecc71",
    "enemy": "#e74c3c",
    "defeated": "#8a8f98",
}


def normalize_base_status(status: str) -> str:
    status = (status or "friendly").strip().lower()
    return status if status in BASE_STATUS_COLORS else "friendly"


def base_status_label(status: str) -> str:
    return normalize_base_status(status).title()


def base_status_color(status: str) -> QColor:
    return QColor(BASE_STATUS_COLORS[normalize_base_status(status)])


POI_STATUS_COLORS = {
    "friendly": "#2ecc71",
    "enemy": "#e74c3c",
    "defeated": "#8a8f98",
    "active": "#d4ae63",
}


def poi_tactical_status(poi_type: str, defeated: bool = False) -> str:
    if defeated:
        return "defeated"
    raw = (poi_type or "").strip().lower()
    if "friendly" in raw:
        return "friendly"
    if "enemy" in raw:
        return "enemy"
    return "active"


def poi_status_label(status: str) -> str:
    status = (status or "active").strip().lower()
    if status == "enemy":
        return "Enemy"
    if status == "friendly":
        return "Friendly"
    if status == "defeated":
        return "Defeated"
    return "Active"


def poi_status_color(status: str) -> QColor:
    return QColor(POI_STATUS_COLORS.get((status or "active").strip().lower(), POI_STATUS_COLORS["active"]))


def role_can_manage_guild() -> bool:
    return (db.get_setting("guild_role", "member") or "member").lower() in {"owner", "officer"}


def guild_logo_cache_path() -> Path:
    return PROJECT_ROOT / "data" / "guild_logo.png"


class HeroFrame(QFrame):
    """Banner frame that paints image assets safely with QPixmap.

    This avoids unsupported Qt stylesheet background-image rules that caused
    repeated "Could not parse stylesheet" warnings on Windows.
    """
    def __init__(self, banner_path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Hero")
        self.banner_path = Path(banner_path)
        self._pixmap = QPixmap(str(self.banner_path)) if self.banner_path.exists() else QPixmap()
        self.setMinimumHeight(190)
        self.setStyleSheet("QFrame#Hero { background-color:#1b1209; border:1px solid #b88d3c; border-radius:22px; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        painter.fillRect(rect, QColor('#1b1209'))
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (rect.width() - scaled.width()) // 2
            y = (rect.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        # dark readability overlay + golden lower glow
        painter.fillRect(rect, QColor(0, 0, 0, 95))
        super().paintEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1500, 900)
        self.nav_buttons: list[QPushButton] = []
        self.current_catalog_rows: list[Any] = []
        self.current_market_rows: list[Any] = []
        self.current_poi_rows: list[Any] = []
        self.selected_scan_item_id: int | None = None
        self.selected_scan_item_name: str = ""
        self.selected_base_id_for_map: int | None = None
        self.selected_poi_id_for_map: int | None = None
        self._build_ui()
        self.refresh_all()
        self._sync_running = False
        self._last_auto_sync = 0.0
        self.guild_sync_timer = QTimer(self)
        # Network sync runs on the UI thread right now, so keep it on a slower
        # cadence to avoid the app feeling frozen every few seconds. Manual
        # sync and save actions still push changes immediately.
        self.guild_sync_timer.setInterval(60000)
        self.guild_sync_timer.timeout.connect(self.auto_sync_guild)
        self.guild_sync_timer.start()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar.setFixedWidth(330)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(22, 28, 22, 22)
        brand = QLabel("STANKY\nTOOLS")
        brand.setObjectName("Brand")
        brand.setAlignment(Qt.AlignCenter)
        sub = QLabel("FOR GUILD. FOR ARRAKIS.")
        sub.setObjectName("BrandSub")
        sub.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(brand)
        side_layout.addWidget(sub)
        side_layout.addSpacing(24)

        self.pages = QStackedWidget()
        page_specs = [
            ("Dashboard", "dashboard_small.png", self._build_dashboard_page),
            ("Market", "market_small.png", self._build_market_page),
            ("Deep Desert", "deep_desert_small.png", self._build_deep_desert_page),
            ("Hagga Basin", "hagga_basin_small.png", self._build_hagga_basin_page),
            ("Guild", "guild_small.png", self._build_guild_page),
            ("Settings", "settings_small.png", self._build_settings_page),
        ]
        self.guild_page_index = 4
        for idx, (label, icon_name, builder) in enumerate(page_specs):
            btn = QPushButton("  " + label)
            icon_path = asset_path("icons", icon_name)
            if icon_path.exists():
                btn.setIcon(QIcon(str(icon_path)))
                btn.setIconSize(QSize(88, 88))
            btn.setMinimumHeight(118)
            btn.setObjectName("NavButton")
            btn.setProperty("active", idx == 0)
            if label == "Guild":
                self.guild_nav_button = btn
                btn.clicked.connect(lambda checked=False: self.open_guild_admin_page())
            else:
                btn.clicked.connect(lambda checked=False, i=idx: self.set_page(i))
            self.nav_buttons.append(btn)
            side_layout.addWidget(btn)
            self.pages.addWidget(builder())
        side_layout.addStretch()
        side_layout.addWidget(QLabel("v1.0 modern foundation"))

        main.addWidget(sidebar)
        main.addWidget(self.pages, 1)
        self.update_guild_nav_visibility()

    def set_page(self, index: int):
        # Guild page is an admin-only area. Members can see public guild info on the dashboard,
        # but they cannot open the admin section.
        if index == getattr(self, "guild_page_index", 4) and not role_can_manage_guild():
            QMessageBox.information(self, "Guild Admin", "The Guild section is available to owners and officers only.")
            index = 0
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.update_guild_nav_visibility()

    def open_guild_admin_page(self):
        if not role_can_manage_guild():
            QMessageBox.information(self, "Guild Admin", "The Guild section is available to owners and officers only.")
            return
        self.set_page(getattr(self, "guild_page_index", 4))

    def update_guild_nav_visibility(self):
        btn = getattr(self, "guild_nav_button", None)
        admin = role_can_manage_guild()
        if btn is not None:
            btn.setVisible(admin)
        if hasattr(self, "dashboard_guild_button"):
            self.dashboard_guild_button.setVisible(admin)
        if hasattr(self, "pages") and self.pages.currentIndex() == getattr(self, "guild_page_index", 4) and not admin:
            self.pages.setCurrentIndex(0)

    def open_market_tab(self, tab_index: int = 0):
        self.set_page(1)
        if hasattr(self, "market_tabs"):
            self.market_tabs.setCurrentIndex(max(0, min(tab_index, self.market_tabs.count() - 1)))

    def _page_shell(self, title: str, subtitle: str = "") -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)
        banner_key = title.lower().replace(" ", "_")
        banner_file = {
            "dashboard": "dashboard_banner.png",
            "market": "market_banner.png",
            "catalog": "catalog_banner.png",
            "scanner": "scanner_banner.png",
            "deep_desert": "deep_desert_banner.png",
            "hagga_basin": "hagga_basin_banner.png",
            "settings": "settings_banner.png",
            "guild": "guild_banner.png",
        }.get(banner_key, "dashboard_banner.png")
        hero = HeroFrame(asset_path("backgrounds", banner_file))
        h = QVBoxLayout(hero)
        h.setContentsMargins(32, 24, 32, 24)
        kicker = QLabel("THE SPICE MUST FLOW")
        kicker.setObjectName("HeroKicker")
        heading = QLabel(title.upper())
        heading.setObjectName("HeroTitle")
        sub = QLabel(subtitle.upper())
        sub.setObjectName("HeroSub")
        h.addWidget(kicker)
        h.addWidget(heading)
        if subtitle:
            h.addWidget(sub)
        h.addStretch()
        layout.addWidget(hero)
        return page, layout

    def _build_dashboard_page(self) -> QWidget:
        page, layout = self._page_shell("Dashboard", "Guild command center for Arrakis operations.")
        self.stat_grid = QGridLayout()
        self.stat_grid.setSpacing(14)
        layout.addLayout(self.stat_grid)

        command_row = QHBoxLayout()
        self.dashboard_links_table = StankyTable(["Title", "URL", "Poster"])
        self.news_table = StankyTable(["Date", "Poster", "Guild News"])
        self.dashboard_links_table.setWordWrap(True)
        self.news_table.setWordWrap(True)
        self.dashboard_links_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dashboard_links_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dashboard_links_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.dashboard_links_table.cellDoubleClicked.connect(self.open_selected_dashboard_link)
        self.news_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.news_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.news_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.news_table.cellDoubleClicked.connect(self.show_dashboard_news_detail)

        links_panel = self._panel("Useful Links", self.dashboard_links_table)
        news_panel = self._panel("Guild News", self.news_table)

        guild_card = QFrame()
        guild_card.setObjectName("Panel")
        guild_layout = QVBoxLayout(guild_card)
        guild_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Guild Operations")
        title.setObjectName("SectionTitle")
        self.dashboard_guild_logo = QLabel()
        self.dashboard_guild_logo.setMinimumSize(520, 520)
        self.dashboard_guild_logo.setMaximumSize(900, 900)
        self.dashboard_guild_logo.setAlignment(Qt.AlignCenter)
        self.dashboard_guild_logo.setStyleSheet("border:0px; background:transparent; padding:0px;")
        self.dashboard_guild_name = QLabel("Guild: " + (db.get_setting("guild_name", "Guild") or "Guild"))
        self.dashboard_guild_name.setAlignment(Qt.AlignCenter)
        self.dashboard_guild_name.setStyleSheet("font-size:24px; font-weight:900; color:#fff0bf;")
        self.dashboard_user = QLabel("Profile: " + (db.get_setting("display_name", "Not joined") or "Not joined"))
        self.dashboard_user.setAlignment(Qt.AlignCenter)
        self.dashboard_user.setStyleSheet("color:#d4ae63; font-size:15px;")
        self.dashboard_members = QLabel("Members: —")
        self.dashboard_members.setAlignment(Qt.AlignCenter)
        self.dashboard_members.setStyleSheet("color:#f0dfb5; font-size:18px; font-weight:800;")
        quick = QHBoxLayout()
        b1 = QPushButton("Hagga Basin")
        b1.clicked.connect(lambda: self.set_page(3))
        b2 = QPushButton("Deep Desert")
        b2.clicked.connect(lambda: self.set_page(2))
        b3 = QPushButton("Guild")
        b3.setObjectName("PrimaryButton")
        self.dashboard_guild_button = b3
        b3.clicked.connect(self.open_guild_admin_page)
        quick.addWidget(b1)
        quick.addWidget(b2)
        quick.addWidget(b3)
        guild_layout.addWidget(title)
        guild_layout.addWidget(self.dashboard_guild_logo, 1, alignment=Qt.AlignCenter)
        guild_layout.addWidget(self.dashboard_guild_name)
        guild_layout.addWidget(self.dashboard_user)
        guild_layout.addWidget(self.dashboard_members)
        guild_layout.addSpacing(10)
        guild_layout.addLayout(quick)

        command_row.addWidget(links_panel, 2)
        command_row.addWidget(news_panel, 2)
        command_row.addWidget(guild_card, 1)
        layout.addLayout(command_row, 1)
        return page

    def _build_market_page(self) -> QWidget:
        page, layout = self._page_shell("Market", "Market, catalog, and scanner command center.")
        self.market_tabs = QTabWidget()
        self.market_tabs.setDocumentMode(True)

        # Market tab
        market_tab = QWidget()
        market_layout = QVBoxLayout(market_tab)
        market_layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.market_search = QLineEdit()
        self.market_search.setPlaceholderText("Search market...")
        self.market_search.textChanged.connect(self.refresh_market)
        record_btn = QPushButton("Record Price")
        record_btn.setObjectName("PrimaryButton")
        record_btn.clicked.connect(self.record_selected_market_price)
        controls.addWidget(self.market_search, 1)
        controls.addWidget(record_btn)
        market_layout.addLayout(controls)
        self.market_table = StankyTable(["Name", "Category", "Grade", "Lowest Price", "Avg Price", "Highest Price", "Seen", "Last Updated"])
        market_layout.addWidget(self.market_table, 1)

        # Catalog tab
        catalog_tab = QWidget()
        catalog_layout = QVBoxLayout(catalog_tab)
        catalog_layout.setContentsMargins(0, 0, 0, 0)
        catalog_controls = QHBoxLayout()
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("Search item name...")
        self.catalog_search.textChanged.connect(self.refresh_catalog)
        self.catalog_category = QComboBox()
        self.catalog_category.currentTextChanged.connect(self.refresh_catalog)
        self.catalog_import_button = QPushButton("Import Dune Item Database")
        self.catalog_import_button.clicked.connect(self.import_catalog)
        catalog_controls.addWidget(self.catalog_search, 2)
        catalog_controls.addWidget(self.catalog_category, 1)
        catalog_controls.addWidget(self.catalog_import_button)
        catalog_layout.addLayout(catalog_controls)
        self.catalog_import_status = QLabel("Ready.")
        self.catalog_import_status.setStyleSheet("color:#9f8150;")
        self.catalog_import_progress = QProgressBar()
        self.catalog_import_progress.setRange(0, 1)
        self.catalog_import_progress.setValue(0)
        self.catalog_import_progress.setVisible(False)
        catalog_layout.addWidget(self.catalog_import_status)
        catalog_layout.addWidget(self.catalog_import_progress)
        self.catalog_table = StankyTable(["Image", "Name", "Category"])
        self.catalog_table.setIconSize(QSize(72, 72))
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.catalog_table.cellDoubleClicked.connect(self.open_catalog_item)
        catalog_layout.addWidget(self.catalog_table, 1)

        # Scanner tab
        scanner_tab = QWidget()
        scanner_layout = QVBoxLayout(scanner_tab)
        scanner_layout.setContentsMargins(0, 0, 0, 0)
        panel = QFrame()
        panel.setObjectName("Panel")
        p = QVBoxLayout(panel)
        p.setContentsMargins(24, 24, 24, 24)
        label = QLabel("Auction House Scanner")
        label.setObjectName("SectionTitle")
        help_text = QLabel("Choose an item from the catalog, then scan or enter the auction price. The scanner only updates price history for the selected item; it never guesses names or images.")
        help_text.setWordWrap(True)
        p.addWidget(label)
        p.addWidget(help_text)
        form = QFormLayout()
        self.scan_category = QComboBox()
        self.scan_item = QComboBox()
        self.scan_price = QSpinBox()
        self.scan_price.setRange(1, 2_000_000_000)
        self.scan_price.setSingleStep(1000)
        self.scan_grade = QComboBox()
        self.scan_grade.addItems(["No Grade", "Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5"])
        self.scan_status = QLabel("Ready. Select item and record price.")
        self.scan_category.currentTextChanged.connect(self.refresh_scan_items)
        form.addRow("Category", self.scan_category)
        form.addRow("Catalog Item", self.scan_item)
        form.addRow("Price", self.scan_price)
        form.addRow("Grade", self.scan_grade)
        p.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("Record Price")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.record_scanner_price)
        ocr = QPushButton("OCR Price From Image...")
        ocr.clicked.connect(self.ocr_price_from_file)
        buttons.addWidget(save)
        buttons.addWidget(ocr)
        buttons.addStretch()
        p.addLayout(buttons)
        p.addWidget(self.scan_status)
        p.addStretch()
        scanner_layout.addWidget(panel, 1)

        self.market_tabs.addTab(market_tab, "Market")
        self.market_tabs.addTab(catalog_tab, "Catalog")
        self.market_tabs.addTab(scanner_tab, "Scanner")
        layout.addWidget(self.market_tabs, 1)
        return page

    def _build_catalog_page(self) -> QWidget:
        page, layout = self._page_shell("Catalog", "Trusted item database.")
        controls = QHBoxLayout()
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("Search item name...")
        self.catalog_search.textChanged.connect(self.refresh_catalog)
        self.catalog_category = QComboBox()
        self.catalog_category.currentTextChanged.connect(self.refresh_catalog)
        self.catalog_import_button = QPushButton("Import Dune Item Database")
        self.catalog_import_button.clicked.connect(self.import_catalog)
        controls.addWidget(self.catalog_search, 2)
        controls.addWidget(self.catalog_category, 1)
        controls.addWidget(self.catalog_import_button)
        layout.addLayout(controls)
        self.catalog_import_status = QLabel("Ready.")
        self.catalog_import_status.setStyleSheet("color:#9f8150;")
        self.catalog_import_progress = QProgressBar()
        self.catalog_import_progress.setRange(0, 1)
        self.catalog_import_progress.setValue(0)
        self.catalog_import_progress.setVisible(False)
        layout.addWidget(self.catalog_import_status)
        layout.addWidget(self.catalog_import_progress)
        self.catalog_table = StankyTable(["Image", "Name", "Category"])
        self.catalog_table.setIconSize(QSize(72, 72))
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.catalog_table.cellDoubleClicked.connect(self.open_catalog_item)
        layout.addWidget(self.catalog_table, 1)
        return page

    def _build_scanner_page(self) -> QWidget:
        page, layout = self._page_shell("Scanner", "Selected item. Price only.")
        panel = QFrame()
        panel.setObjectName("Panel")
        p = QVBoxLayout(panel)
        p.setContentsMargins(24, 24, 24, 24)
        label = QLabel("Auction House Scanner")
        label.setObjectName("SectionTitle")
        help_text = QLabel("Choose an item from the catalog, then scan or enter the auction price. The scanner only updates price history for the selected item; it never guesses names or images.")
        help_text.setWordWrap(True)
        p.addWidget(label)
        p.addWidget(help_text)

        form = QFormLayout()
        self.scan_category = QComboBox()
        self.scan_item = QComboBox()
        self.scan_price = QSpinBox()
        self.scan_price.setRange(1, 2_000_000_000)
        self.scan_price.setSingleStep(1000)
        self.scan_grade = QComboBox()
        self.scan_grade.addItems(["No Grade", "Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5"])
        self.scan_status = QLabel("Ready. Select item and record price.")
        self.scan_category.currentTextChanged.connect(self.refresh_scan_items)
        form.addRow("Category", self.scan_category)
        form.addRow("Catalog Item", self.scan_item)
        form.addRow("Price", self.scan_price)
        form.addRow("Grade", self.scan_grade)
        p.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("Record Price")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.record_scanner_price)
        ocr = QPushButton("OCR Price From Image...")
        ocr.clicked.connect(self.ocr_price_from_file)
        buttons.addWidget(save)
        buttons.addWidget(ocr)
        buttons.addStretch()
        p.addLayout(buttons)
        p.addWidget(self.scan_status)
        p.addStretch()
        layout.addWidget(panel, 1)
        return page

    def _build_deep_desert_page(self) -> QWidget:
        page, layout = self._page_shell("Deep Desert", "Built-in tactical map and guild POIs.")
        body = QHBoxLayout()
        self.map_view = DeepDesertMapView()
        self.map_view.add_poi_callback = self.add_poi_at
        poi_panel = QFrame()
        poi_panel.setObjectName("Panel")
        poi_layout = QVBoxLayout(poi_panel)
        poi_layout.setContentsMargins(14, 14, 14, 14)
        title = QLabel("Guild POIs")
        title.setObjectName("SectionTitle")
        self.poi_table = StankyTable(["Type", "Status", "Note"])
        self.poi_table.setWordWrap(True)
        self.poi_table.setMaximumWidth(760)
        self.poi_table.cellClicked.connect(self.center_on_poi)
        self.poi_table.cellDoubleClicked.connect(self.center_on_poi)
        self.poi_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.poi_table.customContextMenuRequested.connect(self.show_poi_context_menu)
        self.poi_table.setColumnWidth(0, 120)
        self.poi_table.setColumnWidth(1, 95)
        self.poi_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.poi_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.poi_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        btns = QHBoxLayout()
        reset = QPushButton("Reset View")
        reset.clicked.connect(lambda: self.map_view.reset_view())
        refresh = QPushButton("Sync POIs")
        refresh.setObjectName("PrimaryButton")
        refresh.clicked.connect(self.sync_guild_pois)
        btns.addWidget(reset)
        btns.addWidget(refresh)
        poi_layout.addWidget(title)
        self.poi_sync_status = QLabel("Auto-sync starts when you join a guild.")
        self.poi_sync_status.setStyleSheet("color:#9f8150;")
        poi_layout.addWidget(QLabel("Double-click map to add POI. Use Status when your guild takes a base."))
        poi_layout.addWidget(self.poi_sync_status)
        poi_layout.addLayout(btns)
        poi_layout.addWidget(self.poi_table, 2)
        body.addWidget(self.map_view, 3)
        body.addWidget(poi_panel, 1)
        layout.addLayout(body, 1)
        return page

    def _build_hagga_basin_page(self) -> QWidget:
        page, layout = self._page_shell("Hagga Basin", "Guild base map and seitch locations.")
        body = QHBoxLayout()
        self.hagga_map_view = DeepDesertMapView()
        self.hagga_map_view.add_poi_callback = self.add_base_at

        base_panel = QFrame()
        base_panel.setObjectName("Panel")
        base_layout = QVBoxLayout(base_panel)
        base_layout.setContentsMargins(14, 14, 14, 14)
        title = QLabel("Guild Bases")
        title.setObjectName("SectionTitle")
        base_layout.addWidget(title)
        hint = QLabel("Double-click the Hagga Basin map to place a base marker. Each member can have up to 3 bases.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9f8150;")
        base_layout.addWidget(hint)

        self.base_table = StankyTable(["Member", "Base", "Seitch", "Status"])
        self.base_table.cellClicked.connect(self.center_on_base)
        self.base_table.cellDoubleClicked.connect(self.center_on_base)
        self.base_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.base_table.customContextMenuRequested.connect(self.show_base_context_menu)
        self.base_table.setMaximumWidth(560)
        self.base_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.base_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.base_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.base_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        base_layout.addWidget(self.base_table, 1)

        row = QHBoxLayout()
        add = QPushButton("Add Base")
        add.setObjectName("PrimaryButton")
        add.clicked.connect(self.add_base_dialog)
        edit = QPushButton("Edit")
        edit.clicked.connect(self.edit_selected_base)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete_selected_base)
        reset = QPushButton("Reset View")
        reset.clicked.connect(lambda: self.hagga_map_view.reset_view())
        row.addWidget(add)
        row.addWidget(edit)
        row.addWidget(delete)
        row.addWidget(reset)
        base_layout.addLayout(row)
        self.base_sync_status = QLabel("Base markers sync with your guild code.")
        self.base_sync_status.setStyleSheet("color:#9f8150;")
        base_layout.addWidget(self.base_sync_status)

        body.addWidget(self.hagga_map_view, 3)
        body.addWidget(base_panel, 1)
        layout.addLayout(body, 1)
        return page

    def _build_guild_page(self) -> QWidget:
        page, layout = self._page_shell("Guild", "Members, roles, news, links, and command updates.")
        body = QHBoxLayout()

        members_panel = QFrame()
        members_panel.setObjectName("Panel")
        members_layout = QVBoxLayout(members_panel)
        members_layout.setContentsMargins(16, 16, 16, 16)
        members_title = QLabel("Members & Roles")
        members_title.setObjectName("SectionTitle")
        members_layout.addWidget(members_title)
        self.guild_page_members = StankyTable(["Member", "Role"])
        self.guild_page_members.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.guild_page_members.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        members_layout.addWidget(self.guild_page_members, 1)
        member_buttons = QHBoxLayout()
        refresh_members = QPushButton("Refresh Members")
        refresh_members.clicked.connect(self.refresh_guild_page)
        manage_members = QPushButton("Manage Members")
        manage_members.setObjectName("PrimaryButton")
        manage_members.clicked.connect(self.show_members_roles_dialog)
        member_buttons.addWidget(refresh_members)
        member_buttons.addWidget(manage_members)
        members_layout.addLayout(member_buttons)

        right_panel = QFrame()
        right_panel.setObjectName("Panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        news_title = QLabel("Guild News")
        news_title.setObjectName("SectionTitle")
        right_layout.addWidget(news_title)
        self.guild_page_news = StankyTable(["Date", "Poster", "Update"])
        self.guild_page_news.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guild_page_news.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.guild_page_news.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.guild_page_news.cellDoubleClicked.connect(self.show_guild_news_detail)
        right_layout.addWidget(self.guild_page_news, 1)
        news_buttons = QHBoxLayout()
        add_news = QPushButton("Submit Guild Update")
        add_news.setObjectName("PrimaryButton")
        add_news.clicked.connect(self.submit_guild_news)
        delete_news = QPushButton("Delete News")
        delete_news.clicked.connect(self.delete_selected_guild_news)
        news_buttons.addWidget(add_news)
        news_buttons.addWidget(delete_news)
        news_buttons.addStretch()
        right_layout.addLayout(news_buttons)

        links_title = QLabel("Useful Links")
        links_title.setObjectName("SectionTitle")
        right_layout.addWidget(links_title)
        self.guild_page_links = StankyTable(["Title", "URL", "Poster"])
        self.guild_page_links.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guild_page_links.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.guild_page_links.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.guild_page_links.cellDoubleClicked.connect(self.open_selected_guild_link)
        right_layout.addWidget(self.guild_page_links, 1)
        link_buttons = QHBoxLayout()
        add_link = QPushButton("Add Link")
        add_link.clicked.connect(self.add_guild_link)
        edit_link = QPushButton("Edit Link")
        edit_link.clicked.connect(self.edit_guild_link)
        delete_link = QPushButton("Delete Link")
        delete_link.clicked.connect(self.delete_guild_link)
        link_buttons.addWidget(add_link)
        link_buttons.addWidget(edit_link)
        link_buttons.addWidget(delete_link)
        link_buttons.addStretch()
        right_layout.addLayout(link_buttons)

        activity_title = QLabel("Activity Feed")
        activity_title.setObjectName("SectionTitle")
        right_layout.addWidget(activity_title)
        self.guild_page_activity = StankyTable(["Date", "Actor", "Activity"])
        self.guild_page_activity.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guild_page_activity.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.guild_page_activity.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        right_layout.addWidget(self.guild_page_activity, 1)

        body.addWidget(members_panel, 1)
        body.addWidget(right_panel, 2)
        layout.addLayout(body, 1)
        QTimer.singleShot(250, self.refresh_guild_page)
        return page

    def _build_settings_page(self) -> QWidget:
        page, layout = self._page_shell("Settings", "Guild identity and app setup.")
        panel = QFrame()
        panel.setObjectName("Panel")
        p = QVBoxLayout(panel)
        p.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Guild Setup")
        title.setObjectName("SectionTitle")
        p.addWidget(title)

        form = QFormLayout()
        self.display_name = QLineEdit(db.get_setting("display_name", ""))
        self.display_name.setPlaceholderText("Example: Tony")
        self.guild_code = QLineEdit(db.get_setting("guild_code", ""))
        self.guild_code.setPlaceholderText("Example: STNK-8X2K")
        form.addRow("Display Name", self.display_name)
        form.addRow("Guild Code", self.guild_code)
        p.addLayout(form)

        row = QHBoxLayout()
        self.join_guild_button = QPushButton("Join Guild")
        self.join_guild_button.setObjectName("PrimaryButton")
        self.join_guild_button.clicked.connect(self.join_guild)
        self.create_guild_button = QPushButton("Create Guild")
        self.create_guild_button.clicked.connect(self.create_guild)
        self.leave_guild_button = QPushButton("Leave Guild")
        self.leave_guild_button.clicked.connect(self.leave_guild)
        row.addWidget(self.join_guild_button)
        row.addWidget(self.create_guild_button)
        row.addWidget(self.leave_guild_button)
        row.addStretch()
        p.addLayout(row)

        self.guild_status = QLabel("Not connected yet.")
        self.guild_status.setStyleSheet("color:#9f8150;")
        p.addWidget(self.guild_status)
        self.guild_role_label = QLabel("Role: " + (db.get_setting("guild_role", "member") or "member"))
        self.guild_role_label.setStyleSheet("color:#e0b65c;")
        p.addWidget(self.guild_role_label)
        self.update_guild_button_visibility()

        guild_manage_panel = QFrame()
        guild_manage_panel.setObjectName("Card")
        guild_manage_layout = QVBoxLayout(guild_manage_panel)
        guild_manage_layout.setContentsMargins(16, 14, 16, 14)
        guild_manage_title = QLabel("GUILD MANAGEMENT")
        guild_manage_title.setObjectName("CardTitle")
        guild_manage_layout.addWidget(guild_manage_title)
        logo_row = QHBoxLayout()
        self.settings_guild_logo = QLabel()
        self.settings_guild_logo.setFixedSize(72, 72)
        self.settings_guild_logo.setAlignment(Qt.AlignCenter)
        self.settings_guild_logo.setStyleSheet("border:1px solid #d4ae63; border-radius:10px; background:#120f0c;")
        upload_logo = QPushButton("Upload Guild Logo")
        upload_logo.clicked.connect(self.upload_guild_logo)
        delete_logo = QPushButton("Delete Guild Logo")
        delete_logo.clicked.connect(self.delete_guild_logo)
        logo_row.addWidget(self.settings_guild_logo)
        logo_row.addWidget(upload_logo)
        logo_row.addWidget(delete_logo)
        logo_row.addStretch()
        guild_manage_layout.addLayout(logo_row)
        member_hint = QLabel("Members and roles are hidden until opened.")
        member_hint.setStyleSheet("color:#9f8150;")
        guild_manage_layout.addWidget(member_hint)
        member_buttons = QHBoxLayout()
        view_members = QPushButton("View Members / Roles")
        view_members.setObjectName("PrimaryButton")
        view_members.clicked.connect(self.show_members_roles_dialog)
        member_buttons.addWidget(view_members)
        member_buttons.addStretch()
        guild_manage_layout.addLayout(member_buttons)
        p.addWidget(guild_manage_panel)

        maintenance_panel = QFrame()
        maintenance_panel.setObjectName("Card")
        maintenance_layout = QVBoxLayout(maintenance_panel)
        maintenance_layout.setContentsMargins(16, 14, 16, 14)
        maintenance_title = QLabel("MAINTENANCE")
        maintenance_title.setObjectName("CardTitle")
        maintenance_buttons = QHBoxLayout()
        test = QPushButton("Test Connection")
        test.clicked.connect(self.test_supabase_connection)
        refresh_map = QPushButton("Refresh Deep Desert Map")
        refresh_map.clicked.connect(self.check_map_update)
        maintenance_buttons.addWidget(test)
        maintenance_buttons.addWidget(refresh_map)
        maintenance_buttons.addStretch()
        maintenance_layout.addWidget(maintenance_title)
        maintenance_layout.addLayout(maintenance_buttons)
        p.addWidget(maintenance_panel)

        update_panel = QFrame()
        update_panel.setObjectName("Card")
        update_layout = QVBoxLayout(update_panel)
        update_layout.setContentsMargins(16, 14, 16, 14)
        update_title = QLabel("APP UPDATES")
        update_title.setObjectName("CardTitle")
        self.update_status = QLabel(f"Current version: {updater.APP_VERSION}")
        self.update_status.setStyleSheet("color:#e0b65c;")
        update_buttons = QHBoxLayout()
        check_update = QPushButton("Check for App Update")
        check_update.setObjectName("PrimaryButton")
        check_update.clicked.connect(self.check_app_update)
        open_releases = QPushButton("Open Releases")
        open_releases.clicked.connect(lambda: webbrowser.open(updater.RELEASES_URL))
        update_buttons.addWidget(check_update)
        update_buttons.addWidget(open_releases)
        update_buttons.addStretch()
        update_layout.addWidget(update_title)
        update_layout.addWidget(self.update_status)
        update_layout.addLayout(update_buttons)
        p.addWidget(update_panel)

        p.addStretch()
        layout.addWidget(panel)
        layout.addStretch()
        return page

    def check_app_update(self):
        if hasattr(self, "update_status"):
            self.update_status.setText("Checking GitHub releases...")
        QApplication.processEvents()
        try:
            info = updater.check_for_update()
            if not info.update_available:
                if hasattr(self, "update_status"):
                    self.update_status.setText(f"StankyTools is current ({info.current_version}).")
                message = info.message or f"You are already on the latest version: {info.current_version}"
                QMessageBox.information(self, "No Update", message)
                return

            if hasattr(self, "update_status"):
                self.update_status.setText(f"Update available: {info.latest_version}")
            message = (
                f"A new StankyTools version is available.\n\n"
                f"Current: {info.current_version}\n"
                f"Latest: {info.latest_version}\n\n"
                "Download and install it now?"
            )
            if QMessageBox.question(self, "Update Available", message) != QMessageBox.Yes:
                return

            progress = QProgressDialog("Downloading update...", "Cancel", 0, 100, self)
            progress.setWindowTitle("StankyTools Update")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            def on_progress(done: int, total: int):
                if total > 0:
                    progress.setValue(max(0, min(100, int((done / total) * 100))))
                QApplication.processEvents()
                if progress.wasCanceled():
                    raise RuntimeError("Update download canceled.")

            zip_path = updater.download_update(info, progress=on_progress)
            progress.setValue(100)
            if hasattr(self, "update_status"):
                self.update_status.setText("Update downloaded. Restart required.")

            if not updater.is_packaged_app():
                QMessageBox.information(
                    self,
                    "Update Downloaded",
                    "The update ZIP was downloaded, but automatic install only works in the packaged EXE build. "
                    "When testing from `py main.py`, update from the GitHub release manually.",
                )
                webbrowser.open(info.html_url)
                return

            if QMessageBox.question(self, "Restart to Update", "Update downloaded. Restart StankyTools now to install it?") == QMessageBox.Yes:
                updater.stage_update_and_restart(zip_path)
                QApplication.quit()
        except Exception as exc:
            if hasattr(self, "update_status"):
                self.update_status.setText("Could not update StankyTools.")
            QMessageBox.critical(self, "Update Failed", str(exc))

    def _panel(self, title: str, content: QWidget) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        header = QLabel(title)
        header.setObjectName("SectionTitle")
        layout.addWidget(header)
        layout.addWidget(content, 1)
        return panel

    def refresh_all(self):
        self.refresh_catalog_categories()
        self.refresh_scan_categories()
        self.refresh_dashboard()
        self.refresh_catalog()
        self.refresh_market()
        self.refresh_pois()
        self.refresh_bases()
        self.refresh_map()

    def refresh_dashboard(self):
        while self.stat_grid.count():
            item = self.stat_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        guild = db.get_setting("guild_code", "").upper()
        if guild:
            self.sync_guild_dashboard_content(show_errors=False)
        if hasattr(self, "dashboard_guild_name"):
            self.dashboard_guild_name.setText(db.get_setting("guild_name", "Guild") or "Guild")
        if hasattr(self, "dashboard_user"):
            self.dashboard_user.setText("Profile: " + (db.get_setting("display_name", "Not joined") or "Not joined"))
        if hasattr(self, "dashboard_members"):
            members = getattr(self, "current_guild_members", None) or self.refresh_guild_members()
            self.dashboard_members.setText(f"Members: {len(members)}" if guild else "Members: —")
        if hasattr(self, "dashboard_guild_logo"):
            self.refresh_dashboard_guild_logo()
        stats = db.dashboard_stats()
        base_count = len(db.list_bases(guild)) if guild else 0
        members_count = len(getattr(self, "current_guild_members", []) or []) if guild else 0
        cards = [
            StatCard("Guild Members", fmt_price(members_count), "Current roster"),
            StatCard("Guild Bases", fmt_price(base_count), "Hagga Basin"),
            StatCard("Guild POIs", fmt_price(stats.get("pois", 0)), "Deep Desert intel"),
            StatCard("Items Tracked", fmt_price(stats.get("catalog_items", 0)), "Catalog database"),
        ]
        for i, card in enumerate(cards):
            self.stat_grid.addWidget(card, 0, i)
        self.refresh_dashboard_activity_tables()

    def refresh_catalog_categories(self):
        if not hasattr(self, "catalog_category"):
            return
        current = self.catalog_category.currentText()
        self.catalog_category.blockSignals(True)
        self.catalog_category.clear()
        self.catalog_category.addItem("All Categories")
        self.catalog_category.addItems(db.catalog_categories())
        if current:
            idx = self.catalog_category.findText(current)
            if idx >= 0:
                self.catalog_category.setCurrentIndex(idx)
        self.catalog_category.blockSignals(False)

    def refresh_catalog(self):
        if not hasattr(self, "catalog_table"):
            return
        search = self.catalog_search.text() if hasattr(self, "catalog_search") else ""
        category = self.catalog_category.currentText() if hasattr(self, "catalog_category") else ""
        rows = db.list_catalog(search, category)
        self.current_catalog_rows = rows
        self.catalog_table.setUpdatesEnabled(False)
        self.catalog_table.setSortingEnabled(False)
        self.catalog_table.setRowCount(0)
        for row in rows:
            table_row = self.catalog_table.rowCount()
            self.catalog_table.insertRow(table_row)

            image_item = QTableWidgetItem()
            image_item.setIcon(QIcon(catalog_image_pixmap(row["image_path"] if "image_path" in row.keys() else "", 72)))
            image_item.setData(Qt.UserRole, row["name"].lower())
            image_item.setData(Qt.UserRole + 10, int(row["id"]))
            image_item.setToolTip("Double-click to preview image")

            name_item = QTableWidgetItem(row["name"] or "—")
            name_item.setData(Qt.UserRole, (row["name"] or "").lower())
            name_item.setData(Qt.UserRole + 10, int(row["id"]))
            if row["source_url"]:
                name_item.setToolTip("Double-click to open item page")

            category_item = QTableWidgetItem(row["category"] or "—")
            category_item.setData(Qt.UserRole, (row["category"] or "").lower())
            category_item.setData(Qt.UserRole + 10, int(row["id"]))

            self.catalog_table.setItem(table_row, 0, image_item)
            self.catalog_table.setItem(table_row, 1, name_item)
            self.catalog_table.setItem(table_row, 2, category_item)
            self.catalog_table.setRowHeight(table_row, 82)
        self.catalog_table.setSortingEnabled(True)
        self.catalog_table.setUpdatesEnabled(True)

    def refresh_market(self):
        if not hasattr(self, "market_table"):
            return
        rows = db.market_summary(self.market_search.text() if hasattr(self, "market_search") else "")
        self.current_market_rows = rows
        self.market_table.setUpdatesEnabled(False)
        self.market_table.setSortingEnabled(False)
        self.market_table.setRowCount(0)
        for row in rows:
            grade = "—" if row["grade"] is None else f"G{row['grade']}"
            self.market_table.add_row([
                row["name"],
                row["category"],
                grade,
                row["low_price"],
                row["avg_price"],
                row["high_price"],
                row["seen_count"] or 0,
                row["last_seen"] or "—",
            ], {3, 4, 5, 6})
        self.market_table.setSortingEnabled(True)
        self.market_table.setUpdatesEnabled(True)

    def selected_market_item_id(self) -> tuple[int, str] | None:
        row_idx = self.market_table.currentRow()
        if row_idx < 0:
            return None
        name = self.market_table.item(row_idx, 0).text()
        category = self.market_table.item(row_idx, 1).text()
        for row in db.list_catalog(name, category):
            if row["name"] == name and row["category"] == category:
                return int(row["id"]), row["name"]
        return None

    def record_selected_market_price(self):
        selected = self.selected_market_item_id()
        if not selected:
            QMessageBox.information(self, "Select Item", "Select a market row first.")
            return
        item_id, name = selected
        dlg = PriceDialog(self, item_id, name)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_dashboard()
            self.refresh_market()

    def open_catalog_item(self, row: int, col: int):
        if row < 0 or row >= len(self.current_catalog_rows):
            return
        item = self.current_catalog_rows[row]
        if col == 0:
            self.show_catalog_image_preview(item)
            return
        if item["source_url"]:
            webbrowser.open(item["source_url"])

    def show_catalog_image_preview(self, item):
        dlg = QDialog(self)
        dlg.setWindowTitle(str(item["name"] or "Item Preview"))
        dlg.setMinimumSize(520, 560)
        layout = QVBoxLayout(dlg)
        title = QLabel(str(item["name"] or "Item"))
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignCenter)
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumHeight(420)
        pix = catalog_image_pixmap(item["image_path"] if "image_path" in item.keys() else "", 420)
        image_label.setPixmap(pix)
        meta = QLabel(str(item["category"] or ""))
        meta.setAlignment(Qt.AlignCenter)
        meta.setStyleSheet("color:#d4ae63; font-size:15px;")
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        layout.addWidget(title)
        layout.addWidget(image_label, 1)
        layout.addWidget(meta)
        layout.addWidget(close, alignment=Qt.AlignCenter)
        dlg.exec()

    def import_catalog(self):
        if getattr(self, "catalog_import_worker", None) is not None and self.catalog_import_worker.isRunning():
            QMessageBox.information(self, "Import Running", "Catalog import is already running.")
            return
        self.catalog_import_worker = CatalogImportWorker(self)
        self.catalog_import_worker.progress.connect(self.on_catalog_import_progress)
        self.catalog_import_worker.finished_ok.connect(self.on_catalog_import_finished)
        self.catalog_import_worker.failed.connect(self.on_catalog_import_failed)
        if hasattr(self, "catalog_import_button"):
            self.catalog_import_button.setEnabled(False)
        if hasattr(self, "catalog_import_progress"):
            self.catalog_import_progress.setRange(0, 0)
            self.catalog_import_progress.setVisible(True)
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText("Starting catalog import...")
        self.catalog_import_worker.start()

    def on_catalog_import_progress(self, message: str):
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText(message)

    def on_catalog_import_finished(self, result: dict):
        if hasattr(self, "catalog_import_button"):
            self.catalog_import_button.setEnabled(True)
        if hasattr(self, "catalog_import_progress"):
            self.catalog_import_progress.setRange(0, 1)
            self.catalog_import_progress.setValue(1)
            self.catalog_import_progress.setVisible(False)
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText(f"Import complete: {result}")
        self.refresh_all()
        QMessageBox.information(self, "Import Complete", str(result))

    def on_catalog_import_failed(self, message: str):
        if hasattr(self, "catalog_import_button"):
            self.catalog_import_button.setEnabled(True)
        if hasattr(self, "catalog_import_progress"):
            self.catalog_import_progress.setRange(0, 1)
            self.catalog_import_progress.setValue(0)
            self.catalog_import_progress.setVisible(False)
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText("Import failed.")
        QMessageBox.critical(self, "Import Failed", message)

    def check_map_update(self):
        try:
            meta = deep_desert.check_for_update()
            QMessageBox.information(self, "Deep Desert", f"Map checked. Changed: {meta.get('changed')}\nLast checked: {meta.get('last_checked')}")
            self.refresh_map()
        except Exception as exc:
            QMessageBox.critical(self, "Map Update Failed", str(exc))

    def refresh_map(self):
        self.refresh_hagga_map()
        if not hasattr(self, "map_view"):
            return
        static_map = PROJECT_ROOT / "data" / "deep_desert_map.png"
        if static_map.exists():
            self.map_view.set_map(str(static_map))
            self.refresh_pois()
            if hasattr(self, "poi_sync_status"):
                self.poi_sync_status.setText("Deep Desert map loaded from local tactical grid.")
            return
        meta = deep_desert.load_meta()
        image_path = meta.get("image_path", "")
        image_file = Path(image_path)
        if image_path and not image_file.is_absolute():
            image_file = PROJECT_ROOT / image_file
        if image_path and image_file.exists():
            self.map_view.set_map(str(image_file))
            self.refresh_pois()
            return

    def refresh_pois(self):
        if not hasattr(self, "poi_table"):
            return
        self.poi_table.setSortingEnabled(False)
        self.poi_table.setRowCount(0)
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            rows = []
        else:
            rows = [row for row in db.list_pois() if (row["guild_code"] if "guild_code" in row.keys() else "").upper() == guild]
        self.current_poi_rows = rows
        self.poi_by_id = {}
        self._refreshing_pois = True
        for row in rows:
            poi_type = row["poi_type"] if "poi_type" in row.keys() else "Custom"
            note = row["note"] if "note" in row.keys() else ""
            pooped = bool(row["pooped_on"]) if "pooped_on" in row.keys() else False
            table_row = self.poi_table.rowCount()
            self.poi_table.insertRow(table_row)
            poi_id = int(row["id"])
            self.poi_by_id[poi_id] = row

            type_item = QTableWidgetItem(poi_type or "Custom")
            type_item.setData(Qt.UserRole, (poi_type or "Custom").lower())
            type_item.setData(Qt.UserRole + 10, poi_id)

            tactical_status = poi_tactical_status(poi_type or "Custom", pooped)
            status_item = QTableWidgetItem(poi_status_label(tactical_status))
            status_item.setData(Qt.UserRole, tactical_status)
            status_item.setData(Qt.UserRole + 10, poi_id)
            status_item.setToolTip("Defeated = your guild has cleared this POI." if tactical_status == "defeated" else f"{poi_status_label(tactical_status)} marker")

            note_item = QTableWidgetItem(note or "—")
            note_item.setData(Qt.UserRole, (note or "").lower())
            note_item.setData(Qt.UserRole + 10, poi_id)
            note_item.setToolTip(note or "")

            self.poi_table.setItem(table_row, 0, type_item)
            self.poi_table.setItem(table_row, 1, status_item)
            self.poi_table.setItem(table_row, 2, note_item)
        self._refreshing_pois = False
        self.poi_table.resizeRowsToContents()
        for r in range(self.poi_table.rowCount()):
            self.poi_table.setRowHeight(r, max(54, self.poi_table.rowHeight(r)))
        self.poi_table.setSortingEnabled(True)
        if hasattr(self, "map_view"):
            self.map_view.draw_pois(rows, getattr(self, "selected_poi_id_for_map", None))

    def auto_sync_guild(self):
        if getattr(self, "_sync_running", False):
            return
        if not db.get_setting("guild_code", "") or not db.get_setting("display_name", ""):
            return
        now = time.monotonic()
        if now - getattr(self, "_last_auto_sync", 0.0) < 45:
            return
        self._last_auto_sync = now
        self.sync_guild_pois(show_popup=False)
        self.sync_guild_bases(show_popup=False)
        self.sync_guild_dashboard_content(show_errors=False)

    def refresh_activity(self):
        # Guild Activity feed has been removed from the UI.
        return

    def log_guild_activity(self, message: str, poi_id: int | None = None):
        guild = db.get_setting("guild_code", "").upper()
        actor = db.get_setting("display_name", "") or "System"
        url, key = active_supabase()
        if not guild or not url or not key:
            return
        try:
            payload = [{"guild_code": guild, "actor": actor, "message": message}]
            supabase_request("POST", url, key, "guild_activity", payload)
            self.sync_guild_dashboard_content(show_errors=False)
            self.refresh_dashboard_activity_tables()
        except Exception:
            pass

    def delete_remote_poi(self, poi):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild or "PASTE_" in key:
            return
        remote_id = poi["remote_id"] if "remote_id" in poi.keys() else ""
        if not remote_id:
            return
        try:
            endpoint = f"guild_pois?id=eq.{urllib.parse.quote(str(remote_id))}"
            supabase_request("DELETE", url, key, endpoint)
        except Exception:
            pass

    def sync_guild_pois(self, show_popup: bool = True):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        display_name = db.get_setting("display_name", "")
        if not url or not key or not guild or "PASTE_" in key:
            if show_popup:
                QMessageBox.information(self, "Guild Sync", "Join or create a guild before syncing POIs.")
            return
        try:
            self._sync_running = True
            # Keep member presence/role fresh.
            try:
                supabase_request("POST", url, key, "guild_members?on_conflict=guild_code,display_name", [{
                    "guild_code": guild,
                    "display_name": display_name,
                    "role": db.get_setting("guild_role", "member") or "member",
                }])
                role_rows = supabase_request("GET", url, key, f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(display_name)}&select=role&limit=1")
                role = (role_rows[0].get("role") if role_rows else db.get_setting("guild_role", "member")) or "member"
                db.set_setting("guild_role", role)
                if hasattr(self, "guild_role_label"):
                    self.guild_role_label.setText("Role: " + role)
            except Exception:
                pass

            # Pull remote POIs for this guild.
            endpoint = f"guild_pois?guild_code=eq.{urllib.parse.quote(guild)}&select=*"
            remote = supabase_request("GET", url, key, endpoint)
            remote_ids = set()
            for item in remote:
                remote_id = str(item.get("id", ""))
                if remote_id:
                    remote_ids.add(remote_id)
                label = item.get("name") or item.get("label") or "Untitled POI"
                note = item.get("notes") if item.get("notes") is not None else item.get("note", "")
                poi_type = item.get("poi_type") or item.get("type") or "Custom"
                created_by = item.get("created_by") or ""
                last_updated_by = item.get("last_updated_by") or created_by
                pooped_on = bool(item.get("pooped_on", False))
                db.upsert_remote_poi(
                    remote_id,
                    float(item.get("x", 0)),
                    float(item.get("y", 0)),
                    label,
                    note or "",
                    guild,
                    poi_type=poi_type,
                    created_by=created_by,
                    last_updated_by=last_updated_by,
                    pooped_on=pooped_on,
                )

            # Push local POIs. Existing remote_id is reused; missing remote_id gets a client UUID.
            local = db.list_unsynced_pois(guild)
            payload = []
            local_remote_pairs: list[tuple[int, str]] = []
            for row in local:
                rid = row["remote_id"] or str(uuid.uuid4())
                poi_type = row["poi_type"] if "poi_type" in row.keys() else "Custom"
                created_by = row["created_by"] if "created_by" in row.keys() else display_name
                last_updated_by = row["last_updated_by"] if "last_updated_by" in row.keys() else display_name
                pooped_on = bool(row["pooped_on"]) if "pooped_on" in row.keys() else False
                payload.append({
                    "id": rid,
                    "guild_code": guild,
                    "name": row["label"],
                    "poi_type": poi_type or "Custom",
                    "notes": row["note"] or "",
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "created_by": created_by or display_name or "Unknown",
                    "last_updated_by": last_updated_by or display_name or "Unknown",
                    "pooped_on": pooped_on,
                })
                local_remote_pairs.append((int(row["id"]), rid))

            uploaded = 0
            if payload:
                supabase_request("POST", url, key, "guild_pois?on_conflict=id", payload)
                uploaded = len(payload)
                for local_id, rid in local_remote_pairs:
                    db.set_poi_remote_id(local_id, rid)

            self.refresh_pois()
            self.refresh_dashboard()
            if hasattr(self, "poi_sync_status"):
                self.poi_sync_status.setText(f"Auto-sync active. Pulled {len(remote)} POIs. Uploaded/updated {uploaded}.")
            if show_popup:
                QMessageBox.information(
                    self,
                    "Guild Sync",
                    f"Sync complete. Pulled {len(remote)} POIs and uploaded/updated {uploaded} local POIs.",
                )
        except Exception as exc:
            if show_popup:
                QMessageBox.critical(self, "Guild Sync Failed", str(exc))
            elif hasattr(self, "poi_sync_status"):
                self.poi_sync_status.setText(f"Auto-sync issue: {exc}")
        finally:
            self._sync_running = False


    def refresh_dashboard_activity_tables(self):
        guild = db.get_setting("guild_code", "").upper()
        if hasattr(self, "dashboard_links_table"):
            self.dashboard_links_table.setSortingEnabled(False)
            self.dashboard_links_table.setRowCount(0)
            self.current_dashboard_links = db.list_guild_links(guild, 12)
            for row in self.current_dashboard_links:
                self.dashboard_links_table.add_row([row["title"] or "Untitled", row["url"] or "", row["created_by"] or "—"])
            self.dashboard_links_table.setSortingEnabled(True)
            self.dashboard_links_table.resizeRowsToContents()
        if hasattr(self, "news_table"):
            self.news_table.setSortingEnabled(False)
            self.news_table.setRowCount(0)
            self.current_dashboard_news = db.list_guild_news(guild, 12)
            for row in self.current_dashboard_news:
                title_body = (row["title"] or "Guild Update")
                if row["body"]:
                    title_body += " — " + str(row["body"]).replace("\n", " ")
                self.news_table.add_row([
                    format_app_date(row["created_at"]),
                    row["created_by"] or "—",
                    title_body,
                ])
            self.news_table.setSortingEnabled(True)
            self.news_table.resizeRowsToContents()

    def refresh_guild_page(self):
        guild = db.get_setting("guild_code", "").upper()
        self.sync_guild_dashboard_content(show_errors=False)
        if hasattr(self, "guild_page_members"):
            self.guild_page_members.setSortingEnabled(False)
            self.guild_page_members.setRowCount(0)
            for item in getattr(self, "current_guild_members", []) or []:
                self.guild_page_members.add_row([item.get("display_name", ""), item.get("role", "member")])
            self.guild_page_members.setSortingEnabled(True)
        if hasattr(self, "guild_page_news"):
            self.guild_page_news.setSortingEnabled(False)
            self.guild_page_news.setRowCount(0)
            self.current_guild_news = db.list_guild_news(guild, 30)
            for row in self.current_guild_news:
                text = (row["title"] or "Guild Update")
                if row["body"]:
                    text += " — " + str(row["body"]).replace("\n", " ")
                self.guild_page_news.add_row([format_app_date(row["created_at"]), row["created_by"] or "—", text])
            self.guild_page_news.setSortingEnabled(True)
        if hasattr(self, "guild_page_links"):
            self.guild_page_links.setSortingEnabled(False)
            self.guild_page_links.setRowCount(0)
            self.current_guild_links = db.list_guild_links(guild, 50)
            for row in self.current_guild_links:
                self.guild_page_links.add_row([row["title"] or "Untitled", row["url"] or "", row["created_by"] or "—"])
            self.guild_page_links.setSortingEnabled(True)
        if hasattr(self, "guild_page_activity"):
            self.guild_page_activity.setSortingEnabled(False)
            self.guild_page_activity.setRowCount(0)
            for row in db.list_guild_activity(guild, 40):
                self.guild_page_activity.add_row([format_app_date(row["created_at"]), row["actor"] or "—", row["message"] or "—"])
            self.guild_page_activity.setSortingEnabled(True)
            self.guild_page_activity.resizeRowsToContents()

    def sync_guild_dashboard_content(self, show_errors: bool = False):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild:
            return
        try:
            news = supabase_request("GET", url, key, f"guild_news?guild_code=eq.{urllib.parse.quote(guild)}&select=*&order=created_at.desc&limit=30")
            db.cache_guild_news(news, guild)
        except Exception as exc:
            if show_errors:
                QMessageBox.warning(self, "Guild News", str(exc))
        try:
            activity = supabase_request("GET", url, key, f"guild_activity?guild_code=eq.{urllib.parse.quote(guild)}&select=*&order=created_at.desc&limit=40")
            db.cache_guild_activity(activity, guild)
        except Exception:
            pass
        try:
            links = supabase_request("GET", url, key, f"guild_links?guild_code=eq.{urllib.parse.quote(guild)}&select=*&order=title.asc")
            db.cache_guild_links(links, guild)
        except Exception:
            pass

    def submit_guild_news(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can submit guild news.")
            return
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            QMessageBox.information(self, "Guild News", "Join or create a guild first.")
            return
        title, ok = QInputDialog.getText(self, "Guild News", "Title:")
        if not ok or not title.strip():
            return
        body, ok = QInputDialog.getMultiLineText(self, "Guild News", "Update:", "")
        if not ok:
            return
        url, key = active_supabase()
        try:
            payload = [{
                "guild_code": guild,
                "title": title.strip(),
                "body": body.strip(),
                "created_by": db.get_setting("display_name", ""),
            }]
            supabase_request("POST", url, key, "guild_news", payload)
            self.log_guild_activity(f"posted guild news: {title.strip()}")
            self.refresh_guild_page()
            self.refresh_dashboard()
        except Exception as exc:
            QMessageBox.critical(self, "Guild News Failed", str(exc))


    def _news_row_from_table(self, table_name: str, row: int):
        rows = getattr(self, "current_guild_news" if table_name == "guild" else "current_dashboard_news", []) or []
        if 0 <= row < len(rows):
            return rows[row]
        return None

    def show_dashboard_news_detail(self, row: int, col: int):
        news = self._news_row_from_table("dashboard", row)
        if not news:
            return
        title = news["title"] or "Guild Update"
        body = news["body"] or "No details were provided."
        QMessageBox.information(self, title, body)

    def show_guild_news_detail(self, row: int, col: int):
        news = self._news_row_from_table("guild", row)
        if not news:
            return
        title = news["title"] or "Guild Update"
        body = news["body"] or "No details were provided."
        QMessageBox.information(self, title, body)

    def delete_selected_guild_news(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can delete guild news.")
            return
        if not hasattr(self, "guild_page_news"):
            return
        row = self.guild_page_news.currentRow()
        news = self._news_row_from_table("guild", row)
        if not news:
            QMessageBox.information(self, "Guild News", "Select a news item first.")
            return
        rid = str(news["remote_id"] or "")
        if not rid:
            QMessageBox.warning(self, "Guild News", "This news item does not have a remote id yet. Refresh and try again.")
            return
        if QMessageBox.question(self, "Delete Guild News", "Delete this guild news update?") != QMessageBox.Yes:
            return
        try:
            supabase_request("DELETE", *active_supabase(), f"guild_news?id=eq.{urllib.parse.quote(rid)}")
            self.log_guild_activity("deleted a guild news update")
            self.sync_guild_dashboard_content(show_errors=False)
            self.refresh_guild_page()
            self.refresh_dashboard()
        except Exception as exc:
            QMessageBox.critical(self, "Guild News Failed", str(exc))

    def open_selected_dashboard_link(self, row: int, col: int):
        links = getattr(self, "current_dashboard_links", []) or []
        if 0 <= row < len(links):
            url = links[row]["url"] or ""
            if url:
                webbrowser.open(url)

    def add_guild_link(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can add useful links.")
            return
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            QMessageBox.information(self, "Useful Links", "Join or create a guild first.")
            return
        title, ok = QInputDialog.getText(self, "Useful Link", "Title:")
        if not ok or not title.strip():
            return
        link, ok = QInputDialog.getText(self, "Useful Link", "URL:")
        if not ok or not link.strip():
            return
        if not link.lower().startswith(("http://", "https://")):
            link = "https://" + link
        try:
            supabase_request("POST", *active_supabase(), "guild_links", [{
                "guild_code": guild,
                "title": title.strip(),
                "url": link.strip(),
                "created_by": db.get_setting("display_name", ""),
            }])
            self.log_guild_activity(f"added useful link: {title.strip()}")
            self.refresh_guild_page()
        except Exception as exc:
            QMessageBox.critical(self, "Useful Link Failed", str(exc))

    def selected_guild_link_remote_id(self) -> str:
        if not hasattr(self, "guild_page_links"):
            return ""
        row = self.guild_page_links.currentRow()
        if row < 0:
            return ""
        links = getattr(self, "current_guild_links", []) or []
        if row >= len(links):
            return ""
        return str(links[row]["remote_id"] or "")

    def open_selected_guild_link(self, row: int, col: int):
        links = getattr(self, "current_guild_links", []) or []
        if 0 <= row < len(links):
            url = links[row]["url"] or ""
            if url:
                webbrowser.open(url)

    def edit_guild_link(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can edit useful links.")
            return
        rid = self.selected_guild_link_remote_id()
        if not rid:
            QMessageBox.information(self, "Useful Links", "Select a link first.")
            return
        row = self.guild_page_links.currentRow()
        links = getattr(self, "current_guild_links", []) or []
        old = links[row] if 0 <= row < len(links) else None
        title, ok = QInputDialog.getText(self, "Useful Link", "Title:", text=(old["title"] if old else ""))
        if not ok or not title.strip():
            return
        link, ok = QInputDialog.getText(self, "Useful Link", "URL:", text=(old["url"] if old else ""))
        if not ok or not link.strip():
            return
        try:
            supabase_request("PATCH", *active_supabase(), f"guild_links?id=eq.{urllib.parse.quote(rid)}", {"title": title.strip(), "url": link.strip()})
            self.refresh_guild_page()
        except Exception as exc:
            QMessageBox.critical(self, "Useful Link Failed", str(exc))

    def delete_guild_link(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can delete useful links.")
            return
        rid = self.selected_guild_link_remote_id()
        if not rid:
            QMessageBox.information(self, "Useful Links", "Select a link first.")
            return
        if QMessageBox.question(self, "Delete Link", "Delete this useful link?") != QMessageBox.Yes:
            return
        try:
            supabase_request("DELETE", *active_supabase(), f"guild_links?id=eq.{urllib.parse.quote(rid)}")
            self.refresh_guild_page()
        except Exception as exc:
            QMessageBox.critical(self, "Useful Link Failed", str(exc))

    def refresh_scan_categories(self):
        """Populate scanner category dropdown from the catalog."""
        if not hasattr(self, "scan_category"):
            return
        current = self.scan_category.currentText()
        self.scan_category.blockSignals(True)
        self.scan_category.clear()
        self.scan_category.addItems(db.catalog_categories())
        if current:
            idx = self.scan_category.findText(current)
            if idx >= 0:
                self.scan_category.setCurrentIndex(idx)
        self.scan_category.blockSignals(False)
        self.refresh_scan_items()

    def refresh_scan_items(self):
        """Populate scanner item dropdown for the selected category."""
        if not hasattr(self, "scan_item"):
            return
        category = self.scan_category.currentText() if hasattr(self, "scan_category") else ""
        rows = db.list_catalog("", category)
        self._scan_item_rows = rows
        current_id = self.scan_item.currentData() if self.scan_item.count() else None
        self.scan_item.blockSignals(True)
        self.scan_item.clear()
        for row in rows:
            self.scan_item.addItem(row["name"], int(row["id"]))
        if current_id is not None:
            for i in range(self.scan_item.count()):
                if self.scan_item.itemData(i) == current_id:
                    self.scan_item.setCurrentIndex(i)
                    break
        self.scan_item.blockSignals(False)

    def record_scanner_price(self):
        """Record a manual/OCR price for the currently selected catalog item."""
        if not hasattr(self, "scan_item") or self.scan_item.currentIndex() < 0:
            QMessageBox.information(self, "Scanner", "Select a catalog item first.")
            return
        item_id = int(self.scan_item.currentData())
        name = self.scan_item.currentText()
        grade_text = self.scan_grade.currentText() if hasattr(self, "scan_grade") else "No Grade"
        grade = None if grade_text == "No Grade" else int(grade_text.replace("Grade", "").strip())
        price = int(self.scan_price.value())
        try:
            db.record_price(item_id, price, grade)
            self.scan_status.setText(f"Recorded {fmt_price(price)} for {name}.")
            self.refresh_dashboard()
            self.refresh_market()
        except Exception as exc:
            QMessageBox.critical(self, "Scanner Error", str(exc))

    def ocr_price_from_file(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose cropped price image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        price = ocr_price_from_image(path)
        if price:
            self.scan_price.setValue(price)
            self.scan_status.setText(f"OCR read price: {fmt_price(price)}")
        else:
            QMessageBox.information(self, "OCR Price", "Could not read a clean numeric price from that image.")

    def selected_poi_id(self) -> int | None:
        if not hasattr(self, "poi_table"):
            return None
        row = self.poi_table.currentRow()
        if row < 0:
            return None
        for col in range(self.poi_table.columnCount()):
            item = self.poi_table.item(row, col)
            if item is not None:
                poi_id = item.data(Qt.UserRole + 10)
                if poi_id is not None:
                    return int(poi_id)
        return None

    def center_on_poi(self, row: int, col: int):
        if row < 0 or not hasattr(self, "poi_table"):
            return
        poi_id = None
        for c in range(self.poi_table.columnCount()):
            item = self.poi_table.item(row, c)
            if item is not None:
                poi_id = item.data(Qt.UserRole + 10)
                if poi_id is not None:
                    break
        if poi_id is None:
            return
        poi = getattr(self, "poi_by_id", {}).get(int(poi_id))
        if not poi:
            return
        self.selected_poi_id_for_map = int(poi_id)
        if hasattr(self, "map_view"):
            self.map_view.draw_pois(self.current_poi_rows, self.selected_poi_id_for_map)
            self.map_view.center_on(float(poi["x"]), float(poi["y"]))

    def can_manage_poi(self, poi) -> bool:
        role = (db.get_setting("guild_role", "member") or "member").lower()
        current_user = db.get_setting("display_name", "")
        creator = poi["created_by"] if "created_by" in poi.keys() else ""
        return role in {"owner", "officer"} or (creator and creator == current_user)


    def show_poi_context_menu(self, pos):
        if not hasattr(self, "poi_table"):
            return
        row = self.poi_table.rowAt(pos.y())
        if row < 0:
            return
        self.poi_table.selectRow(row)
        self.center_on_poi(row, 0)
        menu = QMenu(self)
        friendly_action = menu.addAction("Set Friendly")
        enemy_action = menu.addAction("Set Enemy")
        defeated_action = menu.addAction("Set Defeated")
        menu.addSeparator()
        edit_action = menu.addAction("Edit Note")
        delete_action = menu.addAction("Delete POI")
        chosen = menu.exec(self.poi_table.viewport().mapToGlobal(pos))
        if chosen == friendly_action:
            self.set_selected_poi_status("friendly")
        elif chosen == enemy_action:
            self.set_selected_poi_status("enemy")
        elif chosen == defeated_action:
            self.set_selected_poi_status("defeated")
        elif chosen == edit_action:
            self.edit_selected_poi()
        elif chosen == delete_action:
            self.delete_selected_poi()

    def set_selected_poi_status(self, status: str):
        if not self._require_guild_for_map_action("POI status changes"):
            return
        poi_id = self.selected_poi_id()
        if not poi_id:
            return
        poi = db.get_poi(poi_id)
        if not poi:
            return
        current_type = poi["poi_type"] if "poi_type" in poi.keys() else poi["label"]
        note = poi["note"] if "note" in poi.keys() else ""
        status = (status or "active").strip().lower()
        if status == "friendly":
            poi_type = "Friendly Base"
            defeated = False
        elif status == "enemy":
            poi_type = "Enemy Base"
            defeated = False
        elif status == "defeated":
            poi_type = current_type or "Enemy Base"
            defeated = True
        else:
            poi_type = current_type or "Custom"
            defeated = False
        db.update_poi(poi_id, poi_type, note, pooped_on=defeated, updated_by=db.get_setting("display_name", ""))
        self.sync_guild_pois(show_popup=False)
        self.refresh_pois()
        self.refresh_dashboard()

    def edit_selected_poi(self):
        if not self._require_guild_for_map_action("POI editing"):
            return
        poi_id = self.selected_poi_id()
        if not poi_id:
            QMessageBox.information(self, "Edit POI", "Select a POI first.")
            return
        poi = db.get_poi(poi_id)
        if not poi:
            return
        if not self.can_manage_poi(poi):
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers or the POI creator can edit this marker.")
            return
        current_type = poi["poi_type"] if "poi_type" in poi.keys() else "Custom"
        current_note = poi["note"] if "note" in poi.keys() else ""
        poi_type, ok = QInputDialog.getItem(
            self,
            "POI Type",
            "Type:",
            ["Enemy Base", "Friendly Base", "Spice", "Resource", "Vehicle", "Danger", "Note", "Custom"],
            0,
            False,
        )
        if not ok:
            return
        note_dialog = QDialog(self)
        note_dialog.setWindowTitle("POI Note")
        note_dialog.setMinimumSize(620, 420)
        note_layout = QVBoxLayout(note_dialog)
        note_label = QLabel("Note:")
        note_edit = QTextEdit()
        note_edit.setPlainText(current_note)
        note_layout.addWidget(note_label)
        note_layout.addWidget(note_edit, 1)
        note_buttons = QHBoxLayout()
        note_cancel = QPushButton("Cancel")
        note_save = QPushButton("Save")
        note_save.setObjectName("PrimaryButton")
        note_cancel.clicked.connect(note_dialog.reject)
        note_save.clicked.connect(note_dialog.accept)
        note_buttons.addStretch()
        note_buttons.addWidget(note_cancel)
        note_buttons.addWidget(note_save)
        note_layout.addLayout(note_buttons)
        if note_dialog.exec() != QDialog.Accepted:
            return
        note = note_edit.toPlainText()
        pooped = False
        if hasattr(self, "poi_table") and self.poi_table.currentRow() >= 0:
            status_item = self.poi_table.item(self.poi_table.currentRow(), 1)
            pooped = (status_item.text().lower() == "defeated") if status_item else False
        db.update_poi(poi_id, poi_type, note, pooped_on=pooped, updated_by=db.get_setting("display_name", ""))
        self.log_guild_activity(f"updated POI: {poi_type}")
        self.sync_guild_pois(show_popup=False)
        self.refresh_pois()
        self.refresh_dashboard()

    def delete_selected_poi(self):
        if not self._require_guild_for_map_action("POI deletion"):
            return
        poi_id = self.selected_poi_id()
        if not poi_id:
            QMessageBox.information(self, "Delete POI", "Select a POI first.")
            return
        poi = db.get_poi(poi_id)
        if not poi:
            return
        if QMessageBox.question(self, "Delete POI", "Delete this POI?") != QMessageBox.Yes:
            return
        self.delete_remote_poi(poi)
        db.delete_poi(poi_id)
        self.log_guild_activity("deleted a POI")
        self.refresh_pois()
        self.refresh_dashboard()

    def _require_guild_for_map_action(self, action_name: str = "this action") -> bool:
        if db.get_setting("guild_code", "").strip() and db.get_setting("display_name", "").strip():
            return True
        QMessageBox.information(
            self,
            "Guild Required",
            f"Join or create a guild before using {action_name}.",
        )
        return False

    def add_poi_at(self, x: float, y: float):
        if not self._require_guild_for_map_action("guild POIs"):
            return
        poi_type, ok = QInputDialog.getItem(
            self,
            "Add POI",
            "Type:",
            ["Enemy Base", "Friendly Base", "Spice", "Resource", "Vehicle", "Danger", "Note", "Custom"],
            0,
            False,
        )
        if not ok:
            return
        note_dialog = QDialog(self)
        note_dialog.setWindowTitle("POI Note")
        note_dialog.setMinimumSize(620, 420)
        note_layout = QVBoxLayout(note_dialog)
        note_layout.addWidget(QLabel("Note:"))
        note_edit = QTextEdit()
        note_layout.addWidget(note_edit, 1)
        note_buttons = QHBoxLayout()
        note_cancel = QPushButton("Cancel")
        note_save = QPushButton("Save")
        note_save.setObjectName("PrimaryButton")
        note_cancel.clicked.connect(note_dialog.reject)
        note_save.clicked.connect(note_dialog.accept)
        note_buttons.addStretch()
        note_buttons.addWidget(note_cancel)
        note_buttons.addWidget(note_save)
        note_layout.addLayout(note_buttons)
        if note_dialog.exec() != QDialog.Accepted:
            return
        note = note_edit.toPlainText()
        guild = db.get_setting("guild_code", "").upper()
        user = db.get_setting("display_name", "")
        db.add_poi(x, y, poi_type, note, guild_code=guild, poi_type=poi_type, created_by=user)
        self.log_guild_activity(f"added POI: {poi_type}")
        self.sync_guild_pois(show_popup=False)
        self.refresh_pois()
        self.refresh_dashboard()

    SEITCHES = [
        "Abbir", "al-Mut", "Alraab", "Barkan", "Coanua", "Eaqrab", "Fajr", "Gara Kulon",
        "Hajar", "Jacurutu", "Kathib", "Khafash", "Legg", "Makab", "Nadir", "Rajifri",
        "Ramal", "Rifana", "Saajid", "Sandrat", "Ta'lab", "Tabr", "Tharwa", "Umbu", "Yaracuwan",
    ]

    def refresh_hagga_map(self):
        if not hasattr(self, "hagga_map_view"):
            return
        image_path = Path(__file__).resolve().parents[1] / "data" / "hagga_basin_map.png"
        if image_path.exists():
            self.hagga_map_view.set_map(str(image_path))
            self.refresh_bases()
        elif hasattr(self, "base_sync_status"):
            self.base_sync_status.setText("Missing data/hagga_basin_map.png")

    def refresh_bases(self):
        if not hasattr(self, "base_table"):
            return
        guild = db.get_setting("guild_code", "").upper()
        rows = db.list_bases(guild) if guild else []
        self.current_base_rows = rows
        self.base_by_id = {}
        self.base_table.setSortingEnabled(False)
        self.base_table.setRowCount(0)
        for row in rows:
            table_row = self.base_table.rowCount()
            self.base_table.insertRow(table_row)
            base_id = int(row["id"])
            self.base_by_id[base_id] = row
            member = row["created_by"] or "—"
            status = base_status_label(row["status"] if "status" in row.keys() else "friendly")
            vals = [f"● {member}", row["base_name"] or "Guild Base", row["seitch"] or "—", status]
            member_color = profile_color(member)
            status_color = base_status_color(status)
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.UserRole, str(val).lower())
                item.setData(Qt.UserRole + 10, base_id)
                if col == 0:
                    item.setForeground(QBrush(member_color))
                    item.setToolTip(f"{member}'s profile color: {member_color.name()}")
                if col == 3:
                    item.setForeground(QBrush(status_color))
                    item.setToolTip("Base tactical status")
                self.base_table.setItem(table_row, col, item)
        self.base_table.setSortingEnabled(True)
        if hasattr(self, "hagga_map_view"):
            self.hagga_map_view.draw_bases(rows, getattr(self, "selected_base_id_for_map", None))

    def selected_base_id(self) -> int | None:
        if not hasattr(self, "base_table"):
            return None
        row = self.base_table.currentRow()
        if row < 0:
            return None
        for col in range(self.base_table.columnCount()):
            item = self.base_table.item(row, col)
            if item is not None:
                base_id = item.data(Qt.UserRole + 10)
                if base_id is not None:
                    return int(base_id)
        return None

    def center_on_base(self, row: int, col: int):
        base_id = None
        for c in range(self.base_table.columnCount()):
            item = self.base_table.item(row, c)
            if item is not None:
                base_id = item.data(Qt.UserRole + 10)
                if base_id is not None:
                    break
        if base_id is None:
            return
        self.selected_base_id_for_map = int(base_id)
        base = getattr(self, "base_by_id", {}).get(int(base_id))
        if base and hasattr(self, "hagga_map_view"):
            self.hagga_map_view.draw_bases(self.current_base_rows, self.selected_base_id_for_map)
            self.hagga_map_view.center_on(float(base["x"]), float(base["y"]))

    def _base_count_for_user(self) -> int:
        guild = db.get_setting("guild_code", "").upper()
        user = db.get_setting("display_name", "")
        return len([b for b in db.list_bases(guild) if (b["created_by"] or "") == user])

    def add_base_dialog(self):
        if not hasattr(self, "hagga_map_view"):
            return
        if not self._require_guild_for_map_action("guild bases"):
            return
        QMessageBox.information(self, "Add Base", "Double-click the Hagga Basin map where the base is located.")

    def add_base_at(self, x: float, y: float):
        guild = db.get_setting("guild_code", "").upper()
        user = db.get_setting("display_name", "")
        if not guild or not user:
            QMessageBox.information(self, "Guild Base", "Join a guild first before placing base markers.")
            return
        if self._base_count_for_user() >= 3:
            QMessageBox.warning(self, "Guild Base", "Each member can only have 3 bases.")
            return
        base_name, ok = QInputDialog.getText(self, "Base Name", "Base name:", text=f"{user}'s Base")
        if not ok or not base_name.strip():
            return
        seitch, ok = QInputDialog.getItem(self, "Seitch", "Base seitch:", self.SEITCHES, 0, False)
        if not ok:
            return
        db.add_base(x, y, base_name.strip(), seitch, guild, user)
        self.log_guild_activity(f"added base: {base_name.strip()}")
        self.sync_guild_bases(show_popup=False)
        self.refresh_bases()
        self.refresh_dashboard()

    def edit_selected_base(self):
        if not self._require_guild_for_map_action("base editing"):
            return
        base_id = self.selected_base_id()
        if not base_id:
            QMessageBox.information(self, "Edit Base", "Select a base marker first.")
            return
        base = db.get_base(base_id)
        if not base:
            return
        user = db.get_setting("display_name", "")
        if (base["created_by"] or "") != user:
            QMessageBox.warning(self, "Permission Denied", "You can only edit your own bases.")
            return
        base_name, ok = QInputDialog.getText(self, "Base Name", "Base name:", text=base["base_name"] or "Guild Base")
        if not ok or not base_name.strip():
            return
        current = self.SEITCHES.index(base["seitch"]) if base["seitch"] in self.SEITCHES else 0
        seitch, ok = QInputDialog.getItem(self, "Seitch", "Base seitch:", self.SEITCHES, current, False)
        if not ok:
            return
        db.update_base(base_id, base_name.strip(), seitch)
        self.log_guild_activity(f"updated base: {base_name.strip()}")
        self.sync_guild_bases(show_popup=False)
        self.refresh_bases()

    def delete_selected_base(self):
        if not self._require_guild_for_map_action("base deletion"):
            return
        base_id = self.selected_base_id()
        if not base_id:
            QMessageBox.information(self, "Delete Base", "Select a base marker first.")
            return
        base = db.get_base(base_id)
        if not base:
            return
        user = db.get_setting("display_name", "")
        if (base["created_by"] or "") != user:
            QMessageBox.warning(self, "Permission Denied", "You can only delete your own bases.")
            return
        if QMessageBox.question(self, "Delete Base", "Delete this base marker?") != QMessageBox.Yes:
            return
        self.delete_remote_base(base)
        db.delete_base(base_id)
        self.log_guild_activity("deleted a base")
        self.refresh_bases()
        self.refresh_dashboard()


    def show_base_context_menu(self, pos):
        if not hasattr(self, "base_table"):
            return
        row = self.base_table.rowAt(pos.y())
        if row < 0:
            return
        self.base_table.selectRow(row)
        self.center_on_base(row, 0)
        menu = QMenu(self)
        edit_action = menu.addAction("Edit Base")
        delete_action = menu.addAction("Remove Base")
        chosen = menu.exec(self.base_table.viewport().mapToGlobal(pos))
        if chosen == edit_action:
            self.edit_selected_base()
        elif chosen == delete_action:
            self.delete_selected_base()

    def set_selected_base_status(self, status: str):
        base_id = self.selected_base_id()
        if not base_id:
            return
        if not role_can_manage_guild():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can change base status.")
            return
        status = normalize_base_status(status)
        db.update_base_status(base_id, status)
        self.log_guild_activity(f"set base status to {status}")
        self.sync_guild_bases(show_popup=False)
        self.refresh_bases()

    def _current_guild_admin(self) -> bool:
        return role_can_manage_guild()

    def refresh_guild_logo_widgets(self):
        path = guild_logo_cache_path()
        fallback = asset_path("images", "default_guild_logo.png")
        pix = QPixmap(str(path)) if path.exists() else QPixmap(str(fallback)) if fallback.exists() else QPixmap()
        widgets = []
        if hasattr(self, "dashboard_guild_logo"):
            widgets.append(self.dashboard_guild_logo)
        if hasattr(self, "settings_guild_logo"):
            widgets.append(self.settings_guild_logo)
        for label in widgets:
            if not pix.isNull():
                label.setPixmap(pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                label.setText("")
            else:
                label.setPixmap(QPixmap())
                label.setText("Guild\nLogo")

    def refresh_dashboard_guild_logo(self):
        self.refresh_guild_logo_widgets()

    def sync_guild_logo_from_remote(self):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild:
            self.refresh_guild_logo_widgets()
            return
        try:
            rows = supabase_request("GET", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}&select=logo_data&limit=1")
            logo_data = (rows[0].get("logo_data") if rows else "") or ""
            path = guild_logo_cache_path()
            if logo_data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(base64.b64decode(logo_data))
            elif path.exists():
                path.unlink()
        except Exception:
            pass
        self.refresh_guild_logo_widgets()

    def upload_guild_logo(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can upload the guild logo.")
            return
        guild = db.get_setting("guild_code", "").upper()
        url, key = active_supabase()
        if not guild or not url or not key:
            QMessageBox.information(self, "Guild Logo", "Join a guild first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose Guild Logo", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, "Guild Logo", "That image could not be loaded.")
            return
        cache = guild_logo_cache_path()
        cache.parent.mkdir(parents=True, exist_ok=True)
        pix.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(cache), "PNG")
        encoded = base64.b64encode(cache.read_bytes()).decode("ascii")
        try:
            supabase_request("PATCH", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}", {"logo_data": encoded})
            self.refresh_guild_logo_widgets()
            self.refresh_dashboard()
            QMessageBox.information(self, "Guild Logo", "Guild logo updated.")
        except Exception as exc:
            QMessageBox.critical(self, "Guild Logo", f"Could not upload logo. Make sure the guilds.logo_data column exists.\n\n{exc}")

    def delete_guild_logo(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can delete the guild logo.")
            return
        if QMessageBox.question(self, "Delete Guild Logo", "Delete the current guild logo?") != QMessageBox.Yes:
            return
        guild = db.get_setting("guild_code", "").upper()
        url, key = active_supabase()
        try:
            if guild and url and key:
                supabase_request("PATCH", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}", {"logo_data": ""})
            path = guild_logo_cache_path()
            if path.exists():
                path.unlink()
            self.refresh_guild_logo_widgets()
            self.refresh_dashboard()
        except Exception as exc:
            QMessageBox.critical(self, "Guild Logo", str(exc))

    def show_members_roles_dialog(self):
        """Open member/role management only when requested."""
        rows = self.refresh_guild_members()
        dlg = QDialog(self)
        dlg.setWindowTitle("Guild Members / Roles")
        dlg.setMinimumSize(640, 460)
        layout = QVBoxLayout(dlg)
        title = QLabel("Guild Members / Roles")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        info = QLabel("Members are hidden from Settings until this window is opened.")
        info.setStyleSheet("color:#9f8150;")
        layout.addWidget(info)

        table = StankyTable(["Member", "Role"])
        table.setSortingEnabled(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(table, 1)

        def populate():
            fresh = self.refresh_guild_members()
            table.setRowCount(0)
            for item in fresh:
                r = table.rowCount()
                table.insertRow(r)
                name_item = QTableWidgetItem(str(item.get("display_name", "")))
                name_item.setData(Qt.UserRole, str(item.get("display_name", "")))
                role_item = QTableWidgetItem(str(item.get("role", "member")))
                role_item.setData(Qt.UserRole, str(item.get("role", "member")))
                table.setItem(r, 0, name_item)
                table.setItem(r, 1, role_item)

        def remove_selected():
            row = table.currentRow()
            if row < 0:
                QMessageBox.information(dlg, "Guild Members", "Select a member first.")
                return
            name_item = table.item(row, 0)
            role_item = table.item(row, 1)
            member_name = name_item.text() if name_item else ""
            member_role = (role_item.text() if role_item else "member").lower()
            if self.remove_guild_member(member_name, member_role):
                populate()

        populate()
        buttons = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(populate)
        remove = QPushButton("Remove Selected")
        remove.clicked.connect(remove_selected)
        remove.setEnabled(self._current_guild_admin())
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        buttons.addWidget(refresh)
        buttons.addWidget(remove)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dlg.exec()

    def refresh_guild_members(self):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild:
            self.current_guild_members = []
            return []
        try:
            rows = supabase_request("GET", url, key, f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&select=display_name,role&order=display_name.asc")
            if not isinstance(rows, list):
                rows = []
            current_name = db.get_setting("display_name", "")
            if current_name and not any((r.get("display_name", "") or "").strip().lower() == current_name.strip().lower() for r in rows if isinstance(r, dict)):
                rows.append({"display_name": current_name, "role": db.get_setting("guild_role", "member") or "member"})
            self.current_guild_members = rows
            return rows
        except Exception as exc:
            self.current_guild_members = []
            if hasattr(self, "guild_status"):
                self.guild_status.setText(f"Member refresh issue: {exc}")
            return []

    def remove_guild_member(self, member_name: str, member_role: str = "member") -> bool:
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can remove guild members.")
            return False
        member_name = (member_name or "").strip()
        member_role = (member_role or "member").lower()
        if not member_name:
            QMessageBox.information(self, "Guild Members", "Select a member first.")
            return False
        current_user = db.get_setting("display_name", "")
        current_role = (db.get_setting("guild_role", "member") or "member").lower()
        if member_name == current_user:
            QMessageBox.warning(self, "Guild Members", "You cannot remove yourself here. Use Leave Guild.")
            return False
        if member_role == "owner":
            QMessageBox.warning(self, "Guild Members", "The owner cannot be removed.")
            return False
        if current_role == "officer" and member_role == "officer":
            QMessageBox.warning(self, "Guild Members", "Officers cannot remove other officers.")
            return False
        if QMessageBox.question(self, "Remove Member", f"Remove {member_name} from this guild?") != QMessageBox.Yes:
            return False
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        try:
            endpoint = f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(member_name)}"
            supabase_request("DELETE", url, key, endpoint)
            self._promote_next_owner_or_delete_guild(guild, previous_owner_left=(member_role == "owner"))
            self.refresh_guild_members()
            self.refresh_dashboard()
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Remove Member Failed", str(exc))
            return False

    def remove_selected_guild_member(self):
        # Backward-compatible handler for older UI builds. The current UI opens a
        # dialog with its own table instead of showing members directly in Settings.
        if not hasattr(self, "guild_members_table"):
            self.show_members_roles_dialog()
            return
        row = self.guild_members_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Guild Members", "Select a member first.")
            return
        name_item = self.guild_members_table.item(row, 0)
        role_item = self.guild_members_table.item(row, 1)
        self.remove_guild_member(name_item.text() if name_item else "", role_item.text() if role_item else "member")

    def sync_guild_bases(self, show_popup: bool = False):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild or "PASTE_" in key:
            return
        try:
            endpoint = f"guild_bases?guild_code=eq.{urllib.parse.quote(guild)}&select=*"
            remote = supabase_request("GET", url, key, endpoint)
            for item in remote:
                db.upsert_remote_base(
                    str(item.get("id", "")),
                    float(item.get("x", 0)),
                    float(item.get("y", 0)),
                    item.get("base_name") or item.get("name") or "Guild Base",
                    item.get("seitch") or "",
                    guild,
                    item.get("created_by") or "",
                    status=item.get("status") or "friendly",
                )
            local = db.list_unsynced_bases(guild)
            payload = []
            pairs = []
            for row in local:
                rid = row["remote_id"] or str(uuid.uuid4())
                payload.append({
                    "id": rid,
                    "guild_code": guild,
                    "base_name": row["base_name"] or "Guild Base",
                    "seitch": row["seitch"] or "",
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "created_by": row["created_by"] or db.get_setting("display_name", ""),
                    "status": normalize_base_status(row["status"] if "status" in row.keys() else "friendly"),
                })
                pairs.append((int(row["id"]), rid))
            uploaded = 0
            if payload:
                supabase_request("POST", url, key, "guild_bases?on_conflict=id", payload)
                uploaded = len(payload)
                for local_id, rid in pairs:
                    db.set_base_remote_id(local_id, rid)
            self.refresh_bases()
            if hasattr(self, "base_sync_status"):
                self.base_sync_status.setText(f"Base sync active. Pulled {len(remote)}. Uploaded/updated {uploaded}.")
            if show_popup:
                QMessageBox.information(self, "Base Sync", f"Pulled {len(remote)} bases. Uploaded/updated {uploaded}.")
        except Exception as exc:
            if hasattr(self, "base_sync_status"):
                self.base_sync_status.setText(f"Base sync issue: {exc}")
            if show_popup:
                QMessageBox.critical(self, "Base Sync Failed", str(exc))

    def delete_remote_base(self, base):
        url, key = active_supabase()
        remote_id = base["remote_id"] if "remote_id" in base.keys() else ""
        if not url or not key or not remote_id:
            return
        try:
            endpoint = f"guild_bases?id=eq.{urllib.parse.quote(str(remote_id))}"
            supabase_request("DELETE", url, key, endpoint)
        except Exception:
            pass


    def update_guild_button_visibility(self):
        joined = bool(db.get_setting("guild_code", "") and db.get_setting("display_name", ""))
        if hasattr(self, "join_guild_button"):
            self.join_guild_button.setVisible(not joined)
        if hasattr(self, "create_guild_button"):
            self.create_guild_button.setVisible(not joined)
        if hasattr(self, "leave_guild_button"):
            self.leave_guild_button.setVisible(joined)
        if hasattr(self, "guild_status"):
            guild_name = db.get_setting("guild_name", "Guild") or "Guild"
            user = db.get_setting("display_name", "")
            self.guild_status.setText(f"Joined: {guild_name} as {user}" if joined else "Not joined yet.")
        self.update_guild_nav_visibility()
        if joined:
            self.refresh_guild_members()
            self.sync_guild_logo_from_remote()
        elif hasattr(self, "guild_members_table"):
            self.guild_members_table.setRowCount(0)
            self.refresh_guild_logo_widgets()

    def _fetch_guild_members_remote(self, guild: str) -> list[dict]:
        url, key = active_supabase()
        if not url or not key or not guild:
            return []
        try:
            rows = supabase_request(
                "GET",
                url,
                key,
                f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&select=display_name,role,joined_at&order=joined_at.asc",
            )
            return rows if isinstance(rows, list) else []
        except Exception:
            return []


    def _delete_remote_guild_completely(self, guild: str) -> None:
        """Delete a guild and all remote rows tied to it. Safe to call more than once."""
        url, key = active_supabase()
        guild = (guild or "").upper()
        if not url or not key or not guild:
            return
        # Delete children first so this works even if cascade is missing.
        for table in ("guild_news", "guild_links", "guild_activity", "guild_bases", "guild_pois", "guild_members"):
            try:
                supabase_request("DELETE", url, key, f"{table}?guild_code=eq.{urllib.parse.quote(guild)}")
            except Exception:
                pass
        try:
            supabase_request("PATCH", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}", {"logo_data": ""})
        except Exception:
            pass
        try:
            supabase_request("DELETE", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}")
        except Exception:
            pass

    def _promote_next_owner_or_delete_guild(self, guild: str, previous_owner_left: bool = False) -> None:
        url, key = active_supabase()
        if not url or not key or not guild:
            return
        members = self._fetch_guild_members_remote(guild)
        if not members:
            self._delete_remote_guild_completely(guild)
            return
        has_owner = any((m.get("role") or "").lower() == "owner" for m in members)
        if has_owner and not previous_owner_left:
            return
        if has_owner:
            return
        officers = [m for m in members if (m.get("role") or "").lower() == "officer"]
        next_owner = officers[0] if officers else members[0]
        name = next_owner.get("display_name", "")
        if not name:
            return
        try:
            supabase_request(
                "PATCH",
                url,
                key,
                f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(name)}",
                {"role": "owner"},
            )
            supabase_request(
                "PATCH",
                url,
                key,
                f"guilds?guild_code=eq.{urllib.parse.quote(guild)}",
                {"owner_name": name},
            )
        except Exception:
            pass

    def _clear_local_guild_identity(self) -> None:
        db.set_setting("guild_code", "")
        db.set_setting("guild_name", "")
        db.set_setting("guild_role", "member")
        if hasattr(self, "guild_code"):
            self.guild_code.setText("")
        logo_path = guild_logo_cache_path()
        if logo_path.exists():
            try:
                logo_path.unlink()
            except Exception:
                pass
        if hasattr(self, "guild_role_label"):
            self.guild_role_label.setText("Role: member")

    def leave_guild(self):
        guild = db.get_setting("guild_code", "").upper()
        display_name = db.get_setting("display_name", "")
        current_role = (db.get_setting("guild_role", "member") or "member").lower()
        members_before = self._fetch_guild_members_remote(guild) if guild else []
        if len(members_before) <= 1:
            msg = (
                "You are the last member of this guild. Leaving will permanently delete the guild, "
                "its POIs, bases, news, useful links, activity, and logo. Continue?"
            )
        else:
            msg = "Leave this guild on this computer?"
        if QMessageBox.question(self, "Leave Guild", msg) != QMessageBox.Yes:
            return
        url, key = active_supabase()
        if guild and display_name and url and key:
            try:
                supabase_request(
                    "DELETE",
                    url,
                    key,
                    f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(display_name)}",
                )
                # Always re-check after the delete. This prevents orphan guild rows when the
                # current member was the only remaining member, and lets the guild name be reused.
                remaining_members = self._fetch_guild_members_remote(guild)
                if not remaining_members:
                    self._delete_remote_guild_completely(guild)
                else:
                    self._promote_next_owner_or_delete_guild(guild, previous_owner_left=(current_role == "owner"))
            except Exception as exc:
                QMessageBox.warning(self, "Leave Guild", f"Remote leave had an issue, but local guild settings will be cleared.\n\n{exc}")
        if guild:
            db.clear_local_guild_cache(guild)
        self.selected_poi_id_for_map = None
        self.selected_base_id_for_map = None
        self._clear_local_guild_identity()
        self.refresh_pois()
        self.refresh_bases()
        self.update_guild_button_visibility()
        self.refresh_dashboard()

    def save_sync_settings(self):
        if hasattr(self, "display_name"):
            db.set_setting("display_name", self.display_name.text().strip())
        if hasattr(self, "guild_code"):
            db.set_setting("guild_code", self.guild_code.text().strip().upper())
        self.update_guild_button_visibility()

    def test_supabase_connection(self):
        url, key = active_supabase()
        if not url or not key or "PASTE_" in key:
            QMessageBox.information(self, "Connection", "Connection is not configured for this build.")
            return
        try:
            supabase_request("GET", url, key, "guilds?select=id&limit=1")
            QMessageBox.information(self, "Connection", "Connection successful.")
        except Exception as exc:
            QMessageBox.critical(self, "Connection", str(exc))

    def create_guild(self):
        if hasattr(self, "display_name"):
            db.set_setting("display_name", self.display_name.text().strip())
        url, key = active_supabase()
        display_name = db.get_setting("display_name", "")
        if not display_name:
            QMessageBox.information(self, "Guild", "Enter a display name first.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Guild")
        dlg.setMinimumWidth(440)
        dlg_layout = QVBoxLayout(dlg)
        form = QFormLayout()
        guild_name_input = QLineEdit()
        guild_name_input.setPlaceholderText("Example: Griffin Wing")
        guild_code_input = QLineEdit(make_guild_code())
        guild_code_input.setPlaceholderText("Example: GRIFFIN-WING")
        form.addRow("Guild Name", guild_name_input)
        form.addRow("Guild Code", guild_code_input)
        dlg_layout.addLayout(form)
        btns = QHBoxLayout()
        generate = QPushButton("Generate Code")
        generate.clicked.connect(lambda: guild_code_input.setText(make_guild_code()))
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dlg.reject)
        create = QPushButton("Create Guild")
        create.setObjectName("PrimaryButton")
        create.clicked.connect(dlg.accept)
        btns.addWidget(generate)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(create)
        dlg_layout.addLayout(btns)
        if dlg.exec() != QDialog.Accepted:
            return
        guild_name = guild_name_input.text().strip()
        guild_code = ''.join(ch for ch in guild_code_input.text().strip().upper() if ch.isalnum() or ch == '-')
        if not guild_name:
            QMessageBox.information(self, "Create Guild", "Guild name is required.")
            return
        if not guild_code:
            QMessageBox.information(self, "Create Guild", "Guild code is required.")
            return
        if not url or not key:
            QMessageBox.warning(self, "Create Guild Failed", "Connection is not configured for this build.")
            return
        try:
            existing_name = supabase_request(
                "GET",
                url,
                key,
                f"guilds?guild_name=ilike.{urllib.parse.quote(guild_name)}&select=guild_code,guild_name",
            )
            for existing in list(existing_name or []):
                existing_code_value = (existing.get("guild_code") or "").upper()
                if not existing_code_value:
                    continue
                existing_members = self._fetch_guild_members_remote(existing_code_value)
                if existing_members:
                    QMessageBox.warning(self, "Guild Exists", "A guild with that name already exists. Choose another guild name.")
                    return
                # Cleanup empty/orphaned guild rows so the name can be reused.
                self._delete_remote_guild_completely(existing_code_value)
            existing_code = supabase_request("GET", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild_code)}&select=guild_code&limit=1")
            for existing in list(existing_code or []):
                existing_code_value = (existing.get("guild_code") or "").upper()
                existing_members = self._fetch_guild_members_remote(existing_code_value)
                if existing_members:
                    QMessageBox.warning(self, "Guild Code Exists", "A guild with that code already exists. Choose another guild code.")
                    return
                self._delete_remote_guild_completely(existing_code_value)
            supabase_request("POST", url, key, "guilds?on_conflict=guild_code", [{
                "guild_code": guild_code,
                "guild_name": guild_name,
                "owner_name": display_name,
            }])
            supabase_request("POST", url, key, "guild_members?on_conflict=guild_code,display_name", [{
                "guild_code": guild_code,
                "display_name": display_name,
                "role": "owner",
            }])
            old_guild = db.get_setting("guild_code", "").upper()
            if old_guild and old_guild != guild_code.upper():
                db.clear_local_guild_cache(old_guild)
            db.set_setting("guild_code", guild_code)
            db.set_setting("guild_name", guild_name)
            db.set_setting("guild_role", "owner")
            if hasattr(self, "guild_code"):
                self.guild_code.setText(guild_code)
            if hasattr(self, "guild_role_label"):
                self.guild_role_label.setText("Role: owner")
            self.sync_guild_pois(show_popup=False)
            self.update_guild_button_visibility()
            self.refresh_guild_members()
            self.sync_guild_logo_from_remote()
            self.refresh_dashboard()
            QMessageBox.information(self, "Guild Created", f"Guild created. Share this code with members:\n\n{guild_code}")
        except Exception as exc:
            QMessageBox.critical(self, "Create Guild Failed", str(exc))

    def join_guild(self, show_success: bool = True):
        old_guild = db.get_setting("guild_code", "").upper()
        display_name = self.display_name.text().strip() if hasattr(self, "display_name") else db.get_setting("display_name", "")
        guild = self.guild_code.text().strip().upper() if hasattr(self, "guild_code") else db.get_setting("guild_code", "").upper()
        guild = ''.join(ch for ch in guild if ch.isalnum() or ch == '-')
        url, key = active_supabase()
        if not guild or not display_name:
            QMessageBox.information(self, "Guild", "Enter display name and guild code first.")
            return
        try:
            found = supabase_request("GET", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}&select=*")
            if not found:
                QMessageBox.warning(self, "Guild", "Guild code not found. Ask the guild owner to create it first.")
                return
            if old_guild and old_guild != guild:
                db.clear_local_guild_cache(old_guild)
            db.set_setting("display_name", display_name)
            db.set_setting("guild_code", guild)
            db.set_setting("guild_name", found[0].get("guild_name", ""))
            existing_member = supabase_request(
                "GET",
                url,
                key,
                f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(display_name)}&select=role&limit=1",
            )
            role = (existing_member[0].get("role") if existing_member else "member") or "member"
            supabase_request("POST", url, key, "guild_members?on_conflict=guild_code,display_name", [{
                "guild_code": guild,
                "display_name": display_name,
                "role": role,
            }])
            db.set_setting("guild_role", role)
            if hasattr(self, "guild_code"):
                self.guild_code.setText(guild)
            if hasattr(self, "display_name"):
                self.display_name.setText(display_name)
            if hasattr(self, "guild_role_label"):
                self.guild_role_label.setText("Role: " + role)
            self.sync_guild_pois(show_popup=False)
            self.sync_guild_bases(show_popup=False)
            self.sync_guild_dashboard_content(show_errors=False)
            self.update_guild_button_visibility()
            self.refresh_guild_members()
            self.sync_guild_logo_from_remote()
            self.refresh_pois()
            self.refresh_bases()
            self.refresh_guild_page()
            self.refresh_dashboard()
            if show_success:
                QMessageBox.information(self, "Guild", f"Joined guild {guild}.")
        except Exception as exc:
            QMessageBox.critical(self, "Join Guild Failed", str(exc))



def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(DUNE_QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
