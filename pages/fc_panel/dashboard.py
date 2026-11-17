"""
Fitment Centre Dashboard (`/fc/dashboard`).

Sections, top to bottom: seven KPI cards (Available Devices, Total Installations, Today's Installations, In Progress,
Pending Approvals, Repaired Devices, Replaced Devices), Live Fleet (Moving / Idle / SOS / Offline, own Refresh
button, refreshes itself every 5 minutes - same widget as the OEM dashboard), Installation Trend (Daily / Weekly /
Monthly / Yearly / Total), Device & Installation Status (a donut of Available / Installed / Faulty devices, plus an
Active / In Progress / In Repair / Replaced installation-lifecycle row), Recent Installations (a table, newest
first) and Pending Work (installation jobs requiring action: Health Check, Panic Test, Document Upload, Activation,
Approval).

Not documented anywhere in the guide (chapter 6 describes the device lifecycle, not this specific screen), so every
check here reconciles what the page shows with `GET /api/dashboard/fitment-centre/summary` and the installation
list, rather than asserting any business rule the guide does not state.

See BUG-081: the summary API has no field for Health Check / Document Upload / Approval, so those three Pending
Work rows can never show a real count - `pending_work()` returns `None` for a row that reads "Count not available
from API" so a test can assert that placeholder explicitly instead of it masquerading as a real zero.
"""

import re

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.fc_panel.base import FcPanelPage

KPI_LABELS = (
    "Available Devices", "Total Installations", "Today's Installations", "In Progress",
    "Pending Approvals", "Repaired Devices", "Replaced Devices",
)
SECTIONS = ("Live Fleet", "Installation Trend", "Device & Installation Status", "Recent Installations", "Pending Work")
PENDING_WORK_ROWS = ("Health Check", "Panic Test", "Document Upload", "Activation", "Approval")
NOT_AVAILABLE = "Count not available from API"


class FcDashboardPage(FcPanelPage):
    PATH = "/fc/dashboard"
    HEADING = "Fitment Centre Dashboard"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.refresh_button = page.get_by_role("button", name="Refresh")  # the Live Fleet refresh

    # ── navigation / waiting ─────────────────────────────────────────────────

    def open(self) -> "FcDashboardPage":
        super().open()
        self.wait_loaded()
        return self

    def wait_loaded(self) -> None:
        expect(self.main).to_contain_text(re.compile(r"Replaced Devices"), timeout=20_000)
        self._settle()

    def _settle(self) -> None:
        try:
            self.page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass

    # ── KPI cards ────────────────────────────────────────────────────────────

    def kpis(self) -> dict[str, int]:
        text = self.main.inner_text()
        out = {}
        for label in KPI_LABELS:
            m = re.search(rf"(\d[\d,]*)\s*{re.escape(label)}", text) or re.search(rf"{re.escape(label)}\s*(\d[\d,]*)", text)
            assert m, f"KPI {label!r} not found on the dashboard"
            out[label] = int(m.group(1).replace(",", ""))
        return out

    def expect_kpis(
        self, *, available_devices: int, total_installations: int, todays_installations: int, in_progress: int,
        pending_approvals: int, repaired_devices: int, replaced_devices: int,
    ) -> None:
        values = {
            "Available Devices": available_devices, "Total Installations": total_installations,
            "Today's Installations": todays_installations, "In Progress": in_progress,
            "Pending Approvals": pending_approvals, "Repaired Devices": repaired_devices, "Replaced Devices": replaced_devices,
        }
        expect(self.main).to_contain_text(re.compile(r"Replaced Devices"), timeout=15_000)
        kpis = self.kpis()
        assert kpis == values, f"KPI mismatch: shown={kpis} expected={values}"

    # ── sections ─────────────────────────────────────────────────────────────

    def section_heading(self, name: str) -> Locator:
        return self.page.get_by_role("heading", name=name, level=2, exact=True)

    def section_text(self, name: str) -> str:
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", self.main.inner_text())
        start = text.index(name)
        following = [text.index(s, start + len(name)) for s in SECTIONS if s != name and s in text[start + len(name):]]
        return text[start:min(following)] if following else text[start:]

    # ── Live Fleet (same shape as the OEM dashboard's) ───────────────────────

    def live_fleet(self) -> dict[str, int]:
        text = self.section_text("Live Fleet")
        return {state: int(re.search(rf"{state}\s*●?\s*(\d+)", text).group(1)) for state in ("Moving", "Idle", "SOS", "Offline")}

    def live_fleet_vehicle_count(self) -> int:
        return int(re.search(r"(\d+)\s+vehicles?", self.section_text("Live Fleet")).group(1))

    # ── Installation Trend ────────────────────────────────────────────────────

    def select_trend_period(self, period: str) -> None:
        self.page.get_by_role("button", name=period, exact=True).click()

    def trend_totals(self) -> dict[str, int]:
        text = self.section_text("Installation Trend")
        return {
            "total": int(re.search(r"Total\s*(\d+)", text).group(1)),
            "average": int(re.search(r"Average\s*(\d+)", text).group(1)),
            "highest": int(re.search(r"Highest\s*(\d+)", text).group(1)),
        }

    # ── Device & Installation Status ─────────────────────────────────────────

    def device_status(self) -> dict[str, int]:
        text = self.section_text("Device & Installation Status")
        return {
            "Available": int(re.search(r"Available\s*(\d+)", text).group(1)),
            "Installed": int(re.search(r"Installed\s*(\d+)", text).group(1)),
            "Faulty": int(re.search(r"Faulty\s*(\d+)", text).group(1)),
            "Total Devices": int(re.search(r"Total Devices\s*(\d+)", text).group(1)),
        }

    def installation_lifecycle(self) -> dict[str, int]:
        text = self.section_text("Device & Installation Status")
        return {state: int(re.search(rf"{state}\s*(\d+)", text).group(1)) for state in ("Active", "In Progress", "In Repair", "Replaced")}

    # ── Recent Installations ─────────────────────────────────────────────────
    # The table's header cells are not marked up as `columnheader` (0 found - confirmed by inspection) and even
    # render as plain `cell`s like the data rows, so the header row is dropped positionally (it is always first).

    def recent_installations(self) -> list[dict[str, str]]:
        table = self.page.get_by_role("table")
        rows = table.get_by_role("row").filter(has=self.page.get_by_role("cell"))
        out = []
        for row in rows.all()[1:]:
            vehicle, imei, installation, activation, updated = [c.strip() for c in row.get_by_role("cell").all_inner_texts()]
            out.append({"vehicle": vehicle, "imei": imei, "installation": installation, "activation": activation, "updated": updated})
        return out

    def expect_no_recent_installations(self) -> None:
        expect(self.main).to_contain_text("No recent installations")

    # ── Pending Work ──────────────────────────────────────────────────────────

    def pending_work(self) -> dict[str, "int | None"]:
        """{row label: count, or None if the row reads 'Count not available from API' (BUG-081)}."""
        text = self.section_text("Pending Work")
        out: dict[str, int | None] = {}
        for label in PENDING_WORK_ROWS:
            start = text.index(label)
            following = [text.index(s, start + len(label)) for s in PENDING_WORK_ROWS if s != label and s in text[start + len(label):]]
            chunk = text[start:min(following)] if following else text[start:]
            out[label] = None if NOT_AVAILABLE in chunk else int(re.search(r"(?:^|\n)(\d+)\s*$", chunk.strip()).group(1))
        return out
