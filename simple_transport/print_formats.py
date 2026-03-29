from __future__ import annotations

import frappe


LORRY_RECEIPT_PRINT_FORMAT = "Lorry Receipt"
SALES_INVOICE_PRINT_FORMAT = "Transport Invoice"

LORRY_RECEIPT_HTML = """
{% set company = frappe.get_doc('Company', doc.company) if doc.company else None %}
{% set vehicle = frappe.get_doc('Vehicle', doc.vehicle) if doc.vehicle else None %}
{% set driver_name = frappe.db.get_value('Employee', doc.driver, 'employee_name') if doc.driver else '' %}
{% set company_address_link = frappe.get_all('Dynamic Link', filters={'link_doctype': 'Company', 'link_name': doc.company, 'parenttype': 'Address'}, fields=['parent'], limit=1) if doc.company else [] %}
{% set company_address = frappe.get_doc('Address', company_address_link[0].parent) if company_address_link else None %}

{% macro liable_cell(label) -%}
<td class="st-lr__liable {% if (doc.gst_payable_by or '') == label %}is-selected{% endif %}">{{ label }}</td>
{%- endmacro %}

{% macro lr_copy(copy_label) -%}
<div class="st-lr">
	<div class="st-lr__copy-label">{{ copy_label }}</div>
	<div class="st-lr__header">
		<div class="st-lr__brand">
			<div class="st-lr__company">{{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }}</div>
			<div class="st-lr__subtitle">TRANSPORT CONTRACTOR</div>
			{% if company_address %}
			<div>{{ company_address.address_line1 or '' }}{% if company_address.address_line2 %}, {{ company_address.address_line2 }}{% endif %}</div>
			<div>{{ company_address.city or '' }}{% if company_address.state %}, {{ company_address.state }}{% endif %}{% if company_address.pincode %} - {{ company_address.pincode }}{% endif %}</div>
			{% endif %}
			<div>
				{% if company and company.phone_no %}M. {{ company.phone_no }}{% endif %}
				{% if company and company.email %}{% if company.phone_no %}, {% endif %}Email : {{ company.email }}{% endif %}
			</div>
			<div>{{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }} GSTIN : {{ company.tax_id or '-' if company else '-' }}</div>
		</div>
		<div class="st-lr__meta">
			<div><strong>LR No :</strong> {{ doc.name }}</div>
			<div><strong>Date :</strong> {{ frappe.format(doc.lr_date, {'fieldtype': 'Date'}) }}</div>
			<div><strong>From :</strong> {{ doc.loading_point or '-' }}</div>
			<div><strong>Vehicle :</strong> {{ vehicle.license_plate if vehicle and vehicle.license_plate else doc.vehicle or '-' }}</div>
			<div><strong>Driver :</strong> {{ driver_name or doc.driver or '-' }}</div>
		</div>
	</div>

	<div class="st-lr__note">Subject to Baroda Jurisdiction Only.</div>

	<table class="st-lr__table">
		<tr>
			<th>Consignor</th>
			<td>
				<div><strong>{{ doc.consignor_name or doc.customer or '-' }}</strong></div>
				<div>{{ (doc.consignor_address or doc.loading_point or '-') | replace('\\n', '<br>') | safe }}</div>
				{% if doc.consignor_contact_no %}<div>Contact : {{ doc.consignor_contact_no }}</div>{% endif %}
			</td>
			<th>Consignee</th>
			<td>
				<div><strong>{{ doc.consignee_name or doc.unloading_point or '-' }}</strong></div>
				<div>{{ (doc.consignee_address or doc.unloading_point or '-') | replace('\\n', '<br>') | safe }}</div>
				{% if doc.consignee_contact_no %}<div>Contact : {{ doc.consignee_contact_no }}</div>{% endif %}
			</td>
		</tr>
		<tr>
			<th>Operation Manager</th>
			<td>{{ doc.operation_manager or '-' }}</td>
			<th>Route</th>
			<td>{{ doc.loading_point or '-' }} to {{ doc.unloading_point or '-' }}</td>
		</tr>
	</table>

	<table class="st-lr__table">
		<tr>
			<th>Material</th>
			<th>Gate Pass No</th>
			<th>Gross Weight</th>
			<th>Net Weight</th>
			<th>Freight Rate</th>
			<th>Freight Amount</th>
		</tr>
		<tr>
			<td>{{ doc.goods_description or '-' }}</td>
			<td>{{ doc.gate_pass_no or '-' }}</td>
			<td>{{ doc.gross_weight_mt or doc.quantity_mt or 0 }} MT</td>
			<td>{{ doc.quantity_mt or 0 }} MT</td>
			<td>{{ frappe.format(doc.freight_rate_per_mt, {'fieldtype': 'Currency'}) }} / MT</td>
			<td>{{ frappe.format(doc.freight_amount, {'fieldtype': 'Currency'}) }}</td>
		</tr>
	</table>

	<table class="st-lr__liable-table">
		<tr>
			<th colspan="3">The Person liable for Paying G.S.T.</th>
		</tr>
		<tr>
			{{ liable_cell('Consignor') }}
			{{ liable_cell('Consignee') }}
			{{ liable_cell('GTA') }}
		</tr>
	</table>

	{% if doc.remarks %}
	<div class="st-lr__remarks">
		<div class="st-lr__remarks-title">Remarks</div>
		<div>{{ doc.remarks | replace('\\n', '<br>') | safe }}</div>
	</div>
	{% endif %}

	<div class="st-lr__sign">
		<div class="st-lr__sign-line"></div>
		<div>For {{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }}</div>
	</div>
</div>
{%- endmacro %}

<div class="st-lr-sheet">
	{{ lr_copy('Office Copy') }}
	<div class="st-lr-sheet__divider"></div>
	{{ lr_copy('Party Copy') }}
</div>
"""

