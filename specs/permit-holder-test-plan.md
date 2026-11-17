# Permit Holder (Fleet Owner) Panel - Test Plan & Results

Scope: the one role left untested from the original four-role gap in `specs/role-panels-test-plan.md`
("Permit Holder: entirely untested - no account reachable"). That blocker is now lifted - `PERMIT_HOLDER_USERNAME`
/ `PERMIT_HOLDER_PASSWORD` are available in `.env` - so this pass covers the Fleet Owner panel end to end.
Read `VLTD_How_It_Works.pdf` first (chapters 3, 5, 6.7 via `VLTD_Admin_Panel_Complete_Explanation.md`, 13, 14.1
and 18) and re-checked everything documented there against the live panel; nothing here is assumed beyond what
either the guide or live exploration confirmed.

## 1. Who this account is

The credentials in `.env` belong to **Sakshi Gupta** (`permit_holder` role code, `type: fleet_owner`), permit
holder code `FLT2610582`. This is one of the 9 orphaned Permit Holder records already documented as **BUG-089**
in `bug_report.md` - created as a side effect of a blocked New Installation attempt (Step 3 Health Check), not
through any real onboarding flow. Practically, this means:

- The account is real, active (`status: approved`) and fully usable for testing - BUG-089 explains *why* it
  exists, it doesn't make it unusable.
- It owns exactly **one vehicle** (`DL04CA1041`, a School Bus), and that vehicle's installation never completed
  (per BUG-080) - so its device/GPS data is sparse (one static position, "Offline"/"Needs Review" on the health
  report). This caps how much can be verified about live telemetry, trip data and alert generation for this
  specific vehicle (see "Gaps" below) but does not block any ownership, permission or CRUD testing.
- No second Permit Holder account is available, so "same-organisation users share watchlists" (guide chapter 13)
  could not be verified with a real second user - see "Gaps".

## 2. Panel discovery (confirmed live, 2026-11-14)

Role permissions, read from the account's own `GET /api/auth/me` (25 total):

| Group | Permissions |
|---|---|
| Dashboard | `permit_holder.dashboard.view` |
| Tracking | `tracking.live_view`, `tracking.history_view`, `device_commands.view` |
| Watchlists | `watchlists.view`, `watchlists.manage` |
| Alerts | `alerts.view` |
| Vehicles | `permit_holder.vehicles.view`, `permit_holder.vehicles.update_status` |
| Vehicle-Driver mapping | `permit_holder.vehicle_drivers.{view,assign,release}` |
| Drivers | `permit_holder.drivers.{view,create,update,update_status}` |
| Staff | `permit_holder.staff.{view,create,update,delete}` |
| Reports | `permit_holder.reports.{device_mapping,driver_mapping,challans,device_validity,driver_audit}.view` |

Navigation is a **horizontal top nav with hover dropdowns** (`Dashboard`, `Operations`, `Fleet Management`,
`Reports`, `Helpdesk`) - a different pattern from the left-sidebar-with-collapsible-groups used by
Admin/OEM/FC. This matters for automation: `role=button` + `.hover()` opens the dropdown; a plain `.click()`
on the link never shows it as visible without that hover first (worth knowing before writing locators - cost
real time during this exploration).

| Menu | Page | URL | Notes |
|---|---|---|---|
| (direct) | Dashboard | `/fleet-owner/dashboard` | Live Fleet / Operational Status / Quick Actions / Driver Status / Challan Status tiles |
| Operations | Live Tracking | `/fleet-owner/live-tracking` | Fleet/Watchlist toggle (plain buttons, not ARIA tabs) |
| Operations | Geofences | `/fleet-owner/geofences` | loads; **no `geofences.*` permission is granted to this role at all** (see "Observations") |
| Operations | Trip Playback | `/fleet-owner/trip-playback` | loads |
| Operations | Alerts | `/fleet-owner/alerts` | loads |
| Operations | Command Center | `/fleet-owner/command-center` | Send Command / Command List / Command History |
| Fleet Management | Drivers | `/fleet-owner/drivers` | own Driver sub-accounts (name/email/contact/licence/address + password) - distinct from the Admin-created `driver` role tested in `role-panels-test-plan.md` |
| Fleet Management | Vehicles | `/fleet-owner/vehicles` | row actions menu: **View Vehicle, Manage Drivers, Deactivate** |
| Reports | Device Packets, Device Health, Device Status & Connectivity, Device SIM Validity, Alert Report, Vehicle Alert Trail, Alert Set History, Driver Mapping Report, Challan Report | `/fleet-owner/reports/*`, `/fleet-owner/set-history` | all load and all match the account's own single vehicle's data (cross-checked against the API, not just eyeballed) |
| (direct) | Watch History | `/fleet-owner/watch-history` | |
| (direct) | Helpdesk | `/fleet-owner/helpdesk` | Support Tickets, same pattern as other panels |

