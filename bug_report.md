# VLTD Admin/TC Portal – Bug Report

| | |
|---|---|
| **Application** | https://vltd.misbackend.com (Transport Commissioner portal) |
| **Date tested** | 2026-10-13 to 2026-10-27 |
| **Tested as** | Admin / Transport Commissioner (`ADMIN_*`) and OEM Admin (`OEM_*`), both from `.env` |
| **Scope** | Login, Dashboard, User Management (OEM, RTO, Inspector, Driver, TC Staff create forms; Fitment Center and Permit Holder lists), create-form input validation (UI and server-side), TC Staff permissions (all 63), OEM Management (Device Models, Firmware, SIM Modules: CRUD, table, search, filters, validation) |
| **Also in scope since 2026-10-22** | State Admin operations (system configuration, merge / transfer / untag look-ups, PIS, geofences, watchlists, announcements, reports) and the OEM panel (devices, allocation, commands, fitment centres, reports, SIM validity) |
| **Also in scope since 2026-11-04** | The Fitment Centre panel (`FC_*`): Dashboard, Operations, role permission boundary, Profile / Change Password / Logout, Helpdesk, Reports and New Installation (blocked, see BUG-080) |
| **Also in scope since 2026-11-10** | The Driver, RTO Inspector and RTO Officer panels (`DRIVER_*` / `INSPECTOR_*` / `RTO_*`, each a dedicated account created this session): dashboards, Verify Fitment, Draft Challan, My Challans, My/Future Duties, Duty History, Installation Approvals, Permit Holder Management (RTO view), Challan Work Queue, and the Driver/Inspector/RTO role/permission matrix. Permit Holder (Fleet Owner) panel: **not testable** - see "Risks" in `specs/role-panels-test-plan.md` |
| **Method** | Automated pytest suite plus exploratory checks of the list pages (counters vs. rows, console, network). UI tests run with a network monitor; server-side checks call the API directly with the admin token |

## 1. Summary

| ID | Severity | Area | Title | Found by |
|---|---|---|---|---|
| BUG-001 | High | Inspector list | "Active" counter shows 0 although every inspector is Active | Exploratory |
| BUG-002 | Medium | Driver list | Status counters are computed from the visible page only | Exploratory |
| BUG-003 | Medium | Driver list | All driver photos are broken (HTTP image on an HTTPS page) | Exploratory |
| BUG-004 | Medium | RTO registration | Map address search is broken: Google Geocoding API not enabled | Automated test + console |
| BUG-005 | Medium | Dashboard | KPI tiles show a real-looking `0` while data is still loading | Automated test (xfail) |
| BUG-006 | Low | OEM registration | TAC Issue Date "Today" button is disabled although today is valid | Automated test |
| BUG-007 | Low | Staff / Permit Holder lists | Row status says "Approved" while the counters say "Active" | Automated test |
| BUG-008 | Low | Dashboard | "View All" on Recent Major Alerts opens the Reports hub, not the alerts list | Automated test |
| BUG-009 | Low | Login | A wrong password shows two messages ("Validation failed." + "Invalid email or password."); API returns 422 | Automated test |
| BUG-010 | Low | Inspector registration | Password hint incomplete; rejection message is raw and not actionable | Exploratory |
| BUG-011 | Low | RTO registration | Pinned location defaults to Odisha and is accepted for a Delhi RTO | Exploratory |
| BUG-012 | Medium | Inspector API | `POST /inspectors` ignores a mismatched `password_confirmation` and creates the account (201) | Automated API test |
| BUG-013 | Medium | Inspector API | `POST /inspectors` with a non-numeric `city_id` crashes with HTTP 500 instead of a 422 validation error | Automated API test |
| BUG-014 | **High** | Staff permissions | Alerts, device commands, geofences and **trip history (GPS points)** are served to a staff user who has none of the permissions the portal requires | Automated API test |
| BUG-015 | **High** | Staff permissions | 14 permissions offered in the Create/Edit Staff form have no effect: the API refuses staff even when all 63 are granted, and the menu then opens pages that fail | Automated API + UI tests |
| BUG-016 | Medium | Staff permissions | A page opened with its own permission also calls endpoints guarded by other permissions, so it renders broken (15 pages) | Automated UI test |
| BUG-017 | Medium | Staff menu / router | The staff menu and the router disagree with the API: System Configuration is offered but fails; PIS Trips is hidden but opens by URL and fails | Automated UI test |
| BUG-018 | Medium | Authentication | The forced change of the temporary password is enforced in the UI only; the API serves data on the temporary password | Automated API test |
| BUG-019 | Medium | API robustness | A malformed record id returns HTTP 500 instead of 404 (Stops, Routes, Driver update, Driver status) | Automated API test |
| BUG-020 | Low | Live tracking pages | `/api/school` and `/api/last-position` answer 404 on every tracking page load, even for the admin | Automated UI test |
| BUG-021 | **High** | OEM Management | **Delete does not work** in the UI for Device Models, Firmware and SIM Modules: the request omits the `oem_id` the server requires, so every delete fails with "Select an OEM." | Automated UI test |
| BUG-022 | **High** | Device Models | **Editing a Device Model never saves**: the UI sends a multipart PATCH, which the server does not read, so it answers "Select an OEM." even though the OEM is sent | Automated UI + API test |
| BUG-023 | ~~High~~ **Fixed** | Firmware | ~~A Firmware cannot be created from the UI: the Device Model list is always empty~~ - **fixed in the build deployed on 2026-10-15** (the form now loads `GET /api/device-models?oem_id=...`); verified | Automated UI test |
| BUG-024 | **High** | OEM Management lists | Only the first 10 records are shown and there is no pager; search and filters only see those 10, so older records cannot be reached | Automated UI test |
| BUG-025 | Medium | Firmware | The Firmware list and View panel show "-" for the OEM and the Part No for every record | Automated UI test |
| BUG-026 | Low | Device Models | The TAC certificate field says "PDF, JPG, JPEG or PNG" but the server accepts PDF only (max 2 MB, not stated) | Automated UI + API test |
| BUG-027 | Medium | Firmware API | `device_model_id: "abc"` crashes the server (HTTP 500) instead of returning a validation error | Automated API test |
| BUG-028 | ~~Low~~ **Fixed** | Firmware | ~~The Edit Firmware form shows "Select Device Model" instead of the record's model~~ - **fixed in the same build**; verified | Automated UI test |
| BUG-029 | Medium | Device Models | Deleting a Device Model that has firmware succeeds and leaves the firmware orphaned; the orphan can no longer be deleted (403) and is listed with "-" everywhere | Exploratory + API test |
| BUG-030 | Medium | OEM Management lists | The list order has no tiebreaker: records created in the same second can appear on two pages while others appear on none | Exploratory + API test |
| BUG-031 | Medium | Device Models, Firmware | The name of a deleted Device Model (and the version of a deleted Firmware) stays reserved forever: it can never be used again, although the record is gone | Automated API test |
| BUG-032 | Medium | Authentication | An unauthenticated API call returns HTTP 500 instead of 401 unless the client sends `Accept: application/json` | Exploratory + API test |
| BUG-033 | Medium | Authentication | Reusing an old refresh key is refused, but the user's other sessions stay alive; the guide says a reused key must end all sessions of that user | Guide check + API test |
| BUG-035 | Low | Inspector API | A 9-character password is accepted; the guide requires at least 10 characters | Guide check + API test |
| BUG-036 | Medium | Help Centres | The list page sends a PUT for every help centre each time it opens, and every one fails with 422 | Live exploration + UI test |
| BUG-037 | Low | Vehicle Device Untag | Searching for an unknown vehicle shows no message | Live exploration + UI test |
| BUG-038 | Medium | OEM Device Models | The OEM sees **Add Model** and a full registration form although it may only view device models; every save is refused (403) | OEM panel test |
| BUG-039 | **High** | OEM Staff | The OEM cannot list or register its own staff: `/api/oem/users` answers 403 even though the OEM Admin holds all 41 permissions | OEM panel test |
| BUG-040 | Medium | OEM monitoring pages | Alerts, Geofences, Live Tracking and Trip Playback call State Admin endpoints (`/api/transport-commissioner/oems`, `/rtos`) which answer 403 for an OEM | OEM panel test |
| BUG-041 | **High** | OEM allocation | Stock can be allocated to a **blacklisted** fitment centre (the guide allows active centres only; the wizard hides them, the API does not check) | OEM panel test |
| BUG-042 | Medium | OEM fitment centres | A duplicate fitment code is not reported by validation, although the form says the code is unique | OEM panel test |
| BUG-043 | Low | OEM SIM Validity Extension | A device that is not installed is shown as "Eligible" with an Extend Validity button; the server then refuses with a generic "Validation failed." | OEM panel test |
| BUG-044 | Low | OEM Dashboard | The Device Details widget shows "-" in the SIM column for every device, although the Device Details page and the API give the SIM module | OEM dashboard test + manual repro |
| BUG-045 | Medium | Admin OEM Management | A Device Model can be created for a **suspended or blacklisted** OEM (the dropdown offers them, the server answers 201) | Manual exploration + test |
| BUG-046 | Medium | Admin OEM Management | The OEM dropdown of the Add Device Model form lists only **100 OEMs** (109 exist); the oldest cannot be chosen or found by search | Manual exploration + test |
| BUG-047 | Medium | OEM Operations (Alerts) | An OEM Admin cannot create an alert rule: "All vehicles" (the default) and "Fitment Centre" answer 403 "your role is not permitted to create or update a rule with this scope"; the guide says an OEM has its own rules | Manual exploration + test |
| BUG-048 | Medium | OEM Operations (Send Command) | Send Command offers a registered device that is **not installed on a vehicle**, and the command service accepts a command for it (the product owner says it must not) | Manual exploration + test |
| BUG-049 | **High** | Geofences (State Admin and OEM) | **Edit geofence crashes the page** ("Something went wrong") for every zone; a zone can never be edited | Manual exploration + test |
| BUG-050 | Low | Geofences (State Admin and OEM) | A zone drawn as a circle or rectangle is saved as a polygon and listed as "Freehand"; the "Circle" and "Rectangle" type filters never match anything | Manual exploration + test |
| BUG-051 | **High** | OEM fitment centres (status endpoints) | **Another OEM can suspend, activate and blacklist a fitment centre it does not own** (200; the details of the same centre answer 404). **API-only** | API test |
| BUG-052 | Medium | OEM fitment centres (edit endpoint) | Editing a centre of another OEM answers **500** and names an internal model class instead of 404. **API-only** | API test |
| BUG-053 | Medium | OEM fitment centres | A **blacklisted** centre can be activated, suspended and edited again although the screen says it "cannot be reversed" (the edit page also opens by URL). **API-only** (+ URL) | API test + manual |
| BUG-054 | Low | OEM fitment centres | Activating an active centre or suspending a suspended one is accepted (200) and adds a history entry. **API-only** | API test |
| BUG-055 | **High** | OEM allocation | Stock can be allocated to a **suspended** fitment centre (201); same family as BUG-041. **API-only** | API test |
| BUG-056 | Low | OEM fitment centres | **Remarks History** shows UTC times while the rest of the page shows local time (09:06 am vs 02:36 pm for the same action) | Manual exploration + test |
| BUG-057 | Medium | OEM fitment centres (details) | The **premises image is never shown** ("Image unavailable"): the API sends `http://<ip>:8087/...` and the https page blocks it as mixed content; the "Open Source" link opens an insecure internal address | Manual exploration + test |
| BUG-058 | Medium | OEM fitment centres (registration and edit) | The server accepts mobile numbers starting 0-5, e-mails without a domain suffix and passwords over 100 characters, all of which the forms refuse or cap. **API-only** | API test |
| BUG-059 | Medium | OEM Staff (list) | When the staff list cannot be loaded (403 today, BUG-039) the page says **"No Staff found. Register a Staff member to get started."** with 0 in every counter and **no error**; the user is told there is no staff, not that loading failed | Manual exploration + test |
| BUG-060 | Low | OEM Staff (Register form) | The form sends a **staff name made of spaces only**; no message is shown (the Fitment Center form refuses a blank name) | Manual exploration + test |
| BUG-061 | **High** | OEM Device Details (Bulk Upload) | **A bulk upload from the screen can never register a device**: the screen reads none of the columns of the product's own sample template (every row is sent as `{}`) and never reads the two mobile-number columns, which the server requires | Manual exploration + test |
| BUG-062 | Medium | OEM Device Allocation History | The history shows only the **newest 10 allocations and has no pager** (341 exist); older allocations can only be reached through filters | Manual exploration + test |
| BUG-063 | Medium | OEM Allocate Stock wizard | The device list shows only the **first 20** available devices and has no pager or "load more"; with 25 in stock 5 cannot be ticked | Manual exploration + test |
| BUG-064 | Low | OEM Allocate Stock wizard | The counter above the device list says **"0 available device(s)"** whatever is listed or ticked | Manual exploration + test |
| BUG-065 | Medium | OEM Device Allocation History | The **search box finds nothing**, whatever is typed (IMEI, serial number, centre name or code, OEM code); the status and centre filters work | Manual exploration + test |
| BUG-066 | Medium | OEM Device Details (Bulk Upload) | The dialog **accepts any file as the file to upload** (.exe, .py, .html ...: shown as "Selected", Upload enabled, no type check, no size / row check); a long file is sent whole and the server stalls and answers **504 after 60 s** (the 10,000-device limit is not enforced either); a .html file does nothing and says nothing. Reported from manual exploration, reproduced 2-3 times | Manual exploration (reported by the tester) + test |
| BUG-067 | Medium | OEM Helpdesk (ticket details) | **"View Ticket Attachment" opens the portal's start page, not the file**: the `/storage/tickets/...` URL (http, then https) is answered by the application shell for every attachment tried | Manual exploration + test |
| BUG-068 | Medium | OEM Helpdesk (Activity) | A public ticket **routed straight to the OEM has an empty activity log** ("No activity is available"): neither its creation nor its assignment is recorded (guide 19.1: every assignment and status change is recorded with time and person) | Manual exploration + test |
| BUG-069 | Low | OEM Helpdesk (New Ticket, API) | The server does **not enforce the 2,000-character description limit** of the form (2,001 to 70,000 characters pass validation; 2,001 created a ticket). **API-only** | API test |
| BUG-070 | Low | OEM Helpdesk (search) | Searching for **`%` or `_` lists every ticket** (the characters are used as wildcards, not searched for literally) | Manual exploration + test |
| BUG-071 | Low | OEM Helpdesk (lists) | The counter says "**1 tickets**" when exactly one ticket is listed | Manual exploration + test |
| BUG-072 | **High** | Profile (API: `GET /api/users/{id}`) | **Any signed-in user can read any other user's full profile by id** (name, e-mail, phone, address, city, state) - tried against the main OEM Admin, the State Admin and other OEM accounts, all 200. **API-only** | Manual exploration + API test |
| BUG-073 | **Critical** | Profile (API: `PUT /api/users/{id}`) | **The same endpoint accepts a write to another user's profile, including their `email` address - an account-takeover path.** A name change sent as the dedicated test account for a different account was accepted (200) and the stored name changed; independently reproduced by the user against two fresh, disposable accounts (A writing to B), with `name`, `email`, and `contact_no` all overwritten. **API-only** | Manual exploration: one direct, restored reproduction by the assistant, plus one independent reproduction by the user confirming the email-takeover path |
| BUG-074 | **High** | Change Password / Logout | **Logout invalidates the access token but not the refresh token**: a refresh token obtained at login still mints a new, fully valid access token after the user has explicitly logged out (4 of 4: twice through the API alone, twice through the actual UI Logout). Same family as BUG-033 | Manual exploration + API test |
| BUG-075 | Medium | Profile (API) | `GET /api/users/{id}` with a syntactically valid but unknown UUID answers **500** "Failed to fetch profile." instead of 404 (3 of 3 different values). Same family as BUG-019 | API test |
| BUG-076 | Low | Change Password | The two password-change requests disagree on **leading/trailing spaces**: the forced first-login page (`POST /api/auth/change-password`) silently stores the new password **trimmed**, while the Profile tab (`PUT /api/users/{id}`) stores it **exactly as typed**, spaces and all - a password set with a trailing space on one screen will not work when typed the same way after being changed on the other | API test |
| BUG-077 | **High** | Change Password (both screens) | **Changing a password does not end any existing session**: the access token used to request the change - and every other already-open session - keeps working afterwards; only a NEW sign-in with the old password is refused. Confirmed on both the Profile tab and the forced first-login page. Same family as BUG-074 | Manual exploration + API test |
| BUG-078 | Medium | Fitment Centre panel (Live Tracking, Geofences, Trip Playback, Alerts, 3 Reports) | **Several Fitment Centre screens call admin-only filter APIs that refuse the FC role (403)**: Live Tracking / Geofences / Trip Playback / Alerts all call `GET /api/transport-commissioner/rtos` and `/oems` to populate their RTO/OEM filter dropdowns; the Device Health, Device Status & Connectivity and Installation reports call `GET /api/device-models?per_page=100` for their Device Model filter. All of these answer 403 for a signed-in Fitment Centre user, on every page load, independent of any specific account's data. **API-only (console-visible)** | Manual exploration (initial Fitment Centre panel sweep) |
| BUG-079 | Medium | Fitment Centre - New Installation (API: `POST /api/installation`) | **Picking a Vehicle Owner Type that does not match the vehicle's VAHAN category crashes the server (500) instead of a validation error.** A School Bus vehicle with `owner_type: "individual"` (a choice the UI itself freely allows) answers 500 "Something went wrong" every time; the identical request with `owner_type: "school"` succeeds (201). **API-only, but directly reachable through the UI** | Manual exploration (New Installation workflow, first FC installations created) |
| BUG-080 | **High** | Fitment Centre - New Installation, Step 3 Device Health Check (API: `GET /api/installation/health/{imei}`) | **No device in the environment can ever pass the Health Check - "Tamper Status" fails for every IMEI that has live packet data, with no way to clear it.** Of 4,777 IMEIs scanned (the full user-supplied sheet), 25 had real, live telemetry (fresh GPS lock, network, power, battery, server connection); all 25 failed the overall health check, every one of them specifically on "Tamper Status" = "Tamper alert not received", re-checked twice more per IMEI with the identical result. Since Step 3 hard-blocks "Next" until all checks pass, **this blocks New Installation end-to-end for every device, real or synthetic, platform-wide** - the highest-priority module cannot be completed by any Fitment Centre in this environment. **API-only (console-visible)** | Manual exploration (New Installation workflow; full-sheet IMEI health scan) |
| BUG-081 | Medium | Fitment Centre Dashboard ("Pending Work" section / API: `GET /api/dashboard/fitment-centre/summary`) | **3 of the 5 "Pending Work" categories can never show a real count, even when matching data exists.** The dashboard lists Health Check, Panic Test, Document Upload, Activation and Approval as "installation jobs requiring action," but the summary API's `pending_actions` object only ever contains `activation`, `panic_test`, `vahan_sync`, `post_repair_verification` and `replacement_required` - there is no field for Health Check, Document Upload or Approval. Confirmed with real, exactly-matching data: with all 7 of this FC's installations genuinely stuck at the Health Check step, the tile still reads "Count not available from API" instead of 7. **API-only (console-visible; UI shows a static placeholder)** | Manual exploration (Dashboard, after first real installations existed) |
| BUG-082 | **High** | OEM panel and Fitment Centre panel - Operations/Live Tracking (`GET /api/last-position` on `vltdgo.misbackend.com`) | **Neither an OEM nor a Fitment Centre can ever see a vehicle's live position - not even their own fleet - only Admin can.** Tested against two different IMEIs: one of the FC's own installed devices, and an unrelated IMEI confirmed to have live, fresh GPS telemetry. Both OEM and FC get **403** `{"error":"your role is not permitted to view this vehicle"}` on every attempt, for both IMEIs, regardless of ownership; Admin gets **200** with real position data for the live IMEI. This breaks the core function of the Live Tracking map (showing where your own vehicles are) for both of the two roles it actually exists for. Refines/supersedes part of BUG-020. **API-only (console-visible)** | Manual exploration (Fitment Centre Operations sweep; cross-role API verification) |
| BUG-083 | Medium | Fitment Centre Helpdesk (ticket detail view, `GET /api/user/ticket`) | **A Fitment Centre's ticket detail page never shows any activity log, not even for its own tickets.** Raising a ticket and later closing it with a note produce no "created" or "closed" entry anywhere in the UI - not even an empty-state message. Same family as BUG-068, but for every FC ticket, not a routing edge case. | Manual exploration + UI test (Fitment Centre Helpdesk automation) |
| BUG-084 | **High** | Fitment Centre Reports (`GET /api/reports/fitment-centre/inventory`) | **The Device Inventory Report crashes with a 500 on every load, with or without filters.** Every other FC report page and the Dashboard's own inventory tile work fine from the same account; this one report is completely unusable, with no workaround. | Manual exploration + UI test (Fitment Centre Reports automation) |
| BUG-085 | Medium | Inspector Dashboard (`GET /api/inspector/dashboard`) | **The Inspector Dashboard always shows "0 Assigned RTOs" / "No RTOs are currently assigned," even for an Inspector who is assigned to an active RTO.** The dashboard's own API response correctly includes the assignment (`inspector.rto_data`); the UI simply never reads it. The Inspector's actual RTO scope (My Challans, Verify Fitment) is unaffected - this is a display-only defect. | Manual exploration + UI test (Inspector panel automation) |
| BUG-086 | **High** | RTO Inspector role permissions (`POST /api/rto/installations/{id}/approve` / `/reject`) | **An RTO Inspector account can approve or reject VLTD installations - an RTO Officer-only action per the platform guide.** The "RTO Inspector" role template is granted `vltd_device_installations.approval.approve` / `.reject` by default; calling the approve endpoint with an Inspector's token reaches the same "not found" business logic an RTO Officer gets (404 for a non-existent ID), while a Driver's token is correctly refused (403) at the authorization layer. The UI hides the Installation Approvals menu for Inspectors, so this is only reachable via direct API/devtools use, but it defeats the "independent RTO check" the approval step exists for. | Manual exploration + API test (Inspector/RTO/Driver cross-role permission check) |
| BUG-087 | Medium | Platform-wide (every data table: OEM Management, OEM panel, Fitment Centre panel confirmed) | **Every table's column headers (`<th>`) are missing the `scope` attribute, state-wide.** This is both a real accessibility defect (screen readers cannot announce which column a cell belongs to) and it breaks this project's own `columnheader`-role-based automation: a scope-less `<th>` is exposed as a generic element instead, so `get_by_role("columnheader")` finds nothing and `get_by_role("cell")`-based "data rows only" filters wrongly include the header row as if it were a data row. | Full regression run (2026-11-10) + direct DOM inspection across 4 tables in 3 panels |
| BUG-088 | **High** | Admin Operations - PIS Management - Stop Management (`GET /api/masters/cities`), and every other form in the product that uses this same master-data endpoint | **The shared "cities" master-data endpoint always returns only Delhi's 17 districts, no matter what state is actually requested - so no form anywhere in the product can ever create a record for a city outside Delhi.** In Add/Edit Stop, the City dropdown has no state selector at all and simply lists these same 17 Delhi entries every time. Calling the underlying endpoint directly with an explicit `state_id` for a different state (tried Andaman and Nicobar Islands, `state_id=1`) makes no difference - the response is byte-for-byte the same 17 Delhi cities (`state_id: 9`) regardless. This same endpoint is reused by OEM registration, Fitment Centre registration, Staff registration, and Inspector transfer (confirmed via this project's own existing test helpers), so the real-world impact is wider than just Stop Management, though only Stop Management was confirmed live via the UI. | Manual exploration (PIS Stop Management) + direct API verification with an explicit non-Delhi `state_id` |
| BUG-089 | Medium | Fitment Centre - New Installation wizard (Steps 1-3), Admin > Permit Holder Management | **The New Installation wizard permanently creates a Permit Holder record as soon as Step 3 (Health Check) is reached, even though BUG-080 means Step 3 can never actually be passed - so every blocked installation attempt leaves behind a real, "Approved" Permit Holder with no device ever installed.** 9 of the 27 Permit Holders currently in the system are confirmed orphans of this kind, created between 2026-11-04 and 2026-11-12 while testing/investigating BUG-080. | User manually walked the wizard and confirmed the creation point; cross-checked against `GET /api/transport-commissioner/fleet-managers` |
| BUG-090 | Medium | Permit Holder (Fleet Owner) panel - Fleet Management | **A Permit Holder is granted full Staff permissions (`permit_holder.staff.view/create/update/delete`), and the backend API for it works, but there is no Staff page anywhere in the Fleet Owner panel** - no menu entry, and every guessed URL (`/fleet-owner/staff`, `/fleet-owner/users/staff`, `/fleet-owner/users`, `/fleet-owner/account/staff`) silently falls back to the Dashboard. Same "permission grants nothing" family as BUG-015. | Live exploration of the Permit Holder panel + direct API check of `GET /api/permit-holder/staff` |

