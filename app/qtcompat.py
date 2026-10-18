"""Qt 绑定兼容层。

- Windows 10/11 走 PySide6（Qt 6）；
- Windows 7 只能走 PySide2（Qt 5.15，且需要 Python 3.8 运行时）。

本模块做两件事，让业务代码只写一套：

1. 在 PySide2 环境下把 ``PySide6.*`` 注册成别名，并且给 Qt5 的
   "旧式枚举"（Qt.FramelessWindowHint）套上 Qt6 的命名空间外壳
   （Qt.WindowType.FramelessWindowHint），这样两边写法完全一致；
2. 提供少量确实无法统一的小接口：鼠标事件坐标、系统明暗模式。
"""

from __future__ import annotations

import sys
import types

QT6 = False
HAS_QT = False

QtCore = None
QtGui = None
QtWidgets = None
QtNetwork = None
Qt = None


class _NamespaceProxy:
    """把 Qt.WindowType 这类命名空间转发到 Qt5 的扁平枚举成员。"""

    def __init__(self, owner, name: str) -> None:
        self._owner = owner
        self._name = name

    def __getattr__(self, item: str):
        try:
            return getattr(self._owner, item)
        except AttributeError as exc:
            raise AttributeError(f"{type(self._owner).__name__}.{self._name}.{item}") from exc


class _ClassProxy:
    """给某个 Qt 类补上命名空间写法，并保留实例化与其它属性。"""

    def __init__(self, cls, namespaces: tuple[str, ...]) -> None:
        self._cls = cls
        self._namespaces = namespaces

    def __getattr__(self, item: str):
        if item in self._namespaces:
            return _NamespaceProxy(self._cls, item)
        return getattr(self._cls, item)

    def __call__(self, *args, **kwargs):
        return self._cls(*args, **kwargs)


class _QtProxy:
    """Qt 命名空间代理：命名空间成员返回 _NamespaceProxy，其余原样转发。"""

    _NAMESPACES = frozenset(
        {
            "WindowType",
            "AlignmentFlag",
            "MouseButton",
            "PenStyle",
            "PenCapStyle",
            "PenJoinStyle",
            "BrushStyle",
            "CursorShape",
            "FocusPolicy",
            "ScrollBarPolicy",
            "TextFormat",
            "WidgetAttribute",
            "GlobalColor",
            "AspectRatioMode",
            "TransformationMode",
            "HighDpiScaleFactorRoundingPolicy",
            "ColorScheme",
            "ItemDataRole",
            "ContextMenuPolicy",
            "WindowState",
        }
    )

    def __init__(self, real) -> None:
        self._real = real

    def __getattr__(self, item: str):
        if item in self._NAMESPACES:
            return _NamespaceProxy(self._real, item)
        return getattr(self._real, item)


class _ModuleShim(types.ModuleType):
    """以 PySide2 的模块为底层，对外冒充 PySide6 的同名模块。"""

    def __init__(self, name: str, target, overrides: dict) -> None:
        super().__init__(name)
        self.__dict__["_target"] = target
        self.__dict__["_overrides"] = overrides
        for key in dir(target):
            if key.startswith("__"):
                continue
            try:
                self.__dict__[key] = getattr(target, key)
            except Exception:  # noqa: BLE001 - 个别属性访问会抛异常，跳过即可
                continue

    def __getattr__(self, item: str):
        overrides = self.__dict__["_overrides"]
        if item in overrides:
            return overrides[item]
        return getattr(self.__dict__["_target"], item)


