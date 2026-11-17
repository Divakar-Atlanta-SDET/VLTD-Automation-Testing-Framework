"""
OEM > Management > User Management > Fitment Center: register, edit, suspend, activate, blacklist and search (guide 3 and 6.1).

The guide only says that the OEM manages the workshops that install its devices and allocates stock to its ACTIVE centres; how a
centre is registered, suspended, activated and blacklisted is taken from the screens (details page: Suspend / Blacklist on an
active centre, Activate / Blacklist on a suspended one, no action on a blacklisted one, every action asks for remarks).

A centre and its login account cannot be deleted by the application, so the tests make as few as possible:
  * `lifecycle`      the long-lived 'AUTO PG FC lifecycle' centre (made once, reused by every run); whatever a test does to it is undone
  * `disposable_fc`  a centre a test may blacklist; the one the registration test made is handed on, else a new one is registered
The OEM's own real centres (Rajendra Fitments ...) are never changed. Tests that change a status run on the one worker that also
runs the allocation tests (xdist group), because they share the OEM's centres.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.fitment_centers import FitmentCenterDetailsPage, FitmentCenterFormPage, FitmentCenterListPage
from utils import data_generator as data
from utils.api_client import ApiClient
from utils.file_utils import create_sized_png
from utils.oem_panel_api import (
    FITMENT_CENTRES, change_fitment_centre_status, edit_fitment_centre, find_fitment_centre,
    fitment_centre, fitment_centre_fields, fitment_centre_remarks, register_fitment_centre,
)

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

_spare: list[dict] = []  # active centres made by the registration test that a later test may blacklist


# ── Fixtures (`lifecycle` is in conftest.py) ──────────────────────────────────────────────────────────────────

@pytest.fixture
def disposable_fc(oem_api: ApiClient):
    """An active centre that a test may blacklist (or lose); handed on to the next test when it is still active afterwards."""
    fc = None
    while _spare and fc is None:
        candidate = fitment_centre(oem_api, _spare.pop()["id"])
        fc = candidate if candidate["status"] == "active" else None
    fc = fc or register_fitment_centre(oem_api)
    yield fc
    if fitment_centre(oem_api, fc["id"])["status"] == "active":
        _spare.append(fc)


def _centre_can_sign_in(oem_api: ApiClient, fc: dict) -> int:
    """Status of the centre's own login (200 allowed, 403 'Your account is not approved or active')."""
    anonymous = ApiClient(oem_api.api, oem_api.origin)
    return anonymous.post("/api/auth/login", json={"email": fc["email_id"], "password": data.PASSWORD}, token=None).status


def _history(oem_api: ApiClient, fc_id: int) -> list[tuple[str, str]]:
    """(type, remarks) of every status entry; entries made in the same second come back in no fixed order, so tests look entries up by their text."""
    return [(entry["type"], entry["remarks"]) for entry in fitment_centre_remarks(oem_api, fc_id)]


def _is_registration(response) -> bool:
    return response.url.endswith("/api/oem/fitment-centres") and response.request.method == "POST"


def _is_edit(response) -> bool:
    return re.search(r"/api/oem/fitment-centres/\d+$", response.url) is not None and response.request.method == "POST"


# ── Happy paths ───────────────────────────────────────────────────────────────

