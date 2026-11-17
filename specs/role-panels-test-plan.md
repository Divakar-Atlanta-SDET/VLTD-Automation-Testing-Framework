# Driver / RTO Inspector / RTO Officer / Permit Holder - Test Plan & Results

Scope: the four remaining Admin > User Management roles not yet covered by this project's automation
(`tests/administration/`, `tests/fc_panel/`, `tests/oem_panel/` already cover OEM, TC Staff and the Fitment
Centre). Explored and automated 2026-11-10, reading `VLTD_How_It_Works.pdf` chapters 4, 5, 6.3-6.5, 15, 17.3 and
18 first, then the live app as each role.

## 1. Accounts created

| Role | Env vars | Created via | Login verified |
|---|---|---|---|
| RTO Officer | `RTO_USERNAME` / `RTO_PASSWORD` | Admin UI, `/tc/users/rto` > Register RTO (code `DL-96`) | Yes - UI and API |
| RTO Inspector | `INSPECTOR_USERNAME` / `INSPECTOR_PASSWORD` | Admin UI, `/tc/users/inspector` > Add Inspector, explicitly assigned to RTO `DL-96` | Yes - UI and API |
| Driver | `DRIVER_USERNAME` / `DRIVER_PASSWORD` | Admin UI, `/tc/users/drivers` > Add Driver (with a licence PDF and a generated photo) | Yes - UI and API |
| Permit Holder | - | **Not created - see "Permit Holder: why no account exists" below** | N/A |

All three accounts were created once, through the application's own normal creation workflow (reusing
`pages/administration/{rto,inspector,driver}_page.py` and `utils/data_generator.py`, already built for the
Admin-side "Register/Add" creation tests in `specs/user-management-create-test-plan.md`). Each account's forced
first-login password change (`is_password_change_required: true` in the login response, under `data.user`,
same field FC/OEM accounts use) was settled once through `POST /api/auth/change-password`, then the **final**
password was written to `.env`. Credentials are never logged, printed or committed (`.env` is in `.gitignore`;
this repository is not currently a git working tree, so there is no push/commit risk either way). No shared
account's password was touched - these are brand-new, dedicated, long-lived accounts, independent of `ADMIN_*`,
`OEM_*` and `FC_USERNAME`.

The app has no delete action for RTO, Inspector or Driver records (same as OEM - see
`specs/user-management-create-test-plan.md`, "Risks"), so these three accounts are permanent additions to the
shared environment, the same way the existing `OEM_*`/`FC_USERNAME` accounts are.

## 2. Permit Holder: why no account exists

Per the guide (`VLTD_How_It_Works.pdf`, glossary and chapter 6.7 of `VLTD_Admin_Panel_Complete_Explanation.md`):
**"Permit Holder is created by Fitment Center during fitment"** - there is no Admin, RTO or self-service creation
path. Confirmed live:

- Admin's Permit Holder list (`/tc/users/permit-holders`) and RTO's own (`/rto/users/permit-holders`) are both
  strictly view-only - no Register/Add/Create button on either (also covered by the existing
  `test_user_creation.py::test_admin_cannot_create_fitment_center_or_permit_holder`, UM-06).
- Traced the only other creation path - the Fitment Centre's New Installation wizard, Step 1 (Vehicle). Fetching
  a fresh, never-before-used vehicle from VAHAN (`GET /api/vahan/vehicle/{reg_no}`) returns a complete, read-only
  owner block (name, email, mobile, address) with **no field anywhere in the step for the FC to set a password**
  for that owner. The owner/Permit Holder account is created automatically, with a system-generated password
  neither the FC, the Admin, nor the RTO can see or set.
- The login page has no "Forgot password" / self-service recovery link at all (checked directly - the only
  links on `/auth/login` are navigation, Support Centre and ticket tracking).
- 20+ real Permit Holder (`fleet-manager`) records already exist in this environment from earlier installations
  (`GET /api/transport-commissioner/fleet-managers`), confirming the auto-creation happens - but their
  passwords are unknown and unrecoverable through any screen or API this project's accounts can reach.

**Conclusion:** a dedicated Permit Holder test account cannot be created or accessed through any legitimate,
available path in this environment. This is a genuine **dependency blocker**, not a defect to fix on our side -
per the task's own instruction ("do not invent credentials or pretend accounts were created"), no Permit Holder
account was created and no Permit Holder panel testing was attempted. If this needs to be unblocked, it requires
either (a) a developer-provided way to set/reset a Permit Holder's password (none currently exists, anywhere),
or (b) completing a full New Installation end-to-end so a real owner can go through whatever out-of-band
credential-issuance exists in production (SMS/email), which is itself blocked by BUG-080 before it would even
matter. Credential-guessing against the existing synthetic Permit Holder accounts was considered and
**deliberately not attempted** - it would not be a legitimate "normal onboarding workflow" check, and the
platform correctly gives no indication such accounts use a predictable/default password.

