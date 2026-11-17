"""SIM Modules - /tc/oem-management/sim-modules (+ /new and /{id}/edit)."""

from pages.oem_management.base_oem_page import OemMgmtListPage
from utils.data_generator import SimModuleData


class SimModulesPage(OemMgmtListPage):
    SLUG = "sim-modules"
    LIST_HEADING = "SIM Modules"
    ADD_BUTTON = "Add SIM Module"
    ADD_HEADING = "Add SIM Module"
    EDIT_HEADING = "Edit SIM Module"
    SUBMIT_CREATE = "Create SIM Module"
    SUBMIT_UPDATE = "Update SIM Module"
    TABLE_NAME = "SIM Modules"
    VIEW_HEADING = "SIM Module Details"
    DELETE_HEADING = "Delete SIM Module"
    COLUMNS = ("Sr.No", "OEM", "OEM Code", "Manufacturer", "Module Name", "Operators", "SIM Type", "Status", "Actions")

    def fill_form(self, sim: SimModuleData, oem_name: str | None = None) -> None:
        if oem_name:
            self.choose_oem(oem_name)
        self.fill("SIM Manufacturer *", sim.sim_manufacturer)
        self.fill("Module Name *", sim.module_name)
        self.fill("Primary Operator", sim.primary_operator)
        self.fill("Primary SIM Type", sim.primary_sim_type)
        self.fill("Secondary Operator", sim.secondary_operator)
        self.fill("Secondary SIM Type", sim.secondary_sim_type)
