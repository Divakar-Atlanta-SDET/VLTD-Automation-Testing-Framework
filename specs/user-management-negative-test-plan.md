# User Management – Negative / Input-Validation Test Plan

Scope: the five create forms of `/tc/users/*` – **OEM, RTO, Inspector, Driver, TC Staff** (Fitment Center and Permit
Holder have no create action for Admin). Companion to `user-management-create-test-plan.md` (happy path).
Explored 2026-10-13. The network tab is monitored in every test (`utils/network_monitor.py`).

## 1. What is checked in every negative case

1. The create form **stays open** – nothing was created.
2. The user sees **at least one validation message** (and, where the wording is known, the right one).
3. **No create request succeeded.** Either the browser blocked it (no request at all) or the server answered 4xx.
4. The server **never answered 5xx** and the body **never leaks** a stack trace, SQL, vendor path or `.php` name.
5. Messages never contain `NaN`, `undefined`, `null` or `[object Object]`.

How the app reports errors (found during exploration), and how the tests read them:

| Source | Example | Read by |
|---|---|---|
| Banner / field `role=alert` | "Business Name is required", "Validation failed." | `[role=alert]` |
| Red text under a field | "GST Certificate is required", "The password field format is invalid." | `p[class*=text-red]` |
| Browser-native validation | "Please include an '@' in the email address" | `input:invalid` → `validationMessage` |
| Toast when a file is chosen | "File size must not exceed 5 MiB." | collected right after filling |

## 2. UI scenarios (`tests/administration/test_user_creation_negative.py`)

| Form | Invalid input covered |
|---|---|
| **OEM** | blank/space-only business name, OEM code, TAC, COP, address, contact name · CIN too short / bad characters · GST too short / bad characters · pincode 5 digits / letters · mobile 9 digits / letters · email without `@` / without domain · weak passwords (too short, no upper, no lower, no number) · password mismatch · no certificates · certificate not a PDF · certificate over 2 MB · no dates · empty form |
| **RTO** | blank name/code/address · code letters-only / one digit / wrong prefix (`XX-12`) · mobile 9 digits / letters · email invalid · district not chosen · pincode 5 digits / letters · map location not pinned · weak passwords · mismatch · empty form |
| **Inspector** | blank name/email · email without `@` · mobile 9 digits / letters · city not chosen · RTO not chosen · weak passwords · mismatch · empty form |
| **Driver** | blank name/email/mobile/licence · email invalid · mobile 9 digits / letters · licence wrong format / too short · weak passwords · mismatch · licence file missing / over 5 MiB · photo missing / a PDF / a text file / over 5 MiB · empty form |
| **TC Staff** | blank name/email/mobile · email invalid · mobile 9 digits / letters · weak passwords · mismatch · empty form |

Additional UI tests:
- **Duplicates** – OEM code, OEM contact email, RTO code, Inspector email, Driver email, Driver licence number, Staff email
  are each rejected by the server, and the list still shows exactly one record with that value (original unchanged).
- **Script injection** – `<script>alert(1)</script>` in an Inspector / Staff name is rejected or stored as inert text;
  no JavaScript dialog fires and no `<script>` element is rendered.
- **COP dates** – a "valid till" earlier than "valid from" cannot be selected in the date picker.
- **Maximum length** – typing past each field's limit is cut off (17 fields, limits read from the forms' `maxlength`).

Not tested as "invalid": Driver *State/City* (optional in the form).

## 3. Server-side scenarios (`tests/administration/test_user_creation_api_validation.py`)

The browser limits input (`maxlength`, required, formats), so over-long values and wrong types can never reach the server
through the UI. These tests send the request directly with the admin's token to prove the **server** enforces the rules.
One field of an otherwise valid body is changed per case; the answer must be **422** with an `errors` entry for that field.

- **Inspector** (`POST /api/transport-commissioner/inspectors`): blank/missing/300-char name, bad/300-char email,
  contact 9 digits / letters / 11 digits, weak passwords, mismatched confirmation, unknown or wrong-type `city_id`,
  empty or unknown `rto_ids`.
- **RTO** (`…/rtos`): blank / letters-only / 3-digit / wrong-prefix code, blank or 300-char name, bad contact,
  bad email, blank address, pincode 5 / 7 digits / letters, latitude/longitude out of range or not numeric,
  unknown city, weak passwords, mismatch.
- **Staff** (`…/staff`): blank / 300-char name, bad email, bad contact, weak passwords, mismatch, unknown permission.
- **Authentication** – every create endpoint (inspectors, rtos, staff, oems, drivers) answers 401/403 with no token,
  a malformed token and an empty bearer token; it must not reach validation (422) or fail (5xx).
- **Error shape** – an empty body returns 422 with a non-empty message list per required field and no leaked internals.

OEM and Driver bodies are multipart (file uploads), so they are covered through the UI only.

## 4. Known defects found by this plan (see `bug_report.md`)

| Case | Result |
|---|---|
| Inspector API, mismatched `password_confirmation` | **201 Created** – confirmation not validated (BUG-012). Case is skipped by default (it creates a record each run); run with `pytest --runxfail -k password-mismatch`. |
| Inspector API, `city_id: "abc"` | **500** "Something went wrong" instead of 422 (BUG-013). Runs on every execution and is reported as an expected failure. |

## 5. Test data and cleanup

Negative tests create nothing when the application behaves correctly. If a defect lets a record through, it carries the
usual `Auto…` name and `auto.<type>.<timestamp>@example.com` email so the DB owner can find it.
