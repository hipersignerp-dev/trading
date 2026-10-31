// HR & Payroll — the prototype's module page (v1.7.0): see public/js/hs_module.js.
frappe.pages["hipersign-people"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "hr");
};
frappe.pages["hipersign-people"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
