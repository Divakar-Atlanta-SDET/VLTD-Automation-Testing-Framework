"""
OEM Command Center (`/oem/command-center`), three tabs:

  Send Command     search a device by IMEI / serial number, pick a catalogue command (or type a custom one), send it
  Command List     the OEM's command templates (label + exact command text per device model), Add / Edit / Delete
  Command History  what was sent, with status counters and filters (served by the separate command service)
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage


class CommandCenterPage(OemPanelPage):
    PATH = "/oem/command-center"
    HEADING = "Command Center"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.toast = page.locator("[data-sonner-toast]")

    def expect_message(self, text: "str | re.Pattern") -> None:
        expect(self.page.get_by_text(text).first).to_be_visible()


# ── Send Command ──────────────────────────────────────────────────────────────

class CommandSendPage(CommandCenterPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.search_box = page.get_by_role("textbox", name="Vehicle", exact=True)
        self.send_button = page.get_by_role("button", name="Send Command", exact=True).last  # the first one is the tab
        self.catalog_mode = page.get_by_role("button", name="Catalog", exact=True)
        self.custom_mode = page.get_by_role("button", name="Custom", exact=True)
        self.custom_text = page.get_by_role("textbox", name="Raw command text")
        self.catalog = self.main.get_by_role("combobox")

    def search(self, term: str) -> None:
        self.search_box.fill(term)

    def pick_device(self, imei: str) -> None:
        self.main.get_by_text(imei).first.click()
        expect(self.main.get_by_text(re.compile(rf"Recent commands for {imei}"))).to_be_visible()

    def use_custom(self) -> None:
        """Type a custom command. A model without catalogue commands shows the text box directly, without the Catalog / Custom switch."""
        if self.custom_mode.count():
            self.custom_mode.click()
        expect(self.custom_text).to_be_visible()

    def expect_no_results(self) -> None:
        expect(self.main.get_by_text("No results found.")).to_be_visible()

    def catalog_options(self) -> list[str]:
        self.catalog.click()
        options = [o.strip() for o in self.page.locator("[role=option]:visible").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return options

    def choose_catalog_command(self, label: str) -> None:
        self.catalog.click()
        self.page.locator("[role=option]:visible").filter(has_text=label).first.click()

    def send(self) -> None:
        self.send_button.click()


# ── Command List (templates) ──────────────────────────────────────────────────

class CommandListPage(CommandCenterPage):
    PATH = "/oem/command-center?tab=list"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.add_button = page.get_by_role("button", name="Add Command", exact=True)
        self.search_box = page.get_by_placeholder("Search by label...")
        self.form_heading = page.get_by_role("heading", name=re.compile(r"(Add|Edit) Command Template"))
        self.model_select = page.get_by_role("combobox", name="Select device model")
        self.label_box = page.get_by_role("textbox", name="e.g. Battery Status")
        self.purpose_select = page.get_by_role("combobox", name="Purpose")
        self.raw_box = page.get_by_role("textbox", name="Exact device-vendor command text")
        self.description_box = page.get_by_role("textbox", name="What does this command do?")
        self.active_checkbox = page.get_by_role("checkbox", name=re.compile(r"^Active"))

    def open(self) -> "CommandListPage":
        super().open()
        expect(self.add_button).to_be_visible()
        return self

    # table
    def row(self, label: str) -> Locator:
        return self.row_with(label)

    def expect_template(self, label: str, raw_command: str) -> None:
        row = self.row(label)
        expect(row).to_have_count(1)
        expect(row).to_contain_text(raw_command)

    def expect_no_template(self, label: str) -> None:
        expect(self.row(label)).to_have_count(0)

    # filters
    def filter_status(self, status: str) -> None:
        self.choose("Status", status)

    def filter_model(self, model_name: str) -> None:
        self.choose("Device Model", model_name)

    # form
    def start_add(self) -> None:
        self.add_button.click()
        expect(self.form_heading).to_have_text("Add Command Template")

    def fill_form(
        self, label: str, raw_command: str, *, model_name: str | None = None,
        sos_clear: bool = False, description: str | None = None, active: bool = True,
    ) -> None:
        if model_name:
            self.choose("Select device model", re.compile(re.escape(model_name)))
        self.label_box.fill(label)
        self.raw_box.fill(raw_command)
        if description is not None:
            self.description_box.fill(description)
        if sos_clear:
            self.choose("Purpose", re.compile(r"^SOS Clear"))
        self.active_checkbox.set_checked(active)

    def submit(self, button: str = "Create") -> None:
        self.page.get_by_role("button", name=button, exact=True).click()

    def edit(self, label: str) -> None:
        self.row(label).get_by_role("button", name="Edit Command").click()
        expect(self.form_heading).to_have_text("Edit Command Template")

    def delete(self, label: str) -> None:
        self.row(label).get_by_role("button", name="Delete Command").click()

    def confirm_delete(self, label: str) -> None:
        expect(self.page.get_by_text(f'Are you sure you want to delete "{label}"?')).to_be_visible()
        self.page.get_by_role("button", name="Delete", exact=True).click()

    def cancel_delete(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).click()


# ── Command History ───────────────────────────────────────────────────────────

class CommandHistoryPage(CommandCenterPage):
    PATH = "/oem/command-center?tab=history"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.vehicle_box = page.get_by_role("textbox", name="Vehicle / IMEI")
        self.command_box = page.get_by_role("textbox", name="Command", exact=True)
        self.from_date = page.get_by_role("textbox", name="From")
        self.to_date = page.get_by_role("textbox", name="To")
        self.table = page.get_by_role("table", name="Command History")

    def rows(self) -> Locator:
        return self.table.get_by_role("row").filter(has=self.page.get_by_role("cell"))

    def expect_counters(self, *, commands: int, pending: int, acknowledged: int, failed: int) -> None:
        pattern = rf"Commands\s*{commands}\s*Pending \(queued / sent\)\s*{pending}\s*Acknowledged\s*{acknowledged}\s*Failed\s*{failed}(?!\d)"
        expect(self.main).to_contain_text(re.compile(pattern, re.I | re.S), timeout=15_000)

    def filter_status(self, status: str) -> None:
        self.choose("Status", status)

    def filter_sent_by(self, option: str) -> None:
        self.choose("Sent by", option)

    def expect_nothing_sent_yet(self) -> None:
        expect(self.table.get_by_text("No commands sent yet")).to_be_visible()

    def expect_no_match(self) -> None:
        expect(self.table.get_by_text("No commands match these filters")).to_be_visible()
