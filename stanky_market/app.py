from __future__ import annotations

import sys
import os
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
import zipfile
import tempfile
import shutil
import html
from datetime import datetime, date

try:
    import shiboken6
except Exception:
    shiboken6 = None

from PySide6.QtCore import Qt, QSize, QTimer, QPointF, QRectF, QThread, Signal, QUrl, QLoggingCategory, qInstallMessageHandler, QDateTime
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QBrush, QPen, QFont, QWheelEvent, QAction, QKeySequence, QShortcut, QImage
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
    QToolButton,
    QDateTimeEdit,
    QGraphicsDropShadowEffect,
)

from . import db, deep_desert, guild_config, updater
from .paths import app_root, asset_dir, data_dir, local_app_data_dir
from .ui.theme import premium_qss
from .ui.widgets.cards import CommandCard, StatusPill
from .services.sync_manager import SyncManager


def _qt_alive(obj) -> bool:
    """Return True only when a Python Qt wrapper still owns a live C++ object."""
    if obj is None:
        return False
    if shiboken6 is None:
        return True
    try:
        return bool(shiboken6.isValid(obj))
    except Exception:
        return False

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    WEBENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    QWebEnginePage = None
    QWebEngineProfile = None
    WEBENGINE_AVAILABLE = False

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except Exception:
    QMediaPlayer = None
    QAudioOutput = None
    QVideoWidget = None
    MULTIMEDIA_AVAILABLE = False


def qt_alive(widget) -> bool:
    """Return False if a Python reference points to a Qt object already deleted by Qt."""
    if widget is None:
        return False
    try:
        return bool(shiboken6.isValid(widget)) if shiboken6 is not None else True
    except Exception:
        return False



def _qt_message_filter(mode, context, message):
    """Hide harmless Qt/WebEngine warnings that look like app errors in PowerShell."""
    text = str(message or "")
    noisy_tokens = (
        "QFont::setPointSize",
        "handshake failed",
        "ssl_client_socket_impl",
        "net_error -100",
        "googletag",
        "Audigent",
        "__gpp",
        "Invalid GPT fixed size",
    )
    if any(token.lower() in text.lower() for token in noisy_tokens):
        return
    try:
        sys.stderr.write(text + "\n")
    except Exception:
        pass

try:
    qInstallMessageHandler(_qt_message_filter)
except Exception:
    pass

APP_TITLE = "StankyTools"

PROJECT_ROOT = app_root()
ASSETS_DIR = asset_dir()

def asset_path(*parts: str) -> Path:
    """Return a bundled asset path, preferring compressed WebP when available.

    Most UI art is shipped as .webp to keep releases smaller. Existing call
    sites may still request .png names; this resolver keeps them working by
    transparently returning the matching .webp file when the exact file is not
    present.
    """
    path = ASSETS_DIR.joinpath(*parts)
    if path.exists():
        return path
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        webp = path.with_suffix(".webp")
        if webp.exists():
            return webp
    return path

def qss_path(path: Path) -> str:
    return path.resolve().as_posix()


def trim_transparent_pixmap(pixmap: QPixmap) -> QPixmap:
    """Crop transparent padding from a pixmap so logos fill their UI slot cleanly."""
    if pixmap.isNull():
        return pixmap
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width = image.width()
    height = image.height()
    if width <= 0 or height <= 0 or not image.hasAlphaChannel():
        return pixmap

    min_x, min_y = width, height
    max_x, max_y = -1, -1
    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() > 8:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y

    if max_x < min_x or max_y < min_y:
        return pixmap
    if min_x == 0 and min_y == 0 and max_x == width - 1 and max_y == height - 1:
        return pixmap

    return QPixmap.fromImage(image.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))


def local_cache_dir(*parts: str) -> Path:
    """Return the user-writable StankyTools cache directory."""
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "StankyTools"
    target = base.joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return target


def ensure_easter_egg_video(parent: QWidget | None = None) -> Path | None:
    """Get the Easter egg video from local cache, bundled fallback, or GitHub Releases."""
    target = local_cache_dir("videos") / "pgmayo.mp4"
    if target.exists() and target.stat().st_size > 0:
        return target

    bundled = asset_path("videos", "pgmayo.mp4")

    progress = None
    try:
        progress = QProgressDialog("Downloading classified transmission from GitHub...", "Cancel", 0, 100, parent)
        progress.setWindowTitle("StankyTools Assets")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        req = urllib.request.Request(
            DEFAULT_EASTER_EGG_VIDEO_URL,
            headers={"User-Agent": f"StankyTools/{updater.APP_VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            with target.open("wb") as f:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total and progress:
                        progress.setValue(min(99, int(done * 100 / total)))
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            raise RuntimeError("Download canceled")
        if progress:
            progress.setValue(100)
        return target if target.exists() and target.stat().st_size > 0 else None
    except Exception as exc:
        try:
            if target.exists() and target.stat().st_size == 0:
                target.unlink(missing_ok=True)
        except Exception:
            pass
        # Developer/source fallback so the Easter egg still works before the GitHub
        # release asset has been uploaded. Release builds should use the cached
        # GitHub copy after the first successful download.
        if bundled.exists() and bundled.stat().st_size > 0:
            try:
                target.write_bytes(bundled.read_bytes())
                return target
            except Exception:
                return bundled
        if parent is not None:
            QMessageBox.warning(
                parent,
                "Classified Transmission",
                "The video asset could not be downloaded from GitHub.\n\n"
                "Upload pgmayo.mp4 to your latest GitHub Release as a release asset named pgmayo.mp4.",
            )
        return None


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


def format_event_central_time(value: str) -> str:
    """Display guild event dates with the saved event time and Central-time label."""
    raw = str(value or "").strip()
    if not raw:
        return "—"
    clean = raw.replace("UTC", "").replace("Central", "").replace("CT", "").strip()
    if "T" in clean:
        clean = clean.replace("T", " ").split("+", 1)[0].split("Z", 1)[0].strip()
    parts = clean.split()
    date_part = parts[0] if parts else clean[:10]
    time_text = ""
    try:
        year, month, day = date_part.split("-")[:3]
        date_text = f"{int(month)}-{int(day)}-{int(year)}"
    except Exception:
        date_text = format_app_date(raw)
    if len(parts) >= 3 and parts[2].upper() in {"AM", "PM"}:
        time_text = f"{parts[1]} {parts[2].upper()}"
    elif len(parts) >= 2 and ":" in parts[1]:
        time_part = parts[1].split(".", 1)[0]
        hhmm = time_part[:5]
        try:
            hour, minute = [int(x) for x in hhmm.split(":")[:2]]
            suffix = "AM" if hour < 12 else "PM"
            hour12 = hour % 12 or 12
            time_text = f"{hour12}:{minute:02d} {suffix}"
        except Exception:
            time_text = hhmm
    return f"{date_text} {time_text} CT" if time_text else f"{date_text} CT"




def parse_event_central_datetime(value: str):
    raw = str(value or "").strip()
    if not raw:
        return None
    clean = raw.replace("UTC", "").replace("Central", "").replace("CT", "").replace("T", " ").strip()
    clean = clean.split("+", 1)[0].split("Z", 1)[0].strip()
    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m-%d-%Y %I:%M %p", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(clean[:len(datetime.now().strftime(fmt))] if fmt != "%Y-%m-%d" else clean[:10], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def event_timing_badge(value: str) -> str:
    dt = parse_event_central_datetime(value)
    if not dt:
        return "🔵 Upcoming"
    today = date.today()
    if dt.date() == today:
        return "🟢 Today"
    if dt.date() < today:
        return "⚫ Ended"
    return "🔵 Upcoming"


def event_sort_tuple(row) -> tuple:
    raw = row["event_at"] or row["created_at"] or ""
    dt = parse_event_central_datetime(raw) or datetime.max
    today = date.today()
    if dt.date() == today:
        group = 0
    elif dt.date() > today:
        group = 1
    else:
        group = 2
    return (group, dt)

def resolve_local_path(value: str) -> Path:
    """Resolve saved paths, including per-user imported item images under AppData."""
    raw = (value or "").strip().replace("\\", "/")
    if not raw:
        return Path()
    p = Path(raw)
    if p.is_absolute():
        return p
    if raw.startswith("item_images/") or raw.startswith("data/"):
        appdata_candidate = local_app_data_dir() / raw
        if appdata_candidate.exists() or raw.startswith("item_images/"):
            return appdata_candidate
    return PROJECT_ROOT / raw


CATALOG_PIXMAP_CACHE: dict[tuple[str, int], QPixmap] = {}
METHOD_DEEP_DESERT_URL = "https://www.method.gg/dune-awakening/deep-desert-companion"
GAMING_TOOLS_DEEP_DESERT_URL = "https://dune.gaming.tools/deep-desert"
DEFAULT_CATALOG_IMAGES_ZIP_URL = "https://github.com/tonyaprile-droid/Stankytools/releases/latest/download/catalog_images.zip"
DEFAULT_EASTER_EGG_VIDEO_URL = "https://github.com/tonyaprile-droid/Stankytools/releases/latest/download/pgmayo.mp4"

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
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #080706, stop:1 #0f0d0a);
    border-right: 1px solid rgba(214,174,90,0.35);
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
QToolButton#NavButton {{
    padding: 14px 18px;
    border: 1px solid rgba(214,174,90,0.22);
    border-radius: 7px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(18,16,13,0.98), stop:1 rgba(8,8,7,0.98));
    color: #F5F3ED;
    font-size: 17px;
    font-weight: 900;
    letter-spacing: 1.2px;
    text-align: left;
}}
QToolButton#NavButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(75,52,20,0.72), stop:1 rgba(18,14,9,0.96));
    border: 1px solid rgba(214,174,90,0.70);
    color: #fff3c8;
}}
QToolButton#NavButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(147,103,29,0.88), stop:1 rgba(54,37,14,0.96));
    border: 1px solid #D6AE5A;
    color: #fff2c9;
}}
QToolButton#NavButton::menu-indicator {{ image: none; }}

QToolButton#ImageNavButton {{
    padding: 0px;
    margin: 0px;
    border: none;
    background: transparent;
}}
QToolButton#ImageNavButton:hover {{
    background: rgba(214,174,90,0.08);
    border: 1px solid rgba(214,174,90,0.45);
    border-radius: 8px;
}}
QToolButton#ImageNavButton[active="true"] {{
    background: rgba(214,174,90,0.13);
    border: 1px solid rgba(214,174,90,0.65);
    border-radius: 8px;
}}
QToolButton#ImageNavButton::menu-indicator {{ image: none; }}
QFrame#SideHeader {{
    background: transparent;
    border: none;
    border-radius: 0px;
}}
QFrame#SideFooter {{
    background: rgba(12,10,7,0.74);
    border: 1px solid rgba(214,174,90,0.30);
    border-radius: 18px;
}}
QLabel#GuildStatusPill {{
    color: #fff2c9;
    background: #3321140a;
    border: 1px solid #7AD4AE63;
    border-radius: 12px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 950;
    letter-spacing: 2px;
}}
QLabel#DashboardGuildLogo {{
    color: #d6ae5a;
    background: #99100b07;
    border: 1px solid #55D4AE63;
    border-radius: 18px;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 2px;
}}

QFrame#Hero {{
    background-color: #1b1209;
    border: 1px solid #8CF4CD7A;
    border-radius: 22px;
}}
QLabel#HeroTitle {{
    font-size: 64px;
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
    background: #F12A1F12;
    border: 1px solid #8AD4AE63;
    border-radius: 12px;
    padding: 11px 18px;
    color: #fff0bf;
    font-size: 15px;
    font-weight: 800;
    min-height: 22px;
}}
QPushButton:hover {{
    background: #FF372817;
    border: 1px solid #f0c76c;
    color: #fff8df;
}}
QPushButton:pressed {{
    background: #D4AE6330;
    border: 1px solid #ffe0a1;
}}
QPushButton:disabled {{
    background: #55110D08;
    border: 1px solid #33D4AE63;
    color: #8f7a54;
}}
QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffe19a, stop:1 #c17b31);
    color: #120b05;
    font-size: 15px;
    font-weight: 950;
    border: 1px solid #fff0bf;
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
        self.setWordWrap(False)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setDefaultSectionSize(44)
        self.horizontalHeader().setMinimumHeight(42)
        self.setFocusPolicy(Qt.NoFocus)

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


class PremiumStatCard(QFrame):
    def __init__(self, title: str, value: str = "—", hint: str = "", tone: str = "gold"):
        super().__init__()
        self.setObjectName("PremiumStatCard")
        apply_soft_shadow(self, blur=28, y=8, alpha=70)
        self.setMinimumHeight(132)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("CardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("CardHint")
        self.hint_label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)

    def set_value(self, value: str, hint: str | None = None):
        if not _qt_alive(self) or not _qt_alive(getattr(self, "value_label", None)):
            return
        self.value_label.setText(value)
        if hint is not None and _qt_alive(getattr(self, "hint_label", None)):
            self.hint_label.setText(hint)


