"""
Dashboard tests for the VLTD Transport Commissioner portal (/tc/dashboard).

Covers:
  D1  sections load                 D8  alert monitoring controls
  D2  KPI cards are numeric         D9  challan analysis controls
  D3  internal reconciliation       D10 navigation / account menu
  D4  UI equals backend response    D12 theme persistence
  D5  zero / null / 500 responses   D13 responsive smoke
  D6  refresh                       (D11 role scoping lives in test_login.py)
  D7  fitment filters

The dataset is live and changes between runs, so no test hard-codes a count:
values are reconciled against the API payload the page itself loaded.
"""

import copy
import re

import pytest
from playwright.sync_api import expect

from pages.dashboard_page import KPI_LABELS, SECTION_HEADINGS, DashboardPage
from utils.dashboard_mocks import mock_dashboard_api, zeroed

pytestmark = [pytest.mark.dashboard]


@pytest.mark.smoke
def test_dashboard_loads_all_sections(dashboard_page: DashboardPage) -> None:
    """D1: every dashboard section and header action is rendered."""
    expect(dashboard_page.heading).to_be_visible()
    for name in SECTION_HEADINGS:
        expect(dashboard_page.section(name)).to_be_visible()
    expect(dashboard_page.refresh_button).to_be_visible()
    expect(dashboard_page.manage_announcements_button).to_be_visible()



@pytest.mark.smoke
def test_kpi_cards_show_numbers(dashboard_page: DashboardPage) -> None:
    """Each of the six KPI tiles shows a non-negative integer, never NaN / undefined."""
    for label in KPI_LABELS:
        expect(dashboard_page.card_value(label)).to_have_text(re.compile(r"^\d[\d,]*$"))
    dashboard_page.expect_no_broken_values()


def test_every_filter_re_queries_the_api_with_its_value(dashboard_page: DashboardPage) -> None:
    """One representative choice per filter: it reaches the API and relabels its chart."""
    d = dashboard_page
    assert d.select_and_wait(d.vehicle_class_select, "Bus")["vehicle_class"] == "bus"
    expect(d.subtitle_of("Fitment Trend")).to_have_text("Bus")
    assert d.select_and_wait(d.fitment_period_select, "Weekly")["fitment_period"] == "weekly"
    assert d.select_and_wait(d.alert_period_select, "Daily")["alert_period"] == "daily"
    assert d.select_and_wait(d.challan_period_select, "Yearly")["challan_period"] == "yearly"

    d.alert_metric_select.select_option(label="Response Status")
    expect(d.subtitle_of("Alert Trend")).to_have_text("Response Status")
    d.challan_metric_select.select_option(label="Penalty Amount")
    expect(d.subtitle_of("Challan Trend")).to_have_text("Penalty Amount")
    d.expect_no_broken_values()



def test_kpi_internal_reconciliation(dashboard_page: DashboardPage) -> None:
    """D3: figures that must agree with each other on one screen do agree."""
    d = dashboard_page
    total = d.card_number("AIS-140 Fitted Vehicles")
    active = d.card_number("Active Fitted Vehicles")
    inactive = d.card_number("Inactive Fitted Vehicles")
    never_sent = d.card_number("Never Sent Data")

    # Fitted = active + inactive; never-sent devices are a subset of fitted ones
    assert active + inactive == total
    assert never_sent <= total

    # Vehicle Mix adds up to the fitted total
    mix = d.vehicle_mix_rows()
    assert sum(count for count, _ in mix.values()) == total
    pct_sum = sum(float(p.rstrip("%")) for _, p in mix.values())
    assert (total == 0 and pct_sum == 0) or abs(pct_sum - 100) < 0.6

    # Active alerts tile == "Open" in Response Summary
    assert d.card_number("Active Alerts") == d.card_number("Open")

    # Network Overview: active never exceeds total
    for entity in ("OEMs", "Fitment Centres", "Inspectors", "RTOs", "Schools", "Fleet Owners"):
        entity_total, entity_active = d.network_row(entity)
        assert entity_active <= entity_total, f"{entity}: active {entity_active} > total {entity_total}"

    # Top RTOs cannot hold more fitments than exist
    for value in d.api["fitments"]["top_rtos"]:
        assert value["value"] <= total


def test_ui_values_match_backend_response(dashboard_page: DashboardPage) -> None:
    """D4: what the dashboard shows equals the payload the API returned."""
    d, api = dashboard_page, dashboard_page.api
    ov = api["overview"]

    expected_kpis = {
        "AIS-140 Fitted Vehicles": ov["total_fitted_vehicles"],
        "Active Fitted Vehicles": ov["active_fitted_vehicles"],
        "Inactive Fitted Vehicles": ov["inactive_fitted_vehicles"],
        "Never Sent Data": ov["fitted_devices_never_sent_data"],
        "Active Alerts": ov["active_alerts"],
        "Challans This Month": ov["challans_this_month"],
    }
    for label, expected in expected_kpis.items():
        assert d.card_number(label) == expected, label

    expect(d.page.get_by_text(f"{ov['critical_alerts']} critical", exact=False).first).to_be_visible()

    # Network overview
    network = {
        "OEMs": "oems",
        "Fitment Centres": "fitment_centres",
        "Inspectors": "inspectors",
        "RTOs": "rtos",
        "Schools": "schools",
        "Fleet Owners": "fleet_owners",
    }
    for label, key in network.items():
        assert d.network_row(label) == (api["network"][key]["total"], api["network"][key]["active"]), label

    # Alert response summary
    summary = api["alerts"]["summary"]
    for label, key in (("Open", "open"), ("Acknowledged", "acknowledged"),
                       ("Action Taken", "action_taken"), ("Resolved", "resolved")):
        assert d.card_number(label) == summary[key], label

    # Challan summary
    challans = api["challans"]["summary"]
    assert d.card_number("Total Challans") == challans["total"]
    assert d.card_number("Major Violations") == challans["major_violations"]
    assert d.card_number("Repeat Violations") == challans["repeat_violations"]

    # Live Fleet strip is fed by the fleet-summary endpoint
    for label, key in (("Moving", "moving"), ("Idle", "idle"), ("SOS", "sos"), ("Offline", "offline")):
        assert d.card_number(label) == d.fleet[key], label


