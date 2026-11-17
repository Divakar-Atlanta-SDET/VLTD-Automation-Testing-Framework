"""
Login tests for the VLTD Admin Portal.

Expected behaviour comes from "VLTD - How Everything Works", chapter 4 (Signing in and staying signed in): sign-in
opens the role's home page, a page requested before sign-in is opened afterwards, 15 minutes without activity signs
the user out, and a reused (stolen) refresh key ends all sessions of that user.

Also covered: the login form (load, required-field validation), invalid credentials (one generic message), session
persistence, logout (server side too), tampered token, protected routes, and input safety (script / SQL-like and
malformed values).

Markers:
  smoke  - quick sanity check
  auth   - authentication suite
"""

import re
import time

import pytest
from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from utils.api_client import ApiClient
from utils.staff_lab import StaffLab


# ── describe: Login Page ─────────────────────────────────────────────────────

class TestLoginPage:
    """Login page – functional tests."""

    # ── Setup ─────────────────────────────────────────────────────────────────

    @pytest.fixture(autouse=True)
    def setup(self, login_page_obj: LoginPage) -> None:
        """Each test starts on a freshly-loaded login page."""
        self.login = login_page_obj

    # ── 1. Page loads correctly ───────────────────────────────────────────────

    @pytest.mark.smoke
    @pytest.mark.auth
    def test_login_page_loads(self) -> None:
        """Login page must display all key UI elements on load."""
        # Heading
        expect(self.login.page_heading).to_be_visible()

        # Form fields
        expect(self.login.email_input).to_be_visible()
        expect(self.login.password_input).to_be_visible()

        # Submit button
        expect(self.login.sign_in_button).to_be_visible()

        # Support link
        expect(self.login.support_link).to_be_visible()

        # Marketing panel heading
        expect(self.login.marketing_heading).to_be_visible()

    # ── 2. Happy-path admin login ─────────────────────────────────────────────


    # ── 3. Empty-form validation ──────────────────────────────────────────────

    @pytest.mark.auth
    def test_empty_form_shows_required_errors(self) -> None:
        """Submitting an empty form must show both required-field alerts."""
        # Submit without entering any credentials
        self.login.submit_empty_form()

        # Both validation alerts appear
        expect(self.login.email_error).to_be_visible()
        expect(self.login.password_error).to_be_visible()

        # Fields must be marked invalid
        expect(self.login.email_input).to_have_attribute("aria-invalid", "true")
        expect(self.login.password_input).to_have_attribute("aria-invalid", "true")

        # Page must NOT navigate away
        expect(self.login.page).to_have_url(
            re.compile(r"/auth/login"),
        )

    # ── 4. Empty email only ───────────────────────────────────────────────────

    @pytest.mark.auth
    def test_missing_email_shows_email_error(self, admin_credentials: dict) -> None:
        """Submitting with email blank (password filled) triggers email error."""
        # Fill password only
        self.login.fill_password(admin_credentials["password"])
        self.login.click_sign_in()

        # Email error visible
        expect(self.login.email_error).to_be_visible()

        # Password error should NOT appear (password was provided)
        expect(self.login.password_error).not_to_be_visible()

    # ── 5. Empty password only ────────────────────────────────────────────────

    @pytest.mark.auth
    def test_missing_password_shows_password_error(
        self, admin_credentials: dict
    ) -> None:
        """Submitting with password blank (email filled) triggers password error."""
        # Fill email only
        self.login.fill_email(admin_credentials["username"])
        self.login.click_sign_in()

        # Password error visible
        expect(self.login.password_error).to_be_visible()

        # Email error should NOT appear (email was provided)
        expect(self.login.email_error).not_to_be_visible()

    # ── 6. Invalid credentials ────────────────────────────────────────────────


    # ── 7. Password show/hide toggle ──────────────────────────────────────────


    # ── 8. Support link ───────────────────────────────────────────────────────


# ── describe: Login – session & security (AUTH-001..009) ─────────────────────

DASHBOARD_URL = re.compile(r"/tc/dashboard")
LOGIN_URL = re.compile(r"/auth/login")
TC_HEADING = "Transport Commissioner Dashboard"
LEAK_PATTERN = re.compile(
    r"sqlstate|syntax error|stack ?trace|traceback|exception|eyJ[\w-]{10,}", re.I
)


