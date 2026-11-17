"""
Device Model and SIM Module deletion constraints (DM-008, SIM-006).

Plan: specs/state-admin-regression-test-plan.md

Verified API behaviour:
  DELETE /api/device-models/{id}?oem_id={oem_id}
    → 422  "Cannot delete device model linked with devices."  (model has an installation)
    → 200  (model is not linked to any installation)
  DELETE /api/sim-modules/{id}?oem_id={oem_id}
    → 422 or 409  when the SIM module is linked to an installed device

Tests skip cleanly when the required environment data is absent.
"""

import pytest

from utils.api_client import ApiClient
from utils.oem_mgmt_api import MODELS, SIMS, OemMgmtApi

pytestmark = [pytest.mark.oem_management, pytest.mark.api]

_INSTALLATION_PATH = "/api/installation"


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_api(playwright, base_url: str, admin_credentials: dict) -> ApiClient:
    """Admin API client shared by every test in this session."""
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


# ── helpers ────────────────────────────────────────────────────────────────────

def _installations(admin: ApiClient, per_page: int = 20) -> list[dict]:
    """Return up to `per_page` installation records (empty list if none or endpoint absent)."""
    resp = admin.get(f"{_INSTALLATION_PATH}?per_page={per_page}")
    if resp.status not in (200,):
        return []
    body = resp.json()
    # The endpoint may wrap items under data.data (paginated) or data (flat list)
    raw = body.get("data", [])
    if isinstance(raw, dict):
        return raw.get("data", [])
    return raw if isinstance(raw, list) else []


# ── tests ──────────────────────────────────────────────────────────────────────

def test_delete_device_model_linked_to_installation_is_refused(admin_api: ApiClient) -> None:
    """DM-008: DELETE a device model that is linked to at least one installed device → 422."""
    records = _installations(admin_api)
    if not records:
        pytest.skip("No installation records found in environment")

    # Find an installation that carries a device with a device_model
    model_id: int | None = None
    oem_id: int | None = None
    for inst in records:
        device = inst.get("device") or {}
        dm = device.get("device_model") or {}
        if dm.get("id"):
            model_id = dm["id"]
            # Resolve the oem_id: try from the model dict, then from the device, then from a detail call
            oem_id = (
                dm.get("oem_id")
                or device.get("oem_id")
                or inst.get("oem_id")
            )
            if oem_id is None:
                # Fetch device-model detail to get oem_id
                detail_resp = admin_api.get(f"{MODELS}/{model_id}")
                if detail_resp.status == 200:
                    detail = detail_resp.json().get("data", {})
                    oem_id = (detail.get("oem") or {}).get("id") or detail.get("oem_id")
            if oem_id:
                break

    if model_id is None:
        pytest.skip("No installed device with a device_model found in environment")
    if oem_id is None:
        pytest.skip(f"Could not resolve oem_id for device_model {model_id}")

    resp = admin_api.delete(f"{MODELS}/{model_id}?oem_id={oem_id}")

    assert resp.status == 422, (
        f"Expected 422 for linked model {model_id}, got {resp.status}: {resp.text()[:300]}"
    )
    message = (resp.json().get("message") or "").lower()
    assert "cannot delete" in message or "linked" in message, (
        f"Unexpected 422 message for linked model: {resp.text()[:300]}"
    )


def test_delete_unlinked_device_model_succeeds(admin_api: ApiClient) -> None:
    """DM-008 (positive): A freshly created device model not linked to any installation can be deleted."""
    mgmt = OemMgmtApi(admin_api)
    model = mgmt.create_model()
    model_id = model["id"]
    oem_id = mgmt.oem_id

    # Delete
    del_resp = admin_api.delete(f"{MODELS}/{model_id}?oem_id={oem_id}")
    assert del_resp.status == 200, (
        f"Expected 200 for unlinked model delete, got {del_resp.status}: {del_resp.text()[:300]}"
    )

    # Verify it is gone
    get_resp = admin_api.get(f"{MODELS}/{model_id}")
    assert get_resp.status == 404, (
        f"Model {model_id} still exists after deletion (status={get_resp.status})"
    )


def test_delete_sim_module_linked_to_installation_is_refused(admin_api: ApiClient) -> None:
    """SIM-006: DELETE a SIM module that is linked to an installed device → 422 or 409."""
    records = _installations(admin_api)
    if not records:
        pytest.skip("No installation records found in environment")

    sim_id: int | None = None
    oem_id: int | None = None
    for inst in records:
        device = inst.get("device") or {}
        # The SIM module may appear under different keys depending on API version
        sim = (
            device.get("sim_module")
            or device.get("simModule")
            or {}
        )
        sim_id_candidate = sim.get("id") or device.get("sim_module_id")
        if sim_id_candidate:
            sim_id = sim_id_candidate
            oem_id = (
                sim.get("oem_id")
                or device.get("oem_id")
                or inst.get("oem_id")
            )
            if oem_id is None:
                # Fetch SIM module detail to get oem_id
                detail_resp = admin_api.get(f"{SIMS}/{sim_id}")
                if detail_resp.status == 200:
                    detail = detail_resp.json().get("data", {})
                    oem_id = (detail.get("oem") or {}).get("id") or detail.get("oem_id")
            if oem_id:
                break

    if sim_id is None:
        # Log what the installation structure looks like to aid future debugging
        if records:
            first_device = records[0].get("device") or {}
            print(f"[debug] installation device keys: {list(first_device.keys())}")
        pytest.skip("No installed device with a SIM module found in environment")
    if oem_id is None:
        pytest.skip(f"Could not resolve oem_id for sim_module {sim_id}")

    resp = admin_api.delete(f"{SIMS}/{sim_id}?oem_id={oem_id}")

    # Server may return 422 (validation) or 409 (conflict) — document honestly
    assert resp.status in (422, 409), (
        f"Expected 422 or 409 for linked SIM {sim_id}, got {resp.status}: {resp.text()[:300]}"
    )
