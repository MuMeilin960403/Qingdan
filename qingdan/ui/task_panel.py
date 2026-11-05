"""The central composer, task list and date-picker orchestration."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from ..filters import ViewKind, due_marks
from ..models import Task
from .calendar import DatePickerPopup
from .common import (
    CircularAddButton,
    DuePill,
    EmptyState,
    IconButton,
    RepeatPill,
    repolish,
)
from .repeat_menu import choose_repeat
from .task_row import TaskRow


class Composer(QFrame):
    submitted = Signal(str, object, object)
    dateButtonClicked = Signal(object)

    def __init__(self, today: date, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("composerFrame")
        self.setProperty("focused", False)
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.today = today
        self._due: date | None = None
        self._repeat: str | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(17, 0, 12, 0)
        layout.setSpacing(10)

        plus = QLabel()
        plus.setPixmap(icons.icon_pixmap("plus", theme.ACCENT, 18))
        plus.setFixedSize(20, 20)
        layout.addWidget(plus, 0, Qt.AlignmentFlag.AlignVCenter)

        self.input = QLineEdit()
        self.input.setObjectName("composerInput")
        self.input.setPlaceholderText("写下一件要做的事…")
        self.input.setFont(theme.make_font(14, weight=QFont.Weight.Medium))
        self.input.setMinimumHeight(34)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.input.setClearButtonEnabled(False)
        palette = self.input.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme.MUTED_LIGHT))
        self.input.setPalette(palette)
        self.input.textChanged.connect(self._update_add_state)
        self.input.returnPressed.connect(self._submit)
        self.input.installEventFilter(self)
        layout.addWidget(self.input, 1)

        divider = QFrame()
        divider.setFixedSize(1, 22)
        divider.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(divider, 0, Qt.AlignmentFlag.AlignVCenter)

        self.due_button = DuePill(
            today=today,
            due=None,
            completed=False,
            allow_empty=True,
        )
        self.due_button.setToolTip("设置截止日期")
        self.due_button.clicked.connect(lambda: self.dateButtonClicked.emit(self.due_button))
        layout.addWidget(self.due_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.repeat_button = RepeatPill(None)
        self.repeat_button.clicked.connect(self._open_repeat_menu)
        layout.addWidget(self.repeat_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.add_button = CircularAddButton()
        self.add_button.setToolTip("添加任务（Enter）")
        self.add_button.clicked.connect(self._submit)
        layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)

    @property
    def due(self) -> date | None:
        return self._due

    @property
    def repeat(self) -> str | None:
        return self._repeat

    def set_today(self, today: date) -> None:
        self.today = today
        self.due_button.set_state(self._due, today, False)

    def set_due(self, due: date | None) -> None:
        self._due = due
        self.due_button.set_state(due, self.today, False)
        self.due_button.setToolTip(
            "点击修改截止日期" if due is not None else "为这项任务设置截止日期"
        )
        if due is None and self._repeat is not None:
            self.set_repeat(None)

    def set_repeat(self, repeat: str | None) -> None:
        self._repeat = repeat
        self.repeat_button.set_repeat(repeat)

    def _open_repeat_menu(self) -> None:
        accepted, repeat = choose_repeat(
            self.window(),
            self.repeat_button,
            self._repeat,
        )
        if not accepted:
            return
        if repeat is not None and self._due is None:
            self.set_due(self.today)
        self.set_repeat(repeat)

    def clear(self) -> None:
        self.input.clear()

    def reset_after_add(self) -> None:
        self.input.clear()
        self.set_repeat(None)

    def focus_input(self) -> None:
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.input:
            if event.type() == QEvent.Type.FocusIn:
                self.setProperty("focused", True)
                repolish(self)
            elif event.type() == QEvent.Type.FocusOut:
                self.setProperty("focused", False)
                repolish(self)
        return super().eventFilter(watched, event)

    def _update_add_state(self, text: str) -> None:
        self.add_button.setEnabled(bool(text.strip()))

    def _submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        # The window clears this only after the store confirms a successful
        # save, so a failed write leaves the draft available to retry.
        self.submitted.emit(text, self._due, self._repeat)


class TaskPanel(QWidget):
    taskAdded = Signal(str, object, object)
    completionChanged = Signal(str, bool)
    taskDeleted = Signal(str)
    titleChanged = Signal(str, str)
    dueChanged = Signal(str, object)
    repeatChanged = Signal(str, object)

    def __init__(self, today: date, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.today = today
        self._date_popup: DatePickerPopup | None = None
        self._date_target: tuple[str, str | None] | None = None
        self._tasks: list[Task] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(1, 0, 2, 0)
        header_layout.setSpacing(12)
        heading = QVBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(0)
        self.kicker = QLabel("")
        self.kicker.setFont(
            theme.make_font(10, weight=QFont.Weight.DemiBold, letter_spacing=0.8)
        )
        self.kicker.setStyleSheet(f"color: {theme.ACCENT};")
        heading.addWidget(self.kicker)
        heading.addSpacing(5)
        self.title_label = QLabel("今天")
        self.title_label.setObjectName("pageTitle")
        self.title_label.setFont(
            theme.make_font(32, weight=QFont.Weight.Bold, letter_spacing=-0.4)
        )
        heading.addWidget(self.title_label)
        heading.addSpacing(3)
        self.subtitle = QLabel("")
        self.subtitle.setFont(theme.make_font(12))
        self.subtitle.setStyleSheet(f"color: {theme.MUTED};")
        heading.addWidget(self.subtitle)
        header_layout.addLayout(heading, 1)
        self.header_mark = QLabel()
        self.header_mark.setPixmap(icons.icon_pixmap("leaf", "#C8D8CF", 62, stroke=1.1))
        self.header_mark.setFixedSize(64, 64)
        header_layout.addWidget(self.header_mark, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(self.header)

        root.addSpacing(19)
        self.composer = Composer(today)
        self.composer.submitted.connect(self.taskAdded)
        self.composer.dateButtonClicked.connect(self._open_composer_date)
        root.addWidget(self.composer)

        root.addSpacing(20)
        self.list_header = QWidget()
        list_header_layout = QHBoxLayout(self.list_header)
        list_header_layout.setContentsMargins(2, 0, 9, 0)
        list_header_layout.setSpacing(8)
        self.list_title = QLabel("任务")
        self.list_title.setFont(theme.make_font(12, weight=QFont.Weight.DemiBold))
        self.list_title.setStyleSheet(f"color: {theme.INK_SOFT};")
        list_header_layout.addWidget(self.list_title)
        list_header_layout.addStretch(1)
        self.list_hint = QLabel("按截止日期排列")
        self.list_hint.setFont(theme.make_font(10))
        self.list_hint.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
        list_header_layout.addWidget(self.list_hint)
        root.addWidget(self.list_header)
        root.addSpacing(10)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 1, 7, 16)
        self.content_layout.setSpacing(8)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

    # ------------------------------------------------------------------ data
    def set_today(self, today: date) -> None:
        self.today = today
        self.composer.set_today(today)

    def render(
        self,
        *,
        view: ViewKind,
        kicker: str,
        title: str,
        subtitle: str,
        tasks: list[Task],
        allow_add: bool,
        default_due: date | None = None,
        reset_composer: bool = False,
        reset_scroll: bool = False,
    ) -> None:
        self.set_today(self.today)
        self._tasks = list(tasks)
        self.kicker.setText(kicker)
        self.title_label.setText(title)
        self.subtitle.setText(subtitle)
        self.composer.setVisible(allow_add)
        if allow_add and reset_composer:
            self.composer.set_due(default_due)
            self.composer.set_repeat(None)
        self._render_list(view, tasks, reset_scroll=reset_scroll)

    def _render_list(
        self,
        view: ViewKind,
        tasks: list[Task],
        *,
        reset_scroll: bool,
    ) -> None:
        previous_scroll = self.scroll.verticalScrollBar().value()
        from .common import clear_layout

        clear_layout(self.content_layout)

        if not tasks:
            self.list_header.hide()
            opening = QWidget()
            opening_layout = QVBoxLayout(opening)
            opening_layout.setContentsMargins(0, 0, 7, 0)
            opening_layout.addStretch(1)
            empty = EmptyState()
            empty_title, empty_body = self._empty_copy(view)
            empty.set_text(empty_title, empty_body)
            opening_layout.addWidget(empty)
            opening_layout.addStretch(1)
            self.content_layout.addWidget(opening)
            self.scroll.verticalScrollBar().setValue(0)
            return

        self.list_header.show()
        self.list_title.setText("任务")
        self.list_hint.setText(
            "按完成时间排列" if view is ViewKind.COMPLETED else "按截止日期排列"
        )
        completed_separator_added = False
        completed_count = sum(task.completed for task in tasks)
        for index, task in enumerate(tasks):
            if view is not ViewKind.COMPLETED and task.completed and not completed_separator_added:
                self.content_layout.addSpacing(7)
                self.content_layout.addWidget(
                    self._make_section_header("已完成", completed_count)
                )
                completed_separator_added = True
            row = TaskRow(task, self.today)
            row.completionToggled.connect(self.completionChanged)
            row.deleteRequested.connect(self.taskDeleted)
            row.titleCommitted.connect(self.titleChanged)
            row.dateRequested.connect(self._on_task_date_requested)
            row.repeatRequested.connect(self._on_task_repeat_requested)
            self.content_layout.addWidget(row)
        self.content_layout.addStretch(1)
        target = 0 if reset_scroll else previous_scroll
        QTimer.singleShot(
            0,
            lambda: self.scroll.verticalScrollBar().setValue(
                min(target, self.scroll.verticalScrollBar().maximum())
            ),
        )

    def _make_section_header(self, label: str, count: int) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(4, 0, 9, 1)
        layout.setSpacing(8)
        title = QLabel(f"{label} · {count}")
        title.setFont(theme.make_font(11, weight=QFont.Weight.Medium))
        title.setStyleSheet(f"color: {theme.MUTED};")
        layout.addWidget(title)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(line, 1)
        wrapper.setFixedHeight(28)
        return wrapper

    def _empty_copy(self, view: ViewKind) -> tuple[str, str]:
        if view is ViewKind.TODAY:
            return "今天还没有安排", "写下一件小事，给今天一个轻盈的开始。"
        if view is ViewKind.ALL:
            return "清单还是空的", "把想做的事情放进来，从第一件开始。"
        if view is ViewKind.UPCOMING:
            return "未来一周很轻松", "还没有临近截止的任务，可以提前安排一点。"
        if view is ViewKind.COMPLETED:
            return "还没有完成的事项", "勾选一项任务后，它会安静地待在这里。"
        return "这一天没有截止任务", "可以添加一件，或者去日历看看别的日期。"

    # ---------------------------------------------------------------- actions
    def focus_composer(self) -> None:
        if self.composer.isVisible():
            self.composer.focus_input()

    def clear_composer(self) -> None:
        self.composer.clear()

    def reset_composer_after_add(self) -> None:
        self.composer.reset_after_add()

    def reveal_task(self, task_id: str) -> None:
        def reveal() -> None:
            for row in self.findChildren(TaskRow):
                if row.task_id == task_id:
                    self.scroll.ensureWidgetVisible(row, 0, 24)
                    return

        QTimer.singleShot(0, reveal)

    def _open_composer_date(self, anchor: QWidget) -> None:
        self._date_target = ("composer", None)
        self._show_date_picker(anchor, self.composer.due)

    def _on_task_date_requested(
        self,
        task_id: str,
        anchor: QWidget,
        current_due: object,
    ) -> None:
        self._date_target = ("task", task_id)
        self._show_date_picker(
            anchor, current_due if isinstance(current_due, date) else None
        )

    def _show_date_picker(self, anchor: QWidget, current: date | None) -> None:
        if self._date_popup is None:
            self._date_popup = DatePickerPopup(self.window())
            self._date_popup.dateSelected.connect(self._on_date_selected)
        self._date_popup.calendar.set_marks(due_marks(self._tasks))
        self._date_popup.open_for(
            anchor,
            current,
            allow_clear=True,
            today=self.today,
        )

    def _on_date_selected(self, value: object) -> None:
        target = self._date_target
        self._date_target = None
        if target is None:
            return
        due = value if isinstance(value, date) else None
        kind, task_id = target
        if kind == "composer":
            self.composer.set_due(due)
            QTimer.singleShot(0, self.focus_composer)
        elif task_id is not None:
            self.dueChanged.emit(task_id, due)

    def _on_task_repeat_requested(
        self,
        task_id: str,
        anchor: QWidget,
        current_repeat: object,
    ) -> None:
        accepted, repeat = choose_repeat(
            self.window(),
            anchor,
            current_repeat if isinstance(current_repeat, str) else None,
        )
        if accepted:
            self.repeatChanged.emit(task_id, repeat)
