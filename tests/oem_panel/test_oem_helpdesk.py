"""
OEM > Helpdesk (Support Tickets), through the screen.

Source: guide 19.1 - a ticket can be raised from a panel or the public portal; the person raising it can route it straight to an OEM, otherwise the
State Admin assigns it; the flow is Opened -> Assigned -> In_progress -> Completed -> Closed and every assignment and status change is recorded with
time and person. The OEM has two lists: "Support Tickets" (what it raised) and "Support Queue" (what is with it, plus what it raised).
What the screen offers to the OEM (Change Status for the owner, Close Ticket for the person who raised it) is taken from the application itself;
the guide does not list the OEM's actions.

Tickets cannot be deleted. The tests reuse three shared 'AUTO HD shared ...' tickets (see conftest) and create two new ones per run: the one the form test
raises (and closes), and the routed ticket `fresh_routed` that the lifecycle test works through. Everything else that could create a ticket is
intercepted (aborted or answered by a stub), so it cannot reach the server.
"""

import json
import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.helpdesk import MyTicketsPage, NewTicketPage, SupportQueuePage, TicketDetails
from utils import data_generator as data
from utils import oem_helpdesk_api as hd
from utils.api_client import ApiClient

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-helpdesk")]

FIELDS = re.compile(rb'name="([a-z_]+)"\r\n\r\n([^\r]*)')


@pytest.fixture(scope="module")
def me(oem_api: ApiClient) -> dict:
    return oem_api.get("/api/auth/me").json()["data"]


def _stub_created(route, request, sent: list | None = None, code: str = "VLTD-20260101-STUBSTUB", assignment: str = "transport_commissioner", status: str = "opened") -> None:
    """Answer the 'raise a ticket' request with a success, without creating anything."""
    if request.method != "POST":
        route.continue_()
        return
    if sent is not None:
        sent.append({k.decode(): v.decode() for k, v in FIELDS.findall(request.post_data_buffer or b"")})
    route.fulfill(status=200, content_type="application/json",
                  body=json.dumps({"status": True, "message": "ticket created successfully", "data": {"ticket_code": code, "status": status, "assignment_mode": assignment}}))


