"""
Staff permissions – API level.  Plan: specs/staff-permissions-test-plan.md

When a TC staff account is created, the admin ticks some of the 63 permissions. These tests prove, call by
call, that the SERVER honours them – "positive" (the permission opens its feature) and "negative" (without
it the feature stays closed, and nothing else opens by accident):

  test_staff_without_permissions_*     no permission  -> only the open features, every gated one is refused
  test_only_permission_*[P]            exactly P      -> P's features open, every other gated feature refused
  test_removing_permission_*[P]        all except P   -> P's features refused, everything else still open
  test_*_permission_has_effect[P]      a permission that should open something but does not (BUG-015)
  test_unprotected_*[probe]            a feature that opens without its permission (BUG-014)

Probes are harmless (see utils/permissions_matrix.py): GET lists, empty POSTs (403 before validation) and
status changes on throw-away "Auto…" records. A call is "allowed" when it is not answered with 403.
"""

import pytest

from utils.permission_codes import CODES
from utils.permissions_matrix import (
    CHECKED,
    INEFFECTIVE,
    NOT_EXERCISED,
    OPEN,
    PROBE_BY_KEY,
    PROBES,
    RESTRICTED,
    UNGATED,
)
from utils.staff_lab import StaffLab

pytestmark = [pytest.mark.permissions, pytest.mark.api, pytest.mark.critical]

def permission_codes() -> list[str]:
    """The 63 permission codes (static list so test ids exist before any login)."""
    return CODES


def _probes_of(code: str):
    return [p for p in CHECKED if p.permission == code]


PROBED_CODES = [c for c in permission_codes() if _probes_of(c)]


def _describe(lab: StaffLab, probes_status: dict[str, int], keys: list[str]) -> str:
    return ", ".join(f"{k}={probes_status[k]}" for k in keys)


# ── The catalogue itself ──────────────────────────────────────────────────────

def test_permission_catalogue_matches(staff_lab: StaffLab) -> None:
    """The permissions offered by the server are exactly the 63 these tests cover."""
    assert sorted(staff_lab.permission_ids) == sorted(CODES), (
        "The permission list changed – update utils/permission_codes.py and utils/permissions_matrix.py"
    )


def test_every_permission_is_covered_or_explained() -> None:
    """Every permission has a probe, is a documented deviation, or has a stated reason it cannot be exercised."""
    covered = {p.permission for p in CHECKED} | {PROBE_BY_KEY[k].permission for k in list(INEFFECTIVE) + list(UNGATED)}
    unexplained = [c for c in CODES if c not in covered and c not in NOT_EXERCISED]
    assert not unexplained, f"Permissions with neither a probe nor a reason: {unexplained}"


# ── No permission at all ──────────────────────────────────────────────────────

def test_staff_without_permissions_are_refused_every_gated_feature(staff_lab: StaffLab) -> None:
    staff_lab.grant([])
    status = staff_lab.statuses(CHECKED)

    allowed = [k for k, s in status.items() if s != 403]
    assert not allowed, f"Staff with NO permissions reached gated features: {_describe(staff_lab, status, allowed)}"


def test_staff_without_permissions_can_use_the_open_features(staff_lab: StaffLab) -> None:
    """Features with no permission of their own stay usable (dashboard, PIS lists, helpdesk …)."""
    staff_lab.grant([])
    status = staff_lab.statuses(OPEN)

    refused = [k for k, s in status.items() if s == 403]
    assert not refused, f"Open features were refused to staff: {_describe(staff_lab, status, refused)}"


def test_staff_can_never_use_transport_commissioner_only_features(staff_lab: StaffLab) -> None:
    """Even with every permission ticked, TC-only features (announcements, system configuration …) stay closed."""
    staff_lab.grant(permission_codes())
    status = staff_lab.statuses(RESTRICTED)

    reached = [k for k, s in status.items() if s != 403]
    assert not reached, f"Staff reached TC-only features: {_describe(staff_lab, status, reached)}"


# ── One permission at a time ──────────────────────────────────────────────────