LORRY_RECEIPT_CSS = """
.st-lr-sheet {
	font-size: 11px;
	color: #1f2933;
}
.st-lr-sheet__divider {
	border-top: 1px dashed #718096;
	margin: 18px 0;
}
.st-lr {
	padding: 6px 4px;
}
.st-lr__copy-label {
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	text-align: right;
	margin-bottom: 4px;
}
.st-lr__header {
	display: flex;
	justify-content: space-between;
	gap: 18px;
	margin-bottom: 8px;
}
.st-lr__brand {
	max-width: 68%;
}
.st-lr__company {
	font-size: 18px;
	font-weight: 700;
}
.st-lr__subtitle {
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 0.08em;
	margin-bottom: 6px;
}
.st-lr__meta {
	min-width: 220px;
	border: 1px solid #8796a5;
	padding: 10px 12px;
}
.st-lr__meta div + div {
	margin-top: 4px;
}
.st-lr__note {
	font-weight: 700;
	margin-bottom: 8px;
}
.st-lr__table,
.st-lr__liable-table {
	width: 100%;
	border-collapse: collapse;
	margin-bottom: 10px;
}
.st-lr__table th,
.st-lr__table td,
.st-lr__liable-table th,
.st-lr__liable-table td {
	border: 1px solid #8796a5;
	padding: 7px 8px;
	vertical-align: top;
}
.st-lr__table th,
.st-lr__liable-table th {
	background: #edf2f7;
	font-weight: 700;
}
.st-lr__liable {
	text-align: center;
	font-weight: 600;
}
.st-lr__liable.is-selected {
	background: #d9efe0;
}
.st-lr__remarks {
	border: 1px solid #8796a5;
	padding: 8px 10px;
	margin-bottom: 18px;
}
.st-lr__remarks-title {
	font-weight: 700;
	margin-bottom: 4px;
}
.st-lr__sign {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	margin-top: 18px;
}
.st-lr__sign-line {
	width: 180px;
	border-top: 1px solid #1f2933;
	margin-bottom: 6px;
	padding-top: 26px;
}
"""

