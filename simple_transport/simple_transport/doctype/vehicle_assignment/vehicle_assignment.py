from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from simple_transport.access import is_operations_manager


class VehicleAssignment(Document):
	def validate(self):
		self.validate_operation_manager()
		self.validate_vehicles()

	def validate_operation_manager(self):
		if self.operation_manager and not is_operations_manager(self.operation_manager):
			frappe.throw(
				_("User {0} must have the ST Operation Manager role.").format(
					self.operation_manager
				)
			)

	def validate_vehicles(self):
		if not self.vehicles:
			frappe.throw(_("Add at least one vehicle to the assignment."))

		seen = set()
		for row in self.vehicles:
			if row.vehicle in seen:
				frappe.throw(_("Vehicle {0} has been added more than once.").format(row.vehicle))
			seen.add(row.vehicle)

			existing_assignment = frappe.db.sql(
				"""
				select assignment.name
				from `tabVehicle Assignment Detail` detail
				inner join `tabVehicle Assignment` assignment on assignment.name = detail.parent
				where detail.vehicle = %s
					and assignment.name != %s
					and assignment.is_active = 1
					and assignment.docstatus < 2
				limit 1
				""",
				(row.vehicle, self.name or ""),
				as_dict=True,
			)
			if existing_assignment:
				frappe.throw(
					_("Vehicle {0} is already assigned in {1}.").format(
						row.vehicle, existing_assignment[0].name
					)
				)
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company")
