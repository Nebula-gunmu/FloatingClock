"""列出系统可用字体，并标出适合时钟（有细字重 / 无衬线 / 数字）的候选。

运行：python tools/list_fonts.py
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from PySide6.QtGui import QFontDatabase, QGuiApplication  # noqa: E402

LIGHT_HINTS = ("light", "thin", "extralight", "ultralight", "semilight", "hairline")
SKIP_PREFIX = ("@", "MS ", "SimSun", "NSimSun", "SimHei", "FangSong", "KaiTi", "DengXian")


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841
    families = QFontDatabase.families()
    print(f"共 {len(families)} 个字体族\n")

    ranked: list[tuple[str, list[str]]] = []
    for family in families:
        if family.startswith("@"):
            continue
        styles = QFontDatabase.styles(family)
        lowered = " ".join(styles).lower()
        if any(hint in lowered for hint in LIGHT_HINTS):
            ranked.append((family, styles))

    print("== 含细字重（Light/Thin）的字体族 ==")
    for family, styles in ranked:
        print(f"{family}: {', '.join(styles)}")

    print("\n== 其它常见无衬线（可能只有 Regular/Bold）==")
    for family in families:
        if family.startswith("@"):
            continue
        if any(family == r[0] for r in ranked):
            continue
        if family.startswith(SKIP_PREFIX):
            continue
        styles = QFontDatabase.styles(family)
        if len(styles) <= 6:
            print(f"{family}: {', '.join(styles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
