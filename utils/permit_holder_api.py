"""
Permit Holder (Fleet Owner) panel API constants.

Mirrors the conventions of `utils/role_panel_api.py` / `utils/fc_panel_api.py`. Confirmed by live network
capture during the first dedicated exploration of this panel (2026-11-14, see
`specs/permit-holder-test-plan.md`), not guessed.
"""

VEHICLE_LIST = "/api/permit-holder/vehicle"
VEHICLE_DETAIL = "/api/permit-holder/vehicle/{vehicle_id}"
STAFF = "/api/permit-holder/staff"  # backend works; no UI page reaches it - see BUG-090

WATCHLISTS = "/api/tracking/watchlists"
WATCHLIST_DETAIL = "/api/tracking/watchlists/{watchlist_id}"
WATCHLIST_ITEMS = "/api/tracking/watchlists/{watchlist_id}/items"
WATCHLIST_ITEM = "/api/tracking/watchlists/{watchlist_id}/items/{vehicle_id}"
WATCHLIST_HISTORY = "/api/tracking/watchlists/history"
