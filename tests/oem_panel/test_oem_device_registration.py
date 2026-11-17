"""
OEM device registration (guide 6.1): one by one and in bulk.

  A device is registered with the Device Model, Firmware and SIM Module that the State Admin set up for the OEM, plus
  IMEI, serial number, SIM numbers and SIM validity. It enters the OEM's stock as "available".
  A bulk upload is all-or-nothing; rows with errors produce a downloadable Excel validation report.

OEM-B1 .. OEM-B6 of specs/oem-panel-test-plan.md. Everything registered here is deleted again (see `device_lab`).
"""

import io
import re
from datetime import date, timedelta

import openpyxl
import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.devices import DeviceFormPage, DeviceListPage
from utils.oem_mgmt_api import OemMgmtApi
from utils.oem_panel_api import BULK_UPLOAD, DEVICES, bulk_row, device_body, unique_imei

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ── OEM-B1: a registered device is stocked, listed and counted ────────────────

def test_registered_device_is_available_listed_and_counted(device_lab, oem_page: Page) -> None:
    before = device_lab.totals()

    device = device_lab.register()

    after = device_lab.totals()
    assert after["total_devices"] == before["total_devices"] + 1
    assert after["available_devices"] == before["available_devices"] + 1
    assert device_lab.inventory_status(device) == "available"

    devices = DeviceListPage(oem_page).open()
    devices.search(device["imei"])
    devices.expect_device(device["imei"], device_lab.model["model_name"], device_lab.sim["module_name"], device_lab.firmware["version"], "available")


def test_device_can_be_registered_through_the_form(device_lab, oem_page: Page) -> None:
    imei = unique_imei()
    body = device_body(device_lab.model, device_lab.firmware, device_lab.sim, imei=imei)

    form = DeviceFormPage(oem_page).open()
    form.fill_device(
        model=device_lab.model["model_name"], firmware=device_lab.firmware["version"], sim_module=device_lab.sim["module_name"],
        imei=imei, serial=body["serial_number"], primary=body["primary_mobile_number"], secondary=body["secondary_mobile_number"],
        iccid=body["iccid"], valid_till=body["valid_till"],
    )
    form.submit()
    expect(oem_page).to_have_url(re.compile(r"/oem/devices$"), timeout=20_000)
    device_lab.adopt(imei)

    created = device_lab.oem.get(f"{DEVICES}?per_page=5&search={imei}").json()["data"]
    assert [d["imei"] for d in created] == [imei]
    assert created[0]["inventory_status"] == "available"
    assert created[0]["serial_number"] == body["serial_number"]


# ── OEM-B2: invalid registrations are refused and create nothing ──────────────

