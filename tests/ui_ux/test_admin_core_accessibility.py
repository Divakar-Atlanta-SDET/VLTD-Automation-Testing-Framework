"""Regression checks for confirmed UI/UX and accessibility findings on the Admin
Core/Dashboard/Tracking pages (Batch 1 of the UI/UX audit). See ui_ux_bug_report.md
for full repro steps and evidence; these are the stable, automatable subset.
"""

import pytest
from playwright.sync_api import Page

from utils.accessibility import run_axe_scan

pytestmark = pytest.mark.ui_ux


def _violation_ids(page: Page) -> set[str]:
    return {finding.rule_id for finding in run_axe_scan(page)}


@pytest.mark.xfail(reason="UX-001: the 4 Dashboard trend charts have no accessible text alternative", strict=False)
def test_dashboard_charts_have_an_accessible_name(admin_page: Page):
    admin_page.wait_for_load_state("networkidle")
    assert "role-img-alt" not in _violation_ids(admin_page)


@pytest.mark.xfail(
    reason="UX-002: vehicle cards on Live Tracking are buttons with interactive controls nested inside them",
    strict=False,
)
def test_live_tracking_cards_have_no_nested_interactive_controls(admin_page: Page):
    admin_page.goto("/tc/live-tracking")
    admin_page.wait_for_load_state("networkidle")
    assert "nested-interactive" not in _violation_ids(admin_page)


@pytest.mark.xfail(
    reason="UX-003: the Live Tracking map filter icon button has no accessible name", strict=False
)
def test_live_tracking_filter_button_has_an_accessible_name(admin_page: Page):
    admin_page.goto("/tc/live-tracking")
    admin_page.wait_for_load_state("networkidle")
    button = admin_page.locator("button.map-toolbar__button").first
    name = button.get_attribute("aria-label") or button.inner_text().strip()
    assert name, "the filter toolbar button has no accessible name"


@pytest.mark.xfail(
    reason="UX-004: the 'Challans This Month' KPI tile's subtext says 'this year' instead of 'this month'",
    strict=False,
)
def test_dashboard_challans_kpi_subtext_matches_its_own_title(admin_page: Page):
    admin_page.wait_for_load_state("networkidle")
    tile = admin_page.get_by_text("Challans This Month")
    for _ in range(4):
        tile = tile.locator("..")
    subtext = tile.inner_text().lower().split("\n\n")[-1]
    assert "this month" in subtext, f"tile subtext says {subtext!r}, not 'this month'"
