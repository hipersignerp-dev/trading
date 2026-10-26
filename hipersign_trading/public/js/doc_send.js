// Print, email and WhatsApp buttons on customer and supplier documents.
const HS_SEND = {
	Quotation: "Hipersign Quotation",
	"Sales Order": "Hipersign Order Confirmation",
	"Sales Invoice": "Hipersign Tax Invoice",
	"Delivery Note": "Hipersign Delivery Note",
	"Purchase Order": "Hipersign Purchase Order",
	"Export Shipment": "Hipersign Packing List",
};
Object.keys(HS_SEND).forEach((dt) => {
	frappe.ui.form.on(dt, {
		refresh(frm) {
			if (frm.is_new()) return;
			const pf = HS_SEND[dt];
			frm.add_custom_button(__("Print / PDF"), () => window.open(frappe.urllib.get_full_url(`/printview?doctype=${encodeURIComponent(dt)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(pf)}`)), __("Send"));
			frm.add_custom_button(__("Email"), () => new frappe.views.CommunicationComposer({ doc: frm.doc, frm, subject: `${__(dt)} ${frm.doc.name}`, recipients: frm.doc.contact_email || "", attach_document_print: true, print_format: pf }), __("Send"));
			frm.add_custom_button(__("WhatsApp"), () => hipersign.send_whatsapp(dt, frm.doc.name, pf), __("Send"));
			if (dt === "Sales Order" && frm.doc.hs_is_export) {
				frm.add_custom_button(__("Proforma invoice"), () => window.open(frappe.urllib.get_full_url(`/printview?doctype=Sales%20Order&name=${encodeURIComponent(frm.doc.name)}&format=Hipersign%20Proforma%20Invoice`)), __("Send"));
			}
		},
	});
});
