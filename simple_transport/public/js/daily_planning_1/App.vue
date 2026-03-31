<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const loading = ref(false);
const busyRoute = ref("");
const removingAssignment = ref("");
const planningDate = ref(frappe.datetime.get_today());
const selectedTransportOrder = ref("");
const transportOrders = ref([]);
const routeRows = ref([]);
const assignableIdleVehicles = ref([]);
const idleVehicles = ref([]);
const unloadingVehicles = ref([]);
const scopeNote = ref("");
const errorMessage = ref("");
const assignmentSelections = ref({});
const clockNow = ref(new Date());

let clockTimer = null;

const totalRequiredVehicles = computed(() =>
	routeRows.value.reduce((sum, row) => sum + (row.required_vehicles || 0), 0)
);
const totalAssignedVehicles = computed(() =>
	routeRows.value.reduce((sum, row) => sum + (row.assigned_count || 0), 0)
);
const totalPendingVehicles = computed(() =>
	routeRows.value.reduce((sum, row) => sum + (row.pending_count || 0), 0)
);
const totalPendingWeight = computed(() =>
	routeRows.value.reduce((sum, row) => sum + (row.pending_weight_mt || 0), 0)
);
const transportOrderLink = computed(() =>
	selectedTransportOrder.value ? `/app/transport-order/${selectedTransportOrder.value}` : "#"
);
const formattedPlanningDate = computed(() => formatDate(planningDate.value));
const formattedClock = computed(() =>
	new Intl.DateTimeFormat("en-IN", {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hour12: true,
	}).format(clockNow.value)
);
const routeGridStyle = computed(() => ({
	gridTemplateColumns: `repeat(${Math.max(routeRows.value.length, 1)}, minmax(165px, 190px))`,
}));

onMounted(() => {
	loadPlanning({ transportOrder: consumeRouteTransportOrder() });
	clockTimer = window.setInterval(() => {
		clockNow.value = new Date();
	}, 1000);
	window.addEventListener("simple-transport:refresh-daily-planning", handleRefreshEvent);
});

onBeforeUnmount(() => {
	if (clockTimer) {
		window.clearInterval(clockTimer);
	}
	window.removeEventListener("simple-transport:refresh-daily-planning", handleRefreshEvent);
});

function consumeRouteTransportOrder() {
	const routeTransportOrder = frappe.route_options?.transport_order || "";
	frappe.route_options = null;
	return routeTransportOrder;
}

function handleRefreshEvent() {
	loadPlanning();
}

function setPlanningState(message = {}) {
	planningDate.value = message.planning_date || planningDate.value;
	transportOrders.value = message.transport_orders || [];
	selectedTransportOrder.value = message.selected_transport_order || "";
	routeRows.value = message.route_rows || [];
	assignableIdleVehicles.value = message.assignable_idle_vehicles || [];
	idleVehicles.value = message.idle_vehicles || [];
	unloadingVehicles.value = message.unloading_vehicles || [];
	scopeNote.value = message.scope_note || "";

	const nextSelections = {};
	for (const route of routeRows.value) {
		nextSelections[route.name] = "";
	}
	assignmentSelections.value = nextSelections;
	dispatchSidebarUpdate();
}

function dispatchSidebarUpdate() {
	window.dispatchEvent(
		new CustomEvent("simple-transport:update-daily-planning-sidebar", {
			detail: {
				idle_vehicles: assignableIdleVehicles.value,
				unloading_vehicles: unloadingVehicles.value,
			},
		})
	);
}

async function loadPlanning({ transportOrder = null, planningDateValue = null } = {}) {
	loading.value = true;
	errorMessage.value = "";

	try {
		const { message } = await frappe.call({
			method:
				"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.get_daily_planning_data",
			args: {
				planning_date: planningDateValue || planningDate.value,
				transport_order: transportOrder ?? selectedTransportOrder.value,
			},
		});
		setPlanningState(message || {});
	} catch (error) {
		errorMessage.value = extractErrorMessage(error);
	} finally {
		loading.value = false;
	}
}

async function addRoute() {
	if (!selectedTransportOrder.value) {
		frappe.show_alert({
			message: __("Select a transport order first."),
			indicator: "orange",
		});
		return;
	}

	frappe.prompt(
		[
			{
				fieldname: "route_master",
				label: __("Route"),
				fieldtype: "Link",
				options: "Route Master",
				reqd: 1,
				get_query: () => ({ filters: { is_active: 1 } }),
			},
			{
				fieldname: "qty_in_mt",
				label: __("Weight (MT)"),
				fieldtype: "Float",
			},
			{
				fieldname: "no_of_vehicles",
				label: __("Vehicles Needed"),
				fieldtype: "Int",
			},
		],
		async (values) => {
			try {
				await frappe.call({
					method:
						"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.add_route_to_transport_order",
					args: {
						transport_order: selectedTransportOrder.value,
						route_master: values.route_master,
						qty_in_mt: values.qty_in_mt,
						no_of_vehicles: values.no_of_vehicles,
					},
				});
				frappe.show_alert({
					message: __("Route added to transport order"),
					indicator: "green",
				});
				await loadPlanning({ transportOrder: selectedTransportOrder.value });
			} catch (error) {
				errorMessage.value = extractErrorMessage(error);
			}
		},
		__("Add Route"),
		__("Add")
	);
}

