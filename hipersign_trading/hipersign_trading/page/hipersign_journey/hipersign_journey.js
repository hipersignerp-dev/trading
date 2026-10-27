// Trade Journey — one purchase followed from the supplier order to the customer's payment.
frappe.pages["hipersign-journey"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Trade Journey"),
		desc: __("One purchase followed end to end: supplier order, shipment, receipt, landed cost, the sales that used the stock, delivery and payment."),
	});
	const st = { po: null };
	v.$actions.html(`<select class="hsx-select hsx-po" style="min-width:280px"></select>`);
	v.$actions.on("change", ".hsx-po", function () {
		st.po = $(this).val();
		load();
	});

	function stage(s) {
		const rows = s.rows.length
			? `<dl>${s.rows
					.map((r) => `<dt>${ui.esc(r[0])}</dt><dd>${r[2] ? `<a href="#" data-hs-route='${ui.esc(JSON.stringify(r[2]))}'>${ui.esc(r[1])}</a>` : ui.esc(r[1])}</dd>`)
					.join("")}</dl>`
			: `<div class="text-muted small">${ui.esc(s.empty || "—")}</div>`;
		return `<div class="hsx-jcard"><div class="h"><span><span class="no">${s.n}</span><b>${ui.esc(s.title)}</b></span>${ui.pill(s.status, s.done ? "green" : "amber")}</div>${rows}</div>`;
	}

	function render(d) {
		const done = d.stages.filter((s) => s.done).length;
		v.$body.html(
			ui.card(
				__("Journey of {0}", [d.po]),
				`<div class="hsx-steps">${d.stages.map((s) => `<span class="${s.done ? "ok" : ""}">${s.n} ${ui.esc(s.title)}</span>`).join("")}</div>
				<div class="hsx-progress" style="margin:10px 0 2px"><i style="width:${(done / d.stages.length) * 100}%"></i></div>
				<div class="text-muted small">${__("{0} of {1} stages complete", [done, d.stages.length])}</div>`,
				{ icon: "branch", actions: `<button class="btn btn-xs btn-default" data-hs-route='${ui.esc(JSON.stringify(["Form", "Purchase Order", d.po]))}'>${__("Open purchase order")}</button>` }
			) + `<div class="hsx-jcards">${d.stages.map(stage).join("")}</div>`
		);
	}

	v.$body.on("click", "a[data-hs-route]", (e) => e.preventDefault());

	function load() {
		if (!st.po) return;
		ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.journey.chain", { po: st.po }).then(render);
	}

	frappe.xcall("hipersign_trading.api.journey.purchase_orders").then((pos) => {
		if (!pos.length) {
			v.$body.html(ui.card("", `<div class="hsx-empty">${__("No purchase orders yet.")}</div>`));
			return;
		}
		const $s = v.$actions.find(".hsx-po");
		$s.html(pos.map((p) => `<option value="${ui.esc(p.name)}">${ui.esc(p.name)} — ${ui.esc(p.supplier_name || "")} · ${ui.esc(__(p.workflow_state || p.status))}</option>`).join(""));
		const want = (frappe.route_options && frappe.route_options.po) || frappe.get_route()[1];
		frappe.route_options = null;
		// start on the most complete journey with an import, as the prototype does
		st.po = pos.find((p) => p.name === want) ? want : (pos.find((p) => p.has_import && flt(p.per_received) >= 100) || pos.find((p) => p.has_import) || pos[0]).name;
		$s.val(st.po);
		load();
	});
};
