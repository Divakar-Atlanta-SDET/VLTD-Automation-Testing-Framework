"""
Fitment Centre Operations: Live Tracking, Geofences, Trip Playback, Alerts, Command Center.

Today's exploration (`specs/fitment-centre-test-plan.md`) found these to be the same screens as the OEM panel's
(`pages/oem_panel/tracking.py`, `command_center.py`) - same headings, same DOM - so this reuses the OEM page objects
through thin FC subclasses (`pages/fc_panel/tracking.py`) and the OEM suite's own `load_problems` / `menu_routes`
helpers, rather than re-discovering the structure. It does NOT reuse OEM test *assertions* about data, since this
FC account's jurisdiction (vehicles it has fitted) is its own.

  smoke        every Operations menu page loads without a 401/403/5xx or a visible load-error message
  jurisdiction the vehicle list this FC sees is exactly the vehicles behind its own installations
  BUG-078      Live Tracking / Geofences / Trip Playback / Alerts call State-Admin-only filter endpoints -> 403
  BUG-082      neither this FC nor its OEM can see the position of a device this FC itself installed
"""

import pytest
from playwright.sync_api import Page, expect

from pages.fc_panel.command_center import FcCommandCenterPage
from pages.fc_panel.tracking import FcAlertsPage, FcGeofencesPage, FcLiveTrackingPage, FcTripPlaybackPage
from utils.api_client import ApiClient
from utils.fc_panel_api import INSTALLATIONS, TRACKING_VEHICLES
from utils.oem_panel_api import GO_ORIGIN
from utils.page_health import load_problems, menu_routes

pytestmark = [pytest.mark.fc_panel]

# The Operations submenu (today's scope only - Management/Installation/Reports/Helpdesk are separate modules).
# All but Command Center are known to fail for the FC role (BUG-078: the same State-Admin-only filter endpoints
# the OEM panel hits as BUG-040). Tested separately, below, as a documented regression rather than silently skipped.
PAGE_CLASSES = [FcLiveTrackingPage, FcGeofencesPage, FcTripPlaybackPage, FcAlertsPage, FcCommandCenterPage]
KNOWN_BAD = {FcLiveTrackingPage, FcGeofencesPage, FcTripPlaybackPage, FcAlertsPage}


def test_operations_submenu_matches_todays_discovered_scope(fc_page: Page) -> None:
    routes = set(menu_routes(fc_page, "/fc/"))
    expected = {cls.PATH for cls in PAGE_CLASSES}
    assert expected <= routes, f"Expected Operations routes missing from the nav: {expected - routes}"


# ── smoke: every Operations page loads cleanly (except the known, tracked exceptions) ───

def test_every_fc_operations_page_loads_cleanly(fc_page: Page) -> None:
    healthy = [cls for cls in PAGE_CLASSES if cls not in KNOWN_BAD]

    broken = {cls.PATH: problems[:3] for cls in healthy if (problems := load_problems(fc_page, cls.PATH))}

    assert not broken, f"Pages that load with failures: {broken}"


def test_command_center_opens_with_its_own_heading(fc_page: Page) -> None:
    """The one Operations page with no known issue: a typed-POM check beyond the generic smoke sweep above."""
    cc = FcCommandCenterPage(fc_page).open()

    expect(cc.heading).to_be_visible()


@pytest.mark.xfail(
    reason="BUG-078: Live Tracking / Geofences / Trip Playback / Alerts call GET /api/transport-commissioner/rtos "
    "and /oems (and Live Tracking also calls /api/last-position for the FC's own devices - BUG-082), all 403 for "
    "the Fitment Centre role",
    strict=False,
)
@pytest.mark.parametrize("path", [cls.PATH for cls in KNOWN_BAD])
def test_operations_pages_do_not_call_state_admin_endpoints(fc_page: Page, path: str) -> None:
    assert not load_problems(fc_page, path)


# ── jurisdiction: an FC sees exactly the vehicles behind its own installations ──

def test_tracking_vehicles_are_exactly_this_fcs_own_installed_vehicles(fc_api: ApiClient) -> None:
    installations = fc_api.get(f"{INSTALLATIONS}?per_page=100").json()["data"]["data"]
    expected_regs = {i["vehicle"]["vehicle_number"] for i in installations}
    if not expected_regs:
        pytest.skip("This FC has no installations yet")

    vehicles = fc_api.get(f"{TRACKING_VEHICLES}?per_page=100").json()["data"]
    shown = vehicles["data"] if isinstance(vehicles, dict) else vehicles
    shown_regs = {v["vehicle_number"] for v in shown}

    assert shown_regs == expected_regs


# ── BUG-082: neither this FC nor its OEM can see its own device's live position ──

@pytest.mark.xfail(
    reason="BUG-082: GET /api/last-position answers 403 'your role is not permitted to view this vehicle' for "
    "both the FC and OEM roles, even for a device the FC itself installed; only Admin can see it",
    strict=False,
)
def test_fc_can_see_the_last_position_of_its_own_installed_device(fc_api: ApiClient) -> None:
    installations = fc_api.get(f"{INSTALLATIONS}?per_page=1").json()["data"]["data"]
    if not installations:
        pytest.skip("This FC has no installations yet")
    imei = installations[0]["device"]["imei"]

    response = fc_api.get(f"/api/last-position?imei={imei}", origin=GO_ORIGIN)

    assert response.status in (200, 404), response.text()[:200]  # 404 ("no known position") is fine; 403 is the bug
