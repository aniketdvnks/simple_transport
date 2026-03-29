from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class FuelRequest(Document):
	def validate(self):
		self.populate_from_trip()
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

	def calculate_amounts(self):
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
		if flt(self.requested_qty_liters) <= 0 and flt(self.requested_amount) <= 0:
			frappe.throw(_("Enter either requested liters or requested amount."))

		for fieldname, label in {
			"fuel_rate_per_liter": _("Fuel Rate per Liter"),
			"requested_qty_liters": _("Requested Quantity"),
			"requested_amount": _("Requested Amount"),
			"approved_qty_liters": _("Approved Quantity"),
			"approved_amount": _("Approved Amount"),
			"disbursed_qty_liters": _("Disbursed Quantity"),
			"disbursed_amount": _("Disbursed Amount"),
		}.items():
			if flt(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative.").format(label))

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
