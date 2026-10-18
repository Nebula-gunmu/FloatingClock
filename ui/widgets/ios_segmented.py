"""iOS 风格分段控件：胶囊底槽 + 白色滑动块，切换 160ms 缓动。"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from app import constants as C
from app import theme as T
from app.qtcompat import event_pos


class IosSegmented(QWidget):
    current_changed = Signal(int)

    def __init__(self, options: list[str], parent=None, theme: T.ThemeManager | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._options = list(options) or [""]
        self._index = 0
        self._pos = 0.0
        self.setFixedHeight(C.SEGMENT_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(C.ANIM_NORMAL)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if theme is not None:
            theme.changed.connect(self.update)

    # ------------------------------------------------------------ 数据
    def options(self) -> list[str]:
        return list(self._options)

    def set_options(self, options: list[str], current: int | None = None) -> None:
        options = [str(option) for option in options] or [""]
        changed = options != self._options
        self._options = options
        target = self._index if current is None else int(current)
        self._index = max(0, min(len(options) - 1, target))
        if changed:
            self._pos = float(self._index)
            self.updateGeometry()
            self.update()

    def current_index(self) -> int:
        return self._index

    def set_current(self, index: int, emit: bool = False) -> None:
        index = max(0, min(len(self._options) - 1, int(index)))
        if index == self._index:
            return
        self._index = index
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(float(index))
        self._anim.start()
        if emit:
            self.current_changed.emit(index)

    # ------------------------------------------------------------ 动画属性
    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, value: float) -> None:
        self._pos = float(value)
        self.update()

    pos = Property(float, _get_pos, _set_pos)

    # ------------------------------------------------------------ 布局
    def sizeHint(self) -> QSize:
        font = T.ui_font(C.SEGMENT_FONT_PX, QFont.Weight.DemiBold)
        from PySide6.QtGui import QFontMetricsF

        metrics = QFontMetricsF(font)
        text_width = max(metrics.horizontalAdvance(option) for option in self._options)
        segment = max(52.0, text_width + 26)
        return QSize(int(segment * len(self._options) + 2 * C.SEGMENT_PADDING), C.SEGMENT_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ------------------------------------------------------------ 交互
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            count = len(self._options)
            usable = max(1.0, self.width() - 2 * C.SEGMENT_PADDING)
            segment = usable / count
            index = int((event_pos(event).x() - C.SEGMENT_PADDING) // segment)
            index = max(0, min(count - 1, index))
            self.set_current(index, emit=True)
            event.accept()
            return
        super().mousePressEvent(event)

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        tokens = self._theme.tokens() if self._theme else C.TOKENS["light"]
        width = float(self.width())
        height = float(self.height())
        radius = height / 2.0
        painter.setBrush(QColor(tokens["segment_track"]))
        painter.drawRoundedRect(QRectF(0, 0, width, height), radius, radius)

        pad = float(C.SEGMENT_PADDING)
        count = len(self._options)
        segment = max(1.0, (width - 2 * pad) / count)
        thumb = QRectF(pad + self._pos * segment, pad, segment, height - 2 * pad)
        painter.setBrush(QColor(tokens["segment_thumb"]))
        painter.drawRoundedRect(thumb, (height - 2 * pad) / 2.0, (height - 2 * pad) / 2.0)

        active_text = QColor(tokens["text"])
        inactive_text = QColor(tokens["segment_text"])
        for index, option in enumerate(self._options):
            cell = QRectF(pad + index * segment, 0, segment, height)
            weight = QFont.Weight.DemiBold if index == self._index else QFont.Weight.Normal
            painter.setFont(T.ui_font(C.SEGMENT_FONT_PX, weight))
            painter.setPen(active_text if index == self._index else inactive_text)
            painter.drawText(cell, int(Qt.AlignmentFlag.AlignCenter), option)
