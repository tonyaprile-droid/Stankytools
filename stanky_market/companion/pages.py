from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QRectF, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QComboBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QCheckBox,
    QInputDialog,
    QTabWidget,
    QProgressBar,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)

from . import store
from .. import db
from ..ui.tactical_theme import theme_colors


def _card(title: str, body: str = "", min_h: int = 110) -> QFrame:
    frame = QFrame()
    frame.setObjectName("CommandCard")
    frame.setMinimumHeight(min_h)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(7)
    t = QLabel(title.upper())
    t.setObjectName("CardTitle")
    layout.addWidget(t)
    if body:
        b = QLabel(body)
        b.setObjectName("CardHint")
        b.setWordWrap(True)
        layout.addWidget(b)
    layout.addStretch(1)
    return frame


def _scroll_content(parent_layout: QVBoxLayout) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    inner = QWidget()
    inner_layout = QVBoxLayout(inner)
    inner_layout.setContentsMargins(0, 0, 0, 0)
    inner_layout.setSpacing(12)
    scroll.setWidget(inner)
    parent_layout.addWidget(scroll, 1)
    return scroll, inner, inner_layout




class CompanionImportWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, mode: str, url: str = "", max_pages: int = 40, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.url = url
        self.max_pages = max_pages
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self):
        return self._cancelled

    def run(self):
        try:
            if self.mode == "catalog":
                result = store.import_catalog_from_exports(progress=self.progress.emit, reset=True)
            elif self.mode == "recipe_url":
                result = store.import_recipe_url_auto(self.url, progress=self.progress.emit)
            elif self.mode == "recipes_web":
                result = store.import_recipes_from_best_web_sources(progress=self.progress.emit, max_pages=self.max_pages, stop_check=self.is_cancelled)
            else:
                raise ValueError(f"Unknown import mode: {self.mode}")
            self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


