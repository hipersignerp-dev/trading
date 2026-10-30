// VAT & E-invoicing — the prototype's module page (v1.6.0): see public/js/hs_module.js.
frappe.pages["hipersign-vat"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "vat");
};
frappe.pages["hipersign-vat"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
