from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from simple_transport.access import is_operations_manager, is_vehicle_assigned_to_manager
from simple_transport.vehicle_status import ACTIVE_TRIP_STATUSES


class LorryReceipt(Document):
    def validate(self):
        self.populate_from_route()
        self.populate_contract_rate()
        self.populate_from_vehicle()
        self.validate_driver()
        self.validate_operation_manager()
        # self.validate_vehicle_assignment()
        self.validate_quantity()
        self.calculate_amounts()
        self.set_status()

    def on_submit(self):
        self.status = "Issued"
        self.sync_planning_assignment_reference()

    def on_cancel(self):
        if self.trip and frappe.db.exists("Trip", self.trip):
            frappe.throw(
                _("Cancel or delete linked Trip {0} before cancelling this Lorry Receipt.").format(
                    self.trip
                )
            )

        self.status = "Cancelled"
        self.sync_planning_assignment_reference(clear=True)

    def on_update(self):
        if self.docstatus == 1:
            self.sync_planning_assignment_reference()

    def on_trash(self):
        self.sync_planning_assignment_reference(clear=True)

    def populate_from_route(self):
        if not self.route_master:
            return

        route = frappe.db.get_value(
            "Route Master",
            self.route_master,
            [
                "company",
                "source_location",
                "destination_location",
                "distance_km",
                "standard_rate_per_mt",
                "route_notes",
            ],
            as_dict=True,
        )

        if not route:
            frappe.throw(_("Route Master {0} was not found.").format(self.route_master))

        self.company = self.company or route.company
        self.loading_point = self.loading_point or route.source_location
        self.unloading_point = self.unloading_point or route.destination_location
        self.distance_km = route.distance_km
        self.freight_rate_per_mt = self.freight_rate_per_mt or route.standard_rate_per_mt
        self.remarks = self.remarks or route.route_notes

    def populate_from_vehicle(self):
        if not self.vehicle:
            return

        vehicle = frappe.db.get_value(
            "Vehicle",
            self.vehicle,
            ["employee", "st_vehicle_capacity_mt"],
            as_dict=True,
        )
        if not vehicle:
            frappe.throw(_("Vehicle {0} was not found.").format(self.vehicle))

        self.driver = self.driver or vehicle.employee
        self.vehicle_capacity_mt = flt(vehicle.st_vehicle_capacity_mt)

    def populate_contract_rate(self):
        if flt(self.freight_rate_per_mt):
            return

        rate_details = get_contract_rate_details(
            customer=self.customer,
            route_master=self.route_master,
            material=self.goods_description,
            lr_date=self.lr_date,
        )
        if rate_details:
            self.freight_rate_per_mt = flt(rate_details.rate_per_mt)

    def validate_driver(self):
        if not self.driver:
            return

        driver = frappe.db.get_value(
            "Employee",
            self.driver,
            ["status", "st_is_driver", "st_driving_license_valid_upto"],
            as_dict=True,
        )
        if not driver:
            frappe.throw(_("Employee {0} was not found.").format(self.driver))

        if driver.status != "Active":
            frappe.throw(_("Driver {0} must be Active.").format(self.driver))

        if not driver.st_is_driver:
            frappe.throw(_("Employee {0} is not marked as a transport driver.").format(self.driver))

        if (
            driver.st_driving_license_valid_upto
            and self.lr_date
            and getdate(driver.st_driving_license_valid_upto) < getdate(self.lr_date)
        ):
            frappe.throw(_("Driver license has expired for employee {0}.").format(self.driver))

    def validate_operation_manager(self):
        if self.operation_manager and not is_operations_manager(self.operation_manager):
            frappe.throw(
                _("User {0} must have the ST Operation Manager role.").format(
                    self.operation_manager
                )
            )

    def validate_vehicle_assignment(self):
        if not self.operation_manager or not self.vehicle:
            return

        if not is_vehicle_assigned_to_manager(self.vehicle, self.operation_manager):
            frappe.throw(
                _("Vehicle {0} is not assigned to operation manager {1}.").format(
                    self.vehicle, self.operation_manager
                )
            )

        active_trip = frappe.db.get_value(
            "Trip",
            {
                "vehicle": self.vehicle,
                "status": ["in", list(ACTIVE_TRIP_STATUSES)],
                "name": ["!=", self.trip or ""],
            },
        )
        if active_trip:
            frappe.throw(_("Vehicle {0} is already on active Trip {1}.").format(self.vehicle, active_trip))

    def validate_quantity(self):
        if flt(self.quantity_mt) <= 0:
            frappe.throw(_("Quantity (MT) must be greater than zero."))

        if not flt(self.gross_weight_mt):
            self.gross_weight_mt = flt(self.quantity_mt)

        if flt(self.gross_weight_mt) and flt(self.gross_weight_mt) < flt(self.quantity_mt):
            frappe.throw(_("Gross weight cannot be less than net weight."))

        if self.vehicle_capacity_mt and flt(self.quantity_mt) > flt(self.vehicle_capacity_mt):
            frappe.throw(
                _("Quantity cannot exceed the vehicle capacity of {0} MT.").format(
                    self.vehicle_capacity_mt
                )
            )

    def calculate_amounts(self):
        self.freight_amount = flt(self.quantity_mt) * flt(self.freight_rate_per_mt)

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
        elif self.docstatus == 1:
            self.status = "Issued"
        else:
            self.status = "Draft"

    def sync_planning_assignment_reference(self, clear: bool = False):
        if not self.planning_assignment:
            return

        value = "" if clear or self.docstatus == 2 else self.name
        frappe.db.set_value(
            "Transport Order Vehicle Assignment",
            self.planning_assignment,
            "lorry_receipt",
            value,
            update_modified=False,
        )


