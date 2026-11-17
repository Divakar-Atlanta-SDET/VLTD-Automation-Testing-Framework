"""
API helper for the OEM Management module (Device Models, Firmware, SIM Modules).

Tests create the records they need through the API (fast, and independent of the UI under test) and
register them for deletion, so nothing is left behind - except the deliberate "AUTO PG" seed records
that keep every list above one page (12+ records) for the pagination checks.

Endpoints (admin token):
  /api/device-models      multipart on create (the TAC certificate is a PDF file); JSON accepted on update
  /api/device-firmwares   JSON
  /api/sim-modules        JSON
  DELETE needs `?oem_id=<owner>` - without it the server answers 422 "Select an OEM."
"""

import time
from dataclasses import asdict

from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.file_utils import TEST_PDF

MODELS = "/api/device-models"
FIRMWARES = "/api/device-firmwares"
SIMS = "/api/sim-modules"

SEED_PREFIX = "AUTO PG"
SEED_TARGET = 12  # every list should hold at least this many records (one page is 10)


def pdf_file(name: str = "tac.pdf", content: bytes | None = None) -> dict:
    """A multipart file part for Playwright's request API."""
    return {
        "name": name,
        "mimeType": "application/pdf",
        "buffer": content if content is not None else TEST_PDF.read_bytes(),
    }


