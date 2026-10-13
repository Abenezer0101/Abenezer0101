"""End-to-end: mock portal -> auth -> fetch -> diff -> digest.

Plain asserts, no test framework needed:  python3 tests/test_pipeline.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hwagent.d2l import Brightspace                      # noqa: E402
from hwagent.report import blockers, bucket, digest      # noqa: E402
from hwagent.session import Portal                       # noqa: E402
from hwagent.store import Store                          # noqa: E402
from tests.mock_brightspace import serve                 # noqa: E402

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
checks = 0


def check(condition, label):
    global checks
    assert condition, f"FAILED: {label}"
    checks += 1
    print(f"  ok  {label}")


def main() -> None:
    server, base = serve()
    work = Path(tempfile.mkdtemp())
    os.environ["D2L_SECURE_SESSION_VAL"] = "fake-session-value"
    os.environ.pop("D2L_SESSION_VAL", None)

    print("\nauth")
    portal = Portal(base, work)
    check(portal.whoami() is None, "rejects a session with no cookies")
    method = portal.connect("auto")
    check(method == "cookie", "authenticates from pasted cookie values")
    check(portal.http.headers.get("X-Csrf-Token") == "tok-123", "picks up the CSRF token")

    api = Brightspace(portal)

    print("\nversion negotiation")
    check(api.version("le", "1.0") == "1.67", "asks the tenant for its LE version")
    check(api.version("lp", "1.0") == "1.9", "asks the tenant for its LP version")
    check(api.version("nope", "9.9") == "9.9", "falls back for an unknown product")

    print("\ncourses")
    courses = api.courses()
    ids = sorted(c.org_unit_id for c in courses)
    check(ids == [771001, 771002], f"walks both bookmark pages and dedups roles -> {ids}")
    check(all(c.code for c in courses), "keeps course codes")

    print("\ntasks")
    courses, tasks = api.collect(include_quizzes=True, include_calendar=True)
    check(len(tasks) == 5, f"5 real tasks (hidden folder dropped) -> {len(tasks)}")
    titles = {t.title for t in tasks}
    check("Hidden draft" not in titles, "skips hidden assignments")
    check("Midterm review session" in titles, "keeps a calendar item with no assignment")
    check(sum(t.source == "calendar" for t in tasks) == 1,
          "drops the calendar echo of an assignment it already has")
    check(any(c["status"] == 403 and c["path"].endswith("/quizzes/") for c in api.calls),
          "records the 403 on quizzes instead of crashing")

    lab3 = next(t for t in tasks if t.title.startswith("Lab 3"))
    check(lab3.points == 25.0, "reads the point value")
    check(lab3.due == datetime(2026, 9, 22, 3, 59, tzinfo=timezone.utc), "parses the due date")
    check("open addressing" in lab3.instructions and "<b>" not in lab3.instructions,
          "renders instruction HTML to readable text")
    check(lab3.submitted is False, "marks an unsubmitted assignment")
    check(next(t for t in tasks if t.title.startswith("Lab 2")).submitted is True,
          "marks a submitted assignment")

    print("\ntriage")
    proposal = next(t for t in tasks if "Proposal" in t.title)
    reasons = " ".join(blockers(proposal))
    check("group work" in reasons and "attachment" in reasons,
          f"flags what it would have to ask you -> {blockers(proposal)}")
    webassign = next(t for t in tasks if "WebAssign" in t.title)
    check("no instructions posted" in " ".join(blockers(webassign)),
          "flags an assignment with an empty brief")
    check(blockers(lab3) == [], "flags nothing when the brief is self-contained")
    check(bucket(lab3, NOW) == "soon", "Lab 3 is due soon")
    check(bucket(next(t for t in tasks if t.title.startswith("Lab 2")), NOW) == "overdue",
          "Lab 2 is overdue")
    check(bucket(webassign, NOW) == "undated", "WebAssign has no due date")

    print("\nchange detection")
    store = Store(work / "seen.json")
    first = store.diff(tasks)
    check(len(first.new) == 5 and not first.changed, "first run: everything is new")
    store.commit(tasks)

    second = Store(work / "seen.json").diff(tasks)
    check(not second.noteworthy and len(second.unchanged) == 5,
          "second run with no changes: silent")

    lab3.due = datetime(2026, 9, 25, 3, 59, tzinfo=timezone.utc)
    third = Store(work / "seen.json").diff(tasks)
    check([t.title for t in third.changed] == ["Lab 3: Hash Tables"],
          "notices a moved deadline, and only that")

    print("\ndigest")
    text = digest(tasks, now=NOW)
    check(text.index("## Overdue") < text.index("## Upcoming"), "sorts by urgency")
    check("- [x] **Lab 2" in text and "- [ ] **Lab 3" in text, "checkboxes track submission")
    check("**needs you:**" in text, "surfaces the questions it has for you")
    check(digest([], now=NOW).strip().endswith("Nothing outstanding."), "handles an empty term")

    print("\nsession expiry")
    portal.http.cookies.clear()
    check(portal.whoami() is None, "treats the login redirect as a dead session")

    server.shutdown()
    print(f"\n{checks} checks passed\n")


if __name__ == "__main__":
    main()
