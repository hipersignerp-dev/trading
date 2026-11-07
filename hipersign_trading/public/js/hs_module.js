// Hipersign ERP v1.6.0 — module pages: the prototype's page per module (KPI row, tabs, filter chips, list or pipeline
// board). Rows open the record panel. Data from hipersign_trading.api.module; the page follows the top bar's scope and period.
frappe.provide("hipersign.module");

const hm_esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
const STAGE_TONE = { New: "blue", Contacted: "blue", Qualified: "violet", Proposal: "violet", Negotiation: "orange", Won: "green", Lost: "red" };
const STATUS_TONE = { Draft: "grey", "To Deliver and Bill": "blue", "To Deliver": "blue", "To Bill": "blue", Completed: "green", Closed: "grey", Cancelled: "red",
	"On Hold": "orange", Open: "blue", Replied: "blue", Ordered: "green", Lost: "red", Expired: "grey", "Partially Ordered": "blue",
	"To Receive and Bill": "blue", "To Receive": "blue", Received: "green", "In Transit": "blue", Booked: "grey", "Under Customs Clearance": "orange",
	Cleared: "green", "Received at Warehouse": "green", Pending: "orange", Submitted: "blue", Stopped: "grey",
	Applied: "orange", Issued: "grey", "Documents Presented": "blue", Accepted: "green", Paid: "green", Discrepant: "red" };

// v1.7.3 (prototype p18): a total line under every table with money columns — one currency per column, rows counted
hipersign.module.foot = function (r) {
	if (!r.rows || r.rows.length < 2 || r.nototal) return "";
	const SKIP = /(balance|rate|price|limit|%|margin|qty|quantity|days|stock|age)/i;
	let any = false;
	const f = r.cols.map((col, i) => {
		if (SKIP.test(col.label || "")) return null;
		const t = {}; let n = 0, ok = true;
		r.rows.forEach((row) => {
			if (row.nosum) return; // v1.8.4: a forecast or memo line is not part of the total
			const c = row.cells[i];
			if (!ok || c === null || c === undefined || c === "") return;
			if (typeof c !== "object" || c.money === undefined) { ok = false; return; }
			const cur = c.currency || "";
			t[cur] = (t[cur] || 0) + flt(c.money); n++;
		});
		if (!ok || !n) return null;
		any = true;
		// one line per currency when a list mixes them (export orders in USD beside local AED orders)
		return Object.entries(t).map(([cur, v]) => `${cur ? hm_esc(cur) + " " : ""}${hm_esc(format_number(v, null, 2))}`).join("<br>");
	});
	if (!any) return "";
	if (f[0] === null) f[0] = `${__("Total")} <span class="hsx-tcount">· ${__("{0} rows", [r.rows.length])}</span>`;
	return `<tfoot><tr>${f.map((x, i) => `<td class="${(r.cols[i] || {}).cls || ""}">${x === null ? "" : x}</td>`).join("")}</tr></tfoot>`;
};

