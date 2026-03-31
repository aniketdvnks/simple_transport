from __future__ import annotations

import base64
import hmac
import json
import re
from datetime import datetime, timezone

import frappe
from frappe import _
from frappe.exceptions import AuthenticationError
from frappe.utils import cint, flt, now_datetime
from simple_transport.vehicle_status import (
	ACTIVE_TRIP_STATUSES,
	get_vehicle_status_from_trip_status,
	sync_vehicle_status,
)


WEBHOOK_TYPE_LABELS = {
	"geo": "Geo Data",
	"trip": "Trip Data",
	"vehicle": "Vehicle Data",
	"dtc": "DTC Data",
	"alert": "Alert Log",
}

ENDPOINT_PATHS = {
	"geo_endpoint_path": "/api/method/simple_transport.gps_integration.receive_geo_data",
	"trip_endpoint_path": "/api/method/simple_transport.gps_integration.receive_trip_data",
	"vehicle_endpoint_path": "/api/method/simple_transport.gps_integration.receive_vehicle_data",
	"dtc_endpoint_path": "/api/method/simple_transport.gps_integration.receive_dtc_data",
	"alert_endpoint_path": "/api/method/simple_transport.gps_integration.receive_alert_log",
}

LAST_ACTIVITY_FIELDS = {
	"geo": "last_geo_on",
	"trip": "last_trip_on",
	"vehicle": "last_vehicle_on",
	"dtc": "last_dtc_on",
	"alert": "last_alert_on",
}

class GPSWebhookSkip(Exception):
	def __init__(self, message: str, **context):
		super().__init__(message)
		self.context = context


def get_relative_endpoint_paths() -> dict[str, str]:
	return dict(ENDPOINT_PATHS)


def ensure_gps_integration_settings():
	if not frappe.db.exists("DocType", "GPS Integration Settings"):
		return

	doc = frappe.get_single("GPS Integration Settings")
	changed = False
	for fieldname, value in get_relative_endpoint_paths().items():
		if doc.get(fieldname) != value:
			doc.set(fieldname, value)
			changed = True

	if changed:
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def receive_geo_data():
	return handle_webhook("geo")


@frappe.whitelist(allow_guest=True)
def receive_trip_data():
	return handle_webhook("trip")


@frappe.whitelist(allow_guest=True)
def receive_vehicle_data():
	return handle_webhook("vehicle")


@frappe.whitelist(allow_guest=True)
def receive_dtc_data():
	return handle_webhook("dtc")


@frappe.whitelist(allow_guest=True)
def receive_alert_log():
	return handle_webhook("alert")


def handle_webhook(webhook_type: str):
	settings = frappe.get_single("GPS Integration Settings")
	payload = get_request_payload()
	headers = get_sanitized_headers()

	if not cint(settings.enabled):
		save_webhook_log(
			webhook_type,
			payload,
			headers,
			status="Ignored",
			message="GPS integration is disabled.",
		)
		return {"ok": True, "status": "ignored", "message": "GPS integration is disabled."}

	try:
		validate_basic_auth(settings)
		result = PROCESSORS[webhook_type](payload, settings)
		touch_last_activity(webhook_type)
		save_webhook_log(
			webhook_type,
			payload,
			headers,
			status="Success",
			message=result.get("message"),
			context=result,
		)
		return {"ok": True, "status": "processed", **result}
	except GPSWebhookSkip as exc:
		touch_last_activity(webhook_type)
		context = dict(exc.context)
		context["message"] = str(exc)
		save_webhook_log(
			webhook_type,
			payload,
			headers,
			status="Ignored",
			message=str(exc),
			context=context,
		)
		return {"ok": True, "status": "ignored", **context}
	except Exception as exc:
		save_webhook_log(
			webhook_type,
			payload,
			headers,
			status="Failed",
			message="Webhook processing failed.",
			error_message=frappe.get_traceback(),
		)
		frappe.log_error(
			title=f"GPS {WEBHOOK_TYPE_LABELS[webhook_type]} webhook failed",
			message=frappe.get_traceback(),
		)
		raise exc


