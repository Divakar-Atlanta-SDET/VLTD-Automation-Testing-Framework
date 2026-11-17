# VLTD UI/UX & Accessibility Bug Report

Separate from `bug_report.md` (functional defects). This file tracks visual-consistency, usability,
and WCAG 2.2 AA accessibility findings only, found during the UI/UX audit starting 2026-11-12.

Bug IDs use the `UX-NNN` prefix (never reuse `BUG-NNN`, which is the functional report's numbering).
Each entry must state how it was verified (manual repro count, viewport(s), automated scan or not) and
its classification: Confirmed UI Bug / Confirmed Accessibility Violation / UX Improvement / Intermittent
Issue / Unable to Confirm. See `specs/ui-ux-audit-plan.md` for the page inventory and batching plan this
report is organized against.

Screenshot evidence lives under `specs/evidence/ui-ux/<batch>/<UX-ID>.png`.

## Summary table

| ID | Category | Module | Severity | Priority | Status |
|---|---|---|---|---|---|
| UX-001 | Accessibility | Admin + OEM + FC + RTO + Inspector Dashboard, and FC Device Models "Inventory Summary" | Medium | Medium | Confirmed Accessibility Violation |
| UX-002 | Accessibility | Admin Live Tracking / Trip Playback / Geofences (Admin-only, checked and ruled out on OEM, FC and RTO) | High | High | Confirmed Accessibility Violation |
| UX-003 | Accessibility | Admin + OEM + FC + RTO Live Tracking | High | High | Confirmed Accessibility Violation |
| UX-004 | UI | Admin Dashboard | Medium | Medium | Confirmed UI Bug |
| UX-005 | UX | Admin + FC + RTO Live Tracking / Alerts / ERSS | Low | Low | UX Improvement (needs product decision) |
| UX-006 | Accessibility | Admin User Management forms + OEM's Register FC/Staff forms + FC/RTO/Inspector/Driver Change Password forms (all 6 roles) | High | High | Confirmed Accessibility Violation |
| UX-007 | UI | Admin User Management (Add Driver form) | Low | Low | Confirmed UI Bug |
| UX-008 | UX | Admin User Management (Add Inspector / Add Driver) | Low | Low | UX Improvement |
| UX-009 | UI | Admin PIS Management (Routes/Timetables/Stops/Service Calendars/Service Patterns/Trips) | Low | Low | Confirmed UI Bug |
| UX-010 | Accessibility | Admin (8 of 14 reports) + OEM (5 of 12) + FC (4 of 11 + Installation History) + RTO (4 of 13 + Approval History) | High | High | Confirmed Accessibility Violation |
| UX-011 | Accessibility | Admin + OEM + FC + RTO Reports — Device Packets | Medium | Medium | Confirmed Accessibility Violation |
| UX-012 | Accessibility | Admin Reports — Multiple-Challan Vehicles | High | High | Confirmed Accessibility Violation |
| UX-013 | Accessibility | Admin + OEM + FC + RTO Reports — Installation Status / Installation Report / Device Installations / Device Health / Device Packets | Low | Low | Confirmed Accessibility Violation |
| UX-014 | UI | Admin Reports (8 of 14 report pages) | Low | Low | Confirmed UI Bug |
| UX-015 | Accessibility | OEM Audit — Ticket Performance Report | Medium | Medium | Confirmed Accessibility Violation |
| UX-016 | Accessibility | RTO Inspector — Draft Challan (evidence upload) | Medium | Medium | Confirmed Accessibility Violation |
| UX-017 | Accessibility | RTO Inspector Draft Challan + Driver Dashboard (icon-prefixed info lists) | Low | Low | Confirmed Accessibility Violation |

## Bug details

### UX-001 - Dashboard trend charts have no accessible text alternative (Medium)

- **Category:** Accessibility
- **Module / Page:** TC/Admin Dashboard — `/tc/dashboard`; **also confirmed on the OEM Dashboard `/oem/dashboard`** (3 chart canvases, same `role-img-alt` violation) during Batch 5 (2026-11-12); **also confirmed on the FC Dashboard `/fc/dashboard`** (2 chart canvases) and, as a new page type for this same defect, **FC's Device Models "Inventory Summary" view `/fc/device-models`** (1 chart canvas) during Batch 7 (2026-11-12); **also confirmed on the RTO Dashboard `/rto/dashboard`** (1 chart canvas) and the **Inspector Dashboard `/inspector/dashboard`** (1 chart canvas) during Batch 8 (2026-11-12) — all the same shared chart component rendering a `role="img"` canvas with no accessible name, not separate bugs. This now reproduces on every one of the 6 testable roles.
- **Element:** 4 chart canvases on Admin (Fitment Trend, Alert Trend, Challan Trend, Vehicle Mix donut) / 3 on OEM / 2 on FC Dashboard / 1 on FC's Device Models "Inventory Summary", each `<canvas role="img">`
- **Description:** Each chart canvas is marked `role="img"` but has no `alt` or `aria-label`, so a screen reader announces nothing meaningful for it.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open the Dashboard. 3. Inspect any of the 4 chart canvases via a screen reader or the DOM/accessibility tree.
- **Actual result:** Canvas exposes `role="img"` with an empty accessible name.
- **Expected result:** Each chart should have a text alternative (e.g. `aria-label` summarizing the trend, or a visually-hidden data table/summary).
- **WCAG criterion:** 1.1.1 Non-text Content
- **Severity / Priority:** Medium / Medium — data is partially duplicated in adjacent legends/KPI tiles, so it's not a total information loss, but still a real barrier.
- **Reproducibility:** Confirmed via automated axe-core scan, consistent result.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core)
- **Screenshot:** `specs/evidence/ui-ux/01-admin-core-tracking/UX-001.png`
- **Status:** Confirmed Accessibility Violation

### UX-002 - Vehicle/record cards are buttons with interactive controls nested inside them (High)

