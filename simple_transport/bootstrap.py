from __future__ import annotations

import html
import json

import frappe
from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
from frappe.permissions import add_permission, update_permission_property


ROLE_EXECUTIVE = "ST C-Level Executive"
ROLE_OPERATIONS = "ST Operation Manager"
ROLE_DRIVER = "ST Driver"

PERMISSION_FLAGS = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"share",
	"print",
	"email",
)

DISPLAY_PERMISSION_FLAGS = (
	"read",
	"create",
	"write",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"print",
)

ROLE_DEFINITIONS = {
	ROLE_EXECUTIVE: {
		"description": "Approves fuel, monitors dispatch, and reviews billing, maintenance, and stock exposure.",
		"note": "Executive users can update approval and disbursement fields on submitted Fuel Requests and control the GPS webhook integration.",
			"permissions": {
				"Page": {"read": 1},
				"GPS Integration Settings": {"read": 1, "write": 1, "report": 1, "export": 1, "print": 1},
				"GPS Webhook Log": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Lorry Receipt": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Route Master": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Material": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Driver Assignment": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Trip": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Fuel Request": {"read": 1, "write": 1, "report": 1, "export": 1, "print": 1},
				"Sales Invoice": {"read": 1, "create": 1, "write": 1, "submit": 1, "cancel": 1, "amend": 1, "report": 1, "export": 1, "print": 1},
				"Customer": {"read": 1, "report": 1, "export": 1},
				"Vehicle": {"read": 1, "report": 1, "export": 1},
				"Vehicle Assignment": {"read": 1, "create": 1, "write": 1, "report": 1, "export": 1},
			"Employee": {"read": 1, "report": 1, "export": 1},
			"Asset": {"read": 1, "report": 1, "export": 1},
			"Asset Maintenance": {"read": 1, "report": 1, "export": 1},
			"Asset Repair": {"read": 1, "report": 1, "export": 1},
			"Item": {"read": 1, "report": 1, "export": 1},
			"Warehouse": {"read": 1, "report": 1, "export": 1},
			"Purchase Receipt": {"read": 1, "report": 1, "export": 1},
			"Stock Entry": {"read": 1, "report": 1, "export": 1},
		},
		"workspace": {
			"name": "ST Executive Console",
			"icon": "change",
			"indicator_color": "green",
			"custom_block": "ST C-Level Executive Permissions",
			"shortcuts": [
				{
					"color": "Orange",
					"doc_view": "List",
					"label": "Pending Fuel Approval",
					"link_to": "Fuel Request",
					"stats_filter": "{\"status\":[\"=\",\"Pending Approval\"]}",
					"type": "DocType",
				},
				{
					"color": "Blue",
					"doc_view": "List",
					"label": "Issued LRs",
					"link_to": "Lorry Receipt",
					"stats_filter": "{\"status\":[\"=\",\"Issued\"]}",
					"type": "DocType",
				},
				{
					"color": "Teal",
					"doc_view": "List",
					"label": "GPS Webhook Logs",
					"link_to": "GPS Webhook Log",
					"type": "DocType",
				},
				{
					"color": "Grey",
					"doc_view": "List",
					"label": "Trips",
					"link_to": "Trip",
					"type": "DocType",
					},
					{
						"color": "Grey",
						"doc_view": "List",
						"label": "Billing",
						"link_to": "Sales Invoice",
						"type": "DocType",
					},
			],
			"cards": [
				(
					"GPS Control",
					[
						("GPS Integration Settings", "DocType"),
						("GPS Webhook Log", "DocType"),
					],
				),
				(
					"Approvals",
					[
						("Fuel Request", "DocType"),
						("Lorry Receipt", "DocType"),
						("Trip", "DocType"),
					],
				),
					(
						"Dispatch & Billing",
						[
							("Vehicle Assignment", "DocType"),
							("Driver Assignment", "DocType"),
							("Sales Invoice", "DocType"),
							("Customer", "DocType"),
							("Material", "DocType"),
						],
					),
				(
					"Fleet & Maintenance",
					[
						("Vehicle", "DocType"),
						("Asset", "DocType"),
						("Asset Maintenance", "DocType"),
						("Asset Repair", "DocType"),
					],
				),
				(
					"Inventory",
					[
						("Item", "DocType"),
						("Warehouse", "DocType"),
						("Purchase Receipt", "DocType"),
						("Stock Entry", "DocType"),
					],
				),
			],
		},
	},
	ROLE_OPERATIONS: {
		"description": "Plans fleet allocation, creates lorry receipts, starts trips, and raises fuel requests.",
		"note": "Operations users can only access vehicles assigned through Vehicle Assignment, and Driver Assignment follows the same assigned-vehicle scope.",
			"permissions": {
				"Page": {"read": 1},
				"GPS Integration Settings": {"read": 1, "print": 1},
				"GPS Webhook Log": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Driver Assignment": {"read": 1, "create": 1, "write": 1, "submit": 1, "cancel": 1, "amend": 1, "report": 1, "export": 1, "print": 1},
				"Lorry Receipt": {"read": 1, "create": 1, "write": 1, "submit": 1, "cancel": 1, "amend": 1, "report": 1, "export": 1, "print": 1},
				"Route Master": {"read": 1, "create": 1, "write": 1, "report": 1, "export": 1, "print": 1},
				"Material": {"read": 1, "create": 1, "write": 1, "report": 1, "export": 1, "print": 1},
				"Trip": {"read": 1, "create": 1, "write": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
			"Fuel Request": {
				"read": 1,
				"create": 1,
				"write": 1,
				"submit": 1,
				"cancel": 1,
				"amend": 1,
				"report": 1,
				"export": 1,
				"print": 1,
			},
				"Sales Invoice": {"read": 1, "create": 1, "write": 1, "report": 1, "export": 1, "print": 1},
				"Customer": {"read": 1, "report": 1, "export": 1},
				"Vehicle": {"read": 1, "report": 1, "export": 1, "print": 1},
				"Vehicle Assignment": {"read": 1, "report": 1, "export": 1, "print": 1},
			"Employee": {"read": 1, "report": 1, "export": 1},
			"Asset": {"read": 1, "report": 1, "export": 1},
			"Asset Maintenance": {"read": 1, "create": 1, "write": 1, "report": 1, "export": 1},
			"Asset Repair": {
				"read": 1,
				"create": 1,
				"write": 1,
				"submit": 1,
				"cancel": 1,
				"amend": 1,
				"report": 1,
				"export": 1,
				"print": 1,
			},
			"Item": {"read": 1, "report": 1, "export": 1},
			"Warehouse": {"read": 1, "report": 1, "export": 1},
			"Purchase Receipt": {"read": 1, "report": 1, "export": 1, "print": 1},
			"Stock Entry": {"read": 1, "report": 1, "export": 1, "print": 1},
		},
		"workspace": {
			"name": "ST Operations Desk",
			"icon": "branch",
			"indicator_color": "orange",
			"custom_block": "ST Operation Manager Permissions",
			"shortcuts": [
				{
					"color": "Blue",
					"doc_view": "List",
					"label": "Issued LRs",
					"link_to": "Lorry Receipt",
					"stats_filter": "{\"status\":[\"=\",\"Issued\"]}",
					"type": "DocType",
				},
				{
					"color": "Orange",
					"doc_view": "List",
					"label": "Pending Fuel Approval",
					"link_to": "Fuel Request",
					"stats_filter": "{\"status\":[\"=\",\"Pending Approval\"]}",
					"type": "DocType",
				},
				{
					"color": "Teal",
					"doc_view": "List",
					"label": "GPS Logs",
					"link_to": "GPS Webhook Log",
					"type": "DocType",
				},
				{
					"color": "Green",
					"doc_view": "New",
					"label": "New Driver Assignment",
					"link_to": "Driver Assignment",
					"type": "DocType",
				},
				{
					"color": "Green",
					"doc_view": "New",
					"label": "New Lorry Receipt",
					"link_to": "Lorry Receipt",
						"type": "DocType",
				},
				{
					"color": "Green",
					"doc_view": "New",
					"label": "New Trip",
					"link_to": "Trip",
						"type": "DocType",
				},
			],
			"cards": [
				(
					"GPS Monitoring",
					[
						("GPS Webhook Log", "DocType"),
						("GPS Integration Settings", "DocType"),
					],
				),
				(
					"Transport Execution",
					[
						("Driver Assignment", "DocType"),
						("Lorry Receipt", "DocType"),
						("Trip", "DocType"),
							("Fuel Request", "DocType"),
							("Sales Invoice", "DocType"),
						],
					),
				(
					"Masters",
						[
							("Route Master", "DocType"),
							("Material", "DocType"),
							("Vehicle Assignment", "DocType"),
							("Driver Assignment", "DocType"),
							("Vehicle", "DocType"),
							("Employee", "DocType"),
						("Customer", "DocType"),
					],
				),
				(
					"Maintenance",
					[
						("Asset Maintenance", "DocType"),
						("Asset Repair", "DocType"),
						("Stock Entry", "DocType"),
					],
				),
				(
					"Inventory",
					[
						("Item", "DocType"),
						("Warehouse", "DocType"),
						("Purchase Receipt", "DocType"),
					],
				),
			],
		},
	},
	ROLE_DRIVER: {
		"description": "Views assigned trips, route details, vehicle details, and fuel request status from the desk.",
		"note": "Driver visibility is restricted to the logged-in employee mapped through Employee.user_id.",
		"permissions": {
			"Page": {"read": 1},
			"Lorry Receipt": {"read": 1, "report": 1, "print": 1},
			"Route Master": {"read": 1, "report": 1, "print": 1},
			"Driver Assignment": {"read": 1, "report": 1, "print": 1},
			"Trip": {"read": 1, "report": 1, "print": 1},
			"Fuel Request": {"read": 1, "report": 1, "print": 1},
			"Vehicle": {"read": 1, "print": 1},
			"Employee": {"read": 1, "print": 1},
		},
		"workspace": {
			"name": "ST Driver Hub",
			"icon": "stock",
			"indicator_color": "blue",
			"custom_block": "ST Driver Permissions",
			"shortcuts": [
				{
					"color": "Blue",
					"doc_view": "List",
					"label": "My Trips",
					"link_to": "Trip",
					"type": "DocType",
				},
				{
					"color": "Orange",
					"doc_view": "List",
					"label": "Fuel Requests",
					"link_to": "Fuel Request",
					"type": "DocType",
				},
				{
					"color": "Grey",
					"doc_view": "List",
					"label": "My Assignments",
					"link_to": "Driver Assignment",
					"type": "DocType",
				},
				{
					"color": "Grey",
					"doc_view": "List",
					"label": "My Vehicle",
					"link_to": "Vehicle",
					"type": "DocType",
				},
				{
					"color": "Grey",
					"doc_view": "List",
					"label": "My Employee Card",
					"link_to": "Employee",
					"type": "DocType",
				},
			],
			"cards": [
				(
						"Driver Desk",
						[
							("Driver Assignment", "DocType"),
							("Lorry Receipt", "DocType"),
							("Trip", "DocType"),
							("Fuel Request", "DocType"),
							("Route Master", "DocType"),
					],
				),
				(
					"Profile",
					[
						("Vehicle", "DocType"),
						("Employee", "DocType"),
					],
				),
			],
		},
	},
}

WORKSPACE_SEQUENCE = {
	ROLE_EXECUTIVE: 10.0,
	ROLE_OPERATIONS: 11.0,
	ROLE_DRIVER: 12.0,
}


def sync_transport_access():
	ensure_roles()
	ensure_role_permissions()
	ensure_permission_reports()
	ensure_workspaces()
	hide_legacy_workspace()
	frappe.clear_cache()


def ensure_roles():
	for role_name in ROLE_DEFINITIONS:
		if frappe.db.exists("Role", role_name):
			role = frappe.get_doc("Role", role_name)
			role.desk_access = 1
			role.save(ignore_permissions=True)
			continue

		role = frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1})
		role.insert(ignore_permissions=True)


