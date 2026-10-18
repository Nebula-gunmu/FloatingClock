"""FloatingClock 程序入口：高 DPI、字体、主题初始化，然后交给 AppController。

开发运行：python main.py（会有控制台）或 pythonw main.py（无控制台）
打包运行：FloatingClock.exe（console=False，无控制台）
"""

from __future__ import annotations

import sys

import app  # noqa: F401  - 必须最先导入：建立 PySide6 / PySide2 兼容层

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from app import constants as C
from app import qtcompat
from app import theme as T
from core.app_controller import AppController


def _configure_high_dpi() -> None:
    """Qt6 默认已启用高 DPI，这里固定缩放策略保证多屏一致。"""
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def main() -> int:
    _configure_high_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName(C.APP_NAME)
    app.setApplicationDisplayName(C.APP_DISPLAY_NAME)
    app.setApplicationVersion(C.APP_VERSION)
    app.setOrganizationName(C.ORG_NAME)
    app.setQuitOnLastWindowClosed(True)
    app.setFont(T.ui_font(C.PANEL_FONT_PX))

    icon_file = C.resource_dir() / "icon.png"
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    controller = AppController(app)
    controller.start()
    return qtcompat.exec_app(app)


if __name__ == "__main__":
    raise SystemExit(main())