async function assignVehicle(route) {
	const vehicle = assignmentSelections.value[route.name];
	if (!vehicle || !selectedTransportOrder.value) {
		frappe.show_alert({
			message: __("Select an idle vehicle before assigning."),
			indicator: "orange",
		});
		return;
	}

	busyRoute.value = route.name;
	errorMessage.value = "";
	try {
		await frappe.call({
			method:
				"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.assign_vehicle_to_transport_order",
			args: {
				transport_order: selectedTransportOrder.value,
				route_detail: route.name,
				vehicle,
			},
		});
		frappe.show_alert({
			message: __("Vehicle assigned to route"),
			indicator: "green",
		});
		await loadPlanning({ transportOrder: selectedTransportOrder.value });
	} catch (error) {
		errorMessage.value = extractErrorMessage(error);
	} finally {
		busyRoute.value = "";
	}
}

function openEditRouteDialog(route) {
	if (!selectedTransportOrder.value || !route?.name) {
		return;
	}

	frappe.prompt(
		[
			{
				fieldname: "qty_in_mt",
				label: __("Weight (MT)"),
				fieldtype: "Float",
				default: route.qty_in_mt || "",
			},
			{
				fieldname: "no_of_vehicles",
				label: __("Vehicles Needed"),
				fieldtype: "Int",
				default: route.no_of_vehicles || "",
			},
		],
		async (values) => {
			try {
				await frappe.call({
					method:
						"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.update_route_on_transport_order",
					args: {
						transport_order: selectedTransportOrder.value,
						route_detail: route.name,
						qty_in_mt: values.qty_in_mt,
						no_of_vehicles: values.no_of_vehicles,
					},
				});
				frappe.show_alert({
					message: __("Route updated"),
					indicator: "green",
				});
				await loadPlanning({ transportOrder: selectedTransportOrder.value });
			} catch (error) {
				errorMessage.value = extractErrorMessage(error);
			}
		},
		__("Update Route"),
		__("Update")
	);
}

async function unassignVehicle(assignmentRow) {
	if (!selectedTransportOrder.value || !assignmentRow) {
		return;
	}

	removingAssignment.value = assignmentRow;
	errorMessage.value = "";
	try {
		await frappe.call({
			method:
				"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.unassign_vehicle_from_transport_order",
			args: {
				transport_order: selectedTransportOrder.value,
				assignment_row: assignmentRow,
			},
		});
		frappe.show_alert({
			message: __("Vehicle unassigned"),
			indicator: "blue",
		});
		await loadPlanning({ transportOrder: selectedTransportOrder.value });
	} catch (error) {
		errorMessage.value = extractErrorMessage(error);
	} finally {
		removingAssignment.value = "";
	}
}

async function openCreateLorryReceiptDialog(route, assignment) {
	if (!selectedTransportOrder.value || !assignment?.name) {
		return;
	}

	try {
		const { message: defaults } = await frappe.call({
			method:
				"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.get_lorry_receipt_defaults",
			args: {
				transport_order: selectedTransportOrder.value,
				assignment_row: assignment.name,
			},
		});

		frappe.prompt(
			[
				{
					fieldname: "lr_date",
					label: __("LR Date"),
					fieldtype: "Date",
					reqd: 1,
					default: planningDate.value,
				},
				{
					fieldname: "gate_pass_no",
					label: __("Gate Pass No"),
					fieldtype: "Data",
				},
				{
					fieldname: "goods_description",
					label: __("Material"),
					fieldtype: "Link",
					options: "Material",
					reqd: 1,
				},
				{
					fieldname: "quantity_mt",
					label: __("Net Weight (MT)"),
					fieldtype: "Float",
					reqd: 1,
					default:
						defaults?.default_quantity_mt ||
						getDefaultRouteQuantity(route, assignment),
				},
				{
					fieldname: "gross_weight_mt",
					label: __("Gross Weight (MT)"),
					fieldtype: "Float",
					default:
						defaults?.default_quantity_mt ||
						getDefaultRouteQuantity(route, assignment),
				},
				{
					fieldname: "freight_rate_per_mt",
					label: __("Freight Rate / MT"),
					fieldtype: "Currency",
					default: defaults?.freight_rate_per_mt || 0,
				},
				{
					fieldname: "loading_supervisor_name",
					label: __("Loading Supervisor"),
					fieldtype: "Data",
				},
				{
					fieldname: "remarks",
					label: __("Remarks"),
					fieldtype: "Small Text",
				},
			],
			async (values) => {
				try {
					await frappe.call({
						method:
							"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.create_lorry_receipt_from_assignment",
						args: {
							transport_order: selectedTransportOrder.value,
							assignment_row: assignment.name,
							...values,
						},
					});
					frappe.show_alert({
						message: __("Lorry Receipt created"),
						indicator: "green",
					});
					await loadPlanning({ transportOrder: selectedTransportOrder.value });
				} catch (error) {
					errorMessage.value = extractErrorMessage(error);
				}
			},
			__("Create Lorry Receipt"),
			__("Create")
		);
	} catch (error) {
		errorMessage.value = extractErrorMessage(error);
	}
}

function printLorryReceipt(assignment) {
	if (!assignment?.lorry_receipt) {
		return;
	}

	const doctype = encodeURIComponent("Lorry Receipt");
	const name = encodeURIComponent(assignment.lorry_receipt);
	const format = encodeURIComponent("Lorry Receipt");
	window.open(
		`/printview?doctype=${doctype}&name=${name}&format=${format}&trigger_print=1&no_letterhead=0`,
		"_blank",
		"noopener"
	);
}

function openDocument(doctype, name) {
	if (!doctype || !name) {
		return;
	}
	frappe.set_route("Form", doctype, name);
}