def ensure_role_permissions():
	changed_doctypes = set()

	for role_name, config in ROLE_DEFINITIONS.items():
		for doctype, permissions in config["permissions"].items():
			if not frappe.db.exists("DocType", doctype):
				continue

			if not frappe.db.exists(
				"Custom DocPerm",
				{"parent": doctype, "role": role_name, "permlevel": 0, "if_owner": 0},
			):
				add_permission(doctype, role_name, 0)

			for flag in PERMISSION_FLAGS:
				update_permission_property(
					doctype,
					role_name,
					0,
					flag,
					1 if permissions.get(flag) else 0,
					validate=False,
				)

			changed_doctypes.add(doctype)

	for doctype in changed_doctypes:
		validate_permissions_for_doctype(doctype)
		frappe.clear_cache(doctype=doctype)


def ensure_permission_reports():
	for role_name, config in ROLE_DEFINITIONS.items():
		workspace = config["workspace"]
		block_name = workspace["custom_block"]

		if frappe.db.exists("Custom HTML Block", block_name):
			doc = frappe.get_doc("Custom HTML Block", block_name)
		else:
			doc = frappe.new_doc("Custom HTML Block")
			doc.name = block_name

		doc.html = build_permissions_report_html(role_name, config)
		doc.style = build_permissions_report_style()
		doc.script = ""
		doc.private = 0
		doc.set("roles", [])
		doc.append("roles", {"role": role_name})
		save_with_flags(doc)


