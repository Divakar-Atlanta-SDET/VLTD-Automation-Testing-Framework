"""
Admin panel smoke: every page in the State Admin menu opens for the admin without a failed call.

Found by walking the whole menu (48 pages). A page is unhealthy when it answers 401 / 403 / 5xx, when a call that
CHANGES data (POST / PUT / PATCH / DELETE) fails while the page merely loads, or when it shows an "unable to load"
style message. 404s are ignored: /api/school and /api/last-position answer 404 on the tracking pages for everyone
(BUG-020).
"""

import re

import pytest
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

pytestmark = [pytest.mark.dashboard]

LOAD_ERROR = re.compile(r"unable to load|not authori[sz]ed|do not have permission|something went wrong", re.I)
API_HOSTS = ("misbackend.com/api/", "misbackend.com/alert/", "misbackend.com/geofence/", "misbackend.com/command/")
KNOWN_BAD_ROUTES = {"/tc/help-centers": "BUG-036"}


def _menu_routes(page: Page) -> list[str]:
    nav = page.get_by_role("navigation", name="Main")
    for group in nav.get_by_role("button").all():
        if group.get_attribute("aria-expanded") == "false":
            group.click()
    routes = page.eval_on_selector_all("a[href^='/tc/']", "els => [...new Set(els.map(e => e.getAttribute('href')))]")
    return sorted(routes)


def _load_and_collect_problems(page: Page, route: str) -> list[str]:
    problems: list[str] = []

    def on_response(response) -> None:
        if not any(host in response.url for host in API_HOSTS):
            return
        method, status = response.request.method, response.status
        if status in (401, 403) or status >= 500 or (method not in ("GET", "HEAD", "OPTIONS") and status >= 400):
            problems.append(f"{method} {response.url.split('misbackend.com')[1][:80]} -> {status}")

    page.on("response", on_response)
    try:
        page.goto(route)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass  # live pages (maps, polling) never go idle; what already arrived is still checked
        expect(page.get_by_role("heading", level=1).first).to_be_visible()
        shown = " ".join(page.locator("main").all_inner_texts())
        if LOAD_ERROR.search(shown):
            problems.append(f"page says: {LOAD_ERROR.search(shown).group(0)!r}")
    finally:
        page.remove_listener("response", on_response)
    return problems


def test_menu_lists_the_documented_areas(admin_page: Page) -> None:
    routes = _menu_routes(admin_page)

    for area in ("users/oem", "users/inspector", "oem-management/firmware", "live-tracking", "geofences", "alerts", "erss",
                 "command-center", "configuration", "operations/vehicle-ownership-transfer", "operations/account-merge",
                 "operations/vehicle-device-untag", "operations/pis-management/timetables", "reports/device-packets",
                 "reports/ownership-transfers", "helpdesk", "announcements", "challans", "watch-history"):
        assert any(route.endswith(area) for route in routes), f"No menu entry for {area}"


def test_every_menu_page_loads_cleanly(admin_page: Page) -> None:
    routes = [r for r in _menu_routes(admin_page) if r not in KNOWN_BAD_ROUTES]
    assert len(routes) >= 40, f"Only {len(routes)} menu pages found"

    broken = {}
    for route in routes:
        problems = _load_and_collect_problems(admin_page, route)
        if problems:
            broken[route] = problems[:3]

    assert not broken, f"Pages that load with failures: {broken}"


@pytest.mark.xfail(reason="BUG-036: the Help Centres page sends a PUT for every row on load and each fails with 422", strict=False)
def test_help_centres_page_loads_without_failed_writes(admin_page: Page) -> None:
    assert not _load_and_collect_problems(admin_page, "/tc/help-centers")
