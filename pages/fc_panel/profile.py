"""
Fitment Centre "My Profile" (`/fc/profile`).

Verified by manual exploration 2026-11-05: identical structure to `pages.oem_panel.profile.OemProfilePage`
(same heading, same two tabs, same field labels) - only the path differs, so this is a thin subclass.
`ChangePasswordForm` is reused directly from the OEM module (it is keyed off field labels, not a role).
"""

from pages.oem_panel.profile import ChangePasswordForm, OemProfilePage

__all__ = ["FcProfilePage", "ChangePasswordForm"]


class FcProfilePage(OemProfilePage):
    PATH = "/fc/profile"
