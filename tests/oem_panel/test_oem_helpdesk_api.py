"""
OEM > Helpdesk: the API behind the two lists, the form and the status / close actions.

The checks that change nothing run on the shared tickets (see conftest); every request that could create or change a ticket is made invalid on purpose or is
expected to be refused, so a failure of the server's rules would show up as a changed shared ticket or one extra ticket, not as silent damage.
"""

from datetime import date, timedelta

import pytest

from utils import oem_helpdesk_api as hd
from utils.api_client import ApiClient

pytestmark = [pytest.mark.oem_panel, pytest.mark.api, pytest.mark.xdist_group("oem-helpdesk")]

LISTS = [hd.USER_TICKETS, hd.QUEUE]
LIST_ROW_KEYS = {"id", "ticket_code", "title", "description", "status", "priority", "assignment_mode", "created_by_me", "creator", "current_owner", "created_at", "updated_at"}
STATUSES = {"opened", "assigned", "in_progress", "completed", "closed"}


def _first_error(response, field: str) -> str | None:
    return (response.json().get("errors") or {}).get(field, [None])[0]


# ── The lists ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", LISTS)
def test_a_list_has_the_agreed_shape(oem_api: ApiClient, shared_own: dict, path: str) -> None:
    response = oem_api.get(f"{path}?page=1&per_page=10")

    assert response.status == 200
    block = response.json()["data"]["tickets"]
    assert {"current_page", "last_page", "per_page", "total", "data"} <= block.keys()
    assert block["per_page"] == 10 and len(block["data"]) <= 10
    for row in block["data"]:
        assert LIST_ROW_KEYS <= row.keys(), f"missing: {LIST_ROW_KEYS - row.keys()}"
        assert row["status"] in STATUSES and isinstance(row["priority"], bool)


@pytest.mark.parametrize("path", LISTS)
def test_paging_walks_every_ticket_once(oem_api: ApiClient, shared_own: dict, path: str) -> None:
    total = hd.count(oem_api, path)
    seen: list[str] = []
    for number in range(1, total // 10 + 3):  # one page past the end
        rows = hd.tickets(oem_api, path, page=number, per_page=10)
        seen += [r["ticket_code"] for r in rows]
        if not rows:
            break

    assert len(seen) == total and len(set(seen)) == total, f"{len(seen)} rows ({len(set(seen))} different) for a total of {total}"


@pytest.mark.parametrize("path", LISTS)
@pytest.mark.parametrize(
    "query, field",
    [("per_page=0", "per_page"), ("per_page=-5", "per_page"), ("per_page=abc", "per_page"), ("per_page=101", "per_page"), ("status=bogus", "status"), ("priority=7", "priority"),
     ("from_date=garbage", "from_date"), ("to_date=2026-13-45", "to_date"), ("from_date=2026-11-05&to_date=2026-11-01", "to_date"), ("search=" + "x" * 256, "search")],
    ids=["per_page-0", "per_page-negative", "per_page-text", "per_page-101", "status-bogus", "priority-7", "from_date-text", "to_date-impossible", "to-before-from", "search-256"],
)
def test_a_list_refuses_an_invalid_filter(oem_api: ApiClient, path: str, query: str, field: str) -> None:
    response = oem_api.get(f"{path}?{query}")

    assert response.status == 422 and _first_error(response, field), f"{response.status} {response.text()[:200]}"


@pytest.mark.parametrize("path", LISTS)
def test_the_date_filters_cut_the_list(oem_api: ApiClient, shared_own: dict, path: str) -> None:
    everything = hd.count(oem_api, path)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    assert hd.listing(oem_api, path, from_date="2000-01-01", per_page=1)["total"] == everything
    assert hd.listing(oem_api, path, from_date=tomorrow, per_page=1)["total"] == 0
    assert hd.listing(oem_api, path, to_date="2000-01-01", per_page=1)["total"] == 0
    assert hd.listing(oem_api, path, to_date=tomorrow, per_page=1)["total"] == everything


@pytest.mark.parametrize("path", LISTS)
def test_the_status_and_priority_filters_only_return_what_they_name(oem_api: ApiClient, shared_own: dict, shared_for_other_oem: dict, path: str) -> None:
    shared = {"search": "AUTO+HD+shared"}  # the three shared tickets (and whatever else carries the marker), however many tickets exist
    opened = hd.tickets(oem_api, path, status="opened", **shared)
    assert shared_own["ticket_code"] in {t["ticket_code"] for t in opened} and {t["status"] for t in opened} == {"opened"}
    prioritised = hd.tickets(oem_api, path, priority=1, **shared)
    assert shared_for_other_oem["ticket_code"] in {t["ticket_code"] for t in prioritised} and all(t["priority"] for t in prioritised)
    assert not any(t["priority"] for t in hd.tickets(oem_api, path, priority=0, **shared))


# ── Raising a ticket: what the server enforces ────────────────────────────────

INVALID_TICKETS = [
    ({}, "title"),
    ({"title": ""}, "title"),
    ({"title": "t" * 141}, "title"),
    ({"description": ""}, "description"),
    ({"description": "   "}, "description"),
    ({"priority": "2"}, "priority"),
    ({"priority": "abc"}, "priority"),
    ({"oem_id": "99999999"}, "oem_id"),
    ({"oem_id": "abc"}, "oem_id"),
    ({"oem_id": "-1"}, "oem_id"),
]


@pytest.mark.parametrize("override, field", INVALID_TICKETS,
                         ids=["empty", "title-empty", "title-141", "description-empty", "description-spaces", "priority-2", "priority-text", "oem-unknown", "oem-text", "oem-negative"])
def test_a_ticket_with_an_invalid_field_is_refused_and_nothing_is_created(oem_api: ApiClient, override: dict, field: str) -> None:
    before = hd.count(oem_api)
    fields = {"title": hd.REASON, "description": "AUTO HD invalid-field probe", "priority": "0", **override} if override else {}

    response = oem_api.request("POST", hd.USER_TICKETS, multipart=fields)

    assert response.status == 422 and _first_error(response, field), f"{response.status} {response.text()[:200]}"
    assert hd.count(oem_api) == before


# ── Status changes and closing ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "body, field",
    [({"status": "bogus", "message": "x"}, "status"), ({"message": "x"}, "status"), ({}, "status"), ({"status": "in_progress", "message": "n" * 2001}, "message")],
    ids=["unknown-status", "no-status", "empty-body", "note-2001"],
)
def test_a_status_change_with_invalid_data_is_refused(oem_api: ApiClient, shared_routed: dict, body: dict, field: str) -> None:
    response = oem_api.patch(f"{hd.QUEUE}/{shared_routed['id']}/status", json=body)

    assert response.status == 422 and _first_error(response, field), f"{response.status} {response.text()[:200]}"
    assert hd.ticket_by_code(oem_api, shared_routed["ticket_code"])["status"] == "assigned"


