"""
OEM > Management > Device Management through the screens: Device Details, Bulk Upload, Allocate Stock, Device Allocation History, Device Models.

`test_oem_device_registration.py` and `test_oem_allocation.py` already prove the rules through the API (registration validation, bulk rules,
allocation, rollback, the happy wizard path). This module covers what only the screens do: the filters that apply on Search, the pager, the
View / Edit / Delete dialogs, the registration form's messages, the Bulk Upload dialog, the wizard's controls and the history page.

Repair, replacement and the SIM extension happy path need a device that a fitment centre installed on a vehicle; the OEM account has none,
so they cannot be tested (see specs/oem-device-management-test-report.md). Everything created here is released again by `device_lab`;
allocations go to the long-lived 'AUTO PG FC lifecycle' centre and are rolled back (the history rows stay, the application cannot delete them).
"""

import json
import math
import re
from datetime import date, timedelta

import openpyxl
import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.allocation import AllocateStockPage, AllocationHistoryPage, AllocationSuccessPage
from pages.oem_panel.devices import DeviceEditPage, DeviceFormPage, DeviceListPage
from pages.oem_panel.misc import OemDeviceModelsPage
from utils.api_client import ApiClient
from utils.file_utils import write_file
from utils.oem_mgmt_api import OemMgmtApi
from utils.oem_panel_api import ALLOCATIONS, DEVICES, bulk_row, device_body, find_oem_account, unique_imei

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

SAMPLE_COLUMNS = ["IMEI", "Serial Number", "Device Model", "SIM Module", "Firmware", "Slot ID", "Primary Mobile Number", "Secondary Mobile Number", "ICCID", "Valid Till"]


def _listing(oem_api: ApiClient, query: str = "") -> dict:
    return oem_api.get(f"{DEVICES}?per_page=100&{query}").json()


def _is_device_list(response) -> bool:
    return "/api/devices?" in response.url and response.request.method == "GET"


# ── Device Details: list, filters, pager ──────────────────────────────────────

def test_the_device_list_pages_through_every_device(device_lab, oem_page: Page, oem_api: ApiClient) -> None:
    for _ in range(11):
        device_lab.register()
    total = _listing(oem_api)["meta"]["pagination"]["total"]
    everything = [d["imei"] for d in _listing(oem_api)["data"]]
    devices = DeviceListPage(oem_page).open()

    expect(devices.pager_summary).to_have_text(f"Showing 1 to 10 of {total} results")
    expect(devices.pager_button("First page")).to_be_disabled()
    seen = devices.imeis()
    assert len(seen) == 10
    for number in range(2, math.ceil(total / 10) + 1):
        devices.go_to("Next page")
        expect(devices.pager_summary).to_have_text(f"Showing {(number - 1) * 10 + 1} to {min(number * 10, total)} of {total} results")
        seen += devices.imeis()

    expect(devices.pager_button("Next page")).to_be_disabled()
    assert sorted(seen) == sorted(everything)  # every device on exactly one page


def test_the_filters_apply_when_search_is_pressed_and_clear_filter_restores_the_list(device_lab, oem_page: Page, lifecycle: dict) -> None:
    first, second, third = device_lab.register(), device_lab.register(), device_lab.register()
    device_lab.allocate(lifecycle["id"], first)
    devices = DeviceListPage(oem_page).open()
    expect(devices.row_with(second["imei"])).to_have_count(1)

    devices.choose_filter(1, "Allocated")
    assert {first["imei"], second["imei"], third["imei"]} <= set(devices.imeis())  # choosing alone does not filter yet
    devices.apply_filters()
    expect(devices.row_with(first["imei"])).to_have_count(1)
    expect(devices.row_with(second["imei"])).to_have_count(0)
    assert set(devices.imeis()) == {first["imei"]}  # only allocated stock

    devices.choose_filter(0, device_lab.model["model_name"])
    devices.apply_filters()
    assert set(devices.imeis()) == {first["imei"]}  # model and status together

    with oem_page.expect_response(_is_device_list):
        devices.clear_button.click()
    expect(devices.row_with(second["imei"])).to_have_count(1)
    assert {first["imei"], second["imei"], third["imei"]} <= set(devices.imeis())


