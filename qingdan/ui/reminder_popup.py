"""A small always-on-top reminder toast."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from ..filters import due_text
from ..reminders import ReminderEvent, reminder_copy
from .common import ElidedLabel, IconButton, attach_shadow


class ReminderPopup(QWidget):
    openRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedWidth(390)
        self._today = date.today()
        self._event: ReminderEvent | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        self.panel = QFrame()
        self.panel.setObjectName("reminderPanel")
        outer.addWidget(self.panel)
        attach_shadow(self.panel, blur=34, dy=10, alpha=42)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(19, 16, 19, 16)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(9)
        bell = QLabel()
        bell.setFixedSize(28, 28)
        bell.setPixmap(icons.icon_pixmap("bell", theme.AMBER, 17))
        bell.setStyleSheet(
            f"background: {theme.AMBER_SOFT}; border-radius: 9px;"
        )
        bell.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(bell, 0, Qt.AlignmentFlag.AlignVCenter)
        header_text = QVBoxLayout()
        header_text.setContentsMargins(0, 0, 0, 0)
        header_text.setSpacing(0)
        self.kicker = QLabel("截止提醒")
        self.kicker.setFont(
            theme.make_font(9.5, weight=QFont.Weight.DemiBold, letter_spacing=0.8)
        )
        self.kicker.setStyleSheet(f"color: {theme.AMBER};")
        header_text.addWidget(self.kicker)
        self.schedule = QLabel("未完成前会持续提醒")
        self.schedule.setFont(theme.make_font(10))
        self.schedule.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
        header_text.addWidget(self.schedule)
        header.addLayout(header_text, 1)
        close_button = IconButton(
            "close",
            button_size=26,
            icon_size=13,
            color=theme.MUTED_LIGHT,
            hover_color=theme.INK_SOFT,
            hover_bg=theme.SURFACE_SOFT,
            tooltip="关闭提醒",
        )
        close_button.clicked.connect(self.hide)
        header.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)
        layout.addSpacing(11)

        self.title_label = QLabel()
        self.title_label.setFont(theme.make_font(16, weight=QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {theme.INK};")
        layout.addWidget(self.title_label)
        layout.addSpacing(3)
        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setFont(theme.make_font(11.5))
        self.body_label.setStyleSheet(f"color: {theme.MUTED};")
        layout.addWidget(self.body_label)
        layout.addSpacing(11)

        self.task_list = QVBoxLayout()
        self.task_list.setContentsMargins(0, 0, 0, 0)
        self.task_list.setSpacing(1)
        layout.addLayout(self.task_list)
        layout.addSpacing(13)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(divider)
        layout.addSpacing(11)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        hint = QLabel("全部处理完之前，每天还会提醒")
        hint.setFont(theme.make_font(9))
        hint.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
        actions.addWidget(hint)
        actions.addStretch(1)

        self.later_button = QPushButton("知道了")
        self.later_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.later_button.setFont(theme.make_font(11))
        self.later_button.setFixedHeight(30)
        self.later_button.setStyleSheet(
            f"""
            QPushButton {{
                color: {theme.MUTED};
                background: transparent;
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                color: {theme.INK_SOFT};
                background: {theme.SURFACE_SOFT};
            }}
            """
        )
        self.later_button.clicked.connect(self.hide)
        actions.addWidget(self.later_button)

        self.open_button = QPushButton("打开清单")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.setFont(
            theme.make_font(11, weight=QFont.Weight.DemiBold)
        )
        self.open_button.setFixedHeight(30)
        self.open_button.setStyleSheet(
            f"""
            QPushButton {{
                color: {theme.SURFACE};
                background: {theme.ACCENT};
                border: none;
                border-radius: 8px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {theme.ACCENT_DARK};
            }}
            """
        )
        self.open_button.clicked.connect(self._open)
        actions.addWidget(self.open_button)
        layout.addLayout(actions)

        self._auto_hide = QTimer(self)
        self._auto_hide.setSingleShot(True)
        self._auto_hide.timeout.connect(self.hide)

    def _clear_tasks(self) -> None:
        while self.task_list.count():
            item = self.task_list.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def show_event(self, event: ReminderEvent, today: date) -> None:
        title, body = reminder_copy(event)
        self._event = event
        self._today = today
        self.title_label.setText(title)
        self.body_label.setText(body)
        self.kicker.setText(
            "今晚提前看" if event.kind == "evening" else "截止提醒"
        )
        self._clear_tasks()
        for task in event.tasks[:3]:
            self.task_list.addWidget(self._make_task_line(task))
        if event.count > 3:
            more = QLabel(f"还有 {event.count - 3} 项未完成")
            more.setFont(theme.make_font(10))
            more.setStyleSheet(f"color: {theme.MUTED_LIGHT}; padding-left: 2px;")
            self.task_list.addWidget(more)

        self.adjustSize()
        screen = QGuiApplication.screenAt(self._anchor_point())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            x = available.right() - self.width() - 12
            y = available.bottom() - self.height() - 12
            self.move(max(available.left() + 12, x), max(available.top() + 12, y))
        self.show()
        self.raise_()
        self._auto_hide.start(30_000)

    def _anchor_point(self):
        from PySide6.QtGui import QCursor

        return QCursor.pos()

    def _make_task_line(self, task) -> QWidget:
        row = QWidget()
        row.setFixedHeight(28)
        line = QHBoxLayout(row)
        line.setContentsMargins(2, 0, 2, 0)
        line.setSpacing(8)
        delta = (task.due - self._today).days if task.due else 0
        if delta < 0:
            fg, bg, label = theme.CORAL, theme.CORAL_SOFT, "逾期"
        elif delta == 0:
            fg, bg, label = theme.AMBER, theme.AMBER_SOFT, "今天"
        elif delta == 1:
            fg, bg, label = theme.ACCENT_DARK, theme.ACCENT_SOFT, "明天"
        else:
            fg, bg = theme.INK_SOFT, "#F2F4F0"
            label = due_text(task.due, self._today)
        badge = QLabel(label)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(42, 21)
        badge.setFont(theme.make_font(9, weight=QFont.Weight.DemiBold))
        badge.setStyleSheet(f"color: {fg}; background: {bg}; border-radius: 6px;")
        line.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        title = ElidedLabel(task.title)
        title.setFont(theme.make_font(11.5))
        title.setStyleSheet(f"color: {theme.INK_SOFT};")
        line.addWidget(title, 1)
        return row

    def _open(self) -> None:
        self.hide()
        self.openRequested.emit()
