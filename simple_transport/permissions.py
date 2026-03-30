from __future__ import annotations

import frappe

from simple_transport.access import (
	get_assigned_driver_condition,
	get_assigned_vehicle_condition,
	get_assigned_vehicle_names,
	get_driver_employee,
	has_transport_full_access,
	is_operations_manager,
)


def get_lorry_receipt_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if condition := get_assigned_vehicle_condition(user, "`tabLorry Receipt`.`vehicle`"):
		return condition

	employee = get_driver_employee(user)
	if employee:
		return f"`tabLorry Receipt`.`driver` = {frappe.db.escape(employee)}"

	return None


def get_driver_assignment_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if condition := get_assigned_vehicle_condition(user, "`tabDriver Assignment`.`vehicle`"):
		return condition

	employee = get_driver_employee(user)
	if employee:
		return f"`tabDriver Assignment`.`driver` = {frappe.db.escape(employee)}"

	return None


def get_trip_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if condition := get_assigned_vehicle_condition(user, "`tabTrip`.`vehicle`"):
		return condition

	employee = get_driver_employee(user)
	if employee:
		return f"`tabTrip`.`driver` = {frappe.db.escape(employee)}"

	return None


def get_fuel_request_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if condition := get_assigned_vehicle_condition(user, "`tabFuel Request`.`vehicle`"):
		return condition

	employee = get_driver_employee(user)
	if employee:
		return f"`tabFuel Request`.`driver` = {frappe.db.escape(employee)}"

	return None


def get_vehicle_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if condition := get_assigned_vehicle_condition(user, "`tabVehicle`.`name`"):
		return condition

	employee = get_driver_employee(user)
	if employee:
		return (
			f"(`tabVehicle`.`employee` = {frappe.db.escape(employee)} "
			f"or `tabVehicle`.`name` in (select `tabTrip`.`vehicle` from `tabTrip` where `tabTrip`.`driver` = {frappe.db.escape(employee)}))"
		)

	return None


def get_employee_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if is_operations_manager(user):
		assigned_driver_condition = get_assigned_driver_condition(user, "`tabEmployee`.`name`")
		driver_roster_condition = (
			"(ifnull(`tabEmployee`.`st_is_driver`, 0) = 1 "
			"or ifnull(`tabEmployee`.`designation`, '') = 'Driver')"
		)
		if assigned_driver_condition:
			return f"({driver_roster_condition} or {assigned_driver_condition})"
		return driver_roster_condition

	if condition := get_assigned_driver_condition(user, "`tabEmployee`.`name`"):
		return condition

	employee = get_driver_employee(user)
	if employee:
		return f"`tabEmployee`.`name` = {frappe.db.escape(employee)}"

	return None


def get_vehicle_assignment_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if is_operations_manager(user):
		return f"`tabVehicle Assignment`.`operation_manager` = {frappe.db.escape(user)}"
	return None


def get_gps_webhook_log_permission_query_conditions(user):
	if has_transport_full_access(user):
		return None

	if condition := get_assigned_vehicle_condition(user, "`tabGPS Webhook Log`.`vehicle`"):
		return condition
	return None


def lorry_receipt_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.vehicle in set(get_assigned_vehicle_names(user))

	employee = get_driver_employee(user)
	if employee:
		return doc.driver == employee

	return None


def driver_assignment_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.vehicle in set(get_assigned_vehicle_names(user))

	employee = get_driver_employee(user)
	if employee:
		return doc.driver == employee

	return None


def trip_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.vehicle in set(get_assigned_vehicle_names(user))

	employee = get_driver_employee(user)
	if employee:
		return doc.driver == employee

	return None


def fuel_request_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.vehicle in set(get_assigned_vehicle_names(user))

	employee = get_driver_employee(user)
	if employee:
		return doc.driver == employee

	return None


def vehicle_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.name in set(get_assigned_vehicle_names(user))

	employee = get_driver_employee(user)
	if employee:
		return doc.employee == employee or bool(
			frappe.db.exists("Trip", {"vehicle": doc.name, "driver": employee})
		)

	return None


def employee_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		if doc.st_is_driver or doc.designation == "Driver":
			return True

		assigned_vehicles = get_assigned_vehicle_names(user)
		if not assigned_vehicles:
			return False

		return bool(
			frappe.db.exists(
				"Vehicle",
				{"employee": doc.name, "name": ["in", assigned_vehicles]},
			)
		)

	employee = get_driver_employee(user)
	if employee:
		return doc.name == employee

	return None


def vehicle_assignment_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.operation_manager == user
	return None


def gps_webhook_log_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user

	if has_transport_full_access(user):
		return True

	if is_operations_manager(user):
		return doc.vehicle in set(get_assigned_vehicle_names(user))

	return None