class OemMgmtApi:
    """Create / read / delete OEM Management records for the OEM that owns the test data."""

    def __init__(self, admin: ApiClient, owner: dict | None = None) -> None:
        self.admin = admin
        if owner is None:
            owners = [
                o for o in admin.list_items(f"{API_PREFIX}/oems?per_page=100")
                if str(o.get("business_name", "")).startswith("AUTO OEM 2")
            ]
            assert owners, "No 'AUTO OEM' record found - run tests/administration/test_user_creation.py::test_register_oem first"
            owner = owners[0]
        self.oem = owner
        self.oem_id: int = self.oem["id"]
        self.oem_name: str = self.oem["business_name"]
        self._created: list[tuple[str, int]] = []
        self._firmware_model: dict[int, int] = {}

    # ── create ───────────────────────────────────────────────────────────────

    def create_model(self, model: data.DeviceModelData | None = None, **overrides) -> dict:
        m = model or data.device_model_data()
        certificate = overrides.pop("tac_certificate", None) or pdf_file()
        fields = {**asdict(m), **overrides}
        multipart = {"oem_id": str(self.oem_id), **{k: str(v) for k, v in fields.items() if v is not None}}
        multipart["tac_certificate"] = certificate
        response = self.admin.post(MODELS, multipart=multipart)
        assert response.status == 201, f"create model failed: {response.status} {response.text()[:200]}"
        record = response.json()["data"]
        self._created.append(("model", record["id"]))
        return record

    def create_firmware(self, model_id: int, firmware: data.FirmwareData | None = None, **overrides) -> dict:
        f = firmware or data.firmware_data()
        body = {"oem_id": self.oem_id, "device_model_id": model_id, "is_active": True, **asdict(f), **overrides}
        response = self.admin.post(FIRMWARES, json=body)
        assert response.status == 201, f"create firmware failed: {response.status} {response.text()[:200]}"
        record = response.json()["data"]
        self._created.append(("firmware", record["id"]))
        self._firmware_model[record["id"]] = model_id
        return record

    def create_sim(self, sim: data.SimModuleData | None = None, **overrides) -> dict:
        s = sim or data.sim_module_data()
        body = {"oem_id": self.oem_id, "is_active": True, **asdict(s), **overrides}
        response = self.admin.post(SIMS, json=body)
        assert response.status == 201, f"create sim failed: {response.status} {response.text()[:200]}"
        record = response.json()["data"]
        self._created.append(("sim", record["id"]))
        return record

    # ── delete / cleanup ─────────────────────────────────────────────────────

    @staticmethod
    def _path(kind: str) -> str:
        return {"model": MODELS, "firmware": FIRMWARES, "sim": SIMS}[kind]

    def track(self, kind: str, record_id: int) -> None:
        """Register a record created elsewhere (e.g. through the UI) for cleanup."""
        self._created.append((kind, record_id))

    def delete(self, kind: str, record_id: int, attempts: int = 3) -> int:
        """Delete a record, retrying when the portal is slow or briefly unavailable. 200 and 404 both mean 'gone'."""
        status = 0
        for attempt in range(attempts):
            status = self.admin.delete(f"{self._path(kind)}/{record_id}?oem_id={self.oem_id}").status
            if status in (200, 404):
                return status
            time.sleep(1 + attempt)
        return status

    def cleanup(self) -> None:
        """Delete everything this helper created.

        Firmware goes first. A device model is only deleted when none of its firmware is left: the server lets a model be
        deleted while it still has firmware (BUG-029) and the orphaned firmware could then never be removed.
        """
        blocked_models: set[int] = set()
        for kind, record_id in [c for c in self._created if c[0] == "firmware"]:
            if self.delete(kind, record_id) not in (200, 404):
                blocked_models.add(self._firmware_model.get(record_id))
        for kind, record_id in [c for c in self._created if c[0] == "sim"]:
            self.delete(kind, record_id)
        for kind, record_id in [c for c in self._created if c[0] == "model"]:
            if record_id not in blocked_models:
                self.delete(kind, record_id)
        self._created.clear()
        self._firmware_model.clear()

    # ── read ─────────────────────────────────────────────────────────────────

    def total(self, kind: str) -> int:
        return self.admin.get(f"{self._path(kind)}?per_page=1").json()["meta"]["pagination"]["total"]

    def exists(self, kind: str, record_id: int) -> bool:
        return self.admin.get(f"{self._path(kind)}/{record_id}").status == 200

    def first_seed(self, kind: str) -> dict:
        """A persistent 'AUTO PG' seed record (stable: never created or deleted by a running test)."""
        key = {"model": "model_name", "firmware": "version", "sim": "module_name"}[kind]
        page = 1
        while True:
            body = self.admin.get(f"{self._path(kind)}?per_page=50&page={page}").json()
            for item in body["data"]:
                if str(item.get(key, "")).startswith(SEED_PREFIX):
                    return item
            if not body["meta"]["pagination"]["has_more"]:
                raise AssertionError(f"no '{SEED_PREFIX}' {kind} record - ensure_seed() should have created one")
            page += 1

    def find(self, kind: str, key: str, value: str) -> dict | None:
        """First record whose `key` equals `value` (walks every page)."""
        page = 1
        while True:
            body = self.admin.get(f"{self._path(kind)}?per_page=50&page={page}").json()
            for item in body["data"]:
                if item.get(key) == value:
                    return item
            if not body["meta"]["pagination"]["has_more"]:
                return None
            page += 1

    # ── persistent seed so every list spans more than one page ───────────────

    def ensure_seed(self, target: int = SEED_TARGET) -> None:
        """Top every list up to `target` records. Seed records are named 'AUTO PG ...' and are never deleted."""
        host = self._seed_host_model()
        n = 0
        while self.total("firmware") < target:
            n += 1
            self.admin.post(FIRMWARES, json={
                "oem_id": self.oem_id, "device_model_id": host, "version": f"{SEED_PREFIX}-{n:02d}",
                "release_date": "2026-02-01", "is_active": True,
            })  # a 422 just means that number is already taken - try the next one
            assert n < 200, "could not seed firmware"
        n = 0
        while self.total("sim") < target:
            n += 1
            self.admin.post(SIMS, json={
                "oem_id": self.oem_id, "sim_manufacturer": "AUTO PG MFG", "module_name": f"{SEED_PREFIX} SIM {n:02d}",
                "is_active": True,
            })
            assert n < 200, "could not seed SIM modules"
        n = 0
        while self.total("model") < target:
            n += 1
            self._create_seed_model(n)
            assert n < 200, "could not seed device models"

    def _seed_host_model(self) -> int:
        existing = self.find("model", "model_name", f"{SEED_PREFIX} DM 01")
        if existing:
            return existing["id"]
        return self._create_seed_model(1)["id"]

    def _create_seed_model(self, n: int) -> dict:
        s = data.unique_suffix()
        response = self.admin.post(MODELS, multipart={
            "oem_id": str(self.oem_id), "model_name": f"{SEED_PREFIX} DM {n:02d}", "part_no": f"PG{n:02d}-{s}",
            "tac_name": f"PGTAC{n:02d}-{s}", "tac_issued_on": "2026-01-15", "tac_certificate": pdf_file(),
        })
        return response.json().get("data") or {"id": None}
