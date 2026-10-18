"""iOS 风格主题：字体工厂、颜色令牌、QSS 与浅色/深色/跟随系统切换。"""

from __future__ import annotations

from string import Template

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from . import constants as C
from . import qtcompat


# ---------------------------------------------------------------- 颜色工具
def qcolor(value: str | QColor, alpha: int | None = None) -> QColor:
    color = QColor(value) if isinstance(value, str) else QColor(value)
    if alpha is not None:
        color.setAlpha(max(0, min(255, int(alpha))))
    return color


def rgba(value: str | QColor, alpha: int) -> str:
    """返回 QSS 可用的 rgba() 字符串，alpha 取 0-255。"""
    color = QColor(value) if isinstance(value, str) else QColor(value)
    return f"rgba({color.red()},{color.green()},{color.blue()},{max(0, min(255, alpha))})"


def mix(first: str | QColor, second: str | QColor, ratio: float) -> QColor:
    """线性混合两种颜色，ratio=0 返回 first。"""
    ratio = max(0.0, min(1.0, ratio))
    a = QColor(first) if isinstance(first, str) else QColor(first)
    b = QColor(second) if isinstance(second, str) else QColor(second)
    return QColor(
        int(a.red() + (b.red() - a.red()) * ratio),
        int(a.green() + (b.green() - a.green()) * ratio),
        int(a.blue() + (b.blue() - a.blue()) * ratio),
        int(a.alpha() + (b.alpha() - a.alpha()) * ratio),
    )


# ---------------------------------------------------------------- 字体工厂
def _apply_families(font: QFont, families: list[str]) -> None:
    try:
        font.setFamilies(families)
    except AttributeError:  # 兼容极老版本
        font.setFamily(families[0])


def clock_font(pixel_size: int, family: str | None = None) -> QFont:
    """主时钟字体：iOS 锁屏式细字重 + 等宽数字（tnum）。

    family 为空时使用默认字体链；指定 family 时也会在其后拼上默认链，
    保证目标机器缺字体时自动回退，不会出现方框或异常宽度。
    """
    font = QFont()
    families: list[str] = []
    if family:
        families.append(family)
    families.extend(name for name in C.FONT_DISPLAY if name not in families)
    _apply_families(font, families)
    font.setPixelSize(max(1, int(pixel_size)))
    font.setWeight(QFont.Weight.Thin)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    try:  # Qt 6.7+：启用等宽数字特性
        font.setFeature(QFont.Tag("tnum"), 1)
    except (AttributeError, TypeError):
        pass
    return font


def sub_font(pixel_size: int) -> QFont:
    """副行字体：日期 + 天气摘要。"""
    font = QFont()
    _apply_families(font, C.FONT_TEXT + C.FONT_CJK)
    font.setPixelSize(max(1, int(pixel_size)))
    font.setWeight(QFont.Weight.Light)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def emoji_font(pixel_size: int) -> QFont:
    font = QFont()
    _apply_families(font, C.FONT_EMOJI + C.FONT_TEXT)
    font.setPixelSize(max(1, int(pixel_size)))
    return font