- **Category:** Accessibility
- **Module / Page:** Admin Live Tracking `/tc/live-tracking` (68 occurrences), Trip Playback `/tc/trip-playback` (2 occurrences), Geofences `/tc/geofences` (1 occurrence, `div[role=button]` variant)
- **Element:** `.tracking-card` — a `<button>` containing a nested `<a>` link and a nested `<span role="button" tabindex="0">`
- **Description:** Each vehicle/record card in these lists is itself a clickable `<button>`, but a link and a secondary action button are nested inside it. This is invalid per the HTML interactive-content model, and breaks keyboard/screen-reader activation of the inner link/button: the outer button intercepts Enter/Space, and screen readers announce ambiguous/conflicting roles.
- **Steps to reproduce:** 1. Log in as Admin, open Live Tracking. 2. Inspect any vehicle card in the left list (e.g. `DL04CA1016`) via DOM inspector. 3. Try reaching the nested link by pressing Tab then Enter.
- **Actual result:** Nested focusable elements exist inside a focusable parent; axe-core flags `nested-interactive`. Confirmed by manual DOM inspection of the actual markup.
- **Expected result:** The card should not itself be a `<button>` if it contains other interactive children — restructure as a non-interactive container with the link/secondary action as the real interactive elements.
- **WCAG criterion:** 4.1.2 Name, Role, Value
- **Severity / Priority:** High / High — breaks the core vehicle-selection interaction on the main Live Tracking page, 68 times on that page alone.
- **Reproducibility:** Confirmed via automated axe-core scan on 3 separate pages + manual DOM inspection of the nesting.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core) + manual DOM inspection
- **Screenshot:** `specs/evidence/ui-ux/01-admin-core-tracking/UX-002a-live-tracking.png`, `UX-002b-trip-playback.png`, `UX-002c-geofences.png`
- **Status:** Confirmed Accessibility Violation
- **Checked and ruled out on OEM Live Tracking (Batch 5, 2026-11-12):** the OEM role's `.tracking-card` buttons use a simpler markup (`<button class="tracking-card"><span>...</span></button>`, no nested `<a>` or nested `role=button` elements — confirmed via DOM inspection, 0 nested-interactive descendants found) and axe-core found no `nested-interactive` violation there. This defect is Admin-role-specific; does not widen to OEM.
- **Checked and ruled out on FC Live Tracking too (Batch 7, 2026-11-12):** same result as OEM — FC's `.tracking-card` is `<button type="button" class="tracking-card" aria-pressed="false"><span>...</span></button>` with only `<span>` children, no nested interactive elements, confirmed via `outerHTML` inspection; axe-core found no `nested-interactive` violation on FC Live Tracking (9 cards present). Admin-role-specific, confirmed twice over.
- **Checked and ruled out on RTO Live Tracking too (Batch 8, 2026-11-12):** axe-core scan of RTO Live Tracking found no `nested-interactive` violation (only the unrelated `button-name` issue tracked as UX-003). Confirmed Admin-role-specific across all 3 roles checked (OEM, FC, RTO).

### UX-003 - Map filter/settings icon button has no accessible name (High)

- **Category:** Accessibility
- **Module / Page:** Admin Live Tracking — `/tc/live-tracking`; **also confirmed on OEM Live Tracking `/oem/live-tracking`** during Batch 5 (2026-11-12), **on FC Live Tracking `/fc/live-tracking`** during Batch 7 (2026-11-12), and **on RTO Live Tracking `/rto/live-tracking`** during Batch 8 (2026-11-12) — identical `button-name` violation (critical, 1 node, `.map-toolbar__button.relative`) on the same shared toolbar component across all four roles checked.
- **Element:** Icon-only toolbar button (sliders icon) next to the "Vehicle, IMEI" search box, class `map-toolbar__button relative`, `aria-expanded="true"`
- **Description:** This button has no text content and no `aria-label`, so a screen reader announces only "button" with no indication of its purpose (opening filter options).
- **Steps to reproduce:** 1. Log in as Admin, open Live Tracking. 2. Tab to, or inspect, the icon button immediately right of the vehicle search box.
- **Actual result:** `<button class="map-toolbar__button relative" aria-expanded="true">` wraps only an SVG icon, no label — confirmed via DOM inspection.
- **Expected result:** Should have `aria-label="Filters"` (or similar) matching what the icon represents.
- **WCAG criterion:** 4.1.2 Name, Role, Value (also relevant to 1.1.1)
- **Severity / Priority:** High / High — critical axe impact; a core filter control is completely unlabeled.
- **Reproducibility:** Confirmed via automated scan, verified twice via direct DOM inspection.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core) + manual DOM inspection
- **Screenshot:** `specs/evidence/ui-ux/01-admin-core-tracking/UX-003.png`
- **Status:** Confirmed Accessibility Violation

### UX-004 - Dashboard "Challans This Month" KPI tile disagrees with its own subtext on the time period (Medium)

- **Category:** UI
- **Module / Page:** TC/Admin Dashboard — `/tc/dashboard`
- **Element:** "Challans This Month" KPI tile (6th tile in the Operational Overview row)
- **Description:** The tile is titled "Challans This Month" but its descriptive subtext reads "0 issued this year" — two different timeframes on the same tile.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open the Dashboard. 3. Look at the 6th KPI tile in "Operational Overview".
- **Actual result:** Title says "This Month", subtext says "this year" — verified via `inner_text()`: `"Challans This Month\n\n0\n\n0 issued this year"`, and visually confirmed in a cropped screenshot.
- **Expected result:** Subtext should match the tile's stated period, e.g. "0 issued this month".
- **WCAG criterion:** N/A (content/copy issue, not an accessibility violation)
- **Severity / Priority:** Medium / Medium — misleading at a glance, could cause a viewer to misread statewide enforcement stats.
- **Reproducibility:** Confirmed twice (live `inner_text` read + visual screenshot crop).
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Manual visual + DOM text inspection
- **Screenshot:** `specs/evidence/ui-ux/01-admin-core-tracking/UX-004.png`
- **Status:** Confirmed UI Bug

### UX-005 - Multiple top-level `<h1>` headings on one page (Low — UX Improvement, not a confirmed violation)