def test_search_matches_a_part_of_the_imei_ignores_spaces_and_reports_no_match(device_lab, oem_page: Page) -> None:
    device = device_lab.register()
    devices = DeviceListPage(oem_page).open()

    devices.search_box.fill(device["imei"][3:9])
    devices.apply_filters()
    assert device["imei"] in devices.imeis()  # a part of the IMEI is enough

    devices.search_box.fill(f"  {device['imei']}  ")
    devices.apply_filters()
    assert devices.imeis() == [device["imei"]]  # surrounding spaces are ignored

    devices.search_box.fill("999999999999999")
    devices.apply_filters()
    expect(devices.empty_state).to_be_visible()


def test_view_device_shows_the_registered_details_and_the_row_menu_offers_three_actions(device_lab, oem_page: Page) -> None:
    device = device_lab.register()
    devices = DeviceListPage(oem_page).open()
    devices.search(device["imei"])
    devices.expect_device(device["imei"])

    assert devices.row_menu(device["imei"]) == ["View Device", "Edit Device", "Delete Device"]
    devices.choose_row_action(device["imei"], "View Device")

    dialog = devices.view_dialog()
    expect(dialog).to_be_visible()
    for text in (device["imei"], device["serial_number"], device_lab.model["model_name"], device_lab.sim["module_name"], device_lab.firmware["version"], "Available", "Active"):
        expect(dialog).to_contain_text(re.compile(re.escape(text), re.I))  # the dialog writes the inventory status in lower case


# ── Device Details: edit and delete ───────────────────────────────────────────

def test_edit_a_device_changes_the_serial_number_and_keeps_the_sim_read_only(device_lab, oem_page: Page, oem_api: ApiClient) -> None:
    device = device_lab.register()
    serial = f"AUTOSNEDIT{device['imei'][-5:]}"
    form = DeviceEditPage(oem_page, device["id"]).open()
    for box in (form.primary_mobile, form.secondary_mobile, form.iccid, form.valid_till):
        expect(box).to_be_disabled()  # guide 6.5: the SIM validity cannot be changed after registration
    expect(form.serial_number).to_have_value(device["serial_number"])
    form.serial_number.fill(serial)

    with oem_page.expect_response(lambda r: r.url.endswith(f"/api/devices/{device['id']}") and r.request.method == "PUT") as sent:
        form.submit()

    assert sent.value.status == 200, sent.value.text()[:300]
    expect(oem_page).to_have_url(re.compile(r"/oem/devices$"))
    stored = oem_api.get(f"{DEVICES}/{device['id']}").json()["data"]
    assert stored["serial_number"] == serial and stored["imei"] == device["imei"] and stored["inventory_status"] == "available"
    devices = DeviceListPage(oem_page).open()
    devices.search(device["imei"])
    devices.expect_device(device["imei"], serial)  # persists after a fresh load


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("imei", "", "IMEI is required"),
        ("imei", "12345678901234", "IMEI must be exactly 15 digits"),
        ("imei", "12345678901234a", "IMEI must be exactly 15 digits"),
        ("serial_number", "   ", "Serial Number is required"),
    ],
    ids=["imei-empty", "imei-14-digits", "imei-letters", "serial-spaces"],
)
def test_editing_with_an_invalid_value_names_the_field_and_changes_nothing(device_lab, oem_page: Page, oem_api: ApiClient, field: str, value: str, message: str) -> None:
    device = device_lab.register()
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "PUT" and "/api/devices/" in r.url else None)
    form = DeviceEditPage(oem_page, device["id"]).open()
    getattr(form, field).fill(value)

    form.submit()

    expect(oem_page.get_by_text(message, exact=True)).to_be_visible()
    assert not sent
    stored = oem_api.get(f"{DEVICES}/{device['id']}").json()["data"]
    assert (stored["imei"], stored["serial_number"]) == (device["imei"], device["serial_number"])


