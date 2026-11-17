"""Fixtures for the OEM Management tests (Device Models, Firmware, SIM Modules)."""

import pytest
from playwright.sync_api import Page

from pages.oem_management.device_models_page import DeviceModelsPage
from pages.oem_management.firmware_page import FirmwarePage
from pages.oem_management.sim_modules_page import SimModulesPage
from utils.api_client import ApiClient
from utils.oem_mgmt_api import OemMgmtApi


@pytest.fixture(scope="session")
def oem_admin(playwright, base_url: str, admin_credentials: dict):
    """Admin API client shared by every test of this worker."""
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="session")
def oem_owner(oem_admin: ApiClient) -> dict:
    """The 'AUTO OEM' that owns all test records. Also tops every list up to 12+ records (persistent seed)."""
    helper = OemMgmtApi(oem_admin)
    helper.ensure_seed()
    return helper.oem


@pytest.fixture
def records(oem_admin: ApiClient, oem_owner: dict):
    """Creates records through the API for one test and deletes them afterwards (the seed is never touched)."""
    helper = OemMgmtApi(oem_admin, oem_owner)
    yield helper
    helper.cleanup()


@pytest.fixture
def device_models_page(admin_page: Page, oem_owner: dict) -> DeviceModelsPage:
    return DeviceModelsPage(admin_page)


@pytest.fixture
def firmware_page(admin_page: Page, oem_owner: dict) -> FirmwarePage:
    return FirmwarePage(admin_page)


@pytest.fixture
def sim_modules_page(admin_page: Page, oem_owner: dict) -> SimModulesPage:
    return SimModulesPage(admin_page)
