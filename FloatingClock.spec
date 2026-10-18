# -*- mode: python ; coding: utf-8 -*-
"""FloatingClock 的 PyInstaller 打包配置（自动适配两套 Qt 绑定）。

同一份 spec 可以在两种环境里打包出对应版本：
- Python 3.11+ / PySide6（Qt 6）→ Windows 10 / 11 版
- Python 3.8 / PySide2（Qt 5.15）→ Windows 7 x64 版

配合不同的输出目录使用：
    pyinstaller --clean --noconfirm --distpath dist FloatingClock.spec
    pyinstaller --clean --noconfirm --distpath dist-win7 --workpath build-win7 FloatingClock.spec

要点：目录式打包（onedir，禁止 --onefile）、console=False、收集 Qt 插件与 resources。
"""

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH)  # noqa: F821 - SPECPATH 由 PyInstaller 注入

try:  # 优先 PySide6（Qt6）
    import PySide6  # noqa: F401

    QT_PREFIX = "PySide6"
except ImportError:
    QT_PREFIX = "PySide2"

RESOURCES_DIR = PROJECT_ROOT / "resources"
if not RESOURCES_DIR.exists():
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

# 图标优先级：ico > png > 无（缺图标也能正常打包）
ICON_CANDIDATES = [RESOURCES_DIR / "icon.ico", RESOURCES_DIR / "icon.png"]
ICON = next((str(path) for path in ICON_CANDIDATES if path.exists()), None)

# 本程序用不到的 Qt 大模块，排除后体积更小、启动更快（不存在的模块名无副作用）
_EXCLUDED_QT_MODULES = (
    "QtWebEngineWidgets",
    "QtWebEngineCore",
    "QtWebEngine",
    "QtQml",
    "QtQuick",
    "QtQuickWidgets",
    "QtSql",
    "QtTest",
    "QtDesigner",
    "QtMultimedia",
    "QtMultimediaWidgets",
    "QtCharts",
    "QtDataVisualization",
    "Qt3DCore",
    "QtPdf",
    "QtPdfWidgets",
)

EXCLUDES = ["tkinter", "unittest"] + [f"{QT_PREFIX}.{name}" for name in _EXCLUDED_QT_MODULES]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[(str(RESOURCES_DIR), "resources")],
    hiddenimports=[
        f"{QT_PREFIX}.QtNetwork",
        f"{QT_PREFIX}.QtGui",
        f"{QT_PREFIX}.QtCore",
        f"{QT_PREFIX}.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FloatingClock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FloatingClock",
)
