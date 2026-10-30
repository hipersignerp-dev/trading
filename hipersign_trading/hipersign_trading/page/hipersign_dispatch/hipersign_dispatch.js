// Dispatch & Delivery — the prototype's "Dispatch & Delivery" module page (v1.6.0): see public/js/hs_module.js.
frappe.pages["hipersign-dispatch"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "dispatch");
};
frappe.pages["hipersign-dispatch"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