def get_contract_rate_details(customer=None, route_master=None, material=None, lr_date=None):
    if not customer or not route_master:
        return None

    route = frappe.db.get_value(
        "Route Master",
        route_master,
        ["source_location", "destination_location"],
        as_dict=True,
    )
    if not route or not route.source_location or not route.destination_location:
        return None

    posting_date = getdate(lr_date) if lr_date else getdate()

    if material:
        rate_details = _find_contract_rate(
            customer=customer,
            posting_date=posting_date,
            source_location=route.source_location,
            destination_location=route.destination_location,
            material=material,
        )
        if rate_details:
            return rate_details

        rate_details = _find_contract_rate(
            customer=customer,
            posting_date=posting_date,
            source_location=route.source_location,
            destination_location=route.destination_location,
            blank_material_only=True,
        )
        if rate_details:
            return rate_details

    return _find_contract_rate(
        customer=customer,
        posting_date=posting_date,
        source_location=route.source_location,
        destination_location=route.destination_location,
    )


def _find_contract_rate(
    customer=None,
    posting_date=None,
    source_location=None,
    destination_location=None,
    material=None,
    blank_material_only=False,
):
    conditions = [
        "contract.docstatus = 1",
        "contract.party_type = 'Customer'",
        "contract.party_name = %s",
        "contract.status = 'Active'",
        "contract.start_date <= %s",
        "(contract.end_date is null or contract.end_date >= %s)",
        "detail.parenttype = 'Contract'",
        "detail.parentfield = 'custom_items'",
        "detail.`from` = %s",
        "detail.`to` = %s",
    ]
    values = [customer, posting_date, posting_date, source_location, destination_location]

    if material:
        conditions.append("ifnull(detail.cargo_type, '') = %s")
        values.append(material)
    elif blank_material_only:
        conditions.append("ifnull(detail.cargo_type, '') = ''")

    rows = frappe.db.sql(
        f"""
        select
            contract.name as contract,
            detail.idx as contract_detail_idx,
            detail.rate_per_mt,
            detail.qty,
            detail.no_of_days,
            detail.cargo_type as material
        from `tabContract` contract
        inner join `tabContract Details` detail on detail.parent = contract.name
        where {' and '.join(conditions)}
        order by ifnull(contract.end_date, '2199-12-31') desc, contract.modified desc, detail.idx asc
        limit 1
        """,
        values,
        as_dict=True,
    )
    return rows[0] if rows else None


@frappe.whitelist()
def get_contract_rate(customer=None, route_master=None, material=None, lr_date=None):
    rate_details = get_contract_rate_details(
        customer=customer,
        route_master=route_master,
        material=material,
        lr_date=lr_date,
    )

    if rate_details:
        return {
            "source": "Contract",
            "contract": rate_details.contract,
            "contract_detail_idx": rate_details.contract_detail_idx,
            "freight_rate_per_mt": flt(rate_details.rate_per_mt),
        }

    route = frappe.db.get_value(
        "Route Master",
        route_master,
        ["standard_rate_per_mt"],
        as_dict=True,
    )
    if route:
        return {
            "source": "Route Master",
            "freight_rate_per_mt": flt(route.standard_rate_per_mt),
        }

    return {
        "source": "",
        "freight_rate_per_mt": 0,
    }
