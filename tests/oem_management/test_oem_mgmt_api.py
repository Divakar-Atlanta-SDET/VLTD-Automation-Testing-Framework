"""
OEM Management API - Device Models, Firmware, SIM Modules.   Plan: specs/oem-management-test-plan.md

Server-side CRUD and input validation, independent of the forms. Test design:
  Boundary value analysis   every text field at (1, max-1, max) -> accepted and (max+1, 2*max) -> refused;
                            the TAC issue date around today; the certificate size around 2048 KB
  Equivalence partitioning  valid / missing / blank / whitespace-only / wrong type / unknown reference /
                            duplicate, per field
  CRUD + read semantics     list paging and sort order, search and filters, detail, update, delete, 404s
Created records are removed after each test (the 'AUTO PG' seed is never touched).
"""

import random
from dataclasses import asdict
from datetime import date, timedelta

import pytest

from utils import data_generator as data
from utils.file_utils import KB
from utils.network_monitor import LEAK_PATTERN
from utils.oem_mgmt_api import FIRMWARES, MODELS, SIMS, OemMgmtApi, pdf_file
from tests.oem_management.bugs import MODEL_UPDATE_BROKEN, NAME_STAYS_RESERVED, ORPHANED_FIRMWARE

pytestmark = [pytest.mark.oem_management, pytest.mark.api]

PDF_HEADER = b"%PDF-1.4\n"


# ── helpers ───────────────────────────────────────────────────────────────────

def post_model(records: OemMgmtApi, certificate="default", **over):
    """POST a device model (multipart). A value of None leaves the field out; returns the raw response."""
    fields = {**asdict(data.device_model_data()), "oem_id": records.oem_id, **over}
    cop_certificate = fields.pop("cop_certificate", None)
    multipart = {k: str(v) for k, v in fields.items() if v is not None}
    if certificate == "default":
        multipart["tac_certificate"] = pdf_file()
    elif certificate is not None:
        multipart["tac_certificate"] = certificate
    if cop_certificate is not None:
        multipart["cop_certificate"] = cop_certificate
    response = records.admin.post(MODELS, multipart=multipart)
    if response.status == 201:
        records.track("model", response.json()["data"]["id"])
    return response


def post_firmware(records: OemMgmtApi, model_id, **over):
    body = {"oem_id": records.oem_id, "device_model_id": model_id, "is_active": True, **asdict(data.firmware_data()), **over}
    body = {k: v for k, v in body.items() if v is not None}
    response = records.admin.post(FIRMWARES, json=body)
    if response.status == 201:
        records.track("firmware", response.json()["data"]["id"])
    return response


def post_sim(records: OemMgmtApi, **over):
    body = {"oem_id": records.oem_id, "is_active": True, **asdict(data.sim_module_data()), **over}
    body = {k: v for k, v in body.items() if v is not None}
    response = records.admin.post(SIMS, json=body)
    if response.status == 201:
        records.track("sim", response.json()["data"]["id"])
    return response


def assert_created(response) -> dict:
    assert response.status == 201, f"expected 201, got {response.status}: {response.text()[:300]}"
    return response.json()["data"]


def assert_rejected(response, field: str, fragment: str | None = None) -> None:
    """422 with an error on `field` (containing `fragment`), and no leaked internals."""
    text = response.text()
    assert response.status == 422, f"expected 422 for '{field}', got {response.status}: {text[:300]}"
    assert not LEAK_PATTERN.search(text), f"response leaks internals: {text[:200]}"
    errors = response.json().get("errors") or {}
    assert field in errors, f"no error on '{field}': {errors}"
    if fragment:
        assert any(fragment in m for m in errors[field]), f"'{fragment}' not in {errors[field]}"


def length_cases(maximum: int):
    """Boundary values for a maximum length: (length, accepted)."""
    return [
        pytest.param(1, True, id="1"),
        pytest.param(maximum - 1, True, id=f"{maximum - 1}"),
        pytest.param(maximum, True, id=f"{maximum}-max"),
        pytest.param(maximum + 1, False, id=f"{maximum + 1}-over"),
        pytest.param(maximum * 2, False, id=f"{maximum * 2}-way-over"),
    ]


