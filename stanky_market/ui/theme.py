from __future__ import annotations

from .tactical_theme import theme_colors


def premium_qss(sidebar_texture=None, theme_key: str | None = "dune") -> str:
    c = theme_colors(theme_key)
    sidebar_image = ""
    try:
        if sidebar_texture and sidebar_texture.exists():
            texture = str(sidebar_texture).replace("\\", "/")
            sidebar_image = f"border-image: url({texture}) 0 0 0 0 stretch stretch;"
    except Exception:
        sidebar_image = ""

    return f"""
    QWidget {{
        background: {c['bg']};
        color: {c['text']};
        font-family: Rajdhani, Segoe UI, Arial;
        font-size: 14px;
        selection-background-color: {c['accent_soft']};
    }}
    QWidget#Root {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c['bg']}, stop:0.55 #0C0D0E, stop:1 #15120E);
    }}
    QFrame#SideBar {{
        min-height: 100%;
        background-color: #0A0B0C;
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #070707, stop:0.55 {c['panel']}, stop:1 {c['accent_faint']});
        {sidebar_image}
        border-right: 1px solid {c['accent']};
    }}
    QFrame#SideFooter, QFrame#SideHeader {{
        background: rgba(12, 13, 14, 0.72);
        border: 1px solid {c['border']};
        border-radius: 10px;
    }}
    QFrame#NavButton {{
        min-height: 82px;
        background: rgba(12, 13, 14, 0.70);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
    }}
    QFrame#NavButton:hover {{
        background: {c['hover']};
        border: 1px solid {c['accent_soft']};
    }}
    QFrame#NavButton[active="true"] {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['accent_faint']}, stop:1 rgba(8,9,10,0.82));
        border: 1px solid {c['accent']};
    }}
    QFrame#NavIconBubble {{
        background: transparent;
        border: none;
    }}
    QFrame#NavAccentBar {{
        background: {c['accent']};
        border-radius: 2px;
    }}
    QWidget#HexNavIcon, QWidget#NavIconWidget {{
        background: transparent;
    }}
    QLabel#NavTitle {{
        background: transparent;
        color: {c['text']};
        font-family: Orbitron, Rajdhani, Segoe UI;
        font-size: 17px;
        font-weight: 900;
    }}
    QLabel#NavSub {{ background: transparent; color: {c['muted']}; font-size: 12px; font-weight: 700; }}
    QLabel#NavChevron {{ background: transparent; color: {c['accent']}; font-size: 18px; font-weight: 900; }}
    QLabel#NavUserName {{ background: transparent; color: {c['text']}; font-size: 15px; font-weight: 950; }}
    QLabel#NavUserStatus {{ background: transparent; color: #54D66A; font-size: 18px; font-weight: 950; }}
    QLabel#MascotLogo {{ background: transparent; border: none; }}

    QFrame#Panel, QFrame#Card, QFrame#CommandCard, QFrame#PremiumStatCard, QFrame#NewsCard, QFrame#QuickActionCard {{
        background: rgba(18, 19, 21, 0.86);
        border: 1px solid {c['border']};
        border-radius: 8px;
    }}
    QFrame#Panel:hover, QFrame#Card:hover, QFrame#CommandCard:hover, QFrame#PremiumStatCard:hover, QFrame#NewsCard:hover {{
        border: 1px solid {c['accent_soft']};
        background: rgba(24, 26, 28, 0.94);
    }}
    QFrame#Hero {{
        border: 1px solid {c['accent']};
        border-radius: 8px;
        background: #080706;
    }}
    QLabel {{ background: transparent; border: none; }}
    QLabel#HeroKicker {{ color: {c['accent']}; font-size: 13px; font-weight: 950; }}
    QLabel#HeroTitle {{ color: #FFFFFF; font-size: 32px; font-weight: 950; }}
    QLabel#HeroSub {{ color: {c['muted']}; font-size: 15px; font-weight: 700; }}
    QLabel#SectionTitle {{ color: {c['accent']}; font-family: Orbitron, Rajdhani, Segoe UI; font-size: 18px; font-weight: 900; }}
    QLabel#SubsectionTitle {{ color: {c['text']}; font-size: 20px; font-weight: 900; }}
    QLabel#CardTitle {{ color: {c['muted']}; font-size: 13px; font-weight: 850; }}
    QLabel#CardValue {{ color: {c['text']}; font-size: 30px; font-weight: 950; }}
    QLabel#CardHint, QLabel#MutedLabel, QLabel#MutedText {{ color: {c['muted']}; font-size: 12px; font-weight: 650; }}
    QLabel#MicroLabel {{ color: {c['muted']}; font-size: 11px; font-weight: 850; }}
    QLabel#VersionPill, QLabel#GuildStatusPill, QLabel#TimeZoneBanner {{
        color: {c['text']};
        background: {c['accent_faint']};
        border: 1px solid {c['accent_soft']};
        border-radius: 8px;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: 850;
    }}
    QLabel#DashboardGuildLogo {{
        color: {c['accent']};
        background: rgba(0,0,0,0.30);
        border: 1px solid {c['accent_soft']};
        border-radius: 8px;
        font-size: 22px;
        font-weight: 950;
    }}
    QLabel#NewsTitle {{ color: {c['text']}; font-size: 15px; font-weight: 900; }}
    QLabel#NewsBody {{ color: {c['text']}; font-size: 13px; }}

    QPushButton {{
        background: rgba(19, 20, 22, 0.92);
        border: 1px solid {c['border']};
        border-radius: 7px;
        padding: 8px 13px;
        color: {c['text']};
        font-weight: 800;
    }}
    QPushButton:hover {{ background: {c['hover']}; border: 1px solid {c['accent']}; }}
    QPushButton#PrimaryButton {{ background: {c['accent_faint']}; border: 1px solid {c['accent']}; color: {c['text']}; }}
    QPushButton#DangerButton {{ background: rgba(150,40,34,0.28); border: 1px solid #C94F45; color: #FFDAD6; }}

    QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateTimeEdit, QDateEdit {{
        background: rgba(6, 7, 8, 0.86);
        border: 1px solid {c['border']};
        border-radius: 7px;
        padding: 7px 9px;
        color: {c['text']};
    }}
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {c['accent']}; }}
    QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 8px; background: rgba(12,13,14,0.68); }}
    QTabBar::tab {{ background: rgba(18,19,21,0.80); color: {c['muted']}; padding: 9px 15px; border: 1px solid {c['border']}; border-top-left-radius: 7px; border-top-right-radius: 7px; }}
    QTabBar::tab:selected {{ color: {c['text']}; border-color: {c['accent']}; background: {c['accent_faint']}; }}
    QTableWidget {{ background: rgba(9,10,11,0.78); gridline-color: rgba(255,255,255,0.06); border: 1px solid {c['border']}; border-radius: 8px; }}
    QHeaderView::section {{ background: rgba(24,26,28,0.96); color: {c['accent']}; padding: 8px; border: none; font-weight: 900; }}
    QTableWidget::item:selected {{ background: {c['accent_faint']}; color: #FFFFFF; }}
    QMenu {{ background: #111315; border: 1px solid {c['border']}; border-radius: 8px; padding: 5px; }}
    QMenu::item {{ padding: 9px 26px 9px 14px; color: {c['text']}; font-size: 14px; }}
    QMenu::item:selected {{ background: {c['hover']}; }}
    QScrollBar:vertical {{ background: rgba(0,0,0,0.22); width: 12px; border-radius: 6px; }}
    QScrollBar::handle:vertical {{ background: {c['accent_soft']}; border-radius: 6px; min-height: 36px; }}
    """
