from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


TRANSPORT_SERVICE_ITEM = "TRANSPORT-FREIGHT-SERVICE"
DEFAULT_SERVICE_NAME = "Transportation Service"
BILLABLE_TRIP_STATUS = "Completed"


def sync_transport_invoice(doc, method=None):
	if doc.doctype != "Sales Invoice" or not hasattr(doc, "st_trip_details"):
		return

	apply_transport_defaults(doc)
	sync_trip_details(doc)
	sync_invoice_item(doc)


def sync_trip_invoice_links(doc, method=None):
	if doc.doctype != "Sales Invoice" or not doc.name or not hasattr(doc, "st_trip_details"):
		return

	current_trip_names = {row.trip for row in doc.get("st_trip_details", []) if row.trip}
	linked_trip_names = set(
		frappe.get_all("Trip", filters={"sales_invoice": doc.name}, pluck="name")
	)

	for trip_name in current_trip_names:
		existing_invoice = frappe.db.get_value("Trip", trip_name, "sales_invoice")
		if existing_invoice and existing_invoice != doc.name:
			frappe.throw(
				_("Trip {0} is already linked to Sales Invoice {1}.").format(
					trip_name, existing_invoice
				)
			)
		frappe.db.set_value("Trip", trip_name, "sales_invoice", doc.name, update_modified=False)

	for trip_name in linked_trip_names - current_trip_names:
		frappe.db.set_value("Trip", trip_name, "sales_invoice", "", update_modified=False)


def clear_trip_invoice_links(doc, method=None):
	if doc.doctype != "Sales Invoice" or not doc.name:
		return

	for trip_name in frappe.get_all("Trip", filters={"sales_invoice": doc.name}, pluck="name"):
		frappe.db.set_value("Trip", trip_name, "sales_invoice", "", update_modified=False)


def apply_transport_defaults(doc):
	if doc.posting_date and not doc.due_date:
		doc.due_date = doc.posting_date

	if not doc.st_copy_label:
		doc.st_copy_label = "ORIGINAL FOR RECIPIENT"

	if not doc.st_service_name:
		doc.st_service_name = DEFAULT_SERVICE_NAME

	if not doc.st_service_period and doc.posting_date:
		doc.st_service_period = getdate(doc.posting_date).strftime("%b %Y")

	if not doc.st_location_of_supply:
		doc.st_location_of_supply = get_invoice_state(doc)

	if not doc.st_invoice_type:
		doc.st_invoice_type = get_default_invoice_type(doc)

	if not doc.st_sac_code:
		doc.st_sac_code = "996511" if is_bill_of_supply(doc) else "996791"


def sync_trip_details(doc):
	rows = [row for row in doc.get("st_trip_details", []) if row.trip]
	doc.set("st_trip_details", rows)

	if not rows:
		return

	seen_trip_names = set()
	for row in doc.get("st_trip_details", []):
		if row.trip in seen_trip_names:
			frappe.throw(_("Trip {0} is selected more than once.").format(row.trip))
		seen_trip_names.add(row.trip)

		trip_data = get_trip_billing_data(row.trip)
		if trip_data["status"] != BILLABLE_TRIP_STATUS:
			frappe.throw(
				_("Trip {0} must be in Completed status before billing.").format(row.trip)
			)

		if not doc.customer:
			doc.customer = trip_data["customer"]
		if not doc.company:
			doc.company = trip_data["company"]

		if trip_data["customer"] != doc.customer:
			frappe.throw(
				_("Trip {0} belongs to customer {1}, not {2}.").format(
					row.trip, trip_data["customer"], doc.customer
				)
			)

		if doc.company and trip_data["company"] and trip_data["company"] != doc.company:
			frappe.throw(
				_("Trip {0} belongs to company {1}, not {2}.").format(
					row.trip, trip_data["company"], doc.company
				)
			)

		existing_invoice = trip_data["sales_invoice"]
		if existing_invoice and existing_invoice != doc.name:
			frappe.throw(
				_("Trip {0} is already linked to Sales Invoice {1}.").format(
					row.trip, existing_invoice
				)
			)

		row.lorry_receipt = trip_data["lorry_receipt"]
		row.lr_date = trip_data["lr_date"]
		row.vehicle_no = trip_data["vehicle_no"]
		row.from_location = trip_data["from_location"]
		row.to_location = trip_data["to_location"]
		row.material = trip_data["material"]
		row.gate_pass_no = trip_data["gate_pass_no"]
		row.weight_mt = trip_data["weight_mt"]
		row.rate_per_mt = trip_data["rate_per_mt"]
		row.amount = trip_data["amount"]


