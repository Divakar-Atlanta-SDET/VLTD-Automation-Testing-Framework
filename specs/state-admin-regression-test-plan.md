# State Admin — Coverage Audit and Regression Test Plan

Source of truth: `VLTD_State_Admin_Flow_Explanation.md` (the "guide"). Audited 2026-10-22 by reading the test code, page objects, `utils/`, `conftest.py` and by read-only GET calls against the live environment (no state was changed).
This file replaces an earlier version of the same name whose coverage table cited test functions that do not exist (for example `test_valid_login_stores_tokens_and_opens_dashboard`, `TestOEMNegative::*`).

Layer: **API** = Playwright `request` · **UI** = browser · **UI+API** = both required · **Manual** · **Clarify** = guide does not define the rule.
Priority: **P0** security, RBAC or irreversible data change · **P1** core workflow · **P2** secondary.

---

## 1. Facts the plan depends on

| Finding | Evidence |
|---|---|
| Four test files were added on 2026-10-22 (16:39–16:43) and were **not part of the last green run (424 passed)**: `tests/administration/test_oem_lifecycle.py`, `test_staff_lifecycle.py`, `test_inspector_transfer.py`, `test_device_model_constraints.py`. This audit read them but did **not execute** them (they suspend, blacklist and create accounts in a shared environment). Their status is "written, unverified". | file mtimes, collection list |
| Permission matrix: 84 probes (65 permissioned, 10 open, 9 restricted); 63 permission codes, 54 have a probe, 38 are in the generic positive/negative matrix, 4 are ungated (BUG-014), 14 probes are ineffective (BUG-015), 9 codes are not exercised. | `utils/permissions_matrix.py` |
| An OEM login now works from `.env` (`OEM_USERNAME`, role "OEM Admin"). Observed: OEM `POST {}` to device-models / firmware / sim-modules → 403, GET → 200, TC dashboard and system-configuration → 403. `TC_USERNAME` is not an email, so a second State Admin cannot log in. No RTO, Fitment Centre, Inspector, School or Super Admin login exists. | read-only probes |
| Environment data: 0 ownership transfers, 2 account merges, 18 permit holders, 4 fitment centres, installations exist, 29 SIM-validity rows. | report endpoints |
| System configuration GET exists (RESTRICTED). Current values: device-offline 24 h, COP 30 d, TAC 30 d, fitment/inspector/RTO distance 1000 m, RTO packet max-age 2 min, **all seven `enabled: true`**. `updated_at` is 2026-10-22 11:05 by the test admin account. Guide says the RTO distance check is off by default. | `GET /api/transport-commissioner/system-configuration` |
| Account-merge report row 2: source owner status is `suspended`, not `Merged` as the guide requires. Needs a manual look before it is called a defect. | `GET .../account-merge/report` |
| Write contracts for system configuration, ownership transfer, account merge, untag, PIS timetables are **not known** (TC `/timetables` and `/vehicle-ownership-transfer` return 404; UI routes exist). First step of each suite below is capturing the UI's network calls. | probes |

---

## 2. Coverage matrix (rule → real test)

Verdicts: **Covered** (assertion checks the guide rule) · **Partial** · **Weak** (assertion would pass on wrong behaviour) · **Gap**.

### §3 Sign-in, session, permissions