class TestLoginSecurity:
    """Login page – session, negative-path and input-security tests."""

    @pytest.fixture(autouse=True)
    def setup(self, login_page_obj: LoginPage) -> None:
        self.login = login_page_obj
        self.page = login_page_obj.page

    def _sign_in_admin(self, admin_credentials: dict) -> None:
        self.login.login(admin_credentials["username"], admin_credentials["password"])
        expect(self.page).to_have_url(DASHBOARD_URL, timeout=15_000)

    # ── L1 / AUTH-001 ────────────────────────────────────────────────────────

    @pytest.mark.smoke
    @pytest.mark.auth
    def test_login_lands_on_role_dashboard_and_session_persists(
        self, admin_credentials: dict
    ) -> None:
        """AUTH-001: admin login lands on the TC dashboard and survives a reload."""
        self._sign_in_admin(admin_credentials)

        expect(self.page.get_by_role("heading", name=TC_HEADING, level=1)).to_be_visible()
        expect(self.login.sign_in_button).to_have_count(0)
        assert {"access_token", "refresh_token"} <= set(self.login.stored_auth_keys())

        self.page.reload()
        expect(self.page).to_have_url(DASHBOARD_URL)
        expect(self.page.get_by_role("heading", name=TC_HEADING, level=1)).to_be_visible()

    # ── L2 + L3 / AUTH-002 ───────────────────────────────────────────────────

    @pytest.mark.auth
    def test_invalid_credentials_show_one_generic_error_and_no_session(self, admin_credentials: dict) -> None:
        """AUTH-002: an unknown account and a wrong password get the SAME message (no account enumeration), no session, no leakage."""
        messages = []
        for email in ("no.such.user@example.com", admin_credentials["username"]):
            self.login.fill_email(email)
            self.login.fill_password("WrongPassword!99")
            self.login.click_sign_in()

            expect(self.login.server_error).to_be_visible(timeout=10_000)
            messages.append(self.login.server_error.first.inner_text().strip())
            self.login.expect_still_on_login()
            self.login.expect_no_session()
            assert "WrongPassword" not in self.page.url
            assert not LEAK_PATTERN.search(self.page.locator("body").inner_text())

        assert messages[0] == messages[1], f"The message reveals whether the account exists: {messages}"

        # A protected page is still blocked
        self.page.goto("/tc/dashboard")
        expect(self.page).to_have_url(LOGIN_URL)

    # ── L4 / AUTH-003 ────────────────────────────────────────────────────────

    @pytest.mark.smoke
    @pytest.mark.auth
    @pytest.mark.parametrize("path", ["/tc/dashboard", "/tc/helpdesk"])
    def test_protected_routes_redirect_unauthenticated_users(self, path: str) -> None:
        """AUTH-003: protected pages redirect to login and render no portal content."""
        self.page.goto(path)

        expect(self.page).to_have_url(LOGIN_URL)
        expect(self.page.get_by_role("heading", name=TC_HEADING)).to_have_count(0)
        self.login.expect_no_session()

    # ── L5 / AUTH-004 ────────────────────────────────────────────────────────

    @pytest.mark.auth
    def test_tampered_token_is_rejected(self, admin_credentials: dict) -> None:
        """AUTH-004: a malformed access/refresh token cannot keep the session alive."""
        self._sign_in_admin(admin_credentials)

        self.page.evaluate(
            """() => {
                localStorage.setItem('access_token', 'garbage.token.value');
                localStorage.setItem('refresh_token', 'garbage-refresh-token');
            }"""
        )
        self.page.goto("/tc/dashboard")

        expect(self.page).to_have_url(LOGIN_URL, timeout=15_000)
        expect(self.page.get_by_role("heading", name=TC_HEADING)).to_have_count(0)

    # ── L6 / AUTH-005 ────────────────────────────────────────────────────────

    @pytest.mark.smoke
    @pytest.mark.auth
    def test_logout_invalidates_session(self, admin_credentials: dict) -> None:
        """AUTH-005: after logout, Back / reload / direct URL cannot restore access."""
        self._sign_in_admin(admin_credentials)
        token = self.page.evaluate("() => localStorage.getItem('access_token')")

        DashboardPage(self.page).logout()

        expect(self.page).to_have_url(LOGIN_URL, timeout=10_000)
        self.login.expect_no_session()

        # The session is ended on the server, not just forgotten by the browser
        api = ApiClient(self.page.context.request, self.login.page.url.split("/auth")[0], token)
        assert api.get("/api/auth/me").status == 401, "The token still works after logout"

        # Back button
        self.page.go_back()
        expect(self.page.get_by_role("heading", name=TC_HEADING)).to_have_count(0)
        expect(self.page).not_to_have_url(DASHBOARD_URL)

        # Reload + direct navigation
        self.page.reload()
        self.page.goto("/tc/dashboard")
        expect(self.page).to_have_url(LOGIN_URL)

    # ── Guide ch.4, "How it works" step 3 ────────────────────────────────────

    @pytest.mark.auth
    def test_signing_in_returns_to_the_page_that_was_requested(self, admin_credentials: dict) -> None:
        """Ch.4: a page opened before signing in is shown after signing in, not the default home page."""
        self.page.goto("/tc/helpdesk")
        expect(self.page).to_have_url(re.compile(r"/auth/login\?redirect="))

        self.login.login(admin_credentials["username"], admin_credentials["password"])

        expect(self.page).to_have_url(re.compile(r"/tc/helpdesk"), timeout=20_000)

    # ── Guide ch.4, "Automatic sign-out after inactivity" ────────────────────

    @pytest.mark.auth
    def test_user_is_signed_out_after_15_minutes_without_activity(self, admin_credentials: dict) -> None:
        """Ch.4: still signed in at 14 minutes of inactivity, signed out (session cleared) after 15."""
        self.page.clock.install()  # fake time: the test does not wait 15 real minutes
        self.page.goto("/auth/login")
        self.login.login(admin_credentials["username"], admin_credentials["password"])
        expect(self.page).to_have_url(DASHBOARD_URL, timeout=30_000)

        self.page.clock.run_for("14:00")
        expect(self.page).to_have_url(DASHBOARD_URL)
        assert "access_token" in self.login.stored_auth_keys()

        self.page.clock.run_for("01:30")
        expect(self.page).to_have_url(LOGIN_URL, timeout=15_000)
        self.login.expect_no_session()

    # ── L8 / AUTH-009 ────────────────────────────────────────────────────────

    @pytest.mark.auth
    @pytest.mark.parametrize(
        "payload, field",
        [
            pytest.param("<script>alert(1)</script>", "email", id="script-in-email"),
            pytest.param("' OR '1'='1' --", "password", id="sql-in-password"),
        ],
    )
    def test_script_like_input_is_handled_safely(self, payload: str, field: str) -> None:
        """AUTH-009: injection-style strings never execute, authenticate or leak errors."""
        dialogs: list[str] = []
        self.page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        if field == "email":
            self.login.login(payload, "SomePassword123!")
        else:
            self.login.login("payload.tester@example.com", payload)

        # Wait for either client validation or the server verdict
        expect(self.page.get_by_role("alert").first).to_be_visible(timeout=10_000)
        self.login.expect_still_on_login()
        self.login.expect_no_session()

        assert dialogs == [], f"JS dialog fired: {dialogs}"
        expect(self.page.locator("img[src='x']")).to_have_count(0)
        assert not LEAK_PATTERN.search(self.page.locator("body").inner_text())

    # ── L9 ───────────────────────────────────────────────────────────────────

    @pytest.mark.auth
    @pytest.mark.parametrize("bad_email", ["notanemail", "missing@tld"])
    def test_malformed_email_is_rejected(self, bad_email: str) -> None:
        """Malformed email addresses cannot sign in and show a validation message."""
        self.login.login(bad_email, "SomePassword123!")

        expect(self.page.get_by_role("alert").first).to_be_visible(timeout=10_000)
        self.login.expect_still_on_login()
        self.login.expect_no_session()

    # ── L10 ──────────────────────────────────────────────────────────────────



