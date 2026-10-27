// Hipersign Home — the prototype's dashboard: the group, the trading lifecycle, today's work, alerts, KPIs and profit.
frappe.pages["hipersign-home"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Hipersign Home"),
		desc: __("One view of purchasing, imports, stock, sales and finance — every number below opens the records behind it."),
	});
	const st = { period: "month", company: "" };
	let chart = null;

	v.$actions.html(
		ui.seg("period", [["month", __("This month")], ["last_month", __("Last month")], ["ytd", __("Year to date")]], st.period) +
			`<select class="hsx-select hsx-co"><option value="">${__("All companies")}</option></select>`
	);
	v.$actions.on("click", "[data-seg=period] button", function () {
		st.period = $(this).attr("data-v");
		$(this).addClass("on").siblings().removeClass("on");
		load();
	});
	v.$actions.on("change", ".hsx-co", function () {
		st.company = $(this).val();
		load();
	});

	function money(x, cur) {
		return ui.money(x, cur, true);
	}

	function group(g) {
		if (!g || !g.rows.length) return "";
		const t = g.totals;
		const kp = [
			{ label: __("Group revenue (YTD)"), value: t.revenue, money: 1, currency: g.currency, tone: "navy", sub: __("after intercompany {0}", [money(t.revenue_after_ic, g.currency)]) },
			{ label: __("Group profit (YTD)"), value: t.profit, money: 1, currency: g.currency, tone: t.profit >= 0 ? "green" : "red" },
			{ label: __("Group cash & bank"), value: t.cash, money: 1, currency: g.currency, tone: "green" },
			{ label: __("Group receivables"), value: t.receivables, money: 1, currency: g.currency, tone: "violet" },
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
			],
			route: r.remote ? ["Form", "Hipersign Group Member", r.company] : null,
		}));
		const table = ui.table(
			[{ label: __("Company") }, { label: __("Currency") }, { label: __("Revenue (local)"), cls: "n" }, { label: __("Revenue ({0})", [g.currency]), cls: "n" },
				{ label: __("Gross margin"), cls: "n" }, { label: __("Profit ({0})", [g.currency]), cls: "n" }, { label: __("Cash ({0})", [g.currency]), cls: "n" }],
			rows
		);
		return ui.card(__("Group"), `<div class="hsx-kpis" style="margin-bottom:12px">${kp}</div>${table}`, {
			icon: "organization",
			sub: __("Year to date · translated to {0} at average rates (cash at closing rate)", [g.currency]),
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
		const $co = v.$actions.find(".hsx-co");
		if ($co.find("option").length === 1) d.companies.forEach((c) => $co.append(`<option value="${ui.esc(c)}">${ui.esc(c)}</option>`));
		$co.toggle(d.companies.length > 1).val(st.company);
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
		frappe.xcall("hipersign_trading.api.home.get_home", { period: st.period, company: st.company || null }).then(render);
	}

	wrapper.hs_load = load;
	load();
};

frappe.pages["hipersign-home"].on_page_show = function (wrapper) {
	if (wrapper.hs_load && wrapper.hs_loaded_at && Date.now() - wrapper.hs_loaded_at > 60000) wrapper.hs_load();
	wrapper.hs_loaded_at = Date.now();
};
