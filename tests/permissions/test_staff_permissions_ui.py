"""
Staff permissions – what a staff user SEES and can OPEN in the portal.  Plan: specs/staff-permissions-test-plan.md

The portal declares, per menu entry, the permission it needs (utils/permissions_matrix.NAV_PERMISSION). For each:

  with the permission     the menu entry exists, the page opens (no redirect) and loads WITHOUT a failed
                          API call or an "Unable to load" message   -> the permission really opens the door
  without the permission  the menu entry is absent and typing the URL sends the user back to the dashboard

Menu entries that declare no permission must work for any staff user (test_open_pages_*).
Pages that show a menu entry but then fail to load are listed in UI_BROKEN / OPEN_BROKEN with the bug id;
one representative per defect runs as a known-bug (xfail) test - see `pytest --known-bugs`.
"""

import re

import pytest
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.login_page import LoginPage
from utils.network_monitor import NetworkMonitor
from utils.permissions_matrix import NAV_OPEN, NAV_PERMISSION
from utils.staff_lab import StaffLab

pytestmark = [pytest.mark.permissions]

LOAD_ERROR = re.compile(r"unable to load|not authorized|not authorised|do not have permission|something went wrong", re.I)

# Menu entry shown WITH its permission, but the page then fails to load. Two causes:
#   BUG-015  the permission is ineffective – the API refuses staff even with it (RTO, Staff, Permit Holders,
#            installation / repair reports, and Inspectors, whose page also needs the RTO list)
#   BUG-016  the page also calls endpoints guarded by OTHER permissions the staff was not told they need
UI_BROKEN = {
    "/tc/users/rto": "BUG-015",
    "/tc/users/staff": "BUG-015",
    "/tc/users/permit-holders": "BUG-015",
    "/tc/users/inspector": "BUG-015",
    "/tc/reports/installation-status": "BUG-015",
    "/tc/reports/maintenance": "BUG-015",
    "/tc/reports/oem-performance": "BUG-015",
    "/tc/reports/alerts": "BUG-016",
    "/tc/reports/device-health": "BUG-016",
    "/tc/reports/device-packets": "BUG-016",
    "/tc/reports/device-status": "BUG-016",
    "/tc/reports/vehicle-activity": "BUG-016",
    "/tc/command-center": "BUG-016",
    "/tc/oem-management/device-models": "BUG-016",
    "/tc/oem-management/firmware": "BUG-016",
    "/tc/oem-management/sim-modules": "BUG-016",
    "/tc/set-history": "BUG-016",
    "/tc/trip-playback": "BUG-016",
    "/tc/alerts": "BUG-016",
    "/tc/erss": "BUG-016",
    "/tc/geofences": "BUG-016",
    "/tc/live-tracking": "BUG-016",
}

# Hidden from the staff menu, yet the router lets staff open it by typing the URL.
HIDDEN_BUT_REACHABLE = {
    "/tc/operations/pis-management/trips": "BUG-017",
}

# Menu entry shown to a staff user with NO permission, but the page fails to load for them.
OPEN_BROKEN = {
    "/tc/configuration": "BUG-017",
}


@pytest.fixture
def staff_ui(page: Page, staff_lab: StaffLab):
    """Log the lab's prober in through the real login page; returns (page, network monitor)."""

    def _login(*permissions: str):
        staff_lab.grant(list(permissions))
        login = LoginPage(page)
        login.navigate(staff_lab.admin.origin + "/auth/login")
        login.login(staff_lab.prober.email, staff_lab.prober.password)
        expect(page).to_have_url(re.compile(r"/tc/dashboard"), timeout=40_000)
        return page, NetworkMonitor(page)

    return _login


def _open(page: Page, net: NetworkMonitor, route: str) -> None:
    net.clear()
    page.goto(route)
    try:  # the page's own data calls run after load; wait for them to settle
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        pass  # pages with live polling never go idle – the settle delay below still applies
    page.wait_for_timeout(1_500)


def _link(page: Page, route: str):
    return page.locator(f"a[href='{route}']")


def _problems(page: Page, net: NetworkMonitor) -> list[str]:
    # 401 / 403 / 5xx are failures. 404s are ignored: /api/school and /api/last-position answer 404 for the admin too.
    failed = [str(c) for c in net.calls if c.status in (401, 403) or c.status >= 500]
    shown = " ".join(page.locator("main").all_inner_texts())
    if LOAD_ERROR.search(shown):
        failed.append(f"page says: {LOAD_ERROR.search(shown).group(0)!r}")
    return failed


