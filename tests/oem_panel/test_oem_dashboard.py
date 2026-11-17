"""
OEM Dashboard (`/oem/dashboard`).

The guide describes the stock states an OEM sees (Available / Allocated / Installed / Faulty, chapter 6.1) and the
announcements that the State Admin publishes to OEMs (19.2); the rest of the page (Live Fleet, trend, tables, report
links) is not described, so those checks reconcile what the page shows with the data behind it and make no claim about
undocumented wording or layout.

  data        every figure of the page equals the API data it summarises, after real stock changes
  states      empty account, null values, server error, slow request
  navigation  the View All / View Report links
  access      other roles and anonymous callers are refused
  notices     announcements for OEMs appear, others do not

Stock changes use `device_lab` (everything is removed afterwards). Tests that change stock run on one worker.
"""

import re
import time
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.dashboard import EMPTY_MESSAGES, PERIOD_UNIT, PERIODS, OemDashboardPage
from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.oem_dashboard_mocks import (
    ALLOCATION_SUMMARY, FITMENT_SUMMARY, INVENTORY, TICKETS, VEHICLE_SUMMARY,
    hold_requests, mock_empty_account, mock_json,
)

pytestmark = [pytest.mark.oem_panel, pytest.mark.dashboard]

STOCK = pytest.mark.xdist_group("oem-devices")
BROKEN_TEXT = re.compile(r"\b(NaN|undefined|null|\[object Object\])\b")


def _fitment_summary(oem: ApiClient) -> list[dict]:
    return oem.get("/api/dashboard/oem/fitment-summary").json()["data"]


# ── data: the page equals the API after real stock changes ────────────────────

@STOCK
def test_every_figure_follows_registration_allocation_and_rollback(device_lab, oem_page: Page, active_fc: dict) -> None:
    allocated, spare = device_lab.register(), device_lab.register()
    allocation_id = device_lab.allocate(active_fc["id"], allocated).json()["data"]["id"]

    def assert_page_equals_api() -> None:
        totals = device_lab.totals()
        dash = OemDashboardPage(oem_page)
        dash.expect_kpis(
            total=totals["total_devices"], available=totals["available_devices"], allocated=totals["allocated_devices"],
            installed=totals["installed_devices"], faulty=totals["faulty_devices"],
        )
        # Device Inventory donut and legend: available + allocated devices
        assert dash.inventory_chart() == {
            "Inventory": totals["available_devices"] + totals["allocated_devices"],
            "Available": totals["available_devices"], "Allocated": totals["allocated_devices"],
        }
        # Allocation Overview: devices currently allocated
        assert dash.overview_allocated_devices() == device_lab.allocation_summary()["allocated_devices"]
        # Fitment Centre Allocations: one row per centre, with its own numbers
        expected = {e["fitment_centre"]["business_name"]: e for e in _fitment_summary(device_lab.oem)}
        shown = {row["name"]: row for row in dash.fitment_centre_rows()}
        assert set(shown) == set(expected)
        for name, row in shown.items():
            assert (row["allocations"], row["devices"], row["active"]) == (
                expected[name]["total_allocations"], expected[name]["allocated_devices"], expected[name]["active_allocations"],
            ), name

    OemDashboardPage(oem_page).open()
    assert_page_equals_api()
    assert device_lab.totals()["allocated_devices"] == 1 and device_lab.inventory_status(spare) == "available"

    assert device_lab.rollback(allocation_id, allocated).status == 200  # stock goes back: the page must follow
    oem_page.reload()
    OemDashboardPage(oem_page).wait_loaded()
    assert_page_equals_api()
    assert device_lab.totals()["allocated_devices"] == 0


@STOCK
def test_recent_devices_lists_the_five_newest_first(device_lab, oem_page: Page) -> None:
    devices = []
    for _ in range(6):
        devices.append(device_lab.register())
        time.sleep(1.1)  # created_at has a resolution of one second; spacing the devices keeps "newest first" unambiguous

    shown = OemDashboardPage(oem_page).open().recent_devices()

    assert [d["imei"] for d in shown] == [d["imei"] for d in reversed(devices)][:5]
    for row, device in zip(shown, reversed(devices)):
        assert (row["serial"], row["model"], row["firmware"], row["status"]) == (
            device["serial_number"], device_lab.model["model_name"], device_lab.firmware["version"], "Active",
        )


