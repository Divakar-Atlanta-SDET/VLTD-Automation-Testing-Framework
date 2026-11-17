"""
Fitment Centre > Profile, Change Password and Logout, through the screen and the API.

Modelled directly on `tests/oem_panel/test_oem_profile_password_logout.py`: `/fc/profile` is structurally identical
to `/oem/profile` (same heading, same two tabs, same field labels - confirmed by manual exploration 2026-11-05),
and `/api/users/{id}` / `/api/auth/*` are the same, role-agnostic endpoints the OEM suite already found several
bugs on. The main purpose of this file is to confirm those bugs (BUG-072, 074, 075, 077) reproduce identically from
a Fitment Centre account - which they do (manually confirmed before writing this file) - rather than to rediscover
them from scratch.

A freshly registered Fitment Centre DOES need a forced first-login password change, same as an OEM account - the
field is named `is_password_change_required` in the login response rather than OEM's `force_password_change`, but
the mechanism (redirect to `/auth/change-password`) is identical; confirmed directly against the real UI 2026-11-05
after an initial exploration had looked for the wrong field name and wrongly concluded there was none.

Every test that changes a password, or that needs a session to end, uses its OWN dedicated throw-away Fitment
Centre account (`fc_profile_account` / `fc_profile_page` fixtures in conftest.py) - never the shared `FC_USERNAME`
account the rest of the FC suite depends on. Nothing here ever prints a password.

BUG-073 (the critical cross-account write / account-takeover path) and BUG-076 (leading/trailing-space mismatch
between the two change-password endpoints) were both manually re-confirmed from FC accounts before writing this
file, using two disposable accounts with the change restored immediately after - same as the OEM side, these are
deliberately NOT automated as routine regression tests (a live cross-account write should not run on every CI
pass); see bug_report.md's BUG-073 update.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.fc_panel.dashboard import FcDashboardPage
from pages.fc_panel.profile import ChangePasswordForm, FcProfilePage
from pages.login_page import LoginPage
from utils import data_generator as data
from utils import oem_profile_api as pf
from utils.api_client import ApiClient

pytestmark = [pytest.mark.fc_panel]


# ── Profile: view and edit ──────────────────────────────────────────────────────

def test_the_profile_shows_the_signed_in_users_own_details(fc_profile_page: Page, fc_profile_account: dict) -> None:
    page = FcProfilePage(fc_profile_page).open()

    fields = page.fields()

    assert fields["Email Address"] == fc_profile_account["email"]
    assert {"Full Name", "Email Address", "Contact Number", "Address"} <= fields.keys()


def test_editing_the_profile_persists_after_reload_and_relogin(fc_profile_page: Page, fc_profile_account: dict) -> None:
    new_name = f"AUTO QA FC Profile {data.unique_suffix()}"
    page = FcProfilePage(fc_profile_page).open()
    before = page.fields()

    page.start_edit()
    page.fill(name=new_name)

    with fc_profile_page.expect_response(lambda r: "/api/users/" in r.url and r.request.method == "PUT") as sent:
        page.save()

    assert sent.value.status == 200, sent.value.text()[:300]
    expect(fc_profile_page.get_by_text("Profile updated successfully.")).to_be_visible()
    assert page.fields()["Full Name"] == new_name

    fc_profile_page.reload()
    page.wait_until_open()
    assert page.fields()["Full Name"] == new_name, "the new name did not survive a reload"

    FcDashboardPage(fc_profile_page).logout()
    expect(fc_profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)
    login = LoginPage(fc_profile_page)
    login.fill_email(fc_profile_account["email"]).fill_password(fc_profile_account["password"]).click_sign_in()
    expect(fc_profile_page).to_have_url(re.compile(r"/fc/dashboard"), timeout=40_000)
    assert FcProfilePage(fc_profile_page).open().fields()["Full Name"] == new_name, "the new name did not survive signing out and back in"
    assert before["Contact Number"] == FcProfilePage(fc_profile_page).fields()["Contact Number"], "an unrelated field changed"


@pytest.mark.parametrize(
    "field, value, message",
    [("name", "", "Full name is required."), ("name", "    ", "Full name is required."), ("email", "", "Email address is required."),
     ("email", "a@b", "Enter a valid email address."), ("contact_no", "987654321", "Contact number must contain exactly 10 digits."),
     ("contact_no", "98765abcde", "Contact number must contain exactly 10 digits.")],
    ids=["name-empty", "name-spaces", "email-empty", "email-invalid", "contact-9-digits", "contact-letters"],
)
def test_editing_the_profile_with_an_invalid_value_is_refused(fc_profile_page: Page, field: str, value: str, message: str) -> None:
    page = FcProfilePage(fc_profile_page).open()
    before = page.fields()
    page.start_edit()

    page.fill(**{field: value})
    page.save()

    expect(fc_profile_page.get_by_text(message, exact=True)).to_be_visible()
    page.cancel_button.click()
    assert page.fields() == before, "the profile changed although the save was refused"


def test_editing_the_profile_to_an_email_another_account_already_uses_is_refused(fc_profile_page: Page, fc_credentials: dict) -> None:
    """Uses the shared FC_USERNAME account's email as the "already in use" target - read-only, nothing about that account changes."""
    page = FcProfilePage(fc_profile_page).open()
    before = page.fields()
    page.start_edit()

    page.fill(email=fc_credentials["username"])
    page.save()

    expect(fc_profile_page.get_by_text("This email address is already in use.", exact=True)).to_be_visible()
    page.cancel_button.click()
    assert page.fields()["Email Address"] == before["Email Address"]


