// Hipersign ERP v1.3 — form modes: Quick (a small dialog), Standard (the essential fields), Detailed (every field).
frappe.provide("hipersign.fm");

hipersign.fm.COVERED = ["Quotation", "Sales Order", "Purchase Order", "Sales Invoice", "Payment Entry", "Customer", "Item", "Lead"];
// fields hidden in Standard (Detailed shows them all)
hipersign.fm.OPTIONAL = {
	Quotation: ["hs_enquiry_ref", "hs_enquiry_date", "order_type", "incoterm", "named_place", "campaign", "source", "letter_head", "select_print_heading",
		"language", "tc_name", "scan_barcode", "competitors", "referral_sales_partner", "utm_source", "utm_campaign", "utm_medium"],
	"Sales Order": ["po_date", "order_type", "hs_payment_method", "hs_shipment_mode", "set_warehouse", "incoterm", "named_place", "project", "cost_center",
		"campaign", "source", "letter_head", "select_print_heading", "language", "tc_name", "scan_barcode", "utm_source", "utm_campaign", "utm_medium"],
	"Purchase Order": ["hs_shipment_mode", "hs_port_of_loading", "hs_port_of_discharge", "incoterm", "named_place", "order_confirmation_no",
		"order_confirmation_date", "set_from_warehouse", "project", "cost_center", "letter_head", "select_print_heading", "language", "tc_name", "scan_barcode"],
	"Sales Invoice": ["po_date", "project", "cost_center", "campaign", "source", "letter_head", "select_print_heading", "language", "tc_name", "scan_barcode",
		"utm_source", "utm_campaign", "utm_medium"],
	"Payment Entry": ["project", "cost_center", "party_bank_account", "letter_head", "print_heading"],
	Customer: ["website", "language", "market_segment", "industry", "tax_category", "tax_withholding_category", "account_manager", "default_commission_rate"],
	Item: ["brand", "barcodes", "shelf_life_in_days", "end_of_life", "warranty_period", "weight_per_unit", "weight_uom", "country_of_origin", "customs_tariff_number"],
	Lead: ["website", "annual_revenue", "no_of_employees", "industry", "market_segment", "language", "fax"],
};
hipersign.fm.MODES = ["Quick", "Standard", "Detailed"];

hipersign.fm.mode = (dt) => ((hipersign.info().form_modes || {})[dt]) || "Detailed";
hipersign.fm.remember = (dt, mode) => {
	(frappe.boot.hipersign = frappe.boot.hipersign || {}).form_modes = Object.assign(hipersign.info().form_modes || {}, { [dt]: mode });
	return frappe.xcall("hipersign_trading.api.quick.set_form_mode", { doctype: dt, mode });
};

// ---------------------------------------------------------------- New: open in the user's mode
hipersign.fm.new = function (dt, values) {
	const m = hipersign.fm.mode(dt);
	if (m === "Quick") return hipersign.fm.quick(dt, values || {});
	hipersign.fm.full_form(dt, values || {});
};

hipersign.fm.full_form = function (dt, v) {
	frappe.model.with_doctype(dt, () => {
		const doc = frappe.model.get_new_doc(dt);
		const party = { Quotation: "party_name", "Sales Order": "customer", "Purchase Order": "supplier" }[dt];
		if (party && v.party) doc[party] = v.party;
		if (dt === "Quotation" && v.party) doc.quotation_to = "Customer";
		if (v.po_no && dt === "Sales Order") doc.po_no = v.po_no;
		(v.items || []).filter((r) => r.item_code).forEach((r) => {
			const row = frappe.model.add_child(doc, "items");
			row.item_code = r.item_code;
			row.qty = r.qty;
		});
		frappe.set_route("Form", dt, doc.name);
	});
};

hipersign.fm.choose = function (dt) {
	const cur = hipersign.fm.mode(dt);
	const desc = { Quick: __("Fewest fields — everything else from the defaults"), Standard: __("The essential fields"), Detailed: __("Every field") };
	const d = new frappe.ui.Dialog({
		title: __("New {0}", [__(dt)]),
		fields: [{ fieldtype: "HTML", options: `<div class="hs-fm-choose">${hipersign.fm.MODES.map((m) =>
			`<button class="btn btn-default btn-block hs-fm-pick ${m === cur ? "btn-primary" : ""}" data-mode="${m}" style="text-align:left;margin-bottom:8px;white-space:normal">
				<b>${__(m)}</b>${m === cur ? " · " + __("your default") : ""}<br><span class="small">${desc[m]}</span></button>`).join("")}
			<p class="small text-muted">${__("Your choice is remembered for next time.")}</p></div>` }],
	});
	d.$wrapper.on("click", ".hs-fm-pick", (e) => {
		const m = $(e.currentTarget).data("mode");
		d.hide();
		hipersign.fm.remember(dt, m).then(() => hipersign.fm.new(dt));
	});
	d.show();
};

