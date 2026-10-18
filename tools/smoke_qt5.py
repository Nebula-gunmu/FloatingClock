"""PySide2（Qt5）冒烟测试：创建主窗口 -> 截图 -> 退出，用于定位卡住的位置。

运行：python tools/smoke_qt5.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / "check"
APPDATA = CHECK_DIR / "appdata_smoke"
(APPDATA / "FloatingClock").mkdir(parents=True, exist_ok=True)
(APPDATA / "FloatingClock" / "settings.json").write_text(
    json.dumps({"appearance_mode": "light", "always_on_top": False}, ensure_ascii=False),
    "utf-8",
)
os.environ["APPDATA"] = str(APPDATA)

sys.path.insert(0, str(ROOT))

import app  # noqa: E402,F401
from app import qtcompat  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

print(f"qt6={qtcompat.QT6}", flush=True)

from core.app_controller import AppController  # noqa: E402


def main() -> int:
    print("creating app", flush=True)
    application = QApplication(sys.argv)
    print("creating controller", flush=True)
    controller = AppController(application)
    print("start", flush=True)
    controller.start()
    print("started", flush=True)

    def shot() -> None:
        print("grabbing", flush=True)
        pixmap = controller.main_window.grab()
        pixmap.save(str(CHECK_DIR / "qt5_smoke.png"))
        print(f"grabbed {pixmap.width()}x{pixmap.height()}", flush=True)
        application.quit()

    QTimer.singleShot(900, shot)
    code = qtcompat.exec_app(application)
    print(f"loop exited {code}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
