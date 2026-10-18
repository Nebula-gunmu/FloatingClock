"""iOS 风格胶囊开关：开=强调色、关=灰色，160ms 缓动动画。"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

from app import constants as C
from app import theme as T


class IosSwitch(QAbstractButton):
    def __init__(self, parent=None, theme: T.ThemeManager | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(C.SWITCH_WIDTH, C.SWITCH_HEIGHT)
        self._offset = 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(C.ANIM_NORMAL)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)
        if theme is not None:
            theme.changed.connect(self.update)

    # ------------------------------------------------------------ 动画属性
    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(target)
        self._anim.start()

    def set_checked_silently(self, checked: bool) -> None:
        """同步外部状态时使用：不触发动画突兀感，直接落位。"""
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self._anim.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    # ------------------------------------------------------------ 绘制
    def sizeHint(self) -> QSize:
        return QSize(C.SWITCH_WIDTH, C.SWITCH_HEIGHT)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        tokens = self._theme.tokens() if self._theme else C.TOKENS["light"]
        off_color = QColor(tokens["switch_off"])
        on_color = self._theme.accent() if self._theme else QColor(C.ACCENT_LIGHT)
        painter.setBrush(T.mix(off_color, on_color, self._offset))
        radius = self.height() / 2.0
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)

        margin = C.SWITCH_KNOB_MARGIN
        knob = self.height() - 2 * margin
        travel = self.width() - knob - 2 * margin
        x = margin + self._offset * travel
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.drawEllipse(QRectF(x, margin + 0.6, knob, knob))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(x, margin, knob, knob))
