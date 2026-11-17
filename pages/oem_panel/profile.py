"""
OEM "My Profile" (`/oem/profile`), reached from the account menu (see `OemPanelPage.open_profile`).

Two tabs: Profile Details (view, then Edit Details -> a form with Full Name, Email Address, Contact Number; Address and
City & State are read-only) and Change Password (Current / New / Confirm, with a strength note and a show/hide toggle
on each password field).
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage


class OemProfilePage(OemPanelPage):
    PATH = "/oem/profile"
    HEADING = "My Profile"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.details_tab = page.get_by_role("tab", name="Profile Details")
        self.change_password_tab = page.get_by_role("tab", name="Change Password")
        self.edit_button = page.get_by_role("button", name="Edit Details")
        self.save_button = page.get_by_role("button", name="Save Changes")
        self.cancel_button = page.get_by_role("button", name="Cancel")
        # view mode: <dt>/<dd> pairs
        self.full_name = page.get_by_role("textbox", name="Full Name *")
        self.email = page.get_by_role("textbox", name="Email Address *")
        self.contact_no = page.get_by_role("textbox", name="Contact Number")

    def wait_until_open(self) -> "OemProfilePage":
        expect(self.heading).to_be_visible(timeout=20_000)
        expect(self.edit_button).to_be_visible(timeout=20_000)  # the data has loaded (view mode); not shown while the tab is Change Password
        return self

    def open(self):
        self.page.goto(self.PATH)
        return self.wait_until_open()

    def fields(self) -> dict[str, str]:
        """View mode: {'Full Name': ..., 'Email Address': ..., 'Contact Number': ..., 'Address': ...}."""
        terms = [(t.text_content() or "").strip() for t in self.page.get_by_role("term").all()]
        definitions = [(d.text_content() or "").strip() for d in self.page.get_by_role("definition").all()]
        return dict(zip(terms, definitions))

    def start_edit(self) -> "OemProfilePage":
        self.edit_button.click()
        expect(self.full_name).to_be_visible()
        return self

    def fill(self, name: str | None = None, email: str | None = None, contact_no: str | None = None) -> None:
        if name is not None:
            self.full_name.fill(name)
        if email is not None:
            self.email.fill(email)
        if contact_no is not None:
            self.contact_no.fill(contact_no)

    def save(self) -> None:
        self.save_button.click()

    def open_change_password(self) -> "ChangePasswordForm":
        self.change_password_tab.click()
        return ChangePasswordForm(self.page).wait_until_open()


class ChangePasswordForm:
    """The Change Password tab of My Profile, and the forced '/auth/change-password' page (same fields, no tabs)."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.current_password = page.get_by_role("textbox", name="Current Password *", exact=True)
        self.new_password = page.get_by_role("textbox", name="New Password *", exact=True)
        self.confirm_password = page.get_by_role("textbox", name="Confirm New Password *", exact=True)
        self.submit_button = page.get_by_role("button", name=re.compile(r"^(Update Password|Change Password)$"))

    def wait_until_open(self) -> "ChangePasswordForm":
        expect(self.current_password).to_be_visible()
        return self

    def fill(self, current: str, new: str, confirm: str | None = None) -> None:
        self.current_password.fill(current)
        self.new_password.fill(new)
        if new:
            self.confirm_password.fill(new if confirm is None else confirm)

    def submit(self) -> None:
        self.submit_button.click()

    def toggle_visibility(self, box: Locator) -> None:
        """Click the show/hide eye button next to the given password field (same pattern as `LoginPage.toggle_password_visibility`)."""
        box.locator("..").get_by_role("button").click()
