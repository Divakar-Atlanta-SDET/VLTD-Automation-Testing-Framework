"""
OEM role versus the State Admin's master data (guide section 4, "OEM Management").

  "OEMs cannot create, edit, or delete this master data; they can only view their own device models."

Uses the OEM_USERNAME / OEM_PASSWORD login from .env. Write attempts target throw-away records created through the
admin API (removed by the `records` fixture), so a missing refusal can never hurt real data.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from utils.api_client import API_PREFIX, ApiClient
from utils.oem_mgmt_api import FIRMWARES, MODELS, SIMS

pytestmark = [pytest.mark.oem_management, pytest.mark.api]

RESOURCES = [pytest.param(MODELS, id="device-models"), pytest.param(FIRMWARES, id="firmware"), pytest.param(SIMS, id="sim-modules")]


@pytest.fixture(scope="session")
def oem_credentials() -> dict:
    import os

    user, password = os.environ.get("OEM_USERNAME", ""), os.environ.get("OEM_PASSWORD", "")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user) or not password:
        pytest.skip("OEM_USERNAME / OEM_PASSWORD in .env are not a valid OEM login")
    return {"username": user, "password": password}


@pytest.fixture(scope="session")
def oem_client(playwright, base_url: str, oem_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, oem_credentials["username"], oem_credentials["password"])
    request.dispose()


@pytest.fixture
def throwaway(records) -> dict:
    """One disposable record of each kind: {path: id}."""
    model = records.create_model()
    firmware = records.create_firmware(model["id"])
    sim = records.create_sim()
    return {MODELS: model["id"], FIRMWARES: firmware["id"], SIMS: sim["id"], "oem_id": records.oem_id}


@pytest.mark.parametrize("path", RESOURCES)
def test_oem_cannot_create_edit_or_delete_master_data(oem_client: ApiClient, records, throwaway: dict, path: str) -> None:
    """Guide s4: every write verb on master data is refused for an OEM, and the record is untouched."""
    record_id = throwaway[path]
    before = records.admin.get(f"{path}/{record_id}").json()["data"]

    attempts = {
        "create": oem_client.post(path, json={}),
        "update-put": oem_client.put(f"{path}/{record_id}", json={}),
        "update-patch": oem_client.patch(f"{path}/{record_id}", json={}),
        "delete": oem_client.delete(f"{path}/{record_id}?oem_id={throwaway['oem_id']}"),
    }

    not_refused = {verb: r.status for verb, r in attempts.items() if r.status != 403}
    assert not not_refused, f"{path}: an OEM was not refused with 403 for: {not_refused}"
    assert records.admin.get(f"{path}/{record_id}").json()["data"] == before, "The record changed"


@pytest.mark.parametrize("path", RESOURCES)
def test_oem_sees_only_its_own_master_data(oem_client: ApiClient, records, path: str) -> None:
    """Guide s4: an OEM can view only its own records, never those of another OEM (here: the AUTO OEM)."""
    response = oem_client.get(f"{path}?per_page=100")
    assert response.status == 200, response.text()[:200]
    rows = response.json()["data"]
    rows = rows.get("data", []) if isinstance(rows, dict) else rows

    owners = {row["oem_id"] if "oem_id" in row else row["device_model"]["oem_id"] for row in rows}  # firmware rows carry the owner on their model
    assert len(owners) <= 1, f"{path}: the OEM sees records of several OEMs: {owners}"
    assert records.oem_id not in owners, f"{path}: the OEM sees the records of another OEM"


@pytest.mark.parametrize(
    "path",
    [f"{API_PREFIX}/{name}" for name in ("oems", "rtos", "staff", "inspectors", "system-configuration", "dashboard")],
)
def test_oem_is_refused_state_admin_endpoints(oem_client: ApiClient, path: str) -> None:
    assert oem_client.get(path).status == 403


def test_oem_lands_on_its_own_dashboard_and_cannot_open_state_admin_pages(page: Page, base_url: str, oem_credentials: dict) -> None:
    """Guide s3: the user is sent to the role's home page; menus and pages of other roles are not available."""
    login = LoginPage(page)
    login.navigate(base_url)
    login.login(oem_credentials["username"], oem_credentials["password"])
    expect(page).to_have_url(re.compile(r"/oem/dashboard"), timeout=30_000)

    for route in ("/tc/dashboard", "/tc/oem-management/device-models"):
        page.goto(route)
        expect(page).to_have_url(re.compile(r"/unauthorized"))
