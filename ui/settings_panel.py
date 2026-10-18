"""设置面板：iOS Inset Grouped 风格分组列表，独立可拖动窗口。

面板只做"输入采集 + 状态回显"，所有设置写入与副作用由 AppController 完成。
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app import constants as C
from app import theme as T
from app.qtcompat import event_global_pos
from app.settings_model import SettingsStore
from core.time_modes import ModeController

from .widgets import (
    ColorSwatch,
    FontPickerPanel,
    IosColorPicker,
    IosSegmented,
    IosSlider,
    IosSwitch,
)

MODE_ORDER = ("clock", "countdown", "stopwatch")
MODE_LABELS = ("时钟", "倒计时", "秒表")
APPEARANCE_LABELS = ("跟随系统", "浅色", "深色")


class SettingsPanel(QWidget):
    setting_changed = Signal(str, object)
    countdown_action = Signal(str)
    stopwatch_action = Signal(str)
    weather_city_applied = Signal(str)
    weather_refresh_requested = Signal()
    quit_requested = Signal()
    closed = Signal()

    def __init__(
        self,
        settings: SettingsStore,
        theme: T.ThemeManager,
        modes: ModeController,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._theme = theme
        self._modes = modes
        self._drag_offset: QPoint | None = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("设置")

        self._build()
        self._wire()
        self.sync_from_settings()
        self._fit_height()
        self._theme.changed.connect(self._on_theme_changed)

        # 面板弹出/收起动画（150ms 左右，与规格要求的 120-200ms 一致）
        self._fading_out = False
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(C.ANIM_NORMAL)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)

    # ------------------------------------------------------------ 构建
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            C.PANEL_SHADOW_MARGIN, C.PANEL_SHADOW_MARGIN, C.PANEL_SHADOW_MARGIN, C.PANEL_SHADOW_MARGIN
        )
        root.setSpacing(0)

        self._body = QFrame(self)
        self._body.setObjectName("panelBody")
        shadow = QGraphicsDropShadowEffect(self._body)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 110))
        self._body.setGraphicsEffect(shadow)
        root.addWidget(self._body)

        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # 标题栏（可拖动）
        self._title_bar = QWidget(self._body)
        self._title_bar.setFixedHeight(C.PANEL_TITLE_HEIGHT)
        self._title_bar.installEventFilter(self)
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(20, 0, 14, 0)
        title_layout.setSpacing(8)
        title = QLabel("设置", self._title_bar)
        title.setObjectName("panelTitle")
        self._close_button = QPushButton("✕", self._title_bar)
        self._close_button.setObjectName("closeButton")
        self._close_button.setFixedSize(22, 22)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        title_layout.addWidget(self._close_button)
        body.addWidget(self._title_bar)

        # 滚动内容
        self._scroll = QScrollArea(self._body)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent;")

        container = QWidget(self._scroll)
        container.setStyleSheet("background: transparent;")
        content = QVBoxLayout(container)
        content.setContentsMargins(
            C.PANEL_CONTENT_MARGIN, 0, C.PANEL_CONTENT_MARGIN, C.PANEL_CONTENT_MARGIN
        )
        content.setSpacing(C.SECTION_GAP)

        self._build_appearance(content)
        self._build_display(content)
        self._build_topmost(content)
        self._build_functions(content)
        self._build_weather(content)
        self._build_calendar(content)
        self._build_system(content)
        content.addStretch(1)

        self._scroll.setWidget(container)
        body.addWidget(self._scroll, 1)

    # ------------------------------------------------------------ 分组：外观
    def _build_appearance(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "外观")

        self._seg_appearance = IosSegmented(list(APPEARANCE_LABELS), self._body, self._theme)
        self._add_row(card, "外观模式", self._seg_appearance)

        self._clock_color_swatch = ColorSwatch(self._theme, self._body)
        self._clock_color_swatch.clicked.connect(self.open_color_picker)
        self._add_row(card, "数字颜色", self._clock_color_swatch)

        self._font_button = self._make_button("默认", "secondaryButton", self._body)
        self._font_button.setMinimumWidth(128)
        self._font_button.clicked.connect(self.open_font_picker)
        self._add_row(card, "时钟字体", self._font_button)

        self._slider_text_opacity = IosSlider(self._body, self._theme)
        self._slider_text_opacity.setRange(0, 100)
        self._add_slider_row(
            card,
            "文字透明度",
            self._slider_text_opacity,
            lambda value: f"{value}%",
        )

        self._slider_font = IosSlider(self._body, self._theme)
        self._slider_font.setRange(C.CLOCK_FONT_MIN, C.CLOCK_FONT_MAX)
        self._add_slider_row(card, "时钟尺寸", self._slider_font, lambda value: f"{value}")

        self._switch_background = IosSwitch(self._body, self._theme)
        self._add_row(card, "磨砂背景", self._switch_background)

        self._slider_bg_opacity = IosSlider(self._body, self._theme)
        self._slider_bg_opacity.setRange(0, 100)
        self._add_slider_row(
            card, "背景透明度", self._slider_bg_opacity, lambda value: f"{value}%"
        )

        self._switch_wheel = IosSwitch(self._body, self._theme)
        self._add_row(card, "滚轮缩放", self._switch_wheel)
        self._trim_separator(card)

    # ------------------------------------------------------------ 分组：显示
    def _build_display(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "显示")

        self._switch_date = IosSwitch(self._body, self._theme)
        self._add_row(card, "显示日期", self._switch_date)

        self._switch_weather = IosSwitch(self._body, self._theme)
        self._add_row(card, "显示天气", self._switch_weather)

        self._seg_mode = IosSegmented(list(MODE_LABELS), self._body, self._theme)
        self._add_row(card, "显示模式", self._seg_mode)
        self._trim_separator(card)

    # ------------------------------------------------------------ 分组：置顶
    def _build_topmost(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "置顶")
        self._switch_topmost = IosSwitch(self._body, self._theme)
        self._add_row(card, "窗口置顶", self._switch_topmost)
        self._trim_separator(card)

    # ------------------------------------------------------------ 分组：功能
    def _build_functions(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "功能")

        self._switch_timers = IosSwitch(self._body, self._theme)
        self._add_row(card, "倒计时 / 秒表", self._switch_timers)

        duration = QWidget(self._body)
        duration_layout = QHBoxLayout(duration)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(6)
        self._spin_minutes = QSpinBox(duration)
        self._spin_minutes.setRange(0, 999)
        self._spin_minutes.setFixedWidth(64)
        self._spin_seconds = QSpinBox(duration)
        self._spin_seconds.setRange(0, 59)
        self._spin_seconds.setFixedWidth(64)
        minutes_label = QLabel("分", duration)
        minutes_label.setObjectName("captionLabel")
        seconds_label = QLabel("秒", duration)
        seconds_label.setObjectName("captionLabel")
        duration_layout.addWidget(self._spin_minutes)
        duration_layout.addWidget(minutes_label)
        duration_layout.addWidget(self._spin_seconds)
        duration_layout.addWidget(seconds_label)
        self._add_row(card, "倒计时时长", duration)

        self._btn_cd_start = self._make_button("开始", "primaryButton", self._body)
        self._btn_cd_pause = self._make_button("暂停", "secondaryButton", self._body)
        self._btn_cd_reset = self._make_button("重置", "secondaryButton", self._body)
        self._add_row(
            card,
            "倒计时",
            self._make_button_group((self._btn_cd_start, self._btn_cd_pause, self._btn_cd_reset)),
        )

        self._btn_sw_start = self._make_button("开始", "primaryButton", self._body)
        self._btn_sw_pause = self._make_button("暂停", "secondaryButton", self._body)
        self._btn_sw_reset = self._make_button("重置", "secondaryButton", self._body)
        self._add_row(
            card,
            "秒表",
            self._make_button_group((self._btn_sw_start, self._btn_sw_pause, self._btn_sw_reset)),
        )
        self._trim_separator(card)

    # ------------------------------------------------------------ 分组：天气
    def _build_weather(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "天气")

        city_box = QWidget(self._body)
        city_layout = QHBoxLayout(city_box)
        city_layout.setContentsMargins(0, 0, 0, 0)
        city_layout.setSpacing(8)
        self._city_edit = QLineEdit(city_box)
        self._city_edit.setPlaceholderText("城市名，如 北京")
        self._city_edit.setFixedWidth(150)
        self._apply_city_button = self._make_button("应用", "primaryButton", city_box)
        city_layout.addWidget(self._city_edit)
        city_layout.addWidget(self._apply_city_button)
        self._add_row(card, "城市", city_box)

        info = QWidget(self._body)
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 2, 0, 2)
        info_layout.setSpacing(3)
        self._weather_city_label = QLabel("尚未解析坐标", info)
        self._weather_city_label.setObjectName("captionLabel")
        self._weather_status_label = QLabel("未设置城市", info)
        self._weather_status_label.setObjectName("captionLabel")
        self._weather_updated_label = QLabel("最后更新 尚未获取", info)
        self._weather_updated_label.setObjectName("captionLabel")
        for label in (self._weather_city_label, self._weather_status_label, self._weather_updated_label):
            label.setWordWrap(True)
            info_layout.addWidget(label)
        self._add_row(card, "状态", info)

        self._refresh_weather_button = self._make_button("手动刷新", "secondaryButton", self._body)
        self._add_row(card, "刷新", self._refresh_weather_button)
        self._trim_separator(card)

    # ------------------------------------------------------------ 分组：日历
    def _build_calendar(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "日历")
        self._switch_calendar = IosSwitch(self._body, self._theme)
        self._add_row(card, "月历卡片", self._switch_calendar)
        hint = QLabel("开启后月历常驻显示在主窗口下方", self._body)
        hint.setObjectName("captionLabel")
        hint.setContentsMargins(C.ROW_PADDING_X, 0, C.ROW_PADDING_X, 10)
        hint.setWordWrap(True)
        card.addWidget(hint)
        self._trim_separator(card)

    # ------------------------------------------------------------ 分组：系统
    def _build_system(self, content: QVBoxLayout) -> None:
        card = self._add_section(content, "系统")
        self._switch_autostart = IosSwitch(self._body, self._theme)
        self._add_row(card, "开机自启", self._switch_autostart)

        self._autostart_note = QLabel("", self._body)
        self._autostart_note.setObjectName("captionLabel")
        self._autostart_note.setContentsMargins(C.ROW_PADDING_X, 0, C.ROW_PADDING_X, 8)
        self._autostart_note.setWordWrap(True)
        self._autostart_note.setVisible(False)
        card.addWidget(self._autostart_note)

        version = QLabel(C.APP_VERSION, self._body)
        version.setObjectName("valueLabel")
        self._add_row(card, "版本号", version)

        self._quit_button = self._make_button("退出应用", "secondaryButton", self._body)
        self._add_row(card, "退出", self._quit_button)
        self._trim_separator(card)

    # ------------------------------------------------------------ 行构建
    def _add_section(self, content: QVBoxLayout, title: str) -> QVBoxLayout:
        header = QLabel(title)
        header.setObjectName("sectionTitle")
        content.addWidget(header)

        card = QFrame()
        card.setObjectName("rowCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 2, 0, 2)
        card_layout.setSpacing(0)
        content.addWidget(card)
        return card_layout

    def _add_row(self, card_layout: QVBoxLayout, label: str | None, control: QWidget) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(C.ROW_PADDING_X, C.ROW_PADDING_Y, C.ROW_PADDING_X, C.ROW_PADDING_Y)
        row_layout.setSpacing(10)
        row.setMinimumHeight(C.ROW_HEIGHT)
        if label:
            text = QLabel(label, row)
            text.setObjectName("rowLabel")
            row_layout.addWidget(text)
            row_layout.addStretch(1)
        row_layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(row)
        self._add_separator(card_layout)
        return row

    def _add_slider_row(
        self,
        card_layout: QVBoxLayout,
        label: str,
        slider: IosSlider,
        formatter,
    ) -> QWidget:
        holder = QWidget()
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(8)
        slider.setFixedWidth(120)
        value = QLabel(formatter(slider.value()))
        value.setObjectName("valueLabel")
        value.setFixedWidth(C.SLIDER_VALUE_WIDTH)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        holder_layout.addWidget(slider)
        holder_layout.addWidget(value)
        slider.valueChanged.connect(lambda v: value.setText(formatter(v)))
        return self._add_row(card_layout, label, holder)

    def _add_separator(self, card_layout: QVBoxLayout) -> None:
        holder = QWidget()
        holder.setObjectName("rowSeparator")
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(C.ROW_PADDING_X, 0, 0, 0)
        holder_layout.setSpacing(0)
        line = QFrame(holder)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {T.rgba(self._theme.tokens()['separator'], 190)};")
        holder_layout.addWidget(line)
        card_layout.addWidget(holder)

    @staticmethod
    def _trim_separator(card_layout: QVBoxLayout) -> None:
        if card_layout.count() == 0:
            return
        item = card_layout.itemAt(card_layout.count() - 1)
        widget = item.widget() if item is not None else None
        if widget is not None and widget.objectName() == "rowSeparator":
            card_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

    def _make_button(self, text: str, object_name: str, parent: QWidget) -> QPushButton:
        button = QPushButton(text, parent)
        button.setObjectName(object_name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _make_button_group(self, buttons: tuple[QPushButton, ...]) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for button in buttons:
            layout.addWidget(button)
        return holder

    # ------------------------------------------------------------ 信号
    def _wire(self) -> None:
        self._seg_appearance.current_changed.connect(
            lambda index: self.setting_changed.emit("appearance_mode", C.APPEARANCE_MODES[index])
        )
        self._slider_text_opacity.valueChanged.connect(
            lambda value: self.setting_changed.emit("text_opacity", value / 100.0)
        )
        self._slider_font.valueChanged.connect(
            lambda value: self.setting_changed.emit("font_size", int(value))
        )
        self._switch_background.toggled.connect(
            lambda checked: self.setting_changed.emit("background_enabled", bool(checked))
        )
        self._slider_bg_opacity.valueChanged.connect(
            lambda value: self.setting_changed.emit("background_opacity", value / 100.0)
        )
        self._switch_wheel.toggled.connect(
            lambda checked: self.setting_changed.emit("wheel_zoom", bool(checked))
        )

        self._switch_date.toggled.connect(
            lambda checked: self.setting_changed.emit("show_date", bool(checked))
        )
        self._switch_weather.toggled.connect(
            lambda checked: self.setting_changed.emit("show_weather", bool(checked))
        )
        self._seg_mode.current_changed.connect(self._on_mode_selected)

        self._switch_topmost.toggled.connect(
            lambda checked: self.setting_changed.emit("always_on_top", bool(checked))
        )

        self._switch_timers.toggled.connect(
            lambda checked: self.setting_changed.emit("timers_enabled", bool(checked))
        )
        self._spin_minutes.valueChanged.connect(
            lambda value: self.setting_changed.emit("countdown_minutes", int(value))
        )
        self._spin_seconds.valueChanged.connect(
            lambda value: self.setting_changed.emit("countdown_seconds", int(value))
        )
        self._btn_cd_start.clicked.connect(lambda: self.countdown_action.emit("start"))
        self._btn_cd_pause.clicked.connect(lambda: self.countdown_action.emit("pause"))
        self._btn_cd_reset.clicked.connect(lambda: self.countdown_action.emit("reset"))
        self._btn_sw_start.clicked.connect(lambda: self.stopwatch_action.emit("start"))
        self._btn_sw_pause.clicked.connect(lambda: self.stopwatch_action.emit("pause"))
        self._btn_sw_reset.clicked.connect(lambda: self.stopwatch_action.emit("reset"))

        self._apply_city_button.clicked.connect(self._apply_city)
        self._city_edit.returnPressed.connect(self._apply_city)
        self._refresh_weather_button.clicked.connect(self.weather_refresh_requested.emit)

        self._switch_calendar.toggled.connect(
            lambda checked: self.setting_changed.emit("calendar_enabled", bool(checked))
        )
        self._switch_autostart.toggled.connect(
            lambda checked: self.setting_changed.emit("autostart", bool(checked))
        )
        self._quit_button.clicked.connect(self.quit_requested.emit)
        self._close_button.clicked.connect(self.hide_panel)

    def _on_mode_selected(self, index: int) -> None:
        if 0 <= index < len(MODE_ORDER):
            self.setting_changed.emit("display_mode", MODE_ORDER[index])

    def _apply_city(self) -> None:
        self.weather_city_applied.emit(self._city_edit.text().strip())

    # ------------------------------------------------------------ 色盘
    def open_color_picker(self) -> None:
        text = self._settings.data.clock_color
        current = QColor(text) if text else self._theme.color("text")
        picker = IosColorPicker(self._theme, current, self)
        picker.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        picker.color_changed.connect(self._on_clock_color_picked)
        picker.reset_requested.connect(lambda: self._on_clock_color_reset())

        anchor = self._clock_color_swatch
        top_left = anchor.mapToGlobal(QPoint(0, 0))
        pos = QPoint(top_left.x() + anchor.width() - picker.WIDTH + 6, top_left.y() + anchor.height() + 8)
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            if pos.x() + picker.WIDTH > area.right():
                pos.setX(area.right() - picker.WIDTH)
            if pos.y() + picker.HEIGHT > area.bottom():
                pos.setY(top_left.y() - picker.HEIGHT - 8)
            pos.setX(max(area.left(), pos.x()))
            pos.setY(max(area.top(), pos.y()))
        picker.move(pos)
        picker.show()

    def _on_clock_color_picked(self, color: QColor) -> None:
        self._clock_color_swatch.set_color(color, automatic=False)
        self.setting_changed.emit("clock_color", color.name())

    def _on_clock_color_reset(self) -> None:
        self._clock_color_swatch.set_color(self._theme.color("text"), automatic=True)
        self.setting_changed.emit("clock_color", "")

    # ------------------------------------------------------------ 字体
    def open_font_picker(self) -> None:
        picker = FontPickerPanel(self._theme, self._settings.data.clock_font, self)
        picker.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        picker.font_selected.connect(self._on_font_selected)

        anchor = self._font_button
        top_left = anchor.mapToGlobal(QPoint(0, 0))
        pos = QPoint(top_left.x() + anchor.width() - picker.width(), top_left.y() + anchor.height() + 8)
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            if pos.x() < area.left():
                pos.setX(area.left())
            if pos.x() + picker.width() > area.right():
                pos.setX(area.right() - picker.width())
            if pos.y() + picker.height() > area.bottom():
                pos.setY(top_left.y() - picker.height() - 8)
            pos.setY(max(area.top(), pos.y()))
        picker.move(pos)
        picker.show()

    def _on_font_selected(self, family: str) -> None:
        label = next(
            (name for name, value in C.CLOCK_FONT_OPTIONS if value == family), "默认"
        )
        self._font_button.setText(label)
        self.setting_changed.emit("clock_font", family)

    # ------------------------------------------------------------ 状态同步
    def sync_from_settings(self) -> None:
        data = self._settings.data
        self._seg_appearance.set_current(C.APPEARANCE_MODES.index(data.appearance_mode), emit=False)
        custom_color = data.clock_color
        self._clock_color_swatch.set_color(
            QColor(custom_color) if custom_color else None, automatic=not custom_color
        )
        font_label = next(
            (name for name, value in C.CLOCK_FONT_OPTIONS if value == data.clock_font), "默认"
        )
        self._font_button.setText(font_label)
        self._slider_text_opacity.setValue(int(round(data.text_opacity * 100)))
        self._slider_font.setValue(int(data.font_size))
        self._switch_background.set_checked_silently(data.background_enabled)
        self._slider_bg_opacity.setValue(int(round(data.background_opacity * 100)))
        self._switch_wheel.set_checked_silently(data.wheel_zoom)

        self._switch_date.set_checked_silently(data.show_date)
        self._switch_weather.set_checked_silently(data.show_weather)
        self._sync_mode_segment()

        self._switch_topmost.set_checked_silently(data.always_on_top)

        self._switch_timers.set_checked_silently(data.timers_enabled)
        self._spin_minutes.setValue(int(data.countdown_minutes))
        self._spin_seconds.setValue(int(data.countdown_seconds))
        self._set_timers_ui_enabled(data.timers_enabled)

        if not self._city_edit.hasFocus():
            self._city_edit.setText(data.weather_city)

        self._switch_calendar.set_checked_silently(data.calendar_enabled)
        self._switch_autostart.set_checked_silently(bool(data.autostart))

    def _sync_mode_segment(self) -> None:
        data = self._settings.data
        enabled = data.timers_enabled
        labels = list(MODE_LABELS) if enabled else [MODE_LABELS[0]]
        self._seg_mode.set_options(labels)
        try:
            index = MODE_ORDER.index(data.display_mode)
        except ValueError:
            index = 0
        if not enabled:
            index = 0
        self._seg_mode.set_current(min(index, len(labels) - 1), emit=False)

    def _set_timers_ui_enabled(self, enabled: bool) -> None:
        for widget in (
            self._seg_mode,
            self._btn_cd_start,
            self._btn_cd_pause,
            self._btn_cd_reset,
            self._btn_sw_start,
            self._btn_sw_pause,
            self._btn_sw_reset,
        ):
            widget.setEnabled(enabled)

    def set_mode_index(self, mode: str) -> None:
        try:
            index = MODE_ORDER.index(mode)
        except ValueError:
            index = 0
        self._seg_mode.set_current(index, emit=False)

    def update_weather_info(self, status: str, resolved: str, updated: str, description: str) -> None:
        self._weather_city_label.setText(resolved)
        self._weather_status_label.setText(f"{status} · {description}" if description else status)
        self._weather_updated_label.setText(f"最后更新 {updated}")
        self._fit_height()

    def set_autostart_note(self, text: str) -> None:
        self._autostart_note.setText(text)
        self._autostart_note.setVisible(bool(text))
        self._fit_height()

    # ------------------------------------------------------------ 显示
    def _fit_height(self) -> None:
        container = self._scroll.widget()
        content_height = container.sizeHint().height() if container is not None else 600
        screen = QGuiApplication.primaryScreen()
        screen_limit = screen.availableGeometry().height() - 80 if screen is not None else C.PANEL_MAX_HEIGHT
        max_height = max(420, min(C.PANEL_MAX_HEIGHT, screen_limit))
        height = content_height + C.PANEL_TITLE_HEIGHT + 2 * C.PANEL_SHADOW_MARGIN + 10
        height = max(320, min(max_height, height))
        self.setFixedSize(C.PANEL_WIDTH, height)

    def show_near(self, anchor: QRect) -> None:
        self._fit_height()
        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 800)
        x = anchor.right() + 14
        if x + self.width() > area.right():
            x = anchor.left() - self.width() - 14
        x = max(area.left(), min(area.right() - self.width(), x))
        y = anchor.top() + (anchor.height() - self.height()) // 2
        y = max(area.top(), min(area.bottom() - self.height(), y))
        self.move(x, y)
        self._fading_out = False
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self._run_fade(1.0)

    def _run_fade(self, target: float) -> None:
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(target)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        if self._fading_out:
            self._fading_out = False
            self.hide()
            self.setWindowOpacity(1.0)

    def toggle_near(self, anchor: QRect) -> None:
        if self.isVisible() and not self._fading_out:
            self.hide_panel()
        else:
            self.show_near(anchor)

    def hide_panel(self) -> None:
        if self.isVisible():
            self._fading_out = True
            self._run_fade(0.0)
        self.closed.emit()

    def set_always_on_top(self, enabled: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        if self.isVisible():
            self.show()

    def _on_theme_changed(self) -> None:
        separator_style = f"background: {T.rgba(self._theme.tokens()['separator'], 190)};"
        for holder in self.findChildren(QWidget, "rowSeparator"):
            line = holder.findChild(QFrame)
            if line is not None:
                line.setStyleSheet(separator_style)
        self.update()

    # ------------------------------------------------------------ 拖动
    def eventFilter(self, obj, event) -> bool:
        if obj is self._title_bar:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = event_global_pos(event) - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_offset is not None:
                self.move(event_global_pos(event) - self._drag_offset)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_offset = None
                return True
        return super().eventFilter(obj, event)