def process_webhook_payload(webhook_type: str, payload: dict | str, save_log: bool = True):
	"""Replay a webhook payload internally for support checks and automated tests."""
	if webhook_type not in PROCESSORS:
		frappe.throw(_("Unsupported webhook type: {0}").format(webhook_type))

	if isinstance(payload, str):
		payload = frappe.parse_json(payload)

	if not isinstance(payload, dict):
		frappe.throw(_("Webhook payload must be a JSON object."))

	settings = frappe.get_single("GPS Integration Settings")
	headers = {}

	try:
		result = PROCESSORS[webhook_type](payload, settings)
		touch_last_activity(webhook_type)
		if save_log:
			save_webhook_log(
				webhook_type,
				payload,
				headers,
				status="Success",
				message=result.get("message"),
				context=result,
			)
		frappe.db.commit()
		return {"ok": True, "status": "processed", **result}
	except GPSWebhookSkip as exc:
		touch_last_activity(webhook_type)
		context = dict(exc.context)
		context["message"] = str(exc)
		if save_log:
			save_webhook_log(
				webhook_type,
				payload,
				headers,
				status="Ignored",
				message=str(exc),
				context=context,
			)
		frappe.db.commit()
		return {"ok": True, "status": "ignored", **context}


def process_geo_data(payload, settings):
	if payload.get("t") not in ("G", None):
		raise GPSWebhookSkip("Payload is not a geo message.", entity="geo_data")

	vehicle_plate = payload.get("vehicle_id")
	vehicle = find_vehicle(
		plate=vehicle_plate,
		device_imei=payload.get("device_id"),
	)
	if not vehicle:
		raise GPSWebhookSkip(
			f"Vehicle {vehicle_plate or payload.get('device_id') or 'Unknown'} was not matched.",
			entity="geo_data",
			vehicle_plate=vehicle_plate,
			provider_id=payload.get("device_id"),
			request_refid=payload.get("refid"),
		)

	geo = payload.get("geo") or {}
	latitude = flt(geo.get("lat"))
	longitude = flt(geo.get("lng"))
	location_text = format_coordinates(latitude, longitude)
	event_time = epoch_millis_to_datetime(payload.get("time"))

	if cint(settings.auto_update_vehicle_data):
		update_vehicle_live_data(
			vehicle.name,
			{
				"st_gps_device_id": payload.get("device_id") or vehicle.st_gps_device_id,
				"st_last_gps_ping": event_time or now_datetime(),
				"st_last_latitude": latitude,
				"st_last_longitude": longitude,
				"st_last_speed_kmph": flt(payload.get("sp")),
				"st_last_heading_degree": flt(payload.get("hd")),
				"st_last_gps_accuracy": cint(geo.get("acc")),
				"st_last_location_text": location_text,
			},
		)

	trip = find_active_trip_for_vehicle(vehicle.name)
	if trip:
		update_trip_from_geo(
			trip,
			vehicle.name,
			event_time=event_time,
			location_text=location_text,
			speed=flt(payload.get("sp")),
			auto_update_trip_progress=cint(settings.auto_update_trip_progress),
		)

	return {
		"message": f"Geo data processed for vehicle {vehicle.name}.",
		"entity": "geo_data",
		"vehicle": vehicle.name,
		"trip": trip.name if trip else "",
		"vehicle_plate": vehicle_plate,
		"provider_id": payload.get("device_id"),
		"request_refid": payload.get("refid"),
		"event_time": event_time,
	}


def process_trip_data(payload, settings):
	data = unwrap_payload(payload)
	vehicle_data = data.get("vehicle") or {}
	vehicle = find_vehicle(
		plate=vehicle_data.get("plate"),
		provider_vehicle_id=vehicle_data.get("id"),
		tag=vehicle_data.get("tag"),
	)
	if not vehicle:
		raise GPSWebhookSkip(
			"Trip webhook could not be matched to a vehicle.",
			entity=data.get("entity") or payload.get("entity") or "trip",
			action=data.get("action") or payload.get("action"),
			provider_id=data.get("id"),
			vehicle_plate=vehicle_data.get("plate"),
		)

	trip = find_trip(provider_trip_id=data.get("id"), vehicle_name=vehicle.name)
	if not trip:
		raise GPSWebhookSkip(
			f"No active local Trip was found for vehicle {vehicle.name}.",
			entity=data.get("entity") or payload.get("entity") or "trip",
			action=data.get("action") or payload.get("action"),
			provider_id=data.get("id"),
			vehicle=vehicle.name,
			vehicle_plate=vehicle_data.get("plate"),
		)

	update_trip_from_provider_trip(
		trip,
		vehicle.name,
		data,
		auto_update_trip_progress=cint(settings.auto_update_trip_progress),
	)

	return {
		"message": f"Trip webhook processed for Trip {trip.name}.",
		"entity": data.get("entity") or payload.get("entity") or "trip",
		"action": data.get("action") or payload.get("action"),
		"vehicle": vehicle.name,
		"trip": trip.name,
		"vehicle_plate": vehicle_data.get("plate"),
		"provider_id": data.get("id"),
		"event_time": epoch_millis_to_datetime(data.get("end_time") or data.get("start_time")),
	}


