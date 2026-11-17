# OEM Panel - Management > Device Management: test report

| | |
|---|---|
| **Date / environment** | 2026-11-02, https://vltd.misbackend.com, Chromium, signed in as the OEM Admin from `.env` |
| **Scope** | Management > Device Management: Device Details, Device Models, Allocate Stock, Device Allocation History. Repair (top menu) and SIM Validity Extension (Operations) were looked at only where they touch devices |
| **Requirements used** | `VLTD_How_It_Works.pdf` 6.1 (master data, device registration one by one and in bulk with a validation report, allocation to active centres, history and rollback, stock states Available / Allocated / Installed / Faulty, allocation rules), 6.4 (repair, replacement), 6.5 (SIM validity extension), 14.4 (OEMs only view device models). No rule was invented; undecided points are listed as observations 20-22 in `bug_report.md` |
| **Code** | `tests/oem_panel/test_oem_device_management_ui.py` (40 tests, new), Page Object additions in `pages/oem_panel/devices.py` and `allocation.py`, shared `other_oem` fixture in `tests/oem_panel/conftest.py`; the existing API tests `test_oem_device_registration.py` and `test_oem_allocation.py` stay as they are |
| **Result** | Device Management module 33 passed + 7 expected failures; whole OEM scope 365 passed, 1 intermittent failure, 50 expected failures (section 8) |

## 1. Submodules and features discovered

| Submodule | Features found |
|---|---|
| **Device Details** `/oem/devices` | list (10 a page, pager), filters Model / Inventory Status (Allocated, Available, Installed, Faulty) / From and To date (custom pickers) that apply on **Search**, IMEI search, Clear Filter; **Add Device** form; **Bulk Upload** dialog (Download Sample, .xlsx / .xls, up to 10,000 devices); row menu **View Device** (overlay), **Edit Device** (page; SIM details read-only), **Delete Device** (confirmation) |
| **Device Models** `/oem/device-models` | list with search and status filter; **Add Model**, and a row menu with **View / Edit / Delete Model** (the OEM may only view, guide 14.4: BUG-038) |
| **Allocate Stock** `/oem/inventory/allocate-stock` | step 1 district -> active centre cards -> Continue; step 2 available devices (search by IMEI, tick, select all, selected list with Remove) -> Allocate; success page with summary, View Allocation History / Details, Allocate More, **Rollback Allocation** (confirmation) |
| **Device Allocation History** `/oem/device-allocations` | list with search, Status (Allocated, Received, Cancelled, Pending, Returned), Fitment Center, date filters, Reset Filters, Refresh; row **View** and, while Allocated, **Rollback**; details page `/oem/device-allocations/{id}` |
| Adjacent | **Repair** `/oem/repairs` (tabs All / Received / Repairing / Repaired / Replacement Required, search, dates; empty here), **SIM Validity Extension** (covered earlier) |

## 2. Manual testing (throw-away lab; every device removed afterwards)

Device list (pager with 12 and 25 devices, every filter, partial and padded IMEI search, no match, date controls); View, Edit (real edit, empty / 14-digit / lettered IMEI, spaces-only serial, duplicate IMEI and serial, SIM fields read-only), Delete (cancel and confirm; allocated device); Add Device through the screen (empty, past SIM date, today, +10 years, duplicate IMEI / ICCID / primary mobile / serial, equal mobile numbers, spaces and 300-character serial, text Slot ID, valid); Bulk Upload (dialog, sample download, no file, text / empty / fake files, a bad row, a good row, **header and cell variants read from the request body**), and the API contract of the bulk endpoint; Allocate Stock (district, centre, Continue and Allocate states, search, select all, 3 / 12 / 25 devices, double click on Allocate, success page); History (columns, filters, pager, 12 search terms, View, Rollback dialog with Cancel and Confirm and a double click); Device Models (menu, Edit, Delete x3); Repair page; dashboard SIM column; the API for isolation (second OEM reads, edits with its **own** valid master data, deletes, allocates, rolls back) and lifecycle (delete and edit of an allocated device). Evidence: `specs/evidence/oem-device-management/` (28 screenshots).

## 3. Findings by classification

| Class | Findings |
|---|---|
| **Confirmed Bug** (repeated 2-3 times) | BUG-061 bulk upload from the screen cannot work (High); BUG-062 history without pager; BUG-063 wizard lists 20 devices; BUG-064 wizard counter 0; BUG-065 history search finds nothing; BUG-066 Bulk Upload accepts any file type, no row limit, 504 on a long file (reported by the tester, reproduced); BUG-038 wider: Edit and Delete Model offered |
| **Requirement mismatch / needs a decision** | an allocated device can be edited incl. its IMEI; no upper limit for SIM validity at registration; free-text Slot ID; extra history statuses (Received, Cancelled, Pending); returned allocations lose their device count; the Excel validation report only appears for unknown master-data names (format errors are JSON), unverifiable on screen because of BUG-061 |
| **Environment / data issue** | the Google map on the geofence page falls back from vector to raster and swallowed the first drag, so geofence drawing tests were flaky (fixed in the Page Object, not a product bug); the OEM account has no installed device |
| **Unable to confirm** | Repair, Replacement, SIM extension happy path and the limit of 2 y / 1 y (need a device installed by a fitment centre); the date pickers of the device list (custom control, not automated) |
| **Not a bug (verified)** | rollback returns devices to Available; a double click sends one request; an allocated device cannot be deleted (422); another OEM cannot reach this OEM's devices and allocations |

