"""iOS 风格滑块：细轨道 + 圆形手柄，拖动/悬停时手柄放大。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSlider

from app import constants as C
from app import theme as T
from app.qtcompat import event_pos


class IosSlider(QSlider):
    def __init__(self, parent=None, theme: T.ThemeManager | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._theme = theme
        self._hover = False
        self.setFixedHeight(C.SLIDER_HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if theme is not None:
            theme.changed.connect(self.update)

    # ------------------------------------------------------------ 几何
    def _margin(self) -> float:
        return float(C.SLIDER_HANDLE_RADIUS_HOVER)

    def _ratio(self) -> float:
        span = self.maximum() - self.minimum()
        if span <= 0:
            return 0.0
        return (self.value() - self.minimum()) / span

    def _handle_x(self) -> float:
        margin = self._margin()
        return margin + self._ratio() * max(0.0, self.width() - 2 * margin)

    def _set_value_from_x(self, x: float) -> None:
        margin = self._margin()
        usable = max(1.0, self.width() - 2 * margin)
        ratio = min(1.0, max(0.0, (x - margin) / usable))
        value = self.minimum() + round(ratio * (self.maximum() - self.minimum()))
        self.setValue(int(value))

    # ------------------------------------------------------------ 交互
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self._set_value_from_x(event_pos(event).x())
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        near = abs(event_pos(event).x() - self._handle_x()) <= C.SLIDER_HANDLE_RADIUS_HOVER + 8
        if near != self._hover:
            self._hover = near
            self.update()
        if self.isSliderDown():
            self._set_value_from_x(event_pos(event).x())
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self.isSliderDown():
            self.setSliderDown(False)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        tokens = self._theme.tokens() if self._theme else C.TOKENS["light"]
        accent = self._theme.accent() if self._theme else QColor(C.ACCENT_LIGHT)
        margin = self._margin()
        center_y = self.height() / 2.0
        track_h = float(C.SLIDER_TRACK_HEIGHT)
        radius = track_h / 2.0

        painter.setBrush(QColor(tokens["track"]))
        painter.drawRoundedRect(QRectF(margin, center_y - radius, self.width() - 2 * margin, track_h), radius, radius)

        handle_x = self._handle_x()
        if self.maximum() > self.minimum():
            painter.setBrush(accent)
            painter.drawRoundedRect(
                QRectF(margin, center_y - radius, max(0.0, handle_x - margin), track_h), radius, radius
            )

        active = self._hover or self.isSliderDown()
        handle_radius = float(
            C.SLIDER_HANDLE_RADIUS_HOVER if active else C.SLIDER_HANDLE_RADIUS
        )
        painter.setBrush(QColor(0, 0, 0, 38))
        painter.drawEllipse(QRectF(handle_x - handle_radius, center_y - handle_radius + 0.8, handle_radius * 2, handle_radius * 2))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(handle_x - handle_radius, center_y - handle_radius, handle_radius * 2, handle_radius * 2))
        painter.setBrush(accent)
        painter.drawEllipse(
            QRectF(
                handle_x - handle_radius * 0.42,
                center_y - handle_radius * 0.42,
                handle_radius * 0.84,
                handle_radius * 0.84,
            )
        )
