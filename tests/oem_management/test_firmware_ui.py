"""
Firmware - UI tests: table, search, filters, create, view, edit, delete.   Plan: specs/oem-management-test-plan.md

A firmware belongs to a device model of an OEM. The records most tests need are created through the API; the create
form is exercised through the UI as well (it could not offer any device model before BUG-023 was fixed).
Techniques: equivalence partitioning, boundary value analysis (version max 50), state-based checks
(Active / Inactive, Optional / Mandatory).
"""

import re

import pytest
from playwright.sync_api import expect

from pages.oem_management.firmware_page import FirmwarePage
from tests.oem_management.bugs import DELETE_BROKEN
from utils import data_generator as data
from utils.oem_mgmt_api import OemMgmtApi

pytestmark = [pytest.mark.oem_management]

NEW_URL = re.compile(r"/firmware/new$")


@pytest.fixture
def firmware(records: OemMgmtApi):
    """A firmware (with its own device model) created through the API."""
    model = records.create_model()
    return records.create_firmware(model["id"]), model


# ── Table (read) ──────────────────────────────────────────────────────────────

def test_list_page_has_all_controls_and_columns(firmware_page: FirmwarePage) -> None:
    p = firmware_page.open()

    for control in (p.add_button, p.refresh_button, p.search_box, p.oem_filter, p.update_type_filter, p.status_filter):
        expect(control).to_be_visible()
    assert [h.lower() for h in p.column_headers()] == [c.lower() for c in p.COLUMNS]


def test_row_shows_version_model_date_type_and_status(firmware_page: FirmwarePage, firmware) -> None:
    record, model = firmware
    p = firmware_page.open()

    row = p.row(record["version"])
    expect(row).to_have_count(1)
    text = " ".join(p.row_cells(row.first))
    for expected in (model["model_name"], record["version"], "01 Feb 2026", "Optional", "Active"):
        assert expected in text, f"'{expected}' missing from row: {text}"



def test_view_shows_firmware_and_model_details(firmware_page: FirmwarePage, firmware) -> None:
    record, model = firmware
    p = firmware_page.open()

    p.view(p.row(record["version"]))
    shown = p.view_text()
    for expected in (record["version"], model["model_name"], "01 Feb 2026", "Created by automation", "Optional", "Active"):
        assert expected in shown, f"'{expected}' missing from the View panel"
    p.close_view()



# ── Search ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "variant",
    [
        pytest.param(lambda v: v, id="full-version"),
        pytest.param(lambda v: v[5:], id="partial"),
        pytest.param(lambda v: v.lower(), id="lower-case"),
    ],
)
def test_search_by_version_finds_the_record(firmware_page: FirmwarePage, firmware, variant) -> None:
    record, _ = firmware
    p = firmware_page.open()

    p.search(variant(record["version"]))

    expect(p.row(record["version"])).to_have_count(1)



def test_search_without_match_shows_empty_state_and_clearing_restores_rows(firmware_page: FirmwarePage) -> None:
    p = firmware_page.open()
    before = p.rows().count()

    p.search("zz-no-such-firmware-zz")
    assert p.visible_record_count() == 0
    expect(p.empty_state()).to_be_visible()

    p.clear_search()
    assert p.rows().count() == before



# ── Filters ───────────────────────────────────────────────────────────────────

def test_status_filter_separates_active_and_inactive(firmware_page: FirmwarePage, records: OemMgmtApi) -> None:
    model = records.create_model()
    active = records.create_firmware(model["id"])
    inactive = records.create_firmware(model["id"], is_active=False)
    p = firmware_page.open()

    p.filter_by_status("Inactive")
    expect(p.row(inactive["version"])).to_have_count(1)
    expect(p.row(active["version"])).to_have_count(0)

    p.filter_by_status("Active")
    expect(p.row(active["version"])).to_have_count(1)
    expect(p.row(inactive["version"])).to_have_count(0)


def test_update_type_filter_separates_mandatory_and_optional(firmware_page: FirmwarePage, records: OemMgmtApi) -> None:
    model = records.create_model()
    optional = records.create_firmware(model["id"], is_mandatory=False)
    mandatory = records.create_firmware(model["id"], is_mandatory=True)
    p = firmware_page.open()

    p.filter_by_update_type("Mandatory")
    expect(p.row(mandatory["version"])).to_have_count(1)
    expect(p.row(optional["version"])).to_have_count(0)

    p.filter_by_update_type("Optional")
    expect(p.row(optional["version"])).to_have_count(1)
    expect(p.row(mandatory["version"])).to_have_count(0)


def test_oem_filter_narrows_the_table(firmware_page: FirmwarePage, firmware, records: OemMgmtApi) -> None:
    record, _ = firmware
    p = firmware_page.open()

    options = p.oem_filter_options()
    assert options[0] == "All OEMs" and len(options) > 1
    p.filter_by_oem(records.oem_name)

    expect(p.row(record["version"])).to_have_count(1)



def test_filter_with_no_result_shows_empty_state(firmware_page: FirmwarePage, firmware) -> None:
    record, _ = firmware  # Active + Optional
    p = firmware_page.open()

    p.filter_by_status("Inactive")
    p.search(record["version"])

    assert p.visible_record_count() == 0
    expect(p.empty_state()).to_be_visible()


# ── Create form ───────────────────────────────────────────────────────────────

def test_device_model_is_disabled_until_an_oem_is_chosen(firmware_page: FirmwarePage) -> None:
    p = firmware_page.open()
    p.open_add_form()

    device_model = p.page.get_by_role("combobox", name="Device Model *")
    expect(device_model).to_be_disabled()
    expect(device_model).to_contain_text("Select OEM first")


