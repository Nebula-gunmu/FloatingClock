"""全局常量：应用元信息、字体、尺寸、主题色板、天气代码映射与路径工具。

设计约束：所有魔法数字/颜色集中在本模块，其它模块只引用常量，不得散落字面量。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------- 应用元信息
APP_NAME = "FloatingClock"
APP_DISPLAY_NAME = "悬浮时钟"
APP_VERSION = "1.0.0"
ORG_NAME = "FloatingClock"

# ---------------------------------------------------------------- 开机自启
AUTOSTART_VALUE_NAME = "FloatingClock"
AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

# ---------------------------------------------------------------- 字体
FONT_DISPLAY = ["Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI"]
FONT_TEXT = ["Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI"]
FONT_CJK = ["Microsoft YaHei UI Light", "Microsoft YaHei UI"]
FONT_EMOJI = ["Segoe UI Emoji"]
FONT_GEAR = ["Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI"]

CLOCK_FONT_MIN = 60
CLOCK_FONT_MAX = 300
CLOCK_FONT_DEFAULT = 132
CLOCK_FONT_WHEEL_RATIO = 0.05
CLOCK_FONT_MIN_STEP = 4

SUBLINE_RATIO = 0.16
SUBLINE_MIN_PX = 12
SUBLINE_MAX_PX = 40

PANEL_FONT_PX = 14
PANEL_TITLE_PX = 17
SECTION_TITLE_PX = 12
CAPTION_FONT_PX = 12
BUTTON_FONT_PX = 13

# ---------------------------------------------------------------- 尺寸
WINDOW_RADIUS = 26
CARD_RADIUS = 20
PANEL_RADIUS = 24
PANEL_WIDTH = 384
PANEL_MAX_HEIGHT = 780
PANEL_SHADOW_MARGIN = 18
PANEL_CONTENT_MARGIN = 16
PANEL_TITLE_HEIGHT = 46

CONTENT_MARGIN_X = 30
CONTENT_MARGIN_TOP = 22
CONTENT_MARGIN_BOTTOM = 26
CLOCK_CONTENT_SPACING = 2
GEAR_SIZE = 30
GEAR_MARGIN = 10
GEAR_FONT_PX = 16

ROW_HEIGHT = 48
ROW_MIN_HEIGHT_SLIDER = 54
ROW_PADDING_X = 16
ROW_PADDING_Y = 6
CARD_INNER_RADIUS = 16
SECTION_SPACING = 8
SECTION_GAP = 20

SWITCH_WIDTH = 52
SWITCH_HEIGHT = 32
SWITCH_KNOB_MARGIN = 2

SEGMENT_HEIGHT = 34
SEGMENT_PADDING = 3
SEGMENT_FONT_PX = 13

SLIDER_HEIGHT = 28
SLIDER_TRACK_HEIGHT = 4
SLIDER_HANDLE_RADIUS = 9
SLIDER_HANDLE_RADIUS_HOVER = 12
SLIDER_VALUE_WIDTH = 44

# 日历卡片
CALENDAR_WIDTH = 320
CAL_HEADER_H = 44
CAL_WEEKDAY_H = 22
CAL_CELL_H = 34
CAL_ROWS = 6
CAL_FOOTER_H = 38
CAL_GRID_INSET = 12
CAL_DAY_FONT_PX = 13
CAL_TITLE_FONT_PX = 15
CAL_ARROW_SIZE = 26
CAL_ARROW_GAP = 6
CAL_TODAY_W = 58
CAL_TODAY_H = 24
CALENDAR_TOP_MARGIN = 10

# ---------------------------------------------------------------- 动效
ANIM_FAST = 140
ANIM_NORMAL = 170
HOVER_HIDE_DELAY_MS = 260

# 置顶重申间隔：定时把窗口重新提到 topmost 组最前，避免被其它置顶窗口压住
TOPMOST_REASSERT_MS = 2500
TOPMOST_SETTLE_MS = 160

# Qt5（Windows 7）没有系统明暗模式信号，改用轮询
SYSTEM_THEME_POLL_MS = 4000

# ---------------------------------------------------------------- 颜色
ACCENT_LIGHT = "#0A84FF"
ACCENT_DARK = "#409CFF"
COLOR_SUCCESS = "#30D158"
COLOR_DANGER = "#FF453A"

TOKENS: dict[str, dict[str, str]] = {
    "light": {
        "accent": ACCENT_LIGHT,
        "text": "#111114",
        "text_secondary": "#6B6B70",
        "text_tertiary": "#B9B9BE",
        "card": "#FFFFFF",
        "card_alt": "#F2F2F7",
        "panel_bg": "#EDEDF2",
        "row_hover": "#F2F2F7",
        "track": "#E5E5EA",
        "switch_off": "#E9E9EB",
        "segment_track": "#EFEFF4",
        "segment_thumb": "#FFFFFF",
        "segment_text": "#6C6C70",
        "separator": "#D2D2D8",
        "acrylic_tint": "#FFFFFF",
        "scroll_handle": "#C7C7CC",
        "gear_bg": "#F0F0F2",
        "shadow": "#000000",
    },
    "dark": {
        "accent": ACCENT_DARK,
        "text": "#FFFFFF",
        "text_secondary": "#B4B4BA",
        "text_tertiary": "#5C5C61",
        "card": "#1C1C1E",
        "card_alt": "#2C2C2E",
        "panel_bg": "#141416",
        "row_hover": "#2C2C2E",
        "track": "#3A3A3C",
        "switch_off": "#39393D",
        "segment_track": "#2C2C2E",
        "segment_thumb": "#636366",
        "segment_text": "#C7C7CC",
        "separator": "#3A3A3C",
        "acrylic_tint": "#000000",
        "scroll_handle": "#48484A",
        "gear_bg": "#2C2C2E",
        "shadow": "#000000",
    },
}

APPEARANCE_MODES = ("system", "light", "dark")

# ---------------------------------------------------------------- 天气
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_REFRESH_MS = 30 * 60 * 1000
WEATHER_TIMEOUT_MS = 8000
WEATHER_OFFLINE_SUFFIX = " · 离线"
WEATHER_EMPTY_SUMMARY = "--°"
WEATHER_USER_AGENT = f"{APP_NAME}/{APP_VERSION} (Windows desktop clock)"

# WMO weather_code -> (符号, 中文描述)
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("☀️", "晴"),
    1: ("🌤️", "大部晴朗"),
    2: ("⛅", "多云"),
    3: ("☁️", "阴"),
    45: ("🌫️", "雾"),
    48: ("🌫️", "雾凇"),
    51: ("🌦️", "小毛毛雨"),
    53: ("🌦️", "毛毛雨"),
    55: ("🌧️", "强毛毛雨"),
    56: ("🌧️", "冻毛毛雨"),
    57: ("🌧️", "强冻毛毛雨"),
    61: ("🌦️", "小雨"),
    63: ("🌧️", "中雨"),
    65: ("🌧️", "大雨"),
    66: ("🌧️", "冻雨"),
    67: ("🌧️", "强冻雨"),
    71: ("🌨️", "小雪"),
    73: ("🌨️", "中雪"),
    75: ("❄️", "大雪"),
    77: ("❄️", "米雪"),
    80: ("🌦️", "小阵雨"),
    81: ("🌧️", "阵雨"),
    82: ("⛈️", "强阵雨"),
    85: ("🌨️", "小阵雪"),
    86: ("❄️", "大阵雪"),
    95: ("⛈️", "雷阵雨"),
    96: ("⛈️", "雷阵雨伴冰雹"),
    99: ("⛈️", "强雷阵雨伴冰雹"),
}
WMO_UNKNOWN = ("☁️", "未知")


# ---------------------------------------------------------------- 路径工具
def config_dir() -> Path:
    """用户配置目录（%APPDATA%/FloatingClock）。"""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def settings_file() -> Path:
    return config_dir() / "settings.json"


def weather_cache_file() -> Path:
    return config_dir() / "weather_cache.json"


def resource_dir() -> Path:
    """资源目录：打包后位于 _MEIPASS/resources，开发时位于项目根/resources。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / "resources"
    return Path(__file__).resolve().parent.parent / "resources"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

# 色盘预设（iOS 系统色 + 黑白灰）
PRESET_COLORS = (
    "#000000", "#3A3A3C", "#8E8E93", "#FFFFFF",
    "#FF3B30", "#FF9500", "#FFCC00", "#34C759",
    "#00C7BE", "#0A84FF", "#5856D6", "#FF2D55",
)

# 时钟数字颜色：空字符串 = 跟随主题
CLOCK_COLOR_AUTO = ""

# 时钟字体候选：只收录 Windows 10/11 普遍自带的字体，避免换一台电脑就变成默认字体；
# 每个选项在 theme.clock_font 里还会拼上 FONT_DISPLAY 作为回退链，
# 即使目标机器缺该字体也能正常显示（Qt 自动回退，不会花屏或报错）。
CLOCK_FONT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("默认", ""),
    ("Segoe UI", "Segoe UI"),
    ("Bahnschrift", "Bahnschrift"),
    ("Consolas", "Consolas"),
    ("Arial", "Arial"),
    ("Tahoma", "Tahoma"),
    ("Verdana", "Verdana"),
    ("Trebuchet MS", "Trebuchet MS"),
)

# 字体列表里每一项的预览文字
FONT_PREVIEW_TEXT = "12:34"
