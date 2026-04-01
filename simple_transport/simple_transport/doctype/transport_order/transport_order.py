# Copyright (c) 2026, DVNKS Systems Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import Counter

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from simple_transport.vehicle_status import IDLE_VEHICLE_STATUS


class TransportOrder(Document):
	def validate(self):
		self.validate_details()
		self.validate_vehicle_assignments()

	def validate_details(self):
		if not self.transport_order_details:
			return

		for row in self.transport_order_details:
			if not row.route:
				frappe.throw(_("Route is required in row {0}.").format(row.idx))

			if flt(row.no_of_vehicles) < 0:
				frappe.throw(_("No Of Vehicles cannot be negative in row {0}.").format(row.idx))

			if flt(row.qty_in_mt) < 0:
				frappe.throw(_("Qty in MT cannot be negative in row {0}.").format(row.idx))

	def validate_vehicle_assignments(self):
		if not self.vehicle_assignments:
			return

		detail_map = {row.name: row for row in self.transport_order_details}
		vehicle_counter = Counter()
		route_counter = Counter()
		route_capacity_counter = Counter()

		for row in self.vehicle_assignments:
			if not row.route_detail:
				frappe.throw(_("Route mapping is missing for assigned vehicle {0}.").format(row.vehicle))

			route_detail = detail_map.get(row.route_detail)
			if not route_detail:
				frappe.throw(
					_("Assigned vehicle {0} is linked to an invalid transport-order route.").format(
						row.vehicle
					)
				)

			row.route_master = route_detail.route
			row.customer = route_detail.customer

			if not row.vehicle:
				frappe.throw(_("Vehicle is required in the Vehicle Assignments table."))

			vehicle_details = frappe.db.get_value(
				"Vehicle",
				row.vehicle,
				["employee", "st_vehicle_capacity_mt", "st_operational_status"],
				as_dict=True,
			)
			if not vehicle_details:
				frappe.throw(_("Vehicle {0} was not found.").format(row.vehicle))

			assigned_capacity_before = flt(route_capacity_counter[row.route_detail])
			route_qty_in_mt = flt(route_detail.qty_in_mt)
			if route_qty_in_mt and assigned_capacity_before >= route_qty_in_mt:
				frappe.throw(
					_(
						"Assigned vehicle capacity already covers the planned weight for route {0}."
					).format(route_detail.route)
				)

			row.driver = vehicle_details.employee
			row.vehicle_capacity_mt = flt(vehicle_details.st_vehicle_capacity_mt)
			row.vehicle_status = vehicle_details.st_operational_status or IDLE_VEHICLE_STATUS
			row.assigned_on = row.assigned_on or now_datetime()
			row.assigned_by = row.assigned_by or frappe.session.user

			if route_qty_in_mt and flt(row.vehicle_capacity_mt) <= 0:
				frappe.throw(
					_("Vehicle {0} must have Capacity (MT) set before planning against route {1}.").format(
						row.vehicle, route_detail.route
					)
				)

			vehicle_counter[row.vehicle] += 1
			if vehicle_counter[row.vehicle] > 1:
				frappe.throw(
					_("Vehicle {0} has been planned more than once on this Transport Order.").format(
						row.vehicle
					)
				)

			existing_planning = frappe.db.sql(
				"""
				select assignment.parent
				from `tabTransport Order Vehicle Assignment` assignment
				inner join `tabTransport Order` transport_order on transport_order.name = assignment.parent
				where assignment.vehicle = %s
					and assignment.parent != %s
					and transport_order.date = %s
				limit 1
				""",
				(row.vehicle, self.name or "", self.date),
				as_dict=True,
			)
			if existing_planning:
				frappe.throw(
					_("Vehicle {0} is already planned in Transport Order {1}.").format(
						row.vehicle, existing_planning[0].parent
					)
				)

			route_counter[row.route_detail] += 1
			route_capacity_counter[row.route_detail] += flt(row.vehicle_capacity_mt)
			required_vehicles = flt(route_detail.no_of_vehicles)
			if not route_qty_in_mt and required_vehicles and route_counter[row.route_detail] > required_vehicles:
				frappe.throw(
					_(
						"Assigned vehicles for route {0} cannot exceed the required count of {1}."
					).format(route_detail.route, int(required_vehicles))
				)


def get_existing_transport_order_for_date(order_date=None) -> str | None:
	order_date = getdate(order_date)
	existing_orders = frappe.get_all(
		"Transport Order",
		filters={"date": order_date},
		fields=["name"],
		order_by="modified desc, creation desc",
		limit=1,
	)
	return existing_orders[0].name if existing_orders else None


def ensure_transport_order_for_date(order_date=None) -> str:
	order_date = getdate(order_date)
	existing_order = get_existing_transport_order_for_date(order_date)
	if existing_order:
		return existing_order

	transport_order = frappe.get_doc(
		{
			"doctype": "Transport Order",
			"date": order_date,
		}
	)
	transport_order.insert(ignore_permissions=True)
	return transport_order.name
