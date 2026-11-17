# OEM Operations - Test Report

Scope: the OEM panel menu group **Operations** only: **Tracking & GIS** (Live Tracking with Watchlists, Geofences, Trip Playback, Alerts with Rules), **Command Center** (Send Command, Command List, Command History) and **SIM Validity Extension**. Tested on 2026-10-30 against https://vltd.misbackend.com as the OEM Admin from `.env` (credentials not recorded), Chromium. Sources: `VLTD_How_It_Works.pdf` (chapters 6.5, 7, 8, 9, 11, 12, 13), the live screens, `bug_report.md`, the existing OEM tests.

Evidence: `specs/evidence/oem-operations/` (screenshots). Defects: BUG-047 (2026-10-30), BUG-048, BUG-049 and BUG-050 (2026-10-31) are new; BUG-040 and BUG-043 were re-verified; see sections 3, 4 and `bug_report.md`.

**Second pass, 2026-10-31:** the product owner answered the open questions (section 5), and the functions that were still missing were covered: the whole Geofences screen (draw, save, duplicate, activate / deactivate, search, filters, delete, cancel), the Alerts Resolved tab and the Trip Playback vehicle search.

**Account fact that limits everything below:** the OEM account has no vehicle (nothing is installed on it), no installed device and no command history of its own. Live positions, trip routes, alert timelines and the installed-device rules of the SIM extension cannot be shown on it, and an installation cannot be created or removed safely (it needs fitment centre, RTO and VAHAN steps).

---

## 1. Feature coverage

| Screen | What it does for the OEM | Explored by hand | Automated |
|---|---|---|---|
| Live Tracking, Fleet tab | map + vehicle list, status counters, filters | yes (empty: 0 vehicles) | empty state |
| Live Tracking, Watchlist tab | create / rename / delete lists, add vehicles, list rules | yes | create, rename, delete, name required, isolation, foreign vehicle refused |
| Alerts, Active / Resolved | pending alerts per vehicle | yes (empty) | empty state of both tabs |
| Alerts, Rules | create an alert rule (type, severity, scope) | yes, all scopes | BUG-047 (expected failure), isolation |
| Geofences | zones, alerts, Create Geofence (draw on the map) | yes (create, duplicate, activate / deactivate, search, filters, edit, delete, cancel) | create by drawing a circle / rectangle, save rules, cancel with discard question, duplicate, activate / deactivate, delete with confirmation, search and status filter, isolation; BUG-049 (edit), BUG-050 (shape filter) |
| Trip Playback | vehicle + date range, Load range | yes | empty state, Load disabled without a vehicle, unknown vehicle number finds nothing |
| Command Center > Command List | command templates per device model | yes | form, validation, limits, SOS Clear, edit, deactivate, filter, search, delete |
| Command Center > Send Command | find a device, choose or type a command, send | yes (one real send, see 8) | search, offered commands, request sent, nothing sent without a command, unregistered device refused; BUG-048 (a not installed device is offered) |
| Command Center > Command History | counters, filters, details | yes | counters, row, filters sent to the service, empty states, isolation |
| SIM Validity Extension | fetch a device by IMEI, extend the SIM | yes | existing tests (fetch, not found, other OEM, refusal), BUG-043 |

## 2. Manual scenarios executed (through the screens)

- **Command List:** Add Command with an empty form (3 messages), a normal command, a duplicate label ("The label has already been taken."), a General and an SOS Clear command, a second SOS Clear ("The purpose has already been taken."), changing a General command into a second SOS Clear (refused), editing label / text and switching Active off (counters 2/1/1 after reload, status filter), label search, Delete with the confirmation, labels of 150 and 151 characters, text of 2000 characters, a whitespace-only label and text, `<script>` in the command text (stored and shown as text).
- **Send Command:** search by full IMEI, partial IMEI, serial number, unknown IMEI ("No results found."); a model without commands shows only a text box ("No commands published yet for this device model."); with commands the page offers Catalog / Custom; only **active** commands are offered; Send with nothing chosen shows "Enter the raw command text." and sends nothing; one real send (see section 8).
- **Command History:** counters, status filter (Queued / Sent / Acknowledged / Failed), Sent by (manual / system), IMEI and command text search, date range (also reversed: no error, no rows), Details panel for a device that is not installed ("No vehicle details found for this device ...").
- **Alerts > Rules:** every scope of Create Alert Rule (All vehicles, RTO, Fitment Centre, Single vehicle) -> BUG-047.
- **Watchlists:** create (name required, the Create button stays disabled without one), create twice with the same name (accepted), rename, delete with confirmation ("The activity log is kept.").
- **Pages without data:** Live Tracking, Alerts, Geofences, Trip Playback all show an explicit empty message; Trip Playback's Load range stays disabled until a vehicle is entered.
- **Backend checks (not reproducible through a screen, so marked as such):** a foreign vehicle added to an OEM watchlist (403 "outside your jurisdiction"); a command to an IMEI registered nowhere (400 "not authorized to command this device"); the State Admin's geofence, watchlist and alert rules against the OEM's token; the State Admin's 40 commands do not appear in the OEM history.

