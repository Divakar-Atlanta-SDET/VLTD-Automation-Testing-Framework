"""
Permission model of the TC portal: which API call ("probe") is governed by which permission.

How probes stay harmless
------------------------
- Reads are GET list calls.
- Creates are `POST {}`: the permission check runs before validation, so a permitted caller gets
  422 (nothing is created) and a denied caller gets 403.
- Updates / status changes target throw-away "Auto…" records created by the automated tests
  (never real data). Only the 403-vs-not-403 outcome matters, so the business result is irrelevant.

A probe is "allowed" when the answer is anything other than 403 (200, 422, 404-after-lookup …).

Each probe belongs to one category:
  PERMISSIONED  governed by one permission (the normal case)
  OPEN          needs no permission – every TC staff user may use it (no permission exists for it)
  RESTRICTED    Transport-Commissioner-only: no staff permission unlocks it
"""

from dataclasses import dataclass

TC = "/api/transport-commissioner"
MAIN = "https://vltd.misbackend.com"
GO = "https://vltdgo.misbackend.com"  # alert / command / geofence services


@dataclass(frozen=True)
class Probe:
    key: str
    method: str
    path: str  # may contain {oem} {rto} {ins} {drv} {tgt} {imei} {model} {fw} {sim} {hc}
    permission: str | None  # governing permission code (None for OPEN / RESTRICTED)
    category: str = "PERMISSIONED"
    body: dict | None = None
    host: str = MAIN

    @property
    def writes(self) -> bool:
        return self.method != "GET"


def _get(key, path, permission, category="PERMISSIONED", host=MAIN) -> Probe:
    return Probe(key, "GET", path, permission, category, None, host)


def _post(key, path, permission, category="PERMISSIONED", body=None, method="POST") -> Probe:
    return Probe(key, method, path, permission, category, {} if body is None else body)


def _delete(key, path, permission) -> Probe:
    """DELETE with an invalid `oem_id`: a permitted caller gets 422 and nothing is deleted; a denied one gets 403."""
    return Probe(key, "DELETE", path + "?oem_id=abc", permission, "PERMISSIONED", None)


