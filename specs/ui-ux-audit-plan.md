# VLTD UI/UX & Accessibility Audit — Page Inventory & Coverage Plan

Date: 2026-11-12. Scope: every page reachable by the 6 testable roles (TC/Admin, OEM, Fitment Centre,
RTO Officer, RTO Inspector, Driver), built from the existing Page Object Model + test suite routes and
confirmed via a live read-only navigation crawl. **Permit Holder excluded** — same unresolved
account-creation blocker documented in `specs/role-panels-test-plan.md` since 2026-11-10.

Findings from this audit go in `ui_ux_bug_report.md` (IDs `UX-NNN`) and the separate UI/UX spreadsheet —
never mixed into the functional `bug_report.md` (`BUG-NNN`).

## Page inventory

### TC / Admin — 61 screens
- Core (15): Dashboard, Command Center, Live Tracking, Trip Playback, Geofences, Alerts, Watch History,
  Set History, ERSS, Announcements, Challans, Challan Master, Help Centers, Helpdesk, Configuration
- User Mgmt (7 list+form pairs): Staff, OEM, RTO, Inspector, Drivers, FC, Permit Holders
- OEM Mgmt (3 list+new+edit triplets): Device Models, Firmware, SIM Modules
- Operations (9): Vehicle-Device Untag, Ownership Transfer, Account Merge, PIS (Routes/Calendars/
  Patterns/Stops/Timetables/Trips)
- Reports (14 report pages)
- Account (2): Profile, Change Password

### OEM — ~36 screens
Core (8), Helpdesk, Devices (list/new/edit), Device Models (read-only), Allocations (list + Allocate
Stock wizard), Fitment Centres (list/new), Staff (list/new), Operations (SIM Validity Extension,
Repairs), Reports (12), Audit (Ticket Performance), Profile/Change Password.

### Fitment Centre — 28 screens
Core (9), Device Models (read-only), Installation (New Installation wizard, Jobs, History, Repair, Map
Devices), Reports (11), Profile/Change Password.

### RTO Officer — ~30 screens
Core (9), Challan Work Queue, Installation Approvals (Pending/Approved/Rejected), Approval History,
Permit Holders list, Reports (13), Profile/Change Password.

### RTO Inspector — 6 screens
Dashboard (BUG-085 lives here), My Challans, Draft Challan, Verify Fitment, Profile, Change Password.

### Driver — 6 screens
Dashboard, My Duty, Future Duties, Duty History, Vehicle Details, Profile/Change Password.

### Permit Holder — excluded (pre-existing blocker, no account exists)

**Total: ~167 screens across 6 testable roles.**

## Batching plan

1. Admin — Core/Dashboard/Tracking
2. Admin — User Management
3. Admin — OEM Management + Operations
4. Admin — Reports
5. OEM — Core + Devices + Allocations + Fitment Centres + Staff
6. OEM — Reports + Audit + Helpdesk
7. Fitment Centre — all
8. RTO Officer + RTO Inspector + Driver — all

## Viewports

Desktop 1920x1080 and 1366x768; Tablet 1024x768 and 768x1024; Mobile 390x844 and 360x800; plus 200%
browser zoom at 1366x768 (WCAG 1.4.4 / 1.4.10 reflow).

## Full inspection vs. spot-check

All list/form/dashboard/wizard pages get full visual + accessibility inspection. The ~14 report pages
per role share one generated template (functional testing already confirmed only data differs, not
layout) - full inspection on Admin's reports, spot-check 2-3 of OEM/FC/RTO's for template drift only.
Same logic for Admin's Device Models / Firmware / SIM Modules triplet: full on Device Models, spot-check
the other two.

axe-core scans run on every page in the full-inspection set at the desktop viewport; tablet/mobile
reflow and touch-target checks are spot-checked on a representative subset per batch (dashboards, one
list page, one form) rather than every single screen, unless a batch's own inspection finds a reason to
widen that.

## Known gaps

- Permit Holder entirely excluded (pre-existing blocker, not new).
- Row-level detail pages (single device/vehicle/ticket) were not pre-enumerated - sampled during the
  page-by-page pass instead of inventoried exhaustively up front.
- Driver's duty screens showed empty states live (same School-account dependency noted in the
  2026-11-10 role-panel test plan, section 8) - populated-state visuals may need seeded data; flagged as
  a testability gap rather than assumed fine.
- Admin's `/tc/configuration`, `/tc/erss`, `/tc/challan-master` sub-tabs/forms were reached but not
  explored past landing as of the inventory pass - confirmed during each page's actual batch.
- Profile/Change Password pages were inferred from the avatar-menu pattern for roles without an existing
  page object (Admin, RTO, Inspector, Driver) - confirmed as each batch is opened.