## 3. Role/permission matrix (from `GET /api/auth/me`, each account's own token)

| Role | Role code | Own panel | Key permissions (abbreviated) |
|---|---|---|---|
| RTO Officer | `rto_officer` | `/rto/dashboard` | `vltd_device_installations.approval.{view,approve,reject}`, `fleet_managers.{view,activate,suspend,blacklist}`, `challans.{view,approve,issue}`, `tracking.*`, `watchlists.*`, `alerts.view`, `reports.view`, `device_commands.view` |
| RTO Inspector | `rto_inspector` | `/inspector/dashboard` | `inspector.{vehicle_owner,fitment_validity,vehicle_driver,challan_masters}.view`, `inspector.challans.{create,view}`, **and, incorrectly, `vltd_device_installations.{view,approval.view,approval.approve,approval.reject}` - see BUG-086** |
| Driver | `driver` | `/driver/dashboard` | none listed beyond its own duty/vehicle/owner reads (no `permissions` array entries observed under this role in `/api/auth/me`) |
| Permit Holder | - | (Fleet Owner panel - not reachable, see §2) | not tested |

Per the guide's role table (chapter 5), Inspector's job is "roadside checks, draft challans and the RTO
installation reports" - **installation approval is listed only for RTO Officer**. The Inspector role having the
approval permissions anyway is BUG-086 (High) - see `bug_report.md`.

## 4. What each role can/cannot do (confirmed live, 2026-11-10)

**RTO Officer** (`rto_page` / `rto_api` fixtures, `tests/role_panels/test_rto_panel.py`)
- Dashboard: installation/approval counters and a live-fleet summary, all correctly **0** for this brand-new
  RTO's jurisdiction (no vehicles/installations under `DL-96` yet) - verified against the API, not just the UI.
- Installation Approvals (Pending / Approved / Rejected), Permit Holder Management (view-only, matches Admin),
  Challan Work Queue, and two Device reports all load cleanly, correctly empty.
- Cannot reach Admin (`/tc/*`), OEM, FC, Inspector or Driver pages (redirected to `/unauthorized`); its token is
  refused (403) by Driver-only API reads.
- **Not tested: approving/rejecting a real installation** - no installation in this environment has ever reached
  the pending-approval state, because BUG-080 blocks every installation at Step 3 (Health Check), long before
  Step 8 ("submitted to RTO"). This is a hard environmental dependency on BUG-080 being fixed, not something
  this test plan can work around.

**RTO Inspector** (`inspector_page` / `inspector_api`, `tests/role_panels/test_inspector_panel.py`)
- Dashboard shows challan/penalty summaries (correctly 0 for a fresh account) but **wrongly shows "0 Assigned
  RTOs"** despite being assigned to `DL-96` - BUG-085.
- Verify Fitment correctly reports a known installation's real, current state (`DL04CA1028`, stuck at Health
  Check per BUG-080 - reports `installation_status: in_progress`, not a false "active"), and correctly 404s an
  unknown plate.
- Draft Challan and My Challans load correctly; My Challans is correctly empty (matches the API).
- Cannot reach Admin/OEM/FC/RTO/Driver pages (redirected to `/unauthorized`).
- **Security gap:** the Inspector's own token passes the RTO-only installation-approval authorization check
  (BUG-086) - not reachable through the UI (the menu is correctly hidden), but reachable directly via API.
- **Not tested: drafting a real challan** - requires either a geolocation-enabled browser context (headless
  Chromium has none, and the screen itself shows "Location permission was denied" without one) or a vehicle
  with live telemetry the inspector can be "within 1 km" of; out of scope for this pass given the time budget,
  flagged as a gap below.

**Driver** (`driver_page` / `driver_api`, `tests/role_panels/test_driver_panel.py`)
- Dashboard, Future Duties and Duty History all correctly show empty states ("No duty assigned", "No vehicle
  assigned", "No Future Duties", "No Duty History"), verified against the API (`/api/driver/duty/me`,
  `/api/driver/vehicle/me`, `/api/driver/duty/future`, `/api/driver/duty/history` all genuinely empty).
- This is **expected, not a defect**: per the guide (chapter 17.3), a Driver's duties come only from timetables
  a School builds (vehicle + mapped driver + route + weekdays); this environment has no School account that has
  mapped this Driver to anything. Testing a populated Driver duty screen would require a School test account and
  a full Vehicles/Drivers/Timetables setup, which is out of this task's scope (Driver/Inspector/RTO/Permit
  Holder only).
- Cannot reach Admin/OEM/FC/RTO/Inspector pages (redirected to `/unauthorized`); its token is refused (403) by
  RTO- and Inspector-only API reads and writes (installation-approval, installation-pending-list, challans,
  inspector dashboard).

## 5. Security / permission-boundary testing (`tests/role_panels/test_role_access_and_isolation.py`)

