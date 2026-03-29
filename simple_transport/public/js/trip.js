frappe.ui.form.on("Trip", {
	setup(frm) {
		frm.set_query("lorry_receipt", () => ({
			filters: {
				docstatus: 1,
				trip: ["in", frm.doc.name ? ["", frm.doc.name] : [""]],
			},
		}));

		frm.set_query("route_master", () => ({
			filters: {
				is_active: 1,
			},
		}));

		frm.set_query("driver", () => ({
			filters: {
				status: "Active",
				st_is_driver: 1,
			},
		}));

		frm.set_query("vehicle", () => ({
			filters: {
				st_operational_status: ["not in", ["Under Maintenance", "Breakdown"]],
			},
			}));
		},

	refresh(frm) {
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("Open Sales Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
			}, __("View"));
			return;
		}

		if (frm.doc.status === "Completed" && frappe.model.can_create("Sales Invoice")) {
			frm.add_custom_button(__("Create Sales Invoice"), () => {
				frappe.route_options = {
					customer: frm.doc.customer,
					company: frm.doc.company,
					st_service_period: get_service_period(frm.doc.dispatch_date),
					st_seed_trip: frm.doc.name,
				};
				frappe.new_doc("Sales Invoice");
			}, __("Create"));
		}
	},
	});

function get_service_period(dispatchDate) {
	const date = dispatchDate
		? frappe.datetime.str_to_obj(dispatchDate)
		: frappe.datetime.str_to_obj(frappe.datetime.get_today());
	return date.toLocaleString("en-IN", { month: "short", year: "numeric" });
}
