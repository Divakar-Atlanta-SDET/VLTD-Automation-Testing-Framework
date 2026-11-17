"""
Account merge refusals (guide section 7.2).

  School accounts cannot be merged.
  A merged account cannot be merged again and cannot receive transfers (here: cannot be the destination).

Every scenario is a REFUSAL: nothing changes when the server behaves as documented. The accounts come from the
environment itself (a merged account from the Account Merge Report, a school from the account search), so the
tests skip - visibly - when the environment has no such account.
"""

import pytest

from utils.api_client import API_PREFIX, ApiClient
from utils.oem_mgmt_api import pdf_file

pytestmark = [pytest.mark.api]

MERGE = f"{API_PREFIX}/account-merge"


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="module")
def accounts(admin_api: ApiClient) -> dict:
    """{'merged': owner id, 'active': owner id, 'school': owner id} found in the environment."""
    report = admin_api.get(f"{MERGE}/report").json()["data"]
    if not report:
        pytest.skip("The environment has no completed account merge")
    merged, active = report[0]["source_owner"]["id"], report[0]["destination_owner"]["id"]

    found = admin_api.get(f"{MERGE}/accounts?search=School").json()["data"]
    schools = [a["id"] for a in found if a["type"] == "School" and a["status"] == "Approved"]
    if not schools:
        pytest.skip("The environment has no active School account")
    return {"merged": merged, "active": active, "school": schools[0]}


def _merge(admin: ApiClient, source: int, destination: int):
    return admin.post(
        MERGE,
        multipart={
            "source_owner_id": str(source),
            "destination_owner_id": str(destination),
            "document": pdf_file(),
            "ownership_confirmed": "1",
            "reason": "administrative_correction",
            "remarks": "Automated refusal check",
        },
    )


@pytest.mark.parametrize(
    "source, destination, refused_field, message",
    [
        ("school", "active", "source_owner_id", "school accounts cannot be merged"),
        ("merged", "active", "source_owner_id", "already been merged"),
        ("active", "merged", "destination_owner_id", "not active"),
    ],
    ids=["school-cannot-be-merged", "merged-cannot-be-merged-again", "merged-cannot-receive"],
)
def test_forbidden_merges_are_refused_and_change_nothing(
    admin_api: ApiClient, accounts: dict, source: str, destination: str, refused_field: str, message: str
) -> None:
    merges_before = admin_api.get(f"{MERGE}/report").json()["pagination"]["total"]

    response = _merge(admin_api, accounts[source], accounts[destination])

    assert response.status == 422, f"Forbidden merge was not refused: {response.status} {response.text()[:300]}"
    errors = response.json()["errors"]
    assert refused_field in errors and message in " ".join(errors[refused_field]).lower(), errors
    assert admin_api.get(f"{MERGE}/report").json()["pagination"]["total"] == merges_before