@pytest.mark.parametrize("field, message", [("imei", "The imei has already been taken."), ("serial_number", "The serial number has already been taken.")])
def test_editing_to_a_value_another_device_has_is_refused(device_lab, oem_page: Page, oem_api: ApiClient, field: str, message: str) -> None:
    device, other = device_lab.register(), device_lab.register()
    form = DeviceEditPage(oem_page, device["id"]).open()
    getattr(form, "serial_number" if field == "serial_number" else "imei").fill(other[field])

    with oem_page.expect_response(lambda r: r.url.endswith(f"/api/devices/{device['id']}") and r.request.method == "PUT") as sent:
        form.submit()

    assert sent.value.status == 422
    expect(oem_page.get_by_text(message, exact=True)).to_be_visible()
    assert oem_api.get(f"{DEVICES}/{device['id']}").json()["data"][field] == device[field]


def test_delete_asks_for_confirmation_and_removes_only_a_confirmed_device(device_lab, oem_page: Page, oem_api: ApiClient) -> None:
    device = device_lab.register()
    devices = DeviceListPage(oem_page).open()
    devices.search(device["imei"])

    devices.choose_row_action(device["imei"], "Delete Device")
    expect(devices.delete_question(device["imei"])).to_be_visible()
    oem_page.get_by_role("button", name="Cancel", exact=True).click()
    expect(devices.delete_question(device["imei"])).to_have_count(0)
    assert oem_api.get(f"{DEVICES}/{device['id']}").status == 200  # Cancel keeps the device

    devices.choose_row_action(device["imei"], "Delete Device")
    with oem_page.expect_response(lambda r: r.request.method == "DELETE" and r.url.endswith(f"/api/devices/{device['id']}")) as sent:
        oem_page.get_by_role("button", name="Delete", exact=True).click()

    assert sent.value.status == 200
    devices.expect_no_device(device["imei"])
    assert oem_api.get(f"{DEVICES}/{device['id']}").status == 404


def test_an_allocated_device_cannot_be_deleted(device_lab, oem_api: ApiClient, lifecycle: dict) -> None:
    device = device_lab.register()
    assert device_lab.allocate(lifecycle["id"], device).status == 201

    response = oem_api.delete(f"{DEVICES}/{device['id']}")

    assert response.status == 422 and "device" in response.json()["errors"], f"{response.status} {response.text()[:200]}"
    assert device_lab.inventory_status(device) == "allocated"


# ── Device registration form (messages and double click) ──────────────────────

def _valid_device(device_lab) -> dict:
    imei = unique_imei()
    body = device_body(device_lab.model, device_lab.firmware, device_lab.sim, imei=imei)
    return dict(
        model=device_lab.model["model_name"], firmware=device_lab.firmware["version"], sim_module=device_lab.sim["module_name"], imei=imei,
        serial=body["serial_number"], primary=body["primary_mobile_number"], secondary=body["secondary_mobile_number"], iccid=body["iccid"],
        valid_till=(date.today() + timedelta(days=800)).isoformat(),
    )


@pytest.mark.parametrize(
    "override, message",
    [
        ({"valid_till": (date.today() - timedelta(days=1)).isoformat()}, "The valid till field must be a date after or equal to today."),
        ({"primary": "987654321"}, "The primary mobile number field format is invalid."),
        ({"iccid": "1" * 18}, "The iccid field must be between 19 and 20 digits."),
        ({"serial": "S" * 101}, "The serial number field must not be greater than 100 characters."),
    ],
    ids=["sim-validity-yesterday", "primary-mobile-9-digits", "iccid-18-digits", "serial-101-characters"],
)
def test_the_registration_form_shows_the_servers_message_and_registers_nothing(device_lab, oem_page: Page, oem_api: ApiClient, override: dict, message: str) -> None:
    device = {**_valid_device(device_lab), **override}
    form = DeviceFormPage(oem_page).open()
    form.fill_device(**device)

    form.submit()

    expect(oem_page.get_by_text(message, exact=True)).to_be_visible()
    expect(oem_page).to_have_url(re.compile(r"/oem/devices/new"))
    assert _listing(oem_api, f"search={device['imei']}")["data"] == []


