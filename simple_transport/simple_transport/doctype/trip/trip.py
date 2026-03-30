from __future__ import annotations

import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, getdate

from simple_transport.access import is_operations_manager, is_vehicle_assigned_to_manager


ACTIVE_TRIP_STATUSES = {
    "Planned",
    "Ready for Dispatch",
    "At Loading Point",
    "In Transit",
    "At Unloading Point",
    "On Hold",
}

VEHICLE_STATUS_MAP = {
    "Planned": "Available",
    "Ready for Dispatch": "Available",
    "At Loading Point": "At Loading Point",
    "In Transit": "In Transit",
    "At Unloading Point": "At Unloading Point",
    "On Hold": "On Hold",
}


class Trip(Document):
    def validate(self):
        self.status = self.status or "Planned"
        self.populate_from_lorry_receipt()
        self.populate_from_route()
        self.populate_from_vehicle()
        self.validate_driver()
        self.validate_operation_manager()
        # self.validate_vehicle_assignment()
        self.validate_dates()
        self.validate_planned_tonnage()
        self.validate_active_trip_conflicts()
        self.calculate_amounts()

    def on_update(self):
        self.sync_vehicle_state()
        self.sync_lorry_receipt_reference()

    def on_trash(self):
        self.sync_vehicle_state(exclude_current=True)
        self.sync_lorry_receipt_reference(clear=True)

    def populate_from_lorry_receipt(self):
        if not self.lorry_receipt:
            return

        receipt = frappe.db.get_value(
            "Lorry Receipt",
            self.lorry_receipt,
            [
                "docstatus",
                "company",
                "customer",
                "operation_manager",
                "route_master",
                "loading_point",
                "unloading_point",
                "distance_km",
                "vehicle",
                "driver",
                "vehicle_capacity_mt",
                "goods_description",
                "quantity_mt",
                "freight_rate_per_mt",
                "consignor_name",
                "consignor_contact_no",
                "consignor_address",
                "consignee_name",
                "consignee_contact_no",
                "consignee_address",
                "loading_supervisor_name",
                "remarks",
                "trip",
                "lr_date",
            ],
            as_dict=True,
        )

        if not receipt:
            frappe.throw(_("Lorry Receipt {0} was not found.").format(self.lorry_receipt))

        if receipt.docstatus != 1:
            frappe.throw(_("Lorry Receipt must be submitted before creating a Trip."))

        if receipt.trip and receipt.trip != self.name:
            frappe.throw(
                _("Lorry Receipt {0} is already linked with Trip {1}.").format(
                    self.lorry_receipt, receipt.trip
                )
            )

        self.company = self.company or receipt.company
        self.customer = receipt.customer
        self.operation_manager = self.operation_manager or receipt.operation_manager
        self.route_master = self.route_master or receipt.route_master
        self.loading_point = self.loading_point or receipt.loading_point
        self.unloading_point = self.unloading_point or receipt.unloading_point
        self.distance_km = self.distance_km or receipt.distance_km
        self.vehicle = self.vehicle or receipt.vehicle
        self.driver = self.driver or receipt.driver
        self.vehicle_capacity_mt = self.vehicle_capacity_mt or receipt.vehicle_capacity_mt
        self.chemical_name = self.chemical_name or receipt.goods_description
        self.planned_tonnage = self.planned_tonnage or receipt.quantity_mt
        self.freight_rate_per_mt = self.freight_rate_per_mt or receipt.freight_rate_per_mt
        self.trip_notes = self.trip_notes or receipt.remarks
        self.consignor_name = self.consignor_name or receipt.consignor_name or receipt.customer
        self.consignor_contact_no = self.consignor_contact_no or receipt.consignor_contact_no
        self.consignor_address = self.consignor_address or receipt.consignor_address
        self.consignee_name = self.consignee_name or receipt.consignee_name
        self.consignee_contact_no = self.consignee_contact_no or receipt.consignee_contact_no
        self.consignee_address = self.consignee_address or receipt.consignee_address
        self.loading_supervisor_name = (
            self.loading_supervisor_name or receipt.loading_supervisor_name
        )
        self.dispatch_date = self.dispatch_date or receipt.lr_date or self.dispatch_date

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
                "estimated_transit_hours",
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
        self.consignor_address = self.consignor_address or route.source_location
        self.consignee_name = self.consignee_name or route.destination_location
        self.consignee_address = self.consignee_address or route.destination_location
        self.distance_km = route.distance_km
        self.route_notes = self.route_notes or route.route_notes
        self.freight_rate_per_mt = self.freight_rate_per_mt or route.standard_rate_per_mt

        if route.estimated_transit_hours and self.dispatch_date and not self.expected_arrival_date:
            days = max(1, math.ceil(flt(route.estimated_transit_hours) / 24))
            self.expected_arrival_date = add_to_date(self.dispatch_date, days=days, as_string=True)

    def populate_from_vehicle(self):
        if not self.vehicle:
            return

        vehicle_details = frappe.db.get_value(
            "Vehicle",
            self.vehicle,
            ["employee", "st_vehicle_capacity_mt"],
            as_dict=True,
        )

        if not vehicle_details:
            frappe.throw(_("Vehicle {0} was not found.").format(self.vehicle))

        self.driver = self.driver or vehicle_details.employee
        self.vehicle_capacity_mt = flt(vehicle_details.st_vehicle_capacity_mt)

    def validate_driver(self):
        if not self.driver:
            return

        driver_details = frappe.db.get_value(
            "Employee",
            self.driver,
            ["status", "st_is_driver", "st_driving_license_valid_upto"],
            as_dict=True,
        )

        if not driver_details:
            frappe.throw(_("Employee {0} was not found.").format(self.driver))

        if driver_details.status != "Active":
            frappe.throw(_("Driver {0} must be Active.").format(self.driver))

        if not driver_details.st_is_driver:
            frappe.throw(_("Employee {0} is not marked as a transport driver.").format(self.driver))

        if (
            driver_details.st_driving_license_valid_upto
            and self.dispatch_date
            and getdate(driver_details.st_driving_license_valid_upto) < getdate(self.dispatch_date)
        ):
            frappe.throw(_("Driver license has expired for employee {0}.").format(self.driver))

    def validate_dates(self):
        if self.expected_arrival_date and self.dispatch_date:
            if getdate(self.expected_arrival_date) < getdate(self.dispatch_date):
                frappe.throw(_("Expected arrival date cannot be before dispatch date."))

        if self.actual_start_datetime and self.actual_end_datetime:
            if self.actual_end_datetime < self.actual_start_datetime:
                frappe.throw(_("Actual end time cannot be before actual start time."))

        if self.status == "Completed" and not self.actual_end_datetime:
            frappe.throw(_("Actual end time is required before a Trip can be marked Completed."))

    def validate_planned_tonnage(self):
        if flt(self.planned_tonnage) <= 0:
            frappe.throw(_("Assigned tonnage must be greater than zero."))

        if self.vehicle_capacity_mt and flt(self.planned_tonnage) > flt(self.vehicle_capacity_mt):
            frappe.throw(
                _("Assigned tonnage cannot exceed the vehicle capacity of {0} MT.").format(
                    self.vehicle_capacity_mt
                )
            )

    def validate_active_trip_conflicts(self):
        if self.status not in ACTIVE_TRIP_STATUSES:
            return

        for fieldname, label in {"vehicle": _("vehicle"), "driver": _("driver")}.items():
            value = self.get(fieldname)
            if not value:
                continue

            existing_trip = frappe.db.get_value(
                "Trip",
                {
                    fieldname: value,
                    "status": ["in", list(ACTIVE_TRIP_STATUSES)],
                    "name": ["!=", self.name or ""],
                },
            )
            if existing_trip:
                frappe.throw(
                    _("Another active Trip {0} already exists for this {1}.").format(
                        existing_trip, label
                    )
                )

    def calculate_amounts(self):
        self.estimated_revenue = flt(self.planned_tonnage) * flt(self.freight_rate_per_mt)
        self.total_expense_amount = sum(flt(row.amount) for row in self.expenses or [])

    def sync_vehicle_state(self, exclude_current: bool = False):
        if not self.vehicle or not frappe.db.exists("Vehicle", self.vehicle):
            return

        meta = frappe.get_meta("Vehicle")
        if not meta.has_field("st_current_trip") or not meta.has_field("st_operational_status"):
            return

        filters = {
            "vehicle": self.vehicle,
            "status": ["in", list(ACTIVE_TRIP_STATUSES)],
        }
        if exclude_current and self.name:
            filters["name"] = ["!=", self.name]

        active_trip = frappe.db.get_value(
            "Trip",
            filters,
            ["name", "status"],
            as_dict=True,
            order_by="modified desc",
        )

        values = {
            "st_current_trip": active_trip.name if active_trip else "",
            "st_operational_status": VEHICLE_STATUS_MAP.get(active_trip.status, "Available")
            if active_trip
            else "Available",
        }
        frappe.db.set_value("Vehicle", self.vehicle, values, update_modified=False)

    def sync_lorry_receipt_reference(self, clear: bool = False):
        previous = self.get_doc_before_save()
        if previous and previous.lorry_receipt and previous.lorry_receipt != self.lorry_receipt:
            if frappe.db.exists("Lorry Receipt", previous.lorry_receipt):
                if frappe.db.get_value("Lorry Receipt", previous.lorry_receipt, "trip") == self.name:
                    frappe.db.set_value(
                        "Lorry Receipt",
                        previous.lorry_receipt,
                        "trip",
                        "",
                        update_modified=False,
                    )

        if not self.lorry_receipt or not frappe.db.exists("Lorry Receipt", self.lorry_receipt):
            return

        value = "" if clear or self.status == "Cancelled" else self.name
        frappe.db.set_value("Lorry Receipt", self.lorry_receipt, "trip", value, update_modified=False)
