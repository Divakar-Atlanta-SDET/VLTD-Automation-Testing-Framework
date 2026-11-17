# VLTD Admin/TC Portal – Login & Dashboard Test Plan

Source: `Testcases/VLTD_Risk_Based_Automation_Test_Cases.csv` (AUTH-001..009, DASH-001..003, MISC-001),
`VLTD_Admin_Panel_Complete_Explanation.md` §4, and a dashboard snapshot of `/tc/dashboard`
(`.playwright-mcp/page-2026-10-09T06-39-14-990Z.yml`).

Assumptions: every scenario starts from a fresh browser context (no cookies/storage). Admin/TC credentials
come from `.env` (`ADMIN_*`, `TC_*`, `OEM_*`). Data-dependent numbers are never hard-coded; they are reconciled
against each other or against the API response the page itself loads.

---

## Part A – Login coverage gap analysis

| CSV ID | Scenario | Existing in `tests/test_login.py` | Gap |
|---|---|---|---|
| AUTH-001 | Valid login → session + correct landing/role | URL only (`test_valid_admin_login`) | **Add** role/landing assertions (heading, role label, session persists on reload) |
| AUTH-002 | Invalid creds rejected safely | URL only (`test_invalid_credentials_stays_on_login`) | **Add** visible safe error, no token/cookie, no password in URL, protected page still blocked |
| AUTH-003 | Protected pages reject unauthenticated | none | **Add** UI redirect for `/tc/dashboard`, `/tc/helpdesk` etc. (API half needs endpoint discovery) |
| AUTH-004 | Malformed/expired token rejected | none | **Add** UI: tampered stored token → redirected to login, no data |
| AUTH-005 | Logout invalidates session | none | **Add** logout, back button, reload, direct URL all blocked |
| AUTH-006/007 | Wrong role cannot use Admin/TC area | none | **Add** OEM user cannot reach `/tc/*` (UI half) |
| AUTH-009 | Script/query strings in inputs handled safely | none | **Add** XSS/SQLi-style strings in email field: no dialog, no leakage |
| – | Extra: invalid email format, whitespace, Enter-key submit, no double-submit | none | **Add** |
| – | Page load, empty form, missing email/password, show/hide, support link | exists | keep |

### Login scenarios to add (all in `tests/test_login.py`, markers `auth`, + `smoke` where noted)

**L1. Successful login lands on role-correct dashboard** (AUTH-001, smoke)
1. Open `/auth/login`; sign in with admin credentials.
2. Expect URL `/tc/dashboard`, h1 "Transport Commissioner Dashboard", "Operational Overview" visible.
3. Reload → still on dashboard (session persists).
4. Expect: no login form visible.

**L2. Invalid credentials show a safe error and create no session** (AUTH-002)
1. Sign in with unknown user + wrong password.
2. Expect: still on `/auth/login`; a generic error is visible (no "user not found" vs "wrong password" distinction, no stack trace/SQL/token text); password not in URL.
3. Expect: no auth token in localStorage/sessionStorage/cookies.
4. Navigate to `/tc/dashboard` → redirected to login.

**L3. Valid email + wrong password does not leak account existence** (AUTH-002)
1. Sign in with real admin email + wrong password.
2. Expect: error text identical to L2.

**L4. Unauthenticated access to protected routes redirects to login** (AUTH-003, smoke)
For each of `/tc/dashboard`, `/tc/helpdesk`: open directly with no session → URL ends at `/auth/login`, no dashboard content rendered.

**L5. Tampered/malformed token is rejected** (AUTH-004)
1. Log in; read the stored auth token key (discovered in run).
2. Overwrite with `garbage.token.value`; reload `/tc/dashboard`.
3. Expect: redirected to login; no KPI data visible.

**L6. Logout invalidates the session** (AUTH-005, smoke)
1. Log in; open account menu → Logout.
2. Expect: `/auth/login`.
3. Browser Back → not dashboard. Reload → login. Direct `/tc/dashboard` → login.

**L7. Non-TC role cannot access TC dashboard** (AUTH-006/007, UI half)
1. Log in as OEM user.
2. Open `/tc/dashboard` → denied/redirected; TC KPI content not shown.

**L8. Script-like and query-manipulation input is handled safely** (AUTH-009)
Parametrised payloads: `<script>alert(1)</script>`, `"><img src=x onerror=alert(1)>`, `' OR '1'='1' --`, `admin@x.com' --`.
Enter in email + password, submit. Expect: no JS dialog fired, no login, no raw SQL/stack text, still on login.

**L9. Malformed email format is rejected client-side** (negative)
`notanemail`, `a@b`, ` ` → validation shown / no navigation.

**L10. Enter key submits the form; leading/trailing whitespace in email handled** (edge)
Fill valid creds, press Enter → dashboard. (Whitespace variant: expect either trimmed success or clear error – recorded, not assumed.)

---

## Part B – Dashboard (new file `tests/test_dashboard.py`, page object `pages/dashboard_page.py`)

Pre-state: logged in as TC/Admin via `logged_in_page` fixture. Locators are role/heading based (see snapshot).

