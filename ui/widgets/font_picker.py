"""字体选择弹窗：只列 Windows 通用字体，并带真实预览。

本机缺失的字体不会出现在列表里；已保存但缺失的字体在渲染时由
theme.clock_font 的 fallback 链自动回退，因此换电脑也能正常显示。
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app import constants as C
from app import theme as T
from app.qtcompat import event_pos


class FontPickerPanel(QWidget):
    font_selected = Signal(str)

    WIDTH = 268
    ROW_HEIGHT = 44
    PADDING = 10
    RADIUS = 16

    def __init__(
        self,
        theme: T.ThemeManager,
        current: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self._theme = theme
        self._current = current or ""
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        available = set(QFontDatabase.families())
        items = [
            (label, family)
            for label, family in C.CLOCK_FONT_OPTIONS
            if not family or family in available
        ]
        if not items:
            items = [(C.CLOCK_FONT_OPTIONS[0][0], "")]
        self._items = items
        self.setFixedSize(self.WIDTH, self.ROW_HEIGHT * len(items) + 2 * self.PADDING)
        theme.changed.connect(self.update)

    # ------------------------------------------------------------ 几何
    def _row_rect(self, index: int) -> QRectF:
        return QRectF(
            self.PADDING,
            self.PADDING + index * self.ROW_HEIGHT,
            self.WIDTH - 2 * self.PADDING,
            self.ROW_HEIGHT,
        )

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        card = self._theme.color("card", 252)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(card)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)
        painter.setPen(QPen(self._theme.color("separator", 180), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)
        painter.setPen(Qt.PenStyle.NoPen)

        for index, (label, family) in enumerate(self._items):
            rect = self._row_rect(index)
            selected = family == self._current
            if selected:
                painter.setBrush(self._theme.color("card_alt"))
                painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 10, 10)

            painter.setPen(self._theme.color("text"))
            painter.setFont(T.ui_font(12, QFont.Weight.DemiBold if selected else QFont.Weight.Normal))
            painter.drawText(
                QRectF(rect.left() + 14, rect.top(), rect.width() * 0.58, rect.height()),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                label,
            )

            painter.setFont(T.clock_font(19, family or None))
            painter.setPen(self._theme.accent() if selected else self._theme.color("text_secondary"))
            painter.drawText(
                QRectF(rect.left(), rect.top(), rect.width() - 14, rect.height()),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                C.FONT_PREVIEW_TEXT,
            )

    # ------------------------------------------------------------ 交互
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        index = int((event_pos(event).y() - self.PADDING) // self.ROW_HEIGHT)
        if 0 <= index < len(self._items):
            self.font_selected.emit(self._items[index][1])
            self.close()
        event.accept()
