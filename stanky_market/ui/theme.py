from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class Palette:
    matte_black: str = "#090909"
    deep_charcoal: str = "#121212"
    panel: str = "#15120e"
    panel_2: str = "#1d1710"
    bronze: str = "#2B2117"
    brass: str = "#8D6A2B"
    gold: str = "#D6AE5A"
    gold_soft: str = "#E8C979"
    warm_white: str = "#F5F3ED"
    muted: str = "#9E927F"
    muted_2: str = "#6F6659"
    success: str = "#55D68A"
    warning: str = "#E1A646"
    error: str = "#D64B4B"
    info: str = "#58C7D9"


PALETTE = Palette()
APP_VERSION_LABEL_PREFIX = "v"


def premium_qss(sidebar_texture: Path | None = None) -> str:
    sidebar_image = ""
    if sidebar_texture and sidebar_texture.exists():
        sidebar_image = f"background-image: url('{sidebar_texture.resolve().as_posix()}'); background-position: center;"
    return f"""
* {{
    font-family: 'Segoe UI Variable', 'Segoe UI', Arial;
    font-size: 14px;
    color: {PALETTE.warm_white};
    selection-background-color: {PALETTE.brass};
    selection-color: {PALETTE.warm_white};
}}
QMainWindow, QWidget#Root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {PALETTE.matte_black}, stop:0.55 #0d0c0a, stop:1 #120e09);
}}
QToolTip {{
    background: #15120e;
    color: {PALETTE.warm_white};
    border: 1px solid {PALETTE.gold};
    border-radius: 8px;
    padding: 8px 10px;
}}
QFrame#SideBar {{
    {sidebar_image}
    background-color: #070807;
    border-right: 1px solid rgba(214,174,90,0.28);
}}
QFrame#SideHeader, QFrame#SideFooter, QFrame#MiniStatus {{
    background: rgba(18,18,18,0.78);
    border: 1px solid rgba(214,174,90,0.18);
    border-radius: 14px;
}}
QLabel#Brand {{
    color: {PALETTE.gold_soft};
    font-size: 26px;
    font-weight: 900;
    letter-spacing: 2px;
}}
QLabel#BrandSub, QLabel#MicroLabel {{
    color: {PALETTE.muted};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
}}
QLabel#VersionPill {{
    color: {PALETTE.gold_soft};
    background: rgba(214,174,90,0.11);
    border: 1px solid rgba(214,174,90,0.32);
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 900;
}}
QToolButton#NavButton {{
    padding: 10px 12px;
    border: 1px solid transparent;
    border-radius: 14px;
    background: rgba(18,18,18,0.38);
    color: {PALETTE.warm_white};
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 1.4px;
    text-align: left;
}}
QToolButton#NavButton:hover {{
    background: rgba(214,174,90,0.11);
    border: 1px solid rgba(214,174,90,0.34);
    color: #fff7dc;
}}
QToolButton#NavButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(214,174,90,0.30), stop:1 rgba(43,33,23,0.72));
    border: 1px solid rgba(214,174,90,0.62);
    color: #fff4ce;
}}
QToolButton#NavButton::menu-indicator {{ image: none; }}
QFrame#Hero {{
    background-color: #15110b;
    border: 1px solid rgba(214,174,90,0.48);
    border-radius: 18px;
}}
QLabel#HeroKicker {{
    color: {PALETTE.gold};
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 3px;
}}
QLabel#HeroTitle {{
    color: {PALETTE.warm_white};
    font-size: 40px;
    font-weight: 950;
    letter-spacing: 1.5px;
}}
QLabel#HeroSub {{
    color: #d0c0a1;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.2px;
}}
QFrame#Panel, QFrame#Card, QFrame#CommandCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(21,18,14,0.96), stop:1 rgba(12,12,11,0.96));
    border: 1px solid rgba(214,174,90,0.26);
    border-radius: 14px;
}}
QFrame#Panel:hover, QFrame#Card:hover, QFrame#CommandCard:hover {{
    border: 1px solid rgba(214,174,90,0.46);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(31,25,17,0.98), stop:1 rgba(13,13,12,0.98));
}}
QLabel#SectionTitle, QLabel#CardTitle {{
    color: {PALETTE.gold_soft};
    font-size: 13px;
    font-weight: 950;
    letter-spacing: 1.8px;
}}
QLabel#CardValue {{
    color: {PALETTE.warm_white};
    font-size: 30px;
    font-weight: 950;
}}
QPushButton, QToolButton#SmallButton {{
    background: rgba(25,22,17,0.95);
    border: 1px solid rgba(214,174,90,0.34);
    border-radius: 11px;
    padding: 9px 14px;
    color: {PALETTE.warm_white};
    font-size: 13px;
    font-weight: 900;
    letter-spacing: .8px;
}}
QPushButton:hover, QToolButton#SmallButton:hover {{
    background: rgba(43,33,23,0.98);
    border: 1px solid rgba(214,174,90,0.74);
    color: #fff7dc;
}}
QPushButton:pressed {{
    background: rgba(141,106,43,0.44);
    padding-top: 10px;
    padding-bottom: 8px;
}}
QPushButton#PrimaryButton, QPushButton#GoldButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #B9872A, stop:1 #6E4E18);
    border: 1px solid rgba(232,201,121,0.85);
    color: #fff8dc;
}}
QLineEdit, QTextEdit, QSpinBox, QComboBox {{
    background: rgba(8,8,7,0.80);
    border: 1px solid rgba(214,174,90,0.24);
    border-radius: 10px;
    padding: 8px 10px;
    color: {PALETTE.warm_white};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid rgba(214,174,90,0.70);
    background: rgba(14,13,11,0.95);
}}
QTableWidget {{
    background: rgba(7,7,6,0.54);
    alternate-background-color: rgba(214,174,90,0.055);
    border: 1px solid rgba(214,174,90,0.18);
    border-radius: 12px;
    gridline-color: rgba(214,174,90,0.10);
    color: {PALETTE.warm_white};
}}
QHeaderView::section {{
    background: rgba(43,33,23,0.94);
    color: {PALETTE.gold_soft};
    border: 0;
    border-right: 1px solid rgba(214,174,90,0.16);
    padding: 8px;
    font-weight: 950;
    letter-spacing: 1px;
}}
QTableWidget::item {{
    padding: 9px;
    border-bottom: 1px solid rgba(214,174,90,0.06);
}}
QTableWidget::item:selected {{
    background: rgba(214,174,90,0.25);
    color: #fff8dc;
}}
QTabWidget::pane {{
    border: 1px solid rgba(214,174,90,0.22);
    border-radius: 14px;
    background: rgba(10,10,9,0.45);
}}
QTabBar::tab {{
    background: rgba(18,18,18,0.72);
    color: {PALETTE.muted};
    border: 1px solid rgba(214,174,90,0.16);
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 10px 16px;
    font-weight: 900;
}}
QTabBar::tab:selected {{
    color: {PALETTE.gold_soft};
    background: rgba(43,33,23,0.92);
    border: 1px solid rgba(214,174,90,0.46);
}}
QScrollBar:vertical {{ background: rgba(8,8,7,0.3); width: 12px; margin: 2px; border-radius: 6px; }}
QScrollBar::handle:vertical {{ background: rgba(214,174,90,0.42); border-radius: 6px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(214,174,90,0.68); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: rgba(8,8,7,0.3); height: 12px; margin: 2px; border-radius: 6px; }}
QScrollBar::handle:horizontal {{ background: rgba(214,174,90,0.42); border-radius: 6px; min-width: 36px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QCheckBox {{ color: {PALETTE.warm_white}; font-weight: 800; spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid rgba(214,174,90,0.48); background: rgba(8,8,7,0.90); }}
QCheckBox::indicator:checked {{ background: {PALETTE.gold}; border: 1px solid {PALETTE.gold_soft}; }}
QProgressBar {{
    background: rgba(8,8,7,0.75);
    border: 1px solid rgba(214,174,90,0.24);
    border-radius: 9px;
    text-align: center;
    color: {PALETTE.warm_white};
}}
QProgressBar::chunk {{ background: rgba(214,174,90,0.75); border-radius: 8px; }}

QFrame#PremiumStatCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(28,22,14,0.98), stop:1 rgba(8,8,7,0.98));
    border: 1px solid rgba(214,174,90,0.30);
    border-radius: 16px;
}}
QFrame#PremiumStatCard:hover {{
    border: 1px solid rgba(214,174,90,0.62);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(42,31,18,0.98), stop:1 rgba(12,12,10,0.98));
}}
QLabel#CardHint, QLabel#NewsBody {{
    color: #B5AA97;
    font-size: 12px;
    font-weight: 650;
}}
QFrame#QuickActionCard, QFrame#NewsCard, QFrame#MarketMoverCard {{
    background: rgba(9,9,8,0.64);
    border: 1px solid rgba(214,174,90,0.18);
    border-radius: 14px;
}}
QFrame#QuickActionCard:hover, QFrame#NewsCard:hover, QFrame#MarketMoverCard:hover {{
    background: rgba(43,33,23,0.72);
    border: 1px solid rgba(214,174,90,0.52);
}}
QLabel#ActionIcon {{
    color: #E8C979;
    font-size: 24px;
    font-weight: 950;
    min-width: 32px;
}}
QLabel#ActionTitle, QLabel#NewsTitle {{
    color: #F5F3ED;
    font-size: 13px;
    font-weight: 950;
    letter-spacing: 1.3px;
}}

QMessageBox, QDialog {{ background: {PALETTE.deep_charcoal}; }}
"""


def with_alpha(hex_color: str, alpha: int) -> QColor:
    c = QColor(hex_color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c
