"""
Announcements (guide section 13): published by the State Admin to chosen user types.

  Each announcement has an importance (information, warning, critical), a start and end time and an on/off
  control. Its status follows the window: scheduled before the start, active during it, expired after the end;
  a switched-off announcement stays inactive.

Windows are chosen so that nobody sees them for long: the audience is RTO inspectors, a window that includes "now"
lasts a few minutes, and every announcement is deleted at the end of its test.
"""

from datetime import datetime, timedelta, timezone

import pytest

from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api]

ANNOUNCEMENTS = f"{API_PREFIX}/announcements"


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


def _stamp(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat()


def _body(subject: str, starts: datetime, ends: datetime, **over) -> dict:
    return {
        "subject": subject, "content": "Created by the automated tests", "priority": "information",
        "recipient_types": ["rto_inspector"], "starts_at": _stamp(starts), "ends_at": _stamp(ends), **over,
    }


def _listed(admin: ApiClient, subject: str) -> dict | None:
    rows = admin.get(f"{ANNOUNCEMENTS}?per_page=100&search={subject}").json()["data"]
    return next((r for r in rows if r["subject"] == subject), None)


@pytest.fixture
def publish(admin_api: ApiClient):
    """publish(starts, ends, **over) -> the listed announcement; all of them are deleted afterwards."""
    created: list[int] = []

    def _publish(starts: datetime, ends: datetime, **over) -> dict:
        subject = f"AUTO announcement {data.unique_suffix()}"
        response = admin_api.post(ANNOUNCEMENTS, json=_body(subject, starts, ends, **over))
        assert response.status == 201, response.text()[:300]
        row = _listed(admin_api, subject)
        assert row, "The announcement was created but is not listed"
        created.append(row["id"])
        return row

    yield _publish
    for announcement_id in created:
        admin_api.delete(f"{ANNOUNCEMENTS}/{announcement_id}")


NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


@pytest.mark.parametrize(
    "starts_in, ends_in, status",
    [(timedelta(days=30), timedelta(days=31), "scheduled"), (-timedelta(minutes=5), timedelta(minutes=10), "active")],
    ids=["before-the-window", "inside-the-window"],
)
def test_status_follows_the_window(publish, starts_in: timedelta, ends_in: timedelta, status: str) -> None:
    row = publish(NOW() + starts_in, NOW() + ends_in)

    assert row["status"] == status
    assert row["recipient_types"] == ["rto_inspector"] and row["priority"] == "information"


def test_a_switched_off_announcement_is_inactive_and_can_be_switched_on_again(admin_api: ApiClient, publish) -> None:
    row = publish(NOW() + timedelta(days=30), NOW() + timedelta(days=31))
    url = f"{ANNOUNCEMENTS}/{row['id']}/status"

    assert admin_api.patch(url, json={"status": "inactive"}).status == 200
    assert _listed(admin_api, row["subject"])["status"] == "inactive"

    assert admin_api.patch(url, json={"status": "active"}).status == 200
    assert _listed(admin_api, row["subject"])["status"] == "scheduled"


@pytest.mark.parametrize("priority", ["information", "warning", "critical"])
def test_every_importance_level_is_accepted(publish, priority: str) -> None:
    assert publish(NOW() + timedelta(days=30), NOW() + timedelta(days=31), priority=priority)["priority"] == priority


@pytest.mark.parametrize(
    "over, field",
    [
        ({"priority": "urgent"}, "priority"),
        ({"recipient_types": ["martians"]}, "recipient_types.0"),
        ({"subject": ""}, "subject"),
        ({"ends_at": _stamp(NOW() + timedelta(days=29))}, "ends_at"),
    ],
    ids=["unknown-importance", "unknown-audience", "no-subject", "ends-before-it-starts"],
)
def test_an_invalid_announcement_is_refused(admin_api: ApiClient, over: dict, field: str) -> None:
    body = {**_body("AUTO announcement never", NOW() + timedelta(days=30), NOW() + timedelta(days=31)), **over}

    response = admin_api.post(ANNOUNCEMENTS, json=body)

    assert response.status == 422 and field in response.json()["errors"], response.text()[:300]
    assert _listed(admin_api, body["subject"]) is None
