// Copyright (c) 2026, Hipersign
frappe.ui.form.on("Company Deadline", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Open")
			frm.add_custom_button(__("Mark done"), () => frm.call("mark_done").then((r) => { frm.reload_doc(); if (r.message) frappe.show_alert(__("Next deadline {0} created", [r.message])); }));
	},
});