def process_vehicle_data(payload, settings):
	data = unwrap_payload(payload)
	vehicle = find_vehicle(
		plate=data.get("plate"),
		provider_vehicle_id=data.get("id"),
		tracker_imei=data.get("tracker_imei"),
		tag=data.get("tag"),
	)
	if not vehicle:
		raise GPSWebhookSkip(
			"Vehicle webhook could not be matched to an existing Vehicle master.",
			entity=data.get("entity") or payload.get("entity") or "vehicle",
			action=data.get("action") or payload.get("action"),
			provider_id=data.get("id"),
			vehicle_plate=data.get("plate"),
		)

	if cint(settings.auto_update_vehicle_data):
		update_vehicle_live_data(
			vehicle.name,
			{
				"make": data.get("manufacturer") or vehicle.make,
				"model": data.get("model") or vehicle.model,
				"st_gps_provider_vehicle_id": data.get("id") or vehicle.st_gps_provider_vehicle_id,
				"st_gps_tracker_id": data.get("tracker_id") or vehicle.st_gps_tracker_id,
				"st_gps_tracker_imei": data.get("tracker_imei") or vehicle.st_gps_tracker_imei,
				"st_gps_device_id": data.get("tracker_imei") or vehicle.st_gps_device_id,
				"st_gps_vehicle_tag": data.get("tag") or vehicle.st_gps_vehicle_tag,
				"st_is_obd_enabled": cint(data.get("is_obd")),
				"st_obd_attached": cint(data.get("obd_attached")),
			},
		)

	return {
		"message": f"Vehicle webhook processed for vehicle {vehicle.name}.",
		"entity": data.get("entity") or payload.get("entity") or "vehicle",
		"action": data.get("action") or payload.get("action"),
		"vehicle": vehicle.name,
		"vehicle_plate": data.get("plate"),
		"provider_id": data.get("id"),
		"event_time": epoch_millis_to_datetime(data.get("updatedAt") or data.get("createdAt")),
	}


def process_dtc_data(payload, settings):
	data = unwrap_payload(payload)
	vehicle = find_vehicle(provider_vehicle_id=data.get("vehicle_id"))
	if not vehicle:
		raise GPSWebhookSkip(
			"DTC webhook could not be matched to a vehicle.",
			entity=data.get("entity") or payload.get("entity") or "dtcs_change_log",
			action=data.get("action") or payload.get("action"),
			provider_id=data.get("id"),
		)

	dtcs = data.get("dtcs") or []
	dtc_codes = ", ".join(filter(None, [row.get("code") for row in dtcs if isinstance(row, dict)]))

	return {
		"message": f"DTC webhook logged for vehicle {vehicle.name}{': ' + dtc_codes if dtc_codes else ''}.",
		"entity": data.get("entity") or payload.get("entity") or "dtcs_change_log",
		"action": data.get("action") or payload.get("action"),
		"vehicle": vehicle.name,
		"provider_id": data.get("id"),
		"event_time": epoch_millis_to_datetime(data.get("timestamp")),
	}


