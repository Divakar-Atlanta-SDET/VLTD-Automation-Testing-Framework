"""
Safety-net cleanup of the data the automated tests leave behind.

Per-test cleanup already happens in the fixtures (`records` removes what a test created). This module is the
last line of defence: it runs ONCE at the end of a test run (see `pytest_terminal_summary` in conftest.py, after
every parallel worker has finished) and also from the command line:

    python -m utils.cleanup

What it does, and why only this much:
  - DELETES leftover Device Models, Firmware and SIM Modules created by tests (names starting "AUTO" or with a
    12-digit timestamp). The persistent "AUTO PG" seed (12+ records per list, kept on purpose for the pagination
    tests) is never touched.
  - DEACTIVATES test staff accounts ("Auto Staff ..."): the application cannot delete staff, and left active they
    would stay usable with a known password.
  - REPORTS what only the database owner can remove, because the application offers no delete for it
    (OEMs, RTOs, Drivers, Inspectors, Help Centres).

Opt out of the automatic run with:  pytest --keep-test-data
"""

import os
import re
from dataclasses import dataclass, field

from utils.api_client import API_PREFIX, ApiClient
from utils.oem_mgmt_api import FIRMWARES, MODELS, SEED_PREFIX, SIMS

# Test-created OEM Management records: "AUTO ..." (but not the seed) or a 12-digit timestamp followed by padding.
TEST_NAME = re.compile(r"^(AUTO(?! PG)|\d{12}|PG\d{12})")
TEST_STAFF_NAME = re.compile(r"^(Auto Staff|<script>alert\(1\)</script>)")
PAGE = 100

# (label, list endpoint, how to read the record's display name) for data the app cannot delete
NOT_REMOVABLE = [
    ("OEMs", f"{API_PREFIX}/oems", lambda i: str(i.get("business_name", "")), re.compile(r"^(AUTO OEM|A{20,})")),
    ("RTOs", f"{API_PREFIX}/rtos", lambda i: str(i.get("business_name", "")), re.compile(r"^AUTO RTO")),
    ("Drivers", f"{API_PREFIX}/drivers", lambda i: str((i.get("user") or {}).get("name", "")), re.compile(r"^Auto Driver")),
    ("Inspectors", f"{API_PREFIX}/inspectors", lambda i: str(i.get("name", "")), re.compile(r"^Auto Inspector")),
    ("Help Centres", "/api/tracking/help-centres", lambda i: str(i.get("name", "")), re.compile(r"^AUTO HC")),
]


@dataclass
class CleanupReport:
    deleted: dict[str, int] = field(default_factory=lambda: {"firmware": 0, "sim": 0, "model": 0})
    deactivated_staff: int = 0
    failed: list[str] = field(default_factory=list)
    left_for_db_owner: dict[str, int] = field(default_factory=dict)

    def lines(self) -> list[str]:
        deleted = ", ".join(f"{n} {kind}" for kind, n in self.deleted.items())
        out = [
            f"deleted leftover OEM Management records: {deleted}",
            f"deactivated test staff accounts: {self.deactivated_staff}",
        ]
        if self.failed:
            out.append(f"could not remove ({len(self.failed)}): " + "; ".join(self.failed[:6]) + (" ..." if len(self.failed) > 6 else ""))
        owner = {k: v for k, v in self.left_for_db_owner.items() if v}
        if owner:
            out.append("remaining for the DB owner (the app cannot delete these): " + ", ".join(f"{v} {k}" for k, v in owner.items()))
        out.append(f"kept on purpose: the '{SEED_PREFIX}' seed records (12+ per OEM Management list)")
        return out


def all_items(api: ApiClient, path: str) -> list[dict]:
    """Every item of a paginated list endpoint."""
    items: list[dict] = []
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        response = api.get(f"{path}{sep}per_page={PAGE}&page={page}")
        if not response.ok:
            return items
        body = response.json()
        data = body["data"]
        items += data.get("data", []) if isinstance(data, dict) else data
        if not (body.get("meta") or {}).get("pagination", {}).get("has_more"):
            return items
        page += 1


class TestDataCleaner:
    __test__ = False  # not a pytest test class

    def __init__(self, admin: ApiClient) -> None:
        self.admin = admin

    def sweep(self) -> CleanupReport:
        report = CleanupReport()
        self._sweep_oem_management(report)
        self._deactivate_test_staff(report)
        self._count_remaining(report)
        return report

    # ── OEM Management (deletable) ───────────────────────────────────────────

    def _sweep_oem_management(self, report: CleanupReport) -> None:
        # children first: firmware depends on models
        for kind, path, name_key, owner_of in (
            ("firmware", FIRMWARES, "version", lambda i: (i.get("device_model") or {}).get("oem_id")),
            ("sim", SIMS, "module_name", lambda i: i.get("oem_id")),
            ("model", MODELS, "model_name", lambda i: i.get("oem_id")),
        ):
            for item in all_items(self.admin, path):
                name = str(item.get(name_key, ""))
                if not TEST_NAME.match(name):
                    continue
                oem_id = owner_of(item)
                if oem_id is None:  # its device model is gone (BUG-029): the app refuses to delete it
                    report.left_for_db_owner["Orphaned firmware"] = report.left_for_db_owner.get("Orphaned firmware", 0) + 1
                    continue
                response = self.admin.delete(f"{path}/{item['id']}?oem_id={oem_id}")
                if response.status == 200:
                    report.deleted[kind] += 1
                else:
                    report.failed.append(f"{kind} '{name}' -> {response.status}")

    # ── staff (cannot be deleted, so deactivate) ─────────────────────────────

    def _deactivate_test_staff(self, report: CleanupReport) -> None:
        for staff in all_items(self.admin, f"{API_PREFIX}/staff"):
            if not TEST_STAFF_NAME.match(str(staff.get("name", ""))) or staff.get("status") != "approved":
                continue
            response = self.admin.patch(
                f"{API_PREFIX}/staff/{staff['id']}/deactivate", json={"remarks": "automated test cleanup"}
            )
            if response.ok:
                report.deactivated_staff += 1
            else:
                report.failed.append(f"staff '{staff['name']}' -> {response.status}")

    # ── what only the DB owner can remove ────────────────────────────────────

    def _count_remaining(self, report: CleanupReport) -> None:
        for label, path, name_of, pattern in NOT_REMOVABLE:
            report.left_for_db_owner[label] = sum(1 for i in all_items(self.admin, path) if pattern.match(name_of(i)))


def main() -> None:
    from dotenv import load_dotenv
    from playwright.sync_api import sync_playwright

    load_dotenv()
    base = os.environ["BASE_URL"].split("/auth")[0].rstrip("/")
    origin = "/".join(base.split("/")[:3])
    with sync_playwright() as p:
        request = p.request.new_context()
        admin = ApiClient.login(request, origin, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
        report = TestDataCleaner(admin).sweep()
        request.dispose()
    print("\n".join(report.lines()))


if __name__ == "__main__":
    main()
