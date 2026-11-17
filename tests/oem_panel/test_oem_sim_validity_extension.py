"""
OEM SIM Validity Extension (guide 6.5).

  "Only for the OEM's own devices that are installed on a vehicle ... and only for an active SIM still assigned."
  The OEM account has no installed device, so the happy path and the 2 y / 1 y limit stay manual; what can be proven is
  that the extension is refused for a device that is NOT installed, that other OEMs' devices cannot be looked up, and how
  the search behaves.

OEM-G1 of specs/oem-panel-test-plan.md.
"""

import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.misc import SimValidityPage

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

NOT_FOUND = "No device found for this IMEI."


def test_fetch_is_only_possible_for_a_complete_imei(oem_page: Page) -> None:
    page = SimValidityPage(oem_page).open()

    page.imei_box.fill("12345678901234")
    expect(page.fetch_button).to_be_disabled()
    page.imei_box.fill("123456789012345")
    expect(page.fetch_button).to_be_enabled()


def test_unknown_imei_is_reported_as_not_found(oem_page: Page) -> None:
    page = SimValidityPage(oem_page).open()

    page.fetch("000000000000000")

    expect(oem_page.get_by_role("alert").filter(has_text=NOT_FOUND)).to_be_visible()


def test_another_oems_device_cannot_be_looked_up(admin_api, oem_api, oem_page: Page) -> None:
    mine = {d["imei"] for d in oem_api.get("/api/devices?per_page=100").json()["data"]}
    foreign = next((r["imei"] for r in admin_api.get("/api/tracking/devices/status-report?per_page=100").json()["data"] if r["imei"] not in mine), None)
    if not foreign:
        pytest.skip("No device of another OEM exists")
    page = SimValidityPage(oem_page).open()

    page.fetch(foreign)

    expect(oem_page.get_by_role("alert").filter(has_text=NOT_FOUND)).to_be_visible()
    expect(oem_page.get_by_text("Device Verification Completed")).to_have_count(0)  # no device details are shown


def _sim_of(device_lab, device: dict) -> dict:
    sims = device_lab.oem.get("/api/device-sims?per_page=100").json()["data"]
    return next(s for s in sims if device["imei"] in str(s) or s.get("iccid") == "8991" + device["imei"] + "0")


def test_extension_is_refused_for_a_device_that_is_not_installed(device_lab) -> None:
    current = (date.today() + timedelta(days=100)).isoformat()
    device = device_lab.register(valid_till=current)
    sim = _sim_of(device_lab, device)

    response = device_lab.oem.patch(f"/api/device-sims/{sim['id']}/validity", json={"valid_till": (date.today() + timedelta(days=200)).isoformat()})

    assert response.status == 422 and "installed" in str(response.json()["errors"]), response.text()[:300]
    assert _sim_of(device_lab, device)["valid_till"][:10] == current, "The SIM validity changed although the extension was refused"


@pytest.mark.xfail(
    reason="BUG-043: the page marks the SIM 'Eligible' and offers 'Extend Validity' for a device that is not installed; "
    "the server then refuses with a generic 'Validation failed.'",
    strict=False,
)
def test_extension_is_not_offered_for_a_device_that_is_not_installed(device_lab, oem_page: Page) -> None:
    device = device_lab.register(valid_till=(date.today() + timedelta(days=100)).isoformat())
    page = SimValidityPage(oem_page).open()

    page.fetch(device["imei"])

    expect(oem_page.get_by_text("Device Verification Completed")).to_be_visible()
    expect(oem_page.get_by_text(re.compile(r"^\s*Eligible\s*$"))).to_have_count(0)
    expect(oem_page.get_by_role("button", name="Extend Validity", exact=True)).to_have_count(0)