@pytest.mark.parametrize("code", PROBED_CODES)
def test_only_permission_opens_only_its_feature(staff_lab: StaffLab, code: str) -> None:
    """Positive + negative: with just `code`, its features open and every other gated feature is refused."""
    own = _probes_of(code)

    staff_lab.grant([code])
    status = staff_lab.statuses(CHECKED)

    own_keys = {p.key for p in own}
    refused_own = [k for k in own_keys if status[k] == 403]
    leaked = [k for k, s in status.items() if k not in own_keys and s != 403]
    assert not refused_own, f"{code} did NOT open its feature: {_describe(staff_lab, status, refused_own)}"
    assert not leaked, f"{code} also opened unrelated features: {_describe(staff_lab, status, leaked)}"


@pytest.mark.parametrize("code", PROBED_CODES)
def test_removing_permission_closes_only_its_feature(staff_lab: StaffLab, code: str) -> None:
    """Negative + positive: with everything EXCEPT `code`, its features are refused and all others stay open."""
    own = _probes_of(code)

    staff_lab.grant_all_except(code)
    status = staff_lab.statuses(CHECKED)

    own_keys = {p.key for p in own}
    still_open = [k for k in own_keys if status[k] != 403]
    wrongly_closed = [k for k, s in status.items() if k not in own_keys and s == 403]
    assert not still_open, f"Without {code} the feature is STILL open: {_describe(staff_lab, status, still_open)}"
    assert not wrongly_closed, f"Removing {code} closed unrelated features: {_describe(staff_lab, status, wrongly_closed)}"


# ── Permissions that should open something but do not (BUG-015) ───────────────

INEFFECTIVE_PERMISSIONS = sorted({PROBE_BY_KEY[k].permission for k in INEFFECTIVE})


@pytest.mark.parametrize("code", INEFFECTIVE_PERMISSIONS)
@pytest.mark.xfail(reason="BUG-015: the permission is offered in the staff form but the API still refuses staff", strict=False)
def test_permission_has_effect(staff_lab: StaffLab, code: str) -> None:
    """A staff user holding `code` must be able to use the feature the permission describes."""
    staff_lab.grant([code])
    targets = [PROBE_BY_KEY[k] for k in INEFFECTIVE if PROBE_BY_KEY[k].permission == code]
    status = staff_lab.statuses(targets)

    refused = [k for k, s in status.items() if s == 403]
    assert not refused, f"{code} is granted but the feature is still refused: {_describe(staff_lab, status, refused)}"


# ── Features that open WITHOUT their permission (BUG-014) ─────────────────────

@pytest.mark.parametrize("key", sorted(UNGATED))
@pytest.mark.xfail(reason="BUG-014: the endpoint does not check the permission the UI requires", strict=False)
def test_unprotected_feature_requires_its_permission(staff_lab: StaffLab, key: str) -> None:
    staff_lab.grant([])
    probe = PROBE_BY_KEY[key]
    status = staff_lab.status(probe)

    assert status == 403, f"{key} answered {status} to a staff user without '{probe.permission}'"


# ── Every probed endpoint needs a login ───────────────────────────────────────

def test_endpoints_require_authentication(staff_lab: StaffLab) -> None:
    """AUTH-003: with no token at all, no probed read endpoint returns data (401, never 200)."""
    answered = {}
    for probe in (p for p in PROBES if not p.writes):
        response = staff_lab.admin.request(probe.method, staff_lab.url_for(probe), token=None, origin=probe.host)
        if response.status not in (401, 403):
            answered[probe.key] = response.status

    assert not answered, f"Endpoints answered without any token: {answered}"


# ── Revoking is immediate ─────────────────────────────────────────────────────

def test_revoking_a_permission_applies_to_an_already_issued_token(staff_lab: StaffLab) -> None:
    """The token issued while the permission was held stops working for that feature as soon as it is removed."""
    probe = PROBE_BY_KEY["oems_list"]

    staff_lab.grant(["oems.view"])
    assert staff_lab.status(probe) != 403, "oems.view did not open the OEM list"

    staff_lab.grant([])  # same token, permission removed
    assert staff_lab.status(probe) == 403, "A revoked permission still works with the old token"
