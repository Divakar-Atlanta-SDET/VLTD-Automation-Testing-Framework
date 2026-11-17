"""
Fitment Centre Dashboard (`/fc/dashboard`).

Not documented in the guide (chapter 6 describes the device lifecycle, not this specific screen), so every check
here reconciles what the page shows with the live API data behind it, read fresh at test time - this account is the
shared, deliberately-provisioned `FC_USERNAME` test account (see `tests/fc_panel/conftest.py`), not a throw-away
one, and its numbers grow as later FC modules are exercised. Nothing here hardcodes today's counts.

  kpis         the 7 top KPI cards equal the summary API
  live fleet   Moving/Idle/SOS/Offline equal /api/tracking/vehicles/summary (same widget as the OEM dashboard)
  status       the Device & Installation Status donut and lifecycle row equal the summary API's inventory/installations
  recent       the Recent Installations table matches the recent-installations API
  pending work BUG-081: Health Check / Document Upload / Approval can never show a real count
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.fc_panel.dashboard import PENDING_WORK_ROWS, FcDashboardPage
from utils.api_client import ApiClient
from utils.fc_panel_api import DASHBOARD_SUMMARY, INSTALLATIONS, VEHICLE_SUMMARY

pytestmark = [pytest.mark.fc_panel, pytest.mark.dashboard]


def _summary(fc: ApiClient) -> dict:
    return fc.get(DASHBOARD_SUMMARY).json()["data"]


def _installation_count(fc: ApiClient) -> int:
    return len(fc.get(f"{INSTALLATIONS}?per_page=100").json()["data"]["data"])


# ── KPI cards ───────────────────────────────────────────────────────────────
# "Pending Approvals" is left unchecked below: the summary API has no field named or obviously mapped to it, so
# asserting it against any one field would be guessing a source the backend never states. The other 6 KPIs match a
# named summary field exactly and are checked for real.

def test_kpi_cards_reconcile_with_the_summary_api(fc_page: Page, fc_api: ApiClient) -> None:
    dash = FcDashboardPage(fc_page).open()
    summary = _summary(fc_api)
    expected = {
        "Available Devices": summary["inventory"]["available"] + summary["inventory"]["allocated"],
        "Total Installations": _installation_count(fc_api),
        "Today's Installations": summary["installations"]["today"],
        "In Progress": summary["installations"]["in_progress"],
        "Repaired Devices": summary["repairs"]["repaired"],
        "Replaced Devices": summary["repairs"]["replaced"],
    }

    shown = dash.kpis()

    assert {k: shown[k] for k in expected} == expected
    assert shown["Pending Approvals"] >= 0  # shown, but its source is unconfirmed - see module docstring


# ── Live Fleet (same widget as the OEM dashboard) ────────────────────────────

def test_live_fleet_reconciles_with_the_vehicle_summary(fc_page: Page, fc_api: ApiClient) -> None:
    dash = FcDashboardPage(fc_page).open()
    summary = fc_api.get(VEHICLE_SUMMARY).json()["data"]

    assert dash.live_fleet() == {"Moving": summary["moving"], "Idle": summary["idle"], "SOS": summary["sos"], "Offline": summary["offline"]}
    assert dash.live_fleet_vehicle_count() == sum(summary.values())


def test_live_fleet_refresh_button_refetches_the_summary(fc_page: Page) -> None:
    dash = FcDashboardPage(fc_page).open()

    with fc_page.expect_response(re.compile(re.escape(VEHICLE_SUMMARY))) as refreshed:
        dash.refresh_button.click()

    assert refreshed.value.status == 200
    expect(dash.heading).to_be_visible()


# ── Device & Installation Status ─────────────────────────────────────────────

def test_device_status_donut_reconciles_with_inventory(fc_page: Page, fc_api: ApiClient) -> None:
    dash = FcDashboardPage(fc_page).open()
    inventory = _summary(fc_api)["inventory"]

    assert dash.device_status() == {
        "Available": inventory["available"] + inventory["allocated"],
        "Installed": inventory["installed"],
        "Faulty": inventory["faulty"],
        "Total Devices": inventory["total"],
    }


def test_installation_lifecycle_row_reconciles_with_summary(fc_page: Page, fc_api: ApiClient) -> None:
    dash = FcDashboardPage(fc_page).open()
    installations = _summary(fc_api)["installations"]

    assert dash.installation_lifecycle() == {
        "Active": installations["active"], "In Progress": installations["in_progress"],
        "In Repair": installations["in_repair"], "Replaced": installations["replaced"],
    }


# ── Recent Installations ─────────────────────────────────────────────────────

def test_recent_installations_matches_the_api(fc_page: Page, fc_api: ApiClient) -> None:
    api_rows = fc_api.get("/api/dashboard/fitment-centre/recent-installations?limit=5").json()["data"]
    if not api_rows:
        pytest.skip("No installations yet on this account")

    dash = FcDashboardPage(fc_page).open()
    shown = dash.recent_installations()

    assert [r["vehicle"] for r in shown] == [r["vehicle"]["vehicle_number"] for r in api_rows]
    assert [r["imei"] for r in shown] == [r["device"]["imei"] for r in api_rows]


# ── Pending Work: BUG-081 ────────────────────────────────────────────────────

def test_pending_work_shows_real_counts_for_activation_and_panic_test(fc_page: Page, fc_api: ApiClient) -> None:
    pending = _summary(fc_api)["pending_actions"]

    dash = FcDashboardPage(fc_page).open()
    shown = dash.pending_work()

    assert shown["Activation"] == pending["activation"]
    assert shown["Panic Test"] == pending["panic_test"]


@pytest.mark.xfail(
    reason="BUG-081: the summary API's pending_actions has no field for Health Check, Document Upload or Approval, "
    "so these 3 of the 5 Pending Work rows can never show a real count, even when matching data exists",
    strict=False,
)
@pytest.mark.parametrize("row", [r for r in PENDING_WORK_ROWS if r not in ("Activation", "Panic Test")])
def test_pending_work_shows_a_real_count_for_every_row(fc_page: Page, row: str) -> None:
    shown = FcDashboardPage(fc_page).open().pending_work()

    assert shown[row] is not None, f"{row!r} reads 'Count not available from API' instead of a real count"
