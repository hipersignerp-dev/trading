// Copyright (c) 2026, Hipersign
frappe.ui.form.on("Company Document", {
	refresh(frm) {
		const c = { Valid: "green", "Due for renewal": "orange", Expired: "red", "Submitted to authority": "blue", "No expiry": "gray" };
		if (frm.doc.status) frm.page.set_indicator(__(frm.doc.status), c[frm.doc.status] || "gray");
		if (!frm.is_new() && frm.doc.expiry_date) {
			frm.add_custom_button(__("Record renewal"), () => frappe.prompt([
				{ fieldtype: "Date", fieldname: "expiry_date", label: __("New expiry date"), reqd: 1 },
				{ fieldtype: "Date", fieldname: "issue_date", label: __("Issued on"), default: frappe.datetime.get_today() },
				{ fieldtype: "Data", fieldname: "document_number", label: __("New number (if it changed)") },
			], (v) => frm.call("renew", v).then(() => frm.reload_doc()), __("Renewed document")));
			if (frm.doc.status !== "Submitted to authority" && frm.doc.status !== "Valid")
				frm.add_custom_button(__("Submitted to authority"), () => { frm.set_value("renewal_status", "Submitted to authority"); frm.save(); });
		}
	},
});
