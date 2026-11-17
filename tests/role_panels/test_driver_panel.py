"""
Driver panel, through the screen and the API.

Per `VLTD_How_It_Works.pdf` chapter 17.3, a Driver's duties come from the timetables a SCHOOL builds (vehicle +
mapped driver + route + weekdays). This environment has no School account that has mapped the dedicated Driver
test account to a vehicle or timetable, so "No duty assigned" / "No vehicle assigned" / "No Future Duties" are
the genuinely correct, expected empty states here - not a defect. These tests confirm that empty state is real
(matches the API) rather than a stuck/broken loading state, and that the panel's own screens load cleanly.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.role_panels.dashboard import DriverDashboardPage
from utils.api_client import ApiClient
from utils.role_panel_api import DRIVER_DUTY_FUTURE, DRIVER_DUTY_HISTORY, DRIVER_DUTY_TODAY, DRIVER_VEHICLE

pytestmark = [pytest.mark.driver_panel]


def test_login_lands_on_the_driver_dashboard(driver_page: Page) -> None:
    dash = DriverDashboardPage(driver_page).open()
    expect(dash.no_duty_message).to_be_visible()
    expect(dash.my_vehicle_heading).to_be_visible()


def test_no_duty_or_vehicle_is_a_genuine_empty_state_not_a_broken_load(driver_api: ApiClient) -> None:
    """Matches the API directly: there really is no duty/vehicle mapping for this driver (see module docstring)."""
    today = driver_api.get(DRIVER_DUTY_TODAY)
    assert today.status == 200, today.text()[:200]
    assert today.json()["data"]["duty"] is None

    vehicle = driver_api.get(DRIVER_VEHICLE)
    assert vehicle.status == 200, vehicle.text()[:200]
    assert vehicle.json()["data"]["vehicle"] is None


@pytest.mark.parametrize("path", ["/driver/duties/future", "/driver/duties/history"], ids=lambda p: p.rsplit("/", 1)[1])
def test_duties_screens_load_without_crashing_or_a_permission_error(driver_page: Page, path: str) -> None:
    driver_page.goto(path)
    expect(driver_page.get_by_text("Something went wrong")).to_have_count(0)
    expect(driver_page.get_by_text(re.compile(r"not authorized|forbidden", re.I))).to_have_count(0)


def test_future_duties_and_history_are_empty_and_match_the_api(driver_page: Page, driver_api: ApiClient) -> None:
    future_total = driver_api.get(f"{DRIVER_DUTY_FUTURE}?page=1&per_page=1").json()["data"]["total"]
    history_total = driver_api.get(f"{DRIVER_DUTY_HISTORY}?page=1&per_page=1").json()["data"]["total"]
    assert future_total == 0
    assert history_total == 0

    driver_page.goto("/driver/duties/future")
    expect(driver_page.get_by_role("main")).to_contain_text("No Future Duties", timeout=20_000)
    driver_page.goto("/driver/duties/history")
    expect(driver_page.get_by_role("main")).to_contain_text("No Duty History", timeout=20_000)
