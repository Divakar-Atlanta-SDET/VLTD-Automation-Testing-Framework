"""
Permit Holder (Fleet Owner) panel - login, dashboard, own-vehicle visibility and the BUG-090 regression.

See `specs/permit-holder-test-plan.md` for the full exploration this is based on.
"""

import pytest
from playwright.sync_api import Page, expect

from utils.api_client import ApiClient
from utils.permit_holder_api import VEHICLE_DETAIL, VEHICLE_LIST

pytestmark = pytest.mark.permit_holder_panel


def test_login_and_dashboard_match_the_account(permit_holder_page: Page, permit_holder_api: ApiClient):
    expect(permit_holder_page).to_have_url(__import__("re").compile(r"/fleet-owner/dashboard"))
    expect(permit_holder_page.get_by_role("heading", name="Fleet Owner Dashboard")).to_be_visible()

    me = permit_holder_api.request("GET", "/api/auth/me").json()["data"]
    assert me["role"]["code"] == "permit_holder"
    assert me["type"] == "fleet_owner"


def test_vehicle_list_and_detail_match_the_api(permit_holder_page: Page, permit_holder_api: ApiClient):
    api_vehicles = permit_holder_api.request("GET", VEHICLE_LIST).json()["data"]["data"]
    assert len(api_vehicles) >= 1, "this permit holder should own at least one vehicle"

    permit_holder_page.goto(permit_holder_page.url.split("/fleet-owner")[0] + "/fleet-owner/vehicles")
    permit_holder_page.wait_for_load_state("networkidle")
    rows = permit_holder_page.locator("table tbody tr")
    expect(rows).to_have_count(len(api_vehicles))

    own_vehicle_id = api_vehicles[0]["id"]
    detail = permit_holder_api.request("GET", VEHICLE_DETAIL.format(vehicle_id=own_vehicle_id))
    assert detail.ok, f"own vehicle detail should be reachable: {detail.status}"
    assert detail.json()["data"]["id"] == own_vehicle_id


@pytest.mark.xfail(reason="BUG-090: permit_holder.staff.* permissions are granted but no Staff page exists anywhere in the Fleet Owner panel", strict=False)
def test_staff_permission_has_no_reachable_page(permit_holder_page: Page, permit_holder_api: ApiClient):
    me = permit_holder_api.request("GET", "/api/auth/me").json()["data"]
    perm_codes = {p["code"] for p in me["permissions"]}
    assert "permit_holder.staff.view" in perm_codes, "precondition: this account should hold the staff.view permission"

    for guess in ("/fleet-owner/staff", "/fleet-owner/users/staff", "/fleet-owner/users", "/fleet-owner/account/staff"):
        permit_holder_page.goto(guess, wait_until="domcontentloaded")
        permit_holder_page.wait_for_timeout(1000)
        assert "/fleet-owner/dashboard" not in permit_holder_page.url, (
            f"expected a real Staff page at {guess}, but it fell back to the Dashboard"
        )
