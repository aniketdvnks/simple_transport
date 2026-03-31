from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from simple_transport.bootstrap import ROLE_EXECUTIVE, ROLE_OPERATIONS, sync_transport_access
from simple_transport.gps_integration import ensure_gps_integration_settings
from simple_transport.print_formats import (
	ensure_lorry_receipt_print_format,
	ensure_sales_invoice_print_format,
)
from simple_transport.sales_invoice import ensure_transport_service_item
from simple_transport.vehicle_status import (
	IDLE_VEHICLE_STATUS,
	get_vehicle_status_options_text,
	sync_all_vehicle_statuses,
)


CUSTOM_FIELDS = {
	"Vehicle": [
		{
			"fieldname": "st_transport_section",
			"fieldtype": "Section Break",
			"label": "Transport Planning",
			"insert_after": "employee",
			"collapsible": 1,
		},
		{
			"fieldname": "st_vehicle_capacity_mt",
			"fieldtype": "Float",
			"label": "Vehicle Capacity (MT)",
			"insert_after": "st_transport_section",
		},
		{
			"fieldname": "st_operational_status",
			"fieldtype": "Select",
			"label": "Status",
			"options": get_vehicle_status_options_text(),
			"default": IDLE_VEHICLE_STATUS,
			"insert_after": "st_vehicle_capacity_mt",
		},
		{
			"fieldname": "st_transport_column_break",
			"fieldtype": "Column Break",
			"insert_after": "st_operational_status",
		},
		{
			"fieldname": "st_current_trip",
			"fieldtype": "Link",
			"label": "Current Trip",
			"options": "Trip",
			"read_only": 1,
			"insert_after": "st_transport_column_break",
		},
		{
			"fieldname": "st_fastag_balance",
			"fieldtype": "Currency",
			"label": "Fastag Balance",
			"insert_after": "st_current_trip",
		},
			{
				"fieldname": "st_last_gps_ping",
				"fieldtype": "Datetime",
				"label": "Last GPS Ping",
				"insert_after": "st_fastag_balance",
			},
			{
				"fieldname": "st_gps_section",
				"fieldtype": "Section Break",
				"label": "GPS Tracking",
				"insert_after": "st_last_gps_ping",
				"collapsible": 1,
			},
			{
				"fieldname": "st_gps_device_id",
				"fieldtype": "Data",
				"label": "GPS Device IMEI",
				"insert_after": "st_gps_section",
			},
			{
				"fieldname": "st_gps_provider_vehicle_id",
				"fieldtype": "Data",
				"label": "GPS Provider Vehicle ID",
				"insert_after": "st_gps_device_id",
			},
			{
				"fieldname": "st_gps_tracker_id",
				"fieldtype": "Data",
				"label": "GPS Tracker ID",
				"insert_after": "st_gps_provider_vehicle_id",
			},
			{
				"fieldname": "st_gps_tracker_imei",
				"fieldtype": "Data",
				"label": "GPS Tracker IMEI",
				"insert_after": "st_gps_tracker_id",
			},
			{
				"fieldname": "st_gps_vehicle_tag",
				"fieldtype": "Data",
				"label": "GPS Vehicle Tag",
				"insert_after": "st_gps_tracker_imei",
			},
			{
				"fieldname": "st_gps_column_break",
				"fieldtype": "Column Break",
				"insert_after": "st_gps_vehicle_tag",
			},
			{
				"fieldname": "st_is_obd_enabled",
				"fieldtype": "Check",
				"label": "OBD Enabled",
				"default": "0",
				"insert_after": "st_gps_column_break",
			},
			{
				"fieldname": "st_obd_attached",
				"fieldtype": "Check",
				"label": "OBD Attached",
				"default": "0",
				"insert_after": "st_is_obd_enabled",
			},
			{
				"fieldname": "st_last_latitude",
				"fieldtype": "Float",
				"label": "Last Latitude",
				"insert_after": "st_obd_attached",
				"read_only": 1,
			},
			{
				"fieldname": "st_last_longitude",
				"fieldtype": "Float",
				"label": "Last Longitude",
				"insert_after": "st_last_latitude",
				"read_only": 1,
			},
			{
				"fieldname": "st_last_speed_kmph",
				"fieldtype": "Float",
				"label": "Last Speed (Km/Hr)",
				"insert_after": "st_last_longitude",
				"read_only": 1,
			},
			{
				"fieldname": "st_last_heading_degree",
				"fieldtype": "Float",
				"label": "Last Heading (Degree)",
				"insert_after": "st_last_speed_kmph",
				"read_only": 1,
			},
			{
				"fieldname": "st_last_gps_accuracy",
				"fieldtype": "Int",
				"label": "GPS Accuracy Level",
				"insert_after": "st_last_heading_degree",
				"read_only": 1,
			},
			{
				"fieldname": "st_last_location_text",
				"fieldtype": "Data",
				"label": "Last GPS Location",
				"insert_after": "st_last_gps_accuracy",
				"read_only": 1,
			},
		],
	"Employee": [
		{
			"fieldname": "st_transport_section",
			"fieldtype": "Section Break",
			"label": "Transport Driver Details",
			"insert_after": "designation",
			"collapsible": 1,
		},
		{
			"fieldname": "st_is_driver",
			"fieldtype": "Check",
			"label": "Transport Driver",
			"default": "0",
			"insert_after": "st_transport_section",
		},
		{
			"fieldname": "st_driving_license_no",
			"fieldtype": "Data",
			"label": "Driving License No",
			"insert_after": "st_is_driver",
			"depends_on": "eval:doc.st_is_driver==1",
		},
		{
			"fieldname": "st_driving_license_valid_upto",
			"fieldtype": "Date",
			"label": "Driving License Valid Upto",
			"insert_after": "st_driving_license_no",
			"depends_on": "eval:doc.st_is_driver==1",
		},
		{
			"fieldname": "st_hazchem_certified",
			"fieldtype": "Check",
			"label": "Hazchem Certified",
			"default": "0",
			"insert_after": "st_driving_license_valid_upto",
			"depends_on": "eval:doc.st_is_driver==1",
			},
		],
		"Contract": [
			{
				"fieldname": "custom_section_break_zi0pb",
				"fieldtype": "Section Break",
				"label": "Transport Rate Details",
				"insert_after": "status",
			},
			{
				"fieldname": "custom_items",
				"fieldtype": "Table",
				"label": "Contract Details",
				"options": "Contract Details",
				"insert_after": "custom_section_break_zi0pb",
			},
		],
		"Sales Invoice": [
			{
				"fieldname": "st_transport_invoice_section",
				"fieldtype": "Section Break",
				"label": "Transport Billing",
				"insert_after": "due_date",
			},
			{
				"fieldname": "st_invoice_type",
				"fieldtype": "Select",
				"label": "Invoice Type",
				"options": "Tax Invoice\nBill of Supply",
				"insert_after": "st_transport_invoice_section",
			},
			{
				"fieldname": "st_copy_label",
				"fieldtype": "Data",
				"label": "Copy Label",
				"default": "ORIGINAL FOR RECIPIENT",
				"insert_after": "st_invoice_type",
			},
			{
				"fieldname": "st_transport_invoice_column_break",
				"fieldtype": "Column Break",
				"insert_after": "st_copy_label",
			},
			{
				"fieldname": "st_service_period",
				"fieldtype": "Data",
				"label": "Period of Service",
				"insert_after": "st_transport_invoice_column_break",
			},
			{
				"fieldname": "st_location_of_supply",
				"fieldtype": "Data",
				"label": "Location of Supply",
				"insert_after": "st_service_period",
			},
			{
				"fieldname": "st_transport_service_section",
				"fieldtype": "Section Break",
				"label": "Transport Service Details",
				"insert_after": "st_location_of_supply",
			},
			{
				"fieldname": "st_service_name",
				"fieldtype": "Data",
				"label": "Service",
				"default": "Transportation Service",
				"insert_after": "st_transport_service_section",
			},
			{
				"fieldname": "st_sac_code",
				"fieldtype": "Data",
				"label": "SAC Code",
				"insert_after": "st_service_name",
			},
			{
				"fieldname": "st_transport_service_column_break",
				"fieldtype": "Column Break",
				"insert_after": "st_sac_code",
			},
			{
				"fieldname": "st_reverse_charge_applicable",
				"fieldtype": "Check",
				"label": "Reverse Charge Applicable",
				"default": "0",
				"insert_after": "st_transport_service_column_break",
			},
			{
				"fieldname": "st_irn_no",
				"fieldtype": "Data",
				"label": "IRN No.",
				"insert_after": "st_reverse_charge_applicable",
			},
			{
				"fieldname": "st_trip_details",
				"fieldtype": "Table",
				"label": "Trip Details",
				"options": "Sales Invoice Trip Detail",
				"insert_after": "st_irn_no",
			},
		],
	}

