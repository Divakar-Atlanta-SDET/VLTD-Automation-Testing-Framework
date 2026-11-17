"""
Dashboard Page Object Model for the VLTD Transport Commissioner portal.

URL: /tc/dashboard
Data sources (observed):
  - GET /api/transport-commissioner/dashboard?vehicle_class=&fitment_period=&alert_period=&challan_period=
  - GET /alert/api/fleet/summary   (Live Fleet strip)
"""

import re
from playwright.sync_api import Locator, Page, Response, expect


DASHBOARD_API = "transport-commissioner/dashboard"
FLEET_API = "fleet/summary"

KPI_LABELS = (
    "AIS-140 Fitted Vehicles",
    "Active Fitted Vehicles",
    "Inactive Fitted Vehicles",
    "Never Sent Data",
    "Active Alerts",
    "Challans This Month",
)

SECTION_HEADINGS = (
    "Operational Overview",
    "Live Fleet",
    "Network Overview",
    "Top RTOs by Fitments",
    "AIS-140 Fitment Analysis",
    "Alert Monitoring",
    "Challan Analysis",
)

BROKEN_TEXT = re.compile(r"\b(NaN|undefined|null|\[object Object\])\b")


def is_dashboard_api(response: Response) -> bool:
    return DASHBOARD_API in response.url and response.request.method == "GET"


def is_fleet_api(response: Response) -> bool:
    return FLEET_API in response.url and response.request.method == "GET"


def to_int(text: str) -> int:
    """'1,234' -> 1234 (also strips currency symbols/whitespace)."""
    return int(re.sub(r"[^\d]", "", text))


class DashboardPage:
    """Page Object for /tc/dashboard."""

    PATH = "/tc/dashboard"

    def __init__(self, page: Page) -> None:
        self.page = page

        self.heading = page.get_by_role(
            "heading", name="Transport Commissioner Dashboard", level=1
        )
        # Header Refresh is the first one on the page; Live Fleet has its own.
        self.refresh_button = page.get_by_role("button", name="Refresh").first
        self.fleet_refresh_button = page.get_by_role("button", name="Refresh").last
        self.manage_announcements_button = page.get_by_role(
            "button", name="Manage Announcements"
        )
        self.view_all_alerts_button = page.get_by_role("button", name="View All")

        # Selects
        self.vehicle_class_select = page.get_by_role("combobox", name="Vehicle class")
        self.fitment_period_select = page.get_by_role("combobox", name="Fitment period")
        self.alert_metric_select = page.get_by_role("combobox", name="Alert metric")
        self.alert_period_select = page.get_by_role("combobox", name="Alert period")
        self.challan_metric_select = page.get_by_role("combobox", name="Challan metric")
        self.challan_period_select = page.get_by_role("combobox", name="Challan period")

        # Navigation / account
        self.helpdesk_link = page.get_by_role("link", name="Helpdesk")
        self.dashboard_link = page.get_by_role("link", name="Dashboard")
        self.account_button = page.get_by_role("button", name="Delhi Transport Department")
        self.theme_toggle = page.get_by_role("button", name=re.compile(r"Switch to (dark|light) theme"))
        self.open_navigation_button = page.get_by_role("button", name="Open navigation")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def section(self, name: str) -> Locator:
        return self.page.get_by_role("heading", name=name, level=2)

    def card(self, label: str) -> Locator:
        """An <article> tile that starts with `label` followed by its value.

        Matching on "label + number" keeps e.g. the 'SOS' fleet tile apart from
        a Recent Major Alert whose title happens to be 'SOS'.
        """
        # textContent has no whitespace between sibling <p>s, hence `\s*`.
        pattern = re.compile(rf"^\s*{re.escape(label)}\s*[₹\s]*\d")
        return self.page.locator("article").filter(has_text=pattern).first

    def card_value(self, label: str) -> Locator:
        return self.card(label).locator("p").nth(1)

    def card_number(self, label: str) -> int:
        return to_int(self.card_value(label).inner_text())

    def card_description(self, label: str) -> str:
        return self.card(label).locator("p").nth(2).inner_text()

    def network_row(self, entity: str) -> tuple[int, int]:
        """(total, active) for a Network Overview row such as 'OEMs'."""
        lines = [
            ln.strip() for ln in self.card(entity).inner_text().splitlines() if ln.strip()
        ]
        nums = [to_int(ln) for ln in lines if re.fullmatch(r"[\d,]+", ln)]
        return nums[0], nums[1]

    def vehicle_mix_rows(self) -> dict[str, tuple[int, str]]:
        """class label -> (count, percentage text) from the Vehicle Mix legend."""
        rows = {}
        for label in ("Goods Carrier", "Cab / Taxi", "Bus", "Passenger Vehicle", "Other"):
            row = self.page.get_by_title(label, exact=True)
            text = row.locator("xpath=../..").inner_text()
            count = re.search(r"\n\s*([\d,]+)\s*\n", "\n" + text + "\n")
            pct = re.search(r"([\d.]+)%", text)
            rows[label] = (to_int(count.group(1)), pct.group(0))
        return rows

    def subtitle_of(self, heading_name: str) -> Locator:
        """The <p> that sits under an h3 such as 'Fitment Trend'."""
        return self.page.get_by_role("heading", name=heading_name, level=3).locator(
            "xpath=following-sibling::p"
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    def goto(self) -> "DashboardPage":
        self.page.goto(self.PATH)
        return self

    def refresh(self) -> Response:
        """Click the header Refresh and return the dashboard API response."""
        with self.page.expect_response(is_dashboard_api) as info:
            self.refresh_button.click()
        return info.value

    def select_and_wait(self, select: Locator, label: str) -> dict:
        """Choose an option and return the query params of the resulting API call."""
        with self.page.expect_request(
            lambda r: DASHBOARD_API in r.url and r.method == "GET"
        ) as info:
            select.select_option(label=label)
        from urllib.parse import parse_qs, urlparse

        return {k: v[0] for k, v in parse_qs(urlparse(info.value.url).query).items()}

    def open_account_menu(self) -> None:
        self.account_button.click()

    def logout(self) -> None:
        self.open_account_menu()
        self.page.get_by_role("menuitem", name="Logout").click()

    # ── Assertions ────────────────────────────────────────────────────────────

    def expect_loaded(self) -> None:
        expect(self.heading).to_be_visible(timeout=20_000)
        expect(self.section("Operational Overview")).to_be_visible()

    def expect_no_broken_values(self) -> None:
        text = self.page.locator("main").inner_text()
        assert not BROKEN_TEXT.search(text), (
            f"Broken value rendered on dashboard: {BROKEN_TEXT.search(text).group(0)}"
        )
