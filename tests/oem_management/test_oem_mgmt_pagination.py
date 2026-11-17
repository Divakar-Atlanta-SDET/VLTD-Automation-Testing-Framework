"""
Pagination of the three OEM Management lists.   Plan: specs/oem-management-test-plan.md

The API pages its lists (10 per page, `meta.pagination`). The conftest keeps at least 12 records in every list
(the persistent "AUTO PG" seed), so every list spans two pages. These tests check that
  - the UI shows the newest 10 records first (same as API page 1),
  - every record is reachable from the UI - through a pager or by searching for it (BUG-024: it is not).
"""

import re

import pytest
from playwright.sync_api import expect

from tests.oem_management.bugs import NO_PAGINATION
from utils.oem_mgmt_api import FIRMWARES, MODELS, OemMgmtApi, SIMS

pytestmark = [pytest.mark.oem_management]

LISTS = [
    pytest.param("device_models_page", MODELS, "model_name", id="device-models"),
    pytest.param("firmware_page", FIRMWARES, "version", id="firmware"),
    pytest.param("sim_modules_page", SIMS, "module_name", id="sim-modules"),
]
PAGE_SIZE = 10


def _all_records(records: OemMgmtApi, path: str) -> list[dict]:
    return records.admin.get(f"{path}?per_page=100").json()["data"]


@pytest.mark.parametrize("page_fixture, path, name_key", LISTS)
def test_the_seed_keeps_every_list_above_one_page(request, records: OemMgmtApi, page_fixture, path, name_key) -> None:
    body = records.admin.get(path).json()["meta"]["pagination"]

    assert body["total"] >= 12, f"{path} has only {body['total']} records"
    assert body["per_page"] == PAGE_SIZE and body["has_more"] is True and body["last_page"] >= 2



@NO_PAGINATION
@pytest.mark.parametrize("page_fixture, path, name_key", LISTS)
def test_every_record_is_reachable_from_the_list(request, records: OemMgmtApi, page_fixture, path, name_key) -> None:
    """Either a pager shows the remaining records, or the page loads them all."""
    page = request.getfixturevalue(page_fixture).open()
    total = records.admin.get(f"{path}?per_page=1").json()["meta"]["pagination"]["total"]

    pager = page.page.get_by_role("button", name=re.compile(r"next|›|»|page \d", re.I))
    reachable = page.rows().count()
    while pager.count() and pager.first.is_enabled() and reachable < total:
        pager.first.click()
        page.page.wait_for_timeout(500)
        reachable += page.rows().count()

    assert reachable >= total, f"The UI can show only {reachable} of {total} records and offers no way to see the rest"


@NO_PAGINATION
@pytest.mark.parametrize("page_fixture, path, name_key", LISTS)
def test_search_finds_a_record_that_is_beyond_the_first_page(request, records: OemMgmtApi, page_fixture, path, name_key) -> None:
    page = request.getfixturevalue(page_fixture).open()
    # Pick a record the page is NOT showing. Taking "the 11th record of the API" is unreliable: records created in the same
    # second have no stable order (BUG-030), so the page and the API can disagree about which ten come first.
    shown = " ".join(page.rows().all_inner_texts())
    hidden = [r for r in _all_records(records, path) if r[name_key] not in shown]
    assert hidden, "the seed should leave at least one record that the first page does not show"
    name = hidden[0][name_key]

    page.search(name)

    expect(page.row(name)).to_have_count(1)