def _install_pyside2_shims() -> None:
    """在 PySide2 环境里伪造 PySide6 模块树。"""
    import PySide2  # noqa: F401
    from PySide2 import QtCore as core
    from PySide2 import QtGui as gui
    from PySide2 import QtNetwork as net
    from PySide2 import QtWidgets as widgets

    qt_proxy = _QtProxy(core.Qt)

    overrides_core = {
        "Qt": qt_proxy,
        "QEvent": _ClassProxy(core.QEvent, ("Type",)),
        "QTimer": core.QTimer,
    }
    overrides_gui = {
        "QPainter": _ClassProxy(gui.QPainter, ("RenderHint",)),
        "QImage": _ClassProxy(gui.QImage, ("Format",)),
        "QFont": _ClassProxy(gui.QFont, ("Weight", "HintingPreference", "StyleStrategy")),
        "QPalette": _ClassProxy(gui.QPalette, ("ColorRole",)),
        "QIcon": gui.QIcon,
    }
    overrides_widgets = {
        "QSizePolicy": _ClassProxy(widgets.QSizePolicy, ("Policy",)),
        "QFrame": _ClassProxy(widgets.QFrame, ("Shape", "Shadow")),
    }
    overrides_net = {
        "QNetworkRequest": _ClassProxy(
            net.QNetworkRequest, ("KnownHeaders", "Attribute", "CacheLoadControl")
        ),
    }

    shims = {
        "PySide6": _ModuleShim("PySide6", PySide2, {}),
        "PySide6.QtCore": _ModuleShim("PySide6.QtCore", core, overrides_core),
        "PySide6.QtGui": _ModuleShim("PySide6.QtGui", gui, overrides_gui),
        "PySide6.QtWidgets": _ModuleShim("PySide6.QtWidgets", widgets, overrides_widgets),
        "PySide6.QtNetwork": _ModuleShim("PySide6.QtNetwork", net, overrides_net),
    }
    for name, module in shims.items():
        sys.modules[name] = module


def _bootstrap() -> None:
    global QT6, HAS_QT, QtCore, QtGui, QtWidgets, QtNetwork, Qt

    try:
        from PySide6 import QtCore as core_mod  # type: ignore
        from PySide6 import QtGui as gui_mod  # type: ignore
        from PySide6 import QtNetwork as net_mod  # type: ignore
        from PySide6 import QtWidgets as widgets_mod  # type: ignore

        QT6 = True
        HAS_QT = True
        QtCore, QtGui, QtWidgets, QtNetwork = core_mod, gui_mod, widgets_mod, net_mod
        Qt = core_mod.Qt
        return
    except ImportError:
        pass

    try:
        import PySide2  # noqa: F401
    except ImportError:
        return

    _install_pyside2_shims()
    from PySide2 import QtCore as core_mod  # type: ignore
    from PySide2 import QtGui as gui_mod  # type: ignore
    from PySide2 import QtNetwork as net_mod  # type: ignore
    from PySide2 import QtWidgets as widgets_mod  # type: ignore

    HAS_QT = True
    QtCore, QtGui, QtWidgets, QtNetwork = core_mod, gui_mod, widgets_mod, net_mod
    Qt = _QtProxy(core_mod.Qt)


_bootstrap()


# ---------------------------------------------------------------- 差异适配
def event_pos(event):
    """鼠标/滚轮事件坐标（Qt6 用 position()，Qt5 用 localPos()）。"""
    if hasattr(event, "position"):
        return event.position()
    return event.localPos()


def event_global_pos(event):
    """事件全局坐标，统一返回 QPoint。"""
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


def system_is_dark():
    """系统是否深色模式。Qt5 没有 colorScheme()，改读注册表；读不到返回 None。"""
    if not HAS_QT:
        return None
    hints = QtGui.QGuiApplication.styleHints()
    if hasattr(hints, "colorScheme") and hasattr(Qt, "ColorScheme"):
        try:
            return hints.colorScheme() == Qt.ColorScheme.Dark
        except (AttributeError, TypeError):
            return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except (OSError, ValueError):
        return None


def supports_color_scheme_signal() -> bool:
    if not HAS_QT:
        return False
    return hasattr(QtGui.QGuiApplication.styleHints(), "colorSchemeChanged")


def exec_app(app) -> int:
    """Qt6 是 app.exec()，Qt5 是 app.exec_()。"""
    if hasattr(app, "exec"):
        return int(app.exec())
    return int(app.exec_())
