# OEM Management (Device Models, Firmware, SIM Modules) - Test Plan

Scope: Administration -> OEM Management: **Device Models** (`/tc/oem-management/device-models`), **Firmware**
(`/firmware`) and **SIM Modules** (`/sim-modules`). All three are CRUD screens for records that belong to an OEM.
Explored 2026-10-15 in the live application. Defects found are logged in `bug_report.md` (BUG-021 ... BUG-031; BUG-023 and BUG-028 are already fixed).

## 1. What each screen offers

| | Device Models | Firmware | SIM Modules |
|---|---|---|---|
| Table columns | Sr.No, OEM, OEM Code, Model Name, Part No, TAC No, COP No, Network Profile, Status, Actions | Sr.No, OEM, Device Model, Part No, Version, Release Date, Update Type, Status, Actions | Sr.No, OEM, OEM Code, Manufacturer, Module Name, Operators, SIM Type, Status, Actions |
| Search (placeholder) | "Model, TAC, OEM, code..." | "Version, OEM, model, part no..." | "OEM, code, module, operator..." |
| Filters | OEM, Status | OEM, Update Type, Status | OEM, Status |
| Row actions | View Model, Edit Model, **Download TAC**, Delete Model | View / Edit / Delete Firmware | View / Edit / Delete SIM Module |
| Form fields (* required) | OEM*, Model Name* (max 100), Part Number* (max 100), Network Profile (max 150), Status, Description, TAC Number* (max 100), TAC Issued On* (date, not in the future), TAC Certificate* (PDF, max 2048 KB), COP Number / Valid From / Valid Till / Certificate (all or none) | OEM*, Device Model*, Firmware Version* (max 50, unique per model), Release Date, Update Type (Optional / Mandatory), Status, Release Notes | OEM*, SIM Manufacturer* (max 150), Module Name* (max 150, unique per OEM), Status, Primary / Secondary Operator (max 100), Primary / Secondary SIM Type (max 100) |

Behaviour found by exploration:
- Search and the three filters run **in the browser on the rows already loaded**; they send no request.
- The lists page at **10 records**; the UI has **no pager** (BUG-024).
- Success messages: "... created / updated / deleted successfully."; validation messages appear under the field and as a banner.
- The server API (`/api/device-models`, `/api/device-firmwares`, `/api/sim-modules`) pages with `per_page` / `page`, supports
  `search` and `oem_id`, and **needs `?oem_id=` on DELETE**.

## 2. Test data strategy

- Records a test needs are created through the **API** (fast, independent of the UI under test) under a dedicated "AUTO OEM".
- **Cleanup**: the `records` fixture deletes everything a test created, even when the test fails.
  A safety net (`utils/cleanup.py`) runs once at the end of every run - after all parallel workers finished - and
  removes leftovers, deactivates test staff accounts and reports what only the DB owner can remove.
  `pytest --keep-test-data` skips it; `python -m utils.cleanup` runs it by hand.
- **Persistent seed**: as requested, every list keeps **at least 12 records** ("AUTO PG ..." Device Models, Firmware, SIM Modules)
  so that each list always spans two pages for the pagination checks. The seed is created on demand, never deleted.

## 3. Techniques and what they cover

| Technique | Applied to |
|---|---|
| **Boundary value analysis** | Every text field at (1, max-1, max) accepted and (max+1, 2 x max) refused: Model Name / Part No / TAC No 100, Network Profile 150, COP No 100, Firmware Version 50, SIM Manufacturer / Module Name 150, operators and SIM types 100. TAC issue date around **today** (yesterday / today accepted, tomorrow refused). Certificate size around **2048 KB** (2048 KB - 1 B, 2048 KB, 2048 KB + 1 B, 5 MB). Paging: per_page, page beyond the last, invalid values. |
| **Equivalence partitioning** | Per required field: valid / missing / blank / whitespace-only. Certificate: PDF / PNG / JPG / text / executable / double extension. Dates: valid, impossible (30 Feb), wrong format, text. OEM reference: valid / missing / non-numeric / zero / unknown. Booleans: true / false / 1 / 0 / text. Duplicates: same name, same name with another manufacturer, same version on another model. Search: full / partial / lower / upper case / other columns / special characters / no match. |
| **State-based** | Active vs Inactive, Optional vs Mandatory, filters combined with search, edit then cancel, create then reset. |
| **Error guessing / security** | Markup in text fields stored and shown as plain text, special characters in search (SQL, regex, script), malformed ids, calls without a token. |

## 4. Scenarios

### UI (per screen)
- **Table**: controls and column order; row content; serial numbers; row menu; View panel (and Close); Download TAC (PDF).
- **Search**: by name / version / TAC / part no / OEM name and code / other columns; case-insensitive; no match -> empty state; clear restores; special characters.
- **Filters**: OEM, Status, Update Type (Firmware); combined with search; no-result state.
- **Create**: happy path (all fields, required only, inactive); empty form lists every required field; each required field alone; whitespace-only;
  field limits (typing stops at 100 where the box has a limit; server message beyond it); TAC date boundary; certificate type and size boundary;
  COP all-or-none and date order; duplicate; Cancel; Reset.
- **Update**: form is pre-filled; save and see the table change; switch status; blank required field refused; duplicate refused; Cancel keeps the record.
- **Delete**: confirmation names the record; Cancel keeps it; confirm removes it.

### Pagination (`test_oem_mgmt_pagination.py`)
First page = newest 10 records; every record reachable (pager or search); search finds a record beyond page 1.

### API (`test_oem_mgmt_api.py`)
Create / read / update / delete for the three resources with the boundary and partition tables above; read semantics common to the three lists
(pagination metadata, pages do not overlap, empty page, invalid paging values, search, special characters); authentication on every verb.

## 5. Results

| Area | Tests | Result |
|---|---|---|
| SIM Modules UI | 54 | all pass; Delete tracked as BUG-021 |
| Device Models UI | 62 | all pass except tracked defects: Delete (021), Update (022), image certificates (026) |
| Firmware UI | 47 | all pass except tracked defects: Delete (021), OEM / Part No dashes (025). Create from the UI works since the 2026-10-15 build (BUG-023 and BUG-028 fixed) |
| Pagination | 12 | 6 pass; the 6 "every record is reachable" checks are tracked as BUG-024 |
| API | 214 | all pass except tracked defects: native multipart update (022), non-numeric model id (027), orphaned firmware (029, not run), unstable sort (030), reuse of deleted names (031) |

The application was updated while testing was in progress: Firmware creation from the UI now works (the Device Model list is loaded for the chosen OEM) and the
Add Firmware form no longer has a Status field. The tests were adjusted and the two fixed defects are marked FIXED in `bug_report.md`.

## 6. Not covered
- Permission checks per role for these screens (the `device_models.*`, `device_firmwares.*`, `sim_modules.*` permissions are covered in `tests/permissions`).
- Firmware file upload (`firmware_file` / checksum): no UI or API field could be identified.
- The OEM-side view of these records (needs an OEM login).
