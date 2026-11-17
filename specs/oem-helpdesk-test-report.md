# OEM Panel - Helpdesk: test report

| | |
|---|---|
| **Date / environment** | 2026-11-03, https://vltd.misbackend.com, Chromium, signed in as the OEM Admin from `.env` (a second throw-away OEM account for the isolation checks) |
| **Scope** | Helpdesk only: Support Tickets, Support Queue, New Ticket, ticket details, Change Status, Close Ticket. The public Support Center was used only to raise tickets that go to the OEM |
| **Requirements used** | `VLTD_How_It_Works.pdf` 19.1 (a ticket can be raised from a panel or the public portal; the reporter can route it straight to an OEM, otherwise the State Admin assigns it; Opened -> Assigned -> In_progress -> Completed -> Closed; every assignment and status change is recorded with time and person) and 20 (Support Center: description, 10-digit contact number, optional attachment, track by code). The guide says nothing else about the OEM's Helpdesk: the OEM's actions are taken from the application and undecided points are listed as observations 23-27 in `bug_report.md` |
| **Code** | `tests/oem_panel/test_oem_helpdesk.py` (22 UI tests), `tests/oem_panel/test_oem_helpdesk_api.py` (71 cases), `pages/oem_panel/helpdesk.py`, `utils/oem_helpdesk_api.py`, Helpdesk fixtures at the end of `tests/oem_panel/conftest.py` |
| **Result** | 84 passed, 0 failed, 0 skipped, 9 expected failures (2 min 30 s). The 9 expected failures fail for their documented reason with `--runxfail` |

## 1. Features discovered