async function openStartTripDialog(assignment) {
	if (!selectedTransportOrder.value || !assignment?.name || !assignment.lorry_receipt) {
		return;
	}

	frappe.prompt(
		[
			{
				fieldname: "dispatch_date",
				label: __("Dispatch Date"),
				fieldtype: "Date",
				reqd: 1,
				default: planningDate.value,
			},
			{
				fieldname: "status",
				label: __("Trip Status"),
				fieldtype: "Select",
				reqd: 1,
				options: "Ready for Dispatch\nAt Loading Point\nIn Transit",
				default: "At Loading Point",
			},
			{
				fieldname: "actual_start_datetime",
				label: __("Actual Start"),
				fieldtype: "Datetime",
				reqd: 1,
				default: frappe.datetime.now_datetime(),
			},
			{
				fieldname: "expected_arrival_date",
				label: __("Expected Arrival"),
				fieldtype: "Date",
			},
			{
				fieldname: "current_location",
				label: __("Current Location"),
				fieldtype: "Data",
			},
		],
		async (values) => {
			try {
				await frappe.call({
					method:
						"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.start_trip_from_assignment",
					args: {
						transport_order: selectedTransportOrder.value,
						assignment_row: assignment.name,
						...values,
					},
				});
				frappe.show_alert({
					message: __("Trip started"),
					indicator: "green",
				});
				await loadPlanning({ transportOrder: selectedTransportOrder.value });
			} catch (error) {
				errorMessage.value = extractErrorMessage(error);
			}
		},
		__("Start Trip"),
		__("Start")
	);
}

function openRouteFuelRequestDialog(route) {
	const assignments = (route?.assignments || []).filter((row) => row?.vehicle);
	if (!assignments.length) {
		frappe.show_alert({
			message: __("Assign at least one vehicle on this route before creating a Fuel Request."),
			indicator: "orange",
		});
		return;
	}

	showFuelRequestDialog(route);
}

function openVehicleFuelRequestDialog(route, assignment) {
	if (!assignment?.vehicle) {
		return;
	}

	showFuelRequestDialog(route, assignment);
}

function showFuelRequestDialog(route, preselectedAssignment = null) {
	if (!selectedTransportOrder.value || !route?.name) {
		return;
	}

	const routeAssignments = (route.assignments || []).filter((row) => row?.vehicle);
	const allowedVehicles = routeAssignments.map((row) => row.vehicle);
	if (!allowedVehicles.length) {
		frappe.show_alert({
			message: __("No assigned vehicles are available for fuel planning on this route."),
			indicator: "orange",
		});
		return;
	}

	const getAssignment = (vehicleName) =>
		preselectedAssignment ||
		routeAssignments.find((row) => row.vehicle === vehicleName) ||
		null;

	const dialog = new frappe.ui.Dialog({
		title: __("Create Fuel Request"),
		fields: [
			{
				fieldname: "vehicle",
				label: __("Vehicle"),
				fieldtype: "Link",
				options: "Vehicle",
				reqd: 1,
				default: preselectedAssignment?.vehicle || "",
				read_only: !!preselectedAssignment,
				get_query: () => ({
					filters: [["Vehicle", "name", "in", allowedVehicles]],
				}),
				onchange: () => loadVehicleDefaults(dialog.get_value("vehicle")),
			},
			{
				fieldname: "request_date",
				label: __("Request Date"),
				fieldtype: "Date",
				reqd: 1,
				default: planningDate.value,
			},
			{
				fieldname: "programme",
				label: __("Programme"),
				fieldtype: "Data",
				read_only: 1,
			},
			{
				fieldname: "distance_km",
				label: __("KM"),
				fieldtype: "Float",
				read_only: 1,
			},
			{
				fieldname: "load_status",
				label: __("Filled / Not Filled"),
				fieldtype: "Select",
				options: "EM\nLO",
			},
			{
				fieldname: "average_kmpl",
				label: __("AVG (KM/L)"),
				fieldtype: "Float",
				onchange: () => refreshFuelPreview(),
			},
			{
				fieldname: "diesel_given_liters",
				label: __("Diesel Given"),
				fieldtype: "Float",
				default: 0,
				onchange: () => refreshFuelPreview(),
			},
			{
				fieldname: "diesel_carry_forward_liters",
				label: __("Diesel Carry Fwd"),
				fieldtype: "Float",
				default: 0,
				onchange: () => refreshFuelPreview(),
			},
			{
				fieldname: "fuel_rate_per_liter",
				label: __("Fuel Rate / Liter"),
				fieldtype: "Currency",
			},
			{
				fieldname: "fuel_math_preview",
				fieldtype: "HTML",
			},
			{
				fieldname: "reason",
				label: __("Reason"),
				fieldtype: "Small Text",
			},
			{
				fieldname: "remarks",
				label: __("Remarks"),
				fieldtype: "Small Text",
			},
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			try {
				const matchedAssignment = getAssignment(values.vehicle);
				const { message } = await frappe.call({
					method:
						"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.create_fuel_request_from_planning",
					args: {
						transport_order: selectedTransportOrder.value,
						route_detail: route.name,
						vehicle: values.vehicle,
						assignment_row: matchedAssignment?.name || "",
						request_date: values.request_date,
						load_status: values.load_status,
						average_kmpl: values.average_kmpl,
						diesel_given_liters: values.diesel_given_liters,
						diesel_carry_forward_liters: values.diesel_carry_forward_liters,
						fuel_rate_per_liter: values.fuel_rate_per_liter,
						reason: values.reason,
						remarks: values.remarks,
					},
				});
				dialog.hide();
				frappe.show_alert({
					message: __(
						"Fuel Request {0} created • Diesel To Be Given {1} L • Balance {2} L",
						[
							message.fuel_request,
							formatFuelNumber(message.diesel_to_be_given_liters),
							formatFuelNumber(message.diesel_balance_liters),
						]
					),
					indicator: "green",
				});
				await loadPlanning({ transportOrder: selectedTransportOrder.value });
			} catch (error) {
				errorMessage.value = extractErrorMessage(error);
			}
		},
	});

	function refreshFuelPreview() {
		const distance = flt(dialog.get_value("distance_km"));
		const average = flt(dialog.get_value("average_kmpl"));
		const dieselGiven = flt(dialog.get_value("diesel_given_liters"));
		const carryForward = flt(dialog.get_value("diesel_carry_forward_liters"));
		const dieselToBeGiven = average > 0 && distance > 0 ? distance / average : 0;
		const balance = carryForward - dieselGiven + dieselToBeGiven;
		const wrapper = dialog.get_field("fuel_math_preview")?.$wrapper;
		if (!wrapper) {
			return;
		}

		wrapper.html(`
			<div class="fuel-preview-grid">
				<div class="fuel-preview-item">
					<span>Diesel To Be Given</span>
					<strong>${formatFuelNumber(dieselToBeGiven)} L</strong>
				</div>
				<div class="fuel-preview-item">
					<span>Balance</span>
					<strong>${formatFuelNumber(balance)} L</strong>
				</div>
			</div>
		`);
	}

	async function loadVehicleDefaults(vehicleName) {
		if (!vehicleName) {
			return;
		}

		try {
			const matchedAssignment = getAssignment(vehicleName);
			const { message: defaults } = await frappe.call({
				method:
					"simple_transport.simple_transport.page.daily_planning_1.daily_planning_1.get_fuel_request_defaults",
				args: {
					transport_order: selectedTransportOrder.value,
					route_detail: route.name,
					vehicle: vehicleName,
					assignment_row: matchedAssignment?.name || "",
				},
			});
			dialog.set_value("programme", defaults?.programme || routeHeading(route));
			dialog.set_value("distance_km", defaults?.distance_km || route.distance_km || 0);
			dialog.set_value("load_status", defaults?.load_status || "");
			dialog.set_value("average_kmpl", defaults?.average_kmpl || 0);
			dialog.set_value("diesel_given_liters", defaults?.diesel_given_liters || 0);
			dialog.set_value(
				"diesel_carry_forward_liters",
				defaults?.diesel_carry_forward_liters || 0
			);
			dialog.set_value("fuel_rate_per_liter", defaults?.fuel_rate_per_liter || 0);
			dialog.set_value("reason", defaults?.reason || "");
			refreshFuelPreview();
		} catch (error) {
			errorMessage.value = extractErrorMessage(error);
		}
	}

	dialog.show();
	if (preselectedAssignment?.vehicle) {
		loadVehicleDefaults(preselectedAssignment.vehicle);
	} else {
		dialog.set_value("programme", routeHeading(route));
		dialog.set_value("distance_km", route.distance_km || 0);
		refreshFuelPreview();
	}
}

