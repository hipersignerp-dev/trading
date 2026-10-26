// Copyright (c) 2026, Hipersign
const HS_EXPORT_STEPS = ["Booked", "Packed", "Export Declaration", "Customs Cleared", "Shipped", "Delivered", "Documents Complete"];

frappe.ui.form.on("Export Shipment", {
	setup(frm) {
		frm.set_query("sales_order", () => ({ filters: { docstatus: 1, hs_is_export: 1 } }));
		frm.set_query("forwarder", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		const i = HS_EXPORT_STEPS.indexOf(frm.doc.status);
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline_alert(
			HS_EXPORT_STEPS.map((s, k) => `<span class="indicator-pill ${k < i ? "green" : k === i ? "blue" : "gray"}" style="margin:2px">${__(s)}</span>`).join(" ") +
				(frm.doc.proof_due_on && !frm.doc.proof_of_export_on ? `<div class="text-danger small" style="margin-top:6px">${__("Proof of export due by {0} to keep 0% VAT", [frappe.datetime.str_to_user(frm.doc.proof_due_on)])}</div>` : "")
		);
		if (frm.is_new()) return;
		if (!frm.doc.delivery_note) {
			frm.add_custom_button(__("Pack — create delivery note"), () =>
				frm.call("make_delivery_note").then((r) => frappe.set_route("Form", "Delivery Note", r.message))
			).addClass("btn-primary");
		} else if (!frm.doc.sales_invoice) {
			frm.add_custom_button(__("Create export invoice (0% VAT)"), () =>
				frm.call("make_sales_invoice").then((r) => frappe.set_route("Form", "Sales Invoice", r.message))
			);
		}
		if (i < HS_EXPORT_STEPS.length - 1) {
			frm.add_custom_button(__("Move to {0}", [__(HS_EXPORT_STEPS[i + 1])]), () =>
				frm.call("advance").then(() => frm.reload_doc())
			).addClass(frm.doc.delivery_note ? "btn-primary" : "");
		}
		frm.add_custom_button(__("Packing list"), () => frm.print_doc(), __("Print"));
	},
});
