// Hipersign ERP v1.3 — bank charges on customer receipts, and the price-list item filter.
frappe.provide("hipersign.money");

// ---------------------------------------------------------------- Payment Entry: the transfer arrived short
frappe.ui.form.on("Payment Entry", {
	refresh(frm) { hipersign.money.short_button(frm); },
	paid_amount(frm) { setTimeout(() => hipersign.money.short_button(frm), 300); },
	received_amount(frm) { setTimeout(() => hipersign.money.short_button(frm), 300); },
});

hipersign.money.short_button = function (frm) {
	frm.remove_custom_button(__("Book the difference as bank charges"));
	if (frm.doc.docstatus !== 0 || frm.doc.payment_type !== "Receive" || frm.doc.party_type !== "Customer" || !(frm.doc.references || []).length) return;
	const owed = (frm.doc.references || []).reduce((a, r) => a + flt(r.outstanding_amount), 0);
	const ded = (frm.doc.deductions || []).reduce((a, r) => a + flt(r.amount), 0);
	const diff = flt(owed - flt(frm.doc.paid_amount) - ded, 2);
	if (diff <= 0.005) return;
	frm.add_custom_button(__("Book the difference as bank charges"), () => {
		frappe.xcall("hipersign_trading.overrides.payment_entry.short_payment_info", { allocated: owed, company: frm.doc.company }).then((s) => {
			if (!s.bank_charges_account) return frappe.msgprint(__("Set the bank charges account in Hipersign Settings first."));
			const over = diff > flt(s.limit) + 0.005;
			if (over && !s.can_override)
				return frappe.msgprint({ title: __("Above the limit"), indicator: "orange",
					message: __("{0} is above the limit of {1} for these invoices. Only the {2} can absorb it — or keep the balance open on the invoice.", [format_currency(diff), format_currency(s.limit), __(s.approver_role)]) });
			(frm.doc.references || []).forEach((r) => frappe.model.set_value(r.doctype, r.name, "allocated_amount", r.outstanding_amount));
			const row = frm.add_child("deductions");
			frappe.model.set_value(row.doctype, row.name, { account: s.bank_charges_account, cost_center: s.cost_center || row.cost_center,
				amount: diff, description: __("Bank charges deducted from the customer's transfer") });
			frm.refresh_field("deductions");
			if (frm.events.set_unallocated_amount) frm.events.set_unallocated_amount(frm);
			frappe.show_alert({ message: __("Invoice settled in full: bank {0} + bank charges {1}", [format_currency(frm.doc.paid_amount), format_currency(diff)]), indicator: "green" }, 6);
		});
	}).addClass("btn-primary");
	frm.dashboard.add_comment(__("{0} less than the invoices — book it as bank charges to settle them in full, or leave the balance open.", [format_currency(diff)]), "orange", true);
};

// ---------------------------------------------------------------- price lists: offer only the items in the selected list
["Quotation", "Sales Order", "Sales Invoice"].forEach((dt) => frappe.ui.form.on(dt, {
	refresh(frm) { hipersign.money.price_query(frm); },
	selling_price_list(frm) { hipersign.money.price_query(frm); },
	hs_all_items(frm) { hipersign.money.price_query(frm); },
}));

hipersign.money.price_query = function (frm) {
	if (!hipersign.info().price_list_items_only || frm.doc.docstatus !== 0) return;
	frm.set_query("item_code", "items", () => ({
		query: "hipersign_trading.api.pricing.items_in_price_list",
		filters: { price_list: frm.doc.selling_price_list, all_items: frm.doc.hs_all_items ? 1 : 0, is_sales_item: 1 },
	}));
	if (frm.doc.selling_price_list && !frm.doc.hs_all_items)
		frappe.xcall("hipersign_trading.api.pricing.price_list_info", { price_list: frm.doc.selling_price_list }).then((r) =>
			frm.set_df_property("hs_all_items", "description", __("The item list shows the {0} items in {1}. Tick to pick any item.", [r.items, frm.doc.selling_price_list])));
};
