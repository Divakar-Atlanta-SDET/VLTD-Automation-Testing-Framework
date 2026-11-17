"""
Fitment Centre > Helpdesk (Support Tickets), through the screen.

Modelled on `tests/oem_panel/test_oem_helpdesk.py`. Confirmed by manual exploration 2026-11-05: the FC role has only
ONE ticket list (`/fc/helpdesk/my-tickets`, same heading/columns/cell order as the OEM's), not two - there is no
FC "Support Queue": `/fc/helpdesk/assigned-tickets` redirects back to `/fc/helpdesk`, and a ticket's row menu only
ever offers "View Details" and "Close Ticket", never "Change Status". The New Ticket form (including its "Send To"
field, which lists every OEM in the system, same as the OEM's own) is otherwise identical. So this file has no
equivalent of the OEM suite's queue-navigation test, routed-ticket lifecycle test, or queue-only status filter -
deliberately, not an oversight (an FC raises tickets; it does not resolve ones routed to it, because nothing can be
routed to it in the first place).

Tickets cannot be deleted. The tests reuse the shared `fc_shared_own` ticket (see conftest) and create fresh ones
per run where a test needs to change something. Everything that could create a ticket without needing to is
intercepted (aborted or answered by a stub).
"""

import json
import re

import pytest
from playwright.sync_api import Page, expect

from pages.fc_panel.helpdesk import FcMyTicketsPage, FcNewTicketPage, TicketDetails
from utils import data_generator as data
from utils import oem_helpdesk_api as hd
from utils.api_client import ApiClient
from utils.file_utils import png_bytes

pytestmark = [pytest.mark.fc_panel, pytest.mark.xdist_group("fc-helpdesk")]

FIELDS = re.compile(rb'name="([a-z_]+)"\r\n\r\n([^\r]*)')


def own_ticket_by_code(client: ApiClient, code: str) -> dict:
    """Like `oem_helpdesk_api.ticket_by_code`, but against `/api/user/ticket` - `/api/helpdesk/tickets` (what
    `ticket_by_code` normally searches) answers 200 but always empty for the FC role (see conftest.py)."""
    found = next((t for t in hd.tickets(client, hd.USER_TICKETS, search=code) if t["ticket_code"] == code), None)
    assert found, f"ticket {code} is not in this account's own tickets"
    return found


@pytest.fixture(scope="module")
def fc_me(fc_api: ApiClient) -> dict:
    return fc_api.get("/api/auth/me").json()["data"]


def _stub_created(route, request, sent: list | None = None, code: str = "VLTD-20260101-STUBSTUB", assignment: str = "transport_commissioner", status: str = "opened") -> None:
    if request.method != "POST":
        route.continue_()
        return
    if sent is not None:
        sent.append({k.decode(): v.decode() for k, v in FIELDS.findall(request.post_data_buffer or b"")})
    route.fulfill(status=200, content_type="application/json",
                  body=json.dumps({"status": True, "message": "ticket created successfully", "data": {"ticket_code": code, "status": status, "assignment_mode": assignment}}))


