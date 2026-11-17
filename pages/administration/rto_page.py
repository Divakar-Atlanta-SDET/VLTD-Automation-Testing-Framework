"""RTO Management – /tc/users/rto and /tc/users/rto/register."""



from playwright.sync_api import expect

from pages.administration.base_user_page import UserListPage
from utils.api_client import API_PREFIX, AdminApi
from utils.data_generator import RtoData


class RtoPage(UserListPage):
    PATH = "/tc/users/rto"
    LIST_HEADING = "RTO Management"
    TOTAL_LABEL = "Total RTOs"
    CREATE_BUTTON = "Register RTO"
    FORM_HEADING = "Register RTO"
    SUBMIT_BUTTON = "Register RTO"

    def __init__(self, page) -> None:
        super().__init__(page)
        self.pin_map_center_button = page.get_by_role("button", name="Pin map center")
        self.no_location_text = page.get_by_text("No location selected")

    def existing_codes(self) -> set[str]:
        """Every RTO code (DL-NN) in use, so a new unique one can be chosen (the list shows only 10 rows - BUG-024)."""
        return {r["code"] for r in AdminApi(self.page).all_items(f"{API_PREFIX}/rtos")}

    def pin_location(self) -> None:
        """Address search is unreliable in headless mode, so pin the current map centre."""
        expect(self.no_location_text).to_be_visible()
        self.pin_map_center_button.click()
        expect(self.no_location_text).to_be_hidden()

    def fill_form(self, rto: RtoData, *, pin: bool = True, confirm: str | None = None) -> None:
        """Fill the form. An empty `rto.district` leaves the select untouched; `pin=False` skips the map."""
        self.fill("RTO Name *", rto.name)
        self.fill("RTO Code *", rto.code)
        self.fill("Contact Number *", rto.mobile)
        self.fill("Contact Email *", rto.email)
        self.fill("Address *", rto.address)
        if rto.district:
            self.choose("District *", rto.district)
        self.fill("Pincode *", rto.pincode)
        if pin:
            self.pin_location()
        self.fill("Description (Optional)", rto.description)
        self.fill_passwords(rto.password, confirm)