def ensure_workspaces():
	for role_name, config in ROLE_DEFINITIONS.items():
		workspace_config = config["workspace"]
		workspace_name = workspace_config["name"]

		if frappe.db.exists("Workspace", workspace_name):
			doc = frappe.get_doc("Workspace", workspace_name)
		else:
			doc = frappe.new_doc("Workspace")
			doc.name = workspace_name

		doc.label = workspace_name
		doc.title = workspace_name
		doc.module = "Simple Transport"
		doc.public = 1
		doc.is_hidden = 0
		doc.hide_custom = 0
		doc.parent_page = ""
		doc.for_user = ""
		doc.icon = workspace_config["icon"]
		doc.indicator_color = workspace_config["indicator_color"]
		doc.sequence_id = WORKSPACE_SEQUENCE[role_name]
		doc.content = json.dumps(build_workspace_content(workspace_config), separators=(",", ":"))

		doc.set("roles", [])
		doc.append("roles", {"role": role_name})

		doc.set("charts", [])
		doc.set("number_cards", [])
		doc.set("quick_lists", [])
		doc.set("custom_blocks", [])
		doc.append(
			"custom_blocks",
			{
				"custom_block_name": workspace_config["custom_block"],
				"label": workspace_config["custom_block"],
			},
		)

		doc.set("shortcuts", [])
		for shortcut in workspace_config["shortcuts"]:
			doc.append("shortcuts", shortcut)

		doc.set("links", [])
		for card_name, card_links in workspace_config["cards"]:
			doc.append(
				"links",
				{
					"label": card_name,
					"type": "Card Break",
					"link_type": "DocType",
					"link_count": len(card_links),
					"hidden": 0,
					"is_query_report": 0,
					"onboard": 0,
				},
			)
			for label, link_type in card_links:
				doc.append(
					"links",
					{
						"label": label,
						"type": "Link",
						"link_to": label,
						"link_type": link_type,
						"link_count": 0,
						"hidden": 0,
						"is_query_report": 0,
						"onboard": 0,
					},
				)

		save_with_flags(doc)


