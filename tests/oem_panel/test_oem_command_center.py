"""
OEM Command Center (guide chapter 12), tested through the screens an OEM user works with.

  "The OEM defines the commands its device models understand (Command List): a label and the exact command text. One of
   them can be marked SOS Clear ... A user with access searches a vehicle (by number or IMEI), picks a command and clicks
   Send Command. The command history shows its status."

  Command List     Add / Edit / Delete form: required fields, boundaries, one SOS Clear per model, deactivate, confirm delete
  Send Command     device search, which commands are offered, what is sent, nothing is sent without a command
  Command History  counters, filters and rows (the service answer is mocked, so no real command is queued), isolation

Sending a command queues a row in the shared command history that cannot be removed, so the send request is answered
by a mock in every test below; only the refusal of an unregistered device is checked against the real service.
Templates made through the form are removed afterwards (also when a test fails).
"""

import json
import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.command_center import CommandHistoryPage, CommandListPage, CommandSendPage
from utils.api_client import ApiClient
from utils.oem_panel_api import COMMAND_TEMPLATES, COMMANDS, GO_ORIGIN, unique_imei

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

CREATED = "Command template created successfully."
TAKEN = re.compile(r"already been taken", re.I)


@pytest.fixture
def ui_templates(lab):
    """Removes every 'AUTO ui' template of the lab's model afterwards, whatever the test created through the form."""
    yield
    for template in lab.oem.get(f"{COMMAND_TEMPLATES}?per_page=100").json()["data"]:
        if template["label"].startswith("AUTO ui") and template["device_model_id"] == lab.model["id"]:
            lab.oem.delete(f"{COMMAND_TEMPLATES}/{template['id']}")


def _stored(oem: ApiClient, label: str) -> dict | None:
    return next((t for t in oem.get(f"{COMMAND_TEMPLATES}?per_page=100").json()["data"] if t["label"] == label), None)


def _total(oem: ApiClient) -> int:
    return oem.get(f"{COMMAND_TEMPLATES}?per_page=1").json()["meta"]["pagination"]["total"]


# ── Command List: the form ────────────────────────────────────────────────────

def test_the_form_asks_for_model_label_and_command(oem_page: Page, lab, ui_templates) -> None:
    page = CommandListPage(oem_page).open()
    before = _total(lab.oem)
    page.start_add()

    page.submit()

    for message in ("Device model is required", "Label is required", "Raw command text is required"):
        expect(oem_page.get_by_text(message)).to_be_visible()
    assert _total(lab.oem) == before


@pytest.mark.parametrize("field", ["label", "command"])
def test_a_blank_label_or_command_is_not_accepted(oem_page: Page, lab, ui_templates, field: str) -> None:
    page = CommandListPage(oem_page).open()
    page.start_add()
    page.fill_form("   " if field == "label" else "AUTO ui blank", "STATUS#" if field == "label" else "     ", model_name=lab.model["model_name"])

    page.submit()

    expect(oem_page.get_by_text("Label is required" if field == "label" else "Raw command text is required")).to_be_visible()
    assert _stored(lab.oem, "AUTO ui blank") is None


def test_a_command_created_in_the_form_is_saved_and_listed(oem_page: Page, lab, ui_templates) -> None:
    page = CommandListPage(oem_page).open()
    page.start_add()
    page.fill_form("AUTO ui status", "STATUS#", model_name=lab.model["model_name"], description="asks the device for its status")

    page.submit()

    page.expect_message(CREATED)
    stored = _stored(lab.oem, "AUTO ui status")
    assert (stored["raw_command"], stored["description"], stored["is_active"], stored["device_model_id"]) == (
        "STATUS#", "asks the device for its status", True, lab.model["id"])
    assert stored["purpose"] != "sos_clear"
    rows = lab.oem.get(f"{COMMAND_TEMPLATES}?per_page=100").json()["data"]
    page.expect_template("AUTO ui status", "STATUS#")
    page.expect_counters(
        Total_Templates=len(rows), Active=sum(bool(t["is_active"]) for t in rows), Inactive=sum(not t["is_active"] for t in rows),
    )


def test_the_form_limits_label_and_command_length(oem_page: Page) -> None:
    page = CommandListPage(oem_page).open()
    page.start_add()

    expect(page.label_box).to_have_attribute("maxlength", "150")
    expect(page.raw_box).to_have_attribute("maxlength", "2000")


@pytest.mark.parametrize(
    "fields, accepted",
    [
        ({"label": "AUTO ui " + "l" * 142}, True), ({"label": "AUTO ui " + "l" * 143}, False),
        ({"raw_command": "R" * 2000}, True), ({"raw_command": "R" * 2001}, False),
    ],
    ids=["label-150", "label-151", "command-2000", "command-2001"],
)
def test_server_enforces_the_label_and_command_limits(template_lab, fields: dict, accepted: bool) -> None:
    """The form stops typing at the limits, so the server's own limit is checked directly."""
    fields = {"label": f"AUTO ui limit {len(str(fields))}", **fields}

    response = template_lab(**fields)

    assert response.status == (201 if accepted else 422), f"{response.status} {response.text()[:200]}"


