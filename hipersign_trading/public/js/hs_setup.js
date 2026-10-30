// Hipersign ERP v1.3 — set-up wizard (single company or group, which pack), Load demo data, feature switches.
frappe.provide("hipersign");

hipersign.info = () => (frappe.boot && frappe.boot.hipersign) || { features: {}, form_modes: {}, ruled_doctypes: [] };
hipersign.feature = (key) => {
	const f = hipersign.info().features || {};
	return f[key] === undefined ? true : !!f[key];
};

hipersign.PACKS = {
	Starter: __("Small local trader, one company — quotations, orders, purchases, stock, delivery, invoices, VAT and accounts. Forms open in Quick mode; no document rules."),
	Standard: __("Growing importer or exporter — adds CRM, imports and landed cost, exports, approvals, KYC, advances, cheques, bank reconciliation and currencies. Documents are recommended, nothing blocks."),
	Enterprise: __("Groups and larger traders — everything: LCs and trade finance, company compliance, group consolidation, HR documents, fixed assets, blocking document rules with exceptions."),
};

hipersign.setup_wizard = function (force) {
	const info = hipersign.info();
	const d = new frappe.ui.Dialog({
		title: __("Set up Hipersign ERP"),
		size: "large",
		fields: [
			{ fieldtype: "HTML", options: `<p class="text-muted">${__("Two questions — you can change both later in Hipersign Settings → Setup & features. Nothing is deleted when you switch.")}</p>` },
			{ fieldtype: "Select", fieldname: "company_mode", label: __("1. How many companies?"), reqd: 1, default: info.company_mode || "Single company",
				options: [{ value: "Single company", label: __("Single company") }, { value: "Group", label: __("Multiple companies (group) — consolidation and inter-company") }] },
			{ fieldtype: "Select", fieldname: "pack", label: __("2. Which pack?"), reqd: 1, default: ["Starter", "Standard", "Enterprise"].includes(info.pack) ? info.pack : "Standard",
				options: ["Starter", "Standard", "Enterprise"].map((p) => ({ value: p, label: __(p) })), change() { d.set_df_property("pack_help", "options", help(d.get_value("pack"))); } },
			{ fieldtype: "HTML", fieldname: "pack_help" },
			{ fieldtype: "Link", fieldname: "company", label: __("Main company"), options: "Company", default: frappe.defaults.get_default("company") },
		],
		primary_action_label: __("Finish set-up"),
		primary_action(v) {
			frappe.xcall("hipersign_trading.api.setup.complete_setup", { company_mode: v.company_mode, pack: v.pack, company: v.company }).then(() => {
				d.hide();
				frappe.msgprint({ title: __("Set-up complete"), indicator: "green",
					message: __("{0} pack, {1}. The menus, rules and forms now follow it. Load demo data from Hipersign Settings → Set-up if this is a demo site.", [__(v.pack), __(v.company_mode)]) });
				setTimeout(() => window.location.reload(), 1800);
			});
		},
	});
	const help = (p) => `<div class="alert alert-info" style="margin-top:6px">${hipersign.PACKS[p] || ""}</div>`;
	d.set_df_property("pack_help", "options", help(d.get_value("pack")));
	if (!force) d.$wrapper.find(".modal-header .btn-modal-close").hide();
	d.show();
};

hipersign.load_demo = function () {
	frappe.xcall("hipersign_trading.api.setup.demo_status").then((st) => {
		if (!st.allowed) return frappe.msgprint({ title: __("Demo data"), indicator: "orange", message: st.why });
		if (st.running) return frappe.msgprint(__("Demo data is loading — check back in a few minutes."));
		frappe.prompt({ fieldtype: "Data", fieldname: "confirm", label: __("Type DEMO to load the demo companies, customers, items and transactions"), reqd: 1,
				description: __("The site switches to the Enterprise pack (group of companies) so every feature has sample data — you can switch back afterwards.") },
			(v) => frappe.xcall("hipersign_trading.api.setup.load_demo", { confirm: v.confirm }).then((m) => frappe.msgprint({ title: __("Demo data"), indicator: "blue", message: m })),
			__("Load demo data"), __("Load"));
	});
};

$(document).on("app_ready", () => {
	const info = hipersign.info();
	// v1.6.0: not over ERPNext's own set-up wizard (the company it creates is the one the questions ask about)
	const in_wizard = (frappe.get_route() || [])[0] === "setup-wizard" || (frappe.boot.sysdefaults && !cint(frappe.boot.sysdefaults.setup_complete));
	if (info.setup_needed && info.is_system_manager && !in_wizard && !sessionStorage.getItem("hs_setup_shown")) {
		sessionStorage.setItem("hs_setup_shown", 1);
		setTimeout(() => hipersign.setup_wizard(false), 1200);
	}
});

// buttons of switched-off features on the forms
frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (!hipersign.feature("exports")) frm.remove_custom_button(__("Export shipment"), __("Create"));
		if (!hipersign.feature("advances")) frm.remove_custom_button(__("Receive advance"), __("Create"));
	},
});
frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (!hipersign.feature("advances")) {
			frm.remove_custom_button(__("Promise to pay"), __("Collection"));
			frm.remove_custom_button(__("Send reminder on WhatsApp"), __("Collection"));
		}
	},
});
