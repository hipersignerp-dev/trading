// Tax return: prepare → Finance Manager approves and locks → filed on EmaraTax → paid.
frappe.ui.form.on("Tax Return", {
	refresh(frm) {
		if (frm.is_new()) return;
		const s = frm.doc.status, call = (m, args) => frm.call(m, args).then(() => frm.reload_doc());
		const color = { Prepared: "blue", "Pending Finance Manager": "orange", Approved: "green", Submitted: "green", Paid: "green", Rejected: "red" }[s];
		frm.page.set_indicator(__(s), color);
		if (s === "Prepared") {
			frm.add_custom_button(__("Refresh figures"), () => call("refresh_figures"));
			frm.add_custom_button(__("Send for approval"), () => call("send_for_approval")).addClass("btn-primary");
		}
		if (s === "Pending Finance Manager" && frappe.user.has_role("Accounts Manager")) {
			frm.add_custom_button(__("Return for correction"), () => frappe.prompt({ fieldtype: "Small Text", fieldname: "r", label: __("Reason"), reqd: 1 }, (v) => call("reject", { reason: v.r })), __("Decide"));
			frm.add_custom_button(__("Approve & lock"), () => call("approve"), __("Decide"));
		}
		if (s === "Approved") frm.add_custom_button(__("Filed on EmaraTax"), () => frappe.prompt([
			{ fieldtype: "Data", fieldname: "ref", label: __("EmaraTax reference"), reqd: 1 },
			{ fieldtype: "Date", fieldname: "d", label: __("Filed on"), default: frappe.datetime.get_today() }], (v) => call("mark_submitted", { reference: v.ref, submitted_on: v.d }))).addClass("btn-primary");
		if (s === "Submitted") frm.add_custom_button(__("Record payment"), () => frappe.prompt([
				{ fieldtype: "Data", fieldname: "ref", label: __("Payment reference (GIBAN / receipt)"), reqd: 1 },
				{ fieldtype: "Date", fieldname: "d", label: __("Paid on"), default: frappe.datetime.get_today() }], (v) => call("mark_paid", { reference: v.ref, paid_on: v.d })));
		if (frm.doc.tax_type === "VAT 201") frm.add_custom_button(__("UAE VAT 201 report"), () => frappe.set_route("query-report", "UAE VAT 201", { company: frm.doc.company, from_date: frm.doc.period_from, to_date: frm.doc.period_to }));
		if (frm.doc.due_date && !["Submitted", "Paid"].includes(s)) {
			const left = frappe.datetime.get_day_diff(frm.doc.due_date, frappe.datetime.get_today());
			frm.dashboard.add_comment(left < 0 ? __("Overdue by {0} days — late filing attracts FTA penalties", [-left]) : __("Due in {0} days ({1})", [left, frappe.datetime.str_to_user(frm.doc.due_date)]), left < 7 ? "red" : "blue", true);
		}
	},
	tax_type(frm) {
		if (frm.doc.tax_type === "Corporate Tax" && frm.is_new()) {
			const y = moment().subtract(1, "year").year();
			frm.set_value({ period_from: `${y}-01-01`, period_to: `${y}-12-31` });
		}
	},
});
