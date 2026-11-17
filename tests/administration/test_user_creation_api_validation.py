"""
Server-side validation of the User Management create endpoints.

The create forms limit input in the browser (maxlength, required, formats). These tests skip the
browser and send the request directly, to prove the SERVER enforces the same rules. Each case
changes ONE field of an otherwise valid body and expects:
  - a 4xx answer (422) whose `errors` object names that field,
  - never a 2xx (record created), never a 5xx, never a stack trace / SQL / path in the body.

Also checks that every create endpoint refuses callers without a valid token.
Endpoints: /api/transport-commissioner/{inspectors,rtos,staff} (JSON) and {oems,drivers} (auth only).
"""

import re

import pytest
from playwright.sync_api import Page

from utils import data_generator as data
from utils.api_client import API_PREFIX, AdminApi
from utils.network_monitor import LEAK_PATTERN

pytestmark = [pytest.mark.user_management, pytest.mark.negative, pytest.mark.api]

CREATE_ENDPOINTS = ["inspectors", "rtos", "staff", "oems", "drivers"]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def api(admin_page: Page) -> AdminApi:
    return AdminApi(admin_page)


@pytest.fixture
def city_id(api: AdminApi) -> int:
    return api.first_id("/api/masters/cities")


@pytest.fixture
def rto_id(api: AdminApi) -> int:
    return api.first_id(f"{API_PREFIX}/rtos")


def inspector_body(base_city_id: int, base_rto_id: int, **overrides) -> dict:
    i = data.inspector_data()
    body = {
        "name": i.name,
        "email": i.email,
        "contact_no": i.mobile,
        "address": i.address,
        "city_id": base_city_id,
        "rto_ids": [base_rto_id],
        "password": i.password,
        "password_confirmation": i.password,
    }
    return {**body, **overrides}


def rto_body(base_city_id: int, taken_codes: set[str], **overrides) -> dict:
    r = data.rto_data(taken_codes)
    body = {
        "code": r.code,
        "name": r.name,
        "description": r.description,
        "address": r.address,
        "contact_email": r.email,
        "contact_number": r.mobile,
        "city_id": base_city_id,
        "pincode": r.pincode,
        "latitude": 28.6139,
        "longitude": 77.209,
        "password": r.password,
        "password_confirmation": r.password,
    }
    return {**body, **overrides}


def staff_body(**overrides) -> dict:
    s = data.staff_data()
    body = {
        "name": s.name,
        "email": s.email,
        "contact_no": s.mobile,
        "password": s.password,
        "password_confirmation": s.password,
        "permission_ids": [],
    }
    return {**body, **overrides}


def assert_field_rejected(response, field: str) -> None:
    """4xx, success=false, and the `errors` object has an entry for `field` (or `field.N`)."""
    text = response.text()
    assert response.status != 201 and response.status < 500, (
        f"Expected a validation error for '{field}', got {response.status}: {text[:300]}"
    )
    assert response.status in (400, 422), f"Unexpected status {response.status}: {text[:300]}"
    assert not LEAK_PATTERN.search(text), f"Response leaks internals: {text[:300]}"
    body = response.json()
    assert body.get("success") is False, body
    errors = body.get("errors") or {}
    assert any(key == field or key.startswith(field + ".") for key in errors), (
        f"No error reported for '{field}'. errors={errors}"
    )


def case(case_id, field, value=None, *, error_field=None, bug=None, creates_record=True, **extra):
    """One invalid field. `error_field`: key the server reports it under (defaults to `field`).

    `bug`: a known server defect (see bug_report.md). If the bug makes the server ACCEPT the data it
    would create a record on every run, so it is skipped by default (`creates_record=True`); run it on
    purpose with `pytest --runxfail`. Bugs that create nothing (e.g. a 500) still run and xfail.
    """
    marks = [pytest.mark.xfail(run=not creates_record, reason=f"{bug}: known server defect")] if bug else []
    return pytest.param(field, value, extra, error_field or field, id=case_id, marks=marks)


# ── Authentication on every create endpoint ───────────────────────────────────

@pytest.mark.parametrize("endpoint", CREATE_ENDPOINTS)
def test_create_endpoint_requires_a_valid_token(api: AdminApi, endpoint: str) -> None:
    """AUTH-003/004: with no token or a malformed one the caller gets 401/403 - it must not reach validation (422) or crash."""
    for token in (None, "garbage.token.value"):
        response = api.post(f"{API_PREFIX}/{endpoint}", json={}, token=token)

        assert response.status in (401, 403), f"{endpoint} answered {response.status} to token={token!r}: {response.text()[:200]}"
        assert not LEAK_PATTERN.search(response.text())


# ── Inspector ─────────────────────────────────────────────────────────────────