## 3. Previously reported bugs, current status

| Bug | Re-verified how | Status |
|---|---|---|
| BUG-040 monitoring pages call State Admin endpoints | opened all four pages as the OEM; DevTools / automated test | **Reproducible**: `GET /api/transport-commissioner/oems` and `/rtos` -> 403 on Alerts, Geofences, Live Tracking and Trip Playback (plus `/api/school` -> 404, BUG-020). Visible effect: the RTO scope of the alert rule form is empty. |
| BUG-043 SIM extension offered for a device that is not installed | registered a device, fetched it on the page | **Reproducible**: the SIM is shown "Eligible" and Extend Validity is offered (test fails with `get_by_text("Eligible")` count 1, expected 0) |
| BUG-020 tracking pages: `/api/school` 404 | same page loads | **Reproducible** (OEM Live Tracking, Alerts, Geofences, Trip Playback) |
| BUG-038, 039, 041, 042, 044 | other OEM modules (device models, staff, allocation, fitment centres, dashboard) | not in Operations; BUG-041 was re-validated earlier the same day and still reproduces |

## 4. New bug

**BUG-047 (Medium): an OEM Admin cannot create an alert rule.** Create Alert Rule with the default scope "All vehicles" and with scope "Fitment Centre" answer 403 `your role is not permitted to create or update a rule with this scope`; the toast shows it and no rule is created. The RTO scope list is empty (BUG-040), the Single-vehicle list is empty (no vehicle), so no scope could be completed. The OEM permission catalogue has `alerts.view` but nothing to manage rules, although guide 9.3 says an OEM has its own rules. Evidence: `BUG-047-alert-rule-refused-403.png`. Test: `test_an_oem_can_create_an_alert_rule` (expected failure, fails with the 403). Details and steps: `bug_report.md`.

**BUG-048 (Medium): Send Command accepts a device that is not installed on a vehicle.** The search lists a registered, available device and the service queued a command for it (done once, 2026-10-30; the queued row cannot be removed). The product owner confirmed it must not accept one. Test: `test_a_device_that_is_not_installed_on_a_vehicle_is_not_offered_for_a_command` (expected failure; only the search is checked so that no further command is queued).

**BUG-049 (High): Edit geofence crashes the page**, "Something went wrong", `TypeError: Cannot read properties of null (reading 'type')`. 3 of 3 zones as the OEM, 1 of 1 as the State Admin. Evidence `geofence-edit.png`. Test: `test_a_zone_can_be_edited` (expected failure).

**BUG-050 (Low): circle and rectangle zones are saved as polygons and listed as "Freehand"**; the Circle and Rectangle type filters never match. State Admin and OEM. Test: `test_a_drawn_zone_is_found_by_its_shape_filter` (2, expected failures).

**Existing bugs updated with the product owner's answers:** BUG-047 (an OEM should be able to set a rule; a scope it cannot use should not be offered) and BUG-045 (suspended and blacklisted OEMs must not be shown in the Device Model form's OEM dropdown; a second test checks the dropdown).

## 5. Observations and unclear requirements (not reported as bugs)

**Answered by the product owner on 2026-10-31:** observation 1 (an OEM may create geofences: intended, now tested), observation 2 (a command for a device that is not installed must not be accepted: BUG-048) and the alert-rule question (BUG-047). Observation 7 (no Watchlist scope in the rule form) stays open.

1. **Geofences for an OEM:** guide 11 lists who may create and manage geofences (State Admin, RTO, fleet owners, schools); an OEM is not listed, yet the OEM screen offers Create Geofence and the service accepts a zone from the OEM (201 by the API; the draw-on-map step was not driven). Is that intended?
2. **Send Command to a device that is not installed:** the guide says the user searches a *vehicle*; the screen searches *devices* (all registered devices, installed or not) and the service accepted a command for a registered, not installed device (queued, no owner / fitment centre / OEM filled in the history row). Is a command for a device without a vehicle meant to be possible?
3. **Wording:** pressing Send with no command chosen says "Enter the raw command text.", also in Catalog mode where nothing was chosen. A duplicate SOS Clear says "The purpose has already been taken." Both work, the wording is technical.
4. **Duplicate watchlist names** are accepted (guide silent).
5. **History date range:** From later than To gives an empty list without a message.
6. **Status code of the refused command** is 400 (not 403) with "you are not authorized to command this device".
7. **Alert rule scopes:** the form has no Watchlist scope although guide 9.2 lists it.
8. **Alert rule scope "Fitment Centre"** offers the blacklisted centre as well (same family as BUG-041).

## 6. Missing coverage identified

