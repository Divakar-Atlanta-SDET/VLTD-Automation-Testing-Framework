"""
OEM Fitment Centres (guide chapter 3 and 6.1): the OEM manages the workshops that install its devices.

  Counters equal the rows; filters return only matching centres; registering a centre is validated.
  The happy-path registration is manual: it creates a login account that the application cannot delete.
  Every refusal below leaves out the mandatory image, so even a server that skipped a rule could not create a centre.

OEM-E1, OEM-E2 of specs/oem-panel-test-plan.md.
"""

import random

import pytest
from playwright.sync_api import Page

from pages.oem_panel.misc import FitmentCentersPage
from utils.api_client import ApiClient
from utils.oem_panel_api import FITMENT_CENTRES

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]  # the counters move when the lifecycle tests change a centre

STATUS_COUNTERS = {"active": "ACTIVE", "suspended": "SUSPENDED", "blacklisted": "BLACKLISTED"}


def _listing(oem: ApiClient, query: str = "") -> dict:
    return oem.get(f"{FITMENT_CENTRES}?per_page=100&{query}").json()


def test_counters_equal_the_rows(oem_api: ApiClient) -> None:
    body = _listing(oem_api)
    rows, summary = body["data"], body["summary"]

    assert summary["total"] == len(rows)
    for status in STATUS_COUNTERS:
        assert summary[status] == sum(r["status"] == status for r in rows), status


def test_page_shows_the_same_counters(oem_api: ApiClient, oem_page: Page) -> None:
    summary = _listing(oem_api)["summary"]

    FitmentCentersPage(oem_page).open().expect_counters(
        Total_Centers=summary["total"], Active=summary["active"], Suspended=summary["suspended"], Blacklisted=summary["blacklisted"],
    )


def test_filters_return_only_matching_centres(oem_api: ApiClient) -> None:
    rows = _listing(oem_api)["data"]
    sample = rows[0]

    by_status = _listing(oem_api, f"status={sample['status']}")["data"]
    by_name = _listing(oem_api, f"search={sample['business_name']}")["data"]

    assert by_status and all(r["status"] == sample["status"] for r in by_status)
    assert any(r["id"] == sample["id"] for r in by_name)
    assert all(sample["business_name"].lower() in r["business_name"].lower() for r in by_name)
    assert _listing(oem_api, "search=zzz-no-such-centre")["data"] == []


# ── OEM-E2: registering a centre is validated ─────────────────────────────────

@pytest.fixture(scope="module")
def valid_fc_fields(oem_api: ApiClient) -> dict:
    """Every field valid EXCEPT the missing image, so the request can never create a centre."""
    rto = oem_api.get("/api/rto-dropdown").json()["data"][0]
    city = oem_api.get("/api/masters/cities").json()["data"][0]
    return {
        "business_name": "AUTO FC never created", "short_name": "AUTOFCX", "owner_name": "Auto Owner",
        "contact_no": "9" + "".join(random.choices("0123456789", k=9)), "email_id": "auto.fc.never@example.com", "address_line_1": "Automation Road",
        "city_id": city["id"], "pincode": "110001", "latitude": 28.6139, "longitude": 77.209,
        "rto_id": rto["id"], "password": "Auto@12345Test", "password_confirmation": "Auto@12345Test",
    }


def test_registration_without_details_lists_every_required_field(oem_api: ApiClient) -> None:
    response = oem_api.post(FITMENT_CENTRES, json={})

    required = {"business_name", "short_name", "owner_name", "contact_no", "email_id", "address_line_1", "city_id",
                "pincode", "latitude", "longitude", "rto_id", "password", "fitment_centre_image"}
    assert response.status == 422
    assert required <= set(response.json()["errors"])


@pytest.mark.parametrize(
    "override, error_field",
    [
        ({"pincode": "11000"}, "pincode"),
        ({"email_id": "not-an-email"}, "email_id"),
        ({"contact_no": "987654321"}, "contact_no"),
        ({"password": "short1A", "password_confirmation": "short1A"}, "password"),
        ({"password_confirmation": "Different@12345"}, "password"),
        ({"rto_id": 999999}, "rto_id"),
        ({"city_id": 999999}, "city_id"),
        ({"latitude": 91}, "latitude"),
    ],
    ids=["pincode-5-digits", "email-without-at", "mobile-9-digits", "password-weak", "password-mismatch",
         "unknown-rto", "unknown-city", "latitude-out-of-range"],
)
def test_invalid_registration_names_the_field(oem_api: ApiClient, valid_fc_fields: dict, override: dict, error_field: str) -> None:
    before = _listing(oem_api)["summary"]["total"]

    response = oem_api.post(FITMENT_CENTRES, json={**valid_fc_fields, **override})

    assert response.status == 422 and error_field in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert _listing(oem_api)["summary"]["total"] == before


@pytest.mark.xfail(
    reason="BUG-042: the server does not report a duplicate fitment code, although the form says it is unique",
    strict=False,
)
def test_duplicate_fitment_code_is_refused(oem_api: ApiClient, valid_fc_fields: dict) -> None:
    existing = _listing(oem_api)["data"][0]["short_name"]

    response = oem_api.post(FITMENT_CENTRES, json={**valid_fc_fields, "short_name": existing})

    assert response.status == 422 and "short_name" in response.json()["errors"], f"{response.status} {response.text()[:300]}"
