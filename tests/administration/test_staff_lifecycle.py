"""
TC Staff lifecycle: status transitions (Active ↔ Suspended, Blacklist).
Plan: specs/state-admin-regression-test-plan.md  IDs: STAFF-004, STAFF-005, STAFF-006

API endpoints:
  PATCH /api/transport-commissioner/staff/{id}/activate    {"remarks": "..."}
  PATCH /api/transport-commissioner/staff/{id}/deactivate  {"remarks": "..."}
  PATCH /api/transport-commissioner/staff/{id}/blacklist   {"remarks": "..."}

Status values: approved (active), suspended, blacklisted.
"""

import pytest

from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.staff_lab import NEW_PASSWORD

pytestmark = [pytest.mark.user_management, pytest.mark.api]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_staff(admin: ApiClient, base_url: str) -> dict:
    """Create a fresh staff account with no permissions and a changed password."""
    s = data.staff_data()
    body = {
        "name": s.name, "email": s.email, "contact_no": s.mobile,
        "password": s.password, "password_confirmation": s.password, "permission_ids": [],
    }
    resp = admin.post(f"{API_PREFIX}/staff", json=body)
    assert resp.status == 201, f"staff creation failed: {resp.text()[:200]}"
    staff_id = resp.json()["data"]["id"]
    # Complete first-login password change
    tmp_client = ApiClient.login(admin.api, base_url, s.email, s.password)
    changed = tmp_client.post(
        "/api/auth/change-password",
        json={
            "current_password": s.password,
            "new_password": NEW_PASSWORD,
            "new_password_confirmation": NEW_PASSWORD,
        },
    )
    assert changed.ok, changed.text()[:200]
    return {"id": staff_id, "name": s.name, "email": s.email, "password": NEW_PASSWORD}


def _get_staff_status(admin: ApiClient, staff_id) -> str | None:
    """Walk paginated staff list and return the status string for the given id, or None."""
    page = 1
    while True:
        resp = admin.get(f"{API_PREFIX}/staff?per_page=100&page={page}")
        body = resp.json()
        # Paginated envelope: {"data": {"data": [...], "pagination": {...}}}
        outer = body.get("data", {})
        items = outer.get("data", []) if isinstance(outer, dict) else outer
        for item in items:
            if str(item.get("id")) == str(staff_id):
                return item.get("status")
        pagination = outer.get("pagination", {}) if isinstance(outer, dict) else {}
        last_page = pagination.get("last_page", 1)
        if page >= last_page:
            return None
        page += 1


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_api(playwright, base_url, admin_credentials) -> ApiClient:
    """Session-scoped admin ApiClient."""
    request = playwright.request.new_context()
    client = ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    yield client
    request.dispose()


@pytest.fixture
def staff_account(admin_api: ApiClient, base_url: str) -> dict:
    """Create a fresh staff account per test; no teardown (conftest sweeps at end-of-suite)."""
    account = _create_staff(admin_api, base_url)
    yield account


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_active_staff_can_be_suspended(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """STAFF-004: a newly created (approved) staff account can be suspended."""
    staff_id = staff_account["id"]

    # Fresh staff is approved after creation + password change
    assert _get_staff_status(admin_api, staff_id) == "approved"

    resp = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/deactivate",
        json={"remarks": "Suspended by automated test"},
    )
    assert resp.status == 200, resp.text()[:200]
    assert "deactivated" in resp.json().get("message", "").lower()

    # Verify the status persists
    assert _get_staff_status(admin_api, staff_id) == "suspended"


def test_suspended_staff_can_be_reactivated(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """STAFF-005: a suspended staff account can be reactivated to approved."""
    staff_id = staff_account["id"]

    # Deactivate first
    deact = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/deactivate",
        json={"remarks": "Suspend before reactivate test"},
    )
    assert deact.status == 200, deact.text()[:200]

    # Now reactivate
    resp = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/activate",
        json={"remarks": "Reactivated by automated test"},
    )
    assert resp.status == 200, resp.text()[:200]
    assert "activated" in resp.json().get("message", "").lower()

    # Verify the status persists
    assert _get_staff_status(admin_api, staff_id) == "approved"


