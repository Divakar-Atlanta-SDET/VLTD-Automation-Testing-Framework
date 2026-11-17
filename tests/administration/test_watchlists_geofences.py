"""
Watchlists (guide 8.6) and geofences (guide 8.5) as the State Admin uses them.

  Watchlists  create / rename / add and remove vehicles / delete; every addition and removal is recorded in
              Watch History with who and when; a deleted list leaves the list but its history stays.
  Geofences   a zone needs a type and enough points; activate / deactivate is separate from delete; delete archives
              the zone (it disappears from the list).

Every test creates its own watchlist / geofence and removes it again, also when the test fails.
"""

import pytest

from utils import data_generator as data
from utils.api_client import ApiClient

pytestmark = [pytest.mark.api]

WATCHLISTS = "/api/tracking/watchlists"
GEOFENCES = "/geofence/api/geofences"
GO = "https://vltdgo.misbackend.com"  # alert / command / geofence services


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="module")
def admin_id(admin_api: ApiClient) -> str:
    return admin_api.get("/api/auth/me").json()["data"]["id"]


@pytest.fixture
def watchlist(admin_api: ApiClient):
    response = admin_api.post(WATCHLISTS, json={"name": f"AUTO WL {data.unique_suffix()}", "description": "created by automation"})
    assert response.status == 201, response.text()[:300]
    created = response.json()["data"]
    yield created
    admin_api.delete(f"{WATCHLISTS}/{created['id']}")


def _history(admin: ApiClient, watchlist_id: int) -> list[dict]:
    return [h for h in admin.get(f"{WATCHLISTS}/history").json()["data"] if h["watchlist_id"] == watchlist_id]


def test_a_watchlist_needs_a_name(admin_api: ApiClient) -> None:
    response = admin_api.post(WATCHLISTS, json={"description": "no name"})

    assert response.status == 422 and "name" in response.json()["errors"]


def test_a_watchlist_can_be_renamed(admin_api: ApiClient, watchlist: dict) -> None:
    response = admin_api.put(f"{WATCHLISTS}/{watchlist['id']}", json={"name": watchlist["name"] + " renamed", "description": "d"})

    assert response.status == 200, response.text()[:300]
    assert admin_api.get(f"{WATCHLISTS}/{watchlist['id']}").json()["data"]["watchlist"]["name"].endswith(" renamed")


def test_vehicle_add_and_remove_are_counted_and_recorded_in_watch_history(admin_api: ApiClient, admin_id: str, watchlist: dict) -> None:
    """State Admin can add any vehicle of the state; each addition and removal is recorded with who and when."""
    vehicle = admin_api.get("/api/tracking/vehicles").json()["data"][0]
    url = f"{WATCHLISTS}/{watchlist['id']}"

    assert admin_api.post(f"{url}/items", json={"vehicle_id": vehicle["id"]}).status == 201
    assert admin_api.get(url).json()["data"]["watchlist"]["items_count"] == 1
    assert admin_api.delete(f"{url}/items/{vehicle['id']}").status == 200
    assert admin_api.get(url).json()["data"]["watchlist"]["items_count"] == 0

    events = [(h["action"], h["vehicle_number"], h["actor"]["id"]) for h in _history(admin_api, watchlist["id"]) if h["vehicle_number"]]
    assert ("added", vehicle["vehicle_number"], admin_id) in events
    assert ("removed", vehicle["vehicle_number"], admin_id) in events
    assert all(h["created_at"] for h in _history(admin_api, watchlist["id"]))


def test_an_unknown_vehicle_cannot_be_added(admin_api: ApiClient, watchlist: dict) -> None:
    response = admin_api.post(f"{WATCHLISTS}/{watchlist['id']}/items", json={"vehicle_id": 99999999})

    assert response.status == 422 and "vehicle_id" in response.json()["errors"]


def test_a_deleted_watchlist_disappears_but_its_history_stays(admin_api: ApiClient, watchlist: dict) -> None:
    vehicle = admin_api.get("/api/tracking/vehicles").json()["data"][0]
    admin_api.post(f"{WATCHLISTS}/{watchlist['id']}/items", json={"vehicle_id": vehicle["id"]})

    assert admin_api.delete(f"{WATCHLISTS}/{watchlist['id']}").status == 200

    assert admin_api.get(f"{WATCHLISTS}/{watchlist['id']}").status == 404
    assert watchlist["id"] not in [w["id"] for w in admin_api.get(WATCHLISTS).json()["data"]]
    assert {h["action"] for h in _history(admin_api, watchlist["id"])} >= {"added", "list_deleted"}


# ── Geofences ─────────────────────────────────────────────────────────────────

TRIANGLE = [{"lat": 28.6139, "lng": 77.2090}, {"lat": 28.6150, "lng": 77.2100}, {"lat": 28.6130, "lng": 77.2110}]


def _geofences(admin: ApiClient) -> list[dict]:
    return admin.request("GET", GEOFENCES, origin=GO).json()["geofences"]


@pytest.fixture
def geofence(admin_api: ApiClient):
    response = admin_api.request(
        "POST", GEOFENCES, origin=GO,
        json={"name": f"AUTO GF {data.unique_suffix()}", "type": "polygon", "points": TRIANGLE, "alert_on_entry": True, "alert_on_exit": True},
    )
    assert response.status in (200, 201), response.text()[:300]
    body = response.json()
    created = body.get("geofence") or body
    yield created
    admin_api.request("DELETE", f"{GEOFENCES}/{created['id']}", origin=GO)


@pytest.mark.parametrize(
    "bad, fragment",
    [({"type": "circle"}, "type"), ({"points": TRIANGLE[:2]}, "points"), ({"name": ""}, "name")],
    ids=["unknown-type", "two-points", "no-name"],
)
def test_an_invalid_geofence_is_refused(admin_api: ApiClient, bad: dict, fragment: str) -> None:
    body = {"name": "AUTO GF never", "type": "polygon", "points": TRIANGLE, **bad}

    response = admin_api.request("POST", GEOFENCES, json=body, origin=GO)

    assert response.status == 400 and fragment in response.json()["error"], response.text()[:300]


def test_a_new_geofence_is_listed_active_and_manageable(admin_api: ApiClient, geofence: dict) -> None:
    listed = next(g for g in _geofences(admin_api) if g["id"] == geofence["id"])

    assert listed["active"] is True and listed["can_manage"] is True
    assert listed["alert_on_entry"] is True and listed["alert_on_exit"] is True


def test_deactivating_is_separate_from_deleting(admin_api: ApiClient, geofence: dict) -> None:
    url = f"{GEOFENCES}/{geofence['id']}"

    assert admin_api.request("PATCH", f"{url}/deactivate", origin=GO).status == 200
    assert next(g for g in _geofences(admin_api) if g["id"] == geofence["id"])["active"] is False
    assert admin_api.request("PATCH", f"{url}/activate", origin=GO).status == 200
    assert next(g for g in _geofences(admin_api) if g["id"] == geofence["id"])["active"] is True


def test_deleting_a_geofence_removes_it_from_the_list(admin_api: ApiClient, geofence: dict) -> None:
    assert admin_api.request("DELETE", f"{GEOFENCES}/{geofence['id']}", origin=GO).status in (200, 204)

    assert geofence["id"] not in [g["id"] for g in _geofences(admin_api)]