def process_alert_log(payload, settings):
	data = unwrap_payload(payload)
	vehicle = find_vehicle(
		plate=data.get("vehicle_plate"),
		provider_vehicle_id=data.get("vehicle_id"),
		tag=data.get("vehicle_tag"),
	)
	if not vehicle:
		raise GPSWebhookSkip(
			"Alert webhook could not be matched to a vehicle.",
			entity=data.get("entity") or payload.get("entity") or "alert_log",
			action=data.get("action") or payload.get("action"),
			provider_id=data.get("id"),
			vehicle_plate=data.get("vehicle_plate"),
		)

	alert_values = parse_embedded_json(data.get("alert_values"))
	location_text = data.get("address") or format_location_string(data.get("location"))
	event_time = epoch_millis_to_datetime(data.get("timestamp"))
	trip = find_active_trip_for_vehicle(vehicle.name)

	if cint(settings.auto_update_vehicle_data) and location_text:
		update_vehicle_live_data(
			vehicle.name,
			{
				"st_last_location_text": location_text,
				"st_last_gps_ping": event_time or now_datetime(),
			},
		)

	if trip and cint(settings.auto_update_trip_progress):
		update_trip_from_alert(
			trip,
			vehicle.name,
			alert_type=(data.get("type") or "").lower(),
			location_text=location_text,
			event_time=event_time,
			alert_values=alert_values,
		)

	return {
		"message": f"Alert webhook logged for vehicle {vehicle.name}.",
		"entity": data.get("entity") or payload.get("entity") or "alert_log",
		"action": data.get("action") or payload.get("action"),
		"vehicle": vehicle.name,
		"trip": trip.name if trip else "",
		"vehicle_plate": data.get("vehicle_plate"),
		"provider_id": data.get("id"),
		"event_time": event_time,
	}


PROCESSORS = {
	"geo": process_geo_data,
	"trip": process_trip_data,
	"vehicle": process_vehicle_data,
	"dtc": process_dtc_data,
	"alert": process_alert_log,
}


def get_request_payload():
	request = getattr(frappe.local, "request", None)
	raw_data = request.get_data(as_text=True) if request else ""
	if not raw_data:
		return {}

	try:
		payload = frappe.parse_json(raw_data)
	except Exception as exc:
		frappe.throw(_("Unable to parse JSON payload: {0}").format(exc))

	if not isinstance(payload, dict):
		frappe.throw(_("Webhook payload must be a JSON object."))

	return payload


def get_sanitized_headers():
	request = getattr(frappe.local, "request", None)
	if not request:
		return {}

	headers = {}
	for key, value in request.headers.items():
		if key.lower() == "authorization":
			continue
		headers[key] = value
	return headers


def validate_basic_auth(settings):
	if not cint(settings.enforce_basic_auth):
		return

	request = getattr(frappe.local, "request", None)
	auth_header = request.headers.get("Authorization", "") if request else ""
	if not auth_header.startswith("Basic "):
		frappe.throw(_("Missing basic authentication header."), AuthenticationError)

	try:
		decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
		username, password = decoded.split(":", 1)
	except Exception:
		frappe.throw(_("Invalid basic authentication header."), AuthenticationError)

	expected_username = settings.webhook_username or ""
	expected_password = settings.get_password("webhook_password") or ""
	if not (
		hmac.compare_digest(username, expected_username)
		and hmac.compare_digest(password, expected_password)
	):
		frappe.throw(_("Invalid webhook credentials."), AuthenticationError)


def touch_last_activity(webhook_type: str):
	fieldname = LAST_ACTIVITY_FIELDS.get(webhook_type)
	if fieldname:
		frappe.db.set_single_value("GPS Integration Settings", fieldname, now_datetime())


def save_webhook_log(
	webhook_type: str,
	payload: dict,
	headers: dict,
	status: str,
	message: str | None = None,
	context: dict | None = None,
	error_message: str | None = None,
):
	context = context or {}
	if not frappe.db.exists("DocType", "GPS Webhook Log"):
		return

	settings = frappe.get_single("GPS Integration Settings")
	if status == "Success" and not cint(settings.log_webhook_payloads):
		return

	doc = frappe.get_doc(
		{
			"doctype": "GPS Webhook Log",
			"webhook_type": WEBHOOK_TYPE_LABELS[webhook_type],
			"processing_status": status,
			"received_on": now_datetime(),
			"entity": context.get("entity") or "",
			"action": context.get("action") or "",
			"event_time": context.get("event_time"),
			"request_refid": context.get("request_refid") or "",
			"vehicle": context.get("vehicle") or "",
			"trip": context.get("trip") or "",
			"vehicle_plate": context.get("vehicle_plate") or "",
			"provider_id": context.get("provider_id") or "",
			"response_message": message or "",
			"error_message": error_message or "",
			"headers_json": to_pretty_json(headers),
			"payload_json": to_pretty_json(payload),
		}
	)
	doc.insert(ignore_permissions=True)


