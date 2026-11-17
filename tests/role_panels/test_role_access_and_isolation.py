"""
Driver / RTO Inspector / RTO Officer - cross-role permission boundary.

Modelled on `tests/fc_panel/test_fc_access_and_isolation.py`. Two directions are checked:

  page routing   direct-URL visits to another role's (or Admin's) pages land on /unauthorized
  API            another role's bearer token is refused by role-exclusive reads and writes

Plus the BUG-086 regression: the Inspector's token should be refused by the RTO-only installation-approval
endpoints the same way the Driver's is, but it currently is not (see bug_report.md).
"""

import pytest
from playwright.sync_api import Page

from utils.api_client import ApiClient
from utils.role_panel_api import RTO_PENDING_INSTALLATIONS, rto_installation_approve

pytestmark = [pytest.mark.rto_panel, pytest.mark.inspector_panel, pytest.mark.driver_panel]

# A deliberately non-existent installation ID: the point is whether the AUTHORIZATION check runs at all
# (403 = refused before reaching business logic) rather than whether a real installation gets approved.
BOGUS_INSTALLATION_ID = 999_999_999

OTHER_ROLE_DASHBOARDS = ["/tc/dashboard", "/fc/dashboard", "/oem/dashboard"]


# ── page routing: each role visiting another role's (or Admin's) pages ────────

@pytest.mark.parametrize("path", OTHER_ROLE_DASHBOARDS + ["/rto/dashboard", "/inspector/dashboard"], ids=lambda p: p.rsplit("/", 1)[0].lstrip("/") + "-" + p.rsplit("/", 1)[1])
def test_driver_visiting_a_non_driver_page_is_sent_to_unauthorized(driver_page: Page, path: str) -> None:
    driver_page.goto(path)
    driver_page.wait_for_url("**/unauthorized", timeout=10_000)


@pytest.mark.parametrize("path", OTHER_ROLE_DASHBOARDS + ["/driver/dashboard", "/tc/users/rto"], ids=lambda p: p.rsplit("/", 1)[0].lstrip("/") + "-" + p.rsplit("/", 1)[1])
def test_inspector_visiting_a_non_inspector_page_is_sent_to_unauthorized(inspector_page: Page, path: str) -> None:
    inspector_page.goto(path)
    inspector_page.wait_for_url("**/unauthorized", timeout=10_000)


@pytest.mark.parametrize("path", OTHER_ROLE_DASHBOARDS + ["/driver/dashboard", "/inspector/dashboard", "/tc/users/rto"], ids=lambda p: p.rsplit("/", 1)[0].lstrip("/") + "-" + p.rsplit("/", 1)[1])
def test_rto_visiting_a_non_rto_page_is_sent_to_unauthorized(rto_page: Page, path: str) -> None:
    rto_page.goto(path)
    rto_page.wait_for_url("**/unauthorized", timeout=10_000)


# ── API: Driver's token against RTO/Inspector-only reads and writes ────────────

def test_driver_token_is_refused_the_rto_pending_installations_list(driver_api: ApiClient) -> None:
    assert driver_api.get(RTO_PENDING_INSTALLATIONS).status == 403


def test_driver_token_is_refused_installation_approval(driver_api: ApiClient) -> None:
    assert driver_api.post(rto_installation_approve(BOGUS_INSTALLATION_ID), json={}).status == 403


def test_driver_token_is_refused_inspector_challans(driver_api: ApiClient) -> None:
    assert driver_api.get("/api/inspector/challans").status == 403


def test_driver_token_is_refused_inspector_dashboard(driver_api: ApiClient) -> None:
    assert driver_api.get("/api/inspector/dashboard").status == 403


def test_rto_token_is_refused_driver_only_reads(rto_api: ApiClient) -> None:
    assert rto_api.get("/api/driver/duty/me").status == 403


# ── BUG-086 regression: the Inspector should NOT pass the installation-approval authorization check ──

@pytest.mark.xfail(reason="BUG-086: an RTO Inspector's token is wrongly accepted by the RTO-only installation approval endpoints", strict=False)
def test_inspector_token_is_refused_the_rto_pending_installations_list(inspector_api: ApiClient) -> None:
    assert inspector_api.get(RTO_PENDING_INSTALLATIONS).status == 403


@pytest.mark.xfail(reason="BUG-086: an RTO Inspector's token is wrongly accepted by the RTO-only installation approval endpoints", strict=False)
def test_inspector_token_is_refused_installation_approval(inspector_api: ApiClient) -> None:
    response = inspector_api.post(rto_installation_approve(BOGUS_INSTALLATION_ID), json={})
    assert response.status == 403, (
        f"expected 403 (refused before reaching business logic), got {response.status} - "
        "the Inspector's request reached the same 'not found' logic an RTO Officer's would"
    )
