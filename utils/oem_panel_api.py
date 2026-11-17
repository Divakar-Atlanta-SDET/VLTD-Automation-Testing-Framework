"""
API helper for the OEM panel tests (devices, allocation, bulk upload).

A device can only be registered with a Firmware and a SIM Module of the OEM, and the State Admin owns that master data
(guide 14.4). `OemDeviceLab` therefore creates a throw-away Device Model + Firmware + SIM Module for the OEM through the
admin API, registers devices through the OEM API, and removes everything again - devices first (a device locks its
master data), then the master data - even when a test fails.

Endpoints used (OEM token unless stated):
  POST   /api/devices                          register one device
  DELETE /api/devices/{id}                     only an *available* device can be deleted
  POST   /api/devices/bulk-upload              {"devices": [row, ...]}  rows reference model / SIM module / firmware by name
  POST   /api/device-allocations               {"fitment_centre_id", "imeis": [...]}
  POST   /api/device-allocations/{id}/rollback {"allocation_id", "imeis": [...]}
  POST   /api/oem/fitment-centres              multipart; the centre and its login account (neither can be deleted afterwards)
  POST   /api/oem/fitment-centres/{id}         multipart edit
  PATCH  /api/oem/fitment-centres/{id}/deactivate | activate | blacklist   {"remarks"} (mandatory)
"""

import random
from dataclasses import dataclass, field

from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.file_utils import png_bytes
from utils.oem_mgmt_api import OemMgmtApi

DEVICES = "/api/devices"
ALLOCATIONS = "/api/device-allocations"
FITMENT_CENTRES = "/api/oem/fitment-centres"
BULK_UPLOAD = f"{DEVICES}/bulk-upload"
COMMAND_TEMPLATES = "/api/device-command-templates"
WATCHLISTS = "/api/tracking/watchlists"

# The command, alert and geofence services run on their own host (pass it as `origin=` to ApiClient.request).
GO_ORIGIN = "https://vltdgo.misbackend.com"
GEOFENCES = "/geofence/api/geofences"
ALERT_RULES = "/alert/api/rules"
COMMANDS = "/command/api/commands"


def unique_imei() -> str:
    """A 15-digit IMEI that is unlikely to exist (random; the leading digit keeps it out of the ranges real devices use)."""
    return "7" + "".join(random.choices("0123456789", k=14))


def device_body(model: dict, firmware: dict, sim: dict, imei: str | None = None, **overrides) -> dict:
    """A valid `POST /api/devices` body."""
    imei = imei or unique_imei()
    body = {
        "imei": imei,
        "serial_number": "AUTOSN" + imei[-8:],
        "device_model_id": model["id"],
        "sim_module_id": sim["id"],
        "current_firmware_id": firmware["id"],
        "primary_mobile_number": "9" + imei[-9:],
        "secondary_mobile_number": "8" + imei[-9:],
        "iccid": "8991" + imei + "0",  # 20 digits
        "valid_till": "2030-12-31",
    }
    return {**body, **overrides}


def bulk_row(model: dict, firmware: dict, sim: dict, slot: int = 1, **overrides) -> dict:
    """A valid row of the bulk-upload payload (names, not ids)."""
    imei = unique_imei()
    row = {
        "imei": imei,
        "serial_number": "AUTOBLK" + imei[-8:],
        "device_model": model["model_name"],
        "sim_module": sim["module_name"],
        "firmware": firmware["version"],
        "slot_id": f"S{slot}",
        "primary_mobile_number": "9" + imei[-9:],
        "secondary_mobile_number": "8" + imei[-9:],
        "iccid": "8991" + imei + "0",
        "valid_till": "2030-12-31",
    }
    return {**row, **overrides}


def find_oem_account(admin: ApiClient, oem: ApiClient) -> dict:
    """The admin's record of the OEM that the OEM login belongs to (matched on the user id)."""
    me = oem.get("/api/auth/me").json()["data"]
    for record in admin.all_items(f"{API_PREFIX}/oems"):  # every page: the list has more than 100 OEMs
        if record.get("user_id") == me["id"]:
            return record
    raise AssertionError("The OEM login does not belong to any OEM that the admin can see")


