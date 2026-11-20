"""A stand-in Brightspace, so the pipeline can be tested without a real portal.

Payload shapes follow the Valence API: bookmark-paged enrolments, dropbox
folders with CustomInstructions/Attachments/Assessment, quizzes under
'Objects'. It also refuses unauthenticated callers and 403s the quizzes route,
which is how a student account usually behaves.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

VERSIONS = [
    {"ProductCode": "lp", "LatestVersion": "1.9", "SupportedVersions": ["1.9"]},
    {"ProductCode": "le", "LatestVersion": "1.67", "SupportedVersions": ["1.67"]},
]

WHOAMI = {"Identifier": "884", "FirstName": "Abenezer", "LastName": "K",
          "UniqueName": "akoru1", "ProfileIdentifier": "x"}

ENROLMENTS = {
    "page1": {
        "PagingInfo": {"Bookmark": "cursor-2", "HasMoreItems": True},
        "Items": [
            {"OrgUnit": {"Id": 771001, "Type": {"Id": 3, "Code": "Course Offering"},
                         "Name": "Data Structures", "Code": "CSC-2720"}},
            {"OrgUnit": {"Id": 6606, "Type": {"Id": 2, "Code": "Department"},
                         "Name": "Computer Science", "Code": "CS-DEPT"}},
        ],
    },
    "cursor-2": {
        "PagingInfo": {"Bookmark": None, "HasMoreItems": False},
        "Items": [
            {"OrgUnit": {"Id": 771002, "Type": {"Id": 3, "Code": "Course Offering"},
                         "Name": "Calculus II", "Code": "MATH-2212"}},
            # the same course again under a second role - must be deduplicated
            {"OrgUnit": {"Id": 771001, "Type": {"Id": 3, "Code": "Course Offering"},
                         "Name": "Data Structures", "Code": "CSC-2720"}},
        ],
    },
}

FOLDERS = {
    771001: [
        {"Id": 4411, "Name": "Lab 3: Hash Tables", "DueDate": "2026-09-22T03:59:00.000Z",
         "CustomInstructions": {"Html": "<p>Implement <b>open addressing</b>.</p>"
                                        "<ul><li>Q1 load factor</li><li>Q2 clustering</li></ul>"},
         "Attachments": [], "TotalFiles": 0, "IsHidden": False,
         "Assessment": {"ScoreDenominator": 25.0}},
        {"Id": 4412, "Name": "Group Project Proposal", "DueDate": "2026-10-10T03:59:00.000Z",
         "CustomInstructions": {"Html": "<p>See the attached rubric. Group of 4.</p>"},
         "Attachments": [{"FileId": 9, "FileName": "rubric.pdf", "Size": 8123}],
         "TotalFiles": 0, "IsHidden": False, "Assessment": {"ScoreDenominator": 100.0}},
        {"Id": 4413, "Name": "Lab 2: Linked Lists", "DueDate": "2026-09-08T03:59:00.000Z",
         "CustomInstructions": {"Html": "<p>Done already.</p>"},
         "Attachments": [], "TotalFiles": 2, "IsHidden": False,
         "Assessment": {"ScoreDenominator": 25.0}},
        {"Id": 4414, "Name": "Hidden draft", "DueDate": None, "IsHidden": True},
    ],
    771002: [
        {"Id": 5501, "Name": "WebAssign Set 5", "DueDate": None,
         "CustomInstructions": {"Html": ""}, "Attachments": [],
         "TotalFiles": 0, "IsHidden": False, "Assessment": {"ScoreDenominator": 10.0}},
    ],
}


CALENDAR = {
    771001: [
        # an echo of the Lab 3 dropbox: the client should drop this one
        {"CalendarEventId": 77, "Title": "Lab 3: Hash Tables",
         "EndDateTime": "2026-09-22T03:59:00.000Z", "Description": ""},
        {"CalendarEventId": 78, "Title": "Midterm review session",
         "EndDateTime": "2026-09-25T18:00:00.000Z",
         "Description": "<p>Optional, in-class.</p>"},
    ],
    771002: [],
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):        # keep the test output clean
        pass

    def _send(self, code: int, payload=None, content_type="application/json"):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        path, query = url.path, parse_qs(url.query)

        # Everything but the version list requires the session cookie.
        if path != "/d2l/api/versions/" and "d2lSecureSessionVal" not in (
                self.headers.get("Cookie") or ""):
            self.send_response(302)
            self.send_header("Location", "/d2l/login")
            self.end_headers()
            return

        if path == "/d2l/api/versions/":
            return self._send(200, VERSIONS)
        if path.endswith("/users/whoami"):
            return self._send(200, WHOAMI)
        if path == "/d2l/lp/auth/xsrf-tokens":
            return self._send(200, {"referrerToken": "tok-123"})
        if path.endswith("/enrollments/myenrollments/"):
            bookmark = query.get("bookmark", ["page1"])[0]
            return self._send(200, ENROLMENTS.get(bookmark, ENROLMENTS["cursor-2"]))

        # /d2l/api/le/<version>/<orgUnitId>/...
        match = re.search(r"/d2l/api/le/[\d.]+/(\d+)/", path)
        org_unit = int(match.group(1)) if match else None

        if path.endswith("/dropbox/folders/"):
            return self._send(200, FOLDERS.get(org_unit, []))
        if path.endswith("/quizzes/"):
            return self._send(403)               # the usual student experience
        if path.endswith("/calendar/events/myEvents/"):
            return self._send(200, {"Objects": CALENDAR.get(org_unit, [])})
        self._send(404)


def serve() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"
