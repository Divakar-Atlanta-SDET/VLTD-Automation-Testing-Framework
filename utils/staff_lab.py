"""
A throw-away "lab" for permission tests.

It creates, through the admin API:
  - a PROBER staff account whose permissions the tests change at will (changes apply immediately,
    even to a token that was already issued – verified against the application),
  - a TARGET staff account that the status-change probes (activate / deactivate / blacklist) act on,
and looks up the "Auto…" records (OEM, RTO, Inspector, Driver) left by the automated creation tests,
which the update / status probes act on. Nothing that belongs to real users is ever touched.
"""

from dataclasses import dataclass, field
from typing import Iterable

from utils import data_generator as data
from utils.api_client import API_PREFIX, ApiClient
from utils.oem_mgmt_api import OemMgmtApi
from utils.permissions_matrix import Probe

NEW_PASSWORD = "Changed@12345Pw"


@dataclass
class StaffAccount:
    id: str
    name: str
    email: str
    mobile: str
    password: str  # current (working) password


@dataclass
class StaffLab:
    admin: ApiClient
    prober: StaffAccount = None
    target: StaffAccount = None
    permission_ids: dict[str, int] = field(default_factory=dict)
    targets: dict[str, object] = field(default_factory=dict)
    _client: ApiClient = None

    # ── setup ────────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, admin: ApiClient) -> "StaffLab":
        lab = cls(admin)
        perms = admin.get(f"{API_PREFIX}/permissions").json()["data"]["permissions"]
        lab.permission_ids = {p["code"]: p["id"] for p in perms}
        lab.prober = lab.new_staff()
        lab.target = lab.new_staff()
        seed = OemMgmtApi(admin)
        seed.ensure_seed()
        lab.targets = {
            "oem": lab._first_auto(f"{API_PREFIX}/oems", lambda i: str(i.get("business_name", "")).startswith("AUTO OEM")),
            "rto": lab._first_auto(f"{API_PREFIX}/rtos", lambda i: str(i.get("business_name", "")).startswith("AUTO RTO")),
            "ins": lab._first_auto(f"{API_PREFIX}/inspectors", lambda i: str(i.get("name", "")).startswith("Auto Inspector")),
            "drv": lab._first_auto(
                f"{API_PREFIX}/drivers", lambda i: str((i.get("user") or {}).get("email", "")).startswith("auto.driver")
            ),
            "tgt": lab.target.id,
            "imei": lab._first_imei(),
            # the permanent 'AUTO PG' seed records: other tests create and delete records all the time,
            # so "the first record of the list" would sometimes vanish in the middle of a probe
            "model": seed.first_seed("model")["id"],
            "fw": seed.first_seed("firmware")["id"],
            "sim": seed.first_seed("sim")["id"],
            "hc": lab._new_help_centre(),
        }
        missing = [k for k, v in lab.targets.items() if v is None]
        assert not missing, (
            f"No 'Auto…' (or installed-device) {missing} record found. Run tests/administration/test_user_creation.py first "
            "(it creates the throw-away OEM, RTO, Inspector and Driver these tests act on)."
        )
        lab._client = ApiClient.login(admin.api, admin.origin, lab.prober.email, lab.prober.password)
        return lab

    def _first_id(self, path: str):
        items = self.admin.list_items(path)
        return items[0]["id"] if items else None

    LAB_HELP_CENTRE = "AUTO HC lab"

    def _new_help_centre(self) -> int:
        """The Help Centre the activate / deactivate / update probes act on.

        The application cannot delete Help Centres, so ONE is created the first time and reused by every later run.
        """
        for centre in self.admin.list_items("/api/tracking/help-centres?per_page=100"):
            if str(centre.get("name", "")).startswith(self.LAB_HELP_CENTRE):
                return centre["id"]
        created = self.admin.post(
            "/api/tracking/help-centres",
            json={
                "name": self.LAB_HELP_CENTRE, "type": "government", "category": "hospital",
                "city_id": self.admin.first_id("/api/masters/cities"), "latitude": 28.6, "longitude": 77.2,
            },
        )
        assert created.status == 201, created.text()[:300]
        return created.json()["data"]["id"]

    def _first_imei(self) -> str | None:
        """IMEI of any installed device (read-only lookup used by the trip-history probe)."""
        for vehicle in self.admin.list_items("/api/tracking/vehicles?per_page=20"):
            installation = vehicle.get("current_device_installation") or {}
            imei = (installation.get("device") or {}).get("imei")
            if imei:
                return imei
        return None

    def _first_auto(self, path: str, match) -> object | None:
        for item in self.admin.list_items(path + "?per_page=100"):
            if match(item):
                return item["id"]
        return None

    def new_staff(self, complete_first_login: bool = True) -> StaffAccount:
        """Create a staff account with NO permissions; by default also replace its temporary password."""
        s = data.staff_data()
        body = {
            "name": s.name, "email": s.email, "contact_no": s.mobile,
            "password": s.password, "password_confirmation": s.password, "permission_ids": [],
        }
        created = self.admin.post(f"{API_PREFIX}/staff", json=body)
        assert created.status == 201, created.text()[:300]
        account = StaffAccount(created.json()["data"]["id"], s.name, s.email, s.mobile, s.password)
        if complete_first_login:
            self.complete_first_login(account)
        return account

    def complete_first_login(self, account: StaffAccount) -> None:
        """New staff must change their temporary password before the UI lets them in."""
        client = ApiClient.login(self.admin.api, self.admin.origin, account.email, account.password)
        changed = client.post(
            "/api/auth/change-password",
            json={
                "current_password": account.password,
                "new_password": NEW_PASSWORD,
                "new_password_confirmation": NEW_PASSWORD,
            },
        )
        assert changed.ok, changed.text()[:300]
        account.password = NEW_PASSWORD

    # ── permissions ──────────────────────────────────────────────────────────

    def grant(self, codes: Iterable[str]) -> None:
        """Make the prober hold EXACTLY these permissions."""
        p = self.prober
        response = self.admin.patch(
            f"{API_PREFIX}/staff/{p.id}",
            json={
                "name": p.name, "email": p.email, "contact_no": p.mobile,
                "permission_ids": [self.permission_ids[c] for c in codes],
            },
        )
        assert response.status == 200, response.text()[:300]

    def grant_all_except(self, code: str) -> None:
        self.grant([c for c in self.permission_ids if c != code])

    # ── probing ──────────────────────────────────────────────────────────────

    def url_for(self, probe: Probe) -> str:
        return probe.path.format(**{k: v for k, v in self.targets.items()})

    def status(self, probe: Probe) -> int:
        origin = probe.host
        response = self._client.request(probe.method, self.url_for(probe), json=probe.body, origin=origin)
        return response.status

    def statuses(self, probes: Iterable[Probe]) -> dict[str, int]:
        return {p.key: self.status(p) for p in probes}
