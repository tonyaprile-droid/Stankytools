from __future__ import annotations

from PySide6.QtWidgets import QPushButton


class GoldButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("GoldButton")
        self.setMinimumHeight(38)
