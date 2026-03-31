from __future__ import annotations

import math
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, now_datetime

from simple_transport.access import (
	get_assigned_vehicle_names,
	has_transport_full_access,
	is_operations_manager,
)
from simple_transport.simple_transport.doctype.lorry_receipt.lorry_receipt import (
	get_contract_rate_details,
)
from simple_transport.vehicle_status import (
	IDLE_VEHICLE_STATUS,
	UNDER_MAINTENANCE_STATUS,
	is_idle_vehicle_status,
	sync_vehicle_status,
)


UNLOADING_VEHICLE_STATUS = "At Unloading Point"
DEFAULT_ROUTE_COLUMN_CAPACITY = 7


def _ensure_planning_access() -> str:
	user = frappe.session.user
	if has_transport_full_access(user) or is_operations_manager(user):
		return user

	frappe.throw(
		_("You do not have access to Daily Planning."),
		frappe.PermissionError,
	)


def _get_vehicle_fields() -> list[str]:
	meta = frappe.get_meta("Vehicle")
	fields = ["name"]
	for fieldname in (
		"license_plate",
		"employee",
		"st_vehicle_capacity_mt",
		"st_operational_status",
		"st_current_trip",
		"st_last_location_text",
	):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return fields


def _get_selected_transport_order(planning_date=None, transport_order=None):
	selected_order = None

	if transport_order:
		selected_order = frappe.get_doc("Transport Order", transport_order)
		selected_order.check_permission("read")
		planning_date = getdate(selected_order.date)
	else:
		planning_date = getdate(planning_date) if planning_date else getdate()

	transport_orders = frappe.get_all(
		"Transport Order",
		filters={"date": planning_date},
		fields=["name", "date", "modified"],
		order_by="date asc, modified desc",
	)

	if not selected_order and transport_orders:
		selected_order = frappe.get_doc("Transport Order", transport_orders[0].name)
		selected_order.check_permission("read")

	return planning_date, transport_orders, selected_order


def _get_route_map(route_names: list[str]) -> dict[str, dict]:
	if not route_names:
		return {}

	rows = frappe.get_all(
		"Route Master",
		filters={"name": ["in", route_names]},
		fields=["name", "source_location", "destination_location", "distance_km"],
	)
	return {row.name: row for row in rows}


def _get_current_vehicle_scope(user: str) -> list[str]:
	if has_transport_full_access(user):
		return frappe.get_all("Vehicle", pluck="name", order_by="modified desc")
	return get_assigned_vehicle_names(user)


def _get_planned_vehicle_map(planning_date, selected_order_name: str | None):
	filters = {"date": planning_date}
	if selected_order_name:
		filters["name"] = ["!=", selected_order_name]

	other_orders = frappe.get_all("Transport Order", filters=filters, pluck="name")
	if not other_orders:
		return {}

	rows = frappe.get_all(
		"Transport Order Vehicle Assignment",
		filters={"parent": ["in", other_orders]},
		fields=["vehicle", "parent"],
	)
	return {row.vehicle: row.parent for row in rows if row.vehicle}


def _enrich_vehicle_row(vehicle):
	status = getattr(vehicle, "st_operational_status", None) or IDLE_VEHICLE_STATUS
	if status in {"Available", "Completed", "Cancelled"}:
		status = IDLE_VEHICLE_STATUS
	elif status == "Breakdown":
		status = UNDER_MAINTENANCE_STATUS

	vehicle.status = status
	vehicle.driver = getattr(vehicle, "employee", "")
	vehicle.capacity_mt = flt(getattr(vehicle, "st_vehicle_capacity_mt", 0))
	vehicle.label = getattr(vehicle, "license_plate", None) or vehicle.name
	vehicle.current_trip = getattr(vehicle, "st_current_trip", "")
	vehicle.last_location = getattr(vehicle, "st_last_location_text", "")
	return vehicle