| Guide rule | Existing test (file::function) | Verdict | Class | Pri |
|---|---|---|---|---|
| Role home page after sign-in; return to requested page | `test_login.py::TestLoginSecurity::test_login_lands_on_role_dashboard_and_session_persists`, `::test_signing_in_returns_to_the_page_that_was_requested` | Covered for State Admin only; OEM role now loginable → home page for OEM untested | UI | P1 |
| Forced password change (first login) | `permissions/test_staff_account_security.py::test_new_staff_must_change_the_temporary_password_in_the_ui` | Covered for staff; **inspector** first login untested (guide §9.1) | UI | P1 |
| API must also enforce it | same file `::test_temporary_password_is_enforced_by_the_api` | xfail BUG-018 | API | P0 |
| 90-day expiry, admin-requested reset | none | Gap; no reset endpoint known | Clarify / Manual | P2 |
| 15 min inactivity sign-out | `test_login.py::TestLoginSecurity::test_user_is_signed_out_after_15_minutes_without_activity` | Covered (fake clock, 14 min stays, 15.5 min out) | UI | – |
| Activity in another tab counts | none | Gap | UI | P2 |
| Reused refresh key ends all sessions | `test_login.py::test_refresh_issues_new_keys_and_the_used_refresh_key_is_rejected`, `::test_reusing_an_old_refresh_key_ends_all_sessions_of_the_user` | Covered; second is xfail BUG-033 | API | – |
| Logout / tampered token / protected routes / generic error | `TestLoginSecurity::test_logout_invalidates_session`, `::test_tampered_token_is_rejected`, `::test_protected_routes_redirect_unauthenticated_users`, `::test_invalid_credentials_show_one_generic_error_and_no_session` | Covered | UI+API | – |
| Sign-ins, failed refreshes, forced sign-outs are audit-logged | none | Gap; no audit endpoint or page identified | Clarify | P1 |
| Super Admin sees/ends sessions | none | Out of State Admin scope (no credential; endpoint 404) | Manual | – |
| Role vs jurisdiction; view-but-not-edit; menus hidden | `permissions/test_staff_permissions_api.py::test_only_permission_opens_only_its_feature`, `::test_removing_permission_closes_only_its_feature`, `::test_staff_without_permissions_are_refused_every_gated_feature`, `::test_staff_without_permissions_can_use_the_open_features`, `::test_staff_can_never_use_transport_commissioner_only_features`, `::test_revoking_a_permission_applies_to_an_already_issued_token`, `::test_endpoints_require_authentication`; UI: `test_staff_permissions_ui.py::test_menu_entry_opens_page_with_permission`, `::test_without_permissions_every_gated_menu_entry_is_hidden_and_blocked`, `::test_open_menu_entries_work_for_staff` | Covered for **staff**. Defects documented as xfail: `::test_permission_has_effect` (BUG-015), `::test_unprotected_feature_requires_its_permission` (BUG-014), `::test_known_bug_*` (BUG-015/016/017). **Not exercised:** 9 codes (FC activate/deactivate/blacklist, permit-holder activate/suspend/blacklist, challans approve/issue, reports export) | API+UI | – |
| State Admin sees only OEMs/inspectors/drivers created by itself or its staff | none | Gap; needs a second State Admin login | Clarify | P0 |
| OEM-role menus/APIs hidden from the State Admin area | none | Gap (OEM token now available) | API | P0 |

### §4 OEM Management (master data)

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Device Model / Firmware / SIM Module create, view, edit, delete, validation | `oem_management/test_oem_mgmt_api.py` (classes `TestDeviceModelCreate`, `TestDeviceModelReadUpdateDelete`, `TestFirmwareCreate`, `TestFirmwareReadUpdateDelete`, `TestSimModuleCreate`, `TestSimModuleReadUpdateDelete`, `TestReuseAfterDelete`, `TestListSemantics`, `TestAuthentication`); UI: `test_device_models_ui.py`, `test_firmware_ui.py`, `test_sim_modules_ui.py`, `test_oem_mgmt_pagination.py` | Covered. Known defects as xfail via `bugs.py` (BUG-021/022/024/025/026/027/029/030/031) | API+UI | – |
| OEMs cannot create/edit/delete master data, can only view their own models | none | **Gap** | API | P0 |
| Linked Device Model / SIM Module cannot be deleted | `administration/test_device_model_constraints.py::test_delete_device_model_linked_to_installation_is_refused`, `::test_delete_sim_module_linked_to_installation_is_refused` | **Weak/unverified**: both `pytest.skip` when no installation is found or its JSON shape differs from the guessed one; SIM test accepts 422 or 409 | API | P0 |
| Firmware cannot move to another Device Model | none (`test_update_changes_the_record` never changes `device_model_id`) | **Gap** | API | P1 |
| Records belong to the selected OEM | `test_oem_mgmt_api.py::TestFirmwareCreate::test_device_model_must_belong_to_the_selected_oem` | Covered | API | – |
| Master data feeds OEM device registration | none | Gap; OEM-role workflow, needs disposable devices | Clarify | P1 |
| COP reminder uses the OEM account COP, daily 09:00 | none | Time-based job | Manual | P2 |

