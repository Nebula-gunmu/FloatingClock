"""iOS 风格月历卡片：圆角卡片、星期行、6 行日期网格、当天高亮、月份切换。"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app import constants as C
from app import theme as T

WEEKDAY_LABELS = ("日", "一", "二", "三", "四", "五", "六")


class CalendarCard(QWidget):
    """纯展示月历：切换月份 + 回到今天，不含任何事件/提醒逻辑。"""

    month_changed = Signal(int, int)

    def __init__(self, theme: T.ThemeManager, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        today = date.today()
        self._year = today.year
        self._month = today.month
        self._hit_prev = QRect()
        self._hit_next = QRect()
        self._hit_today = QRect()
        self.setFixedSize(C.CALENDAR_WIDTH, self._card_height())
        self.setCursor(Qt.CursorShape.ArrowCursor)
        theme.changed.connect(self.update)

    # ------------------------------------------------------------ 尺寸
    @staticmethod
    def _card_height() -> int:
        return C.CAL_HEADER_H + C.CAL_WEEKDAY_H + C.CAL_ROWS * C.CAL_CELL_H + C.CAL_FOOTER_H

    # ------------------------------------------------------------ 月份控制
    def shift_month(self, delta: int) -> None:
        month_index = self._year * 12 + (self._month - 1) + delta
        self._year, month_zero = divmod(month_index, 12)
        self._month = month_zero + 1
        self.month_changed.emit(self._year, self._month)
        self.update()

    def go_today(self) -> None:
        today = date.today()
        if (today.year, today.month) != (self._year, self._month):
            self._year, self._month = today.year, today.month
            self.month_changed.emit(self._year, self._month)
        self.update()

    def current_month(self) -> tuple[int, int]:
        return self._year, self._month

    # ------------------------------------------------------------ 几何辅助
    def _grid_metrics(self) -> tuple[float, float, float, float]:
        inset = float(C.CAL_GRID_INSET)
        grid_width = self.width() - 2 * inset
        cell_w = grid_width / 7.0
        grid_top = float(C.CAL_HEADER_H + C.CAL_WEEKDAY_H)
        return inset, cell_w, grid_top, float(C.CAL_CELL_H)

    def _cell_rect(self, row: int, column: int) -> QRectF:
        inset, cell_w, grid_top, cell_h = self._grid_metrics()
        return QRectF(inset + column * cell_w, grid_top + row * cell_h, cell_w, cell_h)

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        tokens = self._theme.tokens()

        background = self._theme.color("card", 238)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), C.CARD_RADIUS, C.CARD_RADIUS)

        self._paint_header(painter, tokens)
        self._paint_weekdays(painter, tokens)
        self._paint_days(painter, tokens)
        self._paint_footer(painter)

    def _paint_header(self, painter: QPainter, tokens: dict) -> None:
        painter.setPen(self._theme.color("text"))
        painter.setFont(T.ui_font(C.CAL_TITLE_FONT_PX, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(18, 0, self.width() - 120, C.CAL_HEADER_H),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            f"{self._year}年{self._month}月",
        )

        arrow = float(C.CAL_ARROW_SIZE)
        gap = float(C.CAL_ARROW_GAP)
        right = self.width() - 16.0
        self._hit_next = QRect(int(right - arrow), int((C.CAL_HEADER_H - arrow) / 2), int(arrow), int(arrow))
        self._hit_prev = QRect(
            int(right - arrow * 2 - gap), int((C.CAL_HEADER_H - arrow) / 2), int(arrow), int(arrow)
        )
        pen = QPen(self._theme.color("text_secondary"))
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for rect, direction in ((self._hit_prev, 1), (self._hit_next, -1)):
            center = QRectF(rect).center()
            offset = 3.0
            path = QPainterPath(QPointF(center.x() + offset * direction, center.y() - 5.0))
            path.lineTo(QPointF(center.x() - offset * direction, center.y()))
            path.lineTo(QPointF(center.x() + offset * direction, center.y() + 5.0))
            painter.drawPath(path)

    def _paint_weekdays(self, painter: QPainter, tokens: dict) -> None:
        painter.setPen(self._theme.color("text_tertiary"))
        painter.setFont(T.ui_font(C.CAPTION_FONT_PX))
        inset, cell_w, grid_top, _ = self._grid_metrics()
        top = grid_top - C.CAL_WEEKDAY_H
        for index, label in enumerate(WEEKDAY_LABELS):
            painter.drawText(
                QRectF(inset + index * cell_w, top, cell_w, C.CAL_WEEKDAY_H),
                int(Qt.AlignmentFlag.AlignCenter),
                label,
            )

    def _paint_days(self, painter: QPainter, tokens: dict) -> None:
        today = date.today()
        first = date(self._year, self._month, 1)
        leading = (first.weekday() + 1) % 7  # 周日为一周第一列
        start = first - timedelta(days=leading)

        day_font = T.ui_font(C.CAL_DAY_FONT_PX)
        today_font = T.ui_font(C.CAL_DAY_FONT_PX, QFont.Weight.DemiBold)
        regular = self._theme.color("text")
        muted = self._theme.color("text_tertiary")
        accent = self._theme.accent()

        for index in range(C.CAL_ROWS * 7):
            row, column = divmod(index, 7)
            current = start + timedelta(days=index)
            cell = self._cell_rect(row, column)
            is_today = current == today
            if is_today:
                radius = min(cell.width(), cell.height()) * 0.44
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(accent)
                painter.drawEllipse(cell.center(), radius, radius)
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(today_font)
            else:
                in_month = current.month == self._month
                painter.setPen(regular if in_month else muted)
                painter.setFont(day_font)
            painter.drawText(cell, int(Qt.AlignmentFlag.AlignCenter), str(current.day))

    def _paint_footer(self, painter: QPainter) -> None:
        width = float(C.CAL_TODAY_W)
        height = float(C.CAL_TODAY_H)
        x = (self.width() - width) / 2.0
        y = self.height() - C.CAL_FOOTER_H + (C.CAL_FOOTER_H - height) / 2.0
        self._hit_today = QRect(int(x), int(y), int(width), int(height))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._theme.color("card_alt"))
        painter.drawRoundedRect(QRectF(x, y, width, height), height / 2.0, height / 2.0)
        painter.setPen(self._theme.accent())
        painter.setFont(T.ui_font(C.CAPTION_FONT_PX, QFont.Weight.DemiBold))
        painter.drawText(QRectF(x, y, width, height), int(Qt.AlignmentFlag.AlignCenter), "今天")

    # ------------------------------------------------------------ 交互
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        position = event.position().toPoint()
        if self._hit_prev.contains(position):
            self.shift_month(-1)
        elif self._hit_next.contains(position):
            self.shift_month(1)
        elif self._hit_today.contains(position):
            self.go_today()
        event.accept()
