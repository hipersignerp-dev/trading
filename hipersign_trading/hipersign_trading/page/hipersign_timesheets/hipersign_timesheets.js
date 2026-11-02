// Timesheets & labour — the prototype's Projects page (v1.8.0, prototype p19): see public/js/hs_module.js and api/module_prj.py.
frappe.pages["hipersign-timesheets"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "pj_time");
};
frappe.pages["hipersign-timesheets"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
