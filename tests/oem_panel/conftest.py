"""
Fixtures for the OEM panel tests.

  oem_api / admin_api   API clients (session scope, one per xdist worker)
  lab                   Device Model + Firmware + SIM Module of the OEM and the devices registered through them;
                        everything is removed at the end of the session (see utils/oem_panel_api.py)
  available_device      one freshly registered, available device (released after the test)
  active_fc / blacklisted_fc
  lifecycle             the long-lived 'AUTO PG FC lifecycle' fitment centre, active; what a test changes is undone afterwards
  district_of           the district name the allocation wizard uses for a fitment centre
  oem_page              a browser page signed in as the OEM

Tests that create devices or allocations are pinned to ONE worker (`xdist_group("oem-devices")`), because they share
the OEM's inventory counters and the one active fitment centre.
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from utils import data_generator as data
from utils import oem_helpdesk_api as hd
from utils import oem_profile_api as pf
from utils.api_client import API_PREFIX, ApiClient
from utils.file_utils import png_bytes
from utils.oem_panel_api import (
    COMMAND_TEMPLATES, FITMENT_CENTRES, OemDeviceLab, change_fitment_centre_status, create_oem_account, edit_fitment_centre, find_oem_account,
    fitment_centre, register_fitment_centre,
)

DEVICE_GROUP = pytest.mark.xdist_group("oem-devices")
LIFECYCLE_NAME = "AUTO PG FC lifecycle"


@pytest.fixture(scope="session")
def oem_credentials() -> dict:
    user, password = os.environ.get("OEM_USERNAME", ""), os.environ.get("OEM_PASSWORD", "")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user) or not password:
        pytest.skip("OEM_USERNAME / OEM_PASSWORD in .env are not a valid OEM login")
    return {"username": user, "password": password}


@pytest.fixture(scope="session")
def oem_api(playwright, base_url: str, oem_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, oem_credentials["username"], oem_credentials["password"])
    request.dispose()


@pytest.fixture(scope="session")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="session")
def other_oem(playwright, base_url: str, admin_api: ApiClient, oem_api: ApiClient) -> ApiClient:
    """Another OEM that must never reach this OEM's records.

    A throw-away 'AUTO OEM' account left by an earlier run is reused (the application cannot delete OEMs); a new one is made only when
    none of the newest ones can sign in.
    """
    request = playwright.request.new_context()
    mine = oem_api.get("/api/auth/me").json()["data"]["id"]
    records = [o for o in admin_api.all_items(f"{API_PREFIX}/oems")
               if str(o.get("contact_email", "")).startswith("auto.oem.") and o.get("status") == "active" and o["user_id"] != mine]
    client = None
    for record in sorted(records, key=lambda o: o["created_at"], reverse=True)[:5]:
        try:
            client = ApiClient.login(request, base_url, record["contact_email"], data.PASSWORD)
            break
        except AssertionError:
            continue
    if client is None:
        account = create_oem_account(admin_api)
        client = ApiClient.login(request, base_url, account["email"], account["password"])
    yield client
    request.dispose()


@pytest.fixture(scope="session")
def lab(admin_api: ApiClient, oem_api: ApiClient):
    lab = OemDeviceLab.create(admin_api, oem_api)
    yield lab
    lab.cleanup()


@pytest.fixture
def device_lab(lab: OemDeviceLab):
    """The lab for a test that registers / allocates devices itself; whatever it made is released afterwards."""
    yield lab
    lab.release_devices()


@pytest.fixture
def available_device(lab: OemDeviceLab):
    """One available device; every device and allocation made during the test is released afterwards."""
    record = lab.register()
    yield record
    lab.release_devices()


@pytest.fixture(scope="session")
def fitment_centres(oem_api: ApiClient) -> list[dict]:
    """The OEM's own centres, without the 'AUTO PG FC' ones that the fitment-centre lifecycle tests suspend and blacklist."""
    return [fc for fc in oem_api.get(f"{FITMENT_CENTRES}?per_page=100").json()["data"] if not fc["business_name"].startswith("AUTO PG FC")]


@pytest.fixture(scope="session")
def active_fc(fitment_centres: list[dict]) -> dict:
    active = [f for f in fitment_centres if f["status"] == "active"]
    if not active:
        pytest.skip("The OEM has no active fitment centre")
    return active[0]


