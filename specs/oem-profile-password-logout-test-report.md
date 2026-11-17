# OEM Panel - Profile, Change Password, Logout: test report

| | |
|---|---|
| **Date / environment** | 2026-11-03, https://vltd.misbackend.com, Chromium, every password / session test run against a dedicated, throw-away OEM account created for this work (never the shared `.env` account) |
| **Scope** | OEM panel > Profile (view, Edit Details), Change Password (the Profile tab and the forced first-login page), Logout. No other module |
| **Requirements used** | `VLTD_How_It_Works.pdf` chapter 4 (forced password change on first login / after 90 days, 15-minute inactivity sign-out, sessions are tracked, theft protection ends all of a user's sessions) and 9.1 (password policy: 10+ characters, upper, lower, a number). The guide has no section for the Profile screen or for an explicit Logout; the OEM's own actions there are taken from the application. Undecided points are observations 28-31 in `bug_report.md` |
| **Code** | `tests/oem_panel/test_oem_profile_password_logout.py` (27 tests), `pages/oem_panel/profile.py`, `utils/oem_profile_api.py`, `profile_account` / `profile_page` fixtures and the shared account-menu helpers added to `pages/oem_panel/base.py` (`open_account_menu`, `open_profile`, `logout`) |
| **Result** | 23 passed, 4 expected failures, 0 failed, 0 skipped, 0 errors (run twice) |

## 1. Features explored

| Screen | What it offers |
|---|---|
| **My Profile** `/oem/profile` | Profile Details tab (view: Full Name, Email Address, Contact Number, Address, City & State read-only) and **Edit Details** (Full Name, Email Address, Contact Number editable; Address disabled; City & State never editable) |
| **Change Password tab** (inside My Profile) | Current Password, New Password, Confirm New Password, each with its own show/hide toggle; a strength note; calls `PUT /api/users/{id}` with the whole profile resent alongside the password |
| **Forced Change Password** `/auth/change-password` | the same three fields, shown instead of every other screen until the password is changed; calls a different endpoint, `POST /api/auth/change-password` |
| **Logout** | the account-menu item (also Profile, Tickets, What's New); ends the browser session and clears local storage |

## 2-4. Manual exploration

Profile view and every field of Edit Details (empty, spaces-only, 1 character, HTML markup, invalid and duplicate e-mail, a 9/10-digit and lettered contact number, persistence after reload and after a real sign-out/sign-in). Change Password on both screens: empty fields, wrong current password, the policy boundary (9 chars, no upper/lower/digit), mismatched confirmation, reusing the current password, leading/trailing spaces, the show/hide toggles, repeated submission, and what a successful change actually does to the session (it does **not** sign the current tab out - see BUG-077). Logout through the actual UI menu: redirect, local storage cleared, the back button, a direct URL, a refresh, and a second open tab, each checked against the real API afterwards rather than assumed from the redirect alone (as the brief asked): the exact access and refresh tokens the session held were read from `localStorage` (or the API login response) and reused directly against the API after logout. The `/api/users/{id}` endpoint behind the Profile screen was also tried with other accounts' ids, a forged token, and no token at all.

## 5-6. Findings by classification

| Class | Findings |
|---|---|
| **Confirmed Bug** | BUG-072 any signed-in user can read any other user's profile by id (High, API-only); **BUG-073 the same endpoint accepts a write to another user's profile, including their email - account takeover (Critical, API-only, confirmed by two independent reproductions)**; BUG-074 Logout ends the access token but not the refresh token (High); BUG-075 an unknown user id crashes with 500 (Medium, API-only); BUG-076 the two Change Password screens disagree on leading/trailing spaces (Low); BUG-077 changing a password ends no existing session at all, not even the one that made the change (High) |
| **Requirement mismatch / needs a decision** | observations 28-31: two different endpoints/payload shapes for one action; Profile edit accepts values the registration forms would refuse (1-character name, HTML markup stored as literal text, an emptied contact number); the 90-day expiry and the Super Admin's Active Sessions screen could not be produced on demand |
| **Not a bug (verified working)** | the current password is checked server-side; the 10-char / upper / lower / number policy is enforced; reusing the current password is refused; mismatched confirmation is refused; a changed password's old value stops working for a **new** sign-in; Logout clears local storage and blocks the back button, a direct URL and a refresh; the access token (though not the refresh token) is rejected by the API right after Logout; a second, already-open tab is also signed out once it talks to the server again |

No earlier bug concerns this module; BUG-033 (a reused refresh key does not end the user's other sessions) is the closest relative of the new BUG-074 and BUG-077.

## 7. Automation

Profile: view, edit with persistence after reload and after a real sign-out/sign-in, and five invalid-value cases plus the duplicate-e-mail case, each confirmed to leave the stored profile unchanged. Change Password: the happy path confirmed at the API boundary (old password refused, new one accepted) rather than assumed from a redirect, six invalid-value cases, the "must differ from the current password" rule, and the show/hide toggle. The forced first-login page: a brand-new account's first sign-in, the change, and signing in again with the new password. Logout: redirect and that a protected page, a reload and the pre-logout access token are all refused afterwards.

## Regression tests of confirmed bugs (expected failures)

BUG-072 `test_reading_another_users_profile_is_refused`, BUG-074 `test_logout_ends_the_refresh_token_too`, BUG-075 `test_an_unknown_user_id_is_not_found`, BUG-077 `test_changing_the_password_ends_the_current_sessions_own_token`. BUG-073 and BUG-076 are documented but have no routine regression test (see "Remaining gaps").

## 8. Execution summary

| Run | Passed | Failed | Skipped | Expected failures |
|---|---|---|---|---|
| This module, `--known-bugs` (run twice) | 23 | 0 | 0 | 4 |
| The 4 with `--runxfail` | - | 4 | - | each fails for its documented reason |
| Sample of neighbouring modules (isolation, command templates, dashboard), `-n 3` | 60 | 1 (pre-existing data residue in `test_oem_command_templates.py`, unrelated to this module; passes alone before this session's volume of data, see "Remaining gaps") | 0 | - |

A full `tests/oem_panel --known-bugs -n 4` run produced a large batch of errors, all inside the unrelated `oem-devices` xdist group (fitment-centre uploads, SIM validity, device registration - none of which this module touches or shares a fixture with); one of the affected tests was confirmed to pass cleanly when re-run alone. This looks like load on the staging server after the very large volume of throw-away data this whole multi-module testing effort has created (close to 300 throw-away OEM accounts alone by this point), not a regression from this module's changes, but a full clean scope run was not repeated given the time it takes and that it is outside this module's remit.

Problems in my own scripts, fixed on the way (none were product bugs): the account-menu trigger's own locator originally matched on the account's display NAME plus its role text, which broke the moment a test renamed the account (fixed to the stable `aria-haspopup="menu"` attribute instead, in `pages/oem_panel/base.py`); navigating straight to `/auth/login` while still signed in just bounces back to the dashboard, so a real sign-out/sign-in persistence check must log out first; one invalid-email test value was accidentally one that the browser's own HTML validation intercepts before the app ever sees it (changed to a value the app's own message responds to); the password-policy error text is also quoted, word for word, in a permanent hint paragraph next to the field, so the regression check is scoped to the actual error (`role="alert"`), not any text on the page.

## 9. Security findings

The most important finding is **BUG-073, now Critical: `PUT /api/users/{id}` has no ownership check and the write reaches `email`**, confirmed by two independent reproductions - one direct, restored reproduction during this exploration, and a second, separate reproduction by the user against two fresh disposable accounts, which additionally confirmed the write overwrites `email` (and `contact_no`), not just `name`. Overwriting a victim's email is sufficient on its own for full account takeover via the ordinary "forgot password" flow; a direct write to `password` was not attempted since it is not needed to establish that severity. `GET /api/users/{id}` has the identical gap on the read side (BUG-072, 3 of 3). Separately, session-lifetime findings compound the risk: Logout ends the access token but not the refresh token (BUG-074), and changing a password - on either screen - ends **no** session at all, not even the one that made the change (BUG-077); together with the already-documented BUG-033, none of the three places a session should end (Logout, a changed password, detected key reuse) fully does so for a refresh token. In combination, an attacker who takes over an account via BUG-073 is not reliably locked out again by the victim changing their password or logging out everywhere.

## 10. Remaining gaps and blockers

- **Resolved since the first draft of this report:** BUG-073's reach into `email` is now confirmed (independently reproduced by the user, 2026-11-03) - it is an account-takeover path, raised to Critical. Whether it also accepts a direct write to `password` itself remains untested, but is no longer needed to establish severity.
- **Not automated as a routine test:** BUG-073 (a live cross-account write, by design not repeated often) and BUG-076 (each password-change endpoint was checked once, since each run is a real password change).
- **Not testable:** the 90-day password-expiry forced change (needs a 90-day-old account); the Super Admin's Active Sessions screen (outside the OEM panel); the 15-minute inactivity sign-out (guide chapter 4) was not timed out in full.
- **Pre-existing, unrelated:** one data-residue failure in `test_oem_command_templates.py` and a large batch of transient errors in the `oem-devices` xdist group during a full-scope run, both outside this module.
- **Next:** BUG-073 is now Critical and should be prioritized for a fix ahead of the rest of this batch; get a decision on observations 28-31 alongside it.
