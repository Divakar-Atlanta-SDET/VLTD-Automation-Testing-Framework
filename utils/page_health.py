"""
Page-load health check shared by the panel smoke tests.

A page is unhealthy when one of its API calls answers 401 / 403 / 5xx, when a call that CHANGES data (POST / PUT /
PATCH / DELETE) fails while the page merely loads, or when it shows an "unable to load" style message.
404s are ignored: /api/school and /api/last-position answer 404 on the tracking pages for everyone (BUG-020).
"""

import re

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

LOAD_ERROR = re.compile(r"unable to load|not authori[sz]ed|do not have permission|something went wrong", re.I)
API_HOSTS = ("misbackend.com/api/", "misbackend.com/alert/", "misbackend.com/geofence/", "misbackend.com/command/")


def menu_routes(page: Page, prefix: str) -> list[str]:
    """Every menu link below `prefix` (for example '/oem/'), after opening all menu groups."""
    nav = page.get_by_role("navigation", name="Main")
    for group in nav.get_by_role("button").all():
        if group.get_attribute("aria-expanded") == "false":
            group.click()
    routes = page.eval_on_selector_all(f"a[href^='{prefix}']", "els => [...new Set(els.map(e => e.getAttribute('href')))]")
    return sorted(routes)


def load_problems(page: Page, route: str) -> list[str]:
    """Open `route` and return the problems seen while it loaded (empty list = healthy)."""
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
