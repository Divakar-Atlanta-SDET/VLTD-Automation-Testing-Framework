"""
System Configuration (guide section 5): state-wide thresholds, each can be switched on or off, every change is
recorded in the audit log.

  GET /api/transport-commissioner/system-configuration        settings
  PUT /api/transport-commissioner/system-configuration        {"settings": {key: {enabled, value, unit}}}
  GET /api/transport-commissioner/system-configuration/logs   change log, newest first

These tests change a state-wide setting for a moment, so the `original_settings` fixture puts every setting back
(also when a test fails) and the module is pinned to one xdist worker. The change log keeps the entries - that is
the audit trail working as designed.
"""

import pytest

from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api, pytest.mark.xdist_group("system-configuration")]

CONFIG = f"{API_PREFIX}/system-configuration"

SETTINGS = {
    "device_offline_alert": ["minutes", "hours", "days"],
    "cop_expiry_reminder": ["days"],
    "tac_expiry_reminder": ["days"],
    "fitment_vehicle_distance": ["meters", "kilometers"],
    "inspector_vehicle_distance": ["meters", "kilometers"],
    "rto_vehicle_distance": ["meters", "kilometers"],
    "rto_verification_packet_max_age": None,  # unit list not stated by the guide; only checked for presence
}


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


def _current(admin: ApiClient) -> dict:
    return admin.get(CONFIG).json()["data"]["settings"]


def _payload(settings: dict) -> dict:
    return {key: {"enabled": s["enabled"], "value": s["value"], "unit": s["unit"]} for key, s in settings.items()}


@pytest.fixture
def original_settings(admin_api: ApiClient):
    """The settings before the test; written back afterwards no matter what the test did."""
    original = _current(admin_api)
    yield original
    restored = admin_api.put(CONFIG, json={"settings": _payload(original)})
    assert restored.status == 200, f"COULD NOT RESTORE THE SYSTEM CONFIGURATION: {restored.text()[:300]}"
    assert _payload(_current(admin_api)) == _payload(original)


def _newest_log(admin: ApiClient) -> dict:
    return admin.get(f"{CONFIG}/logs").json()["data"][0]


def _assert_audited(admin: ApiClient, key: str, old: dict, new: dict) -> None:
    entry = _newest_log(admin)
    me = admin.get("/api/auth/me").json()["data"]
    assert entry["changed_by"]["id"] == me["id"], entry["changed_by"]
    change = next((c for c in entry["changes"] if c["key"] == key), None)
    assert change, f"No audit entry for {key}: {entry['changes']}"
    assert {k: change["old"][k] for k in ("enabled", "value", "unit")} == old
    assert {k: change["new"][k] for k in ("enabled", "value", "unit")} == new


def test_all_documented_settings_exist_with_their_units(admin_api: ApiClient) -> None:
    settings = _current(admin_api)

    assert set(settings) == set(SETTINGS)
    for key, units in SETTINGS.items():
        if units:
            assert settings[key]["units"] == units, key
        assert settings[key]["value"] > 0, key


@pytest.mark.parametrize("key", list(SETTINGS))
def test_changing_a_value_is_saved_and_audited(admin_api: ApiClient, original_settings: dict, key: str) -> None:
    before = _payload(original_settings)[key]
    after = {**before, "value": before["value"] + 1}

    response = admin_api.put(CONFIG, json={"settings": {key: after}})

    assert response.status == 200, response.text()[:300]
    assert _payload(_current(admin_api))[key] == after
    _assert_audited(admin_api, key, before, after)


@pytest.mark.parametrize("key", list(SETTINGS))
def test_a_setting_can_be_switched_off_and_on(admin_api: ApiClient, original_settings: dict, key: str) -> None:
    before = _payload(original_settings)[key]
    off, on = {**before, "enabled": False}, {**before, "enabled": True}

    assert admin_api.put(CONFIG, json={"settings": {key: off}}).status == 200
    assert _payload(_current(admin_api))[key] == off
    _assert_audited(admin_api, key, before, off)

    assert admin_api.put(CONFIG, json={"settings": {key: on}}).status == 200
    assert _payload(_current(admin_api))[key] == on
    _assert_audited(admin_api, key, off, on)


@pytest.mark.parametrize(
    "key, unit, value",
    [("device_offline_alert", "minutes", 90), ("fitment_vehicle_distance", "kilometers", 2)],
    ids=["offline-in-minutes", "fitment-distance-in-km"],
)
def test_a_value_can_be_saved_in_another_documented_unit(
    admin_api: ApiClient, original_settings: dict, key: str, unit: str, value: int
) -> None:
    before = _payload(original_settings)[key]
    after = {"enabled": before["enabled"], "value": value, "unit": unit}

    assert admin_api.put(CONFIG, json={"settings": {key: after}}).status == 200

    assert _payload(_current(admin_api))[key] == after
    _assert_audited(admin_api, key, before, after)


@pytest.mark.parametrize(
    "bad, error_field",
    [
        ({"value": 0}, "value"),
        ({"value": -1}, "value"),
        ({"value": "abc"}, "value"),
        ({"unit": "parsecs"}, "unit"),
        ({"enabled": None}, "enabled"),
    ],
    ids=["zero", "negative", "text", "unknown-unit", "missing-enabled"],
)
def test_invalid_values_are_rejected_and_nothing_changes(
    admin_api: ApiClient, original_settings: dict, bad: dict, error_field: str
) -> None:
    key = "fitment_vehicle_distance"
    candidate = {**_payload(original_settings)[key], **bad}
    if candidate["enabled"] is None:
        del candidate["enabled"]
    newest_before = _newest_log(admin_api)["id"]

    response = admin_api.put(CONFIG, json={"settings": {key: candidate}})

    assert response.status == 422, response.text()[:300]
    assert f"settings.{key}.{error_field}" in response.json()["errors"]
    assert _payload(_current(admin_api)) == _payload(original_settings)
    assert _newest_log(admin_api)["id"] == newest_before, "A rejected change was written to the audit log"
