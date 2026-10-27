// Hipersign ERP v1.5 — small building blocks for the prototype's screens (Home, Approvals, Alerts…): page header,
// KPI cards, cards, tables, pills. Styles in hipersign_theme.css (.hsx-*), which also work with the standard ERPNext theme.
frappe.provide("hipersign.ui");

hipersign.ui.esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));

hipersign.ui.money = function (v, cur, compact) {
	v = flt(v);
	cur = cur || (frappe.boot.sysdefaults && frappe.boot.sysdefaults.currency) || "AED";
	if (compact && Math.abs(v) >= 1000) {
		const units = [[1e9, "B"], [1e6, "M"], [1e3, "K"]];
		for (const [n, u] of units) {
			if (Math.abs(v) >= n) return `${cur} ${(v / n).toFixed(Math.abs(v) >= n * 100 ? 0 : 2).replace(/\.?0+$/, "")}${u}`;
		}
	}
	// the prototype writes the currency code first (AED 1,234.50), never the local symbol
	return `${cur} ${format_number(v, null, compact ? 0 : 2)}`;
};

hipersign.ui.icon = (name, size) => frappe.utils.icon(name, size || "sm");

// a page in the prototype's layout: Frappe's page head with the title, then a description line and actions
hipersign.ui.page = function (wrapper, opts) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: opts.title, single_column: true });
	const $wrap = $(`<div class="hsx-wrap">
		<div class="hsx-ph"><p class="hsx-desc">${hipersign.ui.esc(opts.desc || "")}</p><div class="hsx-ph-actions"></div></div>
		<div class="hsx-body"></div></div>`).appendTo(page.main);
	return { page, $wrap, $actions: $wrap.find(".hsx-ph-actions"), $body: $wrap.find(".hsx-body") };
};

hipersign.ui.route_attr = (route, options) => (route ? ` data-hs-route='${hipersign.ui.esc(JSON.stringify(route))}'` + (options ? ` data-hs-opts='${hipersign.ui.esc(JSON.stringify(options))}'` : "") : "");

hipersign.ui.kpi = function (k) {
	const val = k.money ? hipersign.ui.money(k.value, k.currency, true) : (k.value == null ? "—" : hipersign.ui.esc(k.value));
	return `<button class="hsx-kpi tone-${k.tone || "blue"}"${hipersign.ui.route_attr(k.route, k.options)}>
		${k.icon ? `<span class="hsx-kpi-ic">${hipersign.ui.icon(k.icon, "md")}</span>` : ""}
		<span class="hsx-kpi-t"><span class="hsx-kpi-l">${hipersign.ui.esc(k.label)}</span><b class="hsx-kpi-v">${val}</b>${k.sub ? `<span class="hsx-kpi-s">${hipersign.ui.esc(k.sub)}</span>` : ""}</span>
	</button>`;
};

hipersign.ui.card = function (title, body, opts) {
	opts = opts || {};
	return `<div class="hsx-card ${opts.cls || ""}">${title ? `<div class="hsx-card-h"><h3>${opts.icon ? hipersign.ui.icon(opts.icon) : ""} ${hipersign.ui.esc(title)}${opts.sub ? ` <small>${hipersign.ui.esc(opts.sub)}</small>` : ""}</h3><div class="hsx-card-a">${opts.actions || ""}</div></div>` : ""}
		<div class="hsx-card-b">${body}</div></div>`;
};

// cols: [{label, cls}], rows: [{cells: [...html], route, options}]
hipersign.ui.table = function (cols, rows, empty) {
	if (!rows.length) return `<div class="hsx-empty">${hipersign.ui.esc(empty || __("Nothing here."))}</div>`;
	return `<div class="hsx-tw"><table class="hsx-t"><thead><tr>${cols.map((c) => `<th class="${c.cls || ""}">${hipersign.ui.esc(c.label)}</th>`).join("")}</tr></thead>
		<tbody>${rows.map((r) => `<tr${hipersign.ui.route_attr(r.route, r.options)} class="${r.route ? "hsx-click" : ""}">${r.cells.map((c, i) => `<td class="${cols[i] && cols[i].cls || ""}">${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
};

hipersign.ui.pill = (text, tone) => `<span class="hsx-pill ${tone || "grey"}">${hipersign.ui.esc(text)}</span>`;

hipersign.ui.seg = function (name, options, current) {
	return `<div class="hsx-seg" data-seg="${name}">${options.map(([v, l]) => `<button class="${v === current ? "on" : ""}" data-v="${hipersign.ui.esc(v)}">${hipersign.ui.esc(l)}</button>`).join("")}</div>`;
};

hipersign.ui.go = function (route, options) {
	if (!route) return;
	if (options) frappe.route_options = options;
	frappe.set_route(...route);
};

// any element with data-hs-route opens it
$(document).on("click", ".hsx-wrap [data-hs-route]", function (e) {
	if ($(e.target).closest("button, a, input, select, textarea").not(this).length) return;
	const r = JSON.parse($(this).attr("data-hs-route"));
	const o = $(this).attr("data-hs-opts");
	hipersign.ui.go(r, o ? JSON.parse(o) : null);
});

hipersign.ui.loading = ($el) => $el.html(`<div class="hsx-loading">${__("Loading…")}</div>`);

hipersign.ui.companies = function () {
	return frappe.xcall("frappe.client.get_list", { doctype: "Company", filters: { is_group: 0 }, fields: ["name"], limit_page_length: 50 }).then((r) => (r || []).map((c) => c.name));
};
