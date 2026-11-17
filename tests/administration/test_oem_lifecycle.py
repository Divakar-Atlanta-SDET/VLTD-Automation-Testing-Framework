"""
OEM lifecycle state transitions (deactivate / activate / blacklist).

Plan IDs: OEM-004, OEM-005, OEM-006
Plan: specs/state-admin-regression-test-plan.md

Endpoints:
  PATCH /api/transport-commissioner/oems/{id}/deactivate   body: {"remarks": "..."}
  PATCH /api/transport-commissioner/oems/{id}/activate     body: {"remarks": "..."}
  PATCH /api/transport-commissioner/oems/{id}/blacklist    body: {"remarks": "..."}

All three require a non-empty 'remarks' field; omitting it yields 422.
OEM statuses: active, suspended, blacklisted.
A blacklisted OEM CAN be reactivated (the server allows it).
OEMs cannot be deleted via the API so function-scoped fixtures create a fresh OEM per test.
"""

import pytest

from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.oem_mgmt_api import pdf_file

pytestmark = [pytest.mark.user_management, pytest.mark.api]

_REMARKS = "Automated lifecycle test"


# ── helpers ────────────────────────────────────────────────────────────────────

def _create_oem_via_api(admin: ApiClient) -> dict:
    """POST a fresh OEM and return its data dict (status must be 201)."""
    d = data.oem_data()
    pdf = pdf_file()
    resp = admin.post(
        f"{API_PREFIX}/oems",
        multipart={
            "business_name": d.business_name,
            "code": d.code,
            "cin_number": d.cin,
            "gst_number": d.gst,
            "tac_no": d.tac_number,
            "cop_no": d.cop_number,
            "tac_issued_on": "2026-01-15",
            "cop_valid_from": "2026-01-01",
            "cop_valid_till": "2026-12-31",
            "address_line_1": d.address,
            "address_line_2": d.address_line_2,
            "pincode": d.pincode,
            "contact_person_name": d.contact_name,
            "contact_email": d.email,
            "contact_phone": d.mobile,
            "password": d.password,
            "password_confirmation": d.password,
            "gst_certificate": pdf,
            "tac_certificate": pdf,
            "cop_certificate": pdf,
        },
    )
    assert resp.status == 201, f"OEM creation failed: {resp.status} {resp.text()[:200]}"
    created = resp.json()["data"]
    return {**created, "id": created["oem_id"]}


def _get_oem(admin: ApiClient, oem_id: int) -> dict:
    """Fetch a single OEM by id from the list endpoint and return its dict."""
    resp = admin.get(f"{API_PREFIX}/oems/{oem_id}")
    assert resp.status == 200, f"GET oem/{oem_id} failed: {resp.status} {resp.text()[:200]}"
    data_ = resp.json()["data"]
    return data_.get("oem", data_)


def _action(admin: ApiClient, oem_id: int, action: str, remarks: str | None = _REMARKS):
    """PATCH the given lifecycle action ('deactivate', 'activate', 'blacklist').
    Pass remarks=None to omit the body entirely (tests the validation path).
    """
    body = {"remarks": remarks} if remarks is not None else {}
    return admin.patch(f"{API_PREFIX}/oems/{oem_id}/{action}", json=body)


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_api(playwright, base_url: str, admin_credentials: dict) -> ApiClient:
    """Admin API client shared by every test in this session."""
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture
def test_oem(admin_api: ApiClient) -> dict:
    """A brand-new, active OEM created for each test. No teardown (OEMs cannot be deleted)."""
    return _create_oem_via_api(admin_api)


# ── tests ──────────────────────────────────────────────────────────────────────

def test_oem_deactivate_requires_remarks(admin_api: ApiClient) -> None:
    """OEM-004 (negative): PATCH deactivate without remarks body must return 422."""
    oem = _create_oem_via_api(admin_api)
    resp = _action(admin_api, oem["id"], "deactivate", remarks=None)

    assert resp.status == 422, f"Expected 422, got {resp.status}: {resp.text()[:300]}"
    errors = resp.json().get("errors", {})
    assert "remarks" in errors, f"'remarks' not in errors: {errors}"


def test_oem_activate_requires_remarks(admin_api: ApiClient) -> None:
    """OEM-004 (negative): PATCH activate without remarks body must return 422."""
    oem = _create_oem_via_api(admin_api)
    # Put the OEM into suspended state first so activate is meaningful
    deactivate_resp = _action(admin_api, oem["id"], "deactivate")
    assert deactivate_resp.status == 200, (
        f"Pre-condition failed (deactivate): {deactivate_resp.status} {deactivate_resp.text()[:200]}"
    )

    resp = _action(admin_api, oem["id"], "activate", remarks=None)

    assert resp.status == 422, f"Expected 422, got {resp.status}: {resp.text()[:300]}"
    errors = resp.json().get("errors", {})
    assert "remarks" in errors, f"'remarks' not in errors: {errors}"


