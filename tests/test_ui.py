from __future__ import annotations

from datetime import date, timedelta

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QLabel

from qingdan.filters import ViewKind
from qingdan.reminders import build_reminder_event
from qingdan.store import StoreError, TaskStore
from qingdan.ui.main_window import MainWindow
from qingdan.ui.mini_window import MiniTaskRow, MiniWindow
from qingdan.ui.task_row import TaskRow


def settle() -> None:
    QApplication.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


@pytest.fixture
def make_window(qtbot, tmp_path):
    windows: list[MainWindow] = []

    def build(*tasks: tuple[str, object]) -> MainWindow:
        store = TaskStore(tmp_path / f"tasks-{len(windows)}.json")
        for title, due in tasks:
            store.add(title, due if isinstance(due, date) else None)
        window = MainWindow(store, persist_geometry=False, enable_reminders=False)
        qtbot.addWidget(window)
        window.resize(1220, 820)
        window.show()
        settle()
        windows.append(window)
        return window

    yield build
    for window in windows:
        window.close()


def rows(window: MainWindow) -> list[TaskRow]:
    return window.task_panel.findChildren(TaskRow)


def test_initial_today_view_and_navigation(make_window):
    today = date.today()
    window = make_window(
        ("过期的任务", today - timedelta(days=1)),
        ("今天的任务", today),
        ("未来的任务", today + timedelta(days=2)),
        ("无日期任务", None),
    )
    assert window.current_view is ViewKind.TODAY
    assert window.task_panel.title_label.text() == "今天"
    assert window.task_panel.composer.due == today
    assert window.task_panel.composer.isVisible()
    assert window.sidebar.nav_buttons[ViewKind.TODAY].isChecked()
    assert {row.task.title for row in rows(window)} == {"过期的任务", "今天的任务"}

    window.sidebar.nav_buttons[ViewKind.ALL].click()
    settle()
    assert window.current_view is ViewKind.ALL
    assert window.task_panel.title_label.text() == "全部任务"
    assert window.task_panel.composer.due is None
    assert len(rows(window)) == 4

    window.sidebar.nav_buttons[ViewKind.UPCOMING].click()
    settle()
    assert window.task_panel.title_label.text() == "未来 7 天"
    assert {row.task.title for row in rows(window)} == {"未来的任务"}

    window.sidebar.nav_buttons[ViewKind.COMPLETED].click()
    settle()
    assert window.task_panel.title_label.text() == "已完成"
    assert not window.task_panel.composer.isVisible()


def test_add_task_with_enter_and_default_due(make_window, qtbot):
    window = make_window()
    composer = window.task_panel.composer
    composer.input.setText("给植物浇水")
    assert composer.add_button.isEnabled()
    qtbot.keyClick(composer.input, Qt.Key.Key_Return)
    settle()

    assert len(window.store.tasks) == 1
    task = window.store.tasks[0]
    assert task.title == "给植物浇水"
    assert task.due == date.today()
    assert composer.input.text() == ""
    assert not composer.add_button.isEnabled()
    assert [row.task.title for row in rows(window)] == ["给植物浇水"]


def test_failed_add_keeps_draft_and_shows_error(make_window, qtbot, monkeypatch):
    window = make_window()
    composer = window.task_panel.composer

    def fail_add(title, due, repeat):
        raise StoreError("模拟磁盘错误")

    monkeypatch.setattr(window.store, "add", fail_add)
    composer.input.setText("不要丢掉这段草稿")
    qtbot.keyClick(composer.input, Qt.Key.Key_Return)
    settle()

    assert composer.input.text() == "不要丢掉这段草稿"
    assert "保存失败" in window.topbar.status_label.text()
    assert window.store.tasks == ()


def test_checkbox_completes_and_updates_progress(make_window, qtbot):
    today = date.today()
    window = make_window(("要完成的任务", today), ("另一项", today))
    row = rows(window)[0]
    qtbot.mouseClick(row.check, Qt.MouseButton.LeftButton)
    settle()

    task = window.store.get(row.task_id)
    assert task is not None and task.completed is True
    assert window.store.get(row.task_id).completed_at is not None
    assert rows(window)[-1].task.completed is True
    assert window.task_panel.subtitle.text().startswith("1 项待办")

    completed_row = rows(window)[-1]
    qtbot.mouseClick(completed_row.check, Qt.MouseButton.LeftButton)
    settle()
    assert window.store.get(completed_row.task_id).completed is False
    assert window.task_panel.subtitle.text().startswith("2 项待办")


