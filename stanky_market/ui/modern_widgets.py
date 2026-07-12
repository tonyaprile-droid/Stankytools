from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFontDatabase, QIcon
from shiboken6 import isValid
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget
)

from ..paths import asset_dir
from .tactical_theme import theme_colors


def _apply_glow(widget: QWidget, alpha: int = 42, blur: int = 34, y: int = 8) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(68, 96, 160, alpha))
    widget.setGraphicsEffect(effect)


def svg_icon(name: str) -> QIcon:
    path = asset_dir() / "icons" / f"{name}.svg"
    return QIcon(str(path)) if path.exists() else QIcon()


def load_ui_fonts() -> None:
    """Load bundled fonts when present; safely fall back to Segoe UI."""
    font_root = asset_dir() / "fonts"
    if font_root.exists():
        for font_file in font_root.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_file))
    app = QApplication.instance()
    if app is not None:
        app.setFont(app.font())


class GlassCard(QFrame):
    def __init__(self, parent=None, *, compact: bool = False, glow: bool = True):
        super().__init__(parent)
        self.setObjectName("GlassCardCompact" if compact else "GlassCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if glow:
            _apply_glow(self, alpha=30 if compact else 42, blur=26 if compact else 34, y=5 if compact else 8)


class ModernStatusPill(QLabel):
    def __init__(self, text: str = "", status: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setAlignment(Qt.AlignCenter)
        self.setProperty("status", status)
        self.setMinimumHeight(26)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_status(self, status: str) -> None:
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_value(self, value: str) -> None:
        self.setText(str(value))


class ModernStatCard(GlassCard):
    clicked = Signal()

    def __init__(self, title: str, value: str = "-", hint: str = "", *, tone: str = "gold", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("ModernStatCard")
        self.setProperty("tone", tone)
        self.setMinimumHeight(166)
        self.setCursor(Qt.PointingHandCursor)
        self._title = str(title)
        self._value = str(value)
        self._hint = str(hint)
        self._icon_name = str(icon)
        self._build_content()

    @staticmethod
    def _alive(widget) -> bool:
        try:
            return widget is not None and isValid(widget)
        except Exception:
            return False

    def _build_content(self) -> None:
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None and self._alive(widget):
                    widget.deleteLater()
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(11)
        top = QHBoxLayout()
        top.setSpacing(10)
        self.title_label = QLabel(self._title.upper(), self)
        self.title_label.setObjectName("ModernCardTitle")
        top.addWidget(self.title_label, 1)
        if self._icon_name:
            self.icon_label = QLabel(self)
            self.icon_label.setPixmap(svg_icon(self._icon_name).pixmap(QSize(22, 22)))
            top.addWidget(self.icon_label)
        layout.addLayout(top)
        layout.addStretch(1)
        self.value_label = QLabel(self._value, self)
        self.value_label.setObjectName("ModernCardValue")
        layout.addWidget(self.value_label)
        self.hint_label = QLabel(self._hint, self)
        self.hint_label.setObjectName("ModernCardHint")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

    def set_value(self, value: str, hint: str | None = None) -> None:
        self._value = str(value)
        if hint is not None:
            self._hint = str(hint)
        if not self._alive(getattr(self, "value_label", None)) or not self._alive(getattr(self, "hint_label", None)):
            self._build_content()
        self.value_label.setText(self._value)
        if hint is not None:
            self.hint_label.setText(self._hint)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class MemberCard(GlassCard):
    clicked = Signal()
    doubleClicked = Signal()

    def __init__(self, name: str, role: str = "Member", specialization: str = "", status: str = "offline", parent=None):
        super().__init__(parent, compact=True, glow=False)
        self.setObjectName("MemberCard")
        self.setMinimumHeight(84)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 17, 20, 17)
        layout.setSpacing(14)
        text = QVBoxLayout()
        text.setSpacing(5)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("MemberName")
        self.name_label.setWordWrap(True)
        self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        text.addWidget(self.name_label)
        if specialization:
            self.specialization_label = QLabel(specialization)
            self.specialization_label.setObjectName("MemberMeta")
            self.specialization_label.setWordWrap(True)
            self.specialization_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            text.addWidget(self.specialization_label)
        layout.addLayout(text, 1)
        self.role_pill = None
        if str(role or "").strip():
            self.role_pill = QLabel(str(role).upper())
            self.role_pill.setObjectName("MemberRoleText")
            self.role_pill.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.role_pill.setMaximumWidth(96)
            self.role_pill.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
            layout.addWidget(self.role_pill)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class QuickActionButton(GlassCard):
    clicked = Signal()

    def __init__(self, icon: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent, glow=False)
        self.setObjectName("QuickActionButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 22)
        layout.setSpacing(12)
        icon_label = QLabel()
        icon_label.setObjectName("QuickActionIcon")
        icon_label.setFixedSize(52, 52)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(svg_icon(icon).pixmap(QSize(27, 27)))
        layout.addWidget(icon_label, 0, Qt.AlignLeft)
        layout.addStretch(1)
        title_label = QLabel(title.upper())
        title_label.setObjectName("QuickActionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("ModernCardHint")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


# Exported reusable sidebar name. The existing app-specific subclass preserves navigation behavior.
class SidebarButton(QPushButton):
    def __init__(self, text: str = "", icon: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("ReusableSidebarButton")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        if icon:
            self.setIcon(svg_icon(icon))
            self.setIconSize(QSize(22, 22))


def modern_dashboard_qss(theme_key: str | None = None) -> str:
    base = r'''
    QWidget { font-family: "Rajdhani", "Segoe UI"; }
    QLabel#HeroTitle, QLabel#SectionTitle, QLabel#ModernCardTitle,
    QLabel#ModernCardValue, QLabel#QuickActionTitle, QLabel#NavTitle {
        font-family: "Orbitron", "Segoe UI Semibold";
    }
    QFrame#GlassCard, QFrame#ModernStatCard, QFrame#QuickActionButton {
        background: rgba(14, 18, 28, 244);
        border: none;
        border-radius: 18px;
    }
    QFrame#GlassCardCompact, QFrame#MemberCard, QFrame#DashboardLinkCard {
        background: rgba(255, 255, 255, 0.028);
        border: none;
        border-radius: 18px;
    }
    QFrame#ModernStatCard:hover, QFrame#QuickActionButton:hover, QFrame#MemberCard:hover {
        background: rgba(31, 39, 56, 242);
    }
    QLabel#ModernCardTitle { color: rgba(221, 228, 240, 0.72); font-size: 12px; font-weight: 700; letter-spacing: 1.2px; }
    QLabel#ModernCardValue { color: #F6F8FC; font-size: 42px; font-weight: 800; }
    QLabel#ModernCardHint, QLabel#MemberMeta { color: rgba(208, 216, 230, 0.58); font-size: 12px; }
    QLabel#MemberName { color: #F3F6FB; font-size: 17px; font-weight: 700; }
    QLabel#DashboardUserName { color: rgba(240,244,252,0.88); font-size: 18px; font-weight: 800; letter-spacing: .5px; }
    QLabel#MemberRoleText { color: rgba(205,214,232,0.58); font-size: 11px; font-weight: 800; letter-spacing: 1px; }
    QLabel#QuickActionTitle { color: #F5F7FC; font-size: 16px; font-weight: 700; letter-spacing: .7px; }
    QLabel#QuickActionIcon { background: rgba(116, 145, 255, 0.12); border: none; border-radius: 14px; padding: 10px; }
    QLabel#StatusPill {
        background: rgba(132, 145, 171, 0.13);
        color: rgba(229, 234, 245, 0.82);
        border: none;
        border-radius: 13px;
        padding: 4px 11px;
        font-size: 11px;
        font-weight: 700;
    }
    QLabel#StatusPill[status="online"], QLabel#StatusPill[status="synced"], QLabel#StatusPill[status="connected"] {
        background: rgba(65, 201, 128, 0.14); color: #7EE2AA;
    }
    QLabel#StatusPill[status="warning"], QLabel#StatusPill[status="interested"] {
        background: rgba(233, 182, 76, 0.14); color: #F0C96F;
    }
    QLabel#StatusPill[status="error"], QLabel#StatusPill[status="offline"], QLabel#StatusPill[status="disconnected"] {
        background: rgba(235, 91, 102, 0.13); color: #F19099;
    }
    QLabel#StatusPill[status="owner"], QLabel#StatusPill[status="officer"] {
        background: rgba(124, 113, 255, 0.15); color: #B7B0FF;
    }
    QFrame#NavButton {
        background: transparent;
        border: none;
        border-radius: 18px;
    }
    QFrame#NavButton:hover { background: rgba(255, 255, 255, 0.055); }
    QFrame#NavButton[active="true"] { background: rgba(101, 126, 255, 0.13); }
    QPushButton#PrimaryButton, QPushButton#GuildSetupButton {
        border: none;
        border-radius: 14px;
        padding: 9px 15px;
        min-height: 20px;
    }

    QWidget#Root, QWidget#ContentRoot, QWidget#ModernDashboardPage, QWidget#DashboardScrollContent { background: #090B10; }
    QScrollArea#DashboardScrollArea { background:#090B10; border:none; }
    QScrollArea#DashboardScrollArea > QWidget > QWidget { background:#090B10; }
    QLabel#DashboardKicker { color: rgba(135,154,255,0.85); font-size: 12px; font-weight: 800; letter-spacing: 3px; }
        QFrame#DashboardGuildHero {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(25,31,45,245), stop:1 rgba(16,20,31,242));
        border: none; border-radius: 18px;
    }
    QLabel#DashboardGuildName { font-family: "Orbitron", "Segoe UI Semibold"; color:#F7F9FE; font-size:28px; font-weight:800; letter-spacing:1px; }
    QLabel#DashboardGuildRole { color:#93A7FF; font-size:13px; font-weight:800; letter-spacing:1.3px; }
    QLabel#DashboardMuted, QLabel#DashboardSectionSubtitle { color:rgba(210,218,235,0.52); font-size:13px; }
    QLabel#DashboardSectionTitle { font-family:"Orbitron", "Segoe UI Semibold"; color:#F3F6FC; font-size:20px; font-weight:800; letter-spacing:1px; }
    QLabel#DashboardMiniHeading { color:rgba(183,195,220,0.62); font-size:11px; font-weight:800; letter-spacing:1.5px; margin-top:6px; }
    QLabel#DashboardStatusText { color:rgba(211,219,235,0.55); font-size:12px; }
    QFrame#DashboardStatusBar, QFrame#DashboardAccessCard { background:rgba(14,18,27,210); border:none; border-radius:18px; }
    QPushButton#DashboardPrimaryButton, QPushButton#DashboardGhostButton, QPushButton#DashboardDangerButton {
        border:none; border-radius:12px; min-height:34px; padding:0 15px; font-weight:700;
    }
    QPushButton#DashboardPrimaryButton { background:rgba(104,126,255,0.92); color:white; }
    QPushButton#DashboardPrimaryButton:hover { background:rgba(122,143,255,1); }
    QPushButton#DashboardGhostButton { background:rgba(255,255,255,0.055); color:rgba(240,244,252,0.86); border:1px solid rgba(255,255,255,0.08); }
    QPushButton#DashboardGhostButton:hover { background:rgba(255,255,255,0.14); color:#FFFFFF; border:1px solid rgba(255,255,255,0.22); }
    QPushButton#DashboardGhostButton:pressed { background:rgba(255,255,255,0.20); }
    QPushButton#DashboardDangerButton { background:rgba(231,82,96,0.10); color:#F39AA3; border:1px solid rgba(231,82,96,0.28); }
    QPushButton#DashboardDangerButton:hover { background:rgba(231,82,96,0.22); color:#FFFFFF; border:1px solid rgba(255,125,138,0.72); }
    QPushButton#DashboardDangerButton:pressed { background:rgba(231,82,96,0.32); }
    QFrame#SideBar { border:none; }
    QFrame#NavButton { border-radius:18px; background:transparent; border:none; }
    QLabel#NavTitle { font-size:16px; font-weight:800; letter-spacing:.8px; }
    QLabel#NavSub { font-size:12px; color:rgba(192,202,222,0.45); }
    QLabel#NavChevron { color:rgba(200,210,230,0.28); }
    QFrame#SideFooter { background:rgba(255,255,255,0.035); border:none; border-radius:18px; }

    QFrame#NewsCard { background: rgba(255,255,255,0.028); border:none; border-radius:16px; }
    QFrame#NewsCard:hover { background: rgba(255,255,255,0.05); }
    QLabel#NewsTitle { color:#F4F7FC; font-size:15px; font-weight:800; }
    QLabel#NewsBody { color:rgba(215,223,238,0.68); font-size:13px; }
    QLabel#MemberName, QLabel#MemberMeta, QLabel#NewsBody, QLabel#DashboardMuted, QLabel#DashboardSectionSubtitle { min-width:0px; }
    QFrame#DashboardGuildHero { min-height:210px; }
    QFrame#QuickActionButton { min-height:150px; }
    QFrame#DashboardMembersPanel {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(14,18,29,248), stop:0.52 rgba(16,20,33,246), stop:1 rgba(13,18,28,248));
        border:none;
        border-radius:18px;
    }
    QFrame#MaxCraftersColumn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(81,50,119,92), stop:0.55 rgba(40,31,66,72), stop:1 rgba(23,25,39,64));
        border:none;
        border-radius:16px;
    }
    QFrame#CombatRosterColumn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(38,64,102,82), stop:0.55 rgba(25,39,63,70), stop:1 rgba(22,26,39,64));
        border:none;
        border-radius:16px;
    }
    QLabel#RosterColumnTitle {
        font-family:"Orbitron", "Segoe UI Semibold";
        color:#F4F7FD;
        font-size:16px;
        font-weight:800;
        letter-spacing:1.2px;
    }
    QLabel#RosterColumnHint { color:rgba(207,217,235,0.56); font-size:12px; }
    QFrame#MemberCard { min-height:84px; }
    QFrame#MemberCard[rosterType="crafter"] {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 rgba(128,76,183,105), stop:0.04 rgba(72,46,105,88), stop:1 rgba(255,255,255,8));
    }
    QFrame#MemberCard[rosterType="combat"] {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 rgba(62,112,171,92), stop:0.04 rgba(35,58,91,82), stop:1 rgba(255,255,255,8));
    }
    QFrame#MemberCard[rosterType="crafter"] QLabel#MemberRoleText { color:#D7AEFF; }
    QFrame#MemberCard[rosterType="combat"] QLabel#MemberRoleText { color:#91C7FF; }

    /* Shared modern styling for every non-dashboard page */
    QWidget#ModernContentPage, QWidget#CatalogPage, QWidget#GuildPage,
    QWidget#SettingsPage, QWidget#MembersGuildPage, QWidget#GameManagerPage {
        background: transparent;
    }
    QScrollArea { background: transparent; border: none; }
    QScrollArea > QWidget > QWidget { background: transparent; }

    QFrame#Card, QFrame#Panel, QFrame#SectionCard, QFrame#CommandCard,
    QFrame#SettingsCard, QFrame#GuildCard, QFrame#CatalogCard,
    QFrame#MapPanel, QFrame#TimerCard, QFrame#ContentCard {
        background: rgba(255,255,255,0.035);
        border: none;
        border-radius: 18px;
    }
    QGroupBox {
        background: rgba(255,255,255,0.028);
        border: none;
        border-radius: 18px;
        margin-top: 18px;
        padding: 18px;
        font-family: "Orbitron", "Segoe UI Semibold";
        font-size: 15px;
        font-weight: 800;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 18px;
        padding: 0 8px;
    }
    QTabWidget::pane {
        background: rgba(255,255,255,0.025);
        border: none;
        border-radius: 18px;
        top: -1px;
    }
    QTabBar::tab {
        background: transparent;
        border: none;
        border-radius: 12px;
        padding: 11px 18px;
        margin-right: 6px;
        min-width: 92px;
        font-weight: 700;
    }
    QTableView, QTableWidget, QListView, QListWidget, QTreeView, QTreeWidget {
        background: rgba(10,13,20,0.72);
        alternate-background-color: rgba(255,255,255,0.025);
        border: none;
        border-radius: 16px;
        gridline-color: rgba(255,255,255,0.035);
        selection-background-color: rgba(255,255,255,0.085);
        padding: 8px;
    }
    QHeaderView::section {
        background: rgba(255,255,255,0.045);
        border: none;
        padding: 10px 12px;
        font-weight: 800;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QDateTimeEdit, QComboBox {
        background: rgba(255,255,255,0.045);
        border: none;
        border-radius: 12px;
        padding: 9px 12px;
        min-height: 22px;
        selection-background-color: rgba(255,255,255,0.15);
    }
    QComboBox::drop-down { border: none; width: 30px; }
    QPushButton {
        border: none;
        border-radius: 12px;
        padding: 9px 15px;
        min-height: 24px;
        font-weight: 700;
    }
    QToolButton { border: none; border-radius: 11px; padding: 8px; }
    QCheckBox, QRadioButton { spacing: 9px; }
    QProgressBar {
        background: rgba(255,255,255,0.045);
        border: none;
        border-radius: 7px;
        min-height: 14px;
        text-align: center;
    }
    QProgressBar::chunk { border-radius: 7px; }
    QSplitter::handle {
        background: rgba(255,255,255,0.035);
        width: 2px;
        height: 2px;
    }
    QMenu {
        background: rgba(16,20,30,250);
        border: none;
        border-radius: 12px;
        padding: 7px;
    }
    QMenu::item { border-radius: 8px; padding: 8px 14px; }
    QToolTip {
        background: rgba(18,22,32,250);
        border: none;
        border-radius: 8px;
        padding: 7px;
    }
    QFrame#SideHeader {
        background: transparent;
        border: none;
        min-height: 176px;
    }
    QLabel#MascotLogo {
        background: transparent;
        border: none;
        padding: 0;
        margin: 0;
        min-width: 210px;
        min-height: 150px;
    }


    /* Unified page typography */
    QLabel#SectionTitle,
    QLabel#DashboardSectionTitle {
        font-family: "Orbitron", "Segoe UI Semibold";
        font-size: 20px;
        font-weight: 800;
        letter-spacing: 1px;
    }

    /* Larger tab headers throughout the application */
    QTabBar::tab {
        font-family: "Rajdhani", "Segoe UI";
        font-size: 16px;
        font-weight: 800;
        min-height: 30px;
        min-width: 112px;
        padding: 13px 22px;
        margin-right: 8px;
        border-radius: 13px;
    }

    QTabBar::tab:selected {
        font-weight: 900;
    }

    QFrame#TimerLabCard {
        background: rgba(255, 255, 255, 0.035);
        border: none;
        border-radius: 18px;
    }

    QLineEdit#LabTimerName {
        font-family: "Orbitron", "Segoe UI Semibold";
        font-size: 17px;
        font-weight: 800;
        min-height: 34px;
    }

    QLabel#LabTimerStatus {
        background: rgba(255, 255, 255, 0.06);
        border: none;
        border-radius: 13px;
        padding: 7px 12px;
        font-family: "Orbitron", "Segoe UI Semibold";
        font-size: 16px;
        font-weight: 800;
    }

    QSpinBox#LabTimerDuration {
        font-size: 15px;
        font-weight: 800;
        min-height: 32px;
    }


    QDialog#SubmissionDialog,
    QDialog#DetailDialog {
        background: rgba(9, 11, 16, 0.98);
        border: none;
        border-radius: 18px;
    }

    QFrame#SubmissionPanel {
        background: rgba(255, 255, 255, 0.075);
        border: none;
        border-radius: 18px;
    }

    QFrame#SubmissionPanel QLabel {
        font-weight: 800;
    }

    QFrame#SubmissionPanel QLineEdit,
    QFrame#SubmissionPanel QTextEdit,
    QFrame#SubmissionPanel QPlainTextEdit,
    QFrame#SubmissionPanel QComboBox,
    QFrame#SubmissionPanel QDateEdit,
    QFrame#SubmissionPanel QTimeEdit,
    QFrame#SubmissionPanel QDateTimeEdit {
        background: rgba(4, 6, 10, 0.56);
        border: none;
        border-radius: 12px;
        padding: 11px 13px;
    }


    /* Stronger dashboard statistics */
    QFrame#ModernStatCard {
        background: rgba(255,255,255,0.075);
        border: none;
        border-radius: 18px;
        min-height: 136px;
    }
    QFrame#ModernStatCard QLabel#StatValue {
        font-size: 40px;
        font-weight: 900;
    }
    QFrame#ModernStatCard QLabel#StatTitle {
        font-size: 15px;
        font-weight: 900;
        letter-spacing: 1px;
    }

    /* Clear event/announcement affordance */
    QLabel#DetailHint {
        background: rgba(255,255,255,0.055);
        border: none;
        border-radius: 11px;
        padding: 9px 12px;
        font-size: 14px;
        font-weight: 800;
    }

    QTableWidget#EventListingTable,
    QTableWidget#AnnouncementListingTable {
        background: rgba(255,255,255,0.055);
        border: none;
        border-radius: 16px;
    }

    QFrame#NewsCard {
        background: rgba(255,255,255,0.07);
        border: none;
        border-radius: 15px;
    }

    QLabel#DashboardIdentitySync {
        margin-top: 5px;
    }

    QTabWidget#GuildAdminTabs QTabBar::tab {
        min-height: 42px;
        min-width: 150px;
        padding: 14px 26px;
        font-size: 17px;
        font-weight: 900;
    }


    QLabel#DashboardWorldSietch {
        background: transparent;
        border: none;
        padding: 2px 0;
        min-height: 24px;
        font-family: "Rajdhani", "Segoe UI";
        font-size: 18px;
        font-weight: 500;
        letter-spacing: 0.7px;
        color: rgba(247,249,254,0.94);
    }


    /* Refined large page tabs */
    QTabBar {
        qproperty-drawBase: 0;
    }

    QTabBar::tab {
        font-family: "Rajdhani", "Segoe UI";
        font-size: 20px;
        font-weight: 500;
        min-height: 46px;
        min-width: 154px;
        padding: 12px 28px;
        margin-right: 12px;
        margin-bottom: 10px;
        border: none;
        border-radius: 14px;
    }

    QTabBar::tab:selected {
        font-weight: 500;
    }

    QTabWidget::pane {
        top: 4px;
        padding-top: 10px;
    }

    QTabWidget#GuildAdminTabs QTabBar::tab,
    QTabWidget#CommandTabs QTabBar::tab {
        font-size: 21px;
        font-weight: 500;
        min-height: 48px;
        min-width: 168px;
        padding: 13px 30px;
        margin-right: 14px;
        margin-bottom: 12px;
    }

    QTabWidget#GuildAdminTabs QTabBar::tab:selected,
    QTabWidget#CommandTabs QTabBar::tab:selected {
        font-weight: 500;
    }


    QFrame#UnifiedTimerConsole {
        background: rgba(255,255,255,0.045);
        border: none;
        border-radius: 18px;
    }

    QFrame#LabTimerRow,
    QFrame#SandstormTimerRow {
        background: rgba(255,255,255,0.045);
        border: none;
        border-radius: 13px;
        min-height: 52px;
    }

    QFrame#SandstormTimerRow {
        background: rgba(255,170,65,0.075);
    }

    QFrame#TimerDivider {
        background: rgba(255,255,255,0.08);
        border: none;
        max-height: 1px;
    }

    QLineEdit#TimerNameInput {
        font-size: 16px;
        font-weight: 600;
        min-height: 30px;
    }

    QSpinBox#TimerDurationInput {
        font-size: 15px;
        font-weight: 600;
        min-height: 30px;
    }

    QLabel#TimerRowStatus {
        background: rgba(255,255,255,0.055);
        border: none;
        border-radius: 11px;
        padding: 7px 10px;
        font-family: "Orbitron", "Segoe UI Semibold";
        font-size: 14px;
        font-weight: 700;
    }

    QLabel#TimerRowStatus[running="true"] {
        background: rgba(80,200,140,0.16);
    }

    QFrame#ModernStatCard {
        min-height: 138px;
        max-height: 158px;
    }

    QFrame#ModernStatCard QLabel#StatValue {
        font-size: 38px;
        padding-bottom: 4px;
    }

    '''
    colors = theme_colors(theme_key)
    accent = colors["accent"]
    bg = colors["bg"]
    panel = colors["panel"]
    panel_hover = colors["panel_hover"]
    secondary = colors["secondary"]
    glow = colors["glow"]
    accent_soft = colors["accent_soft"]
    danger = colors.get("danger", "#FF5555")
    danger_soft = colors.get("danger_soft", "rgba(255,85,85,0.20)")
    success = colors.get("success", "#89FF45")
    success_soft = colors.get("success_soft", "rgba(137,255,69,0.18)")
    warning = colors.get("warning", "#FFCB45")
    warning_soft = colors.get("warning_soft", "rgba(255,203,69,0.18)")
    accent_secondary = colors.get("accent_secondary", accent)
    accent_tertiary = colors.get("accent_tertiary", accent)
    spiced_extra = ""
    if (theme_key or "").strip().lower() == "spiced_up":
        spiced_extra = f"""
        QWidget#Root, QWidget#ContentRoot, QWidget#ModernDashboardPage,
        QWidget#DashboardScrollContent, QWidget#CatalogPage, QWidget#GuildPage,
        QWidget#SettingsPage, QWidget#MembersGuildPage, QWidget#GameManagerPage {{
            background:qradialgradient(cx:0.15,cy:0.12,radius:1.2,fx:0.15,fy:0.12,stop:0 rgba(255,0,214,0.58),stop:0.24 rgba(0,246,255,0.32),stop:0.52 rgba(183,255,0,0.18),stop:1 #05000C);
        }}
        QFrame#SideBar {{ border-right:2px solid #00F6FF; }}
        QFrame#NavButton {{ background:rgba(4,0,12,0.46); border:1px solid rgba(0,246,255,0.20); }}
        QFrame#NavButton:hover {{
            background:rgba(10,0,24,0.78);
            border:1px solid #00F6FF;
        }}
        QFrame#NavButton[active="true"] {{
            background:rgba(18,0,36,0.92);
            border:2px solid #B7FF00;
        }}
        QFrame#NavAccentBar {{ background:#B7FF00; }}
        QFrame#NavIconBubble {{ background:rgba(0,0,0,0.42); border:1px solid rgba(0,246,255,0.58); }}
        QFrame#SideFooter {{ background:rgba(3,0,12,0.88); border:1px solid rgba(0,246,255,0.42); }}
        QFrame#GlassCard, QFrame#ModernStatCard, QFrame#QuickActionButton,
        QFrame#DashboardMembersPanel, QFrame#DashboardStatusBar, QFrame#DashboardAccessCard,
        QFrame#Card, QFrame#Panel, QFrame#SectionCard, QFrame#CommandCard,
        QFrame#SettingsCard, QFrame#GuildCard, QFrame#CatalogCard,
        QFrame#MapPanel, QFrame#TimerCard, QFrame#ContentCard,
        QFrame#StatCard, QFrame#CatalogToolbar, QFrame#CategoryPanel,
        QFrame#ItemGridPanel, QFrame#ItemDetailsPanel {{
            background:rgba(31,0,52,0.80);
            border:1px solid rgba(0,246,255,0.46);
        }}
        QFrame#ModernStatCard, QFrame#StatCard[active="true"], QFrame#DashboardGuildHero {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(255,0,214,0.36),stop:0.45 rgba(52,0,89,0.88),stop:1 rgba(0,246,255,0.24));
            border:2px solid rgba(255,0,214,0.78);
        }}
        QFrame#NewsCard, QFrame#MemberCard, QFrame#GlassCardCompact {{
            background:rgba(69,0,96,0.76);
            border:1px solid rgba(183,255,0,0.38);
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit,
        QLineEdit#SearchField, QComboBox#CatalogFilter {{
            background:rgba(10,0,22,0.86);
            border:1px solid rgba(0,246,255,0.62);
            color:#FFFFFF;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
        QLineEdit#SearchField:focus, QComboBox#CatalogFilter:focus {{
            border:2px solid #B7FF00;
            background:rgba(48,0,78,0.92);
        }}
        QPushButton, QPushButton#GoldButton, QPushButton#NeutralButton, QPushButton#DashboardPrimaryButton {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF00D6,stop:0.55 #7B00FF,stop:1 #00F6FF);
            color:#FFFFFF;
            border:1px solid #B7FF00;
        }}
        QPushButton:hover, QPushButton#GoldButton:hover, QPushButton#NeutralButton:hover {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #B7FF00,stop:0.5 #00F6FF,stop:1 #FF00D6);
            color:#05000C;
        }}
        QPushButton#DangerButton {{ background:rgba(255,23,79,0.34); border:1px solid #FF174F; color:#FFFFFF; }}
        QLabel#DashboardKicker, QLabel#QuickActionTitle, QLabel#CatalogTitle,
        QLabel#CatalogPanelTitle, QLabel#CatalogStatIcon, QLabel#CatalogStatLabel,
        QLabel#RosterColumnTitle {{ color:#B7FF00; }}
        QLabel#ModernCardValue, QLabel#DashboardGuildName, QLabel#DashboardSectionTitle,
        QLabel#MemberName, QLabel#NewsTitle, QLabel#CatalogStatValue,
        QLabel#CatalogDetailTitle {{ color:#FFFFFF; }}
        QLabel#NavTitle {{ color:#F7F2FF; }}
        QFrame#NavButton[active="true"] QLabel#NavTitle {{ color:#FFFFFF; font-weight:950; }}
        QLabel#DashboardGuildRole, QLabel#MemberRoleText, QLabel#CatalogSubtitle,
        QLabel#CatalogDetailBody, QLabel#CatalogMetaValue {{ color:#00F6FF; }}
        QTableWidget#CatalogResultsTable, QListWidget#CatalogCategoryList,
        QTableView, QTableWidget, QListView, QListWidget {{
            background:rgba(8,0,18,0.84);
            border:1px solid rgba(255,0,214,0.42);
            color:#FFFFFF;
        }}
        QTableWidget#CatalogResultsTable::item:selected,
        QListWidget#CatalogCategoryList::item:selected,
        QTableView::item:selected, QTableWidget::item:selected,
        QListView::item:selected, QListWidget::item:selected {{
            background:rgba(255,0,214,0.54);
            color:#FFFFFF;
        }}
        """
    overrides = f"""
    QWidget#Root, QWidget#ContentRoot, QWidget#ModernDashboardPage, QWidget#DashboardScrollContent {{ background: {bg}; }}
    QScrollArea#DashboardScrollArea, QScrollArea#DashboardScrollArea > QWidget > QWidget {{ background: {bg}; border:none; }}
    QFrame#SideBar {{ border:none; border-right:1px solid {glow}; }}
    QFrame#GlassCard, QFrame#ModernStatCard, QFrame#QuickActionButton,
    QFrame#DashboardMembersPanel, QFrame#DashboardStatusBar, QFrame#DashboardAccessCard {{
        background: {panel}; border:none; border-radius:18px;
    }}
    QFrame#GlassCardCompact, QFrame#MemberCard, QFrame#DashboardLinkCard, QFrame#NewsCard {{
        background: rgba(255,255,255,0.035); border:none; border-radius:16px;
    }}
    QFrame#ModernStatCard:hover, QFrame#QuickActionButton:hover, QFrame#MemberCard:hover, QFrame#NewsCard:hover {{
        background: {panel_hover};
    }}
    QLabel#DashboardKicker, QLabel#DashboardGuildRole, QLabel#RosterColumnTitle,
    QLabel#QuickActionTitle, QLabel#MemberRoleText {{ color:{accent}; }}
    QLabel#ModernCardValue, QLabel#DashboardGuildName, QLabel#DashboardSectionTitle, QLabel#MemberName, QLabel#NewsTitle {{ color:#F7F8FC; }}
    QLabel#QuickActionIcon {{ background:{glow}; border:none; border-radius:14px; }}
    QFrame#NavButton {{ background:transparent; border:none; border-radius:14px; }}
    QFrame#NavButton:hover {{ background:{glow}; }}
    QFrame#NavButton[active="true"] {{ background:{glow}; border:1px solid {accent_soft}; }}
    QFrame#NavAccentBar {{ background:{accent}; border:none; border-radius:2px; }}
    QFrame#NavIconBubble {{ background:transparent; border:none; border-radius:12px; }}
    QFrame#NavButton[active="true"] QFrame#NavIconBubble, QFrame#NavButton:hover QFrame#NavIconBubble {{ background:{glow}; }}
    QLabel#NavTitle {{ color:rgba(245,247,252,0.92); font-size:15px; font-weight:800; letter-spacing:.8px; }}
    QFrame#NavButton[active="true"] QLabel#NavTitle {{ color:{accent}; }}
    QFrame#SideFooter {{ background:{panel}; border:none; border-radius:16px; }}
    QPushButton#DashboardPrimaryButton {{ background:{accent}; color:#0B0D12; }}
    QPushButton#DashboardPrimaryButton:hover {{ background:{accent}; color:#FFFFFF; border:1px solid {accent_soft}; }}
    QPushButton#DashboardPrimaryButton:pressed {{ background:{accent_soft}; }}
    QPushButton#DashboardGhostButton {{ background:{glow}; color:#F1F4FA; border:1px solid {accent_soft}; }}
    QPushButton#DashboardGhostButton:hover {{ background:{accent_soft}; color:#FFFFFF; border:1px solid {accent}; }}
    QPushButton#DashboardGhostButton:pressed {{ background:{glow}; }}
    QPushButton#DashboardDangerButton:hover {{ background:rgba(231,82,96,0.22); color:#FFFFFF; border:1px solid rgba(255,125,138,0.72); }}
    QFrame#DashboardGuildHero {{
        background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {panel},stop:1 {secondary});
        border:none; border-radius:18px;
    }}
    QFrame#MaxCraftersColumn {{ background:{glow}; border:none; border-radius:16px; }}
    QFrame#CombatRosterColumn {{ background:rgba(255,255,255,0.035); border:none; border-radius:16px; }}
    QFrame#MemberCard[rosterType="crafter"] {{ background:{glow}; }}
    QFrame#MemberCard[rosterType="combat"] {{ background:rgba(255,255,255,0.035); }}
    QFrame#MemberCard[rosterType="crafter"] QLabel#MemberRoleText,
    QFrame#MemberCard[rosterType="combat"] QLabel#MemberRoleText {{ color:{accent}; }}
    QLabel#StatusPill[status="owner"], QLabel#StatusPill[status="officer"] {{ background:{glow}; color:{accent}; }}

    QFrame#UnifiedTimerConsole {{
        background:{panel};
        border:1px solid {accent_soft};
    }}

    QFrame#LabTimerRow {{
        background:{panel_hover};
    }}

    QFrame#SandstormTimerRow {{
        background:{glow};
        border:1px solid {accent_soft};
    }}

    QLabel#TimerRowStatus {{
        background:{panel};
        color:{accent};
    }}

    QLabel#TimerRowStatus[running="true"] {{
        background:{success_soft};
        color:{success};
    }}

    QLabel#DashboardWorldSietch {{
        background:transparent;
        border:none;
        color:{accent};
    }}

    QWidget#ModernContentPage, QWidget#CatalogPage, QWidget#GuildPage,
    QWidget#SettingsPage, QWidget#MembersGuildPage, QWidget#GameManagerPage {{
        background:{bg};
    }}
    QFrame#Card, QFrame#Panel, QFrame#SectionCard, QFrame#CommandCard,
    QFrame#SettingsCard, QFrame#GuildCard, QFrame#CatalogCard,
    QFrame#MapPanel, QFrame#TimerCard, QFrame#ContentCard,
    QGroupBox, QTabWidget::pane {{
        background:{panel};
        border:none;
    }}
    QGroupBox::title, QTabBar::tab:selected, QHeaderView::section {{
        color:{accent};
    }}
    QTabBar::tab:hover, QTabBar::tab:selected,
    QPushButton:hover, QToolButton:hover, QMenu::item:selected {{
        background:{glow};
        color:{accent};
    }}
    QPushButton:checked, QToolButton:checked {{
        background:{glow};
        color:{accent};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
    QTimeEdit:focus, QDateTimeEdit:focus, QComboBox:focus {{
        background:{panel_hover};
    }}
    QProgressBar::chunk {{ background:{accent}; }}
    QTableView::item:selected, QTableWidget::item:selected,
    QListView::item:selected, QListWidget::item:selected,
    QTreeView::item:selected, QTreeWidget::item:selected {{
        background:{glow};
        color:{accent};
    }}

    QFrame#ModernStatCard {{
        background:{panel_hover};
        border:1px solid {accent_soft};
    }}
    QFrame#ModernStatCard:hover {{
        background:{glow};
        border:1px solid {accent};
    }}
    QFrame#ModernStatCard QLabel#StatValue,
    QFrame#ModernStatCard QLabel#StatTitle {{
        color:{accent};
    }}

    QLabel#DetailHint {{
        background:{glow};
        color:{accent};
    }}

    QTableWidget#EventListingTable,
    QTableWidget#AnnouncementListingTable {{
        background:{panel_hover};
        border:1px solid {accent_soft};
    }}

    QTableWidget#EventListingTable::item,
    QTableWidget#AnnouncementListingTable::item {{
        background:transparent;
    }}

    QTableWidget#EventListingTable::item:selected,
    QTableWidget#AnnouncementListingTable::item:selected {{
        background:{glow};
        color:{accent};
    }}

    QFrame#NewsCard[contentType="event"] {{
        background:{panel_hover};
        border:1px solid {accent_soft};
    }}

    QFrame#NewsCard[contentType="announcement"] {{
        background:{glow};
        border:1px solid {accent_soft};
    }}

    QFrame#NewsCard[contentType="event"]:hover,
    QFrame#NewsCard[contentType="announcement"]:hover {{
        border:1px solid {accent};
    }}

    QTabWidget#GuildAdminTabs QTabBar::tab {{
        background:{panel};
    }}

    QTabWidget#GuildAdminTabs QTabBar::tab:hover,
    QTabWidget#GuildAdminTabs QTabBar::tab:selected {{
        background:{glow};
        color:{accent};
    }}

    QDialog#SubmissionDialog {{
        background:{bg};
    }}
    QFrame#SubmissionPanel {{
        background:{glow};
        border:1px solid {accent_soft};
    }}
    QFrame#SubmissionPanel QLabel {{
        color:#F7F8FC;
    }}
    QFrame#SubmissionPanel QLineEdit,
    QFrame#SubmissionPanel QTextEdit,
    QFrame#SubmissionPanel QPlainTextEdit,
    QFrame#SubmissionPanel QComboBox,
    QFrame#SubmissionPanel QDateEdit,
    QFrame#SubmissionPanel QTimeEdit,
    QFrame#SubmissionPanel QDateTimeEdit {{
        background:{panel};
        color:#F7F8FC;
    }}
    QFrame#SubmissionPanel QLineEdit:focus,
    QFrame#SubmissionPanel QTextEdit:focus,
    QFrame#SubmissionPanel QPlainTextEdit:focus,
    QFrame#SubmissionPanel QComboBox:focus,
    QFrame#SubmissionPanel QDateEdit:focus,
    QFrame#SubmissionPanel QTimeEdit:focus,
    QFrame#SubmissionPanel QDateTimeEdit:focus {{
        background:{panel_hover};
    }}
    """
    semantic = f"""
    QFrame#NewsCard[selected="true"] {{
        background:{glow};
        border:1px solid {accent};
    }}
    QFrame#NewsCard[responseStatus="attending"], QFrame#AttendingEventCard {{
        background:{success_soft};
        border:1px solid {success};
    }}
    QFrame#NewsCard[responseStatus="interested"] {{
        background:{warning_soft};
        border:1px solid {warning};
    }}
    QFrame#NewsCard[responseStatus="not_going"], QFrame#NotGoingEventCard {{
        background:{danger_soft};
        border:1px solid {danger};
    }}
    QLabel#StatusPill[status="not_going"], QLabel#StatusPill[status="error"] {{
        background:{danger_soft};
        color:{danger};
    }}
    QPushButton#DangerButton {{
        background:{danger_soft};
        color:#FFF7F7;
        border:1px solid {danger};
    }}
    """
    gold_catalog = r"""
    /* Gold catalog database redesign */

    QFrame#NavButton {
        background:transparent;
        border:1px solid transparent;
        border-radius:13px;
    }
    QFrame#NavButton:hover {
        background:rgba(214,165,32,0.10);
        border:1px solid rgba(214,165,32,0.20);
    }
    QFrame#NavButton[active="true"] {
        background:rgba(214,165,32,0.16);
        border:1px solid rgba(240,200,75,0.58);
    }
    QFrame#NavAccentBar {
        background:#F0C84B;
        border-radius:2px;
    }
    QLabel#NavTitle {
        color:#AAA493;
        font-size:13px;
        font-weight:900;
    }
    QFrame#NavButton[active="true"] QLabel#NavTitle,
    QFrame#NavButton:hover QLabel#NavTitle {
        color:#F4F1E8;
    }
    QFrame#NavIconBubble {
        background:rgba(214,165,32,0.12);
        border-radius:10px;
    }
    QFrame#SideFooter {
        background:rgba(27,24,15,0.86);
        border:1px solid rgba(214,165,32,0.18);
        border-radius:14px;
    }
    QLabel#NavUserName { color:#F0C84B; font-size:13px; font-weight:900; }

    QWidget#CatalogPage {
        background:#0B0A07;
    }
    QLabel#CatalogTitle {
        color:#F4F1E8;
        font-size:34px;
        font-weight:900;
        letter-spacing:2px;
    }
    QLabel#CatalogSubtitle, QLabel#CatalogStatusText {
        color:#AAA493;
        font-size:13px;
    }
    QFrame#StatCard, QFrame#CatalogToolbar, QFrame#CategoryPanel,
    QFrame#ItemGridPanel, QFrame#ItemDetailsPanel {
        background:#15130D;
        border:1px solid rgba(214,165,32,0.25);
        border-radius:14px;
    }
    QFrame#StatCard[active="true"] {
        background:#1B180F;
        border:1px solid rgba(240,200,75,0.75);
    }
    QLabel#CatalogStatIcon { color:#F0C84B; font-size:23px; }
    QLabel#CatalogStatValue { color:#F4F1E8; font-size:25px; font-weight:900; }
    QLabel#CatalogStatLabel { color:#F0C84B; font-size:11px; font-weight:900; letter-spacing:1px; }
    QLabel#CatalogPanelTitle {
        color:#F0C84B;
        font-size:15px;
        font-weight:900;
        letter-spacing:1px;
    }
    QLineEdit#SearchField, QComboBox#CatalogFilter {
        min-height:42px;
        background:#17150F;
        color:#F4F1E8;
        border:1px solid rgba(214,165,32,0.22);
        border-radius:12px;
        padding:0 13px;
    }
    QLineEdit#SearchField:focus, QComboBox#CatalogFilter:focus {
        border:1px solid #F0C84B;
    }
    QPushButton#GoldButton, QPushButton#NeutralButton, QPushButton#DangerButton {
        min-height:40px;
        border-radius:11px;
        padding:0 14px;
        font-weight:900;
    }
    QPushButton#GoldButton {
        background:rgba(214,165,32,0.12);
        color:#F0C84B;
        border:1px solid rgba(240,200,75,0.62);
    }
    QPushButton#NeutralButton {
        background:#17150F;
        color:#F4F1E8;
        border:1px solid rgba(214,165,32,0.22);
    }
    QPushButton#DangerButton {
        background:rgba(216,74,58,0.10);
        color:#FF8A7E;
        border:1px solid rgba(216,74,58,0.58);
    }
    QListWidget#CatalogCategoryList, QTableWidget#CatalogResultsTable {
        background:#100E09;
        color:#F4F1E8;
        border:none;
        border-radius:10px;
        alternate-background-color:#15130D;
    }
    QListWidget#CatalogCategoryList::item {
        min-height:32px;
        padding:6px 10px;
        border-radius:8px;
        color:#AAA493;
    }
    QListWidget#CatalogCategoryList::item:selected,
    QListWidget#CatalogCategoryList::item:hover {
        background:rgba(214,165,32,0.16);
        color:#F0C84B;
    }
    QTableWidget#CatalogResultsTable::item {
        padding:8px;
        border-bottom:1px solid rgba(214,165,32,0.08);
    }
    QTableWidget#CatalogResultsTable::item:selected {
        background:rgba(214,165,32,0.20);
        color:#F4F1E8;
    }
    QTableWidget#CatalogResultsTable QHeaderView::section {
        background:#17150F;
        color:#F0C84B;
        border:none;
        padding:8px;
        font-weight:900;
    }
    QLabel#CatalogEmptyIcon { color:#F0C84B; font-size:74px; }
    QLabel#CatalogDetailTitle { color:#F4F1E8; font-size:22px; font-weight:900; }
    QLabel#CatalogGradeBadge {
        color:#F0C84B;
        background:rgba(214,165,32,0.13);
        border:1px solid rgba(214,165,32,0.34);
        border-radius:9px;
        padding:5px 9px;
        font-weight:900;
    }
    QLabel#CatalogDetailBody, QLabel#CatalogMetaValue { color:#D8D0BD; font-size:13px; }
    QLabel#CatalogDetailMuted, QLabel#CatalogMetaKey { color:#746F63; font-size:12px; font-weight:800; }
    QLabel#CatalogDetailImage {
        background:#100E09;
        border:1px solid rgba(214,165,32,0.20);
        border-radius:12px;
    }    """
    return base + overrides + semantic + spiced_extra + gold_catalog



