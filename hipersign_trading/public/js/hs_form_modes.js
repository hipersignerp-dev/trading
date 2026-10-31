// Hipersign ERP v1.3 — form modes: Quick (a small dialog), Standard (the essential fields), Detailed (every field).
frappe.provide("hipersign.fm");

hipersign.fm.COVERED = ["Quotation", "Sales Order", "Purchase Order", "Sales Invoice", "Payment Entry", "Customer", "Item", "Lead",
	// v1.5.6: 26 more forms
	"Supplier", "Supplier Quotation", "Material Request", "Purchase Receipt", "Purchase Invoice", "Landed Cost Voucher",
	"Import Shipment", "Export Shipment", "Letter of Credit", "Bank Guarantee",
	"Delivery Note", "Stock Entry", "Stock Reconciliation", "Pick List", "Delivery Trip", "Warranty Claim", "Warehouse",
	"Journal Entry", "Post Dated Cheque", "Credit Limit Request", "Tax Return",
	"Employee", "Leave Application", "Expense Claim", "Asset", "Company Document",
	// quick cards only
	"Address", "Contact", "Customer Group", "Payment Terms Template", "Bank Account", "Driver"];
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
	// v1.5.6 — rarely used fields; a mandatory field or one that already has a value is never hidden
	Supplier: ["alias", "tax_category", "tax_withholding_category", "tax_withholding_group", "is_transporter", "language", "website", "is_frozen", "on_hold", "hold_type",
		"release_date", "allow_purchase_invoice_creation_without_purchase_order", "allow_purchase_invoice_creation_without_purchase_receipt", "gender", "default_bank_account"],
	"Supplier Quotation": ["buying_price_list", "plc_conversion_rate", "ignore_pricing_rule", "tax_category", "shipping_rule", "apply_discount_on", "disable_rounded_total",
		"select_print_heading", "group_same_items", "letter_head", "is_subcontracted", "named_place", "shipping_address", "billing_address", "cost_center", "project", "tc_name"],
	"Material Request": ["customer", "scan_barcode", "letter_head", "select_print_heading", "tc_name", "terms", "buying_price_list"],
	"Purchase Receipt": ["set_posting_time", "supplier_address", "contact_person", "shipping_address", "buying_price_list", "plc_conversion_rate", "ignore_pricing_rule",
		"rejected_warehouse", "supplier_warehouse", "tax_category", "shipping_rule", "apply_discount_on", "disable_rounded_total", "tc_name", "terms", "project", "letter_head",
		"select_print_heading", "group_same_items", "instructions", "transporter_name", "lr_no", "lr_date", "scan_barcode", "billing_address", "apply_putaway_rule",
		"set_from_warehouse", "cost_center", "named_place", "dispatch_address"],
	"Purchase Invoice": ["apply_tds", "cost_center", "set_posting_time", "on_hold", "release_date", "hold_comment", "supplier_address", "contact_person", "shipping_address",
		"buying_price_list", "plc_conversion_rate", "ignore_pricing_rule", "rejected_warehouse", "scan_barcode", "tax_category", "shipping_rule", "apply_discount_on",
		"disable_rounded_total", "write_off_amount", "write_off_account", "write_off_cost_center", "tc_name", "terms", "letter_head", "group_same_items", "select_print_heading",
		"is_opening", "from_date", "to_date"],
	"Landed Cost Voucher": [],
	"Import Shipment": ["shipping_line", "insurance_policy", "vessel_flight"],
	"Export Shipment": ["named_place", "coo_no", "re_export_of", "duty_refund_status"],
	"Letter of Credit": ["tolerance_pct", "charges", "trust_receipt", "tr_amount", "tr_start", "tr_days", "tr_rate", "tr_repaid_on"],
	"Bank Guarantee": ["fixed_deposit_number", "margin_money", "charges", "more_information", "project"],
	"Delivery Note": ["set_posting_time", "issue_credit_note", "po_date", "company_address", "plc_conversion_rate", "ignore_pricing_rule", "scan_barcode", "tax_category",
		"shipping_rule", "apply_discount_on", "tc_name", "terms", "lr_no", "lr_date", "project", "territory", "letter_head", "select_print_heading", "print_without_amount",
		"group_same_items", "sales_partner", "commission_rate", "total_commission", "set_target_warehouse", "disable_rounded_total", "dispatch_address_name", "cost_center",
		"named_place", "utm_medium", "utm_content", "utm_source", "utm_campaign", "company_contact_person"],
	"Stock Entry": ["work_order", "inspection_required", "from_bom", "bom_no", "fg_completed_qty", "use_multi_level_bom", "source_warehouse_address", "target_warehouse_address",
		"scan_barcode", "select_print_heading", "letter_head", "is_opening", "project", "add_to_transit", "apply_putaway_rule", "process_loss_qty", "process_loss_percentage", "cost_center"],
	"Stock Reconciliation": ["set_posting_time", "cost_center", "scan_barcode", "scan_mode"],
	"Pick List": ["work_order", "material_request", "scan_barcode", "scan_mode", "prompt_qty", "consider_rejected_warehouses", "ignore_pricing_rule", "group_same_items"],
	"Delivery Trip": ["calculate_arrival_time", "optimize_route", "driver_address"],
	"Warranty Claim": ["amc_expiry_date", "service_address", "from_company", "complaint_raised_by"],
	Warehouse: ["account", "phone_no", "address_line_2", "pin", "default_in_transit_warehouse", "is_rejected_warehouse", "customer", "warehouse_type"],
	"Journal Entry": ["multi_currency", "write_off_based_on", "write_off_amount", "letter_head", "select_print_heading", "is_opening", "from_template", "tax_withholding_category",
		"apply_tds", "periodic_entry_difference_account", "for_all_stock_asset_accounts", "stock_asset_account", "tax_withholding_group", "ignore_tax_withholding_threshold",
		"override_tax_withholding_entries"],
	"Post Dated Cheque": ["reference_doctype", "reference_name"],
	"Credit Limit Request": [],
	"Tax Return": ["ct_threshold"],
	Employee: ["salutation", "middle_name", "employee_number", "emergency_phone_number", "person_to_be_contacted", "relation", "create_user_permission", "scheduled_confirmation_date",
		"final_confirmation_date", "contract_end_date", "notice_number_of_days", "date_of_retirement", "branch", "prefered_contact_email", "unsubscribed",
		"permanent_accommodation_type", "permanent_address", "current_accommodation_type", "bio", "date_of_issue", "place_of_issue", "marital_status", "blood_group",
		"family_background", "health_details", "attendance_device_id", "ctc"],
	"Leave Application": ["follow_via_email", "letter_head", "color", "salary_slip"],
	"Expense Claim": ["project", "task", "clearance_date", "cost_center", "delivery_trip", "gain_loss_account"],
	Asset: ["asset_owner", "asset_owner_company", "customer", "cost_center", "department", "policy_number", "insurer", "insured_value", "comprehensive_insurance",
		"opening_accumulated_depreciation", "opening_number_of_booked_depreciations", "asset_quantity"],
	"Company Document": ["renewal_cost"],
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
	// v1.7.0: quotations, orders and the masters open the prototype's create modal in every mode (it has the mode switch)
	if (hipersign.cm && hipersign.cm.has(dt) && !(values && values.__full)) return hipersign.cm.new(dt, values || {});
	// v1.7.1: a delivery, receipt or invoice starts from its order (the prototype's flow modals)
	if (hipersign.cm && hipersign.cm.PICK && hipersign.cm.PICK[dt] && !(values && (values.__full || Object.keys(values).length))) return hipersign.cm.pick(dt, {});
	if (m === "Quick") return hipersign.fm.quick(dt, values || {});
	hipersign.fm.full_form(dt, values || {});
};

