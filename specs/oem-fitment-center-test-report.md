# OEM Panel - Management > User Management > Fitment Center: test report

| | |
|---|---|
| **Date / environment** | 2026-10-31, https://vltd.misbackend.com, Chromium, signed in as the OEM Admin from `.env` |
| **Scope** | Register FC, Edit FC, Suspend, Blacklist, Activate, Search, list filters, **paging, sorting, image and GST-certificate uploads**, details page, status history; nothing outside this submodule |
| **Requirements used** | `VLTD_How_It_Works.pdf` (chapter 3 definitions, 6.1 allocation to *active* centres). **The guide does not describe how a centre is registered, suspended, activated or blacklisted**; those rules were taken from the screens and are listed as open questions in `bug_report.md` (observation 13) |
| **Code** | `pages/oem_panel/fitment_centers.py`, `tests/oem_panel/test_oem_fitment_center_lifecycle.py` (85 tests) and `test_oem_fitment_center_paging_and_uploads.py` (60 tests), helpers in `utils/oem_panel_api.py` and `utils/file_utils.py`, shared `lifecycle` fixture in `tests/oem_panel/conftest.py` |
| **Result** | whole OEM scope with `--known-bugs`: **308 passed, 38 expected failures, 0 failed, 0 skipped** (13 min 27 s, `-n 4`, project `.venv`) |
| **Product decisions (2026-10-31)** | Blacklisted is **final** (suspended can be reactivated); the server must **enforce the rules the forms imply** |

## 1. What the screens do (explored manually before any test)

