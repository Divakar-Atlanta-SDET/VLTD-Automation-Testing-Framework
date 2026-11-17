"""Inspector Management – /tc/users/inspector (the create form opens on the same route)."""

import re

from pages.administration.base_user_page import UserListPage
from utils.data_generator import InspectorData


class InspectorPage(UserListPage):
    PATH = "/tc/users/inspector"
    LIST_HEADING = "Inspector Management"
    TOTAL_LABEL = "Total Inspectors"
    CREATE_BUTTON = "Add Inspector"
    FORM_HEADING = "Add Inspector"
    SUBMIT_BUTTON = "Create Inspector"

    def fill_form(
        self,
        inspector: InspectorData,
        *,
        choose_rto: bool = True,
        confirm: str | None = None,
    ) -> tuple[str, str]:
        """Fill the form; returns the (city, rto) that were selected ("" when skipped).

        An empty `inspector.city` leaves the City select untouched; `choose_rto=False` skips the RTO.
        """
        self.fill("Name *", inspector.name)
        self.fill("Email Address *", inspector.email)
        self.fill("Contact Number *", inspector.mobile)
        city = self.choose("City *", inspector.city) if inspector.city else ""
        self.fill("Address", inspector.address)
        rto = self.choose("RTO *", re.compile(r"^DL-\d{2} - ")) if choose_rto else ""
        # this form labels its password fields differently from the others
        self.fill_passwords(
            inspector.password, confirm, password_label="Enter password", confirm_label="Confirm password"
        )
        return city, rto
