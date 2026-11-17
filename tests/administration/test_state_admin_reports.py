"""
State Admin reports (guide section 12) - read-only checks of the rules the guide states.

  SIM Validity   under 7 days is critical, under 30 days is at risk
  Device Packets up to 31 days per search and up to 200 rows per page

Data in the environment changes, so values are reconciled against each other (row vs. its own dates, rows vs. the
summary) instead of being hard-coded.
"""

from datetime import date, timedelta

import pytest

from utils.api_client import API_PREFIX, ApiClient

pytestmark = [pytest.mark.api]

PACKETS = "/api/tracking/devices/packets"


@pytest.fixture(scope="module")
def admin_api(playwright, base_url: str, admin_credentials: dict):
    request = playwright.request.new_context()
    yield ApiClient.login(request, base_url, admin_credentials["username"], admin_credentials["password"])
    request.dispose()


@pytest.fixture(scope="module")
def sim_validity(admin_api: ApiClient) -> dict:
    response = admin_api.get(f"{API_PREFIX}/reports/device-validity?per_page=100")
    assert response.status == 200, response.text()[:200]
    return response.json()


def _expected_category(days_remaining: int) -> str:
    return "critical" if days_remaining < 7 else "at_risk" if days_remaining < 30 else "valid"


def test_sim_validity_uses_the_documented_thresholds(sim_validity: dict) -> None:
    assert sim_validity["thresholds"] == {"critical_less_than_days": 7, "at_risk_less_than_days": 30}


def test_sim_validity_rows_are_classified_by_days_left(sim_validity: dict) -> None:
    """Each row: days_remaining follows from the SIM's valid_till, and the category follows from days_remaining."""
    as_of = date.fromisoformat(sim_validity["as_of_date"])
    wrong = []
    for row in sim_validity["data"]:
        validity = row["validity"]
        days = (date.fromisoformat(row["sim"]["valid_till"]) - as_of).days
        if validity["is_expired"]:
            if days >= 0:
                wrong.append((row["installation_id"], "marked expired but valid_till is", row["sim"]["valid_till"]))
            continue
        if validity["days_remaining"] != days or validity["category"] != _expected_category(days):
            wrong.append((row["installation_id"], days, validity["days_remaining"], validity["category"]))
    assert not wrong, f"Rows that break the rule: {wrong}"


def test_sim_validity_summary_matches_the_rows(sim_validity: dict) -> None:
    rows, summary = sim_validity["data"], sim_validity["summary"]
    assert sim_validity["meta"]["total"] == len(rows) == summary["total"], "Increase per_page: the fixture reads one page"
    for category in ("critical", "at_risk", "valid"):
        assert summary[category] == sum(r["validity"]["category"] == category for r in rows), category
    assert summary["attention_required"] == summary["critical"] + summary["at_risk"]


@pytest.mark.parametrize(
    "days, accepted",
    [(7, True), (31, True), (32, False)],
    ids=["one-week", "31-days-limit", "32-days-refused"],
)
def test_device_packets_search_is_limited_to_31_days(admin_api: ApiClient, days: int, accepted: bool) -> None:
    today = date.today()
    response = admin_api.get(f"{PACKETS}?from={today - timedelta(days=days)}&to={today}")

    if accepted:
        assert response.status == 200, response.text()[:200]
    else:
        assert response.status == 422 and "to" in response.json()["errors"], response.text()[:200]


@pytest.mark.parametrize("per_page, accepted", [(200, True), (201, False)], ids=["200-rows", "201-refused"])
def test_device_packets_page_size_is_capped_at_200(admin_api: ApiClient, per_page: int, accepted: bool) -> None:
    response = admin_api.get(f"{PACKETS}?per_page={per_page}")

    if accepted:
        assert response.status == 200, response.text()[:200]
        assert len(response.json()["data"]) <= 200
    else:
        assert response.status == 422 and "per_page" in response.json()["errors"], response.text()[:200]
