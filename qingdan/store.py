"""Local-first JSON persistence for Qingdan."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

from .models import Task, now_iso
from .recurrence import next_occurrence, normalize_repeat

SCHEMA_VERSION = 1


class StoreError(RuntimeError):
    """Raised when the task file cannot be written."""


class TaskStore:
    """A small, synchronous, atomically-saved task store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._tasks: list[Task] = []
        self.load_warning: str | None = None
        self.load()

    @property
    def tasks(self) -> tuple[Task, ...]:
        return tuple(self._tasks)

    def load(self) -> None:
        self._tasks = []
        self.load_warning = None
        if not self.path.exists():
            return

        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Root is not an object")
            records = payload.get("tasks")
            if not isinstance(records, list):
                raise ValueError("Missing task list")
            tasks = [Task.from_dict(record) for record in records]
            ids: set[str] = set()
            for task in tasks:
                if task.id in ids:
                    raise ValueError("Duplicate task id")
                ids.add(task.id)
            self._tasks = tasks
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            backup = self._backup_corrupt_file()
            suffix = f"，原文件已备份为 {backup.name}" if backup else ""
            self.load_warning = f"任务数据无法读取，已新建空白清单{suffix}。"
            self._tasks = []
            # Keep the original file out of the way so the next successful save
            # cannot overwrite evidence of the corrupted data.
            if backup is None and self.path.exists():
                raise StoreError(self.load_warning) from exc

    def _backup_corrupt_file(self) -> Path | None:
        if not self.path.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"{self.path.stem}.corrupt-{stamp}{self.path.suffix}")
        try:
            self.path.replace(backup)
        except OSError:
            try:
                shutil.copy2(self.path, backup)
                self.path.unlink()
            except OSError:
                return None
        return backup

    def _save(self) -> None:
        payload = {
            "app": "Qingdan",
            "version": SCHEMA_VERSION,
            "tasks": [task.to_dict() for task in self._tasks],
        }
        tmp: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Use a unique sibling temp file. This keeps writes atomic while
            # avoiding collisions with another instance or a sync/indexing tool
            # that may briefly hold a previous *.tmp file open on Windows.
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            tmp = Path(tmp_name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            for attempt in range(3):
                try:
                    os.replace(tmp, self.path)
                    tmp = None
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.06 * (attempt + 1))
        except OSError as exc:
            if tmp is not None:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            raise StoreError(f"无法保存任务：{exc}") from exc

    def add(
        self,
        title: str,
        due: date | None = None,
        repeat: str | None = None,
    ) -> Task:
        task = Task.create(title, due, repeat)
        self._tasks.append(task)
        try:
            self._save()
        except StoreError:
            self._tasks.pop()
            raise
        return task

    def get(self, task_id: str) -> Task | None:
        return next((task for task in self._tasks if task.id == task_id), None)

    def set_completed(self, task_id: str, completed: bool) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        if task.completed == completed:
            return task
        previous = (task.completed, task.completed_at)
        task.completed = completed
        task.completed_at = now_iso() if completed else None
        try:
            self._save()
        except StoreError:
            task.completed, task.completed_at = previous
            raise
        return task

    def set_repeat(
        self,
        task_id: str,
        repeat: str | None,
        default_due: date | None = None,
    ) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        normalized = normalize_repeat(repeat)
        if normalized == task.repeat:
            return task
        previous = (task.repeat, task.due_date)
        if normalized is not None and task.due is None:
            due = default_due or date.today()
            task.due_date = due.isoformat()
        task.repeat = normalized
        try:
            self._save()
        except StoreError:
            task.repeat, task.due_date = previous
            raise
        return task

    def complete_recurring(
        self,
        task_id: str,
        today: date,
    ) -> tuple[Task | None, Task | None]:
        """Complete one occurrence and create its next occurrence.

        The successor is created in the same atomic save as the completion so a
        disk failure can never leave a half-completed repeating series.
        """

        task = self.get(task_id)
        if task is None:
            return None, None
        if task.completed or task.repeat is None or task.due is None:
            return task, None

        follow_up = Task.create(
            task.title,
            next_occurrence(task.due, task.repeat, today),
            task.repeat,
        )
        follow_up.repeat_parent_id = task.id
        previous_completed = (task.completed, task.completed_at)
        task.completed = True
        task.completed_at = now_iso()
        self._tasks.append(follow_up)
        try:
            self._save()
        except StoreError:
            self._tasks.pop()
            task.completed, task.completed_at = previous_completed
            raise
        return task, follow_up

    def reopen_recurring(self, task_id: str) -> Task | None:
        """Reopen a completed occurrence and remove its pending successor."""

        task = self.get(task_id)
        if task is None:
            return None
        if not task.completed or task.repeat is None:
            return task

        child_index = next(
            (
                index
                for index, candidate in enumerate(self._tasks)
                if candidate.repeat_parent_id == task.id and not candidate.completed
            ),
            None,
        )
        removed = self._tasks[child_index] if child_index is not None else None
        if child_index is not None:
            del self._tasks[child_index]
        previous_completed = (task.completed, task.completed_at)
        task.completed = False
        task.completed_at = None
        try:
            self._save()
        except StoreError:
            task.completed, task.completed_at = previous_completed
            if removed is not None:
                self._tasks.insert(child_index or 0, removed)
            raise
        return task

    def rename(self, task_id: str, title: str) -> Task | None:
        clean = title.strip()
        if not clean:
            return None
        task = self.get(task_id)
        if task is None:
            return None
        if task.title == clean:
            return task
        previous = task.title
        task.title = clean
        try:
            self._save()
        except StoreError:
            task.title = previous
            raise
        return task

    def set_due(self, task_id: str, due: date | None) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        value = due.isoformat() if due else None
        if task.due_date == value:
            return task
        previous = (task.due_date, task.repeat)
        task.due_date = value
        if value is None:
            # A recurrence needs a date to anchor the next occurrence.
            task.repeat = None
        try:
            self._save()
        except StoreError:
            task.due_date, task.repeat = previous
            raise
        return task

    def delete(self, task_id: str) -> bool:
        index = next(
            (i for i, task in enumerate(self._tasks) if task.id == task_id),
            None,
        )
        if index is None:
            return False
        removed = self._tasks.pop(index)
        try:
            self._save()
        except StoreError:
            self._tasks.insert(index, removed)
            raise
        return True
