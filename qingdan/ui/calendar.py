"""A small, hand-painted month calendar."""

from __future__ import annotations

import calendar as stdlib_calendar
from datetime import date, timedelta

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from .common import IconButton
from .quick_button import TextChipButton


class DayButton(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.day: date | None = None
        self.in_month = True
        self.is_today = False
        self.is_selected = False
        self.marked = False
        self.mark_pending = False
        self._hover = False
        self.setFixedHeight(34)
        self.setMinimumWidth(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._font = theme.make_font(12, weight=QFont.Weight.Medium)

    def set_data(
        self,
        value: date,
        *,
        in_month: bool,
        today: date,
        selected: date | None,
        marked: bool,
        pending: bool,
    ) -> None:
        self.day = value
        self.in_month = in_month
        self.is_today = value == today
        self.is_selected = value == selected
        self.marked = marked
        self.mark_pending = pending
        self.setEnabled(True)
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        if self.day is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx = self.width() / 2
        cy = self.height() / 2 - 1
        circle = QRectF(cx - 14.5, cy - 14.5, 29, 29)

        if self.is_selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawEllipse(circle)
        elif self._hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT_SOFT))
            painter.drawEllipse(circle)
        elif self.is_today:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#9ABFB1"), 1.1))
            painter.drawEllipse(circle.adjusted(0.6, 0.6, -0.6, -0.6))

        if self.is_selected:
            color = QColor(theme.SURFACE)
        elif not self.in_month:
            color = QColor(theme.MUTED_LIGHT)
            color.setAlpha(135)
        elif self.is_today:
            color = QColor(theme.ACCENT_DARK)
        else:
            color = QColor(theme.INK_SOFT)

        painter.setFont(self._font)
        painter.setPen(color)
        painter.drawText(
            QRectF(0, 0, self.width(), self.height() - 3),
            int(Qt.AlignmentFlag.AlignCenter),
            str(self.day.day),
        )

        if self.marked:
            if self.is_selected:
                dot_color = QColor(theme.SURFACE)
                dot_color.setAlpha(225)
            elif self.mark_pending:
                dot_color = QColor(theme.ACCENT)
            else:
                dot_color = QColor(theme.MUTED_LIGHT)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QRectF(cx - 1.7, self.height() - 9.2, 3.4, 3.4))


