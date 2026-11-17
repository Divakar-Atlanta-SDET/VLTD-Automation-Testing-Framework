# OEM Panel — Test Plan and Automation Test Cases

Status: **Approved and implemented** in `tests/oem_panel/` (answers: no Add Model for OEMs; OEM staff management must work; fixtures, Rajendra Fitments, openpyxl and the blacklisted centre approved). Not automated and why: OEM-D3 (SOS Clear field not identifiable), OEM-F3 / F4 and the exports other than Device Inventory (the account has no installed devices, so the tests could only skip), the 10,001-row bulk upload (the request does not answer within 30 s). Defects found: BUG-038 to BUG-043 in `bug_report.md`.
Sources: `VLTD_How_It_Works.pdf` (the "guide"), a live walk of the OEM panel with the `OEM_*` login from `.env` (read-only, nothing created or changed), and the existing framework. Credentials were not printed or copied.

---

## 1. What was explored

All 30 pages of the OEM menu opened. Pages and the workflow they belong to:

| Area | Pages | Guide § |
|---|---|---|
| Dashboard | `/oem/dashboard` (device inventory, allocation and fitment summaries, recent repairs/devices) | 6.1 |
| Devices | Device Details (list, filters, **Add Device**, **Bulk Upload** with sample download), Device Models (view), Device Allocation History | 6.1, 14.4 |
| Stock | Allocate Stock (2 steps: district and fitment centre, then devices) | 6.1 |
| Fitment centres | Fitment Centers (list, counters, **Register FC**) | 3, 6.1 |
| Service | Repair (status tabs, search), SIM Validity Extension (IMEI fetch) | 6.4, 6.5 |
| Commands | Command Center (Send Command, Command List with **Add Command**, Command History) | 12 |
| Monitoring | Alerts, Geofences, Live Tracking, Trip Playback, Alert Set History, Watch History | 7–13 |
| Reports | Alert Report, Vehicle Alert Trail, Device Health, Device Packets, Device Status, SIM Validity, Expired SIM, Installation Report, Installation Performance, Installed Devices, Device Inventory, User Devices, Ticket Performance | 18 |
| Support | Helpdesk (Support Tickets) | 19 |
| Users | OEM Staff (list, **Register Staff** with 41 permissions) | – |

## 2. Facts about the OEM test account (they decide what can be automated)

| Fact | Evidence |
|---|---|
| Role `oem_admin`; holds all 41 permissions of the OEM catalogue | `/api/auth/me`, `/api/oem/permissions` |
| **No data**: 0 devices, 0 firmware, 0 SIM modules, 0 allocations, 0 repairs, 0 command templates, 0 installed vehicles. Only one Device Model ("Garry Haag", oem_id 39) | OEM list calls |
| Two fitment centres: `Rajendra Fitments` (active) and `Test_Fitment_center` (**blacklisted**) | `/api/oem/fitment-centres` |
| A device can only be registered with a Firmware and a SIM Module of this OEM, and the State Admin owns that master data (guide 14.4). With none, the Add Device form cannot be completed. The admin API can create them for oem_id 39 and delete them again | guide + admin API |
| Devices of other OEMs answer **404** to this OEM (checked with two real device ids) | `GET /api/devices/{id}` |
| `DELETE /api/devices/{id}` exists (404 for an unknown id, not 403/405), so a test device can probably be removed. **Not yet verified on a real record** | probe |
| `openpyxl` is not installed (needed to build bulk-upload sheets) | environment |

## 3. Observed behaviour versus the guide

