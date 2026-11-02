// Project Tracker — every project through the 26 steps in 6 phases (v1.8.0, prototype p19): see public/js/hs_projects.js.
frappe.pages["project-tracker"].on_page_load = function (wrapper) {
	hipersign.projects.tracker(wrapper);
};
frappe.pages["project-tracker"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
	$(".popover").remove();
};