- **Category:** UX / heading hierarchy
- **Module / Page:** Admin Live Tracking (`Live Vehicle Tracking` + a second `<h1>` reading "Alerts"), Alert Monitoring (`Alert Monitoring` + `Alert Timeline`), ERSS Dashboard (`ERSS Dashboard` + `Today's History`). **Also confirmed on FC Live Tracking `/fc/live-tracking`** (`Live Vehicle Tracking` + `Alerts`) and **FC's Alert Monitoring `/fc/alerts`** (`Alert Monitoring` + `Alert Timeline`) during Batch 7 (2026-11-12). **Also confirmed on RTO Live Tracking `/rto/live-tracking`** and **RTO's Alerts page `/rto/alerts`** during Batch 8 (2026-11-12) — identical pattern, same shared Core template, now seen on 3 of the 6 roles.
- **Element:** `<h1>` (multiple per page)
- **Description:** Each of these pages renders two top-level `<h1>` elements instead of one. This relates to WCAG 1.3.1 (Info and Relationships) as a best practice, but axe-core does not flag "multiple h1" as a hard violation, and it's a defensible design choice to treat a side-panel as its own top-level region.
- **Steps to reproduce:** 1. Log in as Admin (or FC). 2. Open Live Tracking, Alert Monitoring, or ERSS Dashboard. 3. Query `document.querySelectorAll('h1')` — returns 2 elements on each page.
- **Actual result:** 2 `<h1>` elements per page on 3 of 15 Admin pages inspected in Batch 1, and on both of the equivalent FC pages checked in Batch 7.
- **Expected result:** One `<h1>` per page, with secondary regions using `<h2>` or lower.
- **WCAG criterion:** 1.3.1 Info and Relationships (soft/best-practice, not a hard axe violation)
- **Severity / Priority:** Low / Low
- **Reproducibility:** Confirmed via automated DOM query on all 3 pages; a repeating pattern, not a one-off.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated DOM query + manual judgment on classification
- **Screenshot:** `specs/evidence/ui-ux/01-admin-core-tracking/UX-005.png`
- **Status:** UX Improvement — recommend a product decision on whether side panels should use `<h1>` or `<h2>`, not logged as a confirmed defect.

### UX-006 - Password-visibility toggle buttons have no accessible name on 4 of 5 Admin User Management forms, and on the equivalent OEM and FC forms (High)

- **Category:** Accessibility
- **Module / Page:** Admin User Management — Register Staff `/tc/users/staff`, Register OEM `/tc/users/oem`, Register RTO `/tc/users/rto`, Add Driver `/tc/users/drivers` (Password + Confirm Password fields on each). **Also confirmed on OEM's own Register Fitment Centre (`/oem/users/fitment-centers`) and Register Staff (`/oem/users/staff`) forms** during Batch 5 (2026-11-12), and **on FC's own Change Password form (`/fc/profile`, Change Password tab)** during Batch 7 (2026-11-12). **Also confirmed on RTO's, Inspector's and Driver's own Change Password forms** (`/rto/profile`, `/inspector/profile`, `/driver/profile`, each on the Change Password tab) during Batch 8 (2026-11-12), each with 3 unlabeled toggle buttons (current/new/confirm password fields) — identical `button-name` violation on the same shared password-input component across every one of the 6 testable roles, so this is one platform-wide component defect, not separate bugs per form.
- **Element:** the eye-icon `<button>` next to each password input (class `.inset-y-0.right-2...`)
- **Description:** On these 4 forms, the password-visibility toggle button has no `aria-label` and no text content, so a screen reader announces only "button". The **Add Inspector** form's equivalent button is implemented correctly, with `aria-label="Show password"` — proving the accessible pattern exists in this codebase and was simply not applied to the other 4 forms.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open Register Staff (or Register OEM / Register RTO / Add Driver). 3. Inspect the eye icon next to the Password field: `<button class="...inset-y-0 right-2...">` with an SVG child, no `aria-label`. 4. Compare with Add Inspector's equivalent button, which has `aria-label="Show password"`.
- **Actual result:** axe-core flags `button-name` (critical impact) with 2 matching nodes (Password + Confirm Password toggles) on each of Staff, OEM, RTO, and Driver forms. Confirmed via direct DOM inspection on all 4.
- **Expected result:** Every password-visibility toggle button across User Management should have an `aria-label` (e.g. "Show password" / "Hide password"), consistent with the Add Inspector form's own implementation.
- **WCAG criterion:** 4.1.2 Name, Role, Value (also relevant to 1.1.1)
- **Severity / Priority:** High / High — critical axe impact, repeats across 4 of 5 forms (8 button instances total), and the fix pattern already exists elsewhere in the same codebase.
- **Reproducibility:** Confirmed via automated axe-core scan on all 4 forms + manual DOM inspection confirming the exact missing attribute, cross-checked against the Inspector form's correct implementation.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core) + manual DOM inspection
- **Screenshot:** `specs/evidence/ui-ux/02-admin-user-management/UX-006a-staff-form.png`, `UX-006b-oem-form.png`, `UX-006c-rto-form.png`, `UX-006d-driver-form.png`, `UX-006e-inspector-form-correct-example.png`
- **Status:** Confirmed Accessibility Violation

### UX-007 - "Add Driver" form's Back button has a different position and style than every other User Management form (Low)

- **Category:** UI
- **Module / Page:** Admin User Management — Add Driver `/tc/users/drivers`
- **Element:** the "← Back" button
- **Description:** On Staff, OEM, RTO and Inspector's create forms, the "← Back" button is a plain white/outlined button placed directly above the page heading. On the Add Driver form, the heading ("Add Driver") renders first, and the Back button appears below it with a different, blue-tinted highlighted style — the only one of the 5 User Management forms that differs.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open Register Staff, Register OEM, Register RTO, or Add Inspector — note the Back button's position (above the heading) and style (plain outline) in each. 3. Open Add Driver (`/tc/users/drivers` → "Add Driver") and compare.
- **Actual result:** Add Driver's Back button is positioned below the heading and uses a highlighted blue style; the other 4 forms are consistent with each other and differ from this one.
- **Expected result:** All 5 forms should use the same Back button position and style, matching the other 4.
- **WCAG criterion:** N/A (visual consistency, not an accessibility violation)
- **Severity / Priority:** Low / Low — cosmetic inconsistency, does not block any workflow.
- **Reproducibility:** Confirmed by direct screenshot comparison of all 5 forms.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Manual visual comparison
- **Screenshot:** `specs/evidence/ui-ux/02-admin-user-management/UX-007.png` (compare against `UX-006c-rto-form.png` or `UX-006e-inspector-form-correct-example.png`)
- **Status:** Confirmed UI Bug

