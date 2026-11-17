"""
Helpers for mocking the dashboard back-end responses in UI tests.

Dashboard endpoint: GET /api/transport-commissioner/dashboard  -> {"data": {...}}
Live Fleet endpoint: GET /alert/api/fleet/summary               -> {"data": {...}}
"""

import json
from typing import Any, Callable

from playwright.sync_api import Page, Route

DASHBOARD_ROUTE = "**/transport-commissioner/dashboard*"
FLEET_ROUTE = "**/fleet/summary*"


def zeroed(value: Any) -> Any:
    """Recursively replace every number with 0 (keeps structure and strings)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return 0
    if isinstance(value, list):
        return [zeroed(v) for v in value]
    if isinstance(value, dict):
        return {k: zeroed(v) for k, v in value.items()}
    return value


def _fulfil(payload: Any, status: int) -> Callable[[Route], None]:
    if status == 200:
        body = json.dumps({"data": payload})
    else:
        body = json.dumps({"message": "mocked failure"})

    def handler(route: Route) -> None:
        route.fulfill(status=status, content_type="application/json", body=body)

    return handler


def mock_dashboard_api(page: Page, payload: dict | None = None, status: int = 200) -> None:
    """Answer every dashboard API call with `payload` (or an error `status`)."""
    page.route(DASHBOARD_ROUTE, _fulfil(payload, status))


def mock_fleet_api(page: Page, payload: dict | None = None, status: int = 200) -> None:
    """Answer every fleet-summary call with `payload` (or an error `status`)."""
    page.route(FLEET_ROUTE, _fulfil(payload, status))