# ── Change Password: the Profile tab ───────────────────────────────────────────

def test_changing_the_password_updates_it_for_the_next_login(fc_profile_page: Page, fc_profile_account: dict) -> None:
    """A successful change does not sign the current tab out (see BUG-077); what it does change is which password a NEW sign-in needs."""
    new_password = data.PASSWORD + "7"
    page = FcProfilePage(fc_profile_page).open()
    form = page.open_change_password()
    form.fill(fc_profile_account["password"], new_password)

    with fc_profile_page.expect_response(lambda r: "/api/users/" in r.url and r.request.method == "PUT") as sent:
        form.submit()

    assert sent.value.status == 200, sent.value.text()[:300]
    expect(fc_profile_page.get_by_text("Profile updated successfully.")).to_be_visible()

    request = fc_profile_page.context.request
    origin = fc_profile_page.url.split("/fc")[0]
    old = request.fetch(f"{origin}/api/auth/login", method="POST", headers={"Accept": "application/json"}, data={"email": fc_profile_account["email"], "password": fc_profile_account["password"]}, max_redirects=0)
    assert old.status != 200, "the old password still signs in after a successful change"
    new = request.fetch(f"{origin}/api/auth/login", method="POST", headers={"Accept": "application/json"}, data={"email": fc_profile_account["email"], "password": new_password}, max_redirects=0)
    assert new.status == 200, f"the new password does not sign in: {new.status} {new.text()[:200]}"


@pytest.mark.xfail(reason="BUG-077: changing the password does not end the current session - confirmed reproducing from an FC account too", strict=False)
def test_changing_the_password_ends_the_current_sessions_own_token(fc_profile_page: Page, fc_profile_account: dict) -> None:
    tokens = pf.page_tokens(fc_profile_page)
    page = FcProfilePage(fc_profile_page).open()
    form = page.open_change_password()
    form.fill(fc_profile_account["password"], data.PASSWORD + "7")
    form.submit()
    expect(fc_profile_page.get_by_text("Profile updated successfully.")).to_be_visible()

    request = fc_profile_page.context.request
    origin = fc_profile_page.url.split("/fc")[0]
    response = request.fetch(f"{origin}/api/auth/me", headers={"Accept": "application/json", "Authorization": f"Bearer {tokens['access']}"}, max_redirects=0)
    assert response.status == 401, f"the token used to change the password still works afterwards: {response.status}"


@pytest.mark.parametrize(
    "current, new, confirm, message",
    [("Wrong-Current-Password-1", None, None, "Current password is incorrect."), (None, "Short1A", None, "Use at least 10 characters"),
     (None, "alllowercase1", None, "Use at least 10 characters"), (None, "ALLUPPERCASE1", None, "Use at least 10 characters"),
     (None, "NoDigitsHere", None, "Use at least 10 characters"), (None, data.PASSWORD + "7", data.PASSWORD + "8", "do not match")],
    ids=["wrong-current", "too-short", "no-uppercase", "no-lowercase", "no-digit", "mismatch"],
)
def test_changing_the_password_with_an_invalid_value_is_refused(fc_profile_page: Page, fc_profile_account: dict, current, new, confirm, message: str) -> None:
    page = FcProfilePage(fc_profile_page).open()
    form = page.open_change_password()

    form.fill(current or fc_profile_account["password"], new or data.PASSWORD + "7", confirm)
    form.submit()

    expect(fc_profile_page.get_by_role("alert").filter(has_text=message)).to_be_visible()
    expect(form.submit_button).to_be_visible()


def test_the_new_password_must_differ_from_the_current_one(fc_profile_page: Page, fc_profile_account: dict) -> None:
    page = FcProfilePage(fc_profile_page).open()
    form = page.open_change_password()

    form.fill(fc_profile_account["password"], fc_profile_account["password"])
    form.submit()

    expect(fc_profile_page.get_by_text("New password must be different from the current password.", exact=True)).to_be_visible()
    expect(form.submit_button).to_be_visible()