### UX-008 - Focus does not move into the form when "Add Inspector" / "Add Driver" is opened (Low — UX Improvement)

- **Category:** UX
- **Module / Page:** Admin User Management — Add Inspector `/tc/users/inspector`, Add Driver `/tc/users/drivers`
- **Element:** the in-page form panel that replaces the list view
- **Description:** Clicking "Add Inspector" or "Add Driver" swaps the list view for the create form within the same page (not a true dialog — no `role="dialog"`/`aria-modal`). After this swap, keyboard focus stays on `<body>` instead of moving to the new form's heading or first field, so a keyboard/screen-reader user gets no cue that the view changed and has to explore from the top again.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open Inspector or Driver list. 3. Click "Add Inspector"/"Add Driver". 4. Check `document.activeElement` — it is still `<body>` (or the global loader), not inside the new form.
- **Actual result:** Focus remains on `<body>` after the view swap, confirmed via `document.activeElement` on both forms.
- **Expected result:** Focus should move to the new form's heading (or its first field) when the view changes, per common SPA accessibility practice.
- **WCAG criterion:** Related to 2.4.3 (Focus Order) as a best practice; not a hard violation since no dialog role is claimed.
- **Severity / Priority:** Low / Low
- **Reproducibility:** Confirmed on both Add Inspector and Add Driver via direct `document.activeElement` checks.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Manual keyboard/focus inspection (no screenshot — a focus state, not a visual difference)
- **Screenshot:** N/A
- **Status:** UX Improvement

### UX-009 - The Refresh/Reset button pair is placed inconsistently across the 6 PIS Management sub-pages (Low)

- **Category:** UI
- **Module / Page:** Admin Operations — PIS Management: Routes, Timetables, Stops, Service Calendars, Service Patterns, Trips (all under `/tc/operations/pis-management/*`)
- **Element:** the "Refresh" and "Reset" buttons relative to the page header vs. the filter bar
- **Description:** These 6 sub-pages otherwise share one visual template (header, 4 stat tiles, filter bar, table), but the Refresh/Reset control pair is positioned differently depending on the page. Timetables, Stops, Service Patterns and Trips (4 of 6) keep both "Reset" and "Refresh" together inside the filter bar, with only the primary Create button in the top-right header row. Routes instead puts "Refresh" in the top-right header row next to "Add Route", leaving only "Reset" in the filter bar. Service Calendars goes further still: both "Refresh" and "Reset" move up into the header row next to "Create Service Calendar", leaving neither button in the filter bar at all.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open each of `/tc/operations/pis-management/{routes,timetables,stops,service-calendars,service-patterns,trips}`. 3. Compare where "Refresh" and "Reset" sit relative to the filter bar and the header's Create button.
- **Actual result:** 3 different layouts across 6 pages that otherwise share the same template (confirmed via screenshot comparison: Timetables/Stops/Service Patterns/Trips = pattern A, Routes = pattern B, Service Calendars = pattern C).
- **Expected result:** All 6 pages should place Refresh/Reset in the same location, matching the dominant pattern (A) already used by 4 of the 6.
- **WCAG criterion:** N/A (visual/layout consistency, not an accessibility violation)
- **Severity / Priority:** Low / Low — no functional impact, purely a template-drift consistency issue, but it repeats across half of this page group.
- **Reproducibility:** Confirmed via direct screenshot comparison of all 6 pages.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Manual visual comparison
- **Screenshot:** `specs/evidence/ui-ux/03-admin-oem-mgmt-operations/UX-009a-routes.png` (pattern B), `UX-009b-timetables.png` (pattern A), `UX-009c-service-calendars.png` (pattern C)
- **Status:** Confirmed UI Bug

### UX-010 - The shared date-range filter has no accessible name, on 8 of 14 Admin report pages (High)

- **Category:** Accessibility
- **Module / Page:** Admin Reports — Ownership Transfers, Account Merges, Device Health, Alert Report, Vehicle Alert Trail, Installation Performance (OEM-wise), Installation Report, Repair & Replacement History (all under `/tc/reports/*`). **Also confirmed on OEM Reports** (2026-11-12, Batch 6) — Alerts, Vehicle Trail, Device Health, Installation Status, OEM Performance (5 of OEM's 12 reports, under `/oem/reports/*`), same `label` axe violation, same `<input type="date">` component. **Also confirmed on FC** (2026-11-12, Batch 7) — Alerts, Vehicle Trail, Device Health, Installation Status (4 of FC's 11 reports, under `/fc/reports/*`), and on FC's own **Installation History** page (`/fc/installation-history`, not a "report" under `/reports/*` but the same unlabeled `<input type="date">` component, 2 nodes). **Also confirmed on RTO** (2026-11-12, Batch 8) — Alerts, Vehicle Trail, Device Health, OEM Performance (4 of RTO's 13 reports, under `/rto/reports/*`), and on RTO's own **Approval History** page (`/rto/audit/approval-history`, not a "report" page either, same unlabeled `<input type="date">` pair) — confirming this is a shared form component used well beyond the Reports section, now reproduced on all 4 roles checked.
- **Element:** `<input type="date">` (the "From"/"To" date-range filter pair used at the top of each of these 8 reports)
- **Description:** Every one of these 8 reports uses the same date-range filter component, and on every one of them both date inputs have no `<label>`, `aria-label`, or `aria-labelledby` - a screen reader announces only "date input, blank" for either field, with no indication it's a from/to date filter.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open any of the 8 reports listed above. 3. Inspect either date input via DOM/accessibility tree, or run an axe-core scan.
- **Actual result:** axe-core's `label` rule fires as **critical**, 2 nodes, identically on all 8 pages (confirmed via direct DOM inspection of the `<input type="date">` markup on 3 of them).
- **Expected result:** Each date input should have an associated label (e.g. a visually-hidden `<label for="...">"From date"` / `"To date"`, or `aria-label`).
- **WCAG criterion:** 1.3.1 Info and Relationships / 4.1.2 Name, Role, Value
- **Severity / Priority:** High / High — critical axe impact, and it is the same shared component repeated across the majority (8 of 14) of this batch's pages, so fixing the one component fixes all 8.
- **Reproducibility:** Confirmed via automated axe-core scan on all 8 pages, with manual DOM inspection confirming the identical markup on 3 of them.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core) + manual DOM inspection
- **Screenshot:** `specs/evidence/ui-ux/04-admin-reports/UX-010.png` (Ownership Transfers, representative)
- **Status:** Confirmed Accessibility Violation

