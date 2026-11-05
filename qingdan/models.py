"""Task model for Qingdan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from .recurrence import normalize_repeat


def now_iso() -> str:
    """Return a local, human-readable ISO timestamp."""

    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(slots=True)
class Task:
    id: str
    title: str
    due_date: str | None
    completed: bool
    created_at: str
    completed_at: str | None = None
    repeat: str | None = None
    repeat_parent_id: str | None = None

    @classmethod
    def create(
        cls,
        title: str,
        due: date | None = None,
        repeat: str | None = None,
    ) -> "Task":
        clean = title.strip()
        if not clean:
            raise ValueError("Task title cannot be empty")
        repeat = normalize_repeat(repeat)
        if repeat is not None and due is None:
            raise ValueError("A repeating task requires a due date")
        return cls(
            id=uuid4().hex,
            title=clean,
            due_date=due.isoformat() if due else None,
            completed=False,
            created_at=now_iso(),
            repeat=repeat,
        )

    @property
    def due(self) -> date | None:
        if not self.due_date:
            return None
        return date.fromisoformat(self.due_date)

    @property
    def completed_on(self) -> date | None:
        if not self.completed_at:
            return None
        try:
            return datetime.fromisoformat(self.completed_at).date()
        except ValueError:
            return None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "due_date": self.due_date,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
        if self.repeat is not None:
            data["repeat"] = self.repeat
        if self.repeat_parent_id is not None:
            data["repeat_parent_id"] = self.repeat_parent_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        if not isinstance(data, dict):
            raise ValueError("Task must be an object")
        task_id = data.get("id")
        title = data.get("title")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Invalid task id")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Invalid task title")

        due_date = data.get("due_date")
        if due_date is not None:
            if not isinstance(due_date, str):
                raise ValueError("Invalid due date")
            date.fromisoformat(due_date)  # validate eagerly

        completed = bool(data.get("completed", False))
        created_at = data.get("created_at")
        if not isinstance(created_at, str) or not created_at:
            created_at = now_iso()

        completed_at = data.get("completed_at")
        if completed_at is not None and not isinstance(completed_at, str):
            raise ValueError("Invalid completion timestamp")

        repeat = normalize_repeat(data.get("repeat"))
        if repeat is not None and due_date is None:
            raise ValueError("A repeating task requires a due date")
        repeat_parent_id = data.get("repeat_parent_id")
        if repeat_parent_id is not None and not isinstance(repeat_parent_id, str):
            raise ValueError("Invalid repeat parent")

        return cls(
            id=task_id.strip(),
            title=title.strip(),
            due_date=due_date,
            completed=completed,
            created_at=created_at,
            completed_at=completed_at,
            repeat=repeat,
            repeat_parent_id=repeat_parent_id,
        )
