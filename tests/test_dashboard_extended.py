"""
Dashboard resilience tests: how the page behaves when the back end misbehaves.

Mocked Live Fleet values and failure, a failing filter request, empty states, 401 / aborted / oversized
responses, Recent Major Alerts content, and a check that no tokens or credentials leak into URLs or the console.
"""

import copy
import re
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, expect

from pages.dashboard_page import DashboardPage
from utils.dashboard_mocks import (
    DASHBOARD_ROUTE,
    mock_dashboard_api,
    mock_fleet_api,
    zeroed,
)

pytestmark = [pytest.mark.dashboard]

FILTER_PARAMS = {"vehicle_class", "fitment_period", "alert_period", "challan_period"}
ALERT_ROW = re.compile(r"(High|Critical).*·\s*(Open|Acknowledged|Action Taken|Resolved)")


def _wait_until(page: Page, condition, timeout_ms: int = 10_000) -> None:
    """Poll `condition()` (a zero-arg callable) until true, or fail after `timeout_ms`."""
    waited = 0
    while not condition():
        if waited >= timeout_ms:
            raise AssertionError("condition not met within %d ms" % timeout_ms)
        page.wait_for_timeout(100)
        waited += 100


def _no_horizontal_scroll(page: Page) -> bool:
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )


@pytest.fixture
def sign_in(login_page_obj, admin_credentials):
    """Return a callable that submits the admin login without waiting for data.

    Lets a test install routes / fake timers *before* the dashboard first loads.
    """

    def _sign_in() -> DashboardPage:
        login_page_obj.fill_email(admin_credentials["username"])
        login_page_obj.fill_password(admin_credentials["password"])
        login_page_obj.click_sign_in()
        dash = DashboardPage(login_page_obj.page)
        expect(dash.heading).to_be_visible(timeout=20_000)
        return dash

    return _sign_in



@pytest.mark.parametrize(
    "case, payload, status",
    [
        ("zeros", {"moving": 0, "idle": 0, "sos": 0, "offline": 0, "total": 0}, 200),
        ("large", {"moving": 1234567, "idle": 2, "sos": 3, "offline": 4, "total": 1234576}, 200),
        ("server-error", None, 500),
    ],
)
def test_live_fleet_mocked_responses(page: Page, sign_in, case: str, payload, status: int) -> None:
    """D8: Live Fleet copes with zeros, very large values and a failing endpoint."""
    mock_fleet_api(page, payload, status)
    d = sign_in()

    # The rest of the dashboard is unaffected either way
    d.expect_loaded()
    expect(d.section("Live Fleet")).to_be_visible()
    d.expect_no_broken_values()

    if status == 200:
        for label, key in (("Moving", "moving"), ("Idle", "idle"), ("SOS", "sos"), ("Offline", "offline")):
            assert d.card_number(label) == payload[key], f"{case}: {label}"
        assert _no_horizontal_scroll(page)
    else:
        expect(d.card("AIS-140 Fitted Vehicles")).to_be_visible()



def test_failed_filter_request_recovers(dashboard_page: DashboardPage) -> None:
    """D15: a 500 on one filter choice does not blank the page and can be undone."""
    d = dashboard_page
    d.page.route(
        re.compile(r".*transport-commissioner/dashboard.*fitment_period=yearly.*"),
        lambda route: route.fulfill(status=500, content_type="application/json", body='{"message":"boom"}'),
    )

    d.fitment_period_select.select_option(label="Yearly")
    expect(d.heading).to_be_visible()
    d.expect_no_broken_values()

    params = d.select_and_wait(d.fitment_period_select, "Monthly")
    assert params["fitment_period"] == "monthly"
    d.expect_loaded()


def test_recent_major_alerts_match_api_order(dashboard_page: DashboardPage) -> None:
    """D16: rows are a prefix of the API's priority alerts, in the same order."""
    d = dashboard_page
    api_alerts = d.api["alerts"]["priority"]
    if not api_alerts:
        pytest.skip("No priority alerts in this environment")

    rows = d.page.locator("article").filter(has_text=ALERT_ROW)
    count = rows.count()
    assert 0 < count <= len(api_alerts)
    for i in range(count):
        row = rows.nth(i)
        alert = api_alerts[i]
        expect(row).to_contain_text(alert["title"])
        expect(row).to_contain_text(alert["vehicle_number"])
        expect(row).to_contain_text(alert["severity_label"])
        expect(row).to_contain_text(alert["response_status_label"])
    expect(d.page.get_by_text("Latest unresolved high-priority events")).to_be_visible()



