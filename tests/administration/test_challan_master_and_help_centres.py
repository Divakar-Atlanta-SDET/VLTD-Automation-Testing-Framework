"""
Challan Master (guide 9.2 / 9.3) and Help Centres (guide 8.4): read-only checks and empty-request validation.

  The automatic "not sending data" challan (silent device, 7 days) needs an offence in the Challan Master.
  Create requests without details are refused and list the required fields.
"""

import pytest

from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api]


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


def test_challan_master_has_an_active_offence_for_silent_devices(admin_api: ApiClient) -> None:
    offences = admin_api.get(f"{API_PREFIX}/challan-masters?per_page=100").json()["data"]["data"]

    silent = [o for o in offences if "not_sending_data" in f"{o['code']} {o['name']}".lower().replace(" ", "_")]
    assert silent, f"No 'not sending data' offence in the Challan Master: {[o['code'] for o in offences]}"
    assert any(o["is_active"] for o in silent)


@pytest.mark.parametrize(
    "path, required",
    [
        (f"{API_PREFIX}/challan-masters", {"code", "name", "penalty_amount"}),
        ("/api/tracking/help-centres", {"name", "type", "category", "city_id", "latitude", "longitude"}),
    ],
    ids=["challan-master", "help-centre"],
)
def test_create_without_details_lists_every_required_field(admin_api: ApiClient, path: str, required: set) -> None:
    response = admin_api.post(path, json={})

    assert response.status == 422, response.text()[:200]
    assert required <= set(response.json()["errors"])
