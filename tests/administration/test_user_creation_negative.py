"""
Negative / input-validation tests for the User Management create forms.

Every case submits ONE kind of invalid input and checks, with the network monitor attached:
  1. the form stays open (nothing was created),
  2. the user sees at least one validation message (matching `expect` when given),
  3. no create request succeeded (it was blocked in the browser, or answered with 4xx),
  4. the server never answered with 5xx and never leaked a stack trace / SQL / file path,
  5. no raw "NaN / undefined / null" text is shown in the messages.

Forms: OEM, RTO, Inspector, Driver, TC Staff.   Plan: specs/user-management-negative-test-plan.md
"""

import re
from dataclasses import replace

import pytest
from playwright.sync_api import Page

from pages.administration.base_user_page import UserListPage
from pages.administration.driver_page import DriverPage
from pages.administration.inspector_page import InspectorPage
from pages.administration.oem_page import OemPage
from pages.administration.rto_page import RtoPage
from pages.administration.staff_page import StaffPage
from utils import data_generator as data
from utils.file_utils import (
    MB,
    TEST_PDF,
    create_oversized_pdf,
    create_oversized_png,
    create_test_png,
    create_text_file,
)
from utils.network_monitor import NetworkMonitor

pytestmark = [pytest.mark.user_management, pytest.mark.negative]

