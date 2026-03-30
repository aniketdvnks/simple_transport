from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, date_diff, getdate


STATUS_DRAFT = "Draft"
STATUS_ACTIVE = "Active"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"


class DriverAssignment(Document):
	def validate(self):
		self.company = self.company or frappe.defaults.get_user_default("Company")
		self.populate_previous_assignment_summary()
		self.populate_closed_assignment_references()
		self.validate_driver()
		self.validate_future_conflicts()
		self.validate_reassignment_dates()
		self.update_assignment_metrics()
		self.set_status()

	def on_submit(self):
		self.close_previous_assignments()
		self.sync_vehicle_employee(self.vehicle, self.driver)
		self.db_set("status", STATUS_ACTIVE, update_modified=False)

	def on_cancel(self):
		self.validate_cancel_sequence()
		self.restore_previous_assignments()
		self.db_set("status", STATUS_CANCELLED, update_modified=False)

	def populate_previous_assignment_summary(self):
		self.previous_assignment = ""
		self.previous_driver = ""
		self.previous_assigned_from = None
		self.previous_assigned_till = None
		self.previous_assignment_days = 0

		previous_assignment = self.get_latest_previous_assignment(self.vehicle)
		if not previous_assignment:
			return

		self.previous_assignment = previous_assignment.name
		self.previous_driver = previous_assignment.driver
		self.previous_assigned_from = previous_assignment.assignment_date
		self.previous_assigned_till = previous_assignment.assigned_till
		self.previous_assignment_days = previous_assignment.assignment_days or 0

	def populate_closed_assignment_references(self):
		self.closed_vehicle_assignment = ""
		self.closed_driver_assignment = ""

		active_vehicle_assignment = self.get_active_assignment("vehicle", self.vehicle)
		active_driver_assignment = self.get_active_assignment("driver", self.driver)

		if (
			active_vehicle_assignment
			and active_vehicle_assignment.driver == self.driver
			and active_vehicle_assignment.vehicle == self.vehicle
		):
			frappe.throw(
				_("Driver {0} is already the active driver for vehicle {1}.").format(
					self.driver, self.vehicle
				)
			)

		if active_vehicle_assignment:
			self.closed_vehicle_assignment = active_vehicle_assignment.name

		if active_driver_assignment and active_driver_assignment.name != self.closed_vehicle_assignment:
			self.closed_driver_assignment = active_driver_assignment.name

	def validate_driver(self):
		if not self.driver:
			frappe.throw(_("Driver is required."))

		driver_details = frappe.db.get_value(
			"Employee",
			self.driver,
			["status", "designation", "st_is_driver"],
			as_dict=True,
		)
		if not driver_details:
			frappe.throw(_("Employee {0} was not found.").format(self.driver))

		if driver_details.status != "Active":
			frappe.throw(_("Driver {0} must be Active.").format(self.driver))

		if not driver_details.st_is_driver:
			frappe.throw(_("Employee {0} is not marked as a transport driver.").format(self.driver))

		if (driver_details.designation or "") != "Driver":
			frappe.throw(_("Employee {0} must have Designation Driver.").format(self.driver))

	def validate_future_conflicts(self):
		for fieldname, label in {"vehicle": _("vehicle"), "driver": _("driver")}.items():
			value = self.get(fieldname)
			if not value or not self.assignment_date:
				continue

			conflict = frappe.db.get_value(
				"Driver Assignment",
				{
					fieldname: value,
					"docstatus": 1,
					"name": ["!=", self.name or ""],
					"assignment_date": [">=", self.assignment_date],
				},
				["name", "assignment_date"],
				as_dict=True,
				order_by="assignment_date asc, creation asc",
			)
			if conflict:
				frappe.throw(
					_(
						"Assignment date must be later than submitted Driver Assignment {0} for this {1}."
					).format(conflict.name, label)
				)

	def validate_reassignment_dates(self):
		reassignment_date = add_to_date(self.assignment_date, days=-1)

		for fieldname in ("closed_vehicle_assignment", "closed_driver_assignment"):
			assignment_name = self.get(fieldname)
			if not assignment_name:
				continue

			assignment = frappe.db.get_value(
				"Driver Assignment",
				assignment_name,
				["assignment_date", "vehicle", "driver"],
				as_dict=True,
			)
			if not assignment:
				continue

			if getdate(reassignment_date) < getdate(assignment.assignment_date):
				frappe.throw(
					_(
						"Assignment date must be after the existing active assignment {0} starting on {1}."
					).format(
						assignment_name,
						frappe.format(assignment.assignment_date, {"fieldtype": "Date"}),
					)
				)

	def update_assignment_metrics(self):
		if self.assigned_till:
			self.assignment_days = date_diff(self.assigned_till, self.assignment_date) + 1
		else:
			self.assignment_days = 0

	def set_status(self):
		if self.docstatus == 2:
			self.status = STATUS_CANCELLED
		elif self.assigned_till:
			self.status = STATUS_COMPLETED
		elif self.docstatus == 1:
			self.status = STATUS_ACTIVE
		else:
			self.status = STATUS_DRAFT

	def close_previous_assignments(self):
		if self.closed_vehicle_assignment:
			self.close_assignment(self.closed_vehicle_assignment, clear_vehicle=False)

		if self.closed_driver_assignment:
			self.close_assignment(self.closed_driver_assignment, clear_vehicle=True)

	def close_assignment(self, assignment_name: str, clear_vehicle: bool = False):
		assignment = frappe.db.get_value(
			"Driver Assignment",
			assignment_name,
			["assignment_date", "vehicle"],
			as_dict=True,
		)
		if not assignment:
			return

		assigned_till = add_to_date(self.assignment_date, days=-1)
		assignment_days = date_diff(assigned_till, assignment.assignment_date) + 1

		frappe.db.set_value(
			"Driver Assignment",
			assignment_name,
			{
				"assigned_till": assigned_till,
				"assignment_days": assignment_days,
				"status": STATUS_COMPLETED,
			},
			update_modified=False,
		)

		if clear_vehicle and assignment.vehicle and frappe.db.exists("Vehicle", assignment.vehicle):
			self.sync_vehicle_employee(assignment.vehicle, "")

	def validate_cancel_sequence(self):
		for fieldname, value in {"vehicle": self.vehicle, "driver": self.driver}.items():
			if not value:
				continue

			later_assignment = frappe.db.get_value(
				"Driver Assignment",
				{
					fieldname: value,
					"docstatus": 1,
					"name": ["!=", self.name],
					"assignment_date": [">", self.assignment_date],
				},
				"name",
			)
			if later_assignment:
				frappe.throw(
					_(
						"Cancel submitted Driver Assignment {0} before cancelling this record."
					).format(later_assignment)
				)

	def restore_previous_assignments(self):
		restored_vehicle_assignment = self.reopen_assignment(self.closed_vehicle_assignment)
		restored_driver_assignment = self.reopen_assignment(self.closed_driver_assignment)

		if restored_vehicle_assignment:
			self.sync_vehicle_employee(restored_vehicle_assignment.vehicle, restored_vehicle_assignment.driver)
		else:
			self.sync_vehicle_employee(self.vehicle, "")

		if (
			restored_driver_assignment
			and restored_driver_assignment.vehicle
			and restored_driver_assignment.vehicle != self.vehicle
		):
			self.sync_vehicle_employee(restored_driver_assignment.vehicle, restored_driver_assignment.driver)

	def reopen_assignment(self, assignment_name: str):
		if not assignment_name or not frappe.db.exists("Driver Assignment", assignment_name):
			return None

		assignment = frappe.get_doc("Driver Assignment", assignment_name)
		expected_assigned_till = add_to_date(self.assignment_date, days=-1)

		if not assignment.assigned_till or getdate(assignment.assigned_till) != getdate(expected_assigned_till):
			return None

		frappe.db.set_value(
			"Driver Assignment",
			assignment.name,
			{
				"assigned_till": None,
				"assignment_days": 0,
				"status": STATUS_ACTIVE,
			},
			update_modified=False,
		)
		assignment.assigned_till = None
		assignment.assignment_days = 0
		assignment.status = STATUS_ACTIVE
		return assignment

	def sync_vehicle_employee(self, vehicle: str | None, driver: str | None):
		if not vehicle or not frappe.db.exists("Vehicle", vehicle):
			return

		frappe.db.set_value("Vehicle", vehicle, "employee", driver or "", update_modified=False)

	def get_active_assignment(self, fieldname: str, value: str | None):
		if not value:
			return None

		return frappe.db.get_value(
			"Driver Assignment",
			{
				fieldname: value,
				"docstatus": 1,
				"status": STATUS_ACTIVE,
				"name": ["!=", self.name or ""],
			},
			["name", "vehicle", "driver", "assignment_date"],
			as_dict=True,
		)

	def get_latest_previous_assignment(self, vehicle: str | None):
		if not vehicle:
			return None

		filters = {
			"vehicle": vehicle,
			"docstatus": 1,
			"name": ["!=", self.name or ""],
		}
		if self.assignment_date:
			filters["assignment_date"] = ["<", self.assignment_date]

		return frappe.db.get_value(
			"Driver Assignment",
			filters,
			[
				"name",
				"driver",
				"assignment_date",
				"assigned_till",
				"assignment_days",
			],
			as_dict=True,
			order_by="assignment_date desc, creation desc",
		)


@frappe.whitelist()
def get_previous_assignment_summary(vehicle: str, assignment_date: str | None = None, current_assignment: str | None = None):
	if not vehicle:
		return {}

	filters = {
		"vehicle": vehicle,
		"docstatus": 1,
	}
	if current_assignment:
		filters["name"] = ["!=", current_assignment]
	if assignment_date:
		filters["assignment_date"] = ["<", assignment_date]

	assignment = frappe.db.get_value(
		"Driver Assignment",
		filters,
		[
			"name",
			"driver",
			"assignment_date",
			"assigned_till",
			"assignment_days",
		],
		as_dict=True,
		order_by="assignment_date desc, creation desc",
	)
	return assignment or {}
