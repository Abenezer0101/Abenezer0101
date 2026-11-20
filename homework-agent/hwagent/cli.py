"""Command line. Four verbs: login, probe, check, show."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .d2l import Brightspace
from .report import blockers, digest
from .session import AuthError, Portal
from .store import Store

DEFAULT_BASE = "https://gastate.view.usg.edu"


def _portal(args) -> Portal:
    base = args.base_url or os.environ.get("D2L_BASE_URL") or DEFAULT_BASE
    return Portal(base, Path(args.state_dir))


def _connect(args) -> tuple[Portal, Brightspace]:
    portal = _portal(args)
    try:
        method = portal.connect(args.auth)
    except AuthError as exc:
        sys.exit(f"login failed.\n{exc}\n\n"
                 "Fastest fix: log in with your own browser, then copy the\n"
                 "d2lSessionVal and d2lSecureSessionVal cookie values into\n"
                 "D2L_SESSION_VAL and D2L_SECURE_SESSION_VAL. See the README.")
    who = portal.whoami() or {}
    name = who.get("FirstName") or who.get("UniqueName") or "authenticated"
    print(f"signed in as {name} (via {method})", file=sys.stderr)
    return portal, Brightspace(portal)


def cmd_login(args) -> None:
    portal = _portal(args)
    if not portal.browser_login(headless=not args.headful):
        sys.exit(f"login did not complete. Diagnostics in {portal.state_dir}/login-failure/")
    print(f"session saved to {portal.auth_state_path}")


def cmd_probe(args) -> None:
    _, api = _connect(args)
    courses = api.courses()
    print(f"\n{len(courses)} course(s):")
    for course in courses:
        print(f"  [{course.org_unit_id}] {course}")
    if courses:
        probe_course = courses[0]
        print(f"\nprobing routes against {probe_course}:")
        api.assignments(probe_course)
        api.quizzes(probe_course)
        api.calendar(probe_course)
    print("\nroute results:")
    for call in api.calls:
        print(f"  {str(call['status']):>5}  {call['path']}  -- {call.get('detail', '')}")


def cmd_check(args) -> None:
    _, api = _connect(args)
    courses, tasks = api.collect(include_quizzes=not args.no_quizzes,
                                 include_calendar=args.calendar)
    print(f"{len(courses)} course(s), {len(tasks)} task(s) found", file=sys.stderr)

    store = Store(Path(args.state_dir) / "seen.json")
    delta = store.diff(tasks)
    selected = tasks if args.all else delta.noteworthy

    if args.json:
        print(json.dumps({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "courses": [c.__dict__ for c in courses],
            "new": [t.to_dict() for t in delta.new],
            "changed": [t.to_dict() for t in delta.changed],
            "all": [t.to_dict() for t in tasks],
        }, indent=2, default=str))
    else:
        if not args.all and not delta:
            print("Nothing new since the last check. "
                  "Run with --all to see everything outstanding.")
        else:
            print(digest(selected, heading="Coursework" if args.all
                         else "New or changed since last check"))

    if not args.dry_run:
        store.commit(tasks)


def cmd_show(args) -> None:
    _, api = _connect(args)
    _, tasks = api.collect()
    needle = args.query.lower()
    hits = [t for t in tasks if needle in t.title.lower() or needle == t.key]
    if not hits:
        sys.exit(f"no task matching {args.query!r}")
    for task in hits:
        print(f"\n{'=' * 70}\n{task.title}\n{'=' * 70}")
        print(f"course:  {task.course}")
        print(f"due:     {task.due.isoformat() if task.due else 'not set'}")
        print(f"points:  {task.points if task.points is not None else 'not set'}")
        print(f"link:    {task.url}")
        if task.attachments:
            print(f"files:   {', '.join(task.attachments)}")
        reasons = blockers(task)
        if reasons:
            print(f"needs you: {'; '.join(reasons)}")
        print(f"\n--- instructions ---\n{task.instructions or '(none posted)'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hwagent",
        description="Read coursework out of a D2L Brightspace portal.")
    parser.add_argument("--base-url", help=f"portal root (default {DEFAULT_BASE})")
    parser.add_argument("--state-dir", default=os.environ.get("HWAGENT_STATE_DIR", "state"),
                        help="where cookies and the seen-task cache live")
    parser.add_argument("--auth", choices=["auto", "cookie", "saved", "browser"],
                        default="auto", help="how to authenticate (default: try all)")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="log in with a browser and save the session")
    login.add_argument("--headful", action="store_true",
                       help="show the browser - use when SSO needs a human touch")
    login.set_defaults(func=cmd_login)

    probe = sub.add_parser("probe", help="report which API routes your account can actually use")
    probe.set_defaults(func=cmd_probe)

    check = sub.add_parser("check", help="list coursework (new and changed by default)")
    check.add_argument("--all", action="store_true", help="show everything, not just changes")
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.add_argument("--calendar", action="store_true", help="also pull calendar items")
    check.add_argument("--no-quizzes", action="store_true")
    check.add_argument("--dry-run", action="store_true", help="do not update the seen-cache")
    check.set_defaults(func=cmd_check)

    show = sub.add_parser("show", help="full detail for one task")
    show.add_argument("query", help="part of the title, or an exact task key")
    show.set_defaults(func=cmd_show)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
