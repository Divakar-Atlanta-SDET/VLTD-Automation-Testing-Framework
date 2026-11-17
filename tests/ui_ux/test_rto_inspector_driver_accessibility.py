"""Regression checks for confirmed UI/UX and accessibility findings on RTO Officer, RTO
Inspector and Driver (Batch 8, the final batch of the UI/UX audit). See ui_ux_bug_report.md
for full repro steps and evidence.
"""

import pytest
from playwright.sync_api import Page

from utils.accessibility import run_axe_scan

pytestmark = pytest.mark.ui_ux


def _violation_ids(page: Page) -> set[str]:
    return {finding.rule_id for finding in run_axe_scan(page)}


@pytest.mark.xfail(reason="UX-001: the RTO Dashboard's trend chart has no accessible text alternative", strict=False)
def test_rto_dashboard_chart_has_an_accessible_name(rto_page: Page):
    rto_page.wait_for_load_state("networkidle")
    rto_page.wait_for_timeout(500)  # the chart canvas mounts just after networkidle fires
    assert "role-img-alt" not in _violation_ids(rto_page)


@pytest.mark.xfail(reason="UX-001: the Inspector Dashboard's chart has no accessible text alternative", strict=False)
def test_inspector_dashboard_chart_has_an_accessible_name(inspector_page: Page):
    inspector_page.wait_for_load_state("networkidle")
    assert "role-img-alt" not in _violation_ids(inspector_page)


@pytest.mark.xfail(
    reason="UX-003: the RTO Live Tracking map filter icon button has no accessible name", strict=False
)
def test_rto_live_tracking_filter_button_has_an_accessible_name(rto_page: Page):
    rto_page.goto("/rto/live-tracking")
    rto_page.wait_for_load_state("networkidle")
    assert "button-name" not in _violation_ids(rto_page)


@pytest.mark.xfail(
    reason="UX-006: RTO's Change Password form has unlabeled password-visibility toggle buttons", strict=False
)
def test_rto_change_password_toggle_buttons_have_an_accessible_name(rto_page: Page):
    rto_page.goto("/rto/profile")
    rto_page.get_by_role("tab", name="Change Password").click()
    rto_page.wait_for_timeout(500)
    assert "button-name" not in _violation_ids(rto_page)


@pytest.mark.xfail(
    reason="UX-006: Inspector's Change Password form has unlabeled password-visibility toggle buttons",
    strict=False,
)
def test_inspector_change_password_toggle_buttons_have_an_accessible_name(inspector_page: Page):
    inspector_page.goto("/inspector/profile")
    inspector_page.get_by_role("tab", name="Change Password").click()
    inspector_page.wait_for_timeout(500)
    assert "button-name" not in _violation_ids(inspector_page)


@pytest.mark.xfail(
    reason="UX-006: Driver's Change Password form has unlabeled password-visibility toggle buttons", strict=False
)
def test_driver_change_password_toggle_buttons_have_an_accessible_name(driver_page: Page):
    driver_page.goto("/driver/profile")
    driver_page.get_by_role("tab", name="Change Password").click()
    driver_page.wait_for_timeout(500)
    assert "button-name" not in _violation_ids(driver_page)


@pytest.mark.xfail(
    reason="UX-010: RTO's Approval History page has an unlabeled date-range filter", strict=False
)
def test_rto_approval_history_date_filter_has_an_accessible_name(rto_page: Page):
    rto_page.goto("/rto/audit/approval-history")
    rto_page.wait_for_timeout(1500)
    assert "label" not in _violation_ids(rto_page)


@pytest.mark.xfail(
    reason="UX-011: RTO's Device Packets report has a nested-interactive date-picker", strict=False
)
def test_rto_device_packets_report_has_no_nested_interactive_controls(rto_page: Page):
    rto_page.goto("/rto/reports/device-packets")
    rto_page.wait_for_timeout(1500)
    assert "nested-interactive" not in _violation_ids(rto_page)


@pytest.mark.xfail(
    reason="UX-013: RTO's Device Health report's scrollable table wrapper is not keyboard-focusable",
    strict=False,
)
def test_rto_device_health_report_scroll_wrapper_is_keyboard_focusable(rto_page: Page):
    rto_page.goto("/rto/reports/device-health")
    rto_page.wait_for_timeout(1500)
    assert "scrollable-region-focusable" not in _violation_ids(rto_page)


@pytest.mark.xfail(
    reason="UX-016: Draft Challan's evidence-upload file input has no accessible name", strict=False
)
def test_draft_challan_file_input_has_an_accessible_name(inspector_page: Page):
    inspector_page.goto("/inspector/challans/create")
    inspector_page.wait_for_timeout(1500)
    assert "label" not in _violation_ids(inspector_page)


@pytest.mark.xfail(
    reason="UX-017: Driver Dashboard's icon-prefixed info list breaks the dl/dt/dd structure", strict=False
)
def test_driver_dashboard_info_list_has_a_valid_definition_list_structure(driver_page: Page):
    driver_page.wait_for_load_state("networkidle")
    assert "definition-list" not in _violation_ids(driver_page)
