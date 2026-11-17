"""
Known defects of the OEM Management module (details and evidence in bug_report.md).

A test that exercises behaviour broken by one of these is marked with the matching `xfail`: it documents the
defect, keeps the suite green, and reports XPASS the day the defect is fixed (then drop the marker).
"""

import pytest


def _bug(bug_id: str, why: str, run: bool = True):
    return pytest.mark.xfail(reason=f"{bug_id}: {why}", strict=False, run=run)


DELETE_BROKEN = _bug(
    "BUG-021", "Delete from the UI sends no oem_id, so the server answers 422 'Select an OEM.' and nothing is deleted"
)
MODEL_UPDATE_BROKEN = _bug(
    "BUG-022", "Updating a Device Model from the UI always fails with 'Select an OEM.' (multipart PATCH is not read by the server)"
)
NO_PAGINATION = _bug(
    "BUG-024", "Lists show only the first 10 records and have no pagination; search/filter only see those 10"
)
FIRMWARE_DASHES = _bug("BUG-025", "Firmware list/view show '-' for the OEM and Part No instead of the real values")
CERT_TYPES = _bug(
    "BUG-026", "The form says the TAC certificate may be PDF, JPG, JPEG or PNG but the server accepts PDF only"
)
FIRMWARE_MODEL_500 = _bug("BUG-027", "A non-numeric device_model_id crashes the server (HTTP 500) instead of a 422")
ORPHANED_FIRMWARE = _bug(
    "BUG-029",
    "Deleting a device model that has firmware succeeds and leaves the firmware orphaned (and undeletable, 403). "
    "Not run by default because it leaves an orphan record every time - run with: pytest --runxfail -k deleting_a_model",
    run=False,
)
UNSTABLE_SORT = _bug(
    "BUG-030",
    "The lists are sorted by creation time only, so records created in the same second can appear on two pages "
    "and others on none (reproducible for Device Models)",
)
INACTIVE_OEM_ACCEPTED = _bug(
    "BUG-045", "A Device Model can be created for a suspended or blacklisted OEM (the OEM dropdown offers them and the server accepts)"
)
OEM_DROPDOWN_CAPPED = _bug(
    "BUG-046", "The OEM dropdown of the Device Model form requests per_page=100 and never loads more, so older OEMs cannot be chosen"
)
NAME_STAYS_RESERVED = _bug(
    "BUG-031",
    "After a Device Model / Firmware is deleted its name / version stays reserved: it can never be used again",
)