def unwrap_payload(payload: dict):
	data = {}
	if isinstance(payload.get("data"), dict):
		data.update(payload.get("data"))

	for key, value in payload.items():
		if key == "data" and isinstance(value, dict):
			continue
		data.setdefault(key, value)

	return data


def find_vehicle(
	plate: str | None = None,
	provider_vehicle_id: str | None = None,
	device_imei: str | None = None,
	tracker_imei: str | None = None,
	tag: str | None = None,
):
	fields = [
		"name",
		"license_plate",
		"make",
		"model",
		"st_gps_provider_vehicle_id",
		"st_gps_device_id",
		"st_gps_tracker_id",
		"st_gps_tracker_imei",
		"st_gps_vehicle_tag",
	]
	vehicles = frappe.get_all("Vehicle", fields=fields, limit_page_length=0)

	normalized_plate = normalize_identifier(plate)
	normalized_tag = normalize_identifier(tag)
	device_imei = (device_imei or "").strip()
	tracker_imei = (tracker_imei or "").strip()
	provider_vehicle_id = (provider_vehicle_id or "").strip()

	for vehicle in vehicles:
		if provider_vehicle_id and vehicle.st_gps_provider_vehicle_id == provider_vehicle_id:
			return frappe._dict(vehicle)

	for vehicle in vehicles:
		if device_imei and device_imei in {
			(vehicle.st_gps_device_id or "").strip(),
			(vehicle.st_gps_tracker_imei or "").strip(),
		}:
			return frappe._dict(vehicle)

	for vehicle in vehicles:
		if tracker_imei and tracker_imei in {
			(vehicle.st_gps_tracker_imei or "").strip(),
			(vehicle.st_gps_device_id or "").strip(),
		}:
			return frappe._dict(vehicle)

	for vehicle in vehicles:
		if normalized_plate and normalized_plate in {
			normalize_identifier(vehicle.license_plate),
			normalize_identifier(vehicle.name),
		}:
			return frappe._dict(vehicle)

	for vehicle in vehicles:
		if normalized_tag and normalized_tag == normalize_identifier(vehicle.st_gps_vehicle_tag):
			return frappe._dict(vehicle)

	return None


def find_active_trip_for_vehicle(vehicle_name: str):
	rows = frappe.get_all(
		"Trip",
		filters={"vehicle": vehicle_name, "status": ["in", list(ACTIVE_TRIP_STATUSES)]},
		fields=["name", "status", "actual_start_datetime", "actual_end_datetime"],
		order_by="modified desc",
		limit=1,
	)
	return frappe._dict(rows[0]) if rows else None


def find_trip(provider_trip_id: str | None = None, vehicle_name: str | None = None):
	if provider_trip_id:
		row = frappe.db.get_value(
			"Trip",
			{"st_gps_trip_id": provider_trip_id},
			["name", "status", "actual_start_datetime", "actual_end_datetime"],
			as_dict=True,
		)
		if row:
			return row

	if vehicle_name:
		return find_active_trip_for_vehicle(vehicle_name)

	return None


def update_vehicle_live_data(vehicle_name: str, values: dict):
	meta = frappe.get_meta("Vehicle")
	clean_values = {}
	for fieldname, value in values.items():
		if meta.has_field(fieldname) and value not in (None, ""):
			clean_values[fieldname] = value

	if clean_values:
		frappe.db.set_value("Vehicle", vehicle_name, clean_values, update_modified=False)


def update_trip_from_geo(
	trip,
	vehicle_name: str,
	event_time,
	location_text: str,
	speed: float,
	auto_update_trip_progress: bool,
):
	values = {
		"current_location": location_text,
		"st_last_gps_sync_on": now_datetime(),
	}
	status = trip.status

	if speed > 0 and not trip.actual_start_datetime and event_time:
		values["actual_start_datetime"] = event_time

	if auto_update_trip_progress and speed > 0 and status in {
		"Planned",
		"Ready for Dispatch",
		"At Loading Point",
		"On Hold",
	}:
		status = "In Transit"
		values["status"] = status

	frappe.db.set_value("Trip", trip.name, values, update_modified=False)
	sync_vehicle_trip_status(vehicle_name, trip.name, status)


