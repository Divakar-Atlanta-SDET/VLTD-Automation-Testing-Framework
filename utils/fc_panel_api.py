"""
Fitment Centre panel API constants.

Mirrors the conventions of `utils/oem_panel_api.py` for the FC role. Only what the Dashboard and Operations
automation needs so far (see `specs/fitment-centre-test-plan.md`); grows as more FC modules are automated.
"""

DASHBOARD_SUMMARY = "/api/dashboard/fitment-centre/summary"
RECENT_INSTALLATIONS = "/api/dashboard/fitment-centre/recent-installations"
INSTALLATION_TREND = "/api/dashboard/fitment-centre/installation-trend"
INSTALLATIONS = "/api/installation"
TAG_DEVICE = "/api/installation/tag-device"
INVENTORY_SUMMARY = "/api/fitment-centre/inventory/summary"
VEHICLE_SUMMARY = "/api/tracking/vehicles/summary"
TRACKING_VEHICLES = "/api/tracking/vehicles"
