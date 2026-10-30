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
			],
			lines: { avail: 1, margin: 0, buying: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Submit for approval"), action: "submit", primary: 1 }],
		},
	};

	C.has = (dt) => !!DT_KIND[dt] || !!(C.DOCS && C.DOCS[dt]) || (hipersign.qc && hipersign.qc.has(dt));

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
		const st = { v: Object.assign({}, preset), lines: [], o: null, p: {}, rates: {}, prospect: false };
		(preset.items || []).forEach((r) => st.lines.push({ item_code: r.item_code, qty: r.qty, rate: r.rate, discount: r.discount }));
		while (st.lines.length < 3) st.lines.push({});
		spec.fields.forEach((df) => { if (st.v[df.f] === undefined && df.def !== undefined) st.v[df.f] = typeof df.def === "function" ? df.def() : df.def; });
		const sh = C.shell({ title: spec.title, sub: spec.sub, mode, modes: 1, wide: 1,
			onMode: (m) => { read(); mode = m; sh.setMode(m); hipersign.fm && hipersign.fm.remember(dt, m); draw(); } });
		sh.$body.html(`<div class="hsc-loading">${__("Loading…")}</div>`);

		const read = () => {
			sh.$body.find("[data-f]").each(function () { const f = $(this).data("f"); st.v[f] = this.type === "checkbox" ? (this.checked ? 1 : 0) : $(this).val(); });
			sh.$body.find(".hsc-line").each(function () {
				const i = +$(this).data("i"), L = st.lines[i]; if (!L) return;
				L.item_code = $(this).find(".l-it").val(); L.qty = $(this).find(".l-q").val(); L.rate = $(this).find(".l-r").val(); L.discount = $(this).find(".l-d").val();
			});
		};
		const src = (df) => (df.src || "").startsWith("@") ? (st.p[df.src.slice(1)] || []) : (st.o[df.src] || []);

		const draw = () => {
			const P = spec.party;
			const partyList = [...(st.o[P.src] || []), ...(P.lead ? (st.o.leads || []).map((l) => ({ name: l.name, label: `${l.label} · ${__("prospect")}` })) : [])];
			let h = `<div class="hsc-grid">`;
			h += C.field({ f: P.f, label: P.label, t: "select", list: partyList, add: P.add, blank: undefined, req: 1 }, st.prospect ? "__add__" : st.v.party);
			if (st.prospect) {
				h += C.field(spec.fields[0], st.v[spec.fields[0].f]);
				h += `</div><div class="hsc-box"><div class="hsc-grid">` + spec.prospect.filter((df) => !df.show || df.show(st.v)).map((df) => C.field(Object.assign({}, df, { list: df.src ? st.o[df.src] : df.opts }), st.v[df.f] ?? (df.def || ""))).join("") + `</div></div><div class="hsc-grid">`;
				spec.fields.slice(1).filter((df) => visible(df, mode) && !(df.src || "").startsWith("@")).forEach((df) => { h += C.field(Object.assign({}, df, { list: src(df) }), st.v[df.f]); });
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
			const vat = net * flt(st.o.vat_rate) / 100, tot = net + vat;
			let left = `<div class="hsc-tl"><span>${__("Net")}</span><b>${fmt(net)}</b></div><div class="hsc-tl"><span>${__("VAT {0}%", [flt(st.o.vat_rate)])}</span><b>${fmt(vat)}</b></div>
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
				if (p.currency && (kind === "purchase_order" || !st.v.currency)) st.v.currency = p.currency;
				if (p.incoterm && !st.v.incoterm) st.v.incoterm = p.incoterm;
				st.v.contact_person = (p.contacts[0] || {}).name || "";
				const ship = p.addresses.find((a) => a.shipping) || p.addresses[0], bill = p.addresses.find((a) => a.billing) || p.addresses[0];
				st.v.shipping_address = ship ? ship.name : ""; st.v.billing_address = bill ? bill.name : "";
				st.p.rate = 1;
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
			frappe.xcall("hipersign_trading.api.create.save", { kind, values, lines, action: a.action }).then((r) => {
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

		frappe.xcall("hipersign_trading.api.create.options", { kind }).then((o) => {
			st.o = o;
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
			const df = { f: f.fieldname, label: f.label, req: f.reqd, ph: f.placeholder, hint: f.description, w: t === "Small Text" || t === "Text" ? 2 : 1 };
			if (t === "Select") Object.assign(df, { t: "select", list: (f.options || "").split("\n").filter((x) => x !== ""), blank: f.reqd ? undefined : "—" });
			else if (t === "Link") Object.assign(df, { t: "select", list: links[f.options] || [], blank: f.reqd ? undefined : "—" });
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
		const need = [...new Set(fields.filter((f) => f.fieldtype === "Link").map((f) => f.options))];
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
	const L = (dt, filters, extra) => Object.assign({ dt, filters: filters || {} }, extra || {});
	const MODES_SHIP = [["Sea", __("Sea")], ["Air", __("Air")], ["Land", __("Land")]];
	C.DOCS = {
		"Import Shipment": { title: __("New import shipment"), sub: __("For an approved import order — documents and charges are added on the shipment"), fields: [
			{ f: "purchase_order", label: __("Purchase order"), t: "select", src: L("Purchase Order", { docstatus: 1, per_received: ["<", 100] }), req: 1, m: "q", w: 2 },
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
		] },
		"Export Shipment": { title: __("New export shipment"), sub: __("Book the shipment for a confirmed export order — 0% VAT needs proof of export"), fields: [
			{ f: "sales_order", label: __("Export order"), t: "select", src: L("Sales Order", { docstatus: 1, per_delivered: ["<", 100] }), req: 1, m: "q", w: 2 },
			{ f: "mode", label: __("Mode"), t: "select", opts: MODES_SHIP, def: "Land", m: "q" },
			{ f: "port_of_loading", label: __("Port / border of loading"), m: "q", ph: "Hatta border (Oman)" },
			{ f: "destination", label: __("Destination"), m: "q", ph: "Muscat, Oman" },
			{ f: "incoterm", label: __("Incoterm"), t: "select", src: L("Incoterm"), m: "s" },
			{ f: "forwarder", label: __("Forwarder / transporter"), t: "select", src: L("Supplier", { disabled: 0 }), m: "s" },
			{ f: "etd", label: __("Planned departure (ETD)"), t: "date", m: "q", def: () => plus(3) },
			{ f: "_transit_days", label: __("Transit days"), t: "number", m: "s", def: 2 },
			{ f: "re_export_of", label: __("Re-export of import"), t: "select", src: L("Import Shipment"), m: "d", blank: __("No — local stock") },
		] },
		"Material Request": { title: __("New purchase request"), sub: __("Ask purchasing to buy items"), fields: [
			{ f: "_department", label: __("Department"), t: "select", src: L("Department", { is_group: 0 }), m: "s" },
			{ f: "schedule_date", label: __("Needed by"), t: "date", m: "q", def: () => plus(7) },
			{ f: "_reason", label: __("Reason"), m: "s", w: 2 },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_purchase_item: 1 }), w: 3 }, { f: "qty", label: __("Qty"), t: "number" }], n: 2 },
			actions: [{ label: __("Save"), action: "save" }, { label: __("Submit request"), action: "submit", primary: 1 }] },
		"Stock Entry": { title: __("Stock transfer"), sub: __("Move stock between warehouses"), fields: [
			{ f: "from_warehouse", label: __("From"), t: "select", src: L("Warehouse", { is_group: 0 }), req: 1, m: "q" },
			{ f: "to_warehouse", label: __("To"), t: "select", src: L("Warehouse", { is_group: 0 }), req: 1, m: "q" },
			{ f: "posting_date", label: __("Transfer date"), t: "date", m: "s", def: today },
			{ f: "_requested_by", label: __("Requested by"), m: "s" },
			{ f: "_reason", label: __("Reason"), m: "s", w: 2 },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_stock_item: 1 }), w: 3 }, { f: "qty", label: __("Quantity"), t: "number" }], n: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Transfer"), action: "submit", primary: 1 }] },
		"Stock Reconciliation": { title: __("Stock count"), sub: __("Count and reconcile — differences go to the Warehouse Manager for approval"), fields: [
			{ f: "_reason", label: __("Reason"), t: "select", opts: ["Cycle count — damaged cartons", "Cycle count — miscount on receipt", "Breakage in warehouse", "Item found — not booked", "Theft or loss", "Year-end physical count"].map((x) => [x, __(x)]), m: "q", w: 2 },
		], rows: { cols: [{ f: "item_code", label: __("Item"), t: "select", src: L("Item", { disabled: 0, is_stock_item: 1 }), w: 3 }, { f: "warehouse", label: __("Warehouse"), t: "select", src: L("Warehouse", { is_group: 0 }), w: 2 },
			{ f: "qty", label: __("Counted quantity"), t: "number" }], n: 1 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Send for approval"), action: "submit", primary: 1 }] },
		"Journal Entry": { title: __("New journal entry"), sub: __("Manual entry — debits and credits must agree; large entries need a supporting document"), fields: [
			{ f: "posting_date", label: __("Posting date"), t: "date", m: "q", def: today },
			{ f: "user_remark", label: __("Memo"), m: "q" },
		], rows: { cols: [{ f: "account", label: __("Account"), t: "select", src: L("Account", { is_group: 0 }), w: 3 }, { f: "debit", label: __("Debit"), t: "number" }, { f: "credit", label: __("Credit"), t: "number" }], n: 2, sum: ["debit", "credit"] },
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
		] },
		"Expense Claim": { title: __("New expense claim"), sub: __("Receipts with the supplier's TRN let the VAT be recovered"), fields: [
			{ f: "employee", label: __("Employee"), t: "select", src: L("Employee", { status: "Active" }), req: 1, m: "q" },
			{ f: "_purpose", label: __("Purpose"), m: "q" },
			{ f: "cost_center", label: __("Cost centre"), t: "select", src: L("Cost Center", { is_group: 0 }), m: "s" },
		], rows: { cols: [{ f: "expense_date", label: __("Date"), t: "date" }, { f: "expense_type", label: __("Type"), t: "select", src: L("Expense Claim Type"), w: 2 },
			{ f: "description", label: __("What, where, with whom"), w: 2 }, { f: "amount", label: __("Amount (AED)"), t: "number" }], n: 1, sum: ["amount"] } },
		"Leave Application": { title: __("Leave request"), sub: __("Goes to the employee's leave approver"), fields: [
			{ f: "employee", label: __("Employee"), t: "select", src: L("Employee", { status: "Active" }), req: 1, m: "q", w: 2 },
			{ f: "leave_type", label: __("Leave type"), t: "select", src: L("Leave Type"), req: 1, m: "q" },
			{ f: "from_date", label: __("From"), t: "date", req: 1, m: "q", def: () => plus(7) },
			{ f: "to_date", label: __("To"), t: "date", req: 1, m: "q", def: () => plus(9) },
			{ f: "description", label: __("Reason"), m: "q", w: 2 },
		] },
		"Letter of Credit": { title: __("New LC application"), sub: __("Import letter of credit for a supplier order — the bank blocks the cash margin"), fields: [
			{ f: "purchase_order", label: __("Purchase order"), t: "select", src: L("Purchase Order", { docstatus: 1, per_received: ["<", 100] }), req: 1, m: "q", w: 2 },
			{ f: "issuing_bank", label: __("Issuing bank"), t: "select", src: L("Bank"), req: 1, m: "q" },
			{ f: "amount", label: __("Amount (order currency)"), t: "number", m: "q", hint: __("Empty = the order total") },
			{ f: "tenor", label: __("Payment"), t: "select", opts: ["At sight", "Usance 30 days", "Usance 60 days", "Usance 90 days", "Usance 120 days", "Usance 180 days"].map((x) => [x, __(x)]), m: "q" },
			{ f: "tolerance_pct", label: __("Tolerance ±%"), t: "number", def: 5, m: "s" },
			{ f: "margin_pct", label: __("Cash margin %"), t: "number", def: 10, m: "s" },
			{ f: "latest_shipment_date", label: __("Latest shipment date"), t: "date", m: "s", def: () => plus(45) },
			{ f: "expiry_date", label: __("Expiry date"), t: "date", m: "q", def: () => plus(75) },
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
		] },
		"Company Document": { title: __("Add company document"), sub: __("Licence, registration or certificate — renewal reminders follow the expiry"), fields: [
			{ f: "company", label: __("Company"), t: "select", src: L("Company"), req: 1, m: "q" },
			{ f: "document_type", label: __("Document type"), t: "select", src: L("Company Document Type"), req: 1, m: "q" },
			{ f: "document_number", label: __("Number"), m: "q" },
			{ f: "authority", label: __("Issuing authority"), m: "s" },
			{ f: "issue_date", label: __("Issue date"), t: "date", m: "s" },
			{ f: "expiry_date", label: __("Expiry date"), t: "date", m: "q" },
			{ f: "responsible_user", label: __("Responsible"), t: "select", src: L("User", { user_type: "System User", enabled: 1 }), m: "s" },
			{ f: "notes", label: __("Notes"), t: "textarea", m: "d", w: 2 },
		] },
	};

	C.doc = function (dt, preset) {
		const spec = C.DOCS[dt];
		preset = preset || {};
		let mode = (hipersign.fm && hipersign.fm.COVERED.includes(dt) && hipersign.fm.mode(dt)) || "Standard";
		const v = Object.assign({}, preset), opt = {};
		spec.fields.forEach((df) => { if (v[df.f] === undefined && df.def !== undefined) v[df.f] = typeof df.def === "function" ? df.def() : df.def; });
		const R = spec.rows, rows = [];
		if (R) { (preset.rows || []).forEach((r) => rows.push(Object.assign({}, r))); while (rows.length < R.n) rows.push({}); }
		const title = () => dt === "Post Dated Cheque" && v.direction === "Issued" ? __("Issue cheque to supplier") : spec.title;
		const sh = C.shell({ title: title(), sub: spec.sub, mode, modes: hipersign.fm && hipersign.fm.COVERED.includes(dt), wide: !!R && R.cols.length > 2,
			onMode: (m) => { read(); mode = m; sh.setMode(m); hipersign.fm.remember(dt, m); draw(); } });
		const src = (s) => s ? opt[JSON.stringify(s)] || [] : null;
		const read = () => {
			sh.$body.find("[data-f]").each(function () { v[$(this).data("f")] = $(this).val(); });
			sh.$body.find("tr[data-r]").each(function () { const r = rows[+$(this).data("r")]; $(this).find("[data-c]").each(function () { r[$(this).data("c")] = $(this).val(); }); });
		};
		const draw = () => {
			sh.$ov.find(".hsc-head h3").text(title());
			const fields = spec.fields.filter((df) => visible(df, mode) && (!df.show || df.show(v)));
			let h = `<div class="hsc-grid">${fields.map((df) => C.field(Object.assign({}, df, { list: df.src ? src(df.src) : df.opts, noblank: df.req && df.t === "select" ? 0 : 0 }), v[df.f])).join("")}</div>`;
			if (R) {
				h += `<div class="hsc-lines"><table><thead><tr>${R.cols.map((c) => `<th class="${c.t === "number" ? "c-n" : ""}" style="${c.w ? `width:${c.w * 14}%` : ""}">${esc(c.label)}</th>`).join("")}<th></th></tr></thead><tbody>`
					+ rows.map((r, i) => `<tr data-r="${i}">${R.cols.map((c) => `<td>${c.t === "select" ? `<select data-c="${c.f}">${optHtml(src(c.src), r[c.f], "—")}</select>`
						: `<input data-c="${c.f}" type="${c.t || "text"}" ${c.t === "number" ? 'step="any"' : ""} value="${esc(r[c.f] ?? (c.t === "date" ? today() : ""))}">`}</td>`).join("")}
						<td><button type="button" class="hsc-del">${frappe.utils.icon("close", "xs")}</button></td></tr>`).join("")
					+ `</tbody></table><div class="hsc-lbtn"><button type="button" class="btn btn-default btn-sm hsc-addr">${frappe.utils.icon("add", "xs")} ${__("Add line")}</button></div></div>`;
				if (R.sum) h += `<div class="hsc-totals"><div>${R.sum.map((f) => `<div class="hsc-tl"><span>${esc((R.cols.find((c) => c.f === f) || {}).label)}</span><b data-sum="${f}">0</b></div>`).join("")}</div><div></div></div>`;
			}
			sh.$body.html(h);
			sums();
		};
		const sums = () => { if (!R || !R.sum) return; read(); R.sum.forEach((f) => sh.$body.find(`[data-sum="${f}"]`).text(format_currency(rows.reduce((a, r) => a + flt(r[f]), 0)))); };
		sh.$body.on("change", "[data-f]", function () { const df = spec.fields.find((x) => x.f === $(this).data("f")); if (df && df.redraw) { read(); draw(); } });
		sh.$body.on("input change", "[data-c]", sums);
		sh.$body.on("click", ".hsc-addr", () => { read(); rows.push({}); draw(); });
		sh.$body.on("click", ".hsc-del", function () { read(); rows.splice(+$(this).closest("tr").data("r"), 1); if (!rows.length) rows.push({}); draw(); });
		const acts = spec.actions || [{ label: __("Save"), action: "save", primary: 1 }];
		sh.$fl.html(`<button type="button" class="btn btn-default hsc-full">${__("Open full form")} ↗</button>`);
		sh.$fl.on("click", ".hsc-full", () => { sh.close(); hipersign.create && hipersign.create.new_doc ? hipersign.create.new_doc(dt, {}) : frappe.new_doc(dt); });
		sh.$fr.html(`<button type="button" class="btn btn-default hsc-cancel">${__("Cancel")}</button>` + acts.map((a, i) =>
			`<button type="button" class="btn ${a.primary ? "btn-primary" : "btn-default"} hsc-act" data-i="${i}">${a.primary ? frappe.utils.icon("check", "xs") + " " : ""}${esc(a.label)}</button>`).join(""));
		sh.$fr.on("click", ".hsc-cancel", sh.close);
		sh.$fr.on("click", ".hsc-act", function () {
			read();
			const miss = spec.fields.filter((df) => df.req && (!df.show || df.show(v)) && !v[df.f]).map((df) => df.label);
			if (miss.length) return frappe.msgprint(__("Please fill in: {0}", [miss.join(", ")]));
			const a = acts[+$(this).data("i")], btn = this;
			$(btn).prop("disabled", true);
			frappe.xcall("hipersign_trading.api.create.save_doc", { doctype: dt, values: v, rows, action: a.action }).then((r) => {
				sh.close();
				frappe.show_alert({ message: r.message, indicator: r.needs_documents ? "orange" : "green" }, 7);
				if (hipersign.panel && hipersign.panel.has(dt)) hipersign.panel.open(dt, r.name); else frappe.set_route("Form", dt, r.name);
				if (window.cur_list && cur_list.doctype === dt) cur_list.refresh();
			}).catch(() => {}).finally(() => $(btn).prop("disabled", false));
		});
		// load every choice list the form uses, then draw
		const srcs = [...spec.fields.filter((d) => d.src).map((d) => d.src), ...(R ? R.cols.filter((c) => c.src).map((c) => c.src) : [])];
		const uniq = [...new Map(srcs.map((s) => [JSON.stringify(s), s])).values()];
		sh.$body.html(`<div class="hsc-loading">${__("Loading…")}</div>`);
		Promise.all(uniq.map((s) => frappe.xcall("hipersign_trading.api.create.link_options", { doctype: s.dt, query: JSON.stringify({ filters: s.filters }) })
			.then((r) => { opt[JSON.stringify(s)] = r || []; }).catch(() => { opt[JSON.stringify(s)] = []; }))).then(draw);
		return sh;
	};

	// ------------------------------------------------------------ routing: every "New …" for these opens the modal
	C.new = function (dt, values) {
		if (DT_KIND[dt]) return C.open(DT_KIND[dt], values || {});
		if (C.DOCS[dt]) return C.doc(dt, values || {});
		return hipersign.qc.open(dt, { values: values || {} });
	};
})();
