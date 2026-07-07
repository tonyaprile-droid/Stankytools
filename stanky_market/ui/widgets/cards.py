from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget


class CommandCard(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", content: QWidget | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("CommandCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        if title:
            label = QLabel(title.upper())
            label.setObjectName("SectionTitle")
            layout.addWidget(label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("MicroLabel")
            sub.setWordWrap(True)
            layout.addWidget(sub)
        if content is not None:
            layout.addWidget(content, 1)


class StatusPill(QFrame):
    def __init__(self, label: str, value: str, tone: str = "gold", parent: QWidget | None = None, icon_path: str | None = None):
        super().__init__(parent)
        self.setObjectName("MiniStatus")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)
        if icon_path:
            icon = QLabel()
            pix = QPixmap(icon_path)
            if not pix.isNull():
                # Wide Guild Role / Join Code badge assets include the words inside the artwork.
                wide_badge = pix.width() > pix.height() * 1.8
                target_w = 210 if wide_badge else 32
                target_h = 64 if wide_badge else 32
                icon.setPixmap(pix.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                icon.setFixedSize(target_w + 6, target_h + 6)
                icon.setAlignment(Qt.AlignCenter)
                row.addWidget(icon)
            else:
                name = QLabel(label.upper())
                name.setObjectName("MicroLabel")
                row.addWidget(name)
        else:
            name = QLabel(label.upper())
            name.setObjectName("MicroLabel")
            row.addWidget(name)
        val = QLabel(value)
        self.value = val
        val.setObjectName("VersionPill" if tone == "gold" else "MicroLabel")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addStretch()
        row.addWidget(val)