PROBES: list[Probe] = [
    # ── Alerts / commands / geofences (separate "go" services) ───────────────
    _get("alerts_list", "/alert/api/alerts", "alerts.view", host=GO),
    _get("commands_list", "/command/api/commands", "device_commands.view", host=GO),
    _get("geofences_list", "/geofence/api/geofences", "tracking.live_view", host=GO),
    # ── Tracking ─────────────────────────────────────────────────────────────
    _get("tracking_vehicles", "/api/tracking/vehicles", "tracking.live_view"),
    _get("vehicle_clusters", "/api/tracking/vehicles/clusters", "tracking.live_view"),
    _get("tracking_oems", "/api/tracking/oems", "tracking.live_view"),
    _get("fleet_operators", "/api/tracking/fleet-operators", "tracking.live_view"),
    _get("tracking_fitment_centres", "/api/tracking/fitment-centres", "tracking.live_view"),
    _get("device_health", "/api/tracking/devices/health", "tracking.live_view"),
    _get("device_packets", "/api/tracking/devices/packets", "tracking.live_view"),
    _get("device_status_report", "/api/tracking/devices/status-report", "tracking.live_view"),
    _get(
        "trip_history",
        "/api/history?imei={imei}&from=2026-10-01T00:00:00Z&to=2026-10-01T01:00:00Z&limit=1",
        "tracking.history_view",
        host=GO,
    ),
    _get("watchlists_list", "/api/tracking/watchlists", "watchlists.view"),
    _get("watchlist_history", "/api/tracking/watchlists/history", "watchlists.view"),
    _post("watchlist_create", "/api/tracking/watchlists", "watchlists.manage"),
    _get("alert_report", "/api/tracking/alerts/report", "alerts.view"),
    # ── Reports ──────────────────────────────────────────────────────────────
    _get("device_validity_report", f"{TC}/reports/device-validity", "reports.view"),
    _get("user_devices_report", f"{TC}/reports/user-devices", "reports.view"),
    # ── OEM management: models, firmware, SIM modules ────────────────────────
    _get("device_models_list", "/api/device-models", "device_models.view"),
    _post("device_model_create", "/api/device-models", "device_models.create"),
    _post("device_model_update", "/api/device-models/{model}", "device_models.update", method="PUT"),
    _delete("device_model_delete", "/api/device-models/{model}", "device_models.delete"),
    _get("device_firmwares_list", "/api/device-firmwares", "device_firmwares.view"),
    _post("device_firmware_create", "/api/device-firmwares", "device_firmwares.create"),
    _post("device_firmware_update", "/api/device-firmwares/{fw}", "device_firmwares.update", method="PUT"),
    _delete("device_firmware_delete", "/api/device-firmwares/{fw}", "device_firmwares.delete"),
    _get("sim_modules_list", "/api/sim-modules", "sim_modules.view"),
    _post("sim_module_create", "/api/sim-modules", "sim_modules.create"),
    _post("sim_module_update", "/api/sim-modules/{sim}", "sim_modules.update", method="PUT"),
    _delete("sim_module_delete", "/api/sim-modules/{sim}", "sim_modules.delete"),
    # ── Users ────────────────────────────────────────────────────────────────
    _get("oems_list", f"{TC}/oems", "oems.view"),
    _post("oem_create", f"{TC}/oems", "oems.create"),
    _post("oem_update", f"{TC}/oems/{{oem}}", "oems.update"),
    _post("oem_activate", f"{TC}/oems/{{oem}}/activate", "oems.activate", method="PATCH"),
    _post("oem_deactivate", f"{TC}/oems/{{oem}}/deactivate", "oems.deactivate", method="PATCH"),
    _post("oem_blacklist", f"{TC}/oems/{{oem}}/blacklist", "oems.blacklist", method="PATCH"),
    _get("inspectors_list", f"{TC}/inspectors", "rto.inspector.view"),
    _post("inspector_create", f"{TC}/inspectors", "rto.inspector.create"),
    _post("inspector_map_rto", f"{TC}/inspectors/{{ins}}/rtos", "rto.inspector.map", method="PUT"),
    _get("rtos_list", f"{TC}/rtos", "rtos.view"),
    _post("rto_create", f"{TC}/rtos", "rtos.create"),
    _post("rto_update", f"{TC}/rtos/{{rto}}", "rtos.update", method="PUT"),
    _get("drivers_list", f"{TC}/drivers", "tc.drivers.view"),
    _get("driver_audit", f"{TC}/drivers/audit", "tc.drivers.audit_view"),
    _post("driver_create", f"{TC}/drivers", "tc.drivers.create"),
    _post("driver_bulk_create", f"{TC}/drivers/bulk", "tc.drivers.bulk_create"),
    _post("driver_update", f"{TC}/drivers/{{drv}}", "tc.drivers.update"),
    _post("driver_status", f"{TC}/drivers/{{drv}}/status", "tc.drivers.update_status", body={"status": "active"}, method="PATCH"),
    _get("staff_list", f"{TC}/staff", "tc.view.staff"),
    _post("staff_create", f"{TC}/staff", "tc.create.staff"),
    _post("staff_update", f"{TC}/staff/{{tgt}}", "tc.update.staff", method="PATCH"),
    _post("staff_activate", f"{TC}/staff/{{tgt}}/activate", "tc.activate.staff", method="PATCH"),
    _post("staff_deactivate", f"{TC}/staff/{{tgt}}/deactivate", "tc.deactivate.staff", method="PATCH"),
    _post("staff_blacklist", f"{TC}/staff/{{tgt}}/blacklist", "tc.blacklist.staff", method="PATCH"),
    _get("fitment_centres_list", "/api/oem/fitment-centres", "fitment.centres.view"),
    _get("fleet_managers_list", f"{TC}/fleet-managers", "fleet_managers.view"),
    _get("help_centres_list", "/api/tracking/help-centres", "help_centers.view"),
    _post("help_centre_create", "/api/tracking/help-centres", "help_centers.create"),
    _post("help_centre_update", "/api/tracking/help-centres/{hc}", "help_centers.update", method="PUT"),
    _post("help_centre_activate", "/api/tracking/help-centres/{hc}/activate", "help_centers.activate", method="PATCH"),
    _post("help_centre_deactivate", "/api/tracking/help-centres/{hc}/deactivate", "help_centers.deactivate", method="PATCH"),
    _get("challans_list", f"{TC}/challans", "challans.view"),
    # ── Vehicle / device installations ───────────────────────────────────────
    _get("installation_list", "/api/installation", "vltd_device_installations.view"),
    _get("device_repairs", "/api/device-repairs", "vltd_device_installations.repair.view"),
    _get("untag_search", "/api/installation/untag-search", "vltd_device_installations.untag"),
    # ── OPEN: usable by any TC staff, no permission exists for them ──────────
    _get("dashboard", f"{TC}/dashboard", None, "OPEN"),
    _get("routes_list", f"{TC}/routes", None, "OPEN"),
    _get("stops_list", f"{TC}/stops", None, "OPEN"),
    _get("challan_masters_list", f"{TC}/challan-masters", None, "OPEN"),
    _get("multiple_challan_report", f"{TC}/reports/multiple-challan-vehicles", None, "OPEN"),
    _get("helpdesk_tickets", "/api/helpdesk/tickets", None, "OPEN"),
    _get("permissions_list", f"{TC}/permissions", None, "OPEN"),
    _post("route_create", f"{TC}/routes", None, "OPEN"),
    _post("stop_create", f"{TC}/stops", None, "OPEN"),
    _post("challan_master_create", f"{TC}/challan-masters", None, "OPEN"),
    # ── RESTRICTED: Transport Commissioner only ──────────────────────────────
    _get("announcements_list", f"{TC}/announcements", None, "RESTRICTED"),
    _get("system_configuration", f"{TC}/system-configuration", None, "RESTRICTED"),
    _get("account_merge_report", f"{TC}/account-merge/report", None, "RESTRICTED"),
    _get("ownership_transfer_report", f"{TC}/ownership-transfer/report", None, "RESTRICTED"),
    _get("installation_performance", "/api/reports/installation-performance", None, "RESTRICTED"),
    _get("command_templates", "/api/device-command-templates", None, "RESTRICTED"),
    _post("announcement_create", f"{TC}/announcements", None, "RESTRICTED"),
    _post("fitment_centre_create", "/api/oem/fitment-centres", None, "RESTRICTED"),
    _post("command_template_create", "/api/device-command-templates", None, "RESTRICTED"),
]

