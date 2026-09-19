"""Turning a pile of tasks into something worth reading."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Task

SOON_HOURS = 72

# Signals that the portal text alone is not enough to start work on something.
_NEEDS_YOU = [
    (re.compile(r"\bgroup\b|\bteam\b|\bpartner\b", re.I), "group work"),
    (re.compile(r"\bin[- ]class\b|\bin[- ]person\b|\blab section\b", re.I), "happens in person"),
    (re.compile(r"\bpresent(ation)?\b|\boral\b", re.I), "presentation"),
    (re.compile(r"see (the )?(syllabus|textbook|slides|handout|attached)", re.I),
     "points at material not in the portal"),
]


def bucket(task: Task, now: datetime) -> str:
    days = task.days_left(now)
    if days is None:
        return "undated"
    if days < 0:
        return "overdue"
    if days * 24 <= SOON_HOURS:
        return "soon"
    return "upcoming"


def blockers(task: Task) -> list[str]:
    """Why I would have to ask you something before starting this."""
    reasons = []
    if task.source == "quiz":
        reasons.append("timed quiz - you have to sit it yourself")
    if not task.instructions.strip():
        reasons.append("no instructions posted in the portal")
    if task.attachments:
        reasons.append(f"instructions are in {len(task.attachments)} attachment(s)")
    text = f"{task.title}\n{task.instructions}"
    for pattern, reason in _NEEDS_YOU:
        if pattern.search(text):
            reasons.append(reason)
    return reasons


def _when(task: Task, now: datetime) -> str:
    if not task.due:
        return "no due date"
    days = task.days_left(now)
    stamp = task.due.strftime("%a %d %b, %H:%M UTC")
    if days < 0:
        return f"{stamp} (OVERDUE by {abs(days):.1f}d)"
    return f"{stamp} (in {days:.1f}d)"


def digest(tasks: list[Task], now: datetime | None = None,
           heading: str = "Coursework") -> str:
    now = now or datetime.now(timezone.utc)
    if not tasks:
        return f"# {heading}\n\nNothing outstanding.\n"

    order = {"overdue": 0, "soon": 1, "upcoming": 2, "undated": 3}
    tasks = sorted(tasks, key=lambda t: (
        order[bucket(t, now)],
        t.due or datetime.max.replace(tzinfo=timezone.utc),
    ))

    lines = [f"# {heading}", "",
             f"_{len(tasks)} item(s), generated {now.strftime('%Y-%m-%d %H:%M UTC')}_", ""]
    label = {"overdue": "Overdue", "soon": f"Due within {SOON_HOURS}h",
             "upcoming": "Upcoming", "undated": "No due date"}
    current = None

    for task in tasks:
        group = bucket(task, now)
        if group != current:
            current = group
            lines += [f"## {label[group]}", ""]
        mark = "x" if task.submitted else " "
        lines.append(f"- [{mark}] **{task.title}** - {task.course}")
        lines.append(f"  - due: {_when(task, now)}")
        if task.points:
            lines.append(f"  - worth: {task.points:g} points")
        reasons = blockers(task)
        if reasons:
            lines.append(f"  - **needs you:** {'; '.join(reasons)}")
        if task.instructions:
            body = task.instructions.replace("\n", " ")
            lines.append(f"  - brief: {body[:400]}{'...' if len(body) > 400 else ''}")
        if task.attachments:
            lines.append(f"  - files: {', '.join(task.attachments)}")
        lines.append(f"  - link: {task.url}")
        lines.append("")
    return "\n".join(lines)
