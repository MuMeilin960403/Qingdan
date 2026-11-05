"""Deadline reminder rules and the in-process reminder scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable, Iterable

from PySide6.QtCore import QObject, QSettings, QTimer, Signal

from .models import Task

MORNING_TIME = time(9, 0)
EVENING_TIME = time(20, 0)
CHECK_INTERVAL_MS = 30_000
STARTUP_DELAY_MS = 1_500


@dataclass(frozen=True, slots=True)
class ReminderEvent:
    """A grouped reminder shown in the UI."""

    kind: str  # "morning" | "evening" | "combined"
    tasks: tuple[Task, ...]
    morning: bool
    evening: bool

    @property
    def count(self) -> int:
        return len(self.tasks)


def pending_with_due(tasks: Iterable[Task]) -> list[Task]:
    return [task for task in tasks if not task.completed and task.due is not None]


def pending_due_on_or_before(tasks: Iterable[Task], day: date) -> list[Task]:
    return sorted(
        (task for task in pending_with_due(tasks) if task.due is not None and task.due <= day),
        key=lambda task: (task.due or day, task.created_at),
    )


def pending_due_on(tasks: Iterable[Task], day: date) -> list[Task]:
    return sorted(
        (task for task in pending_with_due(tasks) if task.due == day),
        key=lambda task: task.created_at,
    )


def build_reminder_event(
    tasks: Iterable[Task],
    today: date,
    *,
    include_morning: bool,
    include_evening: bool,
) -> ReminderEvent | None:
    """Build a grouped reminder for the periods currently being checked."""

    morning_tasks = (
        pending_due_on_or_before(tasks, today) if include_morning else []
    )
    tomorrow = today + timedelta(days=1)
    evening_tasks = pending_due_on(tasks, tomorrow) if include_evening else []

    if not morning_tasks and not evening_tasks:
        return None

    combined: list[Task] = []
    seen: set[str] = set()
    for task in [*morning_tasks, *evening_tasks]:
        if task.id not in seen:
            seen.add(task.id)
            combined.append(task)

    if morning_tasks and evening_tasks:
        kind = "combined"
    elif morning_tasks:
        kind = "morning"
    else:
        kind = "evening"

    return ReminderEvent(
        kind=kind,
        tasks=tuple(combined),
        morning=bool(morning_tasks),
        evening=bool(evening_tasks),
    )


def reminder_copy(event: ReminderEvent) -> tuple[str, str]:
    if event.kind == "morning":
        title = "今天还有未完成的事"
        body = f"{event.count} 项截止任务还没有勾掉，别让它们悄悄过期。"
    elif event.kind == "evening":
        title = "明天有截止任务"
        body = f"提前看一眼，明天有 {event.count} 项任务到期。"
    else:
        title = "临近截止，提前收个尾"
        body = "今天的任务还没完成，明天的截止也临近了。"
    return title, body


class ReminderService(QObject):
    """Checks twice a day and emits a reminder for unfinished due tasks.

    Rules:
    - Around 09:00: tasks due today or already overdue.
    - Around 20:00: tasks due tomorrow.
    - One check per period per day, so a dismissed reminder is not repeated.
    - If reminders are disabled, the period is marked as checked without showing.
    """

    reminderDue = Signal(object)
    enabledChanged = Signal(bool)

    def __init__(
        self,
        store,
        settings: QSettings,
        *,
        clock: Callable[[], datetime] = datetime.now,
        auto_start: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._settings = settings
        self._clock = clock
        self._enabled = bool(self._settings.value("reminders/enabled", True, type=bool))
        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self.check_now)
        if auto_start:
            self._timer.start()
            QTimer.singleShot(STARTUP_DELAY_MS, self.check_now)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._settings.setValue("reminders/enabled", enabled)
        self._settings.sync()
        self.enabledChanged.emit(enabled)

    def stop(self) -> None:
        self._timer.stop()

    def _period_checked(self, key: str, today: date) -> bool:
        stored = self._settings.value(key, "", type=str)
        return stored == today.isoformat()

    def _mark_period_checked(self, key: str, today: date) -> None:
        self._settings.setValue(key, today.isoformat())

    def check_now(self, now: datetime | None = None) -> ReminderEvent | None:
        current = now or self._clock()
        today = current.date()
        check_morning = (
            current.time() >= MORNING_TIME
            and not self._period_checked("reminders/morning_checked", today)
        )
        check_evening = (
            current.time() >= EVENING_TIME
            and not self._period_checked("reminders/evening_checked", today)
        )
        if not check_morning and not check_evening:
            return None

        event = None
        if self._enabled:
            event = build_reminder_event(
                self._store.tasks,
                today,
                include_morning=check_morning,
                include_evening=check_evening,
            )

        if check_morning:
            self._mark_period_checked("reminders/morning_checked", today)
        if check_evening:
            self._mark_period_checked("reminders/evening_checked", today)
        self._settings.sync()

        if event is not None:
            self.reminderDue.emit(event)
        return event


def reminder_schedule_text() -> str:
    return "每天 09:00 提醒今天/逾期任务 · 到期前一天 20:00 提醒"
