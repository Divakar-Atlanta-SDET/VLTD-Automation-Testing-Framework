# TC Staff Permissions – Test Plan

Scope: the **63 permissions** an admin can tick when creating or editing a TC staff member
(`/tc/users/staff/register`, `/tc/users/staff/{id}/edit`). Goal: prove that a staff member can use a feature
**only** when they hold its permission, and that holding it really opens the feature ("positive" and "negative",
in both directions). Explored 2026-10-14. Findings are logged in `bug_report.md` (BUG-014 … BUG-020).

## 1. How permissions work in this application (found by exploration)

- Permission catalogue: `GET /api/transport-commissioner/permissions` – 63 permissions in 15 modules, each with a
  code such as `oems.view`, `tc.drivers.create`, `tracking.live_view`.
- A staff member's permissions are saved with `PATCH /api/transport-commissioner/staff/{id}` (`permission_ids`).
  **A change applies immediately, even to a token that was already issued** (verified), so one account can be reused
  for every scenario.
- The **front end** hides menu entries without the permission and its router redirects direct URLs to the
  dashboard. The **back end** answers `403` ("You do not have permission…" from route middleware, "You are not
  authorized…" from a policy).
- The permission check runs **before** validation (empty `POST` → `403` without the permission, `422` with it), but
  **after** the record lookup for `…/{id}` routes (an unknown id is `404` for everybody). This is what makes
  harmless probing possible.
- A new staff member must replace the temporary password before the UI lets them in (`/auth/change-password`).

## 2. Approach

**Safe probes** (`utils/permissions_matrix.py`) – every probe is one API call that is harmless whatever the answer:

| Kind | Probe | Permitted → | Denied → |
|---|---|---|---|
| Read | `GET` a list | 200 | 403 |
| Create | `POST {}` | 422 (nothing created) | 403 |
| Update | `PUT/PATCH {}` on a throw-away or real record | 422 | 403 |
| Delete | `DELETE …?oem_id=abc` | 422 (nothing deleted) | 403 |
| Status change | `PATCH …/activate` etc. on a throw-away "Auto…" record | any non-403 | 403 |

"Allowed" simply means *not 403*. Records that are changed are the throw-away "Auto…" ones from the creation tests, a
Help Centre and a staff member created by the lab itself – never real data.

**Staff lab** (`utils/staff_lab.py`) – one prober staff account and one target staff account per test worker; the prober's
permissions are changed with the admin API, and the same token is used for every probe.

Each probe belongs to one category: **PERMISSIONED** (governed by one permission), **OPEN** (no permission exists; any
staff may use it) or **RESTRICTED** (Transport-Commissioner-only).

## 3. Scenarios

### API (`tests/permissions/test_staff_permissions_api.py`)
| # | Scenario | Count |
|---|---|---|
| A1 | The 63 permissions on the server equal the list the tests cover (drift check); every permission has a probe or a stated reason | 2 |
| A2 | **No permission**: every gated feature is refused (403); open features still work; TC-only features stay closed even with all 63 | 3 |
| A3 | **Only permission P** (per permission): P's features open **and** every other gated feature stays closed (no leakage) | 63 |
| A4 | **Everything except P** (per permission): P's features close **and** everything else stays open (no over-removal) | 63 |
| A5 | **Permissions that should open something but don't** (BUG-015) | 14 |
| A6 | **Features that open without their permission** (BUG-014) | 4 |
| A7 | Every probed read endpoint refuses a caller with no token | 46 |
| A8 | Revoking a permission applies to a token that was already issued | 1 |

### UI (`tests/permissions/test_staff_permissions_ui.py`) – menu entries taken from the front end's own navigation definition
| # | Scenario | Count |
|---|---|---|
| U1 | **With the permission**: the menu entry exists, the page opens and loads with no 401/403/5xx call and no "Unable to load" text | 30 |
| U2 | **Without any permission**: the entry is hidden and the URL redirects to the dashboard | 30 |
| U3 | **Everything except P**: the entry is hidden and the URL redirects | 30 |
| U4 | **Entries with no permission**: what the menu shows must load; what it hides must be blocked | 18 |

### Account security (`tests/permissions/test_staff_account_security.py`)
- New staff are forced to change the temporary password in the UI; skipping the screen is impossible.
- The API enforces the same rule (BUG-018).
- A malformed record id gives 404, never a server error (BUG-019) – 10 resources.

## 4. Coverage of the 63 permissions

| Result | Permissions | How |
|---|---|---|
| Verified positive **and** negative | 38 | A3 + A4 (+ U1–U3 for those with a menu entry) |
| Granted but **no effect** (the API refuses staff even with all 63) | 14 | A5 / U1 – `rtos.*` (3), `tc.*.staff` (6), `fleet_managers.view`, `challans.view`, `vltd_device_installations.*` (3) |
| **Not enforced** (feature opens without it) | 2 | A6 – `device_commands.view`, `tracking.history_view` (plus parts of `alerts.view`, `tracking.live_view`) |
| Not exercised – no safe target | 9 | `fitment.centres.activate/deactivate/blacklist`, `fleet_managers.activate/suspend/blacklist`, `challans.approve/issue`, `reports.export` (they need a real Fitment Centre / Permit Holder / challan, or no endpoint could be identified) |

## 5. Out of scope / follow-ups
- The 9 permissions above need a disposable Fitment Centre, Permit Holder and challan (or a test OEM/FC login).
- Role-based access for non-TC roles (OEM, RTO, Inspector) – blocked by the invalid `OEM_USERNAME` / `TC_USERNAME` in `.env`.
- Data scoping (a staff member seeing only some vehicles) was not examined.

## 6. Test data
The lab creates 2 staff accounts and 1 Help Centre per test worker per run (`Auto Staff …`, `AUTO HC lab …`), plus
one staff per account-security test. All are tagged for cleanup by the DB owner.
