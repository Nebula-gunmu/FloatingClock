"""iOS 风格色盘：饱和-明度方块 + 色相条 + 系统色预设 + 跟随主题。"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from app import constants as C
from app import theme as T
from app.qtcompat import event_pos


class ColorSwatch(QAbstractButton):
    """设置面板里的颜色入口：色点 + 文案，点击打开色盘。"""

    def __init__(self, theme: T.ThemeManager, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._color = QColor("#111114")
        self._auto = True
        self.setFixedSize(116, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        theme.changed.connect(self.update)

    def set_color(self, color: QColor | None, automatic: bool) -> None:
        self._auto = automatic
        self._color = QColor(color) if color is not None and color.isValid() else self._theme.color("text")
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._theme.color("card_alt"))
        painter.drawRoundedRect(QRectF(self.rect()), 9, 9)

        radius = 7.0
        dot_center = QPointF(16.0, self.height() / 2.0)
        painter.setBrush(self._color)
        painter.setPen(QPen(self._theme.color("separator"), 1.0))
        painter.drawEllipse(dot_center, radius, radius)

        painter.setPen(self._theme.color("text_secondary"))
        painter.setFont(T.ui_font(11))
        text = "跟随主题" if self._auto else self._color.name().upper()
        painter.drawText(
            QRectF(30, 0, self.width() - 34, self.height()),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            text,
        )


class IosColorPicker(QWidget):
    """自绘色盘弹窗（Qt.Popup：点外面自动关闭）。"""

    color_changed = Signal(QColor)
    reset_requested = Signal()

    WIDTH = 268
    HEIGHT = 338
    MARGIN = 16
    RADIUS = 18

    def __init__(
        self,
        theme: T.ThemeManager,
        current: QColor | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._hue = 0.58
        self._sat = 0.6
        self._val = 0.9
        if current is not None and current.isValid():
            hue, sat, val, _alpha = current.getHsvF()
            self._hue = 0.0 if hue < 0 else hue
            self._sat = sat
            self._val = val
        self._current = QColor.fromHsvF(self._hue, self._sat, self._val)
        self._drag = ""
        self._theme.changed.connect(self.update)

    # ------------------------------------------------------------ 几何
    def _sv_rect(self) -> QRect:
        return QRect(self.MARGIN, 42, self.WIDTH - 2 * self.MARGIN, 150)

    def _hue_rect(self) -> QRect:
        return QRect(self.MARGIN, 202, self.WIDTH - 2 * self.MARGIN, 14)

    def _preset_rects(self) -> list[tuple[QRect, QColor]]:
        rects: list[tuple[QRect, QColor]] = []
        size = 22
        gap = 8
        per_row = 8
        for index, name in enumerate(C.PRESET_COLORS):
            row, column = divmod(index, per_row)
            x = self.MARGIN + column * (size + gap)
            y = 232 + row * (size + gap)
            rects.append((QRect(x, y, size, size), QColor(name)))
        return rects

    def _reset_rect(self) -> QRect:
        return QRect(self.MARGIN, 296, self.WIDTH - 2 * self.MARGIN, 30)

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        card = self._theme.color("card", 252)
        painter.setBrush(card)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)
        painter.setPen(QPen(self._theme.color("separator", 180), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)
        painter.setPen(Qt.PenStyle.NoPen)

        painter.setPen(self._theme.color("text"))
        painter.setFont(T.ui_font(12, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(self.MARGIN, 10, self.width() - 2 * self.MARGIN, 22),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            "数字颜色",
        )

        self._paint_sv(painter)
        self._paint_hue(painter)
        self._paint_presets(painter)
        self._paint_reset(painter)

    def _paint_sv(self, painter: QPainter) -> None:
        rect = self._sv_rect()
        base = QColor.fromHsvF(self._hue, 1.0, 1.0)
        painter.save()
        from PySide6.QtGui import QPainterPath

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(rect), 8, 8)
        painter.setClipPath(clip)
        painter.fillRect(rect, base)

        white = QLinearGradient(QPointF(rect.left(), 0), QPointF(rect.right(), 0))
        white.setColorAt(0.0, QColor(255, 255, 255, 255))
        white.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(rect, white)

        black = QLinearGradient(QPointF(0, rect.top()), QPointF(0, rect.bottom()))
        black.setColorAt(0.0, QColor(0, 0, 0, 0))
        black.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.fillRect(rect, black)
        painter.restore()

        x = rect.left() + self._sat * rect.width()
        y = rect.bottom() - self._val * rect.height()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 230), 2.0))
        painter.drawEllipse(QPointF(x, y), 7.0, 7.0)
        painter.setPen(QPen(QColor(0, 0, 0, 60), 1.0))
        painter.drawEllipse(QPointF(x, y), 8.5, 8.5)

    def _paint_hue(self, painter: QPainter) -> None:
        rect = self._hue_rect()
        gradient = QLinearGradient(QPointF(rect.left(), 0), QPointF(rect.right(), 0))
        for step in range(7):
            ratio = step / 6.0
            gradient.setColorAt(ratio, QColor.fromHsvF(min(0.999, ratio), 1.0, 1.0))
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(rect), 7, 7)

        x = rect.left() + self._hue * rect.width()
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0, 70), 1.0))
        painter.drawRoundedRect(QRectF(x - 3.0, rect.top() - 2, 6.0, rect.height() + 4), 3, 3)

    def _paint_presets(self, painter: QPainter) -> None:
        for rect, color in self._preset_rects():
            painter.setBrush(color)
            selected = color.rgb() == self._current.rgb()
            painter.setPen(QPen(self._theme.color("text") if selected else QColor(0, 0, 0, 28), 2.0 if selected else 1.0))
            painter.drawEllipse(QRectF(rect).adjusted(1, 1, -1, -1))

    def _paint_reset(self, painter: QPainter) -> None:
        rect = self._reset_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._theme.color("card_alt"))
        painter.drawRoundedRect(QRectF(rect), rect.height() / 2, rect.height() / 2)
        painter.setPen(self._theme.color("accent"))
        painter.setFont(T.ui_font(12, QFont.Weight.DemiBold))
        painter.drawText(QRectF(rect), int(Qt.AlignmentFlag.AlignCenter), "跟随主题")

    # ------------------------------------------------------------ 交互
    def _set_from_sv(self, x: float, y: float) -> None:
        rect = self._sv_rect()
        self._sat = min(1.0, max(0.0, (x - rect.left()) / max(1.0, rect.width())))
        self._val = min(1.0, max(0.0, (rect.bottom() - y) / max(1.0, rect.height())))
        self._emit_current()

    def _set_from_hue(self, x: float) -> None:
        rect = self._hue_rect()
        self._hue = min(0.9999, max(0.0, (x - rect.left()) / max(1.0, rect.width())))
        self._emit_current()

    def _emit_current(self) -> None:
        self._current = QColor.fromHsvF(self._hue, self._sat, self._val)
        self.color_changed.emit(self._current)
        self.update()

    def _apply_preset(self, color: QColor) -> None:
        hue, sat, val, _alpha = color.getHsvF()
        self._hue = 0.0 if hue < 0 else hue
        self._sat = sat
        self._val = val
        self._emit_current()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = event_pos(event)
        if self._sv_rect().contains(point.toPoint()):
            self._drag = "sv"
            self._set_from_sv(point.x(), point.y())
        elif self._hue_rect().contains(point.toPoint()):
            self._drag = "hue"
            self._set_from_hue(point.x())
        elif self._reset_rect().contains(point.toPoint()):
            self.reset_requested.emit()
            self.close()
        else:
            for rect, color in self._preset_rects():
                if rect.contains(point.toPoint()):
                    self._apply_preset(color)
                    break
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        point = event_pos(event)
        if self._drag == "sv":
            self._set_from_sv(point.x(), point.y())
            event.accept()
            return
        if self._drag == "hue":
            self._set_from_hue(point.x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag = ""
        super().mouseReleaseEvent(event)