hipersign.module.cell = function (c) {
	if (c === null || c === undefined || c === "") return "—";
	if (typeof c !== "object") return hm_esc(typeof c === "number" ? format_number(c, null, c % 1 ? 2 : 0) : c);
	if (c.code) return `<span class="hsx-code">${hm_esc(c.code)}</span>`;
	// v1.8.0: several buttons in one cell (Approve · Lines…); a button that opens a window of the module's script (c.js)
	if (c.buttons) return `<span style="display:inline-flex;gap:4px;flex-wrap:nowrap">${c.buttons.map(hipersign.module.cell).join("")}</span>`;
	if (c.button && c.js) return `<button class="btn btn-xs btn-default hsx-cbtn" data-pjs="${hm_esc(c.js)}" data-pname="${hm_esc(c.name)}" style="white-space:nowrap">${hm_esc(c.button)}</button>`;
	// v1.8.0: a button that runs a Projects action (hipersign_trading.api.projects.act), and a number typed in place (the measurement)
	if (c.button && c.act) return `<button class="btn btn-xs ${c.primary ? "btn-primary" : "btn-default"} hsx-cbtn" data-pact="${hm_esc(c.act)}" data-pname="${hm_esc(c.name)}"
		${c.method ? `data-pmethod="${hm_esc(c.method)}"` : ""} data-pargs="${hm_esc(JSON.stringify(c.args || {}))}" ${c.confirm ? `data-pconfirm="${hm_esc(c.confirm)}"` : ""} style="white-space:nowrap">${hm_esc(c.button)}</button>`;
	if (c.input !== undefined) return `<input type="number" class="form-control input-xs hsx-cin" style="width:84px;display:inline-block" step="any" value="${hm_esc(c.input)}"
		${c.min !== undefined ? `min="${hm_esc(c.min)}"` : ""} ${c.max !== undefined ? `max="${hm_esc(c.max)}"` : ""} data-pact="${hm_esc(c.act)}" data-pname="${hm_esc(c.name)}"
		data-pargs="${hm_esc(JSON.stringify(c.args || {}))}" onclick="event.stopPropagation()"> %`;
	if (c.button) return `<button class="btn btn-xs ${c.primary ? "btn-primary" : "btn-default"} hsx-cbtn" ${c.make ? `data-make="${hm_esc(c.make)}" data-source="${hm_esc(c.source)}"` : ""}
		${c.open ? `data-ldt="${hm_esc(c.open[0])}" data-lname="${hm_esc(c.open[1])}"` : ""} style="white-space:nowrap">${hm_esc(c.button)}</button>`;
	if (c.url) return `<a class="btn btn-xs btn-default" target="_blank" href="${hm_esc(c.url)}" onclick="event.stopPropagation()">${hm_esc(c.label || c.url)}</a>`;
	if (c.text !== undefined) return `<span class="hsx-tone-${hm_esc(c.tone || "")}">${hm_esc(c.text)}</span>`;
	if (c.link) return `<a class="hsx-link" data-ldt="${hm_esc(c.link[0])}" data-lname="${hm_esc(c.link[1])}">${hm_esc(c.link[1])}</a>${c.pill ? `<div><span class="hsx-pill ${STATUS_TONE[c.pill] || "blue"}">${hm_esc(__(c.pill))}</span></div>` : ""}`;
	if (c.main !== undefined) return `<b>${hm_esc(c.main)}</b>${c.sub ? `<span class="hsx-sub2 ${c.late ? "text-danger" : ""}">${hm_esc(c.sub)}</span>` : ""}`;
	if (c.lines) return c.lines.map((l) => `<div>${hm_esc(l)}</div>`).join("") || "—";
	if (c.date !== undefined) return c.date ? `<span class="${c.late ? "text-danger" : ""}" style="white-space:nowrap">${hm_esc(frappe.datetime.str_to_user(c.date))}</span>` : "—";
	if (c.bar !== undefined) return `<span class="hp-bar" style="width:80px"><span style="width:${Math.min(100, c.bar)}%;${c.bar < 100 ? "background:var(--x-blue)" : ""}"></span></span> <b>${format_number(c.bar, null, 0)}%</b>`;
	if (c.pill !== undefined) return `<span class="hsx-pill ${c.tone || STAGE_TONE[c.pill] || STATUS_TONE[c.pill] || (/^Pending/.test(c.pill) ? "orange" : "grey")}">${hm_esc(__(c.pill))}</span>`
		+ (c.sub ? `<span class="hsx-sub2 ${c.late ? "text-danger" : ""}">${hm_esc(c.sub)}</span>` : "");
	if (c.money !== undefined) return `<span class="${c.neg ? "text-danger" : ""}" style="white-space:nowrap">${c.currency ? hm_esc(c.currency) + " " : ""}${hm_esc(format_number(c.money, null, 2))}</span>${c.sub ? `<span class="hsx-sub2" style="white-space:nowrap">${hm_esc(c.sub)}</span>` : ""}`;
	return "";
};

// v1.8.4: a money column where every row is in the same currency shows it once, in the heading ("Value (AED)") — the
// cells repeated "AED" and wide tables (Projects, Manufacturing) scrolled sideways at 1280 px
hipersign.module.one_cur = function (cols, rows) {
	const out = {};
	(cols || []).forEach((c, i) => {
		let cur = null, ok = true, n = 0;
		(rows || []).forEach((r) => {
			const x = (r.cells || [])[i];
			if (!x || typeof x !== "object" || x.money === undefined) return;
			n++;
			if (cur === null) cur = x.currency || "";
			else if ((x.currency || "") !== cur) ok = false;
		});
		if (ok && n && cur) out[i] = cur;
	});
	return out;
};
hipersign.module.thead = function (cols, rows) {
	const one = hipersign.module.one_cur(cols, rows);
	return { one, html: cols.map((c, i) => `<th class="${c.cls || ""}">${hm_esc(c.label)}${one[i] && !String(c.label || "").includes(one[i]) ? ` <span class="hsx-thcur">(${hm_esc(one[i])})</span>` : ""}</th>`).join("") };
};
hipersign.module.tcell = function (c, i, one) {
	return hipersign.module.cell(one[i] && c && typeof c === "object" && c.money !== undefined ? Object.assign({}, c, { currency: "" }) : c);
};

