"""
Mocked back-end answers for the OEM dashboard tests (empty account, null values, server error, slow request).

Each call to the dashboard's data endpoints is routed to a canned JSON body, so these tests do not depend on what the
shared environment holds. Install the routes BEFORE opening the dashboard.
"""

import json
import re

from playwright.sync_api import Page

INVENTORY = r".*/api/dashboard/oem/device-inventory"
ALLOCATION_SUMMARY = r".*/api/dashboard/oem/allocation-summary"
FITMENT_SUMMARY = r".*/api/dashboard/oem/fitment-summary"
DEVICES = r".*/api/devices\?page=1&per_page=5"
ALLOCATIONS = r".*/api/device-allocations\?.*date_from"
REPAIRS = r".*/api/device-repairs"
TICKETS = r".*/api/helpdesk/tickets/performance"
VEHICLE_SUMMARY = r".*/api/tracking/vehicles/summary"

EMPTY_LIST = {"success": True, "data": [], "meta": {"pagination": {"current_page": 1, "per_page": 5, "total": 0, "last_page": 1, "has_more": False}}}
ZERO_INVENTORY = {"total_devices": 0, "available_devices": 0, "allocated_devices": 0, "installed_devices": 0, "faulty_devices": 0}


def mock_json(page: Page, pattern: str, body, status: int = 200) -> None:
    page.route(re.compile(pattern), lambda route: route.fulfill(status=status, content_type="application/json", body=json.dumps(body)))


def mock_empty_account(page: Page) -> None:
    """An OEM with no devices, allocations, repairs, tickets or vehicles."""
    mock_json(page, INVENTORY, {"success": True, "data": ZERO_INVENTORY})
    mock_json(page, ALLOCATION_SUMMARY, {"success": True, "data": {"total_allocations": 0, "active_allocations": 0, "allocated_devices": 0, "returned_allocations": 0}})
    mock_json(page, FITMENT_SUMMARY, {"success": True, "data": []})
    mock_json(page, DEVICES, EMPTY_LIST)
    mock_json(page, ALLOCATIONS, EMPTY_LIST)
    mock_json(page, REPAIRS, EMPTY_LIST)
    mock_json(page, TICKETS, {"status": True, "message": "ok", "data": []})
    mock_json(page, VEHICLE_SUMMARY, {"data": {"moving": 0, "idle": 0, "sos": 0, "offline": 0}})


def hold_requests(page: Page, pattern: str) -> list:
    """Keep requests matching `pattern` pending; returns the list of held routes (call `.continue_()` on them to release)."""
    held: list = []
    page.route(re.compile(pattern), lambda route: held.append(route))
    return held
