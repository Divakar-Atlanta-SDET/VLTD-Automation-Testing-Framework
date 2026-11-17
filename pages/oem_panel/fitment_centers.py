"""
OEM > Management > User Management > Fitment Center: the list, the Register / Edit form and the details page.

  list     /oem/users/fitment-centers            counters, filters, live search, row menu (View details / Edit FC)
  form     /oem/users/fitment-centers/new        and  /{id}/edit
  details  /oem/users/fitment-centers/{id}       Suspend / Activate / Blacklist, each asks for mandatory remarks

The row menu has no status actions, and a blacklisted centre has no actions at all ("No further status actions are available").
The confirmation boxes are plain overlays (no dialog role), so they are found by their title and their fields.
"""

import re
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage
from pages.oem_panel.misc import FitmentCentersPage

STATUS_BUTTONS = {"suspend": "Suspend", "activate": "Activate", "blacklist": "Blacklist"}
CONFIRM_BUTTONS = {"suspend": "Suspend Fitment Center", "activate": "Activate Fitment Center", "blacklist": "Blacklist Fitment Center"}
BADGES = {"active": "Active", "suspended": "Suspended", "blacklisted": "Blacklisted"}


def _is_status_change(response) -> bool:
    return response.request.method == "PATCH" and re.search(r"/fitment-centres/\d+/(deactivate|activate|blacklist)$", response.url) is not None


