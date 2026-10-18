"""无界面自检：格式、设置持久化与夹取、计时器状态机、天气降级、模式切换。

用法：python tools/selftest.py
全部通过时退出码 0，失败时打印 [FAIL] 并退出码 1。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / "check"
CHECK_DIR.mkdir(exist_ok=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = str(CHECK_DIR / "appdata_selftest")

sys.path.insert(0, str(ROOT))

import app  # noqa: E402,F401  - 建立 PySide6 / PySide2 兼容层

try:  # 避免中文在 GBK 控制台上乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from PySide6.QtWidgets import QApplication  # noqa: E402

from datetime import datetime  # noqa: E402

from app import constants as C  # noqa: E402
from app.settings_model import SettingsStore  # noqa: E402
from core.time_modes import (  # noqa: E402
    ModeController,
    TimeMode,
    format_clock,
    format_countdown,
    format_stopwatch,
)
from core.timer_controller import CountdownController, StopwatchController  # noqa: E402
from services import autostart_service  # noqa: E402
from services.weather_service import WeatherService  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[ok] {name}")
    else:
        FAILURES.append(name)
        print(f"[FAIL] {name} {detail}")


def main() -> int:
    app = QApplication(sys.argv)  # noqa: F841

    # ---------- 格式化 ----------
    check("format_clock", format_clock(datetime(2025, 10, 18, 9, 5, 3)) == "09:05:03")
    check("format_countdown 5min", format_countdown(300_000) == "05:00")
    check("format_countdown 0", format_countdown(0) == "00:00")
    check("format_countdown 1h", format_countdown(3_600_000) == "1:00:00")
    check("format_stopwatch", format_stopwatch(61_230) == "01:01.23")

    # ---------- 设置夹取与持久化 ----------
    settings_path = CHECK_DIR / "appdata_selftest" / "FloatingClock" / "settings.json"
    if settings_path.exists():
        settings_path.unlink()
    store = SettingsStore()
    store.set("font_size", 9999)
    check("clamp font max", store.data.font_size == C.CLOCK_FONT_MAX)
    store.set("font_size", 1)
    check("clamp font min", store.data.font_size == C.CLOCK_FONT_MIN)
    store.set("text_opacity", 2.0)
    check("clamp opacity", abs(store.data.text_opacity - 1.0) < 1e-9)
    store.set("appearance_mode", "neon")
    check("invalid enum fallback", store.data.appearance_mode == "system")
    store.set("weather_city", "  北京  ")
    check("city trim", store.data.weather_city == "北京")
    store.set("clock_color", "#0A84FF")
    check("custom clock color", store.data.clock_color == "#0a84ff", store.data.clock_color)
    store.set("clock_color", "not-a-color")
    check("invalid clock color -> auto", store.data.clock_color == C.CLOCK_COLOR_AUTO)
    store.set("clock_font", "Arial")
    check("clock font saved", store.data.clock_font == "Arial", store.data.clock_font)
    store.set("clock_font", "不存在的字体")
    check("invalid font -> default", store.data.clock_font == "")
    store.save()
    reloaded = SettingsStore()
    check("persist reload", reloaded.data.weather_city == "北京")

    # ---------- 倒计时 ----------
    countdown = CountdownController(duration_seconds=1)
    check("countdown initial", countdown.remaining_ms == 1000)
    countdown.start()
    time.sleep(0.35)
    remaining = countdown.poll()
    check("countdown ticking", 300 < remaining < 750, f"remaining={remaining}")
    countdown.pause()
    paused = countdown.remaining_ms
    time.sleep(0.2)
    check("countdown paused", countdown.poll() == paused)
    countdown.reset()
    check("countdown reset", countdown.remaining_ms == 1000)
    finished: list[bool] = []
    countdown.finished.connect(lambda: finished.append(True))
    countdown.set_duration(0)
    countdown.start()
    countdown.poll()
    check("countdown zero no hang", countdown.is_running is False)

    # ---------- 秒表 ----------
    stopwatch = StopwatchController()
    stopwatch.start()
    time.sleep(0.15)
    elapsed = stopwatch.poll()
    check("stopwatch ticking", elapsed >= 120, f"elapsed={elapsed}")
    stopwatch.pause()
    frozen = stopwatch.poll()
    time.sleep(0.1)
    check("stopwatch paused", stopwatch.poll() == frozen)
    stopwatch.reset()
    check("stopwatch reset", stopwatch.poll() == 0)

    # ---------- 模式 ----------
    store.set("display_mode", "clock")
    modes = ModeController(store)
    modes.refresh()
    check("mode clock text", len(modes.text) == 8 and modes.text.count(":") == 2, modes.text)
    modes.set_mode(TimeMode.STOPWATCH)
    check("mode switch", modes.mode is TimeMode.STOPWATCH)
    check("template stopwatch", modes.template == "00:00.00")
    modes.stopwatch_action("start")
    time.sleep(0.12)
    modes._tick(force=True)  # 内部刷新一次，检查文本格式
    check("stopwatch display", "." in modes.text, modes.text)
    modes.set_timers_enabled(False)
    store.set("timers_enabled", False)
    check("timers off -> clock", modes.mode is TimeMode.CLOCK)
    modes.set_mode(TimeMode.COUNTDOWN)
    check("timers off blocks mode", modes.mode is TimeMode.CLOCK)

    # ---------- 天气降级 ----------
    store.set("show_weather", True)
    store.set("weather_city", "")
    weather = WeatherService(store)
    store.set("weather_city", "")
    check("weather empty summary", weather.summary() == "--°", weather.summary())
    check("wmo map non-empty", len(C.WMO_CODES) > 20)
    check("wmo unknown fallback", C.WMO_UNKNOWN[1] == "未知")
    weather._cache = {"temperature": 21.6, "weather_code": 0}  # type: ignore[attr-defined]
    summary = weather.summary()
    check("weather summary", "22°" in summary, summary)
    check("autostart supported flag", isinstance(autostart_service.is_supported(), bool))

    print("")
    if FAILURES:
        print(f"[FAIL] {len(FAILURES)} 项未通过: {FAILURES}")
        return 1
    print("[PASS] 全部自检通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