def test_a_command_text_with_markup_is_listed_as_plain_text(oem_page: Page, template_lab) -> None:
    template_lab(label="AUTO ui markup", raw_command="<b>BOLD</b>#")

    page = CommandListPage(oem_page).open()

    expect(page.row("AUTO ui markup")).to_contain_text("<b>BOLD</b>#")


# ── Command List: SOS Clear ───────────────────────────────────────────────────

def test_only_one_sos_clear_command_is_allowed_per_model(oem_page: Page, lab, ui_templates) -> None:
    """Guide 10 / 12 and the form: 'Only one SOS Clear command per device model.'"""
    page = CommandListPage(oem_page).open()
    page.start_add()
    page.fill_form("AUTO ui sos", "SOSCLEAR#", model_name=lab.model["model_name"], sos_clear=True)
    page.submit()
    page.expect_message(CREATED)
    assert _stored(lab.oem, "AUTO ui sos")["purpose"] == "sos_clear"
    expect(page.row("AUTO ui sos")).to_contain_text("SOS Clear")

    page.start_add()
    page.fill_form("AUTO ui sos two", "SOSCLEAR2#", model_name=lab.model["model_name"], sos_clear=True)
    page.submit()

    page.expect_message(TAKEN)
    assert _stored(lab.oem, "AUTO ui sos two") is None


def test_a_command_cannot_be_changed_into_a_second_sos_clear(oem_page: Page, lab, template_lab, ui_templates) -> None:
    assert template_lab(label="AUTO ui sos first", raw_command="SOS1#", purpose="sos_clear").status == 201
    assert template_lab(label="AUTO ui general", raw_command="GEN#").status == 201
    page = CommandListPage(oem_page).open()
    page.edit("AUTO ui general")
    page.choose("Purpose", re.compile(r"^SOS Clear"))

    page.submit("Update")

    page.expect_message(TAKEN)
    assert _stored(lab.oem, "AUTO ui general")["purpose"] != "sos_clear"


# ── Command List: edit, deactivate, filter, delete ────────────────────────────

def test_edit_changes_the_command_and_deactivating_removes_it_from_the_active_filter(oem_page: Page, lab, template_lab) -> None:
    template_lab(label="AUTO ui before", raw_command="OLD#")
    page = CommandListPage(oem_page).open()
    page.edit("AUTO ui before")

    page.fill_form("AUTO ui after", "NEW#", active=False)
    page.submit("Update")

    page.expect_message("Command template updated successfully.")
    stored = _stored(lab.oem, "AUTO ui after")
    assert (stored["raw_command"], stored["is_active"]) == ("NEW#", False)
    assert _stored(lab.oem, "AUTO ui before") is None
    rows = lab.oem.get(f"{COMMAND_TEMPLATES}?per_page=100").json()["data"]
    page.expect_counters(Total_Templates=len(rows), Active=sum(bool(t["is_active"]) for t in rows), Inactive=sum(not t["is_active"] for t in rows))
    page.filter_status("Inactive")
    expect(page.row("AUTO ui after")).to_have_count(1)
    page.filter_status("Active")
    expect(page.row("AUTO ui after")).to_have_count(0)


def test_search_by_label_narrows_the_list(oem_page: Page, template_lab) -> None:
    template_lab(label="AUTO ui findme", raw_command="A#")
    template_lab(label="AUTO ui other", raw_command="B#")
    page = CommandListPage(oem_page).open()

    page.search_box.fill("findme")

    expect(page.row("AUTO ui findme")).to_have_count(1)
    expect(page.row("AUTO ui other")).to_have_count(0)


def test_delete_asks_for_confirmation_and_cancel_keeps_the_command(oem_page: Page, lab, template_lab) -> None:
    template_lab(label="AUTO ui delete", raw_command="DEL#")
    page = CommandListPage(oem_page).open()

    page.delete("AUTO ui delete")
    expect(oem_page.get_by_text('Are you sure you want to delete "AUTO ui delete"?')).to_be_visible()
    page.cancel_delete()
    assert _stored(lab.oem, "AUTO ui delete") is not None
    page.expect_template("AUTO ui delete", "DEL#")

    page.delete("AUTO ui delete")
    page.confirm_delete("AUTO ui delete")

    page.expect_no_template("AUTO ui delete")
    assert _stored(lab.oem, "AUTO ui delete") is None


# ── Send Command ──────────────────────────────────────────────────────────────