def test_inline_rename_and_delete(make_window):
    window = make_window(("旧标题", None))
    window.sidebar.nav_buttons[ViewKind.ALL].click()
    settle()
    row = rows(window)[0]
    row.title_edit.begin_edit()
    row.title_edit.setText("一个新标题")
    row.title_edit._finish_edit()
    settle()
    assert window.store.tasks[0].title == "一个新标题"

    row = rows(window)[0]
    row._show_delete(True)
    assert row.delete_button.isEnabled()
    row.delete_button.click()
    settle()
    assert window.store.tasks == ()
    assert rows(window) == []
    assert window.task_panel.composer.isVisible()


def test_composer_date_picker_sets_due_date(make_window):
    window = make_window()
    panel = window.task_panel
    panel._open_composer_date(panel.composer.due_button)
    settle()
    popup = panel._date_popup
    assert popup is not None and popup.isVisible()
    popup.quick_buttons[1].click()
    settle()
    assert panel.composer.due == date.today() + timedelta(days=1)
    assert not popup.isVisible()


def test_task_due_date_can_be_edited_from_row(make_window):
    window = make_window(("调整截止日期", None))
    window.sidebar.nav_buttons[ViewKind.ALL].click()
    settle()
    row = rows(window)[0]
    task_id = row.task_id
    panel = window.task_panel
    panel._on_task_date_requested(task_id, row.due_pill, None)
    settle()
    popup = panel._date_popup
    assert popup is not None
    target = date.today() + timedelta(days=4)
    for button in popup.calendar.buttons:
        if button.day == target:
            button.click()
            break
    settle()
    assert window.store.get(task_id).due == target
    assert not popup.isVisible()


def test_calendar_click_filters_to_date_and_reset(make_window):
    today = date.today()
    target = today + timedelta(days=3)
    window = make_window(("目标日期任务", target), ("今天的任务", today))
    window._on_calendar_date(target)
    settle()
    assert window.current_view is ViewKind.DATE
    assert window.selected_date == target
    assert window.task_panel.composer.due == target
    assert window.task_panel.title_label.text() == f"{target.month}月{target.day}日"
    assert window.calendar_reset.isVisible()
    assert not any(
        button.isChecked() for button in window.sidebar.nav_buttons.values()
    )
    assert [row.task.title for row in rows(window)] == ["目标日期任务"]

    window.calendar_reset.click()
    settle()
    assert window.current_view is ViewKind.TODAY
    assert not window.calendar_reset.isVisible()
    assert window.selected_date is None


def test_empty_state_and_date_input(make_window):
    window = make_window()
    assert rows(window) == []
    labels = [label.text() for label in window.task_panel.findChildren(QLabel)]
    assert "今天还没有安排" in labels

    window._on_calendar_date(date.today() + timedelta(days=1))
    settle()
    assert window.task_panel.title_label.text() != "今天"
    assert window.task_panel.composer.due == date.today() + timedelta(days=1)


def test_due_pill_hides_for_completed_task_without_date(make_window):
    window = make_window(("已完成且无日期", None))
    window.sidebar.nav_buttons[ViewKind.ALL].click()
    settle()
    row = rows(window)[0]
    row.check.click()
    settle()
    completed_rows = [item for item in rows(window) if item.task.completed]
    assert len(completed_rows) == 1
    assert completed_rows[0].task.due is None
    assert completed_rows[0].due_pill.isVisible() is False


def test_mini_window_shows_today_and_can_switch_to_all(make_window):
    today = date.today()
    window = make_window(
        ("今天的任务", today),
        ("未来的任务", today + timedelta(days=2)),
        ("无日期任务", None),
    )
    window.show_mini()
    settle()

    mini = window._mini
    assert isinstance(mini, MiniWindow)
    assert mini.isVisible()
    assert not window.isVisible()
    assert mini.today == today
    mini_rows = mini.findChildren(MiniTaskRow)
    assert {row.task.title for row in mini_rows} == {"今天的任务"}

    mini.all_tab.click()
    settle()
    mini_rows = mini.findChildren(MiniTaskRow)
    assert {row.task.title for row in mini_rows} == {
        "今天的任务",
        "未来的任务",
        "无日期任务",
    }

    window._restore_full()
    settle()
    assert window.isVisible()
    assert not mini.isVisible()