hipersign.fm.full_form = function (dt, v) {
	if (hipersign.qc && hipersign.qc.has(dt)) return hipersign.qc.full_form(dt, v || {});
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
	(hipersign.fm.OPTIONAL[dt] || []).forEach((f) => {
		const fd = frm.fields_dict[f];
		if (!fd) return;
		// never hide a mandatory field, or one that already holds a value (switching mode never hides typed data)
		const v = frm.doc[f], d = fd.df.default;
		const filled = v !== undefined && v !== null && v !== "" && v !== 0 && !(Array.isArray(v) && !v.length) && (d === undefined || d === null || String(v) !== String(d));
		const reqd = fd.df.reqd || frappe.meta.get_docfield(dt, f, frm.doc.name)?.reqd;
		frm.toggle_display(f, m === "Detailed" || reqd || filled);
	});
};

hipersign.fm.COVERED.forEach((dt) => frappe.ui.form.on(dt, {
	refresh(frm) {
		hipersign.fm.apply(frm);
		if (frm.doc.docstatus !== 0) return;
		const cur = hipersign.fm.mode(dt);
		hipersign.fm.MODES.forEach((m) => {
			if (m === "Quick" && !hipersign.fm.quick_kinds.includes(dt)) return;
			// a saved master is edited on its form; the card only makes new records
			if (m === "Quick" && hipersign.qc && hipersign.qc.has(dt) && !frm.is_new()) return;
			frm.add_custom_button((m === cur ? "✓ " : "") + __(m), () => {
				hipersign.fm.remember(dt, m).then(() => {
					if (m === "Quick") {
						const v = hipersign.qc && hipersign.qc.has(dt) ? hipersign.qc.from_doc(dt, frm.doc) : hipersign.fm.from_form(frm);
						return hipersign.fm.quick(dt, v);
					}
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
hipersign.fm.quick_kinds = ["Quotation", "Sales Order", "Purchase Order", "Sales Invoice", "Payment Entry", "Customer", "Item", "Lead",
	"Supplier", "Warehouse", "Employee", "Asset", "Address", "Contact", "Customer Group", "Payment Terms Template", "Bank Account", "Driver"];

hipersign.fm.quick = function (dt, v) {
	if (hipersign.qc && hipersign.qc.has(dt)) return hipersign.qc.open(dt, { values: v || {} });
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
			secondary_action_label: __("Standard / Detailed form"), secondary_action: () => { d.hide(); hipersign.fm.remember("Sales Invoice", "Standard").then(() => hipersign.create.new_doc("Sales Invoice", {})); } });
		d.fields_dict.list.$wrapper.html(rows.length ? `<p class="text-muted">${__("Delivered and not yet invoiced — one click creates and submits the tax invoice.")}</p>
			<table class="table table-sm">${rows.map((r) => `<tr><td><b>${frappe.utils.escape_html(r.customer_name || r.customer)}</b><div class="small text-muted">${r.name} · ${frappe.datetime.str_to_user(r.date)}</div></td>
			<td class="text-right">${format_currency(r.amount)}</td><td class="text-right"><button class="btn btn-xs btn-primary hs-inv" data-dn="${r.name}">${__("Create invoice")}</button></td></tr>`).join("")}</table>`
			: `<p class="text-muted">${__("Every delivery has been invoiced.")}</p>`);
		d.$wrapper.on("click", ".hs-inv", (e) => {
			const dn = $(e.currentTarget).data("dn");
			$(e.currentTarget).prop("disabled", true);
			frappe.xcall("hipersign_trading.api.quick.quick_invoice", { delivery_note: dn }).then((r) => {
				frappe.show_alert({ message: r.message, indicator: "green" });
				// v1.5.6: the list is read again, so an invoiced delivery never stays on it
				d.hide();
				hipersign.fm.quick_invoice();
			}).catch(() => $(e.currentTarget).prop("disabled", false));
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
			left -= invs.filter((i) => flt(i.outstanding_amount) < 0).reduce((a, i) => a + flt(i.outstanding_amount), 0);
			const rows = invs.map((i) => { const neg = flt(i.outstanding_amount) < 0; const a = neg ? flt(i.outstanding_amount) : Math.max(0, Math.min(left, flt(i.outstanding_amount))); if (!neg) left -= a;
				return `<tr><td>${i.name}${neg ? " · " + __("credit note") : ""}</td><td>${frappe.datetime.str_to_user(i.due_date)}</td><td class="text-right">${format_currency(i.outstanding_amount, i.currency)}</td><td class="text-right"><b>${a ? format_currency(a, i.currency) : "—"}</b></td></tr>`; }).join("");
			d.fields_dict.alloc.$wrapper.html(`<table class="table table-sm"><tr class="text-muted"><td>${__("Invoice")}</td><td>${__("Due")}</td><td class="text-right">${__("Outstanding")}</td><td class="text-right">${__("Applied")}</td></tr>${rows}</table>`
				+ (flt(d.get_value("amount")) > out + 0.005 ? `<p class="text-danger small">${__("More than the customer owes — record the extra as an advance in the Standard form.")}</p>` : ""));
		};
		if (!reset) return show();
		frappe.xcall("hipersign_trading.api.quick.open_invoices", { customer: c }).then((r) => {
			invs = r || [];
			d.set_value("amount", Math.max(0, invs.reduce((a, i) => a + flt(i.outstanding_amount), 0))).then(show);
		});
	};
	d.show();
	if (v.party) preview(true);
};
