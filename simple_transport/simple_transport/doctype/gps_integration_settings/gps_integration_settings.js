frappe.ui.form.on("GPS Integration Settings", {
	refresh(frm) {
		const baseUrl = window.location.origin;
		const lines = [
			"Provide the following separate webhook URLs to the GPS provider:",
			`Geo Data: ${baseUrl}${frm.doc.geo_endpoint_path || ""}`,
			`Trip Data: ${baseUrl}${frm.doc.trip_endpoint_path || ""}`,
			`Vehicle Data: ${baseUrl}${frm.doc.vehicle_endpoint_path || ""}`,
			`DTC Data: ${baseUrl}${frm.doc.dtc_endpoint_path || ""}`,
			`Alert Log: ${baseUrl}${frm.doc.alert_endpoint_path || ""}`,
		];

		frm.set_intro(lines.join("<br>"), "blue");
		frm.add_custom_button(__("Webhook Logs"), () => {
			frappe.set_route("List", "GPS Webhook Log");
		});
	},
});