**D1. Dashboard loads all sections** (smoke)
Expect visible: h1 "Transport Commissioner Dashboard"; h2 Operational Overview, Live Fleet, Network Overview, Top RTOs by Fitments, AIS-140 Fitment Analysis, Alert Monitoring, Challan Analysis; buttons Refresh, Manage Announcements. Loading status disappears.

**D2. KPI cards render with numeric values** (DASH-001/002, smoke)
Six cards (AIS-140 Fitted Vehicles, Active Fitted Vehicles, Inactive Fitted Vehicles, Never Sent Data, Active Alerts, Challans This Month): each value matches `^\d[\d,]*$`; page text has no `NaN`, `undefined`, `null`.

**D3. KPI internal reconciliation** (DASH-001)
- Active Fitted + Inactive Fitted == AIS-140 Fitted.
- Vehicle Mix "Total Fitted" == AIS-140 Fitted; sum of class counts == total; percentages sum to ~100% (or all 0 when empty).
- Response Summary Open+Acknowledged+Action Taken (+Resolved as applicable) vs Active Alerts – assert Active Alerts == Open (observed 232 == 232), flag if the rule differs.
- Network Overview: Active ≤ Total for every entity.
- Top RTO fitted counts ≤ AIS-140 Fitted.
- Live Fleet (Moving+Idle+SOS+Offline) is consistent with fitted total (rule to be confirmed during run; recorded as soft check until confirmed).

**D4. KPI values equal the backend response** (DASH-001, API + UI)
Capture the dashboard API JSON via `page.expect_response`; compare each displayed card with the matching field. Endpoint/field names discovered at generation time with `browser_network_requests`.

**D5. Zero/empty/null KPI response renders sanely** (DASH-002)
Intercept the dashboard API with `page.route`, fulfil with zeros, then with null/missing fields, then HTTP 500. Expect: no crash, no `NaN`/`undefined`, zeros shown as `0`, `₹ 0` for penalty, empty states for Recent Major Alerts / Top RTOs, error UI (not blank page) on 500.

**D6. Refresh reloads data** (DASH-003)
1. Note "Updated HH:MM" timestamp in Live Fleet.
2. Click Refresh (page header). Expect new dashboard API request fired and no error toast.
3. Mock a changed count in the response (e.g. Active Alerts +1) → card shows new value after Refresh.
4. Live Fleet's own Refresh button updates its "Updated" label; label also states "auto every 5m".

**D7. Fitment Analysis filters** (negative/edge included)
Vehicle class options: All Vehicles, Goods Carrier, Cab / Taxi, Bus, Passenger Vehicle, Other; Period options: Daily, Weekly, Monthly (default), Yearly. For each selection: chart subtitle updates to class name, date-range label updates, no error. Selecting a class with 0 vehicles shows an empty/zero state, not a crash.

**D8. Alert Monitoring controls**
Metric (Alert Type / Response Status) × Period (Daily/Weekly/Monthly/Yearly): subtitle updates, date range label present. Recent Major Alerts rows show title, severity (High/Critical), vehicle number, status, relative time; ≤ N rows. "View All" navigates to the alerts page.

**D9. Challan Analysis controls**
Metric (Challans Issued / Penalty Amount / Violation Severity) × Period: subtitle updates. Challan Summary values numeric; Penalty Amount carries `₹`; disclaimer "Penalty amounts represent issued challans and not confirmed payment collection." visible. Total Challans on summary == "Challans This Month"/year relationship checked softly.

**D10. Dashboard navigation** (MISC-001, smoke)
- "Manage Announcements" → announcements page.
- Sidebar: Dashboard, Control & Operations, Administration, Reports, Helpdesk groups visible; Helpdesk → `/tc/helpdesk`; Dashboard link returns.
- Account menu shows department name + email; Profile/Tickets/Logout present.

**D11. Dashboard is protected and role-scoped** (AUTH-003/006)
Covered by L4 and L7; here additionally assert OEM/other role never sees TC-only KPIs.

**D12. Theme toggle persists across reload** (low priority)
Switch to dark theme → `html`/body class changes; reload → persists (soft).

**D13. Responsive smoke**
At 390×844 the dashboard renders, hamburger "Open navigation" opens the drawer with the same menu.

Out of scope here (needs separate plans): data-seeded DASH-003 with a *real* created record, large-value formatting without a controllable dataset, DB-level reconciliation.

---

## Part C – Implementation notes
- Framework: existing **Python/pytest + pytest-playwright** suite (`conftest.py`, POM in `pages/`).
- New/changed files: `pages/dashboard_page.py` (currently empty), `pages/login_page.py` (add logout/account menu helpers), `tests/test_login.py` (L1–L10), `tests/test_dashboard.py` (D1–D13), `conftest.py` (fixtures for TC/OEM logins, clean-context unauthenticated page).
- New markers `dashboard` (register in `pytest.ini`, since `--strict-markers` is on).
- Run: `pytest tests/test_login.py tests/test_dashboard.py`.
- Healing pass: failures triaged as locator drift vs genuine product defect; product defects are reported, not masked.