def test_register_a_fitment_center(oem_page: Page, oem_api: ApiClient, tmp_path) -> None:
    fields = fitment_centre_fields(oem_api)
    total_before = oem_api.get(FITMENT_CENTRES).json()["summary"]["total"]
    form = FitmentCenterFormPage(oem_page).open_new()
    coordinates = form.fill_new(fields, create_sized_png(tmp_path))

    with oem_page.expect_response(_is_registration) as sent:
        form.submit()

    assert sent.value.status == 201, sent.value.text()[:300]
    assert "created successfully" in sent.value.json()["message"]
    expect(oem_page).to_have_url(re.compile(r"/oem/users/fitment-centers$"))
    stored = find_fitment_centre(oem_api, fields["short_name"])
    _spare.append(stored)
    assert (stored["business_name"], stored["owner_name"], stored["contact_no"], stored["email_id"], stored["status"]) == (
        fields["business_name"], fields["owner_name"], fields["contact_no"], fields["email_id"], "active")
    assert stored["address"]["address_line_1"] == fields["address_line_1"] and stored["address"]["pincode"] == fields["pincode"]
    latitude, longitude = (float(part) for part in coordinates.split(", "))
    assert abs(float(stored["latitude"]) - latitude) < 1e-5 and abs(float(stored["longitude"]) - longitude) < 1e-5  # the pinned point is what was stored
    assert oem_api.get(FITMENT_CENTRES).json()["summary"]["total"] == total_before + 1

    listing = FitmentCenterListPage(oem_page).open()  # persists after a fresh load
    listing.search(fields["short_name"])
    row = listing.row(fields["business_name"])
    expect(row).to_have_count(1)
    expect(row).to_contain_text(re.compile(rf"Code: {fields['short_name']}.*{stored['rto']['code']}.*Active", re.S))
    assert _centre_can_sign_in(oem_api, stored) == 200  # the centre's login account exists


def test_edit_a_fitment_center(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    tag = data.unique_suffix()
    owner, address_2 = f"Owner {tag}", f"Block {tag[-4:]}"
    listing = FitmentCenterListPage(oem_page).open()
    listing.search(lifecycle["short_name"])
    form = listing.open_edit(lifecycle["business_name"])
    expect(form.code_box).to_have_value(lifecycle["short_name"])  # the stored values are filled in
    expect(form.email_box).to_have_value(lifecycle["email_id"])
    expect(form.pincode_box).to_have_value(lifecycle["address"]["pincode"])
    form.owner_box.fill(owner)
    form.address_2_box.fill(address_2)

    with oem_page.expect_response(_is_edit) as sent:
        form.submit()

    assert sent.value.status == 200, sent.value.text()[:300]
    expect(oem_page).to_have_url(re.compile(r"/oem/users/fitment-centers$"))
    stored = fitment_centre(oem_api, lifecycle["id"])
    assert stored["owner_name"] == owner and stored["address"]["address_line_2"] == address_2
    assert stored["business_name"] == lifecycle["business_name"] and stored["status"] == "active"  # nothing else moved

    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])  # persists after a fresh load
    details.expect_shown(**{"OWNER NAME": owner, "ADDRESS LINE 2": address_2})


def test_suspend_a_fitment_center(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    remarks = f"AUTO PG suspend {data.unique_suffix()}"
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])
    expect(details.badge("active")).to_be_visible()
    assert _centre_can_sign_in(oem_api, lifecycle) == 200

    response = details.change_status("suspend", remarks)

    assert response.status == 200, response.text()[:300]
    expect(details.badge("suspended")).to_be_visible()
    expect(details.action_button("activate")).to_be_visible()  # a suspended centre can be activated or blacklisted
    expect(details.action_button("blacklist")).to_be_visible()
    expect(details.action_button("suspend")).to_have_count(0)
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "suspended"
    assert ("suspended", remarks) in _history(oem_api, lifecycle["id"])

    oem_page.reload()  # persists, and the history keeps the remark
    details.wait_until_loaded()
    expect(details.badge("suspended")).to_be_visible()
    assert ("SUSPENDED", remarks) in details.history()

    listing = FitmentCenterListPage(oem_page).open()
    listing.search(lifecycle["short_name"])
    expect(listing.row(lifecycle["business_name"])).to_contain_text("Suspended")
    assert listing.row_menu(lifecycle["business_name"]) == ["View details", "Edit FC"]
    assert _centre_can_sign_in(oem_api, lifecycle) == 403  # a suspended centre cannot sign in