function routeHeading(route) {
	const loadingPoint = route.loading_point || "Loading Point";
	const unloadingPoint = route.unloading_point || "Unloading Point";
	return `${loadingPoint} TO ${unloadingPoint}`.toUpperCase();
}

function routeProgressClass(route) {
	const hasTrip = (route.assignments || []).some((assignment) => assignment.trip);
	const hasLorryReceipt = (route.assignments || []).some((assignment) => assignment.lorry_receipt);

	if (hasTrip) {
		return "progress-trip";
	}
	if (hasLorryReceipt) {
		return "progress-lr";
	}
	if (route.assigned_count > 0) {
		return "progress-assigned";
	}
	return "progress-idle";
}

function routeProgressPercent(route) {
	const plannedWeight = flt(route.qty_in_mt);
	const assignedWeight = flt(route.assigned_capacity_mt);
	if (plannedWeight > 0) {
		return Math.min(100, Math.round((assignedWeight / plannedWeight) * 100));
	}

	const plannedVehicles = flt(route.required_vehicles || route.no_of_vehicles);
	const assignedVehicles = flt(route.assigned_count);
	if (plannedVehicles > 0) {
		return Math.min(100, Math.round((assignedVehicles / plannedVehicles) * 100));
	}

	return assignedVehicles > 0 ? 100 : 0;
}

function assignmentProgressClass(assignment) {
	if (!assignment) {
		return "";
	}
	if (assignment.trip) {
		return "trip-started";
	}
	if (assignment.lorry_receipt) {
		return "lr-created";
	}
	return "assigned";
}

function routeDisplayRows(route) {
	const rows = [...(route.assignments || [])];
	const minimumRows = Math.max(route.display_rows || 0, 7);
	while (rows.length < minimumRows) {
		rows.push(null);
	}
	return rows;
}

function getDefaultRouteQuantity(route, assignment) {
	const pendingWeight = flt(route.pending_weight_mt);
	const vehicleCapacity = flt(assignment?.vehicle_capacity_mt);
	if (pendingWeight && vehicleCapacity) {
		return Math.min(pendingWeight, vehicleCapacity);
	}
	return pendingWeight || vehicleCapacity || 0;
}

function transportOrderLabel(order) {
	return `${order.name}`;
}

function formatFuelNumber(value) {
	return flt(value).toFixed(2);
}

function formatDate(value) {
	if (!value) {
		return "";
	}

	try {
		return frappe.datetime.str_to_user(value);
	} catch (error) {
		return value;
	}
}

function extractErrorMessage(error) {
	return (
		error?.messages?.[0] ||
		error?.message ||
		error?.exc_type ||
		__("Something went wrong while updating daily planning.")
	);
}
</script>