### §5 System Configuration

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Staff cannot reach it | `test_staff_permissions_api.py::test_staff_can_never_use_transport_commissioner_only_features` | Covered (access only) | API | – |
| Defaults 24 h / 30 d / 30 d / 1 km / 1 km / 1 km / 2 min; units; on/off per setting | none | **Gap** | API | P0 |
| Every change is audit-logged | none | **Gap** | API | P0 |
| Changed values take effect (fitment distance off disables the check, etc.) | none | Gap; effect only observable through installation / challan flows | Manual / blocked | P1 |
| RTO approval location check off by default | none | Gap; current environment shows it enabled | Clarify | P1 |
| `/tc/configuration` page | `test_staff_permissions_ui.py::test_known_bug_open_menu_entry_fails_for_staff` (BUG-017, staff view) | State Admin view of the page untested | UI | P1 |

### §6 Device lifecycle, §11 Repairs

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Register, allocate, roll back devices (OEM) | none | Gap, OEM-role, no disposable devices | Clarify | P1 |
| 8-step installation (VAHAN, SIM validity 2 y / 1 y, 1 km, health, SOS, validation 80 % / last 30 s) | none | Needs FC login and real packets | Manual | P0 |
| RTO approve / reject, reject needs remark, same-state check | none | No RTO login | Clarify | P0 |
| Untag device; untagged devices stay in report | none (`untag_search` only as a permission probe, BUG-015) | **Gap**; irreversible on a live installation | UI+API | P1 |
| Used device can never be re-allocated; repair / replacement rules | none | Needs live device data | Manual | P1 |
| SIM validity extension (≤ 2 y / 1 y, later than current) | none | OEM-role, irreversible ("cannot be changed any other way") | Clarify | P1 |

### §7 Ownership transfer and account merge

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Transfer: vehicle moves, old owner loses access, 8 link types released, history stays | none | **Gap**; 0 transfers exist | UI+API | P0 |
| Merge: all vehicles move, source and its staff become Merged | none | **Gap**; report shows source `suspended` | UI+API | P0 |
| Merged account cannot be merged again, receive transfers, change status; school accounts cannot be merged | none | **Gap**; two merged accounts already exist, so refusals can be tested without changing data | API | P0 |
| Reports list transfers / merges | `test_staff_permissions_api.py` RESTRICTED probes (access only); NAV tests for `/tc/reports/ownership-transfers`, `/tc/reports/account-merges` | Partial (loads, content not checked) | API | P1 |

### §8 Monitoring (tracking, alerts, ERSS, geofences, watchlists, commands)

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Permission gates on each feature | probes `tracking_*`, `alerts_list`, `commands_list`, `geofences_list`, `watchlists_*`, `help_centres_*`, `trip_history` in the staff matrix | Covered/xfail (BUG-014 for alerts, commands, geofences, trip history) | API | – |
| Status rules (3 min offline, 5 km/h + 30 m), GPS quality, history packets | none | Needs packet injection | Manual | P1 |
| Rule precedence, ownership rule, incident grouping, open → acknowledged → closed with remark | none | Needs live alerts | Manual; rule CRUD + Alert Set History is API-testable | P1 |
| Geofence CRUD, delete = archive (history stays), activate separate from delete | none | **Gap**, State-Admin-created data | API | P1 |
| Watchlist: State Admin sees all lists, adds any vehicle; Watch History records who/when | none | **Gap** | API | P1 |
| ERSS SOS flow, auto SOS-clear, alert stays open | none | Needs hardware SOS | Manual | P0 |
| Command lifecycle Queued → Sent → Acknowledged / Failed | none | Sends to real devices | Manual | P1 |

