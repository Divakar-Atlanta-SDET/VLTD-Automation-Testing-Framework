"""
Fitment Centre "Operations" pages: Live Tracking, Alerts, Geofences, Trip Playback.

Today's exploration (see `specs/fitment-centre-test-plan.md`) found these to be the same screens, same headings,
same DOM structure as the OEM panel's equivalents (`pages/oem_panel/tracking.py`) - only the path differs - so each
class here subclasses the OEM one and overrides only `PATH`. Do not assume this means identical *behaviour*: BUG-078
and BUG-082 already show the FC role gets 403s the OEM's own pages mask or share, so tests must still verify the FC
session directly rather than relying on OEM coverage alone.
"""

from pages.oem_panel.tracking import AlertsPage, GeofencesPage, LiveTrackingPage, TripPlaybackPage


class FcLiveTrackingPage(LiveTrackingPage):
    PATH = "/fc/live-tracking"


class FcAlertsPage(AlertsPage):
    PATH = "/fc/alerts"


class FcGeofencesPage(GeofencesPage):
    PATH = "/fc/geofences"


class FcTripPlaybackPage(TripPlaybackPage):
    PATH = "/fc/trip-playback"
