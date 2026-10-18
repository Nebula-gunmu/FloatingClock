"""开机自启：读写 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run。

约束：
- 只写当前用户注册表，不要求管理员权限，不使用计划任务/服务；
- 打包环境使用 sys.executable 作为 exe 绝对路径并加引号；
- 开发环境拒绝写入（避免把 python.exe 写进注册表），由界面提示"打包后生效"。
"""

from __future__ import annotations

import sys
from pathlib import Path

from app import constants as C

try:  # 非 Windows 平台或裁剪环境优雅降级
    import winreg
except ImportError:  # pragma: no cover
    winreg = None


def is_supported() -> bool:
    return winreg is not None and sys.platform == "win32"


def executable_path() -> str:
    """自启时应当执行的 exe 绝对路径。"""
    return str(Path(sys.executable).resolve())


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, C.AUTOSTART_REG_PATH) as key:
            winreg.QueryValueEx(key, C.AUTOSTART_VALUE_NAME)
        return True
    except (FileNotFoundError, OSError):
        return False


def enable() -> bool:
    if not is_supported() or not C.is_frozen():
        return False
    command = f'"{executable_path()}"'
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, C.AUTOSTART_REG_PATH) as key:
            winreg.SetValueEx(key, C.AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, command)
        return is_enabled()
    except OSError:
        return False


def disable() -> bool:
    if not is_supported():
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, C.AUTOSTART_REG_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, C.AUTOSTART_VALUE_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def apply(enabled: bool) -> tuple[bool, str]:
    """应用自启开关，返回 (是否成功, 需要提示给用户的文案)。"""
    if not is_supported():
        return False, "当前系统不支持注册表自启"
    if not C.is_frozen():
        return False, "开发环境不写入注册表，打包后才生效"
    if enabled:
        ok = enable()
        return ok, ("已设置开机自启" if ok else "写入注册表失败，可能被安全软件拦截")
    ok = disable()
    return ok, ("已取消开机自启" if ok else "删除注册表值失败，可能被安全软件拦截")
