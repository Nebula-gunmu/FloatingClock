"""生成应用图标 resources/icon.png 与 resources/icon.ico。

纯 PySide6 绘制（不依赖 Pillow），由 build.bat / build.ps1 在打包前调用。
也可以单独运行：python tools/make_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402,F401  - 建立 PySide6 / PySide2 兼容层

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap  # noqa: E402

RESOURCES = ROOT / "resources"
SIZES = (256, 128, 64, 48, 32, 16)


def draw_icon(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    scale = size / 256.0
    radius = 56.0 * scale
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#111114"))
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    center = QPointF(size / 2.0, size / 2.0)
    dial = 86.0 * scale
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#FFFFFF"), max(1.2, 5.0 * scale), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawEllipse(center, dial, dial)

    painter.setPen(QPen(QColor("#0A84FF"), max(1.0, 5.0 * scale), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(center, QPointF(center.x(), center.y() - dial * 0.62))
    painter.setPen(QPen(QColor("#FFFFFF"), max(1.0, 5.0 * scale), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(center, QPointF(center.x() + dial * 0.46, center.y() + dial * 0.16))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0A84FF"))
    painter.drawEllipse(center, 7.0 * scale, 7.0 * scale)

    painter.end()
    return pixmap


def main() -> int:
    RESOURCES.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication(sys.argv)  # noqa: F841 - Qt 绘图需要 GUI 应用实例

    pixmap = draw_icon(256)
    png_path = RESOURCES / "icon.png"
    if not pixmap.save(str(png_path), "PNG"):
        print(f"[warn] 写入失败: {png_path}")
        return 1
    print(f"[ok] {png_path}")

    ico_path = RESOURCES / "icon.ico"
    if pixmap.save(str(ico_path), "ICO"):
        print(f"[ok] {ico_path}")
    else:
        print("[warn] 当前 Qt 不支持写 ICO，已保留 PNG（打包配置会自动回退使用 PNG）")

    # 额外保存一份多尺寸 PNG 便于文档/快捷方式使用
    for extra in SIZES:
        draw_icon(extra).save(str(RESOURCES / f"icon_{extra}.png"), "PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