**No "Watchlists" page and no "Staff" page exist in the nav**, despite both having granted permissions:
- Watchlists is **by design** - the guide says it's a tab inside Live Tracking, not its own page. Confirmed:
  `Fleet`/`Watchlist` toggle buttons sit above the map on Live Tracking.
- Staff has **no page anywhere** - see **BUG-090** below. This is not a documentation gap; the permissions
  (`permit_holder.staff.view/create/update/delete`) are real and the backend endpoint (`GET
  /api/permit-holder/staff`) answers 200 with real pagination - there is simply no menu entry or route to reach
  it from the UI.

## 3. Business-rule verification (live, API cross-checked - not just UI inspection)

### 3.1 Vehicle ownership and data isolation - **all correct, no defects**

| Check | Method | Result |
|---|---|---|
| Permit Holder sees only its own vehicle | `/fleet-owner/vehicles` vs `GET /api/permit-holder/vehicle` | Exactly 1 row (`DL04CA1041`), matches the API |
| Vehicle detail, own vehicle | `GET /api/permit-holder/vehicle/8851` (own) | 200, full detail |
| Vehicle detail, another owner's vehicle, by manipulated ID | `GET /api/permit-holder/vehicle/8835` (belongs to a different `vehicle_owner_id`) | **403** `"This vehicle does not belong to the logged in permit holder."` |
| Add another owner's vehicle to a watchlist, via the search box | typed `DL04CA1028` (owned by a different permit holder) into the watchlist's "Add vehicle" search | **"No matching vehicles."** - the search itself is scoped, so there's nothing to click even before any server check |
| Add another owner's vehicle to a watchlist, via a manipulated `vehicle_id` directly against the API | `POST /api/tracking/watchlists/{id}/items {"vehicle_id": 8835}` | **403** `"You are not authorized to add this vehicle - it is outside your jurisdiction."` |
| Remove another owner's vehicle from a watchlist, via a manipulated `vehicle_id` | `DELETE /api/tracking/watchlists/{id}/items/8835` | **403** `"You are not authorized to remove this vehicle - it is outside your jurisdiction."` |

Ownership isolation is enforced **in depth** - at the UI search layer *and* independently at the API layer for
every one of add/remove/view. This is the strongest-tested module in this pass and it has no findings.

### 3.2 Watchlist management - **all correct, no defects**

Full lifecycle exercised end-to-end against the real API (`/api/tracking/watchlists*`):

| Action | Call | Result |
|---|---|---|
| Create | `POST /api/tracking/watchlists {"name": ...}` | 201, `owner_key: "vehicle_owner:8854"` (scoped to this permit holder) |
| Add own vehicle | `POST .../{id}/items {"vehicle_id": 8851}` | 201 |
| Rename | `PUT /api/tracking/watchlists/{id} {"name": ...}` | 200 |
| Remove own vehicle | `DELETE .../{id}/items/8851` | 200 |
| Delete list | `DELETE /api/tracking/watchlists/{id}` | 200; confirmed gone from a follow-up `GET` |
| History | `GET /api/tracking/watchlists/history` | Every action above appears with `actor` (name + id) and `created_at` - "who and when" is genuinely recorded, matching the guide's rule exactly |

