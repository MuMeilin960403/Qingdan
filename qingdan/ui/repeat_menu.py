"""Shared recurrence chooser menu."""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu, QWidget

from .. import theme
from ..recurrence import REPEAT_HINTS, REPEAT_LABELS, REPEAT_RULES


def choose_repeat(
    parent: QWidget,
    anchor: QWidget,
    current: str | None,
) -> tuple[bool, str | None]:
    """Open the repeat menu and return (accepted, rule)."""

    menu = QMenu(parent)
    menu.setFont(theme.make_font(11))
    group = QActionGroup(menu)
    group.setExclusive(True)
    for rule in (None, *REPEAT_RULES):
        action = menu.addAction(REPEAT_LABELS[rule])
        action.setCheckable(True)
        action.setChecked(rule == current)
        action.setToolTip(REPEAT_HINTS[rule])
        action.setData("__none__" if rule is None else rule)
        group.addAction(action)
    chosen = menu.exec(anchor.mapToGlobal(QPoint(0, anchor.height() + 4)))
    if chosen is None:
        return False, None
    data = chosen.data()
    return True, None if data == "__none__" else data