def _stub_list(total: int, owner: dict | None = None, status: str = "opened"):
    """A route handler that answers a ticket list with `total` made-up tickets, 10 to a page (it follows the page / per_page of the request)."""
    def handler(route, request):
        page_match, size_match = re.search(r"[?&]page=(\d+)", request.url), re.search(r"per_page=(\d+)", request.url)
        page_no, per_page = int(page_match.group(1)) if page_match else 1, int(size_match.group(1)) if size_match else 10
        first = (page_no - 1) * per_page
        rows = [{"id": 9000 + i, "ticket_code": f"VLTD-20260101-STUB{i + 1:04d}", "title": f"Stub ticket {i + 1}", "description": "stub", "status": status, "created_by": "x",
                 "ticket_against": None, "attachment_url": None, "priority": False, "current_owner": owner, "created_at": "2026-01-01T06:00:00.000000Z",
                 "updated_at": "2026-01-01T06:00:00.000000Z", "assignment_mode": "direct_oem" if owner else "transport_commissioner", "created_by_me": owner is None,
                 "creator": {"id": "x", "name": "Stub Creator", "role": {"name": "OEM Admin", "code": "oem_admin"}}, "messages": []}
                for i in range(first, min(first + per_page, total))]
        body = {"status": True, "message": "ok", "data": {"tickets": {"current_page": page_no, "data": rows, "from": first + 1 if rows else None, "to": first + len(rows) if rows else None,
                                                                      "last_page": max(1, -(-total // per_page)), "per_page": per_page, "total": total}}}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
    return handler


# ── The two lists ─────────────────────────────────────────────────────────────

def test_the_two_lists_and_the_new_ticket_form_are_linked(oem_page: Page) -> None:
    queue = SupportQueuePage(oem_page).open()
    for control in (queue.search_box, queue.refresh_button, queue.new_ticket_link):
        expect(control).to_be_visible()
    expect(queue.reset_button).to_be_disabled()  # nothing is filtered yet
    for column in ("Ticket", "Status", "Priority", "Raised By", "Assigned To", "Submitted Via", "Created", "Actions"):
        expect(oem_page.get_by_role("columnheader", name=column)).to_be_visible()

    oem_page.get_by_role("link", name="Support Tickets").click()
    expect(oem_page).to_have_url(re.compile(r"/oem/helpdesk/my-tickets$"))
    expect(MyTicketsPage(oem_page).heading).to_be_visible()
    queue.new_ticket_link.click()
    expect(oem_page).to_have_url(re.compile(r"/oem/helpdesk/create$"))
    expect(NewTicketPage(oem_page).heading).to_be_visible()


def test_support_tickets_lists_a_ticket_the_oem_raised(oem_page: Page, oem_api: ApiClient, me: dict, shared_own: dict) -> None:
    page = MyTicketsPage(oem_page).open()
    expect(page.counter).to_have_text(f"{hd.count(oem_api)} tickets")  # as many as the API reports

    page.find("AUTO HD shared own")

    assert page.cells(shared_own["ticket_code"]) == {
        "Status": "Open", "Priority": "Normal", "Raised By": me["name"], "Assigned To": "Unassigned", "Submitted Via": "Transport Department",
        "Created": page.cells(shared_own["ticket_code"])["Created"],
    }


def test_the_support_queue_shows_a_ticket_routed_to_the_oem_and_what_can_be_done_with_it(oem_page: Page, oem_api: ApiClient, me: dict, shared_routed: dict) -> None:
    code = shared_routed["ticket_code"]
    queue = SupportQueuePage(oem_page).open()
    queue.find("AUTO HD shared routed")

    cells = queue.cells(code)
    assert (cells["Status"], cells["Priority"], cells["Raised By"], cells["Assigned To"], cells["Submitted Via"]) == ("Assigned", "Normal", "Public User", me["name"], "OEM Support")
    assert queue.actions_of(code) == ["View Details", "Change Status", "Close Ticket"]  # the owner can work the ticket; Close is offered to the owner as well
    assert code not in [t["ticket_code"] for t in hd.tickets(oem_api, hd.USER_TICKETS)], "a ticket raised by someone else is listed under 'Support Tickets'"


def test_the_details_of_a_ticket(oem_page: Page, me: dict, shared_routed: dict) -> None:
    code = shared_routed["ticket_code"]
    queue = SupportQueuePage(oem_page).open()
    queue.find("AUTO HD shared routed")

    details = queue.open_details(code)

    fields = details.fields()
    assert (fields["Raised By"], fields["Assigned To"], fields["Status"], fields["Submitted Via"], fields["Priority"]) == ("Public User", me["name"], "Assigned", "OEM Support", "Normal")
    assert {"Raised On", "Last Updated"} <= fields.keys()
    assert "AUTO HD shared routed" in details.description()
    expect(details.title).to_have_text(shared_routed["title"])
    details.back_button.click()
    expect(queue.table).to_be_visible()


# ── Raising a ticket ──────────────────────────────────────────────────────────

def test_a_ticket_raised_through_the_form_is_stored_listed_and_can_be_closed(oem_page: Page, oem_api: ApiClient, me: dict) -> None:
    description = f"AUTO HD form {data.unique_suffix()} - raised by the Helpdesk test, please ignore."
    form = NewTicketPage(oem_page).open()
    form.fill("Tracking or location issue", description)

    with oem_page.expect_response(lambda r: r.url.endswith(hd.USER_TICKETS) and r.request.method == "POST") as sent:
        form.submit()

    assert sent.value.status == 200, sent.value.text()[:300]
    code = form.ticket_code()
    expect(oem_page.get_by_text("Awaiting Transport Department assignment")).to_be_visible()
    stored = hd.ticket_by_code(oem_api, code)
    assert (stored["status"], stored["assignment_mode"], stored["title"], stored["priority"], stored["description"]) == (
        "opened", "transport_commissioner", "Tracking or location issue", False, description)
    assert hd.events(stored) == ["created"], "the creation of a ticket must be recorded in its activity"

    # listed under Support Tickets, also after a reload, with its details and its first activity entry
    page = MyTicketsPage(oem_page).open()
    page.find(code)
    assert page.cells(code)["Status"] == "Open" and page.cells(code)["Submitted Via"] == "Transport Department"
    oem_page.reload()
    expect(MyTicketsPage(oem_page).row(code)).to_be_visible()  # it is the newest ticket, so it is on the first page
    details = MyTicketsPage(oem_page).open_details(code)
    assert details.description() == description

    # Close Ticket: Cancel changes nothing, Confirm Close ends the ticket for good
    queue = SupportQueuePage(oem_page).open()
    queue.find(code)
    details = queue.open_details(code)  # the Support Queue shows the activity log, 'Support Tickets' does not
    assert any(f"Ticket {code} created by {me['name']}" in entry for entry in details.activity())
    queue = SupportQueuePage(oem_page).open()  # a fresh list again
    queue.find(code)
    queue.close_ticket(code).cancel_button.click()
    TicketDetails(oem_page, code).wait_until_open()  # Cancel returns to the ticket
    assert hd.ticket_by_code(oem_api, code)["status"] == "opened"
    queue = SupportQueuePage(oem_page).open()
    queue.find(code)
    queue.close_ticket(code).confirm("AUTO HD: closed by the test")
    details = TicketDetails(oem_page, code).wait_until_open()
    assert details.fields()["Status"] == "Closed"
    assert any("AUTO HD: closed by the test" in entry for entry in details.activity())
    closed = hd.ticket_by_code(oem_api, code)
    assert closed["status"] == "closed" and "closed" in hd.events(closed)
    again = hd.close(oem_api, closed["id"], "again")
    assert again.status == 422 and "final status" in again.text(), "a closed ticket can be closed again"


def test_a_ticket_sent_to_an_oem_carries_the_oem_and_the_priority(oem_page: Page, other_oem_org: dict) -> None:
    """The request is answered by a stub, so no ticket is created."""
    sent: list[dict] = []
    oem_page.route(f"**{hd.USER_TICKETS}", lambda route, request: _stub_created(route, request, sent, assignment="direct_oem", status="assigned"))
    form = NewTicketPage(oem_page).open()
    form.fill("Device not working", "AUTO HD stubbed - never sent to the server", priority="Priority", send_to=other_oem_org["code"])

    form.submit()

    expect(oem_page.get_by_text("Sent to OEM support")).to_be_visible()
    assert sent == [{"title": "Device not working", "description": "AUTO HD stubbed - never sent to the server", "priority": "1", "oem_id": str(other_oem_org["id"])}]


def test_the_form_refuses_an_empty_submit_and_sends_nothing(oem_page: Page) -> None:
    sent: list[dict] = []
    oem_page.route(f"**{hd.USER_TICKETS}", lambda route, request: (sent.append(request.method), route.abort()) if request.method == "POST" else route.continue_())
    form = NewTicketPage(oem_page).open()

    form.submit()

    expect(oem_page.get_by_text("Select a ticket reason.")).to_be_visible()
    expect(oem_page.get_by_text("Description is required.")).to_be_visible()
    assert not sent
    expect(oem_page).to_have_url(re.compile(r"/oem/helpdesk/create$"))


@pytest.mark.parametrize("blank", ["   ", "\t"], ids=["spaces", "tab"])
def test_a_description_of_blanks_is_refused(oem_page: Page, blank: str) -> None:
    sent: list[str] = []
    oem_page.route(f"**{hd.USER_TICKETS}", lambda route, request: (sent.append(request.method), route.abort()) if request.method == "POST" else route.continue_())
    form = NewTicketPage(oem_page).open()
    form.fill("Device not working", blank)

    form.submit()

    expect(oem_page.get_by_text("Description is required.")).to_be_visible()
    assert not sent


def test_the_other_reason_must_be_filled_in(oem_page: Page) -> None:
    sent: list[str] = []
    oem_page.route(f"**{hd.USER_TICKETS}", lambda route, request: (sent.append(request.method), route.abort()) if request.method == "POST" else route.continue_())
    form = NewTicketPage(oem_page).open()
    form.fill("Other", "AUTO HD other reason left empty", other_reason="   ")

    form.submit()

    expect(form.submitted).to_have_count(0)
    assert not sent
    expect(oem_page).to_have_url(re.compile(r"/oem/helpdesk/create$"))


def test_the_fields_stop_at_their_limits(oem_page: Page) -> None:
    form = NewTicketPage(oem_page).open()
    form.pick(form.reason, "Other")

    form.description.fill("d" * 2500)
    form.other_reason.fill("r" * 300)

    assert len(form.description.input_value()) == 2000
    assert len(form.other_reason.input_value()) == 140


def test_a_double_click_on_submit_sends_one_request(oem_page: Page) -> None:
    """The request is answered by a stub, so no ticket is created."""
    sent: list[dict] = []
    oem_page.route(f"**{hd.USER_TICKETS}", lambda route, request: _stub_created(route, request, sent))
    form = NewTicketPage(oem_page).open()
    form.fill("Device not working", "AUTO HD double click - stubbed")

    form.submit_button.dblclick()

    expect(form.submitted).to_be_visible()
    oem_page.wait_for_timeout(500)  # a second request, if there is one, is sent by now
    assert len(sent) == 1


# ── Working a routed ticket ───────────────────────────────────────────────────

def test_the_oem_works_a_routed_ticket_to_completion(oem_page: Page, oem_api: ApiClient, fresh_routed: dict) -> None:
    code, ticket_id = fresh_routed["ticket_code"], fresh_routed["id"]
    queue = SupportQueuePage(oem_page).open()
    queue.find(code)
    assert queue.cells(code)["Status"] == "Assigned"

    form = queue.change_status(code)
    assert {"In Progress", "Completed"} <= set(form.options())
    form.save("In Progress", "AUTO HD: work started")

    details = TicketDetails(oem_page, code).wait_until_open()
    assert details.fields()["Status"] == "In Progress"
    entries = " ".join(details.activity())
    assert "status changed from assigned to in_progress" in entries and "AUTO HD: work started" in entries
    assert hd.ticket_by_code(oem_api, code)["status"] == "in_progress"

    queue = SupportQueuePage(oem_page).open()  # a fresh load shows what is stored
    queue.find(code)
    assert queue.cells(code)["Status"] == "In Progress"
    queue.change_status(code).save("Completed", "AUTO HD: done")
    assert TicketDetails(oem_page, code).wait_until_open().fields()["Status"] == "Completed"

    queue = SupportQueuePage(oem_page).open()
    queue.find(code)
    assert queue.actions_of(code) == ["View Details"], "a completed ticket must offer the owner nothing more to do"
    stored = hd.ticket_by_code(oem_api, code)
    assert stored["status"] == "completed" and hd.events(stored).count("status_changed") >= 2
    refused = hd.set_status(oem_api, ticket_id, "in_progress")
    assert refused.status == 422 and "final status" in refused.text(), f"a completed ticket can be moved again: {refused.status} {refused.text()[:200]}"


# ── Search and filters ────────────────────────────────────────────────────────

def test_search_finds_a_ticket_by_code_in_any_case_and_by_its_description(oem_page: Page, shared_routed: dict, shared_own: dict) -> None:
    queue = SupportQueuePage(oem_page).open()
    code, other = shared_routed["ticket_code"], shared_own["ticket_code"]

    queue.find(code.lower())
    assert queue.codes() == [code]

    queue.find("AUTO HD shared")
    queue.expect_codes(present=[code, other])


def test_a_search_without_a_match_says_so(oem_page: Page) -> None:
    queue = SupportQueuePage(oem_page).open()

    queue.find("no-such-ticket-" + data.unique_suffix())

    expect(queue.table.get_by_text("No tickets match these filters")).to_be_visible()
    expect(queue.counter).to_have_text("0 tickets")


def test_the_status_and_priority_filters_narrow_the_list_and_reset_restores_it(oem_page: Page, oem_api: ApiClient, shared_routed: dict, shared_own: dict, shared_for_other_oem: dict) -> None:
    routed, own, away = shared_routed["ticket_code"], shared_own["ticket_code"], shared_for_other_oem["ticket_code"]
    queue = SupportQueuePage(oem_page).open()
    queue.find("AUTO HD shared")
    queue.expect_codes(present=[routed, own, away])

    queue.filter_status("Assigned")
    queue.expect_codes(present=[routed, away], absent=[own])
    queue.filter_status("Open")
    queue.expect_codes(present=[own], absent=[routed, away])
    queue.filter_status("All statuses")
    queue.filter_priority("Priority")
    queue.expect_codes(present=[away], absent=[routed, own])  # only the ticket raised with Priority

    queue.reset_button.click()

    expect(queue.search_box).to_have_value("")
    expect(queue.reset_button).to_be_disabled()
    expect(queue.counter).to_have_text(f"{hd.count(oem_api, hd.QUEUE)} tickets")


def test_the_refresh_button_loads_the_list_again(oem_page: Page) -> None:
    queue = SupportQueuePage(oem_page).open()

    with oem_page.expect_response(lambda r: r.url.endswith(hd.QUEUE + "?page=1&per_page=10") and r.status == 200):
        queue.refresh_button.click()


# ── Paging, loading and failures (the answers are stubs) ──────────────────────

def test_the_pager_walks_through_every_page(oem_page: Page) -> None:
    oem_page.route(re.compile(r".*/api/user/ticket\?.*"), _stub_list(total=25))
    page = MyTicketsPage(oem_page).open()
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


def test_a_list_that_fails_to_load_is_reported_and_not_shown_as_empty(oem_page: Page) -> None:
    oem_page.route(re.compile(r".*/api/user/ticket\?.*"), lambda route: route.fulfill(status=500, content_type="application/json", body=json.dumps({"success": False, "message": "Server Error"})))
    page = MyTicketsPage(oem_page)
    oem_page.goto(page.PATH)

    expect(page.table.get_by_text("Unable to load tickets")).to_be_visible()
    expect(page.table.get_by_text("The server could not complete the request. Please try again later.")).to_be_visible()
    expect(page.table.get_by_text("No tickets yet")).to_have_count(0)


def test_a_failed_status_change_keeps_the_form_and_is_sent_once(oem_page: Page, me: dict) -> None:
    owner = {"id": me["id"], "name": me["name"], "role": {"name": "OEM Admin", "code": "oem_admin"}}
    sent: list[str] = []
    oem_page.route(re.compile(r".*/api/helpdesk/tickets\?.*"), _stub_list(total=1, owner=owner, status="assigned"))
    oem_page.route(re.compile(r".*/api/helpdesk/tickets/9000/status"),
                   lambda route, request: (sent.append(request.method), route.fulfill(status=500, content_type="application/json", body=json.dumps({"success": False, "message": "Server Error"}))))
    queue = SupportQueuePage(oem_page).open()
    form = queue.change_status("VLTD-20260101-STUB0001")

    form.save_button.dblclick()

    expect(oem_page.get_by_text("The server could not complete the request. Please try again later.")).to_be_visible()
    expect(form.heading).to_be_visible()  # the form stays, so the user can try again
    assert len(sent) == 1


# ── Defects (expected failures; see bug_report.md) ────────────────────────────

@pytest.mark.xfail(reason="BUG-067: 'View Ticket Attachment' opens the portal's start page instead of the attached file (the /storage URL is answered by the app)", strict=False)
def test_the_attachment_link_opens_the_attached_file(oem_page: Page, shared_for_other_oem: dict) -> None:
    queue = SupportQueuePage(oem_page).open()
    queue.find("AUTO HD shared other-oem")
    details = queue.open_details(shared_for_other_oem["ticket_code"])

    with oem_page.context.expect_page() as opened:
        details.attachment_link.click()

    tab = opened.value
    tab.wait_for_load_state("networkidle")  # the app redirects the tab to its start page once it has loaded
    assert "/storage/tickets/" in tab.url, f"the link opened {tab.url} ('{tab.title()}') instead of the file"


@pytest.mark.xfail(reason="BUG-071: the counter says '1 tickets' for a single ticket", strict=False)
def test_the_counter_says_ticket_for_a_single_ticket(oem_page: Page, shared_own: dict) -> None:
    page = MyTicketsPage(oem_page).open()

    page.find(shared_own["ticket_code"])

    expect(page.counter).to_have_text("1 ticket")