SALES_INVOICE_HTML = """
{% set company = frappe.get_doc('Company', doc.company) if doc.company else None %}
{% set customer_tax_id = frappe.db.get_value('Customer', doc.customer, 'tax_id') if doc.customer else '' %}
{% set customer_state = frappe.db.get_value('Address', doc.customer_address, 'state') if doc.customer_address else '' %}
{% set company_tax_id = company.tax_id if company and company.tax_id else '' %}
{% set company_pan = company_tax_id[2:12] if company_tax_id and company_tax_id|length >= 12 else '' %}
{% set customer_pan = customer_tax_id[2:12] if customer_tax_id and customer_tax_id|length >= 12 else '' %}
{% set customer_state_code = customer_tax_id[:2] if customer_tax_id and customer_tax_id|length >= 2 else '' %}
{% set bank_account_name = company.default_bank_account if company and company.default_bank_account else frappe.db.get_value('Bank Account', {'party_type': 'Company', 'party': doc.company, 'is_company_account': 1}, 'name') %}
{% set bank_account = frappe.get_doc('Bank Account', bank_account_name) if bank_account_name else None %}
{% set invoice_title = doc.st_invoice_type or ('Bill of Supply' if doc.st_reverse_charge_applicable else 'Tax Invoice') %}
{% set total_amount = doc.total or doc.net_total %}
{% set grand_total = doc.rounded_total or doc.grand_total %}
{% set ns = namespace(total_weight=0) %}

<div class="st-invoice">
	<div class="st-invoice__header">
		<div class="st-invoice__company">
			<div class="st-invoice__company-name">{{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }}</div>
			<div>
				{% if company and company.tax_id %}GSTIN: {{ company.tax_id }}{% endif %}
				{% if company_pan %} PAN No: {{ company_pan }}{% endif %}
			</div>
			{% if doc.company_address_display %}
			<div class="st-invoice__address">{{ doc.company_address_display | safe }}</div>
			{% endif %}
			<div>
				{% if company and company.phone_no %}Phone No : {{ company.phone_no }}{% endif %}
				{% if company and company.email %}{% if company.phone_no %}, {% endif %}Mail Id: {{ company.email }}{% endif %}
			</div>
		</div>
		<div class="st-invoice__copy-label">{{ doc.st_copy_label or 'ORIGINAL FOR RECIPIENT' }}</div>
	</div>

	<table class="st-invoice__party">
		<tr>
			<td class="st-invoice__party-left">
				<div class="st-invoice__title-line">To, <span>{{ invoice_title }}</span></div>
				<div class="st-invoice__customer-name">{{ doc.customer_name or doc.customer or '-' }}</div>
				{% if doc.address_display %}
				<div class="st-invoice__address">{{ doc.address_display | safe }}</div>
				{% endif %}
				{% if customer_pan %}<div>PAN NO : {{ customer_pan }}</div>{% endif %}
				{% if customer_tax_id %}<div>GSTIN : {{ customer_tax_id }}{% if customer_state %} State : {{ customer_state }}{% if customer_state_code %} ({{ customer_state_code }}){% endif %}{% endif %}</div>{% endif %}
			</td>
			<td class="st-invoice__party-right">
				<table class="st-invoice__meta">
					<tr><th>Invoice No</th><td>{{ doc.name }}</td></tr>
					<tr><th>Date</th><td>{{ frappe.format(doc.posting_date, {'fieldtype': 'Date'}) }}</td></tr>
					<tr><th>Period of service</th><td>{{ doc.st_service_period or '-' }}</td></tr>
					<tr><th>Location of Supply</th><td>{{ doc.st_location_of_supply or '-' }}</td></tr>
					{% if doc.st_reverse_charge_applicable %}
					<tr><th>Reverse Charge Applicable</th><td>YES</td></tr>
					{% endif %}
				</table>
			</td>
		</tr>
	</table>

	<div class="st-invoice__service">
		<div><strong>Service</strong> : {{ doc.st_service_name or 'Transportation Service' }}</div>
		<div><strong>SAC Code</strong> : {{ doc.st_sac_code or '-' }}</div>
		{% if doc.st_irn_no %}<div><strong>IRN No.</strong> : {{ doc.st_irn_no }}</div>{% endif %}
	</div>

	<table class="st-invoice__table">
		<tr>
			<th>S.No</th>
			<th>Date</th>
			<th>LR No.</th>
			<th>Vehicle No</th>
			<th>From</th>
			<th>To</th>
			<th>Material</th>
			<th>Gate Pass No</th>
			<th>Weight</th>
			<th>Rate</th>
			<th>Amount</th>
		</tr>
		{% for row in doc.st_trip_details %}
		{% set ns.total_weight = ns.total_weight + (row.weight_mt or 0) %}
		<tr>
			<td>{{ loop.index }}</td>
			<td>{{ frappe.format(row.lr_date, {'fieldtype': 'Date'}) if row.lr_date else '-' }}</td>
			<td>{{ row.lorry_receipt or '-' }}</td>
			<td>{{ row.vehicle_no or '-' }}</td>
			<td>{{ row.from_location or '-' }}</td>
			<td>{{ row.to_location or '-' }}</td>
			<td>{{ row.material or '-' }}</td>
			<td>{{ row.gate_pass_no or '-' }}</td>
			<td class="st-invoice__number">{{ '{0:.3f}'.format(row.weight_mt or 0) }}</td>
			<td class="st-invoice__number">{{ frappe.format(row.rate_per_mt, {'fieldtype': 'Currency'}) }}</td>
			<td class="st-invoice__number">{{ frappe.format(row.amount, {'fieldtype': 'Currency'}) }}</td>
		</tr>
		{% endfor %}
		<tr class="st-invoice__total-row">
			<td colspan="8" class="st-invoice__label">Total Weight:</td>
			<td class="st-invoice__number">{{ '{0:.3f}'.format(ns.total_weight) }}</td>
			<td></td>
			<td class="st-invoice__number">{{ frappe.format(total_amount, {'fieldtype': 'Currency'}) }}</td>
		</tr>
	</table>

	<table class="st-invoice__totals">
		<tr><th>Total Amt</th><td>{{ frappe.format(total_amount, {'fieldtype': 'Currency'}) }}</td></tr>
		{% for tax in doc.taxes %}
		<tr>
			<th>{{ tax.description or tax.account_head }}{% if tax.rate %} @{{ tax.rate }}%{% endif %}</th>
			<td>{{ frappe.format(tax.tax_amount, {'fieldtype': 'Currency'}) }}</td>
		</tr>
		{% endfor %}
		<tr><th>Round Off</th><td>{{ frappe.format(doc.rounding_adjustment, {'fieldtype': 'Currency'}) }}</td></tr>
		<tr class="st-invoice__grand-total"><th>Grand Total</th><td>{{ frappe.format(grand_total, {'fieldtype': 'Currency'}) }}</td></tr>
	</table>

	<div class="st-invoice__words">Total Invoice Value : {{ doc.in_words or '-' }}</div>

	{% if doc.remarks %}
	<div class="st-invoice__notes"><strong>Remarks :</strong> {{ doc.remarks | replace('\\n', '<br>') | safe }}</div>
	{% endif %}

	{% if doc.terms %}
	<div class="st-invoice__notes"><strong>Terms & Conditions :</strong> {{ doc.terms | safe }}</div>
	{% endif %}

	<div class="st-invoice__footer">
		<div class="st-invoice__bank">
			{% if bank_account %}
			<div><strong>A/c Name :</strong> {{ bank_account.account_name or '-' }} <strong>Bank Name :</strong> {{ bank_account.bank or '-' }}</div>
			<div><strong>A/c No :</strong> {{ bank_account.bank_account_no or '-' }}</div>
			<div><strong>Branch Code :</strong> {{ bank_account.branch_code or '-' }}</div>
			{% else %}
			<div>Company bank account is not configured.</div>
			{% endif %}
			<div>This is system generated invoice and does not require signature</div>
		</div>
		<div class="st-invoice__sign">
			<div>For : {{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }}</div>
			<div class="st-invoice__sign-line"></div>
			<div>Authorised Signatory</div>
		</div>
	</div>
</div>
"""

