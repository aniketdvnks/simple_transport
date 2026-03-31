from __future__ import annotations

import frappe


IDLE_VEHICLE_STATUS = "Idle"
UNDER_MAINTENANCE_STATUS = "Under Maintenance"

ACTIVE_TRIP_STATUSES = (
	"Planned",
	"Ready for Dispatch",
	"At Loading Point",
	"In Transit",
	"At Unloading Point",
	"On Hold",
)

TRIP_STATUS_OPTIONS = (
	"Planned",
	"Ready for Dispatch",
	"At Loading Point",
	"In Transit",
	"At Unloading Point",
	"On Hold",
	"Completed",
	"Cancelled",
)

VEHICLE_STATUS_OPTIONS = (
	IDLE_VEHICLE_STATUS,
	*TRIP_STATUS_OPTIONS,
	UNDER_MAINTENANCE_STATUS,
)

LEGACY_IDLE_STATUSES = {"", "Available", "Completed", "Cancelled"}


def get_vehicle_status_options_text() -> str:
	return "\n".join(VEHICLE_STATUS_OPTIONS)


def get_vehicle_status_from_trip_status(trip_status: str | None) -> str:
	if trip_status in ACTIVE_TRIP_STATUSES:
		return trip_status
	return IDLE_VEHICLE_STATUS


def is_idle_vehicle_status(status: str | None) -> bool:
	return (status or "") in LEGACY_IDLE_STATUSES | {IDLE_VEHICLE_STATUS}


def is_vehicle_under_maintenance(status: str | None) -> bool:
	return (status or "") in {UNDER_MAINTENANCE_STATUS, "Breakdown"}


def get_active_trip_for_vehicle(vehicle_name: str, exclude_trip_name: str | None = None):
	filters = {
		"vehicle": vehicle_name,
		"status": ["in", list(ACTIVE_TRIP_STATUSES)],
	}
	if exclude_trip_name:
		filters["name"] = ["!=", exclude_trip_name]

	return frappe.db.get_value(
		"Trip",
		filters,
		["name", "status"],
		as_dict=True,
		order_by="modified desc",
	)


def sync_vehicle_status(vehicle_name: str, exclude_trip_name: str | None = None):
	if not vehicle_name or not frappe.db.exists("Vehicle", vehicle_name):
		return None

	meta = frappe.get_meta("Vehicle")
	if not meta.has_field("st_current_trip") or not meta.has_field("st_operational_status"):
		return None

	current_status = frappe.db.get_value("Vehicle", vehicle_name, "st_operational_status")
	active_trip = get_active_trip_for_vehicle(vehicle_name, exclude_trip_name=exclude_trip_name)

	if active_trip:
		next_status = get_vehicle_status_from_trip_status(active_trip.status)
		next_trip = active_trip.name
	else:
		next_status = (
			UNDER_MAINTENANCE_STATUS
			if is_vehicle_under_maintenance(current_status)
			else IDLE_VEHICLE_STATUS
		)
		next_trip = ""

	values = {
		"st_current_trip": next_trip,
		"st_operational_status": next_status,
	}
	frappe.db.set_value("Vehicle", vehicle_name, values, update_modified=False)
	return values


def sync_all_vehicle_statuses():
	if not frappe.db.exists("DocType", "Vehicle"):
		return

	for vehicle_name in frappe.get_all("Vehicle", pluck="name", limit_page_length=0):
		sync_vehicle_status(vehicle_name)
