"""
RTO Inspector panel, through the screen and the API.

The dedicated Inspector account was created through Administration > User Management > Add Inspector and
explicitly assigned to the dedicated RTO (code DL-96, see `rto_credentials`) at creation time. Per
`VLTD_How_It_Works.pdf` chapter 15, an Inspector's job is roadside checks (Verify Fitment), drafting challans and
the RTO's own installation reports - NOT installation approval (that is an RTO Officer action, chapter 6.3).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.role_panels.dashboard import InspectorDashboardPage
from utils.api_client import ApiClient
from utils.role_panel_api import INSPECTOR_FITMENT_VALIDITY

pytestmark = [pytest.mark.inspector_panel]


def test_login_lands_on_the_inspector_dashboard(inspector_page: Page) -> None:
    dash = InspectorDashboardPage(inspector_page).open()
    expect(dash.heading).to_be_visible()


# ── BUG-085 regression: the dashboard misreports the Inspector's own RTO assignment ──

@pytest.mark.xfail(reason="BUG-085: the Inspector Dashboard always shows 0 Assigned RTOs, even when one is assigned", strict=False)
def test_dashboard_shows_the_inspectors_assigned_rto(inspector_page: Page, inspector_api: ApiClient) -> None:
    api_rto_count = len(inspector_api.get("/api/inspector/dashboard?trend_days=7&recent_limit=1").json()["data"]["inspector"]["rto_data"])
    assert api_rto_count >= 1, "the dedicated Inspector is expected to be assigned to at least one RTO"

    dash = InspectorDashboardPage(inspector_page).open()
    assert dash.assigned_rtos_count() == api_rto_count
    expect(dash.no_rto_message).to_have_count(0)


# ── Verify Fitment: a known installation vs. an unknown plate ──────────────────

def test_verify_fitment_reports_a_known_installations_current_state(inspector_api: ApiClient) -> None:
    """DL04CA1028 has a real installation stuck at Health Check (see BUG-080) - Verify Fitment should report that
    state accurately, not claim an active installation that doesn't exist."""
    response = inspector_api.get(f"{INSPECTOR_FITMENT_VALIDITY}?parameter=DL04CA1028")
    assert response.status == 200, response.text()[:300]
    data = response.json()["data"]
    assert data["vehicle"]["vehicle_number"] == "DL04CA1028"
    assert data["installation"]["installation_status"] == "in_progress"
    assert data["installation"]["activation_status"] == "pending"


def test_verify_fitment_reports_not_found_for_an_unknown_plate(inspector_api: ApiClient) -> None:
    response = inspector_api.get(f"{INSPECTOR_FITMENT_VALIDITY}?parameter=ZZ99ZZ9999")
    assert response.status == 404


# ── screens load; no permission error ──────────────────────────────────────────

@pytest.mark.parametrize(
    "path, heading",
    [
        ("/inspector/fitment-validity", "Verify Fitment"),
        ("/inspector/challans/create", "Draft Challan"),
        ("/inspector/challans", "My Challans"),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_inspector_screens_load_without_crashing_or_a_permission_error(inspector_page: Page, path: str, heading: str) -> None:
    inspector_page.goto(path)
    expect(inspector_page.get_by_role("heading", name=heading, level=1)).to_be_visible(timeout=20_000)
    expect(inspector_page.get_by_text("Something went wrong")).to_have_count(0)
    expect(inspector_page.get_by_text(re.compile(r"not authorized|forbidden", re.I))).to_have_count(0)


def test_my_challans_is_empty_and_scoped_to_this_inspector(inspector_page: Page, inspector_api: ApiClient) -> None:
    total = inspector_api.get("/api/inspector/challans?page=1&per_page=1").json()["data"]["total"]
    assert total == 0  # a freshly-created Inspector has drafted nothing yet

    inspector_page.get_by_role("link", name="My Challans").click()
    expect(inspector_page.get_by_text("No challans found.")).to_be_visible(timeout=20_000)
