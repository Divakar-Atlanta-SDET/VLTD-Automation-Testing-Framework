"""
OEM dashboard and reports (guide 6.1 and chapter 18).

  The dashboard shows the OEM's stock by state (Available / Allocated / Installed / Faulty); reports show only the OEM's
  own devices and can be exported. Counters must equal the rows they summarise.

Reports that need INSTALLED devices (status, health, SIM validity, installed devices, alerts, expired SIM) are not
automated: the OEM account has none, and an always-skipped test would only add noise. See the plan, section 7.

OEM-F1, OEM-F2 of specs/oem-panel-test-plan.md.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.dashboard import OemDashboardPage
from utils.oem_panel_api import DEVICES

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

STOCK_STATES = ("available_devices", "allocated_devices", "installed_devices", "faulty_devices")


# ── OEM-F1: dashboard stock counters ──────────────────────────────────────────

def test_dashboard_counters_add_up_and_equal_the_device_list(device_lab) -> None:
    device_lab.register()

    totals = device_lab.totals()

    assert totals["total_devices"] == sum(totals[state] for state in STOCK_STATES)
    assert totals["total_devices"] == device_lab.devices_total()
    for key, status in (("available_devices", "available"), ("allocated_devices", "allocated")):
        listed = device_lab.oem.get(f"{DEVICES}?per_page=1&inventory_status={status}").json()["meta"]["pagination"]["total"]
        assert totals[key] == listed, key


def test_dashboard_page_shows_the_stock_counters(device_lab, oem_page: Page) -> None:
    device_lab.register()
    totals = device_lab.totals()

    OemDashboardPage(oem_page).open().expect_counters(
        Total_Devices=totals["total_devices"], Available_Devices=totals["available_devices"],
        Allocated_Devices=totals["allocated_devices"], Installed_Devices=totals["installed_devices"],
    )


def test_device_inventory_report_lists_the_registered_device(device_lab) -> None:
    device = device_lab.register()

    rows = device_lab.oem.get(f"/api/reports/device-inventory?per_page=100&search={device['imei']}").json()["data"]

    match = [r for r in rows if device["imei"] in str(r)]
    assert len(match) == 1, f"The registered device appears {len(match)} times in the inventory report"


# ── OEM-F2: export ────────────────────────────────────────────────────────────

def test_device_inventory_report_exports_a_file(device_lab, oem_page: Page) -> None:
    device_lab.register()  # the export button is disabled while the report has no rows
    oem_page.goto("/oem/reports/device-inventory")
    export = oem_page.get_by_role("button", name="Export CSV", exact=True)
    expect(export).to_be_enabled(timeout=20_000)

    with oem_page.expect_download() as download:
        export.click()

    saved = download.value
    assert saved.suggested_filename.lower().endswith((".csv", ".xlsx")), saved.suggested_filename
    with open(saved.path(), "rb") as handle:
        assert len(handle.read()) > 20, "The exported file is empty"
