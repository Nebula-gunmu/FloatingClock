"""离屏渲染预览：把主窗口与设置面板渲染成 PNG，便于快速核对视觉。

用法：
    python tools/preview.py            # 离屏渲染（无桌面也可用）
    python tools/preview.py --desktop  # 使用真实窗口平台渲染（需要桌面会话）

输出：check/*.png
预览使用独立 APPDATA 目录，不会污染真实设置。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / "check"
CHECK_DIR.mkdir(exist_ok=True)

# 每次预览都从干净配置开始，避免上一轮的字体/颜色残留影响截图
APPDATA_DIR = CHECK_DIR / "appdata"
if APPDATA_DIR.exists():
    import shutil

    shutil.rmtree(APPDATA_DIR, ignore_errors=True)

if "--desktop" not in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = str(CHECK_DIR / "appdata")

sys.path.insert(0, str(ROOT))

import app  # noqa: E402,F401  - 建立 PySide6 / PySide2 兼容层
from app import qtcompat  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from PySide6.QtCore import QPoint, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QRegion  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from core.app_controller import AppController  # noqa: E402
from ui.widgets import FontPickerPanel, IosColorPicker  # noqa: E402

BACKDROP_LIGHT = ("#E9EFF8", "#C3D3EA")
BACKDROP_DARK = ("#28304D", "#12151F")


def render_on_backdrop(widget: QWidget, dark: bool) -> QImage:
    """把窗口渲染到模拟壁纸上，用于查看透明背景下的真实观感。"""
    image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    gradient = QLinearGradient(0, 0, image.width() * 0.6, image.height())
    top, bottom = BACKDROP_DARK if dark else BACKDROP_LIGHT
    gradient.setColorAt(0.0, QColor(top))
    gradient.setColorAt(1.0, QColor(bottom))
    painter.fillRect(image.rect(), gradient)
    widget.render(painter, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
    painter.end()
    return image


def main() -> int:
    app = QApplication(sys.argv)
    controller = AppController(app)
    controller.start()

    # (名称, 需要设置的键值, 文件名)
    steps: list[tuple[str, dict, str]] = [
        ("light", {"appearance_mode": "light", "calendar_enabled": False,
                   "background_enabled": False, "show_weather": True,
                   "clock_color": "", "clock_font": ""}, "main_window.png"),
        ("light_calendar", {"appearance_mode": "light", "calendar_enabled": True,
                            "background_enabled": False}, "main_window_calendar.png"),
        ("dark_calendar", {"appearance_mode": "dark", "calendar_enabled": True,
                           "background_enabled": True}, "main_window_dark.png"),
        ("panel", {"appearance_mode": "light", "calendar_enabled": False,
                   "background_enabled": False}, "settings_panel.png"),
        ("accent_color", {"appearance_mode": "light", "background_enabled": True,
                          "clock_color": "#0A84FF", "calendar_enabled": False},
         "main_window_accent.png"),
        ("font_bahnschrift", {"appearance_mode": "light", "background_enabled": False,
                              "clock_color": "", "clock_font": "Bahnschrift",
                              "calendar_enabled": False}, "main_window_font.png"),
        ("picker", {}, "color_picker.png"),
        ("fontpicker", {}, "font_picker.png"),
    ]

    index = 0

    def apply_settings(values: dict) -> None:
        for key, value in values.items():
            controller.settings.set(key, value)

    def run_next() -> None:
        nonlocal index
        if index >= len(steps):
            app.quit()
            return
        name, values, filename = steps[index]
        index += 1
        apply_settings(values)
        QTimer.singleShot(320, lambda: capture(name, values, filename))

    def capture(name: str, values: dict, filename: str) -> None:
        if filename == "color_picker.png":
            picker = IosColorPicker(controller.theme, QColor("#0A84FF"))
            QTimer.singleShot(120, lambda p=picker: finish_picker(p, filename))
            return
        if filename == "font_picker.png":
            panel = FontPickerPanel(controller.theme, "Bahnschrift")
            QTimer.singleShot(120, lambda p=panel: finish_picker(p, filename))
            return
        if filename == "settings_panel.png":
            controller.panel.show_near(controller.main_window.frameGeometry())
            QTimer.singleShot(
                320, lambda: finish(name, controller.panel, filename)
            )
            return
        finish(name, controller.main_window, filename)

    def finish_picker(picker, filename: str) -> None:
        pixmap = picker.grab()
        path = CHECK_DIR / filename
        pixmap.save(str(path))
        print(f"[ok] {filename} {pixmap.width()}x{pixmap.height()}")
        picker.deleteLater()
        QTimer.singleShot(160, run_next)

    def finish(name: str, widget, filename: str) -> None:
        path = CHECK_DIR / filename
        pixmap = widget.grab()
        ok = pixmap.save(str(path))
        dark = controller.theme.is_dark
        backdrop = render_on_backdrop(widget, dark)
        backdrop_path = CHECK_DIR / f"backdrop_{filename}"
        backdrop.save(str(backdrop_path))
        print(
            f"[{'ok' if ok else 'fail'}] {filename} "
            f"{pixmap.width()}x{pixmap.height()} state={name} theme={controller.theme.effective}"
        )
        if filename == "settings_panel.png":
            controller.panel.hide()
        QTimer.singleShot(220, run_next)

    QTimer.singleShot(120, run_next)
    code = qtcompat.exec_app(app)
    print("[done] preview finished")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
