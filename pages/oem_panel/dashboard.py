"""
OEM Dashboard (`/oem/dashboard`).

Sections, top to bottom: five stock KPI cards, Live Fleet (Moving / Idle / SOS / Offline, own Refresh button, refreshes
itself every 5 minutes), Device Inventory, Allocation Overview, Device Details (5 newest devices), Fitment Centre
Allocations, Allocation Trend (Daily / Weekly / Monthly / Yearly), Device Quality, Raised Tickets, Recent Repairs.

The cards are plain blocks without landmarks, so values are read from the visible text of a section (between its h2 and
the next one) and tables are found by their column headers.
"""

import re

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.oem_panel.base import OemPanelPage

KPI_LABELS = ("Total Devices", "Available Devices", "Allocated Devices", "Installed Devices", "Faulty Devices")
SECTIONS = (
    "Live Fleet", "Device Inventory", "Allocation Overview", "Device Details", "Fitment Centre Allocations",
    "Allocation Trend", "Device Quality", "Raised Tickets", "Recent Repairs",
)
PERIODS = ("Daily", "Weekly", "Monthly", "Yearly")
PERIOD_UNIT = {"Daily": "Day", "Weekly": "Week", "Monthly": "Month", "Yearly": "Year"}

# What each section shows when it has no data (user-visible wording).
EMPTY_MESSAGES = {
    "Device Details": "No devices found",
    "Fitment Centre Allocations": "No allocations found",
    "Allocation Trend": "No allocation data",
    "Device Quality": "No replacement data",
    "Raised Tickets": "No tickets found",
    "Recent Repairs": "No recent repairs",
}


