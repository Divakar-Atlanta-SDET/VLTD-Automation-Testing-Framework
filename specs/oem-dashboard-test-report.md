# OEM Dashboard — Test Report

Scope: the OEM panel **Dashboard only** (`/oem/dashboard`). Tested on 2026-10-30 against https://vltd.misbackend.com as the OEM Admin from `.env` (credentials not recorded), Chromium. Sources: `VLTD_How_It_Works.pdf`, the live page, `bug_report.md`, the existing OEM tests.

**The guide does not describe the OEM dashboard.** It defines the stock states an OEM works with (Available, Allocated, Installed, Faulty: 6.1) and the announcements published to OEMs (19.2). Everything else on the page (Live Fleet, trend, tables, report links, wording) is undocumented, so the tests reconcile what the page shows with the data behind it and make no claim about layout or wording that the guide does not give.

Evidence: `specs/evidence/oem-dashboard/` (12 screenshots, 1 video).

---

## 1. What the page contains (explored live)

| Section | Content | Data source |
|---|---|---|
| KPI cards (5) | Total / Available / Allocated / Installed / Faulty Devices | `GET /api/dashboard/oem/device-inventory` |
| Live Fleet | Moving / Idle / SOS / Offline, "N vehicles", "Updated hh:mm · auto every 5m", own **Refresh** | `GET /api/tracking/vehicles/summary` |
| Device Inventory | donut (Available + Allocated) with legend | device-inventory |
| Allocation Overview | bars Total / Active / Returned allocations, "Allocated Devices" | `GET /api/dashboard/oem/allocation-summary` |
| Device Details | 5 newest devices (IMEI + serial, model, SIM, firmware, status), **View All** | `GET /api/devices?page=1&per_page=5` |
| Fitment Centre Allocations | per centre: allocations / devices / active, **View All** | `GET /api/dashboard/oem/fitment-summary` |
| Allocation Trend | Daily / Weekly / Monthly / Yearly buttons, total, average, peak, bar chart | `GET /api/device-allocations?...date_from&date_to` |
| Device Quality | replacement reasons | no data on this account |
| Raised Tickets | recent tickets, **View Report** | `GET /api/helpdesk/tickets/performance` |
| Recent Repairs | latest devices received for repair, **View All** | `GET /api/device-repairs` |
| Notice banner | announcements for OEMs ("Official notice") | `GET /api/announcements` |

All requests answered 200 and the page raised no console or network failures. KPI cards are not links. Only Live Fleet has a refresh (button and 5-minute timer); the other sections load once per visit.

## 2. Previous-bug verification

**No OEM Dashboard bug was on record** in `bug_report.md` (BUG-038 to BUG-043 belong to other OEM modules). The two State Admin dashboard bugs were checked for the same behaviour on the OEM dashboard:

| Earlier bug (State Admin dashboard) | Check on the OEM dashboard | Status |
|---|---|---|
| BUG-005: KPI tiles show a real-looking 0 while data loads | Held the inventory request and also throttled the network (3 s latency). The five KPI cards show grey skeletons, no number, until the data arrives (screenshot `07-loading-state.png`). | **Not reproducible** (the OEM dashboard is correct) |
| BUG-008: "View All" opens the Reports hub | The four links open `/oem/devices`, `/oem/device-allocations`, `/oem/repairs` and `/oem/audit-reports/ticket-performance`. | **Not reproducible** |

## 3. Confirmed bug

| | |
|---|---|
| ID / title | **BUG-044** - OEM Dashboard: the SIM column of the Device Details widget is always "-" |
| Module / environment | OEM > Dashboard > Device Details; vltd.misbackend.com, Chromium |
| Severity / priority | Low / Low |
| Preconditions | OEM Admin; at least one registered device with a SIM module |
| Steps | 1. Sign in as the OEM, stay on the Dashboard. 2. Read the SIM column of **Device Details**. 3. Click **View All**, search the same IMEI, read **SIM MODULE**. |
| Expected | the SIM module, as on the Device Details page (the API returns `sim_module.module_name` and `sims[0].iccid`) |
| Actual | "-" for every device; the Device Details page shows the module name |
| Evidence | `02-with-data.png`, `05-device-details-page-sim-column.png`, `11-BUG-044-sim-column-dashboard-vs-device-details.webm` |
| Reproducibility | Reproducible every time (more than five runs, 1 to 7 devices) |
| Automated | `test_recent_devices_show_the_sim_module` (expected failure; fails with `'-' == 'AUTO SIM ...'`) |

## 4. Observations that need a product answer (not reported as bugs)

1. **Partial loading:** if only the inventory request is slow (held with request interception, not reproduced with plain network throttling), the Device Inventory card shows `0 / Available 0 / Allocated 0` while the KPI cards show skeletons (`07-loading-state.png`). A normal user is unlikely to see it, so it is not filed.
2. **Server error:** the page shows the server's message ("Something went wrong.") and also shows 0 in the cards (`08-server-error-state.png`). The failure is visible, but the zeros look like real data.
3. **Allocation Trend excludes rolled-back allocations** (returned allocations hold no devices): a device allocated and then returned does not count. Is that intended?
4. **No refresh for the rest of the page:** after registering or allocating in another tab the KPIs stay stale until the page is reloaded; only Live Fleet refreshes. Intended?
5. **Trend range and averages** (Daily = last 7 days, Weekly = about the last 8 weeks, Monthly = January to today, Yearly = last 5 years; average = total / periods) are inferred from the requests the page sends; nothing documents them. The tests do not assert the averages.
6. **Trend completeness (unverified):** the page requests the first 100 allocations of the period only. With more than 100 allocations in the period the totals might be incomplete. This could not be shown with the data available.

