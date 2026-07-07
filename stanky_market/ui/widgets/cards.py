from __future__ import annotations

from PySide6.QtCore import Qt
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
    def __init__(self, label: str, value: str, tone: str = "gold", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("MiniStatus")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(6)
        name = QLabel(label.upper())
        name.setObjectName("MicroLabel")
        val = QLabel(value)
        self.value = val
        val.setObjectName("VersionPill" if tone == "gold" else "MicroLabel")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(name)
        row.addStretch()
        row.addWidget(val)