// list views: the New button opens the user's mode, with a menu for the other two
$(document).on("page-change", () => setTimeout(hipersign.fm.hook_list, 400));
hipersign.fm.hook_list = function () {
	const lv = window.cur_list;
	if (!lv || !lv.doctype || !hipersign.fm.COVERED.includes(lv.doctype) || lv.__hs_fm) return;
	if ((frappe.get_route() || [])[0] !== "List") return;
	if (!lv.page || typeof lv.page.set_primary_action !== "function") {
		// the list is still being built (first page load): try again in a moment
		hipersign.fm._tries = (hipersign.fm._tries || 0) + 1;
		if (hipersign.fm._tries < 20) setTimeout(hipersign.fm.hook_list, 250);
		return;
	}
	hipersign.fm._tries = 0;
	lv.__hs_fm = true;
	const dt = lv.doctype;
	if (!frappe.model.can_create(dt)) return;
	lv.page.set_primary_action(__("New") + ` · ${__(hipersign.fm.mode(dt))}`, () => hipersign.fm.new(dt), "add");
	hipersign.fm.MODES.forEach((m) => lv.page.add_menu_item(__("New — {0}", [__(m)]), () => hipersign.fm.remember(dt, m).then(() => hipersign.fm.new(dt))));
};

// ---------------------------------------------------------------- forms: Standard / Detailed, and the mode switch
hipersign.fm.apply = function (frm) {
	const dt = frm.doctype, m = hipersign.fm.mode(dt);
	(hipersign.fm.OPTIONAL[dt] || []).forEach((f) => { if (frm.fields_dict[f]) frm.toggle_display(f, m === "Detailed"); });
};

hipersign.fm.COVERED.forEach((dt) => frappe.ui.form.on(dt, {
	refresh(frm) {
		hipersign.fm.apply(frm);
		if (frm.doc.docstatus !== 0) return;
		const cur = hipersign.fm.mode(dt);
		hipersign.fm.MODES.forEach((m) => {
			if (m === "Quick" && !hipersign.fm.quick_kinds.includes(dt)) return;
			frm.add_custom_button((m === cur ? "✓ " : "") + __(m), () => {
				hipersign.fm.remember(dt, m).then(() => {
					if (m === "Quick") return hipersign.fm.quick(dt, hipersign.fm.from_form(frm));
					hipersign.fm.apply(frm);
					frm.refresh();
				});
			}, __("Form mode"));
		});
	},
}));

hipersign.fm.from_form = (frm) => ({
	party: frm.doc.party_name || frm.doc.customer || frm.doc.supplier,
	po_no: frm.doc.po_no,
	items: (frm.doc.items || []).filter((r) => r.item_code).map((r) => ({ item_code: r.item_code, item_name: r.item_name, qty: r.qty, rate: r.rate })),
});

// ---------------------------------------------------------------- the Quick dialogs
hipersign.fm.quick_kinds = ["Quotation", "Sales Order", "Purchase Order", "Sales Invoice", "Payment Entry", "Customer", "Item", "Lead"];

hipersign.fm.quick = function (dt, v) {
	if (["Customer", "Item", "Lead"].includes(dt)) return frappe.ui.form.make_quick_entry(dt, null, null, frappe.model.get_new_doc(dt));
	if (dt === "Sales Invoice") return hipersign.fm.quick_invoice();
	if (dt === "Payment Entry") return hipersign.fm.quick_receive(v);
	return hipersign.fm.quick_doc(dt, v);
};

hipersign.fm.parse = function (txt) {
	txt = (txt || "").trim();
	let m = txt.match(/^(\d+(?:\.\d+)?)\s*(?:x|×|pcs|nos|units?)?\s+(.+)$/i);
	if (m) return [parseFloat(m[1]), m[2]];
	m = txt.match(/^(.+?)\s+(?:x|×)?\s*(\d+(?:\.\d+)?)$/i);
	if (m) return [parseFloat(m[2]), m[1]];
	return [null, txt];
};