def _get_vehicle_buckets(user: str, planning_date, selected_order):
	vehicle_names = _get_current_vehicle_scope(user)
	if not vehicle_names:
		return {
			"assignable_idle_vehicles": [],
			"idle_vehicles": [],
			"unloading_vehicles": [],
			"reference_capacity_mt": 0,
			"scope_note": _("No vehicles are assigned to this operation manager yet."),
		}

	planned_elsewhere = _get_planned_vehicle_map(
		planning_date,
		selected_order.name if selected_order else None,
	)
	current_order_assigned = {
		row.vehicle
		for row in getattr(selected_order, "vehicle_assignments", []) or []
		if row.vehicle
	}

	vehicles = frappe.get_all(
		"Vehicle",
		filters={"name": ["in", vehicle_names]},
		fields=_get_vehicle_fields(),
		order_by="modified desc",
	)
	vehicles = [_enrich_vehicle_row(vehicle) for vehicle in vehicles]
	reference_capacity_mt = max((flt(vehicle.capacity_mt) for vehicle in vehicles), default=0)

	assignable_idle_vehicles = []
	idle_vehicles = []
	unloading_vehicles = []

	for vehicle in vehicles:
		if is_idle_vehicle_status(vehicle.status):
			idle_vehicles.append(vehicle)
			if vehicle.name not in planned_elsewhere and vehicle.name not in current_order_assigned:
				assignable_idle_vehicles.append(vehicle)
		elif vehicle.status == UNLOADING_VEHICLE_STATUS:
			unloading_vehicles.append(vehicle)

	return {
		"assignable_idle_vehicles": assignable_idle_vehicles,
		"idle_vehicles": idle_vehicles,
		"unloading_vehicles": unloading_vehicles,
		"reference_capacity_mt": reference_capacity_mt,
		"scope_note": None,
	}


def _get_trip_status_map(trip_names: list[str]) -> dict[str, str]:
	if not trip_names:
		return {}

	rows = frappe.get_all(
		"Trip",
		filters={"name": ["in", trip_names]},
		fields=["name", "status"],
	)
	return {row.name: row.status for row in rows}


def _serialize_assignments(assignments_by_route: dict[str, list], route_map: dict[str, dict]) -> dict[str, list[dict]]:
	trip_names = [
		row.trip
		for rows in assignments_by_route.values()
		for row in rows
		if getattr(row, "trip", None)
	]
	trip_status_map = _get_trip_status_map(trip_names)

	serialized = defaultdict(list)
	for route_detail, rows in assignments_by_route.items():
		for row in rows:
			route = route_map.get(row.route_master) or {}
			serialized[route_detail].append(
				{
					"name": row.name,
					"vehicle": row.vehicle,
					"driver": row.driver,
					"vehicle_capacity_mt": flt(row.vehicle_capacity_mt),
					"assigned_on": row.assigned_on,
					"assigned_by": row.assigned_by,
					"vehicle_status": row.vehicle_status,
					"loading_point": route.get("source_location"),
					"unloading_point": route.get("destination_location"),
					"lorry_receipt": getattr(row, "lorry_receipt", ""),
					"trip": getattr(row, "trip", ""),
					"trip_status": trip_status_map.get(getattr(row, "trip", ""), ""),
				}
			)
	return serialized


def _calculate_route_metrics(detail, assignments: list[dict], reference_capacity_mt: float) -> dict[str, float]:
	total_weight_mt = flt(detail.qty_in_mt)
	assigned_capacity_mt = sum(flt(row.get("vehicle_capacity_mt")) for row in assignments)
	pending_weight_mt = max(total_weight_mt - assigned_capacity_mt, 0) if total_weight_mt else 0

	if total_weight_mt and reference_capacity_mt:
		required_vehicles = int(math.ceil(total_weight_mt / reference_capacity_mt))
		pending_vehicle_count = int(math.ceil(pending_weight_mt / reference_capacity_mt)) if pending_weight_mt else 0
	else:
		required_vehicles = int(flt(detail.no_of_vehicles)) if flt(detail.no_of_vehicles) else 0
		pending_vehicle_count = max(required_vehicles - len(assignments), 0) if required_vehicles else 0

	return {
		"total_weight_mt": total_weight_mt,
		"assigned_capacity_mt": assigned_capacity_mt,
		"pending_weight_mt": pending_weight_mt,
		"required_vehicles": max(required_vehicles, len(assignments)),
		"pending_vehicle_count": pending_vehicle_count,
	}