class QuickActionCard(QFrame):
    clicked = Signal()

    def __init__(self, icon: str, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("QuickActionCard")
        apply_soft_shadow(self, blur=24, y=7, alpha=62)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(108)
        icon_label = QLabel(icon)
        icon_label.setObjectName("ActionIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        title_label = QLabel(title.upper())
        title_label.setObjectName("ActionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("CardHint")
        subtitle_label.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)
        layout.addWidget(icon_label)
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(title_label)
        text.addWidget(subtitle_label)
        text.addStretch()
        layout.addLayout(text, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NewsCard(QFrame):
    doubleClicked = Signal()

    def __init__(self, title: str, body: str = "", poster: str = "", date: str = "", *, emphasize_date: bool = False, truncate_body: bool = False):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("NewsCard")
        apply_soft_shadow(self, blur=22, y=6, alpha=58)
        self.setMinimumHeight(88)
        self._raw_body = body or "No details posted yet."
        self._truncate_body = bool(truncate_body)
        self._expanded = False
        self._truncate_at = 145
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(5)
        top = QHBoxLayout()
        title_label = QLabel((title or "Guild Update").upper())
        title_label.setObjectName("NewsTitle")
        title_label.setWordWrap(True)
        date_label = QLabel(date or "")
        date_label.setObjectName("MicroLabel")
        if emphasize_date:
            date_label.setStyleSheet("color:#F5F3ED; font-size:21px; font-weight:950; letter-spacing:1px;")
        top.addWidget(title_label, 1)
        top.addWidget(date_label)
        self.body_label = QLabel()
        self.body_label.setObjectName("NewsBody")
        self.body_label.setWordWrap(True)
        layout.addLayout(top)
        layout.addWidget(self.body_label)
        self.read_more = QLabel("")
        self.read_more.setObjectName("MicroLabel")
        self.read_more.setCursor(Qt.PointingHandCursor)
        self.read_more.setStyleSheet("color:#D6AE5A; font-weight:900; letter-spacing:1px;")
        self.read_more.mousePressEvent = lambda event: self.toggle_body()
        layout.addWidget(self.read_more)
        if poster:
            by_label = QLabel(f"POSTED BY {poster}")
            by_label.setObjectName("MicroLabel")
            layout.addWidget(by_label)
        self._render_body()

    def _render_body(self):
        if not _qt_alive(getattr(self, "body_label", None)):
            return
        needs_truncate = self._truncate_body and len(self._raw_body) > self._truncate_at
        if needs_truncate and not self._expanded:
            self.body_label.setText(self._raw_body[: self._truncate_at].rstrip() + "...")
            if _qt_alive(getattr(self, "read_more", None)):
                self.read_more.setText("READ MORE")
                self.read_more.show()
        else:
            self.body_label.setText(self._raw_body)
            if _qt_alive(getattr(self, "read_more", None)):
                if needs_truncate:
                    self.read_more.setText("SHOW LESS")
                    self.read_more.show()
                else:
                    self.read_more.hide()

    def toggle_body(self):
        # Read More opens the quiet premium detail dialog through the card callback.
        # It no longer expands inline or uses QMessageBox, avoiding Windows alert sounds.
        self.doubleClicked.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            self.doubleClicked.emit()
            return
        super().mouseDoubleClickEvent(event)


class DetailDialog(QDialog):
    def __init__(self, title: str, body: str, parent=None, meta: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title or "Details")
        self.setMinimumSize(820, 460)
        self.resize(900, 540)
        self.setObjectName("DetailDialog")
        self.setStyleSheet("""
            QDialog#DetailDialog {
                background: #090909;
                border: 1px solid #8D6A2B;
                border-radius: 16px;
            }
            QLabel#DialogHeader {
                color: #D6AE5A;
                font-size: 19px;
                font-weight: 950;
                letter-spacing: 2px;
            }
            QLabel#DialogTitle {
                color: #F5F3ED;
                font-size: 34px;
                font-weight: 950;
                letter-spacing: 0.6px;
            }
            QLabel#DialogBody {
                color: #F5F3ED;
                font-size: 31px;
                line-height: 1.8;
            }
            QLabel#DateMonth {
                color: #D6AE5A;
                font-size: 34px;
                font-weight: 950;
                letter-spacing: 3px;
            }
            QLabel#DateDay {
                color: #D6AE5A;
                font-size: 126px;
                font-weight: 950;
                letter-spacing: 1px;
            }
            QLabel#DateYear {
                color: #D6AE5A;
                font-size: 28px;
                font-weight: 950;
                letter-spacing: 4px;
            }
            QLabel#DateRaw {
                color: #D6AE5A;
                font-size: 64px;
                font-weight: 950;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 22)
        root.setSpacing(12)

        header = QHBoxLayout()
        header_icon = QLabel("▰")
        header_icon.setObjectName("DialogHeader")
        header_text = QLabel("DETAILS")
        header_text.setObjectName("DialogHeader")
        close_x = QPushButton("×")
        close_x.setObjectName("GhostButton")
        close_x.setFixedSize(44, 38)
        close_x.clicked.connect(self.accept)
        header.addWidget(header_icon)
        header.addWidget(header_text)
        header.addStretch()
        header.addWidget(close_x)
        root.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: rgba(214,174,90,0.35); background: rgba(214,174,90,0.35); max-height: 1px;")
        root.addWidget(line)

        content_row = QHBoxLayout()
        content_row.setSpacing(22)

        date_box = QFrame()
        date_box.setObjectName("CommandCard")
        date_box.setFixedWidth(190)
        date_layout = QVBoxLayout(date_box)
        date_layout.setContentsMargins(16, 20, 16, 20)
        date_layout.setSpacing(0)
        clean_meta = str(meta or "").replace("When:", "").replace("Posted:", "").strip()
        month_txt = day_txt = year_txt = ""
        if clean_meta and clean_meta != "—":
            try:
                parts = clean_meta.replace("/", "-").split("-", 2)
                month_num, day_num, year_txt = int(parts[0]), int(parts[1]), parts[2][:4]
                months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
                month_txt = months[max(1, min(12, month_num)) - 1]
                day_txt = f"{day_num:02d}"
            except Exception:
                pass
        if month_txt and day_txt and year_txt:
            m = QLabel(month_txt); m.setObjectName("DateMonth"); m.setAlignment(Qt.AlignCenter)
            d = QLabel(day_txt); d.setObjectName("DateDay"); d.setAlignment(Qt.AlignCenter)
            y = QLabel(year_txt); y.setObjectName("DateYear"); y.setAlignment(Qt.AlignCenter)
            date_layout.addStretch(); date_layout.addWidget(m); date_layout.addWidget(d); date_layout.addWidget(y); date_layout.addStretch()
        elif clean_meta:
            raw = QLabel(clean_meta); raw.setObjectName("DateRaw"); raw.setWordWrap(True); raw.setAlignment(Qt.AlignCenter)
            date_layout.addStretch(); date_layout.addWidget(raw); date_layout.addStretch()
        else:
            raw = QLabel("—"); raw.setObjectName("DateRaw"); raw.setAlignment(Qt.AlignCenter)
            date_layout.addStretch(); date_layout.addWidget(raw); date_layout.addStretch()
        content_row.addWidget(date_box)

        detail_box = QFrame()
        detail_box.setStyleSheet("background: transparent;")
        detail_layout = QVBoxLayout(detail_box)
        detail_layout.setContentsMargins(0, 6, 0, 0)
        detail_layout.setSpacing(14)
        title_label = QLabel(title or "Details")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)
        detail_layout.addWidget(title_label)
        text = QLabel(body or "No details were provided.")
        text.setObjectName("DialogBody")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QFrame()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 12, 0)
        scroll_layout.addWidget(text)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        detail_layout.addWidget(scroll, 1)
        content_row.addWidget(detail_box, 1)
        root.addLayout(content_row, 1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("PrimaryButton")
        close_btn.setMinimumWidth(160)
        close_btn.clicked.connect(self.accept)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(close_btn)
        root.addLayout(bottom)


class LinkCard(QFrame):
    clicked = Signal(str)
    doubleClicked = Signal(str)

    def __init__(self, title: str, url: str = "", poster: str = "—"):
        super().__init__()
        self.url = str(url or "")
        self.setObjectName("NewsCard")
        apply_soft_shadow(self, blur=22, y=6, alpha=58)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(82)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(5)
        title_label = QLabel((title or "Useful Link").upper())
        title_label.setObjectName("NewsTitle")
        title_label.setWordWrap(True)
        url_label = QLabel(self.url or "No URL")
        url_label.setObjectName("NewsBody")
        url_label.setWordWrap(True)
        by_label = QLabel(f"ADDED BY {poster or '—'}")
        by_label.setObjectName("MicroLabel")
        layout.addWidget(title_label)
        layout.addWidget(url_label)
        layout.addWidget(by_label)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            self.doubleClicked.emit(self.url)
            return
        super().mouseDoubleClickEvent(event)


class MarketMoverCard(QFrame):
    def __init__(self, name: str, value: str, trend: str, tone: str = "gold"):
        super().__init__()
        self.setObjectName("MarketMoverCard")
        apply_soft_shadow(self, blur=22, y=6, alpha=58)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        arrow = QLabel(trend)
        arrow.setObjectName("ActionIcon")
        name_label = QLabel(name)
        name_label.setObjectName("NewsTitle")
        value_label = QLabel(value)
        value_label.setObjectName("CardHint")
        text = QVBoxLayout()
        text.addWidget(name_label)
        text.addWidget(value_label)
        layout.addWidget(arrow)
        layout.addLayout(text, 1)



class PriceHistoryGraph(QWidget):
    """Small lightweight price-history graph for the auction terminal."""

    def __init__(self):
        super().__init__()
        self.points: list[int] = []
        self.setMinimumHeight(150)
        self.setObjectName("PriceHistoryGraph")

    def set_points(self, points: list[int]):
        self.points = [int(p or 0) for p in points if p is not None]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(16, 14, -16, -16)
        painter.setPen(QPen(QColor("#2b2117"), 1))
        painter.setBrush(QBrush(QColor("#100d09")))
        painter.drawRoundedRect(rect, 14, 14)
        for i in range(1, 4):
            y = rect.top() + int(rect.height() * i / 4)
            painter.setPen(QPen(QColor(214, 174, 90, 38), 1))
            painter.drawLine(rect.left()+10, y, rect.right()-10, y)
        if len(self.points) < 2:
            painter.setPen(QPen(QColor("#8d6a2b"), 1))
            painter.drawText(rect, Qt.AlignCenter, "Not enough price history yet")
            return
        values = list(reversed(self.points[-24:]))
        lo, hi = min(values), max(values)
        span = max(1, hi - lo)
        step = rect.width() / max(1, len(values) - 1)
        path_points = []
        for idx, value in enumerate(values):
            x = rect.left() + idx * step
            y = rect.bottom() - ((value - lo) / span) * (rect.height() - 22) - 11
            path_points.append(QPointF(x, y))
        painter.setPen(QPen(QColor("#d6ae5a"), 3))
        for a, b in zip(path_points, path_points[1:]):
            painter.drawLine(a, b)
        painter.setBrush(QBrush(QColor("#f5f3ed")))
        painter.setPen(Qt.NoPen)
        for pt in path_points[-4:]:
            painter.drawEllipse(pt, 4, 4)
        painter.setPen(QPen(QColor("#bda56d"), 1))
        painter.drawText(rect.adjusted(12, 8, -12, -8), Qt.AlignTop | Qt.AlignLeft, f"High {fmt_price(hi)}")
        painter.drawText(rect.adjusted(12, 8, -12, -8), Qt.AlignBottom | Qt.AlignLeft, f"Low {fmt_price(lo)}")

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
            self.finished_ok.emit({"items": result.get("items", 0), "images": result.get("images", 0), "source": "Game8", "errors": result.get("errors", 0)})
        except Exception as exc:
            self.failed.emit(str(exc))


class CatalogImagesGitHubWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, url: str = DEFAULT_CATALOG_IMAGES_ZIP_URL, parent=None):
        super().__init__(parent)
        self.url = url.strip() or DEFAULT_CATALOG_IMAGES_ZIP_URL

    def run(self):
        try:
            target_dir = local_app_data_dir() / "item_images"
            target_dir.mkdir(parents=True, exist_ok=True)
            self.progress.emit("Downloading catalog_images.zip from GitHub...")
            req = urllib.request.Request(self.url, headers={"User-Agent": f"StankyTools/{updater.APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read()
            if len(payload) < 1024:
                raise RuntimeError("Downloaded file was too small to be a catalog image ZIP.")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(payload)
                tmp_path = Path(tmp.name)
            imported = 0
            self.progress.emit("Extracting catalog images...")
            try:
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        name = Path(info.filename).name
                        if not name:
                            continue
                        if Path(name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                            continue
                        # Flatten to AppData item_images to match existing database image_path values.
                        out = target_dir / name
                        with zf.open(info) as src, out.open("wb") as dst:
                            dst.write(src.read())
                        imported += 1
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
            self.finished_ok.emit({"images": imported, "folder": str(target_dir), "source": self.url})
        except Exception as exc:
            self.failed.emit(str(exc))




class QuietWebEnginePage(QWebEnginePage if QWebEnginePage is not None else object):
    """Suppress noisy third-party ad console warnings from embedded Method.gg.

    The map still loads normally; this only hides JavaScript console chatter like
    Google Publisher Tag deprecation warnings that make the terminal look broken.
    """
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802
        text = str(message or "")
        noisy_tokens = (
            "googletag",
            "GPT",
            "Audigent",
            "__gpp",
            "Invalid GPT fixed size",
            "encryptedSignalProviders",
            "PubAdsService.setTargeting",
            "Slot.getTargeting",
            "handshake failed",
            "ssl_client_socket_impl",
            "net_error -100",
        )
        if any(token.lower() in text.lower() for token in noisy_tokens):
            return
        try:
            super().javaScriptConsoleMessage(level, message, line_number, source_id)
        except Exception:
            return




class NativeDeepDesertCanvas(QWidget):
    """Simple Deep Desert guild POI map canvas with native zoom, pan, and placement."""
    coordinateChanged = Signal(str)
    poiActionRequested = Signal(float, float, str)
    markerSelected = Signal(str, int)

    # POI placement is normalized against the 881x883 Deep Desert grid background.
    # Hidden filters/items removed on request: House Rep, PvP, Taxi, Intel, Loot,
    # Spice Medium, and Spice Small.
    POIS = []  # Source-map POIs removed until exact official coordinates are available. Guild POIs are placed by users.
    COLORS = {
        "shipwrecks": QColor("#9c5ac6"),
        "caves": QColor("#1591cf"),
        "large_spice_field": QColor("#ff8a22"),
        "testing_stations": QColor("#31588f"),
        "titanium": QColor("#cbb36a"),
        "stravidium": QColor("#76b747"),
    }
    ICON_FILES = {
        "shipwrecks": "shipwreck.png",
        "caves": "cave.png",
        "large_spice_field": "large-spice-field.png",
        "testing_stations": "testing-station.png",
        "titanium": "titanium.png",
        "stravidium": "stravidium.png",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.background = QPixmap(str(data_dir() / "deep_desert_map.png"))
        icon_root = data_dir() / "deep_desert" / "icons"
        self.icon_pixmaps = {key: QPixmap(str(icon_root / filename)) for key, filename in self.ICON_FILES.items()}
        self.enabled_filters: dict[str, bool] = {}
        self.custom_pois = []
        self.custom_bases = []
        self.selected_custom_poi_id = None
        self.selected_custom_base_id = None
        self.hover_text = ""
        self.hover_coord = ""
        self.zoom_factor = float(db.get_setting("deep_desert_zoom", "1.0") or "1.0")
        self.pan = QPointF(0, 0)
        self._dragging = False
        self._last_drag = QPointF(0, 0)
        self.setMouseTracking(True)
        self.setMinimumHeight(620)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setStyleSheet("background:#090806; border:1px solid #4a3518; border-radius:16px;")

    def reload_background(self):
        """Reload the cached weekly Deep Desert screenshot without recreating the canvas."""
        self.background = QPixmap(str(data_dir() / "deep_desert_map.png"))
        self.update()

    def set_filters(self, filters: dict[str, bool]):
        self.enabled_filters = dict(filters)
        self.update()

    def zoom_in(self):
        self.set_zoom(self.zoom_factor * 1.18)

    def zoom_out(self):
        self.set_zoom(self.zoom_factor / 1.18)

    def reset_view(self):
        self.zoom_factor = 1.0
        self.pan = QPointF(0, 0)
        db.set_setting("deep_desert_zoom", "1.0")
        self.update()

    def set_zoom(self, value: float):
        self.zoom_factor = max(1.0, min(3.75, float(value)))
        db.set_setting("deep_desert_zoom", f"{self.zoom_factor:.2f}")
        self._clamp_pan()
        self.update()

    def jump_to(self, x: float, y: float):
        base = self._base_map_rect()
        scaled = QRectF(
            base.center().x() - base.width() * self.zoom_factor / 2,
            base.center().y() - base.height() * self.zoom_factor / 2,
            base.width() * self.zoom_factor,
            base.height() * self.zoom_factor,
        )
        target_x = scaled.x() + (x / 881.0) * scaled.width()
        target_y = scaled.y() + (y / 883.0) * scaled.height()
        self.pan = QPointF(self.width() / 2 - target_x, self.height() / 2 - target_y)
        self._clamp_pan()
        self.update()

    def _base_map_rect(self) -> QRectF:
        pad = 8
        available = QRectF(pad, pad, self.width() - pad * 2, self.height() - pad * 2)
        if self.background.isNull():
            return available
        src_ratio = self.background.width() / max(1, self.background.height())
        dst_ratio = available.width() / max(1, available.height())
        if dst_ratio > src_ratio:
            h = available.height()
            w = h * src_ratio
        else:
            w = available.width()
            h = w / src_ratio
        return QRectF(available.x() + (available.width() - w) / 2, available.y() + (available.height() - h) / 2, w, h)

    def _map_rect(self) -> QRectF:
        base = self._base_map_rect()
        w = base.width() * self.zoom_factor
        h = base.height() * self.zoom_factor
        return QRectF(base.center().x() - w / 2 + self.pan.x(), base.center().y() - h / 2 + self.pan.y(), w, h)

    def _clamp_pan(self):
        if self.zoom_factor <= 1.01:
            self.pan = QPointF(0, 0)
            return
        base = self._base_map_rect()
        max_x = max(0, (base.width() * self.zoom_factor - base.width()) / 2)
        max_y = max(0, (base.height() * self.zoom_factor - base.height()) / 2)
        self.pan = QPointF(max(-max_x, min(max_x, self.pan.x())), max(-max_y, min(max_y, self.pan.y())))

    def _screen_point(self, x: float, y: float):
        r = self._map_rect()
        return r.x() + (x / 881.0) * r.width(), r.y() + (y / 883.0) * r.height()

    def _map_coord_from_screen(self, px: float, py: float):
        r = self._map_rect()
        if r.width() <= 0 or r.height() <= 0:
            return None
        x = ((px - r.x()) / r.width()) * 881.0
        y = ((py - r.y()) / r.height()) * 883.0
        if 0 <= x <= 881 and 0 <= y <= 883:
            return x, y
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#070604"))
        r = self._map_rect()
        if not self.background.isNull():
            painter.drawPixmap(r, self.background, QRectF(0, 0, self.background.width(), self.background.height()))
        else:
            painter.setPen(QPen(QColor("#87633a"), 2))
            painter.drawText(r, Qt.AlignCenter, "Deep Desert background missing")

        self._draw_map_frame(painter, r)

        visible_count = 0
        for category, x, y, label in self.POIS:
            if not self.enabled_filters.get(category, True):
                continue
            sx, sy = self._screen_point(x, y)
            if -60 <= sx <= self.width() + 60 and -60 <= sy <= self.height() + 60:
                self._draw_marker(painter, sx, sy, category, label)
                visible_count += 1

        for base in self.custom_bases:
            try:
                x, y = float(base["x"]), float(base["y"])
                base_id = int(base["id"]) if "id" in base.keys() else None
                name = base["base_name"] if "base_name" in base.keys() else "Base"
                status = base["status"] if "status" in base.keys() else "friendly"
                note = base["seitch"] if "seitch" in base.keys() else ""
            except Exception:
                continue
            sx, sy = self._screen_point(x, y)
            if -80 <= sx <= self.width() + 80 and -80 <= sy <= self.height() + 80:
                self._draw_base_marker(painter, sx, sy, str(name), str(status), str(note), base_id == self.selected_custom_base_id)
                visible_count += 1

        for poi in self.custom_pois:
            try:
                x, y = float(poi["x"]), float(poi["y"])
                label = poi["poi_type"] if "poi_type" in poi.keys() else "Guild POI"
                note = poi["note"] if "note" in poi.keys() else ""
                poi_id = int(poi["id"]) if "id" in poi.keys() else None
                pooped = bool(poi["pooped_on"]) if "pooped_on" in poi.keys() else False
                tactical_status = poi_tactical_status(str(label), pooped, str(poi["status"]) if "status" in poi.keys() else "")
            except Exception:
                continue
            sx, sy = self._screen_point(x, y)
            if -80 <= sx <= self.width() + 80 and -80 <= sy <= self.height() + 80:
                self._draw_custom_marker(painter, sx, sy, str(label), str(note), tactical_status, poi_id == self.selected_custom_poi_id)
                visible_count += 1

        if self.hover_text:
            self._draw_hover_box(painter)

    def _draw_coordinate_grid(self, painter: QPainter, r: QRectF):
        painter.save()
        painter.setClipRect(r)
        painter.setPen(QPen(QColor(214, 174, 90, 42), 1))
        steps = 8
        for i in range(1, steps):
            x = r.x() + r.width() * i / steps
            y = r.y() + r.height() * i / steps
            painter.drawLine(QPointF(x, r.y()), QPointF(x, r.bottom()))
            painter.drawLine(QPointF(r.x(), y), QPointF(r.right(), y))
        painter.setPen(QPen(QColor(245, 243, 237, 88), 1))
        font = painter.font(); font.setPointSize(8); font.setBold(True); painter.setFont(font)
        for i in range(steps):
            painter.drawText(QRectF(r.x() + r.width() * i / steps + 6, r.y() + 6, 44, 20), Qt.AlignLeft, chr(65 + i))
            painter.drawText(QRectF(r.x() + 6, r.y() + r.height() * i / steps + 6, 44, 20), Qt.AlignLeft, str(i + 1))
        painter.restore()

    def _draw_map_frame(self, painter: QPainter, r: QRectF):
        painter.save()
        painter.setPen(QPen(QColor(0, 0, 0, 155), 5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(r, 16, 16)
        painter.setPen(QPen(QColor(214, 174, 90, 112), 1.5))
        painter.drawRoundedRect(r.adjusted(2, 2, -2, -2), 14, 14)
        painter.restore()

    def _draw_marker(self, painter: QPainter, sx: float, sy: float, category: str, label: str):
        pix = self.icon_pixmaps.get(category)
        size = 42 if category in {"shipwrecks", "titanium", "stravidium"} else 38
        if self.zoom_factor > 2.1:
            size += 4
        rect = QRectF(sx - size / 2, sy - size / 2, size, size)
        painter.save()
        color = self.COLORS.get(category, QColor("#f7d27a"))
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 72), 8))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect.adjusted(-2, -2, 2, 2))
        if pix is not None and not pix.isNull():
            painter.drawPixmap(rect, pix, QRectF(0, 0, pix.width(), pix.height()))
        else:
            painter.setPen(QPen(QColor(0, 0, 0, 190), 5))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(rect)
            painter.setPen(QPen(QColor("#fff2c2"), 1.2))
            painter.drawEllipse(rect)
        painter.restore()

    def _draw_custom_marker(self, painter: QPainter, sx: float, sy: float, label: str, note: str = "", status: str = "active", selected: bool = False):
        painter.save()
        color = poi_status_color(status)
        size = 31 if not selected else 46
        rect = QRectF(sx - size / 2, sy - size / 2, size, size)
        if selected:
            # Make selected POIs impossible to miss: large soft pulse + crisp gold ring.
            painter.setPen(QPen(QColor(247, 210, 122, 185), 10))
            painter.setBrush(QColor(247, 210, 122, 42))
            painter.drawEllipse(rect.adjusted(-18, -18, 18, 18))
            painter.setPen(QPen(QColor(255, 239, 166, 210), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect.adjusted(-8, -8, 8, 8))
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 118), 9))
        painter.setBrush(QColor(9, 9, 9, 218))
        painter.drawEllipse(rect.adjusted(-2, -2, 2, 2))
        painter.setPen(QPen(color, 3))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(rect)
        painter.setPen(QColor("#090909"))
        font = painter.font(); font.setPointSize(13 if selected else 12); font.setBold(True); painter.setFont(font)
        marker_text = "✕" if (status or "").lower() == "enemy" else ("✓" if (status or "").lower() == "friendly" else "◆")
        painter.drawText(rect, Qt.AlignCenter, marker_text)
        if self.zoom_factor >= 1.20 or selected:
            text = f"{label[:24]} • {poi_status_label(status)}"
            label_rect = QRectF(sx + size / 2 + 8, sy - 15, max(150, len(text) * 7 + 24), 31)
            painter.setPen(QPen(QColor(214, 174, 90, 108), 1))
            painter.setBrush(QColor(9, 9, 9, 224))
            painter.drawRoundedRect(label_rect, 9, 9)
            painter.setPen(QColor("#f5f3ed"))
            painter.drawText(label_rect.adjusted(10, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def _draw_base_marker(self, painter: QPainter, sx: float, sy: float, label: str, status: str = "friendly", note: str = "", selected: bool = False):
        painter.save()
        color = base_status_color(status)
        size = 32 if not selected else 44
        rect = QRectF(sx - size / 2, sy - size / 2, size, size)
        if selected:
            painter.setPen(QPen(QColor(247, 210, 122, 185), 11))
            painter.setBrush(QColor(247, 210, 122, 44))
            painter.drawEllipse(rect.adjusted(-18, -18, 18, 18))
            painter.setPen(QPen(QColor(255, 239, 166, 220), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect.adjusted(-8, -8, 8, 8))
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 110), 9))
        painter.setBrush(QColor(9, 9, 9, 218))
        painter.drawEllipse(rect.adjusted(-2, -2, 2, 2))
        painter.setPen(QPen(color, 3))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(rect)
        painter.setPen(QPen(QColor('#fff0bf'), 2))
        painter.drawEllipse(rect.adjusted(2, 2, -2, -2))
        painter.setPen(QColor('#090909'))
        font = painter.font(); font.setPointSize(10 if not selected else 12); font.setBold(True); painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, 'B')
        if self.zoom_factor >= 1.20 or selected:
            text = f"{label[:24]} • {base_status_label(status)}"
            label_rect = QRectF(sx + size / 2 + 8, sy - 15, max(145, len(text) * 7 + 24), 31)
            painter.setPen(QPen(QColor(214, 174, 90, 98), 1))
            painter.setBrush(QColor(9, 9, 9, 222))
            painter.drawRoundedRect(label_rect, 9, 9)
            painter.setPen(QColor('#f5f3ed'))
            painter.drawText(label_rect.adjusted(10, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def draw_bases(self, bases, selected_base_id: int | None = None):
        active = []
        for base in list(bases or []):
            try:
                status = normalize_base_status(base["status"] if "status" in base.keys() else "friendly")
                if status in {"defeated", "gone"}:
                    continue
            except Exception:
                pass
            active.append(base)
        self.custom_bases = active
        self.selected_custom_base_id = selected_base_id
        self.update()

    def draw_pois(self, pois, selected_poi_id: int | None = None):
        active = []
        for poi in list(pois or []):
            try:
                label = poi["poi_type"] if "poi_type" in poi.keys() else poi["label"]
                pooped = bool(poi["pooped_on"]) if "pooped_on" in poi.keys() else False
                status = poi_tactical_status(str(label), pooped, str(poi["status"]) if "status" in poi.keys() else "")
                if status in {"defeated", "gone"}:
                    continue
            except Exception:
                pass
            active.append(poi)
        self.custom_pois = active
        self.selected_custom_poi_id = selected_poi_id
        self.update()

    def center_on(self, x: float, y: float):
        self.jump_to(float(x), float(y))

    def mouseDoubleClickEvent(self, event):
        coord = self._map_coord_from_screen(event.pos().x(), event.pos().y())
        if coord:
            self.poiActionRequested.emit(coord[0], coord[1], "guild")
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _draw_compass(self, painter: QPainter):
        painter.save()
        box = QRectF(self.width() - 96, 18, 72, 72)
        painter.setPen(QPen(QColor(214, 174, 90, 110), 1.2))
        painter.setBrush(QColor(9, 9, 9, 178))
        painter.drawEllipse(box)
        cx, cy = box.center().x(), box.center().y()
        painter.setPen(QPen(QColor("#f5f3ed"), 2))
        painter.drawLine(QPointF(cx, cy + 20), QPointF(cx, cy - 22))
        painter.setBrush(QColor("#d6ae5a"))
        painter.drawPolygon([QPointF(cx, cy - 29), QPointF(cx - 7, cy - 12), QPointF(cx + 7, cy - 12)])
        font = painter.font(); font.setPointSize(10); font.setBold(True); painter.setFont(font)
        painter.setPen(QColor("#d6ae5a"))
        painter.drawText(QRectF(cx - 10, cy - 13, 20, 20), Qt.AlignCenter, "N")
        painter.restore()

    def _draw_status_overlay(self, painter: QPainter, visible_count: int):
        # Removed for a cleaner, user-friendly Deep Desert map.
        return

    def _marker_at_screen(self, px: float, py: float):
        """Return ("poi"|"base", id) when the user clicks a visible guild marker."""
        best_hit = None
        best_dist = 999999.0

        for base in list(self.custom_bases or []):
            try:
                marker_id = int(base["id"] if "id" in base.keys() else base.get("id"))
                sx, sy = self._screen_point(float(base["x"]), float(base["y"]))
            except Exception:
                continue
            dist = ((float(px) - sx) ** 2 + (float(py) - sy) ** 2) ** 0.5
            if dist <= 34 and dist < best_dist:
                best_dist = dist
                best_hit = ("base", marker_id)

        for poi in list(self.custom_pois or []):
            try:
                marker_id = int(poi["id"] if "id" in poi.keys() else poi.get("id"))
                sx, sy = self._screen_point(float(poi["x"]), float(poi["y"]))
            except Exception:
                continue
            dist = ((float(px) - sx) ** 2 + (float(py) - sy) ** 2) ** 0.5
            if dist <= 30 and dist < best_dist:
                best_dist = dist
                best_hit = ("poi", marker_id)

        return best_hit

    def _draw_hover_box(self, painter: QPainter):
        painter.save()
        text = self.hover_text + (f"  {self.hover_coord}" if self.hover_coord else "")
        painter.setPen(QColor("#f7d27a"))
        painter.setBrush(QColor(12, 10, 7, 226))
        font = painter.font(); font.setPointSize(10); font.setBold(True); painter.setFont(font)
        w = max(210, len(text) * 7 + 34)
        box = QRectF(18, self.height() - 46, w, 30)
        painter.drawRoundedRect(box, 9, 9)
        painter.drawText(box, Qt.AlignCenter, text)
        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position() if hasattr(event, "position") else event.pos()
            hit = self._marker_at_screen(pos.x(), pos.y())
            if hit:
                marker_type, marker_id = hit
                if marker_type == "poi":
                    self.selected_custom_poi_id = marker_id
                    self.selected_custom_base_id = None
                elif marker_type == "base":
                    self.selected_custom_base_id = marker_id
                    self.selected_custom_poi_id = None
                self.markerSelected.emit(marker_type, int(marker_id))
                self.update()
                event.accept()
                return
            self._dragging = True
            self._last_drag = QPointF(pos.x(), pos.y())
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        if self._dragging:
            delta = QPointF(pos.x() - self._last_drag.x(), pos.y() - self._last_drag.y())
            self.pan += delta
            self._last_drag = QPointF(pos.x(), pos.y())
            self._clamp_pan()
            self.update()
            return

        coord_text = ""
        best = ""
        best_dist = 9999
        for category, x, y, label in self.POIS:
            if not self.enabled_filters.get(category, True):
                continue
            sx, sy = self._screen_point(x, y)
            dist = ((pos.x() - sx) ** 2 + (pos.y() - sy) ** 2) ** 0.5
            if dist < best_dist and dist < 24:
                best_dist = dist
                best = label
        for poi in self.custom_pois:
            try:
                sx, sy = self._screen_point(float(poi["x"]), float(poi["y"]))
                label = poi["poi_type"] if "poi_type" in poi.keys() else "Guild POI"
            except Exception:
                continue
            dist = ((pos.x() - sx) ** 2 + (pos.y() - sy) ** 2) ** 0.5
            if dist < best_dist and dist < 26:
                best_dist = dist
                best = str(label)
        for base in self.custom_bases:
            try:
                sx, sy = self._screen_point(float(base["x"]), float(base["y"]))
                name = base["base_name"] if "base_name" in base.keys() else "Base"
                status = base["status"] if "status" in base.keys() else "friendly"
            except Exception:
                continue
            dist = ((pos.x() - sx) ** 2 + (pos.y() - sy) ** 2) ** 0.5
            if dist < best_dist and dist < 30:
                best_dist = dist
                best = f"{name} • {base_status_label(status)}"
        if best != self.hover_text or coord_text != self.hover_coord:
            self.hover_text = best
            self.hover_coord = ""
            self.update()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        old = self.zoom_factor
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_factor = min(3.75, self.zoom_factor * 1.14)
        else:
            self.zoom_factor = max(1.0, self.zoom_factor / 1.14)
        if abs(self.zoom_factor - old) > 0.001:
            self._clamp_pan()
            db.set_setting("deep_desert_zoom", f"{self.zoom_factor:.2f}")
            self.update()
        event.accept()

    def contextMenuEvent(self, event):
        coord = self._map_coord_from_screen(event.pos().x(), event.pos().y())
        if not coord:
            return
        menu = QMenu(self)
        add_guild = menu.addAction("Add Guild POI here")
        add_friendly = menu.addAction("Add Friendly Base here")
        add_enemy = menu.addAction("Add Enemy Base here")
        chosen = menu.exec(event.globalPos())
        if chosen == add_guild:
            self.poiActionRequested.emit(coord[0], coord[1], "guild")
        elif chosen == add_friendly:
            self.poiActionRequested.emit(coord[0], coord[1], "friendly_base")
        elif chosen == add_enemy:
            self.poiActionRequested.emit(coord[0], coord[1], "enemy_base")


class LiveDeepDesertView(QWidget):
    """Deep Desert Tactical Command Center built as native StankyTools UI."""
    FILTERS = [
        ("shipwrecks", "Shipwrecks"),
        ("caves", "Caves"),
        ("testing_stations", "Testing Stations"),
        ("large_spice_field", "Large Spice Field"),
        ("titanium", "Titanium"),
        ("stravidium", "Stravidium"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reset_target_text = "—"
        self.add_poi_callback = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("Panel")
        hero.setMaximumHeight(86)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 14, 20, 14)
        title_box = QVBoxLayout()
        title = QLabel("DEEP DESERT COMBAT MAP")
        title.setObjectName("SectionTitle")
        title_box.addWidget(title)
        hero_layout.addLayout(title_box, 1)
        self.reset_label = StatusPill("Weekly Update", "Tue 7:30 ET")
        self.sync_label = StatusPill("Map", "Cached")
        self.update_map_btn = QPushButton("Update Weekly Map")
        self.update_map_btn.setObjectName("PrimaryButton")
        self.update_map_btn.setToolTip("Capture the current Deep Desert map from dune.gaming.tools after a 5 second load wait.")
        self.update_map_btn.clicked.connect(lambda: self.update_weekly_map(force=True))
        hero_layout.addWidget(self.reset_label)
        hero_layout.addWidget(self.sync_label)
        hero_layout.addWidget(self.update_map_btn)
        layout.addWidget(hero)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.canvas = NativeDeepDesertCanvas()
        self.canvas.poiActionRequested.connect(self._poi_action_requested)
        body.addWidget(self.canvas, 1)

        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setMaximumWidth(360)
        panel.setMinimumWidth(320)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)

        head = QLabel("PLACED INTEL")
        head.setStyleSheet("color:#d6ae5a; font-size:13px; font-weight:950; letter-spacing:2px;")
        panel_layout.addWidget(head)
        self.marker_table = StankyTable(["Status", "POI / Base", "Note"])
        self.marker_table.setMinimumHeight(430)
        self.marker_table.setObjectName("IntelTable")
        self.marker_table.setColumnWidth(0, 78)
        self.marker_table.setColumnWidth(1, 130)
        panel_layout.addWidget(self.marker_table, 1)
        self.archive_toggle = QPushButton("Archived Intel (0)")
        self.archive_toggle.setCheckable(False)
        self.archive_toggle.setObjectName("PrimaryButton")
        panel_layout.addWidget(self.archive_toggle)
        self.archive_table = StankyTable(["Status", "Archived Intel", "Note"])
        self.archive_table.setObjectName("IntelTable")
        self.archive_table.setMaximumHeight(190)
        self.archive_table.setVisible(False)
        # Archived Intel opens in a quiet custom popup instead of expanding inline.
        self.archive_toggle.clicked.connect(self._show_archive_requested)
        panel_layout.addWidget(self.archive_table)
        reset_btn = QPushButton("Reset Map View")
        reset_btn.clicked.connect(self.canvas.reset_view)
        panel_layout.addWidget(reset_btn)
        body.addWidget(panel)
        layout.addLayout(body, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_reset_countdown)
        self._timer.start(60000)
        self._update_active_label()
        self._sync_canvas_filters()
        self._update_reset_countdown()
        QTimer.singleShot(1500, self._maybe_auto_update_weekly_map)

    def _map_source_url(self) -> str:
        return getattr(deep_desert, "MAP_URL", "https://dune.gaming.tools/deep-desert")

    def _set_map_update_busy(self, busy: bool, text: str | None = None):
        try:
            self.update_map_btn.setEnabled(not busy)
            self.update_map_btn.setText(text or ("Updating..." if busy else "Update Weekly Map"))
        except Exception:
            pass

    def _maybe_auto_update_weekly_map(self):
        """Automatically refresh once after the weekly Tuesday 7:30 AM ET reset window."""
        try:
            if deep_desert.should_auto_screenshot():
                self.update_weekly_map(force=False)
        except Exception:
            # Auto-update is convenience only; never block the map page from opening.
            pass

    def update_weekly_map(self, force: bool = True):
        """Capture dune.gaming.tools/deep-desert after a 5 second wait and use it as the local map.

        This uses QtWebEngine when available so no external browser or Playwright
        install is required. The cached screenshot is stored in the user's data
        folder and survives app updates.
        """
        if not WEBENGINE_AVAILABLE or QWebEngineView is None:
            QMessageBox.information(
                self,
                "Deep Desert Map",
                "This build does not include Qt WebEngine, so the map screenshot updater is unavailable.",
            )
            return
        if not force:
            try:
                if not deep_desert.should_auto_screenshot():
                    return
            except Exception:
                return
        self._set_map_update_busy(True, "Loading Map...")
        self.sync_label.value.setText("Loading")

        view = QWebEngineView()
        self._weekly_map_view = view
        try:
            profile = QWebEngineProfile.defaultProfile() if QWebEngineProfile is not None else None
            page = QuietWebEnginePage(profile, view) if profile is not None else QuietWebEnginePage(view)
            view.setPage(page)
        except Exception:
            pass
        view.resize(1600, 1600)
        view.move(-20000, -20000)
        view.setWindowOpacity(0.01)
        view.show()

        def after_loaded(ok: bool):
            if not ok:
                self._finish_weekly_map_capture(None, "Unable to load dune.gaming.tools/deep-desert")
                return
            self.sync_label.value.setText("Waiting 5s")
            self._set_map_update_busy(True, "Capturing in 5s...")
            QTimer.singleShot(5000, lambda: self._capture_weekly_map_view(view))

        view.loadFinished.connect(after_loaded)
        view.setUrl(QUrl(self._map_source_url()))

    def _capture_weekly_map_view(self, view):
        """Capture only the square Deep Desert map grid, not the full website chrome/sidebar."""
        try:
            js = r"""
(() => {
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  function visibleRect(el) {
    const r = el.getBoundingClientRect();
    const st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity || 1) === 0) return null;
    if (r.width < 300 || r.height < 300) return null;
    if (r.bottom <= 0 || r.right <= 0 || r.top >= vh || r.left >= vw) return null;
    return {
      x: Math.max(0, r.left),
      y: Math.max(0, r.top),
      w: Math.min(r.width, vw - Math.max(0, r.left)),
      h: Math.min(r.height, vh - Math.max(0, r.top)),
      rawW: r.width,
      rawH: r.height
    };
  }

  // 1) Prefer the actual square map element. The site renders the Deep Desert
  // map as a large square grid to the right of the filters/sidebar. This avoids
  // capturing the country tabs, side filters, banner, or page chrome.
  const tags = Array.from(document.querySelectorAll('canvas, img, svg, [class], [style]'));
  let best = null;
  let bestScore = -1;
  for (const el of tags) {
    const tag = el.tagName.toLowerCase();
    if (['html', 'body', 'main', 'section', 'aside', 'nav', 'header', 'footer'].includes(tag)) continue;
    const r = visibleRect(el);
    if (!r) continue;

    const ratio = r.w / Math.max(1, r.h);
    const squareError = Math.abs(ratio - 1);
    if (squareError > 0.12) continue;
    if (r.x < vw * 0.10 || r.y < 60) continue;

    const cls = String(el.className || '').toLowerCase();
    const style = window.getComputedStyle(el);
    const bgImage = String(style.backgroundImage || '').toLowerCase();
    const id = String(el.id || '').toLowerCase();
    const label = (cls + ' ' + id + ' ' + bgImage).toLowerCase();

    let score = r.w * r.h;
    score -= squareError * score * 6;
    if (tag === 'canvas' || tag === 'img' || tag === 'svg') score *= 4;
    if (label.includes('map')) score *= 5;
    if (label.includes('deep')) score *= 3;
    if (label.includes('aspect-square') || label.includes('square')) score *= 4;
    if (bgImage && bgImage !== 'none') score *= 2;
    // Penalize parent wrappers that include nearby filters/text/buttons.
    const textLen = (el.innerText || '').trim().length;
    if (textLen > 80) score *= 0.15;
    if (el.querySelectorAll && el.querySelectorAll('button,input,select,a').length > 2) score *= 0.10;

    if (score > bestScore) {
      bestScore = score;
      best = r;
    }
  }

  if (best && best.w >= 500 && best.h >= 500) {
    const side = Math.min(best.w, best.h);
    return { x: Math.round(best.x), y: Math.round(best.y), w: Math.round(side), h: Math.round(side), mode: 'element' };
  }

  // 2) Geometry fallback based on the known page layout:
  // the map is the large square immediately to the right of the left filter column.
  let sidebarRight = 0;
  for (const el of Array.from(document.querySelectorAll('aside, nav, div'))) {
    const r = visibleRect(el);
    if (!r) continue;
    if (r.x <= 25 && r.w >= 80 && r.w <= 420 && r.h >= 350) {
      sidebarRight = Math.max(sidebarRight, r.x + r.w);
    }
  }

  let x = sidebarRight > 80 ? sidebarRight + 12 : Math.round(vw * 0.19);

  // Top edge is just below the region tabs/date row. Find the first large square-ish
  // visual area to the right of the sidebar. If unavailable, use the red-box proportions
  // from the reference screenshot.
  let y = 0;
  const rightSideSquares = [];
  for (const el of tags) {
    const r = visibleRect(el);
    if (!r) continue;
    const ratio = r.w / Math.max(1, r.h);
    if (r.x >= x - 35 && r.y >= 70 && Math.abs(ratio - 1) <= 0.20 && r.w >= 450 && r.h >= 450) {
      rightSideSquares.push(r);
    }
  }
  if (rightSideSquares.length) {
    rightSideSquares.sort((a, b) => (b.w * b.h) - (a.w * a.h));
    x = Math.round(rightSideSquares[0].x);
    y = Math.round(rightSideSquares[0].y);
  } else {
    y = Math.round(vh * 0.18);
  }

  const side = Math.floor(Math.min(vw - x - 8, vh - y - 8));
  if (side >= 500) return { x, y, w: side, h: side, mode: 'geometry' };

  return null;
})()
"""
            try:
                view.page().runJavaScript(js, lambda rect: self._save_weekly_map_crop(view, rect))
            except Exception:
                self._save_weekly_map_crop(view, None)
        except Exception as exc:
            self._finish_weekly_map_capture(None, str(exc))

    def _save_weekly_map_crop(self, view, rect):
        try:
            pixmap = view.grab()
            if pixmap.isNull() or pixmap.width() < 600 or pixmap.height() < 600:
                self._finish_weekly_map_capture(None, "Captured map image was empty.")
                return

            # The website includes banners, tabs, side filters, and labels around the map.
            # The user only wants the square sandy Deep Desert map area.  DOM selectors on
            # dune.gaming.tools change often, so we first detect the actual tan desert map
            # pixels from the rendered screenshot, then fall back to DOM geometry only if
            # pixel detection fails.
            cropped = None
            detected = self._detect_deep_desert_map_rect(pixmap)
            if detected is not None:
                x, y, side = detected
                cropped = pixmap.copy(x, y, side, side)

            if cropped is None or cropped.isNull():
                if isinstance(rect, dict):
                    x = int(float(rect.get("x", 0)))
                    y = int(float(rect.get("y", 0)))
                    w = int(float(rect.get("w", 0)))
                    h = int(float(rect.get("h", 0)))
                    side = max(0, min(w, h, pixmap.width() - x, pixmap.height() - y))
                    if side >= 500:
                        cropped = pixmap.copy(x, y, side, side)

            # Final fallback based on the green-box reference: a square map sitting to the
            # right of the filter sidebar and below the region tabs.  This fallback is only
            # used if both pixel detection and DOM detection fail.
            if cropped is None or cropped.isNull():
                x = int(pixmap.width() * 0.192)
                y = int(pixmap.height() * 0.183)
                side = min(int(pixmap.width() * 0.789), pixmap.width() - x, pixmap.height() - y)
                if side >= 500:
                    cropped = pixmap.copy(x, y, side, side)
                else:
                    cropped = pixmap

            output = data_dir() / "deep_desert_map.png"
            output.parent.mkdir(parents=True, exist_ok=True)
            if not cropped.save(str(output), "PNG"):
                self._finish_weekly_map_capture(None, "Could not save the Deep Desert map crop.")
                return
            self._finish_weekly_map_capture(str(output), "Updated")
        except Exception as exc:
            self._finish_weekly_map_capture(None, str(exc))

    def _detect_deep_desert_map_rect(self, pixmap):
        """Return (x, y, side) for the sandy square map area, or None.

        This intentionally captures NOTHING outside the map square. It ignores the
        left filter sidebar, top banner/tabs, and any page chrome by looking for
        the large contiguous desert-colored region in the rendered page.
        """
        try:
            image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)
            width = image.width()
            height = image.height()
            if width < 600 or height < 600:
                return None

            step = 4
            col_hits = [0] * width
            row_hits = [0] * height

            def is_desert_pixel(rgb: int) -> bool:
                r = (rgb >> 16) & 255
                g = (rgb >> 8) & 255
                b = rgb & 255
                # Sandy Deep Desert background: warm tan/orange.  These limits are
                # wide enough for grid lines and shade variation, but exclude the
                # dark site UI, white text, green/red guide boxes, and icons.
                return (
                    125 <= r <= 245
                    and 75 <= g <= 205
                    and 35 <= b <= 165
                    and r >= g + 18
                    and g >= b + 10
                    and (r + g + b) >= 260
                )

            for y in range(0, height, step):
                row_count = 0
                for x in range(0, width, step):
                    if is_desert_pixel(image.pixel(x, y)):
                        col_hits[x] += 1
                        row_count += 1
                row_hits[y] = row_count

            # Convert sampled hit counts into active columns/rows. The map area has
            # dense tan pixels across the whole square; sidebar/header rows do not.
            min_col_hits = max(45, int((height / step) * 0.18))
            min_row_hits = max(45, int((width / step) * 0.18))
            active_cols = [i for i, c in enumerate(col_hits) if c >= min_col_hits]
            active_rows = [i for i, c in enumerate(row_hits) if c >= min_row_hits]
            if not active_cols or not active_rows:
                return None

            def longest_segment(values, max_gap=12):
                best = None
                start = prev = values[0]
                for value in values[1:]:
                    if value - prev <= max_gap:
                        prev = value
                        continue
                    if best is None or (prev - start) > (best[1] - best[0]):
                        best = (start, prev)
                    start = prev = value
                if best is None or (prev - start) > (best[1] - best[0]):
                    best = (start, prev)
                return best

            x1, x2 = longest_segment(active_cols)
            y1, y2 = longest_segment(active_rows)

            # Expand from sample coordinates to the map edge. Then force a square by
            # using the smaller dimension so nothing outside the green-box map area is
            # included.
            x1 = max(0, x1 - step)
            y1 = max(0, y1 - step)
            x2 = min(width - 1, x2 + step)
            y2 = min(height - 1, y2 + step)
            detected_w = x2 - x1 + 1
            detected_h = y2 - y1 + 1
            side = min(detected_w, detected_h)

            if side < 500:
                return None

            # The map is the large square on the right side of the page. Reject any
            # accidental detection of a small ad/banner or page background.
            if x1 < int(width * 0.12) or y1 < 70:
                return None

            # If the detected tan region is slightly taller/wider because of antialiasing,
            # anchor to the top-left tan edge and crop inward to stay inside the square.
            x = int(x1)
            y = int(y1)
            side = int(min(side, width - x, height - y))
            return (x, y, side)
        except Exception:
            return None

    def _finish_weekly_map_capture(self, image_path: str | None, status: str):
        try:
            view = getattr(self, "_weekly_map_view", None)
            if view is not None:
                view.hide()
                view.deleteLater()
            self._weekly_map_view = None
        except Exception:
            pass
        self._set_map_update_busy(False)
        if image_path:
            try:
                meta = deep_desert.save_screenshot_meta(image_path)
                self.sync_label.value.setText(format_app_date(str(meta.get("last_checked", ""))))
            except Exception:
                self.sync_label.value.setText("Updated")
            try:
                self.canvas.reload_background()
            except Exception:
                pass
            if status != "Auto":
                QMessageBox.information(self, "Deep Desert Map", "Deep Desert map updated from dune.gaming.tools.")
        else:
            self.sync_label.value.setText("Failed")
            if status:
                QMessageBox.warning(self, "Deep Desert Map", f"Map update failed: {status}")

    def _set_all_filters(self, checked: bool):
        return

    def _filter_changed(self, key: str, checked: bool):
        return

    def _filter_state(self) -> dict[str, bool]:
        return {}

    def _sync_canvas_filters(self):
        self.canvas.set_filters({})

    def _show_archive_requested(self):
        parent = self.window()
        callback = getattr(parent, "show_archived_intel_popup", None)
        if callable(callback):
            callback()

    def _update_active_label(self):
        if hasattr(self, "active_label"):
            self.active_label.setText("Enemy red • Friendly green • Defeated/Gone gray")

    def _jump_to_coord(self):
        raw = self.coord_input.text().replace(" ", "")
        try:
            x_s, y_s = raw.split(",", 1)
            x = max(0, min(881, float(x_s)))
            y = max(0, min(883, float(y_s)))
            self.canvas.jump_to(x, y)
            self.coordinate_label.value.setText(f"X {int(x):03d}  Y {int(y):03d}")
        except Exception:
            QMessageBox.information(self, "Deep Desert", "Enter coordinates like 440,520")

    def _poi_action_requested(self, x: float, y: float, scope: str):
        """Create a guild POI directly from the native map.

        Older RC builds only showed a placeholder message here. The map now
        routes double-click/right-click placement straight into the existing
        guild POI editor so the user never sees a dead-end popup.
        """
        if scope in {"friendly_base", "enemy_base"}:
            callback = getattr(self, "add_base_callback", None)
            if callable(callback):
                callback(float(x), float(y), "friendly" if scope == "friendly_base" else "enemy")
                try:
                    self.canvas.update()
                except Exception:
                    pass
                return
        callback = getattr(self, "add_poi_callback", None)
        if callable(callback):
            callback(float(x), float(y))
            try:
                self.canvas.update()
            except Exception:
                pass
            return
        QMessageBox.information(self, "Deep Desert", "Guild POI placement is not available yet.")

    def _update_reset_countdown(self):
        try:
            meta = deep_desert.load_meta()
            nxt = str(meta.get("next_scheduled_update", ""))
            if nxt:
                self.reset_label.value.setText(format_app_date(nxt))
            else:
                self.reset_label.value.setText("Tue 7:30 ET")
        except Exception:
            self.reset_label.value.setText("Tue 7:30 ET")

    def reload(self):
        try:
            meta = deep_desert.load_meta()
            self.sync_label.value.setText(format_app_date(str(meta.get("last_checked", ""))) or "Cached")
        except Exception:
            self.sync_label.value.setText("Cached")
        try:
            self.canvas.reload_background()
        except Exception:
            self.canvas.update()


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

    def _draw_base_marker(self, painter: QPainter, sx: float, sy: float, label: str, status: str = "friendly", note: str = "", selected: bool = False):
        painter.save()
        color = base_status_color(status)
        size = 32 if not selected else 44
        rect = QRectF(sx - size / 2, sy - size / 2, size, size)
        if selected:
            painter.setPen(QPen(QColor(247, 210, 122, 185), 11))
            painter.setBrush(QColor(247, 210, 122, 44))
            painter.drawEllipse(rect.adjusted(-18, -18, 18, 18))
            painter.setPen(QPen(QColor(255, 239, 166, 220), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect.adjusted(-8, -8, 8, 8))
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 110), 9))
        painter.setBrush(QColor(9, 9, 9, 218))
        painter.drawEllipse(rect.adjusted(-2, -2, 2, 2))
        painter.setPen(QPen(color, 3))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(rect)
        painter.setPen(QPen(QColor('#fff0bf'), 2))
        painter.drawEllipse(rect.adjusted(2, 2, -2, -2))
        painter.setPen(QColor('#090909'))
        font = painter.font(); font.setPointSize(10 if not selected else 12); font.setBold(True); painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, 'B')
        if self.zoom_factor >= 1.20 or selected:
            text = f"{label[:24]} • {base_status_label(status)}"
            label_rect = QRectF(sx + size / 2 + 8, sy - 15, max(145, len(text) * 7 + 24), 31)
            painter.setPen(QPen(QColor(214, 174, 90, 98), 1))
            painter.setBrush(QColor(9, 9, 9, 222))
            painter.drawRoundedRect(label_rect, 9, 9)
            painter.setPen(QColor('#f5f3ed'))
            painter.drawText(label_rect.adjusted(10, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def draw_bases(self, bases, selected_base_id: int | None = None):
        self.custom_bases = list(bases or [])
        self.selected_custom_base_id = selected_base_id
        self.update()

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
            color = profile_color(creator)
            is_mine = (creator or '').strip().lower() == (current_user or '').strip().lower()

            tooltip = (
                f"Member: {creator or 'Unknown'}\n"
                f"Base: {name or 'Guild Base'}\n"
                f"Sietch: {seitch or 'Unknown'}\n"
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
            sub_text = f"{seitch or 'Unknown Sietch'} • {base_status_label(status)}"
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
            sub = self.scene.addText(f"Sietch: {sub_text}")
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
    "gone": "#6b6f76",
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
    "gone": "#6b6f76",
    "active": "#9c5ac6",
}


def poi_tactical_status(poi_type: str, defeated: bool = False, status: str = "") -> str:
    clean = (status or "").strip().lower()
    if clean in {"friendly", "enemy", "defeated", "gone", "active"}:
        return clean
    raw = (poi_type or "").strip().lower()
    if "gone" in raw:
        return "gone"
    if defeated:
        return "defeated"
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
    if status == "gone":
        return "Gone"
    return "Active"


def poi_status_color(status: str) -> QColor:
    return QColor(POI_STATUS_COLORS.get((status or "active").strip().lower(), POI_STATUS_COLORS["active"]))




def apply_soft_shadow(widget, *, blur: int = 30, y: int = 10, alpha: int = 80) -> None:
    """Apply the shared soft card shadow used by the polished UI pass.

    The helper is intentionally defensive because some widgets are recreated
    during guild refreshes and should never crash the app if Qt has already
    cleaned up the native object.
    """
    if not qt_alive(widget):
        return
    try:
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y)
        effect.setColor(QColor(0, 0, 0, alpha))
        widget.setGraphicsEffect(effect)
    except Exception:
        pass

def role_can_manage_guild() -> bool:
    return (db.get_setting("guild_role", "member") or "member").lower() in {"owner", "officer"}


def guild_logo_cache_path(guild_code: str | None = None) -> Path:
    """Return a per-guild logo cache path so multiple guilds do not overwrite each other."""
    guild = (guild_code or db.get_setting("guild_code", "") or "").strip().upper()
    safe = "".join(ch for ch in guild if ch.isalnum() or ch in {"-", "_"})
    if safe:
        return data_dir() / f"guild_logo_{safe}.png"
    return data_dir() / "guild_logo.png"


def legacy_guild_logo_cache_path() -> Path:
    return data_dir() / "guild_logo.png"


def safe_label_set_text(widget, text: str) -> None:
    if qt_alive(widget):
        try:
            widget.setText(text)
        except RuntimeError:
            pass


def safe_label_set_pixmap(widget, pixmap: QPixmap) -> None:
    if qt_alive(widget):
        try:
            widget.setPixmap(pixmap)
        except RuntimeError:
            pass


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


class ToastNotification(QFrame):
    """Small premium notification used for RC1 instead of blocking dialogs."""

    def __init__(self, parent: QWidget, title: str, message: str = "", kind: str = "info"):
        super().__init__(parent)
        self.setObjectName("ToastNotification")
        apply_soft_shadow(self, blur=36, y=12, alpha=100)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_StyledBackground, True)
        colors = {
            "success": "#2ECC71",
            "warning": "#D6AE5A",
            "error": "#B23A48",
            "info": "#57C7D4",
        }
        accent = colors.get(kind, colors["info"])
        self.setStyleSheet(f"""
            QFrame#ToastNotification {{
                background: rgba(10, 9, 7, 238);
                border: 1px solid {accent};
                border-radius: 14px;
            }}
            QLabel#ToastTitle {{
                color: #F5F3ED;
                font-weight: 900;
                letter-spacing: 1px;
                font-size: 13px;
            }}
            QLabel#ToastBody {{
                color: rgba(245,243,237,0.72);
                font-size: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        t = QLabel(title.upper())
        t.setObjectName("ToastTitle")
        b = QLabel(message)
        b.setObjectName("ToastBody")
        b.setWordWrap(True)
        layout.addWidget(t)
        if message:
            layout.addWidget(b)
        self.setFixedWidth(360)
        self.adjustSize()

    def show_near_parent(self, timeout_ms: int = 3200):
        parent = self.parentWidget()
        if parent is not None:
            g = parent.geometry()
            self.move(g.right() - self.width() - 30, g.bottom() - self.height() - 30)
        self.show()
        self.raise_()
        QTimer.singleShot(timeout_ms, self.close)


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
        self._install_easter_egg_shortcut()
        self.refresh_all()
        self._sync_running = False
        self._last_auto_sync = 0.0
        self.sync_manager = SyncManager(self)
        self.guild_sync_timer = QTimer(self)
        # Lightweight polling keeps Events and Member Specializations visible on every open app.
        # Writes still go through the debounced SyncManager; this only pulls remote updates.
        self.guild_sync_timer.setInterval(15000)
        self.guild_sync_timer.timeout.connect(self.pull_guild_updates)
        self.guild_sync_timer.start()
        # Catalog image import is now handled from the Market/Catalog section, not at app startup.

    def notify(self, title: str, message: str = "", kind: str = "info", timeout_ms: int = 3200):
        try:
            toast = ToastNotification(self, title, message, kind)
            toast.show_near_parent(timeout_ms)
            return toast
        except Exception:
            # Notifications should never interrupt the user's workflow.
            return None

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar.setFixedWidth(310)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(8, 8, 8, 14)
        side_layout.setSpacing(10)

        side_header = QFrame()
        side_header.setObjectName("SideHeader")
        side_header.setContentsMargins(0, 0, 0, 0)
        side_header.setStyleSheet("QFrame#SideHeader { background: transparent; border: none; padding: 0px; margin: 0px; }")
        head_layout = QVBoxLayout(side_header)
        head_layout.setContentsMargins(0, 0, 0, 0)
        head_layout.setSpacing(0)

        self.sidebar_logo = QLabel()
        self.sidebar_logo.setObjectName("MascotLogo")
        self.sidebar_logo.setAlignment(Qt.AlignCenter)
        self.sidebar_logo.setContentsMargins(0, 0, 0, 0)
        self.sidebar_logo.setStyleSheet("QLabel#MascotLogo { background: transparent; border: none; padding: 0px; margin: 0px; }")
        self.sidebar_logo.setFixedHeight(340)
        stanky_logo = asset_path("images", "stankytools_mascot_logo.png")
        if stanky_logo.exists():
            pix = trim_transparent_pixmap(QPixmap(str(stanky_logo)))
            if not pix.isNull():
                self.sidebar_logo.setPixmap(pix.scaled(304, 336, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head_layout.addWidget(self.sidebar_logo, 0, Qt.AlignCenter)

        self.sidebar_guild_status = QLabel((db.get_setting("guild_name", "NO GUILD") or "NO GUILD").upper())
        self.sidebar_guild_status.setObjectName("GuildStatusPill")
        self.sidebar_role_status = QLabel((db.get_setting("guild_role", "LOCAL MODE") or "LOCAL MODE").upper())
        self.sidebar_role_status.setObjectName("MicroLabel")
        # Guild identity is shown in its own larger card below the StankyTools brand box.
        # Keep these labels as invisible compatibility references for older refresh paths.
        self.sidebar_guild_status.setVisible(False)
        self.sidebar_role_status.setVisible(False)
        side_layout.addWidget(side_header)

        guild_identity = QFrame()
        guild_identity.setObjectName("CommandCard")
        guild_identity_layout = QHBoxLayout(guild_identity)
        guild_identity_layout.setContentsMargins(14, 14, 14, 14)
        guild_identity_layout.setSpacing(14)
        self.sidebar_guild_logo_small = QLabel("G")
        self.sidebar_guild_logo_small.setAlignment(Qt.AlignCenter)
        self.sidebar_guild_logo_small.setFixedSize(118, 118)
        self.sidebar_guild_logo_small.setObjectName("DashboardGuildLogo")
        guild_text = QVBoxLayout()
        self.sidebar_guild_name_display = QLabel((db.get_setting("guild_name", "NO GUILD") or "NO GUILD").upper())
        self.sidebar_guild_name_display.setObjectName("GuildStatusPill")
        self.sidebar_guild_name_display.setStyleSheet("font-size:16px; font-weight:900; letter-spacing:1px;")
        self.sidebar_guild_role_display = QLabel((db.get_setting("guild_role", "LOCAL MODE") or "LOCAL MODE").upper())
        self.sidebar_guild_role_display.setObjectName("MicroLabel")
        self.sidebar_guild_role_display.setStyleSheet("font-size:13px; font-weight:900; letter-spacing:1px; color:#D6AE5A;")
        guild_text.addWidget(self.sidebar_guild_name_display)
        guild_text.addWidget(self.sidebar_guild_role_display)
        guild_identity_layout.addWidget(self.sidebar_guild_logo_small)
        guild_identity_layout.addLayout(guild_text, 1)
        guild_identity.setVisible(False)
        # Guild identity is shown on the dashboard only, not in the left navigation.
        side_layout.addSpacing(6)

        self.pages = QStackedWidget()
        page_builders = [
            self._build_dashboard_page,
            self._build_market_page,
            self._build_deep_desert_page,
            self._build_hagga_basin_page,
            self._build_guild_page,
            self._build_settings_page,
        ]
        for builder in page_builders:
            self.pages.addWidget(builder())
        self.guild_page_index = 4

        nav_specs = [
            ("Guild Admin", "nav_guild_admin.png", lambda checked=False: self.open_guild_admin_page(), 4),
            ("Dashboard", "nav_dashboard.png", lambda checked=False: self.set_page(0), 0),
            ("Database", "nav_auction_house.png", lambda checked=False: self.set_page(1), 1),
            ("Deep Desert", "nav_deep_desert.png", lambda checked=False: self.set_page(2), 2),
            ("Hagga Basin", "nav_hagga_basin.png", lambda checked=False: self.set_page(3), 3),
            ("Settings", "nav_settings.png", lambda checked=False: self.set_page(5), 5),
        ]
        for label, image_name, callback, page_index in nav_specs:
            btn = QToolButton()
            btn.setText("")
            btn.setAccessibleName(label)
            image_path = asset_path("ui", "menu_buttons", image_name)
            if image_path.exists():
                btn.setIcon(QIcon(str(image_path)))
                btn.setIconSize(QSize(278, 72))
            else:
                btn.setText(label.upper())
                fallback_icon = asset_path("icons", "settings_menu.png")
                if fallback_icon.exists():
                    btn.setIcon(QIcon(str(fallback_icon)))
                    btn.setIconSize(QSize(34, 34))
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setMinimumHeight(78)
            btn.setMaximumHeight(84)
            btn.setObjectName("ImageNavButton")
            btn.setProperty("page_index", page_index)
            btn.setProperty("active", page_index == 0)
            if label == "Guild Admin":
                self.guild_nav_button = btn
            btn.clicked.connect(callback)
            self.nav_buttons.append(btn)
            side_layout.addWidget(btn)
        side_layout.addStretch()
        # Production navigation footer intentionally left clean.

        main.addWidget(sidebar)
        main.addWidget(self.pages, 1)
        self.update_guild_nav_visibility()

    def _install_easter_egg_shortcut(self):
        """Hidden in-app YouTube popup. Press Ctrl+Alt+S."""
        try:
            self.easter_egg_shortcut = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
            self.easter_egg_shortcut.activated.connect(self.show_spice_easter_egg)
        except Exception:
            pass

    def show_spice_easter_egg(self):
        """Show the polished local MP4 classified transmission.

        The video is downloaded from GitHub Releases on first use, then cached
        locally. The overlay autoplays, has no playback controls, and closes
        itself when the media reaches the end.
        """
        video_path = ensure_easter_egg_video(self)
        if not video_path:
            return
        if not MULTIMEDIA_AVAILABLE:
            try:
                webbrowser.open(video_path.as_uri())
            except Exception:
                QMessageBox.information(self, "Classified Transmission", f"Video saved at:\n{video_path}")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("CLASSIFIED TRANSMISSION")
        dlg.setModal(True)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dlg.setMinimumSize(980, 620)
        dlg.setObjectName("ClassifiedTransmissionDialog")
        dlg.setStyleSheet("""
            QDialog#ClassifiedTransmissionDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #030303, stop:1 #14100a);
                border: 1px solid rgba(214,174,90,0.55);
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header = QLabel("CLASSIFIED TRANSMISSION")
        header.setObjectName("SectionTitle")
        header.setStyleSheet("letter-spacing: 3px; color: #D6AE5A; font-size: 18px; font-weight: 800;")
        status = StatusPill("Signal", "Unlocked")
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(status)

        video = QVideoWidget()
        video.setMinimumHeight(500)
        video.setStyleSheet("background: #000; border: 1px solid rgba(214,174,90,0.35); border-radius: 12px;")

        footer = QLabel("ESC TO CLOSE")
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName("MicroLabel")
        footer.setStyleSheet("color: rgba(245,243,237,0.45); letter-spacing: 2px;")

        player = QMediaPlayer(dlg)
        audio = QAudioOutput(dlg)
        audio.setVolume(0.90)
        player.setAudioOutput(audio)
        player.setVideoOutput(video)
        player.setSource(QUrl.fromLocalFile(str(video_path.resolve())))

        def _media_status_changed(status_value):
            try:
                if status_value == QMediaPlayer.MediaStatus.EndOfMedia:
                    QTimer.singleShot(150, dlg.accept)
            except Exception:
                pass

        player.mediaStatusChanged.connect(_media_status_changed)
        dlg.finished.connect(lambda *_: player.stop())

        close_shortcut = QShortcut(QKeySequence("Esc"), dlg)
        close_shortcut.activated.connect(dlg.accept)

        layout.addLayout(header_row)
        layout.addWidget(video, 1)
        layout.addWidget(footer)

        # Start once the dialog has had a chance to initialize its video surface.
        QTimer.singleShot(250, player.play)
        dlg.exec()

    def set_page(self, index: int):
        # Guild page is an admin-only area. Members can see public guild info on the dashboard,
        # but they cannot open the admin section.
        if index == getattr(self, "guild_page_index", 4) and not role_can_manage_guild():
            QMessageBox.information(self, "Guild Admin", "The Guild section is available to owners and officers only.")
            index = 0
        self.pages.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setProperty("active", int(btn.property("page_index") or -1) == index)
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
        if _qt_alive(btn):
            btn.setVisible(admin)

        # Quick Actions were removed from the dashboard. Older in-memory builds may still
        # have a dashboard_guild_button reference, but its Qt object can be destroyed after
        # the dashboard is rebuilt. Never touch it unless the wrapper is still valid.
        dashboard_guild_button = getattr(self, "dashboard_guild_button", None)
        if _qt_alive(dashboard_guild_button):
            dashboard_guild_button.setVisible(admin)
        elif hasattr(self, "dashboard_guild_button"):
            self.dashboard_guild_button = None

        pages = getattr(self, "pages", None)
        if _qt_alive(pages) and pages.currentIndex() == getattr(self, "guild_page_index", 4) and not admin:
            pages.setCurrentIndex(0)

    def open_market_tab(self, tab_index: int = 0):
        self.set_page(1)

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
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.setSpacing(18)

        hero = HeroFrame(asset_path("backgrounds", "dashboard_banner.png"))
        hero.setMinimumHeight(190)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(32, 24, 32, 24)
        hero_layout.setSpacing(22)

        hero_text = QVBoxLayout()
        kicker = QLabel("STANKYTOOLS COMMAND CENTER")
        kicker.setObjectName("HeroKicker")
        title = QLabel("ARRAKIS OPERATIONS")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Market intelligence • Guild coordination • Tactical map control")
        subtitle.setObjectName("HeroSub")
        self.dashboard_sync_status = QLabel("SYNC STATUS: READY")
        self.dashboard_sync_status.setObjectName("VersionPill")
        hero_text.addWidget(kicker)
        hero_text.addWidget(title)
        hero_text.addWidget(subtitle)
        hero_text.addStretch()
        sync_row = QHBoxLayout()
        sync_row.setSpacing(10)
        sync_row.addWidget(self.dashboard_sync_status)
        self.dashboard_guild_sync_button = QPushButton("GUILD SYNC")
        self.dashboard_guild_sync_button.setObjectName("PrimaryButton")
        self.dashboard_guild_sync_button.clicked.connect(self.manual_guild_sync_from_dashboard)
        sync_row.addWidget(self.dashboard_guild_sync_button)
        sync_row.addStretch()
        hero_text.addLayout(sync_row)
        hero_layout.addLayout(hero_text, 1)

        outer.addWidget(hero)

        self.stat_grid = QGridLayout()
        self.stat_grid.setSpacing(14)

        self.dashboard_guild_identity_card = QFrame()
        self.dashboard_guild_identity_card.setObjectName("CommandCard")
        identity_layout = QHBoxLayout(self.dashboard_guild_identity_card)
        identity_layout.setContentsMargins(14, 12, 14, 12)
        identity_layout.setSpacing(12)
        self.dashboard_guild_logo_large = QLabel("G")
        self.dashboard_guild_logo_large.setObjectName("DashboardGuildLogo")
        self.dashboard_guild_logo_large.setAlignment(Qt.AlignCenter)
        self.dashboard_guild_logo_large.setFixedSize(86, 86)
        identity_text = QVBoxLayout()
        identity_text.setSpacing(3)
        self.dashboard_guild_name_label = QLabel((db.get_setting("guild_name", "NO GUILD") or "NO GUILD").upper())
        self.dashboard_guild_name_label.setObjectName("SectionTitle")
        self.dashboard_guild_name_label.setStyleSheet("font-size:18px; font-weight:950; letter-spacing:1px; color:#F5F3ED;")
        self.dashboard_guild_role_label = QLabel((db.get_setting("guild_role", "LOCAL MODE") or "LOCAL MODE").upper())
        self.dashboard_guild_role_label.setObjectName("MicroLabel")
        self.dashboard_guild_role_label.setStyleSheet("font-size:14px; font-weight:900; color:#D6AE5A; letter-spacing:1px;")
        identity_text.addStretch()
        identity_text.addWidget(self.dashboard_guild_name_label)
        identity_text.addWidget(self.dashboard_guild_role_label)
        self.dashboard_specializations_button = QPushButton("Member Specializations")
        self.dashboard_specializations_button.setObjectName("PrimaryButton")
        self.dashboard_specializations_button.clicked.connect(self.show_member_specializations_dialog)
        identity_text.addWidget(self.dashboard_specializations_button)
        identity_text.addStretch()
        identity_layout.addWidget(self.dashboard_guild_logo_large)
        identity_layout.addLayout(identity_text, 1)

        self.dashboard_stat_members = PremiumStatCard("Guild Members", "—", "Current roster")
        self.dashboard_stat_bases = PremiumStatCard("Guild Bases", "—", "Hagga Basin operations")
        self.dashboard_stat_pois = PremiumStatCard("Deep Desert POIs", "—", "Shared tactical markers")
        self.dashboard_stat_items = PremiumStatCard("Items Tracked", "—", "Market catalog")
        for idx, card in enumerate([self.dashboard_guild_identity_card, self.dashboard_stat_members, self.dashboard_stat_bases, self.dashboard_stat_pois, self.dashboard_stat_items]):
            self.stat_grid.addWidget(card, 0, idx)
        # Dashboard stat cards are quick links.
        self.dashboard_stat_bases.setCursor(Qt.PointingHandCursor)
        self.dashboard_stat_pois.setCursor(Qt.PointingHandCursor)
        self.dashboard_stat_items.setCursor(Qt.PointingHandCursor)
        self.dashboard_stat_bases.mousePressEvent = lambda event: self.set_page(3) if event.button() == Qt.LeftButton else None
        self.dashboard_stat_pois.mousePressEvent = lambda event: self.set_page(2) if event.button() == Qt.LeftButton else None
        self.dashboard_stat_items.mousePressEvent = lambda event: self.open_market_tab(0) if event.button() == Qt.LeftButton else None
        outer.addLayout(self.stat_grid)

        # Quick Links removed from dashboard; stat cards above remain clickable.


        actions_panel = QFrame()
        actions_panel.setObjectName("CommandCard")
        actions_layout = QVBoxLayout(actions_panel)
        actions_layout.setContentsMargins(16, 14, 16, 16)
        actions_layout.setSpacing(12)
        actions_title = QLabel("QUICK ACTIONS")
        actions_title.setObjectName("SectionTitle")
        actions_layout.addWidget(actions_title)
        actions_row = QGridLayout()
        actions_row.setSpacing(12)
        action_scan = QuickActionCard("◈", "Database", "Browse the item catalog")
        action_map = QuickActionCard("◎", "Deep Desert", "Open tactical POI map")
        action_market = QuickActionCard("▣", "Database", "Browse the item catalog")
        action_guild = QuickActionCard("◆", "Manage Guild", "Members, news, and links")
        action_sync = QuickActionCard("⚙", "Sync Settings", "Manual sync lives in Settings only")
        action_scan.clicked.connect(lambda: self.open_market_tab(0))
        action_map.clicked.connect(lambda: self.set_page(2))
        action_market.clicked.connect(lambda: self.open_market_tab(0))
        action_guild.clicked.connect(self.open_guild_admin_page)
        action_sync.clicked.connect(lambda: self.set_page(5))
        self.dashboard_guild_button = action_guild
        for idx, action in enumerate([action_scan, action_map, action_market, action_guild, action_sync]):
            actions_row.addWidget(action, 0, idx)
        actions_layout.addLayout(actions_row)
        actions_panel.setVisible(False)

        lower = QHBoxLayout()
        lower.setSpacing(14)

        market_panel = QFrame()
        market_panel.setObjectName("CommandCard")
        market_layout = QVBoxLayout(market_panel)
        market_layout.setContentsMargins(16, 14, 16, 16)
        market_title = QLabel("EVENTS")
        market_title.setObjectName("SectionTitle")
        event_add = QPushButton("Add Event")
        event_add.clicked.connect(self.submit_guild_event)
        market_header = QHBoxLayout()
        market_header.addWidget(market_title, 1)
        market_header.addWidget(event_add)
        market_layout.addLayout(market_header)
        dashboard_events_note = QLabel("Times shown in Central Time (CT).")
        dashboard_events_note.setObjectName("MutedLabel")
        market_layout.addWidget(dashboard_events_note)
        self.dashboard_events_cards = QVBoxLayout()
        self.dashboard_events_cards.setSpacing(10)
        market_layout.addLayout(self.dashboard_events_cards)
        market_layout.addStretch()

        news_panel = QFrame()
        news_panel.setObjectName("CommandCard")
        news_layout = QVBoxLayout(news_panel)
        news_layout.setContentsMargins(16, 14, 16, 16)
        news_header = QHBoxLayout()
        news_title = QLabel("GUILD ANNOUNCEMENTS")
        news_title.setObjectName("SectionTitle")
        view_guild = QPushButton("Open Guild")
        view_guild.clicked.connect(self.open_guild_admin_page)
        news_header.addWidget(news_title, 1)
        news_header.addWidget(view_guild)
        news_layout.addLayout(news_header)
        self.dashboard_news_cards = QVBoxLayout()
        self.dashboard_news_cards.setSpacing(10)
        news_layout.addLayout(self.dashboard_news_cards)
        news_layout.addStretch()

        links_panel = QFrame()
        links_panel.setObjectName("CommandCard")
        links_layout = QVBoxLayout(links_panel)
        links_layout.setContentsMargins(16, 14, 16, 16)
        links_header = QHBoxLayout()
        links_title = QLabel("HELPFUL LINKS")
        links_title.setObjectName("SectionTitle")
        links_header.addWidget(links_title, 1)
        links_layout.addLayout(links_header)
        self.dashboard_link_cards = QVBoxLayout()
        self.dashboard_link_cards.setSpacing(10)
        links_layout.addLayout(self.dashboard_link_cards)
        links_layout.addStretch()

        upcoming_panel = QFrame()
        upcoming_panel.setObjectName("CommandCard")
        upcoming_layout = QVBoxLayout(upcoming_panel)
        upcoming_layout.setContentsMargins(16, 14, 16, 16)
        upcoming_title = QLabel("UPCOMING")
        upcoming_title.setObjectName("SectionTitle")
        upcoming_layout.addWidget(upcoming_title)
        # Guild identity is now displayed left of the Guild Members card.
        self.dashboard_reset_card = PremiumStatCard("Tuesday Reset", "—", "Deep Desert rotation")
        self.dashboard_scan_card = PremiumStatCard("Last Scan", "Ready", "Scanner standby")
        upcoming_layout.addWidget(self.dashboard_reset_card)
        upcoming_layout.addWidget(self.dashboard_scan_card)
        upcoming_layout.addStretch()

        # Hidden compatibility tables keep existing double-click/detail methods and refresh paths intact.
        self.dashboard_links_table = StankyTable(["Title", "URL", "Poster"])
        self.news_table = StankyTable(["Latest News", "Date"])
        self.dashboard_events_table = StankyTable(["Event", "Time (Central)", "Status", "Attending", "Interested"])
        self.dashboard_links_table.hide()
        self.news_table.hide()
        self.dashboard_events_table.hide()
        self.dashboard_links_table.cellDoubleClicked.connect(self.show_dashboard_link_detail)
        self.news_table.cellDoubleClicked.connect(self.show_dashboard_news_detail)
        self.dashboard_events_table.cellDoubleClicked.connect(self.show_dashboard_event_detail)

        lower.addWidget(market_panel, 3)
        lower.addWidget(news_panel, 4)
        lower.addWidget(links_panel, 4)
        upcoming_panel.setVisible(False)
        outer.addLayout(lower, 1)
        return page

    def _build_market_page(self) -> QWidget:
        """Database/Catalog page only.

        The Auction House terminal and scanner are intentionally hidden until
        there is a proper auction tracker solution. This page now focuses only
        on the Game8-backed item catalog with cached images.
        """
        page, layout = self._page_shell("Database", "Game8 item database with local cached images.")
        controls = QHBoxLayout()
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("Search item name...")
        self.catalog_search.textChanged.connect(self.refresh_catalog)
        self.catalog_category = QComboBox()
        self.catalog_category.currentTextChanged.connect(self.refresh_catalog)
        self.catalog_import_button = QPushButton("Import Game8 Catalog")
        self.catalog_import_button.clicked.connect(self.import_catalog)
        self.catalog_delete_local_button = QPushButton("Delete Local Catalog")
        self.catalog_delete_local_button.setObjectName("DangerButton")
        self.catalog_delete_local_button.clicked.connect(self.delete_local_catalog)
        controls.addWidget(self.catalog_search, 2)
        controls.addWidget(self.catalog_category, 1)
        controls.addWidget(self.catalog_import_button)
        controls.addWidget(self.catalog_delete_local_button)
        layout.addLayout(controls)

        self.catalog_import_status = QLabel("Ready.")
        self.catalog_import_status.setStyleSheet("color:#9f8150;")
        self.catalog_import_progress = QProgressBar()
        self.catalog_import_progress.setRange(0, 1)
        self.catalog_import_progress.setValue(0)
        self.catalog_import_progress.setVisible(False)

        self.catalog_images_notice = QLabel(
            "Catalog data and item images import directly from Game8. Auction terminal and scanner are hidden until a proper auction tracker is ready."
        )
        self.catalog_images_notice.setWordWrap(True)
        self.catalog_images_notice.setObjectName("MutedText")
        if self._catalog_image_count() > 0:
            self.catalog_images_notice.setVisible(False)

        layout.addWidget(self.catalog_images_notice)
        layout.addWidget(self.catalog_import_status)
        layout.addWidget(self.catalog_import_progress)
        self.catalog_table = StankyTable(["Image", "Name", "Category"] )
        self.catalog_table.setIconSize(QSize(72, 72))
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.catalog_table.cellDoubleClicked.connect(self.open_catalog_item)
        layout.addWidget(self.catalog_table, 1)
        return page

    def _build_catalog_page(self) -> QWidget:
        page, layout = self._page_shell("Catalog", "Trusted item database.")
        controls = QHBoxLayout()
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("Search item name...")
        self.catalog_search.textChanged.connect(self.refresh_catalog)
        self.catalog_category = QComboBox()
        self.catalog_category.currentTextChanged.connect(self.refresh_catalog)
        self.catalog_import_button = QPushButton("Import Game8 Catalog")
        self.catalog_import_button.clicked.connect(self.import_catalog)
        self.catalog_delete_local_button = QPushButton("Delete Local Catalog")
        self.catalog_delete_local_button.setObjectName("DangerButton")
        self.catalog_delete_local_button.clicked.connect(self.delete_local_catalog)
        controls.addWidget(self.catalog_search, 2)
        controls.addWidget(self.catalog_category, 1)
        controls.addWidget(self.catalog_import_button)
        controls.addWidget(self.catalog_delete_local_button)
        layout.addLayout(controls)
        self.catalog_import_status = QLabel("Ready.")
        self.catalog_import_status.setStyleSheet("color:#9f8150;")
        self.catalog_import_progress = QProgressBar()
        self.catalog_import_progress.setRange(0, 1)
        self.catalog_import_progress.setValue(0)
        self.catalog_import_progress.setVisible(False)

        self.catalog_images_notice = QLabel(
            "Catalog data and item images now import directly from Game8. GitHub catalog importing has been removed."
        )
        self.catalog_images_notice.setWordWrap(True)
        self.catalog_images_notice.setObjectName("MutedText")
        if self._catalog_image_count() > 0:
            self.catalog_images_notice.setVisible(False)

        layout.addWidget(self.catalog_images_notice)
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
        page, layout = self._page_shell("Deep Desert", "Simple native map with one-click guild POI placement.")

        self.live_deep_desert = LiveDeepDesertView()
        self.live_deep_desert.add_poi_callback = self.add_poi_at
        self.live_deep_desert.add_base_callback = self.add_deep_desert_base_at
        self.map_view = self.live_deep_desert.canvas
        layout.addWidget(self.live_deep_desert, 1)

        self.dd_base_table = self.live_deep_desert.marker_table
        self.dd_archive_table = self.live_deep_desert.archive_table
        self.dd_archive_toggle = self.live_deep_desert.archive_toggle
        self.map_view.markerSelected.connect(self.select_deep_desert_marker_from_map)
        self.dd_base_table.cellClicked.connect(self.center_on_deep_desert_marker)
        self.dd_base_table.cellDoubleClicked.connect(self.center_on_deep_desert_marker)
        self.dd_base_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dd_base_table.customContextMenuRequested.connect(self.show_deep_desert_marker_context_menu)
        self.dd_archive_table.cellClicked.connect(self.center_on_deep_desert_archive_marker)
        self.dd_archive_table.cellDoubleClicked.connect(self.center_on_deep_desert_archive_marker)
        self.dd_archive_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dd_archive_table.customContextMenuRequested.connect(self.show_deep_desert_archive_context_menu)

        # Hidden backing table keeps the existing edit/delete/context-menu code working,
        # while the user-facing Deep Desert page stays focused on the map itself.
        self.poi_table = StankyTable(["Type", "Status", "Note"])
        self.poi_table.setVisible(False)
        self.poi_table.cellClicked.connect(self.center_on_poi)
        self.poi_table.cellDoubleClicked.connect(self.center_on_poi)
        self.poi_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.poi_table.customContextMenuRequested.connect(self.show_poi_context_menu)
        self.poi_sync_status = QLabel("Auto-sync enabled")
        self.poi_sync_status.setVisible(False)
        layout.addWidget(self.poi_table)
        layout.addWidget(self.poi_sync_status)
        return page

    def _build_hagga_basin_page(self) -> QWidget:
        page, layout = self._page_shell("Hagga Basin", "Guild base map and sietch locations.")
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
        hint = QLabel("Double-click the Hagga Basin map to place a guild base. Each member gets their own color. Add a custom title and note when saving.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9f8150;")
        base_layout.addWidget(hint)

        self.base_table = StankyTable(["Member", "Sietch", "Status"])
        self.base_table.cellClicked.connect(self.center_on_base)
        self.base_table.cellDoubleClicked.connect(self.center_on_base)
        self.base_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.base_table.customContextMenuRequested.connect(self.show_base_context_menu)
        self.base_table.setMaximumWidth(560)
        self.base_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.base_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.base_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
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
        self.base_sync_status = QLabel("Auto-sync is enabled. Base marker changes sync immediately after save.")
        self.base_sync_status.setStyleSheet("color:#9f8150;")
        base_layout.addWidget(self.base_sync_status)

        body.addWidget(self.hagga_map_view, 3)
        body.addWidget(base_panel, 1)
        layout.addLayout(body, 1)
        return page

    def _build_guild_page(self) -> QWidget:
        page, layout = self._page_shell("Guild Command", "Events, announcements, helpful links, roster, and officer operations.")

        banner = QFrame()
        banner.setObjectName("HeroBanner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 20, 24, 20)
        banner_layout.setSpacing(18)

        logo = QLabel()
        self.guild_page_logo = logo
        logo.setFixedSize(86, 86)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("border:1px solid rgba(214,174,90,0.45); border-radius:14px; background:rgba(0,0,0,0.35);")
        logo_path = resolve_local_path(db.get_setting("guild_logo_path", ""))
        if logo_path.exists():
            _logo_pix = QPixmap(str(logo_path))
            if not _logo_pix.isNull():
                logo.setPixmap(_logo_pix.scaled(78, 78, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo.setText("GW")
        else:
            logo.setText("GW")
            logo.setStyleSheet(logo.styleSheet() + " color:#D6AE5A; font-size:24px; font-weight:900;")

        title_block = QVBoxLayout()
        title = QLabel((db.get_setting("guild_name", "No Guild") or "No Guild").upper())
        self.guild_page_title = title
        title.setObjectName("HeroTitle")
        subtitle = QLabel("TACTICAL GUILD OPERATIONS")
        subtitle.setObjectName("MicroLabel")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addStretch()

        role = StatusPill("Guild Role", db.get_setting("guild_role", "member") or "member", icon_path=str(asset_path("role_icon.png")))
        code = StatusPill("Join Code", db.get_setting("guild_code", "—") or "—", icon_path=str(asset_path("code_icon.png")))
        role.setMinimumWidth(320)
        code.setMinimumWidth(390)
        role.setStyleSheet("QFrame { border: 1px solid rgba(214,174,90,0.75); border-radius: 14px; background: rgba(214,174,90,0.12); } QLabel { font-size: 18px; font-weight: 950; }")
        code.setStyleSheet("QFrame { border: 1px solid rgba(214,174,90,0.75); border-radius: 14px; background: rgba(214,174,90,0.12); } QLabel { font-size: 18px; font-weight: 950; }")
        self.guild_page_role_pill = role
        self.guild_page_code_pill = code
        banner_layout.addWidget(logo)
        banner_layout.addLayout(title_block, 1)
        banner_layout.addWidget(role)
        banner_layout.addWidget(code)
        layout.addWidget(banner)

        admin_actions = QHBoxLayout()
        admin_actions.setSpacing(10)
        guild_roster = QPushButton("View Roster")
        guild_roster.setObjectName("PrimaryButton")
        guild_roster.clicked.connect(self.show_members_roles_dialog)
        guild_add_event = QPushButton("Add Event")
        guild_add_event.setObjectName("PrimaryButton")
        guild_add_event.clicked.connect(self.submit_guild_event)
        guild_add_announcement = QPushButton("Add Announcement")
        guild_add_announcement.setObjectName("PrimaryButton")
        guild_add_announcement.clicked.connect(self.submit_guild_news)
        guild_add_link = QPushButton("Add Helpful Link")
        guild_add_link.setObjectName("PrimaryButton")
        guild_add_link.clicked.connect(self.add_guild_link)
        guild_upload_logo = QPushButton("Upload Logo")
        guild_upload_logo.clicked.connect(self.upload_guild_logo)
        admin_actions.addWidget(guild_roster)
        admin_actions.addWidget(guild_add_event)
        admin_actions.addWidget(guild_add_announcement)
        admin_actions.addWidget(guild_add_link)
        admin_actions.addWidget(guild_upload_logo)
        admin_actions.addStretch()
        layout.addLayout(admin_actions)

        tabs = QTabWidget()
        tabs.setObjectName("GuildAdminTabs")

        # EVENTS TAB
        events_panel = QFrame()
        events_panel.setObjectName("Panel")
        events_layout = QVBoxLayout(events_panel)
        events_layout.setContentsMargins(18, 18, 18, 18)
        events_layout.setSpacing(12)
        events_title = QLabel("EVENTS")
        events_title.setObjectName("SectionTitle")
        events_layout.addWidget(events_title)
        events_time_note = QLabel("All event times are listed in Central Time (CT). Right-click an event to mark Attending, Interested, remove your response, view responses, or open details.")
        events_time_note.setObjectName("MutedLabel")
        events_time_note.setWordWrap(True)
        events_layout.addWidget(events_time_note)
        self.guild_page_events = StankyTable(["Event", "Time (Central)", "Status", "Attending", "Interested", "Read More"])
        self.guild_page_events.setWordWrap(True)
        self.guild_page_events.verticalHeader().setDefaultSectionSize(66)
        self.guild_page_events.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.guild_page_events.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.guild_page_events.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.guild_page_events.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.guild_page_events.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.guild_page_events.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.guild_page_events.cellDoubleClicked.connect(self.show_guild_event_detail)
        self.guild_page_events.setContextMenuPolicy(Qt.CustomContextMenu)
        self.guild_page_events.customContextMenuRequested.connect(self.show_guild_event_context_menu)
        events_layout.addWidget(self.guild_page_events, 1)
        event_buttons = QHBoxLayout()
        add_event = QPushButton("Add Event")
        add_event.setObjectName("PrimaryButton")
        add_event.clicked.connect(self.submit_guild_event)
        attending_event = QPushButton("✅ Attending")
        attending_event.setToolTip("Mark yourself as attending this guild event")
        attending_event.setObjectName("PrimaryButton")
        attending_event.clicked.connect(lambda: self.set_selected_event_response("attending"))
        interested_event = QPushButton("⭐ Interested")
        interested_event.setToolTip("Mark yourself as interested without committing")
        interested_event.setObjectName("PrimaryButton")
        interested_event.clicked.connect(lambda: self.set_selected_event_response("interested"))
        not_attending_event = QPushButton("❌ Remove Response")
        not_attending_event.setToolTip("Clear your event response")
        not_attending_event.clicked.connect(lambda: self.set_selected_event_response(""))
        attendees_event = QPushButton("View Responses")
        attendees_event.clicked.connect(self.show_selected_event_attendees)
        delete_event = QPushButton("Delete Selected")
        delete_event.clicked.connect(self.delete_selected_guild_event)
        event_buttons.addWidget(add_event)
        event_buttons.addWidget(attending_event)
        event_buttons.addWidget(interested_event)
        event_buttons.addWidget(not_attending_event)
        event_buttons.addWidget(attendees_event)
        event_buttons.addWidget(delete_event)
        event_buttons.addStretch()
        events_layout.addLayout(event_buttons)
        tabs.addTab(events_panel, "Events")

        # ANNOUNCEMENTS TAB
        news_panel = QFrame()
        news_panel.setObjectName("Panel")
        news_layout = QVBoxLayout(news_panel)
        news_layout.setContentsMargins(18, 18, 18, 18)
        news_layout.setSpacing(12)
        news_title = QLabel("ANNOUNCEMENTS")
        news_title.setObjectName("SectionTitle")
        news_layout.addWidget(news_title)
        news_note = QLabel("Post guild announcements for every member. Double-click or right-click an announcement to read it.")
        news_note.setObjectName("MutedLabel")
        news_note.setWordWrap(True)
        news_layout.addWidget(news_note)
        self.guild_page_news = StankyTable(["Announcement", "Posted", "Read More"])
        self.guild_page_news.setWordWrap(True)
        self.guild_page_news.verticalHeader().setDefaultSectionSize(62)
        self.guild_page_news.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.guild_page_news.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.guild_page_news.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.guild_page_news.cellDoubleClicked.connect(self.show_guild_news_detail)
        self.guild_page_news.setContextMenuPolicy(Qt.CustomContextMenu)
        self.guild_page_news.customContextMenuRequested.connect(self.show_guild_news_context_menu)
        news_layout.addWidget(self.guild_page_news, 1)
        news_buttons = QHBoxLayout()
        add_news = QPushButton("Add Announcement")
        add_news.setObjectName("PrimaryButton")
        add_news.clicked.connect(self.submit_guild_news)
        read_news = QPushButton("Open Selected")
        read_news.clicked.connect(lambda: self.show_guild_news_detail(self.guild_page_news.currentRow(), 0))
        delete_news = QPushButton("Delete Selected")
        delete_news.clicked.connect(self.delete_selected_guild_news)
        news_buttons.addWidget(add_news)
        news_buttons.addWidget(read_news)
        news_buttons.addWidget(delete_news)
        news_buttons.addStretch()
        news_layout.addLayout(news_buttons)
        tabs.addTab(news_panel, "Announcements")

        # HELPFUL LINKS TAB
        links_panel = QFrame()
        links_panel.setObjectName("Panel")
        links_layout = QVBoxLayout(links_panel)
        links_layout.setContentsMargins(18, 18, 18, 18)
        links_layout.setSpacing(12)
        links_title = QLabel("HELPFUL LINKS")
        links_title.setObjectName("SectionTitle")
        links_layout.addWidget(links_title)
        links_note = QLabel("Pinned guild resources, maps, spreadsheets, builds, Discord posts, or other useful links.")
        links_note.setObjectName("MutedLabel")
        links_note.setWordWrap(True)
        links_layout.addWidget(links_note)
        self.guild_page_links = StankyTable(["Title", "URL", "Added By"])
        self.guild_page_links.setWordWrap(True)
        self.guild_page_links.verticalHeader().setDefaultSectionSize(58)
        self.guild_page_links.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guild_page_links.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.guild_page_links.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.guild_page_links.cellDoubleClicked.connect(self.open_selected_guild_link)
        self.guild_page_links.setContextMenuPolicy(Qt.CustomContextMenu)
        self.guild_page_links.customContextMenuRequested.connect(self.show_guild_link_context_menu)
        links_layout.addWidget(self.guild_page_links, 1)
        link_buttons = QHBoxLayout()
        add_link = QPushButton("Add Helpful Link")
        add_link.setObjectName("PrimaryButton")
        add_link.clicked.connect(self.add_guild_link)
        open_link = QPushButton("Open Selected")
        open_link.clicked.connect(lambda: self.open_selected_guild_link(self.guild_page_links.currentRow(), 0))
        edit_link = QPushButton("Edit Selected")
        edit_link.clicked.connect(self.edit_guild_link)
        delete_link = QPushButton("Delete Selected")
        delete_link.clicked.connect(self.delete_guild_link)
        link_buttons.addWidget(add_link)
        link_buttons.addWidget(open_link)
        link_buttons.addWidget(edit_link)
        link_buttons.addWidget(delete_link)
        link_buttons.addStretch()
        links_layout.addLayout(link_buttons)
        tabs.addTab(links_panel, "Helpful Links")

        # ACTIVITY TAB
        activity_panel = QFrame()
        activity_panel.setObjectName("Panel")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(18, 18, 18, 18)
        activity_layout.setSpacing(12)
        activity_title = QLabel("ACTIVITY")
        activity_title.setObjectName("SectionTitle")
        activity_layout.addWidget(activity_title)
        activity_note = QLabel("Recent guild changes and sync activity.")
        activity_note.setObjectName("MutedLabel")
        activity_note.setWordWrap(True)
        activity_layout.addWidget(activity_note)
        self.guild_page_activity = StankyTable(["Date", "Actor", "Activity"])
        self.guild_page_activity.setWordWrap(True)
        self.guild_page_activity.verticalHeader().setDefaultSectionSize(52)
        self.guild_page_activity.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guild_page_activity.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.guild_page_activity.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        activity_layout.addWidget(self.guild_page_activity, 1)
        tabs.addTab(activity_panel, "Activity")

        layout.addWidget(tabs, 1)
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

        info = QLabel("Guild identity is managed from the Guild menu. Use Join Guild or Create Guild when you are ready.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#d8c098; font-weight:750;")
        p.addWidget(info)

        row = QHBoxLayout()
        self.join_guild_button = QPushButton("Join Guild")
        self.join_guild_button.setObjectName("PrimaryButton")
        self.join_guild_button.clicked.connect(self.prompt_join_guild)
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

        sync_panel = QFrame()
        sync_panel.setObjectName("Card")
        sync_layout = QVBoxLayout(sync_panel)
        sync_layout.setContentsMargins(16, 14, 16, 14)
        sync_title = QLabel("SYNCHRONIZATION")
        sync_title.setObjectName("CardTitle")
        sync_layout.addWidget(sync_title)
        self.settings_sync_status = QLabel("Guild Sync: Manual from Dashboard or queued after your own changes only.")
        self.settings_sync_status.setStyleSheet("color:#e0b65c; font-weight:800;")
        self.settings_last_sync = QLabel("Last Sync: " + db.get_setting("last_manual_sync", "Not yet synced"))
        self.settings_last_sync.setStyleSheet("color:#9f8150;")
        sync_buttons = QHBoxLayout()
        sync_now = QPushButton("Sync All Now")
        sync_now.setObjectName("PrimaryButton")
        sync_now.clicked.connect(self.settings_manual_sync_all)
        sync_buttons.addWidget(sync_now)
        sync_buttons.addStretch()
        sync_layout.addWidget(self.settings_sync_status)
        sync_layout.addWidget(self.settings_last_sync)
        sync_layout.addLayout(sync_buttons)
        p.addWidget(sync_panel)

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

        support_panel = QFrame()
        support_panel.setObjectName("Card")
        support_layout = QVBoxLayout(support_panel)
        support_layout.setContentsMargins(16, 14, 16, 14)
        support_title = QLabel("SUPPORT")
        support_title.setObjectName("CardTitle")
        support_buttons = QHBoxLayout()
        submit_ideas = QPushButton("Submit Ideas")
        submit_ideas.setObjectName("PrimaryButton")
        submit_ideas.clicked.connect(self.submit_idea_feedback)
        donate = QPushButton("Donate")
        donate.clicked.connect(self.open_donate_dialog)
        support_buttons.addWidget(submit_ideas)
        support_buttons.addWidget(donate)
        support_buttons.addStretch()
        support_layout.addWidget(support_title)
        support_layout.addLayout(support_buttons)
        p.addWidget(support_panel)

        p.addStretch()
        layout.addWidget(panel)
        layout.addStretch()
        return page


    def _specialization_values_dialog(self, display_name: str, guild_code: str):
        current = db.get_member_specializations(guild_code, display_name)
        dlg = QDialog(self)
        dlg.setWindowTitle("Member Specializations")
        dlg.setMinimumWidth(440)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 20, 22, 20)
        title = QLabel(f"SPECIALIZATIONS — {display_name}")
        title.setObjectName("DialogHeader")
        layout.addWidget(title)
        info = QLabel("Set each level up to 100. Level 100 shows a star in the guild list.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#d8c098; font-weight:750;")
        layout.addWidget(info)
        form = QFormLayout()
        spins = {}
        specialization_order = [
            ("crafting", "Crafting"),
            ("gathering", "Gathering"),
            ("exploration", "Exploration"),
            ("combat", "Combat"),
            ("sabotage", "Sabatoge"),
        ]
        for key, label in specialization_order:
            spin = QSpinBox()
            spin.setRange(1, 100)
            spin.setValue(int(current.get(key, 1)))
            # Keep the 1-100 limit, but do not show a visible "1 / 100" style suffix.
            spin.setSuffix("")
            spins[key] = spin
            form.addRow(label, spin)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        save = QPushButton("Save")
        save.setObjectName("PrimaryButton")
        cancel.clicked.connect(dlg.reject)
        save.clicked.connect(dlg.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        if dlg.exec() != QDialog.Accepted:
            return False
        values = {
            "combat": spins["combat"].value(),
            "exploration": spins["exploration"].value(),
            "crafting": spins["crafting"].value(),
            "gathering": spins["gathering"].value(),
            "sabotage": spins["sabotage"].value(),
        }
        db.upsert_member_specializations(
            guild_code, display_name,
            values["combat"], values["exploration"], values["crafting"], values["gathering"], values["sabotage"],
        )
        url, key = active_supabase()
        guild = (guild_code or "").strip().upper()
        if url and key and guild and display_name and "PASTE_" not in key:
            try:
                payload = [{"guild_code": guild, "display_name": display_name.strip(), **values}]
                supabase_request("POST", url, key, "member_specializations?on_conflict=guild_code,display_name", payload)
                db.mark_member_specializations_synced(guild, display_name.strip())
            except Exception as exc:
                self.notify("Specializations Saved Locally", f"Remote sync failed and will retry: {str(exc)[:120]}", "warning", 4200)
        return True

    def edit_my_specializations(self):
        guild = db.get_setting("guild_code", "").upper()
        name = db.get_setting("display_name", "").strip()
        if not guild or not name:
            self.notify("Specializations", "Join or create a guild first.", "warning")
            return
        if self._specialization_values_dialog(name, guild):
            self.notify("Specializations Saved", "Your member levels were updated.", "success")
            self.queue_guild_sync("Specializations Saved", "Member specialization levels saved locally and queued for sync.")

    def show_member_specializations_dialog(self):
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            self.notify("Specializations", "Join or create a guild first.", "warning")
            return
        rows = db.list_member_specializations(guild)
        dlg = QDialog(self)
        dlg.setWindowTitle("Member Specializations")
        dlg.resize(860, 520)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 20, 22, 20)
        header = QLabel("MEMBER SPECIALIZATIONS")
        header.setObjectName("DialogHeader")
        layout.addWidget(header)
        table = StankyTable(["Member", "Role", "Crafting", "Gathering", "Exploration", "Combat", "Sabatoge"])
        table.setRowCount(len(rows))
        def fmt(v):
            v = int(v or 1)
            return f"⭐ {v}" if v >= 100 else str(v)
        for r, row in enumerate(rows):
            vals = [row["display_name"], row["role"], fmt(row["crafting"]), fmt(row["gathering"]), fmt(row["exploration"]), fmt(row["combat"]), fmt(row["sabotage"])]
            for c, value in enumerate(vals):
                item = QTableWidgetItem(str(value))
                if c >= 2 and str(value).startswith("⭐"):
                    item.setForeground(QColor("#D6AE5A"))
                    item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                table.setItem(r, c, item)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        layout.addWidget(table, 1)
        buttons = QHBoxLayout()
        edit_mine = QPushButton("Update My Levels")
        edit_mine.setObjectName("PrimaryButton")
        close = QPushButton("Close")
        edit_mine.clicked.connect(lambda: (dlg.accept(), self.edit_my_specializations()))
        close.clicked.connect(dlg.accept)
        buttons.addWidget(edit_mine)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dlg.exec()

    def submit_idea_feedback(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Submit Ideas")
        dlg.setMinimumWidth(560)
        layout = QVBoxLayout(dlg)
        title = QLabel("SUBMIT AN IDEA")
        title.setObjectName("DialogHeader")
        layout.addWidget(title)
        body = QTextEdit()
        body.setPlaceholderText("Tell us what you want added or improved...")
        body.setMinimumHeight(180)
        layout.addWidget(body)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Cancel")
        send = QPushButton("Submit")
        send.setObjectName("PrimaryButton")
        cancel.clicked.connect(dlg.reject)
        send.clicked.connect(dlg.accept)
        row.addWidget(cancel)
        row.addWidget(send)
        layout.addLayout(row)
        if dlg.exec() != QDialog.Accepted:
            return
        text = body.toPlainText().strip()
        if not text:
            self.notify("Submit Ideas", "Nothing was entered.", "warning")
            return
        # Email is intentionally not displayed in the UI. This opens the user's mail client with the recipient filled.
        recipient = base64.b64decode("dG9ueWFwcmlsZUBnbWFpbC5jb20=").decode("utf-8")
        subject = urllib.parse.quote("StankyTools Idea Submission")
        message = urllib.parse.quote(text)
        webbrowser.open(f"mailto:{recipient}?subject={subject}&body={message}")
        self.notify("Submit Ideas", "Your email app was opened with the idea ready to send.", "success")

    def open_donate_dialog(self):
        DetailDialog("Donate", "Donation link is not configured yet. Add your preferred donation URL in a future release and this button will open it directly.", self).exec()

    def settings_manual_sync_all(self):
        """Single user-facing manual sync entry point. Map and guild pages auto-sync on save."""
        if hasattr(self, "settings_sync_status"):
            self.settings_sync_status.setText("Manual Sync: Running...")
        QApplication.processEvents()
        try:
            self.manual_sync_all_markers()
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            db.set_setting("last_manual_sync", stamp)
            if hasattr(self, "settings_last_sync"):
                self.settings_last_sync.setText("Last Sync: " + stamp)
            if hasattr(self, "settings_sync_status"):
                self.settings_sync_status.setText("Guild Sync: Manual sync completed.")
            self.notify("Sync Complete", "All available guild, POI, and base data has been synced.", "success")
        except Exception as exc:
            if hasattr(self, "settings_sync_status"):
                self.settings_sync_status.setText("Manual Sync: Failed")
            self.notify("Sync Failed", str(exc), "error", 5200)

    def check_app_update(self):
        if hasattr(self, "update_status"):
            self.update_status.setText("Checking for updates...")
        self.notify("Updater", "Checking GitHub Releases...", "info", 2200)
        QApplication.processEvents()
        try:
            info = updater.check_for_update()
            if not info.update_available:
                if hasattr(self, "update_status"):
                    self.update_status.setText(f"StankyTools is current ({info.current_version}).")
                message = info.message or f"You are already on the latest version: {info.current_version}"
                self.notify("No Update", message, "info")
                return

            if hasattr(self, "update_status"):
                self.update_status.setText(f"Update available: {info.latest_version}")

            message = (
                f"A new StankyTools version is available.\n\n"
                f"Current: {info.current_version}\n"
                f"Latest: {info.latest_version}\n\n"
                "Choose a folder to download the update ZIP?"
            )
            if QMessageBox.question(self, "Update Available", message) != QMessageBox.Yes:
                return
            remembered = db.get_setting("update_download_folder", "")
            target_folder = QFileDialog.getExistingDirectory(self, "Choose Update Download Folder", remembered or str(Path.home() / "Downloads"))
            if not target_folder:
                return
            db.set_setting("update_download_folder", target_folder)

            progress = QProgressDialog("Downloading update...", "Cancel", 0, 100, self)
            progress.setWindowTitle("StankyTools Update")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            def set_progress_text(text: str):
                progress.setLabelText(text)
                if hasattr(self, "update_status"):
                    self.update_status.setText(text)
                QApplication.processEvents()

            set_progress_text("Downloading update...")

            def on_progress(done: int, total: int):
                if total > 0:
                    pct = max(0, min(100, int((done / total) * 100)))
                    progress.setValue(pct)
                    progress.setLabelText(f"Downloading update... {pct}%")
                QApplication.processEvents()
                if progress.wasCanceled():
                    raise RuntimeError("Update download canceled.")

            zip_path = updater.download_update(info, progress=on_progress, target_dir=Path(target_folder))
            progress.setValue(100)
            set_progress_text("Verifying package...")
            QApplication.processEvents()

            if hasattr(self, "update_status"):
                self.update_status.setText(f"Update downloaded to: {zip_path}")
            self.notify("Update Downloaded", f"Saved to {zip_path}", "success", 7000)
            try:
                if os.name == "nt":
                    os.startfile(str(Path(zip_path).parent))
                else:
                    webbrowser.open(Path(zip_path).parent.as_uri())
            except Exception:
                pass
            QMessageBox.information(
                self,
                "Update Downloaded",
                "The update ZIP was downloaded and validated.\n\n"
                f"Location:\n{zip_path}\n\n"
                "The folder has been opened so you can install it when ready."
            )
            return
        except Exception as exc:
            if hasattr(self, "update_status"):
                self.update_status.setText("Could not update StankyTools.")
            self.notify("Update Failed", str(exc), "error", 7000)
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

    def safe_refresh_dashboard(self):
        try:
            self.refresh_dashboard()
        except RuntimeError:
            # Some Qt widgets may have been rebuilt during navigation; never let
            # a dashboard stat refresh break map/catalog workflows.
            pass
        except Exception:
            pass

    def refresh_dashboard(self):
        # Do not destroy/recreate dashboard cards during refresh; they are long-lived
        # navigation widgets and other parts of the app keep safe references to them.
        guild = db.get_setting("guild_code", "").upper()
        # Dashboard is local-first. Do not pull remote data on every refresh.
        self.update_sidebar_status()
        if qt_alive(getattr(self, "dashboard_guild_name", None)):
            self.dashboard_guild_name.setText((db.get_setting("guild_name", "Guild") or "Guild") if guild else "Not in a Guild")
        if qt_alive(getattr(self, "dashboard_user", None)):
            self.dashboard_user.setText("Profile: " + (db.get_setting("display_name", "Not joined") or "Not joined"))
        if qt_alive(getattr(self, "dashboard_members", None)):
            members = getattr(self, "current_guild_members", None) or self.refresh_guild_members()
            self.dashboard_members.setText(f"Members: {len(members)}" if guild else "Members: —")
        if hasattr(self, "dashboard_guild_logo"):
            self.refresh_dashboard_guild_logo()
        stats = db.dashboard_stats()
        base_count = len(db.list_bases(guild)) if guild else 0
        members_count = len(getattr(self, "current_guild_members", []) or []) if guild else 0
        if hasattr(self, "dashboard_stat_members"):
            self.dashboard_stat_members.set_value(fmt_price(members_count), "Current roster")
            self.dashboard_stat_bases.set_value(fmt_price(base_count), "Hagga Basin operations")
            self.dashboard_stat_pois.set_value(fmt_price(stats.get("pois", 0)), "Shared tactical markers")
            self.dashboard_stat_items.set_value(fmt_price(stats.get("catalog_items", 0)), "Market catalog")
            if qt_alive(getattr(self, "dashboard_hero_guild", None)):
                labels = [lbl for lbl in self.dashboard_hero_guild.findChildren(QLabel) if qt_alive(lbl)]
                if labels:
                    labels[-1].setText((db.get_setting("guild_name", "Not Joined") or "Not Joined") if guild else "Not Joined")
            if qt_alive(getattr(self, "dashboard_sync_status", None)):
                self.dashboard_sync_status.setText("SYNC STATUS: ONLINE" if guild else "SYNC STATUS: LOCAL MODE")
            if hasattr(self, "dashboard_reset_card"):
                try:
                    meta = deep_desert.load_meta()
                    reset = str(meta.get("next_update", "Tuesday 7:15 AM"))
                except Exception:
                    reset = "Tuesday 7:15 AM"
                self.dashboard_reset_card.set_value("TUESDAY", reset)
        else:
            cards = [
                StatCard("Guild Members", fmt_price(members_count), "Current roster"),
                StatCard("Guild Bases", fmt_price(base_count), "Hagga Basin"),
                StatCard("Guild POIs", fmt_price(stats.get("pois", 0)), "Deep Desert markers"),
                StatCard("Items Tracked", fmt_price(stats.get("catalog_items", 0)), "Catalog database"),
            ]
            for i, card in enumerate(cards):
                self.stat_grid.addWidget(card, 0, i)
        self.refresh_dashboard_activity_tables()

    def refresh_guild_surfaces_after_identity_change(self, refresh_remote: bool = False):
        """Refresh every visible guild-aware surface after join/create/leave.

        This intentionally updates live widgets only and catches deleted Qt wrapper
        cases so a stale QLabel cannot make guild creation/join look failed.
        """
        def _call(fn):
            try:
                fn()
            except RuntimeError as exc:
                if "already deleted" not in str(exc):
                    raise
            except Exception:
                pass

        if refresh_remote:
            _call(lambda: self.sync_guild_dashboard_content(show_errors=False))
        _call(self.update_guild_nav_visibility)
        _call(self.update_sidebar_status)
        _call(self.update_guild_button_visibility)
        _call(self.refresh_guild_members)
        _call(self.refresh_guild_logo_widgets)
        _call(self.refresh_dashboard)
        _call(self.refresh_guild_page)
        _call(self.refresh_pois)
        _call(self.refresh_bases)

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
            table_row = self.market_table.rowCount() - 1
            for col in range(self.market_table.columnCount()):
                item = self.market_table.item(table_row, col)
                if item:
                    item.setData(Qt.UserRole + 10, int(row["item_id"] or 0))
                    item.setData(Qt.UserRole + 11, None if row["grade"] is None else int(row["grade"]))
        self.market_table.setSortingEnabled(True)
        self.market_table.setUpdatesEnabled(True)
        if self.market_table.rowCount() > 0 and self.market_table.currentRow() < 0:
            self.market_table.selectRow(0)
        self.update_market_terminal_details()

    def _csv_setting_values(self, key: str) -> set[str]:
        raw = db.get_setting(key, "") or ""
        return {part.strip() for part in raw.split(",") if part.strip()}

    def _set_csv_setting_values(self, key: str, values: set[str]):
        db.set_setting(key, ",".join(sorted(values)))

    def _selected_market_row_data(self):
        if not hasattr(self, "market_table") or self.market_table.currentRow() < 0:
            return None
        item = self.market_table.item(self.market_table.currentRow(), 0)
        if not item:
            return None
        item_id = item.data(Qt.UserRole + 10)
        grade = item.data(Qt.UserRole + 11)
        for row in getattr(self, "current_market_rows", []):
            try:
                if int(row["item_id"] or 0) == int(item_id or 0) and (None if row["grade"] is None else int(row["grade"])) == grade:
                    return row
            except Exception:
                continue
        return None

    def update_market_terminal_details(self):
        if not hasattr(self, "market_item_name"):
            return
        row = self._selected_market_row_data()
        if not row:
            self.market_item_name.setText("Select an item")
            self.market_item_meta.setText("Market details will appear here.")
            for card in [self.market_stat_current, self.market_stat_average, self.market_stat_supply, self.market_stat_profit]:
                card.set_value("—")
            self.market_history_graph.set_points([])
            self.market_item_image.clear()
            return
        item_id = int(row["item_id"] or 0)
        grade = "No Grade" if row["grade"] is None else f"Grade {row['grade']}"
        self.market_item_name.setText(str(row["name"] or "Item").upper())
        self.market_item_meta.setText(f"{row['category']} • {grade} • Last updated {row['last_seen'] or '—'}")
        self.market_stat_current.set_value(fmt_price(row["low_price"]), "Lowest observed")
        self.market_stat_average.set_value(fmt_price(row["avg_price"]), "Average observed")
        self.market_stat_supply.set_value(str(row["seen_count"] or 0), "Recorded listings")
        profit = int(row["high_price"] or 0) - int(row["low_price"] or 0)
        self.market_stat_profit.set_value(fmt_price(profit), "High minus low")
        catalog_rows = [r for r in db.list_catalog(row["name"], row["category"]) if int(r["id"]) == item_id]
        if catalog_rows:
            pix = catalog_image_pixmap(catalog_rows[0]["image_path"] if "image_path" in catalog_rows[0].keys() else "", 210)
            self.market_item_image.setPixmap(pix)
        history = db.price_history(item_id)
        self.market_history_graph.set_points([int(h["price"] or 0) for h in history])
        watch = self._csv_setting_values("market_watchlist")
        fav = self._csv_setting_values("market_favorites")
        self.market_watchlist_btn.setText("Remove Watch" if str(item_id) in watch else "Add Watchlist")
        self.market_favorite_btn.setText("Unfavorite" if str(item_id) in fav else "Favorite")

    def toggle_selected_watchlist(self):
        row = self._selected_market_row_data()
        if not row:
            return
        key = str(int(row["item_id"] or 0))
        values = self._csv_setting_values("market_watchlist")
        values.remove(key) if key in values else values.add(key)
        self._set_csv_setting_values("market_watchlist", values)
        self.update_market_terminal_details()

    def toggle_selected_favorite(self):
        row = self._selected_market_row_data()
        if not row:
            return
        key = str(int(row["item_id"] or 0))
        values = self._csv_setting_values("market_favorites")
        values.remove(key) if key in values else values.add(key)
        self._set_csv_setting_values("market_favorites", values)
        self.update_market_terminal_details()

    def selected_market_item_id(self) -> tuple[int, str] | None:
        row = self._selected_market_row_data() if hasattr(self, "_selected_market_row_data") else None
        if row:
            return int(row["item_id"] or 0), str(row["name"] or "Item")
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

        source = str(item["source_url"] or "")
        if source.startswith("dune-data-engine://"):
            try:
                from . import dune_api
                detail = dune_api.get_item_by_name(str(item["name"] or ""))
                body = dune_api.format_item_detail(detail or {})
            except Exception as exc:
                body = f"Dune Data Engine detail unavailable.\n\n{exc}"
            dlg = DetailDialog(str(item["name"] or "Dune Item"), body, self, meta=str(item["category"] or "Dune Data"))
            dlg.exec()
            return

        if source:
            webbrowser.open(source)

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
        desc_text = ""
        try:
            if "description" in item.keys():
                desc_text = str(item["description"] or "")
        except Exception:
            desc_text = ""
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color:#f3ead6; font-size:14px; padding: 8px 18px;")
        desc.setVisible(bool(desc_text))
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        layout.addWidget(title)
        layout.addWidget(image_label, 1)
        layout.addWidget(meta)
        layout.addWidget(desc)
        layout.addWidget(close, alignment=Qt.AlignCenter)
        dlg.exec()

    def delete_local_catalog(self):
        """Delete every local catalog record and all locally cached catalog artwork.

        This deliberately leaves guild data, map intel, announcements, events,
        helpful links, settings, and downloaded videos untouched. After this
        runs the catalog page should be completely empty until the user imports
        the catalog again from GitHub.
        """
        message = (
            "This will delete every local catalog listing, saved price observation, search/cache file, "
            "and downloaded catalog image on this PC.\n\n"
            "Guild data, bases, Deep Desert intel, announcements, events, helpful links, settings, "
            "and videos will be kept.\n\n"
            "To restore catalog listings later, use Import Game8 Catalog from the Catalog section."
        )
        if QMessageBox.question(self, "Delete Local Catalog", message) != QMessageBox.Yes:
            return

        # Clear visible widgets immediately so stale in-memory rows do not remain on screen.
        self.current_catalog_rows = []
        if hasattr(self, "catalog_table") and _qt_alive(self.catalog_table):
            self.catalog_table.setSortingEnabled(False)
            self.catalog_table.setRowCount(0)
            self.catalog_table.setSortingEnabled(True)
        if hasattr(self, "scan_item") and _qt_alive(self.scan_item):
            self.scan_item.clear()

        try:
            db.clear_local_catalog()
        except Exception as exc:
            self.notify("Catalog Delete Failed", str(exc), "error")
            return

        # Remove all catalog artwork and catalog-only cache files from persistent user storage.
        try:
            targets = [
                local_app_data_dir() / "item_images",
                data_dir() / "catalog",
                data_dir() / "catalog_cache",
                data_dir() / "catalog_import_report.json",
                local_app_data_dir() / "item_images.zip",
            ]
            for target in targets:
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                elif target.exists():
                    try:
                        target.unlink()
                    except Exception:
                        pass
            img_dir = local_app_data_dir() / "item_images"
            img_dir.mkdir(parents=True, exist_ok=True)
            (img_dir / ".gitkeep").touch(exist_ok=True)

            # Clear catalog thumbnail cache if present.
            try:
                global _CATALOG_PIXMAP_CACHE
                _CATALOG_PIXMAP_CACHE.clear()
            except Exception:
                pass
        except Exception:
            pass

        db.set_setting("catalog_images_prompt_dismissed", "")
        db.set_setting("catalog_imported_once", "")
        db.set_setting("catalog_force_github_reimport", "1")

        self.refresh_catalog_categories()
        self.refresh_catalog()
        self.refresh_scan_categories()
        self.safe_refresh_dashboard()
        if hasattr(self, "catalog_images_notice") and _qt_alive(self.catalog_images_notice):
            self.catalog_images_notice.setVisible(True)
        if hasattr(self, "catalog_import_status") and _qt_alive(self.catalog_import_status):
            self.catalog_import_status.setText("Catalog deleted. Use Import Game8 Catalog to rebuild from Game8 only.")
        self.notify("Catalog Deleted", "All local catalog listings and images were removed.", "success")


    def _catalog_image_count(self) -> int:
        folder = local_app_data_dir() / "item_images"
        if not folder.exists():
            return 0
        return sum(1 for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})

    def prompt_catalog_images_if_missing(self):
        """Catalog image imports are intentionally handled inside Market/Catalog only."""
        try:
            if hasattr(self, "catalog_images_notice"):
                self.catalog_images_notice.setVisible(self._catalog_image_count() == 0)
        except Exception:
            return

    def import_catalog_images_from_github(self):
        if getattr(self, "catalog_images_worker", None) is not None and self.catalog_images_worker.isRunning():
            QMessageBox.information(self, "Import Running", "Catalog image import is already running.")
            return
        url = db.get_setting("catalog_images_zip_url", DEFAULT_CATALOG_IMAGES_ZIP_URL)
        url, ok = QInputDialog.getText(
            self,
            "Import Images from GitHub",
            "GitHub catalog_images.zip URL:",
            text=url,
        )
        if not ok:
            return
        url = url.strip() or DEFAULT_CATALOG_IMAGES_ZIP_URL
        db.set_setting("catalog_images_zip_url", url)
        self.catalog_images_worker = CatalogImagesGitHubWorker(url, self)
        self.catalog_images_worker.progress.connect(self.on_catalog_import_progress)
        self.catalog_images_worker.finished_ok.connect(self.on_catalog_images_import_finished)
        self.catalog_images_worker.failed.connect(self.on_catalog_import_failed)
        if hasattr(self, "catalog_github_images_button"):
            self.catalog_github_images_button.setEnabled(False)
        if hasattr(self, "catalog_import_progress"):
            self.catalog_import_progress.setRange(0, 0)
            self.catalog_import_progress.setVisible(True)
        self.catalog_images_worker.start()

    def on_catalog_images_import_finished(self, result: dict):
        if hasattr(self, "catalog_github_images_button"):
            self.catalog_github_images_button.setEnabled(True)
        if hasattr(self, "catalog_import_progress"):
            self.catalog_import_progress.setRange(0, 1)
            self.catalog_import_progress.setValue(1)
            self.catalog_import_progress.setVisible(False)
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText(f"Catalog images imported: {result.get('images', 0)}")
        if hasattr(self, "catalog_images_notice"):
            self.catalog_images_notice.setVisible(self._catalog_image_count() == 0)
        CATALOG_PIXMAP_CACHE.clear()
        self.refresh_catalog()
        try:
            self.notify("Images Imported", f"Imported {result.get('images', 0)} catalog images from GitHub.", "success")
        except Exception:
            QMessageBox.information(self, "Images Imported", f"Imported {result.get('images', 0)} catalog images from GitHub.")

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
            self.catalog_import_status.setText("Starting Game8 catalog import...")
        self.catalog_import_worker.start()

    def on_catalog_import_progress(self, message: str):
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText(message)

    def on_catalog_import_finished(self, result: dict):
        if hasattr(self, "catalog_import_button"):
            self.catalog_import_button.setEnabled(True)
        if hasattr(self, "catalog_github_images_button"):
            self.catalog_github_images_button.setEnabled(True)
        if hasattr(self, "catalog_import_progress"):
            self.catalog_import_progress.setRange(0, 1)
            self.catalog_import_progress.setValue(1)
            self.catalog_import_progress.setVisible(False)
        if hasattr(self, "catalog_import_status"):
            self.catalog_import_status.setText(f"Import complete: {result}")
        self.refresh_all()
        
        try:
            self.notify("Catalog Imported", f"Imported {result.get('items', 0)} Game8 items and {result.get('images', 0)} images.", "success")
        except Exception:
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
        static_map = data_dir() / "deep_desert_map.png"
        if static_map.exists():
            if hasattr(self.map_view, "set_map"):
                self.map_view.set_map(str(static_map))
            self.refresh_pois()
            self.refresh_deep_desert_bases()
            if hasattr(self, "poi_sync_status"):
                self.poi_sync_status.setText("Deep Desert map loaded from local tactical grid.")
            return
        meta = deep_desert.load_meta()
        image_path = meta.get("image_path", "")
        image_file = Path(image_path)
        if image_path and not image_file.is_absolute():
            image_file = data_dir().parent / image_file
        if image_path and image_file.exists():
            if hasattr(self.map_view, "set_map"):
                self.map_view.set_map(str(image_file))
            self.refresh_pois()
            self.refresh_deep_desert_bases()
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

            tactical_status = poi_tactical_status(poi_type or "Custom", pooped, str(row["status"]) if "status" in row.keys() else "")
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
        if hasattr(self, "dd_base_table") and not getattr(self, "_refreshing_deep_desert_markers", False):
            self.refresh_deep_desert_bases()

    def refresh_deep_desert_bases(self):
        """Refresh Deep Desert right-side intel with active and archived items."""
        if not hasattr(self, "dd_base_table"):
            return
        self._refreshing_deep_desert_markers = True
        try:
            guild = db.get_setting("guild_code", "").upper()
            base_rows = db.list_bases(guild, map_key="deep_desert") if guild else []
            poi_rows = [row for row in db.list_pois() if (row["guild_code"] if "guild_code" in row.keys() else "").upper() == guild] if guild else []
            self.current_dd_base_rows = list(base_rows or [])
            self.current_poi_rows = list(poi_rows or [])
            self.dd_base_by_id = {int(r["id"]): r for r in self.current_dd_base_rows}
            self.poi_by_id = {int(r["id"]): r for r in self.current_poi_rows}

            for table in [getattr(self, "dd_base_table", None), getattr(self, "dd_archive_table", None)]:
                if table is not None:
                    table.setSortingEnabled(False)
                    table.setRowCount(0)

            archive_count = 0
            active_count = 0

            def add_marker_row(table, status_text, name, note, marker_type, marker_id, archived=False):
                nonlocal active_count, archive_count
                row_idx = table.rowCount()
                table.insertRow(row_idx)
                values = [status_text, name, note or ""]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value or "—"))
                    item.setData(Qt.UserRole + 10, int(marker_id))
                    item.setData(Qt.UserRole + 11, marker_type)
                    item.setData(Qt.UserRole, str(value or "").lower())
                    if archived:
                        item.setForeground(QBrush(QColor("#9aa0a8")))
                    elif str(status_text).lower() == "enemy":
                        item.setForeground(QBrush(QColor("#ff5a4f")))
                    elif str(status_text).lower() == "friendly":
                        item.setForeground(QBrush(QColor("#65ff64")))
                    table.setItem(row_idx, col, item)
                if archived:
                    archive_count += 1
                else:
                    active_count += 1

            for row in self.current_dd_base_rows:
                try:
                    status = normalize_base_status(row["status"] if "status" in row.keys() else "friendly")
                    archived = status in {"defeated", "gone"}
                    target = self.dd_archive_table if archived and hasattr(self, "dd_archive_table") else self.dd_base_table
                    add_marker_row(target, base_status_label(status), row["base_name"] or "Base", row["seitch"] or "", "base", int(row["id"]), archived)
                except Exception:
                    continue

            for row in self.current_poi_rows:
                try:
                    pooped = bool(row["pooped_on"]) if "pooped_on" in row.keys() else False
                    status = poi_tactical_status(str(row["poi_type"] if "poi_type" in row.keys() else row["label"]), pooped, str(row["status"]) if "status" in row.keys() else "")
                    archived = status in {"defeated", "gone"}
                    target = self.dd_archive_table if archived and hasattr(self, "dd_archive_table") else self.dd_base_table
                    label = row["label"] or row["poi_type"] or "POI"
                    add_marker_row(target, poi_status_label(status), label, row["note"] or "", "poi", int(row["id"]), archived)
                except Exception:
                    continue

            for table in [getattr(self, "dd_base_table", None), getattr(self, "dd_archive_table", None)]:
                if table is not None:
                    table.setSortingEnabled(True)
                    table.resizeRowsToContents()

            if hasattr(self, "dd_archive_toggle"):
                self.dd_archive_toggle.setText(f"Archived Intel ({archive_count})")
                self.dd_archive_toggle.setVisible(archive_count > 0)
                if hasattr(self, "dd_archive_table"):
                    self.dd_archive_table.setVisible(False)

            if hasattr(self, "map_view"):
                # Archived intel is removed from the map. It remains available in the Archived Intel popup.
                active_bases = []
                for _b in self.current_dd_base_rows:
                    try:
                        if normalize_base_status(_b["status"] if "status" in _b.keys() else "friendly") not in {"defeated", "gone"}:
                            active_bases.append(_b)
                    except Exception:
                        active_bases.append(_b)
                active_pois = []
                for _p in self.current_poi_rows:
                    try:
                        _pooped = bool(_p["pooped_on"]) if "pooped_on" in _p.keys() else False
                        _status = poi_tactical_status(str(_p["poi_type"] if "poi_type" in _p.keys() else _p["label"]), _pooped, str(_p["status"]) if "status" in _p.keys() else "")
                        if _status not in {"defeated", "gone"}:
                            active_pois.append(_p)
                    except Exception:
                        active_pois.append(_p)
                self.map_view.draw_bases(active_bases, getattr(self, "selected_dd_base_id_for_map", None))
                self.map_view.draw_pois(active_pois, getattr(self, "selected_poi_id_for_map", None))
        finally:
            self._refreshing_deep_desert_markers = False


    def select_deep_desert_marker_from_map(self, marker_type: str, marker_id: int):
        """When a map marker is clicked, highlight and scroll to the matching Placed Intel row."""
        marker_type = str(marker_type or "").lower()
        try:
            marker_id = int(marker_id)
        except Exception:
            return
        self._selected_deep_desert_marker_type = marker_type
        self._selected_deep_desert_marker_id = marker_id
        if marker_type == "poi":
            self.selected_poi_id_for_map = marker_id
            self.selected_dd_base_id_for_map = None
        elif marker_type == "base":
            self.selected_dd_base_id_for_map = marker_id
            self.selected_poi_id_for_map = None

        # Redraw markers so the clicked one gets the strong selected highlight.
        if hasattr(self, "map_view"):
            self.map_view.draw_bases(self._active_deep_desert_bases(), getattr(self, "selected_dd_base_id_for_map", None))
            self.map_view.draw_pois(self._active_deep_desert_pois(), getattr(self, "selected_poi_id_for_map", None))

        table = getattr(self, "dd_base_table", None)
        if table is None:
            return
        table.clearSelection()
        for row in range(table.rowCount()):
            row_type, row_id = self._deep_desert_marker_at_row(row, table)
            if row_type == marker_type and row_id == marker_id:
                table.selectRow(row)
                first_item = table.item(row, 0)
                if first_item is not None:
                    table.scrollToItem(first_item, QTableWidget.PositionAtCenter)
                table.setCurrentCell(row, 0)
                return

    def _deep_desert_marker_at_row(self, row: int, table=None):
        table = table or getattr(self, "dd_base_table", None)
        if table is None or row < 0:
            return None, None
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item is not None:
                marker_id = item.data(Qt.UserRole + 10)
                marker_type = item.data(Qt.UserRole + 11)
                if marker_id is not None and marker_type:
                    return str(marker_type), int(marker_id)
        return None, None


    def _active_deep_desert_bases(self):
        rows = []
        for row in getattr(self, "current_dd_base_rows", []) or []:
            try:
                if normalize_base_status(row["status"] if "status" in row.keys() else "friendly") not in {"defeated", "gone"}:
                    rows.append(row)
            except Exception:
                rows.append(row)
        return rows

    def _active_deep_desert_pois(self):
        rows = []
        for row in getattr(self, "current_poi_rows", []) or []:
            try:
                pooped = bool(row["pooped_on"]) if "pooped_on" in row.keys() else False
                status = poi_tactical_status(str(row["poi_type"] if "poi_type" in row.keys() else row["label"]), pooped, str(row["status"]) if "status" in row.keys() else "")
                if status not in {"defeated", "gone"}:
                    rows.append(row)
            except Exception:
                rows.append(row)
        return rows

    def center_on_deep_desert_marker(self, row: int, col: int):
        marker_type, marker_id = self._deep_desert_marker_at_row(row)
        if not marker_type or marker_id is None:
            return
        self._selected_deep_desert_marker_type = marker_type
        self._selected_deep_desert_marker_id = marker_id
        if marker_type == "base":
            self.selected_dd_base_id_for_map = marker_id
            self.selected_poi_id_for_map = None
            base = getattr(self, "dd_base_by_id", {}).get(marker_id) or db.get_base(marker_id)
            if base and hasattr(self, "map_view"):
                self.map_view.draw_bases(self._active_deep_desert_bases(), marker_id)
                self.map_view.draw_pois(self._active_deep_desert_pois(), None)
                self.map_view.center_on(float(base["x"]), float(base["y"]))
        else:
            self.selected_poi_id_for_map = marker_id
            self.selected_dd_base_id_for_map = None
            poi = getattr(self, "poi_by_id", {}).get(marker_id) or db.get_poi(marker_id)
            if poi and hasattr(self, "map_view"):
                self.map_view.draw_pois(self._active_deep_desert_pois(), marker_id)
                self.map_view.draw_bases(self._active_deep_desert_bases(), None)
                self.map_view.center_on(float(poi["x"]), float(poi["y"]))

    def show_archived_intel_popup(self):
        """Show archived Deep Desert intel in a quiet, readable StankyTools dialog."""
        if not hasattr(self, "dd_archive_table"):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Archived Intel")
        dialog.setMinimumSize(760, 520)
        dialog.setObjectName("DetailDialog")
        dialog.setStyleSheet("""
            QDialog#DetailDialog { background:#090909; border:1px solid #8D6A2B; border-radius:16px; }
            QLabel#DialogHeader { color:#D6AE5A; font-size:24px; font-weight:950; letter-spacing:2px; }
            QLabel#DialogBody { color:#F5F3ED; font-size:18px; font-weight:700; }
            QTableWidget { background:#10100f; color:#F5F3ED; gridline-color:rgba(214,174,90,0.25); font-size:16px; selection-background-color:#3a2b12; selection-color:#F5F3ED; }
            QHeaderView::section { background:#15120d; color:#D6AE5A; font-size:15px; font-weight:900; padding:8px; border:0; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        header = QHBoxLayout()
        title = QLabel("ARCHIVED INTEL")
        title.setObjectName("DialogHeader")
        close_x = QPushButton("×")
        close_x.setObjectName("GhostButton")
        close_x.setFixedSize(44, 38)
        close_x.clicked.connect(dialog.accept)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_x)
        layout.addLayout(header)
        hint = QLabel("Defeated and gone intel is archived here and removed from the active map.")
        hint.setObjectName("DialogBody")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        table = StankyTable(["Status", "Archived Intel", "Note"])
        table.setRowCount(0)
        src = self.dd_archive_table
        for r in range(src.rowCount()):
            table.insertRow(r)
            for c in range(min(3, src.columnCount())):
                src_item = src.item(r, c)
                item = QTableWidgetItem(src_item.text() if src_item else "—")
                if src_item is not None:
                    item.setData(Qt.UserRole + 10, src_item.data(Qt.UserRole + 10))
                    item.setData(Qt.UserRole + 11, src_item.data(Qt.UserRole + 11))
                    item.setForeground(QBrush(QColor("#9aa0a8")))
                table.setItem(r, c, item)
        table.resizeRowsToContents()
        layout.addWidget(table, 1)
        def center_selected(row, col):
            old = self.dd_archive_table
            # Copy selected row into the hidden archive table selection path.
            try:
                self.dd_archive_table.selectRow(row)
                self.center_on_deep_desert_archive_marker(row, col)
            except Exception:
                pass
        table.cellDoubleClicked.connect(center_selected)
        table.cellClicked.connect(center_selected)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        def popup_archive_menu(pos):
            row = table.rowAt(pos.y())
            if row < 0:
                return
            table.selectRow(row)
            marker_type = None
            marker_id = None
            for c in range(table.columnCount()):
                item = table.item(row, c)
                if item is not None:
                    marker_id = item.data(Qt.UserRole + 10)
                    marker_type = item.data(Qt.UserRole + 11)
                    if marker_id is not None and marker_type:
                        break
            if marker_id is None or not marker_type:
                return
            menu = QMenu(dialog)
            restore_action = menu.addAction("Set Active Again")
            delete_action = menu.addAction("Delete")
            chosen = menu.exec(table.viewport().mapToGlobal(pos))
            if chosen == restore_action:
                if str(marker_type) == "base":
                    db.update_base_status(int(marker_id), "enemy")
                    self.sync_after_marker_change("base")
                else:
                    db.update_poi_status(int(marker_id), "enemy", db.get_setting("display_name", ""))
                    self.sync_after_marker_change("poi")
                self.refresh_deep_desert_bases()
                self.notify("Intel Restored", "Archived intel restored to Active Intel.", "success")
                dialog.accept()
            elif chosen == delete_action:
                confirm = self.confirm("Delete Archived Intel", "Permanently delete this archived intel?") if hasattr(self, "confirm") else (QMessageBox.question(self, "Delete Archived Intel", "Permanently delete this archived intel?") == QMessageBox.Yes)
                if not confirm:
                    return
                if str(marker_type) == "base":
                    base = db.get_base(int(marker_id))
                    if base:
                        self.delete_remote_base(base)
                    db.delete_base(int(marker_id))
                    self.sync_after_marker_change("base")
                else:
                    poi = db.get_poi(int(marker_id))
                    if poi:
                        self.delete_remote_poi(poi)
                    db.delete_poi(int(marker_id))
                    self.sync_after_marker_change("poi")
                self.refresh_deep_desert_bases()
                self.notify("Archived Intel Deleted", "Archived intel was removed.", "success")
                dialog.accept()
        table.customContextMenuRequested.connect(popup_archive_menu)
        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("PrimaryButton")
        close_btn.setMinimumWidth(160)
        close_btn.clicked.connect(dialog.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
        dialog.exec()

    def center_on_deep_desert_archive_marker(self, row: int, col: int):
        if not hasattr(self, "dd_archive_table") or row < 0:
            return
        old_table = self.dd_base_table
        self.dd_base_table = self.dd_archive_table
        try:
            self.center_on_deep_desert_marker(row, col)
        finally:
            self.dd_base_table = old_table

    def show_deep_desert_archive_context_menu(self, pos):
        if not hasattr(self, "dd_archive_table"):
            return
        row = self.dd_archive_table.rowAt(pos.y())
        if row < 0:
            return
        self.dd_archive_table.selectRow(row)
        marker_type, marker_id = self._deep_desert_marker_at_row(row, table=self.dd_archive_table)
        if not marker_type or marker_id is None:
            return
        menu = QMenu(self)
        restore_action = menu.addAction("Set Active Again")
        delete_action = menu.addAction("Delete")
        chosen = menu.exec(self.dd_archive_table.viewport().mapToGlobal(pos))
        if chosen == restore_action:
            if marker_type == "base":
                db.update_base_status(int(marker_id), "enemy")
                self.sync_after_marker_change("base")
            else:
                db.update_poi_status(int(marker_id), "enemy", db.get_setting("display_name", ""))
                self.sync_after_marker_change("poi")
            self.refresh_deep_desert_bases()
            self.notify("Intel Restored", "Archived intel restored to Active Intel.", "success")
        elif chosen == delete_action:
            if QMessageBox.question(self, "Delete Archived Intel", "Permanently delete this archived intel?") != QMessageBox.Yes:
                return
            if marker_type == "base":
                base = db.get_base(int(marker_id))
                if base:
                    self.delete_remote_base(base)
                db.delete_base(int(marker_id))
                self.sync_after_marker_change("base")
            else:
                poi = db.get_poi(int(marker_id))
                if poi:
                    self.delete_remote_poi(poi)
                db.delete_poi(int(marker_id))
                self.sync_after_marker_change("poi")
            self.refresh_deep_desert_bases()
            self.notify("Archived Intel Deleted", "Archived intel was removed.", "success")

    def show_deep_desert_marker_context_menu(self, pos):
        if not hasattr(self, "dd_base_table"):
            return
        row = self.dd_base_table.rowAt(pos.y())
        if row < 0:
            return
        self.dd_base_table.selectRow(row)
        self.center_on_deep_desert_marker(row, 0)
        marker_type, marker_id = self._deep_desert_marker_at_row(row)
        if not marker_type or marker_id is None:
            return
        self._selected_deep_desert_marker_type = marker_type
        self._selected_deep_desert_marker_id = marker_id
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        menu.addSeparator()
        friendly_action = menu.addAction("Friendly")
        enemy_action = menu.addAction("Enemy")
        defeated_action = menu.addAction("Defeated")
        gone_action = menu.addAction("Gone")
        chosen = menu.exec(self.dd_base_table.viewport().mapToGlobal(pos))
        if chosen == edit_action:
            self.edit_selected_deep_desert_base() if marker_type == "base" else self.edit_selected_poi()
        elif chosen == delete_action:
            self.delete_selected_deep_desert_base() if marker_type == "base" else self.delete_selected_poi()
        elif chosen == friendly_action:
            self.set_selected_deep_desert_base_status("friendly") if marker_type == "base" else self.set_selected_poi_status("friendly")
        elif chosen == enemy_action:
            self.set_selected_deep_desert_base_status("enemy") if marker_type == "base" else self.set_selected_poi_status("enemy")
        elif chosen == defeated_action:
            self.set_selected_deep_desert_base_status("defeated") if marker_type == "base" else self.set_selected_poi_status("defeated")
        elif chosen == gone_action:
            self.set_selected_deep_desert_base_status("gone") if marker_type == "base" else self.set_selected_poi_status("gone")

    def selected_deep_desert_base_id(self) -> int | None:
        if getattr(self, "_selected_deep_desert_marker_type", None) == "base":
            marker_id = getattr(self, "_selected_deep_desert_marker_id", None)
            if marker_id is not None:
                return int(marker_id)
        if not hasattr(self, "dd_base_table"):
            return None
        row = self.dd_base_table.currentRow()
        marker_type, marker_id = self._deep_desert_marker_at_row(row)
        if marker_type == "base" and marker_id is not None:
            return int(marker_id)
        return None

    def center_on_deep_desert_base(self, row: int, col: int):
        base_id = None
        for c in range(self.dd_base_table.columnCount()):
            item = self.dd_base_table.item(row, c)
            if item is not None:
                base_id = item.data(Qt.UserRole + 10)
                if base_id is not None:
                    break
        if base_id is None:
            return
        self.selected_dd_base_id_for_map = int(base_id)
        base = getattr(self, "dd_base_by_id", {}).get(int(base_id))
        if base and hasattr(self, "map_view"):
            self.map_view.draw_bases(self.current_dd_base_rows, self.selected_dd_base_id_for_map)
            self.map_view.center_on(float(base["x"]), float(base["y"]))

    def show_deep_desert_base_context_menu(self, pos):
        if not hasattr(self, "dd_base_table"):
            return
        row = self.dd_base_table.rowAt(pos.y())
        if row < 0:
            return
        self.dd_base_table.selectRow(row)
        self.center_on_deep_desert_base(row, 0)
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        menu.addSeparator()
        friendly_action = menu.addAction("Friendly")
        enemy_action = menu.addAction("Enemy")
        defeated_action = menu.addAction("Defeated")
        gone_action = menu.addAction("Gone")
        chosen = menu.exec(self.dd_base_table.viewport().mapToGlobal(pos))
        if chosen == edit_action:
            self.edit_selected_deep_desert_base()
        elif chosen == delete_action:
            self.delete_selected_deep_desert_base()
        elif chosen == friendly_action:
            self.set_selected_deep_desert_base_status("friendly")
        elif chosen == enemy_action:
            self.set_selected_deep_desert_base_status("enemy")
        elif chosen == defeated_action:
            self.set_selected_deep_desert_base_status("defeated")
        elif chosen == gone_action:
            self.set_selected_deep_desert_base_status("gone")

    def add_deep_desert_base_at(self, x: float, y: float, status: str = "enemy"):
        if not self._require_guild_for_map_action("Deep Desert bases"):
            return
        guild = db.get_setting("guild_code", "").upper()
        user = db.get_setting("display_name", "")
        title, ok = QInputDialog.getText(self, "Deep Desert Base", "Base title:", text=f"{base_status_label(status)} Base")
        if not ok or not title.strip():
            return
        note, ok = QInputDialog.getMultiLineText(self, "Deep Desert Base", "Note:", "")
        if not ok:
            return
        db.add_base(x, y, title.strip(), note.strip(), guild, user, map_key="deep_desert", status=normalize_base_status(status))
        self.log_guild_activity(f"added Deep Desert {status} base: {title.strip()}")
        self.sync_after_marker_change("base")
        self.refresh_deep_desert_bases()
        self.refresh_dashboard()

    def edit_selected_deep_desert_base(self):
        base_id = self.selected_deep_desert_base_id()
        if not base_id:
            return
        base = db.get_base(base_id)
        if not base:
            return
        title, ok = QInputDialog.getText(self, "Edit Base", "Base title:", text=base["base_name"] or "Base")
        if not ok or not title.strip():
            return
        note, ok = QInputDialog.getMultiLineText(self, "Edit Base", "Note:", base["seitch"] or "")
        if not ok:
            return
        db.update_base(base_id, title.strip(), note.strip())
        self.sync_after_marker_change("base")
        self.refresh_deep_desert_bases()

    def delete_selected_deep_desert_base(self):
        base_id = self.selected_deep_desert_base_id()
        if not base_id:
            return
        base = db.get_base(base_id)
        if not base:
            return
        if QMessageBox.question(self, "Delete Base", "Delete this Deep Desert base marker?") != QMessageBox.Yes:
            return
        self.delete_remote_base(base)
        db.delete_base(base_id)
        self.sync_after_marker_change("base")
        self.refresh_deep_desert_bases()
        self.refresh_dashboard()

    def set_selected_deep_desert_base_status(self, status: str):
        base_id = self.selected_deep_desert_base_id()
        if not base_id:
            return
        clean = normalize_base_status(status)
        if clean in {"defeated", "gone"}:
            base = db.get_base(base_id)
            current_note = base["seitch"] if base and "seitch" in base.keys() else ""
            archive_note, ok_note = QInputDialog.getMultiLineText(self, "Archive Intel", f"Optional note for {clean.title()} archive:", current_note or "")
            if not ok_note:
                return
            if base:
                db.update_base(base_id, base["base_name"] or "Base", archive_note.strip())
        db.update_base_status(base_id, clean)
        self.sync_after_marker_change("base")
        self.refresh_deep_desert_bases()
        if clean in {"defeated", "gone"}:
            self.notify("Intel Archived", f"Marked as {clean.title()} and moved to Archived Intel.", "success")

    def manual_sync_all_markers(self):
        """Manual recovery sync used only from Settings."""
        if not db.get_setting("guild_code", "").strip() or not db.get_setting("display_name", "").strip():
            QMessageBox.information(self, "Guild Sync", "Join or create a guild before syncing map markers.")
            return
        if hasattr(self, "poi_sync_status"):
            self.poi_sync_status.setText("Manual sync running: POIs, bases, and guild content...")
        if hasattr(self, "base_sync_status"):
            self.base_sync_status.setText("Manual sync running...")
        QApplication.processEvents()
        self.sync_guild_pois(show_popup=False)
        self.sync_guild_bases(show_popup=False)
        self.sync_guild_dashboard_content(show_errors=False)
        if hasattr(self, "poi_sync_status"):
            self.poi_sync_status.setText("Manual sync complete.")
        if hasattr(self, "base_sync_status"):
            self.base_sync_status.setText("Manual sync complete.")
        QMessageBox.information(self, "Guild Sync", "Manual sync complete. POIs, bases, links, and news are up to date.")


    def sync_after_news_change(self):
        """Queue and immediately flush guild news changes after add/edit/delete."""
        if qt_alive(getattr(self, "dashboard_sync_status", None)):
            self.dashboard_sync_status.setText("SYNC STATUS: AUTO-SYNCING NEWS")
        if hasattr(self, "sync_manager"):
            self.sync_manager.queue("news", immediate=False)
            self.notify("Sync Queued", "Guild content will sync in the background.", "info", 1800)
        else:
            QTimer.singleShot(250, lambda: self.sync_guild_dashboard_content(show_errors=False))

    def sync_after_marker_change(self, marker_kind: str):
        """Queue and immediately flush marker changes after add/edit/delete."""
        kind = (marker_kind or "marker").lower()
        if kind == "poi" and hasattr(self, "poi_sync_status"):
            self.poi_sync_status.setText("Auto-syncing Deep Desert POI...")
        elif kind == "base" and hasattr(self, "base_sync_status"):
            self.base_sync_status.setText("Auto-syncing base marker...")
        if hasattr(self, "sync_manager"):
            # Marker changes should reach other open apps quickly.  Use immediate
            # debounce so add/edit/delete POIs do not sit in the queue until the
            # next periodic timer.
            self.sync_manager.queue(kind, immediate=True)
            self.notify("Sync Queued", f"{kind.title()} change saved locally and will sync in the background.", "info", 1800)
        else:
            if kind == "poi":
                self.sync_guild_pois(show_popup=False)
            elif kind == "base":
                self.sync_guild_bases(show_popup=False)
            else:
                self.sync_guild_pois(show_popup=False)
                self.sync_guild_bases(show_popup=False)
            self.sync_guild_dashboard_content(show_errors=False)

    def queue_guild_sync(self, title: str = "Sync Queued", message: str = "Guild sync queued."):
        try:
            self.sync_manager.queue("guild")
        except Exception:
            pass
        self.notify(title, message, "success")


    def refresh_current_member_role(self) -> str:
        """Pull this user's current role from Supabase so promotions unlock Guild Admin immediately after sync."""
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        display_name = db.get_setting("display_name", "").strip()
        if not url or not key or not guild or not display_name or "PASTE_" in key:
            return db.get_setting("guild_role", "member") or "member"
        try:
            rows = supabase_request("GET", url, key, f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(display_name)}&select=role&limit=1")
            if rows:
                role = (rows[0].get("role") or "member").lower()
                db.set_setting("guild_role", role)
                safe_label_set_text(getattr(self, "guild_role_label", None), "Role: " + role)
                self.update_guild_nav_visibility()
                self.update_sidebar_status()
                return role
        except Exception:
            pass
        return db.get_setting("guild_role", "member") or "member"

    def manual_guild_sync_from_dashboard(self):
        if not db.get_setting("guild_code", "").strip() or not db.get_setting("display_name", "").strip():
            self.notify("Guild Sync", "Join or create a guild first.", "warning")
            return
        self.notify("Guild Sync", "Sync started.", "info")
        try:
            self.refresh_current_member_role()
            self.sync_guild_pois(show_popup=False)
            self.sync_guild_bases(show_popup=False)
            self.sync_guild_dashboard_content(show_errors=False)
            self.refresh_current_member_role()
            self.sync_guild_logo_from_remote()
            self.refresh_all()
            self.notify("Guild Synced", "Guild data synced successfully.", "success")
        except Exception as exc:
            self.notify("Guild Sync Failed", str(exc)[:220], "error", 5200)

    def auto_sync_guild(self):
        if getattr(self, "_sync_running", False):
            return
        if not db.get_setting("guild_code", "") or not db.get_setting("display_name", ""):
            return
        now = time.monotonic()
        if now - getattr(self, "_last_auto_sync", 0.0) < 45:
            return
        self._last_auto_sync = now
        if hasattr(self, "sync_manager"):
            self.sync_manager.queue("all", immediate=False)
        else:
            self.sync_guild_pois(show_popup=False)
            self.sync_guild_bases(show_popup=False)
            self.sync_guild_dashboard_content(show_errors=False)

    def pull_guild_updates(self):
        """Pull remote guild content so other users' changes appear automatically.

        Phase 3.5 accidentally narrowed the periodic pull to dashboard content only,
        which meant Deep Desert POIs/bases stopped appearing on other clients unless
        the user manually synced. Keep this method as the central lightweight
        background pull for all guild-visible data.
        """
        if getattr(self, "_sync_running", False):
            return
        if not db.get_setting("guild_code", "").strip():
            return
        try:
            # Pull map markers first so the Deep Desert list/canvas stays current.
            self.sync_guild_pois(show_popup=False)
            self.sync_guild_bases(show_popup=False)

            # Pull dashboard/guild content after markers.
            self.sync_guild_dashboard_content(show_errors=False)
            self.refresh_current_member_role()

            # Redraw only what exists in the current window instance.
            if hasattr(self, "dd_base_table") or hasattr(self, "map_view"):
                self.refresh_deep_desert_bases()
            self.refresh_dashboard()
            self.refresh_guild_page()
        except Exception as exc:
            if hasattr(self, "poi_sync_status"):
                self.poi_sync_status.setText(f"Auto-sync issue: {exc}")

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
            # Keep current user's role fresh without overwriting an owner/officer
            # promotion from another client with stale local "member" data.
            try:
                role_rows = supabase_request("GET", url, key, f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(display_name)}&select=role&limit=1")
                if role_rows:
                    role = (role_rows[0].get("role") or "member").lower()
                    db.set_setting("guild_role", role)
                    if hasattr(self, "guild_role_label"):
                        self.guild_role_label.setText("Role: " + role)
                    self.update_guild_nav_visibility()
                else:
                    supabase_request("POST", url, key, "guild_members?on_conflict=guild_code,display_name", [{
                        "guild_code": guild,
                        "display_name": display_name,
                        "role": db.get_setting("guild_role", "member") or "member",
                    }])
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
                remote_status = item.get("status") or ("defeated" if pooped_on else "active")
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
                    status=remote_status,
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
                poi_status = poi_tactical_status(str(poi_type or "Custom"), pooped_on, str(row["status"]) if "status" in row.keys() else "")
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
                    "status": poi_status,
                })
                local_remote_pairs.append((int(row["id"]), rid))

            uploaded = 0
            if payload:
                try:
                    supabase_request("POST", url, key, "guild_pois?on_conflict=id", payload)
                except Exception as exc:
                    # Older Supabase schemas may not have guild_pois.status yet.
                    # Keep syncing position/name/note rather than failing completely.
                    if "status" not in str(exc).lower():
                        raise
                    legacy_payload = []
                    for item in payload:
                        legacy = dict(item)
                        legacy.pop("status", None)
                        legacy_payload.append(legacy)
                    supabase_request("POST", url, key, "guild_pois?on_conflict=id", legacy_payload)
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


    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

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
        if hasattr(self, "dashboard_link_cards"):
            self._clear_layout(self.dashboard_link_cards)
            link_rows = getattr(self, "current_dashboard_links", []) or []
            if not link_rows:
                self.dashboard_link_cards.addWidget(LinkCard("No Helpful Links", "", "System"))
            for idx, row in enumerate(link_rows[:4]):
                card = LinkCard(row["title"] or "Useful Link", row["url"] or "", row["created_by"] or "—")
                card.doubleClicked.connect(lambda url, i=idx: self.show_dashboard_link_detail(i, 0))
                self.dashboard_link_cards.addWidget(card)
        if hasattr(self, "news_table"):
            self.news_table.setSortingEnabled(False)
            self.news_table.setRowCount(0)
            self.current_dashboard_news = db.list_guild_news(guild, 12)
            for row in self.current_dashboard_news:
                title_body = (row["title"] or "Guild Update")
                if row["body"]:
                    title_body += " — " + str(row["body"]).replace("\n", " ")
                self.news_table.add_row([
                    title_body,
                    format_app_date(row["created_at"]),
                ])
            self.news_table.setSortingEnabled(True)
            self.news_table.resizeRowsToContents()
        if hasattr(self, "dashboard_news_cards"):
            self._clear_layout(self.dashboard_news_cards)
            news_rows = getattr(self, "current_dashboard_news", []) or []
            if not news_rows:
                self.dashboard_news_cards.addWidget(NewsCard("No Guild News", "Create a guild post to broadcast announcements here.", "", "", emphasize_date=True, truncate_body=True))
            for idx, row in enumerate(news_rows[:4]):
                card = NewsCard(row["title"] or "Guild Update", row["body"] or "", "", format_app_date(row["created_at"]), emphasize_date=True, truncate_body=True)
                card.doubleClicked.connect(lambda i=idx: self.show_dashboard_news_detail(i, 0))
                self.dashboard_news_cards.addWidget(card)
        if hasattr(self, "dashboard_events_table"):
            self.dashboard_events_table.setSortingEnabled(False)
            self.dashboard_events_table.setRowCount(0)
            self.current_dashboard_events = sorted(db.list_guild_events(guild, 12), key=event_sort_tuple)
            for row in self.current_dashboard_events:
                title_body = (row["title"] or "Guild Event")
                if row["body"]:
                    title_body += " — " + str(row["body"]).replace("\n", " ")
                event_id = str(row["remote_id"] or "")
                attending_count = db.event_attendance_count(event_id, guild) if event_id else 0
                interested_count = db.event_interested_count(event_id, guild) if event_id else 0
                when_raw = row["event_at"] or row["created_at"]
                self.dashboard_events_table.add_row([
                    title_body,
                    format_event_central_time(when_raw),
                    event_timing_badge(when_raw),
                    f"✅ {attending_count}",
                    f"⭐ {interested_count}",
                ])
            self.dashboard_events_table.setSortingEnabled(True)
            self.dashboard_events_table.resizeRowsToContents()
        if hasattr(self, "dashboard_events_cards"):
            self._clear_layout(self.dashboard_events_cards)
            event_rows = getattr(self, "current_dashboard_events", []) or []
            if not event_rows:
                card = NewsCard("No Events", "Create a guild event to show it here.", "", "", emphasize_date=True, truncate_body=True)
                self.dashboard_events_cards.addWidget(card)
            for idx, row in enumerate(event_rows[:4]):
                card = NewsCard(row["title"] or "Guild Event", row["body"] or "", "", format_event_central_time(row["event_at"] or row["created_at"]), emphasize_date=True, truncate_body=True)
                card.doubleClicked.connect(lambda i=idx: self.show_dashboard_event_detail(i, 0))
                card.setContextMenuPolicy(Qt.CustomContextMenu)
                card.customContextMenuRequested.connect(lambda pos, i=idx, c=card: self.show_dashboard_event_context_menu(i, c.mapToGlobal(pos)))
                self.dashboard_events_cards.addWidget(card)

    def _set_status_pill_value(self, pill, value: str):
        """Safely update a StatusPill value across old/new widget versions."""
        if not qt_alive(pill):
            return
        try:
            if hasattr(pill, "set_value"):
                pill.set_value(value)
                return
        except Exception:
            pass
        try:
            if hasattr(pill, "value") and qt_alive(pill.value):
                pill.value.setText(value)
                return
        except Exception:
            pass
        try:
            labels = [lbl for lbl in pill.findChildren(QLabel) if qt_alive(lbl)]
            if labels:
                labels[-1].setText(value)
        except Exception:
            pass

    def refresh_guild_page_identity(self):
        """Refresh the guild banner/logo immediately after join/create/logo changes."""
        guild = db.get_setting("guild_code", "").upper()
        guild_name = db.get_setting("guild_name", guild or "No Guild") or (guild or "No Guild")
        if qt_alive(getattr(self, "guild_page_title", None)):
            self.guild_page_title.setText(str(guild_name).upper())
        self._set_status_pill_value(getattr(self, "guild_page_role_pill", None), db.get_setting("guild_role", "member") or "member")
        self._set_status_pill_value(getattr(self, "guild_page_code_pill", None), guild or "—")
        logo_label = getattr(self, "guild_page_logo", None)
        if qt_alive(logo_label):
            logo_label.clear()
            logo_path = resolve_local_path(db.get_setting("guild_logo_path", ""))
            pix = QPixmap(str(logo_path)) if logo_path.exists() else QPixmap()
            if not pix.isNull():
                logo_label.setPixmap(pix.scaled(78, 78, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo_label.setText((str(guild_name).strip()[:2] or "ST").upper())

    def refresh_guild_page(self):
        guild = db.get_setting("guild_code", "").upper()
        self.refresh_guild_page_identity()
        # Guild Admin displays local cached data. Use Dashboard > Guild Sync for manual cloud refresh.
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
                title_text = (row["title"] or "Guild Update")
                body_text = str(row["body"] or "").replace("\n", " ")
                if body_text and len(body_text) > 180:
                    body_text = body_text[:180].rstrip() + "..."
                text = title_text + ((" — " + body_text) if body_text else "")
                self.guild_page_news.add_row([text, format_app_date(row["created_at"]), "READ MORE" if row["body"] else "—"])
            self.guild_page_news.setSortingEnabled(True)
        if hasattr(self, "guild_page_events"):
            self.guild_page_events.setSortingEnabled(False)
            self.guild_page_events.setRowCount(0)
            self.current_guild_events = sorted(db.list_guild_events(guild, 30), key=event_sort_tuple)
            for row in self.current_guild_events:
                title_text = (row["title"] or "Guild Event")
                body_text = str(row["body"] or "").replace("\n", " ")
                if body_text and len(body_text) > 180:
                    body_text = body_text[:180].rstrip() + "..."
                text = title_text + ((" — " + body_text) if body_text else "")
                event_id = str(row["remote_id"] or "")
                attending_count = db.event_attendance_count(event_id, guild) if event_id else 0
                interested_count = db.event_interested_count(event_id, guild) if event_id else 0
                me = db.get_setting("display_name", "").strip()
                my_status = db.get_event_response_status(event_id, me, guild) if me and event_id else ""
                att_text = ("✓ " if my_status == "attending" else "") + f"✅ {attending_count}"
                int_text = ("✓ " if my_status == "interested" else "") + f"⭐ {interested_count}"
                when_raw = row["event_at"] or row["created_at"]
                self.guild_page_events.add_row([text, format_event_central_time(when_raw), event_timing_badge(when_raw), att_text, int_text, "READ MORE" if row["body"] else "—"])
            self.guild_page_events.setSortingEnabled(True)
            self.guild_page_events.resizeRowsToContents()
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

        try:
            members = getattr(self, "current_guild_members", []) or []
            news = getattr(self, "current_guild_news", []) or db.list_guild_news(guild, 30)
            links = getattr(self, "current_guild_links", []) or db.list_guild_links(guild, 50)
            officer_count = sum(1 for m in members if str(m.get("role", "")).lower() in {"owner", "officer", "admin"})
            if hasattr(self, "guild_stat_members"):
                self.guild_stat_members.set_value(str(len(members)), "Current roster")
            if hasattr(self, "guild_stat_officers"):
                self.guild_stat_officers.set_value(str(officer_count), "Owner/officer roles")
            if hasattr(self, "guild_stat_news"):
                self.guild_stat_news.set_value(str(len(news)), "Recent announcements")
            if hasattr(self, "guild_stat_links"):
                self.guild_stat_links.set_value(str(len(links)), "Pinned resources")
        except Exception:
            pass

    def push_pending_member_specializations(self) -> None:
        """Upload locally changed member specializations, then clear their pending flag on success."""
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild or "PASTE_" in key:
            return
        pending = db.list_pending_member_specializations(guild)
        if not pending:
            return
        for row in pending:
            display_name = (row["display_name"] or "").strip()
            if not display_name:
                continue
            payload = [{
                "guild_code": guild,
                "display_name": display_name,
                "crafting": int(row["crafting"] or 1),
                "gathering": int(row["gathering"] or 1),
                "exploration": int(row["exploration"] or 1),
                "combat": int(row["combat"] or 1),
                "sabotage": int(row["sabotage"] or 1),
            }]
            supabase_request("POST", url, key, "member_specializations?on_conflict=guild_code,display_name", payload)
            db.mark_member_specializations_synced(guild, display_name)

    def sync_guild_dashboard_content(self, show_errors: bool = False):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild:
            return
        try:
            self.push_pending_member_specializations()
        except Exception as exc:
            if show_errors:
                QMessageBox.warning(self, "Member Specializations Sync", str(exc))
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
        try:
            events = supabase_request("GET", url, key, f"guild_events?guild_code=eq.{urllib.parse.quote(guild)}&select=*&order=event_at.desc&limit=60")
            db.cache_guild_events(events, guild)
        except Exception as exc:
            if show_errors:
                QMessageBox.warning(self, "Guild Events", str(exc))
        try:
            attendance = supabase_request("GET", url, key, f"guild_event_attendance?guild_code=eq.{urllib.parse.quote(guild)}&select=*&order=created_at.asc")
            db.cache_guild_event_attendance(attendance, guild)
        except Exception as exc:
            # Do not let a missing/outdated attendance table block event syncing.
            if show_errors:
                QMessageBox.warning(self, "Event Responses", str(exc))
        try:
            specs = supabase_request("GET", url, key, f"member_specializations?guild_code=eq.{urllib.parse.quote(guild)}&select=*&order=display_name.asc")
            db.cache_member_specializations(specs, guild)
        except Exception as exc:
            if show_errors:
                QMessageBox.warning(self, "Member Specializations", str(exc))

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
        if not url or not key or "PASTE_" in key:
            db.add_local_guild_news(guild, title.strip(), body.strip(), db.get_setting("display_name", ""))
            self.refresh_guild_page()
            self.refresh_dashboard()
            self.queue_guild_sync("Announcement Added", "Saved locally and queued for sync.")
            return
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
            self.queue_guild_sync("Announcement Added", "Guild announcement saved and queued for sync.")
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
        DetailDialog(title, body, self, meta=f"Posted: {format_app_date(news["created_at"])}").exec()

    def show_guild_news_detail(self, row: int, col: int):
        news = self._news_row_from_table("guild", row)
        if not news:
            return
        title = news["title"] or "Guild Update"
        body = news["body"] or "No details were provided."
        DetailDialog(title, body, self, meta=f"Posted: {format_app_date(news["created_at"])}").exec()


    def _event_row_from_table(self, table_name: str, row: int):
        rows = getattr(self, "current_guild_events" if table_name == "guild" else "current_dashboard_events", []) or []
        if 0 <= row < len(rows):
            return rows[row]
        return None

    def _format_event_response_body(self, event) -> str:
        guild = db.get_setting("guild_code", "").upper()
        event_id = str(event["remote_id"] or "") if event else ""
        body = html.escape(event["body"] or "No details were provided.").replace("\n", "<br>")
        created_by = html.escape((event["created_by"] or "—") if event else "—")
        attending = db.list_event_responses(event_id, guild, "attending") if event_id else []
        interested = db.list_event_responses(event_id, guild, "interested") if event_id else []

        def bullet_list(names: list[str]) -> str:
            if not names:
                return "<div style='padding-left:14px;'>• None yet</div>"
            return "".join(f"<div style='padding-left:14px;'>• {html.escape(name)}</div>" for name in names)

        return (
            f"<div style='font-size:22px; line-height:1.55;'>{body}</div>"
            f"<div style='font-size:13px; color:#D6AE5A; margin-top:18px; font-weight:800;'>Created by: {created_by}</div>"
            f"<div style='font-size:13px; line-height:1.35; margin-top:16px;'>"
            f"<div style='font-weight:900; color:#F5F3ED;'>✅ Attending ({len(attending)})</div>"
            f"{bullet_list(attending)}"
            f"<br>"
            f"<div style='font-weight:900; color:#F5F3ED;'>⭐ Interested ({len(interested)})</div>"
            f"{bullet_list(interested)}"
            f"</div>"
        )

    def show_guild_event_context_menu(self, pos):
        table = getattr(self, "guild_page_events", None)
        if not table:
            return
        row = table.rowAt(pos.y())
        if row >= 0:
            table.selectRow(row)
        event = self._event_row_from_table("guild", table.currentRow())
        if not event:
            return
        menu = QMenu(self)
        act_attending = menu.addAction("✅ Mark Attending")
        act_interested = menu.addAction("⭐ Mark Interested")
        act_remove = menu.addAction("❌ Not Attending / Remove Response")
        menu.addSeparator()
        act_view = menu.addAction("View Responses")
        act_open = menu.addAction("Open Details")
        menu.addSeparator()
        act_delete = menu.addAction("Delete Event")
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen == act_attending:
            self.set_selected_event_response("attending")
        elif chosen == act_interested:
            self.set_selected_event_response("interested")
        elif chosen == act_remove:
            self.set_selected_event_response("")
        elif chosen == act_view:
            self.show_selected_event_attendees()
        elif chosen == act_open:
            self.show_guild_event_detail(table.currentRow(), 0)
        elif chosen == act_delete:
            self.delete_selected_guild_event()

    def show_dashboard_event_detail(self, row: int, col: int):
        event = self._event_row_from_table("dashboard", row)
        if not event:
            return
        title = event["title"] or "Guild Event"
        when = event["event_at"] or event["created_at"] or ""
        DetailDialog(title, self._format_event_response_body(event), self, meta=f"When: {format_event_central_time(when)}").exec()

    def show_guild_event_detail(self, row: int, col: int):
        event = self._event_row_from_table("guild", row)
        if not event:
            return
        title = event["title"] or "Guild Event"
        when = event["event_at"] or event["created_at"] or ""
        DetailDialog(title, self._format_event_response_body(event), self, meta=f"When: {format_event_central_time(when)}").exec()

    def show_selected_event_attendees(self):
        row = self.guild_page_events.currentRow() if hasattr(self, "guild_page_events") else -1
        event = self._event_row_from_table("guild", row)
        if not event:
            QMessageBox.information(self, "Event Responses", "Select an event first.")
            return
        when = event["event_at"] or event["created_at"] or ""
        DetailDialog(event["title"] or "Event Responses", self._format_event_response_body(event), self, meta=f"When: {format_event_central_time(when)}").exec()

    def set_event_response_for_event(self, event, status: str = ""):
        if not event:
            QMessageBox.information(self, "Event Response", "Select an event first.")
            return
        status = (status or "").strip().lower()
        if status not in {"attending", "interested", ""}:
            status = ""
        guild = db.get_setting("guild_code", "").upper()
        display_name = db.get_setting("display_name", "").strip()
        if not display_name:
            display_name, ok = QInputDialog.getText(self, "Event Response", "Your guild display name:")
            if not ok or not display_name.strip():
                return
            display_name = display_name.strip()
            db.set_setting("display_name", display_name)
        event_id = str(event["remote_id"] or "").strip()
        if not event_id:
            QMessageBox.warning(self, "Event Response", "This event is missing a sync id. Refresh and try again.")
            return
        when_raw = event["event_at"] or event["created_at"] or ""
        if event_timing_badge(when_raw).endswith("Ended"):
            QMessageBox.information(self, "Event Response", "This event has ended.")
            return
        current_status = db.get_event_response_status(event_id, display_name, guild)
        final_status = "" if status == current_status else status
        url, key = active_supabase()
        try:
            # Save locally first so the UI updates even if the network is slow or Supabase is unavailable.
            db.set_local_event_response(event_id, guild, display_name, final_status)
            if url and key and "PASTE_" not in key and not event_id.startswith("local-event-"):
                safe_event = urllib.parse.quote(event_id)
                safe_guild = urllib.parse.quote(guild)
                safe_name = urllib.parse.quote(display_name)
                if final_status:
                    payload = [{"event_id": event_id, "guild_code": guild, "display_name": display_name, "status": final_status}]
                    supabase_request("POST", url, key, "guild_event_attendance?on_conflict=event_id,display_name", payload)
                else:
                    supabase_request("DELETE", url, key, f"guild_event_attendance?event_id=eq.{safe_event}&guild_code=eq.{safe_guild}&display_name=eq.{safe_name}")
            try:
                self.sync_manager.queue("events", immediate=True)
            except Exception:
                pass
            self.sync_guild_dashboard_content(show_errors=False)
            self.refresh_guild_page()
            self.refresh_dashboard()
            label = "Response removed." if not final_status else ("Marked attending." if final_status == "attending" else "Marked interested.")
            self.notify("Event Response", label, "success")
        except Exception as exc:
            # Keep the local change. The user asked for this to be saved locally; background sync can catch up later.
            self.refresh_guild_page()
            self.refresh_dashboard()
            self.notify("Event Saved Locally", f"Saved locally. Remote sync failed: {str(exc)[:120]}", "warning", 5200)

    def set_selected_event_response(self, status: str = ""):
        row = self.guild_page_events.currentRow() if hasattr(self, "guild_page_events") else -1
        event = self._event_row_from_table("guild", row)
        self.set_event_response_for_event(event, status)

    def show_dashboard_event_context_menu(self, index: int, global_pos):
        event = self._event_row_from_table("dashboard", index)
        if not event:
            return
        menu = QMenu(self)
        act_attending = menu.addAction("✅ Mark Attending")
        act_interested = menu.addAction("⭐ Mark Interested")
        act_remove = menu.addAction("❌ Not Attending / Remove Response")
        menu.addSeparator()
        act_open = menu.addAction("Open Details")
        chosen = menu.exec(global_pos)
        if chosen == act_attending:
            self.set_event_response_for_event(event, "attending")
        elif chosen == act_interested:
            self.set_event_response_for_event(event, "interested")
        elif chosen == act_remove:
            self.set_event_response_for_event(event, "")
        elif chosen == act_open:
            self.show_dashboard_event_detail(index, 0)

    def set_selected_event_attendance(self, attending: bool = True):
        self.set_selected_event_response("attending" if attending else "")

    def _event_datetime_dialog(self, title_text: str = ""):
        dlg = QDialog(self)
        dlg.setWindowTitle("Guild Event")
        dlg.setMinimumWidth(560)
        dlg.setObjectName("DetailDialog")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        title = QLabel("CREATE GUILD EVENT")
        title.setObjectName("DialogHeader")
        layout.addWidget(title)

        form = QFormLayout()
        name = QLineEdit(title_text)
        name.setPlaceholderText("Event title")
        when = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        when.setCalendarPopup(True)
        when.setDisplayFormat("MM/dd/yyyy h:mm AP")
        timezone_note = QLabel("Times are saved and displayed in Central Time (CT).")
        timezone_note.setObjectName("MutedLabel")
        notes = QTextEdit()
        notes.setPlaceholderText("Event notes...")
        notes.setMinimumHeight(140)
        form.addRow("Title", name)
        form.addRow("Date / Time (Central)", when)
        form.addRow("", timezone_note)
        form.addRow("Notes", notes)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        save = QPushButton("Save Event")
        save.setObjectName("PrimaryButton")
        cancel.clicked.connect(dlg.reject)
        save.clicked.connect(dlg.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        if dlg.exec() != QDialog.Accepted:
            return None
        title_val = name.text().strip()
        if not title_val:
            self.notify("Guild Event", "Enter an event title.", "warning")
            return None
        dt_text = when.dateTime().toString("yyyy-MM-dd hh:mm AP")
        return title_val, f"{dt_text} Central", notes.toPlainText().strip()

    def submit_guild_event(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can submit guild events.")
            return
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            QMessageBox.information(self, "Guild Event", "Join or create a guild first.")
            return
        result = self._event_datetime_dialog()
        if not result:
            return
        title, when, body = result
        created_by = db.get_setting("display_name", "")
        url, key = active_supabase()
        if url and key and "PASTE_" not in key:
            try:
                rows = supabase_request("POST", url, key, "guild_events", [{
                    "guild_code": guild,
                    "title": title.strip(),
                    "body": body.strip(),
                    "created_by": created_by,
                    "event_at": when.strip(),
                }])
                if rows:
                    db.upsert_guild_events(rows, guild)
                self.log_guild_activity(f"added guild event: {title.strip()}")
            except Exception as exc:
                db.add_local_guild_event(guild, title.strip(), body.strip(), created_by, when.strip())
                self.notify("Event Saved Locally", f"Remote sync failed and will retry: {str(exc)[:120]}", "warning", 4200)
        else:
            db.add_local_guild_event(guild, title.strip(), body.strip(), created_by, when.strip())
        self.sync_guild_dashboard_content(show_errors=False)
        self.refresh_guild_page()
        self.refresh_dashboard()
        try:
            self.sync_manager.queue("events", immediate=True)
        except Exception:
            pass
        self.queue_guild_sync("Event Added", "Guild event saved and queued for sync.")

    def delete_selected_guild_event(self):
        if not self._current_guild_admin():
            QMessageBox.warning(self, "Permission Denied", "Only owners/officers can delete guild events.")
            return
        if not hasattr(self, "guild_page_events"):
            return
        row = self.guild_page_events.currentRow()
        event = self._event_row_from_table("guild", row)
        if not event:
            QMessageBox.information(self, "Guild Event", "Select an event first.")
            return
        if QMessageBox.question(self, "Delete Guild Event", "Delete this guild event?") != QMessageBox.Yes:
            return
        rid = str(event["remote_id"] or "")
        url, key = active_supabase()
        if rid and not rid.startswith("local-event-") and url and key and "PASTE_" not in key:
            try:
                supabase_request("DELETE", url, key, f"guild_events?id=eq.{urllib.parse.quote(rid)}")
                self.log_guild_activity("deleted a guild event")
            except Exception as exc:
                QMessageBox.critical(self, "Guild Event Failed", str(exc))
                return
        db.delete_local_guild_event(rid)
        self.sync_guild_dashboard_content(show_errors=False)
        self.refresh_guild_page()
        self.refresh_dashboard()

    def show_dashboard_link_detail(self, row: int, col: int):
        links = getattr(self, "current_dashboard_links", []) or []
        if 0 <= row < len(links):
            item = links[row]
            DetailDialog(item["title"] or "Helpful Link", item["url"] or "No URL", self, meta=f"Added by: {item['created_by'] or '—'}").exec()

    def show_guild_news_context_menu(self, pos):
        table = getattr(self, "guild_page_news", None)
        if not table:
            return
        row = table.rowAt(pos.y())
        if row >= 0:
            table.selectRow(row)
        news = self._news_row_from_table("guild", table.currentRow())
        if not news:
            return
        menu = QMenu(self)
        act_open = menu.addAction("Open Announcement")
        act_delete = menu.addAction("Delete Announcement")
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen == act_open:
            self.show_guild_news_detail(table.currentRow(), 0)
        elif chosen == act_delete:
            self.delete_selected_guild_news()

    def show_guild_link_context_menu(self, pos):
        table = getattr(self, "guild_page_links", None)
        if not table:
            return
        row = table.rowAt(pos.y())
        if row >= 0:
            table.selectRow(row)
        rid = self.selected_guild_link_remote_id()
        if not rid:
            return
        menu = QMenu(self)
        act_open = menu.addAction("Open Link")
        act_edit = menu.addAction("Edit Link")
        act_delete = menu.addAction("Delete Link")
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen == act_open:
            self.open_selected_guild_link(table.currentRow(), 0)
        elif chosen == act_edit:
            self.edit_guild_link()
        elif chosen == act_delete:
            self.delete_guild_link()

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
        url, key = active_supabase()
        if rid.startswith("local-") or not url or not key or "PASTE_" in key:
            db.delete_local_guild_news(rid)
            self.sync_after_news_change()
            self.refresh_guild_page()
            self.refresh_dashboard()
            return
        try:
            supabase_request("DELETE", url, key, f"guild_news?id=eq.{urllib.parse.quote(rid)}")
            self.log_guild_activity("deleted a guild news update")
            self.sync_after_news_change()
            self.refresh_guild_page()
            self.refresh_dashboard()
        except Exception as exc:
            QMessageBox.critical(self, "Guild News Failed", str(exc))

    def open_selected_dashboard_link(self, row: int, col: int):
        self.show_dashboard_link_detail(row, col)

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
        if getattr(self, "_selected_deep_desert_marker_type", None) == "poi":
            marker_id = getattr(self, "_selected_deep_desert_marker_id", None)
            if marker_id is not None:
                return int(marker_id)
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
        gone_action = menu.addAction("Set Gone")
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
        elif chosen == gone_action:
            self.set_selected_poi_status("gone")
        elif chosen == edit_action:
            self.edit_selected_poi()
        elif chosen == delete_action:
            self.delete_selected_poi()

    def set_selected_poi_status(self, status: str):
        poi_id = self.selected_poi_id()
        if not poi_id:
            return
        poi = db.get_poi(poi_id)
        if not poi:
            return
        clean = poi_tactical_status(poi["poi_type"] if "poi_type" in poi.keys() else poi["label"], False, status)
        archive_note = ""
        if clean in {"defeated", "gone"}:
            archive_note, ok_note = QInputDialog.getMultiLineText(self, "Archive Intel", f"Optional note for {clean.title()} archive:", poi["note"] if "note" in poi.keys() else "")
            if not ok_note:
                return
        try:
            if clean in {"defeated", "gone"}:
                db.update_poi(poi_id, poi["poi_type"] if "poi_type" in poi.keys() else poi["label"], archive_note, clean == "defeated", db.get_setting("display_name", ""))
            db.update_poi_status(poi_id, clean, db.get_setting("display_name", ""))
        except Exception:
            db.update_poi(poi_id, clean.title(), archive_note or (poi["note"] if "note" in poi.keys() else ""), clean == "defeated", db.get_setting("display_name", ""))
        self.sync_after_marker_change("poi")
        self.refresh_pois()
        if hasattr(self, "map_view"):
            self.refresh_deep_desert_bases()
        if clean in {"defeated", "gone"}:
            self.notify("Intel Archived", f"Marked as {clean.title()} and moved to Archived Intel.", "success")

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
        self.sync_after_marker_change("poi")
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
        self.sync_after_marker_change("poi")
        self.refresh_pois()
        self.safe_refresh_dashboard()

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
        initial_status = poi_tactical_status(poi_type, False, "")
        try:
            new_id = db.add_poi(x, y, poi_type, note, map_key="deep_desert", guild_code=guild, poi_type=poi_type, created_by=user, status=initial_status)
            self.selected_poi_id_for_map = int(new_id)
        except TypeError:
            new_id = db.add_poi(x, y, poi_type, note)
            self.selected_poi_id_for_map = int(new_id)
        self.log_guild_activity(f"added POI: {poi_type}")
        self.sync_after_marker_change("poi")
        self.refresh_pois()
        self.refresh_deep_desert_bases()
        self.safe_refresh_dashboard()

    # Canonical Hagga Basin sietch list. Keep these alphabetized and do not include the word "Sietch" in the stored/displayed value.
    SEITCHES = [
        "Abbir",
        "al-Mut",
        "Alraab",
        "Barkan",
        "Coanua",
        "Eaqrab",
        "Fajr",
        "Gara Kulon",
        "Hajar",
        "Jacurutu",
        "Kathib",
        "Khafash",
        "Legg",
        "Makab",
        "Nadir",
        "Rajifiri",
        "Ramal",
        "Rifana",
        "Saajid",
        "Sandrat",
        "Ta'lab",
        "Tabr",
        "Tharwa",
        "Umbu",
        "Yaracuwan",
    ]

    def clean_sietch_name(self, value: str) -> str:
        text = (value or "").strip()
        if text.lower().startswith("sietch "):
            text = text[7:].strip()
        if text.lower().startswith("seitch "):
            text = text[7:].strip()
        if text == "Rajifri":
            text = "Rajifiri"
        return text

    def refresh_hagga_map(self):
        if not hasattr(self, "hagga_map_view"):
            return
        image_path = data_dir() / "hagga_basin_map.png"
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
            seitch = self.clean_sietch_name(row["seitch"] if "seitch" in row.keys() else "") or "—"
            status = base_status_label(row["status"] if "status" in row.keys() else "friendly")
            vals = [f"● {member}", seitch, status]
            member_color = profile_color(member)
            status_color = base_status_color(status)
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.UserRole, str(val).lower())
                item.setData(Qt.UserRole + 10, base_id)
                if col == 0:
                    item.setForeground(QBrush(member_color))
                    item.setToolTip(f"{member}'s profile color: {member_color.name()}")
                if col == 2:
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
        moving_id = getattr(self, "_pending_hagga_base_move_id", None)
        if moving_id:
            try:
                db.update_base_position(int(moving_id), float(x), float(y))
                self._pending_hagga_base_move_id = None
                self.sync_after_marker_change("base")
                self.refresh_bases()
                self.safe_refresh_dashboard()
                self.notify("Base Moved", "Base location updated.", "success")
            except Exception as exc:
                self.notify("Move Failed", str(exc), "error")
            return
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
        seitch, ok = QInputDialog.getItem(self, "Sietch", "Base sietch:", self.SEITCHES, 0, False)
        if not ok:
            return
        db.add_base(x, y, base_name.strip(), seitch, guild, user)
        self.log_guild_activity(f"added base: {base_name.strip()}")
        self.sync_after_marker_change("base")
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
        current_sietch = self.clean_sietch_name(base["seitch"] if "seitch" in base.keys() else "")
        current = self.SEITCHES.index(current_sietch) if current_sietch in self.SEITCHES else 0
        seitch, ok = QInputDialog.getItem(self, "Sietch", "Base sietch:", self.SEITCHES, current, False)
        if not ok:
            return
        db.update_base(base_id, base_name.strip(), seitch)
        self.log_guild_activity(f"updated base: {base_name.strip()}")
        self.sync_after_marker_change("base")
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
        self.sync_after_marker_change("base")
        self.refresh_bases()
        self.safe_refresh_dashboard()


    def show_base_context_menu(self, pos):
        if not hasattr(self, "base_table"):
            return
        row = self.base_table.rowAt(pos.y())
        if row < 0:
            return
        self.base_table.selectRow(row)
        self.center_on_base(row, 0)
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        move_action = menu.addAction("Move")
        chosen = menu.exec(self.base_table.viewport().mapToGlobal(pos))
        if chosen == edit_action:
            self.edit_selected_base()
        elif chosen == delete_action:
            self.delete_selected_base()
        elif chosen == move_action:
            self.move_selected_base()

    def move_selected_base(self):
        base_id = self.selected_base_id()
        if not base_id:
            self.notify("Move Base", "Select a base first.", "warning")
            return
        self._pending_hagga_base_move_id = int(base_id)
        self.notify("Move Base", "Double-click the new position on the Hagga Basin map.", "info")

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
        self.sync_after_marker_change("base")
        self.refresh_bases()

    def _current_guild_admin(self) -> bool:
        return role_can_manage_guild()

    def refresh_guild_logo_widgets(self):
        guild = db.get_setting("guild_code", "").strip().upper()
        widgets = [
            getattr(self, "dashboard_guild_logo", None),
            getattr(self, "dashboard_guild_logo_large", None),
            getattr(self, "guild_page_logo", None),
            getattr(self, "settings_guild_logo", None),
        ]
        widgets = [label for label in widgets if qt_alive(label)]
        if not widgets:
            return
        if not guild:
            for label in widgets:
                safe_label_set_pixmap(label, QPixmap())
                safe_label_set_text(label, "NO GUILD")
            return
        setting_path = resolve_local_path(db.get_setting("guild_logo_path", ""))
        path = setting_path if setting_path.exists() else guild_logo_cache_path(guild)
        if not path.exists() and legacy_guild_logo_cache_path().exists():
            path = legacy_guild_logo_cache_path()
        fallback = asset_path("images", "default_guild_logo.png")
        pix = QPixmap(str(path)) if path.exists() else QPixmap(str(fallback)) if fallback.exists() else QPixmap()
        for label in widgets:
            if not qt_alive(label):
                continue
            if not pix.isNull():
                target = label.size() if label.width() > 0 and label.height() > 0 else QSize(96, 96)
                safe_label_set_pixmap(label, pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                safe_label_set_text(label, "")
            else:
                safe_label_set_pixmap(label, QPixmap())
                safe_label_set_text(label, "Guild\nLogo")

    def update_sidebar_status(self):
        guild = db.get_setting("guild_code", "").upper()
        guild_name = db.get_setting("guild_name", "") or (guild if guild else "NO GUILD")
        role = db.get_setting("guild_role", "") or ("MEMBER" if guild else "LOCAL MODE")
        safe_label_set_text(getattr(self, "sidebar_guild_status", None), guild_name.upper())
        safe_label_set_text(getattr(self, "sidebar_role_status", None), role.upper())
        safe_label_set_text(getattr(self, "sidebar_guild_name_display", None), guild_name.upper())
        safe_label_set_text(getattr(self, "sidebar_guild_role_display", None), role.upper())
        self.refresh_guild_logo_widgets()

    def refresh_dashboard_guild_logo(self):
        self.refresh_guild_logo_widgets()

    def sync_guild_logo_from_remote(self):
        """Pull the guild logo from Supabase and update every live logo widget.

        This uses a per-guild cache file and updates the local guild_logo_path setting
        so Dashboard, Guild Admin, and Settings all show the same synced logo.
        """
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or not guild:
            self.refresh_guild_logo_widgets()
            return
        try:
            rows = supabase_request("GET", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}&select=logo_data&limit=1")
            logo_data = (rows[0].get("logo_data") if rows else "") or ""
            path = guild_logo_cache_path(guild)
            if logo_data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(base64.b64decode(logo_data))
                db.set_setting("guild_logo_path", str(path))
            else:
                # Remote has no logo. Clear only the current guild's cached logo so
                # stale logos from another guild do not appear after joining/switching.
                if path.exists():
                    path.unlink()
                if resolve_local_path(db.get_setting("guild_logo_path", "")) == path:
                    db.set_setting("guild_logo_path", "")
        except Exception as exc:
            try:
                if hasattr(self, "sync_manager"):
                    self.sync_manager.statusChanged.emit(f"Guild logo sync skipped: {exc}")
            except Exception:
                pass
        self.refresh_guild_logo_widgets()
        self.refresh_guild_page_identity()

    def upload_guild_logo(self):
        if not self._current_guild_admin():
            self.notify("Permission Denied", "Only owners/officers can upload the guild logo.", "warning")
            return
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            self.notify("Guild Logo", "Join a guild first.", "warning")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose Guild Logo", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            self.notify("Guild Logo", "That image could not be loaded.", "error")
            return

        # Local-first: show the logo immediately, even if the remote database does
        # not yet have guilds.logo_data. This removes the scary Qt/deleted-label
        # error and makes the dashboard/sidebar update instantly.
        cache = guild_logo_cache_path(guild)
        cache.parent.mkdir(parents=True, exist_ok=True)
        pix.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(cache), "PNG")
        db.set_setting("guild_logo_path", str(cache))
        self.refresh_guild_logo_widgets()
        self.refresh_guild_page_identity()
        self.refresh_dashboard()
        self.update_sidebar_status()
        self.notify("Guild Logo Updated", "Logo saved locally. Syncing when remote logo storage is available.", "success")

        url, key = active_supabase()
        if not url or not key or "PASTE_" in key:
            return
        try:
            encoded = base64.b64encode(cache.read_bytes()).decode("ascii")
            updated = supabase_request("PATCH", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}", {"logo_data": encoded})
            # If the remote guild row was missing, upsert it with the logo data so
            # other clients can pull it on their next sync/join.
            if not updated:
                supabase_request("POST", url, key, "guilds?on_conflict=guild_code", [{
                    "guild_code": guild,
                    "guild_name": db.get_setting("guild_name", guild) or guild,
                    "owner_name": db.get_setting("display_name", ""),
                    "logo_data": encoded,
                }])
            self.notify("Guild Logo Synced", "Remote logo updated for all guild members.", "success")
            if hasattr(self, "sync_manager"):
                self.sync_manager.queue("guild", immediate=False)
        except Exception as exc:
            # Do not treat missing logo_data as an upload failure. The local app is
            # already updated and usable; SQL can be added later to enable remote logos.
            msg = str(exc)
            if "logo_data" in msg or "column" in msg.lower():
                self.notify("Logo Saved Locally", "Remote logo column is missing; local logo will still show in this app.", "warning", 5200)
            else:
                self.notify("Logo Sync Pending", msg[:220], "warning", 5200)

    def delete_guild_logo(self):
        if not self._current_guild_admin():
            self.notify("Permission Denied", "Only owners/officers can delete the guild logo.", "warning")
            return
        guild = db.get_setting("guild_code", "").upper()
        path = guild_logo_cache_path(guild)
        dlg = QDialog(self)
        dlg.setWindowTitle("Delete Guild Logo")
        dlg.setMinimumWidth(480)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 20, 22, 20)
        title = QLabel("DELETE GUILD LOGO")
        title.setObjectName("DialogHeader")
        layout.addWidget(title)
        preview = QLabel("No current logo")
        preview.setAlignment(Qt.AlignCenter)
        preview.setFixedHeight(180)
        preview.setObjectName("DashboardGuildLogo")
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                preview.setPixmap(pix.scaled(170, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(preview)
        body = QLabel("This removes the current local guild logo and clears the remote logo when available.")
        body.setWordWrap(True)
        body.setObjectName("DialogBody")
        layout.addWidget(body)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        delete_btn = QPushButton("Delete Logo")
        delete_btn.setObjectName("DangerButton")
        cancel.clicked.connect(dlg.reject)
        delete_btn.clicked.connect(dlg.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(delete_btn)
        layout.addLayout(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        url, key = active_supabase()
        try:
            if guild and url and key:
                supabase_request("PATCH", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild)}", {"logo_data": ""})
            if path.exists():
                path.unlink()
            db.set_setting("guild_logo_path", "")
            self.refresh_guild_logo_widgets()
            self.refresh_guild_page_identity()
            self.refresh_dashboard()
            self.notify("Guild Logo Deleted", "The guild logo was removed.", "success")
        except Exception as exc:
            self.notify("Guild Logo", str(exc), "error", 5200)

    def show_members_roles_dialog(self):
        """Open member/role management only when requested."""
        self.refresh_guild_members()
        dlg = QDialog(self)
        dlg.setWindowTitle("Manage Guild Members")
        dlg.setMinimumSize(720, 500)
        layout = QVBoxLayout(dlg)
        title = QLabel("Manage Guild Members")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        current_role = (db.get_setting("guild_role", "member") or "member").lower()
        if current_role == "owner":
            info_text = "Owners can promote members to officer, demote officers to member, and remove members."
        elif current_role == "officer":
            info_text = "Officers can remove regular members. Role promotion/demotion is owner-only."
        else:
            info_text = "Member management is read-only for your current role."
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setStyleSheet("color:#d6b16b; font-size:13px; font-weight:700;")
        layout.addWidget(info)

        table = StankyTable(["Member", "Role"])
        table.setSortingEnabled(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(table, 1)

        def selected_member():
            row = table.currentRow()
            if row < 0:
                QMessageBox.information(dlg, "Guild Members", "Select a member first.")
                return None, None
            name_item = table.item(row, 0)
            role_item = table.item(row, 1)
            return (name_item.text() if name_item else ""), (role_item.text() if role_item else "member")

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
            update_buttons()

        def update_buttons():
            row = table.currentRow()
            member_role = ""
            member_name = ""
            if row >= 0:
                name_item = table.item(row, 0)
                role_item = table.item(row, 1)
                member_name = name_item.text() if name_item else ""
                member_role = (role_item.text() if role_item else "member").lower()
            owner = (db.get_setting("guild_role", "member") or "member").lower() == "owner"
            admin = self._current_guild_admin()
            current_name = (db.get_setting("display_name", "") or "").strip().lower()
            selected_self = member_name.strip().lower() == current_name
            promote.setEnabled(owner and bool(member_name) and not selected_self and member_role == "member")
            demote.setEnabled(owner and bool(member_name) and not selected_self and member_role == "officer")
            remove.setEnabled(admin and bool(member_name) and not selected_self and member_role != "owner")

        def promote_selected():
            member_name, member_role = selected_member()
            if member_name and self.update_guild_member_role(member_name, member_role, "officer"):
                populate()

        def demote_selected():
            member_name, member_role = selected_member()
            if member_name and self.update_guild_member_role(member_name, member_role, "member"):
                populate()

        def remove_selected():
            member_name, member_role = selected_member()
            if member_name and self.remove_guild_member(member_name, member_role):
                populate()

        buttons = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(populate)
        promote = QPushButton("Promote to Officer")
        promote.setObjectName("PrimaryButton")
        promote.clicked.connect(promote_selected)
        demote = QPushButton("Demote to Member")
        demote.clicked.connect(demote_selected)
        remove = QPushButton("Remove Selected")
        remove.clicked.connect(remove_selected)
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        buttons.addWidget(refresh)
        buttons.addWidget(promote)
        buttons.addWidget(demote)
        buttons.addWidget(remove)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        table.itemSelectionChanged.connect(update_buttons)
        populate()
        dlg.exec()

    def update_guild_member_role(self, member_name: str, old_role: str, new_role: str) -> bool:
        """Promote/demote a guild member. Owners can promote member->officer and demote officer->member."""
        current_role = (db.get_setting("guild_role", "member") or "member").lower()
        if current_role != "owner":
            QMessageBox.warning(self, "Permission Denied", "Only the guild owner can promote or demote members.")
            return False
        member_name = (member_name or "").strip()
        old_role = (old_role or "member").strip().lower()
        new_role = (new_role or "member").strip().lower()
        if not member_name:
            QMessageBox.information(self, "Guild Members", "Select a member first.")
            return False
        if member_name.strip().lower() == (db.get_setting("display_name", "") or "").strip().lower():
            QMessageBox.warning(self, "Guild Members", "You cannot change your own role here.")
            return False
        if old_role == "owner" or new_role == "owner":
            QMessageBox.warning(self, "Guild Members", "Owner transfer is not available from this screen yet.")
            return False
        allowed = {("member", "officer"), ("officer", "member")}
        if (old_role, new_role) not in allowed:
            QMessageBox.information(self, "Guild Members", f"{member_name} is already {old_role}.")
            return False
        action = "promote" if new_role == "officer" else "demote"
        if QMessageBox.question(self, "Update Role", f"{action.title()} {member_name} to {new_role}?") != QMessageBox.Yes:
            return False
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not url or not key or "PASTE_" in key:
            db.upsert_local_member(guild, member_name, new_role)
            self.refresh_guild_members()
            self.refresh_dashboard()
            self.update_guild_nav_visibility()
            self.notify("Role Updated", f"{member_name} is now {new_role.title()}.", "success")
            try:
                self.log_guild_activity(f"{action}d {member_name} to {new_role}")
            except Exception:
                pass
            return True
        try:
            endpoint = f"guild_members?guild_code=eq.{urllib.parse.quote(guild)}&display_name=eq.{urllib.parse.quote(member_name)}"
            supabase_request("POST", url, key, "guild_members?on_conflict=guild_code,display_name", [{
                "guild_code": guild,
                "display_name": member_name,
                "role": new_role,
            }])
            try:
                supabase_request("PATCH", url, key, endpoint, {"role": new_role})
            except Exception:
                pass
            db.upsert_local_member(guild, member_name, new_role)
            self.refresh_guild_members()
            self.refresh_dashboard()
            self.update_guild_nav_visibility()
            self.notify("Role Updated", f"{member_name} is now {new_role.title()}.", "success")
            try:
                self.log_guild_activity(f"{action}d {member_name} to {new_role}")
            except Exception:
                pass
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Role Update Failed", str(exc))
            return False

    def refresh_guild_members(self):
        url, key = active_supabase()
        guild = db.get_setting("guild_code", "").upper()
        if not guild:
            self.current_guild_members = []
            return []
        if not url or not key or "PASTE_" in key:
            rows = [{"display_name": r["display_name"], "role": r["role"]} for r in db.list_local_members(guild)]
            current_name = db.get_setting("display_name", "")
            if current_name and not any((r.get("display_name", "") or "").strip().lower() == current_name.strip().lower() for r in rows):
                role = db.get_setting("guild_role", "member") or "member"
                db.upsert_local_member(guild, current_name, role)
                rows.append({"display_name": current_name, "role": role})
            self.current_guild_members = rows
            return rows
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
        if not url or not key or "PASTE_" in key:
            db.remove_local_member(guild, member_name)
            self.refresh_guild_members()
            self.refresh_dashboard()
            return True
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
        if qt_alive(getattr(self, "join_guild_button", None)):
            self.join_guild_button.setVisible(not joined)
        if qt_alive(getattr(self, "create_guild_button", None)):
            self.create_guild_button.setVisible(not joined)
        if qt_alive(getattr(self, "leave_guild_button", None)):
            self.leave_guild_button.setVisible(joined)
        if qt_alive(getattr(self, "guild_status", None)):
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
        """Create a guild using a local-first flow.

        The old flow waited for remote work and then refreshed/rebuilt widgets. If Qt
        deleted a label during that refresh, the final UI update could raise the
        shiboken "QLabel already deleted" error and show a scary failure even though
        the guild data had already been saved. This flow saves locally immediately,
        refreshes only live widgets, and queues/attempts remote sync in the background.
        """
        display_name = db.get_setting("display_name", "").strip()

        dlg = QDialog(self)
        dlg.setWindowTitle("Create Guild")
        dlg.setMinimumWidth(440)
        dlg_layout = QVBoxLayout(dlg)
        form = QFormLayout()
        display_name_input = QLineEdit(display_name)
        display_name_input.setPlaceholderText("Example: Tony")
        guild_name_input = QLineEdit()
        guild_name_input.setPlaceholderText("Example: Griffin Wing")
        guild_code_input = QLineEdit(make_guild_code())
        guild_code_input.setPlaceholderText("Example: GRIFFIN-WING")
        form.addRow("Display Name", display_name_input)
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

        display_name = display_name_input.text().strip()
        if not display_name:
            QMessageBox.information(self, "Create Guild", "Display name is required.")
            return
        db.set_setting("display_name", display_name)
        guild_name = guild_name_input.text().strip()
        guild_code = ''.join(ch for ch in guild_code_input.text().strip().upper() if ch.isalnum() or ch == '-')
        if not guild_name:
            QMessageBox.information(self, "Create Guild", "Guild name is required.")
            return
        if not guild_code:
            QMessageBox.information(self, "Create Guild", "Guild code is required.")
            return

        old_guild = db.get_setting("guild_code", "").upper()
        if old_guild and old_guild != guild_code.upper():
            db.clear_local_guild_cache(old_guild)

        # Local-first save: the app should reflect the new guild immediately.
        db.set_setting("guild_code", guild_code)
        db.set_setting("guild_name", guild_name)
        db.set_setting("guild_role", "owner")
        db.upsert_local_member(guild_code, display_name, "owner")
        self._specialization_values_dialog(display_name, guild_code)

        def safe_refresh_created_guild():
            try:
                if qt_alive(getattr(self, "guild_code", None)):
                    self.guild_code.setText(guild_code)
                if qt_alive(getattr(self, "guild_role_label", None)):
                    self.guild_role_label.setText("Role: owner")
                self.refresh_guild_surfaces_after_identity_change(refresh_remote=False)
            except RuntimeError as exc:
                # Widget was destroyed during a rebuild. Ignore and schedule one
                # calmer refresh pass instead of reporting a failed guild creation.
                if "already deleted" in str(exc):
                    QTimer.singleShot(150, lambda: self.refresh_guild_surfaces_after_identity_change(refresh_remote=False))
                else:
                    raise
            except Exception:
                # The guild is already saved locally. Avoid a false failure dialog.
                pass

        safe_refresh_created_guild()
        self.notify("Guild Created", f"{guild_code} created locally. Syncing in the background.", "success")

        def remote_create_and_sync():
            url, key = active_supabase()
            if not url or not key or "PASTE_" in key:
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
                    if not existing_code_value or existing_code_value == guild_code.upper():
                        continue
                    existing_members = self._fetch_guild_members_remote(existing_code_value)
                    if existing_members:
                        if hasattr(self, "sync_manager"):
                            self.sync_manager.statusChanged.emit("Remote guild name already exists")
                        return
                    self._delete_remote_guild_completely(existing_code_value)

                existing_code = supabase_request("GET", url, key, f"guilds?guild_code=eq.{urllib.parse.quote(guild_code)}&select=guild_code&limit=1")
                for existing in list(existing_code or []):
                    existing_code_value = (existing.get("guild_code") or "").upper()
                    if existing_code_value != guild_code.upper():
                        continue
                    existing_members = self._fetch_guild_members_remote(existing_code_value)
                    # If there are members and this user is not already the owner,
                    # keep the local guild usable and report sync as pending.
                    if existing_members and not any((m.get("display_name") == display_name and (m.get("role") or "").lower() == "owner") for m in existing_members):
                        if hasattr(self, "sync_manager"):
                            self.sync_manager.statusChanged.emit("Remote guild code already exists")
                        return

                _logo_path = guild_logo_cache_path(guild_code)
                _guild_payload = {
                    "guild_code": guild_code,
                    "guild_name": guild_name,
                    "owner_name": display_name,
                }
                if _logo_path.exists():
                    try:
                        _guild_payload["logo_data"] = base64.b64encode(_logo_path.read_bytes()).decode("ascii")
                    except Exception:
                        pass
                supabase_request("POST", url, key, "guilds?on_conflict=guild_code", [_guild_payload])
                supabase_request("POST", url, key, "guild_members?on_conflict=guild_code,display_name", [{
                    "guild_code": guild_code,
                    "display_name": display_name,
                    "role": "owner",
                }])
                if hasattr(self, "sync_manager"):
                    self.sync_manager.queue("guild", immediate=True)
                QTimer.singleShot(0, lambda: self.refresh_guild_surfaces_after_identity_change(refresh_remote=False))
            except Exception as exc:
                # Do not roll back local guild creation. The app can retry from Settings.
                if hasattr(self, "sync_manager"):
                    self.sync_manager.statusChanged.emit(f"Guild sync pending: {exc}")

        # Delay remote work until after the dialog closes and the UI has repainted.
        QTimer.singleShot(250, remote_create_and_sync)

    def prompt_join_guild(self):
        dlg = GuildJoinDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        display_name = dlg.display_name.text().strip()
        guild = ''.join(ch for ch in dlg.guild_code.text().strip().upper() if ch.isalnum() or ch == '-')
        db.set_setting("display_name", display_name)
        db.set_setting("guild_code", guild)
        # Local-first UI: show the joined guild instantly while remote validation/sync runs.
        if guild:
            db.set_setting("guild_name", db.get_setting("guild_name", guild) or guild)
            db.set_setting("guild_role", db.get_setting("guild_role", "member") or "member")
            db.upsert_local_member(guild, display_name, db.get_setting("guild_role", "member") or "member")
            self._specialization_values_dialog(display_name, guild)
            self.refresh_guild_surfaces_after_identity_change(refresh_remote=False)
            QTimer.singleShot(50, lambda: self.refresh_guild_surfaces_after_identity_change(refresh_remote=False))
        self.join_guild(show_success=True)

    def join_guild(self, show_success: bool = True):
        old_guild = db.get_setting("guild_code", "").upper()
        display_name = db.get_setting("display_name", "").strip()
        guild = db.get_setting("guild_code", "").strip().upper()
        guild = ''.join(ch for ch in guild if ch.isalnum() or ch == '-')
        url, key = active_supabase()
        if not guild or not display_name:
            QMessageBox.information(self, "Guild", "Enter display name and guild code first.")
            return
        if not url or not key or "PASTE_" in key:
            if old_guild and old_guild != guild:
                db.clear_local_guild_cache(old_guild)
            db.set_setting("display_name", display_name)
            db.set_setting("guild_code", guild)
            db.set_setting("guild_name", db.get_setting("guild_name", guild) or guild)
            db.set_setting("guild_role", db.get_setting("guild_role", "member") or "member")
            db.upsert_local_member(guild, display_name, db.get_setting("guild_role", "member") or "member")
            if hasattr(self, "guild_code"):
                self.guild_code.setText(guild)
            if hasattr(self, "display_name"):
                self.display_name.setText(display_name)
            if hasattr(self, "guild_role_label"):
                self.guild_role_label.setText("Role: " + (db.get_setting("guild_role", "member") or "member"))
            self.refresh_guild_surfaces_after_identity_change(refresh_remote=False)
            QTimer.singleShot(200, lambda: self.refresh_guild_surfaces_after_identity_change(refresh_remote=False))
            if show_success:
                self.notify("Guild Joined", f"Joined local guild {guild}.", "success")
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
            self.refresh_guild_surfaces_after_identity_change(refresh_remote=False)
            self.sync_guild_logo_from_remote()
            QTimer.singleShot(200, lambda: self.refresh_guild_surfaces_after_identity_change(refresh_remote=False))
            if show_success:
                self.notify("Guild Joined", f"Joined guild {guild}.", "success")
        except Exception as exc:
            QMessageBox.critical(self, "Join Guild Failed", str(exc))



def main() -> None:
    # Quiet noisy Qt WebEngine/ad-script logging before the embedded map starts.
    try:
        QLoggingCategory.setFilterRules("qt.webenginecontext.debug=false\njs.warning=false\njs.info=false")
    except Exception:
        pass
    app = QApplication(sys.argv)
    try:
        font = QFont("Segoe UI")
        font.setPointSize(10)
        app.setFont(font)
    except Exception:
        pass
    app.setStyleSheet(premium_qss(asset_path('backgrounds', 'sidebar_texture.png')))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