@pytest.mark.parametrize(
    "field, message",
    [("imei", "This IMEI is already registered."), ("serial", "This serial number is already registered."), ("iccid", "This ICCID is already registered.")],
)
def test_a_value_that_is_already_registered_is_refused_on_the_form(device_lab, oem_page: Page, field: str, message: str) -> None:
    existing = device_lab.register()
    taken = {"imei": existing["imei"], "serial": existing["serial_number"], "iccid": existing["sims"][0]["iccid"]}[field]
    form = DeviceFormPage(oem_page).open()
    form.fill_device(**{**_valid_device(device_lab), field: taken})

    form.submit()

    expect(oem_page.get_by_text(message, exact=True)).to_be_visible()


def test_a_double_click_on_add_device_registers_one_device(device_lab, oem_page: Page, oem_api: ApiClient) -> None:
    device = _valid_device(device_lab)
    posts = []
    oem_page.on("request", lambda r: posts.append(r) if r.method == "POST" and r.url.endswith("/api/devices") else None)
    form = DeviceFormPage(oem_page).open()
    form.fill_device(**device)

    form.submit_button.dblclick()

    expect(oem_page).to_have_url(re.compile(r"/oem/devices$"), timeout=20_000)
    device_lab.adopt(device["imei"])
    assert len(posts) == 1
    assert len(_listing(oem_api, f"search={device['imei']}")["data"]) == 1


# ── Bulk Upload dialog ────────────────────────────────────────────────────────

def test_the_bulk_upload_dialog_offers_the_sample_with_the_documented_columns(oem_page: Page, tmp_path) -> None:
    dialog = DeviceListPage(oem_page).open().bulk_upload()

    expect(oem_page.get_by_text("Maximum upload: 10,000 devices")).to_be_visible()
    expect(oem_page.get_by_text("Supported formats: .xlsx, .xls")).to_be_visible()
    sample = dialog.download_sample(tmp_path)

    sheet = openpyxl.load_workbook(sample).active
    assert [cell.value for cell in sheet[1]] == SAMPLE_COLUMNS
    assert sheet.max_row >= 2  # the sample shows example rows


def test_bulk_upload_without_a_file_sends_nothing(oem_page: Page) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "POST" and "bulk-upload" in r.url else None)
    dialog = DeviceListPage(oem_page).open().bulk_upload()

    dialog.upload()

    oem_page.wait_for_timeout(500)  # nothing is expected to happen; give a request the chance to show up
    assert not sent
    expect(dialog.title).to_be_visible()  # the dialog stays open


@pytest.mark.parametrize(
    "name, content",
    [("notes.txt", "hello"), ("empty.xlsx", b""), ("fake.xlsx", "this is not a workbook")],
    ids=["text-file", "empty-xlsx", "text-called-xlsx"],
)
def test_an_unreadable_file_is_reported_and_registers_nothing(oem_page: Page, oem_api: ApiClient, tmp_path, name: str, content) -> None:
    total = _listing(oem_api)["meta"]["pagination"]["total"]
    dialog = DeviceListPage(oem_page).open().bulk_upload()
    dialog.choose(write_file(tmp_path, name, content))

    dialog.upload()

    expect(oem_page.get_by_text("Bulk upload failed.")).to_be_visible()
    assert _listing(oem_api)["meta"]["pagination"]["total"] == total


