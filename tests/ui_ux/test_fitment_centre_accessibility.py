"""Regression checks for Batch 7 of the UI/UX audit (Fitment Centre role).

Batch 7 found no FC-specific defects; every issue found is a shared-component bug already
tracked under Admin and/or OEM, now also confirmed on FC (UX-001, UX-003, UX-005, UX-006,
UX-010, UX-011, UX-013), plus a re-confirmed rule-out of UX-002. See ui_ux_bug_report.md.
"""

import pytest
from playwright.sync_api import Page

from utils.accessibility import run_axe_scan

pytestmark = pytest.mark.ui_ux


def _violation_ids(page: Page) -> set[str]:
    return {finding.rule_id for finding in run_axe_scan(page)}


@pytest.mark.xfail(reason="UX-001: the FC Dashboard's trend charts have no accessible text alternative either", strict=False)
def test_fc_dashboard_charts_have_an_accessible_name(fc_page: Page):
    fc_page.wait_for_load_state("networkidle")
    assert "role-img-alt" not in _violation_ids(fc_page)


@pytest.mark.xfail(
    reason="UX-001: FC's Device Models 'Inventory Summary' chart has no accessible text alternative either",
    strict=False,
)
def test_fc_device_models_inventory_chart_has_an_accessible_name(fc_page: Page):
    fc_page.goto("/fc/device-models")
    fc_page.wait_for_load_state("networkidle")
    assert "role-img-alt" not in _violation_ids(fc_page)


def _open_live_tracking(page: Page) -> None:
    # Live Tracking polls continuously, so it never reaches networkidle; a bounded wait is used instead.
    page.goto("/fc/live-tracking")
    page.wait_for_timeout(4000)


@pytest.mark.xfail(reason="UX-003: the FC Live Tracking map filter icon button has no accessible name either", strict=False)
def test_fc_live_tracking_filter_button_has_an_accessible_name(fc_page: Page):
    _open_live_tracking(fc_page)
    button = fc_page.locator("button.map-toolbar__button").first
    name = button.get_attribute("aria-label") or button.inner_text().strip()
    assert name, "the FC filter toolbar button has no accessible name"


def test_fc_live_tracking_cards_have_no_nested_interactive_controls(fc_page: Page):
    """UX-002 does NOT reproduce here either - FC's cards use simpler, non-nested markup. Not xfail: must keep passing."""
    _open_live_tracking(fc_page)
    assert "nested-interactive" not in _violation_ids(fc_page)


@pytest.mark.xfail(
    reason="UX-006: FC's own Change Password form has unlabeled password-visibility toggle buttons", strict=False
)
def test_fc_change_password_toggle_has_an_accessible_name(fc_page: Page):
    fc_page.goto("/fc/profile")
    fc_page.wait_for_load_state("networkidle")
    fc_page.get_by_text("Change Password", exact=False).first.click()
    fc_page.wait_for_timeout(1000)
    assert "button-name" not in _violation_ids(fc_page)


@pytest.mark.parametrize(
    "path",
    ["/fc/reports/alerts", "/fc/reports/alerts/vehicle-trail", "/fc/reports/device-health",
     "/fc/reports/installation-status"],
)
@pytest.mark.xfail(reason="UX-010: FC's shared date-range filter has no accessible name either", strict=False)
def test_fc_report_date_filter_has_a_label(fc_page: Page, path: str):
    fc_page.goto(path)
    fc_page.wait_for_load_state("networkidle")
    assert "label" not in _violation_ids(fc_page)


@pytest.mark.xfail(reason="UX-010: FC's Installation History date filter has no accessible name either", strict=False)
def test_fc_installation_history_date_filter_has_a_label(fc_page: Page):
    fc_page.goto("/fc/installation-history")
    fc_page.wait_for_load_state("networkidle")
    assert "label" not in _violation_ids(fc_page)


@pytest.mark.xfail(reason="UX-011: FC's Device Packets report has a nested-interactive date-picker too", strict=False)
def test_fc_device_packets_date_picker_has_no_nested_interactive_controls(fc_page: Page):
    fc_page.goto("/fc/reports/device-packets")
    fc_page.wait_for_load_state("networkidle")
    assert "nested-interactive" not in _violation_ids(fc_page)


@pytest.mark.xfail(
    reason="UX-013: FC's Installation Status report table wrapper isn't keyboard-focusable either", strict=False
)
def test_fc_installation_status_table_is_keyboard_focusable(fc_page: Page):
    fc_page.goto("/fc/reports/installation-status")
    fc_page.wait_for_load_state("networkidle")
    assert "scrollable-region-focusable" not in _violation_ids(fc_page)
