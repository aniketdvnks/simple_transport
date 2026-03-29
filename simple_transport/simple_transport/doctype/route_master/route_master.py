from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RouteMaster(Document):
	def validate(self):
		if not self.source_location or not self.destination_location:
			frappe.throw(_("Source and destination are required for a route."))

		self.company = self.company or frappe.defaults.get_user_default("Company")
		self.route_code = (self.route_code or self.get_route_code()).upper()
		self.route_name = f"{self.source_location} -> {self.destination_location}"

		if self.source_location.strip().lower() == self.destination_location.strip().lower():
			frappe.throw(_("Source and destination cannot be the same."))

		if flt(self.distance_km) <= 0:
			frappe.throw(_("Distance in KM must be greater than zero."))

		for fieldname, label in {
			"standard_rate_per_mt": _("Standard Rate per MT"),
			"standard_fuel_allowance_liters": _("Standard Fuel Allowance"),
			"toll_estimate": _("Toll Estimate"),
		}.items():
			if flt(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative.").format(label))

	def get_route_code(self) -> str:
		base_code = f"{self.abbreviate(self.source_location)}-{self.abbreviate(self.destination_location)}"
		candidate = base_code
		counter = 1

		while frappe.db.exists(
			"Route Master",
			{
				"route_code": candidate,
				"name": ["!=", self.name or ""],
			},
		):
			counter += 1
			candidate = f"{base_code}-{counter}"

		return candidate

	@staticmethod
	def abbreviate(value: str) -> str:
		tokens = re.findall(r"[A-Za-z0-9]+", value or "")
		if not tokens:
			return "ROUTE"

		if len(tokens) == 1:
			return tokens[0][:3].upper()

		return "".join(token[0].upper() for token in tokens[:3])
