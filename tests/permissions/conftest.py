"""Fixtures for the staff-permission tests."""

import pytest

from utils.api_client import ApiClient
from utils.staff_lab import StaffLab


@pytest.fixture(scope="session")
def staff_lab(playwright, base_url: str, admin_credentials: dict):
    """One StaffLab per test worker: a prober + target staff account and the 'Auto…' records to act on."""
    request = playwright.request.new_context()
    admin = ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    lab = StaffLab.create(admin)
    yield lab
    request.dispose()
