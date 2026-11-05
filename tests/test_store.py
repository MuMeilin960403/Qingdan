from __future__ import annotations

import json
from datetime import date

import pytest

from qingdan.models import Task
from qingdan.store import SCHEMA_VERSION, StoreError, TaskStore


def test_add_toggle_rename_and_reload(tmp_path):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)
    task = store.add("  写周报  ", date(2026, 11, 5))
    assert task.title == "写周报"
    assert task.due == date(2026, 11, 5)
    assert path.exists()

    store.set_completed(task.id, True)
    assert store.get(task.id).completed is True
    assert store.get(task.id).completed_at is not None

    store.rename(task.id, "写完周报")
    store.set_due(task.id, None)
    store2 = TaskStore(path)
    loaded = store2.get(task.id)
    assert loaded is not None
    assert loaded.title == "写完周报"
    assert loaded.completed is True
    assert loaded.due is None

    store2.set_completed(task.id, False)
    assert TaskStore(path).get(task.id).completed is False
    assert TaskStore(path).get(task.id).completed_at is None


def test_delete_and_unknown_id(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task = store.add("一件小事")
    assert store.set_completed("missing", True) is None
    assert store.rename("missing", "x") is None
    assert store.set_due("missing", None) is None
    assert store.delete(task.id) is True
    assert store.delete(task.id) is False
    assert store.tasks == ()


def test_failed_save_rolls_back_in_memory_changes(tmp_path, monkeypatch):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)
    existing = store.add("原任务", date(2026, 11, 5))
    before = TaskStore(path).tasks

    def fail() -> None:
        raise StoreError("模拟磁盘错误")

    monkeypatch.setattr(store, "_save", fail)

    with pytest.raises(StoreError):
        store.add("不会保存", date(2026, 11, 6))
    assert [task.title for task in store.tasks] == ["原任务"]

    with pytest.raises(StoreError):
        store.set_completed(existing.id, True)
    assert store.get(existing.id).completed is False
    assert store.get(existing.id).completed_at is None

    with pytest.raises(StoreError):
        store.rename(existing.id, "改了但没保存")
    assert store.get(existing.id).title == "原任务"

    with pytest.raises(StoreError):
        store.set_due(existing.id, None)
    assert store.get(existing.id).due == date(2026, 11, 5)

    with pytest.raises(StoreError):
        store.delete(existing.id)
    assert store.get(existing.id) is not None

    # The on-disk file was never changed.
    assert TaskStore(path).tasks == before


def test_empty_title_is_rejected(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    with pytest.raises(ValueError):
        store.add("   ")
    task = store.add("保留标题")
    assert store.rename(task.id, " ") is None
    assert store.get(task.id).title == "保留标题"


def test_task_schema_validation():
    task = Task.from_dict(
        {
            "id": "abc",
            "title": "测试",
            "due_date": "2026-11-05",
            "completed": True,
            "created_at": "2026-11-04T09:00:00+08:00",
            "completed_at": "2026-11-05T10:00:00+08:00",
        }
    )
    assert task.due == date(2026, 11, 5)
    assert task.completed_on == date(2026, 11, 5)
    with pytest.raises(ValueError):
        Task.from_dict({"id": "abc", "title": "", "due_date": None})


def test_saved_file_has_expected_shape(tmp_path):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)
    store.add("检查 JSON", date(2026, 11, 5))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["app"] == "Qingdan"
    assert payload["version"] == SCHEMA_VERSION
    assert payload["tasks"][0]["title"] == "检查 JSON"


def test_corrupt_file_is_backed_up_and_app_starts_empty(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text("{ this is not JSON", encoding="utf-8")
    store = TaskStore(path)
    assert store.tasks == ()
    assert store.load_warning is not None
    assert not path.exists()
    backups = list(tmp_path.glob("tasks.corrupt-*.json"))
    assert len(backups) == 1
    assert "not JSON" in backups[0].read_text(encoding="utf-8")

    # A normal save after recovery works and does not overwrite the backup.
    store.add("恢复后的任务")
    assert TaskStore(path).tasks[0].title == "恢复后的任务"
    assert len(list(tmp_path.glob("tasks.corrupt-*.json"))) == 1


def test_duplicate_ids_recover_to_blank_file(tmp_path):
    path = tmp_path / "tasks.json"
    record = {
        "id": "same",
        "title": "重复",
        "due_date": None,
        "completed": False,
        "created_at": "2026-11-05T10:00:00+08:00",
        "completed_at": None,
    }
    path.write_text(
        json.dumps(
            {"app": "Qingdan", "version": 1, "tasks": [record, record]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store = TaskStore(path)
    assert store.tasks == ()
    assert store.load_warning is not None
    assert len(list(tmp_path.glob("tasks.corrupt-*.json"))) == 1