def hide_legacy_workspace():
	if not frappe.db.exists("Workspace", "Simple Transport"):
		return

	workspace = frappe.get_doc("Workspace", "Simple Transport")
	workspace.is_hidden = 1
	workspace.save(ignore_permissions=True)


def build_permissions_report_html(role_name: str, config: dict) -> str:
	rows = []
	for doctype, permissions in config["permissions"].items():
		active_permissions = [
			flag.replace("_", " ").title()
			for flag in DISPLAY_PERMISSION_FLAGS
			if permissions.get(flag)
		]
		rows.append(
			f"""
			<tr>
				<td>{html.escape(doctype)}</td>
				<td>{html.escape(', '.join(active_permissions) or 'Read')}</td>
			</tr>
			"""
		)

	return f"""
	<section class="st-role-report">
		<div class="st-role-report__header">
			<div>
				<div class="st-role-report__kicker">Role Permission Report</div>
				<h3>{html.escape(role_name)}</h3>
				<p>{html.escape(config['description'])}</p>
			</div>
			<div class="st-role-report__metric">
				<span>{len(config['permissions'])}</span>
				<small>doctypes in scope</small>
			</div>
		</div>
		<table class="st-role-report__table">
			<thead>
				<tr>
					<th>DocType</th>
					<th>Permissions</th>
				</tr>
			</thead>
			<tbody>
				{''.join(rows)}
			</tbody>
		</table>
		<p class="st-role-report__note">{html.escape(config['note'])}</p>
	</section>
	"""


