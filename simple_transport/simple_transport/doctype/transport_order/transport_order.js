// Copyright (c) 2026, DVNKS Systems Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Order", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Daily Planning"), () => {
			frappe.route_options = {
				transport_order: frm.doc.name,
			};
			frappe.set_route("daily-planning-1");
		});
	},
});