def test_a_close_note_is_limited_to_2000_characters(oem_api: ApiClient, shared_own: dict) -> None:
    response = hd.close(oem_api, shared_own["id"], "n" * 2001)

    assert response.status == 422 and _first_error(response, "message")
    assert hd.ticket_by_code(oem_api, shared_own["ticket_code"])["status"] == "opened"


def test_a_ticket_cannot_jump_to_closed_through_the_status_action(oem_api: ApiClient, shared_routed: dict) -> None:
    response = hd.set_status(oem_api, shared_routed["id"], "closed", "skip")

    assert response.status == 403
    assert hd.ticket_by_code(oem_api, shared_routed["ticket_code"])["status"] == "assigned"


@pytest.mark.parametrize("ticket_id", ["99999999", "abc"], ids=["unknown-id", "text-id"])
@pytest.mark.parametrize("action", ["status", "close"])
def test_an_unknown_ticket_is_not_found(oem_api: ApiClient, action: str, ticket_id: str) -> None:
    response = oem_api.patch(f"{hd.QUEUE}/{ticket_id}/{action}", json={"status": "in_progress"} if action == "status" else {})

    assert response.status == 404


@pytest.mark.parametrize("assignee_type", ["oem", "user", "fitment_centre"])
def test_the_oem_cannot_assign_a_ticket(oem_api: ApiClient, shared_own: dict, other_oem_org: dict, assignee_type: str) -> None:
    """Assigning is the State Admin's action (guide 19.1)."""
    response = oem_api.patch(f"{hd.QUEUE}/{shared_own['id']}/assign", json={"assignee_type": assignee_type, "assignee_id": other_oem_org["id"]})

    assert response.status == 403, f"{response.status} {response.text()[:200]}"
    assert hd.ticket_by_code(oem_api, shared_own["ticket_code"])["status"] == "opened"


@pytest.mark.parametrize("method, path", [("DELETE", "/api/helpdesk/tickets/{id}"), ("DELETE", "/api/user/ticket/{id}"), ("PUT", "/api/helpdesk/tickets/{id}")], ids=["delete", "delete-own", "edit"])
def test_a_ticket_can_be_neither_deleted_nor_edited(oem_api: ApiClient, shared_own: dict, method: str, path: str) -> None:
    response = oem_api.request(method, path.format(id=shared_own["id"]), json={"description": "tampered"})

    assert response.status in (404, 405)
    assert hd.ticket_by_code(oem_api, shared_own["ticket_code"])["description"] == shared_own["description"]


