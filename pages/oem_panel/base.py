"""Shared behaviour of the OEM panel pages (`/oem/...`): open by path, wait for the heading, custom selects."""

import re

from playwright.sync_api import Locator, Page, expect


class OemPanelPage:
    PATH = ""
    HEADING: "str | re.Pattern" = ""  # heading of the page
    HEADING_LEVEL: int | None = 1     # h1 on list pages; the registration form uses an h2

    def __init__(self, page: Page) -> None:
        self.page = page
        self.heading = (page.get_by_role("heading", name=self.HEADING, level=self.HEADING_LEVEL) if self.HEADING_LEVEL
                        else page.get_by_role("heading", name=self.HEADING))
        self.main = page.locator("main")
        # the header's account menu trigger (its own label is the signed-in user's name, which Profile can change; aria-haspopup is stable)
        self.account_menu_button = page.locator("header button[aria-haspopup='menu'], nav button[aria-haspopup='menu']")

    def open(self):
        self.page.goto(self.PATH)
        expect(self.heading).to_be_visible(timeout=20_000)
        return self

    def open_account_menu(self) -> None:
        self.account_menu_button.click()

    def open_profile(self) -> "OemProfilePage":
        from pages.oem_panel.profile import OemProfilePage  # avoid a circular import
        self.open_account_menu()
        self.page.get_by_role("menuitem", name="Profile").click()
        return OemProfilePage(self.page).wait_until_open()

    def logout(self) -> None:
        self.open_account_menu()
        self.page.get_by_role("menuitem", name="Logout").click()

    def choose(self, combobox_name: str, option: "str | re.Pattern") -> None:
        """Open a custom select (role=combobox) and pick the option; waits for lazily loaded option lists."""
        self.page.get_by_role("combobox", name=combobox_name, exact=True).click()
        pattern = option if isinstance(option, re.Pattern) else re.compile(rf"^\s*{re.escape(option)}\s*$")
        target = self.page.locator("[role=option]:visible").filter(has_text=pattern).first
        expect(target).to_be_visible()
        target.click()

    def options_of(self, combobox_name: str) -> list[str]:
        self.page.get_by_role("combobox", name=combobox_name, exact=True).click()
        options = [o.strip() for o in self.page.locator("[role=option]:visible").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return options

    def row_with(self, *texts: str) -> Locator:
        """Table rows that contain all the given texts."""
        row = self.page.get_by_role("row")
        for text in texts:
            row = row.filter(has_text=text)
        return row

    def expect_counters(self, **expected: int) -> None:
        """The stat cards at the top of a list page, e.g. expect_counters(Total_Centers=2, Active=1).

        Labels are matched in the order given, each with its number right behind it (other text may sit between cards); the cards fill in after separate
        requests, so this waits (auto-retrying) instead of reading the page once.
        """
        pattern = ".*?".join(rf"{label.replace('_', ' ')}\s*{value}(?!\d)" for label, value in expected.items())
        expect(self.main).to_contain_text(re.compile(pattern, re.I | re.S), timeout=15_000)
