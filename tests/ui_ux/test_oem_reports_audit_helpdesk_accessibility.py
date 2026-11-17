"""Regression checks for confirmed UI/UX and accessibility findings on OEM Reports,
Audit, and Helpdesk (Batch 6 of the UI/UX audit). See ui_ux_bug_report.md for full
repro steps and evidence. UX-010/011/013 were first found under Admin (Batch 4) and
confirmed here to also reproduce under OEM; UX-015 is OEM/Audit-specific.
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
        "/oem/reports/alerts",
        "/oem/reports/alerts/vehicle-trail",
        "/oem/reports/device-health",
        "/oem/reports/installation-status",
        "/oem/reports/oem-performance",
    ],
)
@pytest.mark.xfail(
    reason="UX-010: the shared date-range filter has no accessible name (also reproduces on OEM reports)",
    strict=False,
)
def test_oem_report_date_range_inputs_have_an_accessible_name(oem_page: Page, path: str):
    oem_page.goto(path)
    oem_page.wait_for_load_state("networkidle")
    assert "label" not in _violation_ids(oem_page)


@pytest.mark.xfail(
    reason="UX-011: Device Packets' custom date-picker trigger nests interactive controls (also on OEM)",
    strict=False,
)
def test_oem_device_packets_date_picker_has_no_nested_interactive_controls(oem_page: Page):
    oem_page.goto("/oem/reports/device-packets")
    oem_page.wait_for_load_state("networkidle")
    assert "nested-interactive" not in _violation_ids(oem_page)


@pytest.mark.parametrize("path", ["/oem/reports/device-installations", "/oem/reports/installation-status"])
@pytest.mark.xfail(
    reason="UX-013: the report table's scrollable wrapper is not keyboard-focusable (also on OEM)", strict=False
)
def test_oem_report_table_wrapper_is_keyboard_focusable(oem_page: Page, path: str):
    oem_page.goto(path)
    oem_page.wait_for_load_state("networkidle")
    assert "scrollable-region-focusable" not in _violation_ids(oem_page)


@pytest.mark.xfail(
    reason="UX-015: the Ticket Performance Report's attachment download link has no accessible name",
    strict=False,
)
def test_ticket_performance_attachment_links_have_an_accessible_name(oem_page: Page):
    oem_page.goto("/oem/audit-reports/ticket-performance")
    oem_page.wait_for_load_state("networkidle")
    assert "link-name" not in _violation_ids(oem_page)
