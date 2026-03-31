frappe.ui.form.on("Fuel Request", {
	setup(frm) {
		frm.set_query("trip", () => ({
			filters: {
				status: ["not in", ["Completed", "Cancelled"]],
			},
		}));

		frm.set_query("vehicle", () => ({
			filters: {
				st_operational_status: ["!=", "Under Maintenance"],
			},
		}));
	},

	vehicle(frm) {
		if (frm.doc.trip || !frm.doc.vehicle) {
			return;
		}

		frappe.db.get_value("Vehicle", frm.doc.vehicle, ["employee"], (value) => {
			if (value?.employee) {
				frm.set_value("driver", value.employee);
			}
		});
	},

	route_master(frm) {
		if (!frm.doc.route_master) {
			return;
		}

		frappe.db.get_value(
			"Route Master",
			frm.doc.route_master,
			["source_location", "destination_location", "distance_km"],
			(value) => {
				if (value?.distance_km && !frm.doc.distance_km) {
					frm.set_value("distance_km", value.distance_km);
				}

				if (!frm.doc.programme) {
					const programme = [value?.source_location, value?.destination_location]
						.filter(Boolean)
						.join(" / ");
					if (programme) {
						frm.set_value("programme", programme);
					}
				}
				refresh_fuel_math(frm);
			}
		);
	},

	average_kmpl(frm) {
		refresh_fuel_math(frm);
	},

	distance_km(frm) {
		refresh_fuel_math(frm);
	},

	diesel_given_liters(frm) {
		refresh_fuel_math(frm);
	},

	diesel_carry_forward_liters(frm) {
		refresh_fuel_math(frm);
	},
});

function refresh_fuel_math(frm) {
	const distance = flt(frm.doc.distance_km);
	const average = flt(frm.doc.average_kmpl);
	const dieselGiven = flt(frm.doc.diesel_given_liters);
	const carryForward = flt(frm.doc.diesel_carry_forward_liters);

	let dieselToBeGiven = flt(frm.doc.diesel_to_be_given_liters);
	if (distance > 0 && average > 0) {
		dieselToBeGiven = distance / average;
		frm.set_value("diesel_to_be_given_liters", dieselToBeGiven);
	}

	frm.set_value(
		"diesel_balance_liters",
		carryForward - dieselGiven + flt(dieselToBeGiven)
	);

	if (!flt(frm.doc.requested_qty_liters) && flt(dieselToBeGiven)) {
		frm.set_value("requested_qty_liters", dieselToBeGiven);
	}
}
