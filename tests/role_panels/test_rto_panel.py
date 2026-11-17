"""
RTO Officer panel, through the screen and the API.

The dedicated RTO (`RTO_USERNAME`, code DL-96) was created fresh this session and has no vehicles, installations
or permit holders under it yet - every list and counter is correctly empty. These tests confirm that empty state
is genuine (matches the API, not a broken/stuck loading state) and that the panel's jurisdiction-scoped screens
load without error, per `VLTD_How_It_Works.pdf` chapter 5 ("RTO Officer: approves installations, handles challans,
watches the district") and chapter 18 (RTO installation reports).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.role_panels.dashboard import RtoDashboardPage
from utils.api_client import ApiClient
from utils.role_panel_api import RTO_PENDING_INSTALLATIONS

pytestmark = [pytest.mark.rto_panel]


def test_login_lands_on_the_rto_dashboard(rto_page: Page) -> None:
    dash = RtoDashboardPage(rto_page).open()
    expect(dash.heading).to_be_visible()


def test_dashboard_counters_match_the_api_for_a_jurisdiction_with_no_data_yet(rto_page: Page, rto_api: ApiClient) -> None:
    """A fresh RTO with nothing under it yet: every tile should read 0, matching the pending-installations API."""
    dash = RtoDashboardPage(rto_page).open()
    assert dash.counter("Total Installations") == 0
    assert dash.counter("Pending Approvals") == 0

    api_pending = rto_api.get(f"{RTO_PENDING_INSTALLATIONS}?per_page=1").json()["meta"]["pagination"]["total"]
    assert api_pending == 0


@pytest.mark.parametrize(
    "path, heading",
    [
        ("/rto/users/permit-holders", "Permit Holder Management"),
        ("/rto/challans", "Challan Work Queue"),
        ("/rto/installation-approvals/pending", "Pending Installation Approvals"),
        ("/rto/installation-approvals/approved", "Approved Installation Report"),
        ("/rto/installation-approvals/rejected", "Rejected Installation Report"),
        ("/rto/reports/device-health", "Device Health Report"),
        ("/rto/reports/device-packets", "Device Packets"),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_rto_screens_load_without_crashing_or_a_permission_error(rto_page: Page, path: str, heading: str) -> None:
    rto_page.goto(path)
    expect(rto_page.get_by_role("heading", name=heading, level=1)).to_be_visible(timeout=20_000)
    expect(rto_page.get_by_text("Something went wrong")).to_have_count(0)
    expect(rto_page.get_by_text(re.compile(r"not authorized|forbidden", re.I))).to_have_count(0)


def test_permit_holders_list_is_view_only_for_rto(rto_page: Page) -> None:
    """Matches the Admin side (UM-06): Permit Holders are created by the Fitment Centre, never by RTO or Admin."""
    rto_page.goto("/rto/users/permit-holders")
    expect(rto_page.get_by_role("heading", name="Permit Holder Management", level=1)).to_be_visible(timeout=20_000)
    expect(rto_page.get_by_role("button", name=re.compile(r"^(Register|Add|Create|New)\b"))).to_have_count(0)
    expect(rto_page.get_by_text("No Permit Holders found.")).to_be_visible()