### §9 Inspectors and challans

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Create inspector (happy path) | `administration/test_user_creation.py::test_create_inspector` | Covered (UI: list row shows email, name, mobile, city, RTO, "RTO Inspector", "Active") | UI | – |
| Field validation | `test_user_creation_negative.py::test_inspector_rejects_invalid_input`, `::test_inspector_empty_form_lists_every_required_field`, `::test_inspector_duplicate_email_is_rejected`; `test_user_creation_api_validation.py::test_inspector_api_rejects_invalid_field` | Partial: password rule tested only for "no uppercase" (guide: ≥ 10 chars, upper, lower, number); duplicate **contact number** untested; inactive RTO / RTO without officer untested; BUG-012/013 xfail | UI+API | P1 |
| Temp password must change at first login; creation audit-logged | none for inspector | Gap | UI+API | P1 |
| Transfer: destination active, same state, has officer, differs from current; one-step; audit old/new | `administration/test_inspector_transfer.py::test_inspector_transfer_to_different_rto`, `::test_inspector_transfer_records_new_rto_only` | **Partial, unverified**: new RTO stored and exactly one mapping. Missing: same-RTO refusal, inactive RTO, RTO without officer, audit entry. `::test_inspector_transfer_requires_valid_rto` accepts 422 **or** 404; `::test_inspector_transfer_requires_rto_ids_field` tests the wrong JSON key, not a guide rule. The helper creates inspectors with `rto_id`, whereas the verified creation tests send `rto_ids` | API | P0 |
| Inspector list: Unassigned, search, filter, sees only own | none (BUG-001 documented, not tested) | Gap | UI | P2 |
| Challan Master CRUD | probes `challan_masters_list`, `challan_master_create` (OPEN, access only) | Partial | API | P2 |
| Challan draft → approve → issue (paid: exact amount + reference; cancelled: remark), 1 km location check | none | No inspector login; 3 challans exist | Clarify | P0 |
| Silent-device challan (7 days / 5 min) | none | Time-based | Manual | P2 |

### §10 PIS

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Stops → Routes → Service calendar → Service pattern → Timetables → Trips | `test_staff_permissions_api.py` OPEN probes (`stops_list`, `routes_list`, `stop_create`, `route_create`); `test_staff_permissions_ui.py::test_open_menu_entries_work_for_staff` (pages load); `::test_known_bug_hidden_route_is_reachable_by_url` (trips, BUG-017) | **Gap** in function: no create/edit/delete, dependency order, up/down direction, added/removed dates | API (+1 UI smoke) | P1 |
| Public Track Public Transport page | none | Gap | UI | P2 |

### §12 Reports, §13 Helpdesk / announcements

| Guide rule | Existing test | Verdict | Class | Pri |
|---|---|---|---|---|
| Report access control | staff matrix probes `device_validity_report`, `user_devices_report`, `alert_report`, `multiple_challan_report`, `installation_performance`; NAV tests for every `/tc/reports/*` entry | Covered (access) | API+UI | – |
| Report content: SIM Validity critical < 7 d / at risk < 30 d | none | **Gap**, read-only | API | P1 |
| Device Packets ≤ 31 days, ≤ 200 rows/page | none | Gap, read-only; "may be refused" is not testable as written (Clarify) | API | P2 |
| Installation Report bucket priority; RTO reports filtered by FC's RTO; exports include all pages | none | Gap | API / UI download | P2 |
| Untagged / ownership / merge reports retain history | none | Blocked by untag/transfer data | API | P1 |
| Helpdesk Opened → Assigned → In_progress → Completed → Closed, actor + time recorded | probe `helpdesk_tickets` (OPEN, access only) | Gap | API | P2 |
| Announcements: audiences, importance, window, PDF, scheduled/active/expired, off stays inactive | `test_dashboard.py::test_manage_announcements_navigates` (navigation only); probes `announcements_list/create` (RESTRICTED) | Gap | API | P2 |

### Not guide-defined

| Area | Tests | Note |
|---|---|---|
| Dashboard (State Admin) | `test_dashboard.py` (15), `test_dashboard_extended.py` (9) | The guide has no dashboard rule. They compare the UI with the API payload; keep as smoke, do not extend. |
| Other user creation (OEM, RTO, Driver, Staff) | `test_user_creation.py`, `test_user_creation_negative.py`, `test_user_creation_api_validation.py` | Guide gives creation rules only for inspectors. Other forms are validated against observed behaviour, not the guide. |

---

## 3. Weak, duplicate and outdated tests (no change made)

