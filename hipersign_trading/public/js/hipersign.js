// Hipersign ERP — shared client helpers.
frappe.provide("hipersign");

hipersign.send_whatsapp = function (doctype, name, print_format) {
	frappe.xcall("hipersign_trading.api.share.whatsapp_link", { doctype, name, print_format }).then((r) => {
		const d = new frappe.ui.Dialog({
			title: __("Send by WhatsApp"),
			fields: [
				{ fieldtype: "Data", fieldname: "mobile", label: __("Mobile (with country code)"), default: r.mobile, reqd: 1 },
				{ fieldtype: "Small Text", fieldname: "message", label: __("Message"), default: r.message, reqd: 1 },
				{ fieldtype: "HTML", options: `<p class="text-muted small">${__("WhatsApp opens with the message ready; press send there. The PDF link expires automatically.")}</p>` },
			],
			primary_action_label: __("Open WhatsApp"),
			primary_action(v) {
				const num = (v.mobile || "").replace(/\D/g, "");
				window.open(`https://wa.me/${num}?text=${encodeURIComponent(v.message)}`, "_blank");
				frappe.xcall("hipersign_trading.api.share.log_send", { doctype, name, channel: "WhatsApp", to: v.mobile });
				d.hide();
			},
		});
		d.show();
	});
};

// Show the brand name in the browser tab.
$(document).on("page-change", () => {
	if (document.title && document.title.includes("ERPNext")) document.title = document.title.replace(/ERPNext/g, "Hipersign ERP");
});