| Screen | What it offers |
|---|---|
| **Support Tickets** `/oem/helpdesk` (also `/oem/helpdesk/my-tickets`) | the tickets the OEM raised (`GET /api/user/ticket`); Search (code, title, description), Status (Open, Assigned, In Progress, Completed, Closed), Priority (Normal, Priority), From / To date, Reset Filters, Refresh, counter, 10 a page with a pager, **New Ticket**; row actions *View Details*, *Close Ticket* (for the ticket's raiser) |
| **Support Queue** `/oem/helpdesk/assigned-tickets` | the tickets that are with the OEM plus the ones it raised (`GET /api/helpdesk/tickets`, with the activity log); the same filters; row actions *View Details*, *Change Status* (the owner, until the ticket is Completed or Closed), *Close Ticket* (the raiser, or the owner of an In Progress ticket) |
| **New Ticket** `/oem/helpdesk/create` | Ticket Reason (7 fixed reasons; "Other" adds a required Other Reason, 140 characters), Description (2,000 characters), Priority (Normal / Priority), Send To (Transport Department or any OEM), optional attachment; success page with the ticket code and who it went to |
| **Ticket details** (inside the list page) | Raised By, Assigned To, Status, Submitted Via, Priority, Raised On, Last Updated, Description, attachment link, **Activity** (Support Queue only) |
| **Change Status / Close Ticket** (forms inside the list page) | Status list (Open, In Progress, Completed) and an optional note (2,000 characters); Close Ticket asks "Close this ticket? ... This cannot be undone." with an optional note |
| Public Support Center `/support/create-ticket`, `/support/track-ticket` | used to raise test tickets routed straight to the OEM (`POST /api/public/ticket`: title, description, contact_no, priority, oem_id) |

## 2. Manual exploration

Both lists (columns, counter, empty / no-match / error / loading states, refresh), every filter alone and combined, search with codes in other case, titles, descriptions, spaces, `%`, `_`, quotes, markup and 300 characters, the date pickers and the API date filters, paging and invalid paging values, New Ticket (empty submit, Other reason, spaces, limits, every attachment kind, double click, Send To list), raising a ticket for the Transport Department, sending one to another OEM with Priority and an attachment, a public ticket routed to the OEM, the whole lifecycle through Change Status and Close Ticket, which actions each ticket offers to whom, status changes and closing through the API (invalid values, skipped and backward steps, final status), assignment, delete / edit, and access with another OEM's token, no token and a forged token. Evidence: `specs/evidence/oem-helpdesk/` (screenshots).

## 3. Findings by classification

| Class | Findings |
|---|---|
| **Confirmed Bug** | BUG-067 attachment link opens the portal (Medium); BUG-068 routed ticket has no activity record (Medium); BUG-069 server ignores the 2,000-character description limit (Low, API-only); BUG-070 `%` / `_` list every ticket (Low); BUG-071 "1 tickets" (Low) |
| **Requirement mismatch / needs a decision** | observations 23-27: backward ("Open") and skipped steps, close by the owner of an In Progress ticket, same-status answers (403 vs 200), no attachment type / size rule, an OEM can route to any OEM and the OEM list is public, no Activity under Support Tickets |
| **Environment / data issue** | none (the first, slow loads of the list are the app's own loading skeleton) |
| **Unable to confirm / not tested** | State Admin assignment and its side of the tickets, tickets raised by fitment centres or fleets, OEM staff access (BUG-039), the date-picker controls (the API date filters were tested) |
| **Intermittent (not a bug)** | `test_oem_access_and_isolation.py::test_new_oem_must_change_the_temporary_password` failed once in a parallel run of another module and passed alone and on a repeat (38 of 38): not related to Helpdesk |

## 4. Previously reported bugs

No earlier bug concerns the OEM Helpdesk. Observation 5 (TC staff without permission can read tickets) is a State Admin staff matter and was not re-run. BUG-057 (image served over http) looks like the same cause as BUG-067.

## 5. Validation of suspected issues

| Bug | Attempts |
|---|---|
| BUG-067 | the screen 2 of 2 (tab opens `/`, "VLTD Portal"); 7 of 7 attachment URLs (4 new, 3 older) answer the application shell (200 text/html, 12,878 bytes) |
| BUG-068 | 4 of 4 public tickets routed to the OEM have no created / assigned entry; the OEM-screen path records both |
| BUG-069 | 1 real request (created) + validation with 6 sizes (2,001 ... 70,000) without a description error |
| BUG-070 | 3 of 3 (screen once, API twice, both lists) |
| BUG-071 | every time a single ticket was listed |

## 6. Main happy-path automation

Lists and filters (Support Tickets / Support Queue content and row actions, details, search, status / priority filters with Reset, Refresh, pager, failure and empty states), raising a ticket through the form and checking what is stored, listing it, its activity and closing it (Cancel keeps it, Confirm closes it, a second close is refused), working a routed ticket to completion (Assigned -> In Progress -> Completed, notes, activity, persistence, final lock), the form's validation and limits and a double click, the API contract and filters, authorisation and OEM isolation.

## 7. Regression tests of confirmed bugs (expected failures)

BUG-067 `test_the_attachment_link_opens_the_attached_file`, BUG-068 `test_the_assignment_of_a_routed_ticket_is_recorded`, BUG-069 `test_a_description_over_2000_characters_is_refused` (2 sizes), BUG-070 `test_a_wildcard_character_is_searched_for_literally` (4 cases), BUG-071 `test_the_counter_says_ticket_for_a_single_ticket`.

## 8. Execution summary

| Run | Passed | Failed | Skipped | Expected failures |
|---|---|---|---|---|
| Helpdesk UI + API, `--known-bugs` | 84 | 0 | 0 | 9 |
| Helpdesk, default (known-defect tests not run) | 84 | 0 | 0 | 9 deselected |
| The 9 with `--runxfail` | - | 9 | - | each fails for its documented reason |
| Neighbouring modules (access and isolation, command templates), `-n 2` | 37 then 38 | 1 intermittent, then 0 | 0 | 0 |

Problems in my own scripts, fixed on the way (none were product bugs): the labels of the details are shown in capitals by CSS (read with `text_content`), the empty and error texts exist twice in the DOM (scoped to the table), Cancel on Close Ticket returns to the ticket's details (not the list), and the attachment test must wait for the app's redirect to settle before it reads the tab's URL (it passed by mistake the first time).

## 9. Remaining gaps and blockers

- **Residue:** tickets cannot be deleted. The manual exploration left 8 tickets labelled AUTO / QA probe; the tests keep three shared tickets (`AUTO HD shared ...`, reused every run) and add two new ones per run; a few more came from failed development runs.
- **Not covered:** the State Admin's side (assigning a ticket to an OEM, its own view), tickets with a staff owner (BUG-039), the custom date pickers (API filters tested), real attachment downloads (blocked by BUG-067), and the upper size limit of attachments (6 MB accepted; no larger file was sent).
- **Decisions needed:** observations 23-27 in `bug_report.md`.
- **Next:** after BUG-067 and BUG-068 are fixed, re-run their two tests; once the attachment rules are decided, add the file-type and size tests.
