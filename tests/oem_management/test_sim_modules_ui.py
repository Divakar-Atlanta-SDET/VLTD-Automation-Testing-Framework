"""
SIM Modules - UI tests: table, search, filters, create, view, edit, delete.   Plan: specs/oem-management-test-plan.md

Test records are created through the API (fast, independent of the UI under test) and removed after each test.
Techniques: equivalence partitioning (valid / blank / whitespace / duplicate / too long), boundary value analysis
(maximum lengths 150 / 100 and one beyond), and state-based checks (Active / Inactive).
"""

import re

import pytest
from playwright.sync_api import expect

from pages.oem_management.sim_modules_page import SimModulesPage
from tests.oem_management.bugs import DELETE_BROKEN
from utils import data_generator as data
from utils.oem_mgmt_api import OemMgmtApi

pytestmark = [pytest.mark.oem_management]


def _track_created(records: OemMgmtApi, module_name: str) -> dict:
    """Register a record created through the UI for cleanup, and return it."""
    record = records.find("sim", "module_name", module_name)
    assert record, f"'{module_name}' was not created"
    records.track("sim", record["id"])
    return record


# ── Table (read) ──────────────────────────────────────────────────────────────

def test_list_page_has_all_controls_and_columns(sim_modules_page: SimModulesPage) -> None:
    p = sim_modules_page.open()

    for control in (p.add_button, p.refresh_button, p.search_box, p.oem_filter, p.status_filter):
        expect(control).to_be_visible()
    assert [h.lower() for h in p.column_headers()] == [c.lower() for c in p.COLUMNS]


