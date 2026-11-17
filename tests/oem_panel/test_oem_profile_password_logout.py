"""
OEM > Profile, Change Password and Logout, through the screen and the API.

Source: guide chapter 4 (forced password change on first login or after 90 days, 15-minute inactivity sign-out, sessions are
tracked, theft protection ends all of a user's sessions). The guide gives no section for the Profile screen itself or for an
explicit Logout; what is checked there is taken from the application.

Every test that changes a password, or that needs a session to end, uses its OWN dedicated throw-away OEM account
(`profile_account` / `profile_page` fixtures in conftest.py) - never the shared `.env` account the rest of the suite
depends on. Nothing here ever prints a password.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from pages.oem_panel.dashboard import OemDashboardPage
from pages.oem_panel.profile import OemProfilePage
from utils import data_generator as data
from utils import oem_profile_api as pf
from utils.api_client import ApiClient

pytestmark = [pytest.mark.oem_panel]


# ── Profile: view and edit ──────────────────────────────────────────────────────

def test_the_profile_shows_the_signed_in_users_own_details(profile_page: Page, profile_account: dict) -> None:
    page = OemProfilePage(profile_page).open()

    fields = page.fields()

    assert fields["Email Address"] == profile_account["email"]
    assert {"Full Name", "Email Address", "Contact Number", "Address"} <= fields.keys()


def test_editing_the_profile_persists_after_reload_and_relogin(profile_page: Page, profile_account: dict, admin_api: ApiClient) -> None:
    new_name = f"AUTO QA Profile {data.unique_suffix()}"
    page = OemProfilePage(profile_page).open()
    before = page.fields()

    page.start_edit()
    page.fill(name=new_name)

    with profile_page.expect_response(lambda r: "/api/users/" in r.url and r.request.method == "PUT") as sent:
        page.save()

    assert sent.value.status == 200, sent.value.text()[:300]
    expect(profile_page.get_by_text("Profile updated successfully.")).to_be_visible()
    assert page.fields()["Full Name"] == new_name

    profile_page.reload()
    page.wait_until_open()
    assert page.fields()["Full Name"] == new_name, "the new name did not survive a reload"

    OemDashboardPage(profile_page).logout()  # a bare navigation to /auth/login while still signed in just bounces back to the dashboard
    expect(profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)
    login = LoginPage(profile_page)
    login.fill_email(profile_account["email"]).fill_password(profile_account["password"]).click_sign_in()
    expect(profile_page).to_have_url(re.compile(r"/oem/dashboard"), timeout=40_000)
    assert OemProfilePage(profile_page).open().fields()["Full Name"] == new_name, "the new name did not survive signing out and back in"
    assert before["Contact Number"] == OemProfilePage(profile_page).fields()["Contact Number"], "an unrelated field changed"


@pytest.mark.parametrize(
    "field, value, message",
    [("name", "", "Full name is required."), ("name", "    ", "Full name is required."), ("email", "", "Email address is required."),
     ("email", "a@b", "Enter a valid email address."), ("contact_no", "987654321", "Contact number must contain exactly 10 digits."),
     ("contact_no", "98765abcde", "Contact number must contain exactly 10 digits.")],
    ids=["name-empty", "name-spaces", "email-empty", "email-invalid", "contact-9-digits", "contact-letters"],
)
def test_editing_the_profile_with_an_invalid_value_is_refused(profile_page: Page, field: str, value: str, message: str) -> None:
    page = OemProfilePage(profile_page).open()
    before = page.fields()
    page.start_edit()

    page.fill(**{field: value})
    page.save()

    expect(profile_page.get_by_text(message, exact=True)).to_be_visible()
    page.cancel_button.click()
    assert page.fields() == before, "the profile changed although the save was refused"


def test_editing_the_profile_to_an_email_another_account_already_uses_is_refused(profile_page: Page, oem_org: dict) -> None:
    page = OemProfilePage(profile_page).open()
    before = page.fields()
    page.start_edit()

    page.fill(email=oem_org["contact_email"])
    page.save()

    expect(profile_page.get_by_text("This email address is already in use.", exact=True)).to_be_visible()
    page.cancel_button.click()
    assert page.fields()["Email Address"] == before["Email Address"]


# ── Change Password: the Profile tab ───────────────────────────────────────────

def test_changing_the_password_updates_it_for_the_next_login(profile_page: Page, profile_account: dict, oem_api: ApiClient) -> None:
    """A successful change does not sign the current tab out (see BUG-077); what it does change is which password a NEW sign-in needs."""
    new_password = data.PASSWORD + "7"
    page = OemProfilePage(profile_page).open()
    form = page.open_change_password()
    form.fill(profile_account["password"], new_password)

    with profile_page.expect_response(lambda r: "/api/users/" in r.url and r.request.method == "PUT") as sent:
        form.submit()

    assert sent.value.status == 200, sent.value.text()[:300]
    expect(profile_page.get_by_text("Profile updated successfully.")).to_be_visible()

    request = profile_page.context.request
    old = request.fetch(f"{profile_page.url.split('/oem')[0]}/api/auth/login", method="POST", headers={"Accept": "application/json"}, data={"email": profile_account["email"], "password": profile_account["password"]}, max_redirects=0)
    assert old.status != 200, "the old password still signs in after a successful change"
    new = request.fetch(f"{profile_page.url.split('/oem')[0]}/api/auth/login", method="POST", headers={"Accept": "application/json"}, data={"email": profile_account["email"], "password": new_password}, max_redirects=0)
    assert new.status == 200, f"the new password does not sign in: {new.status} {new.text()[:200]}"


@pytest.mark.xfail(reason="BUG-077: changing the password does not end the current session - the access token used to request the change keeps working afterwards", strict=False)
def test_changing_the_password_ends_the_current_sessions_own_token(profile_page: Page, profile_account: dict) -> None:
    tokens = pf.page_tokens(profile_page)
    page = OemProfilePage(profile_page).open()
    form = page.open_change_password()
    form.fill(profile_account["password"], data.PASSWORD + "7")
    form.submit()
    expect(profile_page.get_by_text("Profile updated successfully.")).to_be_visible()

    request = profile_page.context.request
    response = request.fetch(f"{profile_page.url.split('/oem')[0]}/api/auth/me", headers={"Accept": "application/json", "Authorization": f"Bearer {tokens['access']}"}, max_redirects=0)
    assert response.status == 401, f"the token used to change the password still works afterwards: {response.status}"


@pytest.mark.parametrize(
    "current, new, confirm, message",
    [("Wrong-Current-Password-1", None, None, "Current password is incorrect."), (None, "Short1A", None, "Use at least 10 characters"),
     (None, "alllowercase1", None, "Use at least 10 characters"), (None, "ALLUPPERCASE1", None, "Use at least 10 characters"),
     (None, "NoDigitsHere", None, "Use at least 10 characters"), (None, data.PASSWORD + "7", data.PASSWORD + "8", "do not match")],
    ids=["wrong-current", "too-short", "no-uppercase", "no-lowercase", "no-digit", "mismatch"],
)
def test_changing_the_password_with_an_invalid_value_is_refused(profile_page: Page, profile_account: dict, current, new, confirm, message: str) -> None:
    page = OemProfilePage(profile_page).open()
    form = page.open_change_password()

    form.fill(current or profile_account["password"], new or data.PASSWORD + "7", confirm)
    form.submit()

    expect(profile_page.get_by_role("alert").filter(has_text=message)).to_be_visible()  # the real error, not the static hint text that mentions the same rule
    expect(form.submit_button).to_be_visible()  # the form stays open; nothing was sent that could have changed anything


def test_the_new_password_must_differ_from_the_current_one(profile_page: Page, profile_account: dict) -> None:
    page = OemProfilePage(profile_page).open()
    form = page.open_change_password()

    form.fill(profile_account["password"], profile_account["password"])
    form.submit()

    expect(profile_page.get_by_text("New password must be different from the current password.", exact=True)).to_be_visible()
    expect(form.submit_button).to_be_visible()


def test_the_password_fields_can_be_shown_and_hidden(profile_page: Page) -> None:
    page = OemProfilePage(profile_page).open()
    form = page.open_change_password()
    form.current_password.fill("whatever-is-typed-here")

    expect(form.current_password).to_have_attribute("type", "password")
    form.toggle_visibility(form.current_password)
    expect(form.current_password).to_have_attribute("type", "text")
    form.toggle_visibility(form.current_password)
    expect(form.current_password).to_have_attribute("type", "password")


# ── Change Password: the forced first-login page ───────────────────────────────

def test_a_new_account_must_change_its_temporary_password_before_using_the_panel(page: Page, admin_api: ApiClient, base_url: str) -> None:
    """The forced-redirect part of this is already covered by test_oem_access_and_isolation.py; this adds the form itself."""
    from utils.oem_panel_api import create_oem_account

    account = create_oem_account(admin_api)
    login = LoginPage(page)
    login.navigate(base_url)
    login.login(account["email"], account["password"])
    expect(page).to_have_url(re.compile(r"/auth/change-password"), timeout=30_000)

    from pages.oem_panel.profile import ChangePasswordForm
    form = ChangePasswordForm(page)
    new_password = data.PASSWORD + "9"
    form.fill(account["password"], new_password)
    form.submit()

    expect(page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)
    login.login(account["email"], new_password)
    expect(page).to_have_url(re.compile(r"/oem/dashboard"), timeout=40_000)


# ── Logout ──────────────────────────────────────────────────────────────────────

def test_logout_signs_out_and_protected_pages_cannot_be_reached_afterwards(profile_page: Page) -> None:
    dashboard = OemDashboardPage(profile_page)

    dashboard.logout()

    expect(profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)
    storage = profile_page.evaluate("() => ({access: localStorage.getItem('access_token'), refresh: localStorage.getItem('refresh_token')})")
    assert storage == {"access": None, "refresh": None}, "the tokens are still in local storage after logout"

    profile_page.goto("/oem/dashboard")
    expect(profile_page).to_have_url(re.compile(r"/auth/login"))

    profile_page.reload()
    expect(profile_page).to_have_url(re.compile(r"/auth/login"))


def test_logout_ends_the_access_token(profile_page: Page) -> None:
    tokens = pf.page_tokens(profile_page)
    dashboard = OemDashboardPage(profile_page)

    dashboard.logout()
    expect(profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)

    request = profile_page.context.request
    response = request.fetch(f"{profile_page.url.split('/auth')[0]}/api/auth/me", headers={"Accept": "application/json", "Authorization": f"Bearer {tokens['access']}"}, max_redirects=0)
    assert response.status == 401, f"the pre-logout access token still works: {response.status}"


@pytest.mark.xfail(reason="BUG-074: logout ends the access token but not the refresh token, which still issues a new access token afterwards", strict=False)
def test_logout_ends_the_refresh_token_too(profile_page: Page) -> None:
    tokens = pf.page_tokens(profile_page)
    dashboard = OemDashboardPage(profile_page)

    dashboard.logout()
    expect(profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)

    request = profile_page.context.request
    response = request.fetch(f"{profile_page.url.split('/auth')[0]}/api/auth/refresh", method="POST", headers={"Accept": "application/json"}, data={"refresh_token": tokens["refresh"]}, max_redirects=0)
    assert response.status != 200, f"the pre-logout refresh token still works after logout: {response.status} {response.text()[:150]}"


# ── Security / API-only (expected failures; see bug_report.md) ─────────────────

@pytest.mark.xfail(reason="BUG-072: GET /api/users/{id} returns any user's full profile, not only the caller's own", strict=False)
def test_reading_another_users_profile_is_refused(oem_api: ApiClient, admin_api: ApiClient) -> None:
    other_id = admin_api.get("/api/auth/me").json()["data"]["id"]

    response = oem_api.get(f"{pf.USERS}/{other_id}")

    assert response.status in (403, 404), f"reading another user's profile answered {response.status}, not a refusal"


@pytest.mark.xfail(reason="BUG-075: an unknown user id crashes with 500 instead of answering 404", strict=False)
def test_an_unknown_user_id_is_not_found(oem_api: ApiClient) -> None:
    import uuid

    response = oem_api.get(f"{pf.USERS}/{uuid.uuid4()}")

    assert response.status == 404, f"{response.status} {response.text()[:150]}"


def test_the_profile_api_needs_a_login(oem_api: ApiClient) -> None:
    me_id = oem_api.get(pf.ME).json()["data"]["id"]

    assert oem_api.get(f"{pf.USERS}/{me_id}", token=None).status == 401
    assert oem_api.get(pf.ME, token=None).status == 401


def test_a_forged_token_is_refused(oem_api: ApiClient) -> None:
    assert oem_api.get(pf.ME, token="abc.def.ghi").status == 401