def test_oem_suspend_then_activate(admin_api: ApiClient, test_oem: dict) -> None:
    """OEM-004/OEM-005: Deactivate an active OEM → suspended, then activate → active.
    Persisted status is verified via GET after each action.
    """
    oem_id = test_oem["id"]

    # Deactivate (suspend)
    deact = _action(admin_api, oem_id, "deactivate")
    assert deact.status == 200, f"deactivate failed: {deact.status} {deact.text()[:200]}"
    assert deact.json().get("success") is True
    assert "deactivated" in deact.json().get("message", "").lower()

    # Verify persisted state
    oem_after_deactivate = _get_oem(admin_api, oem_id)
    assert oem_after_deactivate["status"] == "suspended", (
        f"Expected 'suspended', got '{oem_after_deactivate['status']}'"
    )

    # Activate
    act = _action(admin_api, oem_id, "activate")
    assert act.status == 200, f"activate failed: {act.status} {act.text()[:200]}"
    assert act.json().get("success") is True
    assert "activated" in act.json().get("message", "").lower()

    # Verify persisted state
    oem_after_activate = _get_oem(admin_api, oem_id)
    assert oem_after_activate["status"] == "active", (
        f"Expected 'active', got '{oem_after_activate['status']}'"
    )


def test_oem_blacklist(admin_api: ApiClient, test_oem: dict) -> None:
    """OEM-006: Deactivate → blacklist. Verify persisted status == 'blacklisted'."""
    oem_id = test_oem["id"]

    # Suspend first (blacklist requires suspended state)
    deact = _action(admin_api, oem_id, "deactivate")
    assert deact.status == 200, f"deactivate pre-condition failed: {deact.status} {deact.text()[:200]}"

    # Blacklist
    bl = _action(admin_api, oem_id, "blacklist")
    assert bl.status == 200, f"blacklist failed: {bl.status} {bl.text()[:200]}"
    assert bl.json().get("success") is True
    assert "blacklisted" in bl.json().get("message", "").lower()

    # Verify persisted state via GET
    oem_after = _get_oem(admin_api, oem_id)
    assert oem_after["status"] == "blacklisted", (
        f"Expected 'blacklisted', got '{oem_after['status']}'"
    )


def test_oem_blacklisted_can_be_reactivated(admin_api: ApiClient, test_oem: dict) -> None:
    """OEM-006 (honest): The server allows reactivating a blacklisted OEM."""
    oem_id = test_oem["id"]

    _action(admin_api, oem_id, "deactivate")
    bl = _action(admin_api, oem_id, "blacklist")
    assert bl.status == 200, f"blacklist failed: {bl.status} {bl.text()[:200]}"

    # Reactivate from blacklisted state
    act = _action(admin_api, oem_id, "activate")
    assert act.status == 200, (
        f"Server rejected reactivation of a blacklisted OEM: {act.status} {act.text()[:300]}"
    )
    oem_after = _get_oem(admin_api, oem_id)
    assert oem_after["status"] == "active", (
        f"Expected 'active' after reactivation, got '{oem_after['status']}'"
    )


@pytest.mark.parametrize("action", ["deactivate", "activate", "blacklist"])
def test_oem_status_change_without_remarks_is_rejected(
    admin_api: ApiClient, test_oem: dict, action: str
) -> None:
    """OEM-004 (negative): Every lifecycle action requires remarks; omitting it yields 422."""
    oem_id = test_oem["id"]

    # For 'activate' and 'blacklist' the OEM must first be in the right state;
    # deactivate it so all three actions are callable (server validates remarks before state).
    _action(admin_api, oem_id, "deactivate")

    resp = _action(admin_api, oem_id, action, remarks=None)

    assert resp.status == 422, (
        f"action={action}: expected 422 for missing remarks, got {resp.status}: {resp.text()[:200]}"
    )
    errors = resp.json().get("errors", {})
    assert "remarks" in errors, f"action={action}: 'remarks' not in errors: {errors}"


def test_oem_deactivate_activate_does_not_affect_another_oem(admin_api: ApiClient) -> None:
    """OEM-005: Status transitions on one OEM must not alter another OEM's status."""
    oem_a = _create_oem_via_api(admin_api)
    oem_b = _create_oem_via_api(admin_api)

    # Deactivate only OEM-A
    deact = _action(admin_api, oem_a["id"], "deactivate")
    assert deact.status == 200, f"deactivate failed: {deact.status} {deact.text()[:200]}"

    # OEM-B must remain active
    oem_b_after = _get_oem(admin_api, oem_b["id"])
    assert oem_b_after["status"] == "active", (
        f"OEM-B status changed unexpectedly to '{oem_b_after['status']}' after OEM-A was deactivated"
    )