@dataclass
class OemDeviceLab:
    """Master data + devices of the OEM under test, with guaranteed cleanup."""

    admin: ApiClient
    oem: ApiClient
    masters: OemMgmtApi = None
    model: dict = None
    firmware: dict = None
    sim: dict = None
    _devices: list[dict] = field(default_factory=list)
    _allocations: dict[int, list[str]] = field(default_factory=dict)  # allocation id -> IMEIs it holds

    # ── setup ────────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, admin: ApiClient, oem: ApiClient) -> "OemDeviceLab":
        lab = cls(admin, oem)
        lab.masters = OemMgmtApi(admin, find_oem_account(admin, oem))
        lab.model = lab.masters.create_model()
        lab.firmware = lab.masters.create_firmware(lab.model["id"])
        lab.sim = lab.masters.create_sim()
        return lab

    def another_model_with_firmware(self) -> tuple[dict, dict]:
        """A second Device Model of the same OEM with its own Firmware (for 'firmware of another model' checks)."""
        model = self.masters.create_model()
        return model, self.masters.create_firmware(model["id"])

    # ── devices ──────────────────────────────────────────────────────────────

    def register(self, **overrides) -> dict:
        """Register a device and remember it for cleanup. Returns the created record (with `id` and `imei`)."""
        body = device_body(self.model, self.firmware, self.sim, **overrides)
        response = self.oem.post(DEVICES, json=body)
        assert response.status == 201, f"device registration failed: {response.status} {response.text()[:300]}"
        record = response.json()["data"]
        self._devices.append(record)
        return record

    def post_device(self, body: dict):
        """POST a (possibly invalid) device. If the server wrongly accepts it, the device is still cleaned up."""
        response = self.oem.post(DEVICES, json=body)
        if response.status == 201:
            self._devices.append(response.json()["data"])
        return response

    def adopt(self, *imeis: str) -> None:
        """Remember devices created outside the lab (UI form, bulk upload) so that cleanup removes them."""
        for imei in imeis:
            for record in self.oem.get(f"{DEVICES}?per_page=100&search={imei}").json()["data"]:
                if record["imei"] == imei and all(d["id"] != record["id"] for d in self._devices):
                    self._devices.append(record)

    def devices_total(self) -> int:
        return self.oem.get(f"{DEVICES}?per_page=1").json()["meta"]["pagination"]["total"]

    def inventory_status(self, device: dict) -> str:
        return self.oem.get(f"{DEVICES}/{device['id']}").json()["data"]["inventory_status"]

    def totals(self) -> dict:
        return self.oem.get("/api/dashboard/oem/device-inventory").json()["data"]

    # ── allocation ───────────────────────────────────────────────────────────

    def allocate(self, fitment_centre_id: int, *devices: dict):
        """POST an allocation. The response is returned unchecked; successful ones are remembered for rollback."""
        response = self.oem.post(ALLOCATIONS, json={"fitment_centre_id": fitment_centre_id, "imeis": [d["imei"] for d in devices]})
        if response.status == 201:
            self._allocations[response.json()["data"]["id"]] = [d["imei"] for d in devices]
        return response

    def track_allocation(self, allocation_id: int, *devices: dict) -> None:
        """Remember an allocation made outside the lab (UI wizard) so that cleanup rolls it back."""
        self._allocations[allocation_id] = [d["imei"] for d in devices]

    def allocation_summary(self) -> dict:
        return self.oem.get("/api/dashboard/oem/allocation-summary").json()["data"]

    def allocation(self, allocation_id: int) -> dict:
        return self.oem.get(f"{ALLOCATIONS}/{allocation_id}").json()["data"]

    def rollback(self, allocation_id: int, *devices: dict):
        return self.oem.post(
            f"{ALLOCATIONS}/{allocation_id}/rollback",
            json={"allocation_id": allocation_id, "imeis": [d["imei"] for d in devices]},
        )

    # ── cleanup ──────────────────────────────────────────────────────────────

    def release_devices(self) -> None:
        """Roll back every allocation made through this lab, then delete every device registered through it."""
        for allocation_id, imeis in self._allocations.items():  # a second rollback of the same allocation is simply refused
            self.oem.post(f"{ALLOCATIONS}/{allocation_id}/rollback", json={"allocation_id": allocation_id, "imeis": imeis})
        self._allocations.clear()
        for device in self._devices:
            self.oem.delete(f"{DEVICES}/{device['id']}")
        self._devices.clear()

    def cleanup(self) -> None:
        self.release_devices()
        if self.masters:
            self.masters.cleanup()


