"""
Permit Holder watchlist full lifecycle: create, add own vehicle, rename, remove, delete, and the
watch-history audit trail (guide chapter 13: "additions and removals record who and when").
"""

import pytest

from utils.api_client import ApiClient
from utils.permit_holder_api import VEHICLE_LIST, WATCHLIST_DETAIL, WATCHLIST_HISTORY, WATCHLIST_ITEM, WATCHLIST_ITEMS, WATCHLISTS

pytestmark = pytest.mark.permit_holder_panel


def test_watchlist_create_add_rename_remove_delete_and_history(permit_holder_api: ApiClient):
    own_vehicle = permit_holder_api.request("GET", VEHICLE_LIST).json()["data"]["data"][0]

    created = permit_holder_api.request("POST", WATCHLISTS, json={"name": "QA lifecycle watchlist"})
    assert created.status == 201
    watchlist_id = created.json()["data"]["id"]

    try:
        added = permit_holder_api.request(
            "POST", WATCHLIST_ITEMS.format(watchlist_id=watchlist_id), json={"vehicle_id": own_vehicle["id"]}
        )
        assert added.ok, f"adding this permit holder's own vehicle should succeed: {added.status}"

        renamed = permit_holder_api.request(
            "PUT", WATCHLIST_DETAIL.format(watchlist_id=watchlist_id), json={"name": "QA lifecycle watchlist (renamed)"}
        )
        assert renamed.ok
        assert renamed.json()["data"]["name"] == "QA lifecycle watchlist (renamed)"

        removed = permit_holder_api.request(
            "DELETE", WATCHLIST_ITEM.format(watchlist_id=watchlist_id, vehicle_id=own_vehicle["id"])
        )
        assert removed.ok

        history = permit_holder_api.request("GET", WATCHLIST_HISTORY).json()["data"]
        this_list_events = [h for h in history if h["watchlist_id"] == watchlist_id]
        actions = {h["action"] for h in this_list_events}
        assert {"list_renamed", "added", "removed"} <= actions, f"expected all three actions recorded, got {actions}"
        for event in this_list_events:
            assert event["actor"]["name"], "every watchlist history event must record who performed it"
            assert event["created_at"], "every watchlist history event must record when it happened"
    finally:
        permit_holder_api.request("DELETE", WATCHLIST_DETAIL.format(watchlist_id=watchlist_id))

    remaining = permit_holder_api.request("GET", WATCHLISTS).json()["data"]
    assert watchlist_id not in {w["id"] for w in remaining}, "the watchlist should be gone after delete"
