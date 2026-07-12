from __future__ import annotations

from .tactical_theme import theme_colors


def premium_qss(sidebar_texture=None, theme_key: str | None = "dune", page_texture=None) -> str:
    c = theme_colors(theme_key)
    sidebar_image = ""
    page_image = ""
    # Sidebar art is painted by ThemedSidebar so painter opacity works.
    # QSS border-image has no opacity control and would cover that rendering.
    sidebar_image = "border-image: none;"
    try:
        if page_texture and page_texture.exists():
            texture = str(page_texture).replace("\\", "/")
            page_image = f"border-image: url({texture}) 0 0 0 0 stretch stretch;"
    except Exception:
        page_image = ""

    return f"""
    QWidget {{
        background: {c['bg']};
        color: {c['text']};
        font-family: Rajdhani, Segoe UI, Arial;
        font-size: 14px;
        selection-background-color: {c['accent_soft']};
    }}
    QWidget#Root {{
        background: {c['bg']};
    }}
    QWidget#ContentRoot {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c['bg']}, stop:0.55 {c['secondary']}, stop:1 #090A0B);
        {page_image}
    }}
    QFrame#SideBar {{
        min-height: 100%;
        background-color: {c['bg']};
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #070707, stop:0.58 {c['panel']}, stop:1 {c['accent_faint']});
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
        background: {c['panel']};
        border: 1px solid {c['border']};
        border-radius: 8px;
    }}
    QFrame#Panel:hover, QFrame#Card:hover, QFrame#CommandCard:hover, QFrame#PremiumStatCard:hover, QFrame#NewsCard:hover {{
        border: 1px solid {c['accent_soft']};
        background: {c['panel_hover']};
    }}
    QFrame#Hero {{
        border: 1px solid {c['accent']};
        border-radius: 8px;
        background: {c['bg']};
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
        background: {c['secondary']};
        border: 1px solid {c['border']};
        border-radius: 7px;
        padding: 8px 13px;
        color: {c['text']};
        font-weight: 800;
    }}
    QPushButton:hover {{ background: {c['hover']}; border: 1px solid {c['accent']}; }}
    QPushButton#PrimaryButton {{ background: {c['accent_faint']}; border: 1px solid {c['accent']}; color: {c['text']}; }}
    QPushButton#SettingsToolButton {{ background: {c['secondary']}; border: 1px solid {c['accent_soft']}; color: {c['text']}; }}
    QPushButton#SettingsToolButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['accent_faint']}, stop:1 {c['hover']}); border: 2px solid {c['accent']}; color: #FFFFFF; padding: 7px 12px; }}
    QPushButton#SettingsToolButton:pressed {{ background: {c['accent_soft']}; border: 2px solid {c['accent']}; color: #FFFFFF; padding: 7px 12px; }}
    QPushButton#SettingsToolButton:focus {{ border: 2px solid {c['accent']}; }}
    QPushButton#DangerButton {{ background: rgba(150,40,34,0.28); border: 1px solid #C94F45; color: #FFDAD6; }}

    QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateTimeEdit, QDateEdit {{
        background: rgba(0, 0, 0, 0.34);
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



def reference_overrides(theme_key: str | None = "dune") -> str:
    """Final high-specificity pass for the compact guild-dashboard design."""
    c = theme_colors(theme_key)
    accent = c["accent"]
    return f"""
    QWidget#Root, QWidget#ContentRoot, QStackedWidget {{ background: #111111; }}
    QWidget#ModernContentPage {{ background:#111111; }}
    QFrame#PageTitleBanner {{
        background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(62,34,16,150), stop:0.55 rgba(31,23,18,165), stop:1 rgba(18,18,18,230));
        border:none; border-radius:8px; min-height:88px;
    }}
    QLabel#PageTitle {{ color:#FFFFFF; font-family:"Segoe UI"; font-size:28px; font-weight:900; }}
    QLabel#PageSubtitle {{ color:rgba(255,255,255,0.55); font-size:13px; font-weight:500; }}
    QFrame#ImmersiveSidebar {{ background: transparent; border: none; }}
    QFrame#SidebarIdentity {{ background:transparent; border:none; min-height:196px; max-height:196px; }}
    QLabel#SidebarIdentityUser {{ color:#F4F4F4; font-size:13px; font-weight:800; }}
    QLabel#SidebarIdentityGuild {{ color:#C8C4BF; font-size:11px; font-weight:600; }}
    QLabel#SidebarChevron {{ color:#BEB8B1; font-size:13px; }}
    QLineEdit#SidebarSearch {{
        background:#1B1B1B; color:#E9E9E9; border:1px solid rgba(255,255,255,0.10);
        border-radius:7px; min-height:27px; padding:4px 10px; font-size:12px;
    }}
    QLineEdit#SidebarSearch:focus {{ border:1px solid {accent}; }}
    QLabel#SidebarSectionLabel {{ color:{accent}; font-size:12px; font-weight:900; letter-spacing:1px; padding:10px 8px 6px 8px; }}
    QFrame#SidebarSeparator {{ color:rgba(255,255,255,0.12); background:rgba(255,255,255,0.12); max-height:1px; }}
    QLabel#SidebarFooterText {{ color:rgba(255,255,255,0.30); font-size:9px; font-weight:700; letter-spacing:1px; padding:8px; }}

    QFrame#NavButton {{ min-height:40px; max-height:40px; border-radius:7px; background:transparent; border:none; }}
    QFrame#NavButton:hover {{ background:rgba(255,255,255,0.045); border:none; }}
    QFrame#NavButton[active="true"] {{ background:rgba(255,255,255,0.035); border:none; }}
    QFrame#NavButton[active="true"] QLabel#NavTitle {{ color:{accent}; }}
    QLabel#NavTitle {{ color:#E6E4E1; font-family:"Segoe UI"; font-size:12px; font-weight:700; letter-spacing:0px; }}
    QLabel#NavSub {{ color:rgba(255,255,255,0.35); font-size:9px; }}
    QLabel#NavChevron {{ color:rgba(255,255,255,0.42); font-size:11px; }}
    QFrame#NavAccentBar {{ background:{accent}; border-radius:1px; max-width:2px; }}

    QFrame#AppTopBar {{ background:#121212; border:none; min-height:46px; max-height:46px; }}
    QLabel#TopBarIcon {{ color:#E5E5E5; font-size:15px; padding-right:8px; }}
    QLabel#TopBarPageTitle {{ color:rgba(255,255,255,0.42); font-size:12px; font-weight:600; }}
    QPushButton#TopBarButton {{
        background:#181818; color:#E9E6E2; border:1px solid rgba(255,255,255,0.12); border-radius:6px;
        min-height:28px; max-height:28px; padding:0 11px; font-size:11px; font-weight:700;
    }}
    QPushButton#TopBarButton:hover {{ border-color:{accent}; color:#FFFFFF; background:#202020; }}

    QWidget#ModernDashboardPage, QWidget#DashboardScrollContent, QScrollArea#DashboardScrollArea,
    QScrollArea#DashboardScrollArea > QWidget > QWidget {{ background:#111111; }}
    QFrame#DashboardTitleBanner {{
        background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['accent_faint']}, stop:0.55 {c['secondary']}, stop:1 #121212);
        border:none; border-radius:8px; min-height:110px;
    }}
    QLabel#DashboardPageTitle {{ color:#FFFFFF; font-family:"Segoe UI"; font-size:31px; font-weight:900; }}
    QLabel#DashboardTitleInfo {{ color:{accent}; font-size:16px; padding-bottom:5px; }}
    QLabel#DashboardPageSubtitle {{ color:rgba(255,255,255,0.58); font-size:14px; font-weight:500; }}

    QFrame#DashboardGuildHero {{
        background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['accent_faint']}, stop:0.42 {c['panel']}, stop:1 {c['secondary']});
        border:1px solid {c['accent_soft']}; border-radius:9px; min-height:150px;
    }}
    QLabel#DashboardGuildName {{ color:#FFFFFF; font-family:"Segoe UI"; font-size:22px; font-weight:850; }}
    QLabel#DashboardUserName {{ color:#ECE9E5; font-size:16px; font-weight:800; }}
    QLabel#DashboardGuildRole, QLabel#DashboardWorldSietch {{ color:rgba(255,255,255,0.50); font-size:11px; font-weight:700; }}

    QFrame#ModernStatCard {{ border:1px solid {c['accent_soft']}; border-radius:9px; min-height:104px; max-height:118px; }}
    QFrame#ModernStatCard[tone="teal"] {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['accent_faint']}, stop:1 {c['panel']}); }}
    QFrame#ModernStatCard[tone="blue"] {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['secondary']}, stop:1 {c['accent_faint']}); }}
    QFrame#ModernStatCard[tone="purple"] {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['panel']}, stop:0.55 {c['accent_faint']}, stop:1 {c['secondary']}); }}
    QFrame#ModernStatCard[tone="orange"] {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['accent_faint']}, stop:0.65 {c['secondary']}, stop:1 {c['panel']}); }}
    QFrame#ModernStatCard:hover {{ border:1px solid {c['accent']}; }}
    QLabel#ModernCardTitle {{ color:rgba(255,255,255,0.62); font-size:11px; font-weight:700; }}
    QLabel#ModernCardValue {{ color:#FFFFFF; font-size:23px; font-weight:900; }}
    QLabel#ModernCardHint {{ color:rgba(255,255,255,0.42); font-size:10px; }}

    QFrame#SettingsPanel, QFrame#GlassCard, QFrame#DashboardMembersPanel, QFrame#DashboardAccessCard, QFrame#DashboardStatusBar,
    QFrame#Card, QFrame#Panel, QFrame#SectionCard, QFrame#CommandCard, QFrame#SettingsCard,
    QFrame#GuildCard, QFrame#CatalogCard, QFrame#MapPanel, QFrame#TimerCard, QFrame#ContentCard {{
        background:#1B1B1B; border:1px solid rgba(255,255,255,0.10); border-radius:9px;
    }}
    QLabel#DashboardSectionTitle, QLabel#SectionTitle {{ color:#FFFFFF; font-family:"Segoe UI"; font-size:18px; font-weight:850; letter-spacing:0px; }}
    QLabel#DashboardSectionSubtitle {{ color:rgba(255,255,255,0.46); font-size:12px; }}
    QFrame#NewsCard, QFrame#MemberCard {{ background:#202020; border:1px solid rgba(255,255,255,0.08); border-radius:8px; }}
    QFrame#NewsCard:hover, QFrame#MemberCard:hover {{ background:#252525; border-color:rgba(255,255,255,0.16); }}

    QTabWidget::pane {{ background:#191919; border:1px solid rgba(255,255,255,0.10); border-radius:8px; }}
    QTabBar::tab {{ background:transparent; color:rgba(255,255,255,0.58); border-radius:6px; padding:7px 12px; min-height:22px; min-width:70px; font-size:12px; }}
    QTabBar::tab:selected {{ background:{accent}; color:#111111; }}
    QTableView, QTableWidget, QListView, QListWidget, QTreeView, QTreeWidget {{ background:#171717; alternate-background-color:#1D1D1D; border:1px solid rgba(255,255,255,0.10); border-radius:8px; gridline-color:rgba(255,255,255,0.05); }}
    QHeaderView::section {{ background:#202020; color:#DCD8D3; border:none; border-bottom:1px solid rgba(255,255,255,0.10); padding:8px 10px; font-size:11px; font-weight:800; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QComboBox {{ background:#202020; color:#EFEFEF; border:1px solid rgba(255,255,255,0.11); border-radius:7px; padding:6px 9px; min-height:22px; }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color:{accent}; }}
    QPushButton {{ background:#242424; color:#EAE7E3; border:1px solid rgba(255,255,255,0.12); border-radius:7px; padding:7px 12px; min-height:23px; font-weight:700; }}
    QPushButton:hover {{ background:#2B2B2B; border-color:{accent}; }}

    /* Settings cards are intentionally text-only. */
    QFrame#SettingsPanel QLabel[class~="icon"],
    QFrame#SettingsPanel QWidget#SettingsIcon,
    QFrame#SettingsPanel QWidget#ThemeIcon,
    QFrame#SettingsPanel QWidget#ActionIcon,
    QFrame#SettingsPanel QLabel#SettingsHeaderIcon,
    QFrame#SettingsPanel QLabel#ThemeSelectionIcon,
    QFrame#SettingsPanel QLabel#SettingsActionIcon {{
        min-width:0px; max-width:0px; margin:0px; padding:0px; border:none; background:transparent;
    }}
    QProgressBar {{ background:#2A2A2A; border:none; border-radius:4px; min-height:8px; max-height:8px; text-align:center; }}
    QProgressBar::chunk {{ background:{accent}; border-radius:4px; }}
    QScrollBar:vertical {{ background:#151515; width:8px; margin:0; }}
    QScrollBar::handle:vertical {{ background:#55514D; min-height:28px; border-radius:4px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    """


# Final no-header override for the streamlined content layout.
def no_page_header_overrides() -> str:
    return """
    QFrame#PageTitleBanner, QFrame#DashboardTitleBanner {
        min-height:0px; max-height:0px; margin:0px; padding:0px;
        border:none; background:transparent;
    }
    """
