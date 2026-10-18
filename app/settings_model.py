"""集中的设置模型：dataclass 数据结构 + JSON 持久化 + 变更通知。

所有设置项唯一来源，UI 只读写 SettingsStore，不自行保存状态。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from . import constants as C


@dataclass
class Settings:
    """全部可持久化设置项。字段默认值即为首次运行状态。"""

    # 外观
    appearance_mode: str = "system"          # system | light | dark
    text_opacity: float = 1.0                # 0.0 - 1.0
    font_size: int = C.CLOCK_FONT_DEFAULT    # px
    clock_color: str = C.CLOCK_COLOR_AUTO    # 空 = 跟随主题，否则 #RRGGBB
    clock_font: str = ""                     # 空 = 默认字体链
    background_enabled: bool = False
    background_opacity: float = 0.55
    wheel_zoom: bool = True

    # 显示
    show_date: bool = True
    show_weather: bool = True
    display_mode: str = "clock"              # clock | countdown | stopwatch

    # 置顶
    always_on_top: bool = True

    # 功能
    timers_enabled: bool = True
    countdown_minutes: int = 5
    countdown_seconds: int = 0

    # 天气
    weather_city: str = ""

    # 日历
    calendar_enabled: bool = False

    # 系统
    autostart: bool = False

    # 窗口位置（-1 表示尚未保存）
    window_x: int = -1
    window_y: int = -1


_ENUMS = {
    "appearance_mode": C.APPEARANCE_MODES,
    "display_mode": ("clock", "countdown", "stopwatch"),
}

_NUMERIC_RANGE = {
    "font_size": (C.CLOCK_FONT_MIN, C.CLOCK_FONT_MAX),
    "text_opacity": (0.0, 1.0),
    "background_opacity": (0.0, 1.0),
    "countdown_minutes": (0, 999),
    "countdown_seconds": (0, 59),
    "window_x": (-10000, 10000),
    "window_y": (-10000, 10000),
}

_BOOL_KEYS = {
    "background_enabled",
    "wheel_zoom",
    "show_date",
    "show_weather",
    "always_on_top",
    "timers_enabled",
    "calendar_enabled",
    "autostart",
}


class SettingsStore(QObject):
    """设置读写门面：changed(key, value) 在任意设置真正变化后发出。"""

    changed = Signal(str, object)

    def __init__(self, path: Path | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = Path(path) if path else C.settings_file()
        self.data = Settings()
        self.first_run = not self._path.exists()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self.save)
        self.load()

    # ------------------------------------------------------------ 读写
    def load(self) -> None:
        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        known = {f.name for f in fields(Settings)}
        for key, value in raw.items():
            if key in known:
                setattr(self.data, key, self._coerce(key, value))

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(asdict(self.data), ensure_ascii=False, indent=2), "utf-8")
            os.replace(tmp, self._path)
        except OSError:
            # 配置写入失败不得影响程序运行
            pass

    def get(self, key: str):
        return getattr(self.data, key)

    def set(self, key: str, value) -> bool:
        """写入单个设置；返回是否发生了实际变化。"""
        if not hasattr(self.data, key):
            return False
        value = self._coerce(key, value)
        if getattr(self.data, key) == value:
            return False
        setattr(self.data, key, value)
        self._schedule_save()
        self.changed.emit(key, value)
        return True

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            self.set(key, value)

    # ------------------------------------------------------------ 内部
    def _schedule_save(self) -> None:
        self._save_timer.start()

    @staticmethod
    def _coerce(key: str, value):
        try:
            if key in _BOOL_KEYS:
                return bool(value)
            if key in _ENUMS:
                return value if value in _ENUMS[key] else _ENUMS[key][0]
            if key in _NUMERIC_RANGE:
                low, high = _NUMERIC_RANGE[key]
                if key.endswith("_opacity"):
                    num = float(value)
                else:
                    num = int(round(float(value)))
                return max(low, min(high, num))
            if key == "weather_city":
                return str(value).strip()[:40]
            if key == "clock_color":
                text = str(value).strip()
                if not text:
                    return C.CLOCK_COLOR_AUTO
                from PySide6.QtGui import QColor

                color = QColor(text)
                return color.name() if color.isValid() else C.CLOCK_COLOR_AUTO
            if key == "clock_font":
                text = str(value).strip()[:60]
                allowed = {family for _label, family in C.CLOCK_FONT_OPTIONS}
                return text if text in allowed else ""
        except (TypeError, ValueError):
            return getattr(Settings, key, value)
        return value
