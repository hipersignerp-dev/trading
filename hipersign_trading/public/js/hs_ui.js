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
			if (Math.abs(v) >= n) return `${cur} ${(v / n).toFixed(Math.abs(v) >= n * 100 ? 0 : 2).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "") /* v1.8.2: zeros only after the point (110K stayed 11K) */}${u}`;
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
		<div class="hs-band" style="display:none"></div><div class="hsx-body"></div></div>`).appendTo(page.main);
	// v1.8.3 (prototype p20): the graph band sits between the page head and the body, so a body redraw keeps it
	const $band = $wrap.find(".hs-band");
	const band = () => opts.band && hipersign.band && hipersign.band.mount($band, typeof opts.band === "function" ? opts.band() : opts.band);
	if (opts.band) {
		band();
		$(wrapper).on("show", () => { if ($band.data("hs-at") && Date.now() - $band.data("hs-at") > 60000) band(); });
		$(document).on("hs-scope-change", () => { if ($(wrapper).is(":visible")) band(); });
	}
	return { page, $wrap, $actions: $wrap.find(".hsx-ph-actions"), $body: $wrap.find(".hsx-body"), $band, band };
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

// v1.8.4: Chinese month and weekday names in dates the browser formats ("07 11月" not "07 Nov") — Frappe ships only the
// English moment locale; the server already formats Chinese (and Arabic) months
(function () {
	const zh = () => {
		const lang = (frappe.boot && frappe.boot.lang) || "";
		if (!lang.startsWith("zh") || typeof moment === "undefined") return;
		if (!moment.locales().includes("zh-hs")) {
			moment.defineLocale("zh-hs", {
				parentLocale: "en",
				months: ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
				monthsShort: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
				weekdays: ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"],
				weekdaysShort: ["周日", "周一", "周二", "周三", "周四", "周五", "周六"],
				weekdaysMin: ["日", "一", "二", "三", "四", "五", "六"],
				meridiem: (h) => (h < 12 ? "上午" : "下午"),
				relativeTime: { future: "%s后", past: "%s前", s: "几秒", ss: "%d 秒", m: "1 分钟", mm: "%d 分钟", h: "1 小时", hh: "%d 小时", d: "1 天", dd: "%d 天", M: "1 个月", MM: "%d 个月", y: "1 年", yy: "%d 年" },
				week: { dow: (moment.localeData("en").firstDayOfWeek && moment.localeData("en").firstDayOfWeek()) || 1, doy: 4 },
			});
		}
		moment.locale("zh-hs");
	};
	$(document).on("startup", zh);
	if (frappe.boot && frappe.boot.lang) zh();
})();