SALES_INVOICE_CSS = """
.st-invoice {
	font-size: 11px;
	color: #1f2933;
}
.st-invoice__header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 18px;
	margin-bottom: 12px;
}
.st-invoice__company {
	max-width: 72%;
}
.st-invoice__company-name {
	font-size: 20px;
	font-weight: 700;
	margin-bottom: 4px;
}
.st-invoice__copy-label {
	border: 1px solid #8796a5;
	padding: 10px 14px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.06em;
}
.st-invoice__address {
	margin: 4px 0;
}
.st-invoice__party,
.st-invoice__meta,
.st-invoice__table,
.st-invoice__totals {
	width: 100%;
	border-collapse: collapse;
}
.st-invoice__party td,
.st-invoice__meta th,
.st-invoice__meta td,
.st-invoice__table th,
.st-invoice__table td,
.st-invoice__totals th,
.st-invoice__totals td {
	border: 1px solid #8796a5;
	padding: 7px 8px;
	vertical-align: top;
}
.st-invoice__party-left,
.st-invoice__party-right {
	width: 50%;
}
.st-invoice__title-line {
	font-size: 14px;
	font-weight: 700;
	margin-bottom: 8px;
}
.st-invoice__title-line span {
	text-transform: uppercase;
}
.st-invoice__customer-name {
	font-size: 13px;
	font-weight: 700;
	margin-bottom: 6px;
}
.st-invoice__meta th,
.st-invoice__table th,
.st-invoice__totals th {
	background: #edf2f7;
	font-weight: 700;
}
.st-invoice__service {
	display: flex;
	flex-wrap: wrap;
	gap: 18px;
	margin: 10px 0 12px;
}
.st-invoice__number {
	text-align: right;
	white-space: nowrap;
}
.st-invoice__total-row td {
	font-weight: 700;
}
.st-invoice__label {
	text-align: right;
}
.st-invoice__totals {
	margin-top: 12px;
	margin-left: auto;
	width: 320px;
}
.st-invoice__grand-total th,
.st-invoice__grand-total td {
	font-size: 12px;
}
.st-invoice__words {
	font-weight: 700;
	margin: 12px 0;
}
.st-invoice__notes {
	margin-bottom: 8px;
}
.st-invoice__footer {
	display: flex;
	justify-content: space-between;
	gap: 24px;
	margin-top: 18px;
}
.st-invoice__bank {
	max-width: 64%;
}
.st-invoice__sign {
	min-width: 220px;
	text-align: right;
}
.st-invoice__sign-line {
	border-top: 1px solid #1f2933;
	margin: 36px 0 6px auto;
	width: 180px;
}
"""


