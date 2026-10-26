// WPS salary file button on Payroll Entry (Frappe HR)
frappe.ui.form.on("Payroll Entry", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		frm.add_custom_button(__("WPS salary file (SIF)"), () => {
			window.open(`/api/method/hipersign_trading.api.wps.download_sif?payroll_entry=${encodeURIComponent(frm.doc.name)}`);
		}, __("Hipersign"));
	},
});
