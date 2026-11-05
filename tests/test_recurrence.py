from __future__ import annotations

from datetime import date

import pytest

from qingdan.models import Task
from qingdan.recurrence import (
    REPEAT_LABELS,
    next_occurrence,
    normalize_repeat,
    repeat_label,
)
from qingdan.store import StoreError, TaskStore


def test_repeat_labels_and_validation():
    assert repeat_label(None) == "不重复"
    assert repeat_label("daily") == "每天"
    assert repeat_label("workdays") == "重复"
    assert normalize_repeat(None) is None
    assert normalize_repeat("") is None
    assert normalize_repeat("weekly") == "weekly"
    with pytest.raises(ValueError):
        normalize_repeat("yearly")
    assert set(REPEAT_LABELS) == {None, "daily", "weekdays", "weekly", "monthly"}


def test_next_daily_skips_missed_days():
    today = date(2026, 11, 5)
    assert next_occurrence(today, "daily", today) == date(2026, 11, 6)
    assert next_occurrence(date(2026, 11, 2), "daily", today) == date(2026, 11, 6)
    assert next_occurrence(date(2026, 11, 10), "daily", today) == date(2026, 11, 11)


def test_next_weekday_skips_weekend():
    friday = date(2026, 11, 6)
    assert next_occurrence(friday, "weekdays", friday) == date(2026, 11, 9)
    monday = date(2026, 11, 9)
    assert next_occurrence(monday, "weekdays", monday) == date(2026, 11, 10)


def test_next_weekly_and_monthly():
    today = date(2026, 11, 5)
    assert next_occurrence(today, "weekly", today) == date(2026, 11, 12)
    assert next_occurrence(date(2026, 10, 31), "monthly", today) == date(2026, 11, 30)
    assert next_occurrence(date(2026, 11, 30), "monthly", today) == date(2026, 12, 30)


def test_next_occurrence_requires_a_rule():
    with pytest.raises(ValueError):
        next_occurrence(date(2026, 11, 5), "", date(2026, 11, 5))


def test_repeat_requires_a_due_date():
    with pytest.raises(ValueError):
        Task.create("没有截止日期的重复任务", None, "daily")


def test_complete_recurring_creates_next_occurrence_and_persists(tmp_path):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)
    task = store.add("每天喝水", date(2026, 11, 5), "daily")

    current, follow_up = store.complete_recurring(task.id, date(2026, 11, 5))
    assert current is not None and current.completed is True
    assert follow_up is not None
    assert follow_up.title == "每天喝水"
    assert follow_up.due == date(2026, 11, 6)
    assert follow_up.repeat == "daily"
    assert follow_up.repeat_parent_id == task.id
    assert follow_up.completed is False

    reloaded = TaskStore(path)
    assert len(reloaded.tasks) == 2
    finished = next(item for item in reloaded.tasks if item.id == task.id)
    upcoming = next(item for item in reloaded.tasks if item.id == follow_up.id)
    assert finished.completed is True
    assert upcoming.due == date(2026, 11, 6)
    assert upcoming.repeat == "daily"


def test_reopen_recurring_removes_pending_successor(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("每周复盘", date(2026, 11, 6), "weekly")
    store.complete_recurring(task.id, date(2026, 11, 6))
    assert len(store.tasks) == 2

    reopened = store.reopen_recurring(task.id)
    assert reopened is not None and reopened.completed is False
    assert len(store.tasks) == 1
    assert store.tasks[0].id == task.id


def test_overdue_repeat_advances_to_a_future_date(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("每天整理桌面", date(2026, 11, 1), "daily")
    _current, follow_up = store.complete_recurring(task.id, date(2026, 11, 5))
    assert follow_up is not None and follow_up.due == date(2026, 11, 6)


def test_set_repeat_supplies_default_due_and_clear_due_clears_repeat(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("交水电费", None)
    changed = store.set_repeat(task.id, "monthly", default_due=date(2026, 11, 5))
    assert changed is not None
    assert changed.repeat == "monthly"
    assert changed.due == date(2026, 11, 5)

    cleared = store.set_due(task.id, None)
    assert cleared is not None
    assert cleared.due is None
    assert cleared.repeat is None


def test_recurring_save_failures_roll_back(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("每天记录", date(2026, 11, 5), "daily")

    def fail() -> None:
        raise StoreError("模拟磁盘错误")

    monkeypatch.setattr(store, "_save", fail)
    with pytest.raises(StoreError):
        store.complete_recurring(task.id, date(2026, 11, 5))
    assert len(store.tasks) == 1
    assert store.get(task.id).completed is False

    monkeypatch.undo()
    store.complete_recurring(task.id, date(2026, 11, 5))
    assert len(store.tasks) == 2
    monkeypatch.setattr(store, "_save", fail)
    with pytest.raises(StoreError):
        store.reopen_recurring(task.id)
    assert len(store.tasks) == 2
    assert store.get(task.id).completed is True
