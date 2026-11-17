"""
OEM Helpdesk (Support Tickets) API, as the OEM panel uses it.

  GET   /api/user/ticket                   "Support Tickets": the tickets the signed-in user raised
  GET   /api/helpdesk/tickets              "Support Queue": the tickets the user raised or that are with the user (with their activity log)
  POST  /api/user/ticket                   multipart: title (the reason), description, priority (0 / 1), oem_id (optional), file (optional)
  POST  /api/public/ticket                 the public Support Center: title, description, contact_no, priority, oem_id (no login)
  PATCH /api/helpdesk/tickets/{id}/status  {"status": opened | assigned | in_progress | completed, "message"}  - by the current owner
  PATCH /api/helpdesk/tickets/{id}/close   {"message"}                                                         - by the person who raised it, or the owner
  PATCH /api/helpdesk/tickets/{id}/assign  State Admin action; the OEM is refused

Tickets cannot be deleted, so every ticket a test creates stays in the system: the tests keep that to a minimum (shared tickets are looked up by
a marker in their description and reused; see `shared_ticket`).
"""

from utils import data_generator as data
from utils.api_client import ApiClient

USER_TICKETS = "/api/user/ticket"
QUEUE = "/api/helpdesk/tickets"
PUBLIC_TICKETS = "/api/public/ticket"
PUBLIC_OEMS = "/api/public/ticket/oems"

REASON = "Device not working"  # one of the fixed ticket reasons (it becomes the ticket's title)
FINAL = ("completed", "closed")


def tickets(client: ApiClient, path: str = QUEUE, **params) -> list[dict]:
    """The tickets on the first page (100 at most) of a list endpoint."""
    query = "&".join(f"{k}={v}" for k, v in {"per_page": 100, **params}.items())
    return client.get(f"{path}?{query}").json()["data"]["tickets"]["data"]


def listing(client: ApiClient, path: str = QUEUE, **params) -> dict:
    """The paging block of a list endpoint ({'total', 'last_page', 'current_page', 'per_page', 'data'})."""
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"{path}?{query}").json()["data"]["tickets"]


def find(client: ApiClient, text: str, status: str | None = None) -> dict | None:
    """The newest ticket the client can see whose code, title or description contains `text` (and, when given, that has this status)."""
    for ticket in tickets(client, QUEUE, search=text.replace(" ", "+")):
        if status is None or ticket["status"] == status:
            return ticket
    return None


def ticket_by_code(client: ApiClient, code: str) -> dict:
    found = next((t for t in tickets(client, QUEUE, search=code) if t["ticket_code"] == code), None)
    assert found, f"ticket {code} is not in the queue of this account"
    return found


def raise_ticket(client: ApiClient, description: str, *, title: str = REASON, priority: bool = False, oem_id: int | None = None, file: dict | None = None):
    """Raise a ticket as a signed-in user (what the New Ticket form sends). Returns the API response; a 200 means a ticket now exists for good."""
    fields = {"title": title, "description": description, "priority": "1" if priority else "0"}
    if oem_id is not None:
        fields["oem_id"] = str(oem_id)
    if file is not None:
        fields["file"] = file
    return client.request("POST", USER_TICKETS, multipart=fields)


def raise_public_ticket(anonymous: ApiClient, description: str, oem_id: int | None = None, title: str = REASON) -> str:
    """Raise a ticket from the public Support Center (no login). With `oem_id` it goes straight to that OEM (status 'assigned'). Returns the code."""
    fields = {"title": title, "description": description, "contact_no": "9" + data.unique_suffix()[-9:], "priority": "0"}
    if oem_id is not None:
        fields["oem_id"] = str(oem_id)
    response = anonymous.request("POST", PUBLIC_TICKETS, multipart=fields, token=None)
    assert response.status == 200, f"public ticket failed: {response.status} {response.text()[:200]}"
    return response.json()["data"]["ticket_code"]


def set_status(client: ApiClient, ticket_id: int, status: str, message: str | None = None):
    body = {"status": status}
    if message is not None:
        body["message"] = message
    return client.patch(f"{QUEUE}/{ticket_id}/status", json=body)


def close(client: ApiClient, ticket_id: int, message: str | None = None):
    return client.patch(f"{QUEUE}/{ticket_id}/close", json={"message": message} if message is not None else {})


def events(ticket: dict) -> list[str]:
    """The kinds of activity the ticket has recorded, oldest first (created, assigned, status_changed, closed)."""
    return [m["event_type"] for m in reversed(ticket.get("messages") or [])]


def count(client: ApiClient, path: str = USER_TICKETS) -> int:
    return client.get(f"{path}?per_page=1").json()["data"]["tickets"]["total"]
