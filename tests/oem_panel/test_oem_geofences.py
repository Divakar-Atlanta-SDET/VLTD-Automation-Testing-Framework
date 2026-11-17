"""
OEM Geofences (guide chapter 11), driven through the screen the OEM user works with.

  "A geofence is a zone drawn on the map; a vehicle entering or leaving it raises an alert. ... Deactivating a zone is separate
   from deleting it: a deleted zone leaves the list and is no longer evaluated, its past alerts are kept."

The product owner confirmed that an OEM may create geofences. The zones are drawn by dragging across the Google map, and the
service stores every shape as a polygon. The OEM account has no vehicle, so assigning vehicles and the alerts a zone raises
stay manual; the isolation of other organisations' zones is in `test_oem_tracking_and_alerts.py`.

Everything a test creates is named 'AUTO ui ...' and removed afterwards (also when the test fails); the OEM's older zones
that were not made by a test are never touched.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.tracking import GeofencesPage
from utils import data_generator as data
from utils.api_client import ApiClient
from utils.oem_panel_api import GEOFENCES, GO_ORIGIN

pytestmark = [pytest.mark.oem_panel]

TRIANGLE = [{"lat": 28.6139, "lng": 77.2090}, {"lat": 28.6150, "lng": 77.2100}, {"lat": 28.6130, "lng": 77.2110}]


def _zones(api: ApiClient) -> list[dict]:
    return api.request("GET", GEOFENCES, origin=GO_ORIGIN).json()["geofences"]


def _stored(api: ApiClient, name: str) -> dict | None:
    return next((z for z in _zones(api) if z["name"] == name), None)


def _is_creation(response) -> bool:
    return response.url.endswith("/geofence/api/geofences") and response.request.method == "POST"


@pytest.fixture
def oem_zones(oem_api: ApiClient):
    """A zone-name prefix unique to the test; afterwards every zone of the OEM with that prefix is removed (tests run in parallel)."""
    tag = f"AUTO ui {data.unique_suffix()}"
    yield tag
    for zone in _zones(oem_api):
        if zone["name"].startswith(tag):
            oem_api.request("DELETE", f"{GEOFENCES}/{zone['id']}", origin=GO_ORIGIN)


@pytest.fixture
def api_zone(oem_api: ApiClient, oem_zones: str) -> dict:
    """A zone created through the service."""
    response = oem_api.request(
        "POST", GEOFENCES, origin=GO_ORIGIN,
        json={"name": f"{oem_zones} zone", "type": "polygon", "points": TRIANGLE, "alert_on_entry": True, "alert_on_exit": True},
    )
    assert response.status in (200, 201), response.text()[:300]
    body = response.json()
    return body.get("geofence") or body


@pytest.fixture
def zones_page(oem_page: Page) -> GeofencesPage:
    return GeofencesPage(oem_page).open_zones()


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("shape", ["Circle", "Rectangle"])
def test_a_zone_drawn_on_the_map_is_saved_and_listed_active(zones_page: GeofencesPage, oem_api: ApiClient, oem_zones: str, shape: str) -> None:
    name = f"{oem_zones} {shape.lower()}"

    with zones_page.page.expect_response(_is_creation) as sent:
        zones_page.create(name, shape)

    assert sent.value.status == 201, sent.value.text()[:200]
    zones_page.find(name)
    expect(zones_page.zone(name)).to_contain_text("Active")
    stored = _stored(oem_api, name)
    assert stored["active"] is True and len(stored["points"]) >= 3, stored


def test_a_zone_cannot_be_saved_without_a_name_or_a_boundary(zones_page: GeofencesPage) -> None:
    zones_page.start_create()
    expect(zones_page.save_button).to_be_disabled()

    zones_page.name_box.fill("AUTO ui incomplete")
    expect(zones_page.save_button).to_be_disabled()  # a name alone is not enough

    zones_page.draw("Circle")
    expect(zones_page.save_button).to_be_enabled()

    zones_page.name_box.fill("")
    expect(zones_page.save_button).to_be_disabled()  # a boundary alone is not enough


def test_cancelling_the_form_asks_before_discarding_and_creates_nothing(zones_page: GeofencesPage, oem_api: ApiClient, oem_zones: str) -> None:
    name = f"{oem_zones} cancelled"
    zones_page.start_create()
    zones_page.name_box.fill(name)
    zones_page.draw("Circle")

    zones_page.cancel_form()
    expect(zones_page.page.get_by_text("The current form and draft boundary will be cleared.")).to_be_visible()
    zones_page.keep_editing()

    expect(zones_page.name_box).to_have_value(name)  # nothing was lost
    expect(zones_page.save_button).to_be_enabled()

    zones_page.cancel_form()
    zones_page.discard()

    expect(zones_page.create_button).to_be_visible()
    assert _stored(oem_api, name) is None


# ── List: duplicate, deactivate, delete, search, filter ───────────────────────

def test_duplicating_a_zone_adds_an_inactive_copy(zones_page: GeofencesPage, oem_api: ApiClient, api_zone: dict) -> None:
    zones_page.page.reload()
    zones_page.zones_tab.click()
    zones_page.find(api_zone["name"])

    zones_page.duplicate(api_zone["name"])

    copy = f"{api_zone['name']} Copy"
    expect(zones_page.zone(copy)).to_contain_text("Inactive")
    assert _stored(oem_api, copy)["active"] is False and _stored(oem_api, api_zone["name"])["active"] is True


def test_a_zone_can_be_deactivated_and_activated_again(zones_page: GeofencesPage, oem_api: ApiClient, api_zone: dict) -> None:
    zones_page.page.reload()
    zones_page.zones_tab.click()
    zones_page.find(api_zone["name"])
    zone = zones_page.zone(api_zone["name"])

    with zones_page.page.expect_response(lambda r: r.url.endswith("/deactivate")):
        zones_page.toggle(api_zone["name"])

    expect(zone).to_contain_text("Inactive")
    assert _stored(oem_api, api_zone["name"])["active"] is False

    with zones_page.page.expect_response(lambda r: r.url.endswith("/activate")):
        zones_page.toggle(api_zone["name"])

    expect(zone).to_contain_text("Active")
    assert _stored(oem_api, api_zone["name"])["active"] is True


def test_delete_asks_for_confirmation_and_cancel_keeps_the_zone(zones_page: GeofencesPage, oem_api: ApiClient, api_zone: dict) -> None:
    zones_page.page.reload()
    zones_page.zones_tab.click()
    zones_page.find(api_zone["name"])

    zones_page.delete(api_zone["name"])

    expect(zones_page.page.get_by_text("Its past alerts and events are kept.")).to_be_visible()
    zones_page.cancel_delete()
    expect(zones_page.zone(api_zone["name"])).to_be_visible()
    assert _stored(oem_api, api_zone["name"]) is not None

    zones_page.delete(api_zone["name"])
    zones_page.confirm_delete()

    expect(zones_page.zone(api_zone["name"])).to_have_count(0)
    assert _stored(oem_api, api_zone["name"]) is None


def test_search_and_the_status_filter_narrow_the_list(zones_page: GeofencesPage, oem_api: ApiClient, api_zone: dict) -> None:
    oem_api.request("PATCH", f"{GEOFENCES}/{api_zone['id']}/deactivate", origin=GO_ORIGIN)
    zones_page.page.reload()
    zones_page.zones_tab.click()

    zones_page.find(api_zone["name"])
    expect(zones_page.zone(api_zone["name"])).to_be_visible()

    zones_page.choose_filter(zones_page.status_filter, "Active")
    expect(zones_page.zone(api_zone["name"])).to_have_count(0)
    expect(zones_page.page.get_by_text("No geofences match these filters.")).to_be_visible()

    zones_page.choose_filter(zones_page.status_filter, "Inactive")
    expect(zones_page.zone(api_zone["name"])).to_be_visible()

    zones_page.find("AUTO ui no such zone")
    expect(zones_page.page.get_by_text("No geofences match these filters.")).to_be_visible()


# ── Known defects ─────────────────────────────────────────────────────────────

@pytest.mark.xfail(
    reason="BUG-049: Edit geofence crashes the page ('Something went wrong': TypeError reading 'type' of null) for every zone, "
           "for the OEM and for the State Admin",
    strict=False,
)
def test_a_zone_can_be_edited(zones_page: GeofencesPage, oem_api: ApiClient, api_zone: dict) -> None:
    zones_page.page.reload()
    zones_page.zones_tab.click()
    zones_page.find(api_zone["name"])
    renamed = f"{api_zone['name']} renamed"

    zones_page.edit(api_zone["name"])

    expect(zones_page.name_box).to_have_value(api_zone["name"])
    zones_page.name_box.fill(renamed)
    zones_page.save_button.click()
    zones_page.find(renamed)
    expect(zones_page.zone(renamed)).to_be_visible()
    assert _stored(oem_api, renamed) is not None and _stored(oem_api, api_zone["name"]) is None


@pytest.mark.xfail(
    reason="BUG-050: every zone drawn as a circle or a rectangle is saved as a polygon and listed as 'Freehand', so the "
           "'Circle' and 'Rectangle' type filters never match anything",
    strict=False,
)
@pytest.mark.parametrize("shape", ["Circle", "Rectangle"])
def test_a_drawn_zone_is_found_by_its_shape_filter(zones_page: GeofencesPage, oem_zones: str, shape: str) -> None:
    name = f"{oem_zones} {shape.lower()}"
    with zones_page.page.expect_response(_is_creation):
        zones_page.create(name, shape)
    zones_page.find(name)
    expect(zones_page.zone(name)).to_be_visible()

    zones_page.choose_filter(zones_page.type_filter, shape)

    expect(zones_page.zone(name)).to_be_visible()
    expect(zones_page.zone(name)).to_contain_text(re.compile(shape, re.I))
