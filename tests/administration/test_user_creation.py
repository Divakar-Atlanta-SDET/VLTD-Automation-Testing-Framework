"""
Happy-path creation tests for the User Management module (/tc/users/*).

Plan: specs/user-management-create-test-plan.md

  UM-01 Register an OEM            UM-04 Register a Driver
  UM-02 Register an RTO            UM-05 Register TC Staff
  UM-03 Create an Inspector        UM-06 Fitment Center / Permit Holder are read-only for Admin

Each test creates ONE uniquely-named record (prefix "AUTO", see utils/data_generator.py),
then finds it again through the list page search and checks the stored details and the
"Total" counter. Records cannot be deleted from the UI; the DB owner removes them.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.administration.driver_page import DriverPage
from pages.administration.inspector_page import InspectorPage
from pages.administration.oem_page import OemPage
from pages.administration.rto_page import RtoPage
from pages.administration.staff_page import StaffPage
from utils import data_generator as data
from utils.file_utils import create_test_png

pytestmark = [pytest.mark.user_management, pytest.mark.critical]


@pytest.mark.smoke
def test_register_oem(admin_page: Page) -> None:
    """UM-01: an OEM registered with valid data appears in the list as Active."""
    oem = data.oem_data()
    oem_page = OemPage(admin_page).open()
    total_before = oem_page.total()

    oem_page.open_create_form()
    oem_page.fill_form(oem)
    oem_page.submit_and_wait()

    oem_page.expect_in_list(
        oem.code,
        oem.business_name,
        f"Code: {oem.code}",
        oem.cin,
        oem.gst,
        oem.tac_number,
        oem.cop_number,
        oem.contact_name,
        oem.email,
        oem.mobile,
        oem.pincode,
        "Active",
    )
    assert OemPage(admin_page).open().total() >= total_before + 1


@pytest.mark.smoke
def test_register_rto(admin_page: Page) -> None:
    """UM-02: an RTO registered with valid data and a pinned location appears as Active."""
    rto_page = RtoPage(admin_page).open()
    rto = data.rto_data(rto_page.existing_codes())
    total_before = rto_page.total()

    rto_page.open_create_form()
    rto_page.fill_form(rto)
    rto_page.submit_and_wait()

    rto_page.expect_in_list(rto.code, rto.name, rto.email, rto.mobile, "Active")
    assert RtoPage(admin_page).open().total() >= total_before + 1


@pytest.mark.smoke
def test_create_inspector(admin_page: Page) -> None:
    """UM-03: an Inspector assigned to an RTO appears in the list as an active RTO Inspector."""
    inspector = data.inspector_data()
    inspector_page = InspectorPage(admin_page).open()
    total_before = inspector_page.total()

    inspector_page.open_create_form()
    city, rto = inspector_page.fill_form(inspector)
    inspector_page.submit_and_wait()

    rto_code = rto.split(" - ")[0]  # option reads "DL-04 - Delhi"; the list shows "DL-04 Delhi"
    inspector_page.expect_in_list(
        inspector.email,
        inspector.name,
        inspector.mobile,
        city,
        rto_code,
        "RTO Inspector",
        "Active",
    )
    assert InspectorPage(admin_page).open().total() >= total_before + 1


@pytest.mark.smoke
def test_register_driver(admin_page: Page, tmp_path) -> None:
    """UM-04: a Driver with licence and photo appears in the list as Active."""
    driver = data.driver_data()
    photo = create_test_png(tmp_path)
    driver_page = DriverPage(admin_page).open()
    total_before = driver_page.total()

    driver_page.open_create_form()
    city = driver_page.fill_form(driver, photo)
    driver_page.submit_and_wait()

    driver_page.expect_in_list(
        driver.licence_number,
        driver.name,
        driver.email,
        driver.mobile,
        city,
        "Active",
    )
    assert DriverPage(admin_page).open().total() >= total_before + 1


@pytest.mark.smoke
def test_register_tc_staff(admin_page: Page) -> None:
    """UM-05: TC Staff with one permission appears in the list (status shown as 'Approved')."""
    staff = data.staff_data()
    staff_page = StaffPage(admin_page).open()
    total_before = staff_page.total()

    staff_page.open_create_form()
    staff_page.expect_selected_count(0)
    staff_page.fill_form(staff)

    # Permission selection: select one, Clear All resets, select again
    staff_page.select_permission(staff.permission)
    staff_page.expect_selected_count(1)
    staff_page.clear_all_button.click()
    staff_page.expect_selected_count(0)
    staff_page.select_permission(staff.permission)
    staff_page.expect_selected_count(1)

    staff_page.submit_and_wait()

    staff_page.expect_in_list(staff.email, staff.name, "Approved")
    assert StaffPage(admin_page).open().total() >= total_before + 1


@pytest.mark.parametrize(
    "path, heading",
    [
        ("/tc/users/fc", "Fitment Center Management"),
        ("/tc/users/permit-holders", "Permit Holder Management"),
    ],
    ids=["fitment-center", "permit-holder"],
)
def test_admin_cannot_create_fitment_center_or_permit_holder(
    admin_page: Page, path: str, heading: str
) -> None:
    """UM-06: these lists are view-only for Admin – no Register/Add/Create action exists."""
    admin_page.goto(path)
    expect(admin_page.get_by_role("heading", name=heading, level=1)).to_be_visible(timeout=20_000)

    expect(admin_page.get_by_role("button", name=re.compile(r"^(Register|Add|Create|New)\b"))).to_have_count(0)
