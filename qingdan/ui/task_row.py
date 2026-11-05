"""A single task row with inline editing and due-date editing."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QWidget,
)

from .. import theme
from ..models import Task
from .common import CheckCircle, DuePill, IconButton, RepeatPill, repolish


class InlineTitleEdit(QLineEdit):
    committed = Signal(str)

    def __init__(
        self,
        text: str,
        *,
        editable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._editable = editable
        self._editing = False
        self._original = text
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFrame(False)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setStyleSheet(
            """
            QLineEdit {
                background: transparent;
                border: none;
                padding: 0;
            }
            """
        )
        self.setToolTip(text)
        self.editingFinished.connect(self._finish_edit)

    def set_editable(self, editable: bool) -> None:
        self._editable = editable

    def begin_edit(self) -> None:
        if self._editing or not self._editable or self.isReadOnly() is False:
            return
        self._original = self.text()
        self.setReadOnly(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self._editing = True
        self.selectAll()
        self.setFocus(Qt.FocusReason.MouseFocusReason)

    def _finish_edit(self) -> None:
        if not self._editing:
            return
        self._editing = False
        value = self.text().strip()
        if not value:
            value = self._original
            self.setText(value)
            changed = False
        else:
            changed = value != self._original
            if changed:
                self.setText(value)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip(value)
        if self.hasFocus():
            self.clearFocus()
        if changed:
            self.committed.emit(value)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.isReadOnly() and self._editable:
            self.begin_edit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self._editing:
            self._editing = False
            self.setText(self._original)
            self.setReadOnly(True)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        if self._editing:
            self._finish_edit()


class TaskRow(QFrame):
    completionToggled = Signal(str, bool)
    deleteRequested = Signal(str)
    titleCommitted = Signal(str, str)
    dateRequested = Signal(str, object, object)
    repeatRequested = Signal(str, object, object)

    def __init__(self, task: Task, today: date, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task = task
        self.today = today
        self.task_id = task.id
        self.setObjectName("taskRow")
        self.setProperty("completed", task.completed)
        self.setProperty("hovered", False)
        self.setFixedHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 11, 0)
        layout.setSpacing(12)

        self.check = CheckCircle()
        self.check.setChecked(task.completed)
        self.check.clicked.connect(self._on_check_clicked)
        if task.completed:
            self.check.setToolTip("标记为未完成")
            self.check.setAccessibleName(f"标记为未完成：{task.title}")
        else:
            self.check.setToolTip("标记为已完成")
            self.check.setAccessibleName(f"标记为已完成：{task.title}")
        layout.addWidget(self.check, 0, Qt.AlignmentFlag.AlignVCenter)

        self.title_edit = InlineTitleEdit(task.title, editable=not task.completed)
        if not task.completed:
            self.title_edit.setToolTip(f"{task.title}\n双击编辑任务名称")
        self.title_edit.setFont(self._title_font(task.completed))
        self.title_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none; padding: 0; }"
            + (
                f"QLineEdit {{ color: {theme.DONE}; }}"
                if task.completed
                else ""
            )
        )
        self.title_edit.committed.connect(self._on_title_committed)
        layout.addWidget(self.title_edit, 1, Qt.AlignmentFlag.AlignVCenter)

        self.repeat_pill = RepeatPill(task.repeat)
        self.repeat_pill.clicked.connect(
            lambda: self.repeatRequested.emit(
                self.task_id, self.repeat_pill, task.repeat
            )
        )
        if not (task.completed and task.repeat is None):
            layout.addWidget(self.repeat_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            self.repeat_pill.hide()

        self.due_pill = DuePill(
            today=today,
            due=task.due,
            completed=task.completed,
            allow_empty=not (task.completed and task.due is None),
        )
        if task.due is None:
            self.due_pill.setToolTip("为这项任务设置截止日期")
        else:
            self.due_pill.setToolTip("点击修改截止日期")
        self.due_pill.clicked.connect(
            lambda: self.dateRequested.emit(self.task_id, self.due_pill, task.due)
        )
        layout.addWidget(self.due_pill, 0, Qt.AlignmentFlag.AlignVCenter)

        self.delete_button = IconButton(
            "trash",
            button_size=30,
            icon_size=15,
            color=theme.MUTED_LIGHT,
            hover_color=theme.CORAL,
            hover_bg=theme.CORAL_SOFT,
            tooltip="删除任务",
        )
        self._delete_effect = QGraphicsOpacityEffect(self.delete_button)
        self._delete_effect.setOpacity(0.0)
        self.delete_button.setGraphicsEffect(self._delete_effect)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(lambda: self.deleteRequested.emit(self.task_id))
        layout.addWidget(self.delete_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self._hovered = False
        self.setMouseTracking(True)

    @staticmethod
    def _title_font(completed: bool) -> QFont:
        font = theme.make_font(
            14,
            weight=QFont.Weight.Medium,
        )
        font.setStrikeOut(completed)
        return font

    def _on_check_clicked(self) -> None:
        self.completionToggled.emit(self.task_id, self.check.isChecked())

    def _on_title_committed(self, text: str) -> None:
        self.titleCommitted.emit(self.task_id, text)

    def _show_delete(self, show: bool) -> None:
        if show == self._hovered:
            return
        self.delete_button.setEnabled(show)
        self._delete_effect.setOpacity(1.0 if show else 0.0)
        self._hovered = show
        self.setProperty("hovered", show)
        repolish(self)
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._show_delete(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._show_delete(False)
        super().leaveEvent(event)