def build_catalog_page(window) -> QWidget:
    page, layout = window._page_shell("Catalog", "")

    def apply_catalog_theme() -> None:
        c = theme_colors(db.get_setting("color_theme", "dune") or "dune")
        page.setStyleSheet(f"""
            QFrame#CatalogCompactRow {{
                background: {c['panel']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QFrame#CatalogCompactRow:hover {{
                background: {c['panel_hover']};
                border: 1px solid {c['accent_soft']};
            }}
            QLabel#CatalogCompactName {{
                font-size: 14px;
                font-weight: 800;
                color: {c['text']};
                letter-spacing: 0px;
            }}
        """)

    page.refresh_theme_assets = apply_catalog_theme
    apply_catalog_theme()

    tabs = QTabWidget()
    tabs.setObjectName("CommandTabs")
    layout.addWidget(tabs, 1)

    catalog_tab = QWidget()
    catalog_layout = QVBoxLayout(catalog_tab)
    catalog_layout.setContentsMargins(8, 8, 8, 8)
    catalog_layout.setSpacing(12)

    # Polished summary strip
    stats_row = QHBoxLayout()
    stats_row.setSpacing(10)
    stat_cards = {}
    for key, label in (("items", "Items"), ("recipes", "Recipes"), ("categories", "Categories"), ("images", "Images")):
        card = QFrame()
        card.setObjectName("CommandCard")
        card.setMinimumHeight(74)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        value = QLabel("-")
        value.setObjectName("HeroMetric")
        caption = QLabel(label.upper())
        caption.setObjectName("MutedText")
        card_layout.addWidget(value)
        card_layout.addWidget(caption)
        stats_row.addWidget(card)
        stat_cards[key] = value
    catalog_layout.addLayout(stats_row)

    controls = QHBoxLayout()
    controls.setSpacing(8)
    search = QLineEdit()
    search.setPlaceholderText("Search items, categories, materials, weapons, vehicles, buildings...")
    category = QComboBox()
    category.setMinimumWidth(340)
    category.setMinimumHeight(46)
    category.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    load_exports_btn = QPushButton("Reload Bundled Catalog")
    delete_imported_btn = QPushButton("Delete Imported Items")
    delete_imported_btn.setObjectName("DangerButton")
    controls.addWidget(search, 3)
    controls.addWidget(category, 2)
    controls.addWidget(load_exports_btn)
    controls.addWidget(delete_imported_btn)
    catalog_layout.addLayout(controls)

    notice = QLabel("Search for an item or choose a category. Results show names only. Images, stats, and requirements load in the details panel after double-click.")
    notice.setObjectName("MutedText")
    notice.setWordWrap(True)
    catalog_layout.addWidget(notice)

    import_status = QLabel("Ready")
    import_status.setObjectName("MutedText")
    import_progress = QProgressBar()
    import_progress.setRange(0, 0)
    import_progress.setVisible(False)
    catalog_layout.addWidget(import_status)
    catalog_layout.addWidget(import_progress)

    content_splitter = QSplitter(Qt.Horizontal)
    content_splitter.setObjectName("CatalogDetailSplitter")

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    catalog_inner = QWidget()
    list_layout = QGridLayout(catalog_inner)
    list_layout.setContentsMargins(0, 0, 0, 0)
    list_layout.setHorizontalSpacing(12)
    list_layout.setVerticalSpacing(12)
    scroll.setWidget(catalog_inner)

    detail_panel = QFrame()
    detail_panel.setObjectName("CommandCard")
    detail_panel.setMinimumWidth(330)
    detail_panel.setMaximumWidth(460)
    detail_layout = QVBoxLayout(detail_panel)
    detail_layout.setContentsMargins(16, 16, 16, 16)
    detail_layout.setSpacing(10)

    detail_title = QLabel("Select an Item")
    detail_title.setObjectName("SectionTitle")
    detail_title.setWordWrap(True)
    detail_meta = QLabel("Double-click a catalog result to view details and crafting requirements here.")
    detail_meta.setObjectName("MutedText")
    detail_meta.setWordWrap(True)
    detail_image = QLabel()
    detail_image.setFixedSize(96, 96)
    detail_image.setAlignment(Qt.AlignCenter)
    detail_image.setObjectName("CatalogIcon")
    detail_image.setText("*")
    detail_requirements = QTextEdit()
    detail_requirements.setReadOnly(True)
    detail_requirements.setObjectName("TextPreview")
    detail_requirements.setPlaceholderText("Item details will appear here.")

    detail_layout.addWidget(detail_title)
    detail_layout.addWidget(detail_meta)
    detail_layout.addWidget(detail_image, 0, Qt.AlignLeft)
    detail_layout.addWidget(detail_requirements, 1)

    content_splitter.addWidget(scroll)
    content_splitter.addWidget(detail_panel)
    content_splitter.setSizes([780, 360])
    catalog_layout.addWidget(content_splitter, 1)

    def update_stats():
        stats = store.catalog_stats()
        for key, value in stat_cards.items():
            value.setText(f"{int(stats.get(key, 0)):,}")

    def refresh_categories():
        current = (category.currentText() or "").strip()
        target = current or "Placeable"
        category.blockSignals(True)
        category.clear()
        category.addItem("All")
        for cat in store.item_categories():
            category.addItem(cat)
        idx = category.findText(target)
        category.setCurrentIndex(idx if idx >= 0 else 0)
        category.blockSignals(False)

    def requirement_lines(row):
        recipes = store.recipes_for_item(row["name"])
        if not recipes:
            return ["No crafting requirement data is available for this item yet."]
        lines = []
        for recipe in recipes:
            lines.append(f"{recipe['station'] or 'Unknown Station'}")
            lines.append(f"Output: {recipe['output_item']} x{recipe['output_qty']}")
            materials = store.recipe_materials(recipe["id"], int(recipe["output_qty"] or 1))
            if materials:
                lines.append("Requires:")
                for mat, amount in materials:
                    lines.append(f"  - {mat}: {amount:g}")
            lines.append("")
        return lines

    def open_item_detail(row):
        detail_title.setText(row["name"])
        meta_parts = [row["category"] or "Item"]
        if "subcategory" in row.keys() and row["subcategory"]:
            meta_parts.append(row["subcategory"])
        detail_meta.setText(
            " - ".join(meta_parts)
            + f"\nTier: {row['tier'] or '-'}    Rarity: {row['rarity'] or '-'}\nStack: {row['stack_size'] or '-'}    Volume: {row['volume'] or '-'}"
        )

        image_path = row["image_path"] if "image_path" in row.keys() else ""
        detail_image.clear()
        detail_image.setText("*")
        if image_path:
            resolved = store.resolve_catalog_asset_path(image_path)
            pix = QPixmap(resolved)
            if not pix.isNull():
                detail_image.setPixmap(pix.scaled(88, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        detail_image.setVisible(True)

        detail_text = [
            "DESCRIPTION",
            row["notes"] or "No description available.",
            "",
            "CRAFTING REQUIREMENTS",
            *requirement_lines(row),
        ]
        detail_requirements.setPlainText("\n".join(detail_text))

    def make_item_row(row):
        """Compact result row: name only.

        The catalog list is intentionally text-only for speed. Images, tier,
        stack size, rarity, description, and requirements appear only in the
        right-side details panel after double-click.
        """
        item = QFrame()
        item.setObjectName("CatalogCompactRow")
        item.setMinimumHeight(38)
        item.setCursor(Qt.PointingHandCursor)
        outer = QHBoxLayout(item)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(8)

        name = QLabel(row["name"])
        name.setObjectName("CatalogCompactName")
        name.setWordWrap(False)
        outer.addWidget(name, 1)

        item.setToolTip("Double-click to show image, details, and crafting requirements in the side panel")
        item.mouseDoubleClickEvent = lambda event, r=row: open_item_detail(r)
        return item

    def clear_grid():
        while list_layout.count():
            item = list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    render_state = {"rows": [], "index": 0, "token": 0, "craftable": set()}
    render_timer = QTimer(page)
    render_timer.setInterval(1)

    def _render_next_batch():
        token = render_state.get("token", 0)
        rows = render_state.get("rows", [])
        start = int(render_state.get("index", 0))
        if start >= len(rows):
            render_timer.stop()
            import_status.setText(f"Showing {len(rows):,} catalog results. Double-click an item for image/details." if rows else "Ready")
            return
        batch_size = 120
        end = min(start + batch_size, len(rows))
        for index in range(start, end):
            if token != render_state.get("token", 0):
                return
            row = rows[index]
            list_layout.addWidget(make_item_row(row), index, 0)
        render_state["index"] = end
        list_layout.setRowStretch(len(rows) + 1, 1)
        import_status.setText(f"Loading catalog results... {end:,} / {len(rows):,}")

    render_timer.timeout.connect(_render_next_batch)

    refresh_debounce = QTimer(page)
    refresh_debounce.setSingleShot(True)
    refresh_debounce.setInterval(250)

    def refresh():
        render_state["token"] += 1
        render_timer.stop()
        clear_grid()
        update_stats()

        query = search.text().strip()
        selected_category = category.currentText() or "All"
        if not query and selected_category == "All":
            empty = _card(
                "Search or select a category",
                "Type an item name, material, weapon, vehicle, building, or choose a category above to show results.",
                150,
            )
            list_layout.addWidget(empty, 0, 0)
            import_status.setText("Catalog ready. Search or choose a category to display items.")
            return

        import_status.setText("Querying catalog...")
        rows = store.list_items(query, selected_category)
        if not rows:
            empty = _card("No matching items", "Try a different search term or category.", 140)
            list_layout.addWidget(empty, 0, 0)
            import_status.setText("No catalog items matched your search/filter.")
            return
        render_state["rows"] = rows
        render_state["craftable"] = store.craftable_item_names()
        render_state["index"] = 0
        import_status.setText(f"Preparing {len(rows):,} catalog items...")
        render_timer.start()

    def schedule_refresh(*_args):
        refresh_debounce.start()

    refresh_debounce.timeout.connect(refresh)

    def load_exports_catalog():
        answer = QMessageBox.question(
            page,
            "Load Exports Catalog",
            "Reload the optimized bundled catalog database? This runs in the background and replaces the current catalog.",
        )
        if answer != QMessageBox.Yes:
            return

        import_progress.setVisible(True)
        import_progress.setRange(0, 0)
        load_exports_btn.setEnabled(False)
        delete_imported_btn.setEnabled(False)
        import_status.setText("Starting bundled catalog reload...")

        worker = CompanionImportWorker("catalog", parent=page)
        page._catalog_import_worker = worker
        worker.progress.connect(lambda msg: import_status.setText(str(msg)))

        def done(stats):
            import_progress.setVisible(False)
            load_exports_btn.setEnabled(True)
            delete_imported_btn.setEnabled(True)
            import_status.setText(f"Loaded {stats.get('items', 0):,} items and {stats.get('recipes', 0):,} recipes.")
            window.notify("Catalog Loaded", f"{stats.get('items', 0):,} items - {stats.get('recipes', 0):,} recipes", "success")
            refresh_categories()
            refresh()
            craft_tab = tabs.widget(1)
            if hasattr(craft_tab, "refresh_companion_craft"):
                craft_tab.refresh_companion_craft()
            page._catalog_import_worker = None

        def fail(message):
            import_progress.setVisible(False)
            load_exports_btn.setEnabled(True)
            delete_imported_btn.setEnabled(True)
            import_status.setText("Catalog import failed.")
            QMessageBox.warning(page, "Catalog Import Failed", str(message))
            page._catalog_import_worker = None

        worker.finished_ok.connect(done)
        worker.failed.connect(fail)
        worker.start()

    def delete_imported_items():
        answer = QMessageBox.question(
            page,
            "Delete Imported Items",
            "Delete all imported catalog items and recipe data so you can start fresh?",
        )
        if answer != QMessageBox.Yes:
            return
        stats = store.clear_imported_catalog_items(include_recipes=True)
        import_status.setText(f"Deleted {stats.get('items', 0):,} items and {stats.get('recipes', 0):,} recipes.")
        refresh_categories()
        refresh()
        craft_tab = tabs.widget(1)
        if hasattr(craft_tab, "refresh_companion_craft"):
            craft_tab.refresh_companion_craft()
        window.notify("Catalog Cleared", "Imported catalog and recipe data deleted.", "success")

    search.textChanged.connect(schedule_refresh)
    category.currentTextChanged.connect(schedule_refresh)
    load_exports_btn.clicked.connect(load_exports_catalog)
    delete_imported_btn.clicked.connect(delete_imported_items)

    refresh_categories()
    refresh()
    catalog_tab.refresh_companion_catalog = refresh

    craft_tab = _strip_embedded_banner(build_crafting_page(window))
    tabs.addTab(catalog_tab, "Catalog")
    tabs.addTab(craft_tab, "Build Calculator")
    page.refresh_companion_catalog = refresh
    return page

def build_crafting_page(window) -> QWidget:
    page, layout = window._page_shell(
        "Build Calculator",
        "Add placeable items and quantities to calculate your base power and water balance.",
    )
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(12)
    page.setObjectName("BuildCalculatorPage")
    page.setObjectName("BuildCalculatorPage")

    def apply_build_theme() -> None:
        c = theme_colors(db.get_setting("color_theme", "dune") or "dune")
        page.setStyleSheet(f"""
            QWidget#BuildCalculatorPage {{ background: {c['bg']}; color: {c['text']}; }}
            QFrame#BuildOuterCard, QFrame#BuildPanel, QFrame#BuildSummaryPanel, QFrame#BuildBreakdownPanel, QFrame#BuildTipBar {{
                background: {c['panel']}; border: none; border-radius: 8px;
            }}
            QFrame#BuildItemsHeader {{ background: {c['secondary']}; border: none; border-radius: 0; }}
            QFrame#BuildItemRow {{ background: transparent; border: none; border-radius: 0; }}
            QLabel#BuildSubtitle, QLabel#BuildMuted, QLabel#BuildUnit {{ color: {c['muted']}; font-size: 13px; }}
            QLabel#BuildSectionTitle {{ color: {c['accent']}; font-size: 16px; font-weight: 900; }}
            QLabel#BuildColumnTitle {{ color: {c['muted']}; font-size: 12px; font-weight: 800; }}
            QLabel#BuildStatusMessage {{ color: {c['text']}; font-size: 16px; font-weight: 800; }}
            QLabel#BuildStatusValue {{ color: {c['text']}; font-size: 15px; font-weight: 900; }}
            QLabel#BuildGroupHeader {{ color: {c['accent']}; font-size: 13px; font-weight: 950; padding: 12px 10px 5px 10px; }}
            QLabel#BuildBadge {{ background: {c['accent_faint']}; color: {c['text']}; border: none; border-radius: 6px; padding: 3px 8px; font-size: 12px; font-weight: 800; }}
            QLabel#BuildItemName {{ color: {c['text']}; font-size: 14px; font-weight: 800; }}
            QLabel#BuildItemType {{ color: {c['accent']}; font-size: 12px; }}
            QLabel#BuildItemImage, QLabel#BuildBreakdownImage {{ background: rgba(0,0,0,0.24); border: none; border-radius: 5px; color: {c['muted']}; }}
            QPushButton#BuildQtyButton {{ background: {c['secondary']}; border: none; border-radius: 5px; color: {c['text']}; font-size: 18px; font-weight: 700; }}
            QPushButton#BuildQtyButton:hover {{ background: {c['hover']}; border: none; }}
            QLabel#BuildQtyValue {{ background: rgba(0,0,0,0.30); color: {c['text']}; font-size: 15px; font-weight: 900; qproperty-alignment: AlignCenter; }}
            QPushButton#BuildClearButton {{ background: {c['danger_soft']}; border: none; border-radius: 6px; color: {c['danger']}; font-size: 12px; font-weight: 800; padding: 10px 14px; }}
            QLabel#BuildStatIcon {{ font-size: 26px; font-weight: 900; }}
            QLabel#BuildStatValue {{ color: {c['text']}; font-size: 28px; font-weight: 900; }}
            QLabel#BuildStatusBadge {{ background: {c['success_soft']}; border-radius: 5px; color: {c['success']}; font-size: 11px; font-weight: 900; padding: 5px 8px; }}
            QFrame#BuildStatusBanner {{ background: {c['accent_faint']}; border: none; border-radius: 6px; }}
            QLabel#BuildBreakHead {{ color: {c['muted']}; font-size: 11px; font-weight: 900; }}
            QLabel#BuildTableCell {{ color: {c['text']}; font-size: 12px; }}
            QLabel#BuildTotalLabel {{ color: {c['accent']}; font-size: 18px; font-weight: 900; }}
            QScrollArea {{ background: transparent; border: 0; }}
            QScrollBar:vertical {{ background: rgba(0,0,0,0.20); width: 8px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {c['accent_soft']}; border-radius: 4px; min-height: 42px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

    page.refresh_theme_assets = apply_build_theme
    apply_build_theme()

    rows = list(store.build_calculator_items())
    quantities: dict[int, int] = {int(row["id"]): 0 for row in rows}
    qty_labels: dict[int, QLabel] = {}
    green, red, purple, blue = "#45F36B", "#FF3E48", "#C15CFF", "#4FA4FF"

    def number_text(value: float, plus: bool = False, dash_zero: bool = False, negative: bool = False) -> str:
        value = float(value or 0)
        if dash_zero and abs(value) < 0.000001:
            return "-"
        sign = "-" if value < 0 else ""
        if negative and value > 0:
            sign = "-"
        elif plus and value > 0:
            sign = "+"
        amount = abs(value)
        body = f"{int(round(amount)):,}" if abs(amount - round(amount)) < 0.000001 else f"{amount:,.2f}".rstrip("0").rstrip(".")
        return f"{sign}{body}"

    def row_float(row, key: str) -> float:
        try:
            return float(row[key] or 0)
        except Exception:
            return 0.0

    def set_label_color(label: QLabel, color: str) -> None:
        label.setStyleSheet(f"color: {color};")

    def make_image_label(image_path: str, size: int = 42) -> QLabel:
        label = QLabel("*")
        label.setObjectName("BuildItemImage" if size > 30 else "BuildBreakdownImage")
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignCenter)
        if image_path:
            pix = QPixmap(store.resolve_catalog_asset_path(image_path))
            if not pix.isNull():
                label.setText("")
                label.setPixmap(pix.scaled(size - 8, size - 8, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return label

    outer = QFrame()
    outer.setObjectName("BuildOuterCard")
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(14, 14, 14, 8)
    outer_layout.setSpacing(14)
    layout.addWidget(outer, 1)

    main_row = QHBoxLayout()
    main_row.setSpacing(18)
    outer_layout.addLayout(main_row, 1)

    left_panel = QFrame()
    left_panel.setObjectName("BuildPanel")
    left_panel.setMinimumWidth(430)
    left_layout = QVBoxLayout(left_panel)
    left_layout.setContentsMargins(0, 0, 0, 12)
    left_layout.setSpacing(0)
    main_row.addWidget(left_panel, 5)

    items_header = QFrame()
    items_header.setObjectName("BuildItemsHeader")
    items_header_layout = QHBoxLayout(items_header)
    items_header_layout.setContentsMargins(18, 13, 18, 13)
    items_header_layout.setSpacing(10)
    left_title = QLabel("PLACEABLE ITEMS")
    left_title.setObjectName("BuildSectionTitle")
    count_badge = QLabel(f"{len(rows):,}")
    count_badge.setObjectName("BuildBadge")
    qty_head = QLabel("QUANTITY")
    qty_head.setObjectName("BuildColumnTitle")
    items_header_layout.addWidget(left_title)
    items_header_layout.addWidget(count_badge)
    items_header_layout.addStretch(1)
    items_header_layout.addWidget(qty_head)
    left_layout.addWidget(items_header)

    item_scroll = QScrollArea()
    item_scroll.setWidgetResizable(True)
    item_scroll.setFrameShape(QFrame.NoFrame)
    item_scroll.setMinimumHeight(360)
    item_inner = QWidget()
    item_list = QVBoxLayout(item_inner)
    item_list.setContentsMargins(14, 0, 14, 8)
    item_list.setSpacing(0)
    item_scroll.setWidget(item_inner)
    left_layout.addWidget(item_scroll, 1)

    clear_btn = QPushButton("Clear All Items")
    clear_btn.setObjectName("BuildClearButton")
    clear_btn.setMinimumHeight(42)
    clear_wrap = QVBoxLayout()
    clear_wrap.setContentsMargins(14, 12, 14, 8)
    clear_wrap.addWidget(clear_btn)
    left_layout.addLayout(clear_wrap)

    right_col = QVBoxLayout()
    right_col.setSpacing(6)
    main_row.addLayout(right_col, 7)

    summary_heading = QHBoxLayout()
    summary_icon = QLabel("")
    summary_icon.setObjectName("BuildSectionTitle")
    summary_label = QLabel("BASE SUMMARY")
    summary_label.setObjectName("BuildSectionTitle")
    summary_heading.addWidget(summary_icon)
    summary_heading.addWidget(summary_label)
    summary_heading.addStretch(1)
    right_col.addLayout(summary_heading)

    summary_panel = QFrame()
    summary_panel.setObjectName("BuildSummaryPanel")
    summary_grid = QGridLayout(summary_panel)
    summary_grid.setContentsMargins(18, 18, 18, 18)
    summary_grid.setHorizontalSpacing(0)
    summary_grid.setVerticalSpacing(12)
    right_col.addWidget(summary_panel)

    stat_defs = [("generated", "P+", "POWER GENERATED", green, "Power"), ("used", "P-", "POWER USED", red, "Power"), ("net", "NET", "NET POWER", purple, "Power"), ("water", "H2O", "WATER GENERATED", blue, "/ day")]
    stat_values: dict[str, QLabel] = {}
    net_badge = QLabel("SURPLUS")
    net_badge.setObjectName("BuildStatusBadge")
    for col, (key, icon_text, label_text, color, unit_text) in enumerate(stat_defs):
        stat_box = QVBoxLayout()
        stat_box.setSpacing(8)
        icon = QLabel(icon_text)
        icon.setObjectName("BuildStatIcon")
        icon.setAlignment(Qt.AlignCenter)
        set_label_color(icon, color)
        label = QLabel(label_text)
        label.setObjectName("BuildColumnTitle")
        label.setAlignment(Qt.AlignCenter)
        value = QLabel("0")
        value.setObjectName("BuildStatValue")
        value.setAlignment(Qt.AlignCenter)
        unit = QLabel(unit_text)
        unit.setObjectName("BuildUnit")
        unit.setAlignment(Qt.AlignCenter)
        stat_box.addWidget(icon)
        stat_box.addWidget(label)
        stat_box.addWidget(value)
        stat_box.addWidget(unit)
        stat_box.addWidget(net_badge, 0, Qt.AlignCenter) if key == "net" else stat_box.addSpacing(25)
        summary_grid.addLayout(stat_box, 0, col)
        summary_grid.setColumnStretch(col, 1)
        stat_values[key] = value

    status_banner = QFrame()
    status_banner.setObjectName("BuildStatusBanner")
    status_layout = QHBoxLayout(status_banner)
    status_layout.setContentsMargins(16, 12, 16, 12)
    status_layout.setSpacing(10)
    status_icon = QLabel("i")
    status_icon.setObjectName("BuildSectionTitle")
    status_message = QLabel("")
    status_message.setObjectName("BuildStatusMessage")
    status_message.setWordWrap(True)
    status_value = QLabel("")
    status_value.setObjectName("BuildStatusValue")
    status_layout.addWidget(status_icon)
    status_layout.addWidget(status_message, 1)
    status_layout.addWidget(status_value)
    right_col.addWidget(status_banner)

    breakdown_panel = QFrame()
    breakdown_panel.setObjectName("BuildBreakdownPanel")
    breakdown_layout = QVBoxLayout(breakdown_panel)
    breakdown_layout.setContentsMargins(16, 14, 16, 14)
    breakdown_layout.setSpacing(10)
    breakdown_title = QLabel("ITEM BREAKDOWN")
    breakdown_title.setObjectName("BuildSectionTitle")
    breakdown_layout.addWidget(breakdown_title)
    breakdown_grid = QGridLayout()
    breakdown_grid.setHorizontalSpacing(10)
    breakdown_grid.setVerticalSpacing(0)
    breakdown_layout.addLayout(breakdown_grid, 1)
    right_col.addWidget(breakdown_panel, 1)

    def clear_grid(grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.deleteLater()
            elif child_layout:
                clear_grid(child_layout)

    def totals() -> tuple[float, float, float, float]:
        generated = used = water = 0.0
        for row in rows:
            qty = quantities.get(int(row["id"]), 0)
            generated += qty * row_float(row, "power_generated")
            used += qty * row_float(row, "power_cost")
            water += qty * row_float(row, "water_gained_per_day")
        return generated, used, generated - used, water

    def add_breakdown_text(text: str, row: int, col: int, color: str = "#F7F2FF", bold: bool = False, align=Qt.AlignCenter) -> QLabel:
        label = QLabel(text)
        label.setObjectName("BuildTableCell")
        label.setAlignment(align)
        label.setStyleSheet(f"color: {color}; {'font-weight: 900;' if bold else ''}")
        breakdown_grid.addWidget(label, row, col)
        return label

    def refresh_breakdown() -> None:
        clear_grid(breakdown_grid)
        for col, text in enumerate(["ITEM", "QUANTITY", "POWER GAINED", "POWER USED", "WATER GAINED / DAY"]):
            head = QLabel(text)
            head.setObjectName("BuildBreakHead")
            head.setAlignment(Qt.AlignLeft if col == 0 else Qt.AlignCenter)
            breakdown_grid.addWidget(head, 0, col)
        selected = [row for row in rows if quantities.get(int(row["id"]), 0) > 0]
        if not selected:
            empty = QLabel("No placeable items selected yet.")
            empty.setObjectName("BuildMuted")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumHeight(170)
            breakdown_grid.addWidget(empty, 1, 0, 1, 5)
            return
        table_row = 1
        for item in selected:
            item_id = int(item["id"])
            qty = quantities[item_id]
            item_cell = QHBoxLayout()
            item_cell.setContentsMargins(0, 4, 0, 4)
            item_cell.setSpacing(8)
            name = QLabel(item["name"])
            name.setObjectName("BuildTableCell")
            item_cell.addWidget(name, 1)
            breakdown_grid.addLayout(item_cell, table_row, 0)
            gained = qty * row_float(item, "power_generated")
            used = qty * row_float(item, "power_cost")
            water = qty * row_float(item, "water_gained_per_day")
            add_breakdown_text(str(qty), table_row, 1)
            add_breakdown_text(number_text(gained, plus=True, dash_zero=True), table_row, 2, green if gained else "#DCD2EF", bool(gained))
            add_breakdown_text(number_text(used, dash_zero=True, negative=True), table_row, 3, red if used else "#DCD2EF", bool(used))
            add_breakdown_text(number_text(water, plus=True, dash_zero=True), table_row, 4, blue if water else "#DCD2EF", bool(water))
            table_row += 1
        generated, used, _net, water = totals()
        spacer = QFrame()
        spacer.setFixedHeight(8)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        breakdown_grid.addWidget(spacer, table_row, 0, 1, 5)
        table_row += 1
        total_label = QLabel("TOTALS")
        total_label.setObjectName("BuildTotalLabel")
        breakdown_grid.addWidget(total_label, table_row, 0)
        add_breakdown_text("", table_row, 1)
        add_breakdown_text(number_text(generated, plus=True), table_row, 2, green, True)
        add_breakdown_text(number_text(used, negative=True), table_row, 3, red, True)
        add_breakdown_text(number_text(water, plus=True), table_row, 4, blue, True)
        breakdown_grid.setColumnStretch(0, 3)
        for col in range(1, 5):
            breakdown_grid.setColumnStretch(col, 2)

    def refresh_totals() -> None:
        generated, used, net, water = totals()
        stat_values["generated"].setText(number_text(generated, plus=True))
        stat_values["used"].setText(number_text(used, negative=True))
        stat_values["net"].setText(number_text(net, plus=True))
        stat_values["water"].setText(number_text(water, plus=True))
        set_label_color(stat_values["generated"], green)
        set_label_color(stat_values["used"], red)
        set_label_color(stat_values["net"], purple)
        set_label_color(stat_values["water"], blue)
        if net > 0:
            net_badge.setText("SURPLUS")
            net_badge.setStyleSheet("background: rgba(57,170,78,0.34); color: #75F58B; border-radius: 5px; padding: 5px 8px; font-weight: 900;")
            status_message.setText("Your base is generating more power than it uses.")
            status_value.setText(f"Power Surplus: {number_text(net, plus=True)}")
        elif net < 0:
            net_badge.setText("DEFICIT")
            net_badge.setStyleSheet("background: rgba(255,62,72,0.24); color: #FF6268; border-radius: 5px; padding: 5px 8px; font-weight: 900;")
            status_message.setText("Your base requires more power than it generates.")
            status_value.setText(f"Additional Power Needed: {number_text(abs(net))}")
        else:
            net_badge.setText("SURPLUS")
            net_badge.setStyleSheet("background: rgba(57,170,78,0.34); color: #75F58B; border-radius: 5px; padding: 5px 8px; font-weight: 900;")
            status_message.setText("Your base power generation and usage are balanced.")
            status_value.setText("Power Balance: 0")
        refresh_breakdown()

    def change_quantity(item_id: int, delta: int) -> None:
        quantities[item_id] = max(0, quantities.get(item_id, 0) + delta)
        label = qty_labels.get(item_id)
        if label is not None:
            label.setText(str(quantities[item_id]))
        refresh_totals()

    def clear_all() -> None:
        for item_id in list(quantities):
            quantities[item_id] = 0
            label = qty_labels.get(item_id)
            if label is not None:
                label.setText("0")
        refresh_totals()

    def clear_item_list() -> None:
        while item_list.count():
            item = item_list.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.deleteLater()
            elif child_layout:
                clear_grid(child_layout)

    def add_group_header(text: str) -> None:
        header = QLabel(text)
        header.setObjectName("BuildGroupHeader")
        item_list.addWidget(header)

    def add_item_row(row) -> None:
        item_id = int(row["id"])
        item_row = QFrame()
        item_row.setObjectName("BuildItemRow")
        item_row.setMinimumHeight(64)
        row_layout = QHBoxLayout(item_row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(12)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        name = QLabel(row["name"])
        name.setObjectName("BuildItemName")
        name.setWordWrap(True)
        subtype = QLabel(row["subcategory"] or row["category"] or "Placeable")
        subtype.setObjectName("BuildItemType")
        copy.addWidget(name)
        copy.addWidget(subtype)
        row_layout.addLayout(copy, 1)
        minus = QPushButton("-")
        minus.setObjectName("BuildQtyButton")
        minus.setFixedSize(34, 34)
        value = QLabel("0")
        value.setObjectName("BuildQtyValue")
        value.setFixedSize(50, 34)
        plus = QPushButton("+")
        plus.setObjectName("BuildQtyButton")
        plus.setFixedSize(34, 34)
        qty_labels[item_id] = value
        minus.clicked.connect(lambda checked=False, ident=item_id: change_quantity(ident, -1))
        plus.clicked.connect(lambda checked=False, ident=item_id: change_quantity(ident, 1))
        row_layout.addWidget(minus)
        row_layout.addWidget(value)
        row_layout.addWidget(plus)
        item_list.addWidget(item_row)

    def render_item_list() -> None:
        nonlocal rows
        rows = list(store.build_calculator_items())
        quantities.clear()
        quantities.update({int(row["id"]): 0 for row in rows})
        qty_labels.clear()
        count_badge.setText(f"{len(rows):,}")
        clear_item_list()
        if rows:
            groups = [
                ("POWER GAIN", [row for row in rows if row_float(row, "power_generated") > 0 or row_float(row, "water_gained_per_day") > 0]),
                ("POWER LOSS", [row for row in rows if row_float(row, "power_generated") <= 0 and row_float(row, "water_gained_per_day") <= 0 and row_float(row, "power_cost") > 0]),
            ]
            for title, group_rows in groups:
                if not group_rows:
                    continue
                add_group_header(title)
                for row in group_rows:
                    add_item_row(row)
            item_list.addStretch(1)
        else:
            empty = QLabel("No power or water placeables were found.")
            empty.setObjectName("BuildMuted")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumHeight(220)
            item_list.addWidget(empty)
            item_list.addStretch(1)

    render_item_list()

    clear_btn.clicked.connect(clear_all)

    tip = QFrame()
    tip.setObjectName("BuildTipBar")
    tip_layout = QHBoxLayout(tip)
    tip_layout.setContentsMargins(18, 12, 18, 12)
    tip_layout.setSpacing(10)
    tip_icon = QLabel("*")
    tip_icon.setStyleSheet("color: #FFD173; font-size: 14px;")
    tip_text = QLabel("Tip: Only placeable items are shown. All values are totals and include any applicable modifiers.")
    tip_text.setObjectName("BuildSubtitle")
    tip_text.setWordWrap(True)
    tip_layout.addWidget(tip_icon)
    tip_layout.addWidget(tip_text, 1)
    outer_layout.addWidget(tip)

    def refresh_companion_craft() -> None:
        render_item_list()
        refresh_totals()

    page.refresh_companion_craft = refresh_companion_craft
    refresh_totals()
    return page

class BlueprintGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(430)
        self.setMouseTracking(True)
        self.tool = "foundation"
        self.cells: dict[tuple[int, int], str] = {}
        self.grid_size = 26

    def set_tool(self, tool: str):
        self.tool = tool

    def mousePressEvent(self, event):
        x = int(event.position().x() // self.grid_size)
        y = int(event.position().y() // self.grid_size)
        key = (x, y)
        if self.tool == "erase" or event.button() == Qt.RightButton:
            self.cells.pop(key, None)
        else:
            self.cells[key] = self.tool
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(18, 15, 12))
        pen = QPen(QColor(92, 76, 48), 1)
        painter.setPen(pen)
        for x in range(0, self.width(), self.grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), self.grid_size):
            painter.drawLine(0, y, self.width(), y)
        colors = {
            "foundation": QColor(166, 135, 74),
            "wall": QColor(118, 104, 86),
            "door": QColor(80, 150, 90),
            "stairs": QColor(130, 95, 170),
            "station": QColor(210, 150, 60),
            "storage": QColor(70, 120, 180),
            "power": QColor(220, 190, 80),
            "note": QColor(190, 80, 70),
        }
        for (x, y), tool in self.cells.items():
            rect = QRectF(x * self.grid_size + 2, y * self.grid_size + 2, self.grid_size - 4, self.grid_size - 4)
            painter.fillRect(rect, QBrush(colors.get(tool, QColor(140, 140, 140))))
            painter.setPen(QPen(QColor(10, 8, 5), 1))
            painter.drawRect(rect)

    def to_json(self) -> str:
        return json.dumps({"cells": [{"x": x, "y": y, "tool": t} for (x, y), t in self.cells.items()]})

    def export_png(self, path: str):
        image = QImage(self.size(), QImage.Format_ARGB32)
        self.render(image)
        image.save(path)


def build_blueprints_page(window) -> QWidget:
    store.seed_samples()
    page, layout = window._page_shell("Blueprints", "Blueprint library from the blueprint market concept.")

    top = QHBoxLayout()
    search = QLineEdit()
    search.setPlaceholderText("Search blueprints by name, base type, tags, or notes...")
    import_btn = QPushButton("Import Blueprints from Web")
    top.addWidget(search, 2)
    top.addWidget(import_btn)
    layout.addLayout(top)

    notice = QLabel("The old 2D build planner has been removed. This page is now a blueprint browser/library. It is ready for blueprint-market style web imports, favorites, tags, previews, and material notes.")
    notice.setObjectName("MutedText")
    notice.setWordWrap(True)
    layout.addWidget(notice)

    _, _, bp_layout = _scroll_content(layout)

    def open_blueprint(row):
        lines = [row["name"], "", f"Type: {row['base_type'] or '-'}", f"Players: {row['players_recommended'] or '-'}", f"Tags: {row['tags'] or '-'}", "", "Power Notes:", row["power_notes"] or "-", "", "Material Notes:", row["material_notes"] or "-"]
        QMessageBox.information(page, "Blueprint Details", "\n".join(lines))

    def make_blueprint_card(row):
        body = f"{row['base_type'] or '-'}  -  Players: {row['players_recommended'] or '-'}\nTags: {row['tags'] or '-'}\n{row['material_notes'] or ''}\nDouble-click for details."
        card = _card(row["name"], body, 135)
        card.setToolTip("Double-click to view blueprint details")
        card.mouseDoubleClickEvent = lambda event, r=row: open_blueprint(r)
        return card

    def refresh_blueprints():
        while bp_layout.count():
            item = bp_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        rows = store.list_blueprints(search.text())
        if not rows:
            bp_layout.addWidget(_card("No blueprints", "Import blueprints from web."))
        for row in rows:
            bp_layout.addWidget(make_blueprint_card(row))
        bp_layout.addStretch(1)

    def import_blueprints():
        try:
            stats = store.import_blueprints_from_web(progress=lambda msg: window.notify("Blueprint Import", msg, "info"))
            refresh_blueprints()
            window.notify("Blueprints Imported", f"Imported {stats.get('blueprints', 0)} blueprint records. Errors: {stats.get('errors', 0)}", "success")
        except Exception as exc:
            QMessageBox.warning(page, "Blueprint Import Failed", f"Could not import blueprints from web:\n{exc}")

    def load_samples():
        store.seed_samples(force=True)
        refresh_blueprints()
        window.notify("Sample Blueprints Ready", "Sample blueprints have been loaded.", "success")

    search.textChanged.connect(refresh_blueprints)
    import_btn.clicked.connect(import_blueprints)
    refresh_blueprints()
    return page


def build_building_page(window) -> QWidget:
    return build_blueprints_page(window)

def build_timers_page(window) -> QWidget:
    """Build one unified timer console with five lab timers and Sandstorm."""
    page, layout = window._page_shell(
        "Timers",
        "Track five laboratories and the next sandstorm from one console.",
    )

    timer_console = QFrame()
    timer_console.setObjectName("UnifiedTimerConsole")
    console_layout = QVBoxLayout(timer_console)
    console_layout.setContentsMargins(24, 22, 24, 24)
    console_layout.setSpacing(16)

    console_header = QHBoxLayout()
    title = QLabel("TIMER CONSOLE")
    title.setObjectName("SectionTitle")
    subtitle = QLabel("Five labs and one sandstorm timer")
    subtitle.setObjectName("MutedText")
    console_header.addWidget(title)
    console_header.addStretch(1)
    console_header.addWidget(subtitle)
    console_layout.addLayout(console_header)

    divider = QFrame()
    divider.setFrameShape(QFrame.HLine)
    divider.setObjectName("TimerDivider")
    console_layout.addWidget(divider)

    rows_container = QWidget()
    rows_layout = QVBoxLayout(rows_container)
    rows_layout.setContentsMargins(0, 0, 0, 0)
    rows_layout.setSpacing(10)
    console_layout.addWidget(rows_container)

    active: dict[str, float] = {}
    now = time.time()
    for persisted_key in ["lab_1", "lab_2", "lab_3", "lab_4", "lab_5", "sandstorm"]:
        try:
            persisted_end = float(store.get_setting(f"timer_{persisted_key}_end", "0") or 0)
        except Exception:
            persisted_end = 0
        if persisted_end > now:
            active[persisted_key] = persisted_end
    status_labels: dict[str, QLabel] = {}
    duration_inputs: dict[str, QSpinBox] = {}
    name_inputs: dict[str, QLineEdit] = {}

    def fmt(seconds: int) -> str:
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def saved_minutes(key: str, default: int) -> int:
        try:
            return max(
                1,
                min(
                    1440,
                    int(store.get_setting(f"timer_{key}_minutes", str(default)) or default),
                ),
            )
        except Exception:
            return default

    def saved_name(key: str, default: str) -> str:
        value = store.get_setting(f"timer_{key}_name", default)
        return str(value or default)

    def save_timer(key: str) -> None:
        duration = duration_inputs.get(key)
        name = name_inputs.get(key)
        if duration is not None:
            store.set_setting(f"timer_{key}_minutes", str(duration.value()))
        if name is not None:
            fallback = "Sandstorm" if key == "sandstorm" else f"Laboratory {key.split('_')[-1]}"
            store.set_setting(
                f"timer_{key}_name",
                name.text().strip() or fallback,
            )

    def start_timer(key: str) -> None:
        duration = duration_inputs.get(key)
        if duration is None:
            return
        save_timer(key)
        seconds = int(duration.value()) * 60
        active[key] = time.time() + seconds
        store.set_setting(f"timer_{key}_end", str(active[key]))
        status = status_labels.get(key)
        if status is not None:
            try:
                status.setText(fmt(seconds))
                status.setProperty("running", True)
                status.style().unpolish(status)
                status.style().polish(status)
            except RuntimeError:
                status_labels.pop(key, None)

        name = name_inputs.get(key)
        timer_name = name.text().strip() if name is not None else "Timer"
        refresh_dashboard = getattr(window, "_refresh_dashboard_active_timers", None)
        if callable(refresh_dashboard):
            refresh_dashboard()
        window.notify(
            "Timer Started",
            f"{timer_name or 'Timer'} is now running.",
            "success",
        )

    def reset_timer(key: str) -> None:
        active.pop(key, None)
        store.set_setting(f"timer_{key}_end", "0")
        status = status_labels.get(key)
        refresh_dashboard = getattr(window, "_refresh_dashboard_active_timers", None)
        if callable(refresh_dashboard):
            refresh_dashboard()
        if status is not None:
            try:
                status.setText("Ready")
                status.setProperty("running", False)
                status.style().unpolish(status)
                status.style().polish(status)
            except RuntimeError:
                status_labels.pop(key, None)

    def add_timer_row(
        key: str,
        default_name: str,
        default_minutes: int,
        *,
        sandstorm: bool = False,
    ) -> None:
        row = QFrame()
        row.setObjectName("SandstormTimerRow" if sandstorm else "LabTimerRow")
        row.setProperty("timerType", "sandstorm" if sandstorm else "lab")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 12, 16, 12)
        row_layout.setSpacing(12)

        name = QLineEdit(saved_name(key, default_name))
        name.setObjectName("TimerNameInput")
        name.setMaxLength(40)
        name.setMinimumWidth(190)
        name.editingFinished.connect(lambda k=key: save_timer(k))

        duration = QSpinBox()
        duration.setObjectName("TimerDurationInput")
        duration.setRange(1, 1440)
        duration.setSuffix(" min")
        duration.setValue(saved_minutes(key, default_minutes))
        duration.setMinimumWidth(112)
        duration.valueChanged.connect(lambda value, k=key: save_timer(k))

        status = QLabel("Ready")
        status.setObjectName("TimerRowStatus")
        status.setAlignment(Qt.AlignCenter)
        status.setMinimumWidth(112)
        status.setProperty("running", False)

        start_button = QPushButton("Start")
        start_button.setObjectName("PrimaryButton")
        start_button.setMinimumWidth(90)
        reset_button = QPushButton("Reset")
        reset_button.setMinimumWidth(90)

        start_button.clicked.connect(lambda checked=False, k=key: start_timer(k))
        reset_button.clicked.connect(lambda checked=False, k=key: reset_timer(k))

        row_layout.addWidget(name, 1)
        row_layout.addWidget(duration)
        row_layout.addWidget(status)
        row_layout.addWidget(start_button)
        row_layout.addWidget(reset_button)

        rows_layout.addWidget(row)
        name_inputs[key] = name
        duration_inputs[key] = duration
        status_labels[key] = status

    for slot in range(1, 6):
        add_timer_row(
            f"lab_{slot}",
            f"Laboratory {slot}",
            45,
        )

    add_timer_row(
        "sandstorm",
        "Sandstorm",
        30,
        sandstorm=True,
    )

    rows_layout.addStretch(1)
    layout.addWidget(timer_console, 1)

    for active_key, active_end in active.items():
        active_label = status_labels.get(active_key)
        if active_label is not None:
            active_label.setText(fmt(int(active_end - time.time())))
            active_label.setProperty("running", True)
            active_label.style().unpolish(active_label)
            active_label.style().polish(active_label)

    def tick() -> None:
        now = time.time()
        for key, end_time in list(active.items()):
            remaining = int(end_time - now)
            label = status_labels.get(key)
            if label is not None:
                try:
                    label.setText(fmt(remaining))
                except RuntimeError:
                    status_labels.pop(key, None)

            if remaining <= 0:
                active.pop(key, None)
                store.set_setting(f"timer_{key}_end", "0")
                if label is not None:
                    try:
                        label.setText("Ready")
                        label.setProperty("running", False)
                        label.style().unpolish(label)
                        label.style().polish(label)
                    except RuntimeError:
                        status_labels.pop(key, None)

                name = name_inputs.get(key)
                timer_name = name.text().strip() if name is not None else "Timer"
                window.notify(
                    "Timer Complete",
                    f"{timer_name or 'Timer'} is ready.",
                    "info",
                )

    timer = QTimer(page)
    timer.setInterval(1000)
    timer.timeout.connect(tick)
    timer.start()

    page._companion_timer = timer
    page._timer_active = active
    page._timer_status_labels = status_labels
    page._timer_duration_inputs = duration_inputs
    page._timer_name_inputs = name_inputs
    return page



def _strip_embedded_banner(tab_page: QWidget) -> QWidget:
    """Remove the page-shell hero/banner when a full page is embedded inside Game Manager tabs."""
    lay = tab_page.layout()
    if lay and lay.count():
        first = lay.itemAt(0).widget()
        if first is not None and first.__class__.__name__ == "HeroFrame":
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(10)
    return tab_page

def _action_card(title: str, body: str, buttons: list[QPushButton], min_h: int = 145) -> QFrame:
    frame = _card(title, body, min_h)
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addStretch(1)
    for btn in buttons:
        row.addWidget(btn)
    frame.layout().addLayout(row)
    return frame

def build_game_manager_page(window) -> QWidget:
    page, layout = window._page_shell("Game Manager", "Set your Dune Awakening game/config folder.")

    card = QFrame()
    card.setObjectName("CommandCard")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(16, 14, 16, 14)
    card_layout.setSpacing(10)

    title = QLabel("CONFIG FOLDER")
    title.setObjectName("CardTitle")
    card_layout.addWidget(title)

    game_path = QLineEdit(store.get_setting("game_folder", "") or store.detect_dune_game_folder())
    game_path.setPlaceholderText("Dune Awakening game folder or config folder")
    browse = QPushButton("Browse")
    auto_detect = QPushButton("Auto Detect")
    save = QPushButton("Save Path")
    open_btn = QPushButton("Open Folder")

    row = QHBoxLayout()
    row.addWidget(game_path, 1)
    row.addWidget(browse)
    row.addWidget(auto_detect)
    row.addWidget(save)
    row.addWidget(open_btn)
    card_layout.addLayout(row)

    layout.addWidget(card)

    tweaks_card = QFrame()
    tweaks_card.setObjectName("CommandCard")
    tweaks_layout = QVBoxLayout(tweaks_card)
    tweaks_layout.setContentsMargins(16, 14, 16, 14)
    tweaks_layout.setSpacing(10)
    tweaks_title = QLabel("ENGINE TWEAKS")
    tweaks_title.setObjectName("CardTitle")
    tweaks_layout.addWidget(tweaks_title)
    tweaks_hint = QLabel("Select only the tweaks you want. StankyTools creates a backup before editing Engine.ini.")
    tweaks_hint.setObjectName("MutedText")
    tweaks_hint.setWordWrap(True)
    tweaks_layout.addWidget(tweaks_hint)

    tweak_checks = {}
    tweak_grid = QGridLayout()
    tweak_grid.setHorizontalSpacing(16)
    tweak_grid.setVerticalSpacing(8)
    row_index = 0
    for i, (key, data) in enumerate(store.ENGINE_TWEAKS.items()):
        label = data[0] if isinstance(data, tuple) else str(key)
        chk = QCheckBox(label)
        chk.setObjectName("ThemeCheck")
        tweak_checks[key] = chk
        tweak_grid.addWidget(chk, i // 2, i % 2)
        row_index = max(row_index, i // 2)
    start_col = len(store.ENGINE_TWEAKS) % 2
    row_index = len(store.ENGINE_TWEAKS) // 2
    for j, (key, data) in enumerate(getattr(store, "LAUNCH_TWEAKS", {}).items()):
        label = data[0] if isinstance(data, tuple) else str(key)
        chk = QCheckBox(label)
        chk.setObjectName("ThemeCheck")
        chk.setToolTip("Copies the recommended Steam launch option: -nostartupscreen")
        tweak_checks[key] = chk
        n = len(store.ENGINE_TWEAKS) + j
        tweak_grid.addWidget(chk, n // 2, n % 2)
    tweaks_layout.addLayout(tweak_grid)

    tweak_status = QLabel("Select tweaks, then apply them to your selected config folder.")
    tweak_status.setObjectName("MutedText")
    tweaks_layout.addWidget(tweak_status)

    tweak_buttons = QHBoxLayout()
    apply_tweaks_btn = QPushButton("Apply Selected Tweaks")
    apply_tweaks_btn.setObjectName("PrimaryButton")
    remove_tweaks_btn = QPushButton("Remove StankyTools Tweaks")
    remove_tweaks_btn.setObjectName("PrimaryButton")
    tweak_buttons.addWidget(apply_tweaks_btn)
    tweak_buttons.addWidget(remove_tweaks_btn)
    tweak_buttons.addStretch(1)
    tweaks_layout.addLayout(tweak_buttons)
    layout.addWidget(tweaks_card)
    layout.addStretch(1)

    def auto_detect_path():
        detected = store.detect_dune_game_folder()
        if detected:
            game_path.setText(detected)
            store.set_setting("game_folder", detected)
            window.notify("Game Folder Detected", detected, "success")
        else:
            QMessageBox.information(page, "Auto Detect", "Dune Awakening was not found automatically. Please browse to the game or config folder.")

    def browse_path():
        path = QFileDialog.getExistingDirectory(page, "Select Dune Awakening or Config Folder", game_path.text() or str(Path.home()))
        if path:
            game_path.setText(path)

    def save_path():
        store.set_setting("game_folder", game_path.text().strip())
        window.notify("Game Folder Saved", game_path.text().strip() or "Path cleared.", "success")

    def open_folder():
        import os
        path = game_path.text().strip()
        if not path:
            QMessageBox.information(page, "Open Folder", "Set a game/config folder first.")
            return
        os.startfile(path) if hasattr(os, "startfile") else None

    def selected_tweaks():
        return [key for key, chk in tweak_checks.items() if chk.isChecked()]

    def apply_selected_tweaks():
        path = game_path.text().strip()
        if not path:
            QMessageBox.information(page, "Engine Tweaks", "Set a game/config folder first.")
            return
        try:
            result = store.apply_engine_tweaks(path, selected_tweaks())
            launch_options = result.get("launch_options", []) or []
            if launch_options:
                QApplication.clipboard().setText(" ".join(launch_options))
            message = "Applied: " + ", ".join(result.get("tweaks", []))
            if launch_options:
                message += " | Launch option copied: " + " ".join(launch_options)
            tweak_status.setText(message)
            window.notify("Tweaks Applied", f"Applied {result.get('count', 0)} tweak(s).", "success")
        except Exception as exc:
            QMessageBox.warning(page, "Tweaks Failed", str(exc))

    def remove_stankytools_tweaks():
        path = game_path.text().strip()
        if not path:
            QMessageBox.information(page, "Engine Tweaks", "Set a game/config folder first.")
            return
        try:
            result = store.clear_engine_tweaks(path)
            tweak_status.setText(f"Removed {result.get('removed', 0)} StankyTools tweak block(s).")
            window.notify("Tweaks Removed", "StankyTools tweak blocks removed.", "success")
        except Exception as exc:
            QMessageBox.warning(page, "Remove Failed", str(exc))

    browse.clicked.connect(browse_path)
    auto_detect.clicked.connect(auto_detect_path)
    save.clicked.connect(save_path)
    open_btn.clicked.connect(open_folder)
    apply_tweaks_btn.clicked.connect(apply_selected_tweaks)
    remove_tweaks_btn.clicked.connect(remove_stankytools_tweaks)
    return page