@pytest.mark.xfail(
    reason="BUG-066: the dialog accepts any file (.exe, .py, .html ...) as the file to upload; only the file picker's filter hints at .xlsx / .xls",
    strict=False,
)
@pytest.mark.parametrize("name", ["setup.exe", "script.py", "page.html"], ids=["exe", "python", "html"])
def test_a_file_that_is_not_an_excel_sheet_is_refused_when_it_is_chosen(oem_page: Page, tmp_path, name: str) -> None:
    dialog = DeviceListPage(oem_page).open().bulk_upload()

    dialog.file_input.set_input_files(write_file(tmp_path, name, "print('hello')\n"))  # plain text with a foreign extension, nothing executable

    oem_page.wait_for_timeout(500)
    accepted = oem_page.get_by_text(f"Selected: {name}").count() == 1 and dialog.upload_button.is_enabled()
    assert not accepted, f"{name} is shown as the selected file and Upload is enabled although only .xlsx / .xls are supported"


@pytest.mark.xfail(
    reason="BUG-066: the screen does not enforce its own limit of 10,000 devices; a long file is sent whole and the server answers 504 after 60 s",
    strict=False,
)
def test_a_file_with_more_than_10000_rows_is_not_sent(oem_page: Page, tmp_path) -> None:
    sent = []
    oem_page.route(re.compile(r".*/api/devices/bulk-upload$"), lambda route: (sent.append(len(json.loads(route.request.post_data or "{}").get("devices", []))), route.abort()))
    dialog = DeviceListPage(oem_page).open().bulk_upload()
    dialog.choose(write_file(tmp_path, "long.py", "".join(f"value_{i} = {i}\n" for i in range(10_100))))  # the request is aborted below: the server is never asked

    dialog.upload()

    oem_page.wait_for_timeout(1500)
    assert not [rows for rows in sent if rows > 10_000], f"a request with {sent} rows was sent although the dialog says 'Maximum upload: 10,000 devices'"


def _filled_in_sample(sample, path, row: dict):
    """The product's own sample workbook with its example rows replaced by one row of real data."""
    workbook = openpyxl.load_workbook(sample)
    sheet = workbook.active
    sheet.delete_rows(2, sheet.max_row)
    sheet.append([row[key] for key in ("imei", "serial_number", "device_model", "sim_module", "firmware", "slot_id", "primary_mobile_number",
                                       "secondary_mobile_number", "iccid", "valid_till")])
    workbook.save(path)
    return path


@pytest.mark.xfail(
    reason="BUG-061: the screen reads none of the sample template's columns (every row is sent as {}) and never reads the two mobile-number columns, "
           "so a bulk upload from the screen cannot succeed",
    strict=False,
)
def test_the_sheet_is_read_into_complete_rows(device_lab, oem_page: Page, tmp_path) -> None:
    row = bulk_row(device_lab.model, device_lab.firmware, device_lab.sim)
    captured: list[dict] = []

    def handle(route, request) -> None:
        captured.append(request.post_data_json)
        route.abort()  # nothing is registered by this test

    oem_page.route("**/api/devices/bulk-upload", handle)
    dialog = DeviceListPage(oem_page).open().bulk_upload()
    sample = dialog.download_sample(tmp_path)
    dialog.choose(_filled_in_sample(sample, tmp_path / "filled.xlsx", row))

    dialog.upload()

    oem_page.wait_for_timeout(1000)
    assert captured, "no request was sent"
    assert captured[0]["devices"] == [row], captured[0]


@pytest.mark.xfail(reason="BUG-061: a bulk upload from the screen cannot succeed (see test_the_sheet_is_read_into_complete_rows)", strict=False)
def test_a_filled_in_sample_registers_the_device(device_lab, oem_page: Page, oem_api: ApiClient, tmp_path) -> None:
    row = bulk_row(device_lab.model, device_lab.firmware, device_lab.sim)
    dialog = DeviceListPage(oem_page).open().bulk_upload()
    dialog.choose(_filled_in_sample(dialog.download_sample(tmp_path), tmp_path / "filled.xlsx", row))

    with oem_page.expect_response(lambda r: r.url.endswith("/api/devices/bulk-upload")) as sent:
        dialog.upload()

    device_lab.adopt(row["imei"])
    assert sent.value.status == 201, sent.value.text()[:300]
    assert [d["imei"] for d in _listing(oem_api, f"search={row['imei']}")["data"]] == [row["imei"]]