def _build_route_rows(selected_order, reference_capacity_mt: float) -> list[dict]:
	if not selected_order:
		return []

	route_names = [row.route for row in selected_order.transport_order_details if row.route]
	route_map = _get_route_map(route_names)
	assignments_by_route = defaultdict(list)
	for row in selected_order.vehicle_assignments or []:
		assignments_by_route[row.route_detail].append(row)

	serialized_assignments = _serialize_assignments(assignments_by_route, route_map)
	route_rows = []
	for detail in selected_order.transport_order_details:
		route = route_map.get(detail.route) or {}
		assignments = serialized_assignments.get(detail.name, [])
		metrics = _calculate_route_metrics(detail, assignments, reference_capacity_mt)

		route_rows.append(
			{
				"name": detail.name,
				"route_master": detail.route,
				"qty_in_mt": flt(detail.qty_in_mt),
				"no_of_vehicles": int(flt(detail.no_of_vehicles)) if flt(detail.no_of_vehicles) else 0,
				"required_vehicles": metrics["required_vehicles"],
				"assigned_count": len(assignments),
				"pending_count": metrics["pending_vehicle_count"],
				"pending_weight_mt": metrics["pending_weight_mt"],
				"assigned_capacity_mt": metrics["assigned_capacity_mt"],
				"loading_point": route.get("source_location"),
				"unloading_point": route.get("destination_location"),
				"distance_km": flt(route.get("distance_km") or 0),
				"assignments": assignments,
				"display_rows": max(
					DEFAULT_ROUTE_COLUMN_CAPACITY,
					len(assignments),
					metrics["required_vehicles"],
				),
			}
		)

	return route_rows


def _get_assignment_row(doc, assignment_row: str):
	row = next((child for child in doc.vehicle_assignments or [] if child.name == assignment_row), None)
	if not row:
		frappe.throw(_("Vehicle assignment row {0} was not found.").format(assignment_row))
	return row


def _get_route_detail(doc, route_detail: str):
	row = next((child for child in doc.transport_order_details or [] if child.name == route_detail), None)
	if not row:
		frappe.throw(_("The selected route was not found on Transport Order {0}.").format(doc.name))
	return row


def _get_route_assignment_capacity(doc, route_detail: str) -> float:
	return sum(
		flt(row.vehicle_capacity_mt)
		for row in doc.vehicle_assignments or []
		if row.route_detail == route_detail
	)


def _ensure_vehicle_can_be_planned(user: str, vehicle: str, planning_date, selected_order_name: str | None = None):
	if not vehicle or not frappe.db.exists("Vehicle", vehicle):
		frappe.throw(_("Vehicle {0} was not found.").format(vehicle))

	if not has_transport_full_access(user):
		allowed = set(get_assigned_vehicle_names(user))
		if vehicle not in allowed:
			frappe.throw(_("Vehicle {0} is not assigned to you.").format(vehicle))

	vehicle_status = frappe.db.get_value("Vehicle", vehicle, "st_operational_status") or IDLE_VEHICLE_STATUS
	if not is_idle_vehicle_status(vehicle_status):
		frappe.throw(
			_("Only idle vehicles can be planned. Vehicle {0} is currently {1}.").format(
				vehicle, vehicle_status
			)
		)

	planned_elsewhere = _get_planned_vehicle_map(planning_date, selected_order_name)
	if vehicle in planned_elsewhere:
		frappe.throw(
			_("Vehicle {0} is already planned in Transport Order {1}.").format(
				vehicle, planned_elsewhere[vehicle]
			)
		)


def _get_default_company():
	companies = frappe.get_all("Company", pluck="name", limit=1)
	return companies[0] if companies else None


@frappe.whitelist()
def get_daily_planning_data(planning_date=None, transport_order=None):
	user = _ensure_planning_access()
	planning_date, transport_orders, selected_order = _get_selected_transport_order(
		planning_date=planning_date,
		transport_order=transport_order,
	)
	vehicle_data = _get_vehicle_buckets(user, planning_date, selected_order)
	scope_note = vehicle_data["scope_note"] or (
		_("Showing only vehicles assigned to operation manager {0}.").format(user)
		if is_operations_manager(user) and not has_transport_full_access(user)
		else ""
	)

	return {
		"planning_date": str(planning_date),
		"transport_orders": transport_orders,
		"selected_transport_order": selected_order.name if selected_order else "",
		"route_rows": _build_route_rows(selected_order, vehicle_data["reference_capacity_mt"]),
		"assignable_idle_vehicles": vehicle_data["assignable_idle_vehicles"],
		"idle_vehicles": vehicle_data["idle_vehicles"],
		"unloading_vehicles": vehicle_data["unloading_vehicles"],
		"scope_note": scope_note,
	}


