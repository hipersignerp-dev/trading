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
	// v1.5.6 (SET-04): picking a pack here applies it, like the Pack menu
	feature_pack(frm) {
		const p = frm.doc.feature_pack, prev = frm.__hs_pack || (frm.doc.__onload || {}).feature_pack;
		if (!["Starter", "Standard", "Enterprise"].includes(p)) return;
		frappe.confirm(__("Set every feature switch to the {0} pack? No data is deleted.", [__(p)]),
			() => frm.save(),
			() => frm.set_value("feature_pack", frm.__hs_pack_saved || prev || "Custom"));
	},
	onload_post_render(frm) { frm.__hs_pack_saved = frm.doc.feature_pack; frm.__hs_desk = hs_desk_sig(frm); },
	after_save(frm) {
		frm.__hs_pack_saved = frm.doc.feature_pack;
		// v1.6.0: the desktop tiles, theme and menu are in the page's boot — reload once so they show at once
		const sig = hs_desk_sig(frm);
		if (frm.__hs_desk !== undefined && sig !== frm.__hs_desk) {
			frm.__hs_desk = sig;
			frappe.show_alert({ message: __("Desktop and menu updated — reloading…"), indicator: "blue" });
			setTimeout(() => frappe.ui.toolbar.clear_cache(), 900);
		}
	},
	company_mode(frm) { if (frm.doc.company_mode === "Group") frm.set_value("feat_group", 1); },
	feat_imports(frm) { if (!frm.doc.feat_imports && frm.doc.feat_lc) frm.set_value("feat_lc", 0); },
});

function hs_desk_sig(frm) {
	return ["only_hipersign_tiles", "desk_theme", "keep_hipersign_sidebar", "hide_getting_started"].map((f) => String(frm.doc[f] || "")).join("|");
}