| # | Observation | Guide | Verdict |
|---|---|---|---|
| O1 | Device Models page offers **"Add Model"** and a full "Register Model" form. The server refuses every write (`POST/PUT/PATCH/DELETE` → 403) and the OEM holds only `device_models.view` | "OEMs cannot create, edit or delete this master data" (14.4) | **Conflict: the UI offers an action the OEM cannot perform** (likely defect) |
| O2 | OEM Staff page: `GET /api/oem/users` and `POST /api/oem/users` answer **403** although the OEM holds every permission of its catalogue; the page shows 0 staff and cannot register anyone | Not described | **Needs clarification / likely defect** (same pattern as BUG-015) |
| O3 | Alerts, Geofences, Live Tracking, Trip Playback call `GET /api/transport-commissioner/oems` and `/rtos` → **403**, plus the known `/api/school` 404 | Each organisation has its own panel (7) | Likely defect (same family as BUG-016 / BUG-020) |
| O4 | Add Device form fields: model, firmware (disabled until a model is chosen), SIM module, slot id, IMEI, serial number, primary and secondary mobile, ICCID, SIM valid till | Row fields in 6.1 match | Consistent |
| O5 | Server rules: IMEI = 15 digits; mobile = valid 10-digit; ICCID = 19–20 digits; SIM valid-till must not be in the past | Guide gives no digit rules; SIM validity minimum (2 y / 1 y) is checked at installation, not here | Observed, undocumented |
| O6 | Bulk upload: `POST /api/devices/bulk-upload` (field `devices`), sample sheet downloads as `.xlsx` | up to 10,000 devices, error report to download (6.1) | Limit and error report **not verified** |
| O7 | Allocate Stock step 1 = district, then fitment centre | "chooses a district and one of its active fitment centres" | Consistent |
| O8 | Allocation with an unknown IMEI answers `imeis.0: One or more selected devices were not found`. Whether a blacklisted fitment centre is refused could not be seen without a real device | active centres only | **Unverified** |
| O9 | Command List has "Add Command" and a Device Model filter; templates need model, label, raw command | OEM defines commands, one can be SOS Clear (12) | Consistent; SOS Clear control not seen in the list view |
| O10 | OEM dashboard figures are all 0 and cannot be reconciled until devices exist | 6.1 states | Blocked by data |

## 4. Existing coverage of the OEM role

Only `tests/oem_management/test_oem_role_access.py` (13 tests): OEM cannot write master data, sees only its own models/firmware/SIMs, is refused six State Admin endpoints, lands on `/oem/dashboard` and is redirected from `/tc` pages. **Nothing covers devices, allocation, rollback, commands, fitment centres, reports, repairs or SIM extension.**

## 5. Risks and dependencies

| Item | Risk | Handling |
|---|---|---|
| Registering a device needs admin-created Firmware + SIM Module for OEM 39 | Those records cannot be deleted while a device uses them | Fixture order: create master data → create device → test → delete device → delete master data (in `finally`) |
| Device delete not proven | If it fails, every run leaves a device and locks its firmware/SIM | **Step 0 of Phase 2: prove create → delete on one device before writing anything else; stop and report if delete is refused** |
| Allocation touches the real active FC `Rajendra Fitments` | A leftover allocation would hide a device from the OEM's stock | Rollback in `finally`; assert the device is `Available` again |
| FC registration creates an undeletable login account | Residue like OEMs/RTOs | Only refusals are automated; the happy path is manual |
| Reports are empty on this account | Counter checks pass vacuously | Reconcile only when rows exist; otherwise **skip visibly**, never pass silently |
| Shared environment | Parallel workers allocating the same FC | Lifecycle module pinned to one worker (`xdist_group`) |

## 6. Test cases proposed for automation

Layer: **API** = Playwright `request`; **UI** = browser; **UI+API** = API setup, UI assertion. Priority: P0 security / data integrity / irreversible, P1 core workflow, P2 secondary. Fixture "lifecycle" = admin creates Firmware + SIM Module for OEM 39, OEM registers a device, everything removed afterwards.

