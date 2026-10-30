// Finance — the prototype's "Finance & Management Visibility" module page (v1.6.0): see public/js/hs_module.js.
frappe.pages["hipersign-fin"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "finance");
};
frappe.pages["hipersign-fin"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