# ── Allocate Stock wizard ─────────────────────────────────────────────────────

def test_the_wizard_needs_a_district_a_centre_and_a_device(device_lab, oem_page: Page, lifecycle: dict, district_of) -> None:
    device = device_lab.register()
    wizard = AllocateStockPage(oem_page).open()
    expect(wizard.continue_button).to_be_disabled()

    wizard.select_district(district_of(lifecycle))
    expect(wizard.continue_button).to_be_disabled()  # a district alone is not enough
    wizard.select_fitment_centre(lifecycle["business_name"])
    expect(wizard.continue_button).to_be_enabled()
    wizard.continue_to_devices()

    expect(wizard.allocate_button).to_be_disabled()  # nothing ticked
    wizard.select_device(device["imei"])
    expect(wizard.selected_counter).to_have_text("1 Selected")
    expect(wizard.allocate_button).to_be_enabled()


def test_the_wizard_search_narrows_the_devices_and_select_all_ticks_every_listed_one(device_lab, oem_page: Page, lifecycle: dict, district_of) -> None:
    devices = [device_lab.register() for _ in range(3)]
    wizard = AllocateStockPage(oem_page).start(district_of(lifecycle), lifecycle["business_name"])

    wizard.search_box.fill(devices[1]["imei"])
    expect(wizard.device_row(devices[1]["imei"])).to_have_count(1)
    expect(wizard.device_row(devices[0]["imei"])).to_have_count(0)

    wizard.search_box.fill("")
    expect(wizard.device_row(devices[0]["imei"])).to_have_count(1)
    wizard.select_all_box.check()
    expect(wizard.selected_counter).to_have_text(f"{len(wizard.listed_imeis())} Selected")


def test_a_double_click_on_allocate_and_on_confirm_rollback_sends_one_request_each(device_lab, oem_page: Page, lifecycle: dict, district_of) -> None:
    device = device_lab.register()
    posts = []
    oem_page.on("request", lambda r: posts.append(r.url) if r.method == "POST" and "/api/device-allocations" in r.url else None)
    wizard = AllocateStockPage(oem_page).start(district_of(lifecycle), lifecycle["business_name"])
    wizard.select_device(device["imei"])

    wizard.allocate_button.dblclick()

    allocation_id = AllocationSuccessPage(oem_page).allocation_id()
    device_lab.track_allocation(allocation_id, device)
    assert len(posts) == 1 and posts[0].endswith("/api/device-allocations")
    expect(oem_page.locator("main")).to_contain_text(lifecycle["business_name"])  # the summary names the receiving centre
    assert device_lab.inventory_status(device) == "allocated"

    oem_page.get_by_role("button", name="Rollback Allocation").click()
    expect(oem_page.get_by_text("Rollback allocation?")).to_be_visible()
    oem_page.get_by_role("button", name="Cancel").last.click()
    assert device_lab.inventory_status(device) == "allocated"  # Cancel keeps the allocation

    oem_page.get_by_role("button", name="Rollback Allocation").click()
    posts.clear()
    oem_page.get_by_role("button", name="Confirm Rollback").dblclick()
    expect(oem_page.get_by_text("Selected devices returned to inventory successfully.")).to_be_visible()
    assert len(posts) == 1 and device_lab.inventory_status(device) == "available"


