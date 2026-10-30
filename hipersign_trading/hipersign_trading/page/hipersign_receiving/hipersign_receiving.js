// Goods Receiving — the prototype's "Goods Receiving" module page (v1.6.0): see public/js/hs_module.js.
frappe.pages["hipersign-receiving"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "receiving");
};
frappe.pages["hipersign-receiving"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
