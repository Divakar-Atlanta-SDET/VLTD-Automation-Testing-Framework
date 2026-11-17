"""
API constants for the Driver, RTO Inspector and RTO Officer panels.

Mirrors the conventions of `utils/fc_panel_api.py` / `utils/oem_panel_api.py`: only what the dedicated-account
exploration and automation needs so far (see `specs/role-panels-test-plan.md`).
"""

# ── Inspector ───────────────────────────────────────────────────────────────
INSPECTOR_DASHBOARD = "/api/inspector/dashboard"
INSPECTOR_FITMENT_VALIDITY = "/api/inspector/fitment-validity"  # ?parameter=<vehicle_or_chassis_number>
INSPECTOR_CHALLANS = "/api/inspector/challans"

# ── RTO Officer ───────────────────────────────────────────────────────────────
RTO_PENDING_INSTALLATIONS = "/api/rto/installations/pending"
RTO_APPROVED_INSTALLATIONS = "/api/reports/rto-approved-installations"
RTO_REJECTED_INSTALLATIONS = "/api/reports/rto-rejected-installations"


def rto_installation_approve(installation_id: int) -> str:
    return f"/api/rto/installations/{installation_id}/approve"


def rto_installation_reject(installation_id: int) -> str:
    return f"/api/rto/installations/{installation_id}/reject"


# ── Driver ──────────────────────────────────────────────────────────────────
DRIVER_DUTY_TODAY = "/api/driver/duty/me"
DRIVER_DUTY_FUTURE = "/api/driver/duty/future"
DRIVER_DUTY_HISTORY = "/api/driver/duty/history"
DRIVER_VEHICLE = "/api/driver/vehicle/me"
DRIVER_OWNER = "/api/driver/owner/me"

# ── Shared (any of the three roles) ───────────────────────────────────────────
FLEET_MANAGERS = "/api/transport-commissioner/fleet-managers"  # Permit Holders; Admin-token read-only in this suite
