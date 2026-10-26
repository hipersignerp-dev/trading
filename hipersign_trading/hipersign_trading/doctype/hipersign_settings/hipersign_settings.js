// Copyright (c) 2026, Hipersign
frappe.ui.form.on("Hipersign Settings", {
	refresh(frm) {
		frm.set_intro(frm.doc.setup_done ? __("Pack: {0} · {1} · documents {2}", [__(frm.doc.feature_pack || ""), __(frm.doc.company_mode || ""), __(frm.doc.document_level || "")])
			: __("Set-up is not finished — choose single company or group and the pack."), frm.doc.setup_done ? "blue" : "orange");
		frm.add_custom_button(__("Set-up wizard"), () => hipersign.setup_wizard(true), __("Set-up"));
		["Starter", "Standard", "Enterprise"].forEach((p) =>
			frm.add_custom_button(__("Switch to {0}", [__(p)]), () => frappe.confirm(__("Set every feature switch to the {0} pack? No data is deleted.", [__(p)]),
				() => frm.call("set_pack", { pack: p }).then(() => frm.reload_doc())), __("Pack")));
		frm.add_custom_button(__("Load demo data"), () => hipersign.load_demo(), __("Set-up"));
		frm.add_custom_button(__("Clear everyone's form-mode choices"), () =>
			frappe.xcall("hipersign_trading.api.quick.clear_form_modes").then((n) => frappe.show_alert(__("{0} choices cleared", [n]))), __("Set-up"));
		frm.add_custom_button(__("Editable lists"), () => frappe.set_route("List", "Hipersign List Value"), __("Set-up"));
		frm.add_custom_button(__("Document rules"), () => frappe.set_route("List", "Hipersign Document Rule"), __("Set-up"));
	},
	company_mode(frm) { if (frm.doc.company_mode === "Group") frm.set_value("feat_group", 1); },
	feat_imports(frm) { if (!frm.doc.feat_imports && frm.doc.feat_lc) frm.set_value("feat_lc", 0); },
});