### A. Authorization and isolation

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-A1 | P0 | OEM requests devices, allocations, repairs and fitment centres that belong to another OEM (ids from the admin status report / lists) | 404 for each; no data returned; own lists unaffected (parametrize over resource) | API |
| OEM-A2 | P0 | OEM calls State Admin write/read endpoints not yet covered: announcements, ownership-transfer, account-merge, untag-search, challan masters, PIS stops/routes, helpdesk assign | 403 for each (parametrize); extends the existing six | API |
| OEM-A3 | P1 | No token / malformed token on OEM endpoints: devices, device-allocations, device-repairs, device-command-templates, fitment-centres | 401 each (parametrize over endpoint × token) | API |
| OEM-A4 | P1 | Every OEM menu page opens without a 401/403/5xx or a failed write | One loop test passes; pages with known 403s (O3, O2) are separate known-bug tests | UI |
| OEM-A5 | P1 | Device Models page for an OEM that holds only `device_models.view` | No "Add Model" button and no Register form (known bug O1 until fixed) | UI |
| OEM-A6 | P1 | A new OEM (created by admin API) signs in with the temporary password | Redirected to Change Password; cannot skip to `/oem/dashboard` (guide ch. 4) | UI+API |

### B. Device registration (guide 6.1)

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-B1 | P0 | Register a device (lifecycle fixture) | 201; appears in Device Details by IMEI search with model, SIM module, firmware, inventory **Available**; dashboard Total and Available each +1; removed in cleanup | UI+API |
| OEM-B2 | P0 | Invalid registrations: IMEI 14 digits / letters, duplicate IMEI, mobile 9 digits, ICCID 18 digits, SIM valid-till in the past, firmware of another model, model / SIM / firmware of another OEM | 422 (or 404) with the field named; nothing created; list total unchanged (parametrize) | API |
| OEM-B3 | P1 | Add Device form: empty submit; model chosen enables firmware list showing only that model's firmware | Required fields listed; firmware options = firmware of the chosen model | UI |
| OEM-B4 | P1 | Bulk upload sample sheet | Downloads as a spreadsheet with the columns of guide 6.1 (IMEI, serial number, model, SIM module, firmware, ICCID, primary and secondary mobile, SIM validity) | API |
| OEM-B5 | P1 | Bulk upload with invalid rows | Row-level errors returned, zero devices created; upload with 10,001 rows refused (needs `openpyxl`, see §8) | API |
| OEM-B6 | P2 | Device list filters (model, inventory status, date range, IMEI search) against known devices | Only matching devices shown | UI |

### C. Allocation and rollback (guide 6.1)

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-C1 | P0 | Allocate an Available device to the active fitment centre | Allocation in history (FC, count 1, status Active); device inventory **Allocated**; dashboard Available −1 / Allocated +1; allocation detail lists the IMEI | UI+API |
| OEM-C2 | P0 | Refusals: same device again; unknown IMEI; another OEM's device; no devices selected; no fitment centre; **blacklisted fitment centre with a real Available device** | 422 each; device stays Available; history unchanged (parametrize) | API |
| OEM-C3 | P0 | Roll back an allocation | Device back to **Available**; history status changed; second rollback refused | API |
| OEM-C4 | P1 | Allocate Stock wizard: district → only that district's active centres; step 2 lists only Available devices | Blacklisted / other-district centres absent; allocated devices absent | UI |
| OEM-C5 | P2 | Allocation history filters (status, fitment centre, dates) | Rows match the filter | UI |

### D. Command Center (guide 12)

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-D1 | P1 | Create, edit, deactivate and delete a command template for the OEM's own model | Saved, listed with counters (total / active / inactive) consistent; deleted template gone | API (+UI list check) |
| OEM-D2 | P1 | Invalid templates: missing label / raw command, unknown model, another OEM's model | 422 / 403; nothing created | API |
| OEM-D3 | P1 | SOS Clear flag (see Q4) | Only one SOS Clear per model, or as the product owner defines | API |

### E. Fitment centres (guide 3, 6.1)

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-E1 | P1 | Fitment Center list counters and filters | Total / Active / Suspended / Blacklisted equal the rows; status, RTO, city and search filters return only matching centres | API+UI |
| OEM-E2 | P1 | Register FC refusals: empty request, bad pincode / email / mobile, weak or mismatched password, duplicate fitment code, wrong image type or size | 422 per field; no centre created (parametrize) | API |

