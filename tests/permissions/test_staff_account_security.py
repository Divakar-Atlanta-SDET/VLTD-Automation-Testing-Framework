"""
Staff account security around permissions.  Plan: specs/staff-permissions-test-plan.md

  - A newly created staff member must replace the temporary password before using the portal.
    The UI enforces it; the API must too (BUG-018).
  - A malformed record id must give 404, never a server crash (BUG-019).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from utils.api_client import API_PREFIX, ApiClient
from utils.permissions_matrix import PROBE_BY_KEY
from utils.staff_lab import StaffLab

pytestmark = [pytest.mark.permissions]


def test_new_staff_must_change_the_temporary_password_in_the_ui(page: Page, staff_lab: StaffLab) -> None:
    """A freshly created staff member lands on the change-password screen and cannot reach the portal."""
    account = staff_lab.new_staff(complete_first_login=False)

    login = LoginPage(page)
    login.navigate(staff_lab.admin.origin + "/auth/login")
    login.login(account.email, account.password)
    expect(page).to_have_url(re.compile(r"/auth/change-password"), timeout=30_000)

    page.goto("/tc/dashboard")  # try to skip the step
    expect(page).to_have_url(re.compile(r"/auth/change-password"))


@pytest.mark.xfail(reason="BUG-018: the API serves data to a staff member who never changed the temporary password", strict=False)
def test_temporary_password_is_enforced_by_the_api(staff_lab: StaffLab) -> None:
    """The same rule must hold server-side: with the temporary password only, protected calls are refused."""
    account = staff_lab.new_staff(complete_first_login=False)
    client = ApiClient.login(staff_lab.admin.api, staff_lab.admin.origin, account.email, account.password)

    probe = PROBE_BY_KEY["dashboard"]
    response = client.request(probe.method, staff_lab.url_for(probe))

    assert response.status in (401, 403), (
        f"{probe.key} answered {response.status} to a staff member who has not changed the temporary password"
    )


WORKING_ID_ROUTES = ["staff", "inspectors", "oems", "rtos", "fleet-managers", "challans"]


def test_malformed_record_id_is_a_404_not_a_crash(staff_lab: StaffLab) -> None:
    """A non-numeric id on the working resources gives 404, never a server error."""
    wrong = {}
    for resource in WORKING_ID_ROUTES:
        response = staff_lab.admin.request("GET", f"{API_PREFIX}/{resource}/not-an-id")
        if response.status != 404:
            wrong[resource] = response.status
    assert not wrong, f"GET .../not-an-id did not answer 404: {wrong}"


@pytest.mark.xfail(reason="BUG-019: malformed ids on stops / routes / drivers crash the server (500)", strict=False)
@pytest.mark.parametrize("method, path", [("GET", f"{API_PREFIX}/stops/not-an-id"), ("POST", f"{API_PREFIX}/drivers/not-an-id")])
def test_known_bug_malformed_id_crashes_the_server(staff_lab: StaffLab, method: str, path: str) -> None:
    response = staff_lab.admin.request(method, path, json={} if method != "GET" else None)
    assert response.status == 404, f"{method} {path} -> {response.status}"


@pytest.mark.xfail(reason="BUG-032: a request without 'Accept: application/json' and without a token answers 500", strict=False)
def test_unauthenticated_request_without_a_json_accept_header_is_a_401(staff_lab: StaffLab) -> None:
    """Scripts and curl do not send `Accept: application/json`; they must still get 401, never a crash."""
    wrong = {}
    for path in ("/api/auth/me", f"{API_PREFIX}/oems"):
        response = staff_lab.admin.api.fetch(staff_lab.admin.origin + path, method="GET", max_redirects=0)
        if response.status not in (401, 403):
            wrong[path] = response.status
    assert not wrong, f"Unauthenticated GET without Accept header: {wrong}"
