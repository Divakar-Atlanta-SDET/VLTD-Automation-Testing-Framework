"""
OEM Tracking & GIS: Live Tracking and Watchlists (guide 7, 13), Alerts and their rules (9), Geofences (11), Trip Playback (8).

The OEM account has no vehicle (nothing is installed on it), so what can be shown is what does not need one:

  empty states      every page says so instead of showing broken or stale data
  watchlists        create / rename / delete through the screen; "each organisation sees only its own lists"; "only your
                    own vehicles" (guide 13)
  isolation         a geofence or alert rule of the State Admin is invisible to the OEM and cannot be changed by it (9.3, 11)
  alert rules       an OEM "has its own rules" (9.3): creating one is a known defect (BUG-047)

Live positions, trip routes, alert timelines and the vehicle-based limits need installed devices and stay manual.
Everything a test creates is removed afterwards (also when it fails).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.tracking import AlertsPage, GeofencesPage, LiveTrackingPage, TripPlaybackPage
from utils import data_generator as data
from utils.api_client import ApiClient
from utils.oem_panel_api import ALERT_RULES, GEOFENCES, GO_ORIGIN, WATCHLISTS

pytestmark = [pytest.mark.oem_panel]

TRIANGLE = [{"lat": 28.6139, "lng": 77.2090}, {"lat": 28.6150, "lng": 77.2100}, {"lat": 28.6130, "lng": 77.2110}]


@pytest.fixture
def no_vehicles(oem_api: ApiClient) -> None:
    summary = oem_api.get("/api/tracking/vehicles/summary").json()["data"]
    if any(summary.values()):
        pytest.skip("The OEM has vehicles now; the empty states cannot be shown")


@pytest.fixture
def oem_watchlists(oem_api: ApiClient):
    """A name prefix unique to the test; afterwards every watchlist of the OEM with that prefix is removed (tests run in parallel, so never by a shared prefix)."""
    tag = f"AUTO ui {data.unique_suffix()}"
    yield tag
    for watchlist in oem_api.get(WATCHLISTS).json()["data"]:
        if watchlist["name"].startswith(tag):
            oem_api.delete(f"{WATCHLISTS}/{watchlist['id']}")


def _watchlist(api: ApiClient, name: str) -> dict | None:
    return next((w for w in api.get(WATCHLISTS).json()["data"] if w["name"] == name), None)


# ── Empty states ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "page_class, message",
    [
        (LiveTrackingPage, "0 vehicles"),
        (AlertsPage, "No alerts are waiting to be cleared."),
        (GeofencesPage, "No geofence alerts are waiting to be cleared."),
        (TripPlaybackPage, "No points loaded for this range yet."),
    ],
    ids=["live-tracking", "alerts", "geofences", "trip-playback"],
)
def test_a_page_without_vehicles_says_so(oem_page: Page, no_vehicles, page_class, message: str) -> None:
    page_class(oem_page).open()

    expect(oem_page.get_by_text(message).first).to_be_visible()


def test_a_trip_cannot_be_loaded_without_a_vehicle(oem_page: Page) -> None:
    page = TripPlaybackPage(oem_page).open()

    expect(page.load_button).to_be_disabled()


def test_the_resolved_tab_says_nothing_was_cleared(oem_page: Page, no_vehicles) -> None:
    AlertsPage(oem_page).open_resolved()

    expect(oem_page.get_by_text("No cleared alerts in this range")).to_be_visible()
    expect(oem_page.get_by_text("0 cleared")).to_be_visible()


def test_trip_playback_finds_no_vehicle_for_an_unknown_number(oem_page: Page) -> None:
    page = TripPlaybackPage(oem_page).open()

    page.vehicle_box.fill("ZZ99ZZ9999")

    expect(oem_page.get_by_text("No matching vehicles")).to_be_visible()
    expect(page.load_button).to_be_disabled()


# ── Watchlists ────────────────────────────────────────────────────────────────

def test_a_watchlist_can_be_created_renamed_and_deleted(oem_page: Page, oem_api: ApiClient, oem_watchlists: str) -> None:
    name = f"{oem_watchlists} list"
    page = LiveTrackingPage(oem_page).open_watchlists()

    with oem_page.expect_response(lambda r: r.url.endswith("/api/tracking/watchlists") and r.request.method == "POST") as created:
        page.create_watchlist(name, "made by the test")

    assert created.value.status == 201
    page.expect_selected(f"{name} (0)")
    stored = _watchlist(oem_api, name)
    assert (stored["description"], stored["items_count"]) == ("made by the test", 0)

    page.rename_watchlist(f"{name} renamed")

    page.expect_selected(f"{name} renamed (0)")
    assert _watchlist(oem_api, name) is None and _watchlist(oem_api, f"{name} renamed") is not None

    page.confirm_delete(f"{name} renamed")

    page.expect_selected(re.compile(r"Select a watchlist|No watchlists yet"))
    assert _watchlist(oem_api, f"{name} renamed") is None


def test_a_watchlist_cannot_be_created_without_a_name(oem_page: Page) -> None:
    page = LiveTrackingPage(oem_page).open_watchlists()
    page.new_watchlist_button.click()
    create = oem_page.get_by_role("button", name="Create", exact=True)

    expect(create).to_be_disabled()
    page.name_box.fill("   ")
    expect(create).to_be_disabled()
    page.name_box.fill("AUTO ui named")
    expect(create).to_be_enabled()


def test_each_organisation_sees_only_its_own_watchlists(oem_page: Page, oem_api: ApiClient, admin_api: ApiClient, oem_watchlists: str) -> None:
    """Guide 13: the State Admin sees every list; an OEM sees only the lists of its own users."""
    mine = oem_api.post(WATCHLISTS, json={"name": f"{oem_watchlists} oem list"}).json()["data"]
    theirs = admin_api.post(WATCHLISTS, json={"name": f"AUTO ui admin list {data.unique_suffix()}"}).json()["data"]
    try:
        assert theirs["id"] not in [w["id"] for w in oem_api.get(WATCHLISTS).json()["data"]]
        assert oem_api.get(f"{WATCHLISTS}/{theirs['id']}").status == 404
        assert oem_api.delete(f"{WATCHLISTS}/{theirs['id']}").status in (403, 404)
        assert mine["id"] in [w["id"] for w in admin_api.get(WATCHLISTS).json()["data"]]
        assert _watchlist(admin_api, theirs["name"]) is not None, "the OEM removed the State Admin's list"

        page = LiveTrackingPage(oem_page).open_watchlists()
        expect(page.watchlist_select).to_contain_text("Select a watchlist")
        options = " ".join(page.watchlist_options())
        assert f"{oem_watchlists} oem list" in options and theirs["name"] not in options
    finally:
        admin_api.delete(f"{WATCHLISTS}/{theirs['id']}")


def test_a_vehicle_outside_the_oems_jurisdiction_cannot_be_watched(oem_api: ApiClient, admin_api: ApiClient, oem_watchlists: str) -> None:
    """Guide 13: 'Vehicles outside it are refused on add.' Backend check - the OEM has no vehicle to search for in the screen."""
    foreign = admin_api.get("/api/tracking/vehicles").json()["data"][0]
    watchlist = oem_api.post(WATCHLISTS, json={"name": f"{oem_watchlists} jurisdiction"}).json()["data"]

    response = oem_api.post(f"{WATCHLISTS}/{watchlist['id']}/items", json={"vehicle_id": foreign["id"]})

    assert response.status == 403 and "jurisdiction" in response.text().lower(), f"{response.status} {response.text()[:200]}"
    assert oem_api.get(f"{WATCHLISTS}/{watchlist['id']}").json()["data"]["watchlist"]["items_count"] == 0


# ── Geofences and alert rules of other organisations ──────────────────────────

@pytest.fixture
def admin_geofence(admin_api: ApiClient):
    response = admin_api.request(
        "POST", GEOFENCES, origin=GO_ORIGIN,
        json={"name": f"AUTO ui admin zone {data.unique_suffix()}", "type": "polygon", "points": TRIANGLE, "alert_on_entry": True},
    )
    assert response.status in (200, 201), response.text()[:300]
    body = response.json()
    created = body.get("geofence") or body
    yield created
    admin_api.request("DELETE", f"{GEOFENCES}/{created['id']}", origin=GO_ORIGIN)


def test_a_geofence_of_the_state_admin_is_invisible_and_untouchable_for_the_oem(oem_api: ApiClient, admin_api: ApiClient, admin_geofence: dict) -> None:
    """Guide 9.3 / 11: a panel sees and manages only the zones it created (or whose vehicles are all in its jurisdiction)."""
    seen = oem_api.request("GET", GEOFENCES, origin=GO_ORIGIN).json()["geofences"]
    assert admin_geofence["id"] not in [g["id"] for g in seen]

    url = f"{GEOFENCES}/{admin_geofence['id']}"
    changes = {
        "deactivate": oem_api.request("PATCH", f"{url}/deactivate", origin=GO_ORIGIN).status,
        "delete": oem_api.request("DELETE", url, origin=GO_ORIGIN).status,
    }

    assert set(changes.values()) <= {403, 404}, f"The OEM could change the State Admin's geofence: {changes}"
    still = next(g for g in admin_api.request("GET", GEOFENCES, origin=GO_ORIGIN).json()["geofences"] if g["id"] == admin_geofence["id"])
    assert still["active"] is True


def test_alert_rules_of_other_organisations_are_not_listed(oem_api: ApiClient, admin_api: ApiClient) -> None:
    """Guide 9.3: 'Each organisation has its own rules and therefore its own alerts.'"""
    admin_rules = {r["id"] for r in admin_api.request("GET", ALERT_RULES, origin=GO_ORIGIN).json()["rules"]}
    oem_rules = {r["id"] for r in oem_api.request("GET", ALERT_RULES, origin=GO_ORIGIN).json()["rules"]}
    if not admin_rules:
        pytest.skip("The State Admin has no alert rule to compare with")

    assert not (admin_rules & oem_rules), f"The OEM lists State Admin rules: {sorted(admin_rules & oem_rules)}"


# ── Alert rules ───────────────────────────────────────────────────────────────

@pytest.mark.xfail(
    reason="BUG-047: creating an alert rule as an OEM Admin is refused with 403 'your role is not permitted to create or update a rule with this scope' "
           "for 'All vehicles' (the form's default) and 'Fitment Centre'; the RTO scope has no options (BUG-040)",
    strict=False,
)
def test_an_oem_can_create_an_alert_rule(oem_page: Page, oem_api: ApiClient) -> None:
    """Guide 9.3: the OEM has its own rules; without one it sees no alert except SOS."""
    page = AlertsPage(oem_page).open_rules()
    name = f"AUTO ui rule {data.unique_suffix()}"
    try:
        with oem_page.expect_response(lambda r: r.url.endswith("/alert/api/rules") and r.request.method == "POST") as sent:
            page.create_overspeed_rule(name, 80)

        assert sent.value.status in (200, 201), f"{sent.value.status} {sent.value.text()[:200]}"
        expect(page.rule(name)).to_be_visible()
    finally:
        for rule in oem_api.request("GET", ALERT_RULES, origin=GO_ORIGIN).json()["rules"]:
            if rule["name"] == name:
                oem_api.request("DELETE", f"{ALERT_RULES}/{rule['id']}", origin=GO_ORIGIN)
