"""倒计时与秒表的纯逻辑控制器（基于 monotonic 时钟，与界面完全解耦）。"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal


class CountdownController(QObject):
    """倒计时状态机：start / pause / reset，结束时发出 finished 一次。"""

    finished = Signal()

    def __init__(self, duration_seconds: int = 300, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._duration_ms = max(0, int(duration_seconds)) * 1000
        self._remaining_ms = self._duration_ms
        self._deadline = 0.0
        self._running = False
        self._finish_emitted = True

    # ------------------------------------------------------------ 查询
    @property
    def duration_seconds(self) -> int:
        return self._duration_ms // 1000

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def remaining_ms(self) -> int:
        if self._running:
            return max(0, int((self._deadline - time.monotonic()) * 1000))
        return max(0, self._remaining_ms)

    # ------------------------------------------------------------ 控制
    def set_duration(self, seconds: int) -> None:
        self._duration_ms = max(0, int(seconds)) * 1000
        self.reset()

    def start(self) -> None:
        if self._running or self._remaining_ms <= 0:
            return
        self._deadline = time.monotonic() + self._remaining_ms / 1000.0
        self._running = True
        self._finish_emitted = False

    def pause(self) -> None:
        if not self._running:
            return
        self._remaining_ms = self.remaining_ms
        self._running = False

    def reset(self) -> None:
        self._running = False
        self._remaining_ms = self._duration_ms
        self._finish_emitted = True

    def toggle(self) -> None:
        self.pause() if self._running else self.start()

    def poll(self) -> int:
        """由显示层按帧调用：返回剩余毫秒，并在归零瞬间触发 finished。"""
        remaining = self.remaining_ms
        if self._running and remaining <= 0:
            self._running = False
            self._remaining_ms = 0
            if not self._finish_emitted:
                self._finish_emitted = True
                self.finished.emit()
        return remaining


class StopwatchController(QObject):
    """秒表状态机：start / pause / reset，支持累计计时。"""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._accumulated_ms = 0.0
        self._started_at = 0.0
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def elapsed_ms(self) -> int:
        if self._running:
            return int(self._accumulated_ms + (time.monotonic() - self._started_at) * 1000)
        return int(self._accumulated_ms)

    def start(self) -> None:
        if self._running:
            return
        self._started_at = time.monotonic()
        self._running = True

    def pause(self) -> None:
        if not self._running:
            return
        self._accumulated_ms += (time.monotonic() - self._started_at) * 1000
        self._running = False

    def reset(self) -> None:
        self._running = False
        self._accumulated_ms = 0.0

    def toggle(self) -> None:
        self.pause() if self._running else self.start()

    def poll(self) -> int:
        return self.elapsed_ms