@pytest.mark.xfail(
    reason="BUG-044: the dashboard's Device Details widget shows '-' in the SIM column for every device, "
    "although the Device Details page and the API give the SIM module",
    strict=False,
)
@STOCK
def test_recent_devices_show_the_sim_module(device_lab, oem_page: Page) -> None:
    device = device_lab.register()

    row = next(d for d in OemDashboardPage(oem_page).open().recent_devices() if d["imei"] == device["imei"])

    assert row["sim"] == device_lab.sim["module_name"]


@STOCK
@pytest.mark.parametrize("period", PERIODS)
def test_allocation_trend_counts_new_allocations_in_every_period(device_lab, oem_page: Page, active_fc: dict, period: str) -> None:
    dash = OemDashboardPage(oem_page).open()
    dash.select_period(period)
    before = dash.trend()

    device_lab.allocate(active_fc["id"], device_lab.register(), device_lab.register())
    oem_page.reload()
    dash.wait_loaded()
    dash.select_period(period)
    after = dash.trend()

    assert after["total"] == before["total"] + 2
    assert (after["period"], after["peak_unit"]) == (period, PERIOD_UNIT[period])  # the figures are labelled for the chosen period
    assert 0 < after["average"] <= after["total"] and after["peak"] >= 2


# ── Live Fleet ────────────────────────────────────────────────────────────────

def test_live_fleet_equals_the_vehicle_summary_and_refreshes_on_request(oem_page: Page, oem_api: ApiClient) -> None:
    dash = OemDashboardPage(oem_page).open()
    summary = oem_api.get("/api/tracking/vehicles/summary").json()["data"]

    assert dash.live_fleet() == {"Moving": summary["moving"], "Idle": summary["idle"], "SOS": summary["sos"], "Offline": summary["offline"]}
    assert dash.live_fleet_vehicle_count() == sum(summary.values())

    with oem_page.expect_response(re.compile(r"/api/tracking/vehicles/summary")) as refreshed:
        dash.refresh_button.click()
    assert refreshed.value.status == 200
    expect(dash.heading).to_be_visible()


def test_live_fleet_refreshes_itself_every_five_minutes(oem_page: Page) -> None:
    oem_page.clock.install()
    dash = OemDashboardPage(oem_page).open()
    requests: list[str] = []
    oem_page.on("request", lambda r: requests.append(r.url) if "/api/tracking/vehicles/summary" in r.url else None)

    oem_page.clock.run_for("04:30")
    assert not requests, "Live Fleet refreshed before 5 minutes had passed"
    oem_page.clock.run_for("00:45")

    expect(dash.heading).to_be_visible()
    assert requests, "Live Fleet did not refresh itself after 5 minutes"


# ── states: empty, null, error, slow ──────────────────────────────────────────

def test_empty_account_shows_zeros_and_an_empty_message_in_every_section(oem_page: Page) -> None:
    mock_empty_account(oem_page)

    dash = OemDashboardPage(oem_page).open()

    assert set(dash.kpis().values()) == {0}
    assert dash.live_fleet() == {"Moving": 0, "Idle": 0, "SOS": 0, "Offline": 0} and dash.live_fleet_vehicle_count() == 0
    assert dash.inventory_chart() == {"Inventory": 0, "Available": 0, "Allocated": 0}
    for section in EMPTY_MESSAGES:
        dash.expect_empty_state(section)
    assert not BROKEN_TEXT.search(dash.main.inner_text())


def test_null_values_are_shown_as_zero_not_as_broken_text(oem_page: Page) -> None:
    mock_empty_account(oem_page)
    mock_json(oem_page, INVENTORY, {"success": True, "data": dict.fromkeys(
        ("total_devices", "available_devices", "allocated_devices", "installed_devices", "faulty_devices"))})
    mock_json(oem_page, ALLOCATION_SUMMARY, {"success": True, "data": dict.fromkeys(
        ("total_allocations", "active_allocations", "allocated_devices", "returned_allocations"))})

    dash = OemDashboardPage(oem_page).open()

    assert set(dash.kpis().values()) == {0}
    assert not BROKEN_TEXT.search(dash.main.inner_text())


def test_a_server_error_is_reported_and_the_page_stays_usable(oem_page: Page) -> None:
    mock_empty_account(oem_page)
    for pattern in (INVENTORY, ALLOCATION_SUMMARY, FITMENT_SUMMARY):
        mock_json(oem_page, pattern, {"success": False, "message": "Something went wrong."}, status=500)

    dash = OemDashboardPage(oem_page).open()

    expect(dash.main).to_contain_text("Something went wrong.")
    oem_page.get_by_role("link", name="Repair").click()
    expect(oem_page).to_have_url(re.compile(r"/oem/repairs"))


