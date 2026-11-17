"""
Fixtures for the Fitment Centre panel tests.

  fc_credentials   FC_USERNAME / FC_PASSWORD from .env
  fc_api           API client (session scope, one per xdist worker)
  fc_page          a browser page signed in as the Fitment Centre, sitting on the FC dashboard
  oem_credentials / oem_api / oem_page
                   the OEM side of the same cross-role boundary (duplicated from tests/oem_panel/conftest.py,
                   which fc_panel tests cannot see - fixtures don't cross sibling conftest files in pytest)
  fc_profile_account / fc_profile_page
                   a fresh, throw-away Fitment Centre account (registered through oem_api, past its forced
                   first-login password change), for Profile / Change Password / Logout tests that must never
                   touch the shared FC_USERNAME account
  anonymous / fc_shared_own / fc_fresh_own
                   Helpdesk fixtures: a client with no login, a shared ticket the FC_USERNAME account raised for
                   itself (created once, reused by marker), and a fresh one for a test that changes it

This account is the single, deliberately-provisioned `FC_USERNAME` test account (not a throw-away one created per
test): it holds real, hand-set-up data (10 allocated devices, 7 in-progress installations - see
`specs/fitment-centre-test-plan.md`, "Risks") that later FC modules will keep building on, so these tests must only
read it, never delete or reset it.
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from utils.api_client import ApiClient


@pytest.fixture(scope="session")
def fc_credentials() -> dict:
    user, password = os.environ.get("FC_USERNAME", ""), os.environ.get("FC_PASSWORD", "")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user) or not password:
        pytest.skip("FC_USERNAME / FC_PASSWORD in .env are not a valid Fitment Centre login")
    return {"username": user, "password": password}


@pytest.fixture(scope="session")
def fc_api(playwright, base_url: str, fc_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, fc_credentials["username"], fc_credentials["password"])
    request.dispose()


@pytest.fixture
def fc_page(page: Page, login_page_obj: LoginPage, fc_credentials: dict) -> Page:
    """A page signed in as the Fitment Centre, sitting on the FC dashboard."""
    login_page_obj.login(fc_credentials["username"], fc_credentials["password"])
    expect(page).to_have_url(re.compile(r"/fc/dashboard"), timeout=40_000)
    return page


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


@pytest.fixture
def oem_page(page: Page, login_page_obj: LoginPage, oem_credentials: dict) -> Page:
    """A page signed in as the OEM, sitting on the OEM dashboard."""
    login_page_obj.login(oem_credentials["username"], oem_credentials["password"])
    expect(page).to_have_url(re.compile(r"/oem/dashboard"), timeout=40_000)
    return page


# ── Profile / Change Password / Logout ─────────────────────────────────────────
# A test that changes a password, or ends a session, must never touch the shared `FC_USERNAME` account that every
# other fixture depends on - each test that needs one gets its own fresh, throw-away Fitment Centre account.
#
# A freshly registered Fitment Centre DOES need a forced first-login password change, same as an OEM account -
# confirmed 2026-11-05 after an initial, wrong read of the login response (the flag is `is_password_change_required`,
# not `force_password_change` as on the OEM side; different field name, same mechanism). So this settles the
# temporary password through the API first, exactly like `tests/oem_panel/conftest.py`'s `profile_account` does via
# `pf.settled_oem_account` - the UI's forced-redirect behaviour itself is covered separately by
# `test_a_new_account_must_change_its_temporary_password_before_using_the_panel` in the test file.

@pytest.fixture
def fc_profile_account(oem_api: ApiClient, playwright, base_url: str) -> dict:
    """A fresh throw-away Fitment Centre account, past its forced first-login password change. {'id', 'email', 'password'}."""
    from utils import data_generator as data
    from utils import oem_profile_api as pf
    from utils.oem_panel_api import register_fitment_centre

    centre = register_fitment_centre(oem_api)
    account = {"id": centre["user_id"], "email": centre["email_id"], "password": data.PASSWORD}
    request = playwright.request.new_context()
    temp_client = ApiClient.login(request, base_url, account["email"], account["password"])
    settled_password = data.PASSWORD + "9"  # still meets the policy (10+, upper, lower, number); different from the temporary one
    response = pf.forced_change_password(temp_client, account["password"], settled_password)
    assert response.status == 200, f"could not settle the throw-away FC account's password: {response.status} {response.text()[:200]}"
    request.dispose()
    return {**account, "password": settled_password}


@pytest.fixture
def fc_profile_page(page: Page, login_page_obj: LoginPage, fc_profile_account: dict) -> Page:
    """A page signed in as a dedicated, throw-away Fitment Centre account (never the shared `FC_USERNAME` one)."""
    login_page_obj.login(fc_profile_account["email"], fc_profile_account["password"])
    expect(page).to_have_url(re.compile(r"/fc/dashboard"), timeout=40_000)
    return page


# ── Helpdesk ─────────────────────────────────────────────────────────────────────
# Unlike the OEM panel, the FC role cannot be the target of a routed/assigned ticket (confirmed 2026-11-05: the
# public form's and the New Ticket form's "Send To" list only ever offers OEMs and "Transport Department", never a
# fitment centre; `/fc/helpdesk/assigned-tickets` redirects back to `/fc/helpdesk`). So there is no FC equivalent of
# `shared_routed` / `shared_for_other_oem` / `fresh_routed` - an FC only ever has tickets IT raised.

@pytest.fixture(scope="session")
def anonymous(playwright, base_url: str):
    """A client with no login, for the public Support Center."""
    request = playwright.request.new_context()
    yield ApiClient(request, base_url)
    request.dispose()


def _find_own(client: ApiClient, text: str, status: str | None = None) -> dict | None:
    """Like `oem_helpdesk_api.find`, but against `/api/user/ticket` - confirmed 2026-11-05 that `/api/helpdesk/tickets`
    (the OEM "Support Queue" endpoint `find` normally uses) answers 200 but always EMPTY for the FC role, even for
    tickets the FC raised itself; there is no FC equivalent of a queue that also lists what it raised."""
    from utils import oem_helpdesk_api as hd

    for ticket in hd.tickets(client, hd.USER_TICKETS, search=text.replace(" ", "+")):
        if status is None or ticket["status"] == status:
            return ticket
    return None


def _shared_fc_ticket(client: ApiClient, marker: str, status: str, create) -> dict:
    ticket = _find_own(client, marker, status)
    if ticket is None:
        create()
        ticket = _find_own(client, marker, status)
    assert ticket, f"the shared ticket '{marker}' could not be created"
    return ticket


def own_ticket_by_code(client: ApiClient, code: str) -> dict:
    """Like `oem_helpdesk_api.ticket_by_code`, but against `/api/user/ticket` (see `_find_own`)."""
    from utils import oem_helpdesk_api as hd

    found = next((t for t in hd.tickets(client, hd.USER_TICKETS, search=code) if t["ticket_code"] == code), None)
    assert found, f"ticket {code} is not in this account's own tickets"
    return found


@pytest.fixture(scope="session")
def fc_shared_own(fc_api: ApiClient) -> dict:
    """A ticket the shared FC_USERNAME account raised for itself: status 'opened', unassigned."""
    from utils import oem_helpdesk_api as hd

    marker = "AUTO HD FC shared own"
    return _shared_fc_ticket(fc_api, marker, "opened", lambda: hd.raise_ticket(fc_api, f"{marker} - ticket for the Fitment Centre Helpdesk tests, please ignore."))


@pytest.fixture
def fc_fresh_own(fc_api: ApiClient) -> dict:
    """A new ticket the shared FC_USERNAME account raises, for a test that changes it (stays in the system afterwards)."""
    from utils import data_generator as data
    from utils import oem_helpdesk_api as hd

    marker = f"AUTO HD FC fresh {data.unique_suffix()}"
    response = hd.raise_ticket(fc_api, f"{marker} - ticket for the Fitment Centre Helpdesk tests, please ignore.")
    assert response.status == 200, response.text()[:200]
    code = response.json()["data"]["ticket_code"]
    return own_ticket_by_code(fc_api, code)
