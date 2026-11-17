"""
Fitment Centre Reports (`/fc/reports/*`, `/fc/set-history`, `/fc/watch-history`).

13 report pages, discovered by today's nav sweep (see `specs/fitment-centre-test-plan.md`). Most are smoke-tested
only, directly in the test file (goto + heading check): several (Device Packets, Alert Report, SIM Validity,
Permit Holder Devices, Vehicle Mappings) depend on real device telemetry or watchlists this environment does not
have yet, the same root cause as BUG-080, so an empty report here is expected, not a defect to assert on.

Two pages get deeper treatment:
  Installation Report    the one report with real, known data (the FC's 7 real installations) - reconciled against
                          `GET /api/installation`. Confirmed 2026-11-05: it defaults to today's date only, so the
                          installations (created 2026-11-04) don't show without widening the date range - not a
                          bug, just a filter default to account for.
  Device Inventory Report  crashes outright (BUG-084) - `set_date_range` is not needed there.
"""

import re

from pages.fc_panel.base import FcPanelPage


class FcInstallationReportPage(FcPanelPage):
    PATH = "/fc/reports/installation-status"
    HEADING = "Installation Report"

    # Unlike several other FC reports (Alert Report, Device Health, Device Status: "Export Excel"; Repair History:
    # "Export CSV"), this one has no export control at all - confirmed 2026-11-05, not assumed to be a bug (export
    # availability is inconsistent across FC reports generally, not specific to this one; see the test plan).

    def set_date_range(self, date_from: str, date_to: str) -> None:
        """`date_from`/`date_to` as 'YYYY-MM-DD'; widens the report beyond its today-only default."""
        dates = self.page.locator("input[type=date]")
        dates.first.fill(date_from)
        dates.last.fill(date_to)
        self.page.wait_for_load_state("networkidle")

    def counters(self) -> dict[str, int]:
        text = self.main.inner_text()
        labels = ("Total Installations", "Active", "In Progress", "In Repair")
        values = {}
        for label in labels:
            match = re.search(rf"{label}\s*\n+\s*(\d+)", text, re.I)
            values[label] = int(match.group(1)) if match else None
        return values


class FcDeviceInventoryReportPage(FcPanelPage):
    PATH = "/fc/reports/device-inventory"
    HEADING = "Device Inventory Report"