| Function | Observed behaviour |
|---|---|
| List `/oem/users/fitment-centers` | Counters (Total / Active / Suspended / Blacklisted), search box, RTO / City / Status filters with **Apply Filters**, Clear, Refresh; 10 rows a page; a row menu with **View details** and **Edit FC** (Edit is missing for a blacklisted centre) |
| Register FC `/new` | Business name (150), Fitment code (20), Owner (150), GST (15, optional, needs a PDF certificate), Contact and alternate contact (10 digits), Email (150, becomes the centre's login), City, RTO, Address 1 / 2 (500), Pincode (6), a pinned map point, an image (JPG/PNG/WEBP, 5 MB, 300-4096 px), password (min 10, upper, lower, number) + confirmation. Success: `POST /api/oem/fitment-centres` 201, back to the list, the centre is **Active** and can sign in |
| Edit FC `/{id}/edit` | Same form, stored values filled in, image optional; `POST /api/oem/fitment-centres/{id}` 200; works for Active and Suspended centres |
| Details `/{id}` | Header with status badge, Last updated, buttons by status: Active -> Suspend, Blacklist; Suspended -> Activate, Blacklist; Blacklisted -> none ("No further status actions are available."); full record; Remarks History |
| Suspend / Activate / Blacklist | A box with **mandatory remarks** (confirm stays disabled for empty or spaces-only text); Blacklist warns "This action cannot be reversed."; requests `PATCH /{id}/deactivate | activate | blacklist {"remarks"}`; the remark is stored with the actor and time |
| Search | Name, code, e-mail, mobile, owner; ignores case and surrounding spaces; runs on **Apply Filters**; empty result: "No matching Fitment Centers found." |

Differences found between the statuses: a suspended centre can still be edited, activated or blacklisted; a blacklisted one shows nothing. Both lose their login (403 "Your account is not approved or active.") and both disappear from the allocation wizard.

## 2. Manual scenarios executed (own test centres only)

Register (empty form, every invalid format, spaces, lengths, real registration through the form and through the API); edit (prefilled values, empty and invalid values, spaces-only name, a duplicate fitment code, a real edit and restore); suspend, activate and blacklist (cancel, empty remarks, with remarks, double click on confirm, mocked 500, expired session, markup in remarks, direct URL of unknown and foreign ids); search (name, code, e-mail, mobile, owner, upper case, padded with spaces, no match, `%`, markup and SQL text); filters; the API for each endpoint (no token, bad token, missing / blank / over-long remarks, unknown id, foreign id, repeated and reversed transitions, over-long and malformed registration values, duplicate e-mail and mobile); the centre's own login while Active, Suspended and Blacklisted; allocation of stock to a suspended centre; a second OEM acting on this OEM's centres. Evidence: `specs/evidence/oem-fitment-centers/` (25 screenshots).

## 3. The six happy-path tests

| Function | Test | Checks |
|---|---|---|
| Create | `test_register_a_fitment_center` | fills the whole form (pinned map point, image), 201 and message, back on the list, stored record equals the input incl. the pinned coordinates, status Active, counter +1, listed after a fresh load, the centre's login works |
| Edit | `test_edit_a_fitment_center` | stored values prefilled, owner and address line 2 changed, 200, API and details page show the change after a reload, nothing else moved |
| Suspend | `test_suspend_a_fitment_center` | remarks, 200, badge Suspended, buttons Activate + Blacklist, remark in the history (API and screen), persists after reload, list row and row menu, the centre's login refused |
| Blacklist | `test_blacklist_a_fitment_center` | warning text, Cancel keeps it active, remarks, badge Blacklisted, "No further status actions", no buttons, row menu only View details, history, login refused |
| Activate | `test_activate_a_suspended_fitment_center` | suspended by API, activated on screen with remarks, Suspend + Blacklist buttons back, history, persists, login works again |
| Search | `test_search_finds_the_fitment_center` | by code: exactly one row and one request with `search=`; clearing brings the full first page back |

## 4. Other tests added

- **Search / filters:** name in capitals, name padded with spaces, e-mail, mobile, code in lower case (5); no match for unknown text, markup and SQL text (3); status filter Active / Suspended (1).
- **Form validation (screen):** empty registration lists all 13 required messages and sends nothing; seven invalid values (contact, alternate contact, e-mail, pincode, GST, weak password, mismatched password) each name the field and send nothing; edit with empty / spaces-only fields is refused and changes nothing; field length limits.
- **Status boxes:** remarks mandatory and Cancel changes nothing; a double click on confirm sends one request and adds one history entry; markup in a remark is shown as text and does not run; a 500 is reported and the status stays; an expired session goes to sign-in and changes nothing.
- **Server (API):** 13 invalid registration values (lengths, GST, contacts, pincode, coordinates, spaces-only name) and duplicate e-mail / mobile are refused with 422 and create nothing; remarks missing, empty, spaces-only or 1,001 characters are refused for suspend / activate / blacklist; the four endpoint families need a valid login (no token and a malformed token: 401); a suspended centre cannot sign in.
- **Isolation:** another OEM's list and search are empty, its GET is 404, and the screen says "Fitment Center details not found." for a foreign id.

## 5. Existing bugs re-verified

| Bug | Result on 2026-10-31 |
|---|---|
| BUG-041 allocation to a blacklisted centre | still reproduces (expected failure) |
| BUG-042 duplicate fitment code | still reproduces, **now also through the Edit screen** (200) |
| BUG-047 / 048 / 049 / 050 and the other OEM bugs | unchanged (all 26 expected failures still fail for their documented reason; no unexpected pass) |

## 6. New defects (all in `bug_report.md`)

| Bug | Severity | Kind | Summary | Regression test |
|---|---|---|---|---|
| BUG-051 | High | **API-only** | Another OEM can suspend, activate and blacklist a centre it does not own (200) | `test_another_oem_cannot_change_the_status_of_a_centre_it_does_not_own` (2) |
| BUG-052 | Medium | **API-only** | Editing another OEM's centre answers 500 and shows an internal class name | `test_editing_a_centre_of_another_oem_is_refused_like_a_missing_one` |
| BUG-053 | Medium | API-only (+ edit URL opens) | A blacklisted centre can be activated, suspended and edited | `test_a_blacklisted_centre_stays_blacklisted` |
| BUG-054 | Low | **API-only** | The status a centre already has can be set again (history entry added) | `test_a_status_the_centre_already_has_cannot_be_set_again` (2) |
| BUG-055 | High | **API-only** | Stock can be allocated to a suspended centre (201) | `test_stock_cannot_be_allocated_to_a_suspended_fitment_center` |
| BUG-056 | Low | Screen | Remarks History shows UTC, the rest of the page local time | `test_the_remarks_history_time_matches_the_last_updated_time` |

API-only findings are labelled as such: the screen never offers those actions, so they are not presented as UI bugs.

## 7. Execution summary

| Run | Passed | Failed | Skipped | Expected failures |
|---|---|---|---|---|
| Lifecycle module, default | 65 | 0 | 0 | 20 deselected |
| Lifecycle module with `--known-bugs` | 65 | 0 | 0 | 20 |
| Paging and uploads module with `--known-bugs` | 59 | 0 | 0 | 1 |
| Nine expected-failure tests with `--runxfail` | 1 (a matching test) | 9 | 0 | - |
| OEM scope with `--known-bugs`, `-n 4` (`.venv`) | 308 | 0 | 0 | 38 |
| Isolation module after the fix of the skip | 30 | 0 | 0 | - |

Script problems found and fixed on the way (none were product bugs): the list searches only on **Apply Filters**; dropdown options of the previous select linger while the next one opens; the coordinates text has leading spaces; history entries written in the same second come back in no fixed order, so tests match entries by their text; the existing isolation test read only the first page of the lists.

## 8. Blockers, coverage gaps and next steps

- **Cannot be cleaned up:** centres and their login accounts and OEM accounts cannot be deleted by the application. This run left the long-lived "AUTO PG FC lifecycle" centre (kept Active and reused), several `AUTO PG FC <timestamp>` centres (blacklisted or active, harmless) and several throw-away `AUTO OEM` accounts (one per run of the isolation tests, plus one from the manual probe). A DB owner can remove them (`AUTO PG FC*`, `auto.fc.*@example.com`, `AUTO OEM *`).
- **Not covered:** what a centre can do after signing in (Fitment Center panel), OEM staff with and without fitment permissions, a valid-size real JPEG or WEBP (no image library is installed; a 1 x 1 file proves only the type), and sorting on the screen (the headers are not sortable).
- **Decisions needed:** owner name, fitment-code characters and pincode `000000` have no rule on the screens (observation 16); whether the form should keep a previously chosen valid image after a rejected pick.
- **Next:** continue with the next submodule only when asked.

## 9. Paging, sorting and uploads (second pass, 2026-10-31)

**Paging and sorting.** The list shows 10 centres a page (no page-size control) with First / Previous / Go to page N / Next / Last and "Showing a to b of n results"; the page number is not in the URL (reload returns to page 1); a filter returns to page 1. The column headers are not sortable on the screen: the list is always newest first. The API sorts by `created_at`, `updated_at`, `short_name`, `owner_name` (asc / desc); other fields and directions answer 422.

| Test | Checks |
|---|---|
| `test_the_pager_walks_through_every_centre` | summary text on every page, First / Previous disabled on page 1, Next / Last disabled on the last page, every centre exactly once, First / Last / numbered buttons |
| `test_the_list_shows_the_newest_centre_first` | the screen's order equals the API default |
| `test_applying_a_filter_goes_back_to_the_first_page` | from page 2 a status filter shows page 1 of that status |
| `test_every_centre_is_on_exactly_one_page` (3 page sizes) | meta (current page, last page, from, to, total), no centre missing or twice |
| `test_a_page_beyond_the_last_is_empty`, `test_the_server_refuses_invalid_paging_and_sorting` (6) | empty page; 422 for per_page 0 / 101 / text, an unknown sort field, a wrong direction |
| `test_the_api_sorts_in_the_requested_direction` (8), `test_sorting_and_a_filter_work_together` | the four sort fields in both directions; sort + status filter |

**Uploads.** Image: JPG, PNG or WEBP, up to 5 MB, 300-4096 px a side. GST certificate: PDF, up to 2 MB, required when a GST number is entered. Only generated, harmless files: text, HTML, empty and tiny files, solid or random-pixel PNGs, padded files. A request that tests the server always carries a deliberately wrong pincode, so even a server that skipped a rule could not create or change a centre; the test looks for the error on the file field, and a control request with a good file shows that the file field is then not reported.

| Layer | Result |
|---|---|
| Screen, image (12 refusals + 2 accepted) | 299 px, 4097 px, 300 x 5000, a text / empty / HTML file called `.png`, a `.txt`, PDF, GIF, SVG, a PNG called `.png.exe`, a 6 MB file: each shows its message and **sends nothing**; 300 x 300 and a non-square image are accepted |
| Screen, certificate (4) | missing certificate with a GST number, a text file, an image, a 3 MB PDF: each message shown, nothing sent |
| Server, image (9 + control + JPEG / WEBP) | text, empty, HTML, SVG, GIF, PDF, 299 px, 4097 px and a real 6.4 MB PNG are refused on **registration and edit**; JPEG and WEBP are accepted as types |
| Server, certificate (6 + 2) | text, empty, HTML, image, text file and a 3 MB file refused on both endpoints; a GST number without a certificate refused; a real PDF accepted |

Not a defect, noted: the server judges the **content** (a real PNG called `.txt` or `.png.exe` is accepted; a stored name cannot be seen without creating a centre), and after a rejected pick the form keeps showing and submitting the earlier valid file (confirm it is intended).

**Rules the forms imply (product decision).** Compared client and server value by value: the server enforces length, GST format, duplicate e-mail and mobile and the file rules, but not the mobile format (starts 6-9), the e-mail domain suffix or the 100-character password limit: **BUG-058** (11 values, registration and edit, API-only). The fitment code uniqueness is BUG-042.

**New defects:**

| Bug | Severity | Kind | Summary | Test |
|---|---|---|---|---|
| BUG-057 | Medium | Screen | The premises image is never shown: the API sends `http://<ip>:8087/...`, the https page blocks it (mixed content), "Image unavailable" for every centre | `test_the_premises_image_is_shown_on_the_details_page` |
| BUG-058 | Medium | **API-only** | Server accepts mobile numbers starting 0-5, e-mails without a domain suffix and passwords over 100 characters that the forms refuse | `test_the_server_enforces_the_contact_and_password_rules_of_the_registration_form` (6), `..._of_the_edit_form` (5) |

BUG-053 is now confirmed by the product owner (blacklisted is final).

Script problems fixed on the way: the pager summary text has no fixed spacing (matched with `\s+`); the oversized-image tests needed a real 6.4 MB PNG of random pixels because a padded file is reported as "not an image" before its size is checked.
