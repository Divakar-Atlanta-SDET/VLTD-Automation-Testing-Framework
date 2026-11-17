"""
Minimal dashboard page objects for the Driver, RTO Inspector and RTO Officer panels.

Each is its own distinct panel (confirmed by exploration, see `specs/role-panels-test-plan.md`), not derived
from the OEM/FC panel hierarchy, so these are plain, independent page objects rather than subclasses of
`pages.oem_panel` / `pages.fc_panel`.
"""

import re

from playwright.sync_api import Page, expect


class RtoDashboardPage:
    PATH = "/rto/dashboard"
    HEADING = "RTO Dashboard"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.heading = page.get_by_role("heading", name=self.HEADING, level=1)
        self.pending_approvals_button = page.get_by_role("button", name="Pending Approvals")

    def open(self) -> "RtoDashboardPage":
        self.page.goto(self.PATH)
        expect(self.heading).to_be_visible(timeout=20_000)
        self.page.wait_for_load_state("networkidle")  # the summary tiles populate asynchronously after the heading renders
        return self

    _TILE_VALUE_JS = """(label) => {
        const matches = [...document.querySelectorAll('*')].filter(e => e.textContent.trim() === label);
        for (const el of matches) {
            const text = el.parentElement.textContent.trim();
            if (/\\d/.test(text.replace(label, ''))) return text;
        }
        return matches.length ? matches[matches.length - 1].parentElement.textContent.trim() : null;
    }"""

    def counter(self, label: str) -> int:
        """Read one of the dashboard's summary tiles (e.g. 'Total Installations', 'Pending Approvals')."""
        text = self.page.evaluate(self._TILE_VALUE_JS, label)
        assert text is not None, f"no tile labelled {label!r} found on the dashboard"
        match = re.search(r"(\d[\d,]*)", text.replace(label, "", 1))
        assert match, f"no number found near the '{label}' tile: {text!r}"
        return int(match.group(1).replace(",", ""))


class InspectorDashboardPage:
    PATH = "/inspector/dashboard"
    HEADING = "Inspector Dashboard"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.heading = page.get_by_role("heading", name=self.HEADING, level=1)
        self.no_rto_message = page.get_by_text("No RTOs are currently assigned")

    def open(self) -> "InspectorDashboardPage":
        self.page.goto(self.PATH)
        expect(self.heading).to_be_visible(timeout=20_000)
        self.page.wait_for_load_state("networkidle")  # the summary tiles populate asynchronously after the heading renders
        return self

    _TILE_VALUE_JS = RtoDashboardPage._TILE_VALUE_JS

    def assigned_rtos_count(self) -> int:
        text = self.page.evaluate(self._TILE_VALUE_JS, "Assigned RTOs")
        assert text is not None, "no 'Assigned RTOs' tile found on the Inspector dashboard"
        match = re.search(r"(\d[\d,]*)", text.replace("Assigned RTOs", "", 1))
        assert match, f"no number found near the 'Assigned RTOs' tile: {text!r}"
        return int(match.group(1).replace(",", ""))


class DriverDashboardPage:
    """The Driver Dashboard's own h1 is the signed-in driver's NAME, not a fixed heading, so this page object
    anchors on the stable 'Duties' nav item and the 'My Vehicle' card instead."""

    PATH = "/driver/dashboard"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.duties_menu = page.get_by_role("button", name="Duties")
        self.my_vehicle_heading = page.get_by_text("My Vehicle", exact=True)
        self.no_duty_message = page.get_by_text("No duty assigned")

    def open(self) -> "DriverDashboardPage":
        self.page.goto(self.PATH)
        expect(self.my_vehicle_heading).to_be_visible(timeout=20_000)
        return self