def build_permissions_report_style() -> str:
	return """
	.st-role-report {
		border: 1px solid #dbe5ec;
		border-radius: 18px;
		padding: 20px;
		background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%);
		box-shadow: 0 10px 30px rgba(24, 60, 84, 0.08);
	}
	.st-role-report__header {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		align-items: flex-start;
		margin-bottom: 16px;
	}
	.st-role-report__kicker {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #0d6b8f;
		margin-bottom: 8px;
	}
	.st-role-report__header h3 {
		margin: 0 0 8px;
		font-size: 24px;
		color: #163247;
	}
	.st-role-report__header p,
	.st-role-report__note {
		margin: 0;
		color: #466173;
		line-height: 1.5;
	}
	.st-role-report__metric {
		min-width: 120px;
		padding: 14px 16px;
		border-radius: 14px;
		background: #163247;
		color: #ffffff;
		text-align: center;
	}
	.st-role-report__metric span {
		display: block;
		font-size: 28px;
		font-weight: 700;
		line-height: 1;
	}
	.st-role-report__metric small {
		display: block;
		margin-top: 6px;
		font-size: 12px;
		opacity: 0.8;
	}
	.st-role-report__table {
		width: 100%;
		border-collapse: collapse;
		margin-bottom: 14px;
	}
	.st-role-report__table th,
	.st-role-report__table td {
		padding: 10px 12px;
		border-bottom: 1px solid #e4edf2;
		text-align: left;
		vertical-align: top;
	}
	.st-role-report__table th {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: #0d6b8f;
	}
	.st-role-report__table td:first-child {
		font-weight: 600;
		color: #163247;
		width: 28%;
	}
	@media (max-width: 768px) {
		.st-role-report__header {
			flex-direction: column;
		}
		.st-role-report__metric {
			width: 100%;
		}
	}
	"""


def build_workspace_content(workspace_config: dict) -> list[dict]:
	content = [
		{
			"type": "header",
			"data": {"text": f"<span class=\"h4\">{workspace_config['name']}</span>", "col": 12},
		},
		{
			"type": "custom_block",
			"data": {"custom_block_name": workspace_config["custom_block"], "col": 12},
		},
	]

	for shortcut in workspace_config["shortcuts"]:
		content.append({"type": "shortcut", "data": {"shortcut_name": shortcut["label"], "col": 3}})

	card_col = max(3, int(12 / max(len(workspace_config["cards"]), 1)))
	for card_name, _card_links in workspace_config["cards"]:
		content.append({"type": "card", "data": {"card_name": card_name, "col": card_col}})

	return content


def save_with_flags(doc):
	doc.flags.ignore_mandatory = True
	if doc.is_new():
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
	else:
		doc.save(ignore_permissions=True)
	return doc
