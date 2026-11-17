"""
Device Models - UI tests: table, search, filters, create, view, edit, download, delete.
Plan: specs/oem-management-test-plan.md

Techniques: equivalence partitioning (valid / blank / whitespace / duplicate / wrong type), boundary value
analysis (field maximums, today's date for the TAC issue date, the 2 MB certificate limit) and state-based
checks (Active / Inactive). Records are created through the API and removed after each test.
"""

import re

import pytest
from playwright.sync_api import expect

from pages.oem_management.device_models_page import DeviceModelsPage
from tests.oem_management.bugs import DELETE_BROKEN, INACTIVE_OEM_ACCEPTED, MODEL_UPDATE_BROKEN, OEM_DROPDOWN_CAPPED
from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.file_utils import TEST_PDF, create_text_file
from utils.oem_mgmt_api import OemMgmtApi

pytestmark = [pytest.mark.oem_management]

NEW_URL = re.compile(r"/device-models/new$")


def _track_created(records: OemMgmtApi, model_name: str) -> dict:
    record = records.find("model", "model_name", model_name)
    assert record, f"'{model_name}' was not created"
    records.track("model", record["id"])
    return record


def _open_filled_form(page: DeviceModelsPage, records: OemMgmtApi, model: data.DeviceModelData | None = None, **kwargs):
    model = model or data.device_model_data()
    page.open()
    page.open_add_form()
    page.fill_form(model, oem_name=records.oem_name, **kwargs)
    return model


# ── Table (read) ──────────────────────────────────────────────────────────────

def test_list_page_has_all_controls_and_columns(device_models_page: DeviceModelsPage) -> None:
    p = device_models_page.open()

    for control in (p.add_button, p.refresh_button, p.search_box, p.oem_filter, p.status_filter):
        expect(control).to_be_visible()
    assert [h.lower() for h in p.column_headers()] == [c.lower() for c in p.COLUMNS]


