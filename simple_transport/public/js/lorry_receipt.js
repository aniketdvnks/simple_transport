frappe.ui.form.on("Lorry Receipt", {
	setup(frm) {
		frm.set_query("route_master", () => ({
			filters: { is_active: 1 },
		}));

		frm.set_query("driver", () => ({
			filters: {
				status: "Active",
				st_is_driver: 1,
			},
		}));

		frm.set_query("vehicle", () => ({
			filters: {
				st_operational_status: ["not in", ["Under Maintenance"]],
			},
		}));
	},

	refresh(frm) {
		if (frm.is_new() && frappe.user_roles.includes("ST Operation Manager") && !frm.doc.operation_manager) {
			frm.set_value("operation_manager", frappe.session.user);
		}

		if (frm.doc.docstatus === 1 && !frm.doc.trip && frappe.model.can_create("Trip")) {
			frm.add_custom_button(__("Start Trip"), () => {
				frappe.new_doc("Trip", {
					lorry_receipt: frm.doc.name,
				});
			},);
		}

		if (frm.doc.trip) {
			frm.add_custom_button(__("Open Trip"), () => {
				frappe.set_route("Form", "Trip", frm.doc.trip);
			}, __("View"));
		}

		if (frm.doc.trip) {
			frappe.db.get_value("Trip", frm.doc.trip, ["sales_invoice", "status", "dispatch_date"]).then(({ message }) => {
				if (!message) {
					return;
				}

				if (message.sales_invoice) {
					frm.add_custom_button(__("Open Sales Invoice"), () => {
						frappe.set_route("Form", "Sales Invoice", message.sales_invoice);
					}, __("View"));
					return;
				}

				if (message.status === "Completed" && frappe.model.can_create("Sales Invoice")) {
					frm.add_custom_button(__("Create Sales Invoice"), () => {
						frappe.route_options = {
							customer: frm.doc.customer,
							company: frm.doc.company,
							st_service_period: get_service_period(frm.doc.lr_date || message.dispatch_date),
							st_seed_trip: frm.doc.trip,
						};
						frappe.new_doc("Sales Invoice");
					}, __("Create"));
				}
			});
		}

		frm.set_intro(
			"Create one Lorry Receipt per vehicle dispatch. Trip should be created against the submitted LR for live execution tracking.",
			"blue"
		);
	},

	customer(frm) {
		fetch_contract_rate(frm);
	},

	route_master(frm) {
		fetch_contract_rate(frm);
	},

	goods_description(frm) {
		fetch_contract_rate(frm);
	},

	lr_date(frm) {
		fetch_contract_rate(frm);
	},

	quantity_mt(frm) {
		set_freight_amount(frm);
	},

	freight_rate_per_mt(frm) {
		set_freight_amount(frm);
	},
});

function fetch_contract_rate(frm) {
	if (!frm.doc.customer || !frm.doc.route_master) {
		set_freight_amount(frm);
		return;
	}

	frappe.call({
		method: "simple_transport.simple_transport.doctype.lorry_receipt.lorry_receipt.get_contract_rate",
		args: {
			customer: frm.doc.customer,
			route_master: frm.doc.route_master,
			material: frm.doc.goods_description,
			lr_date: frm.doc.lr_date,
		},
		callback: (r) => {
			if (!r.message) {
				return;
			}

			if (!frm.doc.freight_rate_per_mt || frm.is_new()) {
				frm.set_value("freight_rate_per_mt", r.message.freight_rate_per_mt || 0);
			} else {
				set_freight_amount(frm);
			}
		},
	});
}

function set_freight_amount(frm) {
	const amount = flt(frm.doc.quantity_mt) * flt(frm.doc.freight_rate_per_mt);
	frm.set_value("freight_amount", amount);
}

function get_service_period(dateValue) {
	const date = dateValue
		? frappe.datetime.str_to_obj(dateValue)
		: frappe.datetime.str_to_obj(frappe.datetime.get_today());
	return date.toLocaleString("en-IN", { month: "short", year: "numeric" });
}