def test_activate_a_suspended_fitment_center(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    remarks = f"AUTO PG activate {data.unique_suffix()}"
    assert change_fitment_centre_status(oem_api, lifecycle["id"], "suspend", "AUTO PG set-up").status == 200
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])
    expect(details.badge("suspended")).to_be_visible()

    response = details.change_status("activate", remarks)

    assert response.status == 200, response.text()[:300]
    expect(details.badge("active")).to_be_visible()
    expect(details.action_button("suspend")).to_be_visible()
    expect(details.action_button("blacklist")).to_be_visible()
    expect(details.action_button("activate")).to_have_count(0)
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "active"
    assert ("active", remarks) in _history(oem_api, lifecycle["id"])

    oem_page.reload()
    details.wait_until_loaded()
    expect(details.badge("active")).to_be_visible()
    assert ("ACTIVE", remarks) in details.history()
    assert _centre_can_sign_in(oem_api, lifecycle) == 200  # the centre works again


def test_blacklist_a_fitment_center(oem_page: Page, oem_api: ApiClient, disposable_fc: dict) -> None:
    remarks = f"AUTO PG blacklist {data.unique_suffix()}"
    details = FitmentCenterDetailsPage(oem_page).open_id(disposable_fc["id"])
    details.open_action("blacklist")
    expect(oem_page.get_by_text("This action cannot be reversed.")).to_be_visible()
    details.cancel_action()  # the question can be refused
    assert fitment_centre(oem_api, disposable_fc["id"])["status"] == "active"

    response = details.change_status("blacklist", remarks)

    assert response.status == 200, response.text()[:300]
    expect(details.badge("blacklisted")).to_be_visible()
    expect(details.no_actions).to_be_visible()
    for action in ("suspend", "activate", "blacklist"):
        expect(details.action_button(action)).to_have_count(0)
    assert fitment_centre(oem_api, disposable_fc["id"])["status"] == "blacklisted"
    assert ("blacklisted", remarks) in _history(oem_api, disposable_fc["id"])

    oem_page.reload()
    details.wait_until_loaded()
    expect(details.badge("blacklisted")).to_be_visible()
    assert ("BLACKLISTED", remarks) in details.history()
    listing = FitmentCenterListPage(oem_page).open()
    listing.search(disposable_fc["short_name"])
    expect(listing.row(disposable_fc["business_name"])).to_contain_text("Blacklisted")
    assert listing.row_menu(disposable_fc["business_name"]) == ["View details"]  # no Edit FC either
    assert _centre_can_sign_in(oem_api, disposable_fc) == 403


def test_search_finds_the_fitment_center(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    listing = FitmentCenterListPage(oem_page).open()
    summary = oem_api.get(FITMENT_CENTRES).json()["summary"]

    listing.search(lifecycle["short_name"])  # by code: exactly the one centre

    expect(listing.row(lifecycle["business_name"])).to_have_count(1)
    expect(oem_page.get_by_role("row")).to_have_count(2)  # header + the match
    listing.clear_search()
    expect(oem_page.get_by_role("row")).to_have_count(min(summary["total"], 10) + 1)  # the full first page is back


# ── Search and filters ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "term",
    [lambda fc: fc["business_name"].upper(), lambda fc: f"  {fc['business_name']}  ", lambda fc: fc["email_id"], lambda fc: fc["contact_no"], lambda fc: fc["short_name"].lower()],
    ids=["name-upper-case", "name-with-spaces", "email", "mobile", "code-lower-case"],
)
def test_search_matches_name_code_email_and_mobile_without_case_or_spaces(oem_page: Page, lifecycle: dict, term) -> None:
    listing = FitmentCenterListPage(oem_page).open()

    listing.search(term(lifecycle))

    expect(listing.row(lifecycle["business_name"])).to_have_count(1)


@pytest.mark.parametrize("term", ["zzz-no-such-centre", "<script>alert(1)</script>", "'; DROP TABLE x;--"], ids=["unknown", "markup", "sql-text"])
def test_search_without_a_match_shows_the_empty_state(oem_page: Page, term: str) -> None:
    listing = FitmentCenterListPage(oem_page).open()

    listing.search(term)

    expect(listing.empty_state).to_be_visible()
    expect(oem_page.get_by_role("row")).to_have_count(2)  # header + the empty-state row


