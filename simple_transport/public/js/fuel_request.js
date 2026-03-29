frappe.ui.form.on("Fuel Request", {
	setup(frm) {
		frm.set_query("trip", () => ({
			filters: {
				status: ["not in", ["Completed", "Cancelled"]],
			},
		}));
	},
});
