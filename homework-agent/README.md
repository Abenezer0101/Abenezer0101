# homework-agent

Reads your coursework out of a D2L Brightspace portal, tells you what is new
since last time, and flags the things it would have to ask you about before
anyone could start on them.

It is a fetcher and a triager. It does not submit anything, and it does not
write your answers — it puts the real brief in front of you (or in front of
Claude, in a session where you can talk it through) instead of you clicking
through five courses to find out what is due.

Built against `https://gastate.view.usg.edu` (GSU iCollege), but the portal
URL is a flag, so it works for any Brightspace tenant.

## How it reads the portal

Brightspace's own web UI talks to a REST API at `/d2l/api/...` using your
ordinary session cookies. This uses the same routes the same way, so there is
no OAuth application for an administrator to register, and no HTML scraping to
break on the next theme update.

Which of those routes a *student* account may call is set per tenant. That is
why `probe` exists: one run prints exactly what your account can and cannot
see, rather than leaving you to guess.

## Install

```bash
pip install -r requirements.txt
# only if you want automated login rather than pasting cookies:
playwright install chromium
```

Python 3.11+.

## Signing in

Two ways. Pick the first one.

**Paste a session cookie (recommended).** Your password never touches this
machine, and it works even when the login has MFA or a single sign-on
redirect in front of it.

1. Log in to the portal in your normal browser.
2. Open devtools → Application → Cookies → the portal's domain.
3. Copy the values of `d2lSecureSessionVal` and `d2lSessionVal`.

```bash
export D2L_SECURE_SESSION_VAL='...'
export D2L_SESSION_VAL='...'
```

These expire — every few hours to a few days, depending on the tenant. When
`check` reports that the session is dead, repeat the three steps.

**Automated login.** Playwright drives the real login form:

```bash
export D2L_USERNAME='your.campus.id'
export D2L_PASSWORD='...'
python -m hwagent login              # add --headful if SSO needs a human touch
```

The session is saved to `state/auth_state.json` (mode 600) and reused until it
expires. The form filler matches on field *shape* rather than one school's
markup, so an SSO redesign should not break it; if it does, it drops a
screenshot and the page HTML in `state/login-failure/`, and you can pin exact
selectors with `D2L_USER_SELECTOR`, `D2L_PASS_SELECTOR` and
`D2L_SUBMIT_SELECTOR`.

MFA cannot be automated. If your login prompts for a code, use the cookie
method.

## Use

```bash
python -m hwagent probe              # which API routes your account can use
python -m hwagent check              # what is new or changed since last run
python -m hwagent check --all        # everything outstanding
python -m hwagent check --all --json # machine-readable, for piping
python -m hwagent show "Lab 3"       # full instructions for one task
```

`check` remembers what it has shown you in `state/seen.json`, so a scheduled
run stays quiet until something actually appears or a deadline moves. Sorting
is by urgency: overdue, then due within 72h, then upcoming, then undated.

`--calendar` adds dated calendar items on top of assignments and quizzes.
Calendar entries that merely echo an assignment already listed are dropped.

### The "needs you" line

Some things cannot be started from the portal text alone, and the report says
so rather than pretending otherwise: a brief that is empty, instructions that
live in an attachment, anything marked as group work, anything that happens in
person, and timed quizzes you have to sit yourself.

## Running it daily

The job is a single command — `python -m hwagent check` — so anything that can
run a command on a schedule will do. On your own machine:

```cron
0 7 * * * cd /path/to/homework-agent && python -m hwagent check >> daily.log 2>&1
```

Running it from a Claude Code session on a schedule works too, and has the
advantage that the digest lands somewhere you can immediately talk about. Two
things have to be true first: the environment's egress policy must allow your
portal's host, and the cookie or credential environment variables must be set
on the environment rather than committed here.

## Security

`.gitignore` already covers `.env`, `state/`, `raw/` and `auth_state.json`.
Credentials and cookies belong in environment variables or your shell profile,
never in the repository. Every request this makes is a `GET`; nothing is
submitted, uploaded, or changed on the portal side.

## Tests

```bash
python3 tests/test_pipeline.py
```

32 checks covering auth, API version negotiation, bookmark pagination, role
deduplication, hidden-assignment filtering, a 403 on a route a student cannot
call, HTML-to-text rendering, the triage flags, change detection across runs,
and report ordering. They run against a mock Brightspace in
`tests/mock_brightspace.py`, so no portal or credentials are needed.

## Layout

```
hwagent/
  models.py    Task and Course, HTML-to-text, D2L timestamp parsing
  session.py   authentication: cookie paste, saved state, browser login
  d2l.py       the Valence API client, with per-call outcome recording
  store.py     what we have already reported, and what changed
  report.py    triage buckets, "needs you" flags, the markdown digest
  cli.py       login / probe / check / show
tests/
  mock_brightspace.py   a stand-in portal
  test_pipeline.py      end-to-end
```
