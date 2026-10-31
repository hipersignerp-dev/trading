// Export & Re-export — the prototype's module page (v1.7.0): see public/js/hs_module.js.
frappe.pages["hipersign-exports"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "exports");
};
frappe.pages["hipersign-exports"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
