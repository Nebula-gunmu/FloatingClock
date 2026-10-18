"""应用协调器：把设置、主题、模式、天气与两个窗口连接起来。

界面类只负责显示与输入事件，所有设置写入与副作用（自启、天气、置顶、主题）
都在本类中统一处理。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from app import constants as C
from app.settings_model import SettingsStore
from app.theme import ThemeManager
from core.time_modes import ModeController
from services import autostart_service
from services.weather_service import WeatherService
from ui.main_clock_window import MainClockWindow
from ui.settings_panel import SettingsPanel


class AppController(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._suppress_autostart = False

        self.settings = SettingsStore()
        self.theme = ThemeManager(app)
        self.modes = ModeController(self.settings)
        self.weather = WeatherService(self.settings)
        self.main_window = MainClockWindow(self.settings, self.theme)
        self.panel = SettingsPanel(self.settings, self.theme, self.modes)

        self._connect()
        self.panel.set_always_on_top(self.settings.data.always_on_top)

    # ------------------------------------------------------------ 启动
    def start(self) -> None:
        self.theme.set_mode(self.settings.data.appearance_mode)
        self.main_window.apply_settings()
        self.main_window.restore_position()
        self.main_window.show()

        self.modes.refresh()
        self.main_window.set_display_text(self.modes.text)
        self.main_window.set_weather_summary(self.weather.summary())

        self._sync_autostart()
        self.weather.start()
        self._update_weather_panel()

        if self.settings.first_run:
            QTimer.singleShot(80, self._open_panel)

    # ------------------------------------------------------------ 连接
    def _connect(self) -> None:
        self.settings.changed.connect(self._on_setting_changed)

        self.modes.display_changed.connect(self.main_window.set_display_text)
        self.modes.template_changed.connect(self.main_window.set_template)
        self.modes.mode_changed.connect(self._on_mode_changed)

        self.main_window.gear_clicked.connect(self._open_panel)
        self.main_window.zoom_requested.connect(self._on_zoom_requested)
        self.main_window.position_changed.connect(self._on_position_changed)

        self.panel.setting_changed.connect(self.settings.set)
        self.panel.countdown_action.connect(self.modes.countdown_action)
        self.panel.stopwatch_action.connect(self.modes.stopwatch_action)
        self.panel.weather_city_applied.connect(self.weather.set_city)
        self.panel.weather_refresh_requested.connect(self.weather.refresh)
        self.panel.quit_requested.connect(self.quit)

        self.weather.updated.connect(self._on_weather_updated)
        self.weather.status_changed.connect(self._update_weather_panel)

    # ------------------------------------------------------------ 设置分发
    def _on_setting_changed(self, key: str, value) -> None:
        if key == "appearance_mode":
            self.theme.set_mode(str(value))
            return
        if key == "display_mode":
            self.modes.set_mode(str(value))
            return
        if key == "always_on_top":
            self.main_window.set_topmost(bool(value))
            self.panel.set_always_on_top(bool(value))
            return
        if key == "timers_enabled":
            self.modes.set_timers_enabled(bool(value))
            self.panel.sync_from_settings()
            return
        if key in ("countdown_minutes", "countdown_seconds"):
            self.modes.set_countdown_duration(
                self.settings.data.countdown_minutes, self.settings.data.countdown_seconds
            )
            return
        if key == "show_weather":
            self.weather.set_enabled(bool(value))
            self.main_window.set_weather_summary(self.weather.summary())
            self._update_weather_panel()
            return
        if key == "autostart":
            if self._suppress_autostart:
                return
            self._apply_autostart(bool(value))
            return
        if key == "weather_city":
            return
        if key in ("window_x", "window_y"):
            return
        if key == "clock_color":
            self.main_window.apply_clock_color()
            return
        if key == "clock_font":
            self.main_window.apply_clock_font()
            return
        if key == "text_opacity":
            self.main_window.apply_text_opacity()
            return

        # 其余均为纯显示项：交给主窗口统一套用
        self.main_window.apply_settings()
        if key == "font_size":
            self.panel.sync_from_settings()

    # ------------------------------------------------------------ 模式
    def _on_mode_changed(self, mode: str) -> None:
        self.settings.set("display_mode", mode)
        self.panel.set_mode_index(mode)

    # ------------------------------------------------------------ 交互
    def _open_panel(self) -> None:
        self.panel.toggle_near(self.main_window.frameGeometry())

    def _on_zoom_requested(self, direction: int) -> None:
        if not self.settings.data.wheel_zoom:
            return
        current = int(self.settings.data.font_size)
        step = max(C.CLOCK_FONT_MIN_STEP, int(round(current * C.CLOCK_FONT_WHEEL_RATIO)))
        self.settings.set("font_size", current + direction * step)

    def _on_position_changed(self, x: int, y: int) -> None:
        self.settings.set("window_x", int(x))
        self.settings.set("window_y", int(y))

    # ------------------------------------------------------------ 天气
    def _on_weather_updated(self) -> None:
        self.main_window.set_weather_summary(self.weather.summary())
        self._update_weather_panel()

    def _update_weather_panel(self) -> None:
        self.panel.update_weather_info(
            self.weather.status_text(),
            self.weather.resolved_text(),
            self.weather.last_updated_text(),
            self.weather.description(),
        )

    # ------------------------------------------------------------ 自启
    def _sync_autostart(self) -> None:
        actual = autostart_service.is_enabled() if C.is_frozen() else False
        self._suppress_autostart = True
        try:
            self.settings.set("autostart", actual)
        finally:
            self._suppress_autostart = False
        self.panel.sync_from_settings()
        if C.is_frozen():
            self.panel.set_autostart_note("")
        else:
            self.panel.set_autostart_note("开发环境不写入注册表，打包后才生效")

    def _apply_autostart(self, enabled: bool) -> None:
        ok, note = autostart_service.apply(enabled)
        self.panel.set_autostart_note(note)
        if C.is_frozen() and not ok:
            actual = autostart_service.is_enabled()
            self._suppress_autostart = True
            try:
                self.settings.set("autostart", actual)
            finally:
                self._suppress_autostart = False
            self.panel.sync_from_settings()

    # ------------------------------------------------------------ 退出
    def quit(self) -> None:
        self.settings.set("window_x", self.main_window.x())
        self.settings.set("window_y", self.main_window.y())
        self.settings.save()
        self.weather.stop()
        self.modes.stop()
        self.panel.hide()
        self.main_window.hide()
        self._app.quit()
