frappe.ui.form.on("Driver Assignment", {
	setup(frm) {
		frm.set_query("driver", () => ({
			query: "simple_transport.simple_transport.doctype.driver_assignment.driver_assignment.get_available_driver_query",
			filters: {
				current_assignment: frm.doc.name || "",
			},
		}));
	},
});
