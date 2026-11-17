"""
Read-only consistency checks of the State Admin's monitoring data (guide sections 5, 7, 12, 15).

The environment is live, so nothing is hard-coded: every figure is reconciled against the rows or lists it is
derived from, and the timing rule is only checked far from its boundary (a packet 5+ minutes old is never "online",
one under a minute old always is).

  Vehicle / device status   a device that has not sent for a long time is offline; counters equal their rows
  Alert Report              the status counters add up to the total
  Dashboard network totals  equal the totals of the OEM, RTO, Inspector and Permit Holder lists
  Inspector list            search and the RTO filter return only matching inspectors (guide 15.1)
"""

from datetime import datetime, timedelta, timezone

import pytest

from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api]

STATUS_REPORT = "/api/tracking/devices/status-report"
HEALTH = "/api/tracking/devices/health"


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


def _age(row: dict) -> timedelta | None:
    return datetime.now(timezone.utc) - datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None


def test_device_online_flag_follows_the_last_packet(admin_api: ApiClient) -> None:
    """Online means a recent packet: stale devices (5+ min) are never online, fresh ones (under 1 min) always are."""
    rows = admin_api.get(f"{STATUS_REPORT}?per_page=100").json()["data"]

    wrong = []
    for row in rows:
        age = _age(row)
        if row["is_online"] != ("online" in row["statuses"]):
            wrong.append((row["vehicle_number"], "is_online disagrees with statuses", row["statuses"]))
        if age is None or age > timedelta(minutes=5):
            if row["is_online"]:
                wrong.append((row["vehicle_number"], "online although last packet is", age))
        elif age < timedelta(minutes=1) and not row["is_online"]:
            wrong.append((row["vehicle_number"], "offline although last packet is", age))
    assert not wrong, wrong


def test_device_status_counters_equal_their_rows(admin_api: ApiClient) -> None:
    body = admin_api.get(f"{STATUS_REPORT}?per_page=100").json()
    rows, summary = body["data"], body["summary"]

    assert summary["total"] == body["meta"]["total"] == len(rows)
    for status in ("online", "active", "inactive", "intermittent", "never_sending", "not_sending_x_days", "recently_offline"):
        assert summary[status] == sum(status in row["statuses"] for row in rows), status


def test_live_tracking_status_summary_covers_every_vehicle(admin_api: ApiClient) -> None:
    """Moving + Idle + SOS + Offline = all vehicles of the state; no vehicle is in two groups or none."""
    summary = admin_api.get("/api/tracking/vehicles/summary").json()["data"]
    vehicles = admin_api.get("/api/tracking/vehicles?per_page=100").json()

    assert sum(summary[k] for k in ("moving", "idle", "sos", "offline")) == vehicles["meta"]["total"] == len(vehicles["data"])


def test_device_health_counters_equal_their_rows(admin_api: ApiClient) -> None:
    body = admin_api.get(f"{HEALTH}?per_page=100").json()
    rows, summary = body["data"], body["meta"]["summary"]

    assert summary["total"] == len(rows)
    for status in ("healthy", "needs_review", "tamper", "offline"):
        assert summary[status] == sum(row["status"] == status for row in rows), status
    assert summary["low_battery"] == sum(bool(row["low_battery"]) for row in rows)
    assert summary["poor_gps"] == sum(bool(row["poor_gps_fix"]) for row in rows)


def test_alert_report_status_counters_add_up(admin_api: ApiClient) -> None:
    body = admin_api.get("/api/tracking/alerts/report?per_page=1").json()
    summary = body["summary"] if "summary" in body else body["meta"]["summary"]

    assert summary["total"] == body["meta"]["total"]
    assert summary["open"] + summary["in_progress"] + summary["acknowledged"] + summary["resolved"] + summary["closed"] == summary["total"]
    assert summary["cleared"] == summary["resolved"] + summary["closed"]


@pytest.mark.parametrize("key", ["oems", "rtos", "inspectors"])
def test_dashboard_network_totals_equal_the_user_lists(admin_api: ApiClient, key: str) -> None:
    network = admin_api.get(f"{API_PREFIX}/dashboard").json()["data"]["network"]
    summary = admin_api.get(f"{API_PREFIX}/{key}").json()["summary"]

    assert network[key]["total"] == summary["total"], f"Dashboard {key}: {network[key]} vs list {summary}"


def test_dashboard_fleet_owners_and_schools_equal_the_permit_holder_list(admin_api: ApiClient) -> None:
    network = admin_api.get(f"{API_PREFIX}/dashboard").json()["data"]["network"]
    summary = admin_api.get(f"{API_PREFIX}/fleet-managers").json()["summary"]

    for field in ("total", "active"):
        assert network["fleet_owners"][field] + network["schools"][field] == summary[field], field


def _inspectors(admin: ApiClient, query: str) -> list[dict]:
    body = admin.get(f"{API_PREFIX}/inspectors?{query}&per_page=100").json()["data"]
    return body["data"] if isinstance(body, dict) else body


def test_inspector_search_returns_only_matches_by_name_email_or_contact(admin_api: ApiClient) -> None:
    sample = _inspectors(admin_api, "")[0]

    for field in ("name", "email", "contact_no"):
        term = sample[field]
        found = _inspectors(admin_api, f"search={term}")
        assert any(i["id"] == sample["id"] for i in found), f"search by {field} did not find the inspector"
        assert all(term.lower() in " ".join(str(i[f]) for f in ("name", "email", "contact_no")).lower() for i in found), field


def test_inspector_rto_filter_returns_only_that_rtos_inspectors(admin_api: ApiClient) -> None:
    linked = next(i for i in _inspectors(admin_api, "") if i["rto_mappings"])
    rto_id = linked["rto_mappings"][0]["rto"]["id"]

    found = _inspectors(admin_api, f"rto_id={rto_id}")

    assert any(i["id"] == linked["id"] for i in found)
    assert all(rto_id in [m["rto"]["id"] for m in i["rto_mappings"]] for i in found), "An inspector of another RTO was returned"
