"""
OEM Command Center - command templates (guide chapter 12).

  "The OEM defines the commands its device models understand (Command List): a label and the exact command text."

The tests create templates for the lab's Device Model and delete them again. The SOS-Clear flag is not covered: the
form's field could not be identified (plan question Q4).

OEM-D1, OEM-D2 of specs/oem-panel-test-plan.md.
"""

import pytest
from playwright.sync_api import Page

from pages.oem_panel.command_center import CommandListPage
from utils.oem_mgmt_api import OemMgmtApi
from utils.oem_panel_api import COMMAND_TEMPLATES

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

TEMPLATES = COMMAND_TEMPLATES


def _template(oem, template_id: int) -> dict | None:
    return next((t for t in oem.get(f"{TEMPLATES}?per_page=100").json()["data"] if t["id"] == template_id), None)


def test_template_can_be_created_edited_deactivated_and_deleted(template_lab, lab) -> None:
    created = template_lab(label="AUTO status", raw_command="STATUS#")
    assert created.status == 201, created.text()[:300]
    template_id = created.json()["data"]["id"]
    stored = _template(lab.oem, template_id)
    assert (stored["label"], stored["raw_command"], stored["is_active"], stored["device_model_id"]) == ("AUTO status", "STATUS#", True, lab.model["id"])

    edited = lab.oem.put(f"{TEMPLATES}/{template_id}", json={
        "device_model_id": lab.model["id"], "label": "AUTO status v2", "raw_command": "STATUS2#", "is_active": False,
    })
    assert edited.status == 200, edited.text()[:300]
    stored = _template(lab.oem, template_id)
    assert (stored["label"], stored["raw_command"], stored["is_active"]) == ("AUTO status v2", "STATUS2#", False)

    assert lab.oem.delete(f"{TEMPLATES}/{template_id}").status == 200
    assert _template(lab.oem, template_id) is None


def test_command_list_page_shows_the_template_and_counts_it(template_lab, lab, oem_page: Page) -> None:
    template_lab(label="AUTO shown", raw_command="LISTED#")
    inactive = template_lab(label="AUTO switched-off", raw_command="OFF#", is_active=False).json()["data"]["id"]
    lab.oem.put(f"{TEMPLATES}/{inactive}", json={"device_model_id": lab.model["id"], "label": "AUTO switched-off", "raw_command": "OFF#", "is_active": False})
    rows = lab.oem.get(f"{TEMPLATES}?per_page=100").json()["data"]

    page = CommandListPage(oem_page).open()

    page.expect_template("AUTO shown", "LISTED#")
    page.expect_counters(
        Total_Templates=len(rows),
        Active=sum(bool(t["is_active"]) for t in rows),
        Inactive=sum(not t["is_active"] for t in rows),
    )


@pytest.mark.parametrize(
    "fields, error_field",
    [
        ({"label": ""}, "label"),
        ({"raw_command": ""}, "raw_command"),
        ({"device_model_id": None}, "device_model_id"),
        ({"device_model_id": 999999}, "device_model_id"),
    ],
    ids=["no-label", "no-command", "no-model", "unknown-model"],
)
def test_invalid_template_is_refused(template_lab, lab, fields: dict, error_field: str) -> None:
    before = lab.oem.get(f"{TEMPLATES}?per_page=1").json()["meta"]["pagination"]["total"]

    response = template_lab(**fields)

    assert response.status == 422 and error_field in response.json()["errors"], f"{response.status} {response.text()[:300]}"
    assert lab.oem.get(f"{TEMPLATES}?per_page=1").json()["meta"]["pagination"]["total"] == before


def test_a_label_can_be_used_once_per_model(template_lab) -> None:
    assert template_lab(label="AUTO unique").status == 201

    again = template_lab(label="AUTO unique")

    assert again.status == 422 and "label" in again.json()["errors"], again.text()[:300]


def test_template_cannot_be_created_for_another_oems_model(template_lab, admin_api) -> None:
    other = OemMgmtApi(admin_api)  # the AUTO OEM, a different OEM
    try:
        foreign = other.create_model()

        response = template_lab(device_model_id=foreign["id"])

        assert response.status in (403, 422), f"A template was created for another OEM's model: {response.status}"
    finally:
        other.cleanup()
