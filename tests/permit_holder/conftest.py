"""
Fixtures for the Permit Holder (Fleet Owner) panel tests.

  permit_holder_credentials / permit_holder_api / permit_holder_page   PERMIT_HOLDER_USERNAME/PASSWORD

This account (Sakshi Gupta, permit holder code FLT2610582) is one of the orphaned Permit Holder records
documented as BUG-089 in `bug_report.md` - created as a side effect of a blocked New Installation, not through
a real onboarding flow. It is still a real, active account and is reused across this whole module, the same
way `tests/role_panels/conftest.py` reuses its three accounts - never deleted or reset by a test. See
`specs/permit-holder-test-plan.md` for how it was discovered and what it can/cannot do.
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from utils.api_client import ApiClient


def _credentials(user_env: str, password_env: str, label: str) -> dict:
    user, password = os.environ.get(user_env, ""), os.environ.get(password_env, "")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user) or not password:
        pytest.skip(f"{user_env} / {password_env} in .env are not a valid {label} login")
    return {"username": user, "password": password}


@pytest.fixture(scope="session")
def permit_holder_credentials() -> dict:
    return _credentials("PERMIT_HOLDER_USERNAME", "PERMIT_HOLDER_PASSWORD", "Permit Holder")


@pytest.fixture(scope="session")
def permit_holder_api(playwright, base_url: str, permit_holder_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, permit_holder_credentials["username"], permit_holder_credentials["password"])
    request.dispose()


@pytest.fixture
def permit_holder_page(page: Page, login_page_obj: LoginPage, permit_holder_credentials: dict) -> Page:
    login_page_obj.login(permit_holder_credentials["username"], permit_holder_credentials["password"])
    expect(page).to_have_url(re.compile(r"/fleet-owner/dashboard"), timeout=40_000)
    return page


@pytest.fixture(scope="session")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="session")
def other_owner_vehicle_id(admin_api: ApiClient, permit_holder_api: ApiClient) -> int:
    """A real vehicle_id that does NOT belong to the permit_holder_api account - for ownership-isolation checks."""
    own_ids = {v["id"] for v in permit_holder_api.request("GET", "/api/permit-holder/vehicle").json()["data"]["data"]}
    vehicles = admin_api.request("GET", "/api/tracking/vehicles").json()["data"]
    candidates = [v["id"] for v in vehicles if v["id"] not in own_ids]
    if not candidates:
        pytest.skip("no vehicle outside this permit holder's own fleet was found to test isolation against")
    return candidates[0]
