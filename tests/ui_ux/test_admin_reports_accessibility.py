"""Regression checks for confirmed UI/UX and accessibility findings on Admin Reports
(Batch 4 of the UI/UX audit). See ui_ux_bug_report.md for full repro steps and evidence.
"""

import pytest
from playwright.sync_api import Page

from utils.accessibility import run_axe_scan

pytestmark = pytest.mark.ui_ux


def _violation_ids(page: Page) -> set[str]:
    return {finding.rule_id for finding in run_axe_scan(page)}


@pytest.mark.parametrize(
    "path",
    [
        "/tc/reports/ownership-transfers",
        "/tc/reports/account-merges",
        "/tc/reports/device-health",
        "/tc/reports/alerts",
        "/tc/reports/vehicle-alert-trail",
        "/tc/reports/oem-performance",
        "/tc/reports/installation-status",
        "/tc/reports/maintenance",
    ],
)
@pytest.mark.xfail(
    reason="UX-010: the shared date-range filter has no accessible name on 8 of 14 Admin report pages",
    strict=False,
)
def test_report_date_range_inputs_have_an_accessible_name(admin_page: Page, path: str):
    admin_page.goto(path)
    admin_page.wait_for_load_state("networkidle")
    assert "label" not in _violation_ids(admin_page)


@pytest.mark.xfail(
    reason="UX-011: Device Packets' custom date-picker trigger nests interactive controls", strict=False
)
def test_device_packets_date_picker_has_no_nested_interactive_controls(admin_page: Page):
    admin_page.goto("/tc/reports/device-packets")
    admin_page.wait_for_load_state("networkidle")
    assert "nested-interactive" not in _violation_ids(admin_page)


@pytest.mark.xfail(
    reason="UX-012: Multiple-Challan Vehicles' Minimum Challans input and an adjacent button have no accessible name",
    strict=False,
)
def test_multiple_challan_vehicles_filters_have_accessible_names(admin_page: Page):
    admin_page.goto("/tc/reports/multiple-challan-vehicles")
    admin_page.wait_for_load_state("networkidle")
    violations = _violation_ids(admin_page)
    assert "label" not in violations
    assert "button-name" not in violations


@pytest.mark.xfail(
    reason="UX-013: Installation Report's scrollable table wrapper is not keyboard-focusable", strict=False
)
def test_installation_report_table_wrapper_is_keyboard_focusable(admin_page: Page):
    admin_page.goto("/tc/reports/installation-status")
    admin_page.wait_for_load_state("networkidle")
    assert "scrollable-region-focusable" not in _violation_ids(admin_page)


@pytest.mark.xfail(
    reason="UX-014: the filter-reset button is worded 3 different ways across Admin report pages", strict=False
)
def test_filter_reset_button_wording_is_consistent_across_reports(admin_page: Page):
    labels = {}
    for path in ["/tc/reports/ownership-transfers", "/tc/reports/device-status", "/tc/reports/device-validity"]:
        admin_page.goto(path)
        admin_page.wait_for_load_state("networkidle")
        for text in ("Clear filters", "Reset filters", "Reset"):
            button = admin_page.get_by_role("button", name=text, exact=True)
            if button.count():
                labels[path] = text
                break
    assert len(set(labels.values())) == 1, f"inconsistent filter-reset wording across reports: {labels}"
