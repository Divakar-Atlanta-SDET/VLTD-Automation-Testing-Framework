"""Device Models - /tc/oem-management/device-models (+ /new and /{id}/edit)."""

from pathlib import Path

from playwright.sync_api import expect

from pages.oem_management.base_oem_page import OemMgmtListPage
from utils.data_generator import DeviceModelData
from utils.file_utils import TEST_PDF


class DeviceModelsPage(OemMgmtListPage):
    SLUG = "device-models"
    LIST_HEADING = "Device Models"
    ADD_BUTTON = "Add Device Model"
    ADD_HEADING = "Add Device Model"
    EDIT_HEADING = "Edit Device Model"
    SUBMIT_CREATE = "Create Device Model"
    SUBMIT_UPDATE = "Update Device Model"
    TABLE_NAME = "Device Models"
    VIEW_HEADING = "Device Model Details"
    DELETE_HEADING = "Delete Device Model"
    COLUMNS = ("Sr.No", "OEM", "OEM Code", "Model Name", "Part No", "TAC No", "COP No", "Network Profile", "Status", "Actions")

    def fill_form(
        self,
        model: DeviceModelData,
        oem_name: str | None = None,
        certificate: Path | None = TEST_PDF,
    ) -> None:
        """Fill the create form. `oem_name=None` / `certificate=None` leave those fields empty."""
        if oem_name:
            self.choose_oem(oem_name)
        self.fill("Model Name *", model.model_name)
        self.fill("Part Number *", model.part_no)
        self.fill("Network Profile", model.network_profile_name)
        self.page.get_by_role("textbox", name="Enter device model description").fill(model.description)
        self.fill("TAC Number *", model.tac_name)
        self.fill("TAC Issued On *", model.tac_issued_on)
        if certificate is not None:
            self.attach_tac_certificate(certificate)

    def oem_choices(self) -> list[str]:
        """Every OEM the form's dropdown offers (opens the dropdown and waits for its request to finish)."""
        self.page.get_by_role("combobox", name="OEM *", exact=True).click()
        options = self.page.locator("[role=option]:visible")
        expect(options.first).to_be_visible()
        self.page.wait_for_load_state("networkidle")
        return options.all_inner_texts()

    def attach_tac_certificate(self, file: Path) -> None:
        self.page.locator("input[type=file]").first.set_input_files(str(file))
        expect(self.page.get_by_text(Path(file).name, exact=True)).to_be_visible()

    def edit_url_pattern(self) -> str:
        return r"/tc/oem-management/device-models/\d+/edit"
