"""Fitment Centre Command Center (`/fc/command-center`) - same screen as the OEM panel's, only the path differs."""

from pages.oem_panel.command_center import CommandCenterPage


class FcCommandCenterPage(CommandCenterPage):
    PATH = "/fc/command-center"
