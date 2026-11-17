"""Driver Management – /tc/users/drivers (the create form opens on the same route)."""

from pathlib import Path

from playwright.sync_api import expect

from pages.administration.base_user_page import UserListPage
from utils.data_generator import DriverData
from utils.file_utils import TEST_PDF


class DriverPage(UserListPage):
    PATH = "/tc/users/drivers"
    LIST_HEADING = "Driver Management"
    TOTAL_LABEL = "Total Drivers"
    CREATE_BUTTON = "Add Driver"
    FORM_HEADING = "Add Driver"
    SUBMIT_BUTTON = "Register Driver"

    def fill_form(
        self,
        driver: DriverData,
        photo: Path | None,
        *,
        licence_file: Path | None = TEST_PDF,
        confirm: str | None = None,
    ) -> str:
        """Fill the form; returns the city that was selected ("" when skipped).

        Empty `driver.state` / `driver.city` leave those selects untouched; `photo=None` or
        `licence_file=None` skip the upload.
        """
        self.fill("Driver Name *", driver.name)
        self.fill("Email Address *", driver.email)
        self.fill("Contact Number *", driver.mobile)
        self.fill("Driver Licence Number *", driver.licence_number)

        city = ""
        if driver.state:
            self.choose("State", driver.state)
            if driver.city:
                expect(self.page.get_by_role("combobox", name="City", exact=True)).to_be_enabled()
                city = self.choose("City", driver.city)
        self.fill("Address", driver.address)

        self.fill_passwords(driver.password, confirm)

        # the licence field accepts pdf/images; the photo field is the one that accepts .webp
        if licence_file is not None:
            self.page.locator("input[type=file][accept*='pdf']").set_input_files(str(licence_file))
        if photo is not None:
            self.page.locator("input[type=file][accept*='webp']").set_input_files(str(photo))
        return city
