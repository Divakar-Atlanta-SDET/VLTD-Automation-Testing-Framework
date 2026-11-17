"""Shared behaviour of the Fitment Centre panel pages (`/fc/...`): open by path, wait for the heading, custom selects.

Identical mechanics to `pages.oem_panel.base.OemPanelPage` - only the paths differ per page, so this subclasses it
rather than duplicating `choose`, `options_of`, `row_with` and `expect_counters`. `open_profile` is overridden to
return the Fitment Centre's own profile page object (`/fc/profile`), not the OEM one.
"""

from pages.oem_panel.base import OemPanelPage


class FcPanelPage(OemPanelPage):
    def open_profile(self) -> "FcProfilePage":
        from pages.fc_panel.profile import FcProfilePage  # avoid a circular import

        self.open_account_menu()
        self.page.get_by_role("menuitem", name="Profile").click()
        return FcProfilePage(self.page).wait_until_open()
