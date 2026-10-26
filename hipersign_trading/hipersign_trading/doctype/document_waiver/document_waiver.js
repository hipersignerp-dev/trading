// Copyright (c) 2026, Hipersign
frappe.ui.form.on("Document Waiver", {
	refresh(frm) {
		const ind = { Pending: "orange", Approved: "green", Rejected: "red", Received: "blue", Overdue: "red", Used: "gray" };
		frm.page.set_indicator(__(frm.doc.status), ind[frm.doc.status] || "gray");
		if (frm.doc.reference_doctype && frm.doc.reference_name)
			frm.add_custom_button(__("Open {0}", [__(frm.doc.reference_doctype)]), () => frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name));
		if (frm.doc.status === "Pending" && !frm.is_new() && (frappe.user.has_role(frm.doc.approver_role) || frappe.user.has_role("System Manager"))) {
			frm.add_custom_button(__("Approve"), () => frappe.prompt({ fieldtype: "Small Text", fieldname: "note", label: __("Note") },
				(v) => frm.call("approve", { note: v.note }).then(() => frm.reload_doc()), __("Approve exception")), __("Decide"));
			frm.add_custom_button(__("Reject"), () => frappe.prompt({ fieldtype: "Small Text", fieldname: "note", label: __("Why"), reqd: 1 },
				(v) => frm.call("reject", { note: v.note }).then(() => frm.reload_doc()), __("Reject exception")), __("Decide"));
		}
	},
});
