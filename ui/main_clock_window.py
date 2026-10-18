"""主悬浮窗：无边框透明窗口，承载时钟数字、副行与日历卡片。

本类只负责"显示 + 输入事件翻译"，不包含任何业务规则：
拖动/滚轮/悬浮等交互通过信号交给 AppController 处理。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app import constants as C
from app import theme as T
from app.settings_model import SettingsStore
from winplatform import win_effects

from .widgets import CalendarCard, ClockFace


class MainClockWindow(QWidget):
    gear_clicked = Signal()
    zoom_requested = Signal(int)
    position_changed = Signal(int, int)

    def __init__(self, settings: SettingsStore, theme: T.ThemeManager, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._theme = theme
        self._acrylic_ok = False
        self._blur_mode = win_effects.BLUR_NONE
        self._native_ready = False
        self._drag_offset: QPoint | None = None
        self._weather_text = ""
        self._date_text = ""
        self._date_key: tuple[int, int, int] | None = None

        self.setWindowFlags(self._base_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowTitle(C.APP_DISPLAY_NAME)
        self.setMouseTracking(True)

        self._clock = ClockFace(self)
        self._subline = QLabel(self)
        self._subline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subline.setTextFormat(Qt.TextFormat.PlainText)
        self._subline.setWordWrap(False)
        self._subline.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._subline.setVisible(False)

        self._calendar = CalendarCard(theme, self)
        self._calendar_holder = QWidget(self)
        calendar_layout = QVBoxLayout(self._calendar_holder)
        calendar_layout.setContentsMargins(0, C.CALENDAR_TOP_MARGIN, 0, 0)
        calendar_layout.setSpacing(0)
        calendar_layout.addWidget(self._calendar, 0, Qt.AlignmentFlag.AlignHCenter)
        self._calendar_holder.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            C.CONTENT_MARGIN_X, C.CONTENT_MARGIN_TOP, C.CONTENT_MARGIN_X, C.CONTENT_MARGIN_BOTTOM
        )
        self._layout.setSpacing(C.CLOCK_CONTENT_SPACING)
        self._layout.addWidget(self._clock, 0, Qt.AlignmentFlag.AlignHCenter)
        self._layout.addWidget(self._subline, 0, Qt.AlignmentFlag.AlignHCenter)
        self._layout.addWidget(self._calendar_holder, 0, Qt.AlignmentFlag.AlignHCenter)

        # 齿轮设置按钮：鼠标停留在时钟区域时淡入，离开淡出
        self._gear = QToolButton(self)
        self._gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gear.setFixedSize(C.GEAR_SIZE, C.GEAR_SIZE)
        self._gear.setText("⚙")
        self._gear.setToolTip("设置")
        self._gear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._gear.setFont(T.gear_font())
        self._gear.clicked.connect(self.gear_clicked.emit)
        self._gear.installEventFilter(self)
        self._gear.setVisible(False)

        self._gear_effect = QGraphicsOpacityEffect(self._gear)
        self._gear_effect.setOpacity(0.0)
        self._gear.setGraphicsEffect(self._gear_effect)
        self._gear_anim = QPropertyAnimation(self._gear_effect, b"opacity", self)
        self._gear_anim.setDuration(C.ANIM_FAST)
        self._gear_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._gear_anim.finished.connect(self._on_gear_anim_finished)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(C.HOVER_HIDE_DELAY_MS)
        self._hide_timer.timeout.connect(self._hide_gear_if_away)

        self._date_timer = QTimer(self)
        self._date_timer.setInterval(1000)
        self._date_timer.timeout.connect(self._refresh_date)
        self._date_timer.start()

        self._clock.hover_changed.connect(self._on_clock_hover)
        self._clock.drag_started.connect(self._on_drag_started)
        self._clock.drag_moved.connect(self._on_drag_moved)
        self._clock.drag_finished.connect(self._on_drag_finished)
        self._clock.zoom_step.connect(self.zoom_requested.emit)

        self._theme.changed.connect(self._on_theme_changed)

        # 置顶重申定时器：防止被其它置顶窗口压住
        self._topmost_timer = QTimer(self)
        self._topmost_timer.setInterval(C.TOPMOST_REASSERT_MS)
        self._topmost_timer.timeout.connect(self._reassert_topmost)

        self._apply_theme()
        self.apply_settings()

    # ------------------------------------------------------------ 窗口标志
    def _base_flags(self) -> Qt.WindowType:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._settings.data.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        return flags

    def set_topmost(self, enabled: bool) -> None:
        """切换置顶：Qt 标志 + Win32 SetWindowPos 双保险。"""
        geometry = self.geometry()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()
        self.setGeometry(geometry)
        self._native_ready = False
        QTimer.singleShot(0, self._init_native)
        self._update_topmost_timer()

    def _update_topmost_timer(self) -> None:
        if self._settings.data.always_on_top:
            if not self._topmost_timer.isActive():
                self._topmost_timer.start()
        else:
            self._topmost_timer.stop()

    def _reassert_topmost(self) -> None:
        """把窗口重新提到 topmost 组最前（不抢焦点）。"""
        if not self._settings.data.always_on_top or not self.isVisible():
            return
        hwnd = self._hwnd()
        if hwnd:
            win_effects.set_topmost(hwnd, True)

    # ------------------------------------------------------------ 设置应用
    def apply_settings(self) -> None:
        data = self._settings.data
        self._clock.set_font_family(data.clock_font or None)
        self._clock.set_font_px(data.font_size)
        self._clock.set_opacity(data.text_opacity)
        self._clock.set_color(self._clock_color())
        self._subline.setFont(T.sub_font(self._subline_px()))
        self._update_subline_color()
        self._calendar.setVisible(True)
        self._calendar_holder.setVisible(bool(data.calendar_enabled))
        self._refresh_date()
        self._update_subline()
        self._sync_background()
        self._sync_topmost_flag()
        self._sync_size(preserve_center=True)

    def _sync_topmost_flag(self) -> None:
        wanted = bool(self._settings.data.always_on_top)
        current = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if wanted != current:
            self.set_topmost(wanted)
        else:
            self._update_topmost_timer()

    def _subline_px(self) -> int:
        return max(
            C.SUBLINE_MIN_PX,
            min(C.SUBLINE_MAX_PX, int(round(self._settings.data.font_size * C.SUBLINE_RATIO))),
        )

    def _update_subline_color(self) -> None:
        alpha = int(round(255 * max(0.0, min(1.0, self._settings.data.text_opacity))))
        color = T.rgba(self._theme.tokens()["text_secondary"], alpha)
        self._subline.setStyleSheet(f"color: {color};")

    def _clock_color(self) -> QColor:
        """数字颜色：未自定义时跟随主题文字色。"""
        custom = self._settings.data.clock_color
        if custom:
            color = QColor(custom)
            if color.isValid():
                return color
        return self._theme.color("text")

    def apply_clock_color(self) -> None:
        self._clock.set_color(self._clock_color())

    def apply_clock_font(self) -> None:
        self._clock.set_font_family(self._settings.data.clock_font or None)
        self._sync_size(preserve_center=True)

    def apply_text_opacity(self) -> None:
        self._clock.set_opacity(self._settings.data.text_opacity)
        self._update_subline_color()

    def _apply_theme(self) -> None:
        tokens = self._theme.tokens()
        self._gear.setStyleSheet(
            "QToolButton {"
            f" background: {T.rgba(tokens['gear_bg'], 190)};"
            f" color: {tokens['text_secondary']};"
            ' font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";'
            " border: none;"
            f" border-radius: {C.GEAR_SIZE // 2}px;"
            "}"
        )
        self._clock.set_color(self._clock_color())
        self._update_subline_color()

    def _on_theme_changed(self) -> None:
        self._apply_theme()
        self._sync_background()
        self.update()

    # ------------------------------------------------------------ 文本
    def set_display_text(self, text: str) -> None:
        self._clock.set_text(text)
        self._sync_size(preserve_center=True)

    def set_template(self, template: str) -> None:
        self._clock.set_template(template)
        self._sync_size(preserve_center=True)

    def set_weather_summary(self, text: str) -> None:
        if text == self._weather_text:
            return
        self._weather_text = text
        self._update_subline()

    def _refresh_date(self) -> None:
        now = datetime.now()
        key = (now.year, now.month, now.day)
        if key == self._date_key:
            return
        self._date_key = key
        self._date_text = f"{now.month}月{now.day}日 {C.WEEKDAY_CN[now.weekday()]}"
        self._update_subline()

    def _update_subline(self) -> None:
        data = self._settings.data
        parts: list[str] = []
        if data.show_date and self._date_text:
            parts.append(self._date_text)
        if data.show_weather and self._weather_text:
            parts.append(self._weather_text)
        text = "    ".join(parts)
        visible = bool(text)
        changed = text != self._subline.text() or visible != self._subline.isVisible()
        self._subline.setText(text)
        self._subline.setVisible(visible)
        if changed:
            self._sync_size(preserve_center=True)

    # ------------------------------------------------------------ 几何
    def _sync_size(self, preserve_center: bool = True) -> None:
        old_center = self.geometry().center() if self.isVisible() else None
        self._layout.activate()
        hint = self._layout.totalSizeHint()
        if hint == self.size():
            self._place_gear()
            return
        self.resize(hint)
        if preserve_center and old_center is not None:
            self.move(old_center.x() - hint.width() // 2, old_center.y() - hint.height() // 2)
        self._place_gear()

    def _place_gear(self) -> None:
        x = max(0, self.width() - C.GEAR_SIZE - C.GEAR_MARGIN)
        y = max(0, self.height() - C.GEAR_SIZE - C.GEAR_MARGIN)
        self._gear.move(x, y)
        self._gear.raise_()

    def restore_position(self) -> None:
        data = self._settings.data
        self._sync_size(preserve_center=False)
        if data.window_x >= 0 and data.window_y >= 0:
            self.move(data.window_x, data.window_y)
            if self._is_on_screen():
                return
        self.center_on_screen()

    def center_on_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.center().x() - self.width() // 2
        y = area.top() + int(area.height() * 0.18)
        self.move(x, y)

    def _is_on_screen(self) -> bool:
        center = self.frameGeometry().center()
        return any(screen.availableGeometry().contains(center) for screen in QGuiApplication.screens())

    # ------------------------------------------------------------ 齿轮显隐
    def _on_clock_hover(self, hovered: bool) -> None:
        if hovered:
            self._hide_timer.stop()
            self._show_gear()
        else:
            self._hide_timer.start()

    def _show_gear(self) -> None:
        if not self._gear.isVisible():
            self._gear.setVisible(True)
            self._gear.raise_()
        self._gear_anim.stop()
        self._gear_anim.setStartValue(self._gear_effect.opacity())
        self._gear_anim.setEndValue(1.0)
        self._gear_anim.start()

    def _hide_gear(self) -> None:
        if not self._gear.isVisible():
            return
        self._gear_anim.stop()
        self._gear_anim.setStartValue(self._gear_effect.opacity())
        self._gear_anim.setEndValue(0.0)
        self._gear_anim.start()

    def _on_gear_anim_finished(self) -> None:
        if self._gear_effect.opacity() < 0.01:
            self._gear.setVisible(False)

    def _hide_gear_if_away(self) -> None:
        if self._clock.underMouse() or self._gear.underMouse():
            return
        self._hide_gear()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._gear:
            if event.type() == QEvent.Type.Enter:
                self._hide_timer.stop()
            elif event.type() == QEvent.Type.Leave:
                self._hide_timer.start()
        return super().eventFilter(obj, event)

    def leaveEvent(self, event) -> None:
        self._hide_timer.start()
        super().leaveEvent(event)

    # ------------------------------------------------------------ 拖动
    def _on_drag_started(self, global_pos: QPoint) -> None:
        self._drag_offset = global_pos - self.frameGeometry().topLeft()

    def _on_drag_moved(self, global_pos: QPoint) -> None:
        if self._drag_offset is None:
            return
        self.move(global_pos - self._drag_offset)

    def _on_drag_finished(self) -> None:
        self._drag_offset = None
        self.position_changed.emit(self.x(), self.y())

    # ------------------------------------------------------------ 原生效果
    def _hwnd(self) -> int:
        try:
            return int(self.winId())
        except (RuntimeError, TypeError):
            return 0

    def _init_native(self) -> None:
        if not win_effects.is_supported():
            return
        hwnd = self._hwnd()
        if not hwnd:
            return
        win_effects.set_topmost(hwnd, self._settings.data.always_on_top)
        self._native_ready = True
        self._sync_background()
        if self._settings.data.always_on_top:
            # 窗口刚映射时 Qt 可能覆盖 z-order，等它稳定后再提一次
            QTimer.singleShot(
                C.TOPMOST_SETTLE_MS,
                lambda: win_effects.set_topmost(self._hwnd(), True),
            )

    # ------------------------------------------------------------ 背景（原生磨砂）
    def _sync_background(self) -> None:
        """开启时用 Windows 原生磨砂（实时、随拖动跟手，矩形区域）。"""
        data = self._settings.data
        if not self._native_ready:
            self._blur_mode = win_effects.BLUR_NONE
            self._acrylic_ok = False
            self.update()
            return

        hwnd = self._hwnd()
        if not hwnd:
            return

        if data.background_enabled:
            tint = self._theme.color("acrylic_tint")
            alpha = int(max(0.0, min(1.0, data.background_opacity)) * 255)
            self._blur_mode = win_effects.enable_background(
                hwnd, (tint.red(), tint.green(), tint.blue()), alpha
            )
        else:
            win_effects.disable_background(hwnd)
            self._blur_mode = win_effects.BLUR_NONE
        self._acrylic_ok = self._blur_mode != win_effects.BLUR_NONE
        self.update()

    # ------------------------------------------------------------ 事件
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_size(preserve_center=False)
        QTimer.singleShot(0, self._init_native)
        self._update_topmost_timer()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_gear()

    def closeEvent(self, event) -> None:
        self.position_changed.emit(self.x(), self.y())
        super().closeEvent(event)

    def paintEvent(self, _event) -> None:
        data = self._settings.data
        if not data.background_enabled:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        opacity = max(0.0, min(1.0, data.background_opacity))
        base = self._theme.color("acrylic_tint")
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        rounded = QPainterPath()
        rounded.addRoundedRect(rect, C.WINDOW_RADIUS, C.WINDOW_RADIUS)

        if self._blur_mode in (win_effects.BLUR_ACCENT, win_effects.BLUR_AERO):
            # 原生亚克力 / Aero 玻璃：模糊由系统绘制（矩形区域），这里只叠一层很淡的主题色调
            inner = QColor(base)
            inner.setAlpha(int(255 * opacity * 0.10))
            painter.fillRect(self.rect(), inner)
        elif self._blur_mode == win_effects.BLUR_SYSTEM:
            # 系统 backdrop 自带模糊与原生圆角，按透明度叠色调即可
            inner = QColor(base)
            inner.setAlpha(int(255 * opacity * 0.30))
            painter.fillPath(rounded, inner)
        else:
            # 磨砂不可用时的降级：半透明圆角纯色背景
            solid = QColor(base)
            solid.setAlpha(int(255 * opacity * 0.92))
            painter.fillPath(rounded, solid)
