"""Smaller OEM pages: Device Models (view only), SIM Validity Extension, Fitment Centers, OEM Staff."""

import re

from playwright.sync_api import Locator, expect

from pages.oem_panel.base import OemPanelPage


class OemDeviceModelsPage(OemPanelPage):
    PATH = "/oem/device-models"
    HEADING = "Device Models"

    @property
    def add_model_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Model"))


class SimValidityPage(OemPanelPage):
    PATH = "/oem/operations/sim-validity-extension"
    HEADING = "SIM Validity Extension"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.imei_box = page.get_by_role("textbox", name=re.compile("IMEI"))
        self.fetch_button = page.get_by_role("button", name="Fetch Device", exact=True)

    def fetch(self, imei: str) -> None:
        self.imei_box.fill(imei)
        self.fetch_button.click()


class FitmentCentersPage(OemPanelPage):
    PATH = "/oem/users/fitment-centers"
    HEADING = "Fitment Center Management"


class OemStaffPage(OemPanelPage):
    PATH = "/oem/users/staff"
    HEADING = "OEM Staff"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.register_button = page.get_by_role("button", name="Register Staff", exact=True)
        self.load_error = page.get_by_text(re.compile(r"unable to load|not authori[sz]ed|do not have permission", re.I))
