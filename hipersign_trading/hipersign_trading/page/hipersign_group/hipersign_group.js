// Group & Countries — the prototype's module page (v1.7.0): see public/js/hs_module.js.
frappe.pages["hipersign-group"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "group");
};
frappe.pages["hipersign-group"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