// summary cards under the KPIs: horizontal bars (amount per name) or a donut (share per name)
const HM_COLORS = { blue: "var(--x-blue, #2563eb)", violet: "var(--x-violet, #7c3aed)", orange: "#d97706", green: "#16a34a", navy: "#1e3a8a", teal: "#0d9488", red: "#dc2626", grey: "#94a3b8" };
hipersign.module.card_html = function (c) {
	const ui = hipersign.ui, cur = c.currency;
	// v1.8.0: a card of counts (projects by stage) shows plain numbers
	const val = (v) => (c.count ? format_number(v, null, 0) : ui.money(v, cur, true));
	const max = Math.max(1, ...(c.rows || []).map((r) => r[1]));
	let body = "";
	if (c.type === "cols") return `<div class="hsx-mcard ${c.wide ? "wide" : ""}"><div class="hsx-mcard-h"><b>${hm_esc(c.title)}</b> <span class="text-muted">${hm_esc(c.sub || "")}</span></div>${hipersign.module.cols_html(c)}</div>`;
	if (!(c.rows || []).length) body = `<div class="hsx-empty">${__("Nothing in this period.")}</div>`;
	else if (c.type === "bars") body = c.rows.map(([l, v]) => `<div class="hsx-hbar"><span class="hsx-hbar-l" title="${hm_esc(l)}">${hm_esc(l)}</span>
		<span class="hsx-hbar-t"><i style="width:${Math.max(2, (v / max) * 100)}%"></i></span><b>${hm_esc(val(v))}</b></div>`).join("");
	else {
		const tot = c.rows.reduce((a, r) => a + r[1], 0) || 1;
		let acc = 0;
		const stops = c.rows.map(([, v, col]) => { const a = acc; acc += (v / tot) * 360; return `${HM_COLORS[col] || col} ${a}deg ${acc}deg`; }).join(",");
		body = `<div class="hsx-donut-w"><div class="hsx-donut" style="background:conic-gradient(${stops})"><span><b>${hm_esc(c.center)}</b><small>${hm_esc(c.center_label || "")}</small></span></div>
			<div class="hsx-legend">${c.rows.map(([l, v, col]) => `<span><i style="background:${HM_COLORS[col] || col}"></i>${hm_esc(l)} ${hm_esc(val(v))}</span>`).join("")}</div></div>`;
	}
	return `<div class="hsx-mcard ${c.wide ? "wide" : ""}"><div class="hsx-mcard-h"><b>${hm_esc(c.title)}</b> <span class="text-muted">${hm_esc(c.sub || "")}</span></div>${body}</div>`;
};

// v1.8.0 (prototype p19): grouped columns — a series per colour, a group per label (negative values hang below the line)
hipersign.module.cols_html = function (c) {
	const S = c.series || [], L = c.labels || [];
	if (!L.length) return `<div class="hsx-empty">${__("Nothing in this period.")}</div>`;
	// v1.8.4: column cards (output vs plan, variance by work order…) get axes and the chart type menu — the chart kit
	if (hipersign.chart && hipersign.chart.chart) {
		return hipersign.chart.chart({ labels: L, series: S.map((s) => ({ name: s.name, data: s.data.map(flt), color: s.color })), kind: "bar", key: c.title,
			money: !c.count && !c.pct, currency: c.currency, h: 220 });
	}
	const all = S.flatMap((s) => s.data.map((v) => flt(v)));
	const max = Math.max(1, ...all.map((v) => Math.abs(v))), neg = all.some((v) => v < 0);
	const h = 120, half = neg ? h / 2 : h;
	const col = (v, colr) => { const px = Math.max(v ? 2 : 0, Math.abs(v) / max * half); return `<i title="${hm_esc(format_number(v, null, 0))}" style="height:${px}px;background:${HM_COLORS[colr] || colr};${neg ? (v < 0 ? `margin-top:${half}px` : `margin-bottom:${half}px`) : ""}"></i>`; };
	return `<div class="hsx-cols" style="height:${h}px">${L.map((l, i) => `<div class="hsx-colg"><div class="hsx-colb">${S.map((s) => col(flt(s.data[i]), s.color)).join("")}</div><span>${hm_esc(l)}</span></div>`).join("")}</div>
		<div class="hsx-legend">${S.map((s) => `<span><i style="background:${HM_COLORS[s.color] || s.color}"></i>${hm_esc(s.name)}</span>`).join("")}</div>`;
};