INSPECTOR_API_CASES = [
    case("name-blank", "name", ""),
    case("name-300-chars", "name", "A" * 300),
    case("email-invalid", "email", "not-an-email"),
    case("contact-9-digits", "contact_no", "987654321"),
    case("password-no-uppercase", "password", "alllowercase123", password_confirmation="alllowercase123"),
    case("password-no-lowercase", "password", "ALLUPPERCASE123", password_confirmation="ALLUPPERCASE123"),
    case("password-no-number", "password", "NoDigitsHereAtAll", password_confirmation="NoDigitsHereAtAll"),
    case("password-9-chars", "password", "Abcdefg12", password_confirmation="Abcdefg12", bug="BUG-035"),
    case("password-mismatch", "password_confirmation", "Different@12345", error_field="password", bug="BUG-012"),
    case("city-does-not-exist", "city_id", 999999),
    case("city-wrong-type", "city_id", "abc", bug="BUG-013", creates_record=False),
    case("rto-does-not-exist", "rto_ids", [999999]),
]


@pytest.mark.parametrize("field, value, extra, error_field", INSPECTOR_API_CASES)
def test_inspector_api_rejects_invalid_field(api: AdminApi, city_id, rto_id, field, value, extra, error_field) -> None:
    body = inspector_body(city_id, rto_id, **{field: value}, **extra)
    if value is None:
        body.pop(field)
    assert_field_rejected(api.post(f"{API_PREFIX}/inspectors", json=body), error_field)


@pytest.mark.parametrize("field", ["email", "contact_no"])
def test_inspector_email_and_contact_number_must_be_unique(api: AdminApi, city_id, rto_id, field: str) -> None:
    """Guide s9.1: email and contact number must be unique on the platform."""
    existing = api.list_items(f"{API_PREFIX}/inspectors")[0]

    body = inspector_body(city_id, rto_id, **{field: existing[field]})

    assert_field_rejected(api.post(f"{API_PREFIX}/inspectors", json=body), field)


# ── RTO ───────────────────────────────────────────────────────────────────────

RTO_API_CASES = [
    case("code-letters-only", "code", "ABCDE"),
    case("code-three-digits", "code", "DL-123"),
    case("name-300-chars", "name", "A" * 300),
    case("contact-9-digits", "contact_number", "987654321"),
    case("email-invalid", "contact_email", "not-an-email"),
    case("pincode-7-digits", "pincode", "1100011"),
    case("latitude-out-of-range", "latitude", 91),
    case("city-does-not-exist", "city_id", 999999),
    case("password-no-uppercase", "password", "alllowercase123", password_confirmation="alllowercase123"),
    case("password-mismatch", "password_confirmation", "Different@12345", error_field="password"),
]


@pytest.mark.parametrize("field, value, extra, error_field", RTO_API_CASES)
def test_rto_api_rejects_invalid_field(api: AdminApi, city_id, field, value, extra, error_field) -> None:
    existing = {r["code"] for r in api.all_items(f"{API_PREFIX}/rtos")}
    body = rto_body(city_id, existing, **{field: value}, **extra)
    assert_field_rejected(api.post(f"{API_PREFIX}/rtos", json=body), error_field)


# ── TC Staff ──────────────────────────────────────────────────────────────────

STAFF_API_CASES = [
    case("name-300-chars", "name", "A" * 300),
    case("email-invalid", "email", "not-an-email"),
    case("contact-9-digits", "contact_no", "987654321"),
    case("password-no-uppercase", "password", "alllowercase123", password_confirmation="alllowercase123"),
    case("password-mismatch", "password_confirmation", "Different@12345", error_field="password"),
    case("permission-does-not-exist", "permission_ids", [999999]),
]


@pytest.mark.parametrize("field, value, extra, error_field", STAFF_API_CASES)
def test_staff_api_rejects_invalid_field(api: AdminApi, field, value, extra, error_field) -> None:
    body = staff_body(**{field: value}, **extra)
    assert_field_rejected(api.post(f"{API_PREFIX}/staff", json=body), error_field)


# ── Error responses are well-formed ───────────────────────────────────────────

@pytest.mark.parametrize("endpoint", ["inspectors", "rtos", "staff"])
def test_empty_body_lists_required_fields_without_server_error(api: AdminApi, endpoint: str) -> None:
    response = api.post(f"{API_PREFIX}/{endpoint}", json={})

    assert response.status == 422, f"{endpoint}: {response.status} {response.text()[:200]}"
    body = response.json()
    assert body["success"] is False
    assert len(body["errors"]) >= 3, f"Expected several required-field errors, got {body['errors']}"
    assert not LEAK_PATTERN.search(response.text())
    assert all(isinstance(msgs, list) and msgs for msgs in body["errors"].values())
    assert not re.search(r"\b(null|undefined)\b", response.text().split('"errors"')[1])
