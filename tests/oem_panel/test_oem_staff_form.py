"""
OEM > Management > User Management > Staff: the parts of the module that can be reached today.

BUG-039 blocks the module: `GET /api/oem/users` and `POST /api/oem/users` answer 403 for the OEM Admin (who holds all 41 permissions of the
OEM catalogue, none of which guards staff), so no staff member can be listed, registered, viewed, edited, searched or suspended, and no
OEM staff account exists to test staff access with. What does work is the Register OEM Staff form and its permission picker, the
shape of the request it sends and the pages' own error handling; those are tested here. The request is intercepted and aborted, so
no test can ever create a staff account. The guide does not describe OEM staff; every rule below is taken from the screen.

The tests of the blocked workflows (register, list) are expected failures that describe the behaviour the product owner confirmed
("the OEM manages its own staff") and will pass when BUG-039 is fixed; they will then create one staff account each.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.staff import OemStaffFormPage, OemStaffListPage
from utils import data_generator as data
from utils.api_client import ApiClient

pytestmark = [pytest.mark.oem_panel]

CATALOGUE = "/api/oem/permissions"
STAFF = "/api/oem/users"


def _catalogue(oem_api: ApiClient) -> list[dict]:
    return oem_api.get(CATALOGUE).json()["data"]["permissions"]


@pytest.fixture
def aborted_registrations(oem_page: Page) -> list[dict]:
    """Every registration request the form sends (as JSON); each is aborted, so nothing can be created."""
    sent: list[dict] = []

    def handle(route, request) -> None:
        if request.method == "POST":
            sent.append(request.post_data_json)
            route.abort()
        else:
            route.continue_()

    oem_page.route(f"**{STAFF}", handle)
    return sent


@pytest.fixture
def form(oem_page: Page, aborted_registrations) -> OemStaffFormPage:
    return OemStaffFormPage(oem_page).open_new()


def _valid() -> dict:
    tag = data.unique_suffix()
    return {"name": f"AUTO Staff {tag}", "email": f"auto.staff.{tag}@example.com", "contact": "9" + tag[-9:], "password": data.PASSWORD}


# ── The permission picker ─────────────────────────────────────────────────────

def test_the_form_offers_exactly_the_permissions_of_the_oem_catalogue(form: OemStaffFormPage, oem_api: ApiClient) -> None:
    catalogue = _catalogue(oem_api)

    expect(form.counter).to_have_text(f"0 of {len(catalogue)} selected")
    groups = form.permissions_by_group()

    shown = [entry for entries in groups.values() for entry in entries]
    assert sorted(shown) == sorted((p["id"], p["name"]) for p in catalogue), "the permissions (id and name) on the screen differ from /api/oem/permissions"
    assert len(groups) == 16 and len(set(shown)) == len(shown)  # grouped, none listed twice


def test_select_all_clear_all_and_groups_move_the_counter(form: OemStaffFormPage, oem_api: ApiClient) -> None:
    total = len(_catalogue(oem_api))

    form.select_all_button.click()
    assert form.selected() == (total, total)
    form.clear_all_button.click()
    assert form.selected() == (0, total)

    form.group_checkbox("Tracking Permissions").check()  # the four tracking permissions
    assert form.selected() == (4, total)
    form.open_group(form.group_names().index("Tracking Permissions"))
    form.permission_checkbox("View Live Tracking").uncheck()
    assert form.selected() == (3, total)
    expect(form.group_checkbox("Tracking Permissions")).not_to_be_checked()  # no longer a whole group


def test_the_permission_search_narrows_the_list_and_keeps_the_selection(form: OemStaffFormPage) -> None:
    form.group_checkbox("Tracking Permissions").check()

    form.permission_search.fill("watchlist")
    expect(form.main.get_by_text("Tracking Permissions")).to_be_visible()
    expect(form.main.get_by_text("Alert Permissions")).to_have_count(0)
    form.permission_search.fill("zzzz")
    expect(form.main.get_by_text('No permissions found for "zzzz".')).to_be_visible()

    form.permission_search.fill("")
    assert form.selected()[0] == 4  # the search did not change what is selected


def test_the_request_carries_the_selected_permission_ids(form: OemStaffFormPage, oem_api: ApiClient, aborted_registrations: list[dict]) -> None:
    catalogue = {p["name"]: p["id"] for p in _catalogue(oem_api)}
    staff = _valid()
    form.fill(**staff)
    for group in ("Alert Permissions", "Dashboard Permissions"):  # one permission each: View Alerts, View Dashboard
        form.group_checkbox(group).check()

    form.submit()

    expect(form.main.get_by_text("Passwords do not match")).to_have_count(0)
    assert len(aborted_registrations) == 1
    body = aborted_registrations[0]
    assert body["name"] == staff["name"] and body["email"] == staff["email"] and body["contact_no"] == staff["contact"]
    assert body["password"] == body["password_confirmation"] == staff["password"]
    assert sorted(body["permission_ids"]) == sorted([catalogue["View Alerts"], catalogue["View Dashboard"]])


# ── Form validation (nothing is sent) ─────────────────────────────────────────

def test_an_empty_form_lists_every_required_field_and_sends_nothing(form: OemStaffFormPage, aborted_registrations: list[dict]) -> None:
    form.submit()

    for message in ("Staff Name is required", "Email is required", "Contact Number is required", "Password is required", "Confirm Password is required"):
        expect(form.error(message)).to_be_visible()
    assert not aborted_registrations


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("email", "not-an-email", "Enter a valid email"),
        ("email", "a@b", "Enter a valid email"),
        ("contact", "987654321", "Enter valid 10 digit mobile number"),
        ("contact", "5876543210", "Enter valid 10 digit mobile number"),
        ("contact", "98765abcde", "Enter valid 10 digit mobile number"),
        ("password", "Aa1xxxx", "Password must contain uppercase, lowercase, number and minimum 10 characters"),
        ("password", "abcdefghij1", "Password must contain uppercase, lowercase, number and minimum 10 characters"),
        ("password", "ABCDEFGHIJ1", "Password must contain uppercase, lowercase, number and minimum 10 characters"),
        ("password", "Abcdefghijk", "Password must contain uppercase, lowercase, number and minimum 10 characters"),
    ],
    ids=["email-no-at", "email-no-domain", "contact-9-digits", "contact-starts-5", "contact-letters", "password-short", "password-no-upper",
         "password-no-lower", "password-no-digit"],
)
def test_an_invalid_value_names_the_field_and_sends_nothing(form: OemStaffFormPage, aborted_registrations: list[dict], field: str, value: str, message: str) -> None:
    staff = {**_valid(), field: value}
    form.fill(**staff)

    form.submit()

    expect(form.error(message)).to_be_visible()
    assert not aborted_registrations


def test_mismatched_passwords_are_refused(form: OemStaffFormPage, aborted_registrations: list[dict]) -> None:
    form.fill(**_valid(), confirmation="Different@12345")

    form.submit()

    expect(form.error("Passwords do not match")).to_be_visible()
    assert not aborted_registrations


def test_the_password_fields_are_masked_and_the_fields_limit_their_length(form: OemStaffFormPage) -> None:
    assert form.password_box.get_attribute("type") == "password" and form.confirm_password_box.get_attribute("type") == "password"
    for box, limit in ((form.name_box, 100), (form.email_box, 255), (form.contact_box, 10)):
        box.fill("9" * (limit + 30))
        assert len(box.input_value()) == limit


def test_cancel_leaves_the_form_without_sending_anything(form: OemStaffFormPage, oem_page: Page, aborted_registrations: list[dict]) -> None:
    form.fill(**_valid())

    form.cancel_button.click()

    expect(oem_page).to_have_url(re.compile(r"/oem/users/staff$"))
    assert not aborted_registrations


# ── The pages and the API around the blocked workflows ────────────────────────

def test_an_unknown_staff_id_is_reported_on_the_details_page(oem_page: Page) -> None:
    oem_page.goto("/oem/users/staff/99999999")

    expect(oem_page.get_by_text("OEM Staff details not found.")).to_be_visible()


@pytest.mark.parametrize("method, path", [("GET", STAFF), ("POST", STAFF), ("GET", CATALOGUE)], ids=["list", "register", "permissions"])
@pytest.mark.parametrize("token", [None, "garbage"], ids=["no-token", "malformed-token"])
def test_staff_endpoints_require_a_login(oem_api: ApiClient, method: str, path: str, token) -> None:
    response = oem_api.request(method, path, json=None if method == "GET" else {}, token=token)

    assert response.status == 401


def test_the_oem_admin_holds_every_permission_of_the_catalogue(oem_api: ApiClient) -> None:
    catalogue = _catalogue(oem_api)
    held = {entry if isinstance(entry, str) else entry["code"] for entry in oem_api.get("/api/auth/me").json()["data"]["permissions"]}

    assert len(catalogue) == 41 and len({p["code"] for p in catalogue}) == 41
    assert {p["code"] for p in catalogue} <= held
    assert not any(re.search(r"staff|users", p["code"]) for p in catalogue), "a staff-management permission now exists: update BUG-039 and add its tests"


# ── Known defects (see bug_report.md) ─────────────────────────────────────────

BLOCKED = pytest.mark.xfail(reason="BUG-039: /api/oem/users answers 403 for the OEM Admin, so staff cannot be listed or registered", strict=False)


@BLOCKED
def test_register_a_staff_member(oem_page: Page, oem_api: ApiClient) -> None:
    staff = _valid()
    form = OemStaffFormPage(oem_page).open_new()
    form.fill(**staff)
    form.group_checkbox("Alert Permissions").check()

    with oem_page.expect_response(lambda r: r.url.endswith(STAFF) and r.request.method == "POST") as sent:
        form.submit()

    assert sent.value.status == 201, f"{sent.value.status} {sent.value.text()[:200]}"
    expect(oem_page).to_have_url(re.compile(r"/oem/users/staff$"))
    listed = oem_api.get(f"{STAFF}?search={staff['email']}").json()["data"]
    assert any(member["email"] == staff["email"] for member in listed)


@pytest.mark.xfail(
    reason="BUG-059: when the staff list cannot be loaded the page says 'No Staff found. Register a Staff member to get started.' and shows 0 in every counter, with no error",
    strict=False,
)
@pytest.mark.parametrize("status", [403, 500], ids=["forbidden", "server-error"])
def test_a_failed_staff_list_is_reported_as_an_error(oem_page: Page, status: int) -> None:
    oem_page.route(f"**{STAFF}?*", lambda route: route.fulfill(status=status, content_type="application/json", body='{"success":false,"message":"nope"}'))
    listing = OemStaffListPage(oem_page)

    listing.open()

    expect(listing.empty_state).to_have_count(0)  # an empty state says "there is nobody"; this is "could not load"
    expect(oem_page.get_by_text(re.compile(r"unable to load|could not|failed|not authori[sz]ed|permission|error", re.I)).first).to_be_visible()


@pytest.mark.xfail(
    reason="BUG-060: the form sends a staff name made of spaces only (the Fitment Center form refuses it)",
    strict=False,
)
def test_a_staff_name_of_spaces_is_refused(form: OemStaffFormPage, aborted_registrations: list[dict]) -> None:
    form.fill(**{**_valid(), "name": "   "})

    form.submit()

    assert not aborted_registrations, "the form sent a name of spaces"
    expect(form.error(re.compile(r"Staff Name is required", re.I))).to_be_visible()


@pytest.mark.xfail(
    reason="BUG-007 (also on the OEM Staff page): the status filter offers 'Approved' while the counter says 'Active'",
    strict=False,
)
def test_the_status_names_of_the_filter_and_the_counters_agree(oem_page: Page) -> None:
    listing = OemStaffListPage(oem_page).open()

    options = listing.status_options()

    assert "Active" in options and "Approved" not in options, options