@frappe.whitelist()
def assign_vehicle_to_transport_order(transport_order: str, route_detail: str, vehicle: str):
	user = _ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("write")

	route_row = _get_route_detail(doc, route_detail)

	if flt(route_row.qty_in_mt):
		vehicle_capacity_mt = flt(frappe.db.get_value("Vehicle", vehicle, "st_vehicle_capacity_mt"))
		if vehicle_capacity_mt <= 0:
			frappe.throw(
				_("Vehicle {0} must have Capacity (MT) set before planning against this route.").format(
					vehicle
				)
			)
		assigned_capacity = _get_route_assignment_capacity(doc, route_detail)
		if assigned_capacity >= flt(route_row.qty_in_mt):
			frappe.throw(
				_("Assigned vehicle capacity already covers the planned weight for route {0}.").format(
					route_row.route
				)
			)
	elif flt(route_row.no_of_vehicles):
		assigned_count = sum(1 for row in doc.vehicle_assignments or [] if row.route_detail == route_detail)
		if assigned_count >= int(flt(route_row.no_of_vehicles)):
			frappe.throw(
				_("All required vehicles are already planned for route {0}.").format(route_row.route)
			)

	_ensure_vehicle_can_be_planned(user, vehicle, getdate(doc.date), doc.name)

	doc.append(
		"vehicle_assignments",
		{
			"route_detail": route_row.name,
			"route_master": route_row.route,
			"customer": route_row.customer,
			"vehicle": vehicle,
			"assigned_by": user,
		},
	)
	doc.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def unassign_vehicle_from_transport_order(transport_order: str, assignment_row: str):
	_ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("write")

	row = _get_assignment_row(doc, assignment_row)
	if row.lorry_receipt or row.trip:
		frappe.throw(_("Remove linked Lorry Receipt / Trip before unassigning this vehicle."))

	doc.remove(row)
	doc.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def add_route_to_transport_order(transport_order: str, route_master: str, qty_in_mt=None, no_of_vehicles=None):
	_ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("write")

	if not route_master or not frappe.db.exists("Route Master", route_master):
		frappe.throw(_("Route Master is required."))

	doc.append(
		"transport_order_details",
		{
			"route": route_master,
			"qty_in_mt": flt(qty_in_mt),
			"no_of_vehicles": int(flt(no_of_vehicles)) if flt(no_of_vehicles) else 0,
		},
	)
	doc.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def update_route_on_transport_order(
	transport_order: str,
	route_detail: str,
	qty_in_mt=None,
	no_of_vehicles=None,
):
	_ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("write")

	route_row = _get_route_detail(doc, route_detail)
	route_row.qty_in_mt = flt(qty_in_mt) if qty_in_mt not in (None, "") else 0
	route_row.no_of_vehicles = int(flt(no_of_vehicles)) if no_of_vehicles not in (None, "") else 0
	doc.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def create_lorry_receipt_from_assignment(
	transport_order: str,
	assignment_row: str,
	lr_date=None,
	gate_pass_no=None,
	goods_description=None,
	quantity_mt=None,
	gross_weight_mt=None,
	freight_rate_per_mt=None,
	loading_supervisor_name=None,
	remarks=None,
):
	user = _ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("write")

	row = _get_assignment_row(doc, assignment_row)
	if row.lorry_receipt and frappe.db.exists("Lorry Receipt", row.lorry_receipt):
		frappe.throw(_("Lorry Receipt {0} already exists for this vehicle planning row.").format(row.lorry_receipt))

	route_row = _get_route_detail(doc, row.route_detail)
	quantity_mt = flt(quantity_mt)
	if quantity_mt <= 0:
		frappe.throw(_("Net Weight (MT) is required to create the Lorry Receipt."))

	lorry_receipt = frappe.get_doc(
		{
			"doctype": "Lorry Receipt",
			"company": _get_default_company(),
			"lr_date": getdate(lr_date) if lr_date else getdate(doc.date),
			"gate_pass_no": gate_pass_no,
			"customer": route_row.customer,
			"operation_manager": user,
			"route_master": row.route_master,
			"vehicle": row.vehicle,
			"driver": row.driver,
			"goods_description": goods_description,
			"quantity_mt": quantity_mt,
			"gross_weight_mt": flt(gross_weight_mt) or quantity_mt,
			"freight_rate_per_mt": flt(freight_rate_per_mt),
			"loading_supervisor_name": loading_supervisor_name,
			"remarks": remarks,
			"transport_order": doc.name,
			"transport_order_detail": row.route_detail,
			"planning_assignment": row.name,
		}
	)
	lorry_receipt.insert(ignore_permissions=True)
	lorry_receipt.submit()

	frappe.db.set_value(
		"Transport Order Vehicle Assignment",
		row.name,
		"lorry_receipt",
		lorry_receipt.name,
		update_modified=False,
	)
	return {
		"lorry_receipt": lorry_receipt.name,
		"trip": lorry_receipt.trip,
	}