<template>
	<div class="planning-board">
		<header class="board-header">
			<div class="board-title-row">
				<h1>DAILY SCHEDULE :: DATE : {{ formattedPlanningDate }}</h1>
				<div class="board-time">{{ formattedClock }}</div>
			</div>
			<div class="board-summary-row">
				<div>Transport Order : <strong>{{ selectedTransportOrder || "Not selected" }}</strong></div>
				<div>Routes : <strong>{{ routeRows.length }}</strong></div>
				<div>Required : <strong>{{ totalRequiredVehicles }}</strong></div>
				<div>Assigned : <strong>{{ totalAssignedVehicles }}</strong></div>
				<div>Pending Vehicles : <strong>{{ totalPendingVehicles }}</strong></div>
				<div>Pending Weight : <strong>{{ totalPendingWeight }} MT</strong></div>
			</div>
		</header>

		<section class="toolbar-strip">
			<label class="toolbar-field">
				<span>Date</span>
				<input
					v-model="planningDate"
					type="date"
					@change="loadPlanning({ planningDateValue: planningDate, transportOrder: '' })"
				/>
			</label>

			<label class="toolbar-field toolbar-order">
				<span>Transport Order</span>
				<select
					v-model="selectedTransportOrder"
					:disabled="loading || !transportOrders.length"
					@change="loadPlanning({ transportOrder: selectedTransportOrder })"
				>
					<option value="" disabled>Select transport order</option>
					<option v-for="order in transportOrders" :key="order.name" :value="order.name">
						{{ transportOrderLabel(order) }}
					</option>
				</select>
			</label>

			<button class="toolbar-button" :disabled="loading" type="button" @click="loadPlanning()">
				{{ loading ? "Refreshing..." : "Refresh" }}
			</button>

			<button
				class="toolbar-button secondary"
				:disabled="!selectedTransportOrder"
				type="button"
				@click="addRoute"
			>
				Add Route
			</button>

			<a
				v-if="selectedTransportOrder"
				class="toolbar-link"
				:href="transportOrderLink"
				target="_blank"
				rel="noopener noreferrer"
			>
				Open Transport Order
			</a>
		</section>

		<div v-if="scopeNote" class="info-strip">{{ scopeNote }}</div>
		<div v-if="errorMessage" class="error-strip">{{ errorMessage }}</div>

		<section class="route-sheet">
			<div class="section-caption">ROUTES</div>

			<div v-if="!routeRows.length && !loading" class="empty-strip">
				No transport order routes found for the selected planning date.
			</div>

			<div v-else class="route-scroll">
				<div class="route-grid" :style="routeGridStyle">
					<section
						v-for="route in routeRows"
						:key="route.name"
						class="route-column"
						:class="routeProgressClass(route)"
					>
						<div class="route-head">
							<div class="route-heading-row">
								<div class="route-heading">{{ routeHeading(route) }}</div>
								<div class="route-head-actions">
									<button class="route-edit-button" type="button" @click="openEditRouteDialog(route)">
										Edit
									</button>
									<button
										class="icon-button route-fuel-button"
										type="button"
										:title="`Create Fuel Request for ${routeHeading(route)}`"
										:disabled="!(route.assignments || []).length"
										@click="openRouteFuelRequestDialog(route)"
									>
										<svg class="fuel-icon" viewBox="0 0 24 24" aria-hidden="true">
											<path
												d="M6 4h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6zM8 7h6M8 11h6M16 9h2l2 2v7a2 2 0 0 1-2 2"
												fill="none"
												stroke="currentColor"
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="1.8"
											/>
										</svg>
									</button>
								</div>
							</div>
							<div class="route-metrics">
								<div>{{ route.qty_in_mt || 0 }} MT</div>
								<div>Assigned {{ route.assigned_capacity_mt || 0 }} MT</div>
								<div>Pending {{ route.pending_weight_mt || 0 }} MT</div>
								<div>Need {{ route.pending_count || 0 }} Vehicles</div>
							</div>
							<div class="route-progress-row">
								<div class="route-progress-track">
									<div
										class="route-progress-bar"
										:class="routeProgressClass(route)"
										:style="{ width: `${routeProgressPercent(route)}%` }"
									></div>
								</div>
								<div class="route-progress-value">{{ routeProgressPercent(route) }}%</div>
							</div>
							<div class="assign-row">
								<select
									v-model="assignmentSelections[route.name]"
									:disabled="!assignableIdleVehicles.length || route.pending_count <= 0"
								>
									<option value="" disabled>Select idle vehicle</option>
									<option
										v-for="vehicle in assignableIdleVehicles"
										:key="vehicle.name"
										:value="vehicle.name"
									>
										{{ vehicle.label || vehicle.name }} • {{ vehicle.capacity_mt || 0 }} MT
									</option>
								</select>
								<button
									class="assign-button"
									type="button"
									:disabled="
										busyRoute === route.name ||
										!assignableIdleVehicles.length ||
										!assignmentSelections[route.name] ||
										route.pending_count <= 0
									"
									@click="assignVehicle(route)"
								>
									{{ busyRoute === route.name ? "Adding..." : "Add" }}
								</button>
							</div>
						</div>

						<div class="route-body">
							<div
								v-for="(assignment, index) in routeDisplayRows(route)"
								:key="assignment ? assignment.name : `${route.name}-${index}`"
								class="route-cell"
								:class="[
									assignment ? assignmentProgressClass(assignment) : '',
									{
										open: !assignment && index < (route.pending_count || 0),
									},
								]"
							>
								<template v-if="assignment">
									<div class="cell-top" :class="assignmentProgressClass(assignment)">
										<strong>{{ assignment.vehicle }}</strong>
										<div class="cell-top-actions">
											<button
												class="icon-button fuel-icon-button"
												type="button"
												:title="`Create Fuel Request for ${assignment.vehicle}`"
												@click="openVehicleFuelRequestDialog(route, assignment)"
											>
												<svg class="fuel-icon" viewBox="0 0 24 24" aria-hidden="true">
													<path
														d="M6 4h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6zM8 7h6M8 11h6M16 9h2l2 2v7a2 2 0 0 1-2 2"
														fill="none"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="1.8"
													/>
												</svg>
											</button>
											<button
												v-if="!assignment.lorry_receipt && !assignment.trip"
												class="remove-button"
												type="button"
												:disabled="removingAssignment === assignment.name"
												@click="unassignVehicle(assignment.name)"
											>
												{{ removingAssignment === assignment.name ? "..." : "x" }}
											</button>
										</div>
									</div>
									<div class="cell-meta">
										{{ assignment.driver || "Driver not assigned" }}
										<span v-if="assignment.vehicle_capacity_mt">
											• {{ assignment.vehicle_capacity_mt }} MT
										</span>
									</div>
									<div class="cell-actions">
										<button
											v-if="!assignment.lorry_receipt"
											class="cell-button lr-button"
											type="button"
											@click="openCreateLorryReceiptDialog(route, assignment)"
										>
											Create LR
										</button>
										<template v-else>
											<button
												class="cell-button info-button"
												type="button"
												@click="openDocument('Lorry Receipt', assignment.lorry_receipt)"
											>
												Open LR
											</button>
											<button
												class="cell-button info-button"
												type="button"
												@click="printLorryReceipt(assignment)"
											>
												Print
											</button>
											<button
												v-if="!assignment.trip"
												class="cell-button trip-button"
												type="button"
												@click="openStartTripDialog(assignment)"
											>
												Start Trip
											</button>
											<button
												v-else
												class="cell-button trip-button"
												type="button"
												@click="openDocument('Trip', assignment.trip)"
											>
												Open Trip
											</button>
										</template>
									</div>
								</template>
								<template v-else>
									<div class="empty-cell-text">
										{{ index < (route.pending_count || 0) ? "Open slot" : "" }}
									</div>
								</template>
							</div>
						</div>
					</section>
				</div>
			</div>
		</section>
	</div>