PROBE_BY_KEY = {p.key: p for p in PROBES}
PERMISSIONED = [p for p in PROBES if p.category == "PERMISSIONED"]
OPEN = [p for p in PROBES if p.category == "OPEN"]
RESTRICTED = [p for p in PROBES if p.category == "RESTRICTED"]

# ── Known deviations (documented in bug_report.md) ────────────────────────────

# Governed by a permission, but a staff user WITHOUT it still gets through.
UNGATED = {
    "alerts_list": "BUG-014",
    "commands_list": "BUG-014",
    "geofences_list": "BUG-014",
    "trip_history": "BUG-014",  # GPS points of a device, returned to staff with no permission
}

# Governed by a permission, but even a staff user WITH EVERY permission is refused (403):
# the endpoint is Transport-Commissioner-only, so the permission has no effect.
INEFFECTIVE = {
    key: "BUG-015"
    for key in (
        "rtos_list", "rto_create", "rto_update",
        "staff_list", "staff_create", "staff_update", "staff_activate", "staff_deactivate", "staff_blacklist",
        "fleet_managers_list", "challans_list",
        "installation_list", "device_repairs", "untag_search",
    )
}

# Probes the generic matrix tests assert on (the deviations above get their own explicit tests).
CHECKED = [p for p in PERMISSIONED if p.key not in UNGATED and p.key not in INEFFECTIVE]

