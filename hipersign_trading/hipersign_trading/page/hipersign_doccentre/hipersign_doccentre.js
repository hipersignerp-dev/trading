// v1.8.4 (#37): Document Centre — missing documents, exceptions and document rules as a Hipersign page (api/module_extra.py).
frappe.pages["hipersign-doccentre"].on_page_load = function (wrapper) {
	hipersign.module.render(wrapper, "doccentre");
};
frappe.pages["hipersign-doccentre"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
