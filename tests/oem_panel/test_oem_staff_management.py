"""
OEM staff management (OEM Staff page).

Confirmed by the product owner: the OEM manages its own staff, so listing staff and registering staff must work for the
OEM Admin. Today every call answers 403 even though the OEM Admin holds all 41 permissions of its catalogue
(known defect, BUG-039). These tests describe the expected behaviour and are expected to fail until it is fixed.
"""

import pytest
from playwright.sync_api import Page

from pages.oem_panel.misc import OemStaffPage
from utils.api_client import ApiClient
from utils.page_health import load_problems

pytestmark = [pytest.mark.oem_panel]

KNOWN_DEFECT = pytest.mark.xfail(
    reason="BUG-039: /api/oem/users answers 403 for the OEM Admin, so staff can be neither listed nor registered",
    strict=False,
)


@KNOWN_DEFECT
def test_oem_can_list_its_staff(oem_api: ApiClient) -> None:
    response = oem_api.get("/api/oem/users?page=1")

    assert response.status == 200, f"{response.status} {response.text()[:200]}"


@KNOWN_DEFECT
def test_registering_staff_validates_instead_of_refusing_the_oem(oem_api: ApiClient) -> None:
    """An empty request must be answered with the list of missing fields (422), not with 'no permission' (403)."""
    response = oem_api.post("/api/oem/users", json={})

    assert response.status == 422, f"{response.status} {response.text()[:200]}"


@KNOWN_DEFECT
def test_staff_page_loads_without_failed_calls(oem_page: Page) -> None:
    OemStaffPage(oem_page).open()  # the page is reachable ...

    assert not load_problems(oem_page, OemStaffPage.PATH), "... but the list request behind it fails"
