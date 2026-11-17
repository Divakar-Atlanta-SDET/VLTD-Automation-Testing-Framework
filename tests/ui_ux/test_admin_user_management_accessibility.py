"""Regression checks for confirmed UI/UX and accessibility findings on the Admin
User Management forms (Batch 2 of the UI/UX audit). See ui_ux_bug_report.md for
full repro steps and evidence.
"""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui_ux


def _open_register_form(admin_page: Page, path: str, button_name: str) -> None:
    admin_page.goto(path)
    admin_page.wait_for_load_state("networkidle")
    admin_page.get_by_role("button", name=button_name, exact=True).click()
    admin_page.wait_for_timeout(800)


def _password_toggle_names(admin_page: Page) -> list[str | None]:
    return admin_page.eval_on_selector_all(
        "input[type=password] ~ button, input[type=password] + button",
        "buttons => buttons.map(b => b.getAttribute('aria-label'))",
    )


@pytest.mark.parametrize(
    "path,button_name",
    [
        ("/tc/users/staff", "Register Staff"),
        ("/tc/users/oem", "Register OEM"),
        ("/tc/users/rto", "Register RTO"),
        ("/tc/users/drivers", "Add Driver"),
    ],
)
@pytest.mark.xfail(
    reason="UX-006: the password-visibility toggle button has no accessible name on this form", strict=False
)
def test_password_toggle_buttons_have_an_accessible_name(admin_page: Page, path: str, button_name: str):
    _open_register_form(admin_page, path, button_name)
    names = _password_toggle_names(admin_page)
    assert names, "no password-visibility toggle buttons found next to a password input"
    assert all(names), f"toggle button(s) with no aria-label: {names}"


@pytest.mark.xfail(
    reason="UX-007: the Add Driver form's Back button differs in position/style from the other forms",
    strict=False,
)
def test_add_driver_back_button_appears_above_the_heading(admin_page: Page):
    admin_page.goto("/tc/users/drivers")
    admin_page.wait_for_load_state("networkidle")
    admin_page.get_by_role("button", name="Add Driver", exact=True).click()
    admin_page.wait_for_timeout(800)
    back_button = admin_page.get_by_role("button", name="Back")
    heading = admin_page.get_by_role("heading", name="Add Driver", level=1)
    expect(heading).to_be_visible()
    back_box = back_button.bounding_box()
    heading_box = heading.bounding_box()
    assert back_box and heading_box, "could not measure Back button / heading position"
    assert back_box["y"] < heading_box["y"], "Back button should appear above the heading, as on every other form"