def update_trip_from_provider_trip(trip, vehicle_name: str, data: dict, auto_update_trip_progress: bool):
	start_time = epoch_millis_to_datetime(data.get("start_time"))
	end_time = epoch_millis_to_datetime(data.get("end_time"))
	values = {
		"st_gps_trip_id": data.get("id"),
		"st_last_gps_sync_on": now_datetime(),
	}
	status = trip.status

	if data.get("distance") not in (None, ""):
		values["st_gps_distance_km"] = flt(data.get("distance"))

	if data.get("duration") not in (None, ""):
		values["st_gps_duration_ms"] = cint(flt(data.get("duration")))

	if start_time and not trip.actual_start_datetime:
		values["actual_start_datetime"] = start_time

	if cint(data.get("is_complete")):
		if end_time:
			values["actual_end_datetime"] = end_time
		status = "Completed"
		values["status"] = status
	elif auto_update_trip_progress and start_time and status in ACTIVE_TRIP_STATUSES and status != "In Transit":
		status = "In Transit"
		values["status"] = status

	frappe.db.set_value("Trip", trip.name, values, update_modified=False)
	sync_vehicle_trip_status(vehicle_name, trip.name, status)


def update_trip_from_alert(trip, vehicle_name: str, alert_type: str, location_text: str, event_time, alert_values: dict):
	values = {
		"st_last_gps_sync_on": now_datetime(),
	}
	if location_text:
		values["current_location"] = location_text

	status = trip.status
	if alert_type == "stoppage":
		stoppage_going_on = to_boolean(alert_values.get("stoppage_going_on"))
		if stoppage_going_on is True and status in {
			"At Loading Point",
			"At Unloading Point",
			"In Transit",
		}:
			status = "On Hold"
			values["status"] = status
		elif stoppage_going_on is False and status == "On Hold":
			status = "In Transit"
			values["status"] = status

	if event_time and not trip.actual_start_datetime and status in {"In Transit", "On Hold"}:
		values["actual_start_datetime"] = event_time

	frappe.db.set_value("Trip", trip.name, values, update_modified=False)
	sync_vehicle_trip_status(vehicle_name, trip.name, status)


def sync_vehicle_trip_status(vehicle_name: str, trip_name: str, trip_status: str):
	values = {
		"st_current_trip": trip_name if trip_status in ACTIVE_TRIP_STATUSES else "",
		"st_operational_status": get_vehicle_status_from_trip_status(trip_status),
	}
	frappe.db.set_value("Vehicle", vehicle_name, values, update_modified=False)
	if trip_status not in ACTIVE_TRIP_STATUSES:
		sync_vehicle_status(vehicle_name)


def epoch_millis_to_datetime(value):
	if value in (None, ""):
		return None

	try:
		millis = int(float(value))
	except (TypeError, ValueError):
		return None

	return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).replace(tzinfo=None)


def normalize_identifier(value):
	return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def format_coordinates(latitude: float, longitude: float):
	if not latitude and not longitude:
		return ""
	return f"{latitude:.6f}, {longitude:.6f}"


def format_location_string(value):
	if not value:
		return ""
	if isinstance(value, str):
		parts = [part.strip() for part in value.split(",")]
		if len(parts) >= 2:
			try:
				return format_coordinates(float(parts[0]), float(parts[1]))
			except (TypeError, ValueError):
				return value
	return str(value)


def parse_embedded_json(value):
	if isinstance(value, dict):
		return value
	if not value:
		return {}
	try:
		return json.loads(value)
	except Exception:
		return {}


def to_pretty_json(value):
	try:
		return json.dumps(value or {}, indent=2, sort_keys=True, default=str)
	except Exception:
		return "{}"


def to_boolean(value):
	if isinstance(value, bool):
		return value
	if value in (None, ""):
		return None
	if isinstance(value, (int, float)):
		return bool(value)
	return str(value).strip().lower() in {"1", "true", "yes", "y"}