def ensure_lorry_receipt_print_format():
	upsert_print_format(
		print_format_name=LORRY_RECEIPT_PRINT_FORMAT,
		doc_type="Lorry Receipt",
		html=LORRY_RECEIPT_HTML,
		css=LORRY_RECEIPT_CSS,
	)


def ensure_sales_invoice_print_format():
	upsert_print_format(
		print_format_name=SALES_INVOICE_PRINT_FORMAT,
		doc_type="Sales Invoice",
		html=SALES_INVOICE_HTML,
		css=SALES_INVOICE_CSS,
	)


def upsert_print_format(print_format_name: str, doc_type: str, html: str, css: str):
	if frappe.db.exists("Print Format", print_format_name):
		doc = frappe.get_doc("Print Format", print_format_name)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = print_format_name

	doc.doc_type = doc_type
	doc.module = "Simple Transport"
	doc.standard = "No"
	doc.custom_format = 1
	doc.disabled = 0
	doc.print_format_type = "Jinja"
	doc.print_format_for = "DocType"
	doc.html = html
	doc.css = css
	doc.margin_top = 8
	doc.margin_bottom = 8
	doc.margin_left = 8
	doc.margin_right = 8
	doc.flags.ignore_mandatory = True

	if doc.is_new():
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
	else:
		doc.save(ignore_permissions=True)