@frappe.whitelist()
def start_trip_from_assignment(
	transport_order: str,
	assignment_row: str,
	dispatch_date=None,
	status=None,
	actual_start_datetime=None,
	expected_arrival_date=None,
	current_location=None,
):
	user = _ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("write")

	row = _get_assignment_row(doc, assignment_row)
	if not row.lorry_receipt or not frappe.db.exists("Lorry Receipt", row.lorry_receipt):
		frappe.throw(_("Create the Lorry Receipt before starting the Trip."))
	if row.trip and frappe.db.exists("Trip", row.trip):
		frappe.throw(_("Trip {0} already exists for this vehicle planning row.").format(row.trip))

	trip = frappe.get_doc(
		{
			"doctype": "Trip",
			"lorry_receipt": row.lorry_receipt,
			"operation_manager": user,
			"dispatch_date": getdate(dispatch_date) if dispatch_date else getdate(doc.date),
			"status": status or "At Loading Point",
			"actual_start_datetime": get_datetime(actual_start_datetime)
			if actual_start_datetime
			else now_datetime(),
			"expected_arrival_date": getdate(expected_arrival_date) if expected_arrival_date else None,
			"current_location": current_location,
		}
	)
	trip.insert(ignore_permissions=True)

	frappe.db.set_value(
		"Transport Order Vehicle Assignment",
		row.name,
		"trip",
		trip.name,
		update_modified=False,
	)
	sync_vehicle_status(row.vehicle)
	return {"trip": trip.name}


@frappe.whitelist()
def get_lorry_receipt_defaults(
	transport_order: str,
	assignment_row: str,
	goods_description=None,
):
	_ensure_planning_access()
	doc = frappe.get_doc("Transport Order", transport_order)
	doc.check_permission("read")

	row = _get_assignment_row(doc, assignment_row)
	route_row = _get_route_detail(doc, row.route_detail)

	assigned_capacity = _get_route_assignment_capacity(doc, row.route_detail)
	pending_weight_mt = max(flt(route_row.qty_in_mt) - assigned_capacity, 0) if flt(route_row.qty_in_mt) else 0
	default_quantity_mt = min(
		value for value in [flt(row.vehicle_capacity_mt) or 0, pending_weight_mt or 0] if value
	) if (flt(row.vehicle_capacity_mt) or pending_weight_mt) else 0

	rate_details = get_contract_rate_details(
		customer=route_row.customer,
		route_master=row.route_master,
		material=goods_description,
		lr_date=doc.date,
	)
	freight_rate_per_mt = flt(rate_details.rate_per_mt) if rate_details else 0

	return {
		"vehicle": row.vehicle,
		"driver": row.driver,
		"vehicle_capacity_mt": flt(row.vehicle_capacity_mt),
		"pending_weight_mt": pending_weight_mt,
		"default_quantity_mt": default_quantity_mt or flt(row.vehicle_capacity_mt),
		"freight_rate_per_mt": freight_rate_per_mt,
	}
