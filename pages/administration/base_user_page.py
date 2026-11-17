"""
Shared behaviour for the /tc/users/* list pages and their create forms.

Each entity page object subclasses `UserListPage` and adds its own form helpers.
"""

import re

from playwright.sync_api import Locator, Page, expect


class DatePicker:
    """The app's custom calendar widget (trigger button + popover with Today/Cancel/Select)."""

    def __init__(self, page: Page, trigger_name: str) -> None:
        self.page = page
        self.trigger = page.get_by_role("button", name=trigger_name, exact=True)
        self.popover = page.locator(".date-picker-open .date-picker-popover")

    def _open(self) -> None:
        self.trigger.click()
        expect(self.popover).to_be_visible()

    def _confirm(self) -> None:
        select = self.popover.get_by_role("button", name="Select", exact=True)
        if select.is_visible():
            select.click()
        expect(self.popover).to_be_hidden()

    def pick_day(self, months_from_now: int = 0, day: int = 15) -> None:
        """Pick `day` of the month `months_from_now` away (negative = past).

        Days 8-22 occur once in the calendar grid (leading/trailing days of the
        neighbouring months are 1-7 and 23-31), so `exact` is unambiguous.
        """
        self._open()
        nav = "Next month" if months_from_now > 0 else "Previous month"
        for _ in range(abs(months_from_now)):
            self.popover.get_by_role("button", name=nav).click()
        self.popover.get_by_role("button", name=str(day), exact=True).click()
        self._confirm()


class UserListPage:
    """Base page object for a user-management list page + its create form."""

    PATH = ""              # e.g. "/tc/users/oem"
    LIST_HEADING = ""      # h1 of the list page
    TOTAL_LABEL = ""       # caption of the "Total …" counter
    CREATE_BUTTON = ""     # button that opens the create form
    FORM_HEADING = ""      # h1 of the create form
    SUBMIT_BUTTON = ""     # submit button of the create form

    def __init__(self, page: Page) -> None:
        self.page = page
        self.list_heading = page.get_by_role("heading", name=self.LIST_HEADING, level=1)
        self.create_button = page.get_by_role("button", name=self.CREATE_BUTTON, exact=True)
        self.form_heading = page.get_by_role("heading", name=self.FORM_HEADING, level=1)
        self.submit_button = page.get_by_role("button", name=self.SUBMIT_BUTTON, exact=True)
        self.search_box = page.get_by_role("textbox", name="Search", exact=True)
        self.apply_filters_button = page.get_by_role("button", name="Apply Filters")

    # ── Helpers for building locators ────────────────────────────────────────

    def textbox(self, name: str) -> Locator:
        return self.page.get_by_role("textbox", name=name, exact=True)

    def fill(self, name: str, value: str) -> None:
        self.textbox(name).fill(value)

    def fill_passwords(
        self,
        password: str,
        confirm: str | None = None,
        password_label: str = "Password *",
        confirm_label: str = "Confirm Password *",
    ) -> None:
        """Fill password + confirmation. `confirm=None` repeats the password; "" leaves it blank.

        The confirmation box stays disabled until the password has a value.
        """
        self.fill(password_label, password)
        confirm_value = password if confirm is None else confirm
        if password and confirm_value:
            expect(self.textbox(confirm_label)).to_be_enabled()
            self.fill(confirm_label, confirm_value)

    def choose(self, combobox_name: str, option: "str | re.Pattern") -> str:
        """Open a custom select and pick the option equal to `option` (or matching the pattern).

        Option lists load/re-render asynchronously, so we always wait for a specific
        option instead of taking "the first one". Returns the chosen option's text.
        """
        self.page.get_by_role("combobox", name=combobox_name, exact=True).click()
        pattern = option if isinstance(option, re.Pattern) else re.compile(rf"^\s*{re.escape(option)}\s*$")
        # only the open dropdown's options: a previous select may leave hidden options in the DOM
        target = self.page.locator("[role=option]:visible").filter(has_text=pattern).first
        expect(target).to_be_visible()
        text = (target.text_content() or "").strip()
        target.click()
        return text

    # ── List page ────────────────────────────────────────────────────────────

    def open(self) -> "UserListPage":
        self.page.goto(self.PATH)
        expect(self.list_heading).to_be_visible(timeout=20_000)
        # rows load asynchronously (empty skeleton rows come first); counters read 0 until data arrives
        expect(self.page.get_by_role("row").nth(1)).to_contain_text(re.compile(r"\w"), timeout=20_000)
        return self

    def total(self) -> int:
        counter = self.page.locator(
            f"xpath=//p[normalize-space()='{self.TOTAL_LABEL}']/following::h2[1]"
        )
        return int(counter.inner_text().replace(",", ""))

    def search(self, text: str) -> None:
        self.search_box.fill(text)
        if self.apply_filters_button.is_enabled():
            self.apply_filters_button.click()

    def row(self, text: str) -> Locator:
        return self.page.get_by_role("row").filter(has_text=text)

    def first_row_text(self) -> str:
        """Text of the first data row (used to pick an existing record for duplicate tests)."""
        return self.page.get_by_role("row").nth(1).inner_text()

    def open_create_form(self) -> None:
        self.create_button.click()
        expect(self.form_heading).to_be_visible()

    # ── Create form ──────────────────────────────────────────────────────────

    # Everything a user can be told about a rejected form, read in a single atomic call:
    #   - role=alert banners / field alerts,
    #   - red inline error text under a field (<p class="…text-red…">),
    #   - the browser's own validation text for invalid inputs (e.g. "missing an '@'").
    _MESSAGES_JS = """() => {
        const texts = [];
        document.querySelectorAll('[role=alert]').forEach(e => texts.push(e.textContent));
        document.querySelectorAll("p[class*='text-red']").forEach(e => {
            if (e.offsetParent !== null) texts.push(e.textContent);
        });
        document.querySelectorAll('input:invalid').forEach(e => texts.push(e.validationMessage));
        return texts.map(t => (t || '').trim()).filter(t => t.length > 1);
    }"""

    def messages(self) -> list[str]:
        """Validation / error messages currently shown to the user (de-duplicated, in page order)."""
        return list(dict.fromkeys(self.page.evaluate(self._MESSAGES_JS)))

    def submit_and_wait(self) -> None:
        """Click submit and wait for the form to close; fail with the on-screen messages if it doesn't."""
        self.submit_button.click()
        try:
            expect(self.form_heading).to_be_hidden(timeout=30_000)
        except AssertionError:
            errors = self.page.locator("p, span").filter(has_text=re.compile(r"required|invalid|must|already|exists", re.I))
            raise AssertionError(
                f"Form '{self.FORM_HEADING}' did not close after submit. "
                f"Messages: {self.messages()} | Field errors: {errors.all_inner_texts()[:8]}"
            ) from None

    def expect_in_list(self, search_text: str, *expected_texts: str) -> Locator:
        """Search for the new record and assert its row contains every expected text."""
        self.open()
        self.search(search_text)
        row = self.row(search_text)
        expect(row).to_have_count(1, timeout=20_000)
        for text in expected_texts:
            expect(row).to_contain_text(text)
        return row
