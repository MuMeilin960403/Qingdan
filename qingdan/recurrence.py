"""Pure recurrence rules for repeating tasks."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

REPEAT_RULES = ("daily", "weekdays", "weekly", "monthly")

REPEAT_LABELS: dict[str | None, str] = {
    None: "不重复",
    "daily": "每天",
    "weekdays": "工作日",
    "weekly": "每周",
    "monthly": "每月",
}

REPEAT_HINTS: dict[str | None, str] = {
    None: "只做这一次",
    "daily": "每天生成一次",
    "weekdays": "周一至周五生成",
    "weekly": "每周同一天生成",
    "monthly": "每月同一天生成",
}


def normalize_repeat(value: object) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or value not in REPEAT_RULES:
        raise ValueError(f"Invalid repeat rule: {value!r}")
    return value


def repeat_label(value: str | None, empty: str = "重复") -> str:
    return REPEAT_LABELS.get(value, empty)


def _advance_one(current: date, rule: str) -> date:
    if rule == "daily":
        return current + timedelta(days=1)
    if rule == "weekdays":
        candidate = current + timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        return candidate
    if rule == "weekly":
        return current + timedelta(days=7)
    if rule == "monthly":
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(current.day, last_day))
    raise ValueError(f"Invalid repeat rule: {rule!r}")


def next_occurrence(current_due: date, rule: str, today: date) -> date:
    """Return the next scheduled date strictly after today.

    If a recurring task is completed late, missed occurrences are skipped so the
    next task is a future task instead of another overdue backlog item.
    """

    rule = normalize_repeat(rule)  # type: ignore[assignment]
    if rule is None:
        raise ValueError("A repeat rule is required")
    candidate = _advance_one(current_due, rule)
    guard = 0
    while candidate <= today:
        candidate = _advance_one(candidate, rule)
        guard += 1
        if guard > 5000:
            raise ValueError("Repeat rule produced too many iterations")
    return candidate