def ui_font(pixel_size: int = C.PANEL_FONT_PX, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont()
    _apply_families(font, C.FONT_TEXT + C.FONT_CJK)
    font.setPixelSize(int(pixel_size))
    font.setWeight(weight)
    return font


def gear_font(pixel_size: int = C.GEAR_FONT_PX) -> QFont:
    font = QFont()
    _apply_families(font, C.FONT_GEAR)
    font.setPixelSize(int(pixel_size))
    return font


# ---------------------------------------------------------------- QSS 模板
_QSS = Template(
    """
QWidget {
    font-family: "Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI";
    font-size: ${panel_font}px;
    color: ${text};
}
QLabel#sectionTitle {
    color: ${text_secondary};
    font-size: ${section_font}px;
    font-weight: 600;
    padding: 0 0 0 6px;
}
QLabel#rowLabel { font-size: ${panel_font}px; }
QLabel#valueLabel, QLabel#captionLabel {
    color: ${text_secondary};
    font-size: ${caption_font}px;
}
QLabel#panelTitle { font-size: ${title_font}px; font-weight: 600; }
QFrame#rowCard { background: ${card}; border: none; border-radius: ${card_radius}px; }
QFrame#rowSeparator { background: ${separator}; border: none; }
QFrame#panelBody {
    background: ${panel_bg};
    border-radius: ${panel_radius}px;
}
QPushButton#primaryButton {
    background: ${accent};
    color: #FFFFFF;
    border: none;
    border-radius: 15px;
    padding: 5px 16px;
    font-size: ${button_font}px;
    font-weight: 600;
    min-height: 30px;
}
QPushButton#primaryButton:hover { background: ${accent_hover}; }
QPushButton#secondaryButton {
    background: ${segment_track};
    color: ${text};
    border: none;
    border-radius: 15px;
    padding: 5px 14px;
    font-size: ${button_font}px;
    min-height: 30px;
}
QPushButton#secondaryButton:hover { background: ${track}; }
QPushButton#linkButton {
    background: transparent;
    color: ${accent};
    border: none;
    font-size: ${button_font}px;
    padding: 4px 6px;
}
QPushButton#closeButton {
    background: ${track};
    color: ${text_secondary};
    border: none;
    border-radius: 11px;
    font-size: ${button_font}px;
}
QPushButton#closeButton:hover { background: ${segment_track}; }
QLineEdit, QSpinBox {
    background: ${card_alt};
    border: none;
    border-radius: 10px;
    padding: 5px 10px;
    font-size: ${button_font}px;
    color: ${text};
    selection-background-color: ${accent};
    min-height: 26px;
}
QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 2px 2px 0;
}
QScrollBar::handle:vertical {
    background: ${scroll_handle};
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolTip {
    background: ${card};
    color: ${text};
    border: none;
    padding: 4px 8px;
}
"""
)


class ThemeManager(QObject):
    """主题单一来源：settings.appearance_mode -> 实际浅色/深色，并广播 changed。"""

    changed = Signal()

    def __init__(self, app: QApplication, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._mode = "system"
        self._effective = "light"
        if qtcompat.supports_color_scheme_signal():
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_scheme_changed)
        else:
            # Qt5（Windows 7）没有 colorScheme()，用轮询注册表代替
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(C.SYSTEM_THEME_POLL_MS)
            self._poll_timer.timeout.connect(self._on_system_poll)
            self._poll_timer.start()
        self._effective = self._detect_system()
        self._apply()

    # ------------------------------------------------------------ 查询
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def effective(self) -> str:
        """实际生效的外观：light / dark。"""
        return self._effective

    @property
    def is_dark(self) -> bool:
        return self._effective == "dark"

    def tokens(self) -> dict[str, str]:
        return C.TOKENS[self._effective]

    def color(self, key: str, alpha: int | None = None) -> QColor:
        return qcolor(self.tokens()[key], alpha)

    def accent(self) -> QColor:
        return self.color("accent")

    # ------------------------------------------------------------ 切换
    def set_mode(self, mode: str) -> None:
        if mode not in C.APPEARANCE_MODES:
            mode = "system"
        self._mode = mode
        self._refresh()

    def _detect_system(self) -> str:
        return "dark" if qtcompat.system_is_dark() else "light"

    def _on_system_scheme_changed(self, _scheme) -> None:
        if self._mode == "system":
            self._refresh()

    def _on_system_poll(self) -> None:
        if self._mode == "system":
            self._refresh()

    def _refresh(self) -> None:
        effective = self._detect_system() if self._mode == "system" else self._mode
        changed = effective != self._effective
        self._effective = effective
        self._apply()
        if changed:
            self.changed.emit()

    # ------------------------------------------------------------ 应用
    def _apply(self) -> None:
        tokens = self.tokens()
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, qcolor(tokens["panel_bg"]))
        palette.setColor(QPalette.ColorRole.WindowText, qcolor(tokens["text"]))
        palette.setColor(QPalette.ColorRole.Base, qcolor(tokens["card"]))
        palette.setColor(QPalette.ColorRole.Text, qcolor(tokens["text"]))
        palette.setColor(QPalette.ColorRole.Button, qcolor(tokens["card"]))
        palette.setColor(QPalette.ColorRole.ButtonText, qcolor(tokens["text"]))
        palette.setColor(QPalette.ColorRole.Highlight, qcolor(tokens["accent"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, qcolor(tokens["card"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, qcolor(tokens["text"]))
        self._app.setPalette(palette)
        self._app.setStyleSheet(self.stylesheet())

    def stylesheet(self) -> str:
        tokens = self.tokens()
        accent = qcolor(tokens["accent"])
        return _QSS.substitute(
            panel_font=C.PANEL_FONT_PX,
            section_font=C.SECTION_TITLE_PX,
            caption_font=C.CAPTION_FONT_PX,
            title_font=C.PANEL_TITLE_PX,
            button_font=C.BUTTON_FONT_PX,
            card_radius=C.CARD_INNER_RADIUS,
            panel_radius=C.PANEL_RADIUS,
            text=tokens["text"],
            text_secondary=tokens["text_secondary"],
            card=tokens["card"],
            card_alt=tokens["card_alt"],
            panel_bg=rgba(tokens["panel_bg"], 250),
            segment_track=tokens["segment_track"],
            track=tokens["track"],
            separator=rgba(tokens["separator"], 150),
            scroll_handle=tokens["scroll_handle"],
            accent=tokens["accent"],
            accent_hover=mix(accent, "#FFFFFF", 0.18).name(),
        )
