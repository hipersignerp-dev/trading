// Hipersign ERP v1.7.3 — supplier quotations compared side by side (prototype "Compare quotations" / award).
// Route: hipersign-compare/<RFQ>; without an RFQ it lists the RFQs that have quotations.
frappe.pages["hipersign-compare"].on_page_load = function (wrapper) {
	const ui = hipersign.ui, esc = frappe.utils.escape_html;
	const v = ui.page(wrapper, { title: __("Supplier Quotation Comparison"), desc: __("Every supplier's offer per item, in its currency and in AED, with lead time and terms — the lowest price is marked; award per item and the purchase orders are made.") });
	const st = { rfq: null, data: null, pick: {} };
	const money = (n, c) => `${c ? esc(c) + " " : ""}${format_number(n, null, 2)}`;

	function list() {
		ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.compare.open_rfqs").then((rows) => {
			v.$body.html(ui.card(__("Requests for quotation with offers"), rows.length ? `<div class="hsx-tw"><table class="hsx-t"><thead><tr><th>${__("RFQ")}</th><th>${__("Date")}</th>
				<th class="num">${__("Suppliers asked")}</th><th class="num">${__("Quotations")}</th><th>${__("Status")}</th><th></th></tr></thead><tbody>${rows.map((r) => `<tr>
				<td><span class="hsx-code">${esc(r.rfq)}</span></td><td>${frappe.datetime.str_to_user(r.transaction_date || "")}</td><td class="num">${r.suppliers}</td><td class="num">${r.quotes}</td>
				<td>${r.ordered ? `<span class="hsx-pill green">${__("Ordered")}</span>` : `<span class="hsx-pill blue">${__("Quotes received")}</span>`}</td>
				<td><button class="btn btn-primary btn-xs hsc-open" data-rfq="${esc(r.rfq)}">${__("Compare")}</button></td></tr>`).join("")}</tbody></table></div>`
				: `<div class="hsx-empty">${__("No supplier quotations against an RFQ yet. Send an RFQ from Supplier Purchasing → Purchase requests.")}</div>`));
		});
	}

	function draw() {
		const d = st.data, S = d.suppliers;
		if (!S.length) return v.$body.html(ui.card(d.rfq, `<div class="hsx-empty">${__("No quotations received for this RFQ yet.")}</div>`));
		const head = `<tr><th>${__("Item")}</th><th class="num">${__("Qty")}</th>${S.map((s) => `<th class="num">${esc(s.name)}<br><small class="text-muted">${esc(s.quotation)} · ${esc(s.currency)}${s.expired ? " · " + __("expired") : ""}</small></th>`).join("")}${d.can_award ? `<th>${__("Award to")}</th>` : ""}</tr>`;
		const body = d.items.map((it) => `<tr><td><b>${esc(it.item_name || it.item_code)}</b><br><small class="text-muted">${esc(it.item_code)}</small></td><td class="num">${format_number(it.qty, null, 0)} ${esc(it.uom || "")}</td>
			${S.map((s) => { const l = s.lines[it.item_code]; if (!l) return `<td class="num text-muted">—</td>`;
				const best = it.best === s.quotation;
				return `<td class="num ${best ? "hsc-best" : ""}">${money(l.rate, s.currency)}${s.currency !== d.base ? `<br><small>${money(l.aed, d.base)}</small>` : ""}<br><small class="text-muted">${l.lead ? __("{0} days", [l.lead]) : ""}</small>${best ? `<br><span class="hsx-pill green">${__("Best price")}</span>` : ""}</td>`; }).join("")}
			${d.can_award ? `<td><select class="form-control input-xs hsc-pick" data-item="${esc(it.item_code)}"><option value="">${__("— not now —")}</option>${S.filter((s) => s.lines[it.item_code] && !s.expired).map((s) => `<option value="${esc(s.quotation)}" ${st.pick[it.item_code] === s.quotation ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select></td>` : ""}</tr>`).join("");
		const foot = `<tr><td><b>${__("Total for the RFQ")}</b></td><td></td>${S.map((s) => `<td class="num"><b>${money(s.total_aed, d.base)}</b><br><small class="text-muted">${__("{0} of {1} items", [s.covers, d.items.length])}</small></td>`).join("")}${d.can_award ? "<td></td>" : ""}</tr>
			<tr><td>${__("Terms")}</td><td></td>${S.map((s) => `<td class="num"><small>${esc(s.terms || "—")}${s.incoterm ? " · " + esc(s.incoterm) : ""}<br>${__("Valid till")} ${frappe.datetime.str_to_user(s.valid_till || "") || "—"}</small></td>`).join("")}${d.can_award ? "<td></td>" : ""}</tr>`;
		v.$body.html(`<p><a class="hsc-back">← ${__("All RFQs")}</a></p>` + ui.card(`${__("Comparison")} — ${esc(d.rfq)}`, `<div class="hsx-tw"><table class="hsx-t hsc-cmp"><thead>${head}</thead><tbody>${body}</tbody><tfoot>${foot}</tfoot></table></div>
			<p class="hsx-note">${__("Prices are converted to {0} at today's rate. The lowest price per item is preselected; expired quotations are not offered.", [esc(d.base)])}</p>`,
			{ actions: d.can_award ? `<button class="btn btn-primary btn-sm hsc-award">${__("Award & create purchase orders")}</button>` : "" }));
	}

	function open(rfq) {
		st.rfq = rfq; ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.compare.rfq_compare", { rfq }).then((d) => {
			st.data = d; st.pick = {};
			d.items.forEach((it) => { if (it.best) st.pick[it.item_code] = it.best; });
			draw();
		});
	}

	v.$body.on("click", ".hsc-open", function () { frappe.set_route("hipersign-compare", $(this).attr("data-rfq")); });
	v.$body.on("click", ".hsc-back", () => frappe.set_route("hipersign-compare"));
	v.$body.on("change", ".hsc-pick", function () { st.pick[$(this).attr("data-item")] = $(this).val(); });
	v.$body.on("click", ".hsc-award", function () {
		const btn = this; $(btn).prop("disabled", true);
		frappe.xcall("hipersign_trading.api.compare.award", { rfq: st.rfq, picks: st.pick }).then((r) => {
			frappe.show_alert({ message: r.message, indicator: "green" }, 7);
			if (r.pos.length) { if (hipersign.panel && hipersign.panel.has("Purchase Order")) hipersign.panel.open("Purchase Order", r.pos[0]); else frappe.set_route("Form", "Purchase Order", r.pos[0]); }
			open(st.rfq);
		}).catch(() => {}).finally(() => $(btn).prop("disabled", false));
	});
	wrapper.hs_route = () => { const r = frappe.get_route(); r[1] ? open(r[1]) : list(); };
};
frappe.pages["hipersign-compare"].on_page_show = function (wrapper) { wrapper.hs_route && wrapper.hs_route(); };
