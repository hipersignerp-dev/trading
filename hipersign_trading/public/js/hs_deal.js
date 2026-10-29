// Hipersign ERP v1.6.0 — Live deal demo (demo sites only): play one deal end to end, step by step, on real records.
frappe.provide("hipersign.deal");

hipersign.deal.open = function () {
	const d = new frappe.ui.Dialog({ title: __("Live deal demo"), size: "large", fields: [{ fieldtype: "HTML", fieldname: "body" }] });
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	let busy = false;
	const draw = (st) => {
		if (!st.enabled) return d.fields_dict.body.$wrapper.html(`<p class="text-muted">${__("The Live deal demo is switched off. A System Manager turns it on in Hipersign Settings (demo sites only).")}</p>`);
		const done = (st.run && st.run.done) || [];
		const next = st.steps.find((s) => !done.find((x) => x.key === s.key));
		const rows = st.steps.map((s, i) => {
			const x = done.find((y) => y.key === s.key);
			return `<tr class="${!x && next && next.key === s.key ? "hd-next" : ""}"><td style="width:28px">${x ? frappe.utils.icon("check", "sm") : i + 1}</td><td><b>${esc(s.label)}</b>${x && x.message ? `<div class="small text-muted">${esc(x.message)}</div>` : ""}</td>
				<td class="text-right">${x && x.name ? `<a class="hd-open" data-dt="${esc(x.doctype)}" data-name="${esc(x.name)}">${esc(x.name)}</a>` : x && x.skipped ? `<span class="text-muted">${__("skipped")}</span>` : ""}</td></tr>`;
		}).join("");
		const sm = st.summary;
		const ui = hipersign.ui;
		d.fields_dict.body.$wrapper.html(`<p class="text-muted">${__("One deal from the first enquiry to the customer's cheque. Each step creates and submits the real record — open any of them. Reset removes everything this run made.")}</p>
			<table class="table table-sm hd-t">${rows}</table>
			${sm ? `<div class="hsx-kpis" style="grid-template-columns:repeat(4,1fr)">${[[__("Revenue (net)"), sm.revenue], [__("Landed cost of goods"), sm.landed_cost], [__("Gross profit — {0}%", [sm.margin]), sm.profit], [__("Cash in (advance + cheque)"), sm.cash]]
				.map(([l, v]) => `<div class="hsx-kpi tone-blue"><span class="hsx-kpi-t"><span class="hsx-kpi-l">${esc(l)}</span><b class="hsx-kpi-v">${esc(ui.money(v, sm.currency, true))}</b></span></div>`).join("")}</div>` : ""}`);
		d.set_primary_action(next ? __("Play: {0}", [next.label]) : __("Done"), () => (next ? play(false) : d.hide()));
		d.set_secondary_action_label(st.run ? __("Reset") : __("Play all"));
		d.set_secondary_action(() => (st.run ? reset() : play(true)));
		d.fields_dict.body.$wrapper.find(".hd-open").on("click", function () {
			const dt = $(this).attr("data-dt"), name = $(this).attr("data-name");
			d.hide();
			if (hipersign.panel && hipersign.panel.has(dt)) hipersign.panel.open(dt, name); else frappe.set_route("Form", dt, name);
		});
	};
	const play = (all) => {
		if (busy) return;
		busy = true;
		d.disable_primary_action();
		frappe.xcall("hipersign_trading.api.deal.play_next").then((st) => {
			busy = false;
			d.enable_primary_action();
			draw(st);
			if (st.last) frappe.show_alert({ message: `${st.last.label}: ${st.last.name || ""}`, indicator: "green" });
			const left = st.steps.find((s) => !(st.run.done || []).find((x) => x.key === s.key));
			if (all && left) setTimeout(() => play(true), 400);
		}).catch(() => { busy = false; d.enable_primary_action(); });
	};
	const reset = () => frappe.confirm(__("Cancel and delete every record this demo run made?"), () => {
		d.disable_primary_action();
		frappe.xcall("hipersign_trading.api.deal.reset").then((st) => { d.enable_primary_action(); draw(st); frappe.show_alert({ message: __("Demo deal removed"), indicator: "green" }); });
	});
	d.show();
	d.fields_dict.body.$wrapper.html(`<div class="hsx-loading">${__("Loading…")}</div>`);
	frappe.xcall("hipersign_trading.api.deal.get_state").then(draw);
};
