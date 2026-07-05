from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import webbrowser
from pathlib import Path

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
from . import db
from .catalog_importer import import_catalog
from . import deep_desert

FONT = ("Segoe UI", 11)
FONT_BIG = ("Segoe UI", 16, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")
BG = "#15120d"
PANEL = "#211b13"
PANEL_2 = "#2b2318"
GOLD = "#c9a34e"
TEXT = "#eadfca"
MUTED = "#9f9173"
PURPLE = "#5c4acf"


def money(value):
    if value is None:
        return "—"
    try:
        return f"{int(value):,}"
    except Exception:
        return "—"


class StankyMarketApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stanky Market")
        self.geometry("1240x780")
        self.minsize(1000, 640)
        self.configure(bg=BG)
        self.selected_item_id: int | None = None
        self.selected_item_name: str = ""
        self._build_style()
        self._build_ui()
        self.refresh_all()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT)
        style.configure("Title.TLabel", background=BG, foreground=GOLD, font=FONT_TITLE)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=FONT)
        style.configure("Big.Panel.TLabel", background=PANEL, foreground=GOLD, font=FONT_BIG)
        style.configure("TButton", font=FONT, padding=8, background=PANEL_2, foreground=TEXT)
        style.map("TButton", background=[("active", "#3a2f20")])
        style.configure("Accent.TButton", font=FONT, padding=9, background=GOLD, foreground="#16130e")
        style.configure("TEntry", fieldbackground="#110f0b", foreground=TEXT, insertcolor=TEXT, font=FONT)
        style.configure("TCombobox", fieldbackground="#110f0b", foreground=TEXT, font=FONT)
        style.configure("Treeview", background="#110f0b", foreground=TEXT, fieldbackground="#110f0b", rowheight=34, font=FONT)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=GOLD, font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", PURPLE)])

    def _build_ui(self):
        header = ttk.Frame(self, padding=(20, 18, 20, 8))
        header.pack(fill="x")
        ttk.Label(header, text="STANKY MARKET", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Clean rebuild foundation — price recording + market stats", style="Muted.TLabel").pack(side="left", padx=18)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill="both", expand=True)

        self.market_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=16)
        self.catalog_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=16)
        self.scanner_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=16)
        self.history_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=16)
        self.deep_desert_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=16)

        self.notebook.add(self.market_tab, text="  Market  ")
        self.notebook.add(self.scanner_tab, text="  Price Scanner  ")
        self.notebook.add(self.catalog_tab, text="  Catalog  ")
        self.notebook.add(self.history_tab, text="  History  ")
        self.notebook.add(self.deep_desert_tab, text="  Deep Desert  ")

        self._build_market_tab()
        self._build_scanner_tab()
        self._build_catalog_tab()
        self._build_history_tab()
        self._build_deep_desert_tab()

    def _tree(self, parent, columns):
        tree = ttk.Treeview(parent, columns=list(columns.keys()), show="headings", selectmode="browse")
        for col, width in columns.items():
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w")
        y = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=y.set)
        tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")
        return tree

    def _build_market_tab(self):
        top = ttk.Frame(self.market_tab, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Market Overview", style="Big.Panel.TLabel").pack(side="left")
        self.market_search = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.market_search, width=34)
        entry.pack(side="right")
        entry.bind("<KeyRelease>", lambda e: self.refresh_market())
        ttk.Label(top, text="Search", style="Panel.TLabel").pack(side="right", padx=(0, 8))

        cols = {
            "Name": 240,
            "Category": 170,
            "Type": 110,
            "Grade": 70,
            "Low": 120,
            "Avg": 120,
            "High": 120,
            "Seen": 70,
            "Last Seen": 180,
        }
        self.market_tree = self._tree(self.market_tab, cols)
        self.market_tree.bind("<<TreeviewSelect>>", self._market_selected)

    def _build_scanner_tab(self):
        wrapper = ttk.Frame(self.scanner_tab, style="Panel.TFrame")
        wrapper.pack(fill="both", expand=True)

        left = ttk.Frame(wrapper, style="Panel.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right = ttk.Frame(wrapper, style="Panel.TFrame")
        right.pack(side="right", fill="y")

        ttk.Label(left, text="Select item to update", style="Big.Panel.TLabel").pack(anchor="w", pady=(0, 8))
        self.scan_search = tk.StringVar()
        scan_entry = ttk.Entry(left, textvariable=self.scan_search)
        scan_entry.pack(fill="x", pady=(0, 10))
        scan_entry.bind("<KeyRelease>", lambda e: self.refresh_scanner_catalog())
        cols = {"ID": 60, "Name": 260, "Category": 170, "Type": 110}
        self.scan_tree = self._tree(left, cols)
        self.scan_tree.bind("<<TreeviewSelect>>", self._scan_item_selected)

        ttk.Label(right, text="Price Recorder", style="Big.Panel.TLabel").pack(anchor="w", pady=(0, 12))
        self.selected_label = ttk.Label(right, text="No item selected", style="Panel.TLabel", wraplength=330)
        self.selected_label.pack(anchor="w", pady=(0, 18))

        ttk.Label(right, text="Price", style="Panel.TLabel").pack(anchor="w")
        self.price_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.price_var, width=26).pack(anchor="w", pady=(2, 10))

        ttk.Label(right, text="Grade (blank for resources)", style="Panel.TLabel").pack(anchor="w")
        self.grade_var = tk.StringVar()
        grade = ttk.Combobox(right, textvariable=self.grade_var, values=["", "0", "1", "2", "3", "4", "5"], width=23, state="readonly")
        grade.pack(anchor="w", pady=(2, 10))

        ttk.Label(right, text="Note", style="Panel.TLabel").pack(anchor="w")
        self.note_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.note_var, width=26).pack(anchor="w", pady=(2, 14))

        ttk.Button(right, text="Record Price", style="Accent.TButton", command=self.record_price).pack(anchor="w", fill="x", pady=(0, 10))
        ttk.Label(right, text="This foundation uses manual price entry. The screen OCR module will connect to this same save path next.", style="Panel.TLabel", wraplength=330).pack(anchor="w", pady=8)

    def _build_catalog_tab(self):
        top = ttk.Frame(self.catalog_tab, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Catalog", style="Big.Panel.TLabel").pack(side="left")

        filters = ttk.Frame(top, style="Panel.TFrame")
        filters.pack(side="right")
        ttk.Label(filters, text="Name Search", style="Panel.TLabel").pack(side="left", padx=(0, 6))
        self.catalog_search = tk.StringVar()
        entry = ttk.Entry(filters, textvariable=self.catalog_search, width=30)
        entry.pack(side="left", padx=(0, 12))
        entry.bind("<KeyRelease>", lambda e: self.refresh_catalog())

        ttk.Label(filters, text="Category", style="Panel.TLabel").pack(side="left", padx=(0, 6))
        self.catalog_category = tk.StringVar(value="All Categories")
        self.category_combo = ttk.Combobox(filters, textvariable=self.catalog_category, values=["All Categories"], width=24, state="readonly")
        self.category_combo.pack(side="left")
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_catalog())

        form = ttk.Frame(self.catalog_tab, style="Panel.TFrame")
        form.pack(fill="x", pady=(0, 12))
        self.new_name = tk.StringVar()
        self.new_category = tk.StringVar()
        ttk.Label(form, text="Name", style="Panel.TLabel").pack(side="left", padx=(0, 4))
        ttk.Entry(form, textvariable=self.new_name, width=28).pack(side="left", padx=(0, 10))
        ttk.Label(form, text="Category", style="Panel.TLabel").pack(side="left", padx=(0, 4))
        ttk.Entry(form, textvariable=self.new_category, width=24).pack(side="left", padx=(0, 10))
        ttk.Button(form, text="Add Item", command=self.add_item).pack(side="left")

        cols = {"ID": 60, "Name": 360, "Category": 220, "Image": 90}
        self.catalog_tree = self._tree(self.catalog_tab, cols)
        self.catalog_tree.bind("<Double-1>", self._open_catalog_source)

        import_bar = ttk.Frame(self.catalog_tab, style="Panel.TFrame")
        import_bar.pack(fill="x", pady=(10, 0))
        ttk.Button(import_bar, text="Import Dune Item Database", style="Accent.TButton", command=self.import_dune_catalog).pack(side="left")
        self.import_status = ttk.Label(import_bar, text="Uses only 9 categories: Weapons, Garments, Vehicles, Utility, Augmentations, Components, Raw Resources, Refined Resources, Fuel.", style="Panel.TLabel")
        self.import_status.pack(side="left", padx=12)

    def _build_history_tab(self):
        ttk.Label(self.history_tab, text="Price History", style="Big.Panel.TLabel").pack(anchor="w", pady=(0, 10))
        cols = {"Item": 260, "Grade": 80, "Price": 130, "Observed": 190, "Note": 240}
        self.history_tree = self._tree(self.history_tab, cols)

    def _build_deep_desert_tab(self):
        self.deep_zoom = 1.0
        self.deep_pan_x = 0
        self.deep_pan_y = 0
        self.deep_drag_start = None
        self.deep_add_poi_mode = False
        self.deep_original_image = None
        self.deep_rendered_photo = None
        self.deep_marker_ids = []

        split = ttk.Frame(self.deep_desert_tab, style="Panel.TFrame")
        split.pack(fill="both", expand=True, padx=0, pady=0)

        map_frame = ttk.Frame(split, style="Panel.TFrame")
        map_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=0)
        self.deep_canvas = tk.Canvas(map_frame, bg="#0f0d09", highlightthickness=1, highlightbackground=GOLD)
        self.deep_canvas.pack(fill="both", expand=True)
        self.deep_canvas.bind("<ButtonPress-1>", self.deep_canvas_click)
        self.deep_canvas.bind("<B1-Motion>", self.deep_canvas_drag)
        self.deep_canvas.bind("<ButtonRelease-1>", self.deep_canvas_release)
        self.deep_canvas.bind("<MouseWheel>", self.deep_canvas_wheel)
        self.deep_canvas.bind("<Configure>", lambda e: self.fit_deep_map_to_canvas(redraw=True) if self.deep_original_image else self.render_deep_map())

        side = ttk.Frame(split, style="Panel.TFrame", width=260)
        side.pack(side="right", fill="y", pady=0)
        side.pack_propagate(False)

        ttk.Button(side, text="Check Map Update", style="Accent.TButton", command=self.check_deep_desert_update).pack(fill="x", pady=(0, 8))
        ttk.Button(side, text="Zoom +", command=lambda: self.zoom_deep_map(1.25)).pack(fill="x", pady=(0, 6))
        ttk.Button(side, text="Zoom -", command=lambda: self.zoom_deep_map(0.8)).pack(fill="x", pady=(0, 6))
        ttk.Button(side, text="Fit Map", command=self.fit_deep_map_to_canvas).pack(fill="x", pady=(0, 6))
        ttk.Button(side, text="Reset View", command=self.reset_deep_map_view).pack(fill="x", pady=(0, 10))
        ttk.Button(side, text="Add POI", command=self.enable_add_poi).pack(fill="x", pady=(0, 6))
        ttk.Button(side, text="Delete Selected POI", command=self.delete_selected_poi).pack(fill="x", pady=(0, 14))

        ttk.Label(side, text="POIs", style="Big.Panel.TLabel").pack(anchor="w", pady=(0, 8))
        poi_cols = {"Label": 170, "X": 38, "Y": 38}
        self.poi_tree = ttk.Treeview(side, columns=list(poi_cols.keys()), show="headings", height=18, selectmode="browse")
        for col, width in poi_cols.items():
            self.poi_tree.heading(col, text=col)
            self.poi_tree.column(col, width=width, anchor="w")
        self.poi_tree.pack(fill="both", expand=True)
        self.poi_tree.bind("<<TreeviewSelect>>", self.center_on_selected_poi)
        self.poi_tree.bind("<Double-1>", self.center_on_selected_poi)
        ttk.Label(side, text="Add markers for enemy bases, spice spots, wrecks, routes, or reminders. Click any POI to jump to it.", style="Panel.TLabel", wraplength=240).pack(anchor="w", pady=(10, 0))

        self.load_deep_map_image()
        self.refresh_pois()

    def refresh_deep_desert_status(self):
        # Status text was removed from the UI. This method remains so older calls do not fail.
        return

    def check_deep_desert_update(self):
        def worker():
            try:
                meta = deep_desert.check_for_update()
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Deep Desert Update Failed", str(exc)))
                return
            self.after(0, self.load_deep_map_image)
            status = "updated" if meta.get("changed") else "already current"
            self.after(0, lambda: messagebox.showinfo("Deep Desert Map", f"Map cache {status}."))

        threading.Thread(target=worker, daemon=True).start()

    def load_deep_map_image(self):
        if Image is None or ImageTk is None:
            self.deep_canvas.delete("all")
            self.deep_canvas.create_text(20, 20, anchor="nw", fill=TEXT, text="Install Pillow to view the built-in map:\npy -m pip install -r requirements.txt")
            return
        meta = deep_desert.load_meta()
        path = meta.get("image_path") or ""
        if not path or not Path(path).exists():
            self.deep_original_image = None
            self.deep_canvas.delete("all")
            self.deep_canvas.create_text(20, 20, anchor="nw", fill=TEXT, text="No local map image yet. Click Check Map Update.")
            return
        try:
            self.deep_original_image = Image.open(path).convert("RGBA")
            self.fit_deep_map_to_canvas(redraw=False)
            self.render_deep_map()
        except Exception as exc:
            self.deep_original_image = None
            self.deep_canvas.delete("all")
            self.deep_canvas.create_text(20, 20, anchor="nw", fill=TEXT, text=f"Could not load map image:\n{exc}")

    def fit_deep_map_to_canvas(self, redraw=True):
        if self.deep_original_image is None or not hasattr(self, "deep_canvas"):
            if redraw:
                self.render_deep_map()
            return
        canvas_w = max(1, self.deep_canvas.winfo_width())
        canvas_h = max(1, self.deep_canvas.winfo_height())
        image_w, image_h = self.deep_original_image.size
        if canvas_w <= 1 or canvas_h <= 1:
            self.deep_zoom = 1.0
            self.deep_pan_x = 0
            self.deep_pan_y = 0
        else:
            self.deep_zoom = min(canvas_w / image_w, canvas_h / image_h)
            self.deep_zoom = max(0.05, min(8.0, self.deep_zoom))
            self.deep_pan_x = int((canvas_w - image_w * self.deep_zoom) / 2)
            self.deep_pan_y = int((canvas_h - image_h * self.deep_zoom) / 2)
        if redraw:
            self.render_deep_map()

    def reset_deep_map_view(self, redraw=True):
        self.fit_deep_map_to_canvas(redraw=redraw)

    def center_deep_map_on(self, image_x, image_y, zoom=None):
        if self.deep_original_image is None:
            return
        if zoom is not None:
            self.deep_zoom = max(0.05, min(8.0, zoom))
        else:
            self.deep_zoom = max(self.deep_zoom, 1.0)
        canvas_w = max(1, self.deep_canvas.winfo_width())
        canvas_h = max(1, self.deep_canvas.winfo_height())
        self.deep_pan_x = int(canvas_w / 2 - image_x * self.deep_zoom)
        self.deep_pan_y = int(canvas_h / 2 - image_y * self.deep_zoom)
        self.render_deep_map()

    def zoom_deep_map(self, factor: float):
        canvas_w = max(1, self.deep_canvas.winfo_width())
        canvas_h = max(1, self.deep_canvas.winfo_height())
        before_x, before_y = self.canvas_to_image(canvas_w / 2, canvas_h / 2)
        self.deep_zoom = max(0.05, min(8.0, self.deep_zoom * factor))
        self.deep_pan_x = canvas_w / 2 - before_x * self.deep_zoom
        self.deep_pan_y = canvas_h / 2 - before_y * self.deep_zoom
        self.render_deep_map()

    def render_deep_map(self):
        if not hasattr(self, "deep_canvas"):
            return
        self.deep_canvas.delete("all")
        if self.deep_original_image is None:
            self.deep_canvas.create_text(20, 20, anchor="nw", fill=TEXT, text="No local map image yet. Click Check Map Update.")
            return
        w, h = self.deep_original_image.size
        rw = max(1, int(w * self.deep_zoom))
        rh = max(1, int(h * self.deep_zoom))
        img = self.deep_original_image.resize((rw, rh))
        self.deep_rendered_photo = ImageTk.PhotoImage(img)
        self.deep_canvas.create_image(self.deep_pan_x, self.deep_pan_y, anchor="nw", image=self.deep_rendered_photo, tags=("map",))
        self.draw_poi_markers()

    def image_to_canvas(self, x, y):
        return self.deep_pan_x + x * self.deep_zoom, self.deep_pan_y + y * self.deep_zoom

    def canvas_to_image(self, x, y):
        return (x - self.deep_pan_x) / self.deep_zoom, (y - self.deep_pan_y) / self.deep_zoom

    def draw_poi_markers(self):
        if self.deep_original_image is None:
            return
        for row in db.list_pois():
            cx, cy = self.image_to_canvas(row["x"], row["y"])
            r = 7
            self.deep_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=GOLD, fill=PURPLE, width=2, tags=("poi", f"poi{row['id']}"))
            self.deep_canvas.create_text(cx+10, cy-10, anchor="w", fill=GOLD, text=row["label"], font=("Segoe UI", 10, "bold"), tags=("poi", f"poi{row['id']}"))

    def enable_add_poi(self):
        if self.deep_original_image is None:
            messagebox.showwarning("No Map", "Load the Deep Desert map first with Check Map Update.")
            return
        self.deep_add_poi_mode = True
        self.deep_canvas.configure(cursor="crosshair")
        messagebox.showinfo("Add POI", "Click the map where you want to mark the POI.")

    def _poi_near_canvas_point(self, x, y, radius=12):
        if self.deep_original_image is None:
            return None
        for row in db.list_pois():
            cx, cy = self.image_to_canvas(row["x"], row["y"])
            if abs(cx - x) <= radius and abs(cy - y) <= radius:
                return row
        return None

    def deep_canvas_click(self, event):
        if self.deep_add_poi_mode:
            ix, iy = self.canvas_to_image(event.x, event.y)
            if self.deep_original_image is None:
                return
            w, h = self.deep_original_image.size
            if not (0 <= ix <= w and 0 <= iy <= h):
                messagebox.showwarning("Outside Map", "Click inside the map image.")
                return
            label = simpledialog.askstring("New POI", "POI label (example: Enemy Base, Spice Field, Wreck):", parent=self)
            if not label:
                self.deep_add_poi_mode = False
                self.deep_canvas.configure(cursor="")
                return
            note = simpledialog.askstring("POI Note", "Optional note:", parent=self) or ""
            try:
                db.add_poi(ix, iy, label, note)
            except Exception as exc:
                messagebox.showerror("POI Save Failed", str(exc))
            self.deep_add_poi_mode = False
            self.deep_canvas.configure(cursor="")
            self.refresh_pois()
            self.render_deep_map()
            return
        poi = self._poi_near_canvas_point(event.x, event.y)
        if poi is not None:
            if hasattr(self, "poi_tree"):
                self.poi_tree.selection_set(str(poi["id"]))
                self.poi_tree.see(str(poi["id"]))
            self.center_deep_map_on(poi["x"], poi["y"])
            return
        self.deep_drag_start = (event.x, event.y, self.deep_pan_x, self.deep_pan_y)

    def deep_canvas_drag(self, event):
        if self.deep_add_poi_mode or not self.deep_drag_start:
            return
        sx, sy, px, py = self.deep_drag_start
        self.deep_pan_x = px + (event.x - sx)
        self.deep_pan_y = py + (event.y - sy)
        self.render_deep_map()

    def deep_canvas_release(self, event):
        self.deep_drag_start = None

    def deep_canvas_wheel(self, event):
        factor = 1.15 if event.delta > 0 else 0.87
        before_x, before_y = self.canvas_to_image(event.x, event.y)
        self.deep_zoom = max(0.05, min(8.0, self.deep_zoom * factor))
        self.deep_pan_x = event.x - before_x * self.deep_zoom
        self.deep_pan_y = event.y - before_y * self.deep_zoom
        self.render_deep_map()

    def refresh_pois(self):
        if not hasattr(self, "poi_tree"):
            return
        self.poi_tree.delete(*self.poi_tree.get_children())
        for row in db.list_pois():
            self.poi_tree.insert("", "end", iid=str(row["id"]), values=(row["label"], int(row["x"]), int(row["y"])))

    def center_on_selected_poi(self, event=None):
        if not hasattr(self, "poi_tree"):
            return
        sel = self.poi_tree.selection()
        if not sel:
            return
        poi_id = int(sel[0])
        for row in db.list_pois():
            if int(row["id"]) == poi_id:
                self.center_deep_map_on(row["x"], row["y"])
                break

    def delete_selected_poi(self):
        sel = self.poi_tree.selection() if hasattr(self, "poi_tree") else []
        if not sel:
            messagebox.showwarning("No POI Selected", "Select a POI first.")
            return
        if not messagebox.askyesno("Delete POI", "Delete the selected POI marker?"):
            return
        db.delete_poi(int(sel[0]))
        self.refresh_pois()
        self.render_deep_map()

    def refresh_all(self):
        self.refresh_market()
        self.refresh_catalog()
        self.refresh_scanner_catalog()
        self.refresh_history()

    def refresh_market(self):
        self.market_tree.delete(*self.market_tree.get_children())
        for row in db.market_summary(self.market_search.get() if hasattr(self, "market_search") else ""):
            self.market_tree.insert("", "end", iid=f"m{row['item_id']}-{row['grade']}", values=(
                row["name"], row["category"], row["item_type"], "—" if row["grade"] is None else row["grade"],
                money(row["low_price"]), money(row["avg_price"]), money(row["high_price"]),
                row["seen_count"] or 0, row["last_seen"] or "—"
            ), tags=(str(row["item_id"]),))

    def refresh_catalog(self):
        if hasattr(self, "category_combo"):
            current = self.catalog_category.get() or "All Categories"
            categories = ["All Categories"] + db.catalog_categories()
            self.category_combo.configure(values=categories)
            if current in categories:
                self.catalog_category.set(current)
            else:
                self.catalog_category.set("All Categories")

        self.catalog_tree.delete(*self.catalog_tree.get_children())
        search = self.catalog_search.get() if hasattr(self, "catalog_search") else ""
        category = self.catalog_category.get() if hasattr(self, "catalog_category") else ""
        for row in db.list_catalog(search, category):
            self.catalog_tree.insert("", "end", iid=f"c{row['id']}", values=(row["id"], row["name"], row["category"], "Yes" if row["image_path"] else "No"), tags=(row["source_url"] or "",))

    def refresh_scanner_catalog(self):
        self.scan_tree.delete(*self.scan_tree.get_children())
        for row in db.list_catalog(self.scan_search.get() if hasattr(self, "scan_search") else ""):
            self.scan_tree.insert("", "end", iid=str(row["id"]), values=(row["id"], row["name"], row["category"], row["item_type"]))

    def refresh_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        if self.selected_item_id is None:
            return
        for row in db.price_history(self.selected_item_id):
            self.history_tree.insert("", "end", values=(row["name"], "—" if row["grade"] is None else row["grade"], money(row["price"]), row["observed_at"], row["note"]))

    def _scan_item_selected(self, event=None):
        sel = self.scan_tree.selection()
        if not sel:
            return
        item_id = int(sel[0])
        vals = self.scan_tree.item(sel[0], "values")
        self.selected_item_id = item_id
        self.selected_item_name = vals[1]
        self.selected_label.configure(text=f"Selected: {vals[1]}\nCategory: {vals[2]}\nType: {vals[3]}")
        self.refresh_history()

    def _market_selected(self, event=None):
        sel = self.market_tree.selection()
        if not sel:
            return
        tags = self.market_tree.item(sel[0], "tags")
        if tags:
            self.selected_item_id = int(tags[0])
            self.refresh_history()

    def add_item(self):
        try:
            db.add_catalog_item(self.new_name.get(), self.new_category.get(), "", "Item")
        except Exception as e:
            messagebox.showerror("Add Item Failed", str(e))
            return
        self.new_name.set("")
        self.new_category.set("")
        self.refresh_all()


    def _open_catalog_source(self, event=None):
        sel = self.catalog_tree.selection()
        if not sel:
            return
        tags = self.catalog_tree.item(sel[0], "tags")
        if tags and tags[0]:
            webbrowser.open(tags[0])

    def import_dune_catalog(self):
        if not messagebox.askyesno("Import Catalog", "Import items and images from dune.gaming.tools, including the Tier 6 page?\n\nThis may take several minutes because the importer waits between requests to avoid hammering the website."):
            return
        self.import_status.configure(text="Starting import...")

        def progress(msg: str):
            self.after(0, lambda m=msg: self.import_status.configure(text=m[:140]))

        def worker():
            try:
                stats = import_catalog(progress=progress)
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Import Failed", str(exc)))
                self.after(0, lambda: self.import_status.configure(text="Import failed."))
                return
            self.after(0, self.refresh_all)
            self.after(0, lambda: self.import_status.configure(text=f"Import complete: {stats['items']} items, {stats['images']} images, {stats['errors']} errors."))
            self.after(0, lambda: messagebox.showinfo("Import Complete", f"Imported/updated {stats['items']} items.\nDownloaded {stats['images']} images.\nErrors: {stats['errors']}"))

        threading.Thread(target=worker, daemon=True).start()

    def record_price(self):
        if self.selected_item_id is None:
            messagebox.showwarning("No Item", "Select a catalog item first.")
            return
        raw = self.price_var.get().replace(",", "").strip()
        if not raw.isdigit():
            messagebox.showerror("Invalid Price", "Enter a numeric price, like 2000000 or 2,000,000.")
            return
        grade = self.grade_var.get().strip()
        grade_value = int(grade) if grade else None
        try:
            db.record_price(self.selected_item_id, int(raw), grade_value, self.note_var.get())
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
            return
        self.price_var.set("")
        self.note_var.set("")
        self.refresh_market()
        self.refresh_history()
        messagebox.showinfo("Saved", f"Recorded {money(raw)} for {self.selected_item_name}.")


def main():
    app = StankyMarketApp()
    app.mainloop()
