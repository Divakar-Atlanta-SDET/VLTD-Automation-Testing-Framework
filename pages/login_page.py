"""
Login Page Object Model for the VLTD Admin Portal.

URL: /auth/login
Page title: VLTD Portal

All locators use semantic Playwright role/label-based selectors so they
remain stable even if CSS classes or element IDs change.
"""

import os
import re
from playwright.sync_api import Page, expect


class LoginPage:
    """Page Object for the VLTD login page (/auth/login)."""

    # ── URL ──────────────────────────────────────────────────────────────────
    PATH = "/auth/login"

    def __init__(self, page: Page) -> None:
        self.page = page

        # ── Locators (semantic, role-based) ───────────────────────────────────

        # Header / navigation
        self.home_link = page.get_by_role("link", name="Go to VLTD home")
        self.dark_theme_toggle = page.get_by_role(
            "button", name="Switch to dark theme"
        )
        self.portal_access_link = page.get_by_role("link", name="Portal Access")
        self.mobile_menu_button = page.get_by_role("button", name="Open menu")

        # Aside / marketing panel
        self.vltd_logo = page.get_by_role("img", name="VLTD")
        self.marketing_heading = page.get_by_role(
            "heading", name="Secure access to your VLTD workspace"
        )

        # Login form
        self.page_heading = page.get_by_role(
            "heading", name="Sign in to your account", level=1
        )
        self.email_input = page.get_by_role("textbox", name="Email address *")
        self.password_input = page.get_by_role("textbox", name="Password *")
        self.sign_in_button = page.get_by_role("button", name="Sign in")

        # Inline validation alerts (appear on attempted submit with empty fields)
        self.email_error = page.get_by_role("alert").filter(
            has_text="Email is required."
        )
        self.password_error = page.get_by_role("alert").filter(
            has_text="Password is required."
        )

        # Footer / support
        self.support_link = page.get_by_role("link", name="Visit Support centre")
        self.footer_support_link = page.get_by_role("link", name="Support centre").last
        self.support_email_link = page.get_by_role(
            "link", name="support@vltd.gov.in"
        )

    # ── Navigation ────────────────────────────────────────────────────────────

    def navigate(self, base_url: str | None = None) -> "LoginPage":
        """Navigate to the login page.

        Args:
            base_url: Override base URL. Falls back to the BASE_URL env var.
        """
        url = base_url or os.environ.get("BASE_URL", "")
        self.page.goto(url if url.endswith(self.PATH) else url + self.PATH)
        return self

    # ── Actions ───────────────────────────────────────────────────────────────

    def fill_email(self, email: str) -> "LoginPage":
        """Type into the email address field."""
        self.email_input.fill(email)
        return self

    def fill_password(self, password: str) -> "LoginPage":
        """Type into the password field."""
        self.password_input.fill(password)
        return self

    def toggle_password_visibility(self) -> "LoginPage":
        """Click the show/hide password toggle button."""
        # The toggle sits inside the password field group; locate it by its
        # proximity to the password textbox rather than a brittle CSS selector.
        self.password_input.locator("..").get_by_role("button").click()
        return self

    def click_sign_in(self) -> "LoginPage":
        """Click the Sign in button."""
        self.sign_in_button.click()
        return self

    def login(self, email: str, password: str) -> None:
        """Full login flow: fill email + password then click Sign in.

        After a successful login the browser will redirect away from /auth/login.
        """
        self.fill_email(email).fill_password(password).click_sign_in()

    def submit_empty_form(self) -> "LoginPage":
        """Click Sign in without entering any credentials to trigger validation."""
        self.click_sign_in()
        return self

    def click_support_link(self) -> None:
        """Click the 'Visit Support centre' link inside the login card."""
        self.support_link.click()

    def toggle_dark_theme(self) -> "LoginPage":
        """Click the dark / light theme toggle in the header."""
        self.dark_theme_toggle.click()
        return self

    # ── Assertions / wait helpers ──────────────────────────────────────────────

    def expect_page_loaded(self) -> None:
        """Assert the login page is fully loaded with the expected heading."""
        expect(self.page_heading).to_be_visible()
        expect(self.email_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.sign_in_button).to_be_visible()

    def expect_email_error_visible(self) -> None:
        """Assert the 'Email is required' validation message is visible."""
        expect(self.email_error).to_be_visible()

    def expect_password_error_visible(self) -> None:
        """Assert the 'Password is required' validation message is visible."""
        expect(self.password_error).to_be_visible()

    def expect_logged_in(self, expected_path: str = "/tc/dashboard") -> None:
        """Assert the browser has navigated away to the post-login path."""
        expect(self.page).to_have_url(
            re.compile(re.escape(expected_path)),
            timeout=15_000,
        )

    def expect_still_on_login(self) -> None:
        """Assert we are still on the login page (login was rejected)."""
        expect(self.page).to_have_url(
            re.compile(re.escape(self.PATH)),
            timeout=5_000,
        )

    def expect_email_field_invalid(self) -> None:
        """Assert the email field is in an invalid state (aria-invalid)."""
        expect(self.email_input).to_have_attribute("aria-invalid", "true")

    def expect_password_field_invalid(self) -> None:
        """Assert the password field is in an invalid state (aria-invalid)."""
        expect(self.password_input).to_have_attribute("aria-invalid", "true")

    # ── Session / error helpers ────────────────────────────────────────────────

    AUTH_STORAGE_KEYS = ("access_token", "refresh_token", "auth_user")

    @property
    def server_error(self):
        """Server-side rejection message shown for bad credentials."""
        return self.page.get_by_role("alert").filter(has_text="Invalid email or password.")

    def stored_auth_keys(self) -> list[str]:
        """Auth-related keys currently in localStorage (empty when logged out)."""
        keys = self.page.evaluate("() => Object.keys(localStorage)")
        return [k for k in keys if k in self.AUTH_STORAGE_KEYS]

    def expect_no_session(self) -> None:
        """Assert no auth token/user is stored in the browser."""
        assert self.stored_auth_keys() == [], "Auth data still present in localStorage"