def test_row_shows_the_record_details(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()

    row = p.row(model["model_name"])
    expect(row).to_have_count(1)
    for expected in (records.oem_name, records.oem["code"], model["model_name"], model["part_no"], model["tac_name"], "AUTO-4G", "Active"):
        expect(row).to_contain_text(expected)



def test_view_shows_oem_model_and_tac_details(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()

    p.view(p.row(model["model_name"]))
    shown = p.view_text()
    for expected in (model["model_name"], model["part_no"], model["tac_name"], "15 Jan 2026", "AUTO-4G", records.oem["code"], "Created by automation"):
        assert expected in shown, f"'{expected}' missing from the View panel"
    p.close_view()


def test_download_tac_certificate_returns_the_uploaded_pdf(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()

    p.open_menu(p.row(model["model_name"]))
    with p.page.expect_download(timeout=20_000) as download:
        p.page.get_by_role("menuitem", name=re.compile("Download TAC")).click()

    path = download.value.path()
    assert download.value.suggested_filename.lower().endswith(".pdf")
    assert open(path, "rb").read(5) == b"%PDF-"


# ── Search ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "variant",
    [
        pytest.param(lambda n: n, id="full-name"),
        pytest.param(lambda n: n[len("AUTO DM "):], id="suffix-only"),
        pytest.param(lambda n: n[3:-3], id="middle-part"),
        pytest.param(lambda n: n.lower(), id="lower-case"),
        pytest.param(lambda n: n.upper(), id="upper-case"),
    ],
)
def test_search_by_model_name_finds_the_record(device_models_page: DeviceModelsPage, records: OemMgmtApi, variant) -> None:
    model = records.create_model()
    p = device_models_page.open()

    p.search(variant(model["model_name"]))

    expect(p.row(model["model_name"])).to_have_count(1)



def test_search_without_match_shows_empty_state_and_clearing_restores_rows(device_models_page: DeviceModelsPage) -> None:
    p = device_models_page.open()
    before = p.rows().count()

    p.search("zz-no-such-model-zz")
    assert p.visible_record_count() == 0
    expect(p.empty_state()).to_be_visible()

    p.clear_search()
    assert p.rows().count() == before



# ── Filters ───────────────────────────────────────────────────────────────────

def test_oem_filter_lists_all_oems_and_narrows_the_table(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    records.create_model()
    p = device_models_page.open()

    options = p.oem_filter_options()
    assert options[0] == "All OEMs" and len(options) > 1
    p.filter_by_oem(records.oem_name)

    assert p.rows().count() >= 1
    assert all(records.oem_name in r.inner_text() for r in p.rows().all())


def test_status_filter_separates_active_and_inactive(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    active = records.create_model()
    inactive = records.create_model(is_active="0")
    p = device_models_page.open()

    p.filter_by_status("Inactive")
    expect(p.row(inactive["model_name"])).to_have_count(1)
    expect(p.row(active["model_name"])).to_have_count(0)

    p.filter_by_status("Active")
    expect(p.row(active["model_name"])).to_have_count(1)
    expect(p.row(inactive["model_name"])).to_have_count(0)

    p.filter_by_status("All Status")
    expect(p.row(active["model_name"])).to_have_count(1)
    expect(p.row(inactive["model_name"])).to_have_count(1)



def test_filter_with_no_result_shows_empty_state(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()  # Active
    p = device_models_page.open()

    p.filter_by_status("Inactive")
    p.search(model["model_name"])

    assert p.visible_record_count() == 0
    expect(p.empty_state()).to_be_visible()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_with_all_required_fields(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    p = device_models_page
    model = _open_filled_form(p, records)

    p.submit_create()

    p.wait_for_message(r"created successfully")
    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/device-models$"))
    created = _track_created(records, model.model_name)
    assert created["part_no"] == model.part_no and created["has_tac_certificate"] is True
    expect(p.row(model.model_name)).to_have_count(1)


def test_create_with_cop_details(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    """COP number, both dates and the certificate must be supplied together."""
    p = device_models_page
    model = _open_filled_form(p, records)
    p.fill("COP Number", f"COP{data.unique_suffix()}")
    p.fill("COP Valid From", "2026-01-01")
    p.fill("COP Valid Till", "2026-12-31")
    p.page.locator("input[type=file]").nth(1).set_input_files(str(TEST_PDF))

    p.submit_create()

    p.wait_for_message(r"created successfully")
    created = _track_created(records, model.model_name)
    assert created["has_cop_certificate"] is True and created["cop_valid_from"].startswith("2026-01-01")


@INACTIVE_OEM_ACCEPTED
@pytest.mark.parametrize("status", ["suspended", "blacklisted"])
def test_a_device_model_is_not_created_for_a_suspended_or_blacklisted_oem(device_models_page: DeviceModelsPage, oem_admin: ApiClient, status: str) -> None:
    """The OEM is picked from the dropdown, so only OEMs the form actually offers are used."""
    offered = oem_admin.list_items(f"{API_PREFIX}/oems?per_page=100")
    owner = next((o for o in offered if o["status"] == status), None)
    if owner is None:
        pytest.skip(f"no {status} OEM among the OEMs the form offers")
    helper = OemMgmtApi(oem_admin, owner)
    model = data.device_model_data()
    try:
        p = device_models_page.open()
        p.open_add_form()
        p.fill_form(model, oem_name=owner["business_name"])

        with p.page.expect_response(lambda r: r.url.endswith("/api/device-models") and r.request.method == "POST") as sent:
            p.submit_create()

        if sent.value.status == 201:
            helper.track("model", sent.value.json()["data"]["id"])
        assert sent.value.status != 201, f"A {status} OEM received a new device model: {sent.value.status}"
    finally:
        helper.cleanup()


@INACTIVE_OEM_ACCEPTED
def test_the_oem_dropdown_does_not_offer_suspended_or_blacklisted_oems(device_models_page: DeviceModelsPage, oem_admin: ApiClient) -> None:
    """Product owner (2026-10-31): such OEMs must not be shown in the Device Model form's OEM dropdown."""
    loaded = oem_admin.list_items(f"{API_PREFIX}/oems?per_page=100")  # the 100 the form loads (BUG-046)
    active = {o["business_name"] for o in loaded if o["status"] == "active"}
    inactive = {o["business_name"] for o in loaded if o["status"] != "active"} - active
    p = device_models_page.open()
    p.open_add_form()

    offered = p.oem_choices()

    shown = sorted(name for name in inactive if any(name in option for option in offered))
    assert not shown, f"The dropdown offers {len(shown)} suspended / blacklisted OEMs, for example {shown[:3]}"


@OEM_DROPDOWN_CAPPED
def test_oem_dropdown_offers_every_oem(device_models_page: DeviceModelsPage, oem_admin: ApiClient) -> None:
    total = len(oem_admin.all_items(f"{API_PREFIX}/oems"))
    p = device_models_page.open()
    p.open_add_form()

    offered = p.oem_choices()

    assert len(offered) == total, f"The dropdown offers {len(offered)} of {total} OEMs"


def test_empty_form_lists_every_required_field(device_models_page: DeviceModelsPage) -> None:
    p = device_models_page.open()
    p.open_add_form()

    p.submit_create()

    messages = p.wait_for_message(r"OEM is required")
    for expected in ("OEM is required.", "Model name is required.", "Part number is required.", "TAC number is required.", "TAC issue date is required."):
        assert expected in messages, messages
    expect(p.page).to_have_url(NEW_URL)
    expect(p.page.get_by_text("TAC certificate is required.")).to_be_visible()



def test_certificate_must_be_a_real_file_type(device_models_page: DeviceModelsPage, records: OemMgmtApi, tmp_path) -> None:
    """EP: a text file is refused (the server accepts PDF only)."""
    p = device_models_page
    _open_filled_form(p, records, certificate=None)
    p.page.locator("input[type=file]").first.set_input_files(str(create_text_file(tmp_path)))

    p.submit_create()

    p.wait_for_message(r"must be a file of type")
    expect(p.page).to_have_url(NEW_URL)



def test_cop_number_without_the_other_cop_details_is_rejected(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    p = device_models_page
    _open_filled_form(p, records)
    p.fill("COP Number", "COP-ONLY")

    p.submit_create()

    messages = p.wait_for_message(r"COP valid from date is required")
    for expected in ("COP valid from date is required.", "COP valid till date is required."):
        assert expected in messages, messages
    assert any("COP certificate" in m for m in messages), messages
    expect(p.page).to_have_url(NEW_URL)



def test_duplicate_model_name_is_rejected(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    existing = records.create_model()
    p = device_models_page
    _open_filled_form(p, records)
    p.fill("Model Name *", existing["model_name"])

    p.submit_create()

    p.wait_for_message(r"already been taken")
    expect(p.page).to_have_url(NEW_URL)


def test_cancel_returns_to_the_list_without_saving(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    p = device_models_page
    model = _open_filled_form(p, records)

    p.cancel_form()

    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/device-models$"))
    assert records.find("model", "model_name", model.model_name) is None



# ── Update ────────────────────────────────────────────────────────────────────

def test_edit_form_is_prefilled(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()

    p.edit(p.row(model["model_name"]))

    expect(p.textbox("Model Name *")).to_have_value(model["model_name"])
    expect(p.textbox("Part Number *")).to_have_value(model["part_no"])
    expect(p.textbox("TAC Number *")).to_have_value(model["tac_name"])
    expect(p.textbox("TAC Issued On *")).to_have_value("2026-01-15")
    expect(p.page.get_by_role("combobox", name="OEM *")).to_contain_text(records.oem_name)
    expect(p.page.get_by_text("Existing TAC certificate")).to_be_visible()


@MODEL_UPDATE_BROKEN
def test_edit_saves_changes_and_updates_the_table(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()
    p.edit(p.row(model["model_name"]))

    new_name = model["model_name"] + "-EDITED"
    p.fill("Model Name *", new_name)
    p.submit_update()

    p.wait_for_message(r"updated successfully")
    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/device-models$"))
    expect(p.row(new_name)).to_have_count(1)



# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_confirmation_names_the_record_and_cancel_keeps_it(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()

    p.start_delete(p.row(model["model_name"]))
    text = p.view_text()
    assert f"delete {model['model_name']}" in text and records.oem_name in text
    p.cancel_delete()

    expect(p.row(model["model_name"])).to_have_count(1)
    assert records.exists("model", model["id"])


@DELETE_BROKEN
def test_delete_removes_the_record(device_models_page: DeviceModelsPage, records: OemMgmtApi) -> None:
    model = records.create_model()
    p = device_models_page.open()

    p.start_delete(p.row(model["model_name"]))
    p.confirm_delete()

    p.wait_for_message(r"deleted successfully")
    expect(p.row(model["model_name"])).to_have_count(0)
    assert not records.exists("model", model["id"])