BROKEN_TEXT = re.compile(r"\b(NaN|undefined|null|\[object Object\])\b")
EMAIL_IN_TEXT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Upload tokens used in the case tables -> real files (created in tmp_path when needed)
FILE_BUILDERS = {
    "pdf": lambda tmp: TEST_PDF,
    "png": lambda tmp: create_test_png(tmp),
    "txt": lambda tmp: create_text_file(tmp),
    "pdf_over_2mb": lambda tmp: create_oversized_pdf(tmp, 2 * MB + 1),
    "pdf_over_5mb": lambda tmp: create_oversized_pdf(tmp, 5 * MB + 1),
    "png_over_5mb": lambda tmp: create_oversized_png(tmp, 5 * MB + 1),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _files(value, tmp_path):
    """Replace upload tokens (str) in a form kwarg by real files; leave everything else as is."""
    if isinstance(value, str) and value in FILE_BUILDERS:
        return FILE_BUILDERS[value](tmp_path)
    if isinstance(value, tuple):
        return tuple(_files(v, tmp_path) for v in value)
    return value


def _build_kwargs(form_kwargs: dict, tmp_path) -> dict:
    return {key: _files(value, tmp_path) for key, value in form_kwargs.items()}


def _submit(form: UserListPage, network: NetworkMonitor) -> list[str]:
    """Click submit; wait for either the browser's validation messages or the server's answer."""
    form.submit_button.click()
    for _ in range(60):  # up to ~6 s for a server round-trip
        if network.writes() or form.messages():
            break
        form.page.wait_for_timeout(100)
    form.page.wait_for_timeout(500)  # let late toasts / inline errors render
    return form.messages()


def _attempt(form: UserListPage, network: NetworkMonitor, fill, *, blank: bool = False) -> list[str]:
    """Open the create form, fill it (unless `blank`), submit, and return all messages shown.

    Messages are collected after filling as well, because some rejections (an oversized or
    wrong-type file) are reported the moment the file is chosen, not on submit.
    """
    form.open()
    form.open_create_form()
    network.clear()
    messages: list[str] = []
    if not blank:
        fill()
        messages += form.messages()
    messages += _submit(form, network)
    return list(dict.fromkeys(messages))


def _assert_rejected(form: UserListPage, network: NetworkMonitor, messages: list[str], expect: str | None) -> None:
    assert form.form_heading.is_visible(), (
        f"The create form closed, so the invalid data may have been saved. Network: {network.summary()}"
    )
    assert not network.successful_writes(), (
        f"Server ACCEPTED invalid data: {[str(c) for c in network.successful_writes()]}"
    )
    assert not network.server_errors(), (
        f"Server error (5xx) for invalid input: {[str(c) for c in network.server_errors()]}"
    )
    assert not network.leaks(), (
        f"Response leaks internals: {[(str(c), (c.response_body or '')[:200]) for c in network.leaks()]}"
    )
    assert messages, f"No validation message was shown. Network: {network.summary()}"
    assert not BROKEN_TEXT.search(" ".join(messages)), f"Broken text in messages: {messages}"
    if expect:
        assert any(re.search(expect, m, re.I) for m in messages), (
            f"Expected a message matching /{expect}/ but got {messages}. Network: {network.summary()}"
        )


# ── Case tables: (id, data overrides, form kwargs, expected message regex) ───

def _case(case_id, overrides=None, kwargs=None, expect=None):
    return pytest.param(overrides or {}, kwargs or {}, expect, id=case_id)


# One representative per rule type. The exact rules (every length, format and password-complexity variant) are
# verified once, quickly and stably, by the server-side tests in test_user_creation_api_validation.py.
_PASSWORD_MESSAGE = "password|characters|uppercase|lowercase|number"
PASSWORD_MISMATCH = _case("password-mismatch", {}, {"confirm": "Different@12345"}, expect="match|confirm")

OEM_CASES = [
    _case("business-name-blank", {"business_name": ""}, expect="Business Name is required"),
    _case("cin-too-short", {"cin": "U72200KA2014PTC12345"}, expect="CIN"),
    _case("gst-too-short", {"gst": "07AUTOA123"}, expect="GST"),
    _case("pincode-5-digits", {"pincode": "11000"}, expect="pin|digit"),
    _case("mobile-9-digits", {"mobile": "987654321"}, expect="10|mobile"),
    _case("email-without-at", {"email": "not-an-email"}, expect="email"),
    _case("password-too-short", {"password": "Ab1"}, expect=_PASSWORD_MESSAGE),
    PASSWORD_MISMATCH,
    _case("no-certificates", kwargs={"certificates": (None, None, None)}, expect="Certificate is required"),
    _case("gst-certificate-not-a-pdf", kwargs={"certificates": ("txt", "pdf", "pdf")}, expect="must be a PDF"),
    _case("gst-certificate-over-2mb", kwargs={"certificates": ("pdf_over_2mb", "pdf", "pdf")}, expect="2 ?MB|exceed|size"),
    _case("no-dates", kwargs={"dates": (None, None, None)}, expect="date is required"),
]

RTO_CASES = [
    _case("rto-code-letters-only", {"code": "ABCDE"}, expect="XX-99|format|DL-"),
    _case("mobile-9-digits", {"mobile": "987654321"}, expect="contact|10|mobile|number"),
    _case("email-without-at", {"email": "not-an-email"}, expect="email"),
    _case("district-not-selected", {"district": ""}, expect="District is required"),
    _case("pincode-5-digits", {"pincode": "11000"}, expect="pin|digit"),
    _case("location-not-pinned", kwargs={"pin": False}, expect="location is required"),
    PASSWORD_MISMATCH,
]

INSPECTOR_CASES = [
    _case("email-without-at", {"email": "not-an-email"}, expect="@|email"),
    _case("mobile-9-digits", {"mobile": "987654321"}, expect="10 digits"),
    _case("city-not-selected", {"city": ""}, expect="city"),
    _case("rto-not-selected", kwargs={"choose_rto": False}, expect="RTO is required"),
    PASSWORD_MISMATCH,
]

DRIVER_CASES = [
    _case("email-without-at", {"email": "not-an-email"}, expect="email"),
    _case("mobile-9-digits", {"mobile": "987654321"}, expect="contact|10|mobile|number"),
    _case("licence-wrong-format", {"licence_number": "INVALID123"}, expect="licen[cs]e"),
    PASSWORD_MISMATCH,
    _case("licence-file-missing", kwargs={"licence_file": None}, expect="licence file is required"),
    _case("photo-missing", kwargs={"photo": None}, expect="photo is required"),
    _case("photo-is-a-text-file", kwargs={"photo": "txt"}, expect="photo|image|jpg|type"),
    _case("photo-over-5mb", kwargs={"photo": "png_over_5mb"}, expect="5 ?MiB|exceed|size"),
]

STAFF_CASES = [
    _case("email-without-at", {"email": "not-an-email"}, expect="@|email"),
    _case("mobile-9-digits", {"mobile": "987654321"}, expect="contact|10|mobile|number"),
    PASSWORD_MISMATCH,
]


# ── OEM ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overrides, form_kwargs, expect", OEM_CASES)
def test_oem_rejects_invalid_input(admin_page: Page, network, tmp_path, overrides, form_kwargs, expect) -> None:
    oem = replace(data.oem_data(), **overrides)
    form = OemPage(admin_page)
    kwargs = _build_kwargs(form_kwargs, tmp_path)
    messages = _attempt(form, network, lambda: form.fill_form(oem, **kwargs))
    _assert_rejected(form, network, messages, expect)


def test_oem_empty_form_lists_every_required_field(admin_page: Page, network) -> None:
    form = OemPage(admin_page)
    messages = _attempt(form, network, None, blank=True)
    _assert_rejected(form, network, messages, "required")
    assert not network.writes(), "An empty form must be blocked before any request is sent"
    for field in ("Business Name", "OEM Code", "CIN Number", "GST Number", "TAC Number", "COP Number",
                  "Office Address", "Pincode", "Contact Person Name", "Contact Mobile", "Contact Email", "Password"):
        assert any(field in m for m in messages), f"No required-field message for '{field}': {messages}"


# ── RTO ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overrides, form_kwargs, expect", RTO_CASES)
def test_rto_rejects_invalid_input(admin_page: Page, network, tmp_path, overrides, form_kwargs, expect) -> None:
    form = RtoPage(admin_page)
    form.open()
    rto = replace(data.rto_data(form.existing_codes()), **overrides)
    kwargs = _build_kwargs(form_kwargs, tmp_path)
    messages = _attempt(form, network, lambda: form.fill_form(rto, **kwargs))
    _assert_rejected(form, network, messages, expect)


def test_rto_empty_form_lists_every_required_field(admin_page: Page, network) -> None:
    form = RtoPage(admin_page)
    messages = _attempt(form, network, None, blank=True)
    _assert_rejected(form, network, messages, "required")
    for field in ("RTO Name", "RTO Code", "Contact Number", "Contact Email", "Address", "District", "Pincode", "Password"):
        assert any(field in m for m in messages), f"No required-field message for '{field}': {messages}"


# ── Inspector ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overrides, form_kwargs, expect", INSPECTOR_CASES)
def test_inspector_rejects_invalid_input(admin_page: Page, network, tmp_path, overrides, form_kwargs, expect) -> None:
    inspector = replace(data.inspector_data(), **overrides)
    form = InspectorPage(admin_page)
    kwargs = _build_kwargs(form_kwargs, tmp_path)
    messages = _attempt(form, network, lambda: form.fill_form(inspector, **kwargs))
    _assert_rejected(form, network, messages, expect)


def test_inspector_empty_form_lists_every_required_field(admin_page: Page, network) -> None:
    form = InspectorPage(admin_page)
    messages = _attempt(form, network, None, blank=True)
    _assert_rejected(form, network, messages, "required|digits")
    assert len(messages) >= 5, f"Expected a message per required field, got {messages}"


# ── Driver ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overrides, form_kwargs, expect", DRIVER_CASES)
def test_driver_rejects_invalid_input(admin_page: Page, network, tmp_path, overrides, form_kwargs, expect) -> None:
    driver = replace(data.driver_data(), **overrides)
    form = DriverPage(admin_page)
    kwargs = _build_kwargs({"photo": "png", **form_kwargs}, tmp_path)
    photo = kwargs.pop("photo")
    messages = _attempt(form, network, lambda: form.fill_form(driver, photo, **kwargs))
    _assert_rejected(form, network, messages, expect)


def test_driver_empty_form_lists_every_required_field(admin_page: Page, network) -> None:
    form = DriverPage(admin_page)
    messages = _attempt(form, network, None, blank=True)
    _assert_rejected(form, network, messages, "required")
    for field in ("Driver name", "Email address", "Contact number", "licence number", "password", "licence file", "photo"):
        assert any(field.lower() in m.lower() for m in messages), f"No required-field message for '{field}': {messages}"


# ── TC Staff ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overrides, form_kwargs, expect", STAFF_CASES)
def test_staff_rejects_invalid_input(admin_page: Page, network, tmp_path, overrides, form_kwargs, expect) -> None:
    staff = replace(data.staff_data(), **overrides)
    form = StaffPage(admin_page)
    kwargs = _build_kwargs(form_kwargs, tmp_path)
    messages = _attempt(form, network, lambda: form.fill_form(staff, **kwargs))
    _assert_rejected(form, network, messages, expect)


def test_staff_empty_form_lists_every_required_field(admin_page: Page, network) -> None:
    form = StaffPage(admin_page)
    messages = _attempt(form, network, None, blank=True)
    _assert_rejected(form, network, messages, "required")
    for field in ("Staff Name", "Email", "Contact Number", "Password"):
        assert any(field in m for m in messages), f"No required-field message for '{field}': {messages}"


# ── Duplicates: an existing record's unique value must be rejected, original untouched ──

DUPLICATE_MESSAGE = "already|exist|taken|unique|duplicate"


def _existing_oem(form: OemPage) -> tuple[str, str]:
    """(code, contact email) of an existing OEM, read from the first list row."""
    form.open()
    row = form.first_row_text()
    return re.search(r"Code:\s*(\S+)", row).group(1), EMAIL_IN_TEXT.search(row).group(0)


def _assert_duplicate_rejected(form: UserListPage, network: NetworkMonitor, messages: list[str], duplicate: str) -> None:
    _assert_rejected(form, network, messages, DUPLICATE_MESSAGE)
    form.expect_in_list(duplicate)  # exactly one record still carries the value -> no second copy


def test_oem_duplicate_code_is_rejected(admin_page: Page, network) -> None:
    form = OemPage(admin_page)
    code, _ = _existing_oem(form)
    oem = replace(data.oem_data(), code=code)
    messages = _attempt(form, network, lambda: form.fill_form(oem))
    _assert_duplicate_rejected(form, network, messages, code)



def test_rto_duplicate_code_is_rejected(admin_page: Page, network) -> None:
    form = RtoPage(admin_page).open()
    code = sorted(form.existing_codes())[0]
    rto = replace(data.rto_data(form.existing_codes()), code=code)
    messages = _attempt(form, network, lambda: form.fill_form(rto))
    _assert_duplicate_rejected(form, network, messages, code)


def test_inspector_duplicate_email_is_rejected(admin_page: Page, network) -> None:
    form = InspectorPage(admin_page).open()
    email = EMAIL_IN_TEXT.search(form.first_row_text()).group(0)
    inspector = replace(data.inspector_data(), email=email)
    messages = _attempt(form, network, lambda: form.fill_form(inspector))
    _assert_duplicate_rejected(form, network, messages, email)


@pytest.mark.parametrize("field", ["email", "licence_number"])
def test_driver_duplicate_is_rejected(admin_page: Page, network, tmp_path, field: str) -> None:
    form = DriverPage(admin_page).open()
    row = form.first_row_text()
    existing = EMAIL_IN_TEXT.search(row).group(0) if field == "email" else re.search(r"\bDL\w{12,}", row).group(0)
    driver = replace(data.driver_data(), **{field: existing})
    messages = _attempt(form, network, lambda: form.fill_form(driver, create_test_png(tmp_path)))
    _assert_duplicate_rejected(form, network, messages, existing)


def test_staff_duplicate_email_is_rejected(admin_page: Page, network) -> None:
    form = StaffPage(admin_page).open()
    email = EMAIL_IN_TEXT.search(form.first_row_text()).group(0)
    staff = replace(data.staff_data(), email=email)
    messages = _attempt(form, network, lambda: form.fill_form(staff))
    _assert_duplicate_rejected(form, network, messages, email)


# ── Script injection in a text field: never executed, never reflected as HTML ─────

XSS_PAYLOAD = "<script>alert(1)</script>"


@pytest.mark.parametrize("entity", ["inspector", "staff"])
def test_script_in_name_is_not_executed(admin_page: Page, network, entity: str) -> None:
    """Either the form rejects the payload or it is stored as inert text – no dialog, no HTML."""
    dialogs: list[str] = []
    admin_page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    if entity == "inspector":
        form, record = InspectorPage(admin_page), replace(data.inspector_data(), name=XSS_PAYLOAD)
    else:
        form, record = StaffPage(admin_page), replace(data.staff_data(), name=XSS_PAYLOAD)

    form.open()
    form.open_create_form()
    network.clear()
    form.fill_form(record)
    form.submit_button.click()
    admin_page.wait_for_timeout(3_000)

    assert not network.server_errors(), f"5xx for script payload: {[str(c) for c in network.server_errors()]}"
    assert not network.leaks()
    if not form.form_heading.is_visible():  # accepted -> must be shown as plain text
        row = form.expect_in_list(record.email)
        assert XSS_PAYLOAD in row.inner_text(), "Stored name is not displayed literally"
        assert row.locator("script").count() == 0, "Payload was rendered as an HTML <script> element"
    assert dialogs == [], f"JavaScript executed from user input: {dialogs}"


# ── OEM date picker: COP 'valid till' can never precede 'valid from' ──────────────

def test_oem_cop_valid_till_cannot_precede_valid_from(admin_page: Page) -> None:
    form = OemPage(admin_page).open()
    form.open_create_form()

    form.cop_valid_from.pick_day(months_from_now=1, day=20)  # valid from: 20th of next month
    form.cop_valid_till._open()
    earlier_day = form.cop_valid_till.popover.get_by_role("button", name="15", exact=True)
    assert earlier_day.is_disabled(), "A 'valid till' date earlier than 'valid from' can be selected"