| Test | Problem |
|---|---|
| `test_staff_lifecycle.py::test_deactivate_requires_no_body_or_accepts_remarks` | Passes on 200 or 422; asserts nothing. Remove or decide the rule. |
| `test_staff_lifecycle.py::test_blacklisted_staff_reactivation_is_terminal` (xfail "BUG-034") | The guide says nothing about blacklisting staff. BUG-034 is not in `bug_report.md`. An assumption is recorded as a defect. |
| `test_oem_lifecycle.py::test_oem_blacklisted_can_be_reactivated` | Asserts the opposite policy for OEMs (reactivation allowed) from the staff test above. Same server behaviour is "expected" for one and "a defect" for the other. Guide silent. |
| `test_oem_lifecycle.py::test_oem_deactivate_requires_remarks`, `::test_oem_activate_requires_remarks` | Duplicated by the parametrized `::test_oem_status_change_without_remarks_is_rejected`. |
| `test_oem_lifecycle.py`, `test_staff_lifecycle.py` | Status values, remarks being mandatory and "token is invalidated on suspension" are observed behaviour, not guide rules. Each run adds undeletable OEMs. |
| `test_device_model_constraints.py::test_delete_unlinked_device_model_succeeds` | Duplicates `test_oem_mgmt_api.py::TestDeviceModelReadUpdateDelete::test_delete_removes_the_record`. |
| `test_inspector_transfer.py::test_inspector_transfer_requires_authentication`, `test_staff_lifecycle.py::test_status_actions_require_authentication` | Authentication on every endpoint is already covered generically; keep one parametrized check instead of one per endpoint. |
| Four new files each define their own session `admin_api` fixture | Duplicates `oem_admin` / `staff_lab` fixtures; belongs in the root `conftest.py`. |
| `test_dashboard_extended.py::test_recent_major_alerts_match_api_order` | Skips when the environment has no alerts; passes without checking anything. |
| Previous plan file | Cited non-existent tests; replaced by this file. |
| `README.md` / `bug_report.md` §5 | Counts predate the pruning and the four new files. |

---

## 4. Recommended suite: what to add

Rules for all new tests: one parametrized test per rule family; read-only tests first; any test that changes state uses a disposable record and restores or removes it; no test asserts behaviour the guide does not state without a Clarify note.

| # | Suite (new file) | Scenarios (parametrize over the listed variable) | Layer | Pri | Depends on |
|---|---|---|---|---|---|
| S1 | `administration/test_state_admin_reports.py` | SIM Validity row class vs expiry date (< 7 d critical, < 30 d at risk, parametrize bands); Device Packets: 31-day range accepted, 200-row page cap; Installation Report bucket order; untagged / ownership / merge report shapes. Read-only. | API | P1 | none |
| S2 | `oem_management/test_oem_role_access.py` | OEM token on `/api/device-models`, `/device-firmwares`, `/sim-modules`: create / update / delete → 403, list/view → 200 and only own OEM rows (parametrize over the three resources and verbs); OEM token on TC-only endpoints (`oems`, `system-configuration`, `dashboard`) → 403. Plus OEM login lands on the OEM home page. | API+UI | P0 | `OEM_*` in `.env` (present) |
| S3 | `administration/test_merged_account_rules.py` | Using the existing merged accounts from the merge report: merge again, receive a transfer, change status → all refused and nothing changes; school account cannot be merged (if a school account exists). | API | P0 | write contracts (capture from UI); skips visibly if no merged account |
| S4 | `administration/test_system_configuration.py` | GET defaults and units (parametrize over 7 settings); update each value and on/off, assert persisted and `updated_by/updated_at`; restore in `finally`; an audit entry per change if an audit read endpoint is found. | API | P0 | write contract; audit location (Clarify); restores shared state used by other roles |
| S5 | extend `test_oem_mgmt_api.py` | Firmware update cannot change `device_model_id`; replace the two skip-prone linked-delete tests with one that picks a linked model from `/api/device-models` detail data and fails (not skips) if none exists. | API | P1 | linked model exists (verify) |
| S6 | extend `test_user_creation_api_validation.py` + `test_inspector_transfer.py` | Inspector password rules (length 9/10, no upper, no lower, no digit), duplicate contact number, RTO inactive; transfer to same RTO refused, to inactive RTO refused; first login forces password change (UI). | API+UI | P1 | an inactive RTO (create one, deactivate if API allows) |
| S7 | `administration/test_pis_schedule.py` | Create → read → update → delete for each layer in dependency order (parametrize over stops, routes, calendars, patterns, timetables, trips); route has up and down; calendar added/removed dates; deleting a parent in use is refused (only if the app does so; else Clarify). One UI smoke for the create form. | API (+UI) | P1 | contracts for patterns, timetables, trips |
| S8 | `administration/test_watchlists_geofences.py` | Watchlist create / add / remove / rename / delete, Watch History row with actor and time; geofence create, deactivate, delete (archived: past alerts remain, absent from list). | API | P1 | disposable vehicles are only referenced, never modified |
| S9 | `administration/test_announcements_helpdesk.py` | Announcement window → status scheduled/active/expired (parametrize start/end), switched-off stays inactive, audience types, PDF optional; ticket status path and assignment records time and person. | API | P2 | helpdesk create/assign contract |
| S10 | `administration/test_untag_transfer_merge_flow.py` | Untag, ownership transfer, merge happy paths with post-conditions (report rows, old owner loses access, links released, device stays fitted). | UI+API | P0 | **blocked**: needs disposable permit holders, a vehicle with an installation, and FC / permit-holder creation path (see §7) |