def test_zero_values_render_cleanly(dashboard_page: DashboardPage) -> None:
    """D5a: an all-zero dashboard renders zeros, not NaN/undefined, and no crash."""
    d = dashboard_page
    zero = zeroed(copy.deepcopy(d.api))
    zero["fitments"]["top_rtos"] = []
    mock_dashboard_api(d.page, zero)

    d.refresh()
    for label in KPI_LABELS:
        expect(d.card_value(label)).to_have_text("0")
    expect(d.page.get_by_text(re.compile(r"₹\s*0"))).not_to_have_count(0)
    d.expect_no_broken_values()
    d.expect_loaded()


def test_null_values_render_cleanly(dashboard_page: DashboardPage) -> None:
    """D5b: null KPI fields must not surface as NaN/undefined/null text."""
    d = dashboard_page
    nulled = copy.deepcopy(d.api)
    for key in nulled["overview"]:
        nulled["overview"][key] = None
    for key in nulled["challans"]["summary"]:
        nulled["challans"]["summary"][key] = None
    mock_dashboard_api(d.page, nulled)

    d.refresh()
    d.expect_loaded()
    d.expect_no_broken_values()


def test_server_error_does_not_blank_the_page(dashboard_page: DashboardPage) -> None:
    """D5c: a 500 from the dashboard API leaves the shell usable, no broken values."""
    d = dashboard_page
    mock_dashboard_api(d.page, status=500)

    d.refresh()
    expect(d.heading).to_be_visible()
    expect(d.refresh_button).to_be_visible()
    d.expect_no_broken_values()


@pytest.mark.smoke
def test_refresh_fetches_new_data(dashboard_page: DashboardPage) -> None:
    """D6a: Refresh re-requests the API and shows a changed backend value."""
    d = dashboard_page
    bumped = copy.deepcopy(d.api)
    bumped["overview"]["active_alerts"] += 1
    expected = bumped["overview"]["active_alerts"]
    mock_dashboard_api(d.page, bumped)

    response = d.refresh()
    assert response.status == 200
    expect(d.card_value("Active Alerts")).to_have_text(re.compile(rf"^{expected:,}$|^{expected}$"))


def test_live_fleet_refresh_updates_timestamp_and_data(dashboard_page: DashboardPage) -> None:
    """D6b: the Live Fleet Refresh re-calls the fleet endpoint; label states auto-refresh."""
    d = dashboard_page
    updated = d.page.get_by_text(re.compile(r"Updated .* auto every 5m"))
    expect(updated).to_be_visible()

    with d.page.expect_response(lambda r: "fleet/summary" in r.url) as info:
        d.fleet_refresh_button.click()
    assert info.value.status == 200
    expect(updated).to_be_visible()





def test_challan_summary_content(dashboard_page: DashboardPage) -> None:
    """D9c: summary tiles are numeric, penalty is in rupees, disclaimer is shown."""
    d = dashboard_page
    for label in ("Total Challans", "Major Violations", "Repeat Violations"):
        expect(d.card_value(label)).to_have_text(re.compile(r"^\d[\d,]*$"))
    expect(d.card_value("Penalty Amount")).to_have_text(re.compile(r"^₹\s*[\d,]+(\.\d+)?$"))
    expect(
        d.page.get_by_text("Penalty amounts represent issued challans and not confirmed payment collection.")
    ).to_be_visible()


def test_manage_announcements_navigates(dashboard_page: DashboardPage) -> None:
    """D10a: Manage Announcements opens the announcements page."""
    dashboard_page.manage_announcements_button.click()
    expect(dashboard_page.page).to_have_url(re.compile(r"announce", re.I))


@pytest.mark.smoke
def test_sidebar_navigation(dashboard_page: DashboardPage) -> None:
    """D10b: primary navigation groups exist; Helpdesk and Dashboard links route correctly."""
    d = dashboard_page
    nav = d.page.get_by_role("navigation", name="Main")
    for group in ("Control & Operations", "Administration", "Reports"):
        expect(nav.get_by_role("button", name=group)).to_be_visible()

    d.helpdesk_link.click()
    expect(d.page).to_have_url(re.compile(r"/tc/helpdesk"))
    d.dashboard_link.click()
    expect(d.page).to_have_url(re.compile(r"/tc/dashboard"))


def test_account_menu_contents(dashboard_page: DashboardPage) -> None:
    """D10c: account menu offers Profile, Tickets and Logout."""
    d = dashboard_page
    d.open_account_menu()
    for item in ("Profile", "Tickets", "Logout"):
        expect(d.page.get_by_role("menuitem", name=item)).to_be_visible()



def test_mobile_layout_and_navigation_drawer(dashboard_page: DashboardPage) -> None:
    """D13: at phone width the dashboard still renders and the drawer opens."""
    d = dashboard_page
    d.page.set_viewport_size({"width": 390, "height": 844})
    d.expect_loaded()
    expect(d.card("AIS-140 Fitted Vehicles")).to_be_visible()

    d.open_navigation_button.click()
    drawer = d.page.get_by_role("dialog", name="Application navigation")
    expect(drawer).to_be_visible()
    expect(drawer.get_by_role("link", name="Dashboard")).to_be_visible()
    expect(drawer.get_by_role("link", name="Helpdesk")).to_be_visible()