class FitmentCenterListPage(FitmentCentersPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.register_button = page.get_by_role("button", name="Register FC", exact=True)
        self.search_box = page.get_by_placeholder("Search Fitment Centers...")
        self.apply_button = page.get_by_role("button", name="Apply Filters", exact=True)
        self.clear_button = page.get_by_role("button", name="Clear", exact=True)
        self.status_filter = page.get_by_role("combobox").filter(has_text=re.compile(r"^(All Statuses|Active|Suspended|Blacklisted)$"))
        self.empty_state = page.get_by_text("No matching Fitment Centers found.")

    def open(self) -> "FitmentCenterListPage":
        """Open the list and wait for its first page of centres (typing into the search box earlier is lost when the data arrives)."""
        with self.page.expect_response(lambda r: "/api/oem/fitment-centres?" in r.url):
            self.page.goto(self.PATH)
        expect(self.heading).to_be_visible(timeout=20_000)
        return self

    def row(self, text: str) -> Locator:
        return self.page.get_by_role("row").filter(has_text=text)

    def search(self, term: str) -> None:
        """Type the term and press Apply Filters (the list does not search while typing); waits for the request."""
        self.search_box.fill(term)
        with self.page.expect_response(lambda r: "/api/oem/fitment-centres?" in r.url and "search=" in r.url):
            self.apply_button.click()

    def clear_search(self) -> None:
        self.search_box.fill("")
        with self.page.expect_response(lambda r: "/api/oem/fitment-centres?" in r.url and "search=" not in r.url):
            self.apply_button.click()

    def choose_status(self, option: str) -> None:
        self.status_filter.click()
        self.page.locator("[role=option]:visible").filter(has_text=re.compile(rf"^\s*{option}\s*$")).click()
        with self.page.expect_response(lambda r: "/api/oem/fitment-centres?" in r.url):
            self.apply_button.click()

    # paging: First page / Previous page / Go to page N / Next page / Last page, and "Showing 1 to 10 of 19 results" (10 rows a page)
    @property
    def pager_summary(self) -> Locator:
        return self.page.get_by_text(re.compile(r"Showing\s+\d+\s+to\s+\d+\s+of\s+\d+\s+results"))

    def pager_button(self, name: str) -> Locator:
        return self.page.get_by_role("button", name=name, exact=True)

    def go_to(self, button: str) -> None:
        """Press a pager button and wait for the page of centres it loads."""
        with self.page.expect_response(lambda r: "/api/oem/fitment-centres?" in r.url):
            self.pager_button(button).click()

    def codes(self) -> list[str]:
        """The fitment code of every row shown, in order."""
        rows = [re.sub(r"\s+", " ", text) for text in self.page.get_by_role("row").all_inner_texts()[1:]]
        return [match.group(1) for row in rows if (match := re.search(r"Code: (.+?) GST:", row))]

    def row_menu(self, text: str) -> list[str]:
        """The items of a row's action menu (the menu is closed again)."""
        self.row(text).get_by_role("button", name="Open actions").click()
        items = [item.strip() for item in self.page.get_by_role("menuitem").all_text_contents()]
        self.page.keyboard.press("Escape")
        return items

    def open_details(self, text: str) -> "FitmentCenterDetailsPage":
        self.row(text).get_by_role("button", name="Open actions").click()
        self.page.get_by_role("menuitem", name="View details").click()
        return FitmentCenterDetailsPage(self.page).wait_until_loaded()

    def open_edit(self, text: str) -> "FitmentCenterFormPage":
        self.row(text).get_by_role("button", name="Open actions").click()
        self.page.get_by_role("menuitem", name="Edit FC").click()
        return FitmentCenterFormPage(self.page, edit=True).wait_until_loaded()


class FitmentCenterFormPage(OemPanelPage):
    """The Register Fitment Center form (`edit=False`) and the Edit Fitment Center form (`edit=True`)."""

    HEADING_LEVEL = None

    def __init__(self, page: Page, edit: bool = False) -> None:
        self.edit = edit
        self.PATH = "/oem/users/fitment-centers/new"
        self.HEADING = "Edit Fitment Center" if edit else "Register Fitment Center"
        super().__init__(page)
        self.name_box = page.get_by_label(re.compile(r"^Business Name"))
        self.code_box = page.get_by_placeholder("Enter Unique Code")
        self.owner_box = page.get_by_placeholder("Enter Owner Name")
        self.gst_box = page.get_by_placeholder("Enter GST Number")
        self.contact_box = page.get_by_placeholder("Enter Contact Number", exact=True)
        self.alternate_box = page.get_by_placeholder("Enter Alternate Contact Number")
        self.email_box = page.get_by_placeholder("Enter Contact Email")
        self.address_box = page.get_by_placeholder("Enter Address")
        self.address_2_box = page.get_by_placeholder("Apartment, Landmark (Optional)")
        self.pincode_box = page.get_by_placeholder("Enter Pincode")
        self.password_box = page.get_by_placeholder("Enter Password", exact=True)
        self.confirm_password_box = page.get_by_placeholder("Confirm Password")
        self.city_select = self.main.get_by_role("combobox").nth(0)
        self.rto_select = self.main.get_by_role("combobox").nth(1)
        self.map = page.locator(".gm-style").first
        self.coordinates = page.get_by_text(re.compile(r"^\s*-?\d+\.\d+, -?\d+\.\d+\s*$"))
        self.image_input = page.locator("input[type=file][accept*='image']")
        self.certificate_input = page.locator("input[type=file][accept='application/pdf']")  # appears when a GST number is entered
        self.submit_button = page.get_by_role("button", name="Update Fitment Center" if edit else "Register FC", exact=True)

    def wait_until_loaded(self) -> "FitmentCenterFormPage":
        expect(self.heading).to_be_visible(timeout=20_000)
        if self.edit:
            expect(self.city_select).not_to_have_text(re.compile(r"^Select"), timeout=20_000)  # the stored values are filled in
        return self

    def open_new(self) -> "FitmentCenterFormPage":
        return self.open()

    def pick(self, select: Locator, option: "str | None" = None) -> None:
        """Open a dropdown and choose the option with exactly that text (the first one when none is given); checks what the dropdown then shows."""
        options = self.page.locator("[role=option]:visible")
        expect(options).to_have_count(0)  # the previous dropdown has closed
        select.click()
        expect(options.first).to_be_visible()
        target = self.page.get_by_role("option", name=option, exact=True) if option else options.first
        expect(target).to_be_visible()
        chosen = target.inner_text().strip()
        target.click()
        expect(select).to_contain_text(chosen)

    def pin_location(self) -> str:
        """Click the map once and return the coordinates the form shows."""
        self.map.click(position={"x": 300, "y": 200})
        expect(self.coordinates).to_be_visible()
        return self.coordinates.inner_text().strip()

    def fill_new(self, fields: dict, image: Path, city: str = "Delhi", rto: str | None = None) -> str:
        """Fill every mandatory field of the registration form; returns the pinned coordinates."""
        self.name_box.fill(fields["business_name"])
        self.code_box.fill(fields["short_name"])
        self.owner_box.fill(fields["owner_name"])
        self.contact_box.fill(fields["contact_no"])
        self.email_box.fill(fields["email_id"])
        self.pick(self.city_select, city)
        expect(self.rto_select).to_be_enabled()
        self.pick(self.rto_select, rto)
        self.address_box.fill(fields["address_line_1"])
        self.pincode_box.fill(fields["pincode"])
        coordinates = self.pin_location()
        self.image_input.set_input_files(image)
        self.password_box.fill(fields["password"])
        self.confirm_password_box.fill(fields["password_confirmation"])
        return coordinates

    def submit(self) -> None:
        self.submit_button.click()

    def error(self, message: "str | re.Pattern") -> Locator:
        return self.main.get_by_text(message, exact=isinstance(message, str))


class FitmentCenterDetailsPage(OemPanelPage):
    PATH = "/oem/users/fitment-centers"
    HEADING = "Fitment Center Details"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.remarks_box = page.get_by_placeholder("Enter remarks")
        self.no_actions = page.get_by_text("No further status actions are available.")

    def open_id(self, fc_id: int) -> "FitmentCenterDetailsPage":
        self.page.goto(f"{self.PATH}/{fc_id}")
        return self.wait_until_loaded()

    def wait_until_loaded(self) -> "FitmentCenterDetailsPage":
        expect(self.heading).to_be_visible(timeout=20_000)
        expect(self.main.get_by_text("Remarks History")).to_be_visible(timeout=20_000)
        return self

    def action_button(self, action: str) -> Locator:
        return self.main.get_by_role("button", name=STATUS_BUTTONS[action], exact=True)

    def confirm_button(self, action: str) -> Locator:
        return self.page.get_by_role("button", name=CONFIRM_BUTTONS[action], exact=True)

    def badge(self, status: str) -> Locator:
        return self.main.get_by_text(BADGES[status], exact=True).first

    def open_action(self, action: str) -> None:
        self.action_button(action).click()
        expect(self.confirm_button(action)).to_be_visible()

    def cancel_action(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).click()
        expect(self.remarks_box).to_have_count(0)

    def change_status(self, action: str, remarks: str):
        """Suspend / Activate / Blacklist with remarks; returns the response of the status request."""
        self.open_action(action)
        self.remarks_box.fill(remarks)
        with self.page.expect_response(_is_status_change) as sent:
            self.confirm_button(action).click()
        return sent.value

    def history(self) -> list[tuple[str, str]]:
        """(STATUS, remark text) of every entry in the Remarks History, in the order shown."""
        text = re.sub(r"\s+", " ", self.main.inner_text())
        history = text.split("Remarks History", 1)[1]
        pattern = (r"(SUSPENDED|ACTIVE|BLACKLISTED) By .*?\s*\d{1,2} \w{3} \d{4}, \d{1,2}:\d{2} [ap]m\s*(.*?)"
                   r"(?=(?:SUSPENDED|ACTIVE|BLACKLISTED) By |$)")
        return [(status, remark.strip()) for status, remark in re.findall(pattern, history)]

    def expect_shown(self, **values: str) -> None:
        """Each LABEL value pair is shown on the page, e.g. expect_shown(**{"OWNER NAME": "Auto Owner"})."""
        for label, value in values.items():
            expect(self.main).to_contain_text(re.compile(rf"{re.escape(label)}\s*{re.escape(value)}", re.I))