@pytest.fixture
def send_page(oem_page: Page, lab, available_device):
    """The Send Command tab with a registered device found and selected; the send request is answered by a mock."""
    sent: list[dict] = []

    def fake(route):
        sent.append({"url": route.request.url, "body": json.loads(route.request.post_data or "{}")})
        route.fulfill(status=201, content_type="application/json", body=json.dumps({"id": 1, "status": "queued"}))

    oem_page.route(re.compile(r".*/command/api/vehicles/\d+/commands/custom"), fake)
    page = CommandSendPage(oem_page).open()
    page.search(available_device["imei"])
    page.pick_device(available_device["imei"])
    page.sent = sent
    page.device = available_device
    return page


def test_a_device_is_found_by_full_or_partial_imei_and_by_serial_number(oem_page: Page, available_device) -> None:
    page = CommandSendPage(oem_page).open()
    for term in (available_device["imei"], available_device["imei"][:7], available_device["serial_number"]):
        page.search(term)
        expect(page.main.get_by_text(available_device["imei"])).to_be_visible()


@pytest.mark.xfail(
    reason="BUG-048: Send Command offers (and the command service accepts a command for) a registered device that is not installed on a vehicle; "
           "the product owner confirmed it must not accept one",
    strict=False,
)
def test_a_device_that_is_not_installed_on_a_vehicle_is_not_offered_for_a_command(oem_page: Page, available_device) -> None:
    """Only the search is checked: sending to the device would queue a command that cannot be removed.
    When this is fixed, the tests above that use `available_device` need a device that is installed on a vehicle."""
    page = CommandSendPage(oem_page).open()

    with oem_page.expect_response(lambda r: "/api/devices?search=" in r.url):  # "No results found." is also shown while the search is still running
        page.search(available_device["imei"])

    page.expect_no_results()


def test_an_unknown_imei_finds_nothing(oem_page: Page) -> None:
    page = CommandSendPage(oem_page).open()

    page.search(unique_imei())

    page.expect_no_results()


def test_only_active_commands_of_the_devices_model_are_offered(send_page, lab, template_lab) -> None:
    template_lab(label="AUTO ui offered", raw_command="ON#")
    off = template_lab(label="AUTO ui hidden", raw_command="OFF#").json()["data"]["id"]
    lab.oem.put(f"{COMMAND_TEMPLATES}/{off}", json={"device_model_id": lab.model["id"], "label": "AUTO ui hidden", "raw_command": "OFF#", "is_active": False})
    send_page.page.reload()
    send_page.search(send_page.device["imei"])
    send_page.pick_device(send_page.device["imei"])

    options = send_page.catalog_options()

    assert "AUTO ui offered" in " ".join(options) and "AUTO ui hidden" not in " ".join(options), options


def test_a_catalogue_command_is_sent_with_its_label_and_exact_text(send_page, template_lab) -> None:
    template_lab(label="AUTO ui reboot", raw_command="REBOOT,1#")
    send_page.page.reload()
    send_page.search(send_page.device["imei"])
    send_page.pick_device(send_page.device["imei"])

    send_page.choose_catalog_command("AUTO ui reboot")
    send_page.send()

    send_page.expect_message("Command sent.")
    assert len(send_page.sent) == 1
    assert send_page.sent[0]["url"].endswith(f"/vehicles/{send_page.device['imei']}/commands/custom")
    assert send_page.sent[0]["body"] == {"raw": "REBOOT,1#", "label": "AUTO ui reboot"}


def test_a_model_without_commands_still_accepts_a_custom_command(send_page) -> None:
    expect(send_page.main.get_by_text("No commands published yet for this device model.")).to_be_visible()
    send_page.use_custom()
    send_page.custom_text.fill("CUSTOM,7#")

    send_page.send()

    send_page.expect_message("Command sent.")
    assert [s["body"]["raw"] for s in send_page.sent] == ["CUSTOM,7#"]


def test_a_custom_command_can_be_typed_next_to_the_catalogue(send_page, template_lab) -> None:
    template_lab(label="AUTO ui beside", raw_command="BESIDE#")
    send_page.page.reload()
    send_page.search(send_page.device["imei"])
    send_page.pick_device(send_page.device["imei"])
    send_page.use_custom()
    send_page.custom_text.fill("TYPED,1#")

    send_page.send()

    send_page.expect_message("Command sent.")
    assert [s["body"]["raw"] for s in send_page.sent] == ["TYPED,1#"]


@pytest.mark.parametrize("catalogue", [False, True], ids=["no-catalogue", "catalogue-nothing-chosen"])
def test_nothing_is_sent_without_a_command(send_page, template_lab, catalogue: bool) -> None:
    if catalogue:
        template_lab(label="AUTO ui unused", raw_command="UNUSED#")
        send_page.page.reload()
        send_page.search(send_page.device["imei"])
        send_page.pick_device(send_page.device["imei"])

    send_page.send()

    send_page.expect_message("Enter the raw command text.")
    assert send_page.sent == []


