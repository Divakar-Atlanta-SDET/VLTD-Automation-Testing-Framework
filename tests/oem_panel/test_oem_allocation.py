"""
OEM stock allocation and rollback (guide 6.1).

  The OEM allocates its own AVAILABLE devices to one of its ACTIVE fitment centres; the devices become "allocated".
  A device that is already allocated cannot be allocated again. Rollback returns allocated devices to the OEM's stock.

OEM-C1 .. OEM-C5 of specs/oem-panel-test-plan.md. Allocations are always rolled back by `device_lab`; the allocation
HISTORY rows (status "returned") stay, because the application cannot delete them.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.allocation import AllocateStockPage, AllocationHistoryPage, AllocationSuccessPage
from utils.oem_panel_api import ALLOCATIONS

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]


def _history(lab, **filters) -> list[dict]:
    query = "&".join(f"{k}={v}" for k, v in filters.items())
    return lab.oem.get(f"{ALLOCATIONS}?per_page=100&{query}").json()["data"]


# ── OEM-C1: allocating ────────────────────────────────────────────────────────

def test_allocation_moves_the_device_into_the_fitment_centres_stock(device_lab, active_fc) -> None:
    device = device_lab.register()
    stock, allocations = device_lab.totals(), device_lab.allocation_summary()

    response = device_lab.allocate(active_fc["id"], device)

    assert response.status == 201, response.text()[:300]
    allocation_id = response.json()["data"]["id"]
    assert device_lab.inventory_status(device) == "allocated"

    now = device_lab.totals()
    assert now["available_devices"] == stock["available_devices"] - 1
    assert now["allocated_devices"] == stock["allocated_devices"] + 1
    assert now["total_devices"] == stock["total_devices"]

    summary = device_lab.allocation_summary()
    assert summary["total_allocations"] == allocations["total_allocations"] + 1
    assert summary["active_allocations"] == allocations["active_allocations"] + 1
    assert summary["allocated_devices"] == allocations["allocated_devices"] + 1

    row = next(a for a in _history(device_lab) if a["id"] == allocation_id)
    assert row["status"] == "allocated" and row["fitment_centre"]["id"] == active_fc["id"]
    assert len(row["allocation_items"]) == 1


# ── OEM-C2: refusals leave everything as it was ───────────────────────────────

def test_a_device_cannot_be_allocated_twice(device_lab, active_fc) -> None:
    device = device_lab.register()
    assert device_lab.allocate(active_fc["id"], device).status == 201
    history = len(_history(device_lab))

    again = device_lab.allocate(active_fc["id"], device)

    assert again.status == 422 and "imeis" in again.json()["errors"], again.text()[:300]
    assert len(_history(device_lab)) == history
    assert device_lab.inventory_status(device) == "allocated"


def test_another_oems_device_cannot_be_allocated(device_lab, admin_api, active_fc) -> None:
    rows = admin_api.get("/api/tracking/devices/status-report?per_page=100").json()["data"]
    mine = {d["imei"] for d in device_lab.oem.get("/api/devices?per_page=100").json()["data"]}
    foreign = next((r["imei"] for r in rows if r["imei"] not in mine), None)
    if not foreign:
        pytest.skip("No device of another OEM exists")
    history = len(_history(device_lab))

    response = device_lab.oem.post(ALLOCATIONS, json={"fitment_centre_id": active_fc["id"], "imeis": [foreign]})

    assert response.status == 422, f"Another OEM's device was accepted: {response.status} {response.text()[:200]}"
    assert len(_history(device_lab)) == history


@pytest.mark.parametrize(
    "build, error_field",
    [
        (lambda fc, device: {"fitment_centre_id": fc, "imeis": ["000000000000000"]}, "imeis.0"),
        (lambda fc, device: {"fitment_centre_id": fc, "imeis": []}, "imeis"),
        (lambda fc, device: {"imeis": [device["imei"]]}, "fitment_centre_id"),
        (lambda fc, device: {"fitment_centre_id": 999999, "imeis": [device["imei"]]}, "fitment_centre_id"),
    ],
    ids=["unknown-imei", "no-devices", "no-fitment-centre", "unknown-fitment-centre"],
)
def test_incomplete_or_unknown_allocations_are_refused(device_lab, active_fc, build, error_field: str) -> None:
    device = device_lab.register()
    history = len(_history(device_lab))

    response = device_lab.oem.post(ALLOCATIONS, json=build(active_fc["id"], device))
    if response.status == 201:  # never leave a device allocated if the server wrongly accepts
        device_lab.track_allocation(response.json()["data"]["id"], device)

    assert response.status == 422 and error_field in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert len(_history(device_lab)) == history
    assert device_lab.inventory_status(device) == "available"


@pytest.mark.xfail(
    reason="BUG-041: the server allocates stock to a BLACKLISTED fitment centre; the guide allows active centres only",
    strict=False,
)
def test_stock_cannot_be_allocated_to_a_blacklisted_fitment_centre(device_lab, blacklisted_fc) -> None:
    device = device_lab.register()

    response = device_lab.allocate(blacklisted_fc["id"], device)

    assert response.status == 422, f"A blacklisted centre received stock: {response.status}"
    assert device_lab.inventory_status(device) == "available"


# ── OEM-C3: rollback ──────────────────────────────────────────────────────────

def test_rollback_returns_the_device_to_available_stock(device_lab, active_fc) -> None:
    device = device_lab.register()
    stock = device_lab.totals()
    allocation_id = device_lab.allocate(active_fc["id"], device).json()["data"]["id"]

    response = device_lab.rollback(allocation_id, device)

    assert response.status == 200, response.text()[:300]
    assert device_lab.inventory_status(device) == "available"
    assert device_lab.totals() == stock
    assert device_lab.allocation(allocation_id)["status"] == "returned"


def test_an_allocation_cannot_be_rolled_back_twice(device_lab, active_fc) -> None:
    device = device_lab.register()
    allocation_id = device_lab.allocate(active_fc["id"], device).json()["data"]["id"]
    assert device_lab.rollback(allocation_id, device).status == 200

    again = device_lab.rollback(allocation_id, device)

    assert again.status == 422, f"{again.status} {again.text()[:200]}"
    assert device_lab.inventory_status(device) == "available"


def test_returned_device_can_be_allocated_again(device_lab, active_fc) -> None:
    device = device_lab.register()
    first = device_lab.allocate(active_fc["id"], device).json()["data"]["id"]
    device_lab.rollback(first, device)

    second = device_lab.allocate(active_fc["id"], device)

    assert second.status == 201, second.text()[:300]
    assert device_lab.inventory_status(device) == "allocated"


# ── OEM-C5: history filters ───────────────────────────────────────────────────

def test_history_filters_return_only_matching_allocations(device_lab, active_fc) -> None:
    device = device_lab.register()
    allocation_id = device_lab.allocate(active_fc["id"], device).json()["data"]["id"]

    assert allocation_id in {a["id"] for a in _history(device_lab, status="allocated")}
    assert allocation_id not in {a["id"] for a in _history(device_lab, status="returned")}
    assert allocation_id in {a["id"] for a in _history(device_lab, fitment_centre_id=active_fc["id"])}
    assert all(a["status"] == "returned" for a in _history(device_lab, status="returned"))

    device_lab.rollback(allocation_id, device)
    assert allocation_id in {a["id"] for a in _history(device_lab, status="returned")}


# ── OEM-C4: the Allocate Stock wizard and the history page ────────────────────

def test_wizard_allocates_available_stock_and_history_can_roll_it_back(device_lab, oem_page: Page, active_fc, blacklisted_fc, district_of) -> None:
    free = device_lab.register()
    taken = device_lab.register()
    taken_allocation = device_lab.allocate(active_fc["id"], taken).json()["data"]["id"]

    wizard = AllocateStockPage(oem_page).open()
    wizard.select_district(district_of(active_fc))
    wizard.expect_fitment_centre(active_fc["business_name"])
    wizard.expect_no_fitment_centre(blacklisted_fc["business_name"])  # only ACTIVE centres are offered
    wizard.select_fitment_centre(active_fc["business_name"])
    wizard.continue_to_devices()

    expect(wizard.device_row(free["imei"])).to_have_count(1)
    expect(wizard.device_row(taken["imei"])).to_have_count(0)  # already allocated stock is not offered
    wizard.select_device(free["imei"])
    wizard.allocate()

    allocation_id = AllocationSuccessPage(oem_page).allocation_id()
    device_lab.track_allocation(allocation_id, free)
    assert device_lab.inventory_status(free) == "allocated"

    assert device_lab.rollback(taken_allocation, taken).status == 200  # leave only the wizard's allocation "Allocated"

    history = AllocationHistoryPage(oem_page).open()
    row = history.row_with(active_fc["business_name"], "Allocated").first
    expect(row).to_be_visible()
    history.filter_status("Allocated")
    history.rollback(history.row_with(active_fc["business_name"], "Allocated").first)

    expect(oem_page.get_by_text(re.compile(r"rolled back|returned to inventory", re.I)).first).to_be_visible()
    assert device_lab.inventory_status(free) == "available"
    assert device_lab.allocation(allocation_id)["status"] == "returned"
