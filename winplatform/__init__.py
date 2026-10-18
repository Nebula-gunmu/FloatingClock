"""Windows 平台相关能力包。

说明：提示词中建议的 ``platform/win_effects.py`` 与 Python 标准库 ``platform``
同名，会让 PyInstaller 与第三方库导入到错误模块，因此实际命名为
``winplatform``，职责完全一致：ctypes 封装、失败降级。
"""

from . import win_effects

__all__ = ["win_effects"]