def test_status_filter_lists_only_centres_of_that_status(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    assert change_fitment_centre_status(oem_api, lifecycle["id"], "suspend", "AUTO PG set-up").status == 200
    listing = FitmentCenterListPage(oem_page).open()
    listing.search(lifecycle["short_name"])

    listing.choose_status("Active")
    expect(listing.empty_state).to_be_visible()  # the suspended centre is not under Active
    listing.choose_status("Suspended")
    expect(listing.row(lifecycle["business_name"])).to_contain_text("Suspended")


# ── Form validation ───────────────────────────────────────────────────────────

REQUIRED_MESSAGES = [
    "Business Name is required", "Fitment Code is required", "Owner Name is required", "Contact Number is required", "Contact Email is required",
    "City is required", "RTO is required", "Address is required", "Pincode is required", "Fitment Center location is required",
    "Fitment Center image is required", "Password is required", "Confirm Password is required",
]


def test_registering_an_empty_form_lists_every_required_field_and_sends_nothing(oem_page: Page, oem_api: ApiClient) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "POST" and "/fitment-centres" in r.url else None)
    total = oem_api.get(FITMENT_CENTRES).json()["summary"]["total"]
    form = FitmentCenterFormPage(oem_page).open_new()

    form.submit()

    for message in REQUIRED_MESSAGES:
        expect(form.error(message)).to_be_visible()
    assert not sent
    assert oem_api.get(FITMENT_CENTRES).json()["summary"]["total"] == total


@pytest.mark.parametrize(
    "box, value, message",
    [
        ("contact_box", "12345", "Enter valid 10 digit mobile number"),
        ("alternate_box", "12", "Enter valid 10 digit alternate mobile number"),
        ("email_box", "not-an-email", "Enter a valid email"),
        ("pincode_box", "12", "Enter valid 6 digit pincode"),
        ("gst_box", "BADGST", "Enter valid GST Number"),
        ("password_box", "short", "Password must contain uppercase, lowercase, number and minimum 10 characters"),
        ("confirm_password_box", "Different@12345", "Passwords do not match"),
    ],
    ids=["contact", "alternate-contact", "email", "pincode", "gst", "weak-password", "password-mismatch"],
)
def test_registering_with_an_invalid_value_names_the_field_and_sends_nothing(oem_page: Page, box: str, value: str, message: str) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "POST" and "/fitment-centres" in r.url else None)
    form = FitmentCenterFormPage(oem_page).open_new()
    if box == "confirm_password_box":
        form.password_box.fill("Auto@12345Test")
    getattr(form, box).fill(value)

    form.submit()

    expect(form.error(message)).to_be_visible()
    assert not sent


def test_editing_with_empty_mandatory_fields_is_refused_and_changes_nothing(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "POST" and "/fitment-centres/" in r.url else None)
    listing = FitmentCenterListPage(oem_page).open()
    listing.search(lifecycle["short_name"])
    form = listing.open_edit(lifecycle["business_name"])
    form.name_box.fill("   ")  # spaces are not a name
    form.owner_box.fill("")
    form.pincode_box.fill("")

    form.submit()

    for message in ("Business Name is required", "Owner Name is required", "Pincode is required"):
        expect(form.error(message)).to_be_visible()
    assert not sent
    stored = fitment_centre(oem_api, lifecycle["id"])
    assert (stored["business_name"], stored["owner_name"]) == (lifecycle["business_name"], lifecycle["owner_name"])


def test_the_form_limits_the_length_of_the_fields(oem_page: Page) -> None:
    form = FitmentCenterFormPage(oem_page).open_new()
    for box, limit in (("name_box", 150), ("code_box", 20), ("owner_box", 150), ("email_box", 150), ("address_box", 500), ("pincode_box", 6), ("contact_box", 10)):
        getattr(form, box).fill("9" * (limit + 30))
        assert len(getattr(form, box).input_value()) == limit, box


# ── Status confirmation boxes ─────────────────────────────────────────────────

