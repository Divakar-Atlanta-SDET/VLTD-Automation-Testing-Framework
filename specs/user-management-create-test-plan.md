# User Management – Happy-Path Creation Test Plan

Scope: creating users from the Transport Commissioner (Admin) portal. Explored live on 2026-10-13 as the admin user;
no records were submitted during exploration.

## 1. What the module contains

Routes under `/tc/users/…` (Administration area of the sidebar):

| Entity | List page | Create entry point | Create route | Admin can create? |
|---|---|---|---|---|
| OEM | `/tc/users/oem` | button **Register OEM** | `/tc/users/oem/register` | Yes |
| RTO | `/tc/users/rto` | button **Register RTO** | `/tc/users/rto/register` | Yes |
| Inspector | `/tc/users/inspector` | button **Add Inspector** | opens form at `/tc/users/inspector` | Yes |
| Driver | `/tc/users/drivers` | button **Add Driver** (also *Bulk Upload*) | form at `/tc/users/drivers` | Yes |
| TC Staff | `/tc/users/staff` | button **Register Staff** | `/tc/users/staff/register` | Yes |
| Fitment Center | `/tc/users/fc` | none | – | **No** (created by OEM; Admin approves) |
| Permit Holder | `/tc/users/permit-holders` | none | – | **No** (created by Fitment Center; view-only) |

Every list page has summary counters (Total / Active / Suspended / Blacklisted), a Search box, filters, a table and
a row **Open actions** menu. The list is where a created record can be verified.
Row actions found: OEM *View details, Edit OEM* · RTO *View details, Edit* · Inspector *Transfer Inspector* ·
Driver *View Driver, View Audit, Edit Driver, Activate, Deactivate* · Staff *View details, Edit Staff*.
**There is no Delete action anywhere**, so test records cannot be removed from the UI (see Risks).

## 2. Create forms (fields observed)

**OEM** (all required except Address Line 2)
Business Name · OEM Code (unique) · CIN (21 chars, e.g. `L12345GJ2026PLC123456`) · GST Number (15 chars) ·
GST Certificate (PDF ≤ 2 MB) · TAC Number (unique) · TAC Issued On (date picker, not later than today) ·
TAC Certificate (PDF ≤ 2 MB) · COP Number (unique) · COP Valid From (date) · COP Valid Till (after valid-from, not
before today) · COP Certificate (PDF ≤ 2 MB) · Office Address · Address Line 2 · Pincode (6 digits) ·
Contact Person Name · Contact Mobile (10 digits) · Contact Email (also the OEM login) · Password (≥ 10 chars, upper +
lower + number) · Confirm Password (enabled only after Password is filled). Submit: **Register OEM**.

**RTO**
RTO Name · RTO Code (unique) · Contact Number · Contact Email · Address · District (select, Delhi districts) ·
Pincode (6 digits) · Map Location (search box or **Pin map center**) · Description (optional) · Password ·
Confirm Password. Submit: **Register RTO**.
Note: the address search returned "Location not found" in headless Chromium; **Pin map center** does set a
location (20.354000, 85.824000).

**Inspector**
Name · Email Address · Contact Number (10 digits) · City (select) · Address (optional) · RTO (select, e.g.
"DL-04 - Delhi") · Password (min 10 chars) · Confirm Password. Submit: **Create Inspector**.

**Driver**
Driver Name · Email Address · Contact Number · Driver Licence Number · State (select, 36 options) · City (enabled after
State) · Address · Password (≥ 10, upper + lower + number) · Confirm Password · Driver Licence (file: pdf/jpg/jpeg/png,
≤ 5 MiB) · Driver Photo (file: jpg/jpeg/png/webp, ≤ 5 MiB). Submit: **Register Driver**.

**TC Staff**
Staff Name · Email Address · Contact Number · Permissions (63 in 15 groups, checkboxes, *Select All* / *Clear All*,
search) · Password · Confirm Password. Submit button is below the fold (not yet seen).

## 3. Test data strategy

- Every run creates **unique** data from a timestamp suffix (`AUTO` prefix) so unique fields (OEM code, TAC, COP, RTO
  code, email, licence number) never collide: e.g. `auto.oem.<yyyymmddHHMMSS>@example.com`.
  `utils/data_generator.py` is currently empty and will hold these generators.
- Format-valid values: CIN `U72200KA2014PTC` + 6 digits; GST 15 chars; 6-digit pincode; 10-digit mobile starting
  with 9; password `Auto@12345Test`.
- Files: your `test.pdf` for all three OEM certificates and the driver licence. I suggest moving it to
  `data/files/test.pdf` to keep the project root clean. The driver photo needs an image, so the test writes a tiny valid
  PNG to a temp folder at runtime (no extra file in the repo).
