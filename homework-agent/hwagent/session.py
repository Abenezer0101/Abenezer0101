"""Getting an authenticated session against Brightspace.

Three ways in, cheapest first:

1. ``cookie``  - you log in in your own browser and paste two cookie values.
                 No password ever reaches this machine. Survives MFA and SSO.
2. ``saved``   - reuse ``auth_state.json`` written by a previous browser login.
3. ``browser`` - Playwright drives the real login form with your credentials.

Brightspace's own web UI talks to ``/d2l/api/...`` with exactly these session
cookies, which is why this works without an OAuth app the admin would have to
register for you.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests

SESSION_COOKIES = ("d2lSessionVal", "d2lSecureSessionVal")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class AuthError(RuntimeError):
    pass


class Portal:
    """A logged-in Brightspace session. Read-only: this module only ever GETs."""

    def __init__(self, base_url: str, state_dir: Path):
        self.base_url = base_url.rstrip("/")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.http = requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self.http.headers["Accept"] = "application/json, text/plain, */*"

    # ---------- entry points ----------

    @property
    def auth_state_path(self) -> Path:
        return self.state_dir / "auth_state.json"

    def load_cookies_from_env(self) -> bool:
        pairs = {
            "d2lSessionVal": os.environ.get("D2L_SESSION_VAL"),
            "d2lSecureSessionVal": os.environ.get("D2L_SECURE_SESSION_VAL"),
        }
        if not pairs["d2lSecureSessionVal"]:
            return False
        host = re.sub(r"^https?://", "", self.base_url).split("/")[0].split(":")[0]
        for name, value in pairs.items():
            if value:
                self.http.cookies.set(name, value, domain=host, path="/")
        return True

    def load_saved_state(self) -> bool:
        if not self.auth_state_path.exists():
            return False
        state = json.loads(self.auth_state_path.read_text())
        found = False
        for cookie in state.get("cookies", []):
            self.http.cookies.set(
                cookie["name"], cookie["value"],
                domain=cookie.get("domain", "").lstrip("."),
                path=cookie.get("path", "/"),
            )
            found = found or cookie["name"] in SESSION_COOKIES
        return found

    def connect(self, mode: str = "auto") -> str:
        """Return the name of the method that actually worked."""
        attempts = {
            "cookie": self.load_cookies_from_env,
            "saved": self.load_saved_state,
            "browser": self.browser_login,
        }
        order = list(attempts) if mode == "auto" else [mode]
        tried = []
        for name in order:
            self.http.cookies.clear()
            try:
                if attempts[name]() and self.whoami() is not None:
                    self._attach_csrf()
                    return name
                tried.append(f"{name}: no valid session")
            except Exception as exc:  # keep trying the next method
                tried.append(f"{name}: {type(exc).__name__}: {exc}")
        raise AuthError("could not authenticate.\n  " + "\n  ".join(tried))

    # ---------- verification ----------

    def whoami(self) -> dict | None:
        """``/whoami`` is the cheapest proof that the cookies are live."""
        for version in ("1.9", "1.31", "1.0"):
            try:
                response = self.http.get(
                    f"{self.base_url}/d2l/api/lp/{version}/users/whoami",
                    timeout=30, allow_redirects=False,
                )
            except requests.RequestException:
                continue
            if response.status_code == 200 and "json" in response.headers.get("Content-Type", ""):
                return response.json()
            if response.status_code == 404:
                continue  # unsupported version, try the next
            # 302 to a login page, or 401/403: the session is not valid
            return None
        return None

    def _attach_csrf(self) -> None:
        """Some tenants want this header even on reads. Harmless when they don't."""
        try:
            response = self.http.get(
                f"{self.base_url}/d2l/lp/auth/xsrf-tokens", timeout=20
            )
            token = response.json().get("referrerToken")
            if token:
                self.http.headers["X-Csrf-Token"] = token
        except Exception:
            pass

    # ---------- browser login ----------

    def browser_login(self, headless: bool = True) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise AuthError(
                "browser login needs Playwright: pip install playwright && playwright install chromium"
            ) from exc

        username = os.environ.get("D2L_USERNAME")
        password = os.environ.get("D2L_PASSWORD")
        if not (username and password):
            raise AuthError("set D2L_USERNAME and D2L_PASSWORD for browser login")

        user_sel = os.environ.get("D2L_USER_SELECTOR")
        pass_sel = os.environ.get("D2L_PASS_SELECTOR")
        submit_sel = os.environ.get("D2L_SUBMIT_SELECTOR")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.goto(f"{self.base_url}/d2l/home", wait_until="domcontentloaded", timeout=60_000)

            # SSO chains can be several pages long; walk them until the
            # Brightspace session cookie shows up.
            for _ in range(8):
                page.wait_for_load_state("networkidle", timeout=30_000)
                if any(c["name"] == "d2lSecureSessionVal" for c in context.cookies()):
                    break
                if not self._fill_one_step(page, username, password,
                                           user_sel, pass_sel, submit_sel):
                    break

            cookies = context.cookies()
            ok = any(c["name"] == "d2lSecureSessionVal" for c in cookies)
            if ok:
                context.storage_state(path=str(self.auth_state_path))
                self.auth_state_path.chmod(0o600)
                for cookie in cookies:
                    self.http.cookies.set(
                        cookie["name"], cookie["value"],
                        domain=cookie["domain"].lstrip("."), path=cookie.get("path", "/"),
                    )
            else:
                self._dump_failure(page)
            browser.close()
            return ok

    @staticmethod
    def _visible(page, selector):
        for handle in page.query_selector_all(selector):
            try:
                if handle.is_visible() and handle.is_enabled():
                    return handle
            except Exception:
                continue
        return None

    def _fill_one_step(self, page, username, password,
                       user_sel, pass_sel, submit_sel) -> bool:
        """Fill whatever this page of the login chain is asking for.

        Written against the shape of login forms rather than one school's
        markup, so a USG SSO redesign does not break it. Override with
        D2L_USER_SELECTOR / D2L_PASS_SELECTOR / D2L_SUBMIT_SELECTOR if it does.
        """
        acted = False
        user_field = self._visible(page, user_sel) if user_sel else (
            self._visible(page, "input[type=email]")
            or self._visible(page, "input[name*='user' i]")
            or self._visible(page, "input[id*='user' i]")
            or self._visible(page, "input[name*='login' i]")
            or self._visible(page, "input[type=text]")
        )
        pass_field = self._visible(page, pass_sel or "input[type=password]")

        if user_field and not user_field.input_value():
            user_field.fill(username)
            acted = True
        if pass_field:
            pass_field.fill(password)
            acted = True
        if not acted:
            return False

        submit = self._visible(page, submit_sel) if submit_sel else (
            self._visible(page, "button[type=submit]")
            or self._visible(page, "input[type=submit]")
            or self._visible(page, "#submitButton")
        )
        if submit:
            submit.click()
        else:
            (pass_field or user_field).press("Enter")
        return True

    def _dump_failure(self, page) -> None:
        """If login fails, leave behind enough to diagnose it in one look."""
        debug = self.state_dir / "login-failure"
        debug.mkdir(exist_ok=True)
        try:
            page.screenshot(path=str(debug / "page.png"), full_page=True)
            (debug / "page.html").write_text(page.content())
            (debug / "url.txt").write_text(page.url)
        except Exception:
            pass