def test_a_device_the_oem_does_not_own_cannot_be_commanded(oem_api: ApiClient) -> None:
    """A random IMEI exists nowhere, so the service has to refuse it (a real device of another OEM is never commanded by a test)."""
    before = oem_api.request("GET", COMMANDS, origin=GO_ORIGIN).json()["meta"]["total"]

    response = oem_api.request("POST", f"/command/api/vehicles/{unique_imei()}/commands/custom", origin=GO_ORIGIN, json={"raw": "STATUS#", "label": ""})

    assert response.status in (400, 403, 404) and "not authorized" in response.text().lower(), f"{response.status} {response.text()[:200]}"
    assert oem_api.request("GET", COMMANDS, origin=GO_ORIGIN).json()["meta"]["total"] == before


# ── Command History (the command service's answer is mocked) ──────────────────

def _history(status: str, n: int, imei: str = "351756051523999", label: str = "Reboot", raw: str = "REBOOT#") -> dict:
    return {
        "id": n, "imei": imei, "command_key": "", "command_label": label, "command_type": "CUSTOM", "command_value": raw,
        "raw_command": raw, "status": status, "created_by": "00000000-0000-0000-0000-000000000000", "created_at": f"2026-10-2{n}T09:30:00.000000Z",
    }


def _mock_history(page: Page, rows: list[dict], counts: dict | None = None) -> list[str]:
    """Answers the history list with `rows`; returns the list of query strings the page sent."""
    queries: list[str] = []
    counts = counts or {"all": len(rows)}

    def answer(route):
        queries.append(route.request.url.split("?", 1)[-1])
        route.fulfill(status=200, content_type="application/json", body=json.dumps(
            {"data": rows, "meta": {"counts": counts, "page": 1, "per_page": 15, "total": len(rows)}}))

    page.route(re.compile(r".*/command/api/commands\?.*"), answer)
    return queries


def test_history_counters_add_queued_and_sent_as_pending(oem_page: Page) -> None:
    rows = [_history("queued", 1), _history("sent", 2), _history("acknowledged", 3), _history("acknowledged", 4), _history("failed", 5)]
    _mock_history(oem_page, rows, {"all": 5, "queued": 1, "sent": 1, "acknowledged": 2, "failed": 1})

    page = CommandHistoryPage(oem_page).open()

    page.expect_counters(commands=5, pending=2, acknowledged=2, failed=1)
    expect(page.rows()).to_have_count(5)


def test_history_row_shows_device_command_and_status(oem_page: Page) -> None:
    _mock_history(oem_page, [_history("failed", 3, imei="351756051529876", label="Set speed", raw="SPEED,60#")])

    page = CommandHistoryPage(oem_page).open()

    row = page.rows().first
    expect(row).to_contain_text("351756051529876")
    expect(row).to_contain_text("Set speed : SPEED,60#")
    expect(row).to_contain_text("failed")


def test_history_filters_are_passed_to_the_service(oem_page: Page) -> None:
    _mock_history(oem_page, [_history("queued", 1)])
    page = CommandHistoryPage(oem_page).open()

    page.filter_status("Failed")
    page.filter_sent_by("Sent by me")
    page.vehicle_box.fill("3517560")
    with oem_page.expect_request(lambda r: "command/api/commands" in r.url and "q=3517560" in r.url and "command=REBOOT" in r.url) as sent:
        page.command_box.fill("REBOOT")

    last = dict(part.split("=", 1) for part in sent.value.url.split("?", 1)[1].split("&"))
    assert (last["status"], last["source"], last["q"], last["command"]) == ("failed", "manual", "3517560", "REBOOT")


def test_an_empty_history_says_nothing_was_sent_and_a_filter_without_a_match_says_so(oem_page: Page) -> None:
    _mock_history(oem_page, [])
    page = CommandHistoryPage(oem_page).open()
    page.expect_nothing_sent_yet()

    page.vehicle_box.fill("999999999999999")

    page.expect_no_match()


def test_history_does_not_list_commands_of_other_organisations(oem_api: ApiClient, admin_api: ApiClient) -> None:
    """The State Admin's history holds commands of installed devices; none of them may appear for the OEM."""
    window = "from=2020-01-01&to=2026-12-31&per_page=100"
    others = {c["imei"] for c in admin_api.request("GET", f"{COMMANDS}?{window}", origin=GO_ORIGIN).json()["data"]}
    mine = {c["imei"] for c in oem_api.request("GET", f"{COMMANDS}?{window}", origin=GO_ORIGIN).json()["data"]}

    assert others, "the State Admin has no command to compare with"
    assert not (mine & others), f"The OEM's history lists commands of other organisations' devices: {sorted(mine & others)[:5]}"
