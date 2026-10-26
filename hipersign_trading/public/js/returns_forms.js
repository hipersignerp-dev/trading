// Credit / debit notes: reason required, and a clear note about who approves them
["Sales Invoice", "Purchase Invoice"].forEach((dt) => {
	frappe.ui.form.on(dt, {
		refresh(frm) {
			if (!frm.doc.is_return || frm.doc.docstatus !== 0 || frm.is_new()) return;
			const who = dt === "Sales Invoice" ? __("Sales Manager") : __("Purchase Manager");
			frm.dashboard.set_headline_alert(__("This {0} must be submitted by the {1}.", [dt === "Sales Invoice" ? __("credit note") : __("debit note"), who]), "orange");
		},
	});
});
// Delivery Note: proof of delivery summary
frappe.ui.form.on("Delivery Note", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !frm.doc.hs_delivery_status) return;
		const c = { "Ready to Dispatch": "orange", "Out for Delivery": "blue", Delivered: "green", Failed: "red" }[frm.doc.hs_delivery_status];
		frm.dashboard.add_indicator(__(frm.doc.hs_delivery_status) + (frm.doc.hs_received_by ? " · " + __("signed by {0}", [frm.doc.hs_received_by]) : ""), c);
		if (frm.doc.hs_delivery_status !== "Delivered")
			frm.add_custom_button(__("Open driver app"), () => window.open("/driver"), __("Hipersign"));
	},
});
// Serial No: warranty look-up shortcut
frappe.ui.form.on("Serial No", {
	refresh(frm) {
		if (!frm.is_new()) frm.add_custom_button(__("Warranty look-up"), () => frappe.set_route("serial-lookup", { serial: frm.doc.name }));
	},
});