def test_mini_checkbox_toggles_and_adds_today(qtbot, make_window):
    today = date.today()
    window = make_window(("迷你任务", today))
    window.show_mini()
    settle()
    mini = window._mini
    assert mini is not None

    mini_row = mini.findChildren(MiniTaskRow)[0]
    qtbot.mouseClick(mini_row.check, Qt.MouseButton.LeftButton)
    settle()
    assert window.store.tasks[0].completed is True
    assert mini.findChildren(MiniTaskRow) == []
    assert "清空" in mini.title_label.text()

    mini.input.setText("从迷你窗口添加")
    qtbot.keyClick(mini.input, Qt.Key.Key_Return)
    settle()
    assert len(window.store.tasks) == 2
    added = [task for task in window.store.tasks if task.title == "从迷你窗口添加"][0]
    assert added.due == today
    assert mini.input.text() == ""
    assert len(mini.findChildren(MiniTaskRow)) == 1


def test_mini_reminders_are_disabled_in_tests(make_window):
    window = make_window()
    assert window._reminder_service is None


def test_add_repeating_task_from_composer(make_window, qtbot):
    window = make_window()
    composer = window.task_panel.composer
    composer.set_repeat("daily")
    assert composer.due == date.today()
    composer.input.setText("每天喝水")
    qtbot.keyClick(composer.input, Qt.Key.Key_Return)
    settle()

    assert len(window.store.tasks) == 1
    task = window.store.tasks[0]
    assert task.title == "每天喝水"
    assert task.repeat == "daily"
    assert task.due == date.today()
    assert composer.repeat is None
    assert composer.input.text() == ""


def test_repeating_task_completion_creates_next_and_undo_removes_it(make_window, qtbot):
    window = make_window()
    task = window.store.add("每天拉伸", date.today(), "daily")
    window._refresh()
    settle()

    row = next(item for item in rows(window) if item.task_id == task.id)
    assert row.repeat_pill.repeat == "daily"
    qtbot.mouseClick(row.check, Qt.MouseButton.LeftButton)
    settle()

    assert len(window.store.tasks) == 2
    current = window.store.get(task.id)
    successor = next(item for item in window.store.tasks if item.id != task.id)
    assert current.completed is True
    assert successor.title == "每天拉伸"
    assert successor.repeat == "daily"
    assert successor.due == date.today() + timedelta(days=1)
    assert "下次" in window.topbar.status_label.text()

    completed_row = next(item for item in rows(window) if item.task_id == task.id)
    qtbot.mouseClick(completed_row.check, Qt.MouseButton.LeftButton)
    settle()

    assert len(window.store.tasks) == 1
    assert window.store.get(task.id).completed is False


def test_change_repeat_defaults_due_to_today(make_window):
    window = make_window(("无日期任务", None))
    window.sidebar.nav_buttons[ViewKind.ALL].click()
    settle()
    task = window.store.tasks[0]
    window._change_repeat(task.id, "weekly")
    settle()

    assert window.store.get(task.id).repeat == "weekly"
    assert window.store.get(task.id).due == date.today()


def test_reminder_popup_can_restore_the_full_window(make_window):
    window = make_window(("今天要交的东西", date.today()))
    window.show_mini()
    settle()
    event = build_reminder_event(
        window.store.tasks,
        date.today(),
        include_morning=True,
        include_evening=False,
    )
    assert event is not None
    window._show_reminder(event)
    settle()
    popup = window._reminder_popup
    assert popup is not None and popup.isVisible()
    popup.open_button.click()
    settle()
    assert window.isVisible()
    assert window._mini is not None and not window._mini.isVisible()
    popup.close()


def test_mini_window_pin_toggle_keeps_window_available(make_window):
    window = make_window()
    window.show_mini()
    settle()
    mini = window._mini
    assert mini is not None and mini.isVisible()
    was_pinned = mini._pinned
    mini.pin_button.click()
    settle()
    assert mini._pinned is (not was_pinned)
    assert mini.isVisible()
    mini.pin_button.click()
    settle()
    assert mini._pinned is was_pinned
