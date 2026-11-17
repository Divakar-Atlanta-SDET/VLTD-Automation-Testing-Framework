"""Regression checks for Batch 5 of the UI/UX audit (OEM role).

Batch 5 found no OEM-specific defects; it confirmed that UX-001, UX-003 and UX-006 (originally
logged against the Admin role) are shared-component issues that also reproduce for OEM, and
that UX-002 does NOT reproduce for OEM (simpler, non-nested card markup). See ui_ux_bug_report.md.
"""

import pytest
from playwright.sync_api import Page

from utils.accessibility import run_axe_scan

pytestmark = pytest.mark.ui_ux


def _violation_ids(page: Page) -> set[str]:
    return {finding.rule_id for finding in run_axe_scan(page)}


@pytest.mark.xfail(reason="UX-001: the OEM Dashboard's trend charts have no accessible text alternative either", strict=False)
def test_oem_dashboard_charts_have_an_accessible_name(oem_page: Page):
    oem_page.wait_for_load_state("networkidle")
    assert "role-img-alt" not in _violation_ids(oem_page)


def _open_live_tracking(page: Page) -> None:
    # Live Tracking polls continuously, so it never reaches networkidle; a bounded wait is used instead.
    page.goto("/oem/live-tracking")
    page.wait_for_timeout(4000)


@pytest.mark.xfail(reason="UX-003: the OEM Live Tracking map filter icon button has no accessible name either", strict=False)
def test_oem_live_tracking_filter_button_has_an_accessible_name(oem_page: Page):
    _open_live_tracking(oem_page)
    button = oem_page.locator("button.map-toolbar__button").first
    name = button.get_attribute("aria-label") or button.inner_text().strip()
    assert name, "the OEM filter toolbar button has no accessible name"


def test_oem_live_tracking_cards_have_no_nested_interactive_controls(oem_page: Page):
    """UX-002 does NOT reproduce here - OEM's cards use simpler, non-nested markup. Not xfail: this must keep passing."""
    _open_live_tracking(oem_page)
    assert "nested-interactive" not in _violation_ids(oem_page)


@pytest.mark.xfail(
    reason="UX-006: OEM's own Register Fitment Centre form has unlabeled password-visibility toggle buttons",
    strict=False,
)
def test_oem_register_fitment_centre_password_toggle_has_an_accessible_name(oem_page: Page):
    oem_page.goto("/oem/users/fitment-centers")
    oem_page.wait_for_load_state("networkidle")
    oem_page.get_by_role("button", name="Register", exact=False).first.click()
    oem_page.wait_for_timeout(1000)
    assert "button-name" not in _violation_ids(oem_page)


@pytest.mark.xfail(
    reason="UX-006: OEM's own Register Staff form has unlabeled password-visibility toggle buttons", strict=False
)
def test_oem_register_staff_password_toggle_has_an_accessible_name(oem_page: Page):
    oem_page.goto("/oem/users/staff")
    oem_page.wait_for_load_state("networkidle")
    oem_page.get_by_role("button", name="Register Staff").click()
    oem_page.wait_for_timeout(1000)
    assert "button-name" not in _violation_ids(oem_page)