# ── Permissions that no safe probe can exercise ───────────────────────────────

NOT_EXERCISED = {
    "fitment.centres.activate": "Fitment Centres are created by OEMs; changing a real centre is unsafe",
    "fitment.centres.deactivate": "Fitment Centres are created by OEMs; changing a real centre is unsafe",
    "fitment.centres.blacklist": "Fitment Centres are created by OEMs; changing a real centre is unsafe",
    "fleet_managers.activate": "Permit Holders are created by Fitment Centres; changing a real one is unsafe",
    "fleet_managers.suspend": "Permit Holders are created by Fitment Centres; changing a real one is unsafe",
    "fleet_managers.blacklist": "Permit Holders are created by Fitment Centres; changing a real one is unsafe",
    "challans.approve": "no challan exists to act on",
    "challans.issue": "no challan exists to act on",
    "reports.export": "no export endpoint could be identified from the application",
}

# ── Navigation: menu entry -> permission that the front-end requires ──────────
# Taken from the application's own navigation definition (its declared intent).

NAV_PERMISSION = {
    "/tc/alerts": "alerts.view",
    "/tc/erss": "alerts.view",
    "/tc/command-center": "device_commands.view",
    "/tc/live-tracking": "tracking.live_view",
    "/tc/geofences": "tracking.live_view",
    "/tc/set-history": "tracking.live_view",
    "/tc/trip-playback": "tracking.history_view",
    "/tc/watch-history": "watchlists.view",
    "/tc/help-centers": "help_centers.view",
    "/tc/oem-management/device-models": "device_models.view",
    "/tc/oem-management/firmware": "device_firmwares.view",
    "/tc/oem-management/sim-modules": "sim_modules.view",
    "/tc/users/drivers": "tc.drivers.view",
    "/tc/users/fc": "fitment.centres.view",
    "/tc/users/inspector": "rto.inspector.view",
    "/tc/users/oem": "oems.view",
    "/tc/users/permit-holders": "fleet_managers.view",
    "/tc/users/rto": "rtos.view",
    "/tc/users/staff": "tc.view.staff",
    "/tc/reports/alerts": "reports.view",
    "/tc/reports/device-health": "reports.view",
    "/tc/reports/device-packets": "reports.view",
    "/tc/reports/device-status": "reports.view",
    "/tc/reports/device-validity": "reports.view",
    "/tc/reports/installation-status": "reports.view",
    "/tc/reports/maintenance": "reports.view",
    "/tc/reports/oem-performance": "reports.view",
    "/tc/reports/user-devices": "reports.view",
    "/tc/reports/vehicle-activity": "reports.view",
    "/tc/reports/vehicle-alert-trail": "reports.view",
}

# Menu entries shown to every staff user (no permission declared).
NAV_OPEN = [
    "/tc/dashboard",
    "/tc/helpdesk",
    "/tc/announcements",
    "/tc/challan-master",
    "/tc/challans",
    "/tc/configuration",
    "/tc/operations/account-merge",
    "/tc/operations/pis-management/routes",
    "/tc/operations/pis-management/service-calendars",
    "/tc/operations/pis-management/service-patterns",
    "/tc/operations/pis-management/stops",
    "/tc/operations/pis-management/timetables",
    "/tc/operations/pis-management/trips",
    "/tc/operations/vehicle-device-untag",
    "/tc/operations/vehicle-ownership-transfer",
    "/tc/reports/account-merges",
    "/tc/reports/multiple-challan-vehicles",
    "/tc/reports/ownership-transfers",
]
