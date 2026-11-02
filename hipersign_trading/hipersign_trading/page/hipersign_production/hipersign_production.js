// Production — the prototype's Production page (v1.8.0, prototype p19): see public/js/hs_module.js and api/module_mfg.py.
frappe.pages["hipersign-production"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "mf_prod");
};
frappe.pages["hipersign-production"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
