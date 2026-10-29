// Hipersign Home — the prototype's dashboard: the group, the trading lifecycle, today's work, alerts, KPIs and profit.
frappe.pages["hipersign-home"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Hipersign Home"),
		desc: __("One view of purchasing, imports, stock, sales and finance — every number below opens the records behind it."),
	});
	// v1.5.6: scope (group, country, company) and period come from the top bar, as in the prototype
	const st = {};
	let chart = null;
	$(document).on("hs-scope-change", () => { if (wrapper.hs_load && $(wrapper).is(":visible")) load(); });
	// v1.5.6: a hidden page's chart has no width — stop it redrawing on resize (negative bar widths in the console)
	$(wrapper).on("hide", () => {
		if (chart && chart.destroy) chart.destroy();
	});
	$(wrapper).on("show", () => {
		if (!chart || !chart.boundDrawFn || !chart.parent) return;
		if (window.ResizeObserver) {
			chart.resizeObserver = new ResizeObserver(chart.boundDrawFn);
			chart.resizeObserver.observe(chart.parent);
		}
		window.addEventListener("resize", chart.boundDrawFn);
	});
	v.$body.on("click", "[data-hs-scope]", function (e) {
		e.stopPropagation();
		if (hipersign.topbar && hipersign.topbar.set_scope) hipersign.topbar.set_scope($(this).attr("data-hs-scope"));
	});

	function money(x, cur) {
		return ui.money(x, cur, true);
	}

	function group(g) {
		if (!g || !g.rows.length) return "";
		const t = g.totals;
		// v1.5.6: the prototype's four group tiles; each opens the consolidation
		const cons = ["query-report", "Hipersign Group Consolidation"];
		const kp = [
			{ label: __("Revenue — {0}", [__("year to date")]), value: t.revenue_after_ic, money: 1, currency: g.currency, tone: "navy", route: cons,
				sub: t.ic ? __("after inter-company · {0} before", [money(t.revenue, g.currency)]) : __("No inter-company sales") },
			{ label: __("Profit for the year"), value: t.profit, money: 1, currency: g.currency, tone: t.profit >= 0 ? "green" : "red", route: cons,
				sub: t.revenue ? __("{0}% of revenue", [flt((t.profit / t.revenue) * 100, 1)]) : "" },
			{ label: __("Cash & bank"), value: t.cash, money: 1, currency: g.currency, tone: "green", route: cons, sub: __("Receivables {0}", [money(t.receivables, g.currency)]) },
			{ label: __("Stock"), value: t.stock, money: 1, currency: g.currency, tone: "violet", route: cons, sub: __("Payables {0}", [money(t.payables, g.currency)]) },
		].map(ui.kpi).join("");
		const rows = g.rows.map((r) => ({
			cells: [
				`<b>${ui.esc(r.company)}</b><span class="sub">${ui.esc([r.country, r.role].filter(Boolean).join(" · "))}</span>`,
				ui.esc(r.currency),
				money(r.revenue_local, r.currency),
				money(r.revenue, g.currency),
				r.remote ? "—" : `${flt(r.gross_margin, 1)}%`,
				money(r.profit, g.currency),
				r.remote ? "—" : money(r.cash, g.currency),
				r.remote ? "" : `<button class="btn btn-xs btn-default" data-hs-scope="company:${ui.esc(r.company)}">${__("View")}</button>`,
			],
			route: r.remote ? ["Form", "Hipersign Group Member", r.company] : null,
		}));
		const table = ui.table(
			[{ label: __("Company") }, { label: __("Currency") }, { label: __("Revenue (local)"), cls: "n" }, { label: __("Revenue ({0})", [g.currency]), cls: "n" },
				{ label: __("Gross margin"), cls: "n" }, { label: __("Profit ({0})", [g.currency]), cls: "n" }, { label: __("Cash ({0})", [g.currency]), cls: "n" }, { label: "" }],
			rows
		);
		return ui.card(__("{0} — {1} companies", [st.scope_label || __("Whole group"), g.rows.length]), `<div class="hsx-kpis" style="margin-bottom:12px">${kp}</div>${table}`, {
			icon: "organization",
			sub: __("In {0} — profit at average rates, balances at closing rates", [g.currency]),
			actions: `<button class="btn btn-xs btn-default" data-hs-route='["query-report","Hipersign Group Consolidation"]'>${__("Group consolidation")}</button>`,
		});
	}

	function lifecycle(stages, cur) {
		const html = stages
			.map((s) => {
				const big = s.big_is_money ? money(s.big, cur) + (s.big_suffix ? " " + ui.esc(s.big_suffix) : "") : ui.esc(s.big);
				const small = s.small_is_money ? money(s.small, cur) : ui.esc(s.small);
				return `<button class="hsx-stage"${ui.route_attr(s.route, s.options)}><span class="no">${s.n}</span><span class="ic">${ui.icon(s.icon, "md")}</span>
				<h4>${ui.esc(s.title)}</h4><b>${big}</b><span>${small}</span></button>`;
			})
			.join("");
		return ui.card(__("The connected trading lifecycle"), `<div class="hsx-stages">${html}</div>`, {
			icon: "branch",
			sub: __("From international purchase to customer delivery — click a stage"),
			actions: `<button class="btn btn-xs btn-default" data-hs-route='["hipersign-journey"]'>${__("Trade Journey")}</button>`,
		});
	}

	function work(rows) {
		const body = rows.length
			? `<div class="hsx-work">${rows.map((r) => `<button${ui.route_attr(r.route, r.options)}><b>${r.n}</b><span>${ui.esc(r.label)}</span></button>`).join("")}</div>`
			: `<div class="hsx-empty">${__("Nothing waiting for you today.")}</div>`;
		return ui.card(__("Work for today"), body, { icon: "check", sub: frappe.datetime.str_to_user(frappe.datetime.get_today()) });
	}

	function alerts(a) {
		const body = a.groups.length
			? a.groups
					.slice(0, 6)
					.map((g) => `<div class="hsx-agrp" data-hs-route='["hipersign-alerts"]' data-hs-opts='${ui.esc(JSON.stringify({ category: g.category }))}'>
					<span class="hsx-dot ${g.high ? "High" : g.top.severity}"></span><div><div class="c">${ui.esc(__(g.category))} · ${g.count}</div><div class="t">${ui.esc(g.top.title)}</div></div></div>`)
					.join("")
			: `<div class="hsx-empty">${__("No open alerts.")}</div>`;
		return ui.card(__("Management priority actions"), body, {
			icon: "circle-alert",
			sub: __("{0} open", [a.total]),
			actions: `<button class="btn btn-xs btn-default" data-hs-route='["hipersign-alerts"]'>${__("All insights")}</button>`,
		});
	}

	function pl(p, cur, target) {
		const gm = p.revenue ? (p.gross / p.revenue) * 100 : 0;
		const nm = p.revenue ? (p.profit / p.revenue) * 100 : 0;
		const full = (x) => ui.money(x, cur);
		return ui.card(
			__("Profit — {0}", [st.label]),
			`<table class="hsx-pl"><tr><td>${__("Revenue (net sales)")}</td><td class="n">${full(p.revenue)}</td></tr>
			<tr><td>${__("Cost of goods sold (landed)")}</td><td class="n">− ${full(p.cogs)}</td></tr>
			<tr><td><b>${__("Gross profit")}</b></td><td class="n"><b>${full(p.gross)}</b> · ${ui.pill(flt(gm, 1) + "%", gm >= target ? "green" : "amber")}</td></tr>
			<tr><td>${__("Operating expenses incl. depreciation")}</td><td class="n">− ${full(p.opex)}</td></tr>
			<tr class="tot"><td>${__("Net profit before tax")}</td><td class="n">${full(p.profit)} · ${flt(nm, 1)}%</td></tr></table>`,
			{ icon: "chart", actions: `<button class="btn btn-xs btn-default" data-hs-route='["query-report","Profit and Loss Statement"]'>${__("Profit & loss")}</button>` }
		);
	}

	function render(d) {
		st.label = d.period.label;
		st.scope_label = d.scope_label;
		v.$actions.html(`<button class="btn btn-default btn-sm hsx-tour">${frappe.utils.icon("map-pin", "sm")} ${__("Take the guided tour")}</button>`
			+ ((frappe.boot.hipersign || {}).deal_demo ? ` <button class="btn btn-default btn-sm hsx-deal">${frappe.utils.icon("play", "sm")} ${__("Live deal demo")}</button>` : "")
			+ ` <span class="hsx-chip">${ui.esc(d.period.label)}</span>`);
		v.$actions.find(".hsx-tour").on("click", () => hipersign.tour.start());
		v.$actions.find(".hsx-deal").on("click", () => hipersign.deal && hipersign.deal.open());
		const cur = d.currency;
		const k = d.kpis.map((x) => Object.assign({ currency: cur }, x));
		v.$body.html(
			group(d.group) +
				lifecycle(d.lifecycle, cur) +
				`<div class="hsx-grid2">${work(d.work)}${alerts(d.alerts)}</div>` +
				`<div class="hsx-kpis">${k.map(ui.kpi).join("")}</div>` +
				(d.monthly || d.pl
					? `<div class="${d.monthly && d.pl ? "hsx-grid2" : ""}">${d.monthly ? ui.card(__("Monthly sales vs purchases"), `<div class="hsx-chart"></div>`, { icon: "chart", sub: __("Last 12 months · net") }) : ""}${d.pl ? pl(d.pl, cur, d.target_margin) : ""}</div>`
					: "")
		);
		const el = v.$body.find(".hsx-chart")[0];
		if (!el) return;
		if (chart && chart.destroy) chart.destroy();
		chart = new frappe.Chart(el, {
			type: "bar",
			height: 240,
			colors: ["#1f5ae0", "#6d2fe0"],
			data: { labels: d.monthly.labels, datasets: [{ name: __("Sales"), values: d.monthly.sales }, { name: __("Purchases"), values: d.monthly.purchases }] },
			axisOptions: { xIsSeries: 1 },
			barOptions: { spaceRatio: 0.45 },
			tooltipOptions: { formatTooltipY: (y) => ui.money(y, cur) },
		});
	}

	function load() {
		if (!v.$body.children().length) ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.home.get_home", {}).then(render);
	}

	wrapper.hs_load = load;
	load();
};

frappe.pages["hipersign-home"].on_page_show = function (wrapper) {
	if (wrapper.hs_load && wrapper.hs_loaded_at && Date.now() - wrapper.hs_loaded_at > 60000) wrapper.hs_load();
	wrapper.hs_loaded_at = Date.now();
};