- Dates are computed relative to today (TAC issued yesterday, COP valid from today to today + 1 year).
- Inspector's RTO and City are picked from the live option lists (first available), not hard-coded.

## 4. Scenarios (happy path)

Each scenario is independent, starts logged in as admin, creates one record, and verifies it. Marker: `user_management`
(+ `critical`).

### UM-01 Register an OEM
1. Open `/tc/users/oem`, note the **Total OEMs** counter, click **Register OEM**.
2. Fill the OEM, GST, TAC, COP, address and contact sections with unique valid data.
3. Upload `test.pdf` to the GST, TAC and COP certificate fields.
4. Pick TAC issue date, COP valid-from and valid-till in the date pickers.
5. Enter the password and confirm it (Confirm Password becomes enabled).
6. Click **Register OEM**.

Expected: success feedback is shown; the app returns to the OEM list; searching the unique OEM code (or email) shows one
row with the business name, `Code: <code>`, CIN, GST, TAC, COP and valid-till date, contact name/email/mobile, address
and **Active**; Total OEMs increases by 1.

### UM-02 Register an RTO
1. Open `/tc/users/rto`, note **Total RTOs**, click **Register RTO**.
2. Fill name, unique code, contact number/email, address, district, pincode, description.
3. Click **Pin map center** and confirm the location text changes from "No location selected".
4. Enter and confirm the password; click **Register RTO**.

Expected: success feedback; RTO list shows the new code/name/contact/district and **Active**; Total RTOs +1.

### UM-03 Create an Inspector
1. Open `/tc/users/inspector`, note **Total Inspectors**, click **Add Inspector**.
2. Fill name, email, contact number; choose a City and an RTO; enter an address.
3. Enter and confirm the password; click **Create Inspector**.

Expected: success feedback; the Inspector list (search by email) shows name, email, contact, city, the assigned RTO,
role *RTO Inspector*, **Active** and today's created date; Total Inspectors +1.

### UM-04 Register a Driver
1. Open `/tc/users/drivers`, note **Total Drivers**, click **Add Driver**.
2. Fill name, email, contact, licence number; choose State then City; enter address.
3. Enter and confirm the password; upload the licence (`test.pdf`) and the photo (generated PNG).
4. Click **Register Driver**.

Expected: success feedback; the Driver list (search by email or licence) shows the driver with licence number, contact,
location and **Active**; Total Drivers +1. *Open actions → View Driver* shows the entered details.

### UM-05 Register TC Staff
1. Open `/tc/users/staff`, note **Total Staff**, click **Register Staff**.
2. Fill name, email, contact number.
3. Select a small set of permissions (e.g. the *View Alerts* permission, then confirm the counter reads "1 of 63
   selected"; *Clear All* resets it).
4. Enter and confirm the password; submit.

Expected: success feedback; Staff list shows the new staff with **Active**; Total Staff +1.

### UM-06 Fitment Center and Permit Holder pages are read-only for Admin (guard)
1. Open `/tc/users/fc` and `/tc/users/permit-holders`.

Expected: lists load, no Register/Add/Create button is present (documents the "Admin cannot create" rule).

## 5. Risks, assumptions and open points

1. **Records cannot be deleted** from the UI, so each run leaves five more records in the environment. The Driver can
   be deactivated, the others cannot be removed. This looks like a shared QA environment (other people's test records
   are present). Please confirm it is acceptable to create these records here, or give me a separate environment.
2. **Unverified until the first run:** the exact success toast text, whether the app redirects to the list after
   saving, the Staff submit button name, and whether any hidden validation (for example GST/CIN checksums, or RTO
   location vs. district) rejects my generated values. I will confirm these on the first run and adjust the data
   rather than weaken the assertions.
3. **RTO map:** address search is unreliable in headless mode, so the test uses **Pin map center**. The pinned
   coordinates are outside Delhi; if the app rejects them, I will report it as an observation.
4. **Out of scope for this first batch:** negative/validation tests, edit/suspend/blacklist flows, Inspector transfer,
   Driver bulk upload, and logging in as each newly created user (a useful next step for OEM, RTO and Inspector).

## 6. Implementation outline (pytest, Python)

- `pages/administration/`: one page object per entity (`oem_page.py`, `rto_page.py`, `inspector_page.py`,
  `driver_page.py`, `staff_page.py`) with `open_list()`, `open_create_form()`, `fill_*`, `submit()` and
  `search_row()` helpers; a small shared `DatePicker` helper for the calendar widget.
- `utils/data_generator.py`: unique-data generators; `utils/file_utils.py`: PNG creation.
- `tests/administration/test_user_creation.py`, markers `user_management`, `critical` (registered in `pytest.ini`).
- Reuses the existing `login_page_obj` / `admin_credentials` fixtures with a new `admin_page` fixture (logged-in page).
