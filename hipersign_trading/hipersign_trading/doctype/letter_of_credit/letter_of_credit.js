// Letter of credit: move through the bank stages and make the margin / trust receipt journals.
frappe.ui.form.on("Letter of Credit", {
	refresh(frm) {
		if (frm.is_new()) return;
		const step = (label, status, field) => frm.add_custom_button(__(label), () => {
			frappe.prompt([{ fieldtype: "Date", fieldname: "d", label: __("Date"), default: frappe.datetime.get_today(), reqd: 1 },
				...(status === "Issued" && !frm.doc.lc_number ? [{ fieldtype: "Data", fieldname: "no", label: __("LC number"), reqd: 1 }] : [])],
			(v) => {
				const vals = { status }; vals[field] = v.d; if (v.no) vals.lc_number = v.no;
				frm.set_value(vals).then(() => frm.save());
			}, __(label));
		}, __("Status"));
		const s = frm.doc.status;
		if (s === "Applied") step("Issued by the bank", "Issued", "issue_date");
		if (s === "Issued") step("Documents presented", "Documents Presented", "documents_presented_on");
		if (s === "Documents Presented") step("Accepted", "Accepted", "accepted_on");
		if (["Issued", "Documents Presented", "Accepted"].includes(s)) step("Paid", "Paid", "paid_on");
		if (["Applied", "Issued"].includes(s)) frm.add_custom_button(__("Expired"), () => frm.set_value("status", "Expired").then(() => frm.save()), __("Status"));
		if (frm.doc.margin_amount && !frm.doc.margin_entry && s !== "Applied")
			frm.add_custom_button(__("Margin journal entry"), () => frm.call("make_margin_entry").then(r => r.message && frappe.set_route("Form", "Journal Entry", r.message)), __("Create"));
		if (frm.doc.trust_receipt && !frm.doc.tr_entry)
			frm.add_custom_button(__("Trust receipt journal entry"), () => frm.call("make_trust_receipt_entry").then(r => r.message && frappe.set_route("Form", "Journal Entry", r.message)), __("Create"));
		if (frm.doc.expiry_date && ["Applied", "Issued"].includes(s)) {
			const left = frappe.datetime.get_day_diff(frm.doc.expiry_date, frappe.datetime.get_today());
			if (left <= 14) frm.dashboard.add_comment(left < 0 ? __("Expired {0} days ago", [-left]) : __("Expires in {0} days", [left]), left < 0 ? "red" : "orange", true);
		}
	},
	purchase_order(frm) {
		if (!frm.doc.purchase_order) return;
		frappe.db.get_value("Purchase Order", frm.doc.purchase_order, ["supplier", "currency", "grand_total", "conversion_rate"]).then(({ message: p }) => {
			frm.set_value({ supplier: p.supplier, currency: p.currency, amount: p.grand_total, exchange_rate: p.conversion_rate });
		});
	},
});
