"""OEM Device Details (`/oem/devices`) and Device Registration (`/oem/devices/new`)."""

import re
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage


class DeviceListPage(OemPanelPage):
    PATH = "/oem/devices"
    HEADING = "Device Details"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.search_box = page.get_by_placeholder("Search by IMEI...")
        self.add_button = page.get_by_role("button", name="Add Device", exact=True)
        self.bulk_upload_button = page.get_by_role("button", name="Bulk Upload", exact=True)

    def search(self, imei: str) -> None:
        self.search_box.fill(imei)
        self.main.get_by_role("button", name="Search", exact=True).click()

    def expect_device(self, imei: str, *cell_texts: str) -> None:
        """The searched device is listed exactly once and its row shows every given text."""
        row = self.row_with(imei)
        expect(row).to_have_count(1)
        for text in cell_texts:
            expect(row).to_contain_text(text)

    def expect_no_device(self, imei: str) -> None:
        expect(self.row_with(imei)).to_have_count(0)

    # filters: nothing is sent until Search is pressed (choosing a model or status alone does not filter)
    @property
    def search_button(self) -> Locator:
        return self.main.get_by_role("button", name="Search", exact=True)

    @property
    def clear_button(self) -> Locator:
        return self.main.get_by_role("button", name="Clear Filter", exact=True)

    @property
    def empty_state(self) -> Locator:
        return self.main.get_by_role("cell", name="No Devices Found")

    def choose_filter(self, position: int, option: str) -> None:
        """position 0 = Model, 1 = Inventory Status; the filter applies when Search is pressed."""
        self.main.get_by_role("combobox").nth(position).click()
        self.page.locator("[role=option]:visible").filter(has_text=re.compile(rf"^\s*{re.escape(option)}\s*$")).click()

    def apply_filters(self) -> None:
        with self.page.expect_response(lambda r: "/api/devices?" in r.url):
            self.search_button.click()

    def imeis(self) -> list[str]:
        """The IMEI of every row shown, in order."""
        rows = [re.sub(r"\s+", " ", text) for text in self.page.get_by_role("row").all_inner_texts()[1:]]
        return [match.group(0) for row in rows if (match := re.search(r"(?<!\d)\d{15}(?!\d)", row))]

    # paging: First page / Previous page / Go to page N / Next page / Last page and "Showing 1 to 10 of 12 results"
    @property
    def pager_summary(self) -> Locator:
        return self.page.get_by_text(re.compile(r"Showing\s+\d+\s+to\s+\d+\s+of\s+\d+\s+results"))

    def pager_button(self, name: str) -> Locator:
        return self.page.get_by_role("button", name=name, exact=True)

    def go_to(self, button: str) -> None:
        with self.page.expect_response(lambda r: "/api/devices?" in r.url):
            self.pager_button(button).click()

    # row menu: View Device / Edit Device / Delete Device
    def row_menu(self, imei: str) -> list[str]:
        self.row_with(imei).get_by_role("button", name="Open actions").click()
        items = [item.strip() for item in self.page.get_by_role("menuitem").all_text_contents()]
        self.page.keyboard.press("Escape")
        return items

    def choose_row_action(self, imei: str, action: str) -> None:
        self.row_with(imei).get_by_role("button", name="Open actions").click()
        self.page.get_by_role("menuitem", name=action, exact=True).click()

    def view_dialog(self) -> Locator:
        """The View Device overlay (a plain overlay without a dialog role): found by its subtitle."""
        return self.page.locator("div.fixed").filter(has_text="View registered VLTD device information")

    def delete_question(self, imei: str) -> Locator:
        return self.page.get_by_text(f'Are you sure you want to delete device "{imei}"?')

    def bulk_upload(self) -> "BulkUploadDialog":
        self.bulk_upload_button.click()
        return BulkUploadDialog(self.page).wait_until_open()


class BulkUploadDialog:
    """The Bulk Upload dialog of Device Details: Download Sample, Choose File (.xlsx / .xls, up to 10,000 devices), Cancel, Upload."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.title = page.get_by_text("Bulk Upload Devices", exact=True)
        self.file_input = page.locator("input[type=file]")
        self.sample_button = page.get_by_role("button", name="Download Sample", exact=True)
        self.upload_button = page.get_by_role("button", name="Upload", exact=True)
        self.cancel_button = page.get_by_role("button", name="Cancel", exact=True)

    def wait_until_open(self) -> "BulkUploadDialog":
        expect(self.title).to_be_visible()
        return self

    def download_sample(self, directory: Path) -> Path:
        with self.page.expect_download() as download:
            self.sample_button.click()
        path = Path(directory) / download.value.suggested_filename
        download.value.save_as(path)
        return path

    def choose(self, path: Path) -> None:
        self.file_input.set_input_files(path)
        expect(self.page.get_by_text(f"Selected: {Path(path).name}")).to_be_visible()

    def upload(self) -> None:
        self.upload_button.click()


class DeviceFormPage(OemPanelPage):
    PATH = "/oem/devices/new"
    HEADING = re.compile(r"Device Registration", re.I)
    HEADING_LEVEL = None

    def __init__(self, page) -> None:
        super().__init__(page)
        self.model = page.get_by_label("Device Model", exact=False)
        self.firmware = page.get_by_label("Firmware", exact=False)
        self.sim_module = page.get_by_label("SIM Module", exact=False)
        self.slot_id = page.get_by_placeholder("Enter Slot ID")
        self.imei = page.get_by_placeholder("Enter 15-digit IMEI")
        self.serial_number = page.get_by_placeholder("Enter Serial Number")
        self.primary_mobile = page.get_by_placeholder("Enter Primary Mobile Number")
        self.secondary_mobile = page.get_by_placeholder("Enter Secondary Mobile Number")
        self.iccid = page.get_by_placeholder("Enter SIM ICCID")
        self.valid_till = page.get_by_label("Valid Till", exact=False)
        self.submit_button = page.get_by_role("button", name="Add Device", exact=True)

    def fill_device(self, *, model: str, firmware: str, sim_module: str, imei: str, serial: str,
                    primary: str, secondary: str, iccid: str, valid_till: str) -> None:
        self.model.select_option(label=model)
        expect(self.firmware.locator("option", has_text=firmware)).to_have_count(1)  # the list loads after the model is chosen
        self.firmware.select_option(label=firmware)
        self.sim_module.select_option(label=sim_module)
        self.imei.fill(imei)
        self.serial_number.fill(serial)
        self.primary_mobile.fill(primary)
        self.secondary_mobile.fill(secondary)
        self.iccid.fill(iccid)
        self.valid_till.fill(valid_till)

    def firmware_options(self) -> list[str]:
        return [o.strip() for o in self.firmware.locator("option").all_inner_texts() if o.strip()]

    def submit(self) -> None:
        self.submit_button.click()


class DeviceEditPage(DeviceFormPage):
    """`/oem/devices/{id}/edit`: model, firmware, SIM module, slot, IMEI and serial number can change; the SIM details are read-only."""

    HEADING = "Edit Device"

    def __init__(self, page, device_id: int) -> None:
        super().__init__(page)
        self.PATH = f"/oem/devices/{device_id}/edit"
        self.submit_button = page.get_by_role("button", name="Update Device", exact=True)

    def open(self) -> "DeviceEditPage":
        super().open()
        expect(self.imei).not_to_have_value("")  # the stored values are filled in after the page appears
        return self