class MonthCalendar(QWidget):
    dateClicked = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.today = date.today()
        self.selected: date | None = self.today
        self._marks: dict[date, bool] = {}
        self._display = self.today.replace(day=1)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 0, 0)
        header.setSpacing(4)
        self.month_label = QLabel()
        self.month_label.setFont(theme.make_font(13, weight=QFont.Weight.DemiBold))
        self.month_label.setStyleSheet(f"color: {theme.INK};")
        header.addWidget(self.month_label)
        header.addStretch(1)
        self.prev_button = IconButton(
            "chevron-left",
            button_size=27,
            icon_size=13,
            color=theme.MUTED,
            hover_color=theme.INK,
            hover_bg=theme.SURFACE_SOFT,
            tooltip="上个月",
        )
        self.next_button = IconButton(
            "chevron-right",
            button_size=27,
            icon_size=13,
            color=theme.MUTED,
            hover_color=theme.INK,
            hover_bg=theme.SURFACE_SOFT,
            tooltip="下个月",
        )
        self.prev_button.clicked.connect(lambda: self.move_month(-1))
        self.next_button.clicked.connect(lambda: self.move_month(1))
        header.addWidget(self.prev_button)
        header.addWidget(self.next_button)
        self._root.addLayout(header)

        weekdays = QHBoxLayout()
        weekdays.setContentsMargins(0, 2, 0, 0)
        weekdays.setSpacing(0)
        weekday_font = theme.make_font(10, weight=QFont.Weight.Medium)
        for index, label in enumerate(("一", "二", "三", "四", "五", "六", "日")):
            item = QLabel(label)
            item.setFont(weekday_font)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color = theme.MUTED_LIGHT if index >= 5 else theme.MUTED
            item.setStyleSheet(f"color: {color};")
            item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            weekdays.addWidget(item)
        self._root.addLayout(weekdays)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(0)
        self.grid.setVerticalSpacing(2)
        self.buttons: list[DayButton] = []
        for index in range(42):
            button = DayButton()
            button.clicked.connect(lambda checked=False, b=button: self._on_day(b))
            self.buttons.append(button)
            self.grid.addWidget(button, index // 7, index % 7)
        for column in range(7):
            self.grid.setColumnStretch(column, 1)
        self._root.addLayout(self.grid)
        self._refresh()

    def set_today(self, today: date) -> None:
        self.today = today
        self._refresh()

    def set_marks(self, marks: dict[date, bool]) -> None:
        self._marks = dict(marks)
        self._refresh()

    def set_selected(self, selected: date | None, *, ensure_visible: bool = False) -> None:
        self.selected = selected
        if selected is not None and ensure_visible:
            self._display = selected.replace(day=1)
        self._refresh()

    def show_month(self, value: date) -> None:
        self._display = value.replace(day=1)
        self._refresh()

    def move_month(self, delta: int) -> None:
        month = self._display.month - 1 + delta
        year = self._display.year + month // 12
        month = month % 12 + 1
        self._display = date(year, month, 1)
        self._refresh()

    def go_today(self) -> None:
        self.selected = self.today
        self._display = self.today.replace(day=1)
        self._refresh()
        self.dateClicked.emit(self.today)

    def _on_day(self, button: DayButton) -> None:
        if button.day is None:
            return
        value = button.day
        self.selected = value
        if (value.year, value.month) != (self._display.year, self._display.month):
            self._display = value.replace(day=1)
        self._refresh()
        self.dateClicked.emit(value)

    def _refresh(self) -> None:
        self.month_label.setText(f"{self._display.year}年{self._display.month}月")
        first = self._display
        offset = first.weekday()
        start = first - timedelta(days=offset)
        for index, button in enumerate(self.buttons):
            day = start + timedelta(days=index)
            button.set_data(
                day,
                in_month=day.month == first.month and day.year == first.year,
                today=self.today,
                selected=self.selected,
                marked=day in self._marks,
                pending=self._marks.get(day, False),
            )

    def sizeHint(self) -> QSize:
        return QSize(250, 245)


class DatePickerPopup(QWidget):
    """A popup date picker used by the composer and due chips."""

    dateSelected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setFixedWidth(332)
        self._today = date.today()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        self.panel = QWidget()
        self.panel.setObjectName("datePickerPanel")
        outer.addWidget(self.panel)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(16, 15, 16, 14)
        layout.setSpacing(10)
        title = QLabel("设置截止日期")
        title.setFont(theme.make_font(13, weight=QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {theme.INK};")
        layout.addWidget(title)

        self.calendar = MonthCalendar()
        self.calendar.today = self._today
        self.calendar.set_selected(None)
        self.calendar.dateClicked.connect(self._choose_date)
        layout.addWidget(self.calendar)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(divider)

        self.footer = QHBoxLayout()
        self.footer.setContentsMargins(0, 0, 0, 0)
        self.footer.setSpacing(6)
        quick_font = theme.make_font(12, weight=QFont.Weight.Medium)
        self.quick_buttons: list[QAbstractButton] = []
        for label, offset in (("今天", 0), ("明天", 1), ("下周一", None)):
            button = TextChipButton(label)
            button.setFont(quick_font)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(30)
            if offset is not None:
                button.clicked.connect(
                    lambda checked=False, days=offset: self._choose_offset(days)
                )
            else:
                button.clicked.connect(lambda checked=False: self._choose_next_monday())
            self.footer.addWidget(button)
            self.quick_buttons.append(button)
        self.footer.addStretch(1)
        self.clear_button = TextChipButton("清除")
        self.clear_button.setFont(quick_font)
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFixedHeight(30)
        self.clear_button.clicked.connect(lambda: self._choose_date(None))
        self.footer.addWidget(self.clear_button)
        layout.addLayout(self.footer)

        self.panel.setStyleSheet(
            f"""
            QWidget#datePickerPanel {{
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER_STRONG};
                border-radius: 16px;
            }}
            """
        )
        from .common import attach_shadow

        attach_shadow(self.panel, blur=30, dy=8, alpha=38)

    def set_today(self, today: date) -> None:
        self._today = today
        self.calendar.set_today(today)

    def _next_monday(self) -> date:
        days = (7 - self._today.weekday()) % 7
        if days == 0:
            days = 7
        return self._today + timedelta(days=days)

    def _choose_next_monday(self) -> None:
        self._choose_date(self._next_monday())

    def _choose_offset(self, days: int) -> None:
        self._choose_date(self._today + timedelta(days=days))

    def _choose_date(self, value: date | None) -> None:
        self.dateSelected.emit(value)
        self.close()

    def open_for(
        self,
        anchor: QWidget,
        current: date | None,
        *,
        allow_clear: bool = True,
        today: date | None = None,
    ) -> None:
        current_today = today or date.today()
        self.set_today(current_today)
        self.clear_button.setVisible(allow_clear)
        self.calendar.set_selected(current, ensure_visible=True)
        self.adjustSize()
        point = anchor.mapToGlobal(anchor.rect().bottomLeft())
        screen = anchor.screen()
        available = screen.availableGeometry() if screen else None
        x = point.x()
        y = point.y() + 6
        if available is not None:
            if x + self.width() > available.right():
                x = available.right() - self.width() - 8
            if y + self.height() > available.bottom():
                top = anchor.mapToGlobal(anchor.rect().topLeft()).y()
                y = max(available.top() + 8, top - self.height() - 6)
            x = max(available.left() + 8, x)
        self.move(x, y)
        self.show()
        self.raise_()
        self.calendar.setFocus()