def test_empty_form_lists_every_required_field(firmware_page: FirmwarePage) -> None:
    p = firmware_page.open()
    p.open_add_form()

    p.submit_create()

    messages = p.wait_for_message(r"OEM is required")
    for expected in ("OEM is required.", "Device Model is required.", "Firmware version is required."):
        assert expected in messages, messages
    expect(p.page).to_have_url(NEW_URL)


def _dropdown_options(p: FirmwarePage, name: str) -> set[str]:
    """Open a form dropdown, read its options, and close it again."""
    p.page.get_by_role("combobox", name=name, exact=True).click()
    options = p.page.locator("[role=option]:visible")
    expect(options.first).to_be_visible()
    texts = {o.strip() for o in options.all_inner_texts()}
    p.page.keyboard.press("Escape")
    expect(options).to_have_count(0)
    return texts


def test_create_form_offers_the_update_types_and_no_status(firmware_page: FirmwarePage) -> None:
    """New firmware is always Active (the Status choice exists only on the edit form)."""
    p = firmware_page.open()
    p.open_add_form()

    assert _dropdown_options(p, "Update Type") == {"Optional Update", "Mandatory Update"}
    expect(p.page.get_by_role("combobox", name="Status", exact=True)).to_have_count(0)



def test_device_model_list_offers_the_models_of_the_chosen_oem(firmware_page: FirmwarePage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = firmware_page.open()
    p.open_add_form()

    p.choose_oem(records.oem_name)

    p.page.get_by_role("combobox", name="Device Model *").click()
    expect(p.page.locator("[role=option]:visible").filter(has_text=model["model_name"])).to_have_count(1, timeout=5_000)


def test_create_firmware_through_the_form(firmware_page: FirmwarePage, records: OemMgmtApi) -> None:
    model = records.create_model()
    fw = data.firmware_data()
    p = firmware_page.open()
    p.open_add_form()

    p.fill_form(fw, oem_name=records.oem_name, model_name=model["model_name"])
    p.submit_create()

    p.wait_for_message(r"created successfully")
    created = records.find("firmware", "version", fw.version)
    assert created, "the firmware was not saved"
    records.track("firmware", created["id"])
    expect(p.row(fw.version)).to_have_count(1)
    expect(p.row(fw.version)).to_contain_text(model["model_name"])



def test_device_model_is_required(firmware_page: FirmwarePage, records: OemMgmtApi) -> None:
    p = firmware_page.open()
    p.open_add_form()
    p.choose_oem(records.oem_name)
    p.fill("Firmware Version *", data.firmware_data().version)

    p.submit_create()

    p.wait_for_message(r"Device Model is required")
    expect(p.page).to_have_url(NEW_URL)



def test_duplicate_version_for_the_same_model_is_rejected(firmware_page: FirmwarePage, records: OemMgmtApi) -> None:
    model = records.create_model()
    existing = records.create_firmware(model["id"])
    p = firmware_page.open()
    p.open_add_form()
    p.fill_form(data.firmware_data(), oem_name=records.oem_name, model_name=model["model_name"])

    p.fill("Firmware Version *", existing["version"])
    p.submit_create()

    p.wait_for_message(r"already been taken")
    expect(p.page).to_have_url(NEW_URL)


# ── Update ────────────────────────────────────────────────────────────────────

def test_edit_form_is_prefilled(firmware_page: FirmwarePage, firmware, records: OemMgmtApi) -> None:
    record, _ = firmware
    p = firmware_page.open()

    p.edit(p.row(record["version"]))

    expect(p.textbox("Firmware Version *")).to_have_value(record["version"])
    expect(p.textbox("Release Date")).to_have_value("2026-02-01")
    expect(p.page.get_by_role("textbox", name="Enter firmware release notes...")).to_have_value("Created by automation")
    expect(p.page.get_by_role("combobox", name="OEM *")).to_contain_text(records.oem_name)



def test_edit_saves_changes_and_updates_the_table(firmware_page: FirmwarePage, firmware) -> None:
    record, _ = firmware
    p = firmware_page.open()
    p.edit(p.row(record["version"]))

    new_version = record["version"] + "-E"
    p.fill("Firmware Version *", new_version)
    p.fill("Release Date", "2026-03-15")
    p.choose("Update Type", "Mandatory Update")
    p.submit_update()

    p.wait_for_message(r"updated successfully")
    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/firmware$"))
    row = p.row(new_version)
    expect(row).to_have_count(1)
    expect(row).to_contain_text("15 Mar 2026")
    expect(row).to_contain_text("Mandatory")



# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_confirmation_names_the_record_and_cancel_keeps_it(firmware_page: FirmwarePage, firmware) -> None:
    record, _ = firmware
    p = firmware_page.open()

    p.start_delete(p.row(record["version"]))
    assert f"delete firmware {record['version']}" in p.view_text()
    p.cancel_delete()

    expect(p.row(record["version"])).to_have_count(1)


@DELETE_BROKEN
def test_delete_removes_the_record(firmware_page: FirmwarePage, firmware, records: OemMgmtApi) -> None:
    record, _ = firmware
    p = firmware_page.open()

    p.start_delete(p.row(record["version"]))
    p.confirm_delete()

    p.wait_for_message(r"deleted successfully")
    expect(p.row(record["version"])).to_have_count(0)
    assert not records.exists("firmware", record["id"])
