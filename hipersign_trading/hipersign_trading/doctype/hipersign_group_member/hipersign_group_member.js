// Copyright (c) 2026, Hipersign
frappe.ui.form.on("Hipersign Group Member", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Sync trial balance"), () => frappe.prompt({ fieldtype: "Date", fieldname: "period_end", label: __("Up to"), default: frappe.datetime.get_today(), reqd: 1 },
			(v) => frm.call("sync_now", v).then((r) => { frappe.show_alert({ message: r.message, indicator: "green" }); frm.reload_doc(); }), __("Sync")));
		frm.add_custom_button(__("Consolidation"), () => frappe.set_route("query-report", "Hipersign Group Consolidation"));
	},
});