@pytest.fixture(scope="session")
def blacklisted_fc(fitment_centres: list[dict]) -> dict:
    blocked = [f for f in fitment_centres if f["status"] == "blacklisted"]
    if not blocked:
        pytest.skip("The OEM has no blacklisted fitment centre")
    return blocked[0]


@pytest.fixture(scope="session")
def lifecycle_fc(oem_api: ApiClient) -> dict:
    """The long-lived centre of the lifecycle tests: found by name, registered the first time."""
    listed = oem_api.get(f"{FITMENT_CENTRES}?per_page=100&search={LIFECYCLE_NAME}").json()["data"]
    usable = [fc for fc in listed if fc["business_name"] == LIFECYCLE_NAME and fc["status"] != "blacklisted"]
    return usable[0] if usable else register_fitment_centre(oem_api, business_name=LIFECYCLE_NAME)


@pytest.fixture
def lifecycle(oem_api: ApiClient, lifecycle_fc: dict):
    """The lifecycle centre, active and with its original details; the test's changes are undone afterwards (also when it fails)."""
    fc = fitment_centre(oem_api, lifecycle_fc["id"])
    if fc["status"] == "suspended":
        change_fitment_centre_status(oem_api, fc["id"], "activate", "AUTO PG restore")
        fc = fitment_centre(oem_api, fc["id"])
    assert fc["status"] == "active", f"the lifecycle centre is {fc['status']}"
    yield fc
    now = fitment_centre(oem_api, fc["id"])
    if now["status"] == "suspended":
        change_fitment_centre_status(oem_api, fc["id"], "activate", "AUTO PG restore")
    if (now["short_name"], now["owner_name"], now["address"]["address_line_2"]) != (fc["short_name"], fc["owner_name"], fc["address"]["address_line_2"]):
        edit_fitment_centre(oem_api, now, short_name=fc["short_name"], owner_name=fc["owner_name"], address_line_2=fc["address"]["address_line_2"] or "")


@pytest.fixture(scope="session")
def district_of(oem_api: ApiClient):
    """district_of(fc) -> the district name under which the allocation wizard lists that active fitment centre."""

    def _district(fc: dict) -> str:
        for city in oem_api.get("/api/masters/cities").json()["data"]:
            listed = oem_api.get(f"{FITMENT_CENTRES}?city_id={city['id']}&status=active").json()["data"]
            if any(f["id"] == fc["id"] for f in listed):
                return city["name"]
        raise AssertionError(f"{fc['business_name']} is not listed under any district")

    return _district


@pytest.fixture
def oem_page(page: Page, login_page_obj: LoginPage, oem_credentials: dict) -> Page:
    """A page signed in as the OEM, sitting on the OEM dashboard."""
    login_page_obj.login(oem_credentials["username"], oem_credentials["password"])
    expect(page).to_have_url(re.compile(r"/oem/dashboard"), timeout=40_000)
    return page


@pytest.fixture
def template_lab(lab):
    """create(**fields) -> response; successful ones are deleted afterwards (also when a test fails)."""
    created: list[int] = []

    def create(**fields):
        body = {"device_model_id": lab.model["id"], "label": f"AUTO cmd {len(created)}-{lab.model['id']}", "raw_command": "STATUS#", **fields}
        response = lab.oem.post(COMMAND_TEMPLATES, json=body)
        if response.status == 201:
            created.append(response.json()["data"]["id"])
        return response

    create.oem = lab.oem
    yield create
    for template_id in created:
        lab.oem.delete(f"{COMMAND_TEMPLATES}/{template_id}")


# ── Helpdesk ──────────────────────────────────────────────────────────────────
# Tickets cannot be deleted, so the Helpdesk tests reuse three long-lived 'AUTO HD shared ...' tickets (found by the marker in their description,
# created only when missing, never changed by a test). A test that changes a ticket uses `fresh_routed` or raises its own; all Helpdesk tests run on
# one xdist worker (`xdist_group("oem-helpdesk")`), so the shared tickets are not created twice.

