// Production Tracker — every sales order through the 22 steps in 5 phases (v1.8.0, prototype p19): see public/js/hs_manufacturing.js.
frappe.pages["production-tracker"].on_page_load = function (wrapper) {
	hipersign.mfg.tracker(wrapper);
};
frappe.pages["production-tracker"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
	$(".popover").remove();
};