hipersign.module.render = function (wrapper, key) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, { title: "", desc: "" });
	v.$wrap.addClass("hsx-mod");
	const st = { key, tab: null, chip: {}, q: "", owner: "", source: "", data: null };
	wrapper.hs_module = st;

	function head(m) {
		v.page.set_title(m.title);
		v.$wrap.find(".hsx-desc").text(m.desc || "");
		v.$actions.html((m.new || []).map((n) => {
			const mode = hipersign.fm && hipersign.fm.COVERED.includes(n.doctype) ? hipersign.fm.mode(n.doctype) : null;
			return `<button class="btn btn-sm ${n.primary ? "btn-primary" : "btn-default"} hsx-new" data-dt="${hm_esc(n.doctype)}">${frappe.utils.icon("add", "sm")} ${hm_esc(n.label)}${mode ? ` <span class="hsx-mchip">${hm_esc(__(mode)).toUpperCase()}</span>` : ""}</button>`;
		}).join(" "));
	}

	function load() {
		// v1.7.2: a list opened from search lands here on its own tab (hs_nav.js LIST_PAGE)
		const want = (frappe.route_options || {}).hs_tab, want_chip = (frappe.route_options || {}).hs_chip;
		if (want) { st.tab = want; if (want_chip) st.chip[want] = want_chip; frappe.route_options = null; }
		// v1.8.3 (prototype p20): the page's graphs above the KPI cards, loaded beside the page itself
		hipersign.band && hipersign.band.mount(v.$band, key);
		frappe.xcall("hipersign_trading.api.module.get_module", { key, owner: st.owner, source: st.source }).then((m) => {
			st.data = m;
			head(m);
			hipersign.nav && hipersign.nav.classic_menu && hipersign.nav.classic_menu(v.page, frappe.get_route_str());
			if (!st.tab || !m.tabs.find((t) => t.key === st.tab)) st.tab = m.default_tab || (m.tabs[0] || {}).key;
			const filters = m.filters ? `<select class="form-control hsx-owner"><option value="">${__("All owners")}</option><option value="mine">${__("My leads")}</option>${m.filters.owners.map(([u, n]) => `<option value="${hm_esc(u)}">${hm_esc(n)}</option>`).join("")}</select>
				<select class="form-control hsx-source"><option value="">${__("All sources")}</option>${m.filters.sources.map((s) => `<option value="${hm_esc(s)}">${hm_esc(__(s))}</option>`).join("")}</select>` : "";
			v.$body.html(`<div class="hsx-kpis">${m.kpis.map((k, i) => ui.kpi(Object.assign({}, k, { route: null })).replace("<button ", `<button data-k="${i}" `)).join("")}</div>
				${(m.cards || []).length ? `<div class="hsx-mcards">${m.cards.map(hipersign.module.card_html).join("")}</div>` : ""}
				<div class="hsx-mtabs">${m.tabs.map((t) => `<button data-tab="${t.key}" class="${t.key === st.tab ? "on" : ""}">${hm_esc(t.label)}</button>`).join("")}
					${(m.links || []).map(([l, r], i) => `<a class="hsx-mlink" data-li="${i}">${hm_esc(l)} ↗</a>`).join("")}</div>
				<div class="hsx-chips"></div><div class="hsx-mfilters hsx-chips" style="${filters ? "" : "display:none"}">${filters}
				<input class="form-control hsx-q" placeholder="${__("Search…")}" style="max-width:220px"></div>
				<div class="hsx-mout"></div>${m.note ? `<p class="hsx-note">${hm_esc(m.note)}</p>` : ""}`);
			v.$body.find(".hsx-owner").val(st.owner);
			v.$body.find(".hsx-source").val(st.source);
			v.$body.find(".hsx-q").val(st.q);
			if (!filters) v.$body.find(".hsx-mfilters").toggle(!m.nosearch).find("select").remove();
			tab();
		});
	}

	// v1.8.4: the sidebar's sub-items switch tabs in place (hs_nav.js)
	st.goto = function (k, chip) {
		if (!st.data || !st.data.tabs.find((x) => x.key === k)) { st.tab = k; if (chip) st.chip[k] = chip; return load(); }
		st.tab = k;
		if (chip) st.chip[k] = chip;
		tab();
	};
	function tab() {
		const t = st.data.tabs.find((x) => x.key === st.tab);
		setTimeout(() => $(document).trigger("hs-module-tab"), 0);
		if (!t) return;
		v.$body.find(".hsx-mtabs button").removeClass("on").filter(`[data-tab="${st.tab}"]`).addClass("on");
		if (!st.chip[st.tab] && t.chips.length) st.chip[st.tab] = t.chips[0][0];
		v.$body.find(".hsx-chips").first().html(t.chips.map(([c, l]) => `<button data-chip="${c}" class="${c === st.chip[st.tab] ? "on" : ""}">${hm_esc(l)}</button>`).join("")).toggle(!!t.chips.length);
		rows();
	}

	function rows() {
		let $out = v.$body.find(".hsx-mout");
		ui.loading($out);
		frappe.xcall("hipersign_trading.api.module.get_rows", { key, tab: st.tab, chip: st.chip[st.tab] || null, q: st.q, owner: st.owner, source: st.source }).then((r) => {
			// v1.7.3: a tab can bring its own KPI cards (Quotations → open value, expiring, accepted…); other tabs show the page's
			const $k = v.$body.find(".hsx-kpis"), kp = r.kpis || st.data.kpis;
			$k.html(kp.map((k, i) => ui.kpi(Object.assign({}, k, { route: null })).replace("<button ", `<button data-k="${i}" ${r.kpis ? 'data-tabk="1"' : ""} `)).join(""));
			st.tab_kpis = r.kpis || null;
			if (r.board) return board($out, r.board);
			if (r.blocks) return blocks($out, r.blocks);
			if (r.kanban) { kanban($out, r.kanban, r.kanban_cols); if (!r.after) return; $out.append('<div class="hsx-mout2" style="margin-top:16px"></div>'); r = r.after; }
			if ($out.find(".hsx-mout2").length) $out = $out.find(".hsx-mout2");
			const title = r.title || (st.data.tabs.find((x) => x.key === st.tab) || {}).label;
			const th = hipersign.module.thead(r.cols, r.rows);
			$out.html(ui.card(title, r.rows.length ? `<div class="hsx-tw"><table class="hsx-t hsx-mlist"><thead><tr>${th.html}</tr></thead>
				<tbody>${r.rows.map((row) => `<tr class="${row.cls || ""}" ${row.dt ? `data-dt="${hm_esc(row.dt)}" data-name="${hm_esc(row.name)}"` : ""}>${row.cells.map((c, i) => `<td class="${(r.cols[i] || {}).cls || ""}">${hipersign.module.tcell(c, i, th.one)}</td>`).join("")}</tr>`).join("")}</tbody>${hipersign.module.foot(r)}</table></div>`
				: `<div class="hsx-empty">${hm_esc(r.empty || __("Nothing here."))}</div>`, { actions: (r.actions || []).map((a, i) => `<button class="btn ${a.primary ? "btn-primary" : "btn-default"} btn-xs hsx-ra" data-i="${i}">${hm_esc(a.label)}</button>`).join(" ")
					+ (r.rows.length ? ` <button class="btn btn-default btn-xs hsx-xl">${__("Excel")}</button>` : "") }));
				$out.find(".hsx-ra").on("click", function () {
					const a = r.actions[+$(this).attr("data-i")];
					// v1.8.0: a list action may open a create window or run a server method (Approve submitted timesheets)
					if (a.new) return hipersign.fm ? hipersign.fm.new(a.new, a.values || {}) : frappe.new_doc(a.new);
					if (a.url) return window.open(frappe.urllib.get_full_url(a.url));
					if (a.method) return frappe.xcall(a.method, a.args || {}).then((m) => { frappe.show_alert({ message: (m && m.message) || __("Done"), indicator: "green" }, 6); load(); });
					frappe.route_options = a.options || null; frappe.set_route(...a.route);
				});
			$out.find(".hsx-xl").on("click", () => frappe.tools.downloadify([r.cols.map((c) => c.label)].concat(r.rows.map((row) => row.cells.map(plain))), null, title));
		});
	}

	const plain = (c) => {
		if (c === null || c === undefined) return "";
		if (typeof c !== "object") return c;
		if (c.code) return c.code;
		if (c.main !== undefined) return c.main;
		if (c.lines) return c.lines.join("; ");
		if (c.date !== undefined) return c.date || "";
		if (c.pill !== undefined) return c.pill;
		if (c.money !== undefined) return c.money;
		if (c.bar !== undefined) return c.bar;
		return "";
	};

	// v1.7.0: free layouts (corporate tax computation, group structure): a grid of blocks — steps, statement, list, groups, table
	const money = (v, cur) => (v === null || v === undefined || v === "" ? "—" : `${cur ? hm_esc(cur) + " " : ""}${hm_esc(format_number(v, null, 2))}`);
	const act_html = (acts, cls) => (acts || []).map((a, i) => `<button class="btn btn-xs ${a.primary ? "btn-primary" : "btn-default"} hsx-bact" data-a="${hm_esc(JSON.stringify(a))}">${a.icon ? frappe.utils.icon(a.icon, "xs") + " " : ""}${hm_esc(a.label)}</button>`).join(" ");
	function block(b) {
		// v1.8.4: a stepper in a card (BOQ: from tender to contract), the prototype's flow
		if (b.type === "flow") return ui.card(b.title, `<div class="hsx-steps hsx-flow">${b.steps.map((t, i) => `<div class="hsx-step ${i < b.at ? "done" : i === b.at ? "on" : ""}"><i>${i < b.at ? frappe.utils.icon("check", "xs") : i + 1}</i><span>${hm_esc(t)}</span></div>`).join("")}</div>${b.note ? `<p class="text-muted small" style="margin:10px 0 0">${hm_esc(b.note)}</p>` : ""}`, { sub: b.sub });
		if (b.type === "steps") return `<div class="hsx-steps">${b.steps.map((t, i) => `<div class="hsx-step ${i < b.at ? "done" : i === b.at ? "on" : ""}"><i>${i < b.at ? frappe.utils.icon("check", "xs") : i + 1}</i><span>${hm_esc(t)}</span></div>`).join("")}</div>`;
		if (b.type === "statement") return ui.card(b.title, `<div class="hsx-stmt">${b.lines.map((l) => `<div class="hsx-sl ${l.hl ? "hl " + l.hl : ""} ${l.total ? "total" : ""} ${l.muted ? "muted" : ""}" ${l.dt ? `data-dt="${hm_esc(l.dt)}" data-name="${hm_esc(l.name)}"` : ""}>
			<span>${hm_esc(l.label)}${l.sub ? `<small>${hm_esc(l.sub)}</small>` : ""}</span><b>${l.sign ? hm_esc(l.sign) + " " : ""}${l.text !== undefined ? hm_esc(l.text) : money(l.value, l.currency)}</b></div>`).join("")}</div>`, { sub: b.sub, actions: act_html(b.actions) });
		if (b.type === "list") return ui.card(b.title, `<div class="hsx-blist">${b.items.map((it) => `<div class="hsx-bli" ${it.dt ? `data-dt="${hm_esc(it.dt)}" data-name="${hm_esc(it.name)}"` : ""}><span><b>${hm_esc(it.label)}</b>${it.sub ? `<small>${hm_esc(it.sub)}</small>` : ""}</span>
			<em>${it.value !== undefined ? hipersign.module.cell(it.value) : ""}</em></div>`).join("") || `<div class="hsx-empty">${hm_esc(b.empty || __("Nothing here."))}</div>`}${b.foot ? `<div class="hsx-bfoot">${act_html(b.foot)}</div>` : ""}${b.note ? `<div class="text-muted small" style="margin-top:8px">${hm_esc(b.note)}</div>` : ""}</div>`, { sub: b.sub, actions: act_html(b.actions) });
		if (b.type === "groups") return ui.card(b.title, `${b.banner ? `<div class="hsx-gban">${frappe.utils.icon("building", "sm")} <b>${hm_esc(b.banner.title)}</b> <span>${hm_esc(b.banner.sub || "")}</span></div>` : ""}
			${b.groups.map((g) => `<div class="hsx-grp"><div class="hsx-grp-h"><b>${hm_esc(g.title)}</b> <span>${hm_esc(g.sub || "")}</span></div><div class="hsx-grp-c">${g.cards.map((c) => `<div class="hsx-gc" ${c.dt ? `data-dt="${hm_esc(c.dt)}" data-name="${hm_esc(c.name)}"` : ""}>
				<b>${hm_esc(c.title)}</b>${c.sub ? `<div class="text-muted">${hm_esc(c.sub)}</div>` : ""}<div>${c.tag ? `<span class="hsx-tag">${hm_esc(c.tag)}</span> ` : ""}${hm_esc(c.meta || "")}</div>${(c.lines || []).map((l) => `<div>${hm_esc(l)}</div>`).join("")}</div>`).join("")}</div></div>`).join("")}`, { sub: b.sub });
		if (b.type === "table") { const th = hipersign.module.thead(b.cols, b.rows); return ui.card(b.title, b.rows.length ? `<div class="hsx-tw"><table class="hsx-t hsx-mlist"><thead><tr>${th.html}</tr></thead>
			<tbody>${b.rows.map((row) => `<tr class="${row.cls || ""}" ${row.dt ? `data-dt="${hm_esc(row.dt)}" data-name="${hm_esc(row.name)}"` : ""}>${row.cells.map((c, i) => `<td class="${(b.cols[i] || {}).cls || ""}">${hipersign.module.tcell(c, i, th.one)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
			: `<div class="hsx-empty">${hm_esc(b.empty || __("Nothing here."))}</div>`, { sub: b.sub, actions: act_html(b.actions) }); }
		// v1.8.0: the process explained (phases → steps with who, documents, approval and trigger) and a summary card
		if (b.type === "how") return ui.card(b.title, `<div class="hsx-how">${b.phases.map((ph, pi) => `<div class="hsx-how-ph"><div class="hsx-how-h"><span class="hsx-dotn">${pi + 1}</span>${hm_esc(ph.name)}
			<span class="text-muted small">${__("Steps {0}–{1}", [ph.a + 1, ph.b])}</span></div>${b.steps.slice(ph.a, ph.b).map((st, j) => `<details class="hsx-how-s"><summary><span class="hsx-code">${ph.a + j + 1}</span>
			<b>${hm_esc(st.name)}</b><span class="text-muted small hsx-how-who">${hm_esc(st.who)}</span></summary><div class="hsx-how-kv">
			<div><span>${__("What happens")}</span><span>${hm_esc(st.what)}</span></div><div><span>${__("Documents")}</span><span>${hm_esc(st.docs)}</span></div>
			<div><span>${__("Approval")}</span><span>${hm_esc(st.approval)}</span></div><div><span>${__("Next trigger")}</span><span>${hm_esc(st.next)}</span></div></div></details>`).join("")}</div>`).join("")}</div>`, { sub: b.sub });
		if (b.type === "card") return hipersign.module.card_html(b.card);
		// v1.8.0 (prototype p19): work orders on the floor as tiles — quantity done of planned, progress, the operations' state
		if (b.type === "tiles") return ui.card(b.title, b.tiles.length ? `<div class="hsx-tiles">${b.tiles.map((t) => `<button type="button" class="hsx-tile" data-dt="${hm_esc(t.dt)}" data-name="${hm_esc(t.name)}">
			<div class="hsx-tile-h"><span class="hsx-code">${hm_esc(t.code)}</span><span class="hsx-pill ${hm_esc(t.tone || "blue")}">${hm_esc(t.pill)}</span>${t.late ? `<span class="hsx-pill red">${hm_esc(t.late)}</span>` : ""}</div>
			<b>${hm_esc(t.title)}</b><div class="hsx-tile-big">${hm_esc(t.big)}<small> / ${hm_esc(t.of)}</small></div><span class="hp-bar"><span style="width:${Math.min(100, t.bar)}%"></span></span>
			<div class="hsx-tile-ops">${(t.chips || []).map((c) => `<span class="${hm_esc(c.st)}" title="${hm_esc(c.title || "")}">${hm_esc(c.label)}</span>`).join("")}</div></button>`).join("")}</div>`
			: `<div class="hsx-empty">${hm_esc(b.empty || __("Nothing here."))}</div>`, { sub: b.sub });
		if (b.type === "note") return `<div class="hsx-bnote">${hm_esc(b.text)}${b.actions ? " " + act_html(b.actions) : ""}</div>`;
		return "";
	}
	function blocks($out, bl) {
		$out.html(`<div class="hsx-blocks">${bl.map((b) => `<div class="hsx-blk" style="grid-column:span ${b.span || 3}">${block(b)}</div>`).join("")}</div>`);
		$out.find(".hsx-bli[data-dt], .hsx-gc[data-dt], .hsx-sl[data-dt], .hsx-tile[data-dt]").on("click", function () { open($(this).attr("data-dt"), $(this).attr("data-name")); });
		$out.find(".hsx-bact").on("click", function (e) {
			e.stopPropagation();
			const a = JSON.parse($(this).attr("data-a"));
			const after = () => { load(); };
			if (a.open) return open(a.open[0], a.open[1]);
			if (a.url) return window.open(frappe.urllib.get_full_url(a.url));
			if (a.new) return hipersign.fm ? hipersign.fm.new(a.new, a.values || {}) : frappe.new_doc(a.new, a.values || {});
			if (a.route) { frappe.route_options = a.options || null; return frappe.set_route(...a.route); }
			if (a.method) {
				const go = () => frappe.xcall(a.method, a.args || {}).then((m) => { if (m && m.file) window.open(m.file); frappe.show_alert({ message: (m && m.message) || __("Done"), indicator: "green" }, 6); after(); });
				return a.confirm ? frappe.confirm(a.confirm, go) : go();
			}
		});
	}

	// a read-only board (shipments by stage): cards open their record
	function kanban($out, cols, n) {
		$out.html(`<div class="hsx-board hsx-kanban" style="${n ? `grid-template-columns:repeat(${n},minmax(0,1fr))` : ""}">${cols.map((c) => `<div class="hsx-col"><div class="hsx-col-h"><b>${hm_esc(c.label)}</b><span>${c.count}</span></div>
			${c.cards.length ? c.cards.map((k) => `<div class="hsx-kc" data-dt="${hm_esc(k.dt)}" data-name="${hm_esc(k.name)}">
				<div class="hsx-kc-top"><span class="hsx-code">${hm_esc(k.code)}</span>${k.pill ? hipersign.module.cell({ pill: k.pill }) : ""}</div>
				<b>${hm_esc(k.title)}</b>${(k.lines || []).filter(Boolean).map((l) => `<div class="text-muted small">${hm_esc(l)}</div>`).join("")}
				${k.warn ? `<div class="hsx-kc-warn">${frappe.utils.icon("triangle-alert", "xs")} ${hm_esc(k.warn)}</div>` : ""}
				${k.button ? `<div style="margin-top:6px">${hipersign.module.cell(Object.assign({ button: k.button.label, primary: 1 }, k.button))}</div>` : ""}</div>`).join("")
				: `<div class="text-muted small" style="padding:4px 2px">${__("None")}</div>`}</div>`).join("")}</div>`);
		$out.find(".hsx-kc").on("click", function (e) { if ($(e.target).closest(".hsx-cbtn").length) return; open($(this).attr("data-dt"), $(this).attr("data-name")); });
	}

	function board($out, cols) {
		const cur = (frappe.boot.sysdefaults && frappe.boot.sysdefaults.currency) || "AED";
		$out.html(`<div class="hsx-board">${cols.map((c) => `<div class="hsx-col" data-stage="${hm_esc(c.stage)}"><div class="hsx-col-h">${hipersign.module.cell({ pill: c.stage })}
			<span>${c.count} · ${hm_esc(ui.money(c.value, cur, true))}</span></div>${c.cards.map((k) => `<div class="hsx-lc ${k.overdue ? "overdue" : ""}" draggable="true" data-name="${hm_esc(k.name)}">
			<span class="lc-ow" title="${hm_esc(k.owner_name)}">${hm_esc(k.owner)}</span><b>${hm_esc(k.title)}</b><span class="text-muted">${hm_esc(k.interest || "")}</span>
			<div class="lc-row"><b style="display:inline">${hm_esc(ui.money(k.value, cur, true))}</b>${k.follow ? `<span class="${k.overdue ? "text-danger" : "text-muted"}">${frappe.utils.icon("clock", "xs")} ${hm_esc(frappe.datetime.str_to_user(k.follow))}</span>` : ""}</div>
			<div class="text-muted small" style="margin-top:4px">${hm_esc(__(k.source || ""))}</div></div>`).join("")}</div>`).join("")}</div>`);
		let drag = null;
		$out.find(".hsx-lc").on("dragstart", function (e) { drag = $(this).attr("data-name"); $(this).addClass("dragging"); e.originalEvent.dataTransfer.setData("text/plain", drag); })
			.on("dragend", function () { $(this).removeClass("dragging"); $out.find(".hsx-col").removeClass("drop"); });
		$out.find(".hsx-col").on("dragover", function (e) { e.preventDefault(); $(this).addClass("drop"); }).on("dragleave", function () { $(this).removeClass("drop"); })
			.on("drop", function (e) {
				e.preventDefault();
				const stage = $(this).attr("data-stage");
				if (!drag) return;
				const go = (args) => frappe.xcall("hipersign_trading.api.panel.action", { doctype: "Lead", name: drag, action: "lead_stage", args })
					.then((r) => { frappe.show_alert({ message: r.message, indicator: "green" }); load(); });
				if (stage === "Lost") hipersign.panel.clients.lead_lost({ name: drag }, {}, () => load());
				else go({ stage });
			});
	}

	v.$body.on("click", ".hsx-mlink", function () { const l = st.data.links[+$(this).attr("data-li")]; frappe.route_options = l[2] || null; frappe.set_route(...l[1]); });
	v.$body.on("click", ".hsx-mtabs button", function () { st.tab = $(this).attr("data-tab"); tab(); });
	v.$body.on("click", ".hsx-chips [data-chip]", function () { st.chip[st.tab] = $(this).attr("data-chip"); tab(); });
	v.$body.on("click", "[data-k]", function () {
		const k = ($(this).attr("data-tabk") && st.tab_kpis ? st.tab_kpis : st.data.kpis)[+$(this).attr("data-k")];
		if (!k) return;
		if (k.tab) { st.tab = k.tab; if (k.chip) st.chip[k.tab] = k.chip; tab(); }
		else if (k.route) frappe.set_route(...k.route);
	});
	v.$body.on("change", ".hsx-owner", function () { st.owner = $(this).val(); load(); });
	v.$body.on("change", ".hsx-source", function () { st.source = $(this).val(); load(); });
	v.$body.on("input", ".hsx-q", frappe.utils.debounce(function () { st.q = $(this).val(); rows(); }, 300));
	const open = (dt, name) => (hipersign.panel && hipersign.panel.has && hipersign.panel.has(dt) ? hipersign.panel.open(dt, name) : frappe.set_route("Form", dt, name));
	v.$body.on("click", "tr[data-dt]", function (e) { if ($(e.target).closest(".hsx-link").length) return; open($(this).attr("data-dt"), $(this).attr("data-name")); });
	// v1.8.0: Projects actions — Approve, Record certification, Create invoice, Receive at site … — then the page reloads
	const pact = ($el, extra) => {
		const args = Object.assign(JSON.parse($el.attr("data-pargs") || "{}"), extra || {});
		// v1.8.0: Manufacturing buttons carry their own method (hipersign_trading.api.manufacturing.act)
		const go = () => { $el.prop("disabled", true); return frappe.xcall($el.attr("data-pmethod") || "hipersign_trading.api.projects.act", { action: $el.attr("data-pact"), name: $el.attr("data-pname"), args })
			.then((r) => { frappe.show_alert({ message: (r && r.message) || __("Done"), indicator: "green" }, 7); load(); $(document).trigger("hs-projects-changed"); })
			.catch(() => { $el.prop("disabled", false); load(); }); };
		return $el.attr("data-pconfirm") ? frappe.confirm(hm_esc($el.attr("data-pconfirm")), go) : go();
	};
	v.$body.on("change", ".hsx-cin", function () { pact($(this), { pct: flt($(this).val()) }); });
	v.$body.on("click", ".hsx-cbtn[data-pact]", function (e) { e.stopPropagation(); e.stopImmediatePropagation(); pact($(this)); });
	v.$body.on("click", ".hsx-cbtn[data-pjs]", function (e) {
		e.stopPropagation(); e.stopImmediatePropagation();
		const fn = (hipersign.projects || {})[$(this).attr("data-pjs")];
		if (fn) fn($(this).attr("data-pname"), () => { load(); $(document).trigger("hs-projects-changed"); });
	});
	v.$body.on("click", ".hsx-cbtn", function (e) {
		e.stopPropagation();
		const $b = $(this);
		if ($b.attr("data-pact") || $b.attr("data-pjs")) return;
		if ($b.attr("data-ldt")) return open($b.attr("data-ldt"), $b.attr("data-lname"));
		if ($b.attr("data-make") === "wps") return window.open("/api/method/hipersign_trading.api.wps.download_sif?payroll_entry=" + encodeURIComponent($b.attr("data-source")));
		// v1.7.0: deliver / receive / pay / invoice open the prototype's modal; the page reloads its rows after
		if (hipersign.cm && hipersign.cm.make($b.attr("data-make"), $b.attr("data-source"), (r) => { if (v.reload) v.reload(); else if (wrapper.hs_reload) wrapper.hs_reload();
			if (hipersign.panel && hipersign.panel.has(r.doctype)) hipersign.panel.open(r.doctype, r.name); })) return;
		$b.prop("disabled", true);
		frappe.xcall("hipersign_trading.api.panel.make", { method: $b.attr("data-make"), source_name: $b.attr("data-source") })
			.then((doc) => { const d = frappe.model.sync(doc)[0]; frappe.set_route("Form", d.doctype, d.name); })
			.finally(() => $b.prop("disabled", false));
	});
	v.$body.on("click", ".hsx-link", function (e) { e.stopPropagation(); open($(this).attr("data-ldt"), $(this).attr("data-lname")); });
	v.$body.on("click", ".hsx-lc", function () { hipersign.panel.open("Lead", $(this).attr("data-name")); });
	v.$actions.on("click", ".hsx-new", function () { const dt = $(this).attr("data-dt"); hipersign.fm ? hipersign.fm.new(dt) : frappe.new_doc(dt); });
	$(document).on("hs-scope-change", () => { if ($(wrapper).is(":visible")) load(); });
	// a panel action (stage change, lost, approval…) shows on the page when the panel closes
	$(document).on("hp-changed", () => { if ($(wrapper).is(":visible")) load(); });
	wrapper.hs_reload = load;
	load();
};