# ── Who may see and act ───────────────────────────────────────────────────────

def test_another_oem_sees_only_what_is_sent_to_it(oem_api: ApiClient, other_oem: ApiClient, shared_routed: dict, shared_own: dict, shared_for_other_oem: dict) -> None:
    theirs = {t["ticket_code"] for t in hd.tickets(other_oem, hd.QUEUE)}
    mine = {t["ticket_code"] for t in hd.tickets(oem_api, hd.QUEUE)}

    assert shared_for_other_oem["ticket_code"] in theirs, "a ticket sent to an OEM must reach that OEM"
    assert not theirs & {shared_routed["ticket_code"], shared_own["ticket_code"]}, "another OEM sees this OEM's tickets"
    assert shared_own["ticket_code"] not in {t["ticket_code"] for t in hd.tickets(other_oem, hd.USER_TICKETS)}
    assert {shared_routed["ticket_code"], shared_own["ticket_code"], shared_for_other_oem["ticket_code"]} <= mine


@pytest.mark.parametrize("ticket_fixture", ["shared_routed", "shared_own"])
def test_another_oem_cannot_change_or_close_this_oems_tickets(other_oem: ApiClient, request, ticket_fixture: str) -> None:
    ticket = request.getfixturevalue(ticket_fixture)

    changed = hd.set_status(other_oem, ticket["id"], "in_progress", "AUTO HD: must be refused")
    closed = hd.close(other_oem, ticket["id"], "AUTO HD: must be refused")

    assert (changed.status, closed.status) == (403, 403), f"{changed.status} / {closed.status}"


def test_the_oem_cannot_work_a_ticket_it_sent_to_another_oem(oem_api: ApiClient, shared_for_other_oem: dict) -> None:
    changed = hd.set_status(oem_api, shared_for_other_oem["id"], "in_progress", "AUTO HD: must be refused")

    assert changed.status == 403 and hd.ticket_by_code(oem_api, shared_for_other_oem["ticket_code"])["status"] == "assigned"


@pytest.mark.parametrize(
    "method, path",
    [("GET", hd.USER_TICKETS), ("GET", hd.QUEUE), ("POST", hd.USER_TICKETS), ("PATCH", hd.QUEUE + "/{id}/status"), ("PATCH", hd.QUEUE + "/{id}/close")],
    ids=["list-mine", "list-queue", "raise", "status", "close"],
)
def test_the_helpdesk_needs_a_login(oem_api: ApiClient, shared_own: dict, method: str, path: str) -> None:
    response = oem_api.request(method, path.format(id=shared_own["id"]), json={"status": "in_progress"} if method == "PATCH" else None, token=None)

    assert response.status == 401


def test_a_forged_token_is_refused(oem_api: ApiClient) -> None:
    assert oem_api.get(hd.USER_TICKETS, token="abc.def.ghi").status == 401


# ── Defects (expected failures; see bug_report.md) ────────────────────────────

@pytest.mark.xfail(reason="BUG-068: a public ticket routed straight to an OEM has an empty activity log: neither its creation nor its assignment is recorded (guide 19.1)", strict=False)
def test_the_assignment_of_a_routed_ticket_is_recorded(shared_routed: dict) -> None:
    assert "assigned" in hd.events(shared_routed) or "created" in hd.events(shared_routed), f"activity of {shared_routed['ticket_code']}: {hd.events(shared_routed)}"


@pytest.mark.xfail(reason="BUG-069: the server does not enforce the 2,000-character description limit of the form (2,001 and 70,000 characters pass validation)", strict=False)
@pytest.mark.parametrize("size", [2001, 70_000])
def test_a_description_over_2000_characters_is_refused(oem_api: ApiClient, size: int) -> None:
    """Priority is invalid on purpose, so the request fails whatever the description does and no ticket can be created."""
    response = oem_api.request("POST", hd.USER_TICKETS, multipart={"title": hd.REASON, "description": "d" * size, "priority": "abc"})

    assert response.status == 422 and _first_error(response, "description"), f"description errors: {_first_error(response, 'description')}"


@pytest.mark.xfail(reason="BUG-070: the search treats % and _ as wildcards, so searching for one of them lists every ticket", strict=False)
@pytest.mark.parametrize("path", LISTS)
@pytest.mark.parametrize("term", ["%25", "_"], ids=["percent", "underscore"])
def test_a_wildcard_character_is_searched_for_literally(oem_api: ApiClient, shared_own: dict, path: str, term: str) -> None:
    everything = hd.count(oem_api, path)

    found = hd.listing(oem_api, path, search=term, per_page=1)["total"]

    assert everything > 0 and found < everything, f"searching for {term!r} listed all {found} of {everything} tickets"
