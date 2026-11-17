"""
OEM Helpdesk pages.

  /oem/helpdesk/my-tickets         "Support Tickets": the tickets the OEM raised (also /oem/helpdesk)
  /oem/helpdesk/assigned-tickets   "Support Queue": tickets that are with the OEM, plus the ones it raised; row actions depend on who raised / owns the ticket
  /oem/helpdesk/create             "New Ticket"

A ticket's details, the Change Status form and the Close Ticket form open inside the list page (the URL does not change).
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage

TICKET_CODE = re.compile(r"VLTD-\d{8}-[A-Z0-9]{8}")


class HelpdeskListPage(OemPanelPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.search_box = page.get_by_role("textbox", name="Search")
        self.reset_button = page.get_by_role("button", name="Reset Filters")
        self.refresh_button = page.get_by_role("button", name="Refresh")
        self.new_ticket_link = page.get_by_role("link", name="New Ticket")
        self.counter = page.get_by_text(re.compile(r"^\d+ tickets?$"))
        self.table = page.get_by_role("table")
        self.summary = page.get_by_text(re.compile(r"Showing \d+ to \d+ of \d+ results")).first

    def open(self):
        super().open()
        expect(self.counter).to_be_visible(timeout=20_000)  # the list has been fetched (or has failed: the counter is then absent, tests expect that themselves)
        return self

    # reading the list
    def codes(self) -> list[str]:
        return TICKET_CODE.findall(self.table.inner_text())

    def row(self, code: str) -> Locator:
        return self.page.get_by_role("row").filter(has=self.page.get_by_role("button", name=code, exact=True))

    def expect_codes(self, present: list[str] = (), absent: list[str] = ()) -> None:
        for code in present:
            expect(self.row(code)).to_be_visible()
        for code in absent:
            expect(self.row(code)).to_have_count(0)

    def cells(self, code: str) -> dict[str, str]:
        """{'Status': 'Open', 'Priority': 'Normal', 'Raised By': ..., 'Assigned To': ..., 'Submitted Via': ..., 'Created': ...} of a row."""
        names = ["Status", "Priority", "Raised By", "Assigned To", "Submitted Via", "Created"]
        values = [c.strip() for c in self.row(code).get_by_role("cell").all_inner_texts()][1:7]
        return dict(zip(names, values))

    def total(self) -> int:
        return int(re.match(r"\d+", self.counter.inner_text()).group(0))

    # filters
    def find(self, text: str) -> None:
        """Type into Search and wait for the list that answers (a request with `search=`); an empty text just clears the box."""
        if not text:
            self.search_box.fill("")
            return
        with self.page.expect_response(lambda r: r.request.method == "GET" and "/api/" in r.url and "search=" in r.url):
            self.search_box.fill(text)

    def filter_status(self, option: str) -> None:
        self.choose("Status", option)

    def filter_priority(self, option: str) -> None:
        self.choose("Priority", option)

    # row actions
    def actions_of(self, code: str) -> list[str]:
        self.row(code).get_by_role("button", name="Open actions").click()
        items = [i.strip() for i in self.page.get_by_role("menuitem").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return items

    def do(self, code: str, action: str) -> None:
        self.row(code).get_by_role("button", name="Open actions").click()
        self.page.get_by_role("menuitem", name=action, exact=True).click()

    def open_details(self, code: str) -> "TicketDetails":
        self.row(code).get_by_role("button", name=code, exact=True).click()
        return TicketDetails(self.page, code).wait_until_open()

    # pager
    def pager_button(self, name: str) -> Locator:
        return self.page.get_by_role("button", name=name, exact=True)

    def go_to(self, number: int) -> None:
        self.pager_button(f"Go to page {number}").click()


class MyTicketsPage(HelpdeskListPage):
    PATH = "/oem/helpdesk/my-tickets"
    HEADING = "Support Tickets"


class SupportQueuePage(HelpdeskListPage):
    PATH = "/oem/helpdesk/assigned-tickets"
    HEADING = "Support Queue"

    def change_status(self, code: str) -> "ChangeStatusForm":
        self.do(code, "Change Status")
        return ChangeStatusForm(self.page).wait_until_open()

    def close_ticket(self, code: str) -> "CloseTicketForm":
        self.do(code, "Close Ticket")
        return CloseTicketForm(self.page).wait_until_open()


class TicketDetails:
    """The details of one ticket (opened from a row, or after a status change / close)."""

    def __init__(self, page: Page, code: str) -> None:
        self.page = page
        self.code = code
        self.title = page.get_by_role("heading", level=1).filter(has_not_text=re.compile(r"^Support"))
        self.back_button = page.get_by_role("button", name="Back to Tickets")
        self.attachment_link = page.get_by_role("link", name="View Ticket Attachment")
        self.entries = page.get_by_role("article")

    def wait_until_open(self) -> "TicketDetails":
        expect(self.page.get_by_role("heading", name="Ticket Details")).to_be_visible()
        expect(self.page.get_by_text(self.code, exact=True)).to_be_visible()
        return self

    def fields(self) -> dict[str, str]:
        """{'Raised By': ..., 'Assigned To': ..., 'Status': ..., 'Submitted Via': ..., 'Priority': ..., 'Raised On': ..., 'Last Updated': ...}"""
        terms = [(t.text_content() or "").strip() for t in self.page.get_by_role("term").all()]  # text_content: the screen shows the labels in capitals (CSS)
        definitions = [(d.text_content() or "").strip() for d in self.page.get_by_role("definition").all()]
        return dict(zip(terms, definitions))

    def description(self) -> str:
        """The text under the 'Description' heading."""
        after = self.page.locator("main").inner_text().split("Description", 1)[1]
        return after.strip().split("\n\n")[0].strip()

    def activity(self) -> list[str]:
        """The activity entries as text (oldest first), each 'author | kind | time | message'."""
        return [" | ".join(line.strip() for line in entry.inner_text().splitlines() if line.strip()) for entry in self.entries.all()]

    def expect_no_activity(self) -> None:
        expect(self.page.get_by_text("No activity is available for this ticket.")).to_be_visible()


class _TicketForm:
    HEADING = ""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.heading = page.get_by_role("heading", name=self.HEADING)
        self.note = page.get_by_role("textbox", name="Optional note")
        self.cancel_button = page.get_by_role("button", name="Cancel")

    def wait_until_open(self):
        expect(self.heading).to_be_visible()
        return self


class ChangeStatusForm(_TicketForm):
    HEADING = "Change Status"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.status = page.get_by_role("combobox", name="Status")
        self.save_button = page.get_by_role("button", name="Save Changes")

    def options(self) -> list[str]:
        self.status.click()
        items = [o.strip() for o in self.page.locator("[role=option]:visible").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return items

    def save(self, status: str, note: str | None = None) -> None:
        self.status.click()
        self.page.locator("[role=option]:visible").filter(has_text=re.compile(rf"^\s*{re.escape(status)}\s*$")).first.click()
        if note is not None:
            self.note.fill(note)
        self.save_button.click()


class CloseTicketForm(_TicketForm):
    HEADING = "Close Ticket"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.confirm_button = page.get_by_role("button", name="Confirm Close")

    def confirm(self, note: str | None = None) -> None:
        if note is not None:
            self.note.fill(note)
        self.confirm_button.click()


class NewTicketPage(OemPanelPage):
    PATH = "/oem/helpdesk/create"
    HEADING = "New Ticket"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.reason = page.get_by_role("combobox", name="Ticket Reason *")
        self.other_reason = page.get_by_role("textbox", name="Other Reason")
        self.description = page.get_by_role("textbox", name="Description *")
        self.priority = page.get_by_role("combobox", name="Priority *")
        self.send_to = page.get_by_role("combobox", name="Send To")
        self.attachment = page.locator("input[type=file]")
        self.submit_button = page.get_by_role("button", name="Submit Ticket")
        self.submitted = page.get_by_text("Your ticket has been submitted")

    def open(self):
        super().open()
        expect(self.reason).to_be_enabled()
        return self

    def pick(self, combobox: Locator, option: str) -> None:
        combobox.click()
        self.page.locator("[role=option]:visible").filter(has_text=option).first.click()

    def fill(self, reason: str = "Device not working", description: str = "", priority: str | None = None, send_to: str | None = None, other_reason: str | None = None) -> None:
        self.pick(self.reason, reason)
        if other_reason is not None:
            self.other_reason.fill(other_reason)
        self.description.fill(description)
        if priority:
            self.pick(self.priority, priority)
        if send_to:
            self.pick(self.send_to, send_to)

    def submit(self) -> None:
        self.submit_button.click()

    def ticket_code(self) -> str:
        expect(self.submitted).to_be_visible()
        return TICKET_CODE.search(self.main.inner_text()).group(0)
