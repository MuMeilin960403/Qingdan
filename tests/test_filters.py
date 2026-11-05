from __future__ import annotations

from datetime import date, datetime, timedelta

from qingdan.filters import (
    ViewKind,
    counts,
    date_range_text,
    due_marks,
    due_text,
    today_progress,
    visible_tasks,
    weekday_text,
)
from qingdan.models import Task


def task(
    title: str,
    due: str | None,
    *,
    completed: bool = False,
    completed_at: str | None = None,
    created_at: str = "2026-11-05T08:00:00+08:00",
) -> Task:
    return Task(
        id=title,
        title=title,
        due_date=due,
        completed=completed,
        created_at=created_at,
        completed_at=completed_at,
    )


TODAY = date(2026, 11, 5)


def make_tasks() -> list[Task]:
    return [
        task("逾期", "2026-11-03"),
        task("今天", "2026-11-05"),
        task("未来", "2026-11-08"),
        task("无日期", None),
        task(
            "今日完成",
            None,
            completed=True,
            completed_at="2026-11-05T09:30:00+08:00",
        ),
        task(
            "今天截止但更早完成",
            "2026-11-05",
            completed=True,
            completed_at="2026-11-04T18:00:00+08:00",
        ),
    ]


def test_counts_follow_the_four_navigation_views():
    result = counts(make_tasks(), TODAY)
    assert result[ViewKind.ALL] == 4
    assert result[ViewKind.TODAY] == 2
    assert result[ViewKind.UPCOMING] == 1
    assert result[ViewKind.COMPLETED] == 2


def test_today_includes_overdue_pending_and_tasks_completed_today():
    items = visible_tasks(make_tasks(), ViewKind.TODAY, TODAY)
    titles = {item.title for item in items}
    assert "逾期" in titles
    assert "今天" in titles
    assert "今日完成" in titles
    assert "今天截止但更早完成" not in titles
    assert "未来" not in titles


def test_upcoming_is_next_seven_days_only():
    all_tasks = make_tasks() + [task("七天后", (TODAY + timedelta(days=7)).isoformat())]
    items = visible_tasks(all_tasks, ViewKind.UPCOMING, TODAY)
    assert {item.title for item in items} == {"未来", "七天后"}


def test_date_view_filters_exactly_on_due_date():
    items = visible_tasks(make_tasks(), ViewKind.DATE, TODAY, date(2026, 11, 5))
    assert {item.title for item in items} == {"今天", "今天截止但更早完成"}
    assert visible_tasks(make_tasks(), ViewKind.DATE, TODAY, None) == []


def test_sort_puts_pending_and_earliest_due_first():
    items = visible_tasks(make_tasks(), ViewKind.ALL, TODAY)
    pending = [item for item in items if not item.completed]
    assert [item.title for item in pending[:3]] == ["逾期", "今天", "未来"]
    assert pending[-1].title == "无日期"
    assert items[-1].completed


def test_labels_and_progress():
    assert due_text(None, TODAY) == "无截止日期"
    assert due_text(date(2026, 11, 5), TODAY) == "今天"
    assert due_text(date(2026, 11, 6), TODAY) == "明天"
    assert due_text(date(2026, 11, 4), TODAY) == "昨天"
    assert due_text(date(2026, 11, 2), TODAY) == "逾期 3 天"
    assert due_text(date(2026, 12, 9), TODAY) == "12月9日"
    assert weekday_text(date(2026, 11, 5)) == "星期四"
    assert "11月6日" in date_range_text(date(2026, 11, 6), date(2026, 11, 12))

    done, total, percent = today_progress(make_tasks(), TODAY)
    assert (done, total) == (1, 3)
    assert percent == 33


def test_due_marks_distinguish_pending_from_completed_only():
    tasks = [
        task("完成", "2026-11-05", completed=True, completed_at="2026-11-05T10:00:00+08:00"),
        task("待办", "2026-11-06"),
    ]
    marks = due_marks(tasks)
    assert marks[date(2026, 11, 5)] is False
    assert marks[date(2026, 11, 6)] is True


def test_invalid_completed_at_does_not_crash_task_property():
    malformed = task("异常完成时间", None, completed=True, completed_at="not-a-date")
    assert malformed.completed_on is None
    assert visible_tasks([malformed], ViewKind.TODAY, TODAY) == []