## 4. Previously reported Device Management bugs, re-verified 2026-11-02

| Bug | Result |
|---|---|
| BUG-038 Add Model offered to the OEM | **Reproducible** 3 of 3, and wider (Edit Model, Delete Model; delete answers 403) |
| BUG-041 allocation to a blacklisted centre | **Reproducible** (201) |
| BUG-055 allocation to a suspended centre | **Reproducible** (201) |
| BUG-043 SIM extension offered for a device that is not installed | **Reproducible** |
| BUG-044 dashboard SIM column "-" | **Reproducible** |

## 5. New bugs and their validation

See `bug_report.md` BUG-061 to BUG-066. Validation: BUG-061 sample upload 3 of 3, filled-in sample 1 of 1, six mobile-column variants 6 of 6; BUG-062 3 of 3 page loads and the API total; BUG-063 2 of 2 manual runs (20 of 25) and the test; BUG-064 3 timed runs of 12 s and 4 earlier observations; BUG-065 three runs, 12 search terms, all empty while the status and centre filters find the allocation; BUG-066 three file types x 3 runs (accepted, no type check), row counts 500 / 3,000 / 12,000 x 2 runs (422 in 1 s, 422 in 10 s, 504 after 60 s); a freeze of the whole tab could not be reproduced.

## 6. API and security findings

- **Isolation holds:** another OEM gets 404 for the device (read, edit with its own valid master data, delete) and for the allocation (read), 422 when it tries to allocate the device or roll the allocation back, an empty list, and 422 when it registers a device with this OEM's model / firmware / SIM module.
- Server rules work: duplicate IMEI, ICCID, primary mobile and serial; IMEI 15 digits; ICCID 19-20 digits; mobile format; secondary different from primary; serial max 100; SIM validity not in the past; a device can be deleted only while Available.
- Open: BUG-041 and BUG-055 (allocation to a blacklisted or suspended centre, API-only); BUG-061 (the bulk endpoint itself works, the screen does not reach it).
- A bulk upload from the screen is refused for the wrong reason, which also means the guide's validation report cannot be reached from the screen.

## 7. Automation added

| Area | Tests |
|---|---|
| Device Details | pager walk with 11+ devices; filters apply on Search and Clear Filter restores; partial IMEI, padded IMEI, no match; View shows the details and the row menu has three actions; edit persists and SIM fields are read-only; 4 invalid edits; duplicate IMEI / serial on edit; delete with Cancel and Confirm; allocated device cannot be deleted |
| Registration form | 4 server messages (past SIM date, short mobile, short ICCID, long serial) with nothing created; 3 duplicates; a double click registers once |
| Bulk Upload | dialog, limit and sample columns; no file sends nothing; 3 unreadable files report "Bulk upload failed." and register nothing |
| Allocate Stock | step rules (Continue / Allocate disabled until chosen); search and select all; one request per double click on Allocate and on Confirm Rollback, Cancel keeps the allocation |
| History | newest first and Rollback only while Allocated; status filter and View details |
| Isolation | decisive cross-OEM edit / delete / read / rollback; registration with another OEM's master data |
| **Regression tests of confirmed bugs (expected failures)** | BUG-061 x2 (`test_the_sheet_is_read_into_complete_rows`, `test_a_filled_in_sample_registers_the_device`), BUG-062, BUG-063, BUG-064, BUG-065, BUG-066 x2 (`test_a_file_that_is_not_an_excel_sheet_is_refused_when_it_is_chosen` with 3 file types, `test_a_file_with_more_than_10000_rows_is_not_sent`), BUG-038 Edit / Delete |

## 8. Execution summary

| Run | Passed | Failed | Skipped | Expected failures |
|---|---|---|---|---|
| Device Management module, `--known-bugs` (after BUG-066 was added) | 33 | 0 | 0 | 11 |
| Device Management module, `--known-bugs` (before) | 33 | 0 | 0 | 7 |
| The 7 + older device bugs with `--runxfail` | - | 12 | - | each fails for its documented reason |
| OEM scope with `--known-bugs`, `-n 4` (project `.venv`) | 365 | 1 (intermittent dashboard link, passes 12 of 12 alone; not a product bug) | 0 | 50 |

Script problems fixed on the way (none were product bugs): the empty-state text and the details values appear twice in the DOM; the "n Selected" counter is split across elements; filters of the history apply asynchronously (wait for the request); the wizard counter test first read the row count before the list was drawn (a false pass); a regex with a word boundary was mangled when written; the geofence drawing Page Object now waits for the map tiles (an older test had become flaky: 5 of 6 first drags, now 16 of 16).

## 9. Remaining gaps and blockers

- **Blocked:** Repair and Replacement workflows, the SIM extension happy path and its 2 y / 1 y limit: they need a device installed on a vehicle by a fitment centre (the OEM account has none); OEM staff cannot be used for permission tests (BUG-039).
- **Not automated:** the date filters of the device list (custom pickers); the real JPEG / WEBP and very large (10,000-row) bulk files; the content of the Excel validation report through the screen (blocked by BUG-061).
- **Decisions needed:** observations 20-22 in `bug_report.md` (editing an allocated device's IMEI, SIM validity upper limit, the extra history statuses).
- **Next:** after BUG-061 is fixed, rerun `test_the_sheet_is_read_into_complete_rows` and `test_a_filled_in_sample_registers_the_device`, then add bulk-file tests (a bad row, an unknown master-data name and the report download) through the screen.