def pdf_of_size(size: int) -> dict:
    return pdf_file("tac.pdf", PDF_HEADER + b"0" * (size - len(PDF_HEADER)))


# ══════════════════════════ DEVICE MODELS ══════════════════════════════════════

class TestDeviceModelCreate:
    def test_valid_request_creates_the_record(self, records: OemMgmtApi) -> None:
        model = data.device_model_data()
        created = assert_created(post_model(records, **asdict(model)))

        assert created["model_name"] == model.model_name and created["oem_id"] == records.oem_id
        assert created["part_no"] == model.part_no and created["tac_name"] == model.tac_name
        assert created["is_active"] is not False  # the API leaves it null when omitted; the list shows such records as Active

    @pytest.mark.parametrize("field, maximum", [("model_name", 100), ("network_profile_name", 150)])
    def test_text_length_boundary(self, records: OemMgmtApi, field: str, maximum: int) -> None:
        def value(length: int) -> str:
            # model_name must be unique: keep the exact length but start with a unique timestamp
            return data.unique_suffix().ljust(length, "a")[:length] if field == "model_name" else "a" * length

        for length in (maximum - 1, maximum):
            assert_created(post_model(records, **{field: value(length)}))
        # The names of deleted device models stay reserved (BUG-031), so common 1-character names are used up:
        # draw a random CJK ideograph instead (still exactly one character)
        single = None
        for _ in range(5):
            single = post_model(records, **{field: chr(random.randint(0x4E00, 0x9FFF))})
            if single.status == 201:
                break
        assert single.status == 201, f"no 1-character {field} could be saved: {single.text()[:150]}"
        for length in (maximum + 1, maximum * 2):
            assert_rejected(post_model(records, **{field: value(length)}), field, "must not be greater than")


    @pytest.mark.parametrize("field", ["model_name", "tac_issued_on"])
    @pytest.mark.parametrize("value", [None, "   "], ids=["missing", "whitespace"])
    def test_required_field_partitions(self, records: OemMgmtApi, field: str, value) -> None:
        assert_rejected(post_model(records, **{field: value}), field, "required")

    def test_certificate_is_required(self, records: OemMgmtApi) -> None:
        assert_rejected(post_model(records, certificate=None), "tac_certificate", "required")

    @pytest.mark.parametrize(
        "oem_id, status",
        [(None, 422), ("abc", 422), ("999999", 404)],
        ids=["missing", "not-a-number", "unknown-oem"],
    )
    def test_oem_reference_partitions(self, records: OemMgmtApi, oem_id, status: int) -> None:
        response = post_model(records, oem_id=oem_id)
        assert response.status == status, f"{response.status}: {response.text()[:200]}"

    @pytest.mark.parametrize(
        "offset_days, accepted",
        [(-1, True), (0, True), (1, False)],
        ids=["yesterday", "today", "tomorrow"],
    )
    def test_tac_issue_date_boundary(self, records: OemMgmtApi, offset_days: int, accepted: bool) -> None:
        value = (date.today() + timedelta(days=offset_days)).isoformat()
        response = post_model(records, tac_issued_on=value)
        if accepted:
            assert_created(response)
        else:
            assert_rejected(response, "tac_issued_on", "before or equal to today")

    @pytest.mark.parametrize("value", ["2026-02-30", "15-01-2026", "abc"])
    def test_tac_issue_date_format_partitions(self, records: OemMgmtApi, value: str) -> None:
        assert_rejected(post_model(records, tac_issued_on=value), "tac_issued_on")

    @pytest.mark.parametrize(
        "name, mime, content, accepted",
        [
            ("a.pdf", "application/pdf", PDF_HEADER + b"0" * 100, True),
            ("a.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, False),
            ("a.exe", "application/octet-stream", b"MZ" + b"0" * 100, False),
            ("a.pdf.exe", "application/octet-stream", b"MZ" + b"0" * 100, False),
        ],
        ids=["pdf", "png", "exe", "double-extension"],
    )
    def test_certificate_type_partitions(self, records: OemMgmtApi, name, mime, content, accepted) -> None:
        response = post_model(records, certificate={"name": name, "mimeType": mime, "buffer": content})
        if accepted:
            assert_created(response)
        else:
            assert_rejected(response, "tac_certificate", "must be a file of type")

    @pytest.mark.parametrize(
        "size, accepted",
        [(2048 * KB, True), (2048 * KB + 1, False)],
        ids=["2048KB-max", "2048KB+1B"],
    )
    def test_certificate_size_boundary(self, records: OemMgmtApi, size: int, accepted: bool) -> None:
        response = post_model(records, certificate=pdf_of_size(size))
        if accepted:
            assert_created(response)
        else:
            assert_rejected(response, "tac_certificate", "must not be greater than 2048 kilobytes")

    def test_complete_cop_details_are_accepted(self, records: OemMgmtApi) -> None:
        created = assert_created(post_model(
            records, cop_no="COP-1", cop_valid_from="2026-01-01", cop_validity="2026-12-31", cop_certificate=pdf_file("cop.pdf"),
        ))
        assert created["cop_no"] == "COP-1" and created["has_cop_certificate"] is True

    @pytest.mark.parametrize(
        "over",
        [
            {"cop_no": "COP-1"},
            {"cop_valid_from": "2026-01-01", "cop_validity": "2026-12-31"},
            {"cop_no": "COP-1", "cop_valid_from": "2026-01-01"},
            {"cop_no": "COP-1", "cop_valid_from": "2026-01-01", "cop_validity": "2026-12-31"},  # certificate missing
        ],
        ids=["number-only", "dates-only", "no-end-date", "no-certificate"],
    )
    def test_incomplete_cop_details_are_rejected(self, records: OemMgmtApi, over: dict) -> None:
        assert_rejected(post_model(records, **over), "cop_no", "must be supplied together")

    def test_cop_validity_before_valid_from_is_rejected(self, records: OemMgmtApi) -> None:
        response = post_model(
            records, cop_no="COP-2", cop_valid_from="2026-06-01", cop_validity="2026-01-01", cop_certificate=pdf_file("cop.pdf"),
        )
        assert_rejected(response, "cop_validity", "after or equal to cop valid from")


    def test_duplicate_model_name_is_rejected(self, records: OemMgmtApi) -> None:
        existing = assert_created(post_model(records))
        assert_rejected(post_model(records, model_name=existing["model_name"]), "model_name", "already been taken")

    def test_markup_in_text_fields_is_stored_as_plain_text(self, records: OemMgmtApi) -> None:
        payload = f"<script>alert(1)</script>{data.unique_suffix()}"
        created = assert_created(post_model(records, model_name=payload))
        assert created["model_name"] == payload


class TestDeviceModelReadUpdateDelete:
    def test_detail_returns_the_record(self, records: OemMgmtApi) -> None:
        model = records.create_model()
        body = records.admin.get(f"{MODELS}/{model['id']}").json()["data"]

        assert body["id"] == model["id"] and body["model_name"] == model["model_name"]
        assert body["oem"]["code"] == records.oem["code"] and body["has_tac_certificate"] is True and body["firmwares"] == []

    @pytest.mark.parametrize("path", ["999999", "0"], ids=["unknown-id", "zero"])
    def test_unknown_id_is_404(self, records: OemMgmtApi, path: str) -> None:
        assert records.admin.get(f"{MODELS}/{path}").status == 404

    def test_update_with_json_patch_changes_the_record(self, records: OemMgmtApi) -> None:
        model = records.create_model()
        response = records.admin.patch(
            f"{MODELS}/{model['id']}",
            json={"oem_id": records.oem_id, "model_name": model["model_name"] + "-EDITED", "part_no": "NEWPN",
                  "tac_name": model["tac_name"], "tac_issued_on": "2026-02-02"},
        )

        assert response.status == 200, response.text()[:300]
        body = records.admin.get(f"{MODELS}/{model['id']}").json()["data"]
        assert body["model_name"].endswith("-EDITED") and body["part_no"] == "NEWPN" and body["tac_issued_on"].startswith("2026-02-02")

    def test_update_with_method_override_changes_the_record(self, records: OemMgmtApi) -> None:
        """POST + _method=PATCH (multipart) is the shape that works for multipart updates."""
        model = records.create_model()
        response = records.admin.post(f"{MODELS}/{model['id']}", multipart={
            "_method": "PATCH", "oem_id": str(records.oem_id), "model_name": model["model_name"] + "-OVR",
            "part_no": model["part_no"], "tac_name": model["tac_name"], "tac_issued_on": "2026-01-15",
        })
        assert response.status == 200, response.text()[:300]

    @MODEL_UPDATE_BROKEN
    def test_update_with_a_native_multipart_patch_works(self, records: OemMgmtApi) -> None:
        """What the UI sends: a real PATCH with a multipart body."""
        model = records.create_model()
        response = records.admin.request("PATCH", f"{MODELS}/{model['id']}", multipart={
            "oem_id": str(records.oem_id), "model_name": model["model_name"] + "-UI", "part_no": model["part_no"],
            "tac_name": model["tac_name"], "tac_issued_on": "2026-01-15",
        })
        assert response.status == 200, f"{response.status}: {response.text()[:200]}"

    @pytest.mark.parametrize("field, value", [("model_name", ""), ("tac_issued_on", "2999-01-01")])
    def test_update_validates_like_create(self, records: OemMgmtApi, field: str, value: str) -> None:
        model = records.create_model()
        body = {"oem_id": records.oem_id, "model_name": model["model_name"], "part_no": model["part_no"],
                "tac_name": model["tac_name"], "tac_issued_on": "2026-01-15", field: value}
        assert_rejected(records.admin.patch(f"{MODELS}/{model['id']}", json=body), field)

    def test_update_of_an_unknown_record_is_404(self, records: OemMgmtApi) -> None:
        response = records.admin.patch(f"{MODELS}/999999", json={"oem_id": records.oem_id, "model_name": "x"})
        assert response.status == 404

    def test_delete_requires_the_owning_oem_id(self, records: OemMgmtApi) -> None:
        model = records.create_model()

        without = records.admin.delete(f"{MODELS}/{model['id']}")

        assert_rejected(without, "oem_id", "Select an OEM")
        assert records.exists("model", model["id"])

    def test_delete_removes_the_record(self, records: OemMgmtApi) -> None:
        model = records.create_model()

        response = records.admin.delete(f"{MODELS}/{model['id']}?oem_id={records.oem_id}")

        assert response.status == 200 and "deleted" in response.json()["message"].lower()
        assert records.admin.get(f"{MODELS}/{model['id']}").status == 404

    def test_deleting_twice_is_a_404(self, records: OemMgmtApi) -> None:
        model = records.create_model()
        records.admin.delete(f"{MODELS}/{model['id']}?oem_id={records.oem_id}")

        assert records.admin.delete(f"{MODELS}/{model['id']}?oem_id={records.oem_id}").status == 404

    def test_list_filters_by_oem_and_search(self, records: OemMgmtApi) -> None:
        model = records.create_model()

        by_search = records.admin.get(f"{MODELS}?search={model['model_name']}").json()["data"]
        by_oem = {m["id"] for m in records.admin.get(f"{MODELS}?oem_id={records.oem_id}&per_page=100").json()["data"]}
        owner_of = {m["id"]: m["oem_id"] for m in records.admin.get(f"{MODELS}?per_page=100").json()["data"]}

        assert [m["id"] for m in by_search] == [model["id"]]
        assert model["id"] in by_oem
        # other tests add and remove records meanwhile, so judge only the records both reads contain
        assert all(owner_of[i] == records.oem_id for i in by_oem if i in owner_of), "the OEM filter returned another OEM's record"


# ══════════════════════════ FIRMWARE ═══════════════════════════════════════════

@pytest.fixture
def host_model(records: OemMgmtApi) -> dict:
    return records.create_model()


class TestFirmwareCreate:
    def test_valid_request_creates_the_record(self, records: OemMgmtApi, host_model: dict) -> None:
        fw = data.firmware_data()
        created = assert_created(post_firmware(records, host_model["id"], **asdict(fw)))

        assert created["version"] == fw.version and created["device_model_id"] == host_model["id"]
        assert created["release_date"].startswith(fw.release_date)

    def test_version_length_boundary(self, records: OemMgmtApi, host_model: dict) -> None:
        for length in (1, 49, 50):
            assert_created(post_firmware(records, host_model["id"], version="v" * length))
        for length in (51, 100):
            assert_rejected(post_firmware(records, host_model["id"], version="v" * length), "version", "must not be greater than 50")

    @pytest.mark.parametrize("value", [None, "", "   "], ids=["missing", "blank", "whitespace"])
    def test_version_is_required(self, records: OemMgmtApi, host_model: dict, value) -> None:
        assert_rejected(post_firmware(records, host_model["id"], version=value), "version", "required")


    @pytest.mark.parametrize("value", ["2026-02-30", "abc"])
    def test_invalid_release_dates_are_rejected(self, records: OemMgmtApi, host_model: dict, value: str) -> None:
        assert_rejected(post_firmware(records, host_model["id"], release_date=value), "release_date", "valid date")


    @pytest.mark.parametrize("field", ["is_mandatory", "is_active"])
    @pytest.mark.parametrize("value, accepted", [(True, True), (0, True), ("maybe", False)], ids=["true", "0", "text"])
    def test_boolean_partitions(self, records: OemMgmtApi, host_model: dict, field: str, value, accepted: bool) -> None:
        response = post_firmware(records, host_model["id"], **{field: value})
        if accepted:
            assert_created(response)
        else:
            assert_rejected(response, field, "true or false")

    def test_device_model_is_required(self, records: OemMgmtApi) -> None:
        assert_rejected(post_firmware(records, None), "device_model_id", "required")

    def test_unknown_device_model_is_rejected(self, records: OemMgmtApi) -> None:
        assert_rejected(post_firmware(records, 999999), "device_model_id", "does not belong")


    def test_device_model_must_belong_to_the_selected_oem(self, records: OemMgmtApi, host_model: dict) -> None:
        others = [o["id"] for o in records.admin.list_items("/api/transport-commissioner/oems?per_page=100") if o["id"] != records.oem_id]
        response = post_firmware(records, host_model["id"], oem_id=others[0])
        assert_rejected(response, "device_model_id", "does not belong to the selected OEM")

    def test_oem_is_required_and_must_exist(self, records: OemMgmtApi, host_model: dict) -> None:
        assert_rejected(post_firmware(records, host_model["id"], oem_id=None), "oem_id", "Select an OEM")
        assert post_firmware(records, host_model["id"], oem_id=999999).status == 404

    def test_same_version_twice_for_one_model_is_rejected(self, records: OemMgmtApi, host_model: dict) -> None:
        first = assert_created(post_firmware(records, host_model["id"]))
        assert_rejected(post_firmware(records, host_model["id"], version=first["version"]), "version", "already been taken")

    def test_same_version_for_a_different_model_is_allowed(self, records: OemMgmtApi, host_model: dict) -> None:
        first = assert_created(post_firmware(records, host_model["id"]))
        other_model = records.create_model()
        assert_created(post_firmware(records, other_model["id"], version=first["version"]))


class TestFirmwareReadUpdateDelete:
    def test_detail_returns_the_record_with_its_model(self, records: OemMgmtApi, host_model: dict) -> None:
        fw = records.create_firmware(host_model["id"])
        body = records.admin.get(f"{FIRMWARES}/{fw['id']}").json()["data"]

        assert body["version"] == fw["version"] and body["device_model"]["id"] == host_model["id"]
        assert body["device_model"]["oem"]["code"] == records.oem["code"]

    def test_unknown_id_is_404(self, records: OemMgmtApi) -> None:
        assert records.admin.get(f"{FIRMWARES}/999999").status == 404

    def test_update_changes_the_record(self, records: OemMgmtApi, host_model: dict) -> None:
        fw = records.create_firmware(host_model["id"])
        response = records.admin.patch(f"{FIRMWARES}/{fw['id']}", json={
            "oem_id": records.oem_id, "device_model_id": host_model["id"], "version": fw["version"] + "-E",
            "is_mandatory": True, "is_active": False, "release_date": "2026-05-05",
        })

        assert response.status == 200, response.text()[:300]
        body = records.admin.get(f"{FIRMWARES}/{fw['id']}").json()["data"]
        assert body["version"].endswith("-E") and body["is_mandatory"] in (True, 1) and body["is_active"] in (False, 0)

    @pytest.mark.parametrize("field, value", [("version", ""), ("release_date", "abc")])
    def test_update_validates_like_create(self, records: OemMgmtApi, host_model: dict, field: str, value) -> None:
        fw = records.create_firmware(host_model["id"])
        body = {"oem_id": records.oem_id, "device_model_id": host_model["id"], "version": fw["version"], "is_active": True, field: value}
        assert_rejected(records.admin.patch(f"{FIRMWARES}/{fw['id']}", json=body), field)

    def test_firmware_cannot_be_moved_to_another_device_model(self, records: OemMgmtApi, host_model: dict) -> None:
        """Guide s4.2: a firmware version cannot be moved to a different device model."""
        other_model = records.create_model()
        fw = records.create_firmware(host_model["id"])

        response = records.admin.patch(f"{FIRMWARES}/{fw['id']}", json={
            "oem_id": records.oem_id, "device_model_id": other_model["id"], "version": fw["version"], "is_active": True,
        })

        assert response.status == 422 and "cannot be moved" in response.json()["message"], response.text()[:300]
        assert records.admin.get(f"{FIRMWARES}/{fw['id']}").json()["data"]["device_model"]["id"] == host_model["id"]

    def test_delete_requires_the_owning_oem_id(self, records: OemMgmtApi, host_model: dict) -> None:
        fw = records.create_firmware(host_model["id"])

        assert_rejected(records.admin.delete(f"{FIRMWARES}/{fw['id']}"), "oem_id", "Select an OEM")
        assert records.exists("firmware", fw["id"])

    def test_delete_removes_the_record(self, records: OemMgmtApi, host_model: dict) -> None:
        fw = records.create_firmware(host_model["id"])

        response = records.admin.delete(f"{FIRMWARES}/{fw['id']}?oem_id={records.oem_id}")

        assert response.status == 200
        assert records.admin.get(f"{FIRMWARES}/{fw['id']}").status == 404

    @ORPHANED_FIRMWARE
    def test_deleting_a_model_that_has_firmware(self, records: OemMgmtApi, host_model: dict) -> None:
        """Either the delete is refused, or the firmware goes with it - it must not be left orphaned."""
        fw = records.create_firmware(host_model["id"])

        response = records.admin.delete(f"{MODELS}/{host_model['id']}?oem_id={records.oem_id}")

        assert response.status in (200, 409, 422), f"unexpected {response.status}: {response.text()[:200]}"
        if response.status == 200:
            assert not records.exists("firmware", fw["id"]), "The firmware outlived its deleted device model"


# ══════════════════════════ SIM MODULES ════════════════════════════════════════

SIM_TEXT_FIELDS = [
    ("sim_manufacturer", 150, True),
    ("module_name", 150, True),
    ("primary_operator", 100, False),
]


class TestSimModuleCreate:
    def test_valid_request_creates_the_record(self, records: OemMgmtApi) -> None:
        sim = data.sim_module_data()
        created = assert_created(post_sim(records, **asdict(sim)))

        assert created["module_name"] == sim.module_name and created["sim_manufacturer"] == sim.sim_manufacturer
        assert created["primary_operator"] == "Airtel" and created["secondary_sim_type"] == "Physical"

    def test_only_the_required_fields_are_needed(self, records: OemMgmtApi) -> None:
        sim = data.sim_module_data()
        created = assert_created(records.admin.post(SIMS, json={
            "oem_id": records.oem_id, "sim_manufacturer": sim.sim_manufacturer, "module_name": sim.module_name,
        }))
        records.track("sim", created["id"])

    @pytest.mark.parametrize("field, maximum, required", SIM_TEXT_FIELDS, ids=[f[0] for f in SIM_TEXT_FIELDS])
    def test_text_length_boundary(self, records: OemMgmtApi, field: str, maximum: int, required: bool) -> None:
        def value(length: int) -> str:
            # module_name must be unique, so make the value unique while keeping its exact length
            return data.unique_suffix().ljust(length, "s")[:length] if field == "module_name" else "s" * length

        for length in (1, maximum - 1, maximum):
            assert_created(post_sim(records, **{field: value(length)}))
        for length in (maximum + 1, maximum * 2):
            assert_rejected(post_sim(records, **{field: value(length)}), field, "must not be greater than")

    @pytest.mark.parametrize("field", ["sim_manufacturer", "module_name"])
    @pytest.mark.parametrize("value", [None, "", "   "], ids=["missing", "blank", "whitespace"])
    def test_required_field_partitions(self, records: OemMgmtApi, field: str, value) -> None:
        assert_rejected(post_sim(records, **{field: value}), field, "required")


    def test_oem_is_required_and_must_exist(self, records: OemMgmtApi) -> None:
        assert_rejected(post_sim(records, oem_id=None), "oem_id", "Select an OEM")
        assert post_sim(records, oem_id=999999).status == 404
        assert_rejected(post_sim(records, oem_id="abc"), "oem_id")

    @pytest.mark.parametrize("value, accepted", [(True, True), (False, True), ("maybe", False)], ids=["true", "false", "text"])
    def test_status_partitions(self, records: OemMgmtApi, value, accepted: bool) -> None:
        response = post_sim(records, is_active=value)
        if accepted:
            assert_created(response)
        else:
            assert_rejected(response, "is_active", "true or false")

    def test_duplicate_module_name_is_rejected_whatever_the_manufacturer(self, records: OemMgmtApi) -> None:
        first = assert_created(post_sim(records))
        assert_rejected(post_sim(records, module_name=first["module_name"]), "module_name", "already been taken")
        assert_rejected(
            post_sim(records, module_name=first["module_name"], sim_manufacturer="ANOTHER MFG"), "module_name", "already been taken"
        )


class TestSimModuleReadUpdateDelete:
    def test_detail_returns_the_record(self, records: OemMgmtApi) -> None:
        sim = records.create_sim()
        body = records.admin.get(f"{SIMS}/{sim['id']}").json()["data"]

        assert body["module_name"] == sim["module_name"] and body["oem"]["code"] == records.oem["code"]

    def test_unknown_id_is_404(self, records: OemMgmtApi) -> None:
        assert records.admin.get(f"{SIMS}/999999").status == 404

    def test_update_changes_the_record(self, records: OemMgmtApi) -> None:
        sim = records.create_sim()
        response = records.admin.patch(f"{SIMS}/{sim['id']}", json={
            "oem_id": records.oem_id, "sim_manufacturer": "NEW MFG", "module_name": sim["module_name"] + "-E", "is_active": False,
        })

        assert response.status == 200, response.text()[:300]
        body = records.admin.get(f"{SIMS}/{sim['id']}").json()["data"]
        assert body["sim_manufacturer"] == "NEW MFG" and body["module_name"].endswith("-E") and body["is_active"] in (False, 0)


    @pytest.mark.parametrize("field, value", [("module_name", ""), ("module_name", "x" * 151)])
    def test_update_validates_like_create(self, records: OemMgmtApi, field: str, value: str) -> None:
        sim = records.create_sim()
        body = {"oem_id": records.oem_id, "sim_manufacturer": sim["sim_manufacturer"], "module_name": sim["module_name"], field: value}
        assert_rejected(records.admin.patch(f"{SIMS}/{sim['id']}", json=body), field)

    def test_update_to_another_records_name_is_rejected(self, records: OemMgmtApi) -> None:
        first, second = records.create_sim(), records.create_sim()
        body = {"oem_id": records.oem_id, "sim_manufacturer": "X", "module_name": first["module_name"]}
        assert_rejected(records.admin.patch(f"{SIMS}/{second['id']}", json=body), "module_name", "already been taken")

    def test_a_record_can_keep_its_own_name_on_update(self, records: OemMgmtApi) -> None:
        sim = records.create_sim()
        body = {"oem_id": records.oem_id, "sim_manufacturer": "SAME NAME", "module_name": sim["module_name"]}
        assert records.admin.patch(f"{SIMS}/{sim['id']}", json=body).status == 200

    def test_delete_requires_the_owning_oem_id(self, records: OemMgmtApi) -> None:
        sim = records.create_sim()

        assert_rejected(records.admin.delete(f"{SIMS}/{sim['id']}"), "oem_id", "Select an OEM")
        assert records.exists("sim", sim["id"])

    def test_delete_removes_the_record(self, records: OemMgmtApi) -> None:
        sim = records.create_sim()

        response = records.admin.delete(f"{SIMS}/{sim['id']}?oem_id={records.oem_id}")

        assert response.status == 200
        assert records.admin.get(f"{SIMS}/{sim['id']}").status == 404


# ══════════════════════════ NAMES OF DELETED RECORDS ═══════════════════════════

class TestReuseAfterDelete:
    """Once a record is deleted nothing refers to it any more, so its unique name should be free again."""

    @NAME_STAYS_RESERVED
    def test_a_deleted_device_model_name_can_be_reused(self, records: OemMgmtApi) -> None:
        name = f"AUTO REUSE {data.unique_suffix()}"
        first = assert_created(post_model(records, model_name=name))
        assert records.delete("model", first["id"]) == 200

        assert_created(post_model(records, model_name=name))

    @NAME_STAYS_RESERVED
    def test_a_deleted_firmware_version_can_be_reused(self, records: OemMgmtApi, host_model: dict) -> None:
        version = f"REUSE-{data.unique_suffix()}"
        first = assert_created(post_firmware(records, host_model["id"], version=version))
        assert records.delete("firmware", first["id"]) == 200

        assert_created(post_firmware(records, host_model["id"], version=version))

    def test_a_deleted_sim_module_name_can_be_reused(self, records: OemMgmtApi) -> None:
        name = f"AUTO REUSE SIM {data.unique_suffix()}"
        first = assert_created(post_sim(records, module_name=name))
        assert records.delete("sim", first["id"]) == 200

        assert_created(post_sim(records, module_name=name))


# ══════════════════════════ READ SEMANTICS & SECURITY (all three) ═══════════════

LIST_ENDPOINTS = [pytest.param(MODELS, id="device-models"), pytest.param(FIRMWARES, id="firmware"), pytest.param(SIMS, id="sim-modules")]


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
class TestListSemantics:
    def test_pagination_metadata_is_consistent(self, records: OemMgmtApi, path: str) -> None:
        body = records.admin.get(f"{path}?per_page=5").json()
        meta = body["meta"]["pagination"]

        assert meta["per_page"] == 5 and len(body["data"]) == 5
        assert meta["total"] >= 12 and meta["last_page"] == -(-meta["total"] // 5)
        assert meta["has_more"] is True and meta["current_page"] == 1


    def test_search_that_matches_nothing_returns_an_empty_list(self, records: OemMgmtApi, path: str) -> None:
        body = records.admin.get(f"{path}?search=zz-no-such-record-zz").json()
        assert body["data"] == [] and body["meta"]["pagination"]["total"] == 0

    @pytest.mark.parametrize("term", ["'", "%", "<script>"])
    def test_search_special_characters_never_crash(self, records: OemMgmtApi, path: str, term: str) -> None:
        response = records.admin.get(f"{path}?search={term}")
        assert response.status < 500, f"{term!r} -> {response.status}"
        assert not LEAK_PATTERN.search(response.text())


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
class TestAuthentication:
    @pytest.mark.parametrize("token", [None, "garbage.token.value"], ids=["no-token", "malformed-token"])
    def test_every_verb_refuses_an_unauthenticated_caller(self, records: OemMgmtApi, path: str, token) -> None:
        for method in ("GET", "POST"):
            response = records.admin.request(method, path, json={} if method == "POST" else None, token=token)
            assert response.status in (401, 403), f"{method} {path} -> {response.status}"

    def test_delete_and_update_refuse_an_unauthenticated_caller(self, records: OemMgmtApi, path: str) -> None:
        for method in ("PATCH", "DELETE"):
            response = records.admin.request(method, f"{path}/1", json={}, token=None)
            assert response.status in (401, 403), f"{method} {path}/1 -> {response.status}"