def test_kpi_cards_show_no_number_while_their_data_is_loading(oem_page: Page) -> None:
    """A pending request must not be displayed as a real 0 (the State Admin dashboard does this: BUG-005)."""
    mock_empty_account(oem_page)
    held = hold_requests(oem_page, INVENTORY)

    oem_page.goto(OemDashboardPage.PATH)
    dash = OemDashboardPage(oem_page)
    expect(dash.main).to_contain_text("Devices currently represented as allocated")  # the rest of the page has loaded
    assert held, "The inventory request was never sent"

    expect(dash.main).not_to_contain_text(re.compile(r"(Total|Available|Allocated|Installed|Faulty) Devices\s*\d"))
    held[0].continue_()
    dash.wait_loaded()


# ── navigation ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "section, button, path",
    [
        ("Device Details", "View All", "/oem/devices"),
        ("Fitment Centre Allocations", "View All", "/oem/device-allocations"),
        ("Recent Repairs", "View All", "/oem/repairs"),
        ("Raised Tickets", "View Report", "/oem/audit-reports/ticket-performance"),
    ],
    ids=["devices", "allocations", "repairs", "ticket-report"],
)
def test_section_links_open_their_page(oem_page: Page, section: str, button: str, path: str) -> None:
    dash = OemDashboardPage(oem_page).open()

    dash.section_button(section, button).click()

    expect(oem_page).to_have_url(re.compile(rf"{re.escape(path)}$"))
    expect(oem_page.get_by_role("heading", level=1).first).to_be_visible()


# ── access ────────────────────────────────────────────────────────────────────

DASHBOARD_ENDPOINTS = [
    "/api/dashboard/oem/device-inventory", "/api/dashboard/oem/allocation-summary", "/api/dashboard/oem/fitment-summary",
]


@pytest.mark.parametrize("path", DASHBOARD_ENDPOINTS, ids=lambda p: p.rsplit("/", 1)[1])
def test_dashboard_data_is_refused_to_anonymous_callers_and_other_roles(oem_api: ApiClient, admin_api: ApiClient, path: str) -> None:
    assert oem_api.request("GET", path, token=None).status == 401
    assert oem_api.request("GET", path, token="garbage.token.value").status == 401
    assert oem_api.request("GET", path, token=admin_api.token).status == 403  # the State Admin is not an OEM


# ── notices (guide 19.2) ──────────────────────────────────────────────────────

@pytest.fixture
def announce(admin_api: ApiClient):
    """announce(audience, starts_in, ends_in) -> subject. The State Admin publishes it; it is deleted afterwards."""
    created: list[int] = []

    def _announce(audience: str, starts_in: timedelta, ends_in: timedelta) -> str:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        subject = f"AUTO dashboard notice {data.unique_suffix()}"
        response = admin_api.post(f"{API_PREFIX}/announcements", json={
            "subject": subject, "content": "Created by the OEM dashboard tests", "priority": "warning",
            "recipient_types": [audience], "starts_at": (now + starts_in).isoformat(), "ends_at": (now + ends_in).isoformat(),
        })
        assert response.status == 201, response.text()[:300]
        listed = admin_api.get(f"{API_PREFIX}/announcements?per_page=100&search={subject}").json()["data"]
        created.extend(a["id"] for a in listed if a["subject"] == subject)
        return subject

    yield _announce
    for announcement_id in created:
        admin_api.delete(f"{API_PREFIX}/announcements/{announcement_id}")


def test_a_notice_for_oems_is_shown_on_the_dashboard(announce, oem_page: Page) -> None:
    subject = announce("oem_admin", -timedelta(minutes=2), timedelta(minutes=20))

    dash = OemDashboardPage(oem_page).open()

    expect(dash.announcement).to_be_visible()
    expect(dash.main).to_contain_text(subject)
    expect(dash.main).to_contain_text("Created by the OEM dashboard tests")


@pytest.mark.parametrize(
    "audience, starts_in, ends_in",
    [
        ("rto_inspector", -timedelta(minutes=2), timedelta(minutes=20)),
        ("oem_admin", timedelta(days=1), timedelta(days=2)),
        ("oem_admin", -timedelta(days=2), -timedelta(days=1)),
    ],
    ids=["other-audience", "not-started-yet", "already-expired"],
)
def test_a_notice_that_is_not_for_oems_now_is_not_shown(announce, oem_page: Page, audience: str, starts_in, ends_in) -> None:
    subject = announce(audience, starts_in, ends_in)

    dash = OemDashboardPage(oem_page).open()

    expect(dash.main).not_to_contain_text(subject)