def test_the_password_fields_can_be_shown_and_hidden(fc_profile_page: Page) -> None:
    page = FcProfilePage(fc_profile_page).open()
    form = page.open_change_password()
    form.current_password.fill("whatever-is-typed-here")

    expect(form.current_password).to_have_attribute("type", "password")
    form.toggle_visibility(form.current_password)
    expect(form.current_password).to_have_attribute("type", "text")
    form.toggle_visibility(form.current_password)
    expect(form.current_password).to_have_attribute("type", "password")


# ── Change Password: the forced first-login page ───────────────────────────────

def test_a_new_account_must_change_its_temporary_password_before_using_the_panel(page: Page, oem_api: ApiClient, base_url: str) -> None:
    from utils.oem_panel_api import register_fitment_centre

    centre = register_fitment_centre(oem_api)
    login = LoginPage(page)
    login.navigate(base_url)
    login.login(centre["email_id"], data.PASSWORD)
    expect(page).to_have_url(re.compile(r"/auth/change-password"), timeout=30_000)

    new_password = data.PASSWORD + "9"
    form = ChangePasswordForm(page)
    form.fill(data.PASSWORD, new_password)
    form.submit()

    expect(page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)
    login.login(centre["email_id"], new_password)
    expect(page).to_have_url(re.compile(r"/fc/dashboard"), timeout=40_000)


# ── Logout ──────────────────────────────────────────────────────────────────────

def test_logout_signs_out_and_protected_pages_cannot_be_reached_afterwards(fc_profile_page: Page) -> None:
    dashboard = FcDashboardPage(fc_profile_page)

    dashboard.logout()

    expect(fc_profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)
    storage = fc_profile_page.evaluate("() => ({access: localStorage.getItem('access_token'), refresh: localStorage.getItem('refresh_token')})")
    assert storage == {"access": None, "refresh": None}, "the tokens are still in local storage after logout"

    fc_profile_page.goto("/fc/dashboard")
    expect(fc_profile_page).to_have_url(re.compile(r"/auth/login"))

    fc_profile_page.reload()
    expect(fc_profile_page).to_have_url(re.compile(r"/auth/login"))


def test_logout_ends_the_access_token(fc_profile_page: Page) -> None:
    tokens = pf.page_tokens(fc_profile_page)
    dashboard = FcDashboardPage(fc_profile_page)

    dashboard.logout()
    expect(fc_profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)

    request = fc_profile_page.context.request
    origin = fc_profile_page.url.split("/auth")[0]
    response = request.fetch(f"{origin}/api/auth/me", headers={"Accept": "application/json", "Authorization": f"Bearer {tokens['access']}"}, max_redirects=0)
    assert response.status == 401, f"the pre-logout access token still works: {response.status}"


@pytest.mark.xfail(reason="BUG-074: logout ends the access token but not the refresh token - confirmed reproducing from an FC account too", strict=False)
def test_logout_ends_the_refresh_token_too(fc_profile_page: Page) -> None:
    tokens = pf.page_tokens(fc_profile_page)
    dashboard = FcDashboardPage(fc_profile_page)

    dashboard.logout()
    expect(fc_profile_page).to_have_url(re.compile(r"/auth/login"), timeout=20_000)

    request = fc_profile_page.context.request
    origin = fc_profile_page.url.split("/auth")[0]
    response = request.fetch(f"{origin}/api/auth/refresh", method="POST", headers={"Accept": "application/json"}, data={"refresh_token": tokens["refresh"]}, max_redirects=0)
    assert response.status != 200, f"the pre-logout refresh token still works after logout: {response.status} {response.text()[:150]}"


# ── Security / API-only (expected failures; see bug_report.md) ─────────────────

@pytest.mark.xfail(reason="BUG-072: GET /api/users/{id} returns any user's full profile, not only the caller's own - confirmed reproducing from an FC token too", strict=False)
def test_reading_another_users_profile_is_refused(fc_api: ApiClient, oem_api: ApiClient) -> None:
    other_id = pf.me(oem_api)["id"]

    response = fc_api.get(f"{pf.USERS}/{other_id}")

    assert response.status in (403, 404), f"reading another user's profile answered {response.status}, not a refusal"


@pytest.mark.xfail(reason="BUG-075: an unknown user id crashes with 500 instead of answering 404 - confirmed reproducing from an FC token too", strict=False)
def test_an_unknown_user_id_is_not_found(fc_api: ApiClient) -> None:
    import uuid

    response = fc_api.get(f"{pf.USERS}/{uuid.uuid4()}")

    assert response.status == 404, f"{response.status} {response.text()[:150]}"


def test_the_profile_api_needs_a_login(fc_api: ApiClient) -> None:
    me_id = pf.me(fc_api)["id"]

    assert fc_api.get(f"{pf.USERS}/{me_id}", token=None).status == 401
    assert fc_api.get(pf.ME, token=None).status == 401


def test_a_forged_token_is_refused(fc_api: ApiClient) -> None:
    assert fc_api.get(pf.ME, token="abc.def.ghi").status == 401
