"""
OEM panel - authorization, isolation and page health (guide chapters 3, 4, 5 and section 14.4).

  An OEM sees and changes only its own data, cannot use State Admin features, needs a login for everything, and
  must change the temporary password the State Admin set. Every page of the OEM menu has to open without failed calls.

OEM-A1 .. OEM-A6 of specs/oem-panel-test-plan.md. Known defects are separate `xfail` tests (see bug_report.md).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from pages.oem_panel.misc import OemDeviceModelsPage
from utils.api_client import API_PREFIX, ApiClient
from utils.oem_panel_api import DEVICES, FITMENT_CENTRES, create_oem_account
from utils.page_health import load_problems, menu_routes

pytestmark = [pytest.mark.oem_panel]


# ── OEM-A1: another OEM's data is invisible ───────────────────────────────────

@pytest.fixture(scope="module")
def other_oems_devices(admin_api: ApiClient, oem_api: ApiClient) -> list[int]:
    """Ids of installed devices that do not belong to the OEM under test (read from the State Admin's report)."""
    rows = admin_api.get("/api/tracking/devices/status-report?per_page=100").json()["data"]
    mine = {d["id"] for d in oem_api.get(f"{DEVICES}?per_page=100").json()["data"]}
    ids = [row["device_id"] for row in rows if row["device_id"] not in mine]
    if not ids:
        pytest.skip("No device of another OEM exists to test isolation with")
    return ids[:3]


def test_oem_cannot_read_a_device_of_another_oem(oem_api: ApiClient, other_oems_devices: list[int]) -> None:
    leaked = {i: oem_api.get(f"{DEVICES}/{i}").status for i in other_oems_devices}

    assert set(leaked.values()) == {404}, f"The OEM could reach another OEM's devices: {leaked}"


def test_oem_cannot_read_a_fitment_centre_of_another_oem(admin_api: ApiClient, oem_api: ApiClient) -> None:
    mine = {f["id"] for f in oem_api.get(f"{FITMENT_CENTRES}?per_page=100").json()["data"]}  # the first page alone is 10 centres
    others = [f["id"] for f in admin_api.get(f"{FITMENT_CENTRES}?per_page=100").json()["data"] if f["id"] not in mine]
    if not others:
        pytest.skip("No fitment centre of another OEM exists")

    leaked = {i: oem_api.get(f"{FITMENT_CENTRES}/{i}").status for i in others}

    assert set(leaked.values()) == {404}, leaked


@pytest.mark.xdist_group("oem-devices")
def test_oem_lists_contain_only_its_own_records(oem_api: ApiClient, lab) -> None:
    lab.register()  # make sure the device list is not empty
    try:
        oem_id = lab.masters.oem_id
        devices = oem_api.get(f"{DEVICES}?per_page=100").json()["data"]
        assert devices and all(d["oem_id"] == oem_id for d in devices)
        for path in ("/api/device-allocations", FITMENT_CENTRES, "/api/device-command-templates"):
            rows = oem_api.get(f"{path}?per_page=100").json()["data"]
            assert all(r.get("oem_id", oem_id) == oem_id for r in rows), path
    finally:
        lab.release_devices()


# ── OEM-A2: State Admin features are closed to the OEM ────────────────────────

STATE_ADMIN_ONLY = [
    f"{API_PREFIX}/announcements",
    f"{API_PREFIX}/ownership-transfer/report",
    f"{API_PREFIX}/account-merge/report",
    f"{API_PREFIX}/challan-masters",
    f"{API_PREFIX}/stops",
    f"{API_PREFIX}/routes",
    f"{API_PREFIX}/fleet-managers",
    f"{API_PREFIX}/challans",
    f"{API_PREFIX}/drivers",
    "/api/installation/untag-search?registration_number=DL01AA0001",
    "/api/tracking/help-centres",
]


@pytest.mark.parametrize("path", STATE_ADMIN_ONLY, ids=lambda p: p.split("/")[-1].split("?")[0])
def test_oem_is_refused_state_admin_features(oem_api: ApiClient, path: str) -> None:
    assert oem_api.get(path).status == 403


# ── OEM-A3: a login is needed for everything ──────────────────────────────────

OEM_ENDPOINTS = [
    DEVICES, "/api/device-allocations", "/api/device-repairs", "/api/device-command-templates",
    FITMENT_CENTRES, "/api/dashboard/oem/device-inventory", "/api/devices/bulk-upload/sample",
]


@pytest.mark.parametrize("token", [None, "garbage.token.value"], ids=["no-token", "malformed-token"])
@pytest.mark.parametrize("path", OEM_ENDPOINTS, ids=lambda p: p.split("/api/")[1].replace("/", "_"))
def test_oem_endpoints_require_a_valid_login(oem_api: ApiClient, path: str, token) -> None:
    assert oem_api.request("GET", path, token=token).status == 401


# ── OEM-A4: every menu page opens cleanly ─────────────────────────────────────

# Pages whose requests fail for an OEM (BUG-040: State Admin endpoints; BUG-039: staff list). Tested separately.
KNOWN_BAD_PAGES = {
    "/oem/alerts": "BUG-040", "/oem/geofences": "BUG-040", "/oem/live-tracking": "BUG-040", "/oem/trip-playback": "BUG-040",
    "/oem/users/staff": "BUG-039",
}


def test_every_oem_menu_page_loads_cleanly(oem_page: Page) -> None:
    routes = [r for r in menu_routes(oem_page, "/oem/") if r not in KNOWN_BAD_PAGES]
    assert len(routes) >= 20, f"Only {len(routes)} OEM menu pages found"

    broken = {route: problems[:3] for route in routes if (problems := load_problems(oem_page, route))}

    assert not broken, f"Pages that load with failures: {broken}"


@pytest.mark.xfail(
    reason="BUG-040: the monitoring pages call State Admin endpoints (/api/transport-commissioner/oems, /rtos) "
    "which answer 403 for an OEM",
    strict=False,
)
@pytest.mark.parametrize("route", [r for r, ref in KNOWN_BAD_PAGES.items() if ref == "BUG-040"])
def test_monitoring_pages_do_not_call_state_admin_endpoints(oem_page: Page, route: str) -> None:
    assert not load_problems(oem_page, route)


# ── OEM-A5: master data is view-only (guide 14.4) ─────────────────────────────

@pytest.mark.xfail(reason="BUG-038: the OEM sees 'Add Model' although it may only view device models", strict=False)
def test_oem_is_not_offered_to_add_a_device_model(oem_page: Page) -> None:
    models = OemDeviceModelsPage(oem_page).open()

    expect(models.main.get_by_role("row")).not_to_have_count(0)  # the list itself is visible
    expect(models.add_model_button).to_have_count(0)


# ── OEM-A6: the temporary password must be changed (guide chapter 4) ──────────

def test_new_oem_must_change_the_temporary_password(page: Page, base_url: str, admin_api: ApiClient) -> None:
    account = create_oem_account(admin_api)
    login = LoginPage(page)
    login.navigate(base_url)
    login.login(account["email"], account["password"])
    expect(page).to_have_url(re.compile(r"/auth/change-password"), timeout=30_000)

    page.goto("/oem/dashboard")  # try to skip the step
    expect(page).to_have_url(re.compile(r"/auth/change-password"))