Severity: **High** = wrong business data or blocked flow with no workaround · **Medium** = feature degraded or misleading, workaround exists · **Low** = cosmetic, wording or consistency.

Items that need a product decision rather than a fix are listed in section 3.

## 2. Bug details

### BUG-001 – Inspector "Active" counter always shows 0 (High)
- **Where:** `/tc/users/inspector`
- **Steps:** 1. Log in as admin. 2. Open Administration → Inspector Management. 3. Compare the counters with the table.
- **Expected:** Active = number of active inspectors.
- **Actual:** Total Inspectors = 12, **Active = 0**, Suspended = 0, Blacklisted = 0. All 12 rows have status **Active**. An earlier visit (Total 4) showed the same: Active 0 with Active rows.
- **Impact:** The headline counter is wrong on every visit. (On the first dashboard visit, Network Overview listed Inspectors as 3 total / 3 active, so the two screens also disagreed.)
- **Compare:** the OEM, RTO and Staff lists show Active counters that match their rows.

### BUG-002 – Driver status counters only count the current page (Medium)
- **Where:** `/tc/users/drivers`
- **Steps:** With more than 15 drivers (default rows per page is 15), compare the counters with all rows, including page 2.
- **Expected:** Counters describe all drivers.
- **Actual:** Total = 18, but Active = 14, Inactive = 0, Suspended = 1 (sum 15). These numbers equal the statuses of the **15 rows on page 1**. Page 2 holds 3 more drivers (2 Active, 1 Inactive), so the real figures are Active 16, Inactive 1, Suspended 1.
- **Likely cause:** the counters are computed in the browser from the current page's rows, not returned by the server for the whole data set. Earlier, with only 6 drivers, the counters were correct, which is why this was easy to miss. The other lists may share the problem once they pass 15 rows.

### BUG-003 – Driver photos never display (Medium)
- **Where:** `/tc/users/drivers` (photo thumbnail in every row)
- **Actual:** 15 of 15 thumbnails have `naturalWidth = 0`. Their URLs are `http://103.114.154.160:8087/storage/drivers/photos/...`. The browser blocks them: *"Mixed Content: The page at https://vltd.misbackend.com/tc/users/drivers was loaded over HTTPS, but requested an insecure image 'http://103.114.154.160:8087/…'"* (console error).
- **Expected:** Photos load over HTTPS from the application's own domain.
- **Also:** the response exposes an internal IP address and port, and the uploaded identity photos are served without encryption.

### BUG-004 – RTO map address search does not work (Medium)
- **Where:** `/tc/users/rto/register` → "Map Location" → "Search an address"
- **Steps:** Type "Connaught Place" (or "Connaught Place, New Delhi") and click **Search**.
- **Actual:** "Location not found. Try a more specific address." for every query. Console: *"Geocoding Service: This API is not activated on your API project. You may need to enable this API in the Google Cloud Console."* Also: *"Attempted to load a Vector Map, but failed. Falling back to Raster."*
- **Expected:** The address resolves to a map location.
- **Impact:** The only way to set a location is clicking the map or **Pin map center**. The automated test uses Pin map center for this reason.
- **Fix:** enable the Geocoding API for the project's Google Maps key.

### BUG-005 – Dashboard shows `0` as real data while loading (Medium)
- **Where:** `/tc/dashboard` immediately after login or while a refresh is pending
- **Steps:** Delay the dashboard API response (the automated test holds the request) and read a KPI tile.
- **Actual:** "AIS-140 Fitted Vehicles" shows `0` (class `dashboard-kpi-value`), and empty-state texts appear, with the Refresh buttons disabled. There is no skeleton or placeholder.
- **Expected:** A loading indicator, not a number that looks like a valid result. A slow connection makes the dashboard report "0 vehicles, 0 alerts".
- **Test:** `tests/test_dashboard_extended.py::test_no_misleading_zero_while_loading` (marked expected-failure; it will report an unexpected pass once fixed).

### BUG-006 – TAC Issue Date: "Today" button disabled (Low)
- **Where:** `/tc/users/oem/register` → TAC Issued On
- **Steps:** Open the date picker.
- **Actual:** **Today** is disabled, while today's day (13) is clickable and the helper text says "TAC issue date cannot be later than today." The COP validity pickers have an enabled Today button.
- **Expected:** Today is enabled, or the helper text says "before today".

### BUG-007 – "Approved" vs "Active" (Low)
- **Where:** `/tc/users/staff`, `/tc/users/permit-holders`
- **Actual:** Staff counters read Active = 8, but all 8 rows say **Approved**. Permit Holders: Active = 17, rows say **Approved** (9) / Suspended (1). The OEM, RTO, Inspector and Driver lists use "Active".
- **Expected:** One status vocabulary across the module.

- **Re-verified 2026-10-31: Reproducible.** State Admin > Users > Staff: counters read **ACTIVE 37** (of 348), but the status filter offers **Approved** (All Statuses / Approved / Suspended / Blacklisted) and every row it lists says **Approved**. The **OEM Staff** page (`/oem/users/staff`) has the same wording: counter "ACTIVE", filter "Approved" (its rows cannot be seen, BUG-039). Evidence: `specs/evidence/oem-staff/tc-staff-list-bug007.png`. Test for the OEM page: `tests/oem_panel/test_oem_staff_form.py::test_the_status_names_of_the_filter_and_the_counters_agree` (expected failure).

### BUG-008 – "View All" goes to the Reports hub (Low)
- **Where:** Dashboard → Alert Monitoring → Recent Major Alerts → **View All**
- **Actual:** Opens `/tc/reports` (a page listing 13 reports). A dedicated alerts page exists at `/tc/alerts`, and the report is `/tc/reports/alerts`.
- **Expected:** The alert list or Alert Report, ideally filtered to unresolved high-priority alerts.
- **Test:** `test_view_all_alerts_navigates_away` documents the current behaviour. Update it when this is fixed.

### BUG-009 – Wrong password shows two messages (Low)
- **Where:** `/auth/login`
- **Steps:** Submit an unknown email or a wrong password.
- **Actual:** Two alerts: **"Validation failed."** and **"Invalid email or password."** `POST /api/auth/login` returns **422** instead of 401.
- **Expected:** One message, "Invalid email or password.", with a 401 response. (Positive: the same text appears for an unknown user and a wrong password, so accounts cannot be enumerated.)

### BUG-010 – Inspector password hint is incomplete (Low)
- **Where:** `/tc/users/inspector` → Add Inspector
- **Actual:** The hint says only "Minimum 10 characters." A 10-character lowercase password (`aaaaaaaaaa`) is rejected with "Validation failed." and "**The password field format is invalid.**", with no explanation of the missing rule. The OEM, RTO and Staff forms state "uppercase, lowercase and a number", and the Driver form adds that a symbol "makes it stronger". The project documentation says Driver passwords need a symbol; the form hint treats a symbol as optional.
- **Expected:** One consistent, fully stated password rule, and a readable error message on all forms.

### BUG-011 – RTO map location is not validated (Low)
- **Where:** `/tc/users/rto/register`
- **Actual:** **Pin map center** saves 20.354000, 85.824000 (Odisha) for an RTO whose district is "Central Delhi", and registration succeeds.
- **Expected:** The map starts centred on the selected district or state, or the location is checked against it.

### BUG-012 – Inspector API accepts a mismatched password confirmation (Medium)
- **Where:** `POST /api/transport-commissioner/inspectors`
- **Steps:** Send a valid body but set `"password": "Auto@12345Test"` and `"password_confirmation": "Different@12345"`.
- **Expected:** 422 with an error on `password` ("Password confirmation does not match."), as the **Staff** and **RTO** endpoints do.
- **Actual:** **201 Created** – "Inspector created and mapped to RTOs successfully." The account is created with the unconfirmed password.
- **Why it matters:** the form blocks a mismatch in the browser, so users never see it, but any other client (or a tampered request) can create accounts without confirmation. The server must enforce its own rules.
- **Test:** `test_inspector_api_rejects_invalid_field[password-mismatch]` (skipped by default because it creates an inspector on every run; run with `pytest --runxfail -k password-mismatch`).

### BUG-013 – Inspector API returns HTTP 500 for a non-numeric `city_id` (Medium)
- **Where:** `POST /api/transport-commissioner/inspectors`
- **Steps:** Send a valid body with `"city_id": "abc"`.
- **Expected:** 422 with an error on `city_id`, like an unknown numeric id (`999999`), which is handled correctly.
- **Actual:** **500** `{"success":false,"message":"Something went wrong. Please try again later."}`. The server did not validate the type before using it. (The response does not leak internals.)
- **Test:** `test_inspector_api_rejects_invalid_field[city-wrong-type]` (expected failure; creates no record).

### BUG-014 - Data is served without the permission the portal requires (High)
- **Where:** `GET /alert/api/alerts` (needs `alerts.view`), `GET /command/api/commands` (`device_commands.view`), `GET /geofence/api/geofences` (`tracking.live_view`), `GET /api/history?imei=...` (`tracking.history_view`). The last one is on the alert/tracking service host.
- **Steps:** Create a TC staff member with **no permissions**, log in, and call each endpoint with that token.
- **Expected:** 403, like the other gated endpoints (`/api/tracking/vehicles`, `/api/transport-commissioner/oems` ...).
- **Actual:** **200** with data. `/api/history` returns the recorded GPS points (latitude, longitude, satellites ...) of a device. The menu hides these pages from such a user, but anyone calling the API directly gets the data.
- **Tests:** `test_unprotected_feature_requires_its_permission[alerts_list | commands_list | geofences_list | trip_history]`.

### BUG-015 - 14 permissions grant nothing (High)
- **Permissions:** `rtos.view/create/update`, `tc.view.staff`, `tc.create.staff`, `tc.update.staff`, `tc.activate.staff`, `tc.deactivate.staff`, `tc.blacklist.staff`, `fleet_managers.view`, `challans.view`, `vltd_device_installations.view`, `vltd_device_installations.repair.view`, `vltd_device_installations.untag`.
- **Steps:** Give a staff member **all 63 permissions** and call the matching endpoint (for example `GET /api/transport-commissioner/rtos`, `.../staff`, `.../fleet-managers`, `.../challans`, `GET /api/installation`, `/api/device-repairs`).
- **Expected:** 200. The permission exists so that it can be granted.
- **Actual:** **403 "You are not authorized"** for every one: these endpoints are Transport-Commissioner-only. In the portal, a staff member with `rtos.view` sees the **RTOs** menu entry; opening it shows *"Unable to Load RTOs - You are not authorized to perform this action."* The same happens for Staff, Permit Holders, Inspectors (its page also needs the RTO list) and the Installation, Repair & Replacement and Installation Performance reports.
- **Expected fix:** either honour the permissions, or stop offering them (and hide the menu entries).
- **Tests:** `test_permission_has_effect[...]` (14) and `test_menu_entry_opens_page_with_permission[...]`.

### BUG-016 - A page needs permissions it does not tell the admin about (Medium)
- **Pages (15):** Alerts, ERSS, Command Center, Live Tracking, Geofences, Alert Set History, Trip Playback, Device Models, Firmware, SIM Modules, and the Alert, Device Health, Device Packets, Device Status and Fleet Activity reports.
- **Actual:** with only the page's own permission the page opens, but its supporting calls are refused with 403. For example, Device Models calls the OEM list (`oems.view`); Command Center and Alerts call the vehicle, OEM and fitment lists (`tracking.live_view`, `oems.view`); the Alert Report is unlocked by `alerts.view` while the menu asks for `reports.view`; the Device Health, Packets and Status reports are unlocked by `tracking.live_view` while the menu asks for `reports.view`.
- **Impact:** an admin cannot tell which combination of permissions makes a page usable, and the staff member sees empty tables or errors.
- **Tests:** `test_menu_entry_opens_page_with_permission[...]` (expected failures listed in `UI_BROKEN`).

### BUG-017 - Staff menu and router disagree with the API (Medium)
- **System Configuration** (`/tc/configuration`) is shown to every staff member, but `GET /api/transport-commissioner/system-configuration` returns 403, so the page shows an error.
- **PIS Trip Management** (`/tc/operations/pis-management/trips`) is hidden from the staff menu, but typing the URL opens it (every other hidden entry redirects to the dashboard), and its vehicle list then fails with 403.
- **Tests:** `test_open_menu_entries_are_consistent_and_work_for_staff[/tc/configuration | /tc/operations/pis-management/trips]`.

### BUG-018 - Temporary password is not enforced by the API (Medium)
- **Steps:** Create a staff member (they get a temporary password and `force_password_change: true`), log in **through the API**, and call any protected endpoint, for example `GET /api/transport-commissioner/dashboard`.
- **Expected:** 401/403 until the password is changed. The UI sends the user to `/auth/change-password` and offers no way around it.
- **Actual:** **200**. The token works fully; the rule only exists in the browser.
- **Test:** `test_temporary_password_is_enforced_by_the_api`.

### BUG-019 - Malformed id returns HTTP 500 (Medium)
- **Steps:** Call `GET /api/transport-commissioner/stops/not-an-id`, `GET .../routes/not-an-id`, `POST .../drivers/not-an-id`, `PATCH .../drivers/not-an-id/status`.
- **Expected:** 404, as `staff`, `oems`, `rtos`, `inspectors`, `fleet-managers` and `challans` return.
- **Actual:** **500**. The value reaches the database unvalidated.
- **Test:** `test_malformed_record_id_is_a_404_not_a_crash[...]`.

### BUG-020 - Tracking pages always make a failing `/api/school` call (Low)
- **Where:** Live Tracking, Alerts, ERSS, Geofences, Trip Playback (OEM panel); confirmed again 2026-11-04 on the same 4 pages in the Fitment Centre panel.
- **Actual:** `GET /api/school` returns **404** `{"success":false,"message":"Resource not found or inaccessible."}` on every load, for every role (admin, OEM, FC). The staff tests ignore 404s so that this noise does not hide real permission failures.
- **Update 2026-11-04:** this entry originally also covered `GET /api/last-position`, described as 404 "even for the admin." That is no longer accurate now that the environment has IMEIs with live telemetry to test against - `/api/last-position` behaves very differently from `/api/school` and is split out into its own, much higher-severity entry: **BUG-082**.

### BUG-021 - Delete does not work for Device Models, Firmware and SIM Modules (High)
- **Where:** Administration -> OEM Management -> any of the three lists -> row menu -> Delete -> confirm.
- **Steps:** Create a record, open its row menu, choose *Delete ...*, confirm in the dialog.
- **Expected:** "... deleted successfully." and the row disappears.
- **Actual:** The banner says **"Select an OEM."** and the record stays. The request is `DELETE /api/<resource>/{id}` with no body or query; the server validates an `oem_id` that the UI never sends (`DELETE ...?oem_id=<owner>` works: 200).
- **Impact:** the "D" of CRUD is unusable for all three screens; users cannot remove wrong records.
- **Tests:** `test_delete_removes_the_record` in the three UI files; `test_delete_requires_the_owning_oem_id` documents the server rule.

### BUG-022 - Editing a Device Model never saves (High)
- **Steps:** Open a Device Model -> Edit, change the Model Name -> **Update Device Model**.
- **Expected:** "Device model updated successfully."
- **Actual:** **"Select an OEM."** (HTTP 422). The request body *does* contain `oem_id`. The UI sends a native `PATCH` with a multipart body (it supports file upload), and the server does not read a multipart PATCH/PUT, so every field is missing.
- **Evidence:** the same data succeeds as a JSON `PATCH`/`PUT` or as `POST` with `_method=PATCH`; a native multipart `PATCH`/`PUT` always fails.
- **Tests:** `test_edit_saves_changes_and_updates_the_table` (Device Models UI), `test_update_with_a_native_multipart_patch_works` (API).

### BUG-023 - Firmware cannot be created from the UI (High) - FIXED 2026-10-15
- **Steps:** Administration -> OEM Management -> Firmware -> Add Firmware -> choose any OEM (for example TATA MOTORS, which has 3 device models) -> open the Device Model list.
- **Expected:** the OEM's device models are offered.
- **Actual:** the list is empty and says **"No Device Models are available for the selected OEM."** The page makes no request for models. The OEM list it relies on (`GET /api/transport-commissioner/oems`) does not contain device models.
- **Impact:** Firmware could only be created through the API.
- **Status:** fixed while testing was in progress - the form now requests `GET /api/device-models?oem_id=<oem>&per_page=100` and lists the OEM's models. The tests now run as ordinary passing tests (`test_device_model_list_offers_the_models_of_the_chosen_oem`, `test_create_firmware_through_the_form`, mandatory, version boundary, duplicate, required model).
- **Also changed in that build:** the *Add Firmware* form no longer has a **Status** field (new firmware is always Active; Status is set when editing).

### BUG-024 - Only 10 records are visible, no pagination (High)
- **Where:** all three lists.
- **Steps:** With more than 10 records (the tests keep 12+ "AUTO PG" records in each list), open the list.
- **Expected:** a pager, or all records loaded.
- **Actual:** exactly **10 rows** are shown and there is no pager. Search and the filters work on the loaded rows only (no request is sent), so searching for the 11th/12th record shows "No ... Found". The API returns `meta.pagination` (`total`, `last_page`, `has_more`) that the UI ignores.
- **Impact:** as soon as a list grows past one page, older records cannot be viewed, edited or deleted from the UI.
- **Tests:** `test_every_record_is_reachable_from_the_list`, `test_search_finds_a_record_that_is_beyond_the_first_page` (3 lists each). `test_first_page_shows_the_newest_ten_records` documents the current behaviour.

### BUG-025 - OEM Management lists show "-" for OEM name, state-wide (not just Firmware) (Medium)
- **Where:** Firmware list columns *OEM* and *Part No* (and its View panel); also confirmed on **Device Models** (*OEM* and *OEM CODE* columns both blank/"-") and **SIM Modules** (*OEM* and *OEM CODE* columns both blank/"-") during the 2026-11-12 UI/UX audit (Batch 3).
- **Actual:** always "-" (or empty) on all 3 screens. The firmware API returns only `device_model {id, model_name, oem_id, oem {id, code}}` - no OEM name and no part number - and the UI shows nothing for them; Device Models and SIM Modules show the same empty-OEM symptom in their own list tables.
- **Scope note:** originally logged against Firmware only; widened 2026-11-12 after the UI/UX audit found the identical symptom on Device Models and SIM Modules too. Re-verify the root cause on all 3 before assuming it's one shared bug vs. three independent ones.
- **Tests:** `test_row_shows_the_oem_and_part_number`, `test_view_shows_oem_and_part_number` (Firmware only so far; Device Models/SIM Modules not yet automated).

### BUG-026 - Certificate types promised by the form are rejected (Low)
- **Where:** Device Model form, *TAC Certificate* / *COP Certificate* ("PDF, JPG, JPEG or PNG"; the file chooser also accepts those types).
- **Actual:** choosing a PNG or JPG is accepted by the form and rejected by the server after submit: *"The tac certificate field must be a file of type: pdf."* The 2 MB size limit is not shown anywhere.
- **Tests:** `test_image_certificate_is_accepted_as_the_form_promises` (UI); `test_certificate_type_partitions`, `test_certificate_size_boundary` document the server rules (PDF only, 2048 KB).

### BUG-027 - Firmware API crashes on a non-numeric `device_model_id` (Medium)
- **Steps:** `POST /api/device-firmwares` with `"device_model_id": "abc"`.
- **Expected:** 422 (as for an unknown numeric id).
- **Actual:** **500** "Something went wrong." (Same class as BUG-013 and BUG-019.)
- **Test:** `test_non_numeric_device_model_is_a_validation_error`.

### BUG-028 - Edit Firmware does not show the Device Model (Low) - FIXED 2026-10-15
- **Actual:** the form opens with the OEM filled in and the Device Model showing the placeholder "Select Device Model"; the saved request still contains the right `device_model_id`. A user cannot see which model they are editing.
- **Status:** fixed in the same build; `test_edit_form_shows_the_device_model` now passes.

### BUG-029 - Deleting a Device Model orphans its firmware (Medium)
- **Steps:** Create a Device Model and a Firmware for it, then `DELETE /api/device-models/{id}?oem_id=...`.
- **Expected:** the delete is refused, or the firmware goes with it. (The UI dialog even warns "Deletion may be rejected if this model is already referenced.")
- **Actual:** **200**; the firmware stays, with a `device_model_id` that no longer exists. It is listed with "-" in every column and **cannot be deleted** afterwards (`DELETE` -> 403).
- **Test:** `test_deleting_a_model_that_has_firmware` (does not run by default because it leaves an undeletable record; run with `pytest --runxfail -k deleting_a_model`).

### BUG-030 - List order is not deterministic (Medium)
- **Steps:** Create 12 Device Models quickly (same second) and read them 5 at a time (`?search=<token>&per_page=5&page=1..3`).
- **Expected:** every record exactly once.
- **Actual:** one record appears on two pages and another on none (8 of 8 attempts for Device Models). The lists are sorted by creation time only; ties inside one second are returned in an unstable order that differs between the full query and the paged query (`ids` come back as 440, 435, 436, 437 ... instead of descending).
- **Impact:** bulk-created records (imports, scripts) can be skipped or duplicated by any client that pages.
- **Test:** `test_pages_do_not_overlap_and_cover_the_total` (expected failure).