def test_a_status_change_needs_remarks_and_cancel_changes_nothing(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "PATCH" else None)
    history_before = len(fitment_centre_remarks(oem_api, lifecycle["id"]))
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])

    for action in ("suspend", "blacklist"):
        details.open_action(action)
        expect(details.confirm_button(action)).to_be_disabled()  # no remarks yet
        details.remarks_box.fill("   ")
        expect(details.confirm_button(action)).to_be_disabled()  # spaces are not remarks
        details.cancel_action()

    assert not sent
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "active"
    assert len(fitment_centre_remarks(oem_api, lifecycle["id"])) == history_before


def test_confirming_twice_changes_the_status_once(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "PATCH" else None)
    history_before = len(fitment_centre_remarks(oem_api, lifecycle["id"]))
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])
    details.open_action("suspend")
    details.remarks_box.fill("AUTO PG double click")

    details.confirm_button("suspend").dblclick()

    expect(details.badge("suspended")).to_be_visible()
    oem_page.wait_for_load_state("networkidle")
    assert len(sent) == 1
    assert len(fitment_centre_remarks(oem_api, lifecycle["id"])) == history_before + 1


def test_remarks_are_shown_as_text_not_as_markup(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    markup = '<b>bold</b> <img src=x onerror="window.__xss=1">'
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])
    details.change_status("suspend", markup)

    oem_page.reload()
    details.wait_until_loaded()

    assert ("SUSPENDED", markup) in details.history()  # shown literally
    assert oem_page.evaluate("window.__xss") is None
    expect(details.main.locator("b, img[onerror]")).to_have_count(0)


def test_a_server_error_is_reported_and_the_status_is_unchanged(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    oem_page.route("**/api/oem/fitment-centres/*/deactivate", lambda route: route.fulfill(status=500, content_type="application/json", body='{"success":false,"message":"Server error"}'))
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])
    details.open_action("suspend")
    details.remarks_box.fill("AUTO PG mocked failure")

    details.confirm_button("suspend").click()

    expect(oem_page.get_by_text("Server error")).to_be_visible()
    expect(details.badge("active")).to_be_visible()
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "active"


def test_an_expired_session_sends_the_user_to_sign_in_and_changes_nothing(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])
    details.open_action("suspend")
    details.remarks_box.fill("AUTO PG expired session")
    oem_page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")  # the token is gone
    oem_page.context.clear_cookies()

    details.confirm_button("suspend").click()

    expect(oem_page).to_have_url(re.compile(r"/auth/login"))
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "active"


def test_a_centre_of_another_oem_is_not_found_in_the_screen(oem_page: Page, admin_api: ApiClient, oem_api: ApiClient) -> None:
    mine = {fc["id"] for fc in oem_api.get(f"{FITMENT_CENTRES}?per_page=100").json()["data"]}
    foreign = [fc["id"] for fc in admin_api.get(f"{FITMENT_CENTRES}?per_page=100").json()["data"] if fc["id"] not in mine]
    if not foreign:
        pytest.skip("No fitment centre of another OEM exists")

    oem_page.goto(f"/oem/users/fitment-centers/{foreign[0]}")

    expect(oem_page.get_by_text("Fitment Center details not found.")).to_be_visible()


# ── Server-side checks (API) ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def image_less_fields(oem_api: ApiClient) -> dict:
    """Every field valid EXCEPT the mandatory image, so a request can never create a centre."""
    return fitment_centre_fields(oem_api, business_name="AUTO FC never created", short_name="AUTOVAL")


