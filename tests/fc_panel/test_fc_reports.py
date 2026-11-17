"""
Fitment Centre > Reports, through the screen.

13 report pages discovered by nav sweep (`/fc/reports/*`, `/fc/set-history`, `/fc/watch-history`; see
`specs/fitment-centre-test-plan.md`). Most of them depend on real device telemetry, repairs or watchlists this
environment does not have yet (same root cause as BUG-080), so an empty report is the expected state for them, not
a defect - this file smoke-tests that they at least load without crashing or exposing a permission error, and gives
deeper reconciliation only to the one report with real, known data (Installation Report: this FC's 7 real
installations).

BUG-078 status, re-checked 2026-11-05: the Device Model filter on Device Health Report, Device Status &
Connectivity and Installation Report (`GET /api/device-models`) is now FIXED - it answers 200 and the dropdown
populates with real device models, where it answered 403 on 2026-11-04. The Operations-side part of BUG-078
(`/api/transport-commissioner/rtos` / `/oems` on Live Tracking, Geofences, Trip Playback, Alerts) is unchanged and
still 403s - confirmed separately, not retested here (see `test_fc_operations.py`).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.fc_panel.reports import FcDeviceInventoryReportPage, FcInstallationReportPage
from utils.api_client import ApiClient
from utils.fc_panel_api import INSTALLATIONS

pytestmark = [pytest.mark.fc_panel]

REPORT_PAGES = [
    ("/fc/reports/alerts", "Alert Report"),
    ("/fc/reports/alerts/vehicle-trail", "Vehicle Alert Trail"),
    ("/fc/reports/device-health", "Device Health Report"),
    ("/fc/reports/device-packets", "Device Packets"),
    ("/fc/reports/device-status", "Device Status & Connectivity"),
    ("/fc/reports/device-validity", "Device SIM Validity Report"),
    ("/fc/reports/repair-history", "Repair History"),
    ("/fc/reports/user-devices", "Permit Holder Device Report"),
    ("/fc/reports/vehicle-mappings", "Vehicle Mapping Report"),
    ("/fc/set-history", "Alert Set History"),
    ("/fc/watch-history", "Watch History"),
    # /fc/reports/device-inventory and /fc/reports/installation-status are tested separately below
]


@pytest.mark.parametrize("path, heading", REPORT_PAGES, ids=lambda v: v if isinstance(v, str) and v.startswith("/") else "")
def test_the_report_page_loads_without_crashing_or_a_permission_error(fc_page: Page, path: str, heading: str) -> None:
    fc_page.goto(path)
    expect(fc_page.get_by_role("heading", name=heading, level=1)).to_be_visible(timeout=20_000)
    expect(fc_page.get_by_text("Something went wrong")).to_have_count(0)
    expect(fc_page.get_by_text(re.compile(r"not authorized|forbidden", re.I))).to_have_count(0)


# ── BUG-078, re-checked: the Device Model filter is now fixed ─────────────────

@pytest.mark.parametrize("path", ["/fc/reports/device-health", "/fc/reports/device-status", "/fc/reports/installation-status"],
                          ids=lambda p: p.rsplit("/", 1)[1])
def test_the_device_model_filter_now_populates_real_models(fc_page: Page, path: str) -> None:
    """BUG-078 originally found this 403ing on all 3 of these pages (2026-11-04); fixed as of 2026-11-05."""
    fc_page.goto(path)
    with fc_page.expect_response(lambda r: "/api/device-models" in r.url) as response:
        fc_page.get_by_role("combobox", name=re.compile("Device Model", re.I)).click()
    assert response.value.status == 200

    options = [o.strip() for o in fc_page.locator("[role=option]:visible").all_inner_texts()]
    assert len(options) > 1, f"the Device Model filter has no real models to offer: {options}"


# ── Installation Report: the one report with real, known data ────────────────

def test_installation_report_reconciles_with_the_api_once_the_date_range_is_widened(fc_page: Page, fc_api: ApiClient) -> None:
    """Confirmed 2026-11-05: the report defaults to today-only, which excludes the FC's 7 installations (created
    2026-11-04) - not a bug, just a filter default this test must account for."""
    totals = fc_api.get(f"{INSTALLATIONS}?per_page=1&date_from=2026-11-01&date_to=2026-11-05").json()["data"]["meta"]["pagination"]
    by_status = {
        status: fc_api.get(f"{INSTALLATIONS}?per_page=1&installation_status={status}&date_from=2026-11-01&date_to=2026-11-05").json()["data"]["meta"]["pagination"]["total"]
        for status in ("active", "in_progress", "in_repair")
    }

    page = FcInstallationReportPage(fc_page).open()
    page.set_date_range("2026-11-01", "2026-11-05")

    counters = page.counters()
    assert counters["Total Installations"] == totals["total"]
    assert counters["Active"] == by_status["active"]
    assert counters["In Progress"] == by_status["in_progress"]
    assert counters["In Repair"] == by_status["in_repair"]


# ── Defects (expected failures; see bug_report.md) ────────────────────────────

@pytest.mark.xfail(reason="BUG-084: the Device Inventory Report crashes with a 500 on every load, with or without filters", strict=False)
def test_the_device_inventory_report_loads(fc_page: Page) -> None:
    page = FcDeviceInventoryReportPage(fc_page).open()

    expect(page.heading).to_be_visible()
    expect(fc_page.get_by_text("Something went wrong")).to_have_count(0)
