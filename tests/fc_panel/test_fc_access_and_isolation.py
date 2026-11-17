"""
Fitment Centre panel - role permission boundary (FC cannot reach OEM-only screens/actions, and vice versa).

Modelled on `tests/oem_panel/test_oem_access_and_isolation.py`'s OEM-A2 ("State Admin features are closed to the
OEM"), applied to the FC/OEM boundary instead. Two directions are checked, at both levels:

  page routing   direct-URL visits to the other role's pages land on /unauthorized
  API            the other role's bearer token is refused by write endpoints (garbage/minimal bodies - the point is
                 whether the role check runs at all, not whether a resource actually gets created) and by reads of
                 the other role's own data

Two endpoints are deliberately NOT asserted here (`GET /api/device-command-templates`, `GET /api/device-repairs`
with the FC's token; `GET /api/installation` with the OEM's token): all three returned 200, not the 403 every other
OEM/FC-only resource gave. That could be intentional shared/jurisdiction-scoped reads (see the Fitment Centre test
plan's "Risks" for this module) rather than a leak, and nothing here should assert a business rule that was never
confirmed either way.
"""

import pytest
from playwright.sync_api import Page

from utils.api_client import ApiClient
from utils.fc_panel_api import INSTALLATIONS, INVENTORY_SUMMARY, TAG_DEVICE
from utils.oem_panel_api import ALLOCATIONS, COMMAND_TEMPLATES, DEVICES, FITMENT_CENTRES

pytestmark = [pytest.mark.fc_panel]

OTHER_FC_NAME = "AUTO PG FC lifecycle"  # a real, long-lived, disposable fitment centre - not this session's own FC_USERNAME account


@pytest.fixture(scope="module")
def other_fc_id(oem_api: ApiClient) -> int:
    listed = oem_api.get(f"{FITMENT_CENTRES}?per_page=100&search={OTHER_FC_NAME}").json()["data"]
    match = next((f for f in listed if f["business_name"] == OTHER_FC_NAME), None)
    if match is None:
        pytest.skip(f"'{OTHER_FC_NAME}' does not exist on this OEM account")
    return match["id"]


# ── page routing: FC visiting OEM-only pages ───────────────────────────────────

OEM_ONLY_PAGES = [
    "/oem/device-allocations", "/oem/device-models", "/oem/devices", "/oem/inventory/allocate-stock",
    "/oem/operations/sim-validity-extension", "/oem/repairs", "/oem/users/fitment-centers", "/oem/users/staff",
    "/oem/reports/device-installations", "/oem/reports/oem-performance", "/oem/reports/expired-installations",
    "/oem/audit-reports/ticket-performance",
]


@pytest.mark.parametrize("path", OEM_ONLY_PAGES, ids=lambda p: p.rsplit("/", 1)[1])
def test_fc_visiting_an_oem_only_page_is_sent_to_unauthorized(fc_page: Page, path: str) -> None:
    fc_page.goto(path)
    fc_page.wait_for_url("**/unauthorized", timeout=10_000)


# ── page routing: OEM visiting FC-only pages (reverse direction) ──────────────

FC_ONLY_PAGES = [
    "/fc/new-installation", "/fc/repair-installation", "/fc/installation-jobs", "/fc/map-devices",
    "/fc/device-models", "/fc/installation-history",
]


@pytest.mark.parametrize("path", FC_ONLY_PAGES, ids=lambda p: p.rsplit("/", 1)[1])
def test_oem_visiting_an_fc_only_page_is_sent_to_unauthorized(oem_page: Page, path: str) -> None:
    oem_page.goto(path)
    oem_page.wait_for_url("**/unauthorized", timeout=10_000)


# ── API: FC's token against OEM-only reads ─────────────────────────────────────

OEM_ONLY_READS = [
    DEVICES, ALLOCATIONS, FITMENT_CENTRES,
    "/api/dashboard/oem/device-inventory", "/api/dashboard/oem/allocation-summary", "/api/dashboard/oem/fitment-summary",
    "/api/devices/bulk-upload/sample",
]


@pytest.mark.parametrize("path", OEM_ONLY_READS, ids=lambda p: p.rsplit("/", 1)[1])
def test_fc_token_is_refused_oem_only_reads(fc_api: ApiClient, path: str) -> None:
    assert fc_api.get(path).status == 403


def test_fc_token_is_refused_another_fitment_centres_detail(fc_api: ApiClient, other_fc_id: int) -> None:
    assert fc_api.get(f"{FITMENT_CENTRES}/{other_fc_id}").status == 403


# ── API: FC's token against OEM-only writes (minimal/garbage bodies - the role check is what's being tested) ──

OEM_ONLY_WRITES = [
    ("POST", DEVICES, {}),
    ("POST", ALLOCATIONS, {}),
    ("POST", f"{ALLOCATIONS}/9999999/rollback", {}),
    ("POST", COMMAND_TEMPLATES, {}),
    ("POST", FITMENT_CENTRES, {}),
]


@pytest.mark.parametrize("method, path, body", OEM_ONLY_WRITES, ids=lambda v: v if isinstance(v, str) else "")
def test_fc_token_is_refused_oem_only_writes(fc_api: ApiClient, method: str, path: str, body: dict) -> None:
    assert fc_api.request(method, path, json=body).status == 403


def test_fc_token_cannot_deactivate_another_fitment_centre(fc_api: ApiClient, oem_api: ApiClient, other_fc_id: int) -> None:
    before = oem_api.get(f"{FITMENT_CENTRES}/{other_fc_id}").json()["data"]["fitment_centre"]["status"]

    response = fc_api.patch(f"{FITMENT_CENTRES}/{other_fc_id}/deactivate", json={"remarks": "AUTO permission-boundary probe"})

    assert response.status == 403
    after = oem_api.get(f"{FITMENT_CENTRES}/{other_fc_id}").json()["data"]["fitment_centre"]["status"]
    assert after == before, "the fitment centre's status changed even though the request was refused"


# ── API: OEM's token against FC-only reads and writes (reverse direction) ─────

FC_ONLY_READS = ["/api/dashboard/fitment-centre/summary", INVENTORY_SUMMARY]


@pytest.mark.parametrize("path", FC_ONLY_READS, ids=["dashboard-summary", "inventory-summary"])
def test_oem_token_is_refused_fc_only_reads(oem_api: ApiClient, path: str) -> None:
    assert oem_api.get(path).status == 403


FC_ONLY_WRITES = [("POST", INSTALLATIONS, {}), ("POST", TAG_DEVICE, {})]


@pytest.mark.parametrize("method, path, body", FC_ONLY_WRITES, ids=lambda v: v if isinstance(v, str) else "")
def test_oem_token_is_refused_fc_only_writes(oem_api: ApiClient, method: str, path: str, body: dict) -> None:
    assert oem_api.request(method, path, json=body).status == 403