Not recommended for automation: one test per screen element, per-field repeats of the same validation, per-permission UI copies of the API matrix, anything that waits on 5-minute / daily jobs.

---

## 5. Manual-only

| Scenario | Reason |
|---|---|
| 8-step installation (health, SOS press, 10-minute validation, 80 % / last 30 s) | Needs real packets and a physical SOS. |
| Live status rules, GPS-quality filtering, history packets, geofence entry / exit / no-parking timing | Needs controlled packet streams. |
| ERSS SOS flow and automatic SOS clear; command delivery states | Hardware, real devices. |
| Silent-device challan, SIM-expiry alert, COP reminder, announcement tick, parent notice | Time-based jobs (5 min / daily 09:00 / 7 days). |
| RTO approve / reject, challan approve / issue, repair and replacement | No RTO, inspector or FC credentials. |
| 90-day password expiry, admin-requested reset | Needs time travel or a reset endpoint. |
| The 9 unexercised staff permissions (FC and permit-holder status changes, challans approve/issue, reports export) | No safe record to act on. |

---

## 6. Needs clarification

1. Statuses and transitions of OEMs and staff (suspend, blacklist, reactivate, remarks): the guide defines none. Is a blacklisted account terminal?
2. Is "State Admin" the app's "Transport Commissioner (TC)" and "Super Admin" a separate login? Where does a State Admin read the audit log (config changes, inspector creation / transfer, sign-ins)?
3. RTO location check: guide says off by default; the environment shows `rto_vehicle_distance` enabled. Intended?
4. Account-merge report shows the source owner as `suspended`; guide says `Merged`. Defect or a different field?
5. Device Packets: "may be refused" for wide searches without IMEI — what is the exact limit?
6. Can a second State Admin login be provided to test "sees only records created by itself or its staff" (P0)? Can RTO, Inspector, FC logins be provided?
7. Which permit holders, vehicles and installations are disposable for transfer, merge and untag tests, and how may a permit holder be created (guide: FC creates them)?
8. Who changed system configuration on 2026-10-22 11:05 with the test admin account, and are those values the intended baseline?
9. Is TAC expiry reminder (guide: "saved for future use") in scope?

---

## 7. Dependencies

| Need | For | Status |
|---|---|---|
| `OEM_USERNAME` / `OEM_PASSWORD` | S2 | Present, works |
| Second State Admin, RTO, Inspector, FC, School logins | jurisdiction, challan, installation, merge-school | Missing |
| Write contracts (config, transfer, merge, untag, PIS patterns / timetables / trips) | S3, S4, S7, S10 | Discover from UI network calls; read-only to record |
| Disposable permit holders, vehicle with installation | S10 | Missing |
| A merged account | S3 | Exists (2 rows in report) |
| An installation linked to a device model and SIM | S5 | To verify |
| Cleanup | all | `utils/cleanup.py` removes models, firmware, SIM modules and deactivates staff only; created OEMs, inspectors, PIS records, announcements, tickets remain for the DB owner |

