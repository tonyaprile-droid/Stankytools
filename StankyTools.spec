# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# GitHub Actions and local builds both run from the repository root.
project_root = Path.cwd().resolve()

DROP_DIR_NAMES = {
    ".git", ".github", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "__pycache__", "tests", "test", "docs", "screenshots", "release_artifacts",
    "sample_data", "samples", "tmp", "temp", "logs", "Dune-Awakening-API",
}
DROP_SUFFIXES = {
    ".pyc", ".pyo", ".log", ".tmp", ".bak", ".psd", ".xcf", ".md",
}
DROP_FILENAMES = {
    "desktop.ini", "thumbs.db",
}


def _has_modern_sibling(path: Path) -> bool:
    if path.suffix.lower() != ".png":
        return False
    return path.with_suffix(".webp").exists() or path.with_suffix(".svg").exists()


def collect_filtered(relative_source, destination):
    """Include release data while skipping dev files and duplicate PNG assets."""
    source = project_root / relative_source
    if not source.exists():
        print(f"Skipping missing release data: {source}")
        return []
    if source.is_file():
        return [(str(source), destination)]

    print(f"Including filtered release data: {source}")
    rows = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        parts = {part.lower() for part in rel.parts}
        if parts & DROP_DIR_NAMES:
            continue
        if path.name.lower() in DROP_FILENAMES:
            continue
        if path.suffix.lower() in DROP_SUFFIXES:
            continue
        if _has_modern_sibling(path):
            continue
        rows.append((str(path), str(Path(destination) / rel.parent)))
    return rows


# Only package runtime assets. User-imported catalog images are deliberately excluded.
datas = []
datas += collect_filtered("stanky_market/assets/themes", "stanky_market/assets/themes")
datas += collect_filtered("stanky_market/assets/icons", "stanky_market/assets/icons")
datas += collect_filtered("assets/sidebar", "assets/sidebar")
datas += collect_filtered("assets/settings", "assets/settings")
datas += collect_filtered("assets/catalog/catalog.sqlite3", "assets/catalog")
datas += collect_filtered("data/deep_desert_map.png", "data")
datas += collect_filtered("data/hagga_basin_map.png", "data")

# Let PyInstaller detect normal imports. Avoid bundling large optional Qt modules and
# development/scientific stacks that StankyTools does not require at runtime.
hiddenimports = [
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
]

excludes = [
    "tkinter", "unittest", "test", "distutils", "setuptools", "pip",
    "IPython", "jupyter", "notebook", "pytest",
    "matplotlib", "scipy", "numpy", "pandas", "torch", "sklearn", "cv2", "PIL", "pytesseract",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtDesigner",
    "PySide6.QtGraphs", "PySide6.QtGraphsWidgets", "PySide6.QtHelp",
    "PySide6.QtHttpServer", "PySide6.QtLocation", "PySide6.QtNetworkAuth",
    "PySide6.QtNfc", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtStateMachine", "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
]


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StankyTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="StankyTools",
)