@pytest.fixture(scope="session")
def anonymous(playwright, base_url: str):
    """A client with no login, for the public Support Center."""
    request = playwright.request.new_context()
    yield ApiClient(request, base_url)
    request.dispose()


@pytest.fixture(scope="session")
def oem_org(admin_api: ApiClient, oem_api: ApiClient) -> dict:
    return find_oem_account(admin_api, oem_api)


@pytest.fixture(scope="session")
def other_oem_org(admin_api: ApiClient, other_oem: ApiClient) -> dict:
    return find_oem_account(admin_api, other_oem)


def _shared_ticket(client: ApiClient, marker: str, status: str, create) -> dict:
    ticket = hd.find(client, marker, status)
    if ticket is None:
        create()
        ticket = hd.find(client, marker, status)
    assert ticket, f"the shared ticket '{marker}' could not be created"
    return ticket


@pytest.fixture(scope="session")
def shared_routed(anonymous: ApiClient, oem_api: ApiClient, oem_org: dict) -> dict:
    """A ticket from the public Support Center that goes straight to this OEM: status 'assigned', with the OEM."""
    marker = "AUTO HD shared routed"
    return _shared_ticket(oem_api, marker, "assigned", lambda: hd.raise_public_ticket(anonymous, f"{marker} - public ticket for the OEM Helpdesk tests, please ignore.", oem_org["id"]))


@pytest.fixture(scope="session")
def shared_own(oem_api: ApiClient) -> dict:
    """A ticket this OEM raised for the Transport Department: status 'opened', unassigned."""
    marker = "AUTO HD shared own"
    return _shared_ticket(oem_api, marker, "opened", lambda: hd.raise_ticket(oem_api, f"{marker} - ticket for the OEM Helpdesk tests, please ignore."))


@pytest.fixture(scope="session")
def shared_for_other_oem(oem_api: ApiClient, other_oem_org: dict) -> dict:
    """A ticket this OEM raised with Priority and a PNG attachment, sent to another OEM: status 'assigned', owned by the other OEM."""
    marker = "AUTO HD shared other-oem"
    file = {"name": "helpdesk-proof.png", "mimeType": "image/png", "buffer": png_bytes()}
    return _shared_ticket(oem_api, marker, "assigned", lambda: hd.raise_ticket(oem_api, f"{marker} - ticket for the OEM Helpdesk tests, please ignore.", priority=True, oem_id=other_oem_org["id"], file=file))


@pytest.fixture
def fresh_routed(anonymous: ApiClient, oem_api: ApiClient, oem_org: dict) -> dict:
    """A new public ticket routed to this OEM, for a test that changes it (it stays in the system afterwards)."""
    code = hd.raise_public_ticket(anonymous, f"AUTO HD fresh {data.unique_suffix()} - public ticket for the OEM Helpdesk tests, please ignore.", oem_org["id"])
    return hd.ticket_by_code(oem_api, code)


# ── Profile / Change Password / Logout ─────────────────────────────────────────
# A test that changes a password, or ends a session, must never touch the shared `.env` OEM account that every other
# fixture depends on. Each test that needs one gets its own fresh, throw-away, already-settled account.

@pytest.fixture
def profile_account(admin_api: ApiClient, playwright, base_url: str) -> dict:
    """A fresh throw-away OEM account, past its forced first-login password change. {'id', 'email', 'password'}.

    `create_oem_account` picks its GST number from only a 4-digit random range; this module creates one account per
    test, so a collision with an earlier throw-away account is occasionally seen here even though it is rare in
    modules that reuse one shared account - retried the same way `ApiClient.login` retries a transient failure.
    """
    request = playwright.request.new_context()
    for attempt in range(3):
        try:
            account = pf.settled_oem_account(admin_api, request, base_url)
            break
        except AssertionError as error:
            if attempt == 2 or "already registered" not in str(error):
                raise
    request.dispose()
    return account


@pytest.fixture
def profile_page(login_page_obj, profile_account: dict) -> Page:
    """A page signed in as a dedicated, throw-away OEM account (never the shared one)."""
    login_page_obj.login(profile_account["email"], profile_account["password"])
    expect(login_page_obj.page).to_have_url(re.compile(r"/oem/dashboard"), timeout=40_000)
    return login_page_obj.page