def _first_route_per_permission(routes: dict[str, str]) -> list[tuple[str, str]]:
    """One working route for every permission, so each permission is proven once without repeating its pages."""
    seen: dict[str, str] = {}
    for route, code in sorted(routes.items()):
        seen.setdefault(code, route)
    return sorted((route, code) for code, route in seen.items())


WORKING = {r: c for r, c in NAV_PERMISSION.items() if r not in UI_BROKEN}
KNOWN_BUG_ROUTES = [
    pytest.param(route, NAV_PERMISSION[route], marks=pytest.mark.xfail(reason=bug, strict=True), id=bug)
    for bug, route in (("BUG-015", "/tc/users/rto"), ("BUG-016", "/tc/alerts"))
]


@pytest.mark.parametrize("route, code", _first_route_per_permission(WORKING))
def test_menu_entry_opens_page_with_permission(staff_ui, route: str, code: str) -> None:
    """Positive: with just `code`, the menu entry is there and its page opens and loads cleanly."""
    page, net = staff_ui(code)

    assert _link(page, route).count() >= 1, f"Menu entry {route} is missing although the staff holds {code}"
    _open(page, net, route)
    expect(page).to_have_url(re.compile(re.escape(route) + r"$"))  # the route guard let the user in

    problems = _problems(page, net)
    assert not problems, f"{route} fails to load for a staff user holding {code}: {problems}"


@pytest.mark.parametrize("route, code", KNOWN_BUG_ROUTES)
def test_known_bug_menu_entry_page_fails_to_load(staff_ui, route: str, code: str) -> None:
    """Known defect: the permission shows the menu entry but the page then fails to load (BUG-015 / BUG-016)."""
    page, net = staff_ui(code)

    _open(page, net, route)
    problems = _problems(page, net)
    assert not problems, f"{route} fails to load for a staff user holding {code}: {problems}"


def test_without_permissions_every_gated_menu_entry_is_hidden_and_blocked(staff_ui) -> None:
    """Negative: a staff user with no permission sees none of the gated menu entries and is redirected from each URL."""
    page, _ = staff_ui()  # no permissions

    shown = [route for route in NAV_PERMISSION if _link(page, route).count()]
    assert not shown, f"Menu entries shown without any permission: {shown}"

    not_blocked = []
    for route in NAV_PERMISSION:
        page.goto(route)
        try:
            expect(page).to_have_url(re.compile(r"/tc/dashboard"), timeout=10_000)
        except AssertionError:
            not_blocked.append(route)
    assert not not_blocked, f"URLs that opened without a permission: {not_blocked}"


@pytest.mark.parametrize("route", [r for r in NAV_OPEN if r not in OPEN_BROKEN and r not in HIDDEN_BUT_REACHABLE])
def test_open_menu_entries_work_for_staff(staff_ui, route: str) -> None:
    """Menu entries without a permission: whatever the menu shows must load; whatever it hides must be blocked."""
    page, net = staff_ui()  # no permissions
    shown = _link(page, route).count() > 0

    _open(page, net, route)
    if not shown:
        expect(page).to_have_url(re.compile(r"/tc/dashboard"), timeout=15_000)  # the router agrees with the menu
        return
    expect(page).to_have_url(re.compile(re.escape(route) + r"$"))
    problems = _problems(page, net)
    assert not problems, f"{route} is offered to staff but fails to load: {problems}"


@pytest.mark.xfail(reason="BUG-017: the menu offers /tc/configuration to every staff user but the page fails", strict=True)
def test_known_bug_open_menu_entry_fails_for_staff(staff_ui) -> None:
    page, net = staff_ui()
    _open(page, net, "/tc/configuration")
    problems = _problems(page, net)
    assert not problems, f"/tc/configuration is offered to staff but fails to load: {problems}"


@pytest.mark.xfail(reason="BUG-017: /tc/operations/pis-management/trips is hidden from staff but opens by URL", strict=True)
def test_known_bug_hidden_route_is_reachable_by_url(staff_ui) -> None:
    page, net = staff_ui()
    _open(page, net, "/tc/operations/pis-management/trips")
    expect(page).to_have_url(re.compile(r"/tc/dashboard"), timeout=15_000)
