"""实测背景（磨砂 / 降级纯色）在真实桌面上的渲染结果。

运行：python tools/verify_acrylic.py
输出：
    check/acrylic_real.png   截取窗口区域（含四周 40px 桌面）
    check/acrylic_full.png   整屏缩略图，便于判断背后是什么内容
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "windows"

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / "check"
APPDATA = CHECK_DIR / "appdata_acrylic"
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
            "window_x": 900,
            "window_y": 520,
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

from PySide6.QtCore import QRect, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.app_controller import AppController  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    controller = AppController(app)
    controller.start()

    def capture() -> None:
        window = controller.main_window
        mode = getattr(window, "_blur_mode", "?")
        print(f"blur_mode={mode} geometry={window.geometry().getRect()} build={sys.getwindowsversion().build}")

        screen = QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        shot = screen.grabWindow(0)

        margin = 40
        g = window.frameGeometry()
        rect = QRect(
            int((g.x() - margin) * dpr),
            int((g.y() - margin) * dpr),
            int((g.width() + margin * 2) * dpr),
            int((g.height() + margin * 2) * dpr),
        )
        crop = shot.copy(rect)
        crop.save(str(CHECK_DIR / "acrylic_real.png"))
        print(f"[ok] acrylic_real.png {crop.width()}x{crop.height()} dpr={dpr}")

        full = shot.scaled(
            int(shot.width() * 0.55),
            int(shot.height() * 0.55),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        full.save(str(CHECK_DIR / "acrylic_full.png"))
        print(f"[ok] acrylic_full.png {full.width()}x{full.height()}")
        app.quit()

    QTimer.singleShot(2800, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
