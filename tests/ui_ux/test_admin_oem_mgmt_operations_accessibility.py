"""Regression checks for confirmed UI/UX findings on Admin OEM Management + Operations
(Batch 3 of the UI/UX audit). See ui_ux_bug_report.md for full repro steps and evidence.

Batch 3's axe-core scans found zero accessibility violations across Device Models, Firmware,
SIM Modules, and all 9 Operations pages (including the 6 PIS Management sub-pages) - so there
is no accessibility regression check to add here, only the one confirmed UI consistency bug.
"""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.ui_ux

PIS_PAGES = {
    "timetables": "New Timetable",
    "stops": "Add Stop",
    "service-patterns": "New Service Pattern",
    "trips": "New Trip",
    "routes": "Add Route",
    "service-calendars": "Create Service Calendar",
}


def _refresh_sits_in_the_header_row(admin_page: Page, create_button_name: str) -> bool:
    """True if 'Refresh' is vertically alongside the page's Create/Add/New button (the header
    row), instead of down in the filter bar with 'Reset' - the layout 4 of 6 PIS pages use.
    """
    create_button = admin_page.get_by_role("button", name=create_button_name, exact=True)
    refresh_button = admin_page.get_by_role("button", name="Refresh", exact=True)
    create_box = create_button.bounding_box()
    refresh_box = refresh_button.bounding_box()
    assert create_box and refresh_box, "could not locate the Create and/or Refresh button"
    return abs(create_box["y"] - refresh_box["y"]) < 15


@pytest.mark.parametrize(
    "slug,create_button_name",
    [
        pytest.param("timetables", "New Timetable"),
        pytest.param("stops", "Add Stop"),
        pytest.param("service-patterns", "New Service Pattern"),
        pytest.param("trips", "New Trip"),
        pytest.param(
            "routes",
            "Add Route",
            marks=pytest.mark.xfail(
                reason="UX-009: Route Management puts 'Refresh' in the header row, unlike 4 of the other 5 PIS pages",
                strict=False,
            ),
        ),
        pytest.param(
            "service-calendars",
            "Create Service Calendar",
            marks=pytest.mark.xfail(
                reason="UX-009: Service Calendar Management puts 'Refresh' in the header row, unlike 4 of the other 5 PIS pages",
                strict=False,
            ),
        ),
    ],
)
def test_refresh_button_is_not_in_the_header_row(admin_page: Page, slug: str, create_button_name: str):
    admin_page.goto(f"/tc/operations/pis-management/{slug}")
    admin_page.wait_for_load_state("networkidle")
    assert not _refresh_sits_in_the_header_row(admin_page, create_button_name), (
        f"'Refresh' sits in the header row on {slug}, unlike the dominant PIS Management layout"
    )
