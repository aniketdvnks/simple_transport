frappe.ui.form.on("Sales Invoice", {
	setup(frm) {
		frm.set_query("trip", "st_trip_details", () => {
			const filters = {
				status: "Completed",
			};

			if (frm.doc.customer) {
				filters.customer = frm.doc.customer;
			}

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			if (frm.doc.name) {
				filters.sales_invoice = ["in", ["", frm.doc.name]];
			}

			return { filters };
		});
	},

	onload(frm) {
		apply_seed_trip(frm);
	},

	refresh(frm) {
		apply_seed_trip(frm);

		if (frm.doc.docstatus === 0 && frm.doc.customer) {
			frm.add_custom_button(__("Add Unbilled Trips"), () => add_unbilled_trips(frm), __("Get Items From"));
		}

		if (frm.doc.docstatus === 0 && (frm.doc.st_trip_details || []).length) {
			frm.set_intro(
				"Trip rows drive the invoice breakup, and the freight service item is synced automatically on save.",
				"blue"
			);
		}
	},

	st_reverse_charge_applicable(frm) {
		if (!frm.doc.st_invoice_type) {
			frm.set_value("st_invoice_type", frm.doc.st_reverse_charge_applicable ? "Bill of Supply" : "Tax Invoice");
		}

		if (!frm.doc.st_sac_code) {
			frm.set_value("st_sac_code", frm.doc.st_reverse_charge_applicable ? "996511" : "996791");
		}
	},
});

function apply_seed_trip(frm) {
	if (frm.__st_seed_trip_applied) {
		return;
	}

	const routeOptions = frappe.route_options || {};
	const seedTrip = routeOptions.st_seed_trip;
	if (!seedTrip) {
		return;
	}

	if (!(frm.doc.st_trip_details || []).some((row) => row.trip === seedTrip)) {
		frm.add_child("st_trip_details", { trip: seedTrip });
		frm.refresh_field("st_trip_details");
	}

	delete routeOptions.st_seed_trip;
	frm.__st_seed_trip_applied = true;
}

function add_unbilled_trips(frm) {
	const [fromDate, toDate] = get_default_date_range(frm.doc.posting_date);
	const existingTrips = (frm.doc.st_trip_details || []).map((row) => row.trip).filter(Boolean);

	frappe.prompt(
		[
			{
				fieldname: "from_date",
				fieldtype: "Date",
				label: "From Date",
				default: fromDate,
			},
			{
				fieldname: "to_date",
				fieldtype: "Date",
				label: "To Date",
				default: toDate,
			},
		],
		(values) => {
			frappe.call({
				method: "simple_transport.sales_invoice.get_unbilled_trips",
				args: {
					customer: frm.doc.customer,
					company: frm.doc.company,
					from_date: values.from_date,
					to_date: values.to_date,
					excluded_trips: JSON.stringify(existingTrips),
				},
				callback: (r) => {
					const trips = r.message || [];
					if (!trips.length) {
						frappe.msgprint(__("No completed unbilled trips were found for this customer in the selected period."));
						return;
					}

					trips.forEach((trip) => {
						frm.add_child("st_trip_details", { trip: trip.name });
					});
					frm.refresh_field("st_trip_details");
					frm.dirty();

					frappe.show_alert({
						message: __("{0} trip(s) added to the invoice.", [trips.length]),
						indicator: "green",
					});
				},
			});
		},
		__("Add Unbilled Trips"),
		__("Add")
	);
}

function get_default_date_range(postingDate) {
	const date = postingDate ? frappe.datetime.str_to_obj(postingDate) : frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const fromDate = new Date(date.getFullYear(), date.getMonth(), 1);
	const toDate = new Date(date.getFullYear(), date.getMonth() + 1, 0);

	return [
		frappe.datetime.obj_to_str(fromDate),
		frappe.datetime.obj_to_str(toDate),
	];
}