# ── describe: Login – refresh keys (guide ch.4, "Theft protection") ───────────

@pytest.fixture
def fresh_account(playwright, base_url: str, admin_credentials: dict):
    """A throw-away staff account, so ending its sessions cannot disturb the shared admin login used by other tests."""
    request = playwright.request.new_context()
    admin = ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    account = StaffLab(admin).new_staff()
    yield request, base_url, account
    request.dispose()


def _sign_in(request, origin: str, email: str, password: str) -> dict:
    for attempt in range(4):  # parallel workers can briefly trip rate limiting / transient errors
        response = ApiClient(request, origin).post("/api/auth/login", json={"email": email, "password": password}, token=None)
        if response.ok or response.status not in (429, 500, 502, 503, 504):
            break
        time.sleep(2 * (attempt + 1))
    assert response.ok, f"{response.status} {response.text()[:200]}"
    return response.json()["data"]


def _refresh(request, origin: str, refresh_token: str):
    return ApiClient(request, origin).post("/api/auth/refresh", json={"refresh_token": refresh_token}, token=None)


@pytest.mark.auth
def test_refresh_issues_new_keys_and_the_used_refresh_key_is_rejected(fresh_account) -> None:
    """Ch.4: refreshing gives a working access token and a NEW refresh key; the old refresh key cannot be used again."""
    request, origin, account = fresh_account
    session = _sign_in(request, origin, account.email, account.password)

    refreshed = _refresh(request, origin, session["refresh_token"])
    assert refreshed.status == 200, refreshed.text()[:200]
    new = refreshed.json()["data"]
    assert new["refresh_token"] != session["refresh_token"]
    assert ApiClient(request, origin, new["access_token"]).get("/api/auth/me").status == 200

    assert _refresh(request, origin, session["refresh_token"]).status == 401, "A used refresh key was accepted again"


@pytest.mark.auth
@pytest.mark.xfail(
    reason="BUG-033: reusing an old refresh key is refused, but the user's other sessions keep working "
    "(the guide says all sessions of that user must end)",
    strict=False,
)
def test_reusing_an_old_refresh_key_ends_all_sessions_of_the_user(fresh_account) -> None:
    """Ch.4 Theft protection: a reused refresh key means it was stolen, so every session of that user is ended."""
    request, origin, account = fresh_account
    session = _sign_in(request, origin, account.email, account.password)
    legitimate = _refresh(request, origin, session["refresh_token"]).json()["data"]

    assert _refresh(request, origin, session["refresh_token"]).status == 401  # the thief replays the old key

    assert ApiClient(request, origin, legitimate["access_token"]).get("/api/auth/me").status == 401, (
        "The legitimate session is still alive after the old key was replayed"
    )
    assert _refresh(request, origin, legitimate["refresh_token"]).status == 401
