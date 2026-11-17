"""
Report exports (guide section 12: "Most can be exported") and the read-only vehicle look-ups behind ownership
transfer and device untag (guide 6.4 / 7.1).

Nothing here changes data: exports only download, and the look-ups stop before the Transfer / Untag buttons.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api]

EXPORTABLE_REPORTS = [
    pytest.param("/tc/reports/alerts", id="alert-report"),
    pytest.param("/tc/reports/device-health", id="device-health"),
    pytest.param("/tc/reports/device-status", id="device-status"),
    pytest.param("/tc/reports/vehicle-activity", id="fleet-activity"),
    pytest.param("/tc/reports/account-merges", id="account-merges"),
    pytest.param("/tc/reports/ownership-transfers", id="ownership-transfers"),
]


@pytest.mark.parametrize("route", EXPORTABLE_REPORTS)
def test_report_export_downloads_a_spreadsheet(admin_page: Page, route: str) -> None:
    admin_page.goto(route)
    export = admin_page.get_by_role("button", name="Export Excel")
    expect(export).to_be_visible()
    admin_page.wait_for_load_state("networkidle")
    if export.is_disabled():  # the button is disabled while there is nothing to export
        pytest.skip(f"{route} has no rows to export")

    with admin_page.expect_download() as download:
        export.click()

    saved = download.value
    assert saved.suggested_filename.lower().endswith((".xlsx", ".xls", ".csv")), saved.suggested_filename
    with open(saved.path(), "rb") as handle:
        content = handle.read()
    assert len(content) > 100, "The exported file is empty"
    if saved.suggested_filename.lower().endswith(".xlsx"):
        assert content[:2] == b"PK", "An .xlsx export must be a zip container"


# ── Vehicle look-ups ──────────────────────────────────────────────────────────

LOOKUPS = [
    pytest.param("/tc/operations/vehicle-ownership-transfer", "Registration number or vehicle ID", "Current Owner", "Upload Certificate", id="ownership-transfer"),
    pytest.param("/tc/operations/vehicle-device-untag", "Enter registration number", "Vehicle Owner", "Untag Device", id="device-untag"),
]


@pytest.fixture(scope="module")
def installed_vehicle(playwright, base_url: str, admin_credentials: dict) -> dict:
    """A vehicle with an ACTIVE installation (an installation still in progress is not found by the look-ups)."""
    request = playwright.request.new_context()
    admin = ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    found = None
    for vehicle in admin.get("/api/tracking/vehicles?per_page=100").json()["data"]:
        lookup = admin.get(f"/api/installation/untag-search?registration_number={vehicle['vehicle_number']}")
        if lookup.status == 200:
            found = {"vehicle_number": vehicle["vehicle_number"], "imei": lookup.json()["data"]["device"]["imei"]}
            break
    request.dispose()
    if not found:
        pytest.skip("No vehicle with an active device installation")
    return found


@pytest.mark.parametrize("route, box, owner_label, action", LOOKUPS)
def test_vehicle_lookup_shows_the_current_owner_and_device(
    admin_page: Page, installed_vehicle: dict, route: str, box: str, owner_label: str, action: str
) -> None:
    admin_page.goto(route)
    admin_page.get_by_placeholder(box).fill(installed_vehicle["vehicle_number"])
    admin_page.get_by_role("button", name="Search").click()

    main = admin_page.locator("main")
    expect(main.get_by_text(installed_vehicle["vehicle_number"]).first).to_be_visible()
    expect(main.get_by_text(installed_vehicle["imei"]).first).to_be_visible()
    expect(main.get_by_text(owner_label, exact=True).first).to_be_visible()
    expect(main.get_by_role("button", name=action)).to_be_visible()


@pytest.mark.parametrize("route, box, owner_label, action", LOOKUPS)
def test_unknown_vehicle_offers_no_transfer_or_untag(admin_page: Page, route: str, box: str, owner_label: str, action: str) -> None:
    admin_page.goto(route)
    admin_page.get_by_placeholder(box).fill("ZZ99ZZ9999")
    with admin_page.expect_response(re.compile(r"(ownership-transfer/vehicle|untag-search)\?registration_number=ZZ99ZZ9999")) as search:
        admin_page.get_by_role("button", name="Search").click()

    assert search.value.status == 422
    expect(admin_page.locator("main").get_by_text(owner_label, exact=True)).to_have_count(0)
    expect(admin_page.locator("main").get_by_role("button", name=action)).to_have_count(0)


UNTAG_NO_MESSAGE = pytest.mark.xfail(reason="BUG-037: Vehicle Device Untag shows no message for an unknown vehicle", strict=False)


@pytest.mark.parametrize(
    "route, box, owner_label, action",
    [LOOKUPS[0], pytest.param(*LOOKUPS[1].values, id="device-untag", marks=UNTAG_NO_MESSAGE)],
)
def test_unknown_vehicle_explains_that_nothing_was_found(admin_page: Page, route: str, box: str, owner_label: str, action: str) -> None:
    admin_page.goto(route)
    admin_page.get_by_placeholder(box).fill("ZZ99ZZ9999")
    admin_page.get_by_role("button", name="Search").click()

    expect(admin_page.get_by_text(re.compile(r"not found|no vehicle|invalid|could not|does not exist", re.I)).first).to_be_visible(timeout=3_000)


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.mark.parametrize(
    "method, path",
    [("POST", f"{API_PREFIX}/ownership-transfer"), ("POST", "/api/installation/0/untag")],
    ids=["transfer-without-details", "untag-unknown-installation"],
)
def test_transfer_and_untag_refuse_incomplete_requests(admin_api: ApiClient, method: str, path: str) -> None:
    """Empty requests are refused by validation; nothing is transferred or untagged."""
    response = admin_api.request(method, path, json={})

    assert response.status in (404, 422), f"{method} {path} -> {response.status}: {response.text()[:200]}"