| Gap | Decision |
|---|---|
| Command List form, SOS Clear rule (plan OEM-D3, "field not identifiable"), edit / deactivate / delete confirmation, filters | **automated** (the Purpose field is now identifiable) |
| Send Command search, offered commands, request body, nothing-sent rule | **automated** (send request mocked) |
| Command History counters, filters, empty states, isolation | **automated** |
| Watchlist lifecycle and isolation, foreign vehicle refused | **automated** |
| Geofence and alert-rule isolation, BUG-047 | **automated** |
| Geofence create / duplicate / activate / delete / search / filters / cancel, Alerts Resolved tab, Trip Playback unknown vehicle | **automated** (second pass) |
| Command delivery (Queued -> Sent -> Acknowledged / Failed), auto SOS Clear on a real SOS | not possible: needs a connected device |
| Live Tracking status rules (moving / idle / offline), vehicle filters, track and alert panels, Trip Playback route and events, Alerts grouping / Close all / timeline, watchlist with vehicles and rules | not possible: the OEM has no vehicle |
| SIM extension happy path, 2 y / 1 y limit, "installed on exactly one vehicle" | not possible: needs an installed device |
| Geofence drawing (circle / rectangle on the map) | **automated** (second pass): a drag across the Google map draws the shape; Freestyle and Route drawing, and assigning vehicles (the OEM has none), are not covered |
| A command sent to a real device of another OEM | deliberately not done: a refusal cannot be proven without risking a real queued command; the unregistered-IMEI refusal is tested instead |

## 7. New or updated automation

- `pages/oem_panel/command_center.py` (new): `CommandSendPage`, `CommandListPage` (moved from `misc.py`, extended), `CommandHistoryPage`.
- `pages/oem_panel/tracking.py` (new): `LiveTrackingPage` (watchlists), `AlertsPage` (rules), `GeofencesPage`, `TripPlaybackPage`.
- `tests/oem_panel/test_oem_command_center.py` (new): 30 tests (29 + the BUG-048 search test). `tests/oem_panel/test_oem_tracking_and_alerts.py` (new): 14 tests (13 passing, 1 expected failure). `tests/oem_panel/test_oem_geofences.py` (new, second pass): 11 tests (8 passing, 3 expected failures: BUG-049, BUG-050 x2). `tracking.py` gained the `GeofencesPage` actions (draw, create, duplicate, toggle, delete, cancel, filters) and `AlertsPage.open_resolved`.
- `tests/oem_panel/conftest.py`: the `template_lab` fixture moved here (shared by two files); `utils/oem_panel_api.py`: endpoint constants for the command, alert and geofence service host.
- Safety design: the send request is answered by a mock (no command is queued), command history answers are mocked where counters are checked, every created template / watchlist / zone is removed in a finalizer.
- Script problems found and fixed while writing the tests (none was a product defect): the Custom switch only exists when the model has catalogue commands; the "SOS Clear" option text carries a suffix; the first response matching `/alert/api/rules` was the list (GET), not the creation (POST), which made BUG-047's test fail for the wrong reason until the POST was matched; a toast helper missed "Enter the raw command text.", so the "no feedback" suspicion was dropped before it became a bug.

## 8. Execution results (2026-10-30)

| Scope | Passed | Failed | Skipped | Expected failures (known defects) |
|---|---|---|---|---|
| `test_oem_command_center.py` | 29 | 0 | 0 | 0 |
| `test_oem_tracking_and_alerts.py` | 11 | 0 | 0 | 1 (BUG-047) |
| Whole OEM scope (`tests/oem_panel` + `test_oem_role_access.py`), `--known-bugs`, 4 workers, 5 min 51 s (2026-10-31, after the second pass) | **184** | **0** | **0** | **17** (BUG-038, 039 x3, 040 x4, 041, 042, 043, 044, 047, 048, 049, 050 x2) |
| (2026-10-30, first pass, for comparison) | 174 | 0 | 0 | 13 |

- **Second-pass runs (2026-10-31):** the first full run crashed (xdist could not send the xfail reports of the system Python's pytest 8.4.1; the full run must use the project's `.venv`, pytest 9.1.1). The next run had 3 failures, all script problems found by the run: two tests deleted each other's 'AUTO ui' watchlists / zones because the cleanup used a shared name prefix (each test now uses and removes its own unique prefix), a zone-count comparison raced with parallel tests (now checks the test's own zone), and the map drag was done before the drawing tool was armed (it now waits for the tool's hint). The repeat was green. No product defect was involved.
- A first full run on 2026-10-30 had 11 failures, all "device model does not belong to your OEM" during device registration. It overlapped with an earlier run of mine that was still finishing in the background and removing shared test data; the repeat with nothing else running was green. This is a note on how the runs were done, not a product or test defect.
- Residue the application cannot remove: **one queued command** in the OEM's command history (the real send during exploration, to a throw-away device that was deleted afterwards). Tests do not depend on an empty history.

## 9. Blockers, risks, next steps

- **Blockers:** no vehicle / installed device on the OEM account (section 6). A fixture with an installed device (done once through the fitment-centre, RTO and VAHAN steps and left in place) would unlock Live Tracking, Trip Playback, Alerts, the SIM extension happy path and watchlist vehicles.
- **Risks:** BUG-047 means an OEM cannot configure non-SOS alerts; the command service accepts commands for devices without a vehicle (observation 2).
- **Next steps:** (1) product answers for observations 1, 2 and 7; (2) decide whether BUG-047 is a missing permission or a form that should hide scopes; (3) provide an installed device for the OEM account; (4) fix BUG-040 (it also empties the RTO scope list).
