// Shop floor — the job cards by workstation, a tablet view for the line (v1.8.0, prototype p19): see public/js/hs_manufacturing.js.
frappe.pages["hipersign-shopfloor"].on_page_load = function (wrapper) {
	hipersign.mfg.floor(wrapper);
};
frappe.pages["hipersign-shopfloor"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
	$(".popover").remove();
};
