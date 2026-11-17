"""
Shared behaviour of the three OEM Management pages (Device Models, Firmware, SIM Modules).

Each page has: a header with Refresh and an Add button, a search box, an OEM filter, a Status filter
(Firmware also has an Update Type filter), a table with a row action menu (View / Edit / Delete) and a
create/edit form on its own route (`/new`, `/{id}/edit`).

Search and the filters work on the rows the page has already loaded (they send no request).
"""

import re

from playwright.sync_api import Locator, Page, expect


class OemMgmtListPage:
    SLUG = ""             # e.g. "device-models"
    LIST_HEADING = ""     # h1 of the list page
    ADD_BUTTON = ""       # "Add Device Model"
    ADD_HEADING = ""      # h1 of the create form
    EDIT_HEADING = ""     # h1 of the edit form
    SUBMIT_CREATE = ""    # "Create Device Model"
    SUBMIT_UPDATE = ""    # "Update Device Model"
    TABLE_NAME = ""       # accessible name of the table, e.g. "Device Models"
    COLUMNS: tuple[str, ...] = ()
    VIEW_HEADING = ""     # heading of the "View" panel
    DELETE_HEADING = ""   # heading of the delete confirmation
    EMPTY_TEXT = re.compile(r"No .+ Found", re.I)

    def __init__(self, page: Page) -> None:
        self.page = page
        self.heading = page.get_by_role("heading", name=self.LIST_HEADING, level=1)
        self.add_button = page.get_by_role("button", name=self.ADD_BUTTON, exact=True)
        self.refresh_button = page.get_by_role("button", name="Refresh", exact=True)
        self.search_box = page.get_by_role("textbox", name="Search", exact=True)
        self.oem_filter = page.get_by_role("combobox", name="OEM", exact=True)
        self.status_filter = page.get_by_role("combobox", name="Status", exact=True)
        self.table = page.get_by_role("table", name=self.TABLE_NAME)

    # ── navigation ───────────────────────────────────────────────────────────

    @property
    def path(self) -> str:
        return f"/tc/oem-management/{self.SLUG}"

    def open(self) -> "OemMgmtListPage":
        self.page.goto(self.path)
        expect(self.heading).to_be_visible(timeout=20_000)
        self.wait_for_data()
        return self

    def wait_for_data(self) -> None:
        """Rows (or the empty-state message) are rendered once the list request has finished."""
        expect(self.table).not_to_contain_text(re.compile(r"Loading", re.I), timeout=20_000)
        data_row = self.table.get_by_role("row").nth(1)
        expect(data_row).to_contain_text(re.compile(r"\w"), timeout=20_000)

    # ── table ────────────────────────────────────────────────────────────────

    def rows(self) -> Locator:
        """Data rows (the header row is excluded)."""
        return self.table.get_by_role("row").filter(has=self.page.get_by_role("cell"))

    def row(self, text: str) -> Locator:
        return self.rows().filter(has_text=text)

    def column_headers(self) -> list[str]:
        return [h.strip() for h in self.table.get_by_role("columnheader").all_inner_texts()]

    def row_cells(self, row: Locator) -> list[str]:
        return [c.strip() for c in row.get_by_role("cell").all_inner_texts()]

    def visible_record_count(self) -> int:
        """Number of real records shown (0 when the table shows its empty-state message)."""
        if self.empty_state().count() and self.empty_state().first.is_visible():
            return 0
        return self.rows().count()

    def empty_state(self) -> Locator:
        return self.table.get_by_text(self.EMPTY_TEXT)

    # ── search / filters ─────────────────────────────────────────────────────

    def search(self, text: str) -> None:
        self.search_box.fill(text)
        self.page.wait_for_timeout(400)  # client-side filter; give the table a moment to re-render

    def clear_search(self) -> None:
        self.search_box.fill("")
        self.page.wait_for_timeout(400)

    def pick_filter(self, combobox: Locator, option: str | re.Pattern) -> None:
        combobox.click()
        pattern = option if isinstance(option, re.Pattern) else re.compile(rf"^\s*{re.escape(option)}\s*$")
        target = self.page.locator("[role=option]:visible").filter(has_text=pattern).first
        expect(target).to_be_visible()
        target.click()
        self.page.wait_for_timeout(400)

    def filter_by_oem(self, oem_name: str) -> None:
        self.pick_filter(self.oem_filter, re.compile(re.escape(oem_name)))

    def filter_by_status(self, status: str) -> None:
        self.pick_filter(self.status_filter, status)

    def oem_filter_options(self) -> list[str]:
        self.oem_filter.click()
        options = [o.strip() for o in self.page.locator("[role=option]:visible").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return options

    # ── row actions ──────────────────────────────────────────────────────────

    def open_menu(self, row: Locator) -> None:
        row.first.get_by_role("button", name="Open actions").click()

    def menu_items(self, row: Locator) -> list[str]:
        self.open_menu(row)
        items = [i.strip() for i in self.page.get_by_role("menuitem").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return items

    def choose_action(self, row: Locator, action: str) -> None:
        self.open_menu(row)
        self.page.get_by_role("menuitem", name=re.compile(action)).click()

    def view(self, row: Locator) -> None:
        self.choose_action(row, "View")
        expect(self.page.get_by_text(self.VIEW_HEADING, exact=True)).to_be_visible()

    def view_text(self) -> str:
        """Everything shown in the 'View' panel."""
        return self.page.locator("body").inner_text()

    def close_view(self) -> None:
        self.page.get_by_role("button", name="Close", exact=True).click()
        expect(self.page.get_by_text(self.VIEW_HEADING, exact=True)).to_be_hidden()

    def edit(self, row: Locator) -> None:
        self.choose_action(row, "Edit")
        expect(self.page.get_by_role("heading", name=self.EDIT_HEADING, level=1)).to_be_visible()
        # the record is loaded after the page appears and would overwrite anything typed too early
        expect(self.page.get_by_role("main").get_by_role("textbox").first).not_to_have_value("", timeout=15_000)

    def start_delete(self, row: Locator) -> None:
        self.choose_action(row, "Delete")
        expect(self._delete_prompt()).to_be_visible()

    def _delete_prompt(self) -> Locator:
        return self.page.get_by_text(re.compile(r"Are you sure you want to delete"))

    def confirm_delete(self) -> None:
        self.page.get_by_role("button", name="Delete", exact=True).click()

    def cancel_delete(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).click()
        expect(self._delete_prompt()).to_be_hidden()

    # ── forms ────────────────────────────────────────────────────────────────

    def open_add_form(self) -> None:
        self.add_button.click()
        expect(self.page.get_by_role("heading", name=self.ADD_HEADING, level=1)).to_be_visible()

    def textbox(self, name: str) -> Locator:
        return self.page.get_by_role("textbox", name=name, exact=True)

    def fill(self, name: str, value: str) -> None:
        self.textbox(name).fill(value)

    def choose(self, combobox_name: str, option: str | re.Pattern) -> None:
        """Open a custom select in a form and pick the option (waits for it - lists load asynchronously)."""
        self.page.get_by_role("combobox", name=combobox_name, exact=True).click()
        pattern = option if isinstance(option, re.Pattern) else re.compile(rf"^\s*{re.escape(option)}\s*$")
        target = self.page.locator("[role=option]:visible").filter(has_text=pattern).first
        expect(target).to_be_visible()
        target.click()

    def choose_oem(self, oem_name: str) -> None:
        self.choose("OEM *", re.compile(re.escape(oem_name)))

    def submit_create(self) -> None:
        self.page.get_by_role("button", name=self.SUBMIT_CREATE, exact=True).click()

    def submit_update(self) -> None:
        self.page.get_by_role("button", name=self.SUBMIT_UPDATE, exact=True).click()

    def cancel_form(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).click()

    def reset_form(self) -> None:
        self.page.get_by_role("button", name="Reset", exact=True).click()

    # ── feedback ─────────────────────────────────────────────────────────────

    _MESSAGES_JS = """() => {
        const texts = [];
        document.querySelectorAll("[role=alert], [role=status], [data-sonner-toast], [class*='toast']").forEach(e => texts.push(e.textContent));
        document.querySelectorAll("p[class*='text-red']").forEach(e => { if (e.offsetParent !== null) texts.push(e.textContent); });
        return texts.map(t => (t || '').trim()).filter(t => t.length > 1);
    }"""

    def messages(self) -> list[str]:
        """Toasts and inline validation messages currently shown (de-duplicated)."""
        return list(dict.fromkeys(self.page.evaluate(self._MESSAGES_JS)))

    def wait_for_message(self, pattern: str, timeout: int = 15_000) -> list[str]:
        """Wait until a message matching `pattern` is on screen, then return all messages."""
        regex = re.compile(pattern, re.I)
        deadline = timeout
        while deadline > 0:
            found = self.messages()
            if any(regex.search(m) for m in found):
                return found
            self.page.wait_for_timeout(200)
            deadline -= 200
        raise AssertionError(f"No message matching /{pattern}/ appeared. Seen: {self.messages()}")

    def field_errors(self) -> list[str]:
        return [t.strip() for t in self.page.locator("p[class*='text-red']").all_inner_texts() if t.strip()]
