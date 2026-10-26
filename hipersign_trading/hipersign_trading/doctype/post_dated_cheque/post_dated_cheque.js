// Copyright (c) 2026, Hipersign
frappe.ui.form.on("Post Dated Cheque", {
	setup(frm) {
		frm.set_query("reference_doctype", () => ({}));
		frm.set_query("bank_account", () => ({ filters: { company: frm.doc.company, account_type: "Bank", is_group: 0 } }));
		frm.set_query("reference_name", () => {
			const party = frm.doc.direction === "Received" ? "customer" : "supplier";
			const f = { docstatus: 1 };
			f[party] = frm.doc.party;
			if ((frm.doc.reference_doctype || "").endsWith("Invoice")) f.outstanding_amount = [">", 0];
			return { filters: f };
		});
	},
	direction(frm) {
		frm.set_value("party_type", frm.doc.direction === "Received" ? "Customer" : "Supplier");
		frm.set_value("reference_doctype", frm.doc.direction === "Received" ? "Sales Invoice" : "Purchase Invoice");
		frm.set_value("party", "");
	},
	reference_name(frm) {
		if (!frm.doc.reference_name || !(frm.doc.reference_doctype || "").endsWith("Invoice")) return;
		frappe.db.get_value(frm.doc.reference_doctype, frm.doc.reference_name, "outstanding_amount").then((r) => {
			if (!frm.doc.amount && r.message) frm.set_value("amount", r.message.outstanding_amount);
		});
	},
	refresh(frm) {
		if (frm.is_new()) return;
		const go = (method, args, msg) =>
			frm.call(method, args || {}).then(() => { frm.reload_doc(); if (msg) frappe.show_alert({ message: msg, indicator: "green" }); });
		const st = frm.doc.status;
		const due = frappe.datetime.get_day_diff(frm.doc.cheque_date, frappe.datetime.get_today());
		frm.dashboard.clear_headline();
		if (["In Hand", "Deposited", "Issued"].includes(st))
			frm.dashboard.set_headline_alert(
				due > 0 ? __("Cheque date in {0} days", [due]) : due === 0 ? __("Cheque date is today") : __("{0} days past the cheque date", [-due]),
				due <= 0 ? "orange" : "blue"
			);
		if (st === "In Hand") frm.add_custom_button(__("Deposit"), () => go("deposit", {}, __("Deposited"))).addClass("btn-primary");
		if (st === "Deposited") {
			frm.add_custom_button(__("Cleared"), () => go("clear", {}, __("Payment Entry created"))).addClass("btn-primary");
			frm.add_custom_button(__("Bounced"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Data", label: __("Bank return reason"), default: __("Insufficient funds") },
					(v) => go("bounce", v, __("Marked as bounced"))));
		}
		if (st === "Issued") frm.add_custom_button(__("Presented & cleared"), () => go("clear", {}, __("Payment Entry created"))).addClass("btn-primary");
		if (st === "Bounced")
			frm.add_custom_button(__("Replacement cheque"), () =>
				frappe.prompt([
					{ fieldname: "cheque_no", fieldtype: "Data", label: __("New cheque no."), reqd: 1 },
					{ fieldname: "cheque_date", fieldtype: "Date", label: __("Cheque date"), reqd: 1 },
					{ fieldname: "amount", fieldtype: "Currency", label: __("Amount"), default: frm.doc.amount },
				], (v) => frm.call("replace", v).then((r) => frappe.set_route("Form", "Post Dated Cheque", r.message))));
		if (["In Hand", "Issued", "Bounced"].includes(st))
			frm.add_custom_button(__("Cancel cheque"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Data", label: __("Reason") }, (v) => go("cancel_cheque", v)), __("More"));
		if (frm.doc.payment_entry) frm.add_custom_button(__("Payment Entry"), () => frappe.set_route("Form", "Payment Entry", frm.doc.payment_entry), __("View"));
		if (frm.doc.reference_name) frm.add_custom_button(frm.doc.reference_name, () => frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name), __("View"));
	},
});
