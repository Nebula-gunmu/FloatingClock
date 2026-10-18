"""验证拖动/移动窗口时，磨砂背景是否跟着位置滑动。

运行：python tools/verify_drag.py
输出：check/drag_0.png ~ drag_2.png（三个不同位置下窗口的实拍）
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "windows"

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / "check"
APPDATA = CHECK_DIR / "appdata_drag"
(APPDATA / "FloatingClock").mkdir(parents=True, exist_ok=True)
(APPDATA / "FloatingClock" / "settings.json").write_text(
    json.dumps(
        {
            "appearance_mode": "light",
            "background_enabled": True,
            "background_opacity": 0.6,
            "font_size": 110,
            "show_date": True,
            "show_weather": True,
            "always_on_top": True,
            "window_x": 200,
            "window_y": 150,
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

from PySide6.QtCore import QRect, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.app_controller import AppController  # noqa: E402

POSITIONS = [(180, 140), (620, 400), (1000, 600)]


def main() -> int:
    app = QApplication(sys.argv)
    controller = AppController(app)
    controller.start()
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio()

    def capture(index: int) -> None:
        window = controller.main_window
        geo = window.frameGeometry()
        shot = screen.grabWindow(0)
        rect = QRect(
            int(geo.x() * dpr),
            int(geo.y() * dpr),
            int(geo.width() * dpr),
            int(geo.height() * dpr),
        )
        shot.copy(rect).save(str(CHECK_DIR / f"drag_{index}.png"))
        print(f"[ok] drag_{index}.png pos={geo.getRect()}")

    def step(index: int = 0) -> None:
        if index >= len(POSITIONS):
            app.quit()
            return
        controller.main_window.move(*POSITIONS[index])
        QTimer.singleShot(420, lambda i=index: (capture(i), QTimer.singleShot(120, lambda: step(i + 1))))

    QTimer.singleShot(1400, lambda: step(0))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