@pytest.mark.xfail(
    reason="BUG-063: the wizard asks for 20 devices and has no pager, so devices beyond the first 20 cannot be ticked (the API says 25 are available)",
    strict=False,
)
def test_the_wizard_lists_every_available_device(device_lab, oem_page: Page, oem_api: ApiClient, lifecycle: dict, district_of) -> None:
    devices = [device_lab.register() for _ in range(25)]
    total = _listing(oem_api)["meta"]["pagination"]["total"]
    wizard = AllocateStockPage(oem_page).start(district_of(lifecycle), lifecycle["business_name"])
    expect(wizard.device_row(devices[-1]["imei"]).or_(wizard.device_row(devices[0]["imei"]))).not_to_have_count(0)  # the list has been drawn

    listed = len(wizard.listed_imeis())

    pager = wizard.main.get_by_role("button", name=re.compile("page|more", re.I)).count()
    assert listed == total or pager, f"{listed} of {total} available devices are listed and there is no pager"


@pytest.mark.xfail(reason="BUG-064: the counter above the device list says '0 available device(s)' whatever is listed or ticked", strict=False)
def test_the_available_devices_counter_shows_the_number_listed(device_lab, oem_page: Page, lifecycle: dict, district_of) -> None:
    devices = [device_lab.register() for _ in range(3)]
    wizard = AllocateStockPage(oem_page).start(district_of(lifecycle), lifecycle["business_name"])
    expect(wizard.device_row(devices[-1]["imei"])).to_have_count(1)  # the list has been drawn

    listed = len(wizard.listed_imeis())

    assert listed >= 3
    expect(wizard.available_counter).to_contain_text(f"{listed} available device")


# ── Device Allocation History ─────────────────────────────────────────────────

def test_the_history_shows_the_newest_allocation_first_and_offers_rollback_only_while_allocated(device_lab, oem_page: Page, lifecycle: dict) -> None:
    device = device_lab.register()
    allocation_id = device_lab.allocate(lifecycle["id"], device).json()["data"]["id"]
    history = AllocationHistoryPage(oem_page).open()

    newest = history.data_rows().first
    expect(newest).to_contain_text(lifecycle["business_name"])
    expect(newest).to_contain_text("Allocated")
    expect(newest.get_by_role("button", name="Rollback", exact=True)).to_be_visible()

    assert device_lab.rollback(allocation_id, device).status == 200
    oem_page.reload()
    returned = history.data_rows().first
    expect(returned).to_contain_text("Returned")
    expect(returned.get_by_role("button", name="Rollback", exact=True)).to_have_count(0)  # a returned allocation has no Rollback


def test_the_status_filter_lists_only_allocated_stock_and_view_shows_the_device(device_lab, oem_page: Page, lifecycle: dict) -> None:
    device = device_lab.register()
    allocation_id = device_lab.allocate(lifecycle["id"], device).json()["data"]["id"]
    history = AllocationHistoryPage(oem_page).open()

    with oem_page.expect_response(lambda r: "/api/device-allocations?" in r.url and "status=allocated" in r.url):
        history.filter_status("Allocated")
    expect(history.data_rows().first).to_contain_text("Allocated")
    for status in history.data_rows().all_inner_texts():
        assert "Allocated" in status and "Returned" not in status  # only allocations that still hold stock
    history.data_rows().filter(has_text=lifecycle["business_name"]).first.get_by_role("button", name="View", exact=True).click()

    expect(oem_page).to_have_url(re.compile(rf"/oem/device-allocations/{allocation_id}$"))
    expect(oem_page.get_by_text("Allocation Details").first).to_be_visible()
    expect(oem_page.locator("main")).to_contain_text(device["imei"])
    expect(oem_page.locator("main")).to_contain_text(lifecycle["business_name"])


@pytest.mark.xfail(
    reason="BUG-065: the history search ('Fitment center, IMEI, OEM code...') finds nothing, whatever is typed: IMEI, serial, centre name or code, OEM code",
    strict=False,
)
def test_the_history_search_finds_an_allocation_by_its_imei(device_lab, oem_page: Page, lifecycle: dict) -> None:
    device = device_lab.register()
    device_lab.allocate(lifecycle["id"], device)
    history = AllocationHistoryPage(oem_page).open()

    with oem_page.expect_response(lambda r: "/api/device-allocations?" in r.url and "search=" in r.url):
        history.search_box.fill(device["imei"])

    expect(history.data_rows()).to_have_count(1)
    expect(history.data_rows().first).to_contain_text(lifecycle["business_name"])


