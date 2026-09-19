"""Reading coursework out of Brightspace via its Valence API.

Which routes a *student* account may call is decided by each tenant's role
permissions, not by the API docs, so every call here is best-effort and
records its own outcome. ``hwagent probe`` prints that record: one run tells
you exactly what your account can see, instead of guessing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from .models import Course, Task, html_to_text, parse_d2l_time

COURSE_OFFERING = 3          # OrgUnit.Type.Id for an actual course
PAGE_LIMIT = 40              # stop runaway bookmark paging


class Brightspace:
    def __init__(self, portal):
        self.portal = portal
        self.base = portal.base_url
        self.http = portal.http
        self.calls: list[dict] = []          # the probe record
        self._versions: dict[str, str] = {}

    # ---------- plumbing ----------

    def get(self, path: str, **params) -> tuple[int, object]:
        url = f"{self.base}{path}"
        try:
            response = self.http.get(url, params=params or None,
                                     timeout=45, allow_redirects=False)
        except requests.RequestException as exc:
            self.calls.append({"path": path, "status": "error", "detail": str(exc)})
            return 0, None

        note = {"path": path, "status": response.status_code}
        if response.status_code == 200 and "json" in response.headers.get("Content-Type", ""):
            try:
                payload = response.json()
            except ValueError:
                note["detail"] = "200 but body was not JSON"
                self.calls.append(note)
                return response.status_code, None
            note["detail"] = f"{len(payload)} items" if isinstance(payload, list) else "ok"
            self.calls.append(note)
            return 200, payload

        note["detail"] = {
            302: "redirected to login - session expired",
            401: "not authenticated",
            403: "your role may not call this route",
            404: "route or API version not present on this tenant",
        }.get(response.status_code, response.reason or "unexpected response")
        self.calls.append(note)
        return response.status_code, None

    def version(self, product: str, fallback: str) -> str:
        """Ask the tenant which API version it speaks rather than hardcoding one."""
        if not self._versions:
            _, payload = self.get("/d2l/api/versions/")
            if isinstance(payload, list):
                self._versions = {
                    entry.get("ProductCode", ""): entry.get("LatestVersion", "")
                    for entry in payload if isinstance(entry, dict)
                }
        return self._versions.get(product) or fallback

    def paged(self, path: str, **params) -> list:
        """Walk D2L's bookmark pagination to the end."""
        items, bookmark = [], None
        for _ in range(PAGE_LIMIT):
            call = dict(params)
            if bookmark:
                call["bookmark"] = bookmark
            status, payload = self.get(path, **call)
            if status != 200 or not isinstance(payload, dict):
                break
            items.extend(payload.get("Items") or [])
            paging = payload.get("PagingInfo") or {}
            if not paging.get("HasMoreItems"):
                break
            bookmark = paging.get("Bookmark")
            if not bookmark:
                break
        return items

    # ---------- reading ----------

    def courses(self) -> list[Course]:
        lp = self.version("lp", "1.9")
        found = []
        for item in self.paged(f"/d2l/api/lp/{lp}/enrollments/myenrollments/",
                               orgUnitTypeId=COURSE_OFFERING):
            unit = item.get("OrgUnit") or {}
            unit_type = (unit.get("Type") or {}).get("Id")
            if unit_type not in (COURSE_OFFERING, None):
                continue
            if unit.get("Id"):
                found.append(Course(int(unit["Id"]),
                                    unit.get("Name") or f"Course {unit['Id']}",
                                    unit.get("Code") or ""))
        # Deduplicate: a course can appear once per role.
        return list({c.org_unit_id: c for c in found}.values())

    def assignments(self, course: Course) -> list[Task]:
        """Brightspace calls these 'dropbox folders'. They are the homework."""
        le = self.version("le", "1.67")
        status, payload = self.get(
            f"/d2l/api/le/{le}/{course.org_unit_id}/dropbox/folders/")
        if status != 200 or not isinstance(payload, list):
            return []

        tasks = []
        for folder in payload:
            if not isinstance(folder, dict) or folder.get("IsHidden"):
                continue
            # Field name moved between API versions; accept either.
            instructions = folder.get("CustomInstructions") or folder.get("Instructions") or {}
            html = instructions.get("Html") or instructions.get("Text") or ""
            assessment = folder.get("Assessment") or {}
            folder_id = folder.get("Id")
            submitted = folder.get("TotalFiles")

            tasks.append(Task(
                source="dropbox",
                task_id=str(folder_id),
                course=course.name,
                org_unit_id=course.org_unit_id,
                title=folder.get("Name") or f"Assignment {folder_id}",
                due=parse_d2l_time(folder.get("DueDate")),
                instructions=html_to_text(html),
                instructions_html=html,
                url=(f"{self.base}/d2l/lms/dropbox/user/folder_submit_files.d2l"
                     f"?db={folder_id}&ou={course.org_unit_id}"),
                attachments=[a.get("FileName") for a in (folder.get("Attachments") or [])
                             if a.get("FileName")],
                submitted=bool(submitted) if isinstance(submitted, int) else None,
                points=assessment.get("ScoreDenominator"),
                raw=folder,
            ))
        return tasks

    def quizzes(self, course: Course) -> list[Task]:
        """Often blocked for student roles; returns nothing rather than failing."""
        le = self.version("le", "1.67")
        status, payload = self.get(f"/d2l/api/le/{le}/{course.org_unit_id}/quizzes/")
        objects = payload.get("Objects") if isinstance(payload, dict) else payload
        if status != 200 or not isinstance(objects, list):
            return []

        tasks = []
        for quiz in objects:
            if not isinstance(quiz, dict) or quiz.get("IsActive") is False:
                continue
            quiz_id = quiz.get("QuizId") or quiz.get("Id")
            tasks.append(Task(
                source="quiz",
                task_id=str(quiz_id),
                course=course.name,
                org_unit_id=course.org_unit_id,
                title=quiz.get("Name") or f"Quiz {quiz_id}",
                due=parse_d2l_time(quiz.get("DueDate") or quiz.get("EndDate")),
                instructions=html_to_text((quiz.get("Description") or {}).get("Html", "")),
                url=(f"{self.base}/d2l/lms/quizzing/user/quizzes_list.d2l"
                     f"?ou={course.org_unit_id}"),
                raw=quiz,
            ))
        return tasks

    def calendar(self, course: Course, days_ahead: int = 45) -> list[Task]:
        """Catches dated work that is neither a dropbox nor a quiz."""
        le = self.version("le", "1.67")
        now = datetime.now(timezone.utc)
        status, payload = self.get(
            f"/d2l/api/le/{le}/{course.org_unit_id}/calendar/events/myEvents/",
            startDateTime=now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            endDateTime=(now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        )
        items = payload.get("Objects") if isinstance(payload, dict) else payload
        if status != 200 or not isinstance(items, list):
            return []

        tasks = []
        for event in items:
            if not isinstance(event, dict):
                continue
            event_id = event.get("CalendarEventId") or event.get("Id")
            tasks.append(Task(
                source="calendar",
                task_id=str(event_id),
                course=course.name,
                org_unit_id=course.org_unit_id,
                title=event.get("Title") or "Calendar item",
                due=parse_d2l_time(event.get("EndDateTime") or event.get("StartDateTime")),
                instructions=html_to_text(event.get("Description") or ""),
                url=f"{self.base}/d2l/le/calendar/{course.org_unit_id}",
                raw=event,
            ))
        return tasks

    def collect(self, include_quizzes: bool = True,
                include_calendar: bool = False) -> tuple[list[Course], list[Task]]:
        courses = self.courses()
        tasks: list[Task] = []
        for course in courses:
            tasks.extend(self.assignments(course))
            if include_quizzes:
                tasks.extend(self.quizzes(course))
            if include_calendar:
                tasks.extend(self.calendar(course))
        # Calendar entries usually mirror an assignment; drop the echoes.
        seen_titles = {(t.org_unit_id, t.title.strip().lower())
                       for t in tasks if t.source != "calendar"}
        tasks = [t for t in tasks
                 if t.source != "calendar"
                 or (t.org_unit_id, t.title.strip().lower()) not in seen_titles]
        return courses, tasks
