from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QSettings

from qingdan.models import Task
from qingdan.reminders import (
    ReminderService,
    build_reminder_event,
    pending_due_on,
    pending_due_on_or_before,
    reminder_copy,
)
from qingdan.store import TaskStore

TODAY = date(2026, 11, 5)
TOMORROW = date(2026, 11, 6)


def task(title: str, due: date | None, *, completed: bool = False) -> Task:
    return Task(
        id=title,
        title=title,
        due_date=due.isoformat() if due else None,
        completed=completed,
        created_at="2026-11-01T09:00:00+08:00",
        completed_at="2026-11-05T10:00:00+08:00" if completed else None,
    )


def make_tasks() -> list[Task]:
    return [
        task("逾期任务", date(2026, 11, 3)),
        task("今日任务", TODAY),
        task("明日任务", TOMORROW),
        task("已完成任务", TODAY, completed=True),
    ]


def test_pending_due_helpers_exclude_completed_and_future():
    items = make_tasks()
    assert [item.title for item in pending_due_on_or_before(items, TODAY)] == [
        "逾期任务",
        "今日任务",
    ]
    assert [item.title for item in pending_due_on(items, TOMORROW)] == ["明日任务"]


def test_build_morning_and_evening_events():
    morning = build_reminder_event(
        make_tasks(), TODAY, include_morning=True, include_evening=False
    )
    assert morning is not None
    assert morning.kind == "morning"
    assert [item.title for item in morning.tasks] == ["逾期任务", "今日任务"]
    title, body = reminder_copy(morning)
    assert "今天" in title
    assert "2 项" in body

    evening = build_reminder_event(
        make_tasks(), TODAY, include_morning=False, include_evening=True
    )
    assert evening is not None
    assert evening.kind == "evening"
    assert [item.title for item in evening.tasks] == ["明日任务"]
    assert "明天" in reminder_copy(evening)[0]


def test_build_combined_event():
    event = build_reminder_event(
        make_tasks(), TODAY, include_morning=True, include_evening=True
    )
    assert event is not None
    assert event.kind == "combined"
    assert event.morning and event.evening
    assert {item.title for item in event.tasks} == {"逾期任务", "今日任务", "明日任务"}


def test_no_event_without_pending_due_tasks():
    assert (
        build_reminder_event(
            [task("无日期", None), task("完成", TODAY, completed=True)],
            TODAY,
            include_morning=True,
            include_evening=True,
        )
        is None
    )


def make_service(qtbot, tmp_path, store, clock):
    settings = QSettings(
        str(tmp_path / "reminder-settings.ini"),
        QSettings.Format.IniFormat,
    )
    service = ReminderService(
        store,
        settings,
        clock=lambda: clock,
        auto_start=False,
    )
    received: list[object] = []
    service.reminderDue.connect(received.append)
    return service, received, settings


def test_service_morning_check_and_dedupe(qtbot, tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    store.add("今天的任务", TODAY)
    service, received, _settings = make_service(
        qtbot, tmp_path, store, datetime(2026, 11, 5, 8, 59)
    )

    assert service.check_now() is None
    assert received == []

    service._clock = lambda: datetime(2026, 11, 5, 9, 5)
    event = service.check_now()
    assert event is not None and event.kind == "morning"
    assert len(received) == 1
    assert service.check_now() is None
    assert len(received) == 1

    # The next day, the still-unfinished task is overdue and gets a new nudge.
    event = service.check_now(datetime(2026, 11, 6, 9, 1))
    assert event is not None and event.kind == "morning"
    assert event.tasks[0].title == "今天的任务"


def test_service_evening_reminder_for_tomorrow(qtbot, tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    store.add("明天的任务", TOMORROW)
    service, received, _settings = make_service(
        qtbot, tmp_path, store, datetime(2026, 11, 5, 20, 30)
    )
    event = service.check_now()
    assert event is not None and event.kind == "evening"
    assert len(received) == 1
    assert event.tasks[0].title == "明天的任务"


def test_disabled_service_marks_check_periods_without_notifying(qtbot, tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    store.add("今天的任务", TODAY)
    service, received, _settings = make_service(
        qtbot, tmp_path, store, datetime(2026, 11, 5, 9, 30)
    )
    service.set_enabled(False)
    assert service.check_now() is None
    assert received == []
    assert service.check_now() is None

    service.set_enabled(True)
    assert service.check_now() is None
    assert received == []


def test_reminder_marks_are_persisted_across_instances(qtbot, tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    store.add("今天的任务", TODAY)
    service1, received1, _settings = make_service(
        qtbot, tmp_path, store, datetime(2026, 11, 5, 9, 30)
    )
    assert service1.check_now() is not None
    assert len(received1) == 1

    service2, received2, _settings2 = make_service(
        qtbot, tmp_path, store, datetime(2026, 11, 5, 10, 0)
    )
    assert service2.check_now() is None
    assert received2 == []