## 5. Coverage report

| Area | Check | Test | New |
|---|---|---|---|
| KPI accuracy | the five cards equal the stock figures; devices add up | `test_oem_reports_and_dashboard.py::test_dashboard_counters_add_up_and_equal_the_device_list`, `::test_dashboard_page_shows_the_stock_counters` | existing |
| Data consistency | after register, allocate and roll back: KPIs, donut legend, Allocation Overview, per-centre allocations / devices / active all equal the API | `test_oem_dashboard.py::test_every_figure_follows_registration_allocation_and_rollback` | yes |
| Recent devices | the five newest, newest first, with serial, model, firmware, status | `::test_recent_devices_lists_the_five_newest_first` | yes |
| Recent devices | SIM column shows the SIM module | `::test_recent_devices_show_the_sim_module` (BUG-044) | yes |
| Allocation Trend | for each period the total rises by the devices allocated; figures are labelled for the period | `::test_allocation_trend_counts_new_allocations_in_every_period` (4) | yes |
| Live Fleet | counters and vehicle count equal the vehicle summary; Refresh re-requests it | `::test_live_fleet_equals_the_vehicle_summary_and_refreshes_on_request` | yes |
| Live Fleet | refreshes itself after 5 minutes, not before | `::test_live_fleet_refreshes_itself_every_five_minutes` (fake clock) | yes |
| Empty data | zeros and an empty message in every section, no broken text | `::test_empty_account_shows_zeros_and_an_empty_message_in_every_section` | yes |
| Null data | null figures shown as 0, no NaN / undefined / null | `::test_null_values_are_shown_as_zero_not_as_broken_text` | yes |
| Failure | a server error is reported and the page stays usable | `::test_a_server_error_is_reported_and_the_page_stays_usable` | yes |
| Loading | no number on the KPI cards while their data is pending | `::test_kpi_cards_show_no_number_while_their_data_is_loading` | yes |
| Navigation | View All (devices, allocations, repairs) and View Report | `::test_section_links_open_their_page` (4) | yes |
| Authorization | anonymous and malformed tokens: 401; State Admin token: 403, on all three dashboard endpoints | `::test_dashboard_data_is_refused_to_anonymous_callers_and_other_roles` (3) | yes |
| Authorization | OEM lands on its own dashboard and is turned away from `/tc` pages; dashboard loads without failed calls | `test_oem_role_access.py`, `test_oem_access_and_isolation.py::test_every_oem_menu_page_loads_cleanly` | existing |
| Notices (guide 19.2) | a notice for OEMs is shown; one for another audience, not yet started, or expired is not | `::test_a_notice_for_oems_is_shown_on_the_dashboard`, `::test_a_notice_that_is_not_for_oems_now_is_not_shown` (3) | yes |

## 6. Missing scenarios not automated

| Scenario | Why |
|---|---|
| Installed and Faulty KPIs, Live Fleet with vehicles, Device Quality, Raised Tickets and Recent Repairs with data | They need installed devices, repairs and tickets. The OEM account has none and tickets and installations cannot be created or removed safely. Their empty states and links are covered. |
| Dashboard visibility for OEM staff without the `dashboard.view` permission | OEM staff cannot be created (BUG-039). |
| Trend averages, date ranges and the 100-allocation limit | Not documented (observations 5 and 6). |
| Chart rendering (canvas bars and donut) | The numbers behind the charts are checked; pixel checks add no business value. |

## 7. Implemented scripts

- `pages/oem_panel/dashboard.py` - the Dashboard Page Object (KPI, section, table, trend and Live Fleet readers; replaces the small class that was in `misc.py`).
- `utils/oem_dashboard_mocks.py` - canned back-end answers (empty account, held request).
- `tests/oem_panel/test_oem_dashboard.py` - 24 tests (23 expected to pass, 1 known defect).
- Framework fixes found on the way: `ApiClient.all_items` now follows pagination under `meta.pagination` as well, and `find_oem_account` reads every page, because the admin OEM list has grown past 100 entries and the OEM lab tests could no longer find their OEM.

## 8. Execution report (2026-10-30)

| Scope | Passed | Failed | Skipped | Blocked | Expected failures (known defects) |
|---|---|---|---|---|---|
| `test_oem_dashboard.py` | 23 | 0 | 0 | 0 | 1 (BUG-044) |
| Whole OEM scope (`tests/oem_panel` + `test_oem_role_access.py`), `--known-bugs`, 4 workers, 3 min 15 s | **134** | **0** | **0** | 0 | **12** (BUG-038, 039 x3, 040 x4, 041, 042, 043, 044) |

- During development five tests failed; all five were script problems (the allocation block is a grid, not a table; the Refresh button's accessible name; reading the trend before its data had loaded), fixed before the final run. No product defect caused a failure.
- Stability: the dashboard file and the reports file ran green three times in a row.
- Blockers: none for the dashboard; the data-dependent areas in section 6 are untestable on this account.
- Test data: each run creates and removes its own devices; the allocation history keeps "returned" rows and the notice tests create and delete announcements.
