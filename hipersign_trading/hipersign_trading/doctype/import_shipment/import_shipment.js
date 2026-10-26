// Copyright (c) 2026, Hipersign
const HS_IMPORT_STEPS = ["Booked", "Shipped", "In Transit", "Arrived at Port", "Under Customs Clearance", "Cleared", "Received at Warehouse"];

frappe.ui.form.on("Import Shipment", {
	refresh(frm) {
		const i = HS_IMPORT_STEPS.indexOf(frm.doc.status);
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline_alert(
			HS_IMPORT_STEPS.map((s, k) => `<span class="indicator-pill ${k < i ? "green" : k === i ? "blue" : "gray"}" style="margin:2px">${__(s)}</span>`).join(" ")
		);
		if (!frm.is_new() && i < 5) {
			frm.add_custom_button(__("Move to {0}", [__(HS_IMPORT_STEPS[i + 1])]), () => {
				frm.set_value("status", HS_IMPORT_STEPS[i + 1]);
				frm.save();
			}).addClass("btn-primary");
		}
		if (!frm.is_new() && i >= 5) {
			frm.add_custom_button(__("Receive goods"), () => {
				const po = (frm.doc.purchase_orders || [])[0];
				if (!po) return;
				frappe.model.open_mapped_doc({
					method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
					source_name: po.purchase_order,
				});
			});
			frm.add_custom_button(__("Landed cost voucher"), () =>
				frm.call("make_landed_cost_voucher").then((r) => r.message && frappe.set_route("Form", "Landed Cost Voucher", r.message))
			);
		}
	},
});

frappe.ui.form.on("Shipment Charge", {
	amount(frm) {
		frm.set_value("total_charges", (frm.doc.charges || []).reduce((t, c) => t + (c.amount || 0), 0));
	},
});