def test_empty_state_messages(dashboard_page: DashboardPage) -> None:
    """D19: with no fitments the dashboard explains the emptiness instead of showing blanks."""
    d = dashboard_page
    empty = zeroed(copy.deepcopy(d.api))
    empty["fitments"]["top_rtos"] = []
    empty["fitments"]["vehicle_mix"] = []
    empty["alerts"]["priority"] = []
    mock_dashboard_api(d.page, empty)

    d.refresh()
    expect(d.page.get_by_text("No RTO fitment data")).to_be_visible()
    expect(d.page.get_by_text("RTO rankings will appear once fitted vehicles are available.")).to_be_visible()
    expect(d.page.get_by_text("No vehicle mix data available.")).to_be_visible()
    expect(d.page.get_by_text("0 fitted", exact=True)).to_be_visible()
    d.expect_no_broken_values()


def test_unauthorised_dashboard_response_does_not_show_data(dashboard_page: DashboardPage) -> None:
    """D22a: a 401 from the dashboard API ends the session or shows a clear message."""
    d = dashboard_page
    mock_dashboard_api(d.page, status=401)

    d.refresh_button.click()

    expired_message = d.page.get_by_text(re.compile(r"session|expired|unauthori[sz]ed|sign in again", re.I))
    expect(d.page.locator("body")).to_be_visible()
    d.page.wait_for_timeout(2000)
    assert re.search(r"/auth/login", d.page.url) or expired_message.count() > 0, (
        f"401 neither redirected to login nor showed a message (url={d.page.url})"
    )


def test_aborted_dashboard_request_leaves_page_usable(dashboard_page: DashboardPage) -> None:
    """D22b: a network failure on Refresh keeps the shell usable and Refresh re-enabled."""
    d = dashboard_page
    d.page.route(DASHBOARD_ROUTE, lambda route: route.abort("failed"))

    d.refresh_button.click()
    expect(d.heading).to_be_visible()
    expect(d.refresh_button).to_be_enabled()
    d.expect_no_broken_values()


def test_very_large_values_do_not_break_layout(dashboard_page: DashboardPage) -> None:
    """D23: huge numbers and long names stay inside their tiles and the page width."""
    d = dashboard_page
    big = copy.deepcopy(d.api)
    big["overview"]["total_fitted_vehicles"] = 12_345_678
    big["overview"]["active_fitted_vehicles"] = 12_345_678
    big["overview"]["inactive_fitted_vehicles"] = 0
    big["challans"]["summary"]["revenue"] = 9_876_543_210
    if big["fitments"]["top_rtos"]:
        big["fitments"]["top_rtos"][0]["name"] = "Very Long Regional Transport Office Name " * 3
    mock_dashboard_api(d.page, big)

    d.refresh()
    assert d.card_number("AIS-140 Fitted Vehicles") == 12_345_678
    # Currency is shown compactly in crore: 9,876,543,210 -> "₹ 987.7 Cr"
    expect(d.card_value("Penalty Amount")).to_have_text(re.compile(r"^₹\s*987\.7\s*Cr$"))
    assert _no_horizontal_scroll(d.page)
    d.expect_no_broken_values()



@pytest.mark.xfail(
    reason="Suspected defect: KPI tiles show a real-looking '0' while data is still loading",
    strict=False,
)
def test_no_misleading_zero_while_loading(page: Page, sign_in) -> None:
    """D24b: a pending request must not display '0' as if it were data."""
    held = []
    page.route(DASHBOARD_ROUTE, lambda route: held.append(route))
    d = sign_in()
    page.wait_for_timeout(500)

    try:
        tile_value = page.locator("article").filter(has_text="AIS-140 Fitted Vehicles").first.locator("p").nth(1)
        expect(tile_value).not_to_have_text("0")
    finally:
        if held:
            held[0].continue_()







def test_no_tokens_or_credentials_in_urls_or_console(
    page: Page, sign_in, admin_credentials: dict
) -> None:
    """D42: tokens/passwords never appear in URLs or console; queries carry only filters."""
    urls: list[str] = []
    console: list[str] = []
    page.on("request", lambda r: urls.append(r.url))
    page.on("console", lambda m: console.append(m.text))

    d = sign_in()
    d.expect_loaded()
    d.select_and_wait(d.vehicle_class_select, "Bus")

    token = page.evaluate("() => localStorage.getItem('access_token')")
    secrets = [admin_credentials["password"], token[:40], page.evaluate("() => localStorage.getItem('refresh_token')")]

    for text in urls + console + [page.url]:
        for secret in secrets:
            assert secret not in text, f"secret leaked in: {text[:120]}"

    for url in urls:
        if "transport-commissioner/dashboard" in url:
            assert set(parse_qs(urlparse(url).query)) <= FILTER_PARAMS, url