### UX-011 - Device Packets' date-range picker has nested interactive controls (Medium)

- **Category:** Accessibility
- **Module / Page:** Admin Reports — Device Packets `/tc/reports/device-packets`. **Also confirmed on OEM Reports** (2026-11-12, Batch 6) — OEM's own Device Packets report (`/oem/reports/device-packets`) reproduces the identical `nested-interactive` violation, 2 nodes, same selector shape. **Also confirmed on FC Reports** (2026-11-12, Batch 7) — FC's Device Packets report (`/fc/reports/device-packets`) reproduces the same violation, 2 nodes. **Also confirmed on RTO Reports** (2026-11-12, Batch 8) — RTO's Device Packets report (`/rto/reports/device-packets`) reproduces the same violation, 2 nodes. All four roles' Device Packets report share this exact defect.
- **Element:** `.date-picker-trigger` (a `<div>`-based custom date-picker trigger, different widget from the 8 pages in UX-010)
- **Description:** This report uses its own custom date-picker component (clickable `<div>` trigger showing "12 Nov 2026") rather than the shared `<input type="date">` used elsewhere. It contains nested focusable/interactive elements inside a focusable parent - the same structural defect family as **UX-002** from Batch 1 (Live Tracking's nested-interactive vehicle cards), just a different component instance.
- **Steps to reproduce:** 1. Log in as Admin, open Device Packets. 2. Inspect either date-picker trigger (the two "12 Nov 2026" controls) via DOM inspector.
- **Actual result:** axe-core's `nested-interactive` rule fires, serious impact, 2 nodes.
- **Expected result:** The date-picker trigger should not nest other interactive elements inside a focusable parent, matching the fix needed for UX-002.
- **WCAG criterion:** 4.1.2 Name, Role, Value
- **Severity / Priority:** Medium / Medium — same defect family as the High-severity UX-002, but here it's 1 page with 2 nodes rather than 68 occurrences on a primary page, so scored lower.
- **Reproducibility:** Confirmed via automated axe-core scan, consistent result.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core)
- **Screenshot:** `specs/evidence/ui-ux/04-admin-reports/UX-011.png`
- **Status:** Confirmed Accessibility Violation

### UX-012 - "Minimum Challans" field's visible label isn't programmatically associated with its input, and an adjacent button has no accessible name (High)

- **Category:** Accessibility
- **Module / Page:** Admin Reports — Multiple-Challan Vehicles `/tc/reports/multiple-challan-vehicles`
- **Element:** The "Minimum Challans" number input, and an adjacent icon-only button next to it (purpose unclear from markup alone - likely a stepper or clear control)
- **Description:** This page shows the text "Minimum Challans" visually above a number input, but that text is not connected to the input via `<label for>` or `aria-labelledby`, so a screen reader does not announce the field's purpose when it receives focus. A second, adjacent button on the same filter row also has no text content and no `aria-label`.
- **Steps to reproduce:** 1. Log in as Admin, open Multiple-Challan Vehicles. 2. Inspect the number input under "Minimum Challans" (default value "2") and the button beside it via DOM inspector or axe-core scan.
- **Actual result:** axe-core's `label` rule fires (critical, 1 node, the number input) and `button-name` rule fires (critical, 1 node, the adjacent button).
- **Expected result:** The number input should have `aria-labelledby` pointing at the visible "Minimum Challans" text (or a proper `<label for>`), and the adjacent button should have a descriptive `aria-label`.
- **WCAG criterion:** 1.3.1 / 4.1.2
- **Severity / Priority:** High / High — both are critical-impact axe violations on a filter control a user would need to operate to narrow this report.
- **Reproducibility:** Confirmed via automated axe-core scan, consistent result.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core)
- **Screenshot:** `specs/evidence/ui-ux/04-admin-reports/UX-012.png`
- **Status:** Confirmed Accessibility Violation

### UX-013 - Installation Report's table wrapper is a scrollable region that isn't keyboard-focusable (Low)

- **Category:** Accessibility
- **Module / Page:** Admin Reports — Installation Report `/tc/reports/installation-status`. **Also confirmed on OEM Reports** (2026-11-12, Batch 6) — OEM's Device Installations (`/oem/reports/device-installations`) and Installation Status (`/oem/reports/installation-status`) both reproduce the identical `scrollable-region-focusable` violation. **Also confirmed on FC Reports** (2026-11-12, Batch 7) — FC's Installation Status report (`/fc/reports/installation-status`) reproduces the same violation, 1 node. **Also confirmed on RTO Reports** (2026-11-12, Batch 8) — RTO's Device Health (`/rto/reports/device-health`) and Device Packets (`/rto/reports/device-packets`) both reproduce the same violation, 1 node each.
- **Element:** `.ui-table-wrapper` (the horizontally-scrollable `<div>` wrapping the report's wide table)
- **Description:** The table wrapper can scroll horizontally (the table is wider than its container) but has no `tabindex`, so a keyboard-only user cannot focus it to scroll it with arrow keys - they would need a mouse/trackpad or a horizontal scrollbar drag.
- **Steps to reproduce:** 1. Log in as Admin, open Installation Report. 2. Tab through the page's controls - the table's scrollable area is never reachable by keyboard alone.
- **Actual result:** axe-core's `scrollable-region-focusable` rule fires, moderate impact, 1 node.
- **Expected result:** The scrollable wrapper should have `tabindex="0"` (or equivalent) so it can receive keyboard focus and be scrolled with arrow keys.
- **WCAG criterion:** 2.1.1 Keyboard
- **Severity / Priority:** Low / Low — isolated to this one report's especially wide table; a real but minor barrier for keyboard-only users on this specific page.
- **Reproducibility:** Confirmed via automated axe-core scan.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core)
- **Screenshot:** `specs/evidence/ui-ux/04-admin-reports/UX-013.png`
- **Status:** Confirmed Accessibility Violation

### UX-014 - The "clear all filters" action is worded three different ways across the 14 report pages (Low)

