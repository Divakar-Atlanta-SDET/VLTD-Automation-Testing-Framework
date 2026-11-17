# OEM Panel - Management > User Management > Staff: test report

| | |
|---|---|
| **Date / environment** | 2026-10-31, https://vltd.misbackend.com, Chromium, signed in as the OEM Admin from `.env` |
| **Scope** | OEM panel > Management > User Management > Staff (`/oem/users/staff`) only |
| **Requirements used** | `VLTD_How_It_Works.pdf` has **no section on OEM staff**; the product owner confirmed earlier that the OEM manages its own staff. Everything else is taken from the screens and listed as unclear in `bug_report.md` (observations 18 and 19) |
| **Code** | `pages/oem_panel/staff.py`, `tests/oem_panel/test_oem_staff_form.py` (30 tests), the three older tests of `tests/oem_panel/test_oem_staff_management.py` |
| **Headline** | **The module is blocked by BUG-039** (re-verified through the screen today): the OEM Admin cannot list or register staff (`/api/oem/users` answers 403). Most of the requested scenarios cannot be executed until it is fixed. |

## 1. Staff functionality discovered

| Function | State |
|---|---|
| Staff list | Opens; counters (Total / Active / Suspended / Blacklisted), search, status filter (All Statuses / **Approved** / Suspended / Blacklisted), Apply Filters, Clear, Refresh, columns Staff, Role, Created on, Updated on, Last login, Status, Actions. The data request answers **403**, so the page shows 0 everywhere and "No Staff found" (BUG-039, BUG-059). **No row has ever been seen.** |
| Register Staff | Opens and works up to the server: name (100), e-mail (255), 10-digit mobile (6-9 first digit), 41 permissions in 16 collapsible groups (Select All, Clear All, a box per group, search), password (255) and confirmation (100); the request `POST /api/oem/users {name, email, contact_no, password, password_confirmation, permission_ids}` answers **403 "You do not have permission to perform this action."** |
| View details | `/oem/users/staff/{id}`; for an unknown id "OEM Staff details not found."; a real record could not be opened |
| Edit | `/oem/users/staff/{id}/edit` exists (empty form for an unknown id); not reachable for a real record |
| Activate / suspend / blacklist / delete, roles, staff login | Not observable: no staff member can exist. The status filter shows that the statuses are Approved (Active), Suspended and Blacklisted |

## 2. Manual scenarios executed

Staff list as the OEM Admin (counters, filter options, Apply, Clear, Refresh, requests sent); the Register form (empty submit, no permission, spaces-only name, one-character and digit names, invalid e-mail, 9-digit / 5-first-digit / lettered mobile numbers, four password-policy failures, mismatch, the permission picker, Cancel, a valid submit with the request captured and aborted, and one real valid submit that answered 403); unknown-id details and edit pages; `GET /api/oem/users`, `POST /api/oem/users`, `GET /api/oem/permissions` and the OEM Admin's permissions; read-only probes of neighbouring routes. State Admin > Users > Staff for BUG-007. Evidence: `specs/evidence/oem-staff/` (list.png, list-after-403.png, register-form.png, register-empty-errors.png, register-403.png, tc-staff-list-bug007.png). **No staff account was created.**

## 3. Previously reported Staff bugs

| Bug | Status 2026-10-31 |
|---|---|
| BUG-039 OEM cannot list or register its staff | **Reproducible** through the screen and the API; backend observation added (no staff permission in the 41-permission catalogue) |
| BUG-007 "Approved" vs "Active" | **Reproducible**: State Admin Staff counter ACTIVE 37, filter and rows "Approved"; the OEM Staff page has the same counter / filter wording |
| BUG-014 to BUG-017, BUG-034 | State Admin **TC staff** permissions (another submodule); not re-run. Unable to verify today |

## 4. Happy-path tests

The six requested happy paths (create, view, edit, status, search, role / permission assignment) cannot pass today. Only the registration has a visible screen, so it is the one blocked happy path that is written:

| Test | State |
|---|---|
| `test_register_a_staff_member` | **expected failure (BUG-039)**: fills the form, expects 201, the redirect to the list and the new e-mail in `GET /api/oem/users?search=`. It will create one staff account per run once the bug is fixed |
| view, edit, status change, search, permission assignment | **not written**: their screens have never been seen, and tests built on guessed selectors would be worthless. Listed as the first work after BUG-039 is fixed |

## 5. Other tests added (all pass; nothing can be created)

- **Permission picker:** the 16 groups and 41 permissions equal `/api/oem/permissions` by id and name; Select All / Clear All / group box / single box move the counter; the search narrows the groups, keeps the selection and reports "No permissions found"; the request carries exactly the selected permission ids.
- **Validation (screen):** empty form lists five required messages; nine invalid values (e-mail, mobile, four password-policy cases) each name the field; mismatched passwords; passwords masked and length limits (100 / 255 / 10); Cancel returns to the list; **in every case no request is sent** (the request is intercepted and aborted).
- **API / access:** the list, registration and permission endpoints answer 401 without a token or with a malformed one; the OEM Admin holds all 41 permissions of the catalogue and none concerns staff (the test will tell when one is added).
- **Pages:** unknown staff id.

## 6. New defects

| Bug | Severity | Kind | Summary | Test |
|---|---|---|---|---|
| BUG-059 | Medium | Screen | A staff list that failed to load is shown as "No Staff found. Register a Staff member to get started." with 0 counters and no error | `test_a_failed_staff_list_is_reported_as_an_error` (403 and 500, expected failures) |
| BUG-060 | Low | Screen | The form sends a staff name of spaces only | `test_a_staff_name_of_spaces_is_refused` (expected failure) |

## 7. Execution summary

| Run | Passed | Failed | Skipped | Expected failures |
|---|---|---|---|---|
| Staff modules (new + older), `--known-bugs` | 25 | 0 | 0 | 8 |
| The 8 expected failures with `--runxfail` | - | 8 | - | each fails for its documented reason (403, empty state shown, name sent, "Approved") |
| OEM scope with `--known-bugs`, `-n 4` (project `.venv`) | 333 | 0 | 0 | 43 |

Script problems fixed on the way: a role-name regex containing `/` is not accepted by Playwright's selector engine; the permission groups are an accordion (one open at a time), so permissions are read group by group, waiting for the previous group to close.

## 8. Blockers, unclear requirements, gaps and next steps

- **Blocker (BUG-039):** nothing that needs an existing OEM staff member can be tested: view, edit, search, filters, sorting, paging, activate / suspend / blacklist, role and permission access of a staff login, access to other OEMs' data, session behaviour after a status change, XSS in stored fields, duplicate e-mail / mobile, server-side validation with client checks bypassed (the 403 answers before validation), idempotency and audit history. Not tested for the same reason: the response schema of the list.
- **Unclear requirements:** OEM staff is absent from the guide: roles a staff member gets, whether at least one permission is required, what each status does, whether a name of spaces is valid (BUG-060 assumes not), why the confirmation field stops at 100 characters while the password takes 255.
- **Next steps:** fix BUG-039 (add the missing staff permission or grant the existing check to the OEM Admin) and BUG-059; then explore the list, the details and edit pages and the status actions against real records, write the happy paths for create, view, edit, status change, search and permission assignment, and add the isolation tests with a second OEM (the helper `create_oem_account` already exists). Until then, continue with the next submodule only when asked.
