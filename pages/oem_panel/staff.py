"""
OEM > Management > User Management > Staff: the list and the Register OEM Staff form.

  list   /oem/users/staff         counters (Total / Active / Suspended / Blacklisted), search, status filter, Apply Filters, Clear, Refresh
  form   /oem/users/staff/new     name, e-mail, 10-digit mobile number, 41 permissions in collapsible groups, password + confirmation

The list is fed by `GET /api/oem/users`, which answers 403 for the OEM Admin (BUG-039), so no staff row has ever been seen on
screen; the form is complete and its request is `POST /api/oem/users {name, email, contact_no, password, password_confirmation, permission_ids}`.
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage
from pages.oem_panel.misc import OemStaffPage

GROUP_HEADER = re.compile(r"\d+ permissions?")  # a group header, e.g. "Alert Permissions 1 permissions 0/1"
SELECT_GROUP = "Select all permissions in "


class OemStaffListPage(OemStaffPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.search_box = page.get_by_placeholder("Search Staff...")
        self.apply_button = page.get_by_role("button", name="Apply Filters", exact=True)
        self.clear_button = page.get_by_role("button", name="Clear", exact=True)
        self.refresh_button = page.get_by_role("button", name="Refresh", exact=True)
        self.status_filter = page.get_by_role("combobox").filter(has_text=re.compile(r"^(All Statuses|Approved|Active|Suspended|Blacklisted)$"))
        self.empty_state = page.get_by_text(re.compile(r"No (matching )?Staff found"))

    def status_options(self) -> list[str]:
        self.status_filter.click()
        options = [text.strip() for text in self.page.locator("[role=option]:visible").all_text_contents()]
        self.page.keyboard.press("Escape")
        return options

    def counter_labels(self) -> list[str]:
        text = self.main.inner_text()
        return re.findall(r"(TOTAL STAFF|ACTIVE|SUSPENDED|BLACKLISTED)\s*\d+", text)


class OemStaffFormPage(OemPanelPage):
    PATH = "/oem/users/staff/new"
    HEADING = "Register OEM Staff"
    HEADING_LEVEL = None

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.name_box = page.get_by_placeholder("Enter Staff Name")
        self.email_box = page.get_by_placeholder("Enter Email Address")
        self.contact_box = page.get_by_placeholder("Enter Contact Number")
        self.password_box = page.get_by_placeholder("Enter Password", exact=True)
        self.confirm_password_box = page.get_by_placeholder("Confirm Password")
        self.permission_search = page.get_by_placeholder("Search permissions...")
        self.select_all_button = page.get_by_role("button", name="Select All", exact=True)
        self.clear_all_button = page.get_by_role("button", name="Clear All", exact=True)
        self.counter = page.get_by_text(re.compile(r"\d+ of \d+ selected"))
        self.submit_button = page.get_by_role("button", name="Register Staff", exact=True)
        self.cancel_button = page.get_by_role("button", name="Cancel", exact=True)

    def open_new(self) -> "OemStaffFormPage":
        return self.open()

    def fill(self, name: str, email: str, contact: str, password: str, confirmation: str | None = None) -> None:
        self.name_box.fill(name)
        self.email_box.fill(email)
        self.contact_box.fill(contact)
        self.password_box.fill(password)
        self.confirm_password_box.fill(password if confirmation is None else confirmation)

    def submit(self) -> None:
        self.submit_button.click()

    def error(self, message: "str | re.Pattern") -> Locator:
        return self.main.get_by_text(message, exact=isinstance(message, str))

    # permissions
    def selected(self) -> tuple[int, int]:
        """(selected, total) from the 'n of m selected' counter."""
        selected, total = re.search(r"(\d+) of (\d+) selected", self.counter.inner_text()).groups()
        return int(selected), int(total)

    def group_checkbox(self, group: str) -> Locator:
        return self.main.get_by_role("checkbox", name=f"{SELECT_GROUP}{group}", exact=True)

    def group_names(self) -> list[str]:
        names = [c.get_attribute("aria-label") or "" for c in self.main.get_by_role("checkbox").all()]
        return [name[len(SELECT_GROUP):] for name in names if name.startswith(SELECT_GROUP)]

    def group_header(self, index: int) -> Locator:
        return self.main.get_by_role("button", name=GROUP_HEADER).nth(index)

    def open_group(self, index: int) -> None:
        """The groups are an accordion: opening one closes the open one."""
        header = self.group_header(index)
        if header.get_attribute("aria-expanded") != "true":
            header.click()
        expect(header).to_have_attribute("aria-expanded", "true")

    def permission_checkbox(self, name: str) -> Locator:
        return self.main.get_by_role("checkbox", name=name, exact=True)

    def permissions_by_group(self) -> dict[str, list[tuple[int, str]]]:
        """{group name: [(permission id, permission name)]}, read by opening each group in turn (the id is the checkbox's value)."""
        groups: dict[str, list[tuple[int, str]]] = {}
        for index in range(self.main.get_by_role("button", name=GROUP_HEADER).count()):
            self.open_group(index)
            header_text = self.group_header(index).inner_text().strip()
            group = re.split(r"\s+\d+ permissions?", header_text)[0].strip()
            expected = int(re.search(r"(\d+) permissions?", header_text).group(1))
            boxes = self.main.locator(f"input[type=checkbox]:not([aria-label^='{SELECT_GROUP}'])")
            expect(boxes).to_have_count(expected)  # the previous group has finished closing
            entries = []
            for box in boxes.all():
                label = box.evaluate("e => ((e.closest('label') || e.parentElement).innerText || '').trim()")
                entries.append((int(box.get_attribute("value")), label))
            groups[group] = entries
        return groups
