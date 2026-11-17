"""
OEM "Tracking & GIS" pages: Live Tracking (with the Watchlist tab), Alerts (with the Rules tab), Geofences, Trip Playback.

All four are map screens with a side panel. The side panels have landmarks of their own (a second `main` and
`complementary` regions), so everything is looked up by role and visible text instead of by region.
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.oem_panel.base import OemPanelPage


class LiveTrackingPage(OemPanelPage):
    PATH = "/oem/live-tracking"
    HEADING = "Live Vehicle Tracking"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.fleet_tab = page.get_by_role("button", name="Fleet", exact=True)
        self.watchlist_tab = page.get_by_role("button", name="Watchlist", exact=True)
        self.new_watchlist_button = page.get_by_role("button", name="New", exact=True)
        self.name_box = page.get_by_role("textbox", name=re.compile(r"^(New watchlist name|Watchlist name)$"))
        self.description_box = page.get_by_role("textbox", name="Description (optional)")
        self.watchlist_select = page.get_by_role("combobox", name="Select watchlist")
        self.rename_button = page.get_by_role("button", name="Rename watchlist")
        self.delete_button = page.get_by_role("button", name="Delete watchlist")

    def open_watchlists(self) -> "LiveTrackingPage":
        self.open()
        self.watchlist_tab.click()
        expect(self.new_watchlist_button).to_be_visible()
        return self

    # watchlists
    def create_watchlist(self, name: str, description: str | None = None) -> None:
        self.new_watchlist_button.click()
        self.name_box.fill(name)
        if description is not None:
            self.description_box.fill(description)
        self.page.get_by_role("button", name="Create", exact=True).click()

    def select_watchlist(self, name: str) -> None:
        self.choose("Select watchlist", re.compile(rf"^{re.escape(name)}"))

    def expect_selected(self, text: "str | re.Pattern") -> None:
        expect(self.watchlist_select).to_contain_text(text)

    def rename_watchlist(self, name: str) -> None:
        self.rename_button.click()
        self.name_box.fill(name)
        self.page.get_by_role("button", name="Save", exact=True).click()

    def confirm_delete(self, name: str) -> None:
        self.delete_button.click()
        expect(self.page.get_by_text(re.compile(rf"Delete watchlist\?\s*.{re.escape(name)}.\s*and its"))).to_be_visible()
        self.page.get_by_role("button", name="Delete", exact=True).click()

    def watchlist_options(self) -> list[str]:
        return self.options_of("Select watchlist")


class AlertsPage(OemPanelPage):
    PATH = "/oem/alerts"
    HEADING = "Alert Monitoring"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.rules_tab = page.get_by_role("button", name="Rules", exact=True)
        self.create_rule_button = page.get_by_role("button", name="Create Alert Rule", exact=True)
        self.rule_name_box = page.get_by_placeholder("Operational rule name")
        self.speed_limit_box = page.get_by_role("spinbutton")
        self.submit_rule_button = page.get_by_role("button", name="Create Rule", exact=True)

    def open_resolved(self) -> "AlertsPage":
        self.open()
        self.page.get_by_role("button", name="Resolved", exact=True).click()
        return self

    def open_rules(self) -> "AlertsPage":
        self.open()
        self.rules_tab.click()
        expect(self.create_rule_button).to_be_visible()
        return self

    def create_overspeed_rule(self, name: str, limit: int, scope: str | None = None) -> None:
        """Fill and submit the Create Alert Rule form (type Overspeed, severity High, scope 'All vehicles' unless `scope` is given)."""
        self.create_rule_button.click()
        self.rule_name_box.fill(name)
        self.speed_limit_box.first.fill(str(limit))
        if scope:
            self.page.get_by_role("combobox").filter(has_text=re.compile(r"^\s*All vehicles\s*$")).click()
            self.page.locator("[role=option]:visible").filter(has_text=re.compile(rf"^\s*{re.escape(scope)}\s*$")).first.click()
        self.submit_rule_button.click()

    def rule(self, name: str) -> Locator:
        return self.page.get_by_text(name, exact=True)


class GeofencesPage(OemPanelPage):
    PATH = "/oem/geofences"
    HEADING = "Geofence Alerts"

    # Drag offsets (pixels from the middle of the map) that draw a shape large enough to be accepted.
    DRAG = {"Circle": (130, 70), "Rectangle": (130, 70), "Freestyle": (130, 70)}

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.zones_tab = page.get_by_role("button", name="Geofences", exact=True)
        self.create_button = page.get_by_role("button", name="Create Geofence", exact=True)
        self.name_box = page.get_by_placeholder("e.g. Central depot boundary")
        self.save_button = page.get_by_role("button", name="Save", exact=True)
        self.search_box = page.get_by_placeholder("Search geofences")
        self.type_filter = page.get_by_role("combobox", name="Geofence type filter")
        self.status_filter = page.get_by_role("combobox", name="Geofence status filter")
        self.map = page.locator(".gm-style").first

    def open_zones(self) -> "GeofencesPage":
        self.open()
        self.zones_tab.click()
        expect(self.create_button).to_be_visible()
        return self

    def start_create(self) -> None:
        self.create_button.click()
        expect(self.name_box).to_be_visible()

    def draw(self, shape: str = "Circle") -> None:
        """Pick a drawing tool and drag across the middle of the map (the circle is dragged from its centre outwards)."""
        # the map first tries a vector map, fails and redraws as a raster map: a drag made before that is lost, so wait for the map tiles
        self.page.wait_for_function(
            "() => [...document.querySelectorAll('.gm-style img')].filter(i => i.complete && i.naturalWidth > 0).length >= 4", timeout=20_000,
        )
        self.page.get_by_role("button", name=shape, exact=True).click()
        expect(self.page.get_by_text(re.compile(r"^Drag "))).to_be_visible()  # the tool is armed; dragging earlier draws nothing
        expect(self.map).to_be_visible()
        box = self.map.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        dx, dy = self.DRAG[shape]
        for _ in range(3):  # under load the map now and then ignores a drag; Save (once the name is typed) tells whether it was drawn
            self.page.mouse.move(x, y)
            self.page.mouse.down()
            self.page.mouse.move(x + dx / 3, y + dy / 3, steps=8)
            self.page.mouse.move(x + dx, y + dy, steps=8)
            self.page.mouse.up()
            if not self.name_box.input_value():
                return
            try:
                expect(self.save_button).to_be_enabled(timeout=2_000)
                return
            except AssertionError:
                continue

    def create(self, name: str, shape: str = "Circle") -> None:
        self.start_create()
        self.name_box.fill(name)
        self.draw(shape)
        self.save_button.click()

    def cancel_form(self) -> None:
        """Cancel asks 'Discard unsaved geofence?' first."""
        self.page.get_by_role("button", name="Cancel", exact=True).click()
        expect(self.page.get_by_text("Discard unsaved geofence?")).to_be_visible()

    def keep_editing(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).last.click()  # the dialog's button comes after the form's

    def discard(self) -> None:
        self.page.get_by_role("button", name="Discard", exact=True).click()

    def find(self, text: str) -> None:
        self.search_box.fill(text)

    def zone(self, name: str) -> Locator:
        """The list card of the zone with exactly this name ('X' and 'X Copy' are different cards)."""
        return self.page.get_by_role("article").filter(has=self.page.get_by_text(name, exact=True))

    def edit(self, name: str) -> None:
        self.zone(name).get_by_role("button", name="Edit geofence").click()

    def duplicate(self, name: str) -> None:
        self.zone(name).get_by_role("button", name="Duplicate geofence").click()

    def toggle(self, name: str) -> None:
        """Deactivate an active zone / activate an inactive one."""
        self.zone(name).get_by_role("button", name=re.compile(r"^(Deactivate|Activate) geofence$")).click()

    def delete(self, name: str) -> None:
        self.zone(name).get_by_role("button", name="Delete geofence").click()
        expect(self.page.get_by_text("Delete geofence?")).to_be_visible()

    def confirm_delete(self) -> None:
        self.page.get_by_role("button", name="Delete", exact=True).click()

    def cancel_delete(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).click()

    def choose_filter(self, combobox: Locator, option: str) -> None:
        combobox.click()
        self.page.locator("[role=option]:visible").filter(has_text=re.compile(rf"^\s*{re.escape(option)}\s*$")).first.click()


class TripPlaybackPage(OemPanelPage):
    PATH = "/oem/trip-playback"
    HEADING = "Historical Trip Playback"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.vehicle_box = page.get_by_role("textbox", name=re.compile("vehicle number", re.I))
        self.load_button = page.get_by_role("button", name="Load range", exact=True)