def sync_invoice_item(doc):
	if not doc.get("st_trip_details"):
		return

	item_meta = frappe.db.get_value(
		"Item",
		TRANSPORT_SERVICE_ITEM,
		["item_name", "stock_uom", "description"],
		as_dict=True,
	)
	if not item_meta:
		frappe.throw(
			_("Transport service item {0} was not found.").format(TRANSPORT_SERVICE_ITEM)
		)

	total_weight = sum(flt(row.weight_mt) for row in doc.get("st_trip_details", []))
	total_amount = sum(flt(row.amount) for row in doc.get("st_trip_details", []))
	average_rate = total_amount / total_weight if total_weight else total_amount

	if doc.get("items"):
		item = doc.items[0]
		doc.set("items", [item])
	else:
		item = doc.append("items", {})

	item.item_code = TRANSPORT_SERVICE_ITEM
	item.item_name = item_meta.item_name or "Transport Freight Service"
	item.uom = item_meta.stock_uom or "MT"
	item.qty = total_weight or 1
	item.rate = average_rate or total_amount
	item.description = build_transport_description(doc, item_meta.description)


def build_transport_description(doc, default_description=None):
	description = doc.st_service_name or default_description or DEFAULT_SERVICE_NAME
	details = []
	if doc.st_service_period:
		details.append(_("Period of service: {0}").format(doc.st_service_period))
	if doc.st_location_of_supply:
		details.append(_("Location of Supply: {0}").format(doc.st_location_of_supply))
	return "\n".join([description, *details]) if details else description


def get_trip_billing_data(trip_name):
	trip = frappe.db.get_value(
		"Trip",
		trip_name,
		[
			"name",
			"customer",
			"company",
			"status",
			"sales_invoice",
			"lorry_receipt",
			"vehicle",
			"freight_rate_per_mt",
			"planned_tonnage",
			"delivered_tonnage",
			"loading_point",
			"unloading_point",
			"chemical_name",
		],
		as_dict=True,
	)
	if not trip:
		frappe.throw(_("Trip {0} was not found.").format(trip_name))

	lr = {}
	if trip.lorry_receipt:
		lr = frappe.db.get_value(
			"Lorry Receipt",
			trip.lorry_receipt,
			["lr_date", "gate_pass_no", "goods_description", "quantity_mt", "freight_amount"],
			as_dict=True,
		) or {}

	vehicle_no = ""
	if trip.vehicle:
		vehicle_no = frappe.db.get_value("Vehicle", trip.vehicle, "license_plate") or trip.vehicle

	weight_mt = flt(trip.delivered_tonnage) or flt(trip.planned_tonnage) or flt(lr.get("quantity_mt"))
	rate_per_mt = flt(trip.freight_rate_per_mt)
	if not rate_per_mt and weight_mt and flt(lr.get("freight_amount")):
		rate_per_mt = flt(lr.get("freight_amount")) / weight_mt

	amount = flt(weight_mt) * flt(rate_per_mt)

	return {
		"customer": trip.customer,
		"company": trip.company,
		"status": trip.status,
		"sales_invoice": trip.sales_invoice,
		"lorry_receipt": trip.lorry_receipt,
		"lr_date": lr.get("lr_date"),
		"vehicle_no": vehicle_no,
		"from_location": trip.loading_point,
		"to_location": trip.unloading_point,
		"material": trip.chemical_name or lr.get("goods_description"),
		"gate_pass_no": lr.get("gate_pass_no"),
		"weight_mt": weight_mt,
		"rate_per_mt": rate_per_mt,
		"amount": amount,
	}


def get_invoice_state(doc):
	address_name = doc.shipping_address_name or doc.customer_address
	if address_name and frappe.db.exists("Address", address_name):
		return (frappe.db.get_value("Address", address_name, "state") or "").upper()
	return ""


def get_default_invoice_type(doc):
	return "Bill of Supply" if is_bill_of_supply(doc) else "Tax Invoice"


def is_bill_of_supply(doc):
	if cint(doc.st_reverse_charge_applicable):
		return True
	if flt(doc.total_taxes_and_charges):
		return False
	return not any(flt(tax.tax_amount) or flt(tax.rate) for tax in doc.get("taxes", []))


@frappe.whitelist()
def get_unbilled_trips(customer=None, company=None, from_date=None, to_date=None, excluded_trips=None):
	if not customer:
		return []

	excluded = frappe.parse_json(excluded_trips) if excluded_trips else []
	excluded = excluded or []

	conditions = [
		"trip.customer = %s",
		"trip.status = %s",
		"ifnull(trip.sales_invoice, '') = ''",
	]
	values = [customer, BILLABLE_TRIP_STATUS]

	if company:
		conditions.append("trip.company = %s")
		values.append(company)

	if from_date:
		conditions.append("trip.dispatch_date >= %s")
		values.append(getdate(from_date))

	if to_date:
		conditions.append("trip.dispatch_date <= %s")
		values.append(getdate(to_date))

	if excluded:
		placeholders = ", ".join(["%s"] * len(excluded))
		conditions.append(f"trip.name not in ({placeholders})")
		values.extend(excluded)

	return frappe.db.sql(
		f"""
		select
			trip.name,
			trip.dispatch_date,
			trip.lorry_receipt,
			trip.vehicle,
			trip.loading_point,
			trip.unloading_point,
			trip.chemical_name,
			trip.delivered_tonnage,
			trip.planned_tonnage,
			trip.freight_rate_per_mt
		from `tabTrip` trip
		where {' and '.join(conditions)}
		order by trip.dispatch_date asc, trip.modified asc
		""",
		values,
		as_dict=True,
	)
