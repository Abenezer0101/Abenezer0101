"""Remembering what we already told you about, so a daily run stays quiet."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import Task


@dataclass
class Delta:
    new: list[Task]
    changed: list[Task]          # due date moved, instructions edited, etc.
    unchanged: list[Task]

    @property
    def noteworthy(self) -> list[Task]:
        return self.new + self.changed

    def __bool__(self) -> bool:
        return bool(self.noteworthy)


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.seen: dict[str, str] = {}
        if self.path.exists():
            try:
                self.seen = json.loads(self.path.read_text()).get("seen", {})
            except (ValueError, OSError):
                self.seen = {}          # a corrupt cache is not worth a crash

    def diff(self, tasks: list[Task]) -> Delta:
        new, changed, unchanged = [], [], []
        for task in tasks:
            previous = self.seen.get(task.key)
            if previous is None:
                new.append(task)
            elif previous != task.fingerprint:
                changed.append(task)
            else:
                unchanged.append(task)
        return Delta(new, changed, unchanged)

    def commit(self, tasks: list[Task]) -> None:
        self.seen = {task.key: task.fingerprint for task in tasks}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"seen": self.seen}, indent=2))