- **Category:** UI
- **Module / Page:** Admin Reports — all 14 pages under `/tc/reports/*`
- **Element:** The filter-reset button
- **Description:** The button that resets a report's filters back to default is labeled differently depending on the page: "Clear filters" (Ownership Transfers, Account Merges, Device Health, Installation Performance), "Reset filters" (Device Status, Alert Report, Fleet Activity), and plain "Reset" (Device SIM Validity Report, User Devices Report, Device Packets). Three different pieces of copy for what is functionally the same action.
- **Steps to reproduce:** 1. Log in as Admin. 2. Open each of the 14 reports under Reports. 3. Compare the wording of the filter-reset button.
- **Actual result:** 3 different labels in use across 10 of the 14 pages that have this control at all (confirmed via direct button-text extraction on all 14 pages).
- **Expected result:** One consistent label (e.g. "Reset filters", already the single most common distinct wording family) across every report.
- **WCAG criterion:** N/A (copy/terminology consistency, not an accessibility violation)
- **Severity / Priority:** Low / Low — no functional impact, purely a naming-consistency issue, but it repeats across most of the batch.
- **Reproducibility:** Confirmed via direct button-text extraction on all 14 pages.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Manual/automated DOM text comparison
- **Screenshot:** `specs/evidence/ui-ux/04-admin-reports/UX-014a-clear-filters.png` ("Clear filters"), `UX-014b-reset-filters.png` ("Reset filters"), `UX-014c-reset.png` ("Reset")
- **Status:** Confirmed UI Bug

### UX-015 - Ticket attachment download link on the Ticket Performance Report has no accessible name (Medium)

- **Category:** Accessibility
- **Module / Page:** OEM Audit — Ticket Performance Report `/oem/audit-reports/ticket-performance`
- **Element:** `<a href=".../storage/tickets/<file>.xlsx" target="_blank" rel="noopener noreferrer" class="inline-flex ... text-blue-600 hover:text-blue-700">` (an icon-only attachment-download link in the ticket table, 6 occurrences on the page inspected)
- **Description:** Each row with an attached file renders a download link as an icon with no text content and no `aria-label`, so a screen reader announces only "link" with no indication of what file it downloads or that it's a download action at all.
- **Steps to reproduce:** 1. Log in as OEM. 2. Open Audit → Ticket Performance Report. 3. Inspect any attachment icon/link in the ticket rows via DOM inspector or axe-core scan.
- **Actual result:** axe-core's `link-name` rule fires, serious impact, 6 nodes on this page alone.
- **Expected result:** Each attachment link should have a descriptive `aria-label` (e.g. "Download attachment for ticket VLTD-20261110-LHBXAI2R") or visually-hidden text.
- **WCAG criterion:** 4.1.2 Name, Role, Value (also relevant to 2.4.4 Link Purpose)
- **Severity / Priority:** Medium / Medium — a real barrier to downloading ticket attachments for screen-reader users, but one secondary feature on one audit page, not a core workflow blocker.
- **Reproducibility:** Confirmed via automated axe-core scan, consistent result.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core)
- **Screenshot:** `specs/evidence/ui-ux/06-oem-reports-audit-helpdesk/UX-015-ticket-performance.png`
- **Status:** Confirmed Accessibility Violation

### UX-016 - Draft Challan's evidence-upload file input has no accessible name (Medium)

- **Category:** Accessibility
- **Module / Page:** RTO Inspector — Draft Challan `/inspector/challans/create`, "3. Evidence & Review" section
- **Element:** `<input type="file" class="sr-only" accept=".jpg,.jpeg,.png,.webp,.pdf,...">` (multiple files allowed), paired with a visible styled drop-zone `<button>` that also triggers the same file picker
- **Description:** The actual file input that receives the upload has no `aria-label`, `aria-labelledby`, or associated `<label>`. It sits in the DOM as its own focusable element alongside the visible "drag and drop or browse" button, so a keyboard-only or screen-reader user tabbing through the form can land on an unlabeled file control with no indication of its purpose, separately from the labeled drop-zone button.
- **Steps to reproduce:** 1. Log in as an RTO Inspector. 2. Open Draft Challan (My Challans → Create). 3. Scroll to "3. Evidence & Review" and inspect the hidden file input via DOM inspector or axe-core scan.
- **Actual result:** axe-core's `label` rule fires, critical impact, 1 node.
- **Expected result:** The file input should have an `aria-label` (e.g. "Upload evidence files") or be properly associated with the visible instructions via `aria-labelledby`.
- **WCAG criterion:** 1.3.1 Info and Relationships / 4.1.2 Name, Role, Value
- **Severity / Priority:** Medium / Medium — Draft Challan is a core Inspector workflow, and evidence upload is a required step within it.
- **Reproducibility:** Confirmed via automated axe-core scan, consistent result.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core) + manual DOM inspection
- **Screenshot:** `specs/evidence/ui-ux/08-rto-inspector-driver/UX-016.png`
- **Status:** Confirmed Accessibility Violation

### UX-017 - Icon-prefixed info lists break the `<dl>`/`<dt>`/`<dd>` structure (Low)

