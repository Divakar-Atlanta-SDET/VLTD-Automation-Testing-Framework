"""
Dynamic, unique test-data generators for user-creation tests.

Every call embeds a timestamp + random suffix so unique fields (codes, emails,
licence numbers, certificate numbers) never collide between runs.
All records are tagged "AUTO" so they are easy to find and remove from the DB.
"""

import random
from dataclasses import dataclass
from datetime import datetime

PASSWORD = "Auto@12345Test"
EMAIL_DOMAIN = "example.com"


def unique_suffix() -> str:
    """12-digit timestamp + 4 random digits, e.g. '2610131230054217' (unique across parallel workers)."""
    return datetime.now().strftime("%y%m%d%H%M%S") + f"{random.randint(0, 9999):04d}"


def _digits(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


def _mobile() -> str:
    return "9" + _digits(9)


def _rto_code(taken: set[str]) -> str:
    """RTO codes must look like 'DL-99' (only 100 possible), so pick one not already in use."""
    free = [f"DL-{n:02d}" for n in range(100) if f"DL-{n:02d}" not in taken]
    if not free:
        raise RuntimeError("All 100 RTO codes (DL-00..DL-99) are in use; clean up AUTO RTOs in the DB")
    return random.choice(free)


def _licence_number() -> str:
    """Indian licence format: DL + 2-digit RTO + 4-digit year + 7 digits (15 chars, e.g. DL0420110149646)."""
    return f"DL04{random.randint(2005, 2024)}{_digits(7)}"


def _email(kind: str, suffix: str) -> str:
    return f"auto.{kind}.{suffix}@{EMAIL_DOMAIN}"


@dataclass
class OemData:
    business_name: str
    code: str
    cin: str
    gst: str
    tac_number: str
    cop_number: str
    address: str
    address_line_2: str
    pincode: str
    contact_name: str
    mobile: str
    email: str
    password: str = PASSWORD


@dataclass
class RtoData:
    name: str
    code: str
    mobile: str
    email: str
    address: str
    district: str
    pincode: str
    description: str
    password: str = PASSWORD


@dataclass
class InspectorData:
    name: str
    email: str
    mobile: str
    city: str
    address: str
    password: str = PASSWORD


@dataclass
class DriverData:
    name: str
    email: str
    mobile: str
    licence_number: str
    state: str
    city: str
    address: str
    password: str = PASSWORD


@dataclass
class StaffData:
    name: str
    email: str
    mobile: str
    permission: str
    password: str = PASSWORD


def oem_data() -> OemData:
    s = unique_suffix()
    return OemData(
        business_name=f"AUTO OEM {s}",
        code=f"AUT{s[-9:]}",
        cin=f"U72200KA2014PTC{_digits(6)}",  # 21 characters
        gst=f"07AUTOA{_digits(4)}A1Z5",  # 15 characters
        tac_number=f"TAC{s}",
        cop_number=f"COP{s}",
        address="Automation Test Road, Connaught Place",
        address_line_2="Near Central Park",
        pincode="110001",
        contact_name="Auto Tester",
        mobile=_mobile(),
        email=_email("oem", s),
    )


def rto_data(taken_codes: set[str]) -> RtoData:
    s = unique_suffix()
    return RtoData(
        name=f"AUTO RTO {s}",
        code=_rto_code(taken_codes),
        mobile=_mobile(),
        email=_email("rto", s),
        address="Automation RTO Road, New Delhi",
        district="Central Delhi",
        pincode="110002",
        description="Created by automation",
    )


def inspector_data() -> InspectorData:
    s = unique_suffix()
    return InspectorData(
        name=f"Auto Inspector {s}",
        email=_email("inspector", s),
        mobile=_mobile(),
        city="Alipur",
        address="Automation Inspector Lane, Delhi",
    )


def driver_data() -> DriverData:
    s = unique_suffix()
    return DriverData(
        name=f"Auto Driver {s}",
        email=_email("driver", s),
        mobile=_mobile(),
        licence_number=_licence_number(),
        state="Delhi",
        city="Alipur",
        address="Automation Driver Street, Delhi",
    )


def staff_data() -> StaffData:
    s = unique_suffix()
    return StaffData(
        name=f"Auto Staff {s}",
        email=_email("staff", s),
        mobile=_mobile(),
        permission="View Alerts",
    )


# ── OEM Management (Device Models, Firmware, SIM Modules) ─────────────────────

@dataclass
class DeviceModelData:
    model_name: str
    part_no: str
    tac_name: str  # the "TAC Number" field
    tac_issued_on: str = "2026-01-15"  # must not be in the future
    network_profile_name: str = "AUTO-4G"
    description: str = "Created by automation"


@dataclass
class FirmwareData:
    version: str
    release_date: str = "2026-02-01"
    release_notes: str = "Created by automation"


@dataclass
class SimModuleData:
    sim_manufacturer: str
    module_name: str
    primary_operator: str = "Airtel"
    primary_sim_type: str = "eSIM"
    secondary_operator: str = "Jio"
    secondary_sim_type: str = "Physical"


def device_model_data() -> DeviceModelData:
    s = unique_suffix()
    return DeviceModelData(model_name=f"AUTO DM {s}", part_no=f"PN{s}", tac_name=f"TAC{s}")


def firmware_data() -> FirmwareData:
    return FirmwareData(version=f"AUTO-{unique_suffix()[-8:]}")


def sim_module_data() -> SimModuleData:
    s = unique_suffix()
    return SimModuleData(sim_manufacturer=f"AUTO MFG {s[-6:]}", module_name=f"AUTO SIM {s}")
