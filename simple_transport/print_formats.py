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
{% set gross_weight = doc.gross_weight_mt or doc.quantity_mt or 0 %}
{% set net_weight = doc.quantity_mt or 0 %}

<div class="st-lr-sheet">
	<div class="st-lr-card">
		<div class="st-lr-card__header">
			<div class="st-lr-card__logo-wrap">
				{% if company and company.company_logo %}
				<img class="st-lr-card__logo" src="{{ company.company_logo }}" alt="{{ company.company_name or doc.company }}">
				{% else %}
				<div class="st-lr-card__logo-fallback">SST</div>
				{% endif %}
			</div>
			<div class="st-lr-card__brand">
				<div class="st-lr-card__company">{{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport Private Limited' }}</div>
				<div class="st-lr-card__subtitle">TRANSPORT CONTRACTOR</div>
				{% if company_address %}
				<div class="st-lr-card__address">
					{{ company_address.address_line1 or '' }}{% if company_address.address_line2 %}, {{ company_address.address_line2 }}{% endif %}{% if company_address.city %}, {{ company_address.city }}{% endif %}{% if company_address.pincode %} - {{ company_address.pincode }}{% endif %}{% if company and company.phone_no %}. M. {{ company.phone_no }}{% endif %}{% if company and company.email %}, Email : {{ company.email }}{% endif %}
				</div>
				{% elif doc.company_address_display %}
				<div class="st-lr-card__address">{{ doc.company_address_display | safe }}</div>
				{% endif %}
			</div>
			<div class="st-lr-card__date">
				<div class="st-lr-card__date-label">Date :</div>
				<div class="st-lr-card__date-value">{{ frappe.format(doc.lr_date, {'fieldtype': 'Date'}) if doc.lr_date else '' }}</div>
			</div>
		</div>

		<div class="st-lr-card__route-row">
			<div class="st-lr-card__route-box">
				<div class="st-lr-card__route-label">From :</div>
				<div class="st-lr-card__route-value">
					{% if doc.consignor_name %}<div>{{ doc.consignor_name }}</div>{% endif %}
					<div>{{ doc.loading_point or '' }}</div>
				</div>
			</div>
			<div class="st-lr-card__route-box">
				<div class="st-lr-card__route-label">To :</div>
				<div class="st-lr-card__route-value">
					{% if doc.consignee_name %}<div>{{ doc.consignee_name }}</div>{% endif %}
					<div>{{ doc.unloading_point or '' }}</div>
				</div>
			</div>
		</div>

		<table class="st-lr-card__cargo">
			<colgroup>
				<col style="width: 30%;">
				<col style="width: 50%;">
				<col style="width: 20%;">
			</colgroup>
			<tr>
				<td class="st-lr-card__meta-head"></td>
				<td class="st-lr-card__material-head"></td>
				<td class="st-lr-card__weight-head">Weight</td>
			</tr>
			<tr>
				<td class="st-lr-card__meta-body">
					<div><strong>LR No.</strong> {{ doc.name }}</div>
					<div><strong>Gate Pass No.</strong> {{ doc.gate_pass_no or '' }}</div>
					<div><strong>Vehicle No.</strong> {{ vehicle.license_plate if vehicle and vehicle.license_plate else doc.vehicle or '' }}</div>
					<div><strong>Driver</strong> {{ driver_name or '' }}</div>
					{% if doc.customer %}<div><strong>Customer</strong> {{ doc.customer }}</div>{% endif %}
				</td>
				<td class="st-lr-card__material-body">
					<div class="st-lr-card__material">{{ doc.goods_description or '' }}</div>
					{% if doc.remarks %}
					<div class="st-lr-card__remarks">{{ doc.remarks | replace('\\n', '<br>') | safe }}</div>
					{% endif %}
				</td>
				<td class="st-lr-card__weight-body">
					<div class="st-lr-card__weight-label">G.W.</div>
					<div class="st-lr-card__weight-value">{{ '{0:.3f}'.format(gross_weight or 0) if gross_weight else '' }}</div>
					<div class="st-lr-card__weight-sep"></div>
					<div class="st-lr-card__weight-label">N.W.</div>
					<div class="st-lr-card__weight-value">{{ '{0:.3f}'.format(net_weight or 0) if net_weight else '' }}</div>
				</td>
			</tr>
		</table>

		<div class="st-lr-card__footer">
			<table class="st-lr-card__gst">
				<tr>
					<th colspan="2">The Person liable for Paying G.S.T.</th>
				</tr>
				<tr>
					<td>Consignor</td>
					<td>{% if (doc.gst_payable_by or '') == 'Consignor' %}&#10003;{% endif %}</td>
				</tr>
				<tr>
					<td>Consignee</td>
					<td>{% if (doc.gst_payable_by or '') == 'Consignee' %}&#10003;{% endif %}</td>
				</tr>
				<tr>
					<td>GTA</td>
					<td>{% if (doc.gst_payable_by or '') == 'GTA' %}&#10003;{% endif %}</td>
				</tr>
			</table>

			<div class="st-lr-card__sign-box">
				<div class="st-lr-card__gstin">{{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport Private Limited' }} GSTIN : {{ company.tax_id if company and company.tax_id else '-' }}</div>
				<div class="st-lr-card__sign-spacer"></div>
				<div class="st-lr-card__sign-text">For {{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport Pvt. Ltd.' }}</div>
			</div>
		</div>

		<div class="st-lr-card__jurisdiction">Subject to Baroda Jurisdiction Only.</div>
	</div>
</div>
"""

LORRY_RECEIPT_CSS = """
.st-lr-sheet {
	font-family: Arial, sans-serif;
	color: #111111;
	font-size: 11px;
}

.st-lr-card {
	border: 1px solid #000000;
	padding: 16px 12px 10px;
	min-height: 760px;
	box-sizing: border-box;
	page-break-inside: avoid;
}

.st-lr-card__header {
	display: flex;
	align-items: flex-start;
	gap: 12px;
}

.st-lr-card__logo-wrap {
	width: 64px;
	flex: 0 0 64px;
	padding-top: 4px;
}

.st-lr-card__logo {
	width: 58px;
	height: 58px;
	object-fit: contain;
}

.st-lr-card__logo-fallback {
	width: 58px;
	height: 58px;
	border: 2px solid #000000;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 18px;
	font-weight: 700;
}

.st-lr-card__brand {
	flex: 1 1 auto;
	text-align: center;
	padding-right: 12px;
}

.st-lr-card__company {
	font-family: Tahoma, Arial, sans-serif;
	font-size: 24px;
	font-weight: 700;
	line-height: 1.05;
}

.st-lr-card__subtitle {
	margin-top: 6px;
	font-size: 14px;
	font-weight: 700;
	letter-spacing: 0.02em;
}

.st-lr-card__address {
	margin-top: 6px;
	font-size: 10px;
	line-height: 1.3;
}

.st-lr-card__date {
	width: 120px;
	flex: 0 0 120px;
	font-size: 11px;
	font-style: italic;
	padding-top: 24px;
}

.st-lr-card__date-label {
	font-weight: 700;
}

.st-lr-card__date-value {
	margin-top: 4px;
	border-bottom: 1px solid #000000;
	min-height: 16px;
}

.st-lr-card__route-row {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 14px;
	margin-top: 12px;
}

.st-lr-card__route-box {
	border: 1px solid #000000;
	border-top: 0;
	padding: 6px 8px 8px;
	min-height: 62px;
}

.st-lr-card__route-label {
	font-size: 12px;
	font-weight: 700;
	margin-bottom: 8px;
}

.st-lr-card__route-value {
	border-bottom: 1px solid #000000;
	min-height: 28px;
	padding-bottom: 4px;
	line-height: 1.2;
}

.st-lr-card__cargo,
.st-lr-card__gst {
	width: 100%;
	border-collapse: collapse;
	margin-top: 12px;
}

.st-lr-card__cargo td,
.st-lr-card__gst td,
.st-lr-card__gst th {
	border: 1px solid #000000;
	vertical-align: top;
}

.st-lr-card__meta-head,
.st-lr-card__material-head,
.st-lr-card__weight-head {
	height: 24px;
	font-size: 12px;
	font-weight: 700;
	text-align: center;
}

.st-lr-card__meta-body,
.st-lr-card__material-body,
.st-lr-card__weight-body {
	height: 300px;
}

.st-lr-card__meta-body {
	padding: 10px 10px 8px;
	font-size: 10px;
	line-height: 1.55;
}

.st-lr-card__meta-body strong {
	display: inline-block;
	min-width: 78px;
}

.st-lr-card__material-body {
	padding: 16px 16px 10px;
}

.st-lr-card__material {
	font-size: 21px;
	font-weight: 700;
	line-height: 1.4;
	white-space: pre-wrap;
}

.st-lr-card__remarks {
	margin-top: 18px;
	font-size: 11px;
	line-height: 1.35;
}

.st-lr-card__weight-body {
	padding: 12px 8px;
	text-align: center;
}

.st-lr-card__weight-label {
	font-size: 22px;
	font-weight: 700;
	margin-top: 6px;
}

.st-lr-card__weight-value {
	min-height: 56px;
	font-size: 18px;
	font-weight: 700;
	display: flex;
	align-items: center;
	justify-content: center;
}

.st-lr-card__weight-sep {
	border-top: 1px solid #000000;
	margin: 6px -8px 4px;
}

.st-lr-card__footer {
	display: grid;
	grid-template-columns: 44% 56%;
	gap: 18px;
	margin-top: 12px;
	align-items: start;
}

.st-lr-card__gst th {
	padding: 6px 8px;
	font-size: 9px;
	font-weight: 700;
	text-align: left;
}

.st-lr-card__gst td {
	padding: 6px 8px;
	font-size: 10px;
	font-weight: 700;
}

.st-lr-card__gst td:last-child {
	width: 34px;
	text-align: center;
	font-size: 14px;
}

.st-lr-card__sign-box {
	border: 1px solid #000000;
	min-height: 138px;
	padding: 14px 12px 10px;
	display: flex;
	flex-direction: column;
}

.st-lr-card__gstin {
	font-size: 11px;
	font-weight: 700;
	line-height: 1.35;
}

.st-lr-card__sign-spacer {
	flex: 1 1 auto;
}

.st-lr-card__sign-text {
	font-size: 15px;
	font-weight: 700;
	text-align: right;
}

.st-lr-card__jurisdiction {
	margin-top: 12px;
	font-size: 10px;
	font-style: italic;
	font-weight: 700;
}
"""

SALES_INVOICE_HTML = """
{% set company = frappe.get_doc('Company', doc.company) if doc.company else None %}
{% set company_address_link = frappe.get_all('Dynamic Link', filters={'link_doctype': 'Company', 'link_name': doc.company, 'parenttype': 'Address'}, fields=['parent'], limit=1) if doc.company else [] %}
{% set company_address = frappe.get_doc('Address', company_address_link[0].parent) if company_address_link else None %}
{% set customer_tax_id = frappe.db.get_value('Customer', doc.customer, 'tax_id') if doc.customer else '' %}
{% set customer_state = frappe.db.get_value('Address', doc.customer_address, 'state') if doc.customer_address else '' %}
{% set company_tax_id = company.tax_id if company and company.tax_id else '' %}
{% set company_pan = company_tax_id[2:12] if company_tax_id and company_tax_id|length >= 12 else '' %}
{% set customer_pan = customer_tax_id[2:12] if customer_tax_id and customer_tax_id|length >= 12 else '' %}
{% set customer_state_code = customer_tax_id[:2] if customer_tax_id and customer_tax_id|length >= 2 else '' %}
{% set bank_account_name = company.default_bank_account if company and company.default_bank_account else frappe.db.get_value('Bank Account', {'party_type': 'Company', 'party': doc.company, 'is_company_account': 1}, 'name') %}
{% set bank_account = frappe.get_doc('Bank Account', bank_account_name) if bank_account_name else None %}
{% set invoice_title = doc.st_invoice_type or ('Bill of Supply' if doc.st_reverse_charge_applicable else 'Tax Invoice') %}
{% set total_amount = doc.total or doc.net_total or 0 %}
{% set grand_total = doc.rounded_total or doc.grand_total or total_amount %}
{% set qr_code = doc.get('st_qr_code') or doc.get('irn_qr_code') or doc.get('qr_code') %}
{% set trip_rows = doc.get('st_trip_details') or [] %}
{% set ns = namespace(total_weight=0, filler_rows=8 - (trip_rows | length)) %}
{% if ns.filler_rows < 0 %}{% set ns.filler_rows = 0 %}{% endif %}

<div class="st-invoice">
	<table class="st-invoice__header-grid">
		<colgroup>
			<col style="width: 77%;">
			<col style="width: 23%;">
		</colgroup>
		<tr>
			<td class="st-invoice__brand-cell">
				<div class="st-invoice__brand-wrap">
					<div class="st-invoice__logo-wrap">
						{% if company and company.company_logo %}
						<img class="st-invoice__logo" src="{{ company.company_logo }}" alt="{{ company.company_name or doc.company }}">
						{% endif %}
					</div>
					<div class="st-invoice__brand-copy">
						<div class="st-invoice__company-name">{{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }}</div>
						<div class="st-invoice__company-meta">{% if company_tax_id %}GSTIN: {{ company_tax_id }}{% endif %}{% if company_pan %} PAN No: {{ company_pan }}{% endif %}</div>
						{% if company_address %}
						<div class="st-invoice__company-address">
							{{ company_address.address_line1 or '' }}{% if company_address.address_line2 %}, {{ company_address.address_line2 }}{% endif %}{% if company_address.city %}, {{ company_address.city }}{% endif %}{% if company_address.pincode %}, Pin Code : {{ company_address.pincode }}{% endif %}
						</div>
						{% elif doc.company_address_display %}
						<div class="st-invoice__company-address">{{ doc.company_address_display | safe }}</div>
						{% endif %}
						<div class="st-invoice__company-contact">{% if company and company.phone_no %}Phone No : {{ company.phone_no }}{% endif %}{% if company and company.email %}{% if company.phone_no %}, {% endif %}Mail Id: {{ company.email }}{% endif %}</div>
					</div>
				</div>
			</td>
			<td class="st-invoice__copy-cell">
				<div class="st-invoice__copy-label">{{ doc.st_copy_label or 'ORIGINAL FOR RECIPIENT' }}</div>
				<div class="st-invoice__qr-box">
					{% if qr_code %}
					<img class="st-invoice__qr" src="{{ qr_code }}" alt="QR Code">
					{% endif %}
				</div>
			</td>
		</tr>
	</table>

	<table class="st-invoice__party-grid">
		<colgroup>
			<col style="width: 60%;">
			<col style="width: 18%;">
			<col style="width: 4%;">
			<col style="width: 18%;">
		</colgroup>
		<tr>
			<td class="st-invoice__party-cell" rowspan="6">
				<div class="st-invoice__to-line">
					<span>To,</span>
					<span>{{ invoice_title | upper }}</span>
				</div>
				<div class="st-invoice__customer-name">{{ doc.customer_name or doc.customer or '-' }}</div>
				{% if doc.address_display %}
				<div class="st-invoice__customer-address">{{ doc.address_display | safe }}</div>
				{% endif %}
				{% if customer_pan %}
				<div class="st-invoice__party-meta">PAN NO : {{ customer_pan }}</div>
				{% endif %}
				{% if customer_tax_id %}
				<div class="st-invoice__party-meta">GSTIN : {{ customer_tax_id }}{% if customer_state %} State : {{ customer_state }}{% if customer_state_code %} ({{ customer_state_code }}){% endif %}{% endif %}</div>
				{% endif %}
			</td>
			<td class="st-invoice__meta-label">Invoice No</td>
			<td class="st-invoice__meta-colon">:</td>
			<td class="st-invoice__meta-value">{{ doc.name }}</td>
		</tr>
		<tr>
			<td class="st-invoice__meta-label">Date</td>
			<td class="st-invoice__meta-colon">:</td>
			<td class="st-invoice__meta-value">{{ frappe.format(doc.posting_date, {'fieldtype': 'Date'}) if doc.posting_date else '' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__meta-label">Period of service</td>
			<td class="st-invoice__meta-colon">:</td>
			<td class="st-invoice__meta-value">{{ doc.st_service_period or '-' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__meta-label">Location of Supply</td>
			<td class="st-invoice__meta-colon">:</td>
			<td class="st-invoice__meta-value">{{ doc.st_location_of_supply or '-' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__meta-label">Reverse Charge</td>
			<td class="st-invoice__meta-colon">:</td>
			<td class="st-invoice__meta-value">{{ 'YES' if doc.st_reverse_charge_applicable else '' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__meta-label">&nbsp;</td>
			<td class="st-invoice__meta-colon">&nbsp;</td>
			<td class="st-invoice__meta-value">&nbsp;</td>
		</tr>
	</table>

	<table class="st-invoice__service-grid">
		<tr>
			<td>Service : {{ doc.st_service_name or 'Transportation Service' }}</td>
		</tr>
		<tr>
			<td>SAC Code : {{ doc.st_sac_code or '-' }}</td>
		</tr>
		<tr>
			<td>IRN No.:- {{ doc.st_irn_no or '' }}</td>
		</tr>
	</table>

	<table class="st-invoice__detail-grid">
		<colgroup>
			<col style="width: 4%;">
			<col style="width: 10%;">
			<col style="width: 8%;">
			<col style="width: 9%;">
			<col style="width: 14%;">
			<col style="width: 13%;">
			<col style="width: 13%;">
			<col style="width: 9%;">
			<col style="width: 6%;">
			<col style="width: 7%;">
			<col style="width: 7%;">
		</colgroup>
		<tr class="st-invoice__table-head">
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
		{% for row in trip_rows %}
		{% set ns.total_weight = ns.total_weight + (row.weight_mt or 0) %}
		<tr class="st-invoice__item-row">
			<td class="st-invoice__center">{{ loop.index }}</td>
			<td>{{ frappe.format(row.lr_date, {'fieldtype': 'Date'}) if row.lr_date else '' }}</td>
			<td>{{ row.lorry_receipt or '' }}</td>
			<td>{{ row.vehicle_no or '' }}</td>
			<td>{{ row.from_location or '' }}</td>
			<td>{{ row.to_location or '' }}</td>
			<td>{{ row.material or '' }}</td>
			<td>{{ row.gate_pass_no or '' }}</td>
			<td class="st-invoice__number">{{ '{0:.3f}'.format(row.weight_mt or 0) if row.weight_mt else '' }}</td>
			<td class="st-invoice__number">{{ frappe.format(row.rate_per_mt, {'fieldtype': 'Currency'}) if row.rate_per_mt else '' }}</td>
			<td class="st-invoice__number">{{ frappe.format(row.amount, {'fieldtype': 'Currency'}) if row.amount else '' }}</td>
		</tr>
		{% endfor %}
		{% for _ in range(ns.filler_rows) %}
		<tr class="st-invoice__item-row st-invoice__item-row--blank">
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
			<td>&nbsp;</td>
		</tr>
		{% endfor %}
		<tr class="st-invoice__summary-row">
			<td colspan="7" rowspan="{{ 3 + (doc.taxes | length) }}" class="st-invoice__summary-space">&nbsp;</td>
			<td colspan="2" class="st-invoice__summary-label">Total Weight:</td>
			<td colspan="2" class="st-invoice__summary-value">{{ '{0:.3f}'.format(ns.total_weight) if ns.total_weight else '0.000' }}</td>
		</tr>
		<tr class="st-invoice__summary-row">
			<td colspan="2" class="st-invoice__summary-label">Taxable Amt</td>
			<td colspan="2" class="st-invoice__summary-value">{{ frappe.format(total_amount, {'fieldtype': 'Currency'}) }}</td>
		</tr>
		{% for tax in doc.taxes %}
		<tr class="st-invoice__summary-row">
			<td colspan="2" class="st-invoice__summary-label">{{ tax.description or tax.account_head }}{% if tax.rate %} @{{ '{0:g}'.format(tax.rate) }}%{% endif %}</td>
			<td colspan="2" class="st-invoice__summary-value">{{ frappe.format(tax.tax_amount, {'fieldtype': 'Currency'}) }}</td>
		</tr>
		{% endfor %}
		<tr class="st-invoice__summary-row st-invoice__grand-row">
			<td colspan="7" class="st-invoice__inwords">Total Invoice Value : {{ doc.in_words or '-' }}</td>
			<td colspan="2" class="st-invoice__summary-label">Grand Total</td>
			<td colspan="2" class="st-invoice__summary-value">{{ frappe.format(grand_total, {'fieldtype': 'Currency'}) }}</td>
		</tr>
	</table>

	<table class="st-invoice__footer-grid">
		<colgroup>
			<col style="width: 60%;">
			<col style="width: 40%;">
		</colgroup>
		<tr>
			<td class="st-invoice__footer-note" colspan="2"><span>Remarks :</span> {{ (doc.remarks or '') | replace('\\n', '<br>') | safe }}</td>
		</tr>
		<tr>
			<td class="st-invoice__terms-cell">{{ doc.terms | safe if doc.terms else 'Terms & Conditions :' }}</td>
			<td class="st-invoice__sign-head">For : {{ company.company_name if company and company.company_name else doc.company or 'Shree Shiv Transport' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__bank-cell">
				<div><strong>A/c Name :</strong> {{ bank_account.account_name if bank_account and bank_account.account_name else company.company_name if company and company.company_name else doc.company or '-' }} <strong>Bank Name :</strong> {{ bank_account.bank if bank_account and bank_account.bank else '-' }}</div>
			</td>
			<td class="st-invoice__sign-cell" rowspan="3">
				<div class="st-invoice__sign-spacer"></div>
				<div class="st-invoice__sign-label">Authorised Signatory</div>
			</td>
		</tr>
		<tr>
			<td class="st-invoice__bank-cell"><strong>A/c No :</strong> {{ bank_account.bank_account_no if bank_account and bank_account.bank_account_no else '-' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__bank-cell"><strong>Branch Name :</strong> {{ bank_account.branch_code if bank_account and bank_account.branch_code else '-' }} <strong>IFSC Code :</strong> {{ bank_account.branch_code if bank_account and bank_account.branch_code else '-' }}</td>
		</tr>
		<tr>
			<td class="st-invoice__system-note" colspan="2">This is system generated invoice and does not require signature</td>
		</tr>
	</table>
</div>
"""

SALES_INVOICE_CSS = """
.st-invoice {
	font-family: Calibri, Arial, sans-serif;
	font-size: 9px;
	color: #000000;
}

.st-invoice table {
	width: 100%;
	border-collapse: collapse;
	table-layout: fixed;
}

.st-invoice__header-grid,
.st-invoice__party-grid,
.st-invoice__service-grid,
.st-invoice__detail-grid,
.st-invoice__footer-grid {
	border: 1px solid #000000;
}

.st-invoice__party-grid,
.st-invoice__service-grid,
.st-invoice__detail-grid,
.st-invoice__footer-grid {
	margin-top: -1px;
}

.st-invoice__header-grid td,
.st-invoice__party-grid td,
.st-invoice__detail-grid td,
.st-invoice__detail-grid th,
.st-invoice__footer-grid td {
	border: 1px solid #000000;
	vertical-align: top;
}

.st-invoice__service-grid td {
	border-top: 1px solid #000000;
	padding: 2px 6px;
	font-size: 9px;
	font-weight: 700;
	line-height: 1.15;
}

.st-invoice__brand-cell {
	padding: 6px 8px 4px;
}

.st-invoice__brand-wrap {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	min-height: 98px;
}

.st-invoice__logo-wrap {
	width: 78px;
	flex: 0 0 78px;
	position: relative;
}

.st-invoice__logo {
	max-width: 72px;
	max-height: 46px;
	object-fit: contain;
	position: absolute;
	top: -10px;
	left: -4px;
}

.st-invoice__brand-copy {
	flex: 1 1 auto;
	text-align: center;
}

.st-invoice__company-name {
	font-size: 24px;
	font-weight: 700;
	line-height: 1;
	margin-top: 6px;
}

.st-invoice__company-meta {
	margin-top: 4px;
	font-size: 10px;
	font-weight: 700;
}

.st-invoice__company-address,
.st-invoice__company-contact {
	margin-top: 3px;
	font-size: 10px;
	font-weight: 700;
	line-height: 1.2;
}

.st-invoice__company-address p,
.st-invoice__customer-address p,
.st-invoice__terms-cell p {
	margin: 0;
}

.st-invoice__copy-cell {
	padding: 6px 8px 4px;
}

.st-invoice__copy-label {
	font-size: 12px;
	font-weight: 700;
	color: #cc0000;
	line-height: 1.1;
	text-transform: uppercase;
}

.st-invoice__qr-box {
	width: 96px;
	height: 96px;
	margin-top: 8px;
	border: 1px solid #000000;
	display: flex;
	align-items: center;
	justify-content: center;
}

.st-invoice__qr {
	width: 88px;
	height: 88px;
	object-fit: contain;
}

.st-invoice__party-cell {
	padding: 3px 8px 2px;
}

.st-invoice__to-line {
	display: flex;
	gap: 38px;
	font-size: 12px;
	font-weight: 700;
	line-height: 1.1;
}

.st-invoice__customer-name {
	margin-top: 6px;
	font-size: 10px;
	font-weight: 700;
}

.st-invoice__customer-address {
	margin-top: 3px;
	font-size: 9px;
	font-weight: 700;
	line-height: 1.2;
}

.st-invoice__party-meta {
	margin-top: 4px;
	font-size: 9px;
	font-weight: 700;
	line-height: 1.1;
}

.st-invoice__meta-label,
.st-invoice__meta-colon,
.st-invoice__meta-value {
	padding: 3px 4px;
	font-size: 9px;
	font-weight: 700;
	line-height: 1.1;
}

.st-invoice__meta-label {
	text-align: left;
}

.st-invoice__meta-colon {
	text-align: center;
}

.st-invoice__table-head th {
	padding: 3px 2px;
	font-size: 9px;
	font-weight: 700;
	text-align: center;
	line-height: 1.1;
}

.st-invoice__item-row td {
	padding: 2px 3px;
	font-size: 8.7px;
	line-height: 1.08;
	height: 22px;
}

.st-invoice__item-row--blank td {
	height: 20px;
}

.st-invoice__center {
	text-align: center;
}

.st-invoice__number {
	text-align: right;
}

.st-invoice__summary-row td {
	padding: 3px 4px;
	font-size: 9px;
	font-weight: 700;
	line-height: 1.1;
}

.st-invoice__summary-space {
	background: #ffffff;
}

.st-invoice__summary-label {
	text-align: left;
}

.st-invoice__summary-value {
	text-align: right;
}

.st-invoice__grand-row td {
	padding-top: 4px;
	padding-bottom: 4px;
}

.st-invoice__inwords {
	font-size: 8px;
	font-weight: 700;
	line-height: 1.15;
}

.st-invoice__footer-note,
.st-invoice__terms-cell,
.st-invoice__bank-cell,
.st-invoice__sign-head,
.st-invoice__sign-cell,
.st-invoice__system-note {
	padding: 4px 6px;
	font-size: 8px;
	line-height: 1.15;
}

.st-invoice__footer-note span {
	font-weight: 700;
}

.st-invoice__terms-cell {
	min-height: 44px;
	vertical-align: top;
}

.st-invoice__sign-head {
	font-size: 10px;
	font-weight: 700;
}

.st-invoice__sign-cell {
	height: 92px;
	text-align: center;
	vertical-align: bottom;
}

.st-invoice__sign-spacer {
	height: 42px;
}

.st-invoice__sign-label {
	font-size: 10px;
	font-weight: 700;
}

.st-invoice__bank-cell strong {
	font-weight: 700;
}

.st-invoice__system-note {
	font-size: 8px;
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