def _soon(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


INVALID_FIELDS = [
    pytest.param({"imei": "12345678901234"}, "imei", id="imei-14-digits"),
    pytest.param({"imei": "ABCDEFGHIJKLMNO"}, "imei", id="imei-letters"),
    pytest.param({"primary_mobile_number": "987654321"}, "primary_mobile_number", id="primary-mobile-9-digits"),
    pytest.param({"secondary_mobile_number": "987654321"}, "secondary_mobile_number", id="secondary-mobile-9-digits"),
    pytest.param({"iccid": "1" * 18}, "iccid", id="iccid-18-digits"),
    pytest.param({"iccid": "1" * 21}, "iccid", id="iccid-21-digits"),
    pytest.param({"valid_till": _soon(-1)}, "valid_till", id="sim-validity-yesterday"),
    pytest.param({"serial_number": ""}, "serial_number", id="serial-number-blank"),
    pytest.param({"device_model_id": 999999}, "device_model_id", id="unknown-model"),
    pytest.param({"sim_module_id": 999999}, "sim_module_id", id="unknown-sim-module"),
    pytest.param({"current_firmware_id": 999999}, "current_firmware_id", id="unknown-firmware"),
]


@pytest.mark.parametrize("override, error_field", INVALID_FIELDS)
def test_invalid_registration_is_refused(device_lab, override: dict, error_field: str) -> None:
    before = device_lab.devices_total()
    body = device_body(device_lab.model, device_lab.firmware, device_lab.sim, **override)

    response = device_lab.post_device(body)

    assert response.status == 422, f"Expected a validation error, got {response.status}: {response.text()[:200]}"
    assert error_field in response.json()["errors"], response.json()["errors"]
    assert device_lab.devices_total() == before


def test_the_same_imei_cannot_be_registered_twice(device_lab) -> None:
    first = device_lab.register()

    response = device_lab.post_device(device_body(device_lab.model, device_lab.firmware, device_lab.sim, imei=first["imei"]))

    assert response.status == 422 and "imei" in response.json()["errors"], response.text()[:300]
    assert len(device_lab.oem.get(f"{DEVICES}?per_page=10&search={first['imei']}").json()["data"]) == 1


def test_firmware_must_belong_to_the_chosen_model(device_lab) -> None:
    _, other_firmware = device_lab.another_model_with_firmware()

    response = device_lab.post_device(device_body(device_lab.model, other_firmware, device_lab.sim))

    assert response.status == 422 and "current_firmware_id" in response.json()["errors"], response.text()[:300]


@pytest.fixture
def foreign_master_data(admin_api):
    """Model, firmware and SIM module that belong to ANOTHER OEM (the AUTO OEM that owns the State Admin test data)."""
    other = OemMgmtApi(admin_api)
    model = other.create_model()
    yield model, other.create_firmware(model["id"]), other.create_sim()
    other.cleanup()


@pytest.mark.parametrize("which, error_field", [("model", "device_model_id"), ("firmware", "current_firmware_id"), ("sim", "sim_module_id")])
def test_master_data_of_another_oem_cannot_be_used(device_lab, foreign_master_data, which: str, error_field: str) -> None:
    model, firmware, sim = foreign_master_data
    body = device_body(device_lab.model, device_lab.firmware, device_lab.sim)
    body[{"model": "device_model_id", "firmware": "current_firmware_id", "sim": "sim_module_id"}[which]] = {"model": model, "firmware": firmware, "sim": sim}[which]["id"]

    response = device_lab.post_device(body)

    assert response.status == 422 and error_field in response.json()["errors"], f"{response.status} {response.text()[:300]}"


# ── OEM-B3: the registration form ─────────────────────────────────────────────

def test_empty_form_is_blocked_and_nothing_is_registered(device_lab, oem_page: Page) -> None:
    before = device_lab.devices_total()
    form = DeviceFormPage(oem_page).open()

    form.submit()

    expect(oem_page).to_have_url(re.compile(r"/oem/devices/new"))  # the form stays open
    invalid = {el.get_attribute("id") for el in oem_page.locator(":invalid").all()}
    assert {"device_model", "sim_module", "valid_till"} <= invalid, f"Required selects/date not flagged: {invalid}"
    assert device_lab.devices_total() == before


def test_form_reports_a_malformed_imei_and_registers_nothing(device_lab, oem_page: Page) -> None:
    before = device_lab.devices_total()
    body = device_body(device_lab.model, device_lab.firmware, device_lab.sim)
    form = DeviceFormPage(oem_page).open()
    form.fill_device(
        model=device_lab.model["model_name"], firmware=device_lab.firmware["version"], sim_module=device_lab.sim["module_name"],
        imei="12345", serial=body["serial_number"], primary=body["primary_mobile_number"], secondary=body["secondary_mobile_number"],
        iccid=body["iccid"], valid_till=body["valid_till"],
    )

    form.submit()

    expect(oem_page.get_by_text(re.compile(r"imei.*15 digits", re.I)).first).to_be_visible()
    expect(oem_page).to_have_url(re.compile(r"/oem/devices/new"))
    assert device_lab.devices_total() == before


def test_firmware_list_offers_only_the_chosen_models_firmware(device_lab, oem_page: Page) -> None:
    other_model, other_firmware = device_lab.another_model_with_firmware()
    form = DeviceFormPage(oem_page).open()

    form.model.select_option(label=device_lab.model["model_name"])
    expect(form.firmware.locator("option", has_text=device_lab.firmware["version"])).to_have_count(1)

    options = form.firmware_options()
    assert device_lab.firmware["version"] in options
    assert other_firmware["version"] not in options


# ── OEM-B4 / B5: bulk upload ──────────────────────────────────────────────────

SAMPLE_COLUMNS = ["IMEI", "Serial Number", "Device Model", "SIM Module", "Firmware", "Slot ID",
                  "Primary Mobile Number", "Secondary Mobile Number", "ICCID", "Valid Till"]


def test_bulk_upload_sample_is_a_spreadsheet_with_the_documented_columns(oem_api) -> None:
    """Guide 6.1: each row carries IMEI, serial number, model, SIM module, firmware, ICCID, both mobile numbers and the SIM validity."""
    response = oem_api.get(f"{DEVICES}/bulk-upload/sample")

    assert response.status == 200 and XLSX in response.headers["content-type"]
    sheet = openpyxl.load_workbook(io.BytesIO(response.body())).active
    assert [cell.value for cell in sheet[1]] == SAMPLE_COLUMNS
    assert sheet.max_row >= 2, "The sample has no example row"


def test_bulk_upload_registers_every_valid_row(device_lab) -> None:
    rows = [bulk_row(device_lab.model, device_lab.firmware, device_lab.sim, slot=i) for i in (1, 2)]
    before = device_lab.devices_total()

    response = device_lab.oem.post(BULK_UPLOAD, json={"devices": rows})
    device_lab.adopt(*[r["imei"] for r in rows])

    assert response.status == 201, response.text()[:300]
    assert response.json()["data"]["total_uploaded"] == 2
    assert device_lab.devices_total() == before + 2
    stored = {d["imei"]: d for d in device_lab.oem.get(f"{DEVICES}?per_page=100").json()["data"]}
    assert all(stored[r["imei"]]["inventory_status"] == "available" for r in rows)


def test_one_bad_row_rejects_the_whole_upload(device_lab) -> None:
    good = bulk_row(device_lab.model, device_lab.firmware, device_lab.sim, slot=1)
    bad = bulk_row(device_lab.model, device_lab.firmware, device_lab.sim, slot=2, imei="12")
    before = device_lab.devices_total()

    response = device_lab.oem.post(BULK_UPLOAD, json={"devices": [good, bad]})
    device_lab.adopt(good["imei"])

    assert response.status == 422 and "devices.1.imei" in response.json()["errors"], response.text()[:300]
    assert device_lab.devices_total() == before, "The valid row was stored although another row failed"


def test_rows_repeating_an_imei_in_the_file_are_refused(device_lab) -> None:
    row = bulk_row(device_lab.model, device_lab.firmware, device_lab.sim)
    before = device_lab.devices_total()

    response = device_lab.oem.post(BULK_UPLOAD, json={"devices": [row, row]})
    device_lab.adopt(row["imei"])

    assert response.status == 422 and "devices.0.imei" in response.json()["errors"], response.text()[:300]
    assert device_lab.devices_total() == before


def test_empty_row_lists_every_required_column(oem_api) -> None:
    response = oem_api.post(BULK_UPLOAD, json={"devices": [{}]})

    required = {"imei", "serial_number", "device_model", "sim_module", "firmware", "slot_id",
                "primary_mobile_number", "secondary_mobile_number", "iccid"}
    assert response.status == 422
    assert {f"devices.0.{c}" for c in required} <= set(response.json()["errors"])


def test_unknown_master_data_name_returns_a_validation_report_and_stores_nothing(device_lab) -> None:
    """Guide 6.1: rows that fail the master-data check come back as a downloadable Excel validation report."""
    row = bulk_row(device_lab.model, device_lab.firmware, device_lab.sim, device_model="NO SUCH MODEL")
    before = device_lab.devices_total()

    response = device_lab.oem.post(BULK_UPLOAD, json={"devices": [row]})
    device_lab.adopt(row["imei"])

    assert response.status == 200
    assert XLSX in response.headers["content-type"], f"Expected an Excel report, got {response.headers['content-type']}"
    report = openpyxl.load_workbook(io.BytesIO(response.body())).active
    assert row["imei"] in " ".join(str(c.value) for r in report.iter_rows() for c in r), "The report does not list the failed row"
    assert device_lab.devices_total() == before


# ── OEM-B6: device list filters ───────────────────────────────────────────────

def test_device_list_filters_return_only_matching_devices(device_lab) -> None:
    device = device_lab.register()
    other_model, _ = device_lab.another_model_with_firmware()

    def ids(query: str) -> set[int]:
        return {d["id"] for d in device_lab.oem.get(f"{DEVICES}?per_page=100&{query}").json()["data"]}

    today = date.today().isoformat()
    assert device["id"] in ids(f"search={device['imei']}")
    assert ids("search=000000000000000") == set()
    assert device["id"] in ids(f"device_model_id={device_lab.model['id']}")
    assert device["id"] not in ids(f"device_model_id={other_model['id']}")
    assert device["id"] in ids("inventory_status=available")
    assert device["id"] not in ids("inventory_status=allocated")
    assert device["id"] in ids(f"date_from={today}&date_to={today}")
    assert device["id"] not in ids("date_from=2020-01-01&date_to=2020-01-02")