class OemDashboardPage(OemPanelPage):
    PATH = "/oem/dashboard"
    HEADING = "OEM Dashboard"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.refresh_button = page.get_by_role("button", name="Refresh")  # the Live Fleet refresh
        self.announcement = page.get_by_text("Official Notice")

    # ── navigation / waiting ─────────────────────────────────────────────────

    def open(self) -> "OemDashboardPage":
        super().open()
        self.wait_loaded()
        return self

    def wait_loaded(self) -> None:
        """The KPI cards show skeletons until their request answers; wait for the last card's number."""
        expect(self.main).to_contain_text(re.compile(r"Faulty Devices\s*\d"), timeout=20_000)
        self._settle()

    def _settle(self) -> None:
        """The sections load from their own requests; let them finish before anything is read."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass  # a page that keeps polling never goes idle; what has arrived is still read

    # ── KPI cards ────────────────────────────────────────────────────────────

    def kpis(self) -> dict[str, int]:
        text = self.main.inner_text()
        return {label: int(re.search(rf"{label}\s+(\d[\d,]*)", text).group(1).replace(",", "")) for label in KPI_LABELS}

    def expect_kpis(self, *, total: int, available: int, allocated: int, installed: int, faulty: int) -> None:
        self.expect_counters(
            Total_Devices=total, Available_Devices=available, Allocated_Devices=allocated,
            Installed_Devices=installed, Faulty_Devices=faulty,
        )

    # ── sections ─────────────────────────────────────────────────────────────

    def section_heading(self, name: str) -> Locator:
        return self.page.get_by_role("heading", name=name, level=2, exact=True)

    def section_text(self, name: str) -> str:
        """The visible text of one section (from its heading up to the next section's heading)."""
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", self.main.inner_text())
        start = text.index(name)
        following = [text.index(s, start + len(name)) for s in SECTIONS if s != name and s in text[start + len(name):]]
        return text[start:min(following)] if following else text[start:]

    def section_button(self, section: str, button: str) -> Locator:
        """A button that sits in the header of `section` (the innermost block holding both the heading and the button)."""
        return (
            self.main.locator("div")
            .filter(has=self.section_heading(section))
            .filter(has=self.page.get_by_role("button", name=button, exact=True))
            .last.get_by_role("button", name=button, exact=True)
        )

    def expect_empty_state(self, section: str) -> None:
        expect(self.main).to_contain_text(EMPTY_MESSAGES[section])

    # ── Live Fleet ───────────────────────────────────────────────────────────

    def live_fleet(self) -> dict[str, int]:
        text = self.section_text("Live Fleet")
        return {state: int(re.search(rf"{state}\s+(\d+)", text).group(1)) for state in ("Moving", "Idle", "SOS", "Offline")}

    def live_fleet_vehicle_count(self) -> int:
        return int(re.search(r"(\d+)\s+vehicles?", self.section_text("Live Fleet")).group(1))

    def live_fleet_updated(self) -> str:
        return re.search(r"Updated\s+([^\n·]+)", self.section_text("Live Fleet")).group(1).strip()

    # ── Device Inventory / Allocation Overview ───────────────────────────────

    def inventory_chart(self) -> dict[str, int]:
        """{'Inventory': total in the donut, 'Available': n, 'Allocated': n}."""
        text = self.section_text("Device Inventory")
        return {
            "Inventory": int(re.search(r"(\d+)\s+Inventory", text).group(1)),
            "Available": int(re.search(r"Available\s+Ready for allocation\s+(\d+)", text).group(1)),
            "Allocated": int(re.search(r"Allocated\s+Assigned to fitment centres\s+(\d+)", text).group(1)),
        }

    def overview_allocated_devices(self) -> int:
        return int(re.search(r"Devices currently represented as allocated\s+(\d+)", self.section_text("Allocation Overview")).group(1))

    # ── tables ───────────────────────────────────────────────────────────────

    def _table(self, first_header: str) -> Locator:
        return self.page.get_by_role("table").filter(has=self.page.get_by_role("columnheader", name=first_header))

    def recent_devices(self) -> list[dict[str, str]]:
        """Device Details rows: IMEI (with its serial number underneath), model, SIM, firmware, status."""
        rows = self._table("IMEI").get_by_role("row").filter(has=self.page.get_by_role("cell"))
        devices = []
        for row in rows.all():
            imei_cell, model, sim, firmware, status = [c.strip() for c in row.get_by_role("cell").all_inner_texts()]
            imei, _, serial = imei_cell.partition("\n")
            devices.append({"imei": imei.strip(), "serial": serial.strip(), "model": model, "sim": sim, "firmware": firmware, "status": status})
        return devices

    def fitment_centre_rows(self) -> list[dict]:
        """Fitment Centre Allocations rows (a grid, not a table): name, code, allocations, devices allocated, active allocations."""
        lines = [line for line in self.section_text("Fitment Centre Allocations").split("\n") if line.strip()]
        rows = []
        for i, line in enumerate(lines):
            if line == "Allocations" and i >= 3 and lines[i + 2] == "Allocated" and lines[i + 4] == "Active":
                name, code = lines[i - 3], lines[i - 2]
                rows.append({
                    "text": f"{name} {code}", "name": name,
                    "allocations": int(lines[i - 1]), "devices": int(lines[i + 1]), "active": int(lines[i + 3]),
                })
        return rows

    # ── Allocation Trend ─────────────────────────────────────────────────────

    def select_period(self, period: str) -> None:
        """Switch the Allocation Trend to `period` and wait for that period's data (Monthly is already shown on opening)."""
        if f"{period} Average" in self.main.inner_text():
            return
        with self.page.expect_response(re.compile(r"/api/device-allocations\?.*date_from")):
            self.page.get_by_role("button", name=period, exact=True).click()
        expect(self.main).to_contain_text(re.compile(rf"{period} Average\s*[\d.]+"))

    def trend(self) -> dict:
        """The three figures above the chart: total, average (with the period it is per) and the peak."""
        text = self.section_text("Allocation Trend")
        total = int(re.search(r"Total Allocated\s+(\d+)", text).group(1))
        average = re.search(r"(Daily|Weekly|Monthly|Yearly) Average\s+([\d.]+)", text)
        peak = re.search(r"Peak (Day|Week|Month|Year)\s+(\d+)", text)
        return {"total": total, "period": average.group(1), "average": float(average.group(2)), "peak_unit": peak.group(1), "peak": int(peak.group(2))}