</template>

<style scoped>
:global(.page-head) {
	display: none;
}

:global(.layout-main) {
	display: grid;
	gap: 0;
	grid-template-columns: 270px minmax(0, 1fr);
	margin: 0;
}

:global(.layout-side-section) {
	background: #172b4d;
	border-right: 1px solid #0f1b33;
	max-width: none;
	padding: 0;
}

:global(.layout-main-section-wrapper) {
	max-width: none;
	padding: 0;
}

:global(.layout-main-section) {
	background: #f6f9fc;
	padding: 0;
}

:global(.page-body) {
	background: linear-gradient(180deg, #eef5ff 0%, #f6f9fc 100%);
	max-width: none;
}

:global(.daily-planning-sidebar) {
	background: #172b4d;
	/* display: grid; */
	gap: 0;
	height: 100%;
}

:global(.daily-planning-sidebar .sidebar-section) {
	border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

:global(.daily-planning-sidebar .sidebar-title) {
	background: linear-gradient(135deg, #5e72e4 0%, #11cdef 100%);
	border-bottom: 1px solid rgba(255, 255, 255, 0.16);
	box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.18);
	color: #ffffff;
	cursor: pointer;
	list-style: none;
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 0.04em;
	padding: 12px 14px;
	text-transform: uppercase;
}

:global(.daily-planning-sidebar .sidebar-title::-webkit-details-marker) {
	display: none;
}

:global(.daily-planning-sidebar .sidebar-title::after) {
	color: #ffffff;
	content: "+";
	float: right;
	font-size: 14px;
	line-height: 1;
}

:global(.daily-planning-sidebar .sidebar-section[open] .sidebar-title::after) {
	content: "-";
}

:global(.daily-planning-sidebar .sidebar-list) {
	background: #f6f9fc;
	max-height: calc(100vh - 220px);
	overflow-y: auto;
	padding: 8px;
}

:global(.daily-planning-sidebar .sidebar-vehicle-row) {
	background: #ffffff;
	border-bottom: 1px solid #e3ebf6;
	border-left: 4px solid #5e72e4;
	box-shadow: 0 10px 24px rgba(23, 43, 77, 0.08);
	display: grid;
	gap: 4px;
	margin-bottom: 8px;
	padding: 10px 12px;
}

:global(.daily-planning-sidebar .sidebar-vehicle-row.status-idle) {
	border-left-color: #007bff;
}

:global(.daily-planning-sidebar .sidebar-vehicle-row.status-assigned) {
	border-left-color: #ffc107;
}

:global(.daily-planning-sidebar .sidebar-vehicle-row.status-trip) {
	border-left-color: #2dce89;
}

:global(.daily-planning-sidebar .sidebar-vehicle-row.status-maintenance) {
	border-left-color: #f5365c;
}

:global(.daily-planning-sidebar .sidebar-vehicle-head) {
	align-items: start;
	display: flex;
	gap: 8px;
	justify-content: space-between;
}

:global(.daily-planning-sidebar .sidebar-status),
:global(.daily-planning-sidebar .sidebar-vehicle-sub),
:global(.daily-planning-sidebar .sidebar-vehicle-meta),
:global(.daily-planning-sidebar .sidebar-empty) {
	color: #525f7f;
	font-size: 11px;
}

:global(.daily-planning-sidebar .sidebar-status) {
	border-radius: 4px;
	display: inline-flex;
	font-weight: 700;
	padding: 2px 8px;
}

:global(.daily-planning-sidebar .sidebar-status.status-idle) {
	background: #007bff;
	color: #ffffff;
}

:global(.daily-planning-sidebar .sidebar-status.status-assigned) {
	background: #ffc107;
	color: #172b4d;
}

:global(.daily-planning-sidebar .sidebar-status.status-trip) {
	background: #2dce89;
	color: #ffffff;
}

:global(.daily-planning-sidebar .sidebar-status.status-maintenance) {
	background: #f5365c;
	color: #ffffff;
}

:global(.daily-planning-sidebar .sidebar-empty) {
	color: #ffffff;
	padding: 12px;
}

.planning-board {
	--line: #dfe6f1;
	--line-dark: #c7d3e3;
	--muted: #525f7f;
	--ink: #172b4d;
	--header: #172b4d;
	--primary: #5e72e4;
	--primary-dark: #324cdd;
	--info: #11cdef;
	--assigned: #ffd34f;
	--assigned-strong: #ffb400;
	--lr: #ffb38a;
	--lr-strong: #fb6340;
	--trip: #7ee2b8;
	--trip-strong: #2dce89;
	--idle: #9ecbff;
	--idle-strong: #007bff;
	--danger: #f5365c;
	--cell-height: 58px;
	color: var(--ink);
	display: grid;
	gap: 8px;
	padding: 8px 8px 14px;
}

.board-header,
.toolbar-strip,
.route-sheet,
.info-strip,
.error-strip,
.empty-strip {
	background: #ffffff;
	border: 1px solid var(--line);
	box-shadow: 0 14px 30px rgba(50, 50, 93, 0.08);
}

.board-header {
	background: linear-gradient(135deg, #172b4d 0%, #1a2f5f 55%, #5e72e4 100%);
	display: grid;
	gap: 6px;
	padding: 10px 12px;
}

.board-title-row,
.board-summary-row {
	align-items: center;
	display: grid;
	gap: 10px;
}

.board-title-row {
	grid-template-columns: minmax(0, 1fr) auto;
}

.board-title-row h1,
.section-caption,
.route-heading {
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 0.02em;
	margin: 0;
	text-transform: uppercase;
}

.board-time,
.board-summary-row,
.toolbar-field span,
.cell-meta,
.empty-cell-text,
.info-strip,
.empty-strip,
.route-metrics {
	color: var(--muted);
}

.board-title-row h1,
.board-time {
	color: #ffffff;
}

.board-time {
	font-size: 13px;
	font-weight: 600;
}

.board-summary-row {
	background: rgba(255, 255, 255, 0.12);
	border-top: 1px solid rgba(255, 255, 255, 0.16);
	color: rgba(255, 255, 255, 0.92);
	font-size: 12px;
	grid-template-columns: repeat(6, minmax(0, 1fr));
	padding: 8px 10px 0;
}

.toolbar-strip {
	align-items: end;
	display: grid;
	gap: 8px;
	grid-template-columns: 170px minmax(220px, 1fr) auto auto auto;
	padding: 8px 10px;
}

.toolbar-field {
	display: grid;
	gap: 4px;
}

.toolbar-field span {
	font-size: 11px;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
}

.toolbar-field input,
.toolbar-field select,
.assign-row select {
	background: #ffffff;
	border: 1px solid var(--line-dark);
	border-radius: 6px;
	box-shadow: inset 0 1px 2px rgba(50, 50, 93, 0.04);
	color: var(--ink);
	height: 30px;
	padding: 0 8px;
}

.toolbar-button,
.toolbar-link,
.assign-button,
.cell-button,
.remove-button {
	border-radius: 6px;
	font-size: 12px;
	font-weight: 600;
	transition:
		transform 0.15s ease,
		box-shadow 0.15s ease,
		background 0.15s ease,
		border-color 0.15s ease;
}

.toolbar-button,
.assign-button {
	background: linear-gradient(135deg, var(--primary) 0%, var(--info) 100%);
	border: 1px solid transparent;
	box-shadow: 0 8px 18px rgba(17, 205, 239, 0.22);
	color: #ffffff;
}

.toolbar-button,
.toolbar-link {
	height: 30px;
	padding: 0 12px;
}

.toolbar-button.secondary {
	background: #ffffff;
	border: 1px solid var(--line-dark);
	color: var(--ink);
	box-shadow: 0 8px 18px rgba(50, 50, 93, 0.06);
}

.toolbar-link {
	align-items: center;
	background: #172b4d;
	border: 1px solid #172b4d;
	box-shadow: 0 8px 18px rgba(23, 43, 77, 0.14);
	color: #ffffff;
	display: inline-flex;
	justify-content: center;
	text-decoration: none;
}

.toolbar-button:hover,
.toolbar-link:hover,
.assign-button:hover,
.cell-button:hover,
.route-edit-button:hover {
	box-shadow: 0 12px 24px rgba(50, 50, 93, 0.16);
	transform: translateY(-1px);
}

.toolbar-button:disabled,
.assign-button:disabled,
.remove-button:disabled,
.cell-button:disabled {
	cursor: not-allowed;
	opacity: 0.6;
}

.info-strip,
.error-strip,
.empty-strip {
	font-size: 12px;
	padding: 7px 9px;
}

.info-strip {
	border-left: 4px solid var(--info);
}

.error-strip {
	border-left: 4px solid var(--danger);
	color: var(--danger);
}

.route-sheet {
	display: grid;
}

.section-caption {
	background: linear-gradient(135deg, #172b4d 0%, #324cdd 100%);
	border-bottom: 1px solid #172b4d;
	color: #ffffff;
	padding: 8px 10px;
}

.route-scroll {
	overflow-x: auto;
}

.route-grid {
	display: grid;
	min-width: max-content;
}

.route-column {
	background: #ffffff;
	border-top: 4px solid var(--line);
	border-right: 1px solid var(--line);
	box-shadow: 0 10px 24px rgba(50, 50, 93, 0.08);
	display: grid;
	grid-template-rows: auto 1fr;
}

.route-column:last-child {
	border-right: 0;
}

.route-column.progress-idle {
	border-top-color: var(--idle-strong);
}

.route-column.progress-assigned {
	border-top-color: var(--assigned-strong);
}

.route-column.progress-lr {
	border-top-color: var(--lr-strong);
}

.route-column.progress-trip {
	border-top-color: var(--trip-strong);
}

.route-head {
	background: #ffffff;
	border-bottom: 1px solid var(--line);
	display: grid;
}

.route-heading-row,
.route-heading,
.route-metrics,
.route-progress-row,
.assign-row {
	border-bottom: 1px solid var(--line);
	padding: 5px 6px;
}

.route-heading-row {
	align-items: start;
	display: grid;
	gap: 6px;
	grid-template-columns: minmax(0, 1fr) auto;
}

.route-head-actions,
.cell-top-actions {
	display: grid;
	gap: 4px;
	justify-items: end;
}

.route-heading {
	color: var(--ink);
	line-height: 1.2;
	word-break: break-word;
}

.route-edit-button {
	background: #172b4d;
	border: 1px solid #172b4d;
	box-shadow: 0 8px 18px rgba(23, 43, 77, 0.14);
	color: #ffffff;
	cursor: pointer;
	font-size: 10px;
	font-weight: 700;
	height: 22px;
	padding: 0 6px;
}

.icon-button {
	align-items: center;
	border: 1px solid transparent;
	box-shadow: 0 8px 18px rgba(50, 50, 93, 0.16);
	color: #ffffff;
	cursor: pointer;
	display: inline-flex;
	height: 24px;
	justify-content: center;
	padding: 0;
	width: 24px;
}

.route-fuel-button,
.fuel-icon-button {
	background: linear-gradient(135deg, #fb6340 0%, #fbb140 100%);
}

.fuel-icon {
	height: 13px;
	width: 13px;
}

.route-metrics {
	display: grid;
	font-size: 11px;
	gap: 2px;
}

.route-progress-row {
	align-items: center;
	display: grid;
	gap: 6px;
	grid-template-columns: minmax(0, 1fr) auto;
}

.route-progress-track {
	background: #dfe6f1;
	border-radius: 999px;
	height: 8px;
	overflow: hidden;
}

.route-progress-bar {
	border-radius: 999px;
	box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
	height: 100%;
	min-width: 0;
	transition: width 0.2s ease;
}

.route-progress-bar.progress-idle {
	background: var(--idle-strong);
}

.route-progress-bar.progress-assigned {
	background: var(--assigned-strong);
}

.route-progress-bar.progress-lr {
	background: var(--lr-strong);
}

.route-progress-bar.progress-trip {
	background: var(--trip-strong);
}

.route-progress-value {
	color: var(--ink);
	font-size: 10px;
	font-weight: 700;
	min-width: 34px;
	text-align: right;
}

.assign-row {
	background: #ffffff;
	display: grid;
	gap: 6px;
	grid-template-columns: minmax(0, 1fr) 52px;
}

.assign-row select,
.assign-button {
	height: 28px;
}

.route-body {
	height: calc(var(--cell-height) * 7);
	overflow-y: auto;
}

.route-cell {
	border-bottom: 1px solid var(--line);
	border-left: 4px solid transparent;
	display: grid;
	gap: 3px;
	min-height: var(--cell-height);
	padding: 5px 6px;
}

.route-cell.open {
	background: var(--idle);
	border-left-color: var(--idle-strong);
}

.route-cell.assigned {
	background: var(--assigned);
	border-left-color: var(--assigned-strong);
}

.route-cell.lr-created {
	background: var(--lr);
	border-left-color: var(--lr-strong);
}

.route-cell.trip-started {
	background: var(--trip);
	border-left-color: var(--trip-strong);
}

.cell-top {
	align-items: center;
	display: flex;
	gap: 8px;
	justify-content: space-between;
}

.cell-top strong {
	font-size: 12px;
}

.cell-meta,
.empty-cell-text {
	font-size: 11px;
}

.route-cell.assigned .cell-meta,
.route-cell.lr-created .cell-meta,
.route-cell.trip-started .cell-meta {
	color: rgba(0, 0, 0, 0.74);
}

.cell-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
}

.cell-button {
	background: #ffffff;
	border: 1px solid #c7d3e3;
	box-shadow: 0 8px 18px rgba(50, 50, 93, 0.08);
	color: var(--ink);
	min-height: 22px;
	padding: 0 6px;
}

.cell-button.info-button {
	background: #11cdef;
	border-color: #11cdef;
	color: #ffffff;
}

.cell-button.lr-button {
	background: #fb6340;
	border-color: #fb6340;
	color: #ffffff;
}

.cell-button.trip-button {
	background: #2dce89;
	border-color: #2dce89;
	color: #ffffff;
}

.remove-button {
	align-items: center;
	background: #f5365c;
	border: 1px solid #f5365c;
	box-shadow: 0 8px 18px rgba(245, 54, 92, 0.18);
	color: #ffffff;
	cursor: pointer;
	display: inline-flex;
	height: 20px;
	justify-content: center;
	padding: 0;
	width: 20px;
}

:global(.fuel-preview-grid) {
	display: grid;
	gap: 8px;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	margin: 4px 0 2px;
}

:global(.fuel-preview-item) {
	background: #f6f9fc;
	border-left: 4px solid #fb6340;
	box-shadow: inset 0 0 0 1px #dfe6f1;
	display: grid;
	gap: 2px;
	padding: 8px 10px;
}

:global(.fuel-preview-item span) {
	color: #525f7f;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
}

:global(.fuel-preview-item strong) {
	color: #172b4d;
	font-size: 14px;
	font-weight: 700;
}

@media (max-width: 1200px) {
	.board-summary-row,
	.toolbar-strip {
		grid-template-columns: 1fr;
	}
}

@media (max-width: 991px) {
	:global(.layout-main) {
		grid-template-columns: 1fr;
	}

	:global(.layout-side-section) {
		border-right: 0;
		border-bottom: 1px solid #d9dee5;
	}
}
</style>