def test_staff_cannot_use_api_while_suspended(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """STAFF-004: a suspended staff's token is immediately invalidated."""
    staff_id = staff_account["id"]

    # Log in as staff to obtain a token before suspension
    staff_client = ApiClient.login(admin_api.api, base_url, staff_account["email"], staff_account["password"])

    # Deactivate the staff account via admin
    deact = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/deactivate",
        json={"remarks": "Suspend to test token invalidation"},
    )
    assert deact.status == 200, deact.text()[:200]

    # The suspended staff's token should no longer be accepted
    probe = staff_client.get(f"{API_PREFIX}/dashboard")
    assert probe.status in (401, 403), (
        f"Expected 401/403 for suspended staff but got {probe.status}"
    )


def test_staff_lifecycle_suspend_reactivate_suspend(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """STAFF-006: status transitions are repeatable — suspend → activate → suspend."""
    staff_id = staff_account["id"]

    # First suspension
    r1 = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/deactivate",
        json={"remarks": "Cycle 1: deactivate"},
    )
    assert r1.status == 200, r1.text()[:200]
    assert _get_staff_status(admin_api, staff_id) == "suspended"

    # Reactivate
    r2 = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/activate",
        json={"remarks": "Cycle 1: reactivate"},
    )
    assert r2.status == 200, r2.text()[:200]
    assert _get_staff_status(admin_api, staff_id) == "approved"

    # Second suspension — idempotent / repeatable
    r3 = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/deactivate",
        json={"remarks": "Cycle 2: deactivate again"},
    )
    assert r3.status == 200, r3.text()[:200]
    assert _get_staff_status(admin_api, staff_id) == "suspended"


def test_deactivate_requires_no_body_or_accepts_remarks(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """Documents whether the remarks body is optional for staff deactivation.

    For staff (unlike OEM), remarks may be optional. This test sends deactivate
    without any body and records what the server returns. A 200 means remarks are
    optional; a 422 means they are required (both are documented outcomes).
    """
    staff_id = staff_account["id"]

    resp = admin_api.patch(f"{API_PREFIX}/staff/{staff_id}/deactivate")
    # Both 200 (remarks optional) and 422 (remarks required) are acceptable findings.
    assert resp.status in (200, 422), (
        f"Unexpected status {resp.status} when deactivating without body: {resp.text()[:200]}"
    )


def test_staff_blacklist(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """STAFF-006: a staff account can be blacklisted."""
    staff_id = staff_account["id"]

    resp = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/blacklist",
        json={"remarks": "Blacklisted by automated test"},
    )
    assert resp.status == 200, resp.text()[:200]
    assert "blacklisted" in resp.json().get("message", "").lower()

    assert _get_staff_status(admin_api, staff_id) == "blacklisted"


@pytest.mark.xfail(
    reason="BUG-034: Server allows reactivating blacklisted staff — blacklist should be terminal",
    strict=False,
)
def test_blacklisted_staff_reactivation_is_terminal(admin_api: ApiClient, staff_account: dict, base_url: str) -> None:
    """BUG-034: blacklist is supposed to be a terminal state; activating a blacklisted staff should fail."""
    staff_id = staff_account["id"]

    # Blacklist the staff first
    bl = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/blacklist",
        json={"remarks": "Blacklist before reactivation attempt"},
    )
    assert bl.status == 200, bl.text()[:200]
    assert _get_staff_status(admin_api, staff_id) == "blacklisted"

    # Attempt to reactivate — should be rejected (422 or 409)
    # Currently returns 200, which is the defect this xfail documents.
    resp = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/activate",
        json={"remarks": "Reactivate attempt on blacklisted staff"},
    )
    assert resp.status in (422, 409), (
        f"Expected 422/409 for reactivating a blacklisted staff but got {resp.status}"
    )


def test_status_actions_require_authentication(admin_api: ApiClient, staff_account: dict) -> None:
    """AUTH: status-change endpoints must reject requests with no token."""
    staff_id = staff_account["id"]

    resp = admin_api.patch(
        f"{API_PREFIX}/staff/{staff_id}/deactivate",
        json={"remarks": "No-auth attempt"},
        token=None,
    )
    assert resp.status in (401, 403), (
        f"Expected 401/403 without auth token but got {resp.status}"
    )