OBSOLETE_TRANSPORT_ORDER_FIELDS = {
	"Sales Order": [
		{"fieldname": "st_transport_section"},
		{"fieldname": "st_route_master"},
		{"fieldname": "st_route_distance_km"},
		{"fieldname": "st_operation_manager"},
		{"fieldname": "st_transport_column_break"},
		{"fieldname": "st_transport_date"},
		{"fieldname": "st_contract_type"},
		{"fieldname": "st_customer_order_reference"},
		{"fieldname": "st_chemical_name"},
		{"fieldname": "st_special_instructions"},
		{"fieldname": "st_logistics_section"},
		{"fieldname": "st_consignor_name"},
		{"fieldname": "st_consignor_contact_no"},
		{"fieldname": "st_consignor_address"},
		{"fieldname": "st_logistics_column_break"},
		{"fieldname": "st_consignee_name"},
		{"fieldname": "st_consignee_contact_no"},
		{"fieldname": "st_consignee_address"},
	]
}


def before_migrate():
	rename_transport_masters()


def after_install():
	setup_customizations()
	cleanup_obsolete_transport_order_customizations()
	sync_route_locations()
	sync_all_vehicle_statuses()
	sync_transport_pages()
	ensure_gps_integration_settings()
	ensure_transport_service_item()
	ensure_lorry_receipt_print_format()
	ensure_sales_invoice_print_format()
	sync_transport_access()


