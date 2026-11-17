"""TC Staff Management – /tc/users/staff and /tc/users/staff/register."""

import re

from playwright.sync_api import expect

from pages.administration.base_user_page import UserListPage
from utils.data_generator import StaffData


class StaffPage(UserListPage):
    PATH = "/tc/users/staff"
    LIST_HEADING = "Transport Commissioner Staff"
    TOTAL_LABEL = "Total Staff"
    CREATE_BUTTON = "Register Staff"
    FORM_HEADING = "Register TC Staff"
    SUBMIT_BUTTON = "Register Staff"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.permissions_summary = page.get_by_text(re.compile(r"\d+ of 63 selected"))
        self.clear_all_button = page.get_by_role("button", name="Clear All")

    def select_permission(self, name: str) -> None:
        self.page.get_by_role("checkbox", name=name, exact=True).check()

    def expect_selected_count(self, count: int) -> None:
        expect(self.permissions_summary).to_have_text(f"{count} of 63 selected")

    def fill_form(self, staff: StaffData, *, confirm: str | None = None) -> None:
        self.fill("Staff Name *", staff.name)
        self.fill("Email Address *", staff.email)
        self.fill("Contact Number *", staff.mobile)
        self.fill_passwords(staff.password, confirm)