### F. Reports and dashboard (guide 18)

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-F1 | P1 | Dashboard inventory counters equal the Device Details totals by inventory status | Total = Available + Allocated + Installed + Faulty; equals device list total | API |
| OEM-F2 | P1 | Export downloads for Alert Report, Device Health, Device Status, Device Inventory, Installed Devices, Expired SIM, Ticket Performance | File downloads and is non-empty; button disabled-state with no rows is skipped visibly | UI |
| OEM-F3 | P1 | SIM Validity, Device Health and Device Status counters equal their rows (same rules as the State Admin checks, with the OEM token) | Equal; **skipped visibly** while the account has no installed devices | API |
| OEM-F4 | P2 | Expired SIM report contains only SIMs whose valid-till is in the past | All rows `expired_by > 0` | API |

### G. SIM Validity Extension (guide 6.5)

| ID | P | Scenario | Expected result | Layer |
|---|---|---|---|---|
| OEM-G1 | P1 | Fetch Device with an unknown IMEI, a malformed IMEI, a device of another OEM, and a registered but **not installed** device | Refused with a message; extension impossible; nothing changed | UI+API |

## 7. Manual checks (not worth automating, or unsafe)

| Scenario | Reason |
|---|---|
| SIM validity extension happy path and its 2 y / 1 y limit; repair start, complete, replacement required, post-repair checks | Needs a device installed on a vehicle (FC, RTO and VAHAN steps) |
| Fitment-centre happy-path registration; activate / deactivate / blacklist of a real centre | Creates an undeletable login, or changes the real centre `Rajendra Fitments` |
| Allocation rule "a device that went live can never be allocated again" | Needs a live device |
| Bulk upload of 10,000 devices; validation-report download content | Bulk residue; limit checked at 10,001 rows only |
| Command delivery (Queued → Sent → Acknowledged / Failed), SOS Clear on a real SOS | Real devices |
| Live Tracking, Alerts, Geofences, Trip Playback, Watch History for the OEM's vehicles | No vehicles on this account; behaviour is shared with the State Admin suites |
| COP expiry reminder to the OEM (daily 09:00) | Time-based job |
| Helpdesk ticket flow | Tickets cannot be deleted |

## 8. Questions that need your answer

1. **O1** — Should an OEM see "Add Model" / "Register Model"? (The guide says no.) I will treat it as a known bug unless told otherwise.
2. **O2** — Does the OEM Admin manage its own staff? `/api/oem/users` is refused for the OEM Admin. Intended, or should that role have access?
3. May the lifecycle fixture **create Firmware and SIM Modules for the OEM 39 account ("Garry Haag" owner)** through the admin API and remove them afterwards? Without them no device test is possible.
4. May the allocation tests use the active centre **Rajendra Fitments** (rolled back in `finally`)? Is more than one SOS Clear command per model allowed?
5. May I add `openpyxl` to `requirements.txt` for the bulk-upload tests (OEM-B4/B5)? Without it they are dropped.
6. Is the OEM-side **blacklisted** centre `Test_Fitment_center` safe to use as the negative target for OEM-C2?

## 9. Implementation order (after approval)

1. Prove create → delete of one device on the lifecycle fixture (stop and report if delete fails).
2. `OEM-A*` (no data risk), then `OEM-F2` / `OEM-E*` / `OEM-G1` (read-only or refusals).
3. `OEM-B*`, then `OEM-C*` (lifecycle, one pinned worker), then `OEM-D*`, `OEM-F1/F3/F4`.
4. New files: `tests/oem_panel/` (conftest with the lifecycle fixture, `test_access_and_isolation.py`, `test_device_registration.py`, `test_allocation.py`, `test_command_templates.py`, `test_fitment_centres.py`, `test_reports_and_dashboard.py`, `test_sim_validity_extension.py`) and Page Objects under `pages/oem_panel/` (device list/form, allocation wizard and history, fitment centres, command center). Existing `tests/oem_management/test_oem_role_access.py` stays as is.
5. New defects found during Phase 2 go into `bug_report.md` (candidates already: O1, O2, O3).

Total proposed: 27 cases (A 6, B 6, C 5, D 3, E 2, F 4, G 1); many are parametrized, so the number of executed tests will be larger than 27.