hipersign.fm.quick_doc = function (dt, v) {
	const buying = dt === "Purchase Order";
	const d = new frappe.ui.Dialog({
		title: __("Quick {0}", [__(dt).toLowerCase()]),
		size: "large",
		fields: [
			{ fieldtype: "Link", fieldname: "party", label: buying ? __("Supplier") : __("Customer"), options: buying ? "Supplier" : "Customer", reqd: 1, default: v.party,
				change: () => { hipersign.fm.reprice(d, dt); hipersign.fm.repeat_btn(d, dt); } },
			...(dt === "Sales Order" ? [{ fieldtype: "Column Break" }, { fieldtype: "Data", fieldname: "po_no", label: __("Customer PO no."), default: v.po_no }] : []),
			{ fieldtype: "Section Break" },
			{ fieldtype: "HTML", fieldname: "finder" },
			{ fieldtype: "Table", fieldname: "items", label: __("Items"), cannot_add_rows: false, in_place_edit: true, data: (v.items || []).map((r) => ({ ...r })),
				fields: [
					{ fieldtype: "Link", fieldname: "item_code", label: __("Item"), options: "Item", in_list_view: 1, reqd: 1, columns: 4,
						get_query: () => ({ filters: buying ? { is_purchase_item: 1, disabled: 0 } : { is_sales_item: 1, disabled: 0 } }) },
					{ fieldtype: "Data", fieldname: "item_name", label: __("Name"), in_list_view: 1, read_only: 1, columns: 3 },
					{ fieldtype: "Float", fieldname: "qty", label: __("Qty"), in_list_view: 1, reqd: 1, columns: 1 },
					{ fieldtype: "Currency", fieldname: "rate", label: __("Price (from the list)"), in_list_view: 1, read_only: 1, columns: 2 },
				] },
			{ fieldtype: "HTML", fieldname: "summary" },
		],
		primary_action_label: dt === "Quotation" ? __("Save") : __("Submit order"),
		primary_action: () => hipersign.fm.quick_save(d, dt, dt === "Quotation" ? "save" : "submit"),
		secondary_action_label: __("Standard / Detailed form"),
		secondary_action: () => { const val = d.get_values(true); d.hide(); hipersign.fm.remember(dt, "Standard").then(() => hipersign.fm.full_form(dt, { party: val.party, po_no: val.po_no, items: val.items })); },
	});
	if (dt === "Quotation") d.add_custom_action(__("Save & send on WhatsApp"), () => hipersign.fm.quick_save(d, dt, "save", true), "btn-success");
	d.fields_dict.finder.$wrapper.html(`<div class="hs-fq-find" style="display:flex;gap:8px"><input class="form-control" placeholder="${__("Quantity and item — e.g. 200 cam — then Enter")}">
		<button class="btn btn-default btn-sm">${__("Add")}</button></div><div class="hs-fq-sugg" style="margin:8px 0;display:flex;flex-wrap:wrap;gap:6px"></div><div class="hs-fq-repeat"></div>`);
	const $in = d.fields_dict.finder.$wrapper.find("input"), $sugg = d.fields_dict.finder.$wrapper.find(".hs-fq-sugg");
	let last = [];
	const search = frappe.utils.debounce(() => {
		const [, t] = hipersign.fm.parse($in.val());
		if ((t || "").length < 2) { $sugg.empty(); last = []; return; }
		frappe.xcall("hipersign_trading.api.quick.find_items", { doctype: dt, txt: t, party: d.get_value("party") }).then((rows) => {
			last = rows || [];
			$sugg.html(last.map((r, i) => `<button class="btn btn-xs btn-default hs-fq-pick" data-i="${i}">${frappe.utils.escape_html(r.item_name)} · ${format_currency(r.rate)}${r.stock != null ? " · " + r.stock + " " + __("in stock") : ""}</button>`).join("")
				|| `<span class="text-muted small">${__("No item matches — use the Standard form to add a new item")}</span>`);
		});
	}, 250);
	const add = (r) => {
		const [q] = hipersign.fm.parse($in.val());
		const items = d.fields_dict.items.df.data;
		const ex = items.find((x) => x.item_code === r.item_code);
		if (ex) ex.qty = flt(ex.qty) + (q || 1); else items.push({ item_code: r.item_code, item_name: r.item_name, qty: q || 1, rate: r.rate });
		d.fields_dict.items.grid.refresh();
		$in.val("").focus(); $sugg.empty(); last = [];
		hipersign.fm.summary(d, dt);
	};
	$in.on("input", search);
	$in.on("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); if (last.length === 1) add(last[0]); else if (last.length) frappe.show_alert(__("Several items match — pick one")); } });
	d.fields_dict.finder.$wrapper.find("button.btn-sm").on("click", () => { if (last.length) add(last[0]); });
	$sugg.on("click", ".hs-fq-pick", (e) => add(last[$(e.currentTarget).data("i")]));
	d.fields_dict.items.grid.wrapper.on("change", () => hipersign.fm.summary(d, dt));
	d.show();
	hipersign.fm.repeat_btn(d, dt);
	hipersign.fm.summary(d, dt);
	setTimeout(() => $in.focus(), 300);
};

hipersign.fm.reprice = function (d, dt) {
	const items = d.fields_dict.items.df.data || [];
	Promise.all(items.map((r) => frappe.xcall("hipersign_trading.api.quick.find_items", { doctype: dt, txt: r.item_code, party: d.get_value("party") })
		.then((x) => { const m = (x || []).find((y) => y.item_code === r.item_code); if (m) r.rate = m.rate; }))).then(() => { d.fields_dict.items.grid.refresh(); hipersign.fm.summary(d, dt); });
};

hipersign.fm.repeat_btn = function (d, dt) {
	const $w = d.fields_dict.finder.$wrapper.find(".hs-fq-repeat").empty();
	const party = d.get_value("party");
	if (dt !== "Sales Order" || !party) return;
	frappe.xcall("hipersign_trading.api.quick.last_order", { customer: party }).then((o) => {
		if (!o) return;
		$(`<button class="btn btn-xs btn-default">${frappe.utils.icon("refresh", "xs")} ${__("Repeat last order — {0} · {1} · {2} lines", [o.name, frappe.datetime.str_to_user(o.date), o.items.length])}</button>`)
			.appendTo($w).on("click", () => {
				d.fields_dict.items.df.data = o.items.map((r) => ({ item_code: r.item_code, item_name: r.item_name, qty: r.qty }));
				hipersign.fm.reprice(d, dt);
				frappe.show_alert(__("Copied {0} lines at today's prices — change the quantities if needed", [o.items.length]));
			});
	});
};

hipersign.fm.summary = function (d, dt) {
	const items = (d.fields_dict.items.df.data || []).filter((r) => r.item_code && flt(r.qty) > 0);
	const net = items.reduce((a, r) => a + flt(r.qty) * flt(r.rate), 0);
	d.fields_dict.summary.$wrapper.html(`<div class="text-right" style="margin-top:6px"><span class="text-muted">${items.length} ${items.length === 1 ? __("line") : __("lines")} · ${__("estimated")}</span>
		<b style="font-size:16px;margin-left:8px">${format_currency(net)}</b> <span class="text-muted small">${__("before tax — final prices, credit, approvals and documents are checked on save")}</span></div>`);
};

hipersign.fm.quick_save = function (d, dt, action, send) {
	const v = d.get_values();
	if (!v) return;
	const items = (d.fields_dict.items.df.data || []).filter((r) => r.item_code && flt(r.qty) > 0).map((r) => ({ item_code: r.item_code, qty: r.qty }));
	d.disable_primary_action();
	frappe.xcall("hipersign_trading.api.quick.quick_create", { doctype: dt, data: { party: v.party, po_no: v.po_no, items }, action })
		.then((r) => {
			d.hide();
			frappe.show_alert({ message: r.message, indicator: r.needs_documents ? "orange" : "green" }, 8);
			if (send) hipersign.send_whatsapp(dt, r.name);
			else frappe.set_route("Form", dt, r.name);
		})
		.catch(() => {}) // the server message is already shown; the dialog stays open to fix it
		.finally(() => d.enable_primary_action());
};

hipersign.fm.quick_invoice = function () {
	frappe.xcall("hipersign_trading.api.quick.to_bill").then((rows) => {
		const d = new frappe.ui.Dialog({ title: __("Quick invoice"), size: "large", fields: [{ fieldtype: "HTML", fieldname: "list" }],
			secondary_action_label: __("Standard / Detailed form"), secondary_action: () => { d.hide(); hipersign.fm.remember("Sales Invoice", "Standard").then(() => frappe.new_doc("Sales Invoice")); } });
		d.fields_dict.list.$wrapper.html(rows.length ? `<p class="text-muted">${__("Delivered and not yet invoiced — one click creates and submits the tax invoice.")}</p>
			<table class="table table-sm">${rows.map((r) => `<tr><td><b>${frappe.utils.escape_html(r.customer_name || r.customer)}</b><div class="small text-muted">${r.name} · ${frappe.datetime.str_to_user(r.date)}</div></td>
			<td class="text-right">${format_currency(r.amount)}</td><td class="text-right"><button class="btn btn-xs btn-primary hs-inv" data-dn="${r.name}">${__("Create invoice")}</button></td></tr>`).join("")}</table>`
			: `<p class="text-muted">${__("Every delivery has been invoiced.")}</p>`);
		d.$wrapper.on("click", ".hs-inv", (e) => {
			const dn = $(e.currentTarget).data("dn");
			$(e.currentTarget).prop("disabled", true);
			frappe.xcall("hipersign_trading.api.quick.quick_invoice", { delivery_note: dn }).then((r) => { frappe.show_alert({ message: r.message, indicator: "green" }); $(e.currentTarget).closest("tr").remove(); }).catch(() => $(e.currentTarget).prop("disabled", false));
		});
		d.show();
	});
};

hipersign.fm.quick_receive = function (v) {
	const d = new frappe.ui.Dialog({
		title: __("Receive payment"),
		fields: [
			{ fieldtype: "Link", fieldname: "customer", label: __("Customer"), options: "Customer", reqd: 1, default: v.party, change: () => preview(true) },
			{ fieldtype: "Currency", fieldname: "amount", label: __("Amount received"), reqd: 1, change: () => preview(false) },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "mode_of_payment", label: __("Method"), options: "Mode of Payment", default: "Wire Transfer" },
			{ fieldtype: "Data", fieldname: "reference_no", label: __("Reference") },
			{ fieldtype: "Section Break" },
			{ fieldtype: "HTML", fieldname: "alloc" },
		],
		primary_action_label: __("Record receipt"),
		primary_action(val) {
			frappe.xcall("hipersign_trading.api.quick.quick_receive", val).then((r) => { d.hide(); frappe.show_alert({ message: r.message, indicator: "green" }, 6); frappe.set_route("Form", "Payment Entry", r.name); }).catch(() => {});
		},
		secondary_action_label: __("Standard / Detailed form"),
		secondary_action: () => { d.hide(); hipersign.fm.remember("Payment Entry", "Standard").then(() => frappe.new_doc("Payment Entry", { payment_type: "Receive", party_type: "Customer", party: d.get_value("customer") })); },
	});
	let invs = [];
	const preview = (reset) => {
		const c = d.get_value("customer");
		if (!c) return d.fields_dict.alloc.$wrapper.empty();
		const show = () => {
			let left = flt(d.get_value("amount"));
			const out = invs.reduce((a, i) => a + flt(i.outstanding_amount), 0);
			const rows = invs.map((i) => { const a = Math.max(0, Math.min(left, flt(i.outstanding_amount))); left -= a;
				return `<tr><td>${i.name}</td><td>${frappe.datetime.str_to_user(i.due_date)}</td><td class="text-right">${format_currency(i.outstanding_amount, i.currency)}</td><td class="text-right"><b>${a ? format_currency(a, i.currency) : "—"}</b></td></tr>`; }).join("");
			d.fields_dict.alloc.$wrapper.html(`<table class="table table-sm"><tr class="text-muted"><td>${__("Invoice")}</td><td>${__("Due")}</td><td class="text-right">${__("Outstanding")}</td><td class="text-right">${__("Applied")}</td></tr>${rows}</table>`
				+ (flt(d.get_value("amount")) > out + 0.005 ? `<p class="text-danger small">${__("More than the customer owes — record the extra as an advance in the Standard form.")}</p>` : ""));
		};
		if (!reset) return show();
		frappe.xcall("hipersign_trading.api.quick.open_invoices", { customer: c }).then((r) => {
			invs = r || [];
			d.set_value("amount", invs.reduce((a, i) => a + flt(i.outstanding_amount), 0)).then(show);
		});
	};
	d.show();
	if (v.party) preview(true);
};