| Check | Result |
|---|---|
| Direct-URL access to another role's dashboard (Driver/Inspector/RTO x Admin/OEM/FC/each other) | Refused - redirected to `/unauthorized`, every combination |
| Driver's token against RTO-only reads/writes (`installations/pending`, `installations/{id}/approve`) | Refused - 403 |
| Driver's token against Inspector-only reads (`inspector/challans`, `inspector/dashboard`) | Refused - 403 |
| RTO's token against Driver-only reads (`driver/duty/me`) | Refused - 403 |
| **Inspector's token against RTO-only installation-approval reads/writes** | **Wrongly accepted - BUG-086** |
| Session/logout, token refresh, password-change session invalidation | Not re-tested per role; already confirmed **platform-wide** (not OEM/FC-specific) in the Profile module pass on 2026-11-05 - see BUG-072/073/074/075/077 in `bug_report.md`. No reason to expect Driver/Inspector/RTO behave differently (same `/api/auth/*` endpoints), but not independently re-verified here - flagged as a gap below. |

## 6. Bugs found this pass

See `bug_report.md` for full detail. Summary:

- **BUG-085 (Medium):** Inspector Dashboard always shows "0 Assigned RTOs," even when correctly assigned - a
  display-only bug; the API (`GET /api/inspector/dashboard`) returns the correct `rto_data`, the frontend just
  doesn't read it.
- **BUG-086 (High):** an RTO Inspector's token passes the RTO-only installation approve/reject authorization
  check (reaches the same 404-not-found business logic an RTO Officer gets, instead of a 403) - a role-template
  permission over-grant. Not exploitable end-to-end today only because BUG-080 means no installation ever
  reaches the approvable state.

No other defects found in this pass; every other screen and empty-state matched its own API data exactly.

## 7. Automation delivered

- `pages/role_panels/dashboard.py` - `RtoDashboardPage`, `InspectorDashboardPage`, `DriverDashboardPage` (plain
  page objects; these three panels are structurally independent of the OEM/FC hierarchy, confirmed by
  exploration, so they are not subclassed from `pages.oem_panel`/`pages.fc_panel`).
- `utils/role_panel_api.py` - endpoint constants for all three panels, confirmed by live network capture (not
  guessed): Inspector dashboard/fitment-validity/challans, RTO pending/approved/rejected installations and
  approve/reject actions, Driver duty/vehicle/owner reads.
- `tests/role_panels/conftest.py` - `rto_credentials`/`rto_api`/`rto_page`, `inspector_*`, `driver_*` fixtures,
  modelled on `tests/fc_panel/conftest.py`.
- `tests/role_panels/test_rto_panel.py`, `test_inspector_panel.py`, `test_driver_panel.py` - login, dashboard
  state vs. API, and key module smoke tests for each role (markers `rto_panel`, `inspector_panel`,
  `driver_panel`, registered in `pytest.ini`).
- `tests/role_panels/test_role_access_and_isolation.py` - the cross-role boundary matrix in §5, including the
  BUG-086 regression (`xfail`, `strict=False`, flips to an unexpected pass if the role template is fixed).
- `tests/role_panels/test_inspector_panel.py::test_dashboard_shows_the_inspectors_assigned_rto` - the BUG-085
  regression (`xfail`, `strict=False`).

**Result:** `pytest tests/role_panels/ --known-bugs` -> **43 passed, 3 xfailed** (BUG-085 x1, BUG-086 x2), 0
failed, 0 skipped. Default run (no `--known-bugs`) is 43 passed, 0 failed.

## 8. Remaining gaps and blockers

1. **Permit Holder panel: entirely untested** - no account reachable, see §2. This is the only one of the four
   target roles with zero coverage.
2. **RTO installation approve/reject, end-to-end:** cannot be exercised with a real installation anywhere in
   this environment while BUG-080 stands (no installation ever reaches the pending-approval state). Only the
   authorization *boundary* around these endpoints was tested (§5), not the approve/reject business logic
   itself (jurisdiction match, state check, notification on reject, etc. - guide chapter 6.3).
3. **Inspector's Draft Challan, end-to-end:** not exercised (needs either a geolocation-enabled browser context
   or a vehicle with live telemetry within the configured distance - out of scope for this pass). Only the
   screen load and its "location permission denied" guard were observed.
4. **Driver's populated duty/vehicle screens:** not exercised - requires a School test account and a full
   Vehicles/Drivers/Timetables setup, which is outside "Driver, Inspector, RTO, Permit Holder" scope.
5. **Session expiry / token refresh / logout, per-role:** not independently re-tested for these three roles;
   relying on the platform-wide confirmation already recorded against OEM/FC accounts (BUG-072/073/074/075/077).
6. **Challan lifecycle (approve/issue) and Fleet Manager activate/suspend/blacklist:** RTO's own permissions
   include these, but exercising them needs a real challan or a real Permit Holder record this RTO's inspector
   drafted/owns - blocked by the same two gaps above (no real challan yet, no Permit Holder access).
