from __future__ import annotations

import frappe

from simple_transport.bootstrap import ROLE_DRIVER, ROLE_OPERATIONS


def has_transport_full_access(user=None) -> bool:
	user = user or frappe.session.user
	if user in {"Administrator"}:
		return True
	if user in {"Guest"}:
		return False
	return "System Manager" in frappe.get_roles(user)


def get_driver_employee(user=None):
	user = user or frappe.session.user

	if user in {"Guest"} or has_transport_full_access(user):
		return None

	if ROLE_DRIVER not in frappe.get_roles(user):
		return None

	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def is_operations_manager(user=None) -> bool:
	user = user or frappe.session.user
	if user in {"Guest"}:
		return False
	return ROLE_OPERATIONS in frappe.get_roles(user)


def get_assigned_vehicle_names(user=None) -> list[str]:
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return []

	if not is_operations_manager(user):
		return []

	rows = frappe.db.sql(
		"""
		select distinct detail.vehicle
		from `tabVehicle Assignment Detail` detail
		inner join `tabVehicle Assignment` assignment on assignment.name = detail.parent
		where assignment.operation_manager = %s
			and assignment.is_active = 1
			and assignment.docstatus < 2
			and ifnull(detail.vehicle, '') != ''
		""",
		(user,),
		as_dict=True,
	)
	return [row.vehicle for row in rows]


def get_assigned_vehicle_condition(user: str, vehicle_field: str) -> str | None:
	if has_transport_full_access(user):
		return None

	if not is_operations_manager(user):
		return None

	return f"""{vehicle_field} in (
		select detail.vehicle
		from `tabVehicle Assignment Detail` detail
		inner join `tabVehicle Assignment` assignment on assignment.name = detail.parent
		where assignment.operation_manager = {frappe.db.escape(user)}
			and assignment.is_active = 1
			and assignment.docstatus < 2
	)"""


def is_vehicle_assigned_to_manager(vehicle: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not vehicle or not is_operations_manager(user):
		return False
	return vehicle in set(get_assigned_vehicle_names(user))


def get_assigned_driver_condition(user: str, employee_field: str) -> str | None:
	if has_transport_full_access(user):
		return None

	if not is_operations_manager(user):
		return None

	return f"""{employee_field} in (
		select vehicle.employee
		from `tabVehicle` vehicle
		where vehicle.name in (
			select detail.vehicle
			from `tabVehicle Assignment Detail` detail
			inner join `tabVehicle Assignment` assignment on assignment.name = detail.parent
			where assignment.operation_manager = {frappe.db.escape(user)}
				and assignment.is_active = 1
				and assignment.docstatus < 2
		)
		and ifnull(vehicle.employee, '') != ''
	)"""
