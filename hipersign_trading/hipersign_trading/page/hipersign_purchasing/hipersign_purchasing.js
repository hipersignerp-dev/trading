// Purchase Orders — the prototype's "Supplier Purchasing" module page (v1.6.0): see public/js/hs_module.js.
frappe.pages["hipersign-purchasing"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "purchasing");
};
frappe.pages["hipersign-purchasing"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
