"""OEM stock allocation: the Allocate Stock wizard and the Device Allocation History."""

import re

from playwright.sync_api import Locator, expect

from pages.oem_panel.base import OemPanelPage


class AllocateStockPage(OemPanelPage):
    """Step 1: district -> active fitment centre card. Step 2: tick available devices -> Allocate."""

    PATH = "/oem/inventory/allocate-stock"
    HEADING = "Allocate Device Stock"

    def select_district(self, district: str) -> None:
        self.choose("District", district)

    def expect_fitment_centre(self, name: str) -> None:
        expect(self.main.get_by_text(name, exact=True)).to_be_visible()

    def select_fitment_centre(self, name: str) -> None:
        self.main.get_by_text(name, exact=True).click()

    def expect_no_fitment_centre(self, name: str) -> None:
        expect(self.main.get_by_text(name, exact=True)).to_have_count(0)

    def continue_to_devices(self) -> None:
        self.main.get_by_role("button", name="Continue", exact=True).click()
        expect(self.main.get_by_text("Available Devices", exact=True)).to_be_visible()

    def device_row(self, imei: str) -> Locator:
        return self.page.get_by_role("row").filter(has_text=imei)

    def select_device(self, imei: str) -> None:
        self.device_row(imei).get_by_role("checkbox").check()

    def allocate(self) -> None:
        self.main.get_by_role("button", name="Allocate", exact=True).click()

    # step 1 / step 2 controls
    @property
    def continue_button(self) -> Locator:
        return self.main.get_by_role("button", name="Continue", exact=True)

    @property
    def allocate_button(self) -> Locator:
        return self.main.get_by_role("button", name="Allocate", exact=True)

    @property
    def available_counter(self) -> Locator:
        """The 'n available device(s)' text above the device list."""
        return self.main.get_by_text(re.compile(r"^\d+ available device"))

    @property
    def search_box(self) -> Locator:
        return self.main.get_by_placeholder("Search by IMEI...")

    @property
    def select_all_box(self) -> Locator:
        return self.page.get_by_role("row").first.get_by_role("checkbox")

    @property
    def selected_counter(self) -> Locator:
        return self.main.get_by_text(re.compile(r"\d+ Selected")).first

    def listed_imeis(self) -> list[str]:
        """The IMEI of every device row listed in step 2."""
        rows = [re.sub(r"\s+", " ", text) for text in self.page.get_by_role("row").all_inner_texts()[1:]]
        return [match.group(0) for row in rows if (match := re.search(r"(?<!\d)\d{15}(?!\d)", row))]

    def start(self, district: str, fitment_centre: str) -> "AllocateStockPage":
        """Open the wizard, choose the district and the centre and continue to the device list."""
        self.open()
        self.select_district(district)
        self.select_fitment_centre(fitment_centre)
        self.continue_to_devices()
        return self


class AllocationHistoryPage(OemPanelPage):
    PATH = "/oem/device-allocations"
    HEADING = "Device Allocation History"

    def filter_status(self, status: str) -> None:
        self.choose("Status", status)

    @property
    def search_box(self) -> Locator:
        return self.main.get_by_placeholder("Fitment center, IMEI, OEM code...")

    @property
    def reset_button(self) -> Locator:
        return self.main.get_by_role("button", name="Reset Filters", exact=True)

    def data_rows(self) -> Locator:
        """The allocation rows (the header row is not counted)."""
        return self.page.get_by_role("row").filter(has=self.page.get_by_role("button", name="View", exact=True))

    def row_for(self, allocation_text: str) -> Locator:
        return self.data_rows().filter(has_text=allocation_text)

    def pager_buttons(self) -> list[str]:
        """Names of the paging buttons on the page (First page, Next page, ...): none when there is no pager."""
        names = [button.get_attribute("aria-label") or "" for button in self.main.get_by_role("button").all()]
        return [name for name in names if re.search(r"page", name, re.I)]

    def rollback(self, row: Locator) -> None:
        row.first.get_by_role("button", name="Rollback").click()
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_contain_text("Rollback allocation?")
        dialog.get_by_role("button", name="Confirm Rollback").click()


class AllocationSuccessPage(OemPanelPage):
    """`/oem/device-allocations/{id}/success`, shown after a successful allocation."""

    HEADING = re.compile(r"Devices Allocated Successfully")

    def allocation_id(self) -> int:
        expect(self.page).to_have_url(re.compile(r"/oem/device-allocations/\d+/success"))
        return int(re.search(r"/device-allocations/(\d+)/", self.page.url).group(1))