@pytest.mark.parametrize(
    "override, error_field",
    [
        ({"business_name": "A" * 151}, "business_name"),
        ({"short_name": "A" * 21}, "short_name"),
        ({"owner_name": "A" * 151}, "owner_name"),
        ({"email_id": "a" * 140 + "@example.com"}, "email_id"),
        ({"address_line_1": "A" * 501}, "address_line_1"),
        ({"address_line_2": "A" * 501}, "address_line_2"),
        ({"gst_number": "BADGST"}, "gst_number"),
        ({"alternate_contact_no": "123"}, "alternate_contact_no"),
        ({"contact_no": "98765abcde"}, "contact_no"),
        ({"pincode": "11000a"}, "pincode"),
        ({"latitude": "abc"}, "latitude"),
        ({"longitude": "-999"}, "longitude"),
        ({"business_name": "   "}, "business_name"),
    ],
    ids=["name-151", "code-21", "owner-151", "email-150+", "address-501", "address2-501", "gst", "alternate-contact", "contact-letters", "pincode-letters",
         "latitude-text", "longitude-range", "name-spaces"],
)
def test_the_server_refuses_invalid_registration_values(oem_api: ApiClient, image_less_fields: dict, override: dict, error_field: str) -> None:
    total = oem_api.get(FITMENT_CENTRES).json()["summary"]["total"]

    response = oem_api.post(FITMENT_CENTRES, json={**image_less_fields, **override})

    assert response.status == 422 and error_field in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert oem_api.get(FITMENT_CENTRES).json()["summary"]["total"] == total


@pytest.mark.parametrize("field", ["email_id", "contact_no"])
def test_the_server_refuses_an_email_or_mobile_number_that_is_already_registered(oem_api: ApiClient, image_less_fields: dict, field: str) -> None:
    existing = oem_api.get(f"{FITMENT_CENTRES}?per_page=100").json()["data"][0]

    response = oem_api.post(FITMENT_CENTRES, json={**image_less_fields, field: existing[field]})

    assert response.status == 422 and field in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert "already registered" in response.json()["errors"][field][0]


@pytest.mark.parametrize("action", ["suspend", "activate"])
@pytest.mark.parametrize("remarks", [None, "", "   ", "A" * 1001], ids=["missing", "empty", "spaces", "1001-characters"])
def test_the_server_requires_valid_remarks_for_a_status_change(oem_api: ApiClient, lifecycle: dict, action: str, remarks) -> None:
    body = {} if remarks is None else {"remarks": remarks}
    history_before = len(fitment_centre_remarks(oem_api, lifecycle["id"]))

    response = oem_api.patch(f"{FITMENT_CENTRES}/{lifecycle['id']}/{'deactivate' if action == 'suspend' else 'activate'}", json=body)

    assert response.status == 422 and "remarks" in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "active"
    assert len(fitment_centre_remarks(oem_api, lifecycle["id"])) == history_before


def test_the_server_requires_remarks_to_blacklist(oem_api: ApiClient, disposable_fc: dict) -> None:
    for body in ({}, {"remarks": "   "}):
        response = oem_api.patch(f"{FITMENT_CENTRES}/{disposable_fc['id']}/blacklist", json=body)
        assert response.status == 422 and "remarks" in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert fitment_centre(oem_api, disposable_fc["id"])["status"] == "active"


@pytest.mark.parametrize("method, path", [("GET", ""), ("POST", ""), ("GET", "/{id}"), ("PATCH", "/{id}/deactivate")], ids=["list", "register", "details", "suspend"])
@pytest.mark.parametrize("token", [None, "garbage"], ids=["no-token", "malformed-token"])
def test_fitment_center_endpoints_require_a_login(oem_api: ApiClient, lifecycle: dict, method: str, path: str, token) -> None:
    body = None if method == "GET" else {"remarks": "AUTO PG no login"}
    response = oem_api.request(method, FITMENT_CENTRES + path.format(id=lifecycle["id"]), json=body, token=token)

    assert response.status == 401
    assert fitment_centre(oem_api, lifecycle["id"])["status"] == "active"


def test_another_oem_does_not_see_the_centre(other_oem: ApiClient, lifecycle: dict) -> None:
    assert other_oem.get(f"{FITMENT_CENTRES}/{lifecycle['id']}").status == 404
    listed = other_oem.get(f"{FITMENT_CENTRES}?per_page=100&search={lifecycle['short_name']}").json()
    assert listed["data"] == [] and listed["summary"]["total"] == 0


def test_a_suspended_centre_cannot_sign_in_but_an_active_one_can(oem_api: ApiClient, lifecycle: dict) -> None:
    assert _centre_can_sign_in(oem_api, lifecycle) == 200
    assert change_fitment_centre_status(oem_api, lifecycle["id"], "suspend").status == 200
    assert _centre_can_sign_in(oem_api, lifecycle) == 403
    assert change_fitment_centre_status(oem_api, lifecycle["id"], "activate").status == 200
    assert _centre_can_sign_in(oem_api, lifecycle) == 200


