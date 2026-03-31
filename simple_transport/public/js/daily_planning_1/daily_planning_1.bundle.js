import { createApp } from "vue";
import App from "./App.vue";

class DailyPlanning1 {
	constructor({ page, wrapper }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		this.handleSidebarUpdate = this.handleSidebarUpdate.bind(this);

		this.init();
	}

	init() {
		this.setup_page_actions();
		this.setup_sidebar();
		this.setup_app();
	}

	setup_page_actions() {
		this.page.set_primary_action(__("Refresh"), () => {
			window.dispatchEvent(new CustomEvent("simple-transport:refresh-daily-planning"));
		});
	}

	setup_sidebar() {
		this.page.sidebar.html(`
			<div class="daily-planning-sidebar overlay-sidebar">
				<details class="sidebar-section" open>
					<summary class="sidebar-title">Idle Vehicles</summary>
					<div class="sidebar-list sidebar-list-idle"></div>
				</details>
				<details class="sidebar-section" open>
					<summary class="sidebar-title">At Unloading Point</summary>
					<div class="sidebar-list sidebar-list-unloading"></div>
				</details>
			</div>
		`);
		this.$sidebar = this.page.sidebar.find(".daily-planning-sidebar");
		window.addEventListener(
			"simple-transport:update-daily-planning-sidebar",
			this.handleSidebarUpdate
		);
	}

	handleSidebarUpdate(event) {
		const detail = event?.detail || {};
		this.renderSidebarSection(
			this.$sidebar.find(".sidebar-list-idle"),
			detail.idle_vehicles || [],
			"No idle vehicles"
		);
		this.renderSidebarSection(
			this.$sidebar.find(".sidebar-list-unloading"),
			detail.unloading_vehicles || [],
			"No unloading vehicles"
		);
	}

	renderSidebarSection($target, vehicles, emptyMessage) {
		if (!$target?.length) {
			return;
		}

		if (!vehicles.length) {
			$target.html(`<div class="sidebar-empty">${frappe.utils.escape_html(emptyMessage)}</div>`);
			return;
		}

		const items = vehicles
			.map((vehicle) => {
				const label = frappe.utils.escape_html(vehicle.label || vehicle.name || "");
				const status = frappe.utils.escape_html(vehicle.status || "");
				const statusClass = this.getStatusClass(vehicle.status || "");
				const driver = frappe.utils.escape_html(vehicle.driver || "-");
				const meta = [];
				if (vehicle.capacity_mt) {
					meta.push(`${vehicle.capacity_mt} MT`);
				}
				if (vehicle.current_trip) {
					meta.push(`Trip ${frappe.utils.escape_html(vehicle.current_trip)}`);
				}
				if (vehicle.last_location) {
					meta.push(frappe.utils.escape_html(vehicle.last_location));
				}

				return `
					<div class="sidebar-vehicle-row ${statusClass}">
						<div class="sidebar-vehicle-head">
							<strong>${label}</strong>
							<span class="sidebar-status ${statusClass}">${status}</span>
						</div>
						<div class="sidebar-vehicle-sub">${driver}</div>
						<div class="sidebar-vehicle-meta">${meta.join(" • ")}</div>
					</div>
				`;
			})
			.join("");

		$target.html(items);
	}

	getStatusClass(status) {
		const value = (status || "").toLowerCase();
		if (value === "idle") {
			return "status-idle";
		}
		if (value === "at unloading point") {
			return "status-trip";
		}
		if (value === "under maintenance") {
			return "status-maintenance";
		}
		return "status-assigned";
	}

	setup_app() {
		let app = createApp(App);
		this.$daily_planning_1 = app.mount(this.$wrapper.get(0));
	}

	destroy() {
		window.removeEventListener(
			"simple-transport:update-daily-planning-sidebar",
			this.handleSidebarUpdate
		);
	}
}

frappe.provide("frappe.ui");
frappe.ui.DailyPlanning1 = DailyPlanning1;
export default DailyPlanning1;