def create_oem_account(admin: ApiClient) -> dict:
    """Register a throw-away OEM through the admin API. Returns {'id', 'email', 'password'}.

    OEMs cannot be deleted (the application has no delete for them); the cleanup report lists them for the DB owner.
    """
    from utils import data_generator as data
    from utils.oem_mgmt_api import pdf_file

    d = data.oem_data()
    pdf = pdf_file()
    response = admin.post(
        f"{API_PREFIX}/oems",
        multipart={
            "business_name": d.business_name, "code": d.code, "cin_number": d.cin, "gst_number": d.gst,
            "tac_no": d.tac_number, "cop_no": d.cop_number, "tac_issued_on": "2026-01-15",
            "cop_valid_from": "2026-01-01", "cop_valid_till": "2026-12-31",
            "address_line_1": d.address, "address_line_2": d.address_line_2, "pincode": d.pincode,
            "contact_person_name": d.contact_name, "contact_email": d.email, "contact_phone": d.mobile,
            "password": d.password, "password_confirmation": d.password,
            "gst_certificate": pdf, "tac_certificate": pdf, "cop_certificate": pdf,
        },
    )
    assert response.status == 201, f"OEM creation failed: {response.status} {response.text()[:300]}"
    return {"id": response.json()["data"]["oem_id"], "email": d.email, "password": d.password}


# ── Fitment centres ───────────────────────────────────────────────────────────

FC_ACTIONS = {"suspend": "deactivate", "activate": "activate", "blacklist": "blacklist"}  # UI action -> endpoint
FC_STATUS_AFTER = {"suspend": "suspended", "activate": "active", "blacklist": "blacklisted"}


def fitment_centre_fields(oem: ApiClient, tag: str | None = None, **overrides) -> dict:
    """Valid registration fields (without the image) for a centre that has never existed: unique code, e-mail and mobile number."""
    tag = tag or data.unique_suffix()
    return {
        "business_name": f"AUTO PG FC {tag}", "short_name": f"AUTO{tag[-8:]}", "owner_name": "Auto Owner", "contact_no": "9" + tag[-9:],
        "email_id": f"auto.fc.{tag}@example.com", "address_line_1": "Automation Road 1", "address_line_2": "",
        "city_id": str(oem.get("/api/masters/cities").json()["data"][0]["id"]), "pincode": "110001", "latitude": "28.6139", "longitude": "77.209",
        "rto_id": str(oem.get("/api/rto-dropdown").json()["data"][0]["id"]), "password": data.PASSWORD, "password_confirmation": data.PASSWORD,
        **overrides,
    }


def register_fitment_centre(oem: ApiClient, **overrides) -> dict:
    """Register a centre through the API (a real record plus a login account; the application cannot delete either). Returns the stored centre."""
    fields = fitment_centre_fields(oem, **overrides)
    response = oem.request("POST", FITMENT_CENTRES, multipart={**fields, "fitment_centre_image": {"name": "fc.png", "mimeType": "image/png", "buffer": png_bytes()}})
    assert response.status == 201, f"fitment centre registration failed: {response.status} {response.text()[:300]}"
    return find_fitment_centre(oem, fields["short_name"])


def find_fitment_centre(oem: ApiClient, code: str) -> dict | None:
    listed = oem.get(f"{FITMENT_CENTRES}?per_page=100&search={code}").json()["data"]
    return next((fc for fc in listed if fc["short_name"] == code), None)


def fitment_centre(oem: ApiClient, fc_id: int) -> dict:
    return oem.get(f"{FITMENT_CENTRES}/{fc_id}").json()["data"]["fitment_centre"]


def fitment_centre_remarks(oem: ApiClient, fc_id: int) -> list[dict]:
    """The status history, newest first."""
    return oem.get(f"{FITMENT_CENTRES}/{fc_id}").json()["data"]["remarks"]


def edit_fitment_centre(oem: ApiClient, fc: dict, **changes):
    """Edit through the API: the stored values are sent back with `changes` applied (every mandatory field is required again)."""
    fields = {
        "business_name": fc["business_name"], "short_name": fc["short_name"], "owner_name": fc["owner_name"], "contact_no": fc["contact_no"],
        "email_id": fc["email_id"], "address_line_1": fc["address"]["address_line_1"], "address_line_2": fc["address"]["address_line_2"] or "",
        "city_id": str(fc["address"]["city"]["id"]), "pincode": fc["address"]["pincode"], "latitude": fc["latitude"], "longitude": fc["longitude"],
        "rto_id": str(fc["rto"]["id"]),
    }
    return oem.request("POST", f"{FITMENT_CENTRES}/{fc['id']}", multipart={**fields, **changes})


def change_fitment_centre_status(client: ApiClient, fc_id: int, action: str, remarks: str = "AUTO PG status change"):
    """`action` is the button name: suspend, activate or blacklist."""
    return client.patch(f"{FITMENT_CENTRES}/{fc_id}/{FC_ACTIONS[action]}", json={"remarks": remarks})