# ── Known defects (see bug_report.md); each flips to an unexpected pass when the defect is fixed ──

@pytest.mark.xfail(
    reason="BUG-051 (API-only): another OEM can suspend, activate and blacklist a fitment centre it does not own (200); the details of the same centre answer 404",
    strict=False,
)
@pytest.mark.parametrize("action", ["suspend", "blacklist"])
def test_another_oem_cannot_change_the_status_of_a_centre_it_does_not_own(other_oem: ApiClient, oem_api: ApiClient, lifecycle: dict, disposable_fc: dict, action: str) -> None:
    victim = lifecycle if action == "suspend" else disposable_fc  # a blacklisting cannot be undone, so it targets the disposable centre

    response = change_fitment_centre_status(other_oem, victim["id"], action, "AUTO PG isolation check")

    assert response.status in (403, 404), f"another OEM got {response.status}: {response.text()[:200]}"
    assert fitment_centre(oem_api, victim["id"])["status"] == "active"


@pytest.mark.xfail(
    reason="BUG-052 (API-only): editing a centre of another OEM answers 500 and names an internal model class; it should be 404 like the details",
    strict=False,
)
def test_editing_a_centre_of_another_oem_is_refused_like_a_missing_one(other_oem: ApiClient, oem_api: ApiClient, lifecycle: dict) -> None:
    response = edit_fitment_centre(other_oem, lifecycle, owner_name="AUTO PG other OEM edit")

    assert response.status in (403, 404), f"{response.status} {response.text()[:200]}"
    assert "App\\Models" not in response.text()
    assert fitment_centre(oem_api, lifecycle["id"])["owner_name"] == lifecycle["owner_name"]


@pytest.mark.xfail(
    reason="BUG-053 (API-only): a blacklisted centre can be activated and suspended again; the screen says it 'cannot be reversed'",
    strict=False,
)
def test_a_blacklisted_centre_stays_blacklisted(oem_api: ApiClient, disposable_fc: dict) -> None:
    assert change_fitment_centre_status(oem_api, disposable_fc["id"], "blacklist").status == 200

    for action in ("activate", "suspend"):
        response = change_fitment_centre_status(oem_api, disposable_fc["id"], action)
        assert response.status in (403, 409, 422), f"{action} a blacklisted centre: {response.status}"
        assert fitment_centre(oem_api, disposable_fc["id"])["status"] == "blacklisted"


@pytest.mark.xfail(
    reason="BUG-054 (API-only): activating an active centre and suspending a suspended one are accepted and add history entries",
    strict=False,
)
@pytest.mark.parametrize("action, already", [("activate", "active"), ("suspend", "suspended")])
def test_a_status_the_centre_already_has_cannot_be_set_again(oem_api: ApiClient, lifecycle: dict, action: str, already: str) -> None:
    if already == "suspended":
        assert change_fitment_centre_status(oem_api, lifecycle["id"], "suspend").status == 200
    history_before = len(fitment_centre_remarks(oem_api, lifecycle["id"]))

    response = change_fitment_centre_status(oem_api, lifecycle["id"], action, "AUTO PG repeated")

    assert response.status in (409, 422), f"{action} a {already} centre: {response.status}"
    assert len(fitment_centre_remarks(oem_api, lifecycle["id"])) == history_before


@pytest.mark.xfail(
    reason="BUG-055 (API-only): stock can be allocated to a SUSPENDED fitment centre (201); the guide allows active centres only and the wizard hides the others",
    strict=False,
)
def test_stock_cannot_be_allocated_to_a_suspended_fitment_center(device_lab, oem_api: ApiClient, lifecycle: dict) -> None:
    assert change_fitment_centre_status(oem_api, lifecycle["id"], "suspend").status == 200
    try:
        device = device_lab.register()
        response = device_lab.allocate(lifecycle["id"], device)
        assert response.status == 422, f"A suspended centre received stock: {response.status}"
        assert device_lab.inventory_status(device) == "available"
    finally:
        change_fitment_centre_status(oem_api, lifecycle["id"], "activate", "AUTO PG restore")  # before the lab rolls the allocation back


