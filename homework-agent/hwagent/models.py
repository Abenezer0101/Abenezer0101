"""The one shape everything else speaks in."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

# D2L returns HTML in instruction bodies; we keep a text rendering for reading
# and leave the original alone.
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_BLANKS = re.compile(r"\n{3,}")
_BLOCK_END = re.compile(r"</(p|div|li|tr|h[1-6]|blockquote)\s*>", re.I)
_BREAK = re.compile(r"<br\s*/?>", re.I)

_ENTITIES = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#39;": "'", "&rsquo;": "’", "&ldquo;": "“",
    "&rdquo;": "”", "&mdash;": "—", "&ndash;": "–",
}


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    text = _BREAK.sub("\n", html)
    text = _BLOCK_END.sub("\n\n", text)
    text = _TAG.sub("", text)
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    text = _WS.sub(" ", text)
    text = _BLANKS.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def parse_d2l_time(value) -> datetime | None:
    """D2L hands back UTC ISO-8601, usually '2026-09-30T04:59:00.000Z'."""
    if not value:
        return None
    if isinstance(value, (int, float)):  # some routes use epoch milliseconds
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass
class Course:
    org_unit_id: int
    name: str
    code: str = ""

    def __str__(self) -> str:
        return f"{self.code or self.org_unit_id} - {self.name}"


@dataclass
class Task:
    """An assignment, quiz, or dated calendar item a student has to act on."""

    source: str                      # "dropbox" | "quiz" | "calendar"
    task_id: str
    course: str
    org_unit_id: int
    title: str
    due: datetime | None = None
    instructions: str = ""           # plain text, for reading
    instructions_html: str = ""      # original, in case formatting matters
    url: str = ""
    attachments: list[str] = field(default_factory=list)
    submitted: bool | None = None    # None = the portal did not say
    points: float | None = None
    raw: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.org_unit_id}:{self.source}:{self.task_id}"

    @property
    def fingerprint(self) -> str:
        """Changes when anything a student would care about changes."""
        material = json.dumps(
            [self.title, self.due.isoformat() if self.due else None,
             self.instructions, sorted(self.attachments), self.points],
            sort_keys=True,
        )
        return hashlib.sha256(material.encode()).hexdigest()[:16]

    def days_left(self, now: datetime | None = None) -> float | None:
        if not self.due:
            return None
        now = now or datetime.now(timezone.utc)
        return (self.due - now).total_seconds() / 86400

    def to_dict(self) -> dict:
        out = asdict(self)
        out["due"] = self.due.isoformat() if self.due else None
        out["key"] = self.key
        out["fingerprint"] = self.fingerprint
        return out
