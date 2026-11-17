"""
Public transport schedules built by the State Admin (guide section 10.1), layer by layer:

  Stops -> Routes (ordered stops) -> Service calendar -> Service pattern (route + calendar + direction)
        -> Timetable (service pattern + times)

The PIS API has no DELETE (GET/PATCH only), so created records stay forever. The tests therefore build ONE fixed
chain ("AUTO PIS ...", found or created on first use) and reuse it; everything else is a refusal that creates nothing.
Trips need a vehicle and a driver and are not covered here.
"""

import pytest

from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api]

STOPS, ROUTES = f"{API_PREFIX}/stops", f"{API_PREFIX}/routes"
CALENDARS, PATTERNS, TIMETABLES = f"{API_PREFIX}/service-calendars", f"{API_PREFIX}/service-patterns", f"{API_PREFIX}/timetable"

STOP_A = {"stop_code": "AT7777A", "stop_name": "Auto Stop A 7777", "latitude": 28.61, "longitude": 77.2, "address": "x", "is_active": True}
STOP_B = {"stop_code": "AT7777B", "stop_name": "Auto Stop B 7777", "latitude": 28.62, "longitude": 77.21, "address": "x", "is_active": True}
ROUTE = {"route_code": "AR7777", "route_name": "Auto Route 7777"}
CALENDAR = {
    "name": "AUTO PIS calendar", "monday": True, "tuesday": True, "wednesday": True, "thursday": True,
    "friday": True, "saturday": False, "sunday": False, "effective_from": "2026-11-01", "effective_to": "2026-12-31",
}


def _rows(response) -> list[dict]:
    data = response.json()["data"]
    return data["data"] if isinstance(data, dict) and "data" in data else data


def _find(admin: ApiClient, path: str, key: str, value: str) -> dict | None:
    return next((r for r in _rows(admin.get(f"{path}?search={value}")) if r.get(key) == value), None)


def _find_or_create(admin: ApiClient, path: str, key: str, body: dict) -> dict:
    found = _find(admin, path, key, body[key])
    if not found:
        response = admin.post(path, json=body)
        assert response.status in (200, 201), response.text()[:300]
        found = _find(admin, path, key, body[key])
    assert found, f"{body[key]} was created but is not in the list"
    return found


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="module")
def chain(admin_api: ApiClient) -> dict:
    """The fixed AUTO PIS stops, route and calendar (ids)."""
    a = _find_or_create(admin_api, STOPS, "stop_code", STOP_A)
    b = _find_or_create(admin_api, STOPS, "stop_code", STOP_B)
    route = _find(admin_api, ROUTES, "route_code", ROUTE["route_code"])
    if not route:
        response = admin_api.post(ROUTES, json={**ROUTE, "stops": [a["stop_id"], b["stop_id"]]})
        assert response.status == 201, response.text()[:300]
        route = _find(admin_api, ROUTES, "route_code", ROUTE["route_code"])
    calendar = _find_or_create(admin_api, CALENDARS, "name", CALENDAR)
    return {"stop_a": a["stop_id"], "stop_b": b["stop_id"], "route": route["id"], "calendar": calendar["id"]}


def _assert_refused(response, field: str) -> None:
    assert response.status == 422, f"Expected a validation error for '{field}': {response.status} {response.text()[:300]}"
    assert any(key == field or key.startswith(field + ".") for key in response.json()["errors"]), response.text()[:300]


@pytest.mark.parametrize("missing", ["stop_code", "stop_name", "latitude", "longitude"])
def test_a_stop_needs_code_name_and_position(admin_api: ApiClient, missing: str) -> None:
    body = {k: v for k, v in {**STOP_A, "stop_code": "AT-NEVER", "stop_name": "never created"}.items() if k != missing}

    _assert_refused(admin_api.post(STOPS, json=body), missing)


def test_stop_and_route_codes_are_unique(admin_api: ApiClient, chain: dict) -> None:
    _assert_refused(admin_api.post(STOPS, json=STOP_A), "stop_code")
    _assert_refused(admin_api.post(ROUTES, json={**ROUTE, "stops": [chain["stop_a"], chain["stop_b"]]}), "route_code")


@pytest.mark.parametrize(
    "stops",
    [[], [1], [999999, 999998]],
    ids=["no-stops", "one-stop", "unknown-stops"],
)
def test_a_route_needs_at_least_two_existing_stops(admin_api: ApiClient, stops: list) -> None:
    _assert_refused(admin_api.post(ROUTES, json={"route_code": "AR-NEVER", "route_name": "never created", "stops": stops}), "stops")


def test_a_route_keeps_its_stops_in_the_order_given(admin_api: ApiClient, chain: dict) -> None:
    route = admin_api.get(f"{ROUTES}/{chain['route']}").json()["data"]

    ordered = sorted(route["stops"], key=lambda s: s["pivot"]["stop_order"])
    assert [s["id"] for s in ordered] == [chain["stop_a"], chain["stop_b"]]


@pytest.mark.parametrize("direction", ["INBOUND", "OUTBOUND"])
def test_a_service_pattern_links_a_route_and_calendar_in_one_direction(admin_api: ApiClient, chain: dict, direction: str) -> None:
    code = f"AUTOPIS-{direction[:3]}"
    pattern = _find_or_create(
        admin_api, PATTERNS, "service_code",
        {"route_id": chain["route"], "service_calendar_id": chain["calendar"], "service_code": code,
         "service_name": f"AUTO PIS {direction}", "direction": direction},
    )

    assert pattern["direction"] == direction
    assert pattern["route_id"] == chain["route"] and pattern["service_calendar_id"] == chain["calendar"]


@pytest.mark.parametrize(
    "parent, bad_field",
    [("route_id", "route_id"), ("service_calendar_id", "service_calendar_id")],
    ids=["unknown-route", "unknown-calendar"],
)
def test_a_service_pattern_needs_an_existing_route_and_calendar(admin_api: ApiClient, chain: dict, parent: str, bad_field: str) -> None:
    body = {"route_id": chain["route"], "service_calendar_id": chain["calendar"], "service_code": "AUTOPIS-NEVER",
            "service_name": "never created", "direction": "INBOUND", parent: 999999}

    _assert_refused(admin_api.post(PATTERNS, json=body), bad_field)


def test_a_timetable_needs_an_existing_service_pattern(admin_api: ApiClient) -> None:
    body = {"service_pattern_id": 999999, "name": "never created", "schedule_type": "daily",
            "start_time": "06:00", "end_time": "09:00", "valid_from": "2026-11-01"}

    _assert_refused(admin_api.post(TIMETABLES, json=body), "service_pattern_id")


@pytest.mark.parametrize("missing", ["name", "monday", "effective_from"])
def test_a_service_calendar_needs_a_name_service_days_and_a_start_date(admin_api: ApiClient, missing: str) -> None:
    body = {k: v for k, v in {**CALENDAR, "name": "AUTO PIS never"}.items() if k != missing}

    _assert_refused(admin_api.post(CALENDARS, json=body), missing)


def test_a_stop_can_be_deactivated_and_reactivated(admin_api: ApiClient, chain: dict) -> None:
    """Activate / deactivate is how a stop leaves service (the API has no delete)."""
    url = f"{STOPS}/{chain['stop_a']}"
    try:
        assert admin_api.patch(url, json={**STOP_A, "is_active": False}).status == 200
        assert admin_api.get(url).json()["data"]["is_active"] is False
    finally:
        assert admin_api.patch(url, json={**STOP_A, "is_active": True}).status == 200
    assert admin_api.get(url).json()["data"]["is_active"] is True