@pytest.mark.xfail(
    reason="BUG-062: the history shows only the newest 10 allocations and has no pager (the API holds hundreds), so older allocations can only be reached by filters",
    strict=False,
)
def test_the_history_can_be_paged(oem_page: Page, oem_api: ApiClient) -> None:
    total = oem_api.get(f"{ALLOCATIONS}?per_page=10").json()["meta"]["pagination"]["total"]
    if total <= 10:
        pytest.skip(f"Only {total} allocations exist")
    history = AllocationHistoryPage(oem_page).open()

    expect(history.data_rows()).to_have_count(10)

    assert history.pager_buttons(), f"{total} allocations exist but the page offers no way to see more than 10"


# ── Device Models (view only) ─────────────────────────────────────────────────

@pytest.mark.xfail(
    reason="BUG-038 (also Edit and Delete): the OEM may only view device models (guide 14.4), yet each row offers 'Edit Model' and 'Delete Model'; the server refuses them (403)",
    strict=False,
)
def test_the_oem_is_offered_only_to_view_a_device_model(device_lab, oem_page: Page) -> None:
    page = OemDeviceModelsPage(oem_page).open()
    row = page.row_with(device_lab.model["model_name"])
    row.get_by_role("button", name="Open actions").click()

    items = [item.strip() for item in oem_page.get_by_role("menuitem").all_text_contents()]

    assert items == ["View Model"], items


# ── Isolation between OEMs (API) ──────────────────────────────────────────────

def test_another_oem_cannot_edit_delete_or_roll_back_what_it_does_not_own(device_lab, admin_api: ApiClient, other_oem: ApiClient, oem_api: ApiClient, lifecycle: dict) -> None:
    victim, allocated = device_lab.register(), device_lab.register()
    allocation_id = device_lab.allocate(lifecycle["id"], allocated).json()["data"]["id"]
    masters = OemMgmtApi(admin_api, find_oem_account(admin_api, other_oem))
    try:
        model = masters.create_model()
        firmware = masters.create_firmware(model["id"])
        sim = masters.create_sim()
        # valid data of the OTHER oem, so the request can only be refused because of ownership (validation comes first)
        body = {**device_body(model, firmware, sim, imei=victim["imei"]), "serial_number": f"AUTOSNOTHER{victim['imei'][-4:]}"}

        edit = other_oem.put(f"{DEVICES}/{victim['id']}", json=body)
        delete = other_oem.delete(f"{DEVICES}/{victim['id']}")
        read = other_oem.get(f"{DEVICES}/{victim['id']}")
        rollback = other_oem.post(f"{ALLOCATIONS}/{allocation_id}/rollback", json={"allocation_id": allocation_id, "imeis": [allocated["imei"]]})
        allocation = other_oem.get(f"{ALLOCATIONS}/{allocation_id}")

        assert (edit.status, delete.status, read.status, allocation.status) == (404, 404, 404, 404), (edit.status, delete.status, read.status, allocation.status)
        assert rollback.status == 422, rollback.text()[:200]
        stored = oem_api.get(f"{DEVICES}/{victim['id']}").json()["data"]
        assert stored["serial_number"] == victim["serial_number"] and stored["oem_id"] == victim["oem_id"]
        assert device_lab.inventory_status(allocated) == "allocated"
    finally:
        masters.cleanup()


def test_another_oem_cannot_register_a_device_with_this_oems_master_data(device_lab, other_oem: ApiClient) -> None:
    response = other_oem.post(DEVICES, json=device_body(device_lab.model, device_lab.firmware, device_lab.sim))

    errors = response.json()["errors"]
    assert response.status == 422 and {"device_model_id", "sim_module_id"} <= set(errors), f"{response.status} {response.text()[:200]}"
