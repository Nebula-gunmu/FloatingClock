"""验证置顶优先级：是否带 WS_EX_TOPMOST、是否在 z-order 最前、被抢占后能否夺回。

运行：python tools/verify_topmost.py
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "windows"

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / "check"
APPDATA = CHECK_DIR / "appdata_top"
(APPDATA / "FloatingClock").mkdir(parents=True, exist_ok=True)
(APPDATA / "FloatingClock" / "settings.json").write_text(
    json.dumps(
        {
            "appearance_mode": "light",
            "background_enabled": False,
            "font_size": 110,
            "always_on_top": True,
            "window_x": 360,
            "window_y": 240,
        },
        ensure_ascii=False,
    ),
    "utf-8",
)
os.environ["APPDATA"] = str(APPDATA)

sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from core.app_controller import AppController  # noqa: E402

GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
GW_HWNDNEXT = 2

user32 = ctypes.windll.user32
user32.GetTopWindow.restype = ctypes.c_void_p
user32.GetTopWindow.argtypes = [ctypes.c_void_p]
user32.GetWindow.restype = ctypes.c_void_p
user32.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]


def z_index(hwnd: int) -> int:
    handle = user32.GetTopWindow(None)
    index = 0
    while handle:
        if int(handle) == hwnd:
            return index
        handle = user32.GetWindow(ctypes.c_void_p(handle), GW_HWNDNEXT)
        index += 1
        if index > 4000:
            break
    return -1


def main() -> int:
    app = QApplication(sys.argv)
    controller = AppController(app)
    controller.start()
    state: dict = {}

    def stage1() -> None:
        hwnd = int(controller.main_window.winId())
        state["hwnd"] = hwnd
        exstyle = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
        print(f"main hwnd=0x{hwnd:X} WS_EX_TOPMOST={bool(exstyle & WS_EX_TOPMOST)} z_index={z_index(hwnd)}")

        rival = QWidget(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        rival.setStyleSheet("background: rgba(255, 0, 0, 90);")
        rival.setGeometry(300, 200, 760, 420)
        rival.setWindowTitle("rival")
        rival.show()
        state["rival"] = rival
        QTimer.singleShot(500, stage2)

    def stage2() -> None:
        hwnd = state["hwnd"]
        rival = int(state["rival"].winId())
        print(f"被抢占后: main z={z_index(hwnd)} rival z={z_index(rival)}")
        QTimer.singleShot(3600, stage3)

    def stage3() -> None:
        hwnd = state["hwnd"]
        rival = int(state["rival"].winId())
        main_z = z_index(hwnd)
        rival_z = z_index(rival)
        print(f"重申置顶后: main z={main_z} rival z={rival_z}")
        print("RESULT:", "main 在最前 ✓" if 0 <= main_z < rival_z else "main 仍被压住 ✗")
        state["rival"].close()
        app.quit()

    QTimer.singleShot(1600, stage1)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
