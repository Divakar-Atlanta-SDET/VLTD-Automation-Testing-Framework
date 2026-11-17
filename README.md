# VLTD Automation Framework

Playwright + Pytest (Python) automation framework for VLTD (https://vltd.misbackend.com) — covers the Admin/TC
(State Admin) panel, OEM panel, Fitment Centre panel, Driver/Inspector/RTO Officer panels, the Permit Holder
(Fleet Owner) panel, and a cross-cutting UI/UX accessibility (WCAG) audit.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env   # then fill in BASE_URL and credentials
```

`.env` needs `BASE_URL` plus a username/password pair per role you want to test against:
`ADMIN`, `OEM`, `FC`, `DRIVER`, `INSPECTOR`, `RTO`, `PERMIT_HOLDER` (e.g. `FC_USERNAME` / `FC_PASSWORD`). A fixture
`pytest.skip`s that role's tests if its pair isn't a valid-looking login, so you only need the roles you're testing.
Never commit `.env` or print its values; it's already in `.gitignore`.

## Run

```powershell
pytest                                            # everything
pytest tests/test_login.py tests/test_dashboard.py -n 4   # login + dashboard, parallel
pytest -m smoke                                   # smoke subset
pytest --known-bugs                               # also run the tests that document open defects (xfail)
pytest -m negative -n 4                           # input-validation tests (UI + API)
pytest tests/oem_management -n 4                  # Device Models, Firmware, SIM Modules (State Admin side)
pytest tests/oem_panel -n 4                        # OEM panel: devices, allocation, commands, fitment centres
pytest tests/fc_panel -n 4                         # Fitment Centre panel: dashboard, operations, reports, helpdesk
pytest tests/role_panels -n 4                      # Driver, Inspector, RTO Officer panels + cross-role isolation
pytest tests/permit_holder -n 4                    # Permit Holder (Fleet Owner) panel
pytest tests/ui_ux -m ui_ux                        # UI/UX accessibility (axe-core) regression checks
pytest --keep-test-data                            # skip the end-of-run test-data cleanup
python -m utils.cleanup                            # run that cleanup by hand
```

### Test data and cleanup

- Tests create their own data (names start with `AUTO` / `Auto`) and remove what they can: the `records` fixture deletes the
  OEM Management records a test created, even when the test fails.
- After every run `utils/cleanup.py` sweeps up once (after all parallel workers are done): it deletes leftover Device Models,
  Firmware and SIM Modules, deactivates test staff accounts, and prints what only the database owner can remove
  (OEMs, RTOs, Drivers, Inspectors, Help Centres - the application has no delete for them).
- The `AUTO PG` records (12+ per OEM Management list) are a persistent seed for the pagination tests and are never deleted.

### What the default run contains

The suite is kept lean: core flows, one representative case per input-validation partition, and permission checks per
permission. Tests that document a known application defect (marked `xfail`, see `bug_report.md` and
`ui_ux_bug_report.md`) are **not run by default** - add `--known-bugs` to include them; they then report as expected
failures and flag a fixed bug by XPASS.

Markers: `smoke`, `regression`, `api`, `critical`, `auth`, `dashboard`, `user_management`, `negative`, `permissions`,
`oem_management`, `configuration`, `oem_panel`, `fc_panel`, `driver_panel`, `inspector_panel`, `rto_panel`,
`permit_holder_panel`, `ui_ux`.

## Layout

| Path | Purpose |
|---|---|
| `tests/` | Test modules, grouped by panel: `administration/`, `oem_management/`, `oem_panel/`, `fc_panel/`, `role_panels/` (Driver, Inspector, RTO Officer), `permit_holder/`, `permissions/`, `configuration/`, `ui_ux/`, plus `test_login.py` / `test_dashboard*.py` |
| `pages/` | Page objects, one subfolder per panel (`oem_panel/`, `fc_panel/`, `role_panels/`, `administration/`, `oem_management/`) plus shared `base_page.py`, `login_page.py`, `dashboard_page.py` |
| `conftest.py` | Shared pytest fixtures and CLI options (`--known-bugs`, `--keep-test-data`); each panel also has its own `conftest.py` for role-specific login/API fixtures |
| `utils/` | API clients and helpers per panel (`api_client.py`, `oem_panel_api.py`, `fc_panel_api.py`, `role_panel_api.py`, `permit_holder_api.py`, `oem_mgmt_api.py`, …), plus `accessibility.py` (axe-core wrapper), `cleanup.py`, `data_generator.py` |
| `config/`, `data/` | Environment config, test data (`data/files/test.pdf` is the upload fixture) |
| `Testcases/` | Risk-based test case catalogue (CSV) |
| `specs/` | Test plans and test reports (Markdown), one per panel/module, plus `specs/evidence/` for screenshots |
| `bug_report.md` | Functional/API defect log (BUG-NNN), each linked to its `xfail` test |
| `ui_ux_bug_report.md` | Accessibility/UX defect log (UX-NNN) from the WCAG audit |
| `jira bulk upload - *.csv` | Defect exports formatted for Jira's CSV importer |

### Panel-specific notes

- **OEM panel** (`tests/oem_panel/`): signs in with `OEM_USERNAME` / `OEM_PASSWORD`. Device tests build their own
  data: the admin API creates a Device Model, Firmware and SIM Module for the OEM, the OEM API registers devices,
  and everything is deleted afterwards (devices first). Tests that touch inventory run on one xdist worker
  (`xdist_group("oem-devices")`). Leftovers the application cannot delete: allocation history rows (status
  "returned"), and one OEM per run of the forced-password test.
- **Fitment Centre panel** (`tests/fc_panel/`): signs in with `FC_USERNAME` / `FC_PASSWORD`; covers dashboard,
  operations (installation workflow), reports and helpdesk.
- **Role panels** (`tests/role_panels/`): Driver, RTO Inspector and RTO Officer panels, plus cross-role access/
  isolation checks, in one shared `conftest.py`.
- **Permit Holder panel** (`tests/permit_holder/`): signs in with `PERMIT_HOLDER_USERNAME` / `PERMIT_HOLDER_PASSWORD`
  ("Fleet Owner" in the UI); covers vehicle ownership isolation, watchlist CRUD and cross-owner isolation. See
  `specs/permit-holder-test-plan.md` for the full exploration.
- **UI/UX audit** (`tests/ui_ux/`): runs `utils/accessibility.py`'s axe-core scan against key screens per panel;
  failures map to entries in `ui_ux_bug_report.md`.
