from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class FuelRequest(Document):
	def validate(self):
		self.populate_from_planning()
		self.populate_from_trip()
		self.populate_from_route_master()
		self.set_programme()
		self.calculate_amounts()
		self.validate_amounts()
		self.set_audit_fields()
		self.set_status()

	def on_submit(self):
		self.set_status()
		self.update_trip_reference()

	def on_update_after_submit(self):
		self.set_audit_fields()
		self.set_status()
		self.update_trip_reference()

	def on_cancel(self):
		self.status = "Cancelled"
		self.update_trip_reference()

	def populate_from_planning(self):
		if not self.transport_order or not frappe.db.exists("Transport Order", self.transport_order):
			return

		transport_order = frappe.get_doc("Transport Order", self.transport_order)
		assignment_row = next(
			(row for row in transport_order.vehicle_assignments or [] if row.name == self.planning_assignment),
			None,
		)

		if assignment_row:
			self.route_detail = self.route_detail or assignment_row.route_detail
			self.route_master = self.route_master or assignment_row.route_master
			self.customer = self.customer or assignment_row.customer
			self.vehicle = self.vehicle or assignment_row.vehicle
			self.driver = self.driver or assignment_row.driver
			self.trip = self.trip or assignment_row.trip
			self.lorry_receipt = self.lorry_receipt or assignment_row.lorry_receipt

		route_row = next(
			(row for row in transport_order.transport_order_details or [] if row.name == self.route_detail),
			None,
		)

		if route_row:
			self.route_master = self.route_master or route_row.route
			self.customer = self.customer or route_row.customer

	def populate_from_trip(self):
		if not self.trip:
			return

		trip = frappe.db.get_value(
			"Trip",
			self.trip,
			[
				"company",
				"lorry_receipt",
				"customer",
				"vehicle",
				"driver",
				"route_master",
				"distance_km",
			],
			as_dict=True,
		)

		if not trip:
			frappe.throw(_("Trip {0} was not found.").format(self.trip))

		self.company = trip.company
		self.lorry_receipt = trip.lorry_receipt
		self.customer = trip.customer
		self.vehicle = trip.vehicle
		self.driver = trip.driver
		self.route_master = trip.route_master
		self.distance_km = trip.distance_km

	def populate_from_route_master(self):
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
				"standard_fuel_allowance_liters",
			],
			as_dict=True,
		)
		if not route:
			frappe.throw(_("Route Master {0} was not found.").format(self.route_master))

		self.company = self.company or route.company
		self.distance_km = flt(self.distance_km) or flt(route.distance_km)

		if not flt(self.diesel_to_be_given_liters) and not flt(self.average_kmpl):
			self.diesel_to_be_given_liters = flt(route.standard_fuel_allowance_liters)

	def set_programme(self):
		if self.programme:
			return
		if not self.route_master:
			return

		route = frappe.db.get_value(
			"Route Master",
			self.route_master,
			["source_location", "destination_location"],
			as_dict=True,
		)
		if not route:
			return

		source = (route.source_location or "").strip()
		destination = (route.destination_location or "").strip()
		self.programme = " / ".join(value for value in (source, destination) if value)

	def calculate_amounts(self):
		if flt(self.average_kmpl) and flt(self.distance_km):
			self.diesel_to_be_given_liters = round(
				flt(self.distance_km) / flt(self.average_kmpl),
				6,
			)

		if flt(self.diesel_to_be_given_liters) and not flt(self.requested_qty_liters):
			self.requested_qty_liters = flt(self.diesel_to_be_given_liters)

		self.diesel_balance_liters = round(
			flt(self.diesel_carry_forward_liters)
			- flt(self.diesel_given_liters)
			+ flt(self.diesel_to_be_given_liters),
			6,
		)

		if flt(self.fuel_rate_per_liter):
			if flt(self.requested_qty_liters) and not flt(self.requested_amount):
				self.requested_amount = flt(self.requested_qty_liters) * flt(self.fuel_rate_per_liter)

			if flt(self.approved_qty_liters) and not flt(self.approved_amount):
				self.approved_amount = flt(self.approved_qty_liters) * flt(self.fuel_rate_per_liter)

			if flt(self.disbursed_qty_liters) and not flt(self.disbursed_amount):
				self.disbursed_amount = flt(self.disbursed_qty_liters) * flt(self.fuel_rate_per_liter)

		if self.docstatus == 1 and self.approval_status == "Approved":
			self.approved_qty_liters = flt(self.approved_qty_liters) or flt(self.requested_qty_liters)
			self.approved_amount = flt(self.approved_amount) or flt(self.requested_amount)

	def validate_amounts(self):
		if not self.trip and not self.vehicle:
			frappe.throw(_("Select a Trip or Vehicle before saving the Fuel Request."))

		if flt(self.requested_qty_liters) <= 0 and flt(self.requested_amount) <= 0:
			frappe.throw(_("Enter either requested liters or requested amount."))

		for fieldname, label in {
			"fuel_rate_per_liter": _("Fuel Rate per Liter"),
			"average_kmpl": _("AVG (KM/L)"),
			"diesel_given_liters": _("Diesel Given"),
			"diesel_to_be_given_liters": _("Diesel To Be Given"),
			"requested_qty_liters": _("Requested Quantity"),
			"requested_amount": _("Requested Amount"),
			"approved_qty_liters": _("Approved Quantity"),
			"approved_amount": _("Approved Amount"),
			"disbursed_qty_liters": _("Disbursed Quantity"),
			"disbursed_amount": _("Disbursed Amount"),
		}.items():
			if flt(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative.").format(label))

		if self.load_status and self.load_status not in {"EM", "LO"}:
			frappe.throw(_("Filled / Not Filled must be either EM or LO."))

		if self.approval_status == "Approved":
			if flt(self.approved_qty_liters) > flt(self.requested_qty_liters) and flt(self.requested_qty_liters):
				frappe.throw(_("Approved liters cannot exceed requested liters."))

			if flt(self.approved_amount) > flt(self.requested_amount) and flt(self.requested_amount):
				frappe.throw(_("Approved amount cannot exceed requested amount."))

		if self.approval_status == "Rejected":
			self.approved_qty_liters = 0
			self.approved_amount = 0
			self.disbursed_qty_liters = 0
			self.disbursed_amount = 0
			self.disbursement_status = "Pending"

		if flt(self.disbursed_qty_liters) and flt(self.approved_qty_liters):
			if flt(self.disbursed_qty_liters) > flt(self.approved_qty_liters):
				frappe.throw(_("Disbursed liters cannot exceed approved liters."))

		if flt(self.disbursed_amount) and flt(self.approved_amount):
			if flt(self.disbursed_amount) > flt(self.approved_amount):
				frappe.throw(_("Disbursed amount cannot exceed approved amount."))

	def set_audit_fields(self):
		previous = self.get_doc_before_save()

		if self.docstatus != 1:
			return

		if self.approval_status in {"Approved", "Rejected"}:
			if not previous or previous.approval_status != self.approval_status:
				self.approved_by = frappe.session.user
				self.approval_date = now_datetime()

		if self.disbursement_status in {"Partially Disbursed", "Disbursed"}:
			if not previous or previous.disbursement_status != self.disbursement_status:
				self.disbursed_on = now_datetime()

	def set_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
		elif self.docstatus == 0:
			self.status = "Draft"
		elif self.approval_status == "Rejected":
			self.status = "Rejected"
		elif self.approval_status == "Pending":
			self.status = "Pending Approval"
		elif self.disbursement_status == "Disbursed":
			self.status = "Disbursed"
		elif self.disbursement_status == "Partially Disbursed":
			self.status = "Partially Disbursed"
		else:
			self.status = "Approved"

	def update_trip_reference(self):
		if not self.trip or not frappe.db.exists("Trip", self.trip):
			return

		latest_request = frappe.db.get_value(
			"Fuel Request",
			{
				"trip": self.trip,
				"docstatus": ["!=", 2],
			},
			"name",
			order_by="modified desc",
		)
		value = latest_request or ""

		frappe.db.set_value("Trip", self.trip, "latest_fuel_request", value, update_modified=False)
