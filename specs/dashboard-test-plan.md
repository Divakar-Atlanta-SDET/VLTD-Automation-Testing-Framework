# VLTD Transport Commissioner Dashboard Test Plan

## Application Overview

The VLTD portal's Transport Commissioner dashboard (`/tc/dashboard`) is the landing page after an admin/TC login. It
summarises statewide AIS-140 fitment, alert and challan activity:

- Six KPI tiles, a Live Fleet strip (Moving, Idle, SOS, Offline), Network Overview, and Top RTOs by Fitments.
- Three chart sections with their own metric, vehicle-class and period selectors: AIS-140 Fitment Analysis,
  Alert Monitoring (with Response Summary and Recent Major Alerts) and Challan Analysis.
- A header Refresh, Manage Announcements, an account menu (Profile, Tickets, What's New, Logout), interface-size
  and theme controls, and a sidebar with Control & Operations, Administration, Reports and Helpdesk.

Data comes from `GET /api/transport-commissioner/dashboard` and `GET /alert/api/fleet/summary`. The dataset is live,
so scenarios reconcile the UI against those responses instead of hard-coding counts.

## Test Scenarios

### 1. Page load and KPI tiles

**Seed:** `tests/seed.spec.ts`

#### 1.1. D1 Dashboard loads all sections

**File:** `tests/dashboard/load-sections.spec.ts`

**Steps:**
  1. Run the seed (login as admin, land on /tc/dashboard). Wait for the dashboard API and fleet/summary responses, and for the header Refresh button to be enabled.
    - expect: URL is /tc/dashboard; title is 'VLTD Portal'
    - expect: h1 'Transport Commissioner Dashboard' and its subtitle are visible
    - expect: h2 headings visible: Operational Overview, Live Fleet, Network Overview, Top RTOs by Fitments, AIS-140 Fitment Analysis, Alert Monitoring, Challan Analysis
    - expect: Buttons 'Refresh' and 'Manage Announcements' visible; status 'Loading' no longer indicates activity
    - expect: No console errors and no failed (4xx/5xx) API calls

#### 1.2. D2 Six KPI tiles render numeric values with the correct captions

**File:** `tests/dashboard/kpi-tiles.spec.ts`

**Steps:**
  1. After load, read each tile: AIS-140 Fitted Vehicles, Active Fitted Vehicles, Inactive Fitted Vehicles, Never Sent Data, Active Alerts, Challans This Month.
    - expect: Each value matches ^\d[\d,]*$
    - expect: Captions: 'Total AIS-140 fitted vehicles', 'Currently active AIS-140 fitments', 'Currently inactive AIS-140 fitments', 'Fitted devices with no telemetry data', '<n> critical require attention', '<n> issued this year'
    - expect: Page text contains no NaN, undefined, null or [object Object]

#### 1.3. D3 KPI values match the dashboard API response

**File:** `tests/dashboard/kpi-api-reconcile.spec.ts`

**Steps:**
  1. Use page.waitForResponse on /api/transport-commissioner/dashboard and parse data.overview while loading the page.
    - expect: Fitted tile == total_fitted_vehicles; Active == active_fitted_vehicles; Inactive == inactive_fitted_vehicles; Never Sent == fitted_devices_never_sent_data
    - expect: Active Alerts == active_alerts and its subtext number == critical_alerts
    - expect: Challans This Month == challans_this_month and subtext == challans_this_year
    - expect: Request query string has vehicle_class=all and fitment_period/alert_period/challan_period=monthly

#### 1.4. D4 Cross-section internal reconciliation

**File:** `tests/dashboard/reconciliation.spec.ts`

**Steps:**
  1. Read tiles, Vehicle Mix, Top RTOs, Network Overview and Response Summary from the UI.
    - expect: Active Fitted + Inactive Fitted == AIS-140 Fitted
    - expect: Vehicle Mix 'Total Fitted' and the '<n> fitted' badge == AIS-140 Fitted; sum of class counts == total; percentages sum to about 100 (or all 0 when total is 0)
    - expect: Top RTO values each <= AIS-140 Fitted and sum of all listed RTOs <= total; ranks start at 1 and are in descending order of value
    - expect: Network Overview: Active <= Total on every row; rows are OEMs, Fitment Centres, Inspectors, RTOs, Schools, Fleet Owners
    - expect: Active Alerts == Response Summary Open (soft check; flag if the rule differs); critical count <= Active Alerts

### 2. Live Fleet

**Seed:** `tests/seed.spec.ts`

#### 2.1. D5 Live Fleet values match fleet/summary and show update metadata

**File:** `tests/dashboard/live-fleet.spec.ts`

**Steps:**
  1. Capture the GET .../alert/api/fleet/summary response during load and read Moving, Idle, SOS, Offline tiles and the caption.
    - expect: Tile values correspond to the matching fields of the fleet summary response
    - expect: Caption matches /Updated \d{2}:\d{2} (am|pm) · auto every 5m/
    - expect: 'Live' badge visible
    - expect: Values are integers (or an em dash only while loading)

#### 2.2. D6 Live Fleet own Refresh re-fetches only fleet summary

**File:** `tests/dashboard/live-fleet-refresh.spec.ts`

**Steps:**
  1. Start recording requests, wait a minute boundary if needed, click the Refresh button inside the Live Fleet section.
    - expect: A new fleet/summary request is sent; no new /api/transport-commissioner/dashboard request
    - expect: 'Updated' time is the same or later and no error appears
    - expect: Button is temporarily disabled during the fetch and re-enabled afterwards

#### 2.3. D7 Live Fleet auto-refresh every 5 minutes

**File:** `tests/dashboard/live-fleet-auto.spec.ts`

**Steps:**
  1. Install page.clock (fake timers) before load, load the dashboard, fast-forward 5 minutes.
    - expect: A second fleet/summary request fires after about 5 minutes
    - expect: Updated timestamp changes accordingly
    - expect: No duplicate or runaway polling (not more than 1 request per 5 minutes)

#### 2.4. D8 Live Fleet mocked values and failure

**File:** `tests/dashboard/live-fleet-mock.spec.ts`

**Steps:**
  1. Use page.route on **/alert/api/fleet/summary to fulfil (a) all zeros, (b) very large numbers (1234567), (c) HTTP 500, then load /tc/dashboard.
    - expect: (a) tiles show 0, not an em dash and not NaN
    - expect: (b) values render without overflow or truncation (formatting consistent)
    - expect: (c) Live Fleet shows an error/placeholder, the rest of the dashboard still renders, no uncaught exception

### 3. Network Overview and Top RTOs

**Seed:** `tests/seed.spec.ts`

#### 3.1. D9 Network Overview and Top RTOs match the API

**File:** `tests/dashboard/network-rtos.spec.ts`

**Steps:**
  1. Compare each Network Overview row with data.network and Top RTOs with data.fitments.top_rtos.
    - expect: Total and Active for OEMs, Fitment Centres, Inspectors, RTOs, Schools, Fleet Owners equal API values
    - expect: Record whether network.staff (returned by the API) is intentionally not displayed
    - expect: Top RTO row shows rank, name, code, count and 'fitted'; header badge shows '<n> RTO(s)' with correct pluralisation (1 RTO vs N RTOs)

### 4. Filters and charts

**Seed:** `tests/seed.spec.ts`

#### 4.1. D10 Fitment Analysis vehicle class filter

**File:** `tests/dashboard/fitment-class-filter.spec.ts`

**Steps:**
  1. For each option in the 'Vehicle class' select (All Vehicles, Goods Carrier, Cab / Taxi, Bus, Passenger Vehicle, Other) select it and wait for the response.
    - expect: Select offers exactly those 6 options, default All Vehicles
    - expect: Request carries vehicle_class=<value> (all, goods_carrier, cab_taxi, bus, passenger_vehicle, other) with other params unchanged
    - expect: Fitment Trend subtitle shows the selected class name; date range label is visible
    - expect: Vehicle Mix stays the full current distribution (confirm whether it is filtered)
    - expect: A class with zero vehicles renders flat/zero chart without errors

#### 4.2. D11 Fitment period filter

**File:** `tests/dashboard/fitment-period-filter.spec.ts`

**Steps:**
  1. Select Daily, Weekly, Monthly, Yearly in the 'Fitment period' select in turn.
    - expect: Request carries fitment_period=daily|weekly|monthly|yearly
    - expect: Badge/range label under Fitment Trend updates (default range e.g. '01 May 2026 – 09 Oct 2026' for monthly; label differs per period)
    - expect: Chart x-axis labels count matches trend.labels length of the API response
    - expect: Changing fitment period does not alter alert/challan periods or KPI tiles

#### 4.3. D12 Alert metric and period controls

**File:** `tests/dashboard/alert-filters.spec.ts`

**Steps:**
  1. Switch 'Alert metric' between Alert Type and Response Status and 'Alert period' across Daily/Weekly/Monthly/Yearly.
    - expect: Alert Trend subtitle shows the selected metric
    - expect: Metric change alone does not trigger a new dashboard API call (client-side) or, if it does, the request is successful (record the behaviour)
    - expect: Period change sends alert_period=<value> and updates the date range label
    - expect: Response Summary (Open, Acknowledged, Action Taken, Resolved) matches data.alerts.summary and is not reset by the metric toggle
    - expect: Legend/series reflect alert_types or response_status (open, acknowledged, action_taken, resolved, other) from the API

#### 4.4. D13 Challan metric and period controls

**File:** `tests/dashboard/challan-filters.spec.ts`

**Steps:**
  1. Select each Challan metric (Challans Issued, Penalty Amount, Violation Severity) and each Challan period.
    - expect: Challan Trend subtitle shows selected metric
    - expect: Period change sends challan_period=<value> and updates the date range
    - expect: Challan Summary (Total Challans, Penalty Amount with the rupee symbol, Major Violations, Repeat Violations) equals data.challans.summary
    - expect: Disclaimer 'Penalty amounts represent issued challans and not confirmed payment collection.' remains visible
    - expect: Violation Severity works when severity.critical is null

#### 4.5. D14 Filter combinations are independent and persist through the same session

**File:** `tests/dashboard/filter-combinations.spec.ts`

**Steps:**
  1. Set Vehicle class=Bus, Fitment period=Yearly, Alert period=Weekly, Challan period=Daily, then watch the final request URL.
    - expect: The last dashboard request contains vehicle_class=bus&fitment_period=yearly&alert_period=weekly&challan_period=daily
    - expect: Each section shows its own selection; other sections are unaffected
    - expect: Rapidly changing a select 5 times ends with the UI matching the last selection (no stale response overwrite)

#### 4.6. D15 Filter request fails (HTTP 500) after a selection

**File:** `tests/dashboard/filter-error.spec.ts`

**Steps:**
  1. Use page.route to fail dashboard requests whose URL has fitment_period=yearly with HTTP 500, then select Yearly.
    - expect: An error message/toast appears, the page does not go blank
    - expect: Previous or empty state is shown consistently; the select can be changed back to Monthly and recovers

### 5. Alert Monitoring

**Seed:** `tests/seed.spec.ts`

#### 5.1. D16 Recent Major Alerts list content

**File:** `tests/dashboard/recent-alerts.spec.ts`

**Steps:**
  1. Read the Recent Major Alerts items and compare with data.alerts.priority.
    - expect: Each item shows a title, severity chip (High/Critical), vehicle number, response status (e.g. Open) and relative time ('51 min ago')
    - expect: Items are in descending time order and belong to unresolved alerts only
    - expect: Number of items shown <= number in API (record the UI limit; 3 of 5 on the observed run)
    - expect: Heading text 'Latest unresolved high-priority events'

#### 5.2. D17 View All opens the Reports hub

**File:** `tests/dashboard/view-all.spec.ts`

**Steps:**
  1. Click 'View All' in Recent Major Alerts.
    - expect: URL becomes /tc/reports (Reports hub) and the page renders without error
    - expect: Browser back returns to /tc/dashboard with data loaded again

#### 5.3. D18 Alert sections with zero and null data

**File:** `tests/dashboard/alerts-empty.spec.ts`

**Steps:**
  1. Mock the dashboard API with alerts.summary all 0, alerts.priority [] and alert trend arrays empty.
    - expect: Response Summary shows 0 for all four statuses
    - expect: Recent Major Alerts shows 'No unresolved high-priority alerts.' and View All is still visible/working
    - expect: Active Alerts tile 0 with '0 critical require attention'; chart renders an empty state, no NaN

### 6. Empty, null and error states (mocked API)

**Seed:** `tests/seed.spec.ts`

#### 6.1. D19 All-zero dashboard response

**File:** `tests/dashboard/mock-zeros.spec.ts`

**Steps:**
  1. Before navigation call page.route on **/api/transport-commissioner/dashboard* with a valid payload where every count is 0 and all arrays are empty; navigate to /tc/dashboard.
    - expect: All KPI tiles show 0; Penalty Amount shows '₹ 0'
    - expect: Top RTOs shows 'No RTO fitment data' and 'RTO rankings will appear once fitted vehicles are available.'
    - expect: Vehicle Mix shows 'No vehicle mix data available.' and '0 fitted'
    - expect: Network Overview rows all 0 / 0; no NaN, undefined or percent errors (division by zero)

#### 6.2. D20 Null and missing fields in the response

**File:** `tests/dashboard/mock-nulls.spec.ts`

**Steps:**
  1. Mock the response with overview fields set to null, network missing, vehicle_mix null, trend arrays null, severity.critical null.
    - expect: Page does not crash (no white screen); error boundary is not triggered
    - expect: Null numbers render as 0 or a dash consistently, never 'null', 'NaN' or 'undefined'
    - expect: Other sections with valid data still render

#### 6.3. D21 Dashboard API returns HTTP 500

**File:** `tests/dashboard/mock-500.spec.ts`

**Steps:**
  1. Mock the dashboard endpoint with status 500 and body {message:'Server error'}; load the page.
    - expect: User sees an error state or message (not a blank page, no raw stack trace)
    - expect: Header Refresh is enabled afterwards; unrouting the mock and clicking Refresh recovers and displays the data
    - expect: Live Fleet (separate service) still loads independently

#### 6.4. D22 Dashboard API 401 and network failure

**File:** `tests/dashboard/mock-401-abort.spec.ts`

**Steps:**
  1. (a) Fulfil the dashboard endpoint with 401. (b) In a separate run abort the request with route.abort('failed').
    - expect: (a) User is redirected to /auth/login or shown a session-expired message; no data displayed
    - expect: (b) A retry/error message is shown and the page remains usable

#### 6.5. D23 Very large numbers and long names

**File:** `tests/dashboard/mock-large-values.spec.ts`

**Steps:**
  1. Mock fitted vehicles = 12345678, challan revenue = 9876543210, a Top RTO name of 120 characters and a vehicle number of 30 characters.
    - expect: Numbers use consistent formatting and do not overflow tiles
    - expect: Long text truncates or wraps without breaking the layout; no horizontal page scrollbar on desktop

#### 6.6. D24 Slow API shows loading state without misleading zeros

**File:** `tests/dashboard/slow-load.spec.ts`

**Steps:**
  1. Delay the dashboard response by 5 seconds with page.route and observe the page before the response.
    - expect: Header Refresh and Live Fleet Refresh are disabled and Live Fleet says 'Waiting for live data'
    - expect: Observed defect candidate: tiles display 0 / empty-state text while loading (not skeletons); record and flag it as a defect if zeros are shown as real data
    - expect: After the response, values replace the placeholders and Refresh becomes enabled

### 7. Refresh

**Seed:** `tests/seed.spec.ts`

#### 7.1. D25 Header Refresh re-fetches dashboard data

**File:** `tests/dashboard/header-refresh.spec.ts`

**Steps:**
  1. Click header 'Refresh' with page.waitForRequest on the dashboard endpoint.
    - expect: A new dashboard API request (and fleet summary) fires; the currently selected filters are preserved in the query
    - expect: Button is disabled during loading and re-enabled afterwards; no error toast
    - expect: Values match the new response

#### 7.2. D26 Refresh picks up changed data

**File:** `tests/dashboard/refresh-changed-data.spec.ts`

**Steps:**
  1. Mock the first dashboard response; then change the mock so active_alerts is +1 and critical_alerts +1; click Refresh.
    - expect: Active Alerts tile and subtext update to the new values without a page reload
    - expect: Unchanged tiles remain the same

#### 7.3. D27 Double-click on Refresh

**File:** `tests/dashboard/refresh-double-click.spec.ts`

**Steps:**
  1. Double-click header Refresh quickly and count requests.
    - expect: No more than one in-flight dashboard request (button disabled during load) or duplicates are handled without UI inconsistency
    - expect: UI ends in a consistent loaded state

### 8. Navigation, header and account

**Seed:** `tests/seed.spec.ts`

#### 8.1. D28 Manage Announcements

**File:** `tests/dashboard/announcements.spec.ts`

**Steps:**
  1. Click 'Manage Announcements'.
    - expect: An announcements page, dialog or panel opens (record the actual target), no error
    - expect: Closing/back returns to the dashboard intact

#### 8.2. D29 Main navigation menus

**File:** `tests/dashboard/main-nav.spec.ts`

**Steps:**
  1. In navigation 'Main', open Control & Operations, Administration and Reports buttons, then click Helpdesk and Dashboard links.
    - expect: Dashboard link href is /tc/dashboard; Helpdesk link href is /tc/helpdesk and navigates there
    - expect: Each menu button expands to show items; Escape or outside-click closes it
    - expect: The logo link 'Go to VLTD home' (/) is reachable and the dashboard remains accessible afterwards

#### 8.3. D30 Account menu content

**File:** `tests/dashboard/account-menu.spec.ts`

**Steps:**
  1. Click the account button ('Delhi Transport Department / Transport Commissioner').
    - expect: Menu 'User menu' opens showing the department name and an email address
    - expect: Menuitems: Profile, Tickets, What's New (v1.0.0), Logout; Navigation style radios Dropdown (checked by default), Mega, Hub
    - expect: Escape closes the menu and returns focus to the button

#### 8.4. D31 Account menu Profile and Tickets navigation

**File:** `tests/dashboard/account-links.spec.ts`

**Steps:**
  1. Open the account menu and click Profile; go back; open again and click Tickets.
    - expect: Each opens its own page without errors and the user stays signed in
    - expect: Back navigation returns to the dashboard

#### 8.5. D32 Navigation style switch

**File:** `tests/dashboard/nav-style.spec.ts`

**Steps:**
  1. In the account menu choose 'Mega navigation', then 'Hub navigation', then 'Dropdown navigation'.
    - expect: Menu layout changes accordingly; selected radio shows checked
    - expect: Dashboard content is unaffected; choice persists after reload (record behaviour)

#### 8.6. D33 Logout

**File:** `tests/dashboard/logout.spec.ts`

**Steps:**
  1. Open account menu and click the 'Logout' menuitem.
    - expect: Redirect to /auth/login
    - expect: Browser Back does not show dashboard data; direct navigation to /tc/dashboard redirects to login
    - expect: No dashboard API call succeeds afterwards (401)

#### 8.7. D34 Unauthenticated access redirects to login

**File:** `tests/dashboard/unauth.spec.ts`

**Steps:**
  1. In a new context without storage state, open /tc/dashboard directly.
    - expect: Redirected to /auth/login; no KPI data or section headings rendered

#### 8.8. D35 Theme toggle

**File:** `tests/dashboard/theme.spec.ts`

**Steps:**
  1. Click 'Switch to dark theme', verify, reload, then toggle back.
    - expect: Button label flips to light theme and page colours/theme class change
    - expect: Charts and tiles remain readable; choice persists after reload (record behaviour); toggle back restores the original

#### 8.9. D36 Interface size controls

**File:** `tests/dashboard/font-size.spec.ts`

**Steps:**
  1. Click 'Increase interface size' (A+) twice then 'Decrease interface size' (A−) four times.
    - expect: Text scale grows then shrinks; layout does not break at the maximum; the controls stop at the min/max limits without errors

#### 8.10. D37 Keyboard accessibility and semantics

**File:** `tests/dashboard/a11y.spec.ts`

**Steps:**
  1. Tab through the header, the selects and View All; check that selects change via keyboard (ArrowDown) and inspect landmarks.
    - expect: Focus order is logical with a visible focus ring
    - expect: Selects have accessible names (Vehicle class, Fitment period, Alert metric, Alert period, Challan metric, Challan period)
    - expect: Landmarks banner, navigation 'Main' and main exist; notification region 'Notifications alt+T' present

### 9. Responsive

**Seed:** `tests/seed.spec.ts`

#### 9.1. D38 Mobile viewport 390x844

**File:** `tests/dashboard/mobile.spec.ts`

**Steps:**
  1. Set viewport to 390x844 and load /tc/dashboard.
    - expect: No horizontal page scroll; KPI tiles stack in one or two columns
    - expect: Navigation is available through a hamburger/drawer (record its label) with the same menu entries
    - expect: All six selects remain usable; charts resize and Recent Major Alerts rows do not overflow
    - expect: Header Refresh and Manage Announcements are reachable

#### 9.2. D39 Tablet and wide desktop

**File:** `tests/dashboard/viewports.spec.ts`

**Steps:**
  1. Load the page at 768x1024 and 1920x1080.
    - expect: Grid reflows without overlap or clipped text; the Live Fleet header text and Refresh do not wrap awkwardly
    - expect: All sections remain visible by scrolling

### 10. Security and role scope

**Seed:** `tests/seed.spec.ts`

#### 10.1. D40 Tampered token is rejected

**File:** `tests/dashboard/token-tamper.spec.ts`

**Steps:**
  1. Replace the stored auth token/cookie with 'garbage.token.value' and reload /tc/dashboard.
    - expect: User is redirected to login or sees an unauthorized state; no KPI values are rendered

#### 10.2. D41 Non-TC role cannot view TC dashboard

**File:** `tests/dashboard/role-scope.spec.ts`

**Steps:**
  1. Log in as an OEM user (OEM_* env) and open /tc/dashboard.
    - expect: Access denied or redirect to the role's own landing page
    - expect: TC dashboard API returns 401/403 and no TC KPIs are shown

#### 10.3. D42 No sensitive data in URL or console

**File:** `tests/dashboard/no-leak.spec.ts`

**Steps:**
  1. Load the dashboard and inspect URL, console messages and network request URLs.
    - expect: No token, password or PII in URLs or console output
    - expect: Query strings contain only the four filter parameters
