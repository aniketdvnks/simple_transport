frappe.ui.form.on("Driver Assignment", {
	setup(frm) {
		frm.set_query("driver", () => ({
			filters: {
				status: "Active",
				st_is_driver: 1,
				designation: "Driver",
			},
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.vehicle) {
			refresh_previous_assignment(frm);
		}
	},

	vehicle(frm) {
		refresh_previous_assignment(frm);
	},

	assignment_date(frm) {
		refresh_previous_assignment(frm);
	},
});

function refresh_previous_assignment(frm) {
	if (!frm.doc.vehicle) {
		clear_previous_assignment(frm);
		return;
	}

	frappe.call({
		method: "simple_transport.simple_transport.doctype.driver_assignment.driver_assignment.get_previous_assignment_summary",
		args: {
			vehicle: frm.doc.vehicle,
			assignment_date: frm.doc.assignment_date,
			current_assignment: frm.doc.name || "",
		},
		callback: ({ message }) => {
			const summary = message || {};
			frm.set_value("previous_assignment", summary.name || "");
			frm.set_value("previous_driver", summary.driver || "");
			frm.set_value("previous_assigned_from", summary.assignment_date || "");
			frm.set_value("previous_assigned_till", summary.assigned_till || "");
			frm.set_value("previous_assignment_days", summary.assignment_days || 0);
		},
	});
}

function clear_previous_assignment(frm) {
	frm.set_value("previous_assignment", "");
	frm.set_value("previous_driver", "");
	frm.set_value("previous_assigned_from", "");
	frm.set_value("previous_assigned_till", "");
	frm.set_value("previous_assignment_days", 0);
}
