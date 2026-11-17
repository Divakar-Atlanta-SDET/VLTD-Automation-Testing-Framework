"""
Shared pytest fixtures for the VLTD automation suite.

Provides:
- browser / page fixtures via pytest-playwright
- env-var helpers (BASE_URL, credentials)
- a pre-authenticated `logged_in_page` fixture
"""

import os
import re
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page

# Load .env so os.environ picks up BASE_URL / credentials
load_dotenv()


# ── Test-data cleanup (runs once, after every worker has finished) ─────────────

# Tests under these folders create data in the environment.
DATA_CREATING_TESTS = ("tests/oem_management", "tests/permissions", "tests/administration", "tests/test_login.py", "tests/oem_panel")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--keep-test-data",
        action="store_true",
        default=False,
        help="Do not run the end-of-run cleanup of leftover test data (see utils/cleanup.py).",
    )
    parser.addoption(
        "--known-bugs",
        action="store_true",
        default=False,
        help="Also run the tests that document known application defects (marked xfail; see bug_report.md).",
    )


def pytest_report_header(config) -> str | None:
    if not config.getoption("--known-bugs"):
        return "known-defect tests (xfail) are not run by default - add --known-bugs to include them"
    return None


def pytest_collection_modifyitems(config, items) -> None:
    """Keep the default run clean: tests that document a known application defect only run on request.

    They are the tests marked `xfail`; each one links to a BUG-nnn in bug_report.md and flips to an unexpected
    pass when the defect is fixed. `pytest --known-bugs` runs them.
    """
    if config.getoption("--known-bugs"):
        return
    kept, known = [], []
    for item in items:
        (known if item.get_closest_marker("xfail") else kept).append(item)
    if known:
        config.hook.pytest_deselected(items=known)
        items[:] = kept


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """After the run: delete leftover OEM Management records, deactivate test staff, report what remains.

    This must run in the main process only, i.e. after all pytest-xdist workers are done, so it can never
    remove data that a test running in parallel still needs. xdist workers also call this hook when they finish
    (`config.workerinput` exists only there); a worker that finished early used to delete the master data that the
    other workers were still using, so workers return immediately.
    """
    if hasattr(config, "workerinput"):
        return
    if config.getoption("--keep-test-data") or not os.environ.get("BASE_URL"):
        return
    executed = ("passed", "failed", "error", "xfailed", "xpassed")  # not 'deselected' / 'skipped'
    ran = {
        report.nodeid.replace("\\", "/")
        for outcome in executed
        for report in terminalreporter.stats.get(outcome, [])
        if hasattr(report, "nodeid")
    }
    if not any(node.startswith(DATA_CREATING_TESTS) for node in ran):
        return

    from playwright.sync_api import sync_playwright

    from utils.api_client import ApiClient
    from utils.cleanup import TestDataCleaner

    terminalreporter.section("test-data cleanup")
    try:
        with sync_playwright() as p:
            request = p.request.new_context()
            origin = "/".join(os.environ["BASE_URL"].split("/")[:3])
            admin = ApiClient.login(request, origin, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
            report = TestDataCleaner(admin).sweep()
            request.dispose()
        for line in report.lines():
            terminalreporter.write_line(line)
    except Exception as error:  # cleanup must never turn a green run red
        terminalreporter.write_line(f"cleanup skipped: {type(error).__name__}: {error}")


# ── Environment helpers ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("BASE_URL", "")
    assert url, "BASE_URL must be set in .env or environment"
    # Strip the path so we always have the root origin
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


@pytest.fixture(scope="session")
def admin_credentials() -> dict[str, str]:
    return {
        "username": os.environ["ADMIN_USERNAME"],
        "password": os.environ["ADMIN_PASSWORD"],
    }


# ── Playwright / browser setup ─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict:
    """Extra args passed to browser.launch()."""
    return {"headless": True, "slow_mo": 0}


# ── Login page convenience fixture ────────────────────────────────────────────

@pytest.fixture
def login_page_obj(page: Page, base_url: str):
    """Navigate to the login page and return a LoginPage POM instance."""
    from pages.login_page import LoginPage

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    lp = LoginPage(page)
    for attempt in range(3):  # the portal is occasionally slow to answer when several workers load it at once
        try:
            lp.navigate(base_url + "/auth/login")
            break
        except PlaywrightTimeoutError:
            if attempt == 2:
                raise
    return lp


@pytest.fixture
def logged_in_page(login_page_obj, admin_credentials) -> Page:
    """Return a Page that is already authenticated as admin."""
    login_page_obj.login(
        email=admin_credentials["username"],
        password=admin_credentials["password"],
    )
    return login_page_obj.page


# ── Dashboard fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def dashboard_page(login_page_obj, admin_credentials):
    """Log in as admin and return a loaded DashboardPage.

    The initial dashboard and fleet-summary API payloads are exposed as
    `.api` and `.fleet` so tests can reconcile the UI with the backend.
    """
    from pages.dashboard_page import DashboardPage, is_dashboard_api, is_fleet_api

    page = login_page_obj.page
    login_page_obj.fill_email(admin_credentials["username"])
    login_page_obj.fill_password(admin_credentials["password"])
    with page.expect_response(is_dashboard_api, timeout=30_000) as dash_info, \
            page.expect_response(is_fleet_api, timeout=30_000) as fleet_info:
        login_page_obj.click_sign_in()

    dash = DashboardPage(page)
    dash.api = dash_info.value.json()["data"]
    dash.fleet = fleet_info.value.json()["data"]
    dash.expect_loaded()
    return dash


# ── Admin session for user-management tests ───────────────────────────────────

@pytest.fixture
def admin_page(login_page_obj, admin_credentials) -> Page:
    """A Page logged in as admin and sitting on the loaded dashboard."""
    from playwright.sync_api import expect

    login_page_obj.login(
        email=admin_credentials["username"],
        password=admin_credentials["password"],
    )
    page = login_page_obj.page
    expect(page).to_have_url(re.compile(r"/tc/dashboard"), timeout=20_000)
    return page


@pytest.fixture
def network(admin_page: Page):
    """A NetworkMonitor on the logged-in admin page (the 'Network tab'); login traffic is excluded."""
    from utils.network_monitor import NetworkMonitor

    return NetworkMonitor(admin_page)
