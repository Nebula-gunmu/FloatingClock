"""主时钟文字控件：iOS 锁屏式超细大数字，逐字符等宽格布局避免抖动。

同时负责"时钟区域"的鼠标语义：拖动窗口、滚轮缩放、悬浮检测、点击设置。
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import QWidget

from app import constants as C
from app import theme as T
from app.qtcompat import event_global_pos


class ClockFace(QWidget):
    hover_changed = Signal(bool)
    drag_started = Signal(QPoint)
    drag_moved = Signal(QPoint)
    drag_finished = Signal()
    zoom_step = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._text = "00:00:00"
        self._template = "00:00:00"
        self._font_px = C.CLOCK_FONT_DEFAULT
        self._font_family: str | None = None
        self._font: QFont = T.clock_font(self._font_px, self._font_family)
        self._opacity = 1.0
        self._color = QColor("#FFFFFF")
        self._drag_origin: QPoint | None = None

        self._digit_adv = 0.0
        self._colon_adv = 0.0
        self._dot_adv = 0.0
        self._metrics = QFontMetricsF(self._font)
        self._recalc_metrics()

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    # ------------------------------------------------------------ 数据
    @property
    def text(self) -> str:
        return self._text

    def set_text(self, text: str) -> None:
        text = text or ""
        if text == self._text:
            return
        self._text = text
        self.updateGeometry()
        self.update()

    def set_template(self, template: str) -> None:
        if template == self._template or not template:
            return
        self._template = template
        self.updateGeometry()
        self.update()

    def set_font_px(self, pixel_size: int) -> None:
        pixel_size = int(pixel_size)
        if pixel_size == self._font_px:
            return
        self._font_px = pixel_size
        self._font = T.clock_font(pixel_size, self._font_family)
        self._recalc_metrics()
        self.updateGeometry()
        self.update()

    def set_font_family(self, family: str | None) -> None:
        family = family or None
        if family == self._font_family:
            return
        self._font_family = family
        self._font = T.clock_font(self._font_px, family)
        self._recalc_metrics()
        self.updateGeometry()
        self.update()

    def font_family(self) -> str | None:
        return self._font_family

    def set_opacity(self, opacity: float) -> None:
        self._opacity = max(0.0, min(1.0, float(opacity)))
        self.update()

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    def font_px(self) -> int:
        return self._font_px

    # ------------------------------------------------------------ 几何
    def _recalc_metrics(self) -> None:
        self._metrics = QFontMetricsF(self._font)
        digit_widths = [self._metrics.horizontalAdvance(ch) for ch in "0123456789"]
        widest = max(digit_widths) if digit_widths else 0.0
        # 略收窄数字格，避免等宽布局在 "1" 周围产生过大空隙；宽度仍完全固定，不会抖动
        self._digit_adv = widest * 0.95
        self._colon_adv = max(self._metrics.horizontalAdvance(":"), widest * 0.36)
        self._dot_adv = max(self._metrics.horizontalAdvance("."), widest * 0.26)

    def _char_advance(self, char: str) -> float:
        if char.isdigit():
            return self._digit_adv
        if char == ":":
            return self._colon_adv
        if char == ".":
            return self._dot_adv
        return self._metrics.horizontalAdvance(char)

    def _text_width(self, text: str) -> float:
        return sum(self._char_advance(char) for char in text)

    def sizeHint(self) -> QSize:
        width = max(self._text_width(self._template), self._text_width(self._text))
        return QSize(int(math.ceil(width)) + 6, int(math.ceil(self._metrics.height())) + 6)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        color = QColor(self._color)
        color.setAlphaF(self._opacity)
        painter.setPen(color)
        painter.setFont(self._font)

        text = self._text
        total = self._text_width(text)
        x = (self.width() - total) / 2.0
        height = float(self.height())
        for char in text:
            advance = self._char_advance(char)
            painter.drawText(
                QRectF(x, 0.0, advance, height),
                int(Qt.AlignmentFlag.AlignCenter),
                char,
            )
            x += advance

    # ------------------------------------------------------------ 交互
    def enterEvent(self, event) -> None:
        self.hover_changed.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hover_changed.emit(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event_global_pos(event)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.drag_started.emit(self._drag_origin)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None:
            self.drag_moved.emit(event_global_pos(event))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_origin is not None:
            self._drag_origin = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.drag_finished.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta:
            self.zoom_step.emit(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)
