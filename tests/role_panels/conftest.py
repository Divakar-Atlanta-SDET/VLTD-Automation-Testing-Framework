"""
Fixtures for the Driver, RTO Inspector and RTO Officer panel tests.

  rto_credentials / rto_api / rto_page              the dedicated RTO Officer account (RTO_USERNAME/PASSWORD)
  inspector_credentials / inspector_api / inspector_page   the dedicated Inspector account, assigned to that RTO
  driver_credentials / driver_api / driver_page     the dedicated Driver account

All three accounts were created once through the normal Admin UI (Administration > User Management), had their
forced first-login password settled through the API, and are reused across this whole module - never deleted or
reset by a test (the app has no delete for any of these three entity types anyway). See
`specs/role-panels-test-plan.md` for how they were created and what each one can/cannot do.
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


# ── RTO Officer ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def rto_credentials() -> dict:
    return _credentials("RTO_USERNAME", "RTO_PASSWORD", "RTO")


@pytest.fixture(scope="session")
def rto_api(playwright, base_url: str, rto_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, rto_credentials["username"], rto_credentials["password"])
    request.dispose()


@pytest.fixture
def rto_page(page: Page, login_page_obj: LoginPage, rto_credentials: dict) -> Page:
    login_page_obj.login(rto_credentials["username"], rto_credentials["password"])
    expect(page).to_have_url(re.compile(r"/rto/dashboard"), timeout=40_000)
    return page


# ── RTO Inspector ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def inspector_credentials() -> dict:
    return _credentials("INSPECTOR_USERNAME", "INSPECTOR_PASSWORD", "Inspector")


@pytest.fixture(scope="session")
def inspector_api(playwright, base_url: str, inspector_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, inspector_credentials["username"], inspector_credentials["password"])
    request.dispose()


@pytest.fixture
def inspector_page(page: Page, login_page_obj: LoginPage, inspector_credentials: dict) -> Page:
    login_page_obj.login(inspector_credentials["username"], inspector_credentials["password"])
    expect(page).to_have_url(re.compile(r"/inspector/dashboard"), timeout=40_000)
    return page


# ── Driver ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def driver_credentials() -> dict:
    return _credentials("DRIVER_USERNAME", "DRIVER_PASSWORD", "Driver")


@pytest.fixture(scope="session")
def driver_api(playwright, base_url: str, driver_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, driver_credentials["username"], driver_credentials["password"])
    request.dispose()


@pytest.fixture
def driver_page(page: Page, login_page_obj: LoginPage, driver_credentials: dict) -> Page:
    login_page_obj.login(driver_credentials["username"], driver_credentials["password"])
    expect(page).to_have_url(re.compile(r"/driver/dashboard"), timeout=40_000)
    return page
