frappe.pages["daily-planning-1"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "",
		single_column: false,
	});
};

frappe.pages["daily-planning-1"].on_page_show = function (wrapper) {
	load_desk_page(wrapper);
};

function load_desk_page(wrapper) {
	if (frappe.daily_planning_1?.destroy) {
		frappe.daily_planning_1.destroy();
	}

	let $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	wrapper.page.sidebar.empty();

	frappe.require("daily_planning_1.bundle.js").then(() => {
		frappe.daily_planning_1 = new frappe.ui.DailyPlanning1({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}