def _stub_list(total: int, status: str = "opened"):
    def handler(route, request):
        page_match, size_match = re.search(r"[?&]page=(\d+)", request.url), re.search(r"per_page=(\d+)", request.url)
        page_no, per_page = int(page_match.group(1)) if page_match else 1, int(size_match.group(1)) if size_match else 10
        first = (page_no - 1) * per_page
        rows = [{"id": 9000 + i, "ticket_code": f"VLTD-20260101-STUB{i + 1:04d}", "title": f"Stub ticket {i + 1}", "description": "stub", "status": status, "created_by": "x",
                 "ticket_against": None, "attachment_url": None, "priority": False, "current_owner": None, "created_at": "2026-01-01T06:00:00.000000Z",
                 "updated_at": "2026-01-01T06:00:00.000000Z", "assignment_mode": "transport_commissioner", "created_by_me": True,
                 "creator": {"id": "x", "name": "Stub FC", "role": {"name": "Fitment Centre Admin", "code": "fitment_centre_admin"}}, "messages": []}
                for i in range(first, min(first + per_page, total))]
        body = {"status": True, "message": "ok", "data": {"tickets": {"current_page": page_no, "data": rows, "from": first + 1 if rows else None, "to": first + len(rows) if rows else None,
                                                                      "last_page": max(1, -(-total // per_page)), "per_page": per_page, "total": total}}}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
    return handler


# ── The ticket list ─────────────────────────────────────────────────────────────

def test_the_ticket_list_and_the_new_ticket_form_are_linked(fc_page: Page) -> None:
    my_tickets = FcMyTicketsPage(fc_page).open()
    for control in (my_tickets.search_box, my_tickets.refresh_button, my_tickets.new_ticket_link):
        expect(control).to_be_visible()
    expect(my_tickets.reset_button).to_be_disabled()
    # the OEM's identical check (`test_the_two_lists_and_the_new_ticket_form_are_linked`) currently fails the same
    # way via get_by_role("columnheader", ...): the table's <th> cells have no `scope` attribute, so Chromium does
    # not expose them with the columnheader role - a pre-existing issue, not FC-specific, so this checks the <th>
    # text directly instead of relying on that role.
    for column in ("Ticket", "Status", "Priority", "Raised By", "Assigned To", "Submitted Via", "Created", "Actions"):
        expect(fc_page.locator("th").filter(has_text=column)).to_be_visible()

    my_tickets.new_ticket_link.click()
    expect(fc_page).to_have_url(re.compile(r"/fc/helpdesk/create$"))
    expect(FcNewTicketPage(fc_page).heading).to_be_visible()


def test_my_tickets_lists_a_ticket_the_fc_raised(fc_page: Page, fc_api: ApiClient, fc_me: dict, fc_shared_own: dict) -> None:
    page = FcMyTicketsPage(fc_page).open()
    expect(page.counter).to_have_text(f"{hd.count(fc_api, hd.USER_TICKETS)} tickets")

    page.find("AUTO HD FC shared own")

    assert page.cells(fc_shared_own["ticket_code"]) == {
        "Status": "Open", "Priority": "Normal", "Raised By": fc_me["name"], "Assigned To": "Unassigned", "Submitted Via": "Transport Department",
        "Created": page.cells(fc_shared_own["ticket_code"])["Created"],
    }


def test_the_details_of_a_ticket(fc_page: Page, fc_me: dict, fc_shared_own: dict) -> None:
    code = fc_shared_own["ticket_code"]
    page = FcMyTicketsPage(fc_page).open()
    page.find("AUTO HD FC shared own")

    details = page.open_details(code)

    fields = details.fields()
    assert (fields["Raised By"], fields["Assigned To"], fields["Status"], fields["Submitted Via"], fields["Priority"]) == (fc_me["name"], "Unassigned", "Open", "Transport Department", "Normal")
    assert {"Raised On", "Last Updated"} <= fields.keys()
    assert "AUTO HD FC shared own" in details.description()
    expect(details.title).to_have_text(fc_shared_own["title"])
    details.back_button.click()
    expect(page.table).to_be_visible()


def test_a_ticket_offers_only_view_and_close_never_change_status(fc_page: Page, fc_shared_own: dict) -> None:
    """Confirms the FC role is never offered a resolver action (see module docstring)."""
    page = FcMyTicketsPage(fc_page).open()
    page.find("AUTO HD FC shared own")

    assert page.actions_of(fc_shared_own["ticket_code"]) == ["View Details", "Close Ticket"]


# ── Raising a ticket ──────────────────────────────────────────────────────────

def test_a_ticket_raised_through_the_form_is_stored_listed_and_can_be_closed(fc_page: Page, fc_api: ApiClient) -> None:
    description = f"AUTO HD FC form {data.unique_suffix()} - raised by the Helpdesk test, please ignore."
    form = FcNewTicketPage(fc_page).open()
    form.fill("Tracking or location issue", description)

    with fc_page.expect_response(lambda r: r.url.endswith(hd.USER_TICKETS) and r.request.method == "POST") as sent:
        form.submit()

    assert sent.value.status == 200, sent.value.text()[:300]
    code = form.ticket_code()
    expect(fc_page.get_by_text("Awaiting Transport Department assignment")).to_be_visible()
    stored = own_ticket_by_code(fc_api, code)
    assert (stored["status"], stored["assignment_mode"], stored["title"], stored["priority"], stored["description"]) == (
        "opened", "transport_commissioner", "Tracking or location issue", False, description)
    # `/api/user/ticket` (unlike the OEM's `/api/helpdesk/tickets`) does not return an activity log in its list
    # response at all - confirmed 2026-11-05 (`stored["messages"]` is always `[]` here, by design, not a bug; see
    # conftest.py's `_find_own`). The creation entry is instead confirmed below from the real detail page.

    page = FcMyTicketsPage(fc_page).open()
    page.find(code)
    assert page.cells(code)["Status"] == "Open" and page.cells(code)["Submitted Via"] == "Transport Department"
    fc_page.reload()
    expect(FcMyTicketsPage(fc_page).row(code)).to_be_visible()
    details = FcMyTicketsPage(fc_page).open_details(code)
    assert details.description() == description

    # Close Ticket: Cancel changes nothing, Confirm Close ends the ticket for good
    # (no activity-log check here - see BUG-083: the FC role's ticket detail page never shows one at all, not even
    # the creation entry OEM's identical screen shows; confirmed separately below as its own regression test)
    page = FcMyTicketsPage(fc_page).open()
    page.find(code)
    page.close_ticket(code).cancel_button.click()
    TicketDetails(fc_page, code).wait_until_open()
    assert own_ticket_by_code(fc_api, code)["status"] == "opened"
    page = FcMyTicketsPage(fc_page).open()
    page.find(code)
    page.close_ticket(code).confirm("AUTO HD: closed by the test")
    details = TicketDetails(fc_page, code).wait_until_open()
    assert details.fields()["Status"] == "Closed"
    closed = own_ticket_by_code(fc_api, code)
    assert closed["status"] == "closed"
    again = hd.close(fc_api, closed["id"], "again")
    assert again.status == 422 and "final status" in again.text(), "a closed ticket can be closed again"


def test_a_ticket_sent_to_an_oem_carries_the_oem_and_the_priority(fc_page: Page) -> None:
    """The request is answered by a stub, so no ticket is created."""
    sent: list[dict] = []
    fc_page.route(f"**{hd.USER_TICKETS}", lambda route, request: _stub_created(route, request, sent, assignment="direct_oem", status="assigned"))
    form = FcNewTicketPage(fc_page).open()
    form.fill("Device not working", "AUTO HD FC stubbed - never sent to the server", priority="Priority", send_to="TATA MOTORS")

    form.submit()

    expect(fc_page.get_by_text("Sent to OEM support")).to_be_visible()
    assert len(sent) == 1 and sent[0]["title"] == "Device not working" and sent[0]["priority"] == "1" and "oem_id" in sent[0]


def test_the_form_refuses_an_empty_submit_and_sends_nothing(fc_page: Page) -> None:
    sent: list[str] = []
    fc_page.route(f"**{hd.USER_TICKETS}", lambda route, request: (sent.append(request.method), route.abort()) if request.method == "POST" else route.continue_())
    form = FcNewTicketPage(fc_page).open()

    form.submit()

    expect(fc_page.get_by_text("Select a ticket reason.")).to_be_visible()
    expect(fc_page.get_by_text("Description is required.")).to_be_visible()
    assert not sent
    expect(fc_page).to_have_url(re.compile(r"/fc/helpdesk/create$"))


@pytest.mark.parametrize("blank", ["   ", "\t"], ids=["spaces", "tab"])
def test_a_description_of_blanks_is_refused(fc_page: Page, blank: str) -> None:
    sent: list[str] = []
    fc_page.route(f"**{hd.USER_TICKETS}", lambda route, request: (sent.append(request.method), route.abort()) if request.method == "POST" else route.continue_())
    form = FcNewTicketPage(fc_page).open()
    form.fill("Device not working", blank)

    form.submit()

    expect(fc_page.get_by_text("Description is required.")).to_be_visible()
    assert not sent


def test_the_other_reason_must_be_filled_in(fc_page: Page) -> None:
    sent: list[str] = []
    fc_page.route(f"**{hd.USER_TICKETS}", lambda route, request: (sent.append(request.method), route.abort()) if request.method == "POST" else route.continue_())
    form = FcNewTicketPage(fc_page).open()
    form.fill("Other", "AUTO HD FC other reason left empty", other_reason="   ")

    form.submit()

    expect(form.submitted).to_have_count(0)
    assert not sent
    expect(fc_page).to_have_url(re.compile(r"/fc/helpdesk/create$"))


def test_the_fields_stop_at_their_limits(fc_page: Page) -> None:
    form = FcNewTicketPage(fc_page).open()
    form.pick(form.reason, "Other")

    form.description.fill("d" * 2500)
    form.other_reason.fill("r" * 300)

    assert len(form.description.input_value()) == 2000
    assert len(form.other_reason.input_value()) == 140


def test_a_double_click_on_submit_sends_one_request(fc_page: Page) -> None:
    sent: list[dict] = []
    fc_page.route(f"**{hd.USER_TICKETS}", lambda route, request: _stub_created(route, request, sent))
    form = FcNewTicketPage(fc_page).open()
    form.fill("Device not working", "AUTO HD FC double click - stubbed")

    form.submit_button.dblclick()

    expect(form.submitted).to_be_visible()
    fc_page.wait_for_timeout(500)
    assert len(sent) == 1


# ── Search and filters ────────────────────────────────────────────────────────

def test_search_finds_a_ticket_by_code_in_any_case_and_by_its_description(fc_page: Page, fc_shared_own: dict) -> None:
    page = FcMyTicketsPage(fc_page).open()
    code = fc_shared_own["ticket_code"]

    page.find(code.lower())
    assert page.codes() == [code]

    page.find("AUTO HD FC shared own")
    page.expect_codes(present=[code])


def test_a_search_without_a_match_says_so(fc_page: Page) -> None:
    page = FcMyTicketsPage(fc_page).open()

    page.find("no-such-ticket-" + data.unique_suffix())

    expect(page.table.get_by_text("No tickets match these filters")).to_be_visible()
    expect(page.counter).to_have_text("0 tickets")


def test_the_status_and_priority_filters_narrow_the_list_and_reset_restores_it(fc_page: Page, fc_api: ApiClient, fc_shared_own: dict) -> None:
    """Each ticket is searched by its own specific marker, not the generic 'AUTO HD FC' prefix - this account has
    accumulated enough tickets across test runs that a generic search no longer fits on the list's own first page,
    which is a test-data-volume artifact, not a product bug (see the pager tests above, which cover paging itself)."""
    priority_marker = f"AUTO HD FC priority filter {data.unique_suffix()}"
    priority_code = own_ticket_by_code(fc_api, hd.raise_ticket(fc_api, f"{priority_marker} - please ignore.", priority=True).json()["data"]["ticket_code"])["ticket_code"]

    page = FcMyTicketsPage(fc_page).open()
    page.find("AUTO HD FC shared own")
    page.expect_codes(present=[fc_shared_own["ticket_code"]])
    page.filter_status("Open")
    page.expect_codes(present=[fc_shared_own["ticket_code"]])
    page.filter_status("All statuses")
    page.filter_priority("Priority")
    page.expect_codes(absent=[fc_shared_own["ticket_code"]])

    page.reset_button.click()
    page.find(priority_marker)
    page.filter_priority("Priority")
    page.expect_codes(present=[priority_code])

    page.reset_button.click()

    expect(page.search_box).to_have_value("")
    expect(page.reset_button).to_be_disabled()
    expect(page.counter).to_have_text(f"{hd.count(fc_api, hd.USER_TICKETS)} tickets")


def test_the_refresh_button_loads_the_list_again(fc_page: Page) -> None:
    page = FcMyTicketsPage(fc_page).open()

    with fc_page.expect_response(lambda r: r.url.endswith(hd.USER_TICKETS + "?page=1&per_page=10") and r.status == 200):
        page.refresh_button.click()


# ── Paging, loading and failures (the answers are stubs) ──────────────────────

def test_the_pager_walks_through_every_page(fc_page: Page) -> None:
    fc_page.route(re.compile(r".*/api/user/ticket\?.*"), _stub_list(total=25))
    page = FcMyTicketsPage(fc_page).open()
    expect(page.summary).to_have_text("Showing 1 to 10 of 25 results")
    expect(page.counter).to_have_text("25 tickets")
    assert len(page.codes()) == 10
    expect(page.pager_button("First page")).to_be_disabled()
    expect(page.pager_button("Previous page")).to_be_disabled()

    page.pager_button("Next page").click()
    expect(page.summary).to_have_text("Showing 11 to 20 of 25 results")
    page.go_to(3)
    expect(page.summary).to_have_text("Showing 21 to 25 of 25 results")
    assert len(page.codes()) == 5
    expect(page.pager_button("Next page")).to_be_disabled()
    expect(page.pager_button("Last page")).to_be_disabled()

    page.pager_button("First page").click()
    expect(page.summary).to_have_text("Showing 1 to 10 of 25 results")


def test_a_list_that_fails_to_load_is_reported_and_not_shown_as_empty(fc_page: Page) -> None:
    fc_page.route(re.compile(r".*/api/user/ticket\?.*"), lambda route: route.fulfill(status=500, content_type="application/json", body=json.dumps({"success": False, "message": "Server Error"})))
    page = FcMyTicketsPage(fc_page)
    fc_page.goto(page.PATH)

    expect(page.table.get_by_text("Unable to load tickets")).to_be_visible()
    expect(page.table.get_by_text("The server could not complete the request. Please try again later.")).to_be_visible()
    expect(page.table.get_by_text("No tickets yet")).to_have_count(0)


# ── Defects (expected failures; see bug_report.md) ────────────────────────────

@pytest.mark.xfail(reason="BUG-067: 'View Ticket Attachment' opens the portal's start page instead of the attached file - confirmed reproducing for an FC-raised ticket too", strict=False)
def test_the_attachment_link_opens_the_attached_file(fc_page: Page, fc_api: ApiClient) -> None:
    marker = f"AUTO HD FC attachment {data.unique_suffix()}"
    file = {"name": "helpdesk-proof.png", "mimeType": "image/png", "buffer": png_bytes()}
    response = hd.raise_ticket(fc_api, f"{marker} - ticket for the Fitment Centre Helpdesk tests, please ignore.", file=file)
    assert response.status == 200, response.text()[:200]
    code = response.json()["data"]["ticket_code"]

    page = FcMyTicketsPage(fc_page).open()
    page.find(marker)
    details = page.open_details(code)

    with fc_page.context.expect_page() as opened:
        details.attachment_link.click()

    tab = opened.value
    tab.wait_for_load_state("networkidle")
    assert "/storage/tickets/" in tab.url, f"the link opened {tab.url} ('{tab.title()}') instead of the file"


@pytest.mark.xfail(reason="BUG-071: the counter says '1 tickets' for a single ticket - confirmed reproducing for the FC's own ticket list too", strict=False)
def test_the_counter_says_ticket_for_a_single_ticket(fc_page: Page, fc_shared_own: dict) -> None:
    page = FcMyTicketsPage(fc_page).open()

    page.find(fc_shared_own["ticket_code"])

    expect(page.counter).to_have_text("1 ticket")


@pytest.mark.xfail(reason="BUG-083: the FC role's ticket detail page never shows any activity log, not even the creation entry, for a ticket it raised and closed itself", strict=False)
def test_the_details_of_a_ticket_show_its_creation_in_the_activity_log(fc_page: Page, fc_api: ApiClient, fc_me: dict) -> None:
    marker = f"AUTO HD FC activity {data.unique_suffix()}"
    response = hd.raise_ticket(fc_api, f"{marker} - ticket for the Fitment Centre Helpdesk tests, please ignore.")
    assert response.status == 200, response.text()[:200]
    code = response.json()["data"]["ticket_code"]

    page = FcMyTicketsPage(fc_page).open()
    page.find(marker)
    details = page.open_details(code)

    assert any(f"Ticket {code} created by {fc_me['name']}" in entry for entry in details.activity())