def after_migrate():
	setup_customizations()
	cleanup_obsolete_transport_order_customizations()
	sync_route_locations()
	sync_all_vehicle_statuses()
	sync_transport_pages()
	ensure_gps_integration_settings()
	ensure_transport_service_item()
	ensure_lorry_receipt_print_format()
	ensure_sales_invoice_print_format()
	sync_transport_access()


def before_uninstall():
	delete_custom_fields(CUSTOM_FIELDS)
	delete_custom_fields(OBSOLETE_TRANSPORT_ORDER_FIELDS)


def setup_customizations():
	available_custom_fields = {
		doctype: fields
		for doctype, fields in CUSTOM_FIELDS.items()
		if frappe.db.exists("DocType", doctype)
	}

	if not available_custom_fields:
		return

	create_custom_fields(available_custom_fields, update=True)
	frappe.clear_cache()


def cleanup_obsolete_transport_order_customizations():
	delete_custom_fields(OBSOLETE_TRANSPORT_ORDER_FIELDS)


def sync_transport_pages():
	page_roles = {
		"daily-planning": [ROLE_EXECUTIVE, ROLE_OPERATIONS],
		"daily-planning-1": [ROLE_EXECUTIVE, ROLE_OPERATIONS],
	}

	for page_name, roles in page_roles.items():
		if not frappe.db.exists("Page", page_name):
			continue

		page = frappe.get_doc("Page", page_name)
		current_roles = [row.role for row in page.roles]
		if current_roles == roles:
			continue

		page.set("roles", [])
		for role in roles:
			page.append("roles", {"role": role})
		page.save(ignore_permissions=True)


def rename_transport_masters():
	if frappe.db.exists("DocType", "Cargo Type") and not frappe.db.exists("DocType", "Material"):
		frappe.rename_doc("DocType", "Cargo Type", "Material", force=True)
		frappe.clear_cache()


def sync_route_locations():
	if not frappe.db.exists("DocType", "Location") or not frappe.db.exists("DocType", "Route Master"):
		return

	location_names = set(
		frappe.get_all("Location", pluck="name", limit_page_length=0)
	)

	values = frappe.db.sql(
		"""
		select distinct location_name
		from (
			select source_location as location_name
			from `tabRoute Master`
			where ifnull(source_location, '') != ''
			union
			select destination_location as location_name
			from `tabRoute Master`
			where ifnull(destination_location, '') != ''
			union
			select `from` as location_name
			from `tabContract Details`
			where ifnull(`from`, '') != ''
			union
			select `to` as location_name
			from `tabContract Details`
			where ifnull(`to`, '') != ''
		) locations
		order by location_name
		""",
		as_dict=True,
	)

	for row in values:
		location_name = (row.location_name or "").strip()
		if not location_name or location_name in location_names:
			continue

		location = frappe.get_doc(
			{
				"doctype": "Location",
				"location_name": location_name,
				"is_group": 0,
			}
		)
		location.insert(ignore_permissions=True)
		location_names.add(location_name)

	for route in frappe.get_all(
		"Route Master",
		fields=["name", "source_location", "destination_location"],
		limit_page_length=0,
	):
		frappe.db.set_value(
			"Route Master",
			route.name,
			{
				"source_location": route.source_location,
				"destination_location": route.destination_location,
			},
			update_modified=False,
		)

	frappe.clear_cache(doctype="Location")
	frappe.clear_cache(doctype="Route Master")


def delete_custom_fields(custom_fields: dict[str, list[dict]]):
	for doctype, fields in custom_fields.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)
		frappe.clear_cache(doctype=doctype)
