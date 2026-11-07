// Hipersign ERP v1.7.0 — the prototype's create forms. One modal for every "New …": title and subtitle, the
// Quick / Standard / Detailed switch in the header, two-column fields, and for quotations, orders and invoices the
// line table (item · qty · rate · disc · available · margin · net) with totals and the credit check inside the modal.
// Server: hipersign_trading.api.create (transactions) and api.quick_cards.create (masters).
frappe.provide("hipersign.cm");

(function () {
	const C = hipersign.cm;
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const MODES = ["Quick", "Standard", "Detailed"];
	const KIND_DT = { quotation: "Quotation", sales_order: "Sales Order", purchase_order: "Purchase Order" };
	const DT_KIND = { Quotation: "quotation", "Sales Order": "sales_order", "Purchase Order": "purchase_order" };
	const today = () => frappe.datetime.get_today();
	const plus = (n) => frappe.datetime.add_days(today(), n);
	// a choice list read with the user's permissions: L(doctype, filters, {query}) (api.create.link_options)
	const L = (dt, filters, extra) => Object.assign({ dt, filters: filters || {} }, extra || {});
	// v1.7.3: Select options read from the doctype (opts: "@meta"), so edited lists show
	C.meta_opts = (dt, f) => ((frappe.meta.get_docfield(dt, f) || {}).options || "").split("\n").filter((x) => x).map((x) => [x, __(x)]);
	const with_meta = (dt) => new Promise((r) => frappe.model.with_doctype(dt, r));
	const co = () => frappe.defaults.get_user_default("Company");

	// ------------------------------------------------------------ transaction forms
	// m: q = Quick and up, s = Standard and up, d = Detailed only. w: 1 = half, 2 = full row, 4 = quarter
	C.FORMS = {
		quotation: {
			title: __("New quotation"), sub: __("Stock items, services and custom lines · rates follow the customer group"),
			party: { f: "party", label: __("Customer"), src: "customers", add: __("+ Add new prospect / client…"), lead: 1 },
			fields: [
				{ f: "valid_till", label: __("Valid till"), t: "date", m: "q", def: () => plus(14) },
				{ f: "price_list", label: __("Price list"), t: "select", src: "price_lists", m: "s", w: 2, hint: __("Customer’s list") },
				{ f: "hs_subject", label: __("Subject / project"), m: "s", w: 2, ph: __("e.g. CCTV & access control — Al Barsha villa") },
				{ f: "contact_person", label: __("Contact person"), t: "select", src: "@contacts", m: "s" },
				{ f: "payment_terms", label: __("Payment terms"), t: "select", src: "terms", m: "s" },
				{ f: "hs_delivery_period", label: __("Delivery period"), t: "select", src: "delivery_periods", m: "s" },
				{ f: "hs_warranty_months", label: __("Warranty (months)"), t: "select", src: "warranty", m: "s", def: "12" },
				{ f: "sales_person", label: __("Sales person"), t: "select", src: "sales_people", m: "s" },
				{ f: "hs_enquiry_ref", label: __("Customer's enquiry / RFQ ref."), m: "d", ph: __("Their reference — printed on the quotation") },
				{ f: "hs_enquiry_date", label: __("Enquiry date"), t: "date", m: "d" },
				{ f: "currency", label: __("Quote currency"), t: "select", src: "currencies", m: "d", hint: __("Rates are entered in the price list's currency; the print shows both") },
				{ f: "incoterm", label: __("Incoterm"), t: "select", src: "incoterms", m: "d", blank: __("— local delivery —") },
				// v1.7.3: Detailed — the rest of the quotation's own fields
				{ f: "transaction_date", label: __("Quotation date"), t: "date", m: "d", def: today },
				{ f: "named_place", label: __("Named place (incoterm)"), m: "d" },
				{ f: "customer_address", label: __("Billing address"), t: "select", src: "@addresses", m: "d" },
				{ f: "shipping_address_name", label: __("Shipping address"), t: "select", src: "@addresses", m: "d" },
				{ f: "taxes_and_charges", label: __("VAT template"), t: "select", src: L("Sales Taxes and Charges Template"), m: "d", blank: __("— company default —") },
				{ f: "tax_category", label: __("Tax category"), t: "select", src: L("Tax Category"), m: "d" },
				{ f: "shipping_rule", label: __("Shipping rule"), t: "select", src: L("Shipping Rule"), m: "d" },
				{ f: "apply_discount_on", label: __("Extra discount on"), t: "select", opts: "@meta", m: "d" },
				{ f: "additional_discount_percentage", label: __("Extra discount %"), t: "number", m: "d" },
				{ f: "referral_sales_partner", label: __("Referral sales partner"), t: "select", src: L("Sales Partner"), m: "d" },
				{ f: "territory", label: __("Territory"), t: "select", src: L("Territory", { is_group: 0 }), m: "d" },
				{ f: "utm_source", label: __("Source"), t: "select", src: L("UTM Source"), m: "d" },
				{ f: "utm_campaign", label: __("Campaign"), t: "select", src: L("UTM Campaign"), m: "d" },
				{ f: "tc_name", label: __("Terms template"), t: "select", src: L("Terms and Conditions"), m: "d" },
				{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
				{ f: "select_print_heading", label: __("Print heading"), t: "select", src: L("Print Heading"), m: "d" },
				{ f: "group_same_items", label: __("Group the same items on the print"), t: "check", m: "d" },
				{ f: "ignore_pricing_rule", label: __("Ignore pricing rules"), t: "check", m: "d" },
			],
			prospect: [
				{ f: "new_party", label: __("Company / client name"), req: 1, w: 2 },
				{ f: "record_as", label: __("Record as"), t: "select", opts: [["Lead", __("Prospect — no orders yet")], ["Customer", __("Customer — ready to order")]] },
				{ f: "new_group", label: __("Customer group"), t: "select", src: "groups", show: (v) => v.record_as === "Customer" },
				{ f: "new_contact", label: __("Contact person"), req: 1 },
				{ f: "new_mobile", label: __("Mobile / WhatsApp"), t: "tel", req: 1, ph: "+971 5x xxx xxxx" },
				{ f: "new_email", label: __("Email"), t: "email" },
				{ f: "new_emirate", label: __("Emirate / city"), t: "select", src: "emirates", def: "Dubai" },
				{ f: "new_trn", label: __("TRN") },
				{ f: "new_source", label: __("Lead source"), t: "select", src: "sources" },
			],
			lines: { avail: 0, margin: 0 }, text: { f: "terms_text", label: __("Terms & notes (printed)"), m: "d" },
			actions: [{ label: __("Save"), action: "save", primary: 1 }, { label: __("Save & send on WhatsApp"), action: "save", send: 1 }],
		},
		sales_order: {
			title: __("New sales order"), sub: __("Pricing, credit limit and margin checks run on submit"),
			party: { f: "party", label: __("Customer"), src: "customers", add: __("+ Add new customer…"), master: "Customer" },
			fields: [
				{ f: "po_no", label: __("Customer PO ref."), m: "q" },
				{ f: "price_list", label: __("Price list"), t: "select", src: "price_lists", m: "s", w: 2, hint: __("Customer’s list") },
				{ f: "shipping_address", label: __("Deliver to"), t: "select", src: "@addresses", m: "s", add: __("+ Add new delivery address…"), addDt: "Address" },
				{ f: "delivery_date", label: __("Delivery date"), t: "date", m: "q", def: () => plus(3) },
				{ f: "po_date", label: __("Customer's PO date"), t: "date", m: "d", w: 4, def: today },
				{ f: "contact_person", label: __("Contact person"), t: "select", src: "@contacts", m: "s", w: 4 },
				{ f: "billing_address", label: __("Billing address"), t: "select", src: "@addresses", m: "d", w: 4 },
				{ f: "payment_terms", label: __("Payment terms"), t: "select", src: "terms", m: "s", w: 4 },
				{ f: "sales_person", label: __("Sales person"), t: "select", src: "sales_people", m: "s", w: 4 },
				{ f: "set_warehouse", label: __("Source warehouse"), t: "select", src: "warehouses", m: "d", w: 4, blank: __("Any — choose at delivery") },
				{ f: "remarks", label: __("Remarks"), m: "s", w: 2, ph: __("Internal or printed note") },
				// v1.7.3: Detailed — the rest of the order's own fields
				{ f: "transaction_date", label: __("Order date"), t: "date", m: "d", def: today },
				{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
				{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
				{ f: "incoterm", label: __("Incoterm"), t: "select", src: "incoterms", m: "d", blank: "—" },
				{ f: "named_place", label: __("Named place (incoterm)"), m: "d" },
				{ f: "hs_payment_method", label: __("Payment method"), t: "select", opts: "@meta", m: "d" },
				{ f: "hs_shipment_mode", label: __("Shipment mode"), t: "select", opts: "@meta", m: "d" },
				{ f: "taxes_and_charges", label: __("VAT template"), t: "select", src: L("Sales Taxes and Charges Template"), m: "d", blank: __("— company default —") },
				{ f: "tax_category", label: __("Tax category"), t: "select", src: L("Tax Category"), m: "d" },
				{ f: "vat_emirate", label: __("VAT emirate"), t: "select", opts: "@meta", m: "d" },
				{ f: "shipping_rule", label: __("Shipping rule"), t: "select", src: L("Shipping Rule"), m: "d" },
				{ f: "apply_discount_on", label: __("Extra discount on"), t: "select", opts: "@meta", m: "d" },
				{ f: "additional_discount_percentage", label: __("Extra discount %"), t: "number", m: "d" },
				{ f: "sales_partner", label: __("Sales partner"), t: "select", src: L("Sales Partner"), m: "d" },
				{ f: "territory", label: __("Territory"), t: "select", src: L("Territory", { is_group: 0 }), m: "d" },
				{ f: "utm_source", label: __("Source"), t: "select", src: L("UTM Source"), m: "d" },
				{ f: "utm_campaign", label: __("Campaign"), t: "select", src: L("UTM Campaign"), m: "d" },
				{ f: "tc_name", label: __("Terms template"), t: "select", src: L("Terms and Conditions"), m: "d" },
				{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
				{ f: "select_print_heading", label: __("Print heading"), t: "select", src: L("Print Heading"), m: "d" },
				{ f: "reserve_stock", label: __("Reserve stock for this order"), t: "check", m: "d" },
				{ f: "skip_delivery_note", label: __("No delivery note (services only)"), t: "check", m: "d" },
				{ f: "group_same_items", label: __("Group the same items on the print"), t: "check", m: "d" },
				{ f: "ignore_pricing_rule", label: __("Ignore pricing rules"), t: "check", m: "d" },
			],
			lines: { avail: 1, margin: 1 }, credit: 1,
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit"), action: "submit", primary: 1 }],
		},
		purchase_order: {
			title: __("New purchase order"), sub: __("In the supplier’s currency · approved by the Purchase Manager (and Finance above the limit)"),
			party: { f: "party", label: __("Supplier"), src: "suppliers", add: __("+ Add new supplier…"), master: "Supplier" },
			fields: [
				{ f: "currency", label: __("Currency"), t: "select", src: "currencies", m: "q" },
				{ f: "incoterm", label: __("Incoterm"), t: "select", src: "incoterms", m: "s", blank: "—" },
				{ f: "transaction_date", label: __("Order date"), t: "date", m: "d", def: today },
				{ f: "schedule_date", label: __("Expected at warehouse"), t: "date", m: "q", def: () => plus(30) },
				{ f: "order_confirmation_no", label: __("Supplier quotation ref."), m: "d" },
				{ f: "contact_person", label: __("Supplier contact"), t: "select", src: "@contacts", m: "s" },
				{ f: "set_warehouse", label: __("Ship to"), t: "select", src: "warehouses", m: "s" },
				{ f: "payment_terms", label: __("Payment terms"), t: "select", src: "terms", m: "s" },
				{ f: "hs_shipment_mode", label: __("Shipment mode"), t: "select", src: "modes", m: "s", blank: "—" },
				{ f: "hs_port_of_loading", label: __("Port of loading"), m: "d" },
				{ f: "hs_port_of_discharge", label: __("Port of discharge"), m: "d", ph: "Jebel Ali Port" },
				{ f: "cost_center", label: __("Cost centre"), t: "select", src: "cost_centers", m: "d", blank: "—" },
				// v1.7.3: Detailed — the rest of the order's own fields
				{ f: "order_confirmation_date", label: __("Supplier quotation date"), t: "date", m: "d" },
				{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
				{ f: "named_place", label: __("Named place (incoterm)"), m: "d" },
				{ f: "supplier_address", label: __("Supplier address"), t: "select", src: "@addresses", m: "d" },
				{ f: "taxes_and_charges", label: __("VAT template"), t: "select", src: L("Purchase Taxes and Charges Template"), m: "d", blank: __("— company default —") },
				{ f: "tax_category", label: __("Tax category"), t: "select", src: L("Tax Category"), m: "d" },
				{ f: "reverse_charge", label: __("Reverse charge"), t: "select", opts: "@meta", m: "d" },
				{ f: "shipping_rule", label: __("Shipping rule"), t: "select", src: L("Shipping Rule"), m: "d" },
				{ f: "apply_discount_on", label: __("Extra discount on"), t: "select", opts: "@meta", m: "d" },
				{ f: "additional_discount_percentage", label: __("Extra discount %"), t: "number", m: "d" },
				{ f: "tc_name", label: __("Terms template"), t: "select", src: L("Terms and Conditions"), m: "d" },
				{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
				{ f: "select_print_heading", label: __("Print heading"), t: "select", src: L("Print Heading"), m: "d" },
				{ f: "group_same_items", label: __("Group the same items on the print"), t: "check", m: "d" },
				{ f: "ignore_pricing_rule", label: __("Ignore pricing rules"), t: "check", m: "d" },
				{ f: "terms", label: __("Terms (printed)"), t: "textarea", m: "d", w: 2 },
			],
			lines: { avail: 1, margin: 0, buying: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit for approval"), action: "submit", primary: 1 }],
		},
	};

	C.has = (dt) => !!DT_KIND[dt] || !!(C.DOCS && C.DOCS[dt]) || (hipersign.qc && hipersign.qc.has(dt));
	// v1.7.3: every doctype whose "New" opens a window here (a create window, a card, or "pick the source document")
	C.covers = (dt) => C.has(dt) || !!(C.PICK && C.PICK[dt]);

	// ------------------------------------------------------------ the shell (overlay, header, body, footer)
	C.shell = function ({ title, sub, mode, modes, wide, onMode, onClose }) {
		const $ov = $(`<div class="hsc-ov"><div class="hsc-modal ${wide ? "hsc-wide" : ""}" role="dialog" aria-modal="true">
			<div class="hsc-head"><div class="hsc-ht"><h3>${esc(title)}</h3>${sub ? `<p>${esc(sub)}</p>` : ""}
			${modes ? `<div class="hsc-seg">${MODES.map((m) => `<button type="button" data-m="${m}" class="${m === mode ? "on" : ""}">${__(m)}</button>`).join("")}</div>` : ""}</div>
			<button type="button" class="hsc-x" aria-label="${__("Close")}">${frappe.utils.icon("close", "sm")}</button></div>
			<div class="hsc-body"></div><div class="hsc-foot"><div class="hsc-fl"></div><div class="hsc-fr"></div></div></div></div>`).appendTo("body");
		const close = () => { $ov.remove(); $(document).off("keydown.hsc"); onClose && onClose(); };
		$ov.on("click", ".hsc-x", close);
		$ov.on("mousedown", (e) => { if (e.target === $ov[0]) $ov.data("down", 1); });
		$ov.on("mouseup", (e) => { if (e.target === $ov[0] && $ov.data("down")) close(); $ov.data("down", 0); });
		$(document).on("keydown.hsc", (e) => { if (e.key === "Escape" && !$(".modal.show").length) close(); });
		$ov.on("click", ".hsc-seg button", function () { onMode && onMode($(this).data("m")); });
		setTimeout(() => $ov.addClass("show"), 10);
		return { $ov, $body: $ov.find(".hsc-body"), $fl: $ov.find(".hsc-fl"), $fr: $ov.find(".hsc-fr"), close,
			setMode: (m) => $ov.find(".hsc-seg button").removeClass("on").filter(`[data-m="${m}"]`).addClass("on") };
	};

	const optHtml = (list, val, blank) => (blank !== undefined ? `<option value="">${esc(blank)}</option>` : "")
		+ (list || []).map((o) => { const v = typeof o === "object" ? (Array.isArray(o) ? o[0] : o.name) : o; const l = typeof o === "object" ? (Array.isArray(o) ? o[1] : (o.label || o.name)) : o;
			return `<option value="${esc(v)}" ${String(v) === String(val ?? "") ? "selected" : ""}>${esc(l)}</option>`; }).join("");

	C.field = function (df, val, opts) {
		const t = df.t || "text", id = "hsc-" + df.f;
		const label = `<label for="${id}">${esc(df.label)}${df.req ? " *" : ""}</label>`;
		// v1.7.3: a value shown, not typed (the customer's current credit limit)
		if (df.ro) return `<div class="hsc-f hsc-w${df.w || 1}" data-wrap="${df.f}">${label}<input id="${id}" readonly class="hsc-ro" data-ro="${df.f}" value="${esc(df.fmt ? df.fmt(val) : val ?? "")}">${df.hint ? `<small class="hsc-hint">${esc(df.hint)}</small>` : ""}</div>`;
		let input;
		if (t === "select") {
			const list = df.list || df.opts || [];
			input = `<select id="${id}" data-f="${df.f}">${optHtml(df.add ? [...list, ["__add__", df.add]] : list, val, df.noblank ? undefined : df.blank !== undefined ? df.blank : (df.req ? undefined : "—"))}</select>`;
		} else if (t === "textarea") input = `<textarea id="${id}" data-f="${df.f}" rows="${df.rows || 3}" placeholder="${esc(df.ph || "")}">${esc(val || "")}</textarea>`;
		else if (t === "check") return `<div class="hsc-f hsc-w${df.w || 1} hsc-chk"><label><input type="checkbox" data-f="${df.f}" ${val ? "checked" : ""}> ${esc(df.label)}</label>${df.hint ? `<small>${esc(df.hint)}</small>` : ""}</div>`;
		else input = `<input id="${id}" data-f="${df.f}" type="${t === "number" || t === "currency" ? "number" : t}" ${t === "currency" ? 'step="0.01"' : ""} value="${esc(val ?? "")}" placeholder="${esc(df.ph || "")}">`;
		return `<div class="hsc-f hsc-w${df.w || 1}" data-wrap="${df.f}">${label}${input}${df.hint ? `<small class="hsc-hint" data-hint="${df.f}">${esc(df.hint)}</small>` : ""}</div>`;
	};

	const visible = (df, mode) => (df.m || "s") === "q" || mode !== "Quick" && ((df.m || "s") === "s" || mode === "Detailed");

	// ------------------------------------------------------------ transaction forms
	C.open = function (kind, preset) {
		const spec = C.FORMS[kind];
		const dt = KIND_DT[kind];
		preset = preset || {};
		let mode = (hipersign.fm && hipersign.fm.mode(dt)) || "Standard";
		const st = { v: Object.assign({}, preset), lines: [], o: null, p: {}, rates: {}, prospect: false, L: {} };
		// v1.8.0: a line may carry its source (the material request line, warehouse and project of "Create PO")
		(preset.items || []).forEach((r) => st.lines.push(Object.assign({}, r, { item_code: r.item_code, qty: r.qty, rate: r.rate, discount: r.discount })));
		delete st.v.items;
		while (st.lines.length < 3) st.lines.push({});
		spec.fields.forEach((df) => { if (st.v[df.f] === undefined && df.def !== undefined) st.v[df.f] = typeof df.def === "function" ? df.def() : df.def; });
		const sh = C.shell({ title: kind === "sales_order" && +preset.hs_is_export ? __("New export order") : spec.title, sub: kind === "sales_order" && +preset.hs_is_export ? __("Foreign customer, currency and incoterm — zero-rated, export shipment follows") : spec.sub, mode, modes: 1, wide: 1,
			onMode: (m) => { read(); mode = m; sh.setMode(m); hipersign.fm && hipersign.fm.remember(dt, m); draw(); } });
		const att = C.attach(sh, dt);
		sh.$body.html(`<div class="hsc-loading">${__("Loading…")}</div>`);

		const read = () => {
			sh.$body.find("[data-f]").each(function () { const f = $(this).data("f"); st.v[f] = this.type === "checkbox" ? (this.checked ? 1 : 0) : $(this).val(); });
			sh.$body.find(".hsc-line").each(function () {
				const i = +$(this).data("i"), L = st.lines[i]; if (!L) return;
				L.item_code = $(this).find(".l-it").val(); L.qty = $(this).find(".l-q").val(); L.rate = $(this).find(".l-r").val(); L.discount = $(this).find(".l-d").val();
			});
		};
		// v1.7.3: L(…) lists (st.L), "@meta" Select options and the party's "@contacts" / "@addresses"
		const src = (df) => df.opts === "@meta" ? C.meta_opts(dt, df.f) : df.opts && !df.src ? df.opts : typeof df.src === "object" ? (st.L[JSON.stringify(df.src)] || [])
			: (df.src || "").startsWith("@") ? (st.p[df.src.slice(1)] || []) : (st.o[df.src] || []);

		const draw = () => {
			const P = spec.party;
			const partyList = [...(st.o[P.src] || []), ...(P.lead ? (st.o.leads || []).map((l) => ({ name: l.name, label: `${l.label} · ${__("prospect")}` })) : [])];
			let h = `<div class="hsc-grid">`;
			h += C.field({ f: P.f, label: P.label, t: "select", list: partyList, add: P.add, blank: undefined, req: 1 }, st.prospect ? "__add__" : st.v.party);
			if (st.prospect) {
				h += C.field(spec.fields[0], st.v[spec.fields[0].f]);
				h += `</div><div class="hsc-box"><div class="hsc-grid">` + spec.prospect.filter((df) => !df.show || df.show(st.v)).map((df) => C.field(Object.assign({}, df, { list: df.src ? st.o[df.src] : df.opts }), st.v[df.f] ?? (df.def || ""))).join("") + `</div></div><div class="hsc-grid">`;
				spec.fields.slice(1).filter((df) => visible(df, mode) && !(typeof df.src === "string" && df.src.startsWith("@"))).forEach((df) => { h += C.field(Object.assign({}, df, { list: src(df) }), st.v[df.f]); });
			} else {
				spec.fields.filter((df) => visible(df, mode)).forEach((df) => { h += C.field(Object.assign({}, df, { list: src(df) }), st.v[df.f]); });
			}
			h += `</div>`;
			h += linesHtml();
			if (spec.text && visible(spec.text, mode)) h += `<div class="hsc-grid">${C.field(Object.assign({ t: "textarea", w: 2 }, spec.text), st.v[spec.text.f])}</div>`;
			h += `<div class="hsc-totals"></div><div class="hsc-msg"></div>`;
			sh.$body.html(h);
			if (st.p.group_hint) sh.$body.find(`[data-wrap="party"]`).append(`<small class="hsc-hint">${esc(st.p.group_hint)}</small>`);
			totals();
		};

		const linesHtml = () => {
			const L = spec.lines, items = st.o.items || [], ccy = st.p.currency || st.o.currency;
			return `<div class="hsc-lines"><table><thead><tr><th class="c-it">${spec.lines.buying ? __("Item") : __("Item, service or custom line")}</th><th class="c-n">${__("Qty")}</th>
				<th class="c-n">${L.buying ? __("Price ({0})", [ccy]) : __("Rate ({0})", [ccy])}</th>${L.buying ? "" : `<th class="c-n">${__("Disc %")}</th>`}
				${L.avail ? `<th class="c-n">${__("Available")}</th>` : ""}${L.margin ? `<th class="c-n">${__("Margin")}</th>` : ""}<th class="c-n">${__("Net ({0})", [ccy])}</th><th></th></tr></thead><tbody>
				${st.lines.map((r, i) => `<tr class="hsc-line" data-i="${i}"><td><select class="l-it">${optHtml(items, r.item_code, __("— select item or service —"))}</select></td>
				<td><input class="l-q" type="number" min="0" step="any" value="${esc(r.qty ?? "")}"></td><td><input class="l-r" type="number" step="0.01" value="${esc(r.rate ?? "")}"></td>
				${L.buying ? "" : `<td><input class="l-d" type="number" step="0.01" value="${esc(r.discount ?? 0)}"></td>`}
				${L.avail ? `<td class="c-n l-av">—</td>` : ""}${L.margin ? `<td class="c-n l-mg">—</td>` : ""}<td class="c-n l-net">—</td>
				<td><button type="button" class="hsc-del" title="${__("Remove")}">${frappe.utils.icon("close", "xs")}</button></td></tr>`).join("")}</tbody></table>
				<div class="hsc-lbtn"><button type="button" class="btn btn-default btn-sm hsc-add">${frappe.utils.icon("add", "xs")} ${__("Add line")}</button>
				<button type="button" class="btn btn-default btn-sm hsc-newit">${frappe.utils.icon("tool", "xs")} ${L.buying ? __("New item") : __("New service")}</button>
				${L.buying ? "" : `<button type="button" class="btn btn-default btn-sm hsc-newst">${frappe.utils.icon("edit", "xs")} ${__("New stock item")}</button>`}</div></div>`;
		};

		const fmt = (v, c) => format_currency(v, c || st.p.currency || st.o.currency);
		const totals = () => {
			read();
			const L = spec.lines, items = Object.fromEntries((st.o.items || []).map((i) => [i.name, i]));
			let net = 0, n = 0;
			sh.$body.find(".hsc-line").each(function () {
				const r = st.lines[+$(this).data("i")], it = items[r.item_code];
				const amt = flt(r.qty) * flt(r.rate) * (1 - flt(r.discount) / 100);
				if (r.item_code && flt(r.qty) > 0) { net += amt; n++; }
				$(this).find(".l-net").text(r.item_code && flt(r.qty) ? format_number(amt, null, 2) : "—");
				if (L.avail) $(this).find(".l-av").html(it && it.stock ? `<span class="${flt(r.qty) > flt(it.available) ? "hsc-red" : ""}">${format_number(it.available, null, 0)}</span>` : "—");
				if (L.margin) {
					const val = (st.rates[r.item_code] || {}).valuation, eff = flt(r.rate) * (1 - flt(r.discount) / 100);
					$(this).find(".l-mg").html(r.item_code && eff && val ? `<span class="${eff < val ? "hsc-red" : eff - val < eff * 0.1 ? "hsc-amber" : "hsc-green"}">${format_number((eff - val) / eff * 100, null, 1)}%</span>` : "—");
				}
			});
			const vrate = st.p && st.p.vat_rate !== undefined ? flt(st.p.vat_rate) : flt(st.o.vat_rate), vat = net * vrate / 100, tot = net + vat;
			let left = `<div class="hsc-tl"><span>${__("Net")}</span><b>${fmt(net)}</b></div><div class="hsc-tl"><span>${__("VAT {0}%", [vrate])}</span><b>${fmt(vat)}</b></div>
				<div class="hsc-tl hsc-tt"><span>${kind === "quotation" ? __("Quotation total") : __("Order total")}</span><b>${fmt(tot)}</b></div>`;
			let right = "";
			if (spec.credit && st.v.party && st.p.credit_limit !== undefined) {
				const lim = flt(st.p.credit_limit), exp = flt(st.p.exposure), after = exp + tot * flt(st.p.rate || 1);
				right = `<div class="hsc-tl"><span>${__("Credit limit")}</span><b>${lim ? fmt(lim, st.o.currency) : __("Not set")}</b></div>
					<div class="hsc-tl"><span>${__("Current exposure")}</span><b>${fmt(exp, st.o.currency)}</b></div>
					<div class="hsc-tl"><span>${__("After this order")}</span><b class="${lim && after > lim ? "hsc-red" : "hsc-green"}">${fmt(after, st.o.currency)}</b></div>`;
			}
			sh.$body.find(".hsc-totals").html(`<div>${left}</div><div>${right}</div>`);
			const msg = !st.v.party && !st.prospect ? __("Choose the {0}.", [spec.party.label.toLowerCase()]) : !n ? __("Add at least one line.")
				: spec.credit && flt(st.p.credit_limit) && flt(st.p.exposure) + tot > flt(st.p.credit_limit) ? __("Above the credit limit — the order goes to the Finance Manager for approval.") : "";
			sh.$body.find(".hsc-msg").html(msg ? `<div class="hsc-note">${esc(msg)}</div>` : "");
		};

		const loadParty = (name) => {
			if (!name) { st.p = {}; draw(); return; }
			frappe.xcall("hipersign_trading.api.create.party", { kind, name }).then((p) => {
				st.p = p || {};
				const c = (st.o.customers || []).find((x) => x.name === name);
				st.p.group_hint = p.group ? `${p.group}${flt(p.discount) ? " · " + __("{0}% group discount", [flt(p.discount)]) : ""}` : "";
				st.v.price_list = p.price_list || st.o.default_price_list || st.v.price_list;
				if (p.terms) st.v.payment_terms = p.terms;
				if (p.sales_person && !st.v.sales_person) st.v.sales_person = p.sales_person;
				// v1.8.2: the document is in the party's currency (an export customer billed in USD gets a USD order), as the totals show
				if (p.currency) st.v.currency = p.currency;
				if (p.incoterm && !st.v.incoterm) st.v.incoterm = p.incoterm;
				st.v.contact_person = (p.contacts[0] || {}).name || "";
				const ship = p.addresses.find((a) => a.shipping) || p.addresses[0], bill = p.addresses.find((a) => a.billing) || p.addresses[0];
				st.v.shipping_address = ship ? ship.name : ""; st.v.billing_address = bill ? bill.name : "";
				st.p.rate = 1;
				// v1.8.2: credit exposure is in the company currency — convert this order's total at today's rate
				if (st.v.currency && st.o.currency && st.v.currency !== st.o.currency)
					frappe.xcall("erpnext.setup.utils.get_exchange_rate", { from_currency: st.v.currency, to_currency: st.o.currency })
						.then((r) => { if (flt(r)) { st.p.rate = flt(r); totals && totals(); } }).catch(() => {});
				draw();
				reprice(true);
			});
		};
		const reprice = (all, idx) => {
			read();
			const codes = st.lines.filter((r) => r.item_code).map((r) => r.item_code);
			if (!codes.length) return totals();
			frappe.xcall("hipersign_trading.api.create.rates", { kind, party: st.prospect ? null : st.v.party, items: codes }).then((r) => {
				Object.assign(st.rates, r || {});
				st.lines.forEach((L, i) => {
					if (!L.item_code || !(all || i === idx) || !r[L.item_code]) return;
					L.rate = flt(r[L.item_code].rate) || L.rate;
					// the customer group's discount shows in the Disc % column, as on the prototype
					if (!spec.lines.buying && flt(st.p.discount) && (all || !flt(L.discount))) L.discount = flt(st.p.discount);
					if (i === idx && !flt(L.qty)) L.qty = 1;
				});
				sh.$body.find(".hsc-lines").replaceWith(linesHtml());
				totals();
			});
		};

		sh.$body.on("change", "select[data-f=party]", function () {
			const v = $(this).val();
			if (v === "__add__") {
				if (spec.party.lead) {
					read(); st.prospect = true; st.v.party = ""; st.v.record_as = st.v.record_as || "Lead";
					// a new prospect has no group discount, price list or contacts of its own
					st.p = {}; st.v.price_list = st.o.default_price_list || ""; st.lines.forEach((L) => { L.discount = 0; });
					draw(); reprice(true); return;
				}
				$(this).val(st.v.party || "");
				return C.master(spec.party.master, { after: (d) => { st.o[spec.party.src].unshift({ name: d.name, label: d[spec.party.master === "Customer" ? "customer_name" : "supplier_name"] || d.name }); st.v.party = d.name; draw(); loadParty(d.name); } });
			}
			st.prospect = false; st.v.party = v; loadParty(v);
		});
		sh.$body.on("change", "select[data-f=record_as]", () => { read(); draw(); });
		sh.$body.on("change", "select[data-f=shipping_address]", function () {
			if ($(this).val() !== "__add__") return;
			$(this).val(st.v.shipping_address || "");
			hipersign.qc.open("Address", { values: { link_doctype: "Customer", link_name: st.v.party, address_type: "Shipping" }, open: false,
				after_insert: () => loadParty(st.v.party) });
		});
		sh.$body.on("change", "select[data-f=price_list]", () => reprice(true));
		sh.$body.on("change", ".l-it", function () { reprice(false, +$(this).closest("tr").data("i")); });
		sh.$body.on("input change", ".l-q,.l-r,.l-d", () => totals());
		sh.$body.on("click", ".hsc-add", () => { read(); st.lines.push({}); sh.$body.find(".hsc-lines").replaceWith(linesHtml()); totals(); });
		sh.$body.on("click", ".hsc-del", function () { read(); st.lines.splice(+$(this).closest("tr").data("i"), 1); if (!st.lines.length) st.lines.push({}); sh.$body.find(".hsc-lines").replaceWith(linesHtml()); totals(); });
		const newItem = (service) => C.master("Item", { values: service ? { is_stock_item: 0 } : {}, after: (d) => {
			st.o.items.push({ name: d.name, label: `${d.name} — ${d.item_name}`, item_name: d.item_name, stock: d.is_stock_item, available: 0 });
			read(); const e = st.lines.find((r) => !r.item_code); if (e) e.item_code = d.name; else st.lines.push({ item_code: d.name });
			reprice(false, st.lines.findIndex((r) => r.item_code === d.name)); } });
		sh.$body.on("click", ".hsc-newit", () => newItem(!spec.lines.buying));
		sh.$body.on("click", ".hsc-newst", () => newItem(false));

		const save = (a, btn) => {
			read();
			const lines = st.lines.filter((r) => r.item_code && flt(r.qty) > 0);
			const P = spec.party;
			if (!st.prospect && !st.v.party) return frappe.msgprint(__("Choose the {0}.", [P.label.toLowerCase()]));
			if (st.prospect) for (const df of spec.prospect) if (df.req && !st.v[df.f]) return frappe.msgprint(__("{0} is required.", [df.label]));
			if (!lines.length) return frappe.msgprint(__("Add at least one line with an item and a quantity."));
			const values = Object.assign({}, st.v);
			if (st.prospect) values.new_party = st.v.new_party;
			$(btn).prop("disabled", true);
			att.save("hipersign_trading.api.create.save", { kind, values, lines }, a.action).then((r) => {
				sh.close();
				frappe.show_alert({ message: r.message, indicator: r.needs_documents ? "orange" : "green" }, 7);
				if (a.send && hipersign.send_whatsapp) return hipersign.send_whatsapp(r.doctype, r.name);
				if (hipersign.panel && hipersign.panel.has(r.doctype)) hipersign.panel.open(r.doctype, r.name); else frappe.set_route("Form", r.doctype, r.name);
				if (window.cur_list && cur_list.doctype === r.doctype) cur_list.refresh();
			}).catch(() => {}).finally(() => $(btn).prop("disabled", false));
		};

		sh.$fl.html(`<button type="button" class="btn btn-default hsc-full">${__("Open full form")} ↗</button>`);
		sh.$fl.on("click", ".hsc-full", () => { read(); sh.close(); hipersign.fm.full_form(dt, { party: st.v.party, po_no: st.v.po_no, items: st.lines.filter((r) => r.item_code) }); });
		sh.$fr.html(`<button type="button" class="btn btn-default hsc-cancel">${__("Cancel")}</button>` + spec.actions.map((a, i) =>
			`<button type="button" class="btn ${a.primary ? "btn-primary" : "btn-default"} hsc-act" data-i="${i}">${a.primary ? frappe.utils.icon("check", "xs") + " " : ""}${esc(a.label)}</button>`).join(""));
		sh.$fr.on("click", ".hsc-cancel", sh.close);
		sh.$fr.on("click", ".hsc-act", function () { save(spec.actions[+$(this).data("i")], this); });

		// v1.7.3: the Detailed fields' own lists (project, tax template, letter head …) and Select options load with the form
		const extra = [...new Map(spec.fields.filter((df) => df.src && typeof df.src === "object").map((df) => [JSON.stringify(df.src), df.src])).values()];
		Promise.all([frappe.xcall("hipersign_trading.api.create.options", Object.assign({ kind }, preset.company ? { company: preset.company } : {})), with_meta(dt),
			...extra.map((s) => frappe.xcall("hipersign_trading.api.create.link_options", { doctype: s.dt, query: JSON.stringify({ filters: s.filters }) })
				.then((r) => { st.L[JSON.stringify(s)] = r || []; }).catch(() => { st.L[JSON.stringify(s)] = []; }))]).then(([o]) => {
			st.o = o;
			// v1.8.0: lines passed in keep their item even when it is not on the first page of the list
			(preset.items || []).forEach((r) => { if (r.item_code && st.o.items && !st.o.items.some((x) => x.name === r.item_code))
				st.o.items.push({ name: r.item_code, label: `${r.item_code} — ${r.item_name || ""}`, item_name: r.item_name || r.item_code, stock: 1, available: 0 }); });
			// like the prototype: the first customer / supplier is picked, so the form opens filled in
			if (!st.v.party && (o[spec.party.src] || []).length) st.v.party = o[spec.party.src][0].name;
			if (!st.v.currency) st.v.currency = o.currency;
			if (!st.v.price_list && o.default_price_list) st.v.price_list = o.default_price_list;
			draw();
			if (st.v.party) loadParty(st.v.party); else if (st.lines.some((r) => r.item_code)) reprice(true);
			setTimeout(() => sh.$body.find("select[data-f=party]").focus(), 50);
		});
		return sh;
	};

	// ------------------------------------------------------------ masters (the quick cards, prototype layout)
	C.master = function (dt, opts) {
		opts = opts || {};
		return hipersign.qc.open(dt, Object.assign({ open: false }, opts.values ? { values: opts.values } : {}, {
			after_insert: (d) => { opts.after && opts.after(d); } }));
	};

	C.render_card = function (dt, card, fields, values, opts, resolve) {
		const tdt = dt === "Item" && values.is_stock_item !== undefined && !+values.is_stock_item ? "service" : dt;
		let mode = (hipersign.fm && hipersign.fm.COVERED.includes(dt) && hipersign.fm.mode(dt)) || "Standard";
		const modes = hipersign.fm && hipersign.fm.COVERED.includes(dt) && !opts.after_insert;
		const sh = C.shell({ title: tdt === "service" ? __("New service") : card.title, sub: card.sub, mode, modes,
			onMode: (m) => { read(); mode = m; sh.setMode(m); hipersign.fm.remember(dt, m); draw(); } });
		const v = Object.assign({}, values);
		fields.forEach((f) => { if (f.fieldname && v[f.fieldname] === undefined && f.default !== undefined) v[f.fieldname] = f.default; });
		const links = {};
		const read = () => sh.$body.find("[data-f]").each(function () { v[$(this).data("f")] = this.type === "checkbox" ? (this.checked ? 1 : 0) : $(this).val(); });
		const shown = (f) => {
			if (["Column Break", "Section Break", "HTML"].includes(f.fieldtype) || !f.fieldname) return false;
			if (f.depends_on) {
				const ex = f.depends_on.startsWith("eval:") ? f.depends_on.slice(5) : `doc.${f.depends_on}`;
				try { if (!new Function("doc", `return (${ex})`)(v)) return false; } catch (e) { /* show */ }
			}
			if (mode === "Quick") return f.reqd || f.fieldname === "hs_interested_in";
			return true;
		};
		const conv = (f) => {
			const t = f.fieldtype;
			const df = { f: f.fieldname, label: f.label, req: f.reqd, ph: f.placeholder, hint: f.description, w: f.w || (t === "Small Text" || t === "Text" ? 2 : 1) };
			// v1.7.3: a card may give [value, label] pairs (the user's role)
			if (t === "Select") Object.assign(df, { t: "select", list: Array.isArray(f.options) ? f.options : (f.options || "").split("\n").filter((x) => x !== ""), blank: f.reqd ? undefined : "—" });
			else if (t === "Link") Object.assign(df, { t: "select", list: links[f.options] || [], blank: f.reqd ? undefined : "—" });
			// v1.8.4: "For → Name" (contact, address) is a picker of the chosen customer / supplier / lead, not a typed ID
			else if (t === "Dynamic Link") {
				const l = v[f.options] ? links[v[f.options]] || [] : [];
				Object.assign(df, { t: "select", list: v[f.fieldname] && !l.some((o) => (o.name ?? o) === v[f.fieldname]) ? [{ name: v[f.fieldname], label: v[f.fieldname] }, ...l] : l,
					blank: v[f.options] ? "—" : __("— choose For first —") });
			}
			else if (t === "Check") df.t = "check";
			else if (t === "Date") df.t = "date";
			else if (["Currency", "Float", "Int", "Percent"].includes(t)) df.t = t === "Currency" ? "currency" : "number";
			else if (t === "Small Text" || t === "Text") df.t = "textarea";
			else if (f.options === "Phone") df.t = "tel";
			else if (f.options === "Email") df.t = "email";
			return df;
		};
		const draw = () => {
			sh.$body.html(`<div class="hsc-grid">${fields.filter(shown).map((f) => C.field(conv(f), v[f.fieldname])).join("")}</div>`);
			const nf = sh.$body.find("input,select").first(); setTimeout(() => nf.focus(), 30);
		};
		sh.$body.on("change", "select,input[type=checkbox]", () => { read(); draw(); });
		// Link choices: one call per doctype the card uses
		const dynOf = (f) => ((fields.find((x) => x.fieldname === f.options) || {}).options || "").split("\n").filter((x) => x);
		const need = [...new Set([...fields.filter((f) => f.fieldtype === "Link").map((f) => f.options), ...fields.filter((f) => f.fieldtype === "Dynamic Link").flatMap(dynOf)])];
		Promise.all(need.map((ldt) => frappe.xcall("hipersign_trading.api.create.link_options", { doctype: ldt,
			query: (fields.find((f) => f.options === ldt && f.get_query) || {}).get_query ? JSON.stringify(fields.find((f) => f.options === ldt).get_query()) : null })
			.then((r) => { links[ldt] = r || []; }).catch(() => { links[ldt] = []; }))).then(draw);
		sh.$body.html(`<div class="hsc-loading">${__("Loading…")}</div>`);
		if (!opts.after_insert && hipersign.fm && hipersign.fm.COVERED.includes(dt)) {
			sh.$fl.html(`<button type="button" class="btn btn-default hsc-full">${__("Open full form")} ↗</button>`);
			sh.$fl.on("click", ".hsc-full", () => { read(); sh.close(); hipersign.qc.full_form(dt, v); });
		}
		sh.$fr.html(`<button type="button" class="btn btn-default hsc-cancel">${__("Cancel")}</button><button type="button" class="btn btn-primary hsc-save">${frappe.utils.icon("check", "xs")} ${__("Save")}</button>`);
		sh.$fr.on("click", ".hsc-cancel", sh.close);
		sh.$fr.on("click", ".hsc-save", function () {
			read();
			const miss = fields.filter((f) => f.reqd && shown(f) && (v[f.fieldname] === undefined || v[f.fieldname] === "" || v[f.fieldname] === null)).map((f) => f.label);
			if (miss.length) return frappe.msgprint(__("Please fill in: {0}", [miss.join(", ")]));
			const btn = this; $(btn).prop("disabled", true);
			const link = card.link ? hipersign.qc.link_of(v) : [null, null];
			frappe.xcall("hipersign_trading.api.quick_cards.create", { doctype: dt, values: v, link_doctype: v.link_doctype || link[0], link_name: v.link_name || link[1] })
				.then((r) => {
					sh.close();
					frappe.model.sync(r.doc);
					frappe.show_alert({ message: __("{0} {1} saved", [__(dt), r.title]), indicator: "green" }, 5);
					if (opts.after_insert) opts.after_insert(r.doc);
					else if (opts.open !== false) { if (hipersign.panel && hipersign.panel.has(dt)) hipersign.panel.open(dt, r.name); else frappe.set_route("Form", dt, r.name); }
					if (window.cur_list && cur_list.doctype === dt) cur_list.refresh();
					resolve(r.doc);
				}).catch(() => {}).finally(() => $(btn).prop("disabled", false));
		});
		return sh;
	};


	// ------------------------------------------------------------ "from a document" modals (deliver, receive, pay, invoice)
	C.FLOW_MAKE = {
		"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note": "deliver",
		"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt": "receive",
		"hipersign_trading.api.panel.pay_sales_invoice": "receive_payment",
		"hipersign_trading.api.panel.pay_purchase_invoice": "pay_supplier",
		"erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice": "invoice",
	};
	// a panel / page button that would make a draft opens the modal instead; returns true when it did
	C.make = function (method, source, done) {
		const kind = C.FLOW_MAKE[method];
		if (!kind || (frappe.boot.hipersign || {}).no_create_modal) return false;
		C.flow(kind, source, done);
		return true;
	};
	C.flow = function (kind, source, done) {
		frappe.xcall("hipersign_trading.api.create_flow.prepare", { kind, source }).then((m) => {
			if (m.blocked) return frappe.msgprint({ title: __("Not cleared yet"), indicator: "orange", message: esc(m.blocked) });
			const sh = C.shell({ title: m.title, sub: m.sub, wide: !!m.lines });
			const v = {};
			(m.fields || []).forEach((f) => { v[f.f] = f.v; });
			const lines = (m.lines || []).map((r) => Object.assign({}, r));
			let h = "";
			if (m.badges) h += `<div class="hsc-badges">${m.badges.map(([t, c]) => `<span class="hsc-badge ${c}">${esc(t)}</span>`).join("")}</div>`;
			if (m.scan) h += `<div class="hsc-scan">${frappe.utils.icon("scan", "sm")}<input class="hsc-scanin" placeholder="${__("Scan or type barcode / item code, then Enter")}"><span>${__("Each scan adds 1 to the accepted quantity")}</span></div>`;
			if (m.lines) {
				const ro = m.lines.length && m.lines[0].ro;
				h += `<div class="hsc-lines"><table><thead><tr>${m.cols.map((c, i) => `<th class="${i ? "c-n" : "c-it"}">${esc(c)}</th>`).join("")}</tr></thead><tbody>`;
				lines.forEach((r, k) => {
					const name = `<b>${esc(r.item_name)}</b>${r.barcode ? `<br><small class="hsc-mono">${esc(r.barcode)}</small>` : ""}`;
					if (ro) h += `<tr><td>${name}</td><td class="c-n">${format_number(r.qty, null, 2)}</td><td class="c-n">${format_number(r.rate, null, 2)}</td><td class="c-n">${format_number(r.amount, null, 2)}</td></tr>`;
					else if (kind === "deliver") h += `<tr data-k="${k}"><td>${name}</td><td>${esc(r.uom || "")}</td><td class="c-n">${format_number(r.ordered, null, 0)}</td><td class="c-n">${format_number(r.delivered, null, 0)}</td>
						<td class="c-n"><b>${format_number(r.pending, null, 0)}</b></td><td><input class="f-q" type="number" min="0" value="${r.qty}"></td>
						<td>${r.stock ? `<select class="f-w">${optHtml(r.options, r.warehouse)}</select>` : `<small class="hsc-hint">${__("Service — no stock")}</small>`}</td></tr>`;
					else h += `<tr data-k="${k}"><td>${name}</td><td class="c-n">${format_number(r.ordered, null, 0)}</td><td class="c-n">${format_number(r.received, null, 0)}</td>
						<td class="c-n"><b>${format_number(r.pending, null, 0)}</b></td><td><input class="f-q" type="number" min="0" value="${r.qty}"></td>
						<td><input class="f-r" type="number" min="0" value="0"></td><td><select class="f-w">${optHtml(r.options, r.warehouse)}</select></td></tr>`;
				});
				h += `</tbody></table></div>`;
			}
			h += `<div class="hsc-grid">${(m.fields || []).filter((f) => !(f.t === "select" && !(f.list || []).length && f.f === "hs_delivery_status")).map((f) =>
				f.ro ? `<div class="hsc-f hsc-w${f.w || 1}"><label>${esc(f.label)}</label><input readonly class="hsc-ro" value="${esc(f.v ?? "")}"></div>`
					: C.field(Object.assign({}, f, { noblank: f.t === "select" }), f.v)).join("")}</div>`;
			if (m.note) h += `<div class="hsc-note">${esc(m.note)}</div>`;
			sh.$body.html(h);
			sh.$body.on("keydown", ".hsc-scanin", function (e) {
				if (e.key !== "Enter") return;
				const code = $(this).val().trim(); $(this).val("");
				const k = lines.findIndex((r) => r.item_code === code || r.barcode === code);
				if (k < 0) return frappe.show_alert({ message: __("{0} is not on this order", [code]), indicator: "orange" });
				const $q = sh.$body.find(`tr[data-k="${k}"] .f-q`); $q.val(flt($q.val()) + 1);
			});
			sh.$fr.html(`<button type="button" class="btn btn-default hsc-cancel">${__("Cancel")}</button><button type="button" class="btn btn-primary hsc-go">${frappe.utils.icon(m.icon || "check", "xs")} ${esc(m.button)}</button>`);
			sh.$fr.on("click", ".hsc-cancel", sh.close);
			sh.$fr.on("click", ".hsc-go", function () {
				sh.$body.find("[data-f]").each(function () { v[$(this).data("f")] = $(this).val(); });
				const out = [];
				sh.$body.find("tr[data-k]").each(function () { const r = lines[+$(this).data("k")]; out.push({ i: r.i, qty: $(this).find(".f-q").val(), rejected: $(this).find(".f-r").val(), warehouse: $(this).find(".f-w").val() }); });
				const btn = this; $(btn).prop("disabled", true);
				frappe.xcall("hipersign_trading.api.create_flow.commit", { kind, source, values: v, lines: out }).then((r) => {
					sh.close();
					frappe.show_alert({ message: r.message, indicator: r.needs_documents ? "orange" : "green" }, 7);
					if (done) done(r);
					else if (hipersign.panel && hipersign.panel.has(r.doctype)) hipersign.panel.open(r.doctype, r.name);
					else frappe.set_route("Form", r.doctype, r.name);
				}).catch(() => {}).finally(() => $(btn).prop("disabled", false));
			});
		});
	};


	// ------------------------------------------------------------ the other create forms (one renderer, one save)
	const MODES_SHIP = [["Sea", __("Sea")], ["Air", __("Air")], ["Land", __("Land")]];
	C.DOCS = {
		"Import Shipment": { title: __("New import shipment"), sub: __("For an approved import order — documents and charges are added on the shipment"), fields: [
			{ f: "purchase_order", label: __("Purchase order"), t: "select", src: L("Purchase Order", { docstatus: 1, per_received: ["<", 100] }), req: 1, m: "q", w: 2 , fill: "import_from_po" },
			{ f: "mode", label: __("Mode"), t: "select", opts: MODES_SHIP, def: "Sea", m: "q" },
			{ f: "shipping_line", label: __("Shipping line / airline"), m: "s", ph: "Maersk" },
			{ f: "bl_awb", label: __("BL / AWB number"), m: "q" },
			{ f: "containers", label: __("Number of containers"), t: "number", m: "s" },
			{ f: "vessel_flight", label: __("Vessel / flight"), m: "s" },
			{ f: "port_of_loading", label: __("Port of loading"), m: "s" },
			{ f: "port_of_discharge", label: __("Port of discharge"), def: "Jebel Ali Port", m: "s" },
			{ f: "insurance_policy", label: __("Insurance policy no."), m: "d" },
			{ f: "etd", label: __("ETD"), t: "date", m: "q" },
			{ f: "eta", label: __("ETA"), t: "date", m: "q" },
			// v1.7.3: Detailed — the rest of the shipment's own fields
			{ f: "forwarder", label: __("Forwarder / clearing agent"), t: "select", src: L("Supplier", { disabled: 0 }), m: "d" },
			{ f: "bill_of_entry", label: __("Bill of entry no."), m: "d" },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		] },
		"Export Shipment": { title: __("New export shipment"), sub: __("Book the shipment for a confirmed export order — 0% VAT needs proof of export"), fields: [
			{ f: "sales_order", label: __("Export order"), t: "select", src: L("Sales Order", { docstatus: 1, per_delivered: ["<", 100] }), req: 1, m: "q", w: 2, fill: "export_from_so" },
			{ f: "mode", label: __("Mode"), t: "select", opts: MODES_SHIP, def: "Land", m: "q" },
			{ f: "port_of_loading", label: __("Port / border of loading"), m: "q", ph: "Hatta border (Oman)" },
			{ f: "destination", label: __("Destination"), m: "q", ph: "Muscat, Oman" },
			{ f: "incoterm", label: __("Incoterm"), t: "select", src: L("Incoterm"), m: "s" },
			{ f: "forwarder", label: __("Forwarder / transporter"), t: "select", src: L("Supplier", { disabled: 0 }), m: "s" },
			{ f: "etd", label: __("Planned departure (ETD)"), t: "date", m: "q", def: () => plus(3) },
			{ f: "_transit_days", label: __("Transit days"), t: "number", m: "s", def: 2 },
			{ f: "re_export_of", label: __("Re-export of import"), t: "select", src: L("Import Shipment"), m: "d", blank: __("No — local stock") },
			// v1.7.3: Detailed — the rest of the shipment's own fields
			{ f: "named_place", label: __("Named place (incoterm)"), m: "d" },
			{ f: "bl_awb_cmr", label: __("BL / AWB / CMR no."), m: "d" },
			{ f: "declaration_no", label: __("Export declaration no."), m: "d" },
			{ f: "coo_no", label: __("Certificate of origin no."), m: "d" },
		] },
		"Material Request": { title: __("New purchase request"), sub: __("Ask purchasing to buy items"), fields: [
			{ f: "_department", label: __("Department"), t: "select", src: L("Department", { is_group: 0 }), m: "s" },
			{ f: "schedule_date", label: __("Needed by"), t: "date", m: "q", def: () => plus(7) },
			{ f: "_reason", label: __("Reason"), m: "s", w: 2 },
			// v1.7.3: Detailed — the rest of the request's own fields
			{ f: "transaction_date", label: __("Request date"), t: "date", m: "d", def: today },
			{ f: "set_warehouse", label: __("Deliver to warehouse"), t: "select", src: L("Warehouse", { is_group: 0 }), m: "d" },
			{ f: "buying_price_list", label: __("Price list"), t: "select", src: L("Price List", { enabled: 1, buying: 1 }), m: "d" },
			{ f: "tc_name", label: __("Terms template"), t: "select", src: L("Terms and Conditions"), m: "d" },
			{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
			{ f: "select_print_heading", label: __("Print heading"), t: "select", src: L("Print Heading"), m: "d" },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_purchase_item: 1 }), w: 3 }, { f: "qty", label: __("Qty"), t: "number" }, { f: "_stock", label: __("In stock"), t: "stock", of: "item_code" }], n: 2 },
			actions: [{ label: __("Save"), action: "save" }, { label: __("Submit request"), action: "submit", primary: 1 }] },
		"Stock Entry": { title: __("Stock transfer"), sub: __("Move stock between warehouses"), fields: [
			{ f: "from_warehouse", label: __("From"), t: "select", src: L("Warehouse", { is_group: 0 }), req: 1, m: "q" },
			{ f: "to_warehouse", label: __("To"), t: "select", src: L("Warehouse", { is_group: 0 }), req: 1, m: "q", differ: "from_warehouse" },
			{ f: "posting_date", label: __("Transfer date"), t: "date", m: "s", def: today },
			{ f: "_requested_by", label: __("Requested by"), m: "s" },
			{ f: "_reason", label: __("Reason"), m: "s", w: 2 },
			// v1.7.3: Detailed — the rest of the transfer's own fields
			{ f: "posting_time", label: __("Transfer time"), t: "time", m: "d" },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
			{ f: "add_to_transit", label: __("Goods in transit (receive later)"), t: "check", m: "d" },
			{ f: "apply_putaway_rule", label: __("Apply putaway rules"), t: "check", m: "d" },
			{ f: "inspection_required", label: __("Inspection required"), t: "check", m: "d" },
			{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
			{ f: "select_print_heading", label: __("Print heading"), t: "select", src: L("Print Heading"), m: "d" },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_stock_item: 1 }), w: 3 }, { f: "qty", label: __("Quantity"), t: "number" }], n: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Transfer"), action: "submit", primary: 1 }] },
		"Stock Reconciliation": { title: __("Stock count"), sub: __("Count and reconcile — differences go to the Warehouse Manager for approval"), fields: [
			{ f: "_reason", label: __("Reason"), t: "select", opts: ["Cycle count — damaged cartons", "Cycle count — miscount on receipt", "Breakage in warehouse", "Item found — not booked", "Theft or loss", "Year-end physical count"].map((x) => [x, __(x)]), m: "q", w: 2 },
			// v1.7.3: Detailed — the rest of the count's own fields
			{ f: "posting_date", label: __("Count date"), t: "date", m: "d", def: today },
			{ f: "posting_time", label: __("Count time"), t: "time", m: "d" },
			{ f: "expense_account", label: __("Difference account"), t: "select", src: L("Account", { is_group: 0 }), m: "d", blank: __("— company default —") },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_stock_item: 1 }), w: 3 }, { f: "warehouse", label: __("Warehouse"), t: "select", src: L("Warehouse", { is_group: 0 }), w: 2 },
			{ f: "qty", label: __("Counted quantity"), t: "number" }], n: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Send for approval"), action: "submit", primary: 1 }] },
		"Journal Entry": { title: __("New journal entry"), sub: __("Manual entry — debits and credits must agree; large entries need a supporting document"), fields: [
			{ f: "posting_date", label: __("Posting date"), t: "date", m: "q", def: today },
			{ f: "user_remark", label: __("Memo"), m: "q" },
			// v1.7.3: Detailed — the rest of the entry's own fields
			{ f: "voucher_type", label: __("Entry type"), t: "select", opts: "@meta", m: "d", def: "Journal Entry" },
			{ f: "cheque_no", label: __("Reference / cheque no."), m: "d" },
			{ f: "cheque_date", label: __("Reference date"), t: "date", m: "d" },
			{ f: "bill_no", label: __("Bill no."), m: "d" },
			{ f: "bill_date", label: __("Bill date"), t: "date", m: "d" },
			{ f: "due_date", label: __("Due date"), t: "date", m: "d" },
			{ f: "pay_to_recd_from", label: __("Pay to / received from"), m: "d" },
			{ f: "mode_of_payment", label: __("Mode of payment"), t: "select", src: L("Mode of Payment", { enabled: 1 }), m: "d" },
			{ f: "is_opening", label: __("Opening entry"), t: "select", opts: "@meta", m: "d", def: "No" },
			{ f: "multi_currency", label: __("Multi-currency"), t: "check", m: "d" },
			{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
			{ f: "select_print_heading", label: __("Print heading"), t: "select", src: L("Print Heading"), m: "d" },
		], rows: { cols: [{ f: "account", label: __("Account"), t: "select", src: L("Account", { is_group: 0 }), w: 3 }, { f: "debit", label: __("Debit"), t: "number" }, { f: "credit", label: __("Credit"), t: "number" }], n: 2, balance: 1, sum: ["debit", "credit"] },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Post"), action: "submit", primary: 1 }] },
		"Post Dated Cheque": { title: __("Cheque received from customer"), sub: __("Post-dated cheque — the invoice's outstanding falls at once; clearing moves it to the bank"), fields: [
			{ f: "direction", label: __("Cheque"), t: "select", opts: [["Received", __("Received from a customer")], ["Issued", __("Issued to a supplier")]], def: "Received", m: "q", redraw: 1 },
			{ f: "_invoice", label: __("Invoice"), t: "select", src: L("Sales Invoice", { docstatus: 1, outstanding_amount: [">", 0], is_return: 0 }), req: 1, m: "q", show: (v) => v.direction !== "Issued" },
			{ f: "_invoice", label: __("Supplier invoice"), t: "select", src: L("Purchase Invoice", { docstatus: 1, outstanding_amount: [">", 0] }), req: 1, m: "q", show: (v) => v.direction === "Issued" },
			{ f: "cheque_no", label: __("Cheque no."), req: 1, m: "q" },
			{ f: "drawn_on", label: __("Drawn on (customer bank)"), m: "q", show: (v) => v.direction !== "Issued", ph: "Emirates NBD" },
			{ f: "bank_account", label: __("Our bank account"), t: "select", src: L("Account", { account_type: "Bank", is_group: 0 }), m: "q", show: (v) => v.direction === "Issued" },
			{ f: "amount", label: __("Amount (AED)"), t: "number", req: 1, m: "q" },
			{ f: "cheque_date", label: __("Cheque date"), t: "date", req: 1, m: "q", def: () => plus(30) },
			// v1.7.3: Detailed — the rest of the cheque's own fields
			{ f: "received_on", label: __("Received / issued on"), t: "date", m: "d", def: today },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		] },
		"Expense Claim": { title: __("New expense claim"), sub: __("Receipts with the supplier's TRN let the VAT be recovered"), fields: [
			{ f: "employee", label: __("Employee"), t: "select", src: L("Employee", { status: "Active" }), req: 1, m: "q" },
			{ f: "_purpose", label: __("Purpose"), m: "q" },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "s" },
			// v1.7.3: Detailed — the rest of the claim's own fields
			{ f: "posting_date", label: __("Claim date"), t: "date", m: "d", def: today },
			{ f: "department", label: __("Department"), t: "select", src: L("Department", { is_group: 0 }), m: "d" },
			{ f: "expense_approver", label: __("Approver"), t: "select", src: L("User", { user_type: "System User", enabled: 1 }), m: "d", blank: __("— the employee's approver —") },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
			{ f: "task", label: __("Task"), t: "select", src: L("Task"), m: "d" },
			{ f: "payable_account", label: __("Payable account"), t: "select", src: L("Account", { account_type: "Payable", is_group: 0 }), m: "d", blank: __("— company default —") },
		], rows: { cols: [{ f: "expense_date", label: __("Date"), t: "date" }, { f: "expense_type", label: __("Type"), t: "select", src: L("Expense Claim Type"), w: 2 },
			{ f: "description", label: __("What, where, with whom"), w: 2 }, { f: "amount", label: __("Amount (AED)"), t: "number" }], n: 1, sum: ["amount"] } },
		"Leave Application": { title: __("Leave request"), sub: __("Goes to the employee's leave approver"), fields: [
			{ f: "employee", label: __("Employee"), t: "select", src: L("Employee", { status: "Active" }), req: 1, m: "q", w: 2 },
			{ f: "leave_type", label: __("Leave type"), t: "select", src: L("Leave Type"), req: 1, m: "q" },
			{ f: "from_date", label: __("From"), t: "date", req: 1, m: "q", def: () => plus(7) },
			{ f: "to_date", label: __("To"), t: "date", req: 1, m: "q", def: () => plus(9) },
			{ f: "description", label: __("Reason"), m: "q", w: 2 },
			// v1.7.3: Detailed — the rest of the request's own fields
			{ f: "half_day", label: __("Half day"), t: "check", m: "d", redraw: 1 },
			{ f: "half_day_date", label: __("Half day on"), t: "date", m: "d", show: (v) => +v.half_day },
			{ f: "leave_approver", label: __("Leave approver"), t: "select", src: L("User", { user_type: "System User", enabled: 1 }), m: "d", blank: __("— the employee's approver —") },
			{ f: "posting_date", label: __("Request date"), t: "date", m: "d", def: today },
			{ f: "follow_via_email", label: __("Follow via email"), t: "check", m: "d", def: 1 },
			{ f: "letter_head", label: __("Letter head"), t: "select", src: L("Letter Head"), m: "d" },
		] },
		"Letter of Credit": { title: __("New LC application"), sub: __("Import letter of credit for a supplier order — the bank blocks the cash margin"), fields: [
			{ f: "purchase_order", label: __("Purchase order"), t: "select", src: L("Purchase Order", { docstatus: 1, per_received: ["<", 100] }), req: 1, m: "q", w: 2, fill: "lc_from_po" },
			{ f: "issuing_bank", label: __("Issuing bank"), t: "select", src: L("Bank"), req: 1, m: "q" },
			{ f: "amount", label: __("Amount (order currency)"), t: "number", m: "q", hint: __("Empty = the order total") },
			{ f: "tenor", label: __("Payment"), t: "select", opts: ["At sight", "Usance 30 days", "Usance 60 days", "Usance 90 days", "Usance 120 days", "Usance 180 days"].map((x) => [x, __(x)]), m: "q" },
			{ f: "tolerance_pct", label: __("Tolerance ±%"), t: "number", def: 5, m: "s" },
			{ f: "margin_pct", label: __("Cash margin %"), t: "number", def: 10, m: "s" },
			{ f: "latest_shipment_date", label: __("Latest shipment date"), t: "date", m: "s", def: () => plus(45) },
			{ f: "expiry_date", label: __("Expiry date"), t: "date", m: "q", def: () => plus(75) },
			// v1.7.3: Detailed — the rest of the LC's own fields
			{ f: "bank_account", label: __("Our bank account"), t: "select", src: L("Bank Account", { is_company_account: 1 }), m: "d" },
			{ f: "lc_number", label: __("LC number"), m: "d" },
			{ f: "issue_date", label: __("Issue date"), t: "date", m: "d" },
			{ f: "charges", label: __("Bank charges"), t: "number", m: "d" },
			{ f: "trust_receipt", label: __("Trust receipt financing"), t: "check", m: "d" },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		] },
		"Bank Guarantee": { title: __("Request a bank guarantee"), sub: __("Performance, advance-payment or tender bond for a customer"), fields: [
			{ f: "_bg_kind", label: __("Type"), t: "select", opts: ["Performance bond", "Advance payment guarantee", "Tender (bid) bond", "Retention guarantee", "Customs / financial guarantee"].map((x) => [x, __(x)]), m: "q" },
			{ f: "customer", label: __("Beneficiary (customer)"), t: "select", src: L("Customer", { disabled: 0 }), req: 1, m: "q" },
			{ f: "_contract", label: __("Contract / tender / order"), m: "q" },
			{ f: "_contract_value", label: __("Contract value (AED)"), t: "number", req: 1, m: "q" },
			{ f: "_pct", label: __("Guarantee %"), t: "number", def: 10, m: "q" },
			{ f: "bank", label: __("Issuing bank"), t: "select", src: L("Bank"), m: "q" },
			{ f: "_margin_pct", label: __("Cash margin %"), t: "number", def: 10, m: "s" },
			{ f: "start_date", label: __("Valid from"), t: "date", m: "q", def: today },
			{ f: "_valid_to", label: __("Valid to"), t: "date", m: "q", def: () => plus(365) },
			// v1.7.3: Detailed — the rest of the guarantee's own fields
			{ f: "bank_account", label: __("Our bank account"), t: "select", src: L("Bank Account", { is_company_account: 1 }), m: "d" },
			{ f: "bank_guarantee_number", label: __("Guarantee number"), m: "d" },
			{ f: "fixed_deposit_number", label: __("Fixed deposit no. (margin)"), m: "d" },
			{ f: "charges", label: __("Bank charges"), t: "number", m: "d" },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
		] },
		"Company Document": { title: __("Add company document"), sub: __("Licence, registration or certificate — renewal reminders follow the expiry"), fields: [
			{ f: "company", label: __("Company"), t: "select", src: L("Company"), req: 1, m: "q", def: co },
			{ f: "document_type", label: __("Document type"), t: "select", src: L("Company Document Type"), req: 1, m: "q" },
			{ f: "document_number", label: __("Number"), m: "q" },
			{ f: "authority", label: __("Issuing authority"), m: "s" },
			{ f: "issue_date", label: __("Issue date"), t: "date", m: "s" },
			{ f: "expiry_date", label: __("Expiry date"), t: "date", m: "q" },
			{ f: "responsible_user", label: __("Responsible"), t: "select", src: L("User", { user_type: "System User", enabled: 1 }), m: "s" },
			{ f: "notes", label: __("Notes"), t: "textarea", m: "d", w: 2 },
			// v1.7.3: Detailed — renewal
			{ f: "renewal_status", label: __("Renewal status"), t: "select", opts: "@meta", m: "d" },
			{ f: "renewal_cost", label: __("Renewal cost"), t: "number", m: "d" },
		] },
		// ------------------------------------------------ v1.7.3: the windows the + New menu still sent to the full form
		"Credit Limit Request": { title: __("Credit limit request"), sub: __("A new or higher limit goes to the Finance Manager for approval"), fields: [
			{ f: "customer", label: __("Customer"), t: "select", src: L("Customer", { disabled: 0 }), req: 1, m: "q", w: 2, fill: "credit_of_customer" },
			{ f: "_current_limit", label: __("Current limit"), ro: 1, m: "s", fmt: (x) => (x === undefined || x === "" ? "" : flt(x) ? format_number(x, null, 2) : __("Not set")) },
			{ f: "requested_limit", label: __("New credit limit"), t: "number", req: 1, m: "q" },
			{ f: "reason", label: __("Reason"), t: "textarea", m: "s", w: 2, ph: __("Why the customer needs it — order pipeline, payment record") },
			{ f: "company", label: __("Company"), t: "select", src: L("Company", { is_group: 0 }), req: 1, m: "d", def: co, fill: "credit_of_customer" },
		], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit for approval"), action: "submit", primary: 1 }] },
		"Purchase Invoice": { title: __("New supplier bill"), sub: __("Match it to the order or goods receipt — VAT from the company's template"), fields: [
			{ f: "supplier", label: __("Supplier"), t: "select", src: L("Supplier", { disabled: 0 }), req: 1, m: "q", blank: __("— choose —"), fill: "supplier_bill" },
			{ f: "_source", label: __("Order or goods receipt to match"), t: "select", m: "q", blank: __("— none: type the lines —"), fill: "bill_source",
				src: [L("Purchase Order", { docstatus: 1, per_billed: ["<", 100], status: ["not in", ["Closed", "On Hold"]] }), L("Purchase Receipt", { docstatus: 1, per_billed: ["<", 100], is_return: 0 })] },
			{ f: "bill_no", label: __("Supplier bill no."), req: 1, m: "q" },
			{ f: "bill_date", label: __("Bill date"), t: "date", m: "q", def: today },
			{ f: "due_date", label: __("Due date"), t: "date", m: "s", def: () => plus(30) },
			{ f: "posting_date", label: __("Posting date"), t: "date", m: "d", def: today },
			{ f: "currency", label: __("Currency"), t: "select", src: L("Currency", { enabled: 1 }), m: "d", blank: __("— the supplier's —") },
			{ f: "payment_terms_template", label: __("Payment terms"), t: "select", src: L("Payment Terms Template"), m: "d", blank: __("— the supplier's —") },
			{ f: "taxes_and_charges", label: __("VAT template"), t: "select", src: L("Purchase Taxes and Charges Template"), m: "d", blank: __("— company default —") },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
			{ f: "update_stock", label: __("Update stock (no goods receipt)"), t: "check", m: "d", redraw: 1 },
			{ f: "set_warehouse", label: __("Receive into"), t: "select", src: L("Warehouse", { is_group: 0 }), m: "d", show: (v) => +v.update_stock },
			{ f: "on_hold", label: __("Hold payment"), t: "check", m: "d", redraw: 1 },
			{ f: "hold_comment", label: __("Reason for the hold"), m: "d", w: 2, show: (v) => +v.on_hold },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_purchase_item: 1 }), w: 3 }, { f: "qty", label: __("Qty"), t: "number" },
			{ f: "rate", label: __("Rate"), t: "number" }], n: 1, net: ["qty", "rate"], total: __("Bill total") },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit bill"), action: "submit", primary: 1 }] },
		// a debit note is a Purchase Invoice with "Is Return" — its own window (C.new picks it when is_return is set)
		"Purchase Invoice:return": { doctype: "Purchase Invoice", title: __("New debit note"), sub: __("Purchase return against a supplier bill — the quantities sent back"), fields: [
			{ f: "_return_against", label: __("Supplier bill"), t: "select", src: L("Purchase Invoice", { docstatus: 1, is_return: 0 }), req: 1, m: "q", w: 2, fill: "debit_from_bill" },
			{ f: "hs_return_reason", label: __("Reason"), t: "select", opts: "@meta", m: "q", def: "Wrong item supplied" },
			{ f: "posting_date", label: __("Date"), t: "date", m: "s", def: today },
			{ f: "hs_supplier_rma", label: __("Supplier RMA / reference"), m: "s" },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		], rows: { cols: [{ f: "_item", label: __("Item"), t: "ro", w: 3 }, { f: "_can", label: __("Can return"), t: "ro", n: 1 }, { f: "qty", label: __("Return qty"), t: "number" },
			{ f: "rate", label: __("Rate"), t: "ro", n: 1 }], n: 0, fixed: 1, net: ["qty", "rate"], total: __("Debit note total") },
			full: () => ({ is_return: 1 }),
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit debit note"), action: "submit", primary: 1 }] },
		// v1.7.3: a credit note (sales return) against a tax invoice — the same shape as the debit note
		"Sales Invoice:return": { doctype: "Sales Invoice", title: __("New credit note"), sub: __("Sales return against a tax invoice — the quantities the customer sent back"), fields: [
			{ f: "_return_against", label: __("Tax invoice"), t: "select", src: L("Sales Invoice", { docstatus: 1, is_return: 0 }), req: 1, m: "q", w: 2, fill: "credit_from_invoice" },
			{ f: "hs_return_reason", label: __("Reason"), t: "select", opts: "@meta", m: "q", req: 1, def: "Damaged in transit" },
			{ f: "posting_date", label: __("Date"), t: "date", m: "s", def: today },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		], rows: { cols: [{ f: "_item", label: __("Item"), t: "ro", w: 3 }, { f: "_can", label: __("Can return"), t: "ro", n: 1 }, { f: "qty", label: __("Return qty"), t: "number" },
			{ f: "rate", label: __("Rate"), t: "ro", n: 1 }], n: 0, fixed: 1, net: ["qty", "rate"], total: __("Credit note total") },
			full: () => ({ is_return: 1 }),
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit credit note"), action: "submit", primary: 1 }] },
		"Payment Entry": { title: __("Receive payment"), sub: __("Applied to the customer's open invoices, oldest first"), fields: [
			{ f: "customer", label: __("Customer"), t: "select", src: L("Customer", { disabled: 0 }), req: 1, m: "q", w: 2, blank: __("— choose —"), fill: "receivable" },
			{ f: "amount", label: __("Amount received"), t: "number", req: 1, m: "q", fill: "receivable" },
			{ f: "mode_of_payment", label: __("Mode"), t: "select", src: L("Mode of Payment", { enabled: 1 }), m: "q", def: "Wire Transfer" },
			{ f: "paid_to", label: __("Deposit to"), t: "select", src: L("Account", { account_type: ["in", ["Bank", "Cash"]], is_group: 0 }), m: "s", blank: __("— the mode's account —") },
			{ f: "reference_no", label: __("Bank reference / cheque no."), m: "s", ph: __("From the bank advice") },
			{ f: "reference_date", label: __("Reference date"), t: "date", m: "s", def: today },
			{ f: "_bank_charges", label: __("Bank charges deducted"), t: "number", m: "s", hint: __("The bank credits the amount less these charges") },
			{ f: "posting_date", label: __("Posting date"), t: "date", m: "d", def: today },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "d" },
			{ f: "project", label: __("Project"), t: "select", src: L("Project"), m: "d" },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		], full: (v) => ({ payment_type: "Receive", party_type: "Customer", party: v.customer }),
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Record receipt"), action: "submit", primary: 1 }] },
		// v1.8.4: Receive advance (Finance › Customer advances, a customer or an order): customer, amount, mode — against an order or left on the customer
		"Payment Entry:advance": { doctype: "Payment Entry", preset: { _advance: 1 }, title: __("Receive customer advance"),
			sub: __("Money received before the invoice — against a sales order, or kept on the customer and applied to an invoice later"), fields: [
			{ f: "customer", label: __("Customer"), t: "select", src: L("Customer", { disabled: 0 }), req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "amount", label: __("Amount received"), t: "number", req: 1, m: "q", hint: __("Against an order: blank = the advance still due on it") },
			{ f: "mode_of_payment", label: __("Mode"), t: "select", src: L("Mode of Payment", { enabled: 1 }), m: "q", def: "Wire Transfer" },
			{ f: "sales_order", label: __("Against sales order"), t: "select", src: L("Sales Order", { docstatus: 1, status: ["not in", ["Closed", "Completed", "Cancelled"]] }), m: "s", w: 2, blank: __("— none: kept on the customer —") },
			{ f: "paid_to", label: __("Deposit to"), t: "select", src: L("Account", { account_type: ["in", ["Bank", "Cash"]], is_group: 0 }), m: "s", blank: __("— the mode's account —") },
			{ f: "reference_no", label: __("Bank reference / cheque no."), m: "s", ph: __("From the bank advice") },
			{ f: "reference_date", label: __("Reference date"), t: "date", m: "s", def: today },
			{ f: "posting_date", label: __("Posting date"), t: "date", m: "d", def: today },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		], full: (v) => ({ payment_type: "Receive", party_type: "Customer", party: v.customer }),
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Record advance"), action: "submit", primary: 1 }] },
		"Warranty Claim": { title: __("New warranty claim"), sub: __("Look up the serial — customer, item and warranty follow"), fields: [
			{ f: "serial_no", label: __("Serial no."), t: "select", src: L("Serial No", { status: ["in", ["Delivered", "Active"]] }), m: "q", w: 2, blank: __("— no serial —"), fill: "serial_claim" },
			{ f: "customer", label: __("Customer"), t: "select", src: L("Customer", { disabled: 0 }), req: 1, m: "q", blank: __("— choose —") },
			{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0 }), m: "q" },
			{ f: "complaint", label: __("Complaint"), t: "textarea", req: 1, m: "q", w: 2, ph: __("What the customer reports") },
			{ f: "complaint_date", label: __("Complaint date"), t: "date", req: 1, m: "s", def: today },
			{ f: "complaint_raised_by", label: __("Raised by"), m: "s" },
			{ f: "warranty_amc_status", label: __("Warranty status"), t: "select", opts: "@meta", m: "s" },
			{ f: "warranty_expiry_date", label: __("Warranty expiry"), t: "date", m: "s" },
			{ f: "amc_expiry_date", label: __("AMC expiry"), t: "date", m: "d" },
			{ f: "from_company", label: __("Customer's company / site"), m: "d" },
			{ f: "service_address", label: __("Service address"), t: "textarea", m: "d", w: 2 },
		] },
		"Delivery Trip": { title: __("New delivery trip"), sub: __("Driver, vehicle, departure and the stops in order"), fields: [
			{ f: "driver", label: __("Driver"), t: "select", src: L("Driver", { status: "Active" }), req: 1, m: "q", fill: "driver_vehicle" },
			{ f: "vehicle", label: __("Vehicle"), t: "select", src: L("Vehicle"), req: 1, m: "q" },
			{ f: "_departure_date", label: __("Departure date"), t: "date", m: "q", def: today },
			{ f: "_departure_time", label: __("Departure time"), t: "time", m: "q", def: () => moment().add(30, "minutes").format("HH:mm") },
			{ f: "_route_note", label: __("Route note"), m: "s", w: 2, ph: __("e.g. Jebel Ali → Dubai Marina → JLT") },
			{ f: "driver_address", label: __("Start from (our address)"), t: "select", src: L("Address", { is_your_company_address: 1 }), m: "d", hint: __("Used to estimate the arrival times") },
		], rows: { cols: [{ f: "delivery_note", label: __("Delivery note (ready to dispatch)"), t: "select", src: L("Delivery Note", {}, { query: "trip_notes" }), w: 3, fill: "trip_stop" },
			{ f: "_customer", label: __("Customer"), t: "ro", w: 2 }, { f: "_address", label: __("Deliver to"), t: "ro", w: 2 }], n: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Dispatch"), action: "submit", primary: 1 }] },
		"Employee Advance": { title: __("Employee advance"), sub: __("Cash for a trip or site work — settled by an expense claim or from salary"), fields: [
			{ f: "employee", label: __("Employee"), t: "select", src: L("Employee", { status: "Active" }), req: 1, m: "q" },
			{ f: "advance_amount", label: __("Amount"), t: "number", req: 1, m: "q" },
			{ f: "purpose", label: __("Purpose"), t: "textarea", req: 1, m: "q", w: 2, ph: __("e.g. Site visit to Abu Dhabi — fuel and tolls") },
			{ f: "posting_date", label: __("Date"), t: "date", m: "s", def: today },
			{ f: "mode_of_payment", label: __("Paid by"), t: "select", src: L("Mode of Payment", { enabled: 1 }), m: "s", def: "Cash" },
			{ f: "repay_unclaimed_amount_from_salary", label: __("Recover what is not claimed from salary"), t: "check", m: "s" },
			{ f: "currency", label: __("Currency"), t: "select", src: L("Currency", { enabled: 1 }), m: "d", blank: __("— company currency —") },
			{ f: "advance_account", label: __("Advance account"), t: "select", src: L("Account", { is_group: 0, account_type: "Receivable" }), m: "d", blank: __("— company default —") },
		], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit"), action: "submit", primary: 1 }] },
	};

	C.doc = function (key, preset) {
		const spec = C.DOCS[key];
		const dt = spec.doctype || key; // v1.7.3: one doctype may have several windows (supplier bill / debit note)
		preset = preset || {};
		const covered = hipersign.fm && hipersign.fm.COVERED.includes(dt);
		let mode = (covered && hipersign.fm.mode(dt)) || "Standard";
		const v = Object.assign({}, spec.preset || {}, preset), opt = {}; // v1.8.0: a window may carry fixed values (_site: material request to site)
		spec.fields.forEach((df) => { if (v[df.f] === undefined && df.def !== undefined) v[df.f] = typeof df.def === "function" ? df.def() : df.def; });
		const R = spec.rows, rows = [];
		if (R) { (preset.rows || []).forEach((r) => rows.push(Object.assign({}, r))); while (rows.length < R.n) rows.push({}); }
		const title = () => dt === "Post Dated Cheque" && v.direction === "Issued" ? __("Issue cheque to supplier") : spec.title;
		const sh = C.shell({ title: title(), sub: spec.sub, mode, modes: covered, wide: !!R && R.cols.length > 2,
			onMode: (m) => { read(); mode = m; sh.setMode(m); hipersign.fm.remember(dt, m); draw(); } });
		const att = C.attach(sh, dt, +v.is_return); // v1.7.3: a debit note gets the rules for returns too
		const K = (s) => JSON.stringify(s);
		// v1.7.3: a list may join several sources (purchase orders and goods receipts)
		const src = (s) => !s ? null : Array.isArray(s) ? [].concat(...s.map((x) => opt[K(x)] || [])) : opt[K(s)] || [];
		// v1.8.4: a pick may replace another field's choices (the job card's operations follow the work order)
		const dyn = {};
		const list = (df) => dyn[df.f] ? dyn[df.f] : df.src ? src(df.src) : df.opts === "@meta" ? C.meta_opts(dt, df.f) : df.opts;
		const fmt = (x) => format_currency(x, v.currency || undefined);
		const read = () => {
			// v1.7.3: tick boxes send 1 / 0
			sh.$body.find("[data-f]").each(function () { v[$(this).data("f")] = this.type === "checkbox" ? (this.checked ? 1 : 0) : $(this).val(); });
			sh.$body.find("tr[data-r]").each(function () { const r = rows[+$(this).data("r")]; $(this).find("[data-c]").each(function () { r[$(this).data("c")] = $(this).val(); }); });
		};
		const cell = (c, r) => {
			if (c.t === "stock") return `<td class="c-n hsc-stock" data-stock="${c.of}">${r[c.of] ? (r[c.f] ?? "…") : "—"}</td>`;
			// v1.7.3: values shown, not typed (the customer on a trip stop, the quantity a bill allows back)
			if (c.t === "ro") return `<td class="${c.n ? "c-n" : ""}">${r[c.f] === undefined || r[c.f] === null || r[c.f] === "" ? "—" : esc(c.n ? format_number(r[c.f], null, c.p ?? 2) : r[c.f])}</td>`;
			if (c.t === "select") {
				let l = src(c.src) || [];
				// a value filled from the source document that is not on the list still shows (and is kept)
				if (r[c.f] && !l.some((o) => (o.name ?? o) === r[c.f])) l = [{ name: r[c.f], label: r[c.f] }, ...l];
				return `<td><select data-c="${c.f}">${optHtml(l, r[c.f], "—")}</select></td>`;
			}
			return `<td><input data-c="${c.f}" type="${c.t || "text"}" ${c.t === "number" ? 'step="any"' : ""} value="${esc(r[c.f] ?? (c.t === "date" ? today() : ""))}"></td>`;
		};
		const draw = () => {
			sh.$ov.find(".hsc-head h3").text(title());
			const fields = spec.fields.filter((df) => visible(df, mode) && (!df.show || df.show(v)));
			let h = `<div class="hsc-grid">${fields.map((df) => {
				let l = list(df);
				// v1.8.2: "To" starts on a different warehouse than "From" (a transfer into the same store is refused)
				if (df.differ && l && l.length > 1) {
					const ov = (o) => String(Array.isArray(o) ? o[0] : o.name ?? o);
					const other = v[df.differ] || (list(spec.fields.find((x) => x.f === df.differ) || {}) || []).map(ov)[0];
					if (!v[df.f] || String(v[df.f]) === String(other)) { const o = l.find((x) => ov(x) !== String(other)); if (o) v[df.f] = ov(o); }
				}
				if (df.t === "select" && v[df.f] && l && !l.some((o) => String(Array.isArray(o) ? o[0] : o.name ?? o) === String(v[df.f]))) l = [[v[df.f], v[df.f]], ...l];
				return C.field(Object.assign({}, df, { list: l }), v[df.f]);
			}).join("")}</div>`;
			if (R) {
				h += `<div class="hsc-lines"><table><thead><tr>${R.cols.map((c) => `<th class="${c.t === "number" || c.n ? "c-n" : ""}" style="${c.w ? `width:${c.w * 14}%` : ""}">${esc(c.label)}</th>`).join("")}<th></th></tr></thead><tbody>`
					+ rows.map((r, i) => `<tr data-r="${i}">${R.cols.map((c) => cell(c, r)).join("")}
						<td><button type="button" class="hsc-del">${frappe.utils.icon("close", "xs")}</button></td></tr>`).join("")
					+ `</tbody></table>${R.fixed ? "" : `<div class="hsc-lbtn"><button type="button" class="btn btn-default btn-sm hsc-addr">${frappe.utils.icon("add", "xs")} ${__("Add line")}</button></div>`}</div>`;
				if (R.sum) h += `<div class="hsc-totals"><div>${R.sum.map((f) => `<div class="hsc-tl"><span>${esc((R.cols.find((c) => c.f === f) || {}).label)}</span><b data-sum="${f}">0</b></div>`).join("")}</div><div></div></div>`;
				if (R.net) h += `<div class="hsc-totals hsc-net"></div>`;
			}
			if (v._note) h += `<div class="hsc-note">${frappe.utils.icon("info", "xs")} ${esc(v._note)}</div>`;
			sh.$body.html(h);
			sums();
		};
		// v1.7.2: picking the source document fills what the prototype fills (export order → destination, incoterm…)
		// v1.7.3: the other values go with it, it may fill the lines (rows) and some values always follow the pick (force)
		const filled = {};
		const fill = (df) => {
			if (!df || !df.fill || !v[df.f]) return Promise.resolve();
			return frappe.xcall("hipersign_trading.api.create.fill_doc", { kind: df.fill, name: v[df.f], values: v }).then((r) => {
				const force = r.force || [];
				Object.entries(r.opts || {}).forEach(([k, l]) => { dyn[k] = l; });
				Object.entries(r.values || {}).forEach(([k, val]) => {
					const def = (spec.fields.find((x) => x.f === k) || {}).def;
					if (force.includes(k) || !v[k] || filled[k] !== undefined && String(v[k]) === String(filled[k]) || (typeof def === "function" ? def() : def) === v[k]) { v[k] = val; filled[k] = val; }
				});
				if (r.rows && R) { rows.splice(0, rows.length, ...r.rows.map((x) => Object.assign({}, x))); if (!rows.length && !R.fixed) rows.push({}); }
				v._note = r.note || "";
				draw();
			}).catch(() => {});
		};
		const sums = () => {
			if (!R || !(R.sum || R.net)) return;
			read();
			const t = {};
			(R.sum || []).forEach((f) => { t[f] = rows.reduce((a, r) => a + flt(r[f]), 0); sh.$body.find(`[data-sum="${f}"]`).text(format_currency(t[f])); });
			if (R.balance) { // v1.7.2: the prototype's Empty / Balanced / Difference badge
				const [d, c] = R.sum, diff = flt(t[d] - t[c], 2);
				const b = !t[d] && !t[c] ? ["", __("Empty")] : !diff ? ["green", __("Balanced")] : ["orange", __("Difference {0}", [format_currency(Math.abs(diff))])];
				sh.$body.find(".hsc-totals > div:last-child").html(`<span class="hsc-badge ${b[0]}">${esc(b[1])}</span>`);
			}
			if (R.net) { // v1.7.3: net · VAT (the company's template) · total, as on the order forms
				const [q, rt] = R.net, net = rows.reduce((a, r) => a + flt(r[q]) * flt(r[rt]), 0), vr = flt(v._vat_rate), vat = net * vr / 100;
				sh.$body.find(".hsc-net").html(`<div><div class="hsc-tl"><span>${__("Net")}</span><b>${fmt(net)}</b></div><div class="hsc-tl"><span>${__("VAT {0}%", [vr])}</span><b>${fmt(vat)}</b></div>
					<div class="hsc-tl hsc-tt"><span>${esc(R.total || __("Total"))}</span><b>${fmt(net + vat)}</b></div></div><div></div>`);
			}
		};
		sh.$body.on("change", "[data-f]", function () {
			read();
			const df = spec.fields.find((x) => x.f === $(this).data("f") && (!x.show || x.show(v)));
			if (df && df.fill) return fill(df);
			if (df && df.redraw) draw(); else sums();
		});
		sh.$body.on("input change", "[data-c]", sums);
		sh.$body.on("change", "select[data-c]", function () {
			const $tr = $(this).closest("tr"), r = rows[+$tr.data("r")], code = $(this).val();
			// v1.7.3: a line that fills from its document (the trip stop's customer and address)
			const col = R && R.cols.find((c) => c.f === $(this).data("c"));
			if (col && col.fill) {
				read();
				return frappe.xcall("hipersign_trading.api.create.fill_doc", { kind: col.fill, name: code, values: v }).then((x) => { Object.assign(r, x.values || {}); draw(); }).catch(() => {});
			}
			// v1.7.2: "In stock" next to the item (purchase request)
			const $st = $tr.find(`[data-stock="${$(this).data("c")}"]`);
			if (!$st.length) return;
			if (!code) { r._stock = undefined; return $st.text("—"); }
			$st.text("…");
			frappe.xcall("hipersign_trading.api.create.stock_now", { item_code: code }).then((q) => { r._stock = format_number(q, null, 0); $st.text(r._stock); });
		});
		sh.$body.on("click", ".hsc-addr", () => { read(); rows.push({}); draw(); });
		sh.$body.on("click", ".hsc-del", function () { read(); rows.splice(+$(this).closest("tr").data("r"), 1); if (!rows.length && !R.fixed) rows.push({}); draw(); });
		const acts = spec.actions || [{ label: __("Save"), action: "save", primary: 1 }];
		sh.$fl.html(`<button type="button" class="btn btn-default hsc-full">${__("Open full form")} ↗</button>`);
		sh.$fl.on("click", ".hsc-full", () => { read(); sh.close(); const fv = spec.full ? spec.full(v) : {}; hipersign.create && hipersign.create.new_doc ? hipersign.create.new_doc(dt, fv) : frappe.new_doc(dt, fv); });
		sh.$fr.html(`<button type="button" class="btn btn-default hsc-cancel">${__("Cancel")}</button>` + acts.map((a, i) =>
			`<button type="button" class="btn ${a.primary ? "btn-primary" : "btn-default"} hsc-act" data-i="${i}">${a.primary ? frappe.utils.icon("check", "xs") + " " : ""}${esc(a.label)}</button>`).join(""));
		sh.$fr.on("click", ".hsc-cancel", sh.close);
		sh.$fr.on("click", ".hsc-act", function () {
			read();
			const miss = spec.fields.filter((df) => df.req && (!df.show || df.show(v)) && (v[df.f] === undefined || v[df.f] === null || v[df.f] === "")).map((df) => df.label);
			if (miss.length) return frappe.msgprint(__("Please fill in: {0}", [miss.join(", ")]));
			const a = acts[+$(this).data("i")], btn = this;
			$(btn).prop("disabled", true);
			const values = Object.assign({}, v);
			delete values._note;
			att.save("hipersign_trading.api.create.save_doc", { doctype: dt, values, rows }, a.action).then((r) => {
				sh.close();
				frappe.show_alert({ message: r.message, indicator: r.needs_documents ? "orange" : "green" }, 7);
				if (hipersign.panel && hipersign.panel.has(dt)) hipersign.panel.open(dt, r.name); else frappe.set_route("Form", dt, r.name);
				if (window.cur_list && cur_list.doctype === dt) cur_list.refresh();
			}).catch(() => {}).finally(() => $(btn).prop("disabled", false));
		});
		// load every choice list the form uses (and the doctype for "@meta" options), then draw
		const flat = (s) => (Array.isArray(s) ? s : [s]);
		const srcs = [...spec.fields.filter((d) => d.src).flatMap((d) => flat(d.src)), ...(R ? R.cols.filter((c) => c.src).flatMap((c) => flat(c.src)) : [])];
		const uniq = [...new Map(srcs.map((x) => [K(x), x])).values()];
		sh.$body.html(`<div class="hsc-loading">${__("Loading…")}</div>`);
		Promise.all([with_meta(dt), ...uniq.map((x) => frappe.xcall("hipersign_trading.api.create.link_options", { doctype: x.dt, query: JSON.stringify({ filters: x.filters, query: x.query }) })
			.then((r) => { opt[K(x)] = r || []; }).catch(() => { opt[K(x)] = []; }))]).then(() => {
			draw();
			read();
			// fill from what was passed in or picked first (a customer, an order …)
			spec.fields.filter((x) => x.fill && v[x.f] && visible(x, mode)).slice(0, 1).reduce((p, df) => p.then(() => fill(df)), Promise.resolve());
		});
		return sh;
	};

	// ------------------------------------------------------------ v1.7.2: "Attach documents — kept with the record when you save"
	// (the prototype's box): the document rules for the doctype, a file per document type, uploaded after the save with its type,
	// then the submit — so a blocking rule is met in one go
	C.attach = function (sh, dt, is_return) {
		const st = { rules: [], files: {} };
		const $box = $(`<div class="hsc-att" style="display:none"></div>`).insertAfter(sh.$body);
		const lv = (r) => r.level === "Block" ? `<span class="hsc-badge red">${__("Blocks next step")}</span>` : r.level === "Required" ? `<span class="hsc-badge orange">${__("Required")}</span>` : `<span class="hsc-badge">${__("Optional")}</span>`;
		const draw = () => {
			if (!st.rules.length) return $box.hide();
			$box.show().html(`<div class="hsc-att-h">${frappe.utils.icon("attachment", "sm")} <b>${__("Attach documents")}</b> <span>— ${__("kept with the record when you save")}</span></div>`
				+ st.rules.map((r, i) => `<div class="hsc-att-r"><div class="hsc-att-t"><div><b>${esc(__(r.type))}</b> ${lv(r)}</div>
					${r.note || r.min_amount ? `<small>${esc(r.note || __("From {0}", [format_currency(r.min_amount)]))}</small>` : ""}
					${st.files[i] ? `<small class="hsc-att-f">${frappe.utils.icon("file", "xs")} ${esc(st.files[i].name)}</small>` : ""}</div>
					<label class="btn btn-default btn-sm hsc-att-b">${frappe.utils.icon("upload", "xs")} ${st.files[i] ? __("Replace") : __("Attach")}<input type="file" data-i="${i}" hidden></label></div>`).join(""));
		};
		$box.on("change", "input[type=file]", function () { const f = this.files[0]; if (f) { st.files[+$(this).data("i")] = f; draw(); } });
		frappe.xcall("hipersign_trading.api.docs.new_doc_rules", { doctype: dt, is_return: is_return ? 1 : 0 }).then((r) => { st.rules = r || []; draw(); }).catch(() => {});
		st.has = () => Object.keys(st.files).length > 0;
		st.upload = (name) => Promise.all(Object.entries(st.files).map(([i, f]) => {
			const fd = new FormData();
			fd.append("file", f, f.name); fd.append("doctype", dt); fd.append("docname", name); fd.append("is_private", 1);
			return fetch("/api/method/upload_file", { method: "POST", body: fd, headers: { "X-Frappe-CSRF-Token": frappe.csrf_token, Accept: "application/json" } })
				.then((x) => x.json()).then((j) => {
					if (j.message && j.message.name) return frappe.xcall("hipersign_trading.api.docs.set_file_type", { file: j.message.name, document_type: st.rules[+i].type });
					frappe.show_alert({ message: __("{0} could not be attached ({1}) — attach it on the record", [f.name, __(st.rules[+i].type)]), indicator: "red" }, 9);
				}).catch(() => frappe.show_alert({ message: __("{0} could not be attached — attach it on the record", [f.name]), indicator: "red" }, 9));
		}));
		// save (as a draft when files must go first) → upload → submit
		st.save = (method, args, action) => {
			const later = st.has() && action === "submit";
			return frappe.xcall(method, Object.assign({}, args, { action: later ? "save" : action }))
				.then((r) => (st.has() ? st.upload(r.name).then(() => r) : r))
				.then((r) => (later ? frappe.xcall("hipersign_trading.api.create.submit_saved", { doctype: r.doctype || dt, name: r.name }) : r));
		};
		return st;
	};

	// ------------------------------------------------------------ routing: every "New …" for these opens the modal
	C.new = function (dt, values) {
		if (DT_KIND[dt]) {
			const v = Object.assign({}, values || {});
			// the customer / supplier a dashboard's "+ Quotation" passes as route options
			if (!v.party) v.party = v.party_name || v.customer || v.supplier || undefined;
			if (!v.party) delete v.party;
			return C.open(DT_KIND[dt], v);
		}
		values = values || {};
		// v1.7.3: a debit note is a supplier bill with "Is Return"; a payment to a supplier or a transfer stays on the full form
		if (dt === "Purchase Invoice" && +values.is_return) return C.doc("Purchase Invoice:return", values);
		if (dt === "Sales Invoice" && +values.is_return) return C.doc("Sales Invoice:return", values);
		if (dt === "Payment Entry") {
			if ((values.payment_type && values.payment_type !== "Receive") || (values.party_type && values.party_type !== "Customer")) return hipersign.create.new_doc(dt, values);
			if (values.party && !values.customer) values = Object.assign({}, values, { customer: values.party });
		}
		if (C.DOCS[dt]) return C.doc(dt, values);
		if (C.PICK[dt]) return C.pick(dt, values);
		return hipersign.qc.open(dt, { values: values || {} });
	};

	// v1.7.1: deliveries, receipts and invoices are made from their order, as on the prototype — "New" asks which one
	C.PICK = {
		"Delivery Note": { kind: "deliver", title: __("New delivery"), sub: __("Pick the confirmed sales order to deliver — quantities, warehouse and driver follow"),
			label: __("Sales order to deliver"), src: { dt: "Sales Order", filters: { docstatus: 1, per_delivered: ["<", 100], status: ["not in", ["Closed", "On Hold", "Completed"]] } },
			party: "customer" },
		"Purchase Receipt": { kind: "receive", title: __("Receive goods"), sub: __("Pick the supplier order being received — quantities, rejections and warehouse follow"),
			label: __("Purchase order to receive"), src: { dt: "Purchase Order", filters: { docstatus: 1, per_received: ["<", 100], status: ["not in", ["Closed", "On Hold", "Completed"]] } },
			party: "supplier" },
		"Sales Invoice": { kind: "invoice", title: __("New tax invoice"), sub: __("Invoice what was delivered — pick the delivery note"),
			label: __("Delivery note to invoice"), src: { dt: "Delivery Note", filters: { docstatus: 1, per_billed: ["<", 100], is_return: 0, status: ["not in", ["Closed"]] } },
			party: "customer", other: __("Invoice without a delivery (services, advance)") },
	};
	C.pick = function (dt, values) {
		const p = C.PICK[dt];
		const sh = C.shell({ title: p.title, sub: p.sub });
		sh.$body.html(`<div class="hsc-loading">${__("Loading…")}</div>`);
		frappe.xcall("hipersign_trading.api.create.link_options", { doctype: p.src.dt, query: JSON.stringify({ filters: p.src.filters }) }).then((list) => {
			list = list || [];
			sh.$body.html(`<div class="hsc-grid">${C.field({ f: "source", label: p.label, t: "select", req: 1, w: 2, list }, values.source || (list[0] || {}).name || "")}</div>`
				+ (list.length ? "" : `<div class="hsc-note">${esc(__("Nothing is waiting — confirm an order first, or open the full form."))}</div>`));
			sh.$fl.html(`<button type="button" class="btn btn-default hsc-full">${p.other ? esc(p.other) : __("Open full form")} ↗</button>`);
			sh.$fl.on("click", ".hsc-full", () => { sh.close(); hipersign.create.new_doc(dt, values || {}); });
			sh.$fr.html(`<button type="button" class="btn btn-default hsc-cancel">${__("Cancel")}</button><button type="button" class="btn btn-primary hsc-go" ${list.length ? "" : "disabled"}>${__("Continue")} →</button>`);
			sh.$fr.on("click", ".hsc-cancel", sh.close);
			sh.$fr.on("click", ".hsc-go", () => {
				const src = sh.$body.find('[data-f="source"]').val();
				if (!src) return frappe.msgprint(__("Please fill in: {0}", [p.label]));
				sh.close();
				C.flow(p.kind, src, () => { if (window.cur_list && cur_list.doctype === dt) cur_list.refresh(); });
			});
		}).catch(() => sh.close());
		return sh;
	};

	// v1.7.1: the list's "Add …" button, the + New menu and frappe.new_doc open the prototype's modal for every covered form
	// (not when a Link field asks for a new record, nor when the full form is asked for explicitly)
	C.routes_new = (dt) => !(frappe.boot.hipersign || {}).no_create_modal && (!!DT_KIND[dt] || !!C.DOCS[dt] || !!C.PICK[dt]);
	const _new_doc = frappe.new_doc;
	frappe.new_doc = function (doctype, opts, init_callback) {
		const r = frappe.get_route() || [];
		const on_form = r[0] === "Form" && r[1] === doctype;
		if (!init_callback && !frappe._from_link && !on_form && C.routes_new(doctype) && frappe.model.can_create(doctype)) {
			const ro = Object.assign({}, typeof opts === "object" && opts ? opts : {}, frappe.route_options || {});
			frappe.route_options = null;
			return new Promise((resolve) => { C.new(doctype, ro); resolve(); });
		}
		return _new_doc.apply(this, arguments);
	};
})();
