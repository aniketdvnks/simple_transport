frappe.pages['daily-planning'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Daily Planning',
		single_column: true
	});
	new DailyPlanning(wrapper)
}

class DailyPlanning{
	constructor(wrapper){
		this.page = wrapper.page;
		this.wrapper = $(wrapper).find(".page-content");
		this.currentUser = frappe.session.user;

		 // Petite-Vue bridge
		this.vue = null;
		this.vueMounted = false;

		// Petite-Vue shared reactive state
		if (!window.mycrmVue) {
		window.mycrmVue = {
			section: "lead",
			search: "",
			leadCount: 0,
			appointmentCount: 0,
			cacheHit: false,
		};
		}

		this.init();
	}
}