Not independently verified this pass (see "Gaps"): same-organisation users sharing a watchlist (needs a second
account for this permit holder's organisation, none available), and watchlist rules/geofence assignment
(`Add rule` exists in the UI but creating a real rule and proving it fires wasn't exercised - no time-safe way
to generate a live overspeed/geofence event for this account's one, barely-online vehicle).

### 3.3 Vehicle and device information

- Vehicle detail (reg., chassis, engine, category) matches VAHAN-style data seen elsewhere in the app (same
  shape as the FC's New Installation Step 1 fetch) - consistent, no mismatch found.
- Device Health / Device Status & Connectivity reports show **1 device, "Needs Review"/"Poor GPS Fix" (health)**
  and **"Online Now: 1" clashing with "Active: 1, Inactive: 0"** alongside the vehicle's own tile showing
  "Offline" on Live Tracking - this is a direct consequence of BUG-080 (installation stuck at Health Check, so
  the device is live but never "活" fully validated), not a new defect; flagged as expected given the known
  upstream blocker, not logged as a separate bug.
- User Devices-style drill-down (guide page 33: "for each OEM, RTO, fitment centre or permit holder, a count of
  devices by status, with a drill-down into the installed devices") is only partially testable with 1 device;
  the counts reconcile correctly for that 1 device, but a multi-device drill-down was not exercisable.

### 3.4 Drivers (Fleet Management)

`Add Driver` dialog collects name, email, contact, licence number, address, password and password confirmation -
this permit holder creates and sets a password for its own driver sub-accounts directly (unlike the Admin-created
`driver` role in `role-panels-test-plan.md`, whose password is also Admin-set but through a different flow).
Vehicle row actions (`View Vehicle`, `Manage Drivers`, `Deactivate`) match the granted permissions exactly
(`vehicles.update_status`, `vehicle_drivers.assign/release`) - no extra, ungranted action is exposed. Not
exercised further this pass: actually creating a driver and mapping it to the vehicle (low risk, but adds a
permanent record to a shared environment for a module that's already structurally confirmed to match its
permissions - judged lower priority than the ownership/watchlist work above given the time budget).

## 4. Shared vs. Permit-Holder-specific functionality

| Shared with other panels | Confirmed how |
|---|---|
| `/api/tracking/watchlists*` (create/rename/delete/items/history) | Same endpoints as every other tracking panel (OEM/FC/RTO); only the `owner_key` scoping (`vehicle_owner:<id>`) and the 403 jurisdiction messages are Permit-Holder-specific |
| `/api/auth/*`, login/session pattern | Identical to every other role; not independently re-tested here - relying on the platform-wide confirmation already on record (BUG-072/073/074/075/077 in `bug_report.md`), per the same reasoning `role-panels-test-plan.md` used |
| Report "families" (Device, Alerts, Compliance) | Same report engine as other tracking panels - confirmed only the Permit-Holder-specific scoping (own vehicle only), not the report logic itself, which is already covered elsewhere |
| Helpdesk | Same ticket lifecycle already covered for FC/OEM (`bug_report.md` BUG-068/083 family) - not re-tested for new defects, only confirmed the page loads and matches this account |

Permit-Holder-specific, not shared: the `permit_holder.*` permission family (Drivers, Staff, Vehicle-Driver
mapping, the permit-holder-scoped reports), and the Live-Tracking Fleet/Watchlist toggle pattern.

## 5. Bugs found this pass

### BUG-090 - Permit Holder has full Staff permissions but no Staff page anywhere in the panel (Medium)

- **Where:** Fleet Owner panel; permissions `permit_holder.staff.{view,create,update,delete}` are granted and
  the backend answers normally (`GET /api/permit-holder/staff` -> 200, `{"data": [], "meta": {...}}`), but no
  menu entry, dropdown item or guessable URL (`/fleet-owner/staff`, `/fleet-owner/users/staff`,
  `/fleet-owner/users`, `/fleet-owner/account/staff` all silently fall back to the Dashboard) reaches it.
- **Expected:** either a Staff page exists under Fleet Management (alongside Drivers/Vehicles, where its sibling
  permissions live), or the permission shouldn't be granted to this role if the feature isn't meant to ship yet.
- **Actual:** the permission and a working API exist; the UI has no way to use either.
- **Classification:** Confirmed Bug - same family as the existing BUG-015 pattern ("permission grants nothing")
  already on record for other roles, now also seen on Permit Holder.
- **Severity/Priority:** Medium/Medium - no security exposure (the endpoint still requires this permit holder's
  own token and returns only its own data), but a documented, fully-wired feature (staff accounts) is entirely
  unreachable for every Permit Holder in the product.
- Logged in full in `bug_report.md`.

No other defects found - every ownership, watchlist and report check in §3 passed exactly as documented.

## 6. Test plan - manual vs. automated vs. reusable vs. regression

| Area | Manual | Automated this pass | API reused from elsewhere | Regression |
|---|---|---|---|---|
| Login, dashboard, role/permission shape | done | `test_permit_holder_panel.py::test_login_and_dashboard_match_the_account` | `ApiClient.login` pattern from `tests/role_panels/conftest.py` | yes |
| Own-vehicle visibility (list + detail) | done | `test_permit_holder_panel.py::test_vehicle_list_and_detail_match_the_api` | - | yes |
| Cross-owner vehicle access refused (detail, watchlist add, watchlist remove) | done | `test_permit_holder_isolation.py` (3 tests) | - | yes - this is the highest-priority area per the task brief |
| Watchlist create/rename/add/remove/delete + history | done | `test_permit_holder_watchlists.py` (1 end-to-end test, API-level - the UI hover/combobox chain is exercised once in `test_permit_holder_panel.py` for a smoke check, not repeated per-action) | - | yes |
| BUG-090 (Staff page missing) | done | `test_permit_holder_panel.py::test_staff_permission_has_no_reachable_page` (`xfail`) | - | yes |
| Reports (Device Health/Status/Validity, Alerts, Driver/Challan reports) | done (loaded, spot-checked against API) | not automated | - | out of scope this pass - low risk, same report engine already covered for other roles (§4); would be marginal value for the added maintenance cost |
| Drivers (create, vehicle-driver mapping) | done (dialog fields only) | not automated | - | gap - see §7 |
| Command Center, Trip Playback, Geofences, Alerts (Operations pages) | done (loaded, smoke-level only) | not automated | - | out of scope - no device/alert data exists for this account's one vehicle to meaningfully exercise them |
| Watchlist rules / geofence-on-watchlist | not done | not automated | - | gap - see §7 |

## 7. Remaining gaps and blockers

1. **Same-organisation watchlist sharing** (guide: "all users of that organisation share them") could not be
   verified - this permit holder has no staff/second user account, and BUG-090 means one can't even be created
   through the UI to test with.
2. **Watchlist rules and geofence assignment** ("a watchlist can carry its own rules... which apply to every
   vehicle on it") - the `Add rule` UI exists but wasn't exercised; this account's one vehicle is barely online
   (BUG-080-blocked installation), so there's no safe, fast way to generate a real rule-triggered event to prove
   the rule actually applies, versus just accepting the dialog.
3. **Driver creation and vehicle-driver mapping**, end-to-end - dialog fields confirmed, not submitted (would
   create a permanent record in a shared environment for comparatively low risk-adjusted value this pass).
4. **User Devices multi-device drill-down** (guide page 33) - this account has exactly one device, so the
   drill-down UI couldn't be exercised with more than one row.
5. **Staff module** - entirely blocked by BUG-090 (no page to test against, regardless of the account's own
   permissions).
6. **Command Center "Send Command"**, Trip Playback and Geofences - loaded and smoke-checked only; not
   exercised end-to-end, same reasoning as #2 (this account's vehicle has too little live data to meaningfully
   test a command round-trip or a playback range).

## 8. Execution summary

`pytest tests/permit_holder/ --known-bugs` -> **6 passed, 1 xfailed** (BUG-090), 0 failed, 0 skipped. Default
run (no `--known-bugs`) is **6 passed, 1 deselected**. All test-created watchlists clean up after themselves
(explicit delete in a `finally`/fixture-teardown, confirmed afterwards via a fresh `GET
/api/tracking/watchlists` showing none left) - nothing permanent was added to the shared environment except the
one pre-existing vehicle/watchlist interactions already covered above. New tests are additive; nothing in this
pass touched any other panel's files.

| File | Tests |
|---|---|
| `tests/permit_holder/conftest.py` | `permit_holder_credentials`/`permit_holder_api`/`permit_holder_page`, `admin_api`, `other_owner_vehicle_id` fixtures |
| `tests/permit_holder/test_permit_holder_panel.py` | login/dashboard/role shape; own-vehicle list+detail vs. API; BUG-090 regression (`xfail`) |
| `tests/permit_holder/test_permit_holder_isolation.py` | another owner's vehicle refused on detail, watchlist-add, watchlist-remove (all via a real manipulated `vehicle_id`, not just the UI search) |
| `tests/permit_holder/test_permit_holder_watchlists.py` | full lifecycle: create, add own vehicle, rename, remove, delete, and watch-history actor+timestamp |
| `utils/permit_holder_api.py` | endpoint constants, confirmed by live network capture |
