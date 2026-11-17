"""Role-login fixtures for the UI/UX audit's regression tests.

Mirrors the same fixtures already defined in tests/oem_panel/conftest.py, tests/fc_panel/conftest.py
and tests/role_panels/conftest.py - duplicated here because pytest conftest fixtures are scoped to a
directory and its subdirectories, not shared between sibling test directories, and this project's own
existing convention is for each panel's test directory to define its own role fixtures locally.
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage


def _credentials(user_env: str, password_env: str, label: str) -> dict:
    user, password = os.environ.get(user_env, ""), os.environ.get(password_env, "")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user) or not password:
        pytest.skip(f"{user_env} / {password_env} in .env are not a valid {label} login")
    return {"username": user, "password": password}


@pytest.fixture(scope="session")
def oem_credentials() -> dict:
    return _credentials("OEM_USERNAME", "OEM_PASSWORD", "OEM")


@pytest.fixture
def oem_page(page: Page, login_page_obj: LoginPage, oem_credentials: dict) -> Page:
    login_page_obj.login(oem_credentials["username"], oem_credentials["password"])
    expect(page).to_have_url(re.compile(r"/oem/dashboard"), timeout=40_000)
    return page


@pytest.fixture(scope="session")
def fc_credentials() -> dict:
    return _credentials("FC_USERNAME", "FC_PASSWORD", "Fitment Centre")


@pytest.fixture
def fc_page(page: Page, login_page_obj: LoginPage, fc_credentials: dict) -> Page:
    login_page_obj.login(fc_credentials["username"], fc_credentials["password"])
    expect(page).to_have_url(re.compile(r"/fc/dashboard"), timeout=40_000)
    return page


@pytest.fixture(scope="session")
def rto_credentials() -> dict:
    return _credentials("RTO_USERNAME", "RTO_PASSWORD", "RTO")


@pytest.fixture
def rto_page(page: Page, login_page_obj: LoginPage, rto_credentials: dict) -> Page:
    login_page_obj.login(rto_credentials["username"], rto_credentials["password"])
    expect(page).to_have_url(re.compile(r"/rto/dashboard"), timeout=40_000)
    return page


@pytest.fixture(scope="session")
def inspector_credentials() -> dict:
    return _credentials("INSPECTOR_USERNAME", "INSPECTOR_PASSWORD", "Inspector")


@pytest.fixture
def inspector_page(page: Page, login_page_obj: LoginPage, inspector_credentials: dict) -> Page:
    login_page_obj.login(inspector_credentials["username"], inspector_credentials["password"])
    expect(page).to_have_url(re.compile(r"/inspector/dashboard"), timeout=40_000)
    return page


@pytest.fixture(scope="session")
def driver_credentials() -> dict:
    return _credentials("DRIVER_USERNAME", "DRIVER_PASSWORD", "Driver")


@pytest.fixture
def driver_page(page: Page, login_page_obj: LoginPage, driver_credentials: dict) -> Page:
    login_page_obj.login(driver_credentials["username"], driver_credentials["password"])
    expect(page).to_have_url(re.compile(r"/driver/dashboard"), timeout=40_000)
    return page
