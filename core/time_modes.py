"""时钟 / 倒计时 / 秒表：显示模式枚举、格式化函数与统一控制器。

新增显示模式只需扩展 TimeMode 与 MODE_PROVIDERS（返回文本与模板），
主窗口与设置面板都不需要改动内部逻辑。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, QTimer, Signal

from .timer_controller import CountdownController, StopwatchController

TICK_INTERVAL_MS = 80


class TimeMode(str, Enum):
    CLOCK = "clock"
    COUNTDOWN = "countdown"
    STOPWATCH = "stopwatch"

    @property
    def label(self) -> str:
        return {"clock": "时钟", "countdown": "倒计时", "stopwatch": "秒表"}[self.value]


# 用于计算窗口宽度的等宽模板，保证数字宽度不抖动
MODE_TEMPLATES: dict[TimeMode, str] = {
    TimeMode.CLOCK: "00:00:00",
    TimeMode.COUNTDOWN: "00:00:00",
    TimeMode.STOPWATCH: "00:00.00",
}


# ---------------------------------------------------------------- 格式化
def format_clock(moment: datetime) -> str:
    return moment.strftime("%H:%M:%S")


def format_countdown(remaining_ms: int) -> str:
    total_seconds = max(0, int(round(remaining_ms / 1000)))
    hours, rest = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_stopwatch(elapsed_ms: int) -> str:
    total_cs = max(0, int(elapsed_ms // 10))
    hours, rest = divmod(total_cs, 360000)
    minutes, rest = divmod(rest, 6000)
    seconds, centis = divmod(rest, 100)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"
    return f"{minutes:02d}:{seconds:02d}.{centis:02d}"


class DisplayProvider:
    """显示模式扩展接口：实现 text()/template()/action() 即可接入新模式。"""

    template: str = "00:00:00"

    def text(self) -> str:  # pragma: no cover - 扩展点
        raise NotImplementedError

    def action(self, name: str) -> None:  # pragma: no cover - 扩展点
        raise NotImplementedError


class ModeController(QObject):
    """统一驱动主窗口显示文本：每 80ms 计算一次，文本变化才广播。"""

    display_changed = Signal(str)
    template_changed = Signal(str)
    mode_changed = Signal(str)

    def __init__(self, settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.countdown = CountdownController(self._countdown_seconds(), self)
        self.stopwatch = StopwatchController(self)
        self._mode = self._initial_mode()
        self._text = ""
        self.countdown.finished.connect(self._on_countdown_finished)

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------ 查询
    @property
    def mode(self) -> TimeMode:
        return self._mode

    @property
    def template(self) -> str:
        return MODE_TEMPLATES[self._mode]

    @property
    def text(self) -> str:
        return self._text

    # ------------------------------------------------------------ 模式
    def set_mode(self, mode: str | TimeMode) -> None:
        try:
            target = TimeMode(mode)
        except ValueError:
            target = TimeMode.CLOCK
        if target is not TimeMode.CLOCK and not self._settings.data.timers_enabled:
            target = TimeMode.CLOCK
        if target is self._mode:
            self._tick()
            return
        self._mode = target
        self.mode_changed.emit(target.value)
        self.template_changed.emit(self.template)
        self._tick(force=True)

    def set_timers_enabled(self, enabled: bool) -> None:
        if not enabled:
            self.countdown.reset()
            self.stopwatch.reset()
            if self._mode is not TimeMode.CLOCK:
                self.set_mode(TimeMode.CLOCK)
        self._tick(force=True)

    def set_countdown_duration(self, minutes: int, seconds: int) -> None:
        self.countdown.set_duration(max(0, int(minutes)) * 60 + max(0, int(seconds)))
        self._tick(force=True)

    # ------------------------------------------------------------ 控制
    def countdown_action(self, action: str) -> None:
        if not self._settings.data.timers_enabled:
            return
        if self._mode is not TimeMode.COUNTDOWN:
            self.set_mode(TimeMode.COUNTDOWN)
        {"start": self.countdown.start, "pause": self.countdown.pause,
         "reset": self.countdown.reset, "toggle": self.countdown.toggle}.get(action, lambda: None)()
        self._tick(force=True)

    def stopwatch_action(self, action: str) -> None:
        if not self._settings.data.timers_enabled:
            return
        if self._mode is not TimeMode.STOPWATCH:
            self.set_mode(TimeMode.STOPWATCH)
        {"start": self.stopwatch.start, "pause": self.stopwatch.pause,
         "reset": self.stopwatch.reset, "toggle": self.stopwatch.toggle}.get(action, lambda: None)()
        self._tick(force=True)

    def refresh(self) -> None:
        """外部初始化完成后调用，立即广播一次当前显示文本。"""
        self.template_changed.emit(self.template)
        self._tick(force=True)

    def stop(self) -> None:
        self._timer.stop()

    # ------------------------------------------------------------ 内部
    def _initial_mode(self) -> TimeMode:
        try:
            mode = TimeMode(self._settings.data.display_mode)
        except ValueError:
            mode = TimeMode.CLOCK
        if mode is not TimeMode.CLOCK and not self._settings.data.timers_enabled:
            return TimeMode.CLOCK
        return mode

    def _countdown_seconds(self) -> int:
        data = self._settings.data
        return max(0, int(data.countdown_minutes)) * 60 + max(0, int(data.countdown_seconds))

    def _compose(self) -> str:
        if self._mode is TimeMode.CLOCK:
            return format_clock(datetime.now())
        if self._mode is TimeMode.COUNTDOWN:
            return format_countdown(self.countdown.poll())
        return format_stopwatch(self.stopwatch.poll())

    def _tick(self, force: bool = False) -> None:
        text = self._compose()
        if force or text != self._text:
            self._text = text
            self.display_changed.emit(text)

    def _on_countdown_finished(self) -> None:
        self._text = format_countdown(0)
        self.display_changed.emit(self._text)
