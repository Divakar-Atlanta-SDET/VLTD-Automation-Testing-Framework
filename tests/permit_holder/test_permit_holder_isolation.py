"""
Permit Holder ownership / data-isolation boundary - the highest-priority area in
`specs/permit-holder-test-plan.md`. Every check here hits the live API directly with a manipulated
`vehicle_id` that genuinely belongs to a different owner, not just a UI search.
"""

import pytest

from utils.api_client import ApiClient
from utils.permit_holder_api import VEHICLE_DETAIL, WATCHLIST_DETAIL, WATCHLIST_ITEM, WATCHLIST_ITEMS, WATCHLISTS

pytestmark = pytest.mark.permit_holder_panel


def test_another_owners_vehicle_detail_is_refused(permit_holder_api: ApiClient, other_owner_vehicle_id: int):
    resp = permit_holder_api.request("GET", VEHICLE_DETAIL.format(vehicle_id=other_owner_vehicle_id))
    assert resp.status == 403, f"expected 403 for a vehicle outside this permit holder's fleet, got {resp.status}"


@pytest.fixture
def scratch_watchlist(permit_holder_api: ApiClient):
    created = permit_holder_api.request("POST", WATCHLISTS, json={"name": "QA isolation scratch list"}).json()["data"]
    yield created["id"]
    permit_holder_api.request("DELETE", WATCHLIST_DETAIL.format(watchlist_id=created["id"]))


def test_adding_another_owners_vehicle_to_a_watchlist_is_refused(
    permit_holder_api: ApiClient, scratch_watchlist: int, other_owner_vehicle_id: int
):
    resp = permit_holder_api.request(
        "POST", WATCHLIST_ITEMS.format(watchlist_id=scratch_watchlist), json={"vehicle_id": other_owner_vehicle_id}
    )
    assert resp.status == 403, f"expected 403 adding another owner's vehicle, got {resp.status}: {resp.text()[:200]}"


def test_removing_another_owners_vehicle_from_a_watchlist_is_refused(
    permit_holder_api: ApiClient, scratch_watchlist: int, other_owner_vehicle_id: int
):
    resp = permit_holder_api.request(
        "DELETE", WATCHLIST_ITEM.format(watchlist_id=scratch_watchlist, vehicle_id=other_owner_vehicle_id)
    )
    assert resp.status == 403, f"expected 403 removing another owner's vehicle, got {resp.status}: {resp.text()[:200]}"