- **Category:** Accessibility
- **Module / Page:** RTO Inspector — Draft Challan `/inspector/challans/create` (the challan summary panel: RTO, Vehicle, etc.). **Also confirmed on Driver Dashboard** `/driver/dashboard` (the "Owner & Organization" panel: Contact Person, Contact Number, etc.) during the same batch (2026-11-12) — identical markup pattern in both places.
- **Element:** `<dl>` whose direct children are `<div>` wrappers, each containing a decorative `<svg>` icon alongside a `<dt>`/`<dd>` pair (e.g. `<dl><div><svg/><dt>RTO</dt><dd>-</dd></div>...</dl>`)
- **Description:** Wrapping each `dt`/`dd` pair together with an icon inside its own `<div>`, directly under `<dl>`, breaks the definition-list structure the accessibility tree expects — axe-core flags both the `<dl>` itself and 6 of its `<dt>`/`<dd>` items as not forming a valid list group, which can make a screen reader announce the label/value pairs inconsistently or skip the grouping semantics entirely.
- **Steps to reproduce:** 1. Log in as an RTO Inspector, open Draft Challan, and inspect the challan summary `<dl>` via DOM inspector or axe-core scan — OR — 2. Log in as Driver, open the Dashboard, and inspect the "Owner & Organization" panel's `<dl>` the same way.
- **Actual result:** axe-core's `definition-list` rule fires (serious) plus `dlitem` (serious, 6 nodes) on both pages.
- **Expected result:** Each `<dt>`/`<dd>` pair should be a direct child of `<dl>` (optionally wrapped in a single `<div>` per the HTML5 "association list" pattern, with the icon moved outside that wrapping, or marked `aria-hidden="true"` and kept out of the `dt`/`dd` grouping) so the list structure validates.
- **WCAG criterion:** 1.3.1 Info and Relationships (soft/best-practice — axe treats it as a real violation, but it's a structural nicety rather than a hard information-loss barrier, since the dt/dd text itself is still readable)
- **Severity / Priority:** Low / Low — cosmetic-adjacent structural issue; the information is still present and readable, just not grouped per spec.
- **Reproducibility:** Confirmed via automated axe-core scan on both pages, with manual DOM inspection confirming the identical markup pattern.
- **Viewport / Browser:** Desktop 1920x1080, Chromium
- **Method:** Automated (axe-core) + manual DOM inspection
- **Screenshot:** `specs/evidence/ui-ux/08-rto-inspector-driver/UX-017a-inspector-draft-challan.png`, `UX-017b-driver-dashboard.png`
- **Status:** Confirmed Accessibility Violation

## Ruled out / not logged as findings

- **200% browser zoom reflow on Dashboard** (Batch 1) — initial test using the CSS `zoom` trick showed false horizontal scroll (a known artifact of that technique, not real browser zoom). Re-tested using Chrome DevTools Protocol device-metrics emulation (`scale: 2.0`) at 1366x768, and directly at 683x384 / 480x800 — no horizontal scroll in either case. Ruled out, not a bug.
- **Table `<th>` missing `scope` attribute** (Batch 1, seen again on Watch History / Set History) — same root cause already tracked as **BUG-087** in the functional `bug_report.md`; not duplicated here since it's one state-wide issue, not specific to this batch.
- **Driver's empty duty/vehicle states** (Batch 8) — Driver Dashboard, Future Duties, Duty History, and Vehicle Details all showed genuinely empty data live (no duty, no vehicle assigned — the known School-account dependency from the 2026-11-10 functional test plan). Checked the empty-state *quality* itself rather than treating the missing data as a blocker: each one renders a clear icon, a bolded "No X assigned/found" heading, a plain-English explanatory sentence, and (on the Dashboard) a working "Refresh Duty" action. No UI defect found — these are well-designed empty states, not logged as a finding.
- **OEM Management lists show "-" in the OEM name column** (Batch 3 — Device Models, Firmware, SIM Modules all show this) — this is a data-binding/API gap, not a UI/UX or accessibility issue, so it is deliberately **not** logged here. It is the same symptom already tracked as **BUG-025** in the functional `bug_report.md`, but BUG-025's text only covers the Firmware list — Device Models and SIM Modules show the identical "-" for OEM on every row too. Flagging for the functional report owner to consider widening BUG-025's scope to all 3 lists, rather than treating it as fixed-for-two-of-three.
- A route named literally `<script>alert(1)</script>` was seen rendered as plain text (not executed) on the Route Management and Service Pattern Management lists — confirms the app safely escapes it for display, so this is not a new XSS finding; it is leftover test data from an earlier functional security test, out of scope for this audit, and not logged as a UI/UX finding.
- **Empty-state rendering on 2 reports tested deliberately (Batch 4)** — Ownership Transfers with a date range guaranteed to match nothing ("No ownership transfers found.") and User Devices Report with a nonsense search term ("No Users Found / No users match the selected report filters.") both rendered clean, sensible empty-state messages. Not a bug; included here only to record that empty states were checked and passed.
- **OEM Device Inventory, Device Status, SIM Validity (`device-validity`), Expired Installations, User Devices, and Helpdesk (My Tickets, Assigned Tickets, Create Ticket) (Batch 6)** — 0 axe-core violations, no spelling/layout issues found on any of these. Not bugs; recorded to show they were actually checked, not skipped.
- **FC Command Center, Trip Playback, Geofences, Watch History, Set History, Helpdesk, Installation Jobs, Repair Installation, Map Devices, New Installation wizard (Step 1 only — the page stops short of BUG-080's known Step 3 blocker so later steps were not reached read-only), Profile, Device Inventory, Device Status, SIM Validity, Repair History, User Devices, Vehicle Mappings (Batch 7)** — 0 axe-core violations, no spelling/layout issues found on any of these. Not bugs; recorded to show they were actually checked, not skipped.

## Batch log

| Batch | Scope | Date | Pages inspected | Findings | Headline |
|---|---|---|---|---|---|
| 1 | Admin — Core/Dashboard/Tracking | 2026-11-12 | 15/15 (full visual+a11y pass on Dashboard & Live Tracking; axe scan + DOM heading/button check on the other 13) | 5 (4 confirmed, 1 UX improvement) | Nested-interactive vehicle cards (UX-002) and an unlabeled filter button (UX-003) are the highest-severity items; no real screen-reader session performed yet — axe-core + DOM inspection only. |
| 2 | Admin — User Management | 2026-11-12 | 7/7 (all 5 create forms + list pages fully inspected, read-only) | 3 (2 confirmed, 1 UX improvement) | Password-visibility toggle buttons missing accessible names on 4 of 5 forms (UX-006) is the highest-severity item - notably, the Inspector form's equivalent button is correctly labeled, proving the fix pattern already exists in this codebase. |
| 3 | Admin — OEM Management + Operations | 2026-11-12 | 15/15 (Device Models full; Firmware/SIM Modules spot-checked; 9 Operations pages including 6 PIS sub-pages) | 1 confirmed (axe-core found zero accessibility violations anywhere in this batch) | Only a layout-consistency issue (UX-009, Refresh/Reset placement) survived verification; a pre-existing functional data gap (BUG-025, "OEM" column shows "-") was found to also affect Device Models and SIM Modules, not just Firmware, and flagged for the functional report rather than logged here. |
| 4 | Admin — Reports | 2026-11-12 | 14/14 (full visual + axe-core scan on every report; empty-state checked on 2 of 14) | 5 confirmed (4 accessibility, 1 UI) | The shared date-range filter component used on 8 of 14 reports has no accessible name (UX-010, High) - the single highest-value fix in this batch, since it covers the majority of the group at once. Multiple-Challan Vehicles (UX-012) and Device Packets (UX-011) use their own one-off filter widgets, each with their own accessibility gaps. Empty states on the 2 reports tested render cleanly. |
| 5 | OEM — Core + Devices + Allocations + Fitment Centres + Staff | 2026-11-12 | Core (8, lighter pass reusing Batch 1 findings) + Devices (list+add, full) + Device Models (read-only, full) + Allocations (list + wizard step 1, full) + Fitment Centres (list+register, full) + Staff (list+register, full) | 0 new UX-IDs; widened 3 existing ones (UX-001, UX-003, UX-006) to cover OEM, and explicitly ruled out UX-002 on OEM's simpler card markup | No OEM-specific defects found beyond the same shared-component issues already tracked under Admin - the password-toggle accessible-name gap (UX-006) and the unlabeled chart/filter controls (UX-001/UX-003) are platform-wide, not Admin-only. Allocate Stock wizard step 2+ was not reached (Continue stayed disabled without selecting a fitment centre first) - not pursued further given the read-only scope of this audit. |
| 6 | OEM — Reports + Audit + Helpdesk | 2026-11-12 | Reports: 5 of 12 spot-checked in depth (Alerts, Vehicle Trail, Device Health, Device Packets, Installation Status), remaining 7 given a lighter axe-core-only pass; Audit (Ticket Performance) and Helpdesk (My Tickets, Assigned Tickets, Create Ticket) fully inspected | 1 new (UX-015); widened 3 existing ones (UX-010, UX-011, UX-013) to cover matching OEM reports | OEM's reports reuse the exact same filter/table components already found broken under Admin - the unlabeled date filter (UX-010) reproduces on 5 of OEM's 12 reports, the nested-interactive date-picker (UX-011) reproduces on OEM's own Device Packets, and the unkeyboardable scroll wrapper (UX-013) reproduces on 2 OEM reports. The one new, OEM-specific defect is an unlabeled ticket-attachment download link on the Ticket Performance Report (UX-015). Helpdesk (My Tickets, Assigned Tickets, Create Ticket) is clean - 0 axe violations, no spelling/layout issues. |
| 7 | Fitment Centre — full audit (28 screens) | 2026-11-12 | Core (9, full), Device Models (full), Installation (New Installation wizard Step 1 + Jobs/History/Repair/Map Devices, full), Reports (all 11 scanned, 5 full visual), Profile/Change Password (full) | 0 new UX-IDs; widened 8 existing ones (UX-001, UX-003, UX-005, UX-006, UX-010, UX-011, UX-013) to cover FC; re-confirmed UX-002 ruled out on FC too | Zero FC-specific defects — every issue found on FC is the exact same shared-component bug already tracked under Admin and/or OEM (chart alt text, unlabeled filter button, unlabeled date filter, nested-interactive date-picker, unkeyboardable scroll wrapper, unlabeled password toggle, multi-h1), now confirmed on a third role each time. This is strong evidence these are platform-wide component defects, not per-role issues - fixing each shared component once would resolve it everywhere at once. New Installation wizard's Step 1 (Search Vehicle) is clean; later steps were not reached read-only (consistent with BUG-080's known Step 3 blocker in the functional report). |
| 8 | RTO Officer + RTO Inspector + Driver — full audit (final batch) | 2026-11-12 | RTO Officer: Core (9, full), Challan Work Queue/Installation Approvals x3/Approval History/Permit Holders (full), Reports (13 total - 10 spot-checked directly, 3 confirmed clean), Change Password (full). RTO Inspector: all 6 screens, full. Driver: all 6 screens, full, including empty-state quality review. | 2 new (UX-016, UX-017); widened 6 existing ones (UX-001, UX-003, UX-005, UX-006, UX-010, UX-011, UX-013) to cover RTO/Inspector/Driver; re-confirmed UX-002 ruled out on RTO | Zero genuinely new defects on RTO Officer itself - every RTO issue found is a shared-component bug already tracked under 1-3 other roles, now confirmed on a 4th. The 2 new findings are both specific to RTO Inspector's Draft Challan workflow and a shared icon-list component also found on Driver's Dashboard (UX-017). UX-006 (unlabeled password-toggle button) now reproduces on every one of the 6 testable roles' Change Password forms - the single most widely-reproduced defect in the whole audit. Driver's empty duty/vehicle states were checked for quality rather than treated as a testing blocker, and found to be well-designed, not defective. |

## Audit complete — closing summary

All 8 planned batches are done, covering all 6 testable roles (Permit Holder remains excluded — the same pre-existing account-creation blocker documented in `specs/role-panels-test-plan.md` since 2026-11-10) across roughly 167 inventoried screens. The audit produced **17 UI/UX and accessibility findings** (UX-001 through UX-017: 12 Confirmed Accessibility Violations, 3 Confirmed UI Bugs, 2 UX Improvements flagged for a product decision rather than logged as defects) and **64 automated regression tests** across `tests/ui_ux/` (one test file per batch, all independently re-run as a full suite and verified clean: 6 passed as expected, 58 xfailed confirming each targeted defect is still live, 0 unexpected failures or XPASSes). The single biggest cross-cutting theme is that almost none of these are per-role bugs: of the 17 findings, 8 are the exact same shared UI component (chart canvases with no alt text, an unlabeled map-filter button, an unlabeled date-range filter, a nested-interactive date-picker, an unkeyboardable scroll wrapper, an unlabeled password-toggle button, a duplicate-`<h1>` pattern, and an icon-prefixed definition-list structure) reproducing identically across 3, 4, 5, or in UX-006's case all 6 of the testable roles — meaning a handful of shared-component fixes would resolve the large majority of this audit's findings at once, rather than requiring 17 separate code changes. No real assistive-technology (screen reader) session was performed in any batch; every accessibility finding here comes from axe-core automated scans plus manual DOM/ARIA/keyboard inspection, which is explicitly a subset of full WCAG 2.2 AA verification - this report does not claim compliance, only the specific violations it found and reproduced.