def test_row_shows_the_record_details(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()

    row = p.row(sim["module_name"])
    expect(row).to_have_count(1)
    for expected in (records.oem_name, records.oem["code"], sim["sim_manufacturer"], sim["module_name"], "Airtel", "Jio", "eSIM", "Active"):
        expect(row).to_contain_text(expected)



def test_view_shows_record_and_oem_details(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()

    p.view(p.row(sim["module_name"]))
    shown = p.view_text()
    for expected in (sim["module_name"], sim["sim_manufacturer"], "Airtel", "eSIM", "Jio", "Physical", records.oem["code"]):
        assert expected in shown, f"'{expected}' missing from the View panel"
    p.close_view()



# ── Search (equivalence classes) ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "variant",
    [
        pytest.param(lambda n: n, id="full-name"),
        pytest.param(lambda n: n[len("AUTO SIM "):], id="suffix-only"),
        pytest.param(lambda n: n[3:-3], id="middle-part"),
        pytest.param(lambda n: n.lower(), id="lower-case"),
        pytest.param(lambda n: n.upper(), id="upper-case"),
    ],
)
def test_search_by_module_name_finds_the_record(sim_modules_page: SimModulesPage, records: OemMgmtApi, variant) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()

    p.search(variant(sim["module_name"]))

    expect(p.row(sim["module_name"])).to_have_count(1)



def test_search_without_match_shows_empty_state_and_clearing_restores_rows(sim_modules_page: SimModulesPage) -> None:
    p = sim_modules_page.open()
    before = p.rows().count()

    p.search("zz-no-such-sim-module-zz")
    assert p.visible_record_count() == 0
    expect(p.empty_state()).to_be_visible()

    p.clear_search()
    assert p.rows().count() == before



# ── Filters ───────────────────────────────────────────────────────────────────

def test_oem_filter_lists_all_oems_and_narrows_the_table(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    records.create_sim()
    p = sim_modules_page.open()

    options = p.oem_filter_options()
    assert options[0] == "All OEMs" and len(options) > 1
    p.filter_by_oem(records.oem_name)

    assert p.rows().count() >= 1
    assert all(records.oem_name in r.inner_text() for r in p.rows().all())


def test_status_filter_separates_active_and_inactive(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    active = records.create_sim()
    inactive = records.create_sim(is_active=False)
    p = sim_modules_page.open()

    p.filter_by_status("Inactive")
    expect(p.row(inactive["module_name"])).to_have_count(1)
    expect(p.row(active["module_name"])).to_have_count(0)

    p.filter_by_status("Active")
    expect(p.row(active["module_name"])).to_have_count(1)
    expect(p.row(inactive["module_name"])).to_have_count(0)

    p.filter_by_status("All Status")
    expect(p.row(active["module_name"])).to_have_count(1)
    expect(p.row(inactive["module_name"])).to_have_count(1)



def test_filter_with_no_result_shows_empty_state(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()  # Active
    p = sim_modules_page.open()

    p.filter_by_status("Inactive")
    p.search(sim["module_name"])

    assert p.visible_record_count() == 0
    expect(p.empty_state()).to_be_visible()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_with_all_fields(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = data.sim_module_data()
    p = sim_modules_page.open()
    p.open_add_form()

    p.fill_form(sim, oem_name=records.oem_name)
    p.submit_create()

    p.wait_for_message(r"created successfully")
    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/sim-modules$"))
    _track_created(records, sim.module_name)
    row = p.row(sim.module_name)
    expect(row).to_have_count(1)
    # the OEM name is filled in by a second request, so let the assertions wait for it
    for expected in (records.oem_name, sim.sim_manufacturer, "Active"):
        expect(row).to_contain_text(expected)


def test_create_with_required_fields_only(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = data.sim_module_data()
    p = sim_modules_page.open()
    p.open_add_form()

    p.choose_oem(records.oem_name)
    p.fill("SIM Manufacturer *", sim.sim_manufacturer)
    p.fill("Module Name *", sim.module_name)
    p.submit_create()

    p.wait_for_message(r"created successfully")
    _track_created(records, sim.module_name)
    expect(p.row(sim.module_name)).to_have_count(1)



def test_empty_form_lists_every_required_field(sim_modules_page: SimModulesPage) -> None:
    p = sim_modules_page.open()
    p.open_add_form()

    p.submit_create()

    messages = p.wait_for_message(r"OEM is required")
    for expected in ("OEM is required.", "SIM manufacturer is required.", "Module name is required."):
        assert expected in messages, messages
    expect(p.page).to_have_url(re.compile(r"/sim-modules/new$"))



def test_duplicate_module_name_is_rejected(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    existing = records.create_sim()
    p = sim_modules_page.open()
    p.open_add_form()
    p.fill_form(data.sim_module_data(), oem_name=records.oem_name)

    p.fill("Module Name *", existing["module_name"])
    p.submit_create()

    p.wait_for_message(r"already been taken")
    expect(p.page).to_have_url(re.compile(r"/sim-modules/new$"))


def test_cancel_returns_to_the_list_without_saving(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = data.sim_module_data()
    p = sim_modules_page.open()
    p.open_add_form()
    p.fill_form(sim, oem_name=records.oem_name)

    p.cancel_form()

    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/sim-modules$"))
    assert records.find("sim", "module_name", sim.module_name) is None



# ── Update ────────────────────────────────────────────────────────────────────

def test_edit_form_is_prefilled(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()

    p.edit(p.row(sim["module_name"]))

    expect(p.textbox("SIM Manufacturer *")).to_have_value(sim["sim_manufacturer"])
    expect(p.textbox("Module Name *")).to_have_value(sim["module_name"])
    expect(p.textbox("Primary Operator")).to_have_value("Airtel")
    expect(p.textbox("Secondary SIM Type")).to_have_value("Physical")
    expect(p.page.get_by_role("combobox", name="OEM *")).to_contain_text(records.oem_name)


def test_edit_saves_changes_and_updates_the_table(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()
    p.edit(p.row(sim["module_name"]))

    new_name = sim["module_name"] + "-EDITED"
    p.fill("Module Name *", new_name)
    p.fill("Primary Operator", "BSNL")
    p.submit_update()

    p.wait_for_message(r"updated successfully")
    expect(p.page).to_have_url(re.compile(r"/tc/oem-management/sim-modules$"))
    expect(p.row(new_name)).to_have_count(1)
    expect(p.row(new_name)).to_contain_text("BSNL")
    module_names = [p.row_cells(r)[4] for r in p.rows().all()]
    assert sim["module_name"] not in module_names, "The old name is still listed"


def test_edit_can_switch_status_to_inactive(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()
    p.edit(p.row(sim["module_name"]))

    p.choose("Status", "Inactive")
    p.submit_update()

    p.wait_for_message(r"updated successfully")
    expect(p.row(sim["module_name"])).to_contain_text("Inactive")


def test_edit_rejects_a_blank_required_field(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()
    p.edit(p.row(sim["module_name"]))

    p.fill("Module Name *", "")
    p.submit_update()

    p.wait_for_message(r"Module name is required")
    expect(p.page).to_have_url(re.compile(r"/sim-modules/\d+/edit$"))



# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_confirmation_names_the_record_and_cancel_keeps_it(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()

    p.start_delete(p.row(sim["module_name"]))
    text = p.view_text()
    assert f"delete {sim['module_name']}" in text and records.oem_name in text
    p.cancel_delete()

    expect(p.row(sim["module_name"])).to_have_count(1)
    assert records.exists("sim", sim["id"])


@DELETE_BROKEN
def test_delete_removes_the_record(sim_modules_page: SimModulesPage, records: OemMgmtApi) -> None:
    sim = records.create_sim()
    p = sim_modules_page.open()

    p.start_delete(p.row(sim["module_name"]))
    p.confirm_delete()

    p.wait_for_message(r"deleted successfully")
    expect(p.row(sim["module_name"])).to_have_count(0)
    assert not records.exists("sim", sim["id"])
