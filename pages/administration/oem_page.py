"""OEM Management – /tc/users/oem and /tc/users/oem/register."""

from pathlib import Path

from playwright.sync_api import expect

from pages.administration.base_user_page import DatePicker, UserListPage
from utils.data_generator import OemData
from utils.file_utils import TEST_PDF

# (GST, TAC, COP) certificate files and (TAC issued, COP from, COP till) month offsets
VALID_CERTIFICATES = (TEST_PDF, TEST_PDF, TEST_PDF)
VALID_DATES = (-1, 0, 1)


class OemPage(UserListPage):
    PATH = "/tc/users/oem"
    LIST_HEADING = "OEM Management"
    TOTAL_LABEL = "Total OEMs"
    CREATE_BUTTON = "Register OEM"
    FORM_HEADING = "Register OEM"
    SUBMIT_BUTTON = "Register OEM"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.tac_issue_date = DatePicker(page, "Select TAC issue date")
        self.cop_valid_from = DatePicker(page, "Select validity start date")
        self.cop_valid_till = DatePicker(page, "Select validity end date")
        self.certificate_inputs = page.locator("input[type=file]")

    def attach_certificates(self, files: tuple[Path | None, Path | None, Path | None]) -> None:
        """Attach (GST, TAC, COP) files; `None` skips one.

        A file input disappears once its file is accepted, so each field is addressed by its
        position among the inputs that are still pending. A rejected file (wrong type or too
        large) leaves its input in place, so the field stays pending.
        """
        pending = [0, 1, 2]
        for field_index, file in enumerate(files):
            if file is None:
                continue
            self.certificate_inputs.nth(pending.index(field_index)).set_input_files(str(file))
            try:
                expect(self.certificate_inputs).to_have_count(len(pending) - 1, timeout=2_000)
                pending.remove(field_index)
            except AssertionError:
                pass  # file rejected by the form

    def fill_form(
        self,
        oem: OemData,
        *,
        certificates: tuple[Path | None, Path | None, Path | None] = VALID_CERTIFICATES,
        dates: tuple[int | None, int | None, int | None] = VALID_DATES,
        confirm: str | None = None,
    ) -> None:
        """Fill the form. Keyword options build invalid variants (see tests/administration)."""
        self.fill("Business Name *", oem.business_name)
        self.fill("OEM Code *", oem.code)
        self.fill("CIN Number *", oem.cin)

        self.fill("GST Number *", oem.gst)
        self.fill("TAC Number *", oem.tac_number)
        self.fill("COP Number *", oem.cop_number)

        self.attach_certificates(certificates)

        # TAC issued last month (it cannot be in the future), COP valid this month -> next month
        tac, cop_from, cop_till = dates
        if tac is not None:
            self.tac_issue_date.pick_day(months_from_now=tac)
        if cop_from is not None:
            self.cop_valid_from.pick_day(months_from_now=cop_from, day=20)
        if cop_till is not None:
            self.cop_valid_till.pick_day(months_from_now=cop_till)

        self.fill("Office Address *", oem.address)
        self.fill("Address Line 2", oem.address_line_2)
        self.fill("Pincode *", oem.pincode)

        self.fill("Contact Person Name *", oem.contact_name)
        self.fill("Contact Mobile *", oem.mobile)
        self.fill("Contact Email *", oem.email)
        self.fill_passwords(oem.password, confirm)
