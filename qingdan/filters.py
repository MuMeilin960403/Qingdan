"""Pure task filtering, counting and date-label helpers."""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum
from typing import Iterable

from .models import Task

WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


class ViewKind(str, Enum):
    ALL = "all"
    TODAY = "today"
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    DATE = "date"


def pending(tasks: Iterable[Task]) -> list[Task]:
    return [task for task in tasks if not task.completed]


def completed(tasks: Iterable[Task]) -> list[Task]:
    return [task for task in tasks if task.completed]


def visible_tasks(
    tasks: Iterable[Task],
    view: ViewKind,
    today: date,
    selected_date: date | None = None,
) -> list[Task]:
    items = list(tasks)
    if view is ViewKind.DATE:
        if selected_date is None:
            return []
        items = [task for task in items if task.due == selected_date]
    elif view is ViewKind.COMPLETED:
        items = [task for task in items if task.completed]
    elif view is ViewKind.TODAY:
        items = [
            task
            for task in items
            if (
                (not task.completed and task.due is not None and task.due <= today)
                or (task.completed and task.completed_on == today)
            )
        ]
    elif view is ViewKind.UPCOMING:
        end = today + timedelta(days=7)
        items = [
            task
            for task in items
            if task.due is not None and today < task.due <= end
        ]
    # ALL intentionally keeps everything.

    return sort_tasks(items)


def sort_tasks(tasks: Iterable[Task]) -> list[Task]:
    """Pending tasks first, then nearest deadlines, then newest first."""

    tasks = list(tasks)

    def key(task: Task) -> tuple:
        if task.completed:
            return (
                1,
                _timestamp_key(task.completed_at),
                _timestamp_key(task.created_at),
            )
        return (
            0,
            0 if task.due is not None else 1,
            task.due or date.max,
            _negative_created_key(task.created_at),
        )

    return sorted(tasks, key=key)


def _timestamp_key(value: str | None) -> str:
    # ISO timestamps sort lexically when stored by this app. For completed tasks
    # we want the newest completed item first; invert the string using a stable
    # trick by returning its characters' ordinal complement.
    text = value or ""
    return "".join(chr(0x10FFFF - ord(char)) for char in text)


def _negative_created_key(value: str) -> str:
    return "".join(chr(0x10FFFF - ord(char)) for char in (value or ""))


def counts(tasks: Iterable[Task], today: date) -> dict[ViewKind, int]:
    items = list(tasks)
    tomorrow = today + timedelta(days=1)
    end = today + timedelta(days=7)
    return {
        ViewKind.ALL: sum(not task.completed for task in items),
        ViewKind.TODAY: sum(
            not task.completed and task.due is not None and task.due <= today
            for task in items
        ),
        ViewKind.UPCOMING: sum(
            not task.completed and task.due is not None and tomorrow <= task.due <= end
            for task in items
        ),
        ViewKind.COMPLETED: sum(task.completed for task in items),
    }


def due_text(due: date | None, today: date, *, completed: bool = False) -> str:
    if due is None:
        return "无截止日期"
    delta = (due - today).days
    if delta == 0:
        return "今天"
    if delta == 1:
        return "明天"
    if delta == -1:
        return "昨天"
    if delta < 0 and not completed:
        return f"逾期 {-delta} 天"
    if due.year == today.year:
        return f"{due.month}月{due.day}日"
    return f"{due.year}/{due.month}/{due.day}"


def full_date_text(value: date) -> str:
    return f"{value.year}年{value.month}月{value.day}日"


def weekday_text(value: date) -> str:
    return WEEKDAYS[value.weekday()]


def date_range_text(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{start.month}月{start.day}日 – {end.day}日"
    if start.year == end.year:
        return f"{start.month}月{start.day}日 – {end.month}月{end.day}日"
    return f"{start.year}/{start.month}/{start.day} – {end.year}/{end.month}/{end.day}"


def today_progress(tasks: Iterable[Task], today: date) -> tuple[int, int, int]:
    """Return completed, total and percent for the Today focus."""

    focus = visible_tasks(tasks, ViewKind.TODAY, today)
    total = len(focus)
    done = sum(task.completed for task in focus)
    percent = round(done / total * 100) if total else 0
    return done, total, percent


def due_marks(tasks: Iterable[Task]) -> dict[date, bool]:
    """Map dates to True when at least one pending task is due that day."""

    marks: dict[date, bool] = {}
    for task in tasks:
        due = task.due
        if due is None:
            continue
        marks[due] = marks.get(due, False) or not task.completed
    return marks