---

## 8. Implementation order

1. **Housekeeping on the four unverified files** (decide, then run once in a disposable window): remove the weak / duplicate tests in §3, move `admin_api` to `conftest.py`, drop or log BUG-034.
2. **S2** (OEM role, no data risk, P0).
3. **S1** (read-only reports).
4. **S3** (refusal tests on existing merged accounts).
5. **S4** (configuration; needs baseline answer to Q3 / Q8 and a restore guard).
6. **S5, S6** (extend existing files).
7. **S7, S8, S9** (disposable-data CRUD).
8. **S10 and all "blocked" rows** once §6 Q6–Q7 are answered.

---

## 9. Live exploration and guide trace (2026-10-23)

Walked all 48 pages of the State Admin menu with the `.env` admin login (read-only). Result: every page opens; only Help Centres misbehaves (BUG-036). Tracking pages still call `/api/school` and `/api/last-position` (404, BUG-020).

### Automated since this plan

| Guide area | Tests |
|---|---|
| s4 OEM role limits | `oem_management/test_oem_role_access.py` |
| s5 System Configuration | `administration/test_system_configuration.py` |
| s7.2 Merge refusals | `administration/test_account_merge_rules.py` |
| s9.1 Inspector transfer, first login, password, uniqueness, search / RTO filter | `test_inspector_transfer.py`, `test_user_creation_api_validation.py`, `test_state_admin_consistency.py` |
| s10 PIS layers | `administration/test_pis_schedule.py` |
| s8.5 / 8.6 Geofences, watchlists | `administration/test_watchlists_geofences.py` |
| s13 Announcements | `administration/test_announcements.py` |
| s12 Reports: SIM validity, packet limits, exports; device / alert counters | `test_state_admin_reports.py`, `test_report_exports_and_vehicle_search.py`, `test_state_admin_consistency.py` |
| s8.1 Online/offline vs last packet (checked 5 min / 1 min from the 3-minute boundary) | `test_state_admin_consistency.py` |
| Dashboard network totals = user lists (found: fleet owners + schools = permit holders) | `test_state_admin_consistency.py` |
| s6.4 / 7.1 Vehicle look-ups (read-only), incomplete transfer / untag refused | `test_report_exports_and_vehicle_search.py` |
| s9.3 Challan Master has the silent-device offence | `test_challan_master_and_help_centres.py` |
| Whole menu opens without failed calls | `tests/test_admin_panel_health.py` |

### Manual check (automation would change or depend on real data)

| Guide rule | Why manual |
|---|---|
| Ownership transfer and untag happy path; merge happy path | Irreversible; no disposable vehicle / permit holder. Refusals are automated. |
| Alert life cycle (acknowledge, close with remark, Close all) | 271 pending alerts are real; closing is irreversible. |
| Challan approve / issue (exact amount, remark), only drafted can be approved | 3 real challans; a wrong "accept" would change them. |
| ERSS SOS flow, auto SOS-clear; command Queued/Sent/Acknowledged | Needs a physical SOS and real devices. |
| Geofence entry / exit / no-parking timing; GPS jump / history-packet handling | Needs controlled packet streams. |
| 8-step installation, RTO approval, repair / replacement, SIM validity extension, device allocation | Need FC / RTO / OEM workflows and live devices. |
| Silent-device challan, SIM-expiry alert, COP reminder, announcement tick, parent notice | Time-based jobs. |
| Bulk uploads (drivers 500 rows, help centres, stops, devices 10,000) | Create data in bulk; limits not testable without it. |
| Helpdesk ticket flow | Creating tickets leaves undeletable records (probe declined). |
| Public portal (fitment centre search, QR verify, support, public transport) | Public URLs not found in the panel; needs the portal address. |
| Auto-sign-out across tabs, 90-day expiry, forced reset | Time travel / multi-tab. |

### New observations to clarify
- The automatic "not sending data" offence has a **penalty of 0.00**; the guide requires a paid amount to equal the fine exactly. Is a zero-fine challan intended?
- Dashboard shows 64 inspectors, all active; the Inspector list counter says 0 active (BUG-001).
