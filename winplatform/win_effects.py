"""Windows 原生视窗能力封装：磨砂背景、置顶、圆角。

磨砂背景有两条实现路径：
1. 首选老式亚克力（SetWindowCompositionAttribute + ACCENT_ENABLE_ACRYLICBLURBEHIND）：
   能模糊窗口背后的**真实内容**，并随窗口移动实时更新；磨砂区域是矩形。
   注意 AccentFlags 必须为 0 —— Windows 11 上 flags=2 虽然返回成功，
   但会把整个窗口渲染成不透明黑块。
2. 亚克力不可用时，Windows 11 退回 DWM 系统 backdrop（DWMWA_SYSTEMBACKDROP_TYPE），
   它带原生圆角，但只采样桌面壁纸。

任何一步失败都只返回 None/False，由上层降级为 Qt 自绘的半透明圆角纯色背景，
绝不允许抛异常或残留黑底。
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"

# AccentState
ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19

# SetWindowPos
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200

# DWM window attributes
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMWCP_DEFAULT = 0
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2

DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2
DWMSBT_TRANSIENTWINDOW = 3
DWMSBT_TABBEDWINDOW = 4

# 背景模式
BLUR_NONE = "none"
BLUR_SYSTEM = "system"
BLUR_ACCENT = "accent"
BLUR_AERO = "aero"

WIN11_BUILD = 22000
WIN8_BUILD = 8000

DWM_BB_ENABLE = 0x00000001


class _DwmBlurBehind(ctypes.Structure):
    _fields_ = [
        ("dwFlags", wintypes.DWORD),
        ("fEnable", wintypes.BOOL),
        ("hRgnBlur", wintypes.HRGN),
        ("fTransitionOnMaximized", wintypes.BOOL),
    ]


class _AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class _WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


class _Margins(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


def is_supported() -> bool:
    return IS_WINDOWS


def windows_build() -> int:
    try:
        return int(sys.getwindowsversion().build)
    except (AttributeError, ValueError):
        return 0


def is_win11() -> bool:
    return IS_WINDOWS and windows_build() >= WIN11_BUILD


def _user32():
    return ctypes.windll.user32


def _dwmapi():
    return ctypes.windll.dwmapi


# ---------------------------------------------------------------- 底层调用
def _set_composition_attribute(hwnd: int, data: _WindowCompositionAttributeData) -> bool:
    try:
        fn = getattr(_user32(), "SetWindowCompositionAttribute", None)
        if fn is None:  # Windows 7/8 没有该导出
            return False
        fn.argtypes = [wintypes.HWND, ctypes.POINTER(_WindowCompositionAttributeData)]
        fn.restype = wintypes.BOOL
        return bool(fn(wintypes.HWND(hwnd), ctypes.byref(data)))
    except (OSError, AttributeError, ValueError):
        return False


def _accent_policy(hwnd: int, state: int, gradient: int) -> bool:
    policy = _AccentPolicy(state, 0, gradient, 0)
    data = _WindowCompositionAttributeData(
        WCA_ACCENT_POLICY,
        ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p),
        ctypes.sizeof(policy),
    )
    return _set_composition_attribute(hwnd, data)


def _dwm_set_int(hwnd: int, attribute: int, value: int) -> bool:
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        number = ctypes.c_int(value)
        result = _dwmapi().DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            ctypes.c_uint(attribute),
            ctypes.byref(number),
            ctypes.sizeof(number),
        )
        return result == 0
    except (OSError, AttributeError, ValueError):
        return False


def _extend_frame_into_client(hwnd: int, enabled: bool) -> bool:
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        size = -1 if enabled else 0
        margins = _Margins(size, size, size, size)
        result = _dwmapi().DwmExtendFrameIntoClientArea(
            wintypes.HWND(hwnd), ctypes.byref(margins)
        )
        return result == 0
    except (OSError, AttributeError, ValueError):
        return False


# ---------------------------------------------------------------- 对外接口
def _aero_blur(hwnd: int, enabled: bool) -> bool:
    """Windows 7 的 Aero 玻璃（Win8 之后该效果被移除）。"""
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        data = _DwmBlurBehind(DWM_BB_ENABLE if enabled else 0, bool(enabled), None, False)
        result = _dwmapi().DwmEnableBlurBehindWindow(
            wintypes.HWND(hwnd), ctypes.byref(data)
        )
        return result == 0
    except (OSError, AttributeError, ValueError):
        return False


def enable_background(hwnd: int, tint: tuple[int, int, int], alpha: int) -> str:
    """开启背景，返回实际生效的方式：BLUR_ACCENT / BLUR_AERO / BLUR_SYSTEM / BLUR_NONE。

    优先使用老式亚克力（AccentPolicy）：它能模糊窗口背后的**真实内容**，
    并且随窗口移动实时更新（拖动时背景自然跟手），代价是磨砂区域为矩形。
    Windows 7 没有亚克力，改用 Aero 玻璃；Windows 11 的 system backdrop
    只在前面都不可用时兜底（它带原生圆角，但只采样桌面壁纸）。
    """
    if not IS_WINDOWS or not hwnd:
        return BLUR_NONE
    alpha = max(0, min(255, int(alpha)))
    red, green, blue = (max(0, min(255, int(v))) for v in tint)
    # GradientColor 的字节序为 0xAABBGGRR
    gradient = (alpha << 24) | (blue << 16) | (green << 8) | red

    build = windows_build()
    if 0 < build < WIN8_BUILD:
        if _aero_blur(hwnd, True):
            return BLUR_AERO

    for state in (ACCENT_ENABLE_ACRYLICBLURBEHIND, ACCENT_ENABLE_BLURBEHIND):
        if _accent_policy(hwnd, state, gradient):
            return BLUR_ACCENT

    if build >= WIN11_BUILD:
        if _extend_frame_into_client(hwnd, True) and _dwm_set_int(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_TRANSIENTWINDOW
        ):
            _dwm_set_int(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)
            return BLUR_SYSTEM
    return BLUR_NONE


def disable_background(hwnd: int) -> None:
    """关闭背景并复位所有相关属性，避免残留黑底或圆角裁剪。"""
    if not IS_WINDOWS or not hwnd:
        return
    _aero_blur(hwnd, False)
    _dwm_set_int(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_NONE)
    _extend_frame_into_client(hwnd, False)
    _accent_policy(hwnd, ACCENT_DISABLED, 0)


def set_acrylic(hwnd: int, tint: tuple[int, int, int], alpha: int) -> bool:
    """兼容旧接口：仅使用老式亚克力方案，成功返回 True。"""
    if not IS_WINDOWS or not hwnd:
        return False
    alpha = max(0, min(255, int(alpha)))
    red, green, blue = (max(0, min(255, int(v))) for v in tint)
    gradient = (alpha << 24) | (blue << 16) | (green << 8) | red
    for state in (ACCENT_ENABLE_ACRYLICBLURBEHIND, ACCENT_ENABLE_BLURBEHIND):
        if _accent_policy(hwnd, state, gradient):
            return True
    return False


def disable_effects(hwnd: int) -> None:
    """兼容旧接口：关闭磨砂。"""
    disable_background(hwnd)


def set_rounded_corners(hwnd: int, enabled: bool = True) -> bool:
    """Windows 11：设置窗口圆角偏好。"""
    if not IS_WINDOWS or not hwnd:
        return False
    return _dwm_set_int(
        hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND if enabled else DWMWCP_DONOTROUND
    )


def set_topmost(hwnd: int, enabled: bool) -> bool:
    """Qt 置顶标志之外的第二道保险：Win32 SetWindowPos。

    不激活、不改尺寸位置地把窗口推到 topmost 组最前；
    上层会定时调用它，防止被别的置顶窗口长期压住。
    """
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        fn = _user32().SetWindowPos
        fn.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        fn.restype = wintypes.BOOL
        insert_after = HWND_TOPMOST if enabled else HWND_NOTOPMOST
        result = fn(
            wintypes.HWND(hwnd),
            wintypes.HWND(insert_after),
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER,
        )
        return bool(result)
    except (OSError, AttributeError, ValueError):
        return False