@pytest.mark.xfail(
    reason="BUG-042: a fitment code that another centre already uses is accepted when a centre is edited (200), as it is when one is registered",
    strict=False,
)
def test_a_fitment_code_used_by_another_centre_is_refused_on_edit(oem_page: Page, lifecycle: dict, active_fc: dict) -> None:
    listing = FitmentCenterListPage(oem_page).open()
    listing.search(lifecycle["short_name"])
    form = listing.open_edit(lifecycle["business_name"])
    form.code_box.fill(active_fc["short_name"])

    with oem_page.expect_response(_is_edit) as sent:
        form.submit()

    assert sent.value.status == 422, f"The duplicate code was accepted: {sent.value.status}"


@pytest.mark.xfail(
    reason="BUG-056: the Remarks History shows UTC times (09:06 am) while the rest of the page shows local time (02:36 pm)",
    strict=False,
)
def test_the_remarks_history_time_matches_the_last_updated_time(oem_page: Page, oem_api: ApiClient, lifecycle: dict) -> None:
    assert change_fitment_centre_status(oem_api, lifecycle["id"], "suspend", "AUTO PG time check").status == 200

    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])

    text = re.sub(r"\s+", " ", details.main.inner_text())
    updated = re.search(r"Last updated \d{1,2} \w{3} \d{4}, (\d{1,2}:\d{2} [ap]m)", text).group(1)
    logged = re.search(r"SUSPENDED By .*?\s*\d{1,2} \w{3} \d{4}, (\d{1,2}:\d{2} [ap]m)\s*AUTO PG time check", text).group(1)
    assert logged == updated, f"Remarks History says {logged}, Last updated says {updated}"


FORM_RULES = [
    ("contact_no", "0000000000", "mobile number starting with 0"),
    ("contact_no", "5999999999", "mobile number starting with 5"),
    ("alternate_contact_no", "1234567890", "alternate mobile number starting with 1"),
    ("email_id", "a@b", "e-mail without a domain suffix"),
    ("email_id", "a@example", "e-mail without a top-level domain"),
]


@pytest.mark.xfail(
    reason="BUG-058 (API-only): the server accepts mobile numbers and e-mails the form refuses, and passwords longer than the form's 100 characters",
    strict=False,
)
@pytest.mark.parametrize("field, value", [(f, v) for f, v, _ in FORM_RULES] + [("password", "Aa1" + "x" * 150)], ids=[w.replace(" ", "-") for _, _, w in FORM_RULES] + ["password-153-characters"])
def test_the_server_enforces_the_contact_and_password_rules_of_the_registration_form(oem_api: ApiClient, image_less_fields: dict, field: str, value: str) -> None:
    body = {**image_less_fields, field: value}
    if field == "password":
        body["password_confirmation"] = value

    response = oem_api.post(FITMENT_CENTRES, json=body)  # no image: it can never create a centre

    assert response.status == 422 and field in response.json()["errors"], f"{field}={value[:12]}...: {response.json().get('errors')}"


@pytest.mark.xfail(
    reason="BUG-058 (API-only): the edit endpoint accepts the same mobile numbers and e-mails that the form refuses",
    strict=False,
)
@pytest.mark.parametrize("field, value", [(f, v) for f, v, _ in FORM_RULES], ids=[w.replace(" ", "-") for _, _, w in FORM_RULES])
def test_the_server_enforces_the_contact_rules_of_the_edit_form(oem_api: ApiClient, lifecycle: dict, field: str, value: str) -> None:
    response = edit_fitment_centre(oem_api, lifecycle, pincode="11000a", **{field: value})  # the wrong pincode: nothing can be saved

    assert response.status == 422 and field in response.json()["errors"], f"{field}={value}: {response.json().get('errors')}"
