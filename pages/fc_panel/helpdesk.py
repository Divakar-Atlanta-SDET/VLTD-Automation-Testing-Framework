"""
Fitment Centre Helpdesk pages.

Confirmed by manual exploration 2026-11-05: `/fc/helpdesk/my-tickets` (also `/fc/helpdesk`) is the FC's only ticket
list - same heading, columns and cell order as the OEM's `HelpdeskListPage`. Unlike the OEM panel, there is NO
separate "Support Queue" screen for the FC role: `/fc/helpdesk/assigned-tickets` simply redirects back to
`/fc/helpdesk`, and a ticket's row menu only ever offers "View Details" and "Close Ticket" - never "Change Status".
This matches the guide: an FC raises tickets but does not resolve ones assigned to it (only an OEM, or the State
Admin, works a ticket through its status lifecycle). So this file has no `FcSupportQueuePage` / `ChangeStatusForm`
equivalent - deliberately, not an oversight.

The New Ticket form (`/fc/helpdesk/create`) is identical to the OEM's, including the "Send To" field (which lists
every OEM in the system, not just the FC's own - same breadth as the OEM's own "Send To" list, confirmed by direct
comparison, so this is consistent platform behaviour, not an FC-specific quirk).
"""

from pages.oem_panel.helpdesk import CloseTicketForm, HelpdeskListPage, NewTicketPage, TicketDetails

__all__ = ["FcMyTicketsPage", "FcNewTicketPage", "CloseTicketForm", "TicketDetails"]


class FcMyTicketsPage(HelpdeskListPage):
    PATH = "/fc/helpdesk/my-tickets"
    HEADING = "Support Tickets"

    def close_ticket(self, code: str) -> "CloseTicketForm":
        self.do(code, "Close Ticket")
        return CloseTicketForm(self.page).wait_until_open()


class FcNewTicketPage(NewTicketPage):
    PATH = "/fc/helpdesk/create"
