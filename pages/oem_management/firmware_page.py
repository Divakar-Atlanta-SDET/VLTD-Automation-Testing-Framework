"""Firmware - /tc/oem-management/firmware (+ /new and /{id}/edit)."""

import re

from pages.oem_management.base_oem_page import OemMgmtListPage
from utils.data_generator import FirmwareData


class FirmwarePage(OemMgmtListPage):
    SLUG = "firmware"
    LIST_HEADING = "Firmware"
    ADD_BUTTON = "Add Firmware"
    ADD_HEADING = "Add Firmware"
    EDIT_HEADING = "Edit Firmware"
    SUBMIT_CREATE = "Create Firmware"
    SUBMIT_UPDATE = "Update Firmware"
    TABLE_NAME = "Firmware List"
    VIEW_HEADING = "Firmware Details"
    DELETE_HEADING = "Delete Firmware"
    COLUMNS = ("Sr.No", "OEM", "Device Model", "Part No", "Version", "Release Date", "Update Type", "Status", "Actions")

    def __init__(self, page) -> None:
        super().__init__(page)
        self.update_type_filter = page.get_by_role("combobox", name="Update Type", exact=True)

    def filter_by_update_type(self, update_type: str) -> None:
        self.pick_filter(self.update_type_filter, update_type)

    def choose_device_model(self, model_name: str) -> None:
        self.choose("Device Model *", re.compile(re.escape(model_name)))

    def fill_form(self, firmware: FirmwareData, oem_name: str | None = None, model_name: str | None = None) -> None:
        if oem_name:
            self.choose_oem(oem_name)
        if model_name:
            self.choose_device_model(model_name)
        self.fill("Firmware Version *", firmware.version)
        self.fill("Release Date", firmware.release_date)
        self.page.get_by_role("textbox", name="Enter firmware release notes...").fill(firmware.release_notes)
