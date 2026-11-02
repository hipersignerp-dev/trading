// Estimating & BOQ — the prototype's Projects page (v1.8.0, prototype p19): see public/js/hs_module.js and api/module_prj.py.
frappe.pages["hipersign-boq"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "pj_boq");
};
frappe.pages["hipersign-boq"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