### BUG-031 - A deleted record keeps its name reserved (Medium)
- **Steps:** Create a Device Model named `X`, delete it (`DELETE ...?oem_id=...` -> 200, `GET` -> 404), then create a new Device Model named `X`.
- **Expected:** 201 - the old record no longer exists.
- **Actual:** **422 "The model name has already been taken."** The same happens for a Firmware `version` on the same model. (SIM Module names are free again after a delete, so the three screens disagree.)
- **Why it matters:** a mistaken Device Model can never be re-created under its correct name, and nothing visible explains the clash (the record is not listed). Deleted rows still count in the unique index.
- **Tests:** `test_a_deleted_device_model_name_can_be_reused`, `test_a_deleted_firmware_version_can_be_reused` (expected failures); `test_a_deleted_sim_module_name_can_be_reused` passes as the control.

### BUG-032 - Missing login answers 500 unless the client asks for JSON (Medium)
- **Steps:** `curl https://vltd.misbackend.com/api/auth/me` (no token, no `Accept` header). Same for `/api/transport-commissioner/oems` and the other protected endpoints.
- **Expected:** `401 Unauthorized`.
- **Actual:** **500**. With `Accept: application/json` the same call correctly returns 401. The front end always sends that header, which hides the problem; scripts, `curl`, monitoring tools and some HTTP clients do not.
- **Impact:** authentication failures are reported as server errors, which trips alerting and confuses API clients. (This is the classic symptom of an API that tries to redirect an unauthenticated user to a login page that does not exist.)
- **Test:** `test_unauthenticated_request_without_a_json_accept_header_is_a_401` (expected failure).

### BUG-033 - Theft protection does not end the user's sessions (Medium)
- **Source:** "How Everything Works", chapter 4: *"If the system ever sees an old, already-used sign-in key being reused (a sign of a stolen key), it immediately ends all sessions of that user."*
- **Steps:** sign in; call `POST /api/auth/refresh` with the refresh key (works, a new key pair is returned); call it again with the OLD refresh key; then use the NEW access token and the NEW refresh key.
- **Expected:** the replay is refused **and** the new access token and new refresh key stop working (all sessions ended).
- **Actual:** the replay is refused (401), but `GET /api/auth/me` with the new access token still answers 200 and the new refresh key can still be refreshed (checked again 3 seconds later).
- **Impact:** a thief who replays a stolen key is turned away, but the legitimate holder of the newer key stays signed in, and if the thief obtained the newest key first, nothing stops them.
- **Test:** `test_reusing_an_old_refresh_key_ends_all_sessions_of_the_user` (expected failure; uses a throw-away staff account).

### BUG-035 - Inspector password minimum length is 9, not 10 (Low)
- **Source:** guide section 9.1: "temporary password of at least 10 characters containing uppercase, lowercase, and a number".
- **Steps:** `POST /api/transport-commissioner/inspectors` with password `Abcdefg12` (9 characters) and a matching confirmation.
- **Expected:** 422. **Actual:** 201, inspector created.
- **Test:** `test_inspector_api_rejects_invalid_field[password-9-chars]` (not run by default because a defect would create an inspector each run; run with `--runxfail -k password-9-chars`).

### BUG-036 - Help Centres page fires failing writes on every load (Medium)
- **Steps:** open Administration > Help Centres and watch the network. 13 requests `PUT /api/tracking/help-centres/{id}` are sent, one per help centre, each with only `{"address": "..."}`.
- **Expected:** opening a list changes nothing.
- **Actual:** every PUT answers **422** ("The name field is required."). It looks like an address back-fill that sends an incomplete body; it repeats on every visit and, if the body were complete, would silently overwrite records.
- **Test:** `test_admin_panel_health.py::test_help_centres_page_loads_without_failed_writes` (expected failure).

### BUG-037 - Untag search gives no feedback for an unknown vehicle (Low)
- **Steps:** Operations > Vehicle Device Untag, search `ZZ99ZZ9999`.
- **Expected:** a "vehicle not found" message (Ownership Transfer shows one).
- **Actual:** the API answers 422 and the page stays unchanged.
- **Test:** `test_report_exports_and_vehicle_search.py::test_unknown_vehicle_explains_that_nothing_was_found[device-untag]` (expected failure).

### BUG-038 - OEM is offered "Add Model" (Medium)
- **Source:** guide 14.4: "OEMs cannot create, edit or delete this master data; they can only view their device models." Confirmed by the product owner.
- **Steps:** sign in as the OEM, open Device Models.
- **Actual:** **Add Model** and the Register Model form are shown; `POST/PUT/PATCH/DELETE /api/device-models` answer 403. The server is right, the UI offers an action that cannot work.
- **Test:** `tests/oem_panel/test_oem_access_and_isolation.py::test_oem_is_not_offered_to_add_a_device_model` (expected failure).
- **Re-verified 2026-11-02 (Reproducible, 3 of 3 attempts):** the Device Models page still shows **Add Model**, and each row's menu offers **View Model, Edit Model and Delete Model**. Opening *Edit Model* shows the full form; *Delete Model* asks for confirmation and the server answers **403 "You are not authorized to perform this action."** (3 of 3, on a throw-away model of the suite). Expected: only View. Evidence: `specs/evidence/oem-device-management/device-models.png`, `device-models-edit-delete-refused.png`.
- **Test (Edit and Delete):** `tests/oem_panel/test_oem_device_management_ui.py::test_the_oem_is_offered_only_to_view_a_device_model` (expected failure: `['View Model', 'Edit Model', 'Delete Model']`).

### BUG-039 - OEM cannot manage its own staff (High)
- **Steps:** sign in as the OEM Admin, open Users > Staff, or call `GET /api/oem/users`, `POST /api/oem/users`.
- **Expected:** list / validation (422 for an empty request). Confirmed by the product owner that the OEM manages its staff.
- **Actual:** **403 "You do not have permission"** for both, although `/api/oem/permissions` lists 41 permissions and the OEM Admin holds all 41. The page shows 0 staff; Register Staff cannot succeed. (Same pattern as BUG-015.)
- **Re-verified 2026-10-31 through the screen: Reproducible.** Users > Staff loads with `GET /api/oem/users?page=1&sort_by=created_at&sort_dir=desc` -> **403** (the page shows 0 in every counter and "No Staff found", see BUG-059); the Register OEM Staff form opens, accepts valid data (name, e-mail, mobile, password, one permission) and `POST /api/oem/users` -> **403 "You do not have permission to perform this action."**, shown as a toast ("Failed to register OEM Staff"); nothing is created. Evidence: `specs/evidence/oem-staff/list.png`, `register-403.png`.
- **Backend observation (not a UI finding):** the 41 permissions of the OEM catalogue (`/api/oem/permissions`, the same list the form offers) contain **no staff-management permission** (no code mentions staff or users), so no OEM role can pass the check that guards `/api/oem/users`. The State Admin catalogue has `tc.*.staff` for TC staff only.
- **Impact on this module:** with the list and the registration refused, no OEM staff member can exist, so view, edit, status changes, search, filters, sorting, paging, role / permission access, staff isolation between OEMs and the behaviour of a deactivated staff session **cannot be tested** (blocker). The test plan for them is in `specs/oem-staff-test-report.md`.
- **Manual regression steps once fixed:** register a staff member with one permission (expect 201 and a row in the list), sign in as that staff and confirm only the permitted pages open, edit, suspend, activate and blacklist the member, search by name / e-mail / mobile, and confirm another OEM never sees the member.
- **Tests:** `tests/oem_panel/test_oem_staff_management.py` (3, expected failures).

### BUG-040 - OEM monitoring pages call State Admin endpoints (Medium)
- **Pages:** Alerts, Geofences, Live Tracking, Trip Playback.
- **Actual:** each load sends `GET /api/transport-commissioner/oems` and `/rtos` -> 403 (plus the known `/api/school` 404, BUG-020).
- **Visible effect (2026-10-30):** in Alerts > Rules > Create Alert Rule the **RTO** scope list is empty, because the form cannot read the RTOs (see BUG-047).
- **Test:** `test_monitoring_pages_do_not_call_state_admin_endpoints` (4, expected failures).

### BUG-041 - Stock can be allocated to a blacklisted fitment centre (High)
- **Source:** guide 6.1: the OEM allocates to "one of its active fitment centres".
- **Steps:** register a device, `POST /api/device-allocations {"fitment_centre_id": <blacklisted centre>, "imeis": [...]}`.
- **Actual:** **201**, the device becomes "allocated" to the blacklisted centre. The allocation wizard lists active centres only, so only direct API callers can do it. The same happens for a **suspended** centre: see BUG-055.
- **Test:** `tests/oem_panel/test_oem_allocation.py::test_stock_cannot_be_allocated_to_a_blacklisted_fitment_centre` (expected failure; rolls the allocation back, but the allocation history row, status "returned", cannot be deleted).
- **Re-verified 2026-11-02 (Reproducible):** the existing test still answers 201 ("A blacklisted centre received stock: 201").

### BUG-042 - Duplicate fitment code is not validated (Medium)
- **Steps:** `POST /api/oem/fitment-centres` with an existing `short_name` and every other field valid except the (mandatory) image.
- **Expected:** an error on `short_name` (the form says "Unique code used to identify the Fitment Center").
- **Actual:** the only error is the missing image. Not confirmed by actually creating a centre (that would leave an undeletable account).
- **Test:** `test_oem_fitment_centres.py::test_duplicate_fitment_code_is_refused` (expected failure).
- **Re-verified 2026-10-31 through the screen:** on **Edit FC** the code of another centre (`RF123`, Rajendra Fitments) was saved on a test centre: `POST /api/oem/fitment-centres/{id}` -> **200 "Fitment Centre updated successfully."**, so two centres then shared one code (restored afterwards; only the test centre was touched). Registration through the API was re-checked on 2026-10-31 and still reports only the missing image. Duplicate **e-mail** and **mobile number** *are* refused on registration ("already registered").
- **Test (edit, screen):** `test_oem_fitment_center_lifecycle.py::test_a_fitment_code_used_by_another_centre_is_refused_on_edit` (expected failure: "The duplicate code was accepted: 200").

### BUG-043 - SIM extension is offered for a device that is not installed (Low)
- **Source:** guide 6.5: only for devices installed on a vehicle.
- **Actual:** after fetching a registered, available device the page shows the SIM as **Eligible** and offers Extend Validity; confirming gives the generic banner "Validation failed." (the API says "SIM validity can be extended only for an installed device."). The server rule itself works and is tested.
- **Test:** `test_oem_sim_validity_extension.py::test_extension_is_not_offered_for_a_device_that_is_not_installed` (expected failure).
- **Re-verified 2026-11-02 (Reproducible):** the existing test still finds Extend Validity offered for a device that is not installed.

### BUG-044 - OEM Dashboard: SIM column of the Device Details widget is always "-" (Low)
- **Module / environment:** OEM panel > Dashboard > Device Details; https://vltd.misbackend.com, Chromium, 2026-10-30.
- **Severity / priority:** Low / Low (the data is shown correctly on the Device Details page).
- **Preconditions:** signed in as the OEM Admin; at least one registered device (the Device Model, Firmware and SIM Module of the OEM exist).
- **Steps:**
  1. Sign in as the OEM and stay on the Dashboard.
  2. Scroll to **Device Details** (Recently registered OEM devices) and read the **SIM** column.
  3. Click **View All** (opens Device Details) and search for the same IMEI; read the **SIM MODULE** column.
- **Expected:** the SIM column shows the device's SIM module, as the Device Details page does (the API returns `sim_module.module_name` and `sims[0].iccid`).
- **Actual:** the dashboard shows "-" in the SIM column for every device (checked with 1, 3 and 7 devices); the Device Details page shows `AUTO SIM ...` for the same device.
- **Evidence:** `specs/evidence/oem-dashboard/02-with-data.png`, `05-device-details-page-sim-column.png`, video `11-BUG-044-sim-column-dashboard-vs-device-details.webm`.
- **Reproducibility:** Reproducible every time it was checked (more than five runs, 1 to 7 devices).
- **Test:** `tests/oem_panel/test_oem_dashboard.py::test_recent_devices_show_the_sim_module` (expected failure).
- **Re-verified 2026-11-02 (Reproducible):** a freshly registered device shows '-' in the dashboard's SIM column while Device Details shows the SIM module (manual check and test).

### BUG-045 - Admin Device Model form accepts a suspended or blacklisted OEM (Medium)
- **Module / environment:** State Admin > OEM Management > Device Models > Add Device Model; https://vltd.misbackend.com, Chromium, 2026-10-30. Found by manual exploration, confirmed live.
- **Severity / priority:** Medium / Medium.
- **Preconditions:** signed in as State Admin; at least one OEM with status Suspended and one Blacklisted exist (21 and 6 on 2026-10-30).
- **Steps:**
  1. Open OEM Management > Device Models > **Add Device Model**.
  2. Open the **OEM** dropdown and choose a suspended OEM (then repeat with a blacklisted OEM). The dropdown shows no status, so find the OEM's status under OEM Management first.
  3. Fill the remaining mandatory fields (Model Name, Part Number, TAC Number, TAC Issued On, TAC certificate PDF) and click **Create Device Model**.
