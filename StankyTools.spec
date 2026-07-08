# -*- mode: python ; coding: utf-8 -*-
"""Lean PyInstaller spec for StankyTools.

The old spec used collect_all('PySide6'), which pulls in far more Qt files than
this app needs and can make the portable ZIP hundreds of MB larger. Let
PyInstaller's PySide6 hooks collect the required Qt runtime, then explicitly keep
only the app assets needed by the UI. WebEngine, QML/Quick, and PDF are excluded to keep releases smaller.
"""
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project = Path.cwd()

datas = []
# Keep the installer small: ship UI assets only. Catalog databases/images are imported
# by each user and saved under AppData/StankyTools, not bundled into releases.
if (project / "assets").exists():
    datas.append(("assets", "assets"))

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
]
hiddenimports += collect_submodules("tzdata")

excludes = [
    # Development/test stacks that PyInstaller sometimes discovers indirectly.
    "pytest", "unittest", "doctest", "pdb", "pydoc", "tkinter",
    "IPython", "jupyter", "notebook", "matplotlib", "numpy", "pandas",
    "scipy", "setuptools.tests", "pip", "wheel",
    # Unused Qt modules for this app.
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
    "PySide6.QtDesigner", "PySide6.QtTest", "PySide6.Qt3DCore",
    "PySide6.QtBluetooth", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtLocation", "PySide6.QtNfc",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtPositioning", "PySide6.QtQuick3D",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSql",
    "PySide6.QtSvg", "PySide6.QtTextToSpeech", "PySide6.QtUiTools",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineCore",
    "PySide6.QtPdfWidgets",
]

a = Analysis(
    ["main.py"],
    pathex=[str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
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
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=["Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"],
    name="StankyTools",
)
