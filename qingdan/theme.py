"""Visual language for Qingdan."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

# Core palette
BG = "#F4F1E9"
BG_DEEP = "#ECE8DE"
SURFACE = "#FFFFFF"
SURFACE_SOFT = "#FBF9F4"
BORDER = "#E8E1D3"
BORDER_STRONG = "#DCD3C2"

SIDEBAR = "#173E36"
SIDEBAR_DEEP = "#10312B"
SIDEBAR_TEXT = "#F5F0E4"
SIDEBAR_MUTED = "#9BB1A7"
SIDEBAR_LINE = "#2A5048"
GOLD = "#E9BB6B"
GOLD_SOFT = "#F7E7C9"

ACCENT = "#347563"
ACCENT_DARK = "#245A4B"
ACCENT_SOFT = "#EAF3EF"
INK = "#1C2E29"
INK_SOFT = "#485D56"
MUTED = "#84928B"
MUTED_LIGHT = "#A8B2AC"
DONE = "#98A39D"
CORAL = "#C9654B"
CORAL_SOFT = "#FBEDE8"
AMBER = "#A97526"
AMBER_SOFT = "#FBF1DD"

FONT_FAMILIES = [
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "Segoe UI",
    "Noto Sans CJK SC",
    "sans-serif",
]


def make_font(
    pixel_size: int,
    *,
    weight: QFont.Weight = QFont.Weight.Normal,
    letter_spacing: float = 0,
    italic: bool = False,
) -> QFont:
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(max(1, int(round(pixel_size))))
    font.setWeight(weight)
    font.setItalic(italic)
    if letter_spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    return font


def with_alpha(hex_color: str, alpha: int) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


def configure_application(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(make_font(14))
    app.setStyleSheet(APP_STYLESHEET)


APP_STYLESHEET = f"""
QWidget {{
    color: {INK};
    background: transparent;
}}
QToolTip {{
    background: {INK};
    color: {SURFACE};
    border: none;
    padding: 5px 8px;
    border-radius: 4px;
    font-size: 12px;
}}
QLineEdit {{
    background: transparent;
    border: none;
    padding: 0;
    color: {INK};
    selection-background-color: #B9D9CE;
    selection-color: {INK};
}}
QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    min-height: 32px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: #C7BCA9;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QFrame#windowSurface {{
    background: {BG};
    border: 1px solid #E2DBCC;
    border-radius: 22px;
}}
QFrame#windowSurface[maximized="true"] {{
    border: none;
    border-radius: 0;
}}
QFrame#sidebar {{
    background: {SIDEBAR};
    border: none;
    border-top-left-radius: 21px;
    border-bottom-left-radius: 21px;
}}
QFrame#sidebar[maximized="true"] {{
    border-radius: 0;
}}
QFrame#body {{
    background: {BG};
    border: none;
    border-top-right-radius: 21px;
    border-bottom-right-radius: 21px;
}}
QFrame#body[maximized="true"] {{
    border-radius: 0;
}}
QFrame#composerFrame {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 15px;
}}
QFrame#composerFrame[focused="true"] {{
    border: 1px solid #A9C9BC;
}}
QFrame#taskRow {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#taskRow[completed="true"] {{
    background: #FAF8F3;
    border: 1px solid #EEE9DF;
}}
QFrame#taskRow[hovered="true"] {{
    border: 1px solid #D3C9B8;
}}
QFrame#calendarCard, QFrame#upcomingCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
QFrame#reminderPanel {{
    background: #FFFDF8;
    border: 1px solid {BORDER_STRONG};
    border-radius: 17px;
}}
QFrame#miniSurface {{
    background: {BG};
    border: 1px solid #E2DBCC;
    border-radius: 18px;
}}
QFrame#miniHeaderBand {{
    background: {SIDEBAR};
    border: none;
    border-top-left-radius: 17px;
    border-top-right-radius: 17px;
}}
QFrame#miniTaskRow {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#miniTaskRow[hovered="true"] {{
    border: 1px solid #D1C7B5;
    background: #FFFEFA;
}}
QFrame#miniComposerFrame {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 11px;
}}
QFrame#miniComposerFrame[focused="true"] {{
    border: 1px solid #A9C9BC;
}}
QPushButton#miniTab {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {MUTED};
    font-size: 12px;
    padding: 4px 11px;
}}
QPushButton#miniTab:hover {{
    color: {INK_SOFT};
    background: rgba(255, 255, 255, 0.6);
}}
QPushButton#miniTab:checked {{
    color: {INK};
    background: {SURFACE};
    border: 1px solid {BORDER};
}}
QLineEdit#miniInput {{
    color: {INK};
    font-size: 12px;
}}
QMenu {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 24px 7px 10px;
    border-radius: 6px;
    color: {INK_SOFT};
    font-size: 12px;
}}
QMenu::item:selected {{
    background: {ACCENT_SOFT};
    color: {ACCENT_DARK};
}}
QMenu::item:disabled {{
    color: {MUTED_LIGHT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 5px 8px;
}}
QFrame#progressCard {{
    background: rgba(255, 255, 255, 0.065);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
}}
QFrame#todayChip {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
}}
QLabel#pageTitle {{
    color: {INK};
}}
QLabel#sectionTitle {{
    color: {INK_SOFT};
}}
QLabel#mutedLabel {{
    color: {MUTED};
}}
QLabel#dateLabel {{
    color: {MUTED};
}}
QLabel#sidebarMuted {{
    color: {SIDEBAR_MUTED};
}}
QLabel#sidebarText {{
    color: {SIDEBAR_TEXT};
}}
QPushButton#flatButton {{
    background: transparent;
    border: none;
    color: {ACCENT};
    font-size: 12px;
    padding: 4px 8px;
}}
QPushButton#flatButton:hover {{
    background: {ACCENT_SOFT};
    border-radius: 7px;
}}
QPushButton#quietButton {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {INK_SOFT};
    padding: 6px 10px;
    font-size: 12px;
}}
QPushButton#quietButton:hover {{
    background: {SURFACE_SOFT};
    border-color: {BORDER_STRONG};
}}
QPushButton#dangerButton {{
    background: {CORAL};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
}}
QDialog {{
    background: {BG};
}}
"""