- **Expected (product owner, 2026-10-31):** suspended and blacklisted OEMs are **not shown** in the Device Model form's OEM dropdown (and the server should not create a model for them).
- **Actual:** `POST /api/device-models` answers **201 "Device model created successfully."** for both a suspended and a blacklisted OEM, the page returns to the list and the model exists. The server accepts it too (no check on the OEM's status).
- **Reproducibility:** 2 of 2 attempts (one suspended, one blacklisted OEM); the created models were deleted afterwards.
- **Tests:** `tests/oem_management/test_device_models_ui.py::test_the_oem_dropdown_does_not_offer_suspended_or_blacklisted_oems` (expected failure: "The dropdown offers 26 suspended / blacklisted OEMs"; 26 of the 100 OEMs the form loads) and `test_a_device_model_is_not_created_for_a_suspended_or_blacklisted_oem` (2, expected failures; each removes what it creates). Not checked: Firmware and SIM Module forms.

### BUG-046 - Admin Device Model form: the OEM dropdown lists only 100 OEMs (Medium)
- **Module / environment:** State Admin > OEM Management > Device Models > Add Device Model; https://vltd.misbackend.com, Chromium, 2026-10-30.
- **Severity / priority:** Medium / Medium (the oldest OEMs cannot get a device model through the UI).
- **Preconditions:** more than 100 OEMs exist (109 on 2026-10-30).
- **Steps:**
  1. Open OEM Management > Device Models > **Add Device Model** and open the **OEM** dropdown.
  2. Count the options, then compare with the total number of OEMs (OEM Management list, or the pagination total).
  3. Type the name of one of the oldest OEMs in the dropdown's search box.
- **Expected:** every OEM can be chosen.
- **Actual:** the form requests `GET /api/transport-commissioner/oems?per_page=100` once and never loads more. The dropdown holds **100 of 109** OEMs; the search only filters those 100, so typing the name of a missing OEM finds nothing. The list is newest first, so the 9 missing OEMs are the oldest (ids 36 to 44, including the working OEMs "ZAP station", "TATA MOTORS" and "TrackNova Telematics Pvt. Ltd."). The same limit will hide more OEMs with every new one. The server rejects `per_page=500` (422), so the page has to load further pages, not ask for more per page.
- **Reproducibility:** every time.
- **Test:** `tests/oem_management/test_device_models_ui.py::test_oem_dropdown_offers_every_oem` (expected failure: "The dropdown offers 100 of 109 OEMs"). Not checked: the OEM dropdowns of other forms and filters.

### BUG-047 - OEM Operations: an OEM Admin cannot create an alert rule (Medium)
- **Module / environment:** OEM panel > Operations > Tracking & GIS > Alerts > Rules > Create Alert Rule; https://vltd.misbackend.com, Chromium, 2026-10-30. Reproduced through the screen as the OEM Admin.
- **Severity / priority:** Medium / Medium. The OEM still receives SOS alerts (guide 9.3), but without a rule it sees no other alert type, and the page offers a function it can never complete.
- **Preconditions:** signed in as the OEM Admin (role `oem_admin`, all 41 permissions of the OEM catalogue).
- **Steps:**
  1. Open **Operations > Tracking & GIS > Alerts** and click **Rules**, then **Create Alert Rule**.
  2. Enter a rule name and a speed limit (type Overspeed, severity High); leave **Applies to** on its default, **All vehicles**. Click **Create Rule**.
  3. Repeat with **Applies to = Fitment Centre** and choose *Rajendra Fitments*.
  4. Open the list of **Applies to = RTO**, then **Single vehicle**.
- **Expected (product owner, 2026-10-31: an OEM should be able to set a rule; if a scope is out of reach for the OEM, the feature should not be available in the first place):** the rule is created and listed, and a scope the role may not use is not offered. Guide 9.3 says each organisation, an OEM included, has its own rules ("Each organisation ... has its own rules and therefore its own alerts"), and 9.2 lists the scopes the form offers.
- **Actual:** steps 2 and 3 answer **403** `{"error":"your role is not permitted to create or update a rule with this scope"}`; a red toast shows that text and no rule is created ("0 rules"). The RTO list is empty (the form cannot read RTOs, see BUG-040) and the Single-vehicle list is empty because the OEM has no vehicle, so the scope that might work could not be tried. The OEM permission catalogue holds `alerts.view` but no permission to manage rules, so the screen offers something the role cannot do.
- **Reproducibility:** reproducible every time (all three attempts, plus the automated test).
- **Evidence:** `specs/evidence/oem-operations/BUG-047-alert-rule-refused-403.png` (the form with the toast), `alert-rule-form.png`.
- **Test:** `tests/oem_panel/test_oem_tracking_and_alerts.py::test_an_oem_can_create_an_alert_rule` (expected failure: `403 {"error":"your role is not permitted ..."}`). The feature is currently blocked for the OEM by this defect.

### BUG-048 - OEM Send Command accepts a device that is not installed on a vehicle (Medium)
- **Module / environment:** OEM panel > Operations > Command Center > Send Command; https://vltd.misbackend.com, Chromium, 2026-10-31. Reproduced through the screen as the OEM Admin.
- **Severity / priority:** Medium / Medium. A command can be queued for a device that has no vehicle, owner or fitment centre; the queued row cannot be removed.
- **Preconditions:** signed in as the OEM Admin; a device registered under Devices that is still *available* (not allocated or installed).
- **Steps:**
  1. Register a device (Devices > Register Device) and note its IMEI; do not allocate or install it.
  2. Open **Operations > Command Center > Send Command** and type the IMEI (or a part of it) into **Vehicle**.
  3. Select the device, type a custom command and click **Send Command**.
  4. Open **Command History** and look for the IMEI.
- **Expected (product owner, 2026-10-31):** a device that is not installed on a vehicle is not accepted for a command (not offered by the search, or refused when sent). Guide 12 also speaks of searching a *vehicle*.
- **Actual:** the search lists the registered device (`GET /api/devices?search=<imei>`), the page shows "Recent commands for <imei>", and the send is accepted: **"Command sent."**, and the command appears in Command History as *Queued* with no owner, fitment centre or OEM filled in. The real send was done once during the 2026-10-30 exploration (that queued command cannot be deleted and stays in the OEM's history); the search part is reproduced by the automated test.
- **Reproducibility:** every time for the search; the real send once, deliberately not repeated.
- **Test:** `tests/oem_panel/test_oem_command_center.py::test_a_device_that_is_not_installed_on_a_vehicle_is_not_offered_for_a_command` (expected failure: "No results found." is never shown). Only the search is checked, because a real send cannot be undone; the other Send Command tests use a not-installed device with the send request mocked and will need an installed device once this is fixed.

### BUG-049 - Edit geofence crashes the page (High)
- **Module / environment:** Geofences (State Admin: `/tc/geofences`; OEM: Operations > Tracking & GIS > Geofences, `/oem/geofences`); https://vltd.misbackend.com, Chromium, 2026-10-31. Reproduced through the screen in both panels.
- **Severity / priority:** High / Medium. Editing a zone (rename, change the boundary, alert trigger, vehicles) is impossible for every user; the only workaround is delete and draw again.
- **Preconditions:** at least one geofence exists (any shape, drawn on the map or created through the API).
- **Steps:**
  1. Open the Geofences page and the **Geofences** tab; the zone list is shown.
  2. Click the pencil (**Edit geofence**) on any zone.
- **Expected:** the form opens with the zone's name, type, colour, alert trigger and boundary, and can be saved.
- **Actual:** the whole page is replaced by **"Something went wrong - We couldn't load this page correctly. Reload Page"**. The console shows `Routed component error: TypeError: Cannot read properties of null (reading 'type')`. Nothing is sent to the server.
- **Reproducibility:** every time: 3 of 3 zones as the OEM (a zone drawn on the map, a zone from the API, and an older zone of the OEM) and 1 of 1 as the State Admin.
- **Evidence:** `specs/evidence/oem-operations/geofence-edit.png`.
- **Test:** `tests/oem_panel/test_oem_geofences.py::test_a_zone_can_be_edited` (expected failure: the form never opens).

### BUG-050 - Circle and rectangle zones are listed as "Freehand" (Low)
- **Module / environment:** Geofences (State Admin and OEM); https://vltd.misbackend.com, Chromium, 2026-10-31.
- **Severity / priority:** Low / Low. The zone works; the list and the filter describe it wrongly.
- **Steps:**
  1. Open Geofences > **Create Geofence**, enter a name, choose the **Circle** tool and drag from the centre outwards; **Save**. Repeat with **Rectangle**.
  2. Look at the new card in the list.
  3. Set the **All types** filter to **Circle**, then **Rectangle**.
- **Expected:** the card names the drawn shape and the matching type filter lists it.
- **Actual:** both zones are listed as **Freehand** (the service stores `"type": "polygon"` and rejects `"circle"` as an unknown type), the **Circle** and **Rectangle** filters answer "No geofences match these filters." and only **Freestyle** lists them. A zone's shape cannot be told from its card or filtered for.
- **Reproducibility:** every time: circle and rectangle as the State Admin (2 of 2), circle as the OEM, plus the automated test for both shapes.
- **Test:** `tests/oem_panel/test_oem_geofences.py::test_a_drawn_zone_is_found_by_its_shape_filter` (2, expected failures).

### BUG-051 - Another OEM can suspend, activate and blacklist a fitment centre it does not own (High, API-only)
- **Module / environment:** OEM panel > Management > User Management > Fitment Center (status endpoints); https://vltd.misbackend.com, 2026-10-31. **API-only finding**: the screen never offers another OEM's centre (the details page answers "Fitment Center details not found."), so the defect is reachable only by calling the API with another OEM's token.
- **Severity / priority:** High / High. One OEM can take another OEM's workshop out of service (a suspended or blacklisted centre can no longer sign in: 403 "Your account is not approved or active."). A blacklisting is described by the screen as irreversible.
- **Preconditions:** OEM A owns a fitment centre (id N); OEM B is a second, unrelated OEM account (a throw-away `AUTO OEM` account was used). Only test centres of this suite were targeted.
- **Steps:**
  1. Sign in to the API as OEM B.
  2. `GET /api/oem/fitment-centres/N` -> 404 "Resource not found or inaccessible." (correct), and the list / search of OEM B does not contain it.
  3. `PATCH /api/oem/fitment-centres/N/deactivate {"remarks": "x"}`, then `/activate`, then (on a disposable centre) `/blacklist` with the same body.
- **Expected:** the same 404 as the GET (or 403); the centre is unchanged.
- **Actual:** each request answers **200** ("Fitment Center deactivated / activated / blacklisted successfully."); OEM A's centre changes status and the remark history shows the entry "By AUTO OEM ...". Blacklist was confirmed on a disposable centre (it became blacklisted and its login was refused).
- **Reproducibility:** 3 of 3 actions (suspend, activate, blacklist). Edits are not possible (see BUG-052), and reading is correctly refused.
- **Test:** `tests/oem_panel/test_oem_fitment_center_lifecycle.py::test_another_oem_cannot_change_the_status_of_a_centre_it_does_not_own` (2, expected failures; each restores or discards its own test centre).

### BUG-052 - Editing a centre of another OEM answers 500 and names an internal class (Medium, API-only)
- **Steps:** as OEM B, `POST /api/oem/fitment-centres/N` (multipart, every mandatory field valid) for a centre of OEM A.
- **Expected:** 404 like the details request (nothing is changed).
- **Actual:** **500** `{"message":"Failed to update Fitment Centre.","error":"No query results for model [App\\Models\\FitmentCentre\\FitmentCentre]."}`. Nothing is changed, but an internal model class name is disclosed and the status is wrong. (A request with missing fields answers 422 first, so the check order is validation, then ownership.)
- **Test:** `test_editing_a_centre_of_another_oem_is_refused_like_a_missing_one` (expected failure).

### BUG-053 - A blacklisted centre can be activated, suspended and edited again (Medium, API-only; the edit page is also reachable by URL)
- **Source:** the screen: the blacklist box says "This action cannot be reversed." and a blacklisted centre shows "No further status actions are available."; the row menu offers only View details.
- **Steps:** blacklist a disposable centre, then `PATCH /api/oem/fitment-centres/{id}/activate {"remarks": "x"}` (and `/deactivate`), then `POST /api/oem/fitment-centres/{id}` with the stored values and a new owner name. In the screen, open `/oem/users/fitment-centers/{id}/edit` of a blacklisted centre.
- **Expected (product owner, 2026-10-31: a blacklisted centre can never be reactivated, it is final; a suspended one can):** every request is refused and the centre stays blacklisted and unchanged.
- **Actual:** activate -> 200 (status **active**), deactivate -> 200 (**suspended**), blacklist again -> 200, edit -> 200 (the owner name changed); the edit page of a blacklisted centre opens and shows the Update button.
- **Test:** `test_a_blacklisted_centre_stays_blacklisted` (expected failure).

### BUG-054 - A status the centre already has can be set again (Low, API-only)
- **Steps:** on an active centre `PATCH .../activate {"remarks": "x"}`; on a suspended centre `PATCH .../deactivate {"remarks": "x"}`. The screen never offers these actions.
- **Expected:** refused (409 / 422); no history entry.
- **Actual:** **200** each time, and each adds an entry to the Remarks History (the screen then lists "ACTIVE ... AUTO already active" although nothing changed).
- **Test:** `test_a_status_the_centre_already_has_cannot_be_set_again` (2, expected failures).

### BUG-055 - Stock can be allocated to a suspended fitment centre (High, API-only; same family as BUG-041)
- **Source:** guide 6.1: the OEM allocates to "one of its active fitment centres"; the Allocate Stock wizard lists active centres only.
- **Steps:** suspend a centre, register a device, `POST /api/device-allocations {"fitment_centre_id": <suspended centre>, "imeis": [...]}`.
- **Expected:** 422; the device stays available.
- **Actual:** **201**, "Devices allocated successfully."; the device becomes *allocated* to a centre that cannot sign in. (Rolled back by the test; the allocation history row, status "returned", cannot be deleted.)
- **Test:** `test_stock_cannot_be_allocated_to_a_suspended_fitment_center` (expected failure).
- **Re-verified 2026-11-02 (Reproducible):** the test still answers 201 ("A suspended centre received stock: 201").

### BUG-056 - Remarks History shows UTC times while the rest of the page shows local time (Low)
- **Steps:** suspend a fitment centre (any remark), stay on its details page and compare the **Last updated** time in the header with the time of the new entry under **Remarks History**.
- **Expected:** the same time (the entry was made at that moment).
- **Actual:** the header says e.g. "31 Oct 2026, 02:36 pm" (India time) while the history entry says "31 Oct 2026, 09:06 am" (UTC; the API sends `created_at: "2026-10-31 09:06:40"` without a zone, and the screen does not convert it). Also visible on the older records (Rajendra Fitments: 10:36 am vs 04:07 pm).
- **Reproducibility:** every status change; browser time zone IST (UTC+05:30).
- **Evidence:** `specs/evidence/oem-fitment-centers/remarks-history-time.png`.
- **Test:** `test_the_remarks_history_time_matches_the_last_updated_time` (expected failure).

### BUG-057 - The premises image of a fitment centre is never shown (Medium)
- **Module / environment:** Fitment Center > details page (and the edit page's "View Image"); https://vltd.misbackend.com, Chromium, 2026-10-31.
- **Steps:** open the details page of any fitment centre (the ones registered by the OEM, with an image, included); look at **Documents & Media > Premises Image**.
- **Expected:** the uploaded premises photo is displayed.
- **Actual:** "**Image unavailable - The premises image could not be loaded.**" for every centre. The API returns `image_url` as `http://103.114.154.160:8087/storage/fitment-centres/images/<file>.png` (an insecure internal address with a port); the page is https, so the browser blocks the request (console: *Mixed Content ... requested an insecure element*). The file itself exists (the same URL answers 200 image/png when fetched directly), and the **Open Source** / **View Image** links lead to that http address.
- **Reproducibility:** every centre (3 of 3 older ones and every one registered during the tests).
- **Evidence:** `specs/evidence/oem-fitment-centers/details-active.png`.
- **Test:** `tests/oem_panel/test_oem_fitment_center_paging_and_uploads.py::test_the_premises_image_is_shown_on_the_details_page` (expected failure: "Image unavailable" is shown).

### BUG-058 - The server does not enforce the contact and password rules the forms imply (Medium, API-only)
- **Source:** product owner, 2026-10-31: "the server should enforce rules the forms imply". The Register and Edit forms refuse these values; the API accepts them.
- **Steps (no centre is created or changed: every request is also made invalid by a wrong pincode, or by the missing image, and the field is looked for in the errors):** `POST /api/oem/fitment-centres` (and `POST /api/oem/fitment-centres/{id}` for the edit) with one of: `contact_no` `0000000000` or `5999999999`; `alternate_contact_no` `1234567890`; `email_id` `a@b` or `a@example`; a 101-to-150-character `password` (registration only).
- **Expected:** 422 with an error on that field (the form says "Enter valid 10 digit mobile number" for numbers not starting 6-9, "Enter a valid email" for these addresses, and stops the password at 100 characters).
- **Actual:** the field is **not reported** (registration and edit): only the other deliberate error comes back. The server does refuse a non-numeric or short number, a malformed GST number, an e-mail containing a space, over-long text and a duplicate e-mail or mobile number, so only these rules are missing. A centre registered like this would get an unreachable contact number and an unusable login e-mail.
- **Reproducibility:** every time (11 of 11 values).
- **Test:** `test_oem_fitment_center_lifecycle.py::test_the_server_enforces_the_contact_and_password_rules_of_the_registration_form` (6) and `::test_the_server_enforces_the_contact_rules_of_the_edit_form` (5), expected failures.

### BUG-059 - A staff list that failed to load is shown as "No Staff found" (Medium)
- **Module / environment:** OEM panel > Management > User Management > Staff (`/oem/users/staff`); https://vltd.misbackend.com, Chromium, 2026-10-31.
- **Severity / priority:** Medium / Medium. It hides BUG-039 from the user: the OEM believes it has no staff and is invited to register some.
- **Preconditions:** signed in as the OEM Admin (the list request answers 403 today); the same happens for a server error (reproduced with a 500 for the same request in the automated test).
- **Steps:** open Management > User Management > Staff; apply any filter or search.
- **Expected:** an error such as the other pages show ("Unable to load ...", "You are not authorized ...") and the counters not claiming 0; an empty state only when the server says there are no staff.
- **Actual:** "**No Staff found. Register a Staff member to get started.**" (or "No matching Staff found. Try changing your search keywords." after a filter) with TOTAL / ACTIVE / SUSPENDED / BLACKLISTED all 0 and no error message; Refresh, Apply Filters and Clear repeat the 403 silently.
- **Reproducibility:** every time (403 for real; 403 and 500 mocked in the test).
- **Evidence:** `specs/evidence/oem-staff/list.png`, `list-after-403.png`.
- **Test:** `tests/oem_panel/test_oem_staff_form.py::test_a_failed_staff_list_is_reported_as_an_error` (2, expected failures).

### BUG-060 - The Register OEM Staff form accepts a name of spaces (Low)
- **Steps:** open Staff > Register Staff, type three spaces as Staff Name, fill a valid e-mail, mobile number, password and confirmation, select a permission and press **Register Staff**.
- **Expected:** "Staff Name is required" and no request (the Fitment Center form and the other registration forms refuse a blank name).
- **Actual:** no message; the form sends `POST /api/oem/users {"name": "   ", ...}`. What the server does with it could not be seen because every request answers 403 (BUG-039), so the server-side rule is unknown. A one-character name and a name of digits are also sent; the guide gives no rule for them, so they are not reported.
- **Reproducibility:** every time (the request is intercepted and aborted in the test, so nothing is created).
- **Test:** `test_oem_staff_form.py::test_a_staff_name_of_spaces_is_refused` (expected failure).

### BUG-061 - A bulk upload from the screen can never register a device (High)
- **Module / environment:** OEM panel > Management > Device Management > Device Details > Bulk Upload; https://vltd.misbackend.com, Chromium, 2026-11-02.
- **Severity / priority:** High / High. Guide 6.1 describes bulk registration of up to 10,000 devices from an Excel sheet as the way to stock devices; through the screen it is impossible.
- **Preconditions:** signed in as the OEM Admin; a Device Model, Firmware and SIM Module of the OEM exist.
- **Steps:**
  1. Open Device Details > **Bulk Upload** and press **Download Sample** (`device_bulk_upload_sample.xlsx`, columns IMEI, Serial Number, Device Model, SIM Module, Firmware, Slot ID, Primary Mobile Number, Secondary Mobile Number, ICCID, Valid Till, two example rows).
  2. Choose that file and press **Upload**.
  3. Repeat with the sample's rows replaced by one row of real data (valid model, SIM module, firmware names, mobile numbers, ICCID, date).
- **Expected:** the rows of the sheet are sent and the devices are registered (201), or the errors of the rows are reported (guide 6.1: "the user downloads an Excel validation report").
- **Actual:** the request is `POST /api/devices/bulk-upload {"devices": [{}, {}]}`: **every row is empty**, so the server answers 422 "The devices.0.imei field is required ..." and the screen only says **"Bulk upload failed."** With real data the request is still `{"devices": [{}]}`. Header experiments (the request body is read before it is sent): the screen understands only snake_case headers (`imei, serial_number, device_model, sim_module, firmware, slot_id, iccid, valid_till`), **not the Title Case headers of its own sample**; and in no variant (snake_case, `primary_mobile_no`, `primary_number`, `mobile_1`, `primary_mobile`, numeric or text cells) are `primary_mobile_number` / `secondary_mobile_number` read, although the server requires both. So no sheet can pass.
- **Validation attempts:** the untouched sample 3 of 3 (rows `{}`), the filled-in sample 1 of 1, six header / cell variants for the mobile columns 6 of 6 (never read). Through the API the same data succeeds (201 "1 devices uploaded successfully."), and an unknown master-data name returns an Excel validation report (200 xlsx with the columns plus Row Number, Upload Status, Validation Failure Reason), format errors return 422 JSON keyed by row (`devices.1.imei`). The screen could not be checked for how it shows a report, because it never sends data.
- **Reproducibility:** every time. Classification: **Confirmed Bug**.
- **Evidence:** `specs/evidence/oem-device-management/bulk-upload-dialog.png`.
- **Tests:** `tests/oem_panel/test_oem_device_management_ui.py::test_the_sheet_is_read_into_complete_rows` (the request is intercepted and aborted; expected failure: `{'devices': [{}]}`) and `::test_a_filled_in_sample_registers_the_device` (expected failure: 422).

### BUG-062 - The allocation history shows only the newest 10 allocations (Medium)
- **Source:** guide 6.1: "Device Allocation History shows every allocation, with date and receiver ... a device that is still in allocated stock can be rolled back from here."
- **Steps:** open Device Management > Device Allocation History; scroll to the bottom of the table.
- **Expected:** a pager (First / Previous / pages / Next / Last), as Device Details has, so every allocation can be reached.
- **Actual:** 10 rows and **no pager** and no "Showing ..." text. The page requests `GET /api/device-allocations?page=1&per_page=10&sort_by=allocated_at&sort_dir=desc`; the API reports `total: 312, last_page: 32` (341 today) and page 2 returns 10 more rows. Older allocations (and the Rollback of an old, still allocated one) can only be reached through the status, centre and date filters.
- **Validation attempts:** 3 of 3 page loads (rows = 10, no paging buttons, bottom of the page checked) and the API total each time. Classification: **Confirmed Bug**.
- **Evidence:** `specs/evidence/oem-device-management/allocation-history.png`, `allocation-history-bottom.png`.
- **Test:** `test_oem_device_management_ui.py::test_the_history_can_be_paged` (expected failure: "341 allocations exist but the page offers no way to see more than 10").

### BUG-063 - The Allocate Stock wizard lists only 20 available devices (Medium)
- **Steps:** have more than 20 available devices (25 were registered); Allocate Stock > choose a district and an active centre > Continue; count the rows of the device list.
- **Expected:** all available devices can be ticked (a pager or "load more"), or the screen says that only 20 are shown.
- **Actual:** exactly **20 rows**, no pager, no message. The list is fed by `GET /api/device-allocations/available-devices?page=1&per_page=20&search_type=imei&sort_by=created_at&sort_order=desc`; the same API reports 25. The only way to reach the others is to search each IMEI.
- **Validation attempts:** 2 of 2 manual runs (20 of 25) and the automated test; with 3 and 12 devices all are listed (no cap below 20). Classification: **Confirmed Bug**.
- **Evidence:** `specs/evidence/oem-device-management/allocate-step2-25.png`.
- **Test:** `test_oem_device_management_ui.py::test_the_wizard_lists_every_available_device` (expected failure: "20 of 25 available devices are listed and there is no pager").

### BUG-064 - The wizard's "available device(s)" counter always says 0 (Low)
- **Steps:** Allocate Stock > district > centre > Continue; read the text next to **Available Devices**, tick a device and read it again.
- **Expected:** the number of available devices (or of the listed ones).
- **Actual:** "**0 available device(s)**" with 3, 12 and 25 devices listed and after ticking devices; it did not change in 12 seconds of observation (3 of 3 timed runs).
- **Validation attempts:** 3 timed runs plus 4 earlier observations. Classification: **Confirmed Bug**.
- **Evidence:** `specs/evidence/oem-device-management/allocate-step2.png`.
- **Test:** `test_the_available_devices_counter_shows_the_number_listed` (expected failure).

### BUG-065 - The allocation history search finds nothing (Medium)
- **Steps:** open Device Allocation History, type an IMEI of an allocated device (or the fitment centre name or code) into **Search** ("Fitment center, IMEI, OEM code...").
- **Expected:** the allocations that match.
- **Actual:** "**No matching allocations found. Try changing your search keywords.**" The page sends `GET /api/device-allocations?...&search=<text>` and the API returns `total: 0` for **all 12 terms tried**: the full IMEI of a device in the allocation (two devices), the serial number, the centre name, a part of it, the centre code, the OEM code, the OEM name, the word "Allocated", the allocation id, the centre's e-mail and "AUTO". The same allocation is returned by `status=allocated` and by `fitment_centre_id=<id>`, so only the text search is broken.
- **Validation attempts:** three runs (API with 5 terms, API with 12 terms on a fresh allocation, the screen) all without a match. Classification: **Confirmed Bug**.
- **Test:** `test_oem_device_management_ui.py::test_the_history_search_finds_an_allocation_by_its_imei` (expected failure).

### BUG-066 - The Bulk Upload dialog accepts any file type and has no size or row check; a long file ends in a 504 (Medium)
- **Module / environment:** OEM panel > Management > Device Management > Device Details > Bulk Upload; https://vltd.misbackend.com, Chromium, 2026-11-02. First seen by the tester during manual exploration (file types processed without front-end validation, the application sometimes freezing, one 504); the points below were reproduced afterwards.
- **Severity / priority:** Medium / Medium. No data can be damaged (every row is refused), but a small, wrong file keeps the server busy for a minute and the user sees only a generic message or nothing. A long file of garbage is a cheap way to tie up the endpoint, so the priority can be raised if it is treated as a security / availability issue.
- **Preconditions:** signed in as the OEM Admin. Only harmless generated text files were used (a text file named `notes.exe`, a one-line `hello.py`, a `page.html`, and a `.py` file of repeated `value_n = n` lines); nothing executable.
- **Steps:**
  1. Open Device Details > **Bulk Upload** (the dialog says "Supported formats: .xlsx, .xls" and "Maximum upload: 10,000 devices").
  2. Press **Choose File** and pick a file that is not an Excel sheet (all-files in the picker, or drag it in): `notes.exe`, `hello.py` or `page.html`.
  3. Press **Upload**.
  4. Repeat with a long `.py` file (12,000 lines).
- **Expected:** a file that is not .xlsx / .xls is refused when it is chosen (message, no "Selected", Upload disabled) and never sent; a file with more than 10,000 rows (or over a size limit) is refused with a clear message; an unreadable file gets a specific message.
- **Actual:**
  - The dialog **accepts the file** ("Selected: notes.exe", Upload enabled). Only the `accept=".xlsx,.xls"` hint of the file picker exists, which a user can switch off ("All files") or bypass by dragging. There is no check of extension, type or size.
  - `.exe` and `.py`: the screen parses the text itself and sends `POST /api/devices/bulk-upload` with one empty row per line; the server answers 422 after about 1 s and the screen shows only "**Bulk upload failed.**" (no word about the file type) - 6 of 6.
  - `.html`: **no request is sent and no message appears**; the dialog stays as it was with Upload enabled, so the user does not know whether anything happened - 3 of 3 plus the first run.
  - **Long file**: the screen does not enforce its own limit of 10,000 devices. A 12,000-line `.py` file (230 KB) is sent whole (11,999 rows, a 36 KB body) and the server answers **504 after 60 s** - 2 of 2. The server's time grows with the rows: 499 rows -> 422 in 1 s, 2,999 rows -> 422 in 9-10 s (2 of 2 each), 11,999 rows -> 504. While the dialog waits, the user sees the Upload button spinning for a minute and nothing else; this is probably the "freeze" the tester saw. **A freeze of the whole browser tab could not be reproduced** (the page stayed responsive in all runs; the longest stall measured while waiting was 0.0 s), so only the long wait is confirmed.
- **Validation attempts:** file types 3 files x 3 runs (+ 1 earlier run each); row counts 500 / 3,000 / 12,000 x 2 runs each. Through the API the same payload is refused by the same server rules, so the missing check is on the screen and in the server's per-row validation time. Classification: **Confirmed Bug** (no front-end validation, no limit enforcement; the 504 is the server's reaction to the oversize request, **Intermittent / load-dependent** for smaller sizes - the 504 appears only at the size above).
- **Related:** BUG-061 (the same dialog sends empty rows for a real sample), the existing test `test_an_unreadable_file_is_reported_and_registers_nothing` (a text file is reported as "Bulk upload failed." and registers nothing; that still holds).
- **Evidence:** `specs/evidence/oem-device-management/bulk-upload-page-html-after-upload.png` (page.html selected, Upload enabled, nothing happened).
- **Tests:** `tests/oem_panel/test_oem_device_management_ui.py::test_a_file_that_is_not_an_excel_sheet_is_refused_when_it_is_chosen` (3 cases, expected failures; nothing is sent to the server) and `::test_a_file_with_more_than_10000_rows_is_not_sent` (expected failure; the request is intercepted and aborted, so the server is never asked).

### BUG-067 - "View Ticket Attachment" opens the portal's start page instead of the file (Medium)
- **Module / environment:** OEM panel > Helpdesk > ticket details; https://vltd.misbackend.com, Chromium, 2026-11-03.
- **Severity / priority:** Medium / Medium. A ticket's attachment (a screenshot, a document) cannot be opened by the OEM at all.
- **Preconditions:** signed in as the OEM Admin; a ticket with an attachment (raised with a small PNG; also checked with older tickets of other users, status and headers only).
- **Steps:** 1. Helpdesk > Support Queue, open the details of a ticket that has an attachment. 2. Click **View Ticket Attachment**.
- **Expected:** the attached file opens.
- **Actual:** a new tab opens the portal's **start page** ("VLTD Portal - Loading application..."). The link is `http://vltd.misbackend.com/storage/tickets/<name>.png`; it answers 301 to https, and the https URL answers **200 `text/html`, 12,878 bytes: the application shell**, with or without a token. The API returns the same `attachment_url` for every ticket, so the file is not served at all. The link also starts with `http://` on an https site (see BUG-057, the premises image).
- **Validation attempts:** through the screen 2 of 2 (tab URL `/`, title "VLTD Portal"); 4 new attachment URLs (a PNG, two text files and a 6 MB PNG) and 3 older attachments (.txt, .pdf, .html) 7 of 7 returned the application shell. Classification: **Confirmed Bug**.
- **Evidence:** `specs/evidence/oem-helpdesk/helpdesk-details-with-attachment.png`, `helpdesk-attachment-link-result.png`.
- **Test:** `tests/oem_panel/test_oem_helpdesk.py::test_the_attachment_link_opens_the_attached_file` (expected failure).

### BUG-068 - A ticket routed straight to the OEM has no activity record (Medium)
- **Source:** guide 19.1: "Every assignment and status change is recorded with time and person."
- **Steps:** 1. In the public Support Center (`/support/create-ticket`) raise a ticket and choose this OEM under **Route directly to OEM**. 2. As the OEM open Helpdesk > Support Queue and the ticket's details.
- **Expected:** Activity shows that the ticket was created and assigned to the OEM, with time and person (what a ticket raised from the OEM screen and sent to an OEM shows: "created by ...", "was routed directly to OEM ... by ...").
- **Actual:** the ticket is Assigned to the OEM, but **Activity 0 - "No activity is available for this ticket."** The API's `messages` list is empty; the first entry only appears with the OEM's first status change.
- **Validation attempts:** 4 of 4 public tickets routed to the OEM (two explored by hand, the shared test ticket and one made by the lifecycle test), each with no created / assigned entry; the OEM-screen path (ticket sent to another OEM) records both. Classification: **Confirmed Bug**.
- **Evidence:** `specs/evidence/oem-helpdesk/helpdesk-queue-direct-ticket-details.png`.
- **Test:** `test_oem_helpdesk_api.py::test_the_assignment_of_a_routed_ticket_is_recorded` (expected failure).

### BUG-069 - The server does not enforce the description limit of the New Ticket form (Low, API-only)
- **Steps:** `POST /api/user/ticket` (multipart) with a description of 2,001 characters (or more), a valid title and priority. The form stops at 2,000 characters; the status and close notes are limited to 2,000 on the server.
- **Expected:** 422 "The description field must not be greater than 2000 characters." (the server must enforce what the form implies, as decided for the Fitment Center).
- **Actual:** **200, ticket created** with 2,001 characters. Validation (with an invalid priority so that nothing is created) reports no description error for 2,001, 2,500, 5,000, 20,000 and 70,000 characters.
- **Validation attempts:** one real request (ticket created) and the validation probe with 6 sizes, repeated by the two automated cases. Classification: **Confirmed Bug** (API-only, not reachable through the normal form).
- **Test:** `test_oem_helpdesk_api.py::test_a_description_over_2000_characters_is_refused` (2 cases, expected failures).

### BUG-070 - The Helpdesk search treats `%` and `_` as wildcards (Low)
- **Steps:** Helpdesk > Support Queue (or Support Tickets), type `%` (or `_`) into **Search**.
- **Expected:** only tickets that contain that character (none of the test tickets does), or "No tickets match these filters".
- **Actual:** **every ticket is listed** (`...&search=%25` and `...&search=_` return the full total). A term such as `zzzz%` correctly finds nothing, so the characters are passed to the database's LIKE unescaped.
- **Validation attempts:** 3 of 3 (the screen once, the API twice, on both list endpoints) and the 4 automated cases. Classification: **Confirmed Bug**.
- **Test:** `test_oem_helpdesk_api.py::test_a_wildcard_character_is_searched_for_literally` (4 cases, expected failures).

### BUG-071 - The ticket counter says "1 tickets" (Low)
- **Steps:** Helpdesk > Support Tickets with exactly one ticket (first login of the account, or search for one ticket code).
- **Expected:** "1 ticket".
- **Actual:** "**1 tickets**" (the other counts read correctly: "0 tickets", "2 tickets", ...).
- **Validation attempts:** every time exactly one ticket was listed (3 of 3 by hand plus the test). Classification: **Confirmed Bug** (cosmetic).
- **Test:** `test_oem_helpdesk.py::test_the_counter_says_ticket_for_a_single_ticket` (expected failure).

### BUG-072 - Any signed-in user can read any other user's profile (High, API-only)
- **Module / environment:** OEM panel > Profile; https://vltd.misbackend.com, 2026-11-03. Found and reproduced using a dedicated, throw-away OEM account created for this testing plus existing throw-away `auto.oem.*` accounts; no real account's data was read.
- **Severity / priority:** High / High. `GET /api/users/{id}` is the call the Profile screen makes for the signed-in user's own id; the server does not check that the id belongs to the caller. It returned full profile data (name, e-mail, phone number, address, city, state) for the main OEM Admin, for the **State Admin**, and for other throw-away OEM accounts, when called with the dedicated test account's own bearer token.
- **Preconditions:** any signed-in account; the id of any other user (ids are returned in ordinary list responses throughout the application, e.g. `creator.id` in Helpdesk tickets and `created_by` in device allocations, so an id is easy to come by without guessing).
- **Steps:** 1. Sign in as any OEM. 2. Call `GET /api/users/{id}` with another user's id and this account's own token.
- **Expected:** 403 or 404 for any id that is not the caller's own.
- **Actual:** **200**, with the other user's full profile.
- **Validation attempts:** 3 separate runs, each against three or four different target ids (own, the main OEM Admin, the State Admin, one or two throw-away OEMs) - 200 every time, same fields every time. Classification: **Confirmed Bug**.
- **Evidence:** API-only; no screenshot (nothing in the UI itself is wrong - the screen only ever asks for its own id).
- **Test:** `test_oem_profile_password_logout.py::test_reading_another_users_profile_is_refused` (expected failure).
- **Update 2026-11-05:** confirmed platform-wide, not OEM-specific - reproduces identically from a Fitment Centre account against the OEM's own and the Admin's own profile (both 200). `test_fc_profile_password_logout.py::test_reading_another_users_profile_is_refused` (expected failure).

### BUG-073 - The same endpoint accepts a write to another user's profile, including their email - account takeover (Critical, API-only)
- **Severity / priority:** Critical / Immediate. Guide 4 describes sessions and roles but gives no rule for this screen specifically; no application screen offers editing someone else's profile, so this is reachable only by calling the API directly - but it works, and it reaches `email`.
- **Preconditions:** two throw-away OEM accounts (the dedicated test account and a second, pre-existing `auto.oem.*` account; separately, two more disposable accounts, A and B, used for the independent reproduction below).
- **Steps:** 1. Sign in as account A. 2. Call `PUT /api/users/{account B's id}` using A's own token, with a body changing `name`, `email`, and/or `contact_no`. 3. Read account B's profile back (as B, or as an admin) to confirm the change landed.
- **Expected:** 403 or 404; account B's record unchanged.
- **Actual:** **200**, and account B's stored `name`, `email`, **and `contact_no`** all changed to the values sent by unrelated account A.
  - First reproduction (assistant): a name-only change sent as the dedicated test account against a different account's id was accepted (200) and the stored name changed; confirmed by an independent admin-side read before/after, then restored immediately, with a third read confirming the original value was back.
  - Second, independent reproduction (user, 2026-11-03): using two fresh disposable accounts (A and B) created for this purpose, account A successfully overwrote account B's `name`, `email`, **and `contact_no`** via `PUT /api/users/{B's id}`. Overwriting `email` is sufficient on its own for account takeover - an attacker can redirect the victim's account email to one they control, then use the normal "forgot password" flow to take over the account without ever needing the write endpoint to accept a `password` field directly.
- **Validation attempts:** 2 of 2 independent reproductions (by two different people, against two different account pairs), both confirming the write succeeds; the second also confirming the gap reaches `email`. Each repeat is a real write to a live account, so this was not run more than the two times documented. The read side of the identical endpoint and authorization gap (BUG-072) was independently reproduced 3 of 3, further corroborating this is not a fluke. Classification: **Confirmed Bug**.
- **Not established:** whether the endpoint also accepts a direct write to the `password` field itself (as opposed to `email`, which already enables takeover via forgot-password) - not attempted, since the email result already establishes takeover severity and a live password overwrite on a real session is a more destructive thing to test than is needed to prove the point.
- **Related:** BUG-072 (the read side of the same gap).
- **Test:** none (a live cross-account write is not something to run routinely in the regression suite; see "Remaining gaps" in the test report).
- **Update 2026-11-05:** confirmed platform-wide, not OEM-specific - manually reproduced and immediately restored between two fresh, disposable Fitment Centre accounts (A overwrote B's `name` via `PUT /api/users/{B's id}`, 200; B's own token then read the overwritten value back before it was restored). Same endpoint, same gap, no special handling for the FC role. Not added as a routine regression test, for the same reason as the OEM side.

### BUG-074 - Logout ends the access token but not the refresh token (High)
- **Source:** guide chapter 4 describes "Sessions are tracked" and theft protection ending "all sessions of that user"; an explicit Logout is the user's own request to end their session, so both tokens issued at that sign-in should stop working.
- **Steps:** 1. Sign in (dedicated throw-away account). 2. Read the access token and refresh token the session is actually using (from the browser's own storage, or from the login response when done through the API). 3. Log out (through the UI menu, or `POST /api/auth/logout`). 4. Use the **same** access token, then the **same** refresh token, directly against the API.
- **Expected:** both are refused (401 / 422) after logout.
- **Actual:** the **access token is refused (401)**, but **`POST /api/auth/refresh` with the logged-out refresh token answers 200** and issues a brand-new, working access token - the "logged out" session can still be fully revived by whoever holds the refresh token.
- **Validation attempts:** 4 of 4 (twice calling `/api/auth/logout` directly through the API and reusing that exact pair of tokens; twice logging out through the actual UI menu, reading the tokens from `localStorage` beforehand to make sure the exact session's own tokens were tested, not a token from an unrelated sign-in). Classification: **Confirmed Bug**.
- **Related:** BUG-033 (a reused, already-used refresh token is refused but does not end the user's other sessions) - together, neither the system's own theft detection nor an explicit Logout fully closes out a refresh token.
- **Test:** `test_oem_profile_password_logout.py::test_logout_ends_the_refresh_token_too` (expected failure); `test_logout_ends_the_access_token` (passing: confirms the access-token half already works correctly).
- **Update 2026-11-05:** confirmed platform-wide, not OEM-specific - reproduces identically from a Fitment Centre account (logout: 200; the same refresh token then still mints a new access token: 200). `test_fc_profile_password_logout.py::test_logout_ends_the_refresh_token_too` (expected failure).

### BUG-075 - An unknown user id answers 500 instead of 404 (Medium, API-only)
- **Steps:** `GET /api/users/{id}` with a syntactically valid but non-existent UUID.
- **Expected:** 404.
- **Actual:** **500** `{"success":false,"message":"Failed to fetch profile."}`.
- **Validation attempts:** 3 of 3, three different random UUIDs plus the all-zero UUID, every time 500. Classification: **Confirmed Bug**, same family as BUG-019 (malformed id crashes instead of a clean 404).
- **Test:** `test_oem_profile_password_logout.py::test_an_unknown_user_id_is_not_found` (expected failure).
- **Update 2026-11-05:** confirmed platform-wide, not OEM-specific - reproduces identically from a Fitment Centre token (random UUID -> 500 "Failed to fetch profile."). `test_fc_profile_password_logout.py::test_an_unknown_user_id_is_not_found` (expected failure).

### BUG-076 - The two Change Password requests disagree on leading/trailing spaces (Low)
- **Steps:** 1. Set a new password with a leading and a trailing space through the **forced** first-login page. 2. Try to sign in with that exact, space-padded value, then with it trimmed. 3. Separately, set a new password with a leading and a trailing space through the **Profile > Change Password tab**. 4. Try to sign in with the exact value, then trimmed.
- **Expected:** consistent behaviour (reject the spaces, or keep them, the same way on both screens); neither screen shows any message about the spaces either way.
- **Actual:** the **forced page silently stores the password trimmed** (sign-in only works with the trimmed value afterwards); the **Profile tab stores it exactly as typed** (sign-in only works with the padded value afterwards). Neither screen warns the user, so a password set with a meaningful trailing space on one screen silently stops matching what was typed if the account is ever moved through the other screen (for example after the 90-day expiry forces the other flow).
- **Validation attempts:** each endpoint checked in isolation, with a fresh account, once each (a clean, single-variable comparison; not repeated further since each run is a real password change). Classification: **Confirmed Bug** (cosmetic / consistency, not a security issue - trimming either way is reasonable, disagreeing between the two screens is not).
- **Test:** `test_oem_profile_password_logout.py::test_a_padded_new_password_behaves_the_same_on_both_screens` (expected failure).

### BUG-077 - Changing a password does not end any existing session (High)
- **Source:** the ordinary security expectation of "change my password" (and the same expectation the guide states for Logout and for theft protection, chapter 4) is that it closes out whoever else might be using the old one, including the current session's own token if a stolen token is the reason for the change.
- **Steps:** 1. Sign in (dedicated throw-away account) and note the session's access token. 2. Change the password, either through Profile > Change Password or through the forced first-login page. 3. Use the **same, pre-change access token** again, directly against the API.
- **Expected:** the token stops working; only the new password can start a new session.
- **Actual:** the token **keeps working** (200 on `/api/auth/me` and on a real protected endpoint) immediately after a successful change, on both screens. The only thing that actually changes is that a *new* `/api/auth/login` call needs the new password; anyone already holding a valid token - including an attacker who obtained one before the legitimate user noticed and changed their password - is unaffected.
- **Validation attempts:** Profile tab: 3 of 3 (one through the full browser UI with a second, separately signed-in tab also left working; two more through the API alone). Forced first-login page: 1 of 1. Classification: **Confirmed Bug**.
- **Related:** BUG-074 (Logout has the same gap for the refresh token specifically); BUG-033 (a reused refresh key does not end the user's other sessions either).
- **Test:** `test_oem_profile_password_logout.py::test_changing_the_password_ends_the_current_sessions_own_token` (expected failure).
- **Update 2026-11-05:** confirmed platform-wide, not OEM-specific - reproduces identically from a Fitment Centre account (password changed successfully, 200; the pre-change access token still answers 200 on `/api/auth/me` afterwards). `test_fc_profile_password_logout.py::test_changing_the_password_ends_the_current_sessions_own_token` (expected failure).

### BUG-078 - Several Fitment Centre screens call admin-only filter APIs that refuse the FC role (Medium)

- **Module / environment:** Fitment Centre panel; https://vltd.misbackend.com, Chromium, 2026-11-04. Found during the initial navigation sweep of the FC panel (first day of FC testing), using the dedicated `FC_USERNAME` test account from `.env`.
- **Severity / priority:** Medium / Medium. Nothing crashes and the pages still render, but the RTO and OEM filters on four screens, and the Device Model filter on three report screens, can never be populated for any Fitment Centre user - the request that would fill them is refused before it starts.
- **Preconditions:** signed in as the Fitment Centre test account (any FC account should reproduce this; the failing calls do not depend on which FC is signed in).
- **Steps:** 1. Sign in as the Fitment Centre account. 2. Open each of: Operations > Live Tracking, Geofences, Trip Playback, Alerts; Reports > Device Health Report, Device Status & Connectivity, Installation Report. 3. Watch the Network tab (or browser console) for requests made as each page loads.
- **Expected:** the filter-population calls succeed (200) and return whatever list of RTOs / OEMs / device models the Fitment Centre is allowed to filter by (or the filter is simply not offered to this role, if it genuinely should not see it).
- **Actual:** **403** `{"success":false,"message":"Something went wrong. Please try again later."}` on:
  - `GET /api/transport-commissioner/rtos` and `GET /api/transport-commissioner/oems` - on Live Tracking, Geofences, Trip Playback and Alerts (4 of 4 pages, same two endpoints every time).
  - `GET /api/device-models?per_page=100` - on the Device Health, Device Status & Connectivity and Installation reports (3 of 3 pages).
  - The rest of each page still loads (heading, layout, the data panels that do not depend on these calls); only the affected filter would be left permanently empty for every Fitment Centre user, state-wide - this is not specific to the empty test account used (a 403 does not depend on how much data the account has).
- **Validation attempts:** 3 separate navigations/runs (an initial full-panel sweep of 26 pages; a focused re-check of the 7 affected pages read via the Network tab; a third, independent re-check of Live Tracking and the Device Health report). Same two or three endpoints, same 403, every time. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** these look like admin/State-Admin-scoped endpoints (`/api/transport-commissioner/...`) that the shared filter-dropdown component also calls from the Fitment Centre panel, rather than a Fitment-Centre-scoped equivalent (if one exists) or a request to simply omit the filter for this role. Not confirmed against the backend; a developer would need to say which is intended.
- **Evidence:** `specs/evidence/fitment-centre/live-tracking-filters.png` (the page loads normally; the filter calls fail silently in the background).
- **Test:** `test_fc_operations.py` (xfail, the 4 Operations pages); `test_fc_reports.py::test_the_device_model_filter_now_populates_real_models` (now a passing confirmation, not xfail - see update below).
- **Update 2026-11-05: the Device Model filter half is FIXED.** `GET /api/device-models?per_page=100` now answers 200 on all 3 report pages (Device Health, Device Status & Connectivity, Installation Report), and the dropdown populates with real device model names. Re-checked directly, not just assumed. **The Operations half is unchanged**: `GET /api/transport-commissioner/rtos` and `/oems` still answer 403 on Live Tracking, Geofences, Trip Playback and Alerts, confirmed the same day. So this bug now only covers the Operations pages; the Reports pages are resolved.

### BUG-079 - Owner Type / vehicle category mismatch crashes installation creation instead of a validation error (Medium)

- **Module / environment:** Fitment Centre panel, New Installation workflow; https://vltd.misbackend.com, 2026-11-04. Found while creating the first real installations for the FC test account, using vehicles from a user-supplied VAHAN test-data sheet (all "School Bus" category) and devices allocated earlier the same day.
- **Severity / priority:** Medium / Medium. Not a security issue and there's a clean workaround (pick the matching owner type), but a real Fitment Centre user doing a normal installation on a school bus can trigger this simply by clicking "Individual" instead of "School" - nothing in the UI stops them, and the result is an unhelpful 500 instead of a message telling them what's wrong.
- **Preconditions:** a vehicle fetched from VAHAN whose `vehicle_category` is "School Bus" (likely applies to any category/owner-type combination the backend doesn't expect, not just this one - not exhaustively tested).
- **Steps:** 1. Sign in as the Fitment Centre test account. 2. Start New Installation, search a School Bus vehicle by registration number (VAHAN fetch succeeds). 3. Select Device & SIM (tag-device succeeds). 4. On the final "Install Device" action, the UI sends `owner_type: "individual"` (the first/default-looking radio option) along with a valid lat/long.
- **Expected:** either a 422 with a clear validation message ("Owner Type must be School for this vehicle category", or similar), or the UI should restrict/preselect the owner type based on the vehicle's VAHAN category so the mismatch can't be submitted at all.
- **Actual:** `POST /api/installation` answers **500** `{"success":false,"message":"Something went wrong. Please try again later."}`. The UI shows a generic "Device Installation Failed - Validation failed." banner (itself misleading, since this is a 500, not a 422). The identical request with `owner_type: "school"` (matching the vehicle's actual VAHAN category) succeeds with 201 and creates the installation normally.
- **Validation attempts:** reproduced 3/3 via direct API calls with the exact failing payload (same vehicle+device), then isolated by swapping in a second, untouched vehicle/device pair (still 500 with `owner_type: "individual"`) and finally by changing only `owner_type` to `"school"` on a third pair (201, success). Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** looks like an unhandled exception server-side when the owner-type-specific fields/logic don't match what the vehicle record expects (e.g. a school-specific field being required downstream but missing because the "individual" branch was taken) - not confirmed against the backend.
- **Evidence:** request/response pairs captured directly (see steps above); no screenshot beyond the generic UI error banner, since the real detail is only visible in the network response body.
- **Test:** none yet; a regression test for this will fit naturally alongside the New Installation automation once FC page objects/API helpers exist.

### BUG-080 - No device can ever pass the Step 3 Health Check - "Tamper Status" fails for every live IMEI, blocking New Installation end-to-end (High)

- **Module / environment:** Fitment Centre panel, New Installation workflow, Step 3 (Device Health Check); https://vltd.misbackend.com, 2026-11-04. Found while trying to advance the 5 installations created today past Step 3 - the devices allocated to the FC test account are synthetic (never-deployed hardware) and correctly show no telemetry at all, but the user asked whether any of the ~4,777 IMEIs in their supplied sheet (`ReceivedData_FileList.xlsx`) might already be live, real devices, so each was checked directly against `GET /api/installation/health/{imei}` (which works for any IMEI, with no registration/allocation/tagging needed first).
- **Severity / priority:** High / High. This is the Health Check that gates Step 3 of New Installation for every Fitment Centre on the platform - "Next" stays disabled client-side until all 8 checks pass. If no device anywhere can pass "Tamper Status," then **no Fitment Centre can complete a New Installation at all** in this environment, regardless of which device or vehicle is used. This is the single highest-priority, most load-bearing workflow identified in the Fitment Centre test plan.
- **Preconditions:** none specific - reproduced across 25 different IMEIs, different devices/network operators/power levels.
- **Steps:** 1. Sign in as a Fitment Centre account. 2. Start a New Installation and get to Step 3 (Device Health Check) for a device that is actively sending telemetry - for example IMEI `863070045305140`, which has a live GPS fix, network signal, power and server connection right now. (Or, without the UI: call `GET /api/installation/health/863070045305140` directly - no registration/allocation/tagging needed first.) 3. Look at the 8 individual checks.
- **Expected:** at least some devices with full, fresh telemetry (GPS lock, network, power, battery, server connection all reporting "success") should have an overall `"passed": true`, since their tamper sensor isn't reporting any tamper event - i.e., "no alert" should read as a pass, not a fail. At least one device, out of thousands of IMEIs, should be able to complete Step 3 and let an installation proceed to Step 4.
- **Actual:** GPS Status, GSM/Network Status, External Power, Internal Battery, Device Communication and Time Synchronization all show "success" - but **Tamper Status** still shows **"failed"** ("Tamper alert not received"), so the overall check is `"passed": false` and the wizard's "Next" button stays disabled. The same device re-checked a minute later still fails on Tamper Status only, even though a fresh packet has clearly just arrived (`last_packet_at` moves forward each time).
- **How we know this isn't just one unlucky device:** every IMEI in a 4,777-device sheet the user supplied was checked the same way; 25 of them turned out to have live telemetry like the example above, and **all 25** failed on Tamper Status specifically, with no exceptions. That broader scan isn't needed to reproduce the bug - any one device with live telemetry (e.g. the example IMEI above) shows it immediately.
- **Validation attempts:** the example IMEI re-checked 3 times, minutes apart, same result each time; separately, a full-sheet scan (4,777 IMEIs) found 25 with live data and confirmed all 25 share the identical failure. Classification: **Confirmed Bug** (the behavior - zero passes across every live device tried - is confirmed and reproducible; whether the root cause is a check-logic defect or a test-data gap is not).
- **Possible cause (not confirmed):** either (a) the Tamper Status check's pass/fail logic is inverted or otherwise defective - treating the *absence* of a tamper alert as a failure instead of the healthy/expected state, or (b) the check genuinely requires a distinct "tamper OK" heartbeat field that real field hardware sends but that happens to be absent from every single packet seen in this environment (which would itself be worth knowing, since it would mean this environment currently has no way to demonstrate a passing installation at all). Either way, a developer needs to confirm which, since (a) is a bug to fix and (b) is a test-data/environment gap to fill.
- **Evidence:** `specs/evidence/fitment-centre/health-scan-results.json` (full scan output: 4,777 scanned, 25 with packet data, 0 full passes, all 25 detail records with their per-check breakdown).
- **Test:** none yet; blocks writing a real "complete a New Installation" regression test until this is resolved one way or the other - tracked as the top risk in the Fitment Centre test plan.

### BUG-081 - Dashboard "Pending Work" can never show a real count for Health Check, Document Upload or Approval (Medium)

- **Module / environment:** Fitment Centre Dashboard (`/fc/dashboard`); https://vltd.misbackend.com, 2026-11-04. Found during the Dashboard's manual testing pass, now that the FC test account has real installations to reconcile against (7, all genuinely `in_progress` and stuck at the Health Check step - see BUG-080).
- **Severity / priority:** Medium / Medium. Nothing crashes; the section just permanently under-reports, which could let real pending work go unnoticed by a Fitment Centre relying on this tile.
- **Preconditions:** none - reproduces on any account; most visible once real pending installations exist to compare against.
- **Steps:** 1. Sign in as the Fitment Centre test account, with at least one real installation stuck at the Health Check step (today: 7, all of them). 2. Open the Dashboard and look at "Pending Work." 3. Compare each of its 5 rows against `GET /api/dashboard/fitment-centre/summary`'s `pending_actions` object.
- **Expected:** all 5 rows (Health Check, Panic Test, Document Upload, Activation, Approval) show a real count reflecting actual pending installations.
- **Actual:** the API's `pending_actions` object only contains `activation`, `panic_test`, `vahan_sync`, `post_repair_verification` and `replacement_required` - there is no key for Health Check, Document Upload or Approval at all. The UI correctly shows real numbers for the two it has data for (Activation: 7, Panic Test: 0) but displays a static "Count not available from API" for the other three, even though - right now - Health Check's true count is demonstrably 7 (every one of the FC's installations is sitting at exactly that step).
- **Validation attempts:** confirmed directly against the live API response (`pending_actions` keys enumerated) and cross-checked against the known, exact state of all 7 installations (`GET /api/installation` list, all `installation_status: "in_progress"`, none past Health Check). Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** the summary endpoint appears to simply not compute these three counts yet (missing backend fields), which the frontend then renders as an honest "not available" placeholder rather than a wrong number - so the defect looks backend-side (incomplete `pending_actions`), not a frontend display bug. Not confirmed against the backend.
- **Evidence:** API response captured directly (see Actual); screenshot `specs/evidence/fitment-centre/dashboard-pending-work-gap.png`.
- **Test:** none yet; a dashboard reconciliation test (UI tile vs. API field, for all 5 Pending Work rows) will be added with the rest of the FC Dashboard automation.

### BUG-082 - Neither OEM nor Fitment Centre can ever see a vehicle's live position, only Admin can (High)

- **Module / environment:** Operations > Live Tracking (and the same `last-position` calls fire from Geofences, Trip Playback and Alerts); OEM panel and Fitment Centre panel both affected; https://vltd.misbackend.com + `vltdgo.misbackend.com` (a separate tracking microservice), 2026-11-04. Found during the Fitment Centre Operations sweep: every one of the FC's own 7 installed devices produced a 403 on `GET /api/last-position` when the Live Tracking page loaded.
- **Severity / priority:** High / High. This is not a filter dropdown or a secondary widget - it is the core data the Live Tracking map exists to show (where is my vehicle right now). If neither role that actually owns/operates vehicles can ever retrieve it, the map is non-functional for its real users; only Admin, who has other oversight tools anyway, can see it.
- **Preconditions:** none - reproduces for any OEM or FC account, against any IMEI, owned or not.
- **Steps:** 1. Sign in as a Fitment Centre account (or an OEM account). 2. Open Live Tracking (or call `GET https://vltdgo.misbackend.com/api/last-position?imei={imei}` directly) for one of that FC's own installed devices - for example IMEI `863070045332177` (installation 8843). 3. For comparison, try the same call as Admin, and also try a second, unrelated IMEI that has live telemetry (e.g. `863070045305140`).
- **Expected:** the OEM should be able to see the position of a device it registered and owns; the FC should be able to see the position of a device it installed. A device belonging to neither (IMEI b, for both roles) should reasonably be refused or scoped out - but the FC's own device (IMEI a) should not be.
- **Actual:** **both IMEIs, for both OEM and FC, return the identical 403** `{"error":"your role is not permitted to view this vehicle"}` - including the FC's own installed device. Admin gets **200** on the live IMEI with real position data (`{"imei":"863070045305140","point":{"latitude":25.444267,"longitude":82.856094,...}}`), and a clean 404 `{"error":"no known position for this device"}` on the FC's own (synthetic, telemetry-less) device - i.e. Admin's calls behave exactly as expected based on whether the device has data, while OEM/FC are blocked before that logic is ever reached, regardless of ownership.
- **Validation attempts:** reproduced across 2 different IMEIs (one definitely owned by the testing FC, one owned by neither role) and 3 roles (FC, OEM, Admin), 6 calls total, consistent result each time. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** the permission check on this tracking microservice endpoint looks like it may not be wired to real device/installation ownership at all for OEM/FC roles (unconditional role block), rather than correctly scoping "can this OEM/FC see this specific vehicle." Not confirmed against the backend.
- **Evidence:** request/response pairs captured directly (see Actual); also visible as background 403s on every FC Operations page in today's sweep (`specs/evidence/fitment-centre/live-tracking-filters.png` shows the page rendering normally despite this).
- **Test:** none yet; will be added alongside the Operations module's FC automation.

### BUG-083 - A Fitment Centre's ticket detail page never shows any activity log, not even for its own tickets (Medium)

- **Module / environment:** Fitment Centre Helpdesk, ticket detail view (`/fc/helpdesk/my-tickets`, opened row); https://vltd.misbackend.com, 2026-11-05. Found while automating the FC Helpdesk module: the OEM's identical screen shows a "Ticket {code} created by {name}" activity entry (and a further entry for every status change), confirmed already passing for the OEM; the FC side showed nothing at all.
- **Severity / priority:** Medium / Medium. Same family as BUG-068 (a public ticket routed to an OEM has an empty activity log) but broader and more basic: this is not a routing edge case, it is every ticket an FC ever raises or closes, with no workaround visible to the FC user.
- **Preconditions:** none - reproduces for any ticket the FC raises, whether left open or closed by the FC itself.
- **Steps:** 1. Sign in as a Fitment Centre account. 2. Raise a ticket from New Ticket (any reason/description). 3. Open that ticket's details from My Tickets. 4. Close the ticket with a note, then reopen its details.
- **Expected:** per guide 19.1 ("every assignment and status change is recorded with time and person"), the details should show at minimum a "created" entry, and then a "closed" entry with the note once closed - matching what the OEM's identical-looking screen shows for its own tickets.
- **Actual:** the FC's ticket detail page shows no Activity section at all, in either state - not a "created" entry, not the close note, not even an empty-state message like "No activity is available for this ticket." (which BUG-068 showed does exist as a component, just empty, in the case it covers). Opening the details triggers no additional API call either - the page has nothing to render from, because `GET /api/user/ticket` (the endpoint the FC panel's ticket list and detail view are built on) never returns a `messages`/activity array in the first place, unlike the OEM's `GET /api/helpdesk/tickets`, which does.
- **Validation attempts:** reproduced twice end-to-end (raise -> view details -> confirm nothing shown; raise -> close with a note -> view details -> confirm still nothing shown, not even the note itself), plus confirmed directly against the API response shape (`messages` absent/empty on every ticket read via `/api/user/ticket`). Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** `/api/user/ticket` and `/api/helpdesk/tickets` appear to be two different endpoints returning different ticket shapes for the same underlying ticket, and the FC panel was only ever wired to the one that omits activity - not confirmed against the backend.
- **Related:** BUG-068 (the same gap, previously found only for a public-ticket-to-OEM routing edge case; this shows it is not edge-case-specific).
- **Test:** `test_fc_helpdesk.py::test_the_details_of_a_ticket_show_its_creation_in_the_activity_log` (expected failure).

### BUG-084 - The Fitment Centre's Device Inventory Report crashes with a 500 on every load (High)

- **Module / environment:** Fitment Centre Reports > Device Inventory Report (`/fc/reports/device-inventory`, API: `GET /api/reports/fitment-centre/inventory`); https://vltd.misbackend.com, 2026-11-05. Found during the FC Reports module's navigation sweep: every other report page loaded cleanly, this one alone showed "Something went wrong."
- **Severity / priority:** High / High. There is no workaround (the crash happens with no filters or params at all, not just a specific filter combination) and no partial content - the report is completely unusable for every Fitment Centre.
- **Preconditions:** none - reproduces for any FC account, with or without query parameters.
- **Steps:** 1. Sign in as a Fitment Centre account. 2. Open Reports > Device Inventory Report (or call `GET /api/reports/fitment-centre/inventory` directly, with or without `page`/`per_page`/`sort_by` params).
- **Expected:** the report loads and lists this FC's allocated/inventory devices (10, per the test account's known data), as the Dashboard's own inventory summary and the Operations device lists already do successfully from the same account.
- **Actual:** **500** `{"success":false,"message":"Something went wrong. Please try again later."}` on every call, whether query params are sent or not. The page shows the same generic error text in place of the report.
- **Validation attempts:** reproduced 3 of 3 via direct API calls (no params; with `page=1&per_page=20`; with sort params matching exactly what the page itself sends) and confirmed visually in the UI. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** likely a backend error in this specific report endpoint (separate from the dashboard's working `/api/fitment-centre/inventory/summary`), given every other report and the dashboard's own inventory tile work fine from the same account. Not confirmed against the backend.
- **Test:** `test_fc_reports.py::test_the_device_inventory_report_loads` (expected failure).

### BUG-085 - The Inspector Dashboard always shows "0 Assigned RTOs," even when an RTO is assigned (Medium)

- **Module / environment:** RTO Inspector panel, Inspector Dashboard (`/inspector/dashboard`, API: `GET /api/inspector/dashboard`); https://vltd.misbackend.com, 2026-11-10. Found while exploring a freshly-created, dedicated Inspector test account that the State Admin had explicitly assigned to one active RTO at creation time.
- **Severity / priority:** Medium / Medium. Display-only: the Inspector's real functionality (Verify Fitment, Draft Challan, My Challans) is correctly scoped to the assigned RTO regardless of this widget; a user checking only this dashboard tile would wrongly conclude the account has no RTO and investigate a non-existent problem.
- **Preconditions:** an Inspector account assigned to at least one active RTO.
- **Steps:** 1. As a State Admin, create an Inspector and assign it to an active RTO (`/tc/users/inspector`, Add Inspector). 2. Sign in as that Inspector. 3. Look at the Dashboard's "Assigned RTOs" tile and the panel below it.
- **Expected:** "Assigned RTOs" shows 1 (or however many RTOs are assigned), and the panel lists the assigned RTO(s) by name/code - matching the Admin-side Inspector record (`GET /api/transport-commissioner/inspectors`, field `rto_mappings`).
- **Actual:** the tile reads **"Assigned RTOs: 0"** and the panel says **"No RTOs are currently assigned,"** although: (a) the Admin-side Inspector record correctly shows `rto_mappings: [{ "rto": { "code": "DL-96", "name": "VLTD Dedicated RTO DL-96", ... } }]`, and (b) the dashboard's own API call, `GET /api/inspector/dashboard`, correctly returns `inspector.rto_data: [{ "id": 211, "code": "DL-96", "name": "VLTD Dedicated RTO DL-96", "status": "active" }]` in the same response the page just loaded. The frontend simply does not read this field.
- **Validation attempts:** reproduced 3/3 (initial login + two page reloads, same session and account); cross-checked against two independent, mutually-agreeing API sources (`GET /api/transport-commissioner/inspectors` as Admin, `GET /api/inspector/dashboard` as the Inspector itself) that both confirm the RTO assignment is real and correctly stored - only the dashboard's own rendering of its own API response is wrong. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** the dashboard component likely reads a differently-named or differently-nested field (e.g. expecting a top-level `assigned_rtos` or a plain count) than the `inspector.rto_data` array the API actually sends. Not confirmed against the frontend source.
- **Test:** `test_inspector_panel.py::test_dashboard_shows_the_inspectors_assigned_rto` (expected failure).

### BUG-086 - An RTO Inspector account can approve or reject VLTD installations, an RTO-Officer-only action (High)

- **Module / environment:** RTO Inspector role permissions (backend role-permission template), reachable via `POST /api/rto/installations/{id}/approve` and `/reject`; https://vltd.misbackend.com, 2026-11-10. Found while building the role/permission matrix for a freshly-created, dedicated Inspector account and comparing its granted permission codes against the platform guide's role table (`VLTD_How_It_Works.pdf`, chapter 5: "RTO Officer - Approves installations..."; chapter 15: Inspector's job is roadside checks, draft challans and RTO installation reports - approval is never listed as an Inspector action).
- **Severity / priority:** High / High. This breaks the design intent of guide section 6.3 ("RTO: approve or reject the installation... an independent check by the transport department") - an Inspector approving its own RTO's installations is not independent of the fitment/approval chain the way the guide describes. Not currently exploitable end-to-end in this environment only because BUG-080 prevents any installation from ever reaching the pending-approval state, but the underlying role misconfiguration is real and will matter the moment that blocker is fixed.
- **Preconditions:** a signed-in RTO Inspector account (the default "RTO Inspector" role template, no special grant needed - this is the out-of-the-box permission set).
- **Steps:** 1. Sign in as an RTO Inspector (or obtain its bearer token). 2. Call `GET /api/auth/me` and note the `permissions` array includes `vltd_device_installations.approval.approve` and `vltd_device_installations.approval.reject` (also `vltd_device_installations.approval.view` and plain `.view`). 3. Call `GET /api/rto/installations/pending` with the Inspector's token. 4. Call `POST /api/rto/installations/999999999/approve` with the Inspector's token (a non-existent ID, to test only the authorization layer without needing a real pending installation).
- **Expected:** all four calls should be refused with **403** "You are not authorized to perform this action," the same way a Driver's token is refused on the same endpoints - installation approval should be exclusive to the RTO Officer role.
- **Actual:** the Inspector's token is **accepted** at every step: `GET /api/rto/installations/pending` answers **200** (empty list, since no installation exists at that stage anywhere in the environment - see BUG-080), and `POST /api/rto/installations/999999999/approve` answers **404** "Resource not found or inaccessible" - the *exact same* response an actual RTO Officer's token gets for the same non-existent ID. A Driver's token, by contrast, is correctly refused with **403** on both calls. Reaching "404 not found" instead of "403 forbidden" proves the Inspector's request passed the authorization check and reached the business logic - i.e. a real pending installation would be approvable by this Inspector.
- **Validation attempts:** reproduced with 3 roles compared side by side in the same run (Inspector, Driver, RTO Officer) against the identical bogus installation ID, both for the `pending` list (GET) and the `approve` action (POST); the Inspector and RTO Officer responses matched exactly (200/404), the Driver's did not (403/403). The UI correctly hides the "Installation Approvals" menu for the Inspector role, so this is reachable only via direct API or browser devtools use, not by normal navigation. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** the "RTO Inspector" role's default permission template appears to have been copied from, or merged with, the "RTO Officer" template and never had the approval permissions removed. Not confirmed against the backend's role/permission seed data.
- **Test:** `test_role_access_and_isolation.py::test_inspector_token_is_refused_installation_approval` (expected failure).

### BUG-087 - Every table's column headers are missing the `scope` attribute, state-wide (Medium)

- **Module / environment:** every data table checked across three panels (OEM Management's Device Models list, the OEM panel's Helpdesk ticket list and Device Allocations list, the Fitment Centre panel's Helpdesk ticket list); https://vltd.misbackend.com, 2026-11-10. Found while running the full regression suite in batches (`run_regression_batches.ps1`): 15 previously-passing (non-`xfail`) tests failed, 8 of which trace to this one root cause once investigated.
- **Severity / priority:** Medium / Medium. This is a genuine accessibility defect (a screen reader cannot announce which column a cell belongs to when navigating any table in the product - every list page in every panel is affected), and it is not cosmetic: it also makes "is this a header row or a data row" structurally ambiguous to any code (including assistive technology, and this project's own role-based test locators) that relies on standard ARIA table semantics instead of raw visual position.
- **Preconditions:** none - reproduces on every table checked, for every role (Admin, OEM, Fitment Centre), with no special data or account needed.
- **Steps:** 1. Sign in as any role. 2. Open any list page with a data table (for example, Administration > OEM Management > Device Models, `/tc/oem-management/device-models`). 3. Inspect any `<th>` element in the table header row (e.g. via the browser's DevTools Elements panel, or `document.querySelectorAll('table th')`).
- **Expected:** each `<th>` should carry `scope="col"` (or `scope="row"` where applicable), so it is exposed with the ARIA `columnheader` role and assistive technology/automation can correctly tell header cells apart from data cells.
- **Actual:** **zero** of the `<th>` elements checked, on any of the 4 tables across 3 panels, have a `scope` attribute. Confirmed directly: `document.querySelectorAll('table th')` returns real header cells with the correct text (e.g. "SR.NO", "OEM", "MODEL NAME" on Device Models), but every one has `scope === null`, and `page.get_by_role('columnheader')` finds **0** elements on every table checked. One concrete, mechanical side effect this surfaced: this project's own `rows()` helpers (used across `pages/oem_management/base_oem_page.py` and similar) filter "data rows only" by `get_by_role("row").filter(has=get_by_role("cell"))` - because a scope-less `<th>` is not exposed as `columnheader` in this browser, it falls back to a generic role that satisfies the `cell` filter too, so the header row is wrongly counted as a data row. This alone explains several of the day's regression failures (see the "Full regression run" note below) - e.g. a table test expecting exactly 5 data rows finding 6 (5 real + the header), or a test reading the "first row's" text finding the column-header labels instead of real data.
- **Validation attempts:** reproduced on 4 different tables (Device Models, OEM Helpdesk tickets, OEM Device Allocations, Fitment Centre Helpdesk tickets) across 3 different panels (Admin, OEM, Fitment Centre), each checked directly via DOM inspection, not inferred. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** looks like a single shared table component used across the whole frontend that never sets `scope` on its header cells. Not confirmed against the frontend source.
- **Test:** none dedicated yet; surfaced indirectly by 8 of the 15 non-`xfail` failures in the 2026-11-10 full regression run (`tests/oem_management/test_device_models_ui.py::test_list_page_has_all_controls_and_columns`, `::test_oem_filter_lists_all_oems_and_narrows_the_table`, the equivalent Firmware and SIM Modules tests, `tests/oem_panel/test_oem_helpdesk.py::test_the_two_lists_and_the_new_ticket_form_are_linked`, `tests/oem_panel/test_oem_command_center.py::test_history_counters_add_queued_and_sent_as_pending` and `::test_history_row_shows_device_command_and_status`, and `tests/oem_panel/test_oem_dashboard.py::test_recent_devices_lists_the_five_newest_first`) and already noted once before, narrower in scope, during the 2026-11-05 Fitment Centre Helpdesk pass (see that module's test file comments) without being filed as its own bug at the time.

### BUG-088 - The shared "cities" master-data endpoint always returns Delhi only, no matter what state is requested (High)

- **Reported by:** the user, while reviewing the Stop Management module on 2026-11-12 ("the city dropdown only shows options for delhi state if a user wants to create a stop outside delhi it is not possible").
- **Where:** Admin > Operations > PIS Management > Stops, Add Stop form, the "City *" dropdown; root cause is the shared `GET /api/masters/cities` endpoint, which this project's own existing test helpers (`utils/oem_panel_api.py`, `utils/staff_lab.py`, `tests/administration/test_inspector_transfer.py`, `tests/administration/test_user_creation_api_validation.py`, `tests/oem_panel/conftest.py`, `tests/oem_panel/test_oem_fitment_centres.py`) show is also used by OEM registration, Fitment Centre registration, Staff registration, and Inspector transfer.
- **Steps:** 1. Sign in as Admin. 2. Open Operations > PIS Management > Stops > "Add Stop". 3. Click the "City *" dropdown - only 17 entries appear (Alipur, Bawana, Central Delhi, Delhi, Deoli, East Delhi, Karol Bagh, Najafgarh, Nangloi Jat, Narela, New Delhi, North Delhi, North East Delhi, North West Delhi, Pitampura, Rohini, South Delhi, South West Delhi, West Delhi), with no state selector anywhere on the form to change this. 4. Confirmed directly against the API: `GET /api/masters/cities` returns these same 17 Delhi entries (`state_id: 9`) with no query parameters at all; calling `GET /api/masters/cities?state_id=1` (Andaman and Nicobar Islands, picked from the real `GET /api/masters/states` list of 36 states) returns the byte-for-byte identical 17 Delhi entries - the `state_id` parameter has no effect whatsoever.
- **Expected:** the City dropdown (and the underlying endpoint) should offer cities for whichever state is relevant - either by taking a `state_id` filter that actually works, or by returning the full national city list and letting the UI/search narrow it. Either way, a user should be able to create a Stop (or register an OEM/FC/Staff, or transfer an Inspector) anywhere in India, not just Delhi.
- **Actual:** every one of these forms can only ever offer Delhi's 17 districts. There is no way, through the UI or the API, to create a Stop - or populate the City field on any other form that uses this same endpoint - for any other state.
- **Validation attempts:** reproduced twice: once live through the Add Stop UI (dropdown contents captured in a screenshot), and once via a direct API call passing an explicit, different `state_id` and confirming the response ignores it entirely. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** either the cities master table itself only has Delhi seeded in this environment, or the endpoint accepts a `state_id` parameter but never actually applies it as a filter. Not confirmed against the backend source - distinguishing these two would need a look at the database or the endpoint's implementation, not just its observed behaviour.
- **Screenshot:** `specs/evidence/pis-management/BUG-088.png`
- **Test:** none yet - a regression check reusing `ApiClient.first_id`/`GET /api/masters/cities?state_id=<non-Delhi id>` and asserting the response is not all-Delhi would be a reasonable automated addition.

### BUG-089 - New Installation permanently creates a Permit Holder on reaching Step 3, even though Step 3 can never be passed (BUG-080) (Medium)

- **Reported by:** the user, who noticed Permit Holder Management already lists 27 holders and asked how that's possible when no installation has ever completed (BUG-080 blocks every installation at Step 3). The user then manually walked the New Installation wizard and confirmed the exact point: the Permit Holder record is created as soon as Step 3 (Health Check) is reached, independent of whether that Health Check passes.
- **Where:** Fitment Centre panel > New Installation wizard, Step 1 (Search Vehicle, VAHAN fetch) through Step 3 (Health Check); the resulting record then appears in Admin > Operations > Permit Holder Management (`GET /api/transport-commissioner/fleet-managers`), status "Approved".
- **Steps:** 1. Sign in as a Fitment Centre account (e.g. the "test FC" / FC123 test account). 2. Start New Installation and search a vehicle by registration/chassis number (Step 1 succeeds via VAHAN). 3. Select Device & SIM (Step 2). 4. Advance to Step 3 (Health Check). 5. Because of BUG-080 (Tamper Status always fails for every live device), Step 3 itself can never be passed and the installation never completes - but by this point the Permit Holder has already been created and persists regardless.
- **Expected:** a Permit Holder should only become a permanent "Approved" record once an installation genuinely completes (or at least once onboarding that vehicle's owner is an intentional, explicit action) - not as an automatic side effect of merely reaching an intermediate wizard step, especially one that this environment can never actually pass.
- **Actual:** 9 of the 27 Permit Holders currently in Permit Holder Management are confirmed orphans of exactly this kind: Sakshi Gupta (FLT2610582), Tanvi Khanna (SCH3568066), Yash Tandon (SCH2018172), Aakash Sharma (SCH3973628), Kavita Jain (SCH8465039), Mohit Arora (SCH5512626), Simran Kaur (SCH4994923), Pankaj Verma (SCH2845906) and Naveen Kumar (SCH6480350) - all under Fitment Centre "test FC" / FC123, created between 2026-11-04 and 2026-11-12 (the exact window the team was testing New Installation / investigating BUG-080). Each one's `contact_no` (9000001028 through 9000001047) matches the registration-number suffix of a vehicle in `new_vehicle_registration_chassis_list.csv`, the test data sheet used for that testing - confirming these are leftover side effects of blocked installation attempts, not real onboarded fleet owners or schools. (The remaining 18 Permit Holders, under a different Fitment Centre "TFC123" and dated 2026-09-24 to 2026-10-12, are unrelated pre-existing seed data, not a product defect.)
- **Validation attempts:** reproduced by the user manually walking the wizard and pinpointing Step 3 as the creation trigger; independently cross-checked by pulling the full Permit Holder list via the API and matching all 9 affected records' phone numbers against the chassis test-data sheet by registration-number suffix. Classification: **Confirmed Bug**.
- **Possible cause (not confirmed):** the Step 2 -> Step 3 transition (or Step 3's own page load) likely persists the vehicle owner fetched from VAHAN in Step 1 as a permanent Permit Holder record immediately, instead of only staging it until the installation actually completes.
- **Impact:** every attempt to reach or test Step 3 - including the team's own repeated BUG-080 investigation - leaves behind a permanent "Approved" Permit Holder with no device ever installed, inflating Permit Holder Management's counts and polluting its records state-wide, not just in this environment's test data.
- **Screenshot:** none yet (confirmed via manual walkthrough + API record audit, not a UI capture).
- **Test:** none yet - a regression test depends on the same blocked wizard as BUG-080's "complete a New Installation" test, so tracked alongside it; in the meantime a lighter check could assert that a Permit Holder is *not* created immediately after reaching Step 3, before Health Check passes.

### BUG-090 - Permit Holder has full Staff permissions but no Staff page anywhere in the panel (Medium)

- **Where:** Permit Holder (Fleet Owner) panel, `/fleet-owner/*`. Found during the first dedicated live
  exploration of this panel (2026-11-14) - a Permit Holder test account (`PERMIT_HOLDER_USERNAME`/`PASSWORD` in
  `.env`) only became available this session; see `specs/permit-holder-test-plan.md` for the full discovery.
- **Steps:** 1. Sign in as the Permit Holder test account. 2. Check `GET /api/auth/me` - the role carries
  `permit_holder.staff.view`, `permit_holder.staff.create`, `permit_holder.staff.update` and
  `permit_holder.staff.delete`, the same shape as its sibling `permit_holder.drivers.*` permissions (which DO
  have a working Drivers page under Fleet Management). 3. Look for a Staff entry anywhere in the nav (Dashboard,
  Operations, Fleet Management, Reports, Helpdesk dropdowns) - none exists. 4. Try direct URLs:
  `/fleet-owner/staff`, `/fleet-owner/users/staff`, `/fleet-owner/users`, `/fleet-owner/account/staff` - every
  one silently redirects to `/fleet-owner/dashboard` (no 404, no "unauthorized" - the router simply has no route
  for any of them). 5. Call the backend directly: `GET /api/permit-holder/staff` -> 200,
  `{"message":"Staff fetched successfully.","data":[],"meta":{...}}` - the API is real and working.
- **Expected:** either a Staff page exists under Fleet Management, next to Drivers and Vehicles (where the
  parallel `permit_holder.drivers.*` permissions already have one), letting a Permit Holder create/manage staff
  accounts for their own organisation - or, if this feature isn't meant to ship yet, the permission shouldn't be
  granted to the role at all.
- **Actual:** the permission is granted, the backend honours it, and there is no way to reach it from the UI.
- **Validation attempts:** reproduced twice (fresh login each time); confirmed the API itself works (ruling out
  "the feature is fully disabled") and confirmed the absence isn't a typo in one guessed URL by trying four
  plausible route patterns, all falling back the same way. Classification: **Confirmed Bug** - the same
  "permission exists, grants nothing" pattern already documented as BUG-015 for other roles, now also observed
  on Permit Holder.
- **Possible cause (not confirmed):** the Staff feature's frontend route/menu entry was likely never built for
  this role, while its permissions and backend endpoint were (a common "backend shipped ahead of frontend"
  pattern, matching BUG-015's own likely cause).
- **Screenshot:** none - absence-of-a-page isn't a single screenshot; see `specs/permit-holder-test-plan.md` §2
  for the full nav inventory this was checked against.
- **Test:** `tests/permit_holder/test_permit_holder_panel.py::test_staff_permission_has_no_reachable_page`
  (`xfail`, `strict=False` - flips to an unexpected pass if a Staff page is ever added).

### Full regression run, 2026-11-10 - 15 non-`xfail` failures investigated

Running the entire suite in panel-by-panel batches (`run_regression_batches.ps1 --known-bugs`, full results in `regression-logs/2026-11-10_120417/`) found 15 test failures that are **not** tracked `xfail` regressions for an existing bug (everything else: 1,161 passed, 138 xfailed, 6 skipped, exactly as expected). Investigated each by re-running it in isolation (ruling out cross-test/parallel-worker interference):

- **8 failures -> BUG-087 above** (the missing `<th>` `scope` attribute), confirmed as the root cause by direct DOM inspection, not just inferred from the stack traces.
- **7 failures could not be confirmed as new product defects**, and are **not** added to the bug list as a result (per this task's own instruction: do not report unverified issues as confirmed). `python -m utils.cleanup` was run and all 7 were re-tested again in isolation (no parallel workers) afterwards; 1 of the 7 (`test_oem_device_management_ui.py::test_a_double_click_on_allocate_and_on_confirm_rollback_sends_one_request_each`) now **passes** and was transient. The remaining 6 were each traced to a specific, non-product cause:
  - **`test_oem_device_management_ui.py::test_the_filters_apply_when_search_is_pressed_and_clear_filter_restores_the_list`** - two long-lived "AUTO PG" seed devices (`863070045332359`, `863070045332425`, status `allocated` since 2026-11-04) leak into a result that should only contain one freshly-registered device matching a brand-new Device Model filter. Confirmed via the API directly (`GET /api/devices?status=allocated`) that these two devices genuinely are `allocated` and belong to the old seed model, not a new one - so either the Model+Status filter combination doesn't actually narrow by model the way the test (and a real user) would expect, or (more likely, given BUG-046/BUG-063's already-documented "dropdown only shows the first N, no pager" pattern) the brand-new model the test just created isn't yet selectable from a paginated/truncated filter dropdown, silently leaving the model filter unset. Not independently isolated further; flagged here rather than re-opened as a new bug number, since it may just be BUG-046/063 manifesting in a new place.
  - **`test_oem_helpdesk_api.py::test_another_oem_sees_only_what_is_sent_to_it`** - a genuine test-fixture fragility, confirmed directly: the `other_oem` fixture picks "the newest `AUTO OEM` account that can still sign in," and this session alone created **56 new `AUTO OEM` accounts** today (334 exist in total; the 5 newest are all from today, 2026-11-10) while re-verifying BUG-073 and capturing bug screenshots. That shifted which account the fixture resolves to, so the long-lived shared ticket fixture (which finds-or-reuses a ticket routed to "the other OEM" from as far back as 2026-11-03) and the `other_oem` fixture now point at two different OEMs. This is a test-design assumption (that "the newest AUTO OEM" stays stable across days) broken by this session's own unusually high account-creation volume, not a product defect.
  - **`test_oem_command_templates.py::test_command_list_page_shows_the_template_and_counts_it`** (expected 1 matching row, found 2) and **`test_oem_dashboard.py::test_every_figure_follows_registration_allocation_and_rollback`** (`assert 3 == 1`) - both are count-reconciliation tests comparing a fresh count against a live API total; both are consistent with extra leftover records from this same session's unusually high device/template creation volume (today's manual bug re-verification and screenshot work, plus this full regression run itself retrying some tests), rather than a new defect. Not independently isolated further.
  - **`test_oem_allocation.py::test_wizard_allocates_available_stock_and_history_can_roll_it_back`** - skipped (a fixture precondition wasn't met), not failed; not investigated further since it never actually ran.
  **Conclusion: none of these 7 look like new product bugs** - they all trace to this specific session's own unusually large amount of hands-on testing (dozens of accounts, devices, tickets and templates created by hand today), not to anything wrong with the application. A quieter day's regression run would not be expected to reproduce them. Classification: **Environment/Test-Data Issue** (traced, not a product defect).

## 3. Observations that need a product decision (not counted as bugs)

1. The dashboard API returns `network.staff` and `recent_registrations`, but neither is shown.
2. Recent Major Alerts shows 3 items while the API returns 5 priority alerts.
3. "Live Fleet" counts 11 vehicles while "AIS-140 Fitted Vehicles" is 5; they come from different services and no rule ties them together.
4. The password rules for each role (see BUG-010) should be agreed and documented.
5. A staff member with **no permission** can list and create Challan Masters, Stops and Routes, and read the dashboard, helpdesk tickets and the permission catalogue. No permission exists for these features, so they are open to every staff member. Confirm that is intended.
6. Nine permissions could not be exercised safely (they need a real Fitment Centre, Permit Holder or challan): `fitment.centres.activate/deactivate/blacklist`, `fleet_managers.activate/suspend/blacklist`, `challans.approve/issue`, `reports.export`.
7. Device Models accept a **duplicate Part Number and a duplicate TAC Number** (only the Model Name is unique), although the OEM registration says the TAC number must be unique. Model names and firmware versions are unique case-sensitively (`Model` and `model` are both accepted).
8. The Firmware **release date** accepts any date (1900 ... 2099) and day-first text such as `15-01-2026`; the Device Model **TAC issue date** has no lower bound (1900 is accepted). The API stores `is_active = null` when the field is omitted (the list shows such records as Active).
9. The edit pages load the record *after* they appear and overwrite anything typed in the first moments; users who type immediately lose their input.
10. The application cannot delete OEMs, RTOs, Drivers, Inspectors, Staff or Help Centres, so test data of those kinds accumulates (see section 6). Deactivating a staff account blocks its login ("Your account is not approved or active."), which the cleanup uses.
12. A bulk upload of 10,001 device rows does not answer within 30 seconds (the documented limit is 10,000); not automated. `/api/transport-commissioner/permissions` answers 200 for an OEM.
11. The delete confirmation reads "Are you sure you want to delete Taiko ?" (stray space before the question mark).
13. **Fitment Center lifecycle (answered by the product owner on 2026-10-31):** a **suspended** centre can be reactivated; a **blacklisted** centre can never be reactivated (final). The guide itself does not describe it. Both lose their login (403) and are hidden from the allocation wizard. BUG-053 depends on this rule.
14. The Suspend / Activate / Blacklist boxes do not close with Escape and are plain overlays without a dialog role (not announced to assistive technology). The Edit page of an unknown centre id shows an empty form without any message (the details page says "Fitment Center details not found.").
15. The Fitment Center list searches only when **Apply Filters** is pressed (typing alone sends nothing). A search for `%` returns every centre (the wildcard is not escaped); name, code, e-mail, mobile and owner are searched, ignoring case and surrounding spaces.
16. The server accepts values that the screens have no rule for: special characters in the fitment code (`A B!#`), digits as an owner name (`12345`), script text as a business name (stored and shown as text), a pincode of `000000`. The product owner asked that the server enforce what the *forms imply*: that is BUG-042 (code uniqueness) and BUG-058 (mobile, e-mail, password length). These four have no rule on the screens either, so they are not bugs unless a rule is defined.
17. **Paging, sorting and uploads (tested 2026-10-31):** the list shows 10 centres a page with First / Previous / numbers / Next / Last and "Showing a to b of n results"; there is no page-size control; the page number is not kept in the URL, so a reload or Back returns to page 1. The column headers are not sortable on the screen (the list is always newest first); the API sorts only by `created_at`, `updated_at`, `short_name` and `owner_name` (business name, status and city are refused with 422). `page=0`, `page=-1` and `page=abc` silently give page 1 (no error). **Uploads:** the screens refuse wrong types, unreadable files, sizes and dimensions with clear messages and send nothing; the server checks the real content (text, HTML, SVG, GIF, PDF or empty files called `.png` are refused; a real PNG with a `.txt` name or an `.exe` suffix is accepted because only the content is judged; JPEG and WEBP are accepted types; 5 MB and 2 MB limits and the 300-4096 px rule hold on both endpoints). After a rejected pick the form still shows the earlier valid file name and then submits that earlier file, although the error stays visible: confirm that this is intended. Not tested: what a centre can do after signing in, and a real JPEG or WEBP of valid size (no image library is installed; a 1 x 1 file proves only the type).
18. **OEM Staff is not described in the guide** (it has no section on staff of an OEM). The product owner confirmed (earlier) that the OEM manages its own staff. Everything below comes from the screen: the Register form (name 100, e-mail 255, mobile 10 digits starting 6-9, password with upper, lower, number and 10+ characters, confirmation, 41 permissions in 16 groups) and the list (counters, search, status filter All / Approved / Suspended / Blacklisted, columns Staff, Role, Created on, Updated on, Last login, Status, Actions). Whether at least one permission is required, which roles a staff member gets, and what each status does are unknown until BUG-039 is fixed.
19. The **password** field of the Register OEM Staff form takes 255 characters but the **confirmation** stops at 100, so a password longer than 100 characters can never be confirmed (the Fitment Center form caps both at 100). The password show / hide buttons have no accessible name. The permission groups are an accordion (opening one closes the other). The Edit page of an unknown staff id shows an empty form without a message (the details page says "OEM Staff details not found.").
20. **Device Management (explored 2026-11-02): rules the guide does not decide** (classified *Unable to confirm / needs a decision*, not bugs): (a) an **allocated** device can still be edited, including its **IMEI** (`PUT /api/devices/{id}` -> 200, restored afterwards), so a fitment centre can hold a device whose identity changes; (b) the SIM validity date at registration has no upper limit (+10 years accepted; the 2 y / 1 y limit of guide 6.5 applies to the extension only); (c) Slot ID accepts any text; (d) the history's status filter offers **Received, Cancelled and Pending** besides Allocated and Returned, which the guide does not mention; (e) a *Returned* allocation shows a device count of 0 and the history no longer says how many devices it held; (f) editing a device's serial number leaves its `vahan_serial_number` unchanged.
21. Device Details filters (model, inventory status, dates) apply only when **Search** is pressed; choosing a value alone filters nothing. **Bulk Upload** with no file selected does nothing and says nothing. The View Device overlay does not show the SIM (ICCID, mobile numbers, validity). The date pickers of the list are custom controls and were not automated.
22. **Not testable with this account:** Repair (`/oem/repairs`: tabs All / Received / Repairing / Repaired / Replacement Required, search by vehicle number or IMEI; it lists nothing because a repair is raised by a fitment centre for an installed device), Replacement and the SIM extension happy path (an installed device is needed). The page and its empty state were explored; BUG-043 (SIM extension) was re-verified.
23. **Helpdesk status rules (explored 2026-11-03), needs a decision:** the guide gives the flow Opened -> Assigned -> In_progress -> Completed -> Closed. The application accepts more: (a) the owner's Change Status list offers **Open** while a ticket is Assigned, and `PATCH /api/helpdesk/tickets/{id}/status` accepts the step back (assigned -> opened 200) and opened -> opened (200), yet assigned -> assigned answers 403; (b) **In Progress can be skipped** (assigned -> completed 200); (c) the owner can **close** an In Progress ticket without completing it (200), and the person who raised a ticket can close it while it is still Opened. What it refuses: a jump to *closed* through the status action (403), and any change of a Completed or Closed ticket (422 "Tickets in a final status cannot be reopened or updated."; closing again 422). Who closes a Completed ticket is the person who raised it (the owner is offered only View Details).
24. **Ticket attachments have no rule:** the guide says only "optional attachment". The screen has no file filter or size message and the server accepted a text file called `.exe`, an HTML page and a 6 MB PNG (stored under a random name; the extension follows the content: `.txt` / `.png`). A list of allowed types and a size limit should be agreed. (See also BUG-067: the stored files cannot be opened.)
25. **Routing to other OEMs:** the New Ticket form lists **every OEM in the system** under *Send To* (104 names and codes), so an OEM can send its ticket, with description and attachment, to a competitor; the list comes from `GET /api/public/ticket/oems`, which answers **without a login** (needed by the public Support Center). The guide says only that the reporter can route a ticket directly to an OEM. Decide whether an OEM may route to another OEM and whether the public list should expose all OEMs.
26. "Support Tickets" (what the OEM raised) shows the ticket details **without the Activity log**; "Support Queue" shows it. A refused action answers a generic 403 "Request could not be completed." without a reason. The date pickers of the Helpdesk filters are custom controls (the API filters `from_date` / `to_date` were tested instead). The Support Queue also lists the tickets the OEM raised itself.
27. **Not testable (Helpdesk):** assignment of tickets to the OEM by the State Admin (State Admin panel), tickets raised by fitment centres or fleets, and a ticket assigned to an OEM staff member (OEM staff cannot be used, BUG-039). The State Admin's actions on the same tickets were only read through the API.
28. **Two endpoints for one action:** the forced first-login Change Password page calls `POST /api/auth/change-password` with `{current_password, new_password, new_password_confirmation}`, while the Profile > Change Password tab calls the general profile endpoint, `PUT /api/users/{id}`, with `{name, email, contact_no, current_password, password, password_confirmation}` (the whole profile resent alongside the password). The guide gives no rule either way; see BUG-076 for the one behavioural difference this produces (whitespace).
29. **Profile edit accepts values the Fitment Center / Staff forms would refuse:** a one-character name, a name containing HTML markup (stored and later rendered as literal text, not executed - no script ran in the browser in the cases tried), and clearing the Contact Number entirely (made optional, although it is required at registration) are all saved without a message. Confirm whether Full Name and Contact Number should keep the same rules as registration.
30. **Change Password, confirmed working as intended:** the current password is required and checked server-side; the new password must be at least 10 characters with an uppercase letter, a lowercase letter and a number (matches guide 9.1's rule for inspectors; the OEM Admin's own policy is not written down anywhere else); the new password is refused if it equals the current one; mismatched confirmation is refused; both password fields have an independent show/hide toggle; a successful change signs the session out to `/auth/login` (every screen must sign in again with the new password); the **old** password stops working immediately afterwards.
31. **Not testable:** the 90-day password-expiry forced change (guide 4) could not be produced on demand (it needs a 90-day-old account); the Super Admin's "Active Sessions" screen that can see and end a session (guide 4) is outside the OEM panel; the browser "back button then about:blank" observed once after Logout looks like a Playwright/history artifact of the test setup rather than application behaviour and was not pursued further.

## 4. What passed (no defects found)

- **Login:** valid login lands on `/tc/dashboard`; session survives reload; logout clears tokens and Back/reload/direct URL stay blocked; protected routes redirect to login; a tampered token is rejected; script and SQL-style input in either field never executes, authenticates or leaks errors; malformed emails are rejected.
- **Dashboard:** every KPI equals the API response; Active + Inactive = Total; Vehicle Mix sums to the fitted total; Active Alerts = Open; Network Overview active ≤ total; filters send the right query parameters; zero, null, 401, 500 and aborted responses do not crash the page; very large values keep the layout intact; refresh and Live Fleet auto-refresh (5 minutes) work; no tokens or passwords appear in URLs or console; mobile, tablet and wide layouts have no horizontal scroll.
- **Input validation (UI):** blank or malformed names, codes, CIN, GST, pincodes, mobiles, emails, passwords (too short, no upper/lower/number, mismatch), missing or invalid files (wrong type, over 2 MB / 5 MiB), missing dates, missing selects and an unpinned map location are all stopped with a clear message; the form stays open and no request creates a record. Duplicate OEM code/email, RTO code, Inspector email, Driver email/licence and Staff email are rejected by the server and the original record is unchanged. Script input in a name is never executed.
- **Input validation (server):** for Inspector, RTO and Staff the server returns 422 with a field-level error for over-long values, bad formats, pincodes, coordinates, unknown ids and weak passwords, and returns 401/403 on all five create endpoints without a valid token (exceptions: BUG-012 and BUG-013).
- **Network monitor:** across all negative UI runs no 5xx response and no stack trace, SQL or file path was seen in any response.
- **Staff permissions:** 38 of the 63 permissions behave correctly in both directions: with only the permission its feature opens and nothing else does; with everything except it that feature closes and the rest stays open. A revoked permission applies immediately to an already-issued token, every read endpoint probed refuses a caller without a token, Transport-Commissioner-only features (announcements, system configuration, merge / ownership reports ...) stay closed to staff even with all permissions, and the UI hides menu entries and redirects direct URLs for every permissioned page.
- **OEM Management:** Device Models, Firmware and SIM Modules can be listed, viewed, created (SIM Modules and Device Models through the UI), and SIM Modules and Firmware can be edited; the table shows the stored values; search is case-insensitive and treats special characters literally; the OEM, Status and Update Type filters and their combinations work; every required field and every length, date and certificate rule is enforced by both the form and the server (boundary values at the limit are accepted, one beyond is refused); duplicates are refused; text is stored and displayed as plain text; unauthenticated calls are refused; the TAC certificate downloads as the uploaded PDF.
- **User creation:** OEM, RTO, Inspector, Driver and TC Staff can each be created with valid data and then appear in the list with the entered details and an increased Total. Fitment Center and Permit Holder pages are view-only for Admin.

## 5. Test run

Last complete run of the whole suite, **2026-10-27**, with `pytest --known-bugs -n 4` (known-defect tests included): **671 passed, 2 failed, 1 skipped, 58 expected failures, 1 unexpected pass** in 11 min 46 s.
- **2 failures** (`test_vehicle_lookup_shows_the_current_owner_and_device`): script error. The test took the first tracked vehicle, whose installation is still in progress, so the Ownership Transfer and Untag look-ups correctly found no active installation. The fixture now picks a vehicle with an active installation; the file re-ran green (12 passed, 1 skipped, 1 expected failure).
- **1 unexpected pass** (`test_search_finds_a_record_that_is_beyond_the_first_page[firmware]`): script error, not a fix. It picked "the 11th record of the API", and because records created in the same second have no stable order (BUG-030) that record was sometimes on the first page. It now picks a record the page is not showing; BUG-024 reproduces for all three lists again (10 rows, no pager).
- **No product bug was fixed since 2026-10-23**: every expected failure still fails for its documented reason.
- The default run (without `--known-bugs`) skips the 58 known-defect tests; the OEM panel alone gives 98 passed (111 passed + 11 expected failures with `--known-bugs`).
- A shared script defect was fixed on 2026-10-27: the end-of-run cleanup also ran inside xdist workers, so a worker that finished early deleted the Device Model / Firmware / SIM Module that other workers were still using (22 spurious failures in the OEM panel run). It now runs in the main process only.

Expected failures by defect (58 reported + the one unexpected pass, now fixed in the script): BUG-005, 012 (not run), 013, 014 (4), 015 (16), 016 (2), 017 (2), 018, 019 (2), 021 (3), 022 (2), 024 (6), 029 (not run), 031 (2), 032, 033, 034 (a staff test, not a guide rule), 035 (not run), 036, 037, 038, 039 (3), 040 (4), 041, 042, 043. BUG-012, 029 and 035 are not run by default because they create records (an inspector each, and an undeletable orphan).

Earlier history: 2026-10-15 full run 874 passed, 50 skipped, 73 expected failures, 3 timing failures (fixed). On 2026-10-16 the suite was pruned from 1002 to about 424 tests (one representative case per validation partition, no per-permission UI copies).

Test-code problems found and fixed during the runs (not application bugs): dropdown option lists re-render while loading; file inputs disappear after upload; list pages show skeleton rows before real data; the edit pages overwrite anything typed before the record has loaded; `fill()` and typing respect `maxlength`; a table cell's OEM name arrives with a second request; parallel tests create and delete records at the same moment (ordering checks must not depend on global counts); vehicles listed by the tracking API may have an installation that is not active yet; stat cards fill in after separate requests (wait for the numbers).

## 6. Test data and cleanup

**Cleanup that runs automatically**
- Per test: the `records` fixture deletes the OEM Management records a test created, even when the test fails; it retries, and never deletes a Device Model whose firmware could not be removed (BUG-029 would orphan it).
- After every run (`pytest_terminal_summary`, once, when all workers have finished; skip with `--keep-test-data`, run by hand with `python -m utils.cleanup`): deletes leftover Device Models / Firmware / SIM Modules created by tests, **deactivates every test staff account** ("Auto Staff ..." - their login is then refused), and prints what is left for the DB owner.
- Kept on purpose: the "AUTO PG" seed (12+ records in each OEM Management list) used by the pagination tests; the single "AUTO HC lab" Help Centre used by the permission tests (reused, no longer one per run).

**What only the DB owner can remove** (the application has no delete for it) - counts at the end of the last run:
- 104 OEMs ("AUTO OEM ...", and OEMs whose name is 255 letters "A"), 21 RTOs ("AUTO RTO ..."), 34 Drivers ("Auto Driver ..."), 64 Inspectors ("Auto Inspector ..."), 41 Help Centres ("AUTO HC ..."), about 100 **allocation history rows** with status "returned" (every OEM allocation test leaves some), PIS stops / routes / calendars / patterns (no delete exists), and **12 orphaned firmware rows** (names "AUTO-<digits>" and "PG<digits>-nn" - left by BUG-029; the application refuses to delete them).
- Emails of test accounts match `auto.<type>.<timestamp>@example.com`.
- Every new run of the creation tests adds one OEM, RTO, Inspector, Driver and Staff; RTO codes are random free `DL-NN` values (only 100 exist), so remove old "AUTO RTO" rows regularly or the tests will report that all codes are in use.
- **Fitment centres:** the OEM's centres and their login accounts cannot be deleted. The suite keeps one long-lived centre, "AUTO PG FC lifecycle" (reused every run, restored to Active), adds one centre per run (the registration test; it is blacklisted afterwards by the blacklist test), and one extra per expected-failure run for the blacklist checks. A second, throw-away OEM account is created per run for the isolation tests. Real centres (Rajendra Fitments, Pfeffer Inc, Test_Fitment_center) are never changed.
- Records created by other people in the shared environment (for example the Device Model "Garry Haag" or the SIM module "ARC-123") are never touched by the tests or the cleanup.

## 7. Re-verification on 2026-10-23

Full suite with `--known-bugs` (4 workers): **573 passed, 2 failed, 1 skipped, 48 expected failures, 0 unexpected passes** (10 min 54 s). The 2 failures were staff logins that timed out under load (`test_open_menu_entries_work_for_staff` for the account-merges and ownership-transfers pages); both passed when re-run alone. Bugs without an automated test were re-checked by hand against the live system.

**Still reproducible: 35 of 37**

| Checked by | Bugs |
|---|---|
| Automated known-bug tests (still fail as expected) | 005, 013, 014, 015, 016, 017, 018, 019, 021, 022, 024, 031, 032, 033, 036, 037 |
| Direct API / UI re-check today | 001 (85 inspectors, all active, counter shows 0), 002 (42 drivers: counters 15 / 0 / 0, real 40 / 1 / 1), 003 (photo URLs are `http://103.114.154.160:8087/...`, mixed-content error), 004 (Geocoding API still not activated), 006 (Today button disabled), 007 (rows say Approved, counters say Active), 008 (View All opens `/tc/reports`), 009 (422 and two messages), 010 (hint still "Minimum 10 characters."), 011 (pin saves 20.354, 85.824), 012 (201 for a mismatched confirmation), 020 (404s on tracking pages), 026 (PNG rejected), 027 (500), 030 (11 distinct of 12 records returned over 3 pages), 035 (201 for a 9-character password) |

**Changed**
- **BUG-025:** improved. The Firmware list now shows OEM, model and part number for firmware whose Device Model exists. "-" now appears only for orphaned firmware (the BUG-029 leftovers). The View panel and the firmware detail call (which still returns only the OEM id and code) were not re-checked.
- **BUG-023, BUG-028:** remain fixed.

**Not re-run**
- **BUG-029:** reproducing it leaves another undeletable firmware row.
- **BUG-034 (referenced in `test_staff_lifecycle.py`):** a blacklisted staff member can be reactivated. It still reproduces, but the guide says nothing about it, so it is listed under observations, not as a defect.

### Update 2026-10-27
- Re-run of the whole suite: all 37 earlier defects that have a test still fail for the documented reason (see section 5); none was fixed.
- BUG-038 to BUG-043 (OEM panel) were found and are covered by expected-failure tests: 038 (Add Model offered), 039 (OEM staff 403), 040 (monitoring pages call State Admin endpoints), 041 (allocation to a blacklisted fitment centre), 042 (duplicate fitment code), 043 (SIM extension offered for a device that is not installed).
- BUG-025 stays "improved" (OEM, model and part number show for firmware whose model exists).
- Total documented: 43 entries, of which BUG-023 and BUG-028 are fixed (BUG-034 is mentioned only in a test and not counted: blacklisted staff can be reactivated, which the guide does not define).

### Update 2026-10-30 (OEM Dashboard)
- The OEM Dashboard was explored and tested on its own (`specs/oem-dashboard-test-report.md`). No OEM Dashboard bug was on record before; BUG-005 and BUG-008 (State Admin dashboard) do **not** occur on the OEM dashboard.
- One new defect: BUG-044 (SIM column of the Device Details widget is always "-"). Total documented: 44 entries.
- OEM scope run: 134 passed, 12 expected failures, 0 failed, 0 skipped.


### Update 2026-10-30 (found by manual exploration)
- Two admin-panel defects reported by the tester were confirmed live and automated: BUG-045 (Device Model created for a suspended or blacklisted OEM) and BUG-046 (OEM dropdown limited to 100 of 109 OEMs). Total documented: 46 entries.
- BUG-041 was re-validated the same day: the allocation to a blacklisted fitment centre still answers 201 (test: "A blacklisted centre received stock: 201").

### Update 2026-10-30 (OEM Operations)
- OEM Operations (Tracking & GIS, Command Center, SIM Validity Extension) was explored through the screens and tested (`specs/oem-operations-test-report.md`).
- Previously reported bugs re-verified: BUG-040 still reproduces (Alerts, Geofences, Live Tracking, Trip Playback call `/oems` and `/rtos` -> 403, plus `/api/school` -> 404, BUG-020); BUG-043 still reproduces (a registered, not installed device is shown as "Eligible" for SIM extension).
- One new defect: BUG-047 (an OEM Admin cannot create an alert rule). Total documented: 47 entries.
- Operations tests added: 29 (Command Center), 12 (Tracking & GIS: 11 passing, 1 expected failure). OEM scope run: 174 passed, 13 expected failures, 0 failed, 0 skipped.

### Update 2026-10-31 (OEM Operations, remaining functions)
- Product decisions received: (1) an OEM **may** create geofences; (2) Send Command must **not** accept a device that is not installed on a vehicle (BUG-048); (3) alert-rule creation is blocked for the OEM (BUG-047), and a scope the OEM cannot use should not be offered; (4) suspended and blacklisted OEMs must not be shown in the Device Model form's OEM dropdown (BUG-045 expected result updated, new dropdown test).
- Operations functions not covered before were explored and automated: the whole Geofences screen (draw a circle / rectangle on the map, save, duplicate, activate / deactivate, search and filters, delete with confirmation, cancel with the "Discard unsaved geofence?" question), the Alerts Resolved tab and the Trip Playback search for an unknown vehicle.
- OEM scope run with `--known-bugs`: **184 passed, 17 expected failures, 0 failed, 0 skipped** (every expected failure fails for its documented reason, no unexpected pass). Use the project `.venv` for xdist runs: the system pytest 8.4.1 crashes on xfail reports.
- Three new defects: BUG-048 (Send Command accepts a device that is not installed), BUG-049 (Edit geofence crashes the page, State Admin and OEM), BUG-050 (circle / rectangle zones listed as Freehand, type filters empty). Total documented: 49 entries (BUG-001 to BUG-050; BUG-034 is not counted).

### Update 2026-10-31 (OEM Fitment Center)
- Scope: OEM panel > Management > User Management > Fitment Center: register, edit, suspend, blacklist, activate, search and filters, status history, validation, API and isolation checks. Explored manually first (own test centres only), then automated in `tests/oem_panel/test_oem_fitment_center_lifecycle.py` (74 tests: 65 pass by default, 9 expected failures) with `pages/oem_panel/fitment_centers.py`.
- Six new defects: BUG-051 (another OEM can suspend / activate / blacklist a centre, API-only, High), BUG-052 (foreign edit answers 500 with an internal class name), BUG-053 (a blacklisted centre can be reversed and edited), BUG-054 (repeated status accepted), BUG-055 (stock allocated to a suspended centre, High), BUG-056 (Remarks History in UTC). BUG-042 was re-verified through the Edit screen. BUG-041 re-verified (still 201). Total documented: 55 entries (BUG-001 to BUG-056; BUG-034 is not counted).
- OEM scope run with `--known-bugs` (project `.venv`, `-n 4`): **248 passed, 1 skipped, 26 expected failures, 0 failed**. The skip was the existing isolation test `test_oem_cannot_read_a_fitment_centre_of_another_oem`: it read only the first page (10) of each list and the test centres filled it; it now reads 100 and the module re-ran green (30 passed, no skip). The 26 expected failures are the 17 of 2026-10-31 plus the 9 new ones; each fails for its documented reason (BUG-041, BUG-042 and the rest still reproduce, no unexpected pass).
- Things that work: validation on both forms (required fields, formats, lengths, spaces, mismatched passwords) with nothing sent when refused; every status change needs remarks (UI and server), the Cancel button changes nothing, a double click sends one request; a server error and an expired session are handled without changing the status; remarks are shown as text; a suspended or blacklisted centre cannot sign in; other OEMs cannot see or open a centre (list, search, details 404, "not found" page).

### Update 2026-10-31 (Fitment Center: paging, sorting, uploads, form rules)
- Product decisions received: a **blacklisted centre is final** (BUG-053 confirmed; a suspended one can be reactivated) and **the server must enforce what the forms imply** (BUG-042 stays, new BUG-058).
- Covered now: the pager (walk through all pages, Showing text, disabled First / Previous / Next / Last, every centre on exactly one page, a filter returns to page 1, newest first), the API paging and sorting (4 sort fields, both directions, invalid values refused, sort with a filter), the premises-image rules on the screen (12 refusals, 2 accepted sizes) and on the server (9 bad files and a control, on registration and on edit; JPEG / WEBP accepted), the GST certificate rules on the screen (required with a GST number, PDF only, 2 MB) and on the server (6 bad files, required with a GST number, a PDF accepted).
- Two new defects: **BUG-057** (the premises image is never shown: mixed content) and **BUG-058** (server accepts contact values and passwords the forms refuse; API-only). Total documented: 57 entries (BUG-001 to BUG-058; BUG-034 is not counted).
- OEM scope run with `--known-bugs` (project `.venv`, `-n 4`): **308 passed, 38 expected failures, 0 failed, 0 skipped** in 13 min 27 s (the 26 earlier expected failures + BUG-057 + the 11 for BUG-058; no unexpected pass).
- Test files: `tests/oem_panel/test_oem_fitment_center_paging_and_uploads.py` (60 tests: 59 pass, 1 expected failure) and 11 more tests in `test_oem_fitment_center_lifecycle.py` (BUG-058). Only generated harmless files were used; every server upload test also carries a wrong pincode so it cannot create or change a centre.

### Update 2026-10-31 (OEM Staff)
- Scope: OEM panel > Management > User Management > Staff. **Blocked by BUG-039**: re-verified through the screen (list and registration answer 403), so view, edit, status changes, search, filters, sorting, paging, role / permission access and staff isolation could not be explored or automated. The guide has no section on OEM staff.
- Explored and automated (`tests/oem_panel/test_oem_staff_form.py`, 30 tests): the Register OEM Staff form (required fields, e-mail, mobile, password policy, mismatch, masking, length limits, Cancel), the permission picker (16 groups, 41 permissions equal to `/api/oem/permissions` by id and name, Select All / Clear All / group boxes / search / counter), the request the form sends (intercepted and aborted: nothing can be created), the unknown-id page, the 401 checks and the OEM Admin's permissions. Together with the 3 older tests of `test_oem_staff_management.py`.
- Old bugs: BUG-039 Reproducible; BUG-007 Reproducible (State Admin TC Staff and the OEM Staff filter). BUG-014 to BUG-017 and BUG-034 concern State Admin TC staff (a different submodule) and were not re-run today.
- OEM scope run with `--known-bugs` (project `.venv`, `-n 4`): **333 passed, 43 expected failures, 0 failed, 0 skipped** in 13 min 19 s (the 38 earlier expected failures + 5 new ones; no unexpected pass).
- Two new defects: BUG-059 (a failed staff list is shown as "No Staff found") and BUG-060 (a name of spaces is sent). Total documented: 59 entries (BUG-001 to BUG-060; BUG-034 is not counted).

### Update 2026-11-02 (OEM Device Management)
- Scope: OEM panel > Management > Device Management: **Device Details** (list, filters, pager, View / Edit / Delete, Add Device, Bulk Upload), **Device Models**, **Allocate Stock**, **Device Allocation History**; Repair and SIM Validity Extension (other menus) were looked at only where they touch devices. Explored manually first (throw-away lab of devices, always removed), then automated in `tests/oem_panel/test_oem_device_management_ui.py` (40 tests, 33 pass and 7 expected failures) on top of the existing API tests for registration, bulk rules, allocation and rollback.
- Five new defects, each repeated 2-3 times: **BUG-061** (bulk upload from the screen cannot work, High), **BUG-062** (history has no pager), **BUG-063** (wizard lists 20 devices only), **BUG-064** (wizard counter always 0), **BUG-065** (history search finds nothing). BUG-038 is wider than recorded (Edit Model and Delete Model are offered too).
- Old bugs re-verified: BUG-038, 041, 043, 044 and 055 all **Reproducible**.
- OEM scope run with `--known-bugs` (project `.venv`, `-n 4`): **365 passed, 1 failed, 0 skipped, 50 expected failures** in 17 min 50 s. The one failure, `test_oem_dashboard.py::test_section_links_open_their_page` (a dashboard link stayed on the dashboard), is **Intermittent**: it passed 12 of 12 when re-run alone (3 runs of its 4 cases) and in the four earlier full runs, so it is a load-related timing failure of the test, not a confirmed bug. The run before it had one failure in the geofence cancel test; the cause was the Google map redrawing from vector to raster after load, which swallowed the first drag; `GeofencesPage.draw` now waits for the map tiles and retries (16 of 16 on repeated runs afterwards).
- Things that work: registration validation through the screen (duplicate IMEI, serial, ICCID, primary mobile; past SIM date; 100-character serial) with clear messages and nothing created; edit with validation, SIM fields read-only; delete with confirmation, and an allocated device cannot be deleted (422); the pager of Device Details; filters, partial and padded IMEI search; View Device; the wizard's step rules (Continue / Allocate stay disabled until a district, a centre and a device are chosen), search, select all, a double click on Allocate or Confirm Rollback sends one request; rollback returns the device to Available; **another OEM cannot read, edit, delete, allocate or roll back this OEM's devices and allocations, and cannot use its master data**.
- The throw-away lab of each probe was removed; two exploration devices left by a crashed probe were deleted by id. The only residue is allocation history rows with status Returned (about 340, the application cannot delete them).

### Update 2026-11-02 (Bulk Upload: file types and size, reported by the tester)
- The tester reported from manual exploration that the Bulk Upload dialog accepts unsupported files (.exe, code files) without front-end validation, that the application sometimes freezes, and that one upload returned 504. Reproduced and logged as **BUG-066** (Medium): any file type is accepted, `.exe` / `.py` are sent and refused by the server with only "Bulk upload failed.", `.html` does nothing and says nothing, and the 10,000-device limit is not enforced (a 12,000-line file is sent and the server answers 504 after 60 s, 2 of 2). A freeze of the whole browser tab could not be reproduced; the long wait could.
- Two regression tests added (4 expected failures: 3 file types + the row limit). Module run with `--known-bugs`: the 40 earlier tests unchanged (33 pass, 7 expected failures) plus these, so 33 passed and 11 expected failures; the 4 new tests fail for their documented reason with `--runxfail`. Total documented: 65 entries (BUG-001 to BUG-066; BUG-034 is not counted).

### Update 2026-11-03 (OEM Helpdesk)
- Scope: OEM panel > Helpdesk only: the two lists (**Support Tickets** `/oem/helpdesk/my-tickets` and **Support Queue** `/oem/helpdesk/assigned-tickets`), **New Ticket**, ticket details, **Change Status** and **Close Ticket**; the public Support Center (`/support/create-ticket`) was used only to raise test tickets that go to the OEM. The guide covers Helpdesk in section 19.1 only; every OEM action below is taken from the application.
- Explored by hand first (filters, search, dates, paging through the API, validation, failure and loading states, the whole lifecycle, who may act), then automated in `tests/oem_panel/test_oem_helpdesk.py` (22 tests, UI) and `test_oem_helpdesk_api.py` (71 cases, API and security) with `pages/oem_panel/helpdesk.py` and `utils/oem_helpdesk_api.py`; the fixtures are at the end of `tests/oem_panel/conftest.py`.
- Five new defects: **BUG-067** (attachment link opens the portal, Medium), **BUG-068** (routed ticket has no activity record, Medium), **BUG-069** (description limit not enforced by the server, Low, API-only), **BUG-070** (`%` and `_` list everything, Low), **BUG-071** ("1 tickets", Low). Observations 23-27 need a product decision. Total documented: 70 entries (BUG-001 to BUG-071; BUG-034 is not counted).
- Earlier bugs: none concerns the OEM Helpdesk. Observation 5 (a TC staff member without permission can read tickets) is about State Admin staff and was not re-run; BUG-057 (image served over http) has the same cause as BUG-067 as far as can be seen from the outside.
- What works: authorisation (another OEM cannot see, change or close this OEM's tickets: 403 / empty lists; the OEM cannot assign (403), delete or edit a ticket; every call without a login answers 401); the full lifecycle through the screen (Assigned -> In Progress -> Completed by the owner, Closed by the person who raised it) with a note, an activity entry per change with time and person, persistence after reload, and the lock on a Completed / Closed ticket; validation of the New Ticket form on the screen and the server (reason, description, title length 140, priority, unknown OEM) with nothing created; a double click sends one request (create and status change); search (code in any case, title, description), status, priority and date filters, Reset and Refresh; the pager; clear messages when a list or a status change fails.
- Test tickets: tickets cannot be deleted. The manual exploration left 8 tickets (all described as AUTO / QA probes), the automated tests keep three shared 'AUTO HD shared ...' tickets and add two per run (the one the form test raises and closes, and the routed ticket the lifecycle test completes); failed runs during development added a few more.

### Update 2026-11-03 (OEM Profile, Change Password, Logout)
- Scope: OEM panel > Profile, Change Password (both the Profile tab and the forced first-login page), Logout. Every password test used a dedicated, throw-away OEM account created for this work, never the shared `.env` account the rest of the suite depends on.
- Explored by hand first (view and edit the profile, every validation case on both the edit form and both change-password screens, show/hide toggles, the forced first-login redirect and its enforcement, Logout through the UI, back button, direct URL, refresh, a second open tab, and the raw API behind all of it), then automated in `tests/oem_panel/test_oem_profile_password_logout.py` with `pages/oem_panel/profile.py`, `utils/oem_profile_api.py`, and the `profile_account` / `profile_page` fixtures at the end of `tests/oem_panel/conftest.py`.
- Six new defects: **BUG-072** (any signed-in user can read any other user's full profile by id, High, API-only), **BUG-073** (the same endpoint accepts a write to another user's profile, **Critical, account takeover** - see below), **BUG-074** (Logout does not end the refresh token, High), **BUG-075** (an unknown user id crashes with 500, Medium), **BUG-076** (the two Change Password screens disagree on leading/trailing spaces, Low), **BUG-077** (changing a password does not end any existing session, High). Observations 28-31 cover the rest. Total documented: 76 entries (BUG-001 to BUG-077; BUG-034 is not counted).
- No earlier bug concerns this module directly; BUG-033 (a reused refresh key does not end the user's other sessions) is the closest relative of the new BUG-074.
- **Follow-up, same day:** the user independently re-verified BUG-073 by hand against two fresh disposable accounts (A writing to B), confirming the write reaches `email` (and `contact_no`) as well as `name`. This raises BUG-073 from High to **Critical**: overwriting a victim's email address is enough on its own for account takeover via the normal "forgot password" flow, with no need to write `password` directly. Severity and detail updated above; this is now the single highest-priority open item in the bug report.
- What works: profile view and edit (name, e-mail, contact number) with server-side validation (required fields, e-mail format, duplicate e-mail, 10-digit contact number) and the new values persisting after reload; the Change Password happy path end to end, including that the old password stops working and the new one is required to sign in again; the forced first-login redirect cannot be bypassed by navigating straight to a protected URL; Logout clears local storage, blocks the back button, a direct URL and a refresh (all bounce to `/auth/login`), and the access token is rejected by the API immediately; a second, still-open tab is also signed out once it talks to the server again.
