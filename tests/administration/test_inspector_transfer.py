"""
Inspector rules of guide section 9.1 that need an existing inspector: RTO transfer and the first login.

  PUT /api/transport-commissioner/inspectors/{id}/rtos   {"rto_ids": [<new rto id>]}

On transfer the destination RTO must differ from the current one, and the old link is replaced by the new one in
one step. A new inspector must change the temporary password at the first sign-in. The inspector's RTO is read
back from the inspector list (there is no detail endpoint). Test inspectors cannot be deleted; they are left for the
database owner like the other "Auto Inspector" accounts.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.user_management, pytest.mark.api]

INSPECTORS = f"{API_PREFIX}/inspectors"


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="module")
def active_rtos(admin_api: ApiClient) -> list[dict]:
    active = [r for r in admin_api.all_items(f"{API_PREFIX}/rtos") if r["status"] == "active"]
    if len(active) < 3:
        pytest.skip(f"Need at least 3 active RTOs; found {len(active)}")
    return active


def _create_inspector(admin: ApiClient, rto_id: int):
    i = data.inspector_data()
    body = {
        "name": i.name, "email": i.email, "contact_no": i.mobile, "address": i.address,
        "city_id": admin.first_id("/api/masters/cities"), "rto_ids": [rto_id],
        "password": i.password, "password_confirmation": i.password,
    }
    response = admin.post(INSPECTORS, json=body)
    assert response.status == 201, f"inspector creation failed: {response.status} {response.text()[:200]}"
    return response.json()["data"]["id"], i


def _mapped_rto_ids(admin: ApiClient, email: str) -> list[int]:
    found = [x for x in admin.list_items(f"{INSPECTORS}?search={email}") if x["email"] == email]
    assert found, f"Inspector {email} is not in the list"
    return [m["rto"]["id"] for m in found[0]["rto_mappings"]]


@pytest.fixture
def inspector(admin_api: ApiClient, active_rtos: list[dict]):
    inspector_id, details = _create_inspector(admin_api, active_rtos[0]["id"])
    return {"id": inspector_id, "email": details.email, "password": details.password, "rto_id": active_rtos[0]["id"]}


def _transfer(admin: ApiClient, inspector_id: str, rto_id: int, **kwargs):
    return admin.put(f"{INSPECTORS}/{inspector_id}/rtos", json={"rto_ids": [rto_id]}, **kwargs)


def test_transfer_replaces_the_old_rto_with_the_new_one(admin_api: ApiClient, active_rtos: list[dict], inspector: dict) -> None:
    """Each transfer leaves the inspector linked to exactly the destination RTO (old link removed in the same step)."""
    assert _mapped_rto_ids(admin_api, inspector["email"]) == [inspector["rto_id"]]

    for destination in (active_rtos[1]["id"], active_rtos[2]["id"]):
        response = _transfer(admin_api, inspector["id"], destination)

        assert response.status == 200, response.text()[:300]
        assert _mapped_rto_ids(admin_api, inspector["email"]) == [destination]


def test_transfer_to_the_current_rto_is_refused(admin_api: ApiClient, inspector: dict) -> None:
    response = _transfer(admin_api, inspector["id"], inspector["rto_id"])

    assert response.status == 422 and "rto_ids" in response.json()["errors"], response.text()[:300]
    assert _mapped_rto_ids(admin_api, inspector["email"]) == [inspector["rto_id"]]


def test_transfer_to_an_unknown_rto_is_refused(admin_api: ApiClient, inspector: dict) -> None:
    response = _transfer(admin_api, inspector["id"], 99999999)

    assert response.status == 422 and "rto_ids" in str(response.json()["errors"]), response.text()[:300]
    assert _mapped_rto_ids(admin_api, inspector["email"]) == [inspector["rto_id"]]


def test_transfer_requires_authentication(admin_api: ApiClient, inspector: dict, active_rtos: list[dict]) -> None:
    response = _transfer(admin_api, inspector["id"], active_rtos[1]["id"], token=None)

    assert response.status == 401
    assert _mapped_rto_ids(admin_api, inspector["email"]) == [inspector["rto_id"]]


def test_new_inspector_must_change_the_temporary_password(page: Page, base_url: str, inspector: dict) -> None:
    """Guide s9.1 / s3: the first sign-in with the password set by the State Admin leads to Change Password."""
    login = LoginPage(page)
    login.navigate(base_url)
    login.login(inspector["email"], inspector["password"])
    expect(page).to_have_url(re.compile(r"/auth/change-password"), timeout=30_000)

    page.goto("/")  # try to leave the step
    expect(page).to_have_url(re.compile(r"/auth/change-password"))
