// v1.8.4 (#37): Reports — every report this user may open, by area, with search and favourites (api/reports.py).
// The sidebar's "Reports" sub-items open it on one area (route option hs_group).
frappe.pages["hipersign-reports"].on_page_load = function (wrapper) {
	const ui = hipersign.ui, esc = ui.esc;
	const v = ui.page(wrapper, { title: __("Reports"), desc: __("Every report you can open, by area. Star the ones you use most; they stay at the top.") });
	v.$wrap.addClass("hsx-mod"); // the module pages' chips and cards
	let data = null, q = "", group = "";
	wrapper.hs_reports_group = "";
	const star = (n, on) => `<button class="hs-rp-star ${on ? "on" : ""}" data-fav="${esc(n)}" title="${esc(on ? __("Remove from favourites") : __("Add to favourites"))}"
		aria-pressed="${on ? "true" : "false"}">${frappe.utils.icon(on ? "star-filled" : "star", "sm")}</button>`;
	const card = (r) => `<div class="hs-rp-card" data-report="${esc(r.name)}" role="link" tabindex="0">
		<div class="hs-rp-ic">${frappe.utils.icon("chart-column", "sm")}</div><div class="hs-rp-t"><b>${esc(r.label)}</b><span>${esc(r.doctype || __(r.type || ""))}</span></div>
		${star(r.name, data.favourites.includes(r.name))}</div>`;
	function render() {
		const had = document.activeElement && document.activeElement.classList.contains("hs-rp-q");
		const match = (r) => !q || (r.label + " " + r.name + " " + (r.doctype || "")).toLowerCase().includes(q);
		const groups = data.groups.filter((g) => !group || g.key === group);
		const all = Object.fromEntries(data.groups.flatMap((g) => g.reports.map((r) => [r.name, r])));
		const favs = data.favourites.map((n) => all[n]).filter(Boolean).filter(match);
		const chips = `<div class="hsx-chips hs-rp-chips"><button data-g="" class="${group ? "" : "on"}">${esc(__("All"))}</button>${data.groups.map((g) =>
			`<button data-g="${esc(g.key)}" class="${g.key === group ? "on" : ""}">${esc(g.label)} <span class="hsx-tcount">${g.reports.length}</span></button>`).join("")}</div>`;
		const secs = groups.map((g) => {
			const rs = g.reports.filter(match);
			return rs.length ? `<div class="hsx-card hs-rp-sec"><div class="hsx-card-h"><h3>${frappe.utils.icon(g.icon, "sm")} ${esc(g.label)} <small>${rs.length}</small></h3></div>
				<div class="hsx-card-b"><div class="hs-rp-grid">${rs.map(card).join("")}</div></div></div>` : "";
		}).join("");
		v.$body.html(`<div class="hs-rp-top"><input class="form-control hs-rp-q" placeholder="${esc(__("Search reports…"))}" value="${esc(q)}"></div>${chips}
			${favs.length && !group ? `<div class="hsx-card hs-rp-sec"><div class="hsx-card-h"><h3>${frappe.utils.icon("star", "sm")} ${esc(__("Favourites"))}</h3></div>
				<div class="hsx-card-b"><div class="hs-rp-grid">${favs.map(card).join("")}</div></div></div>` : ""}
			${secs || `<div class="hsx-empty">${esc(__("No report matches."))}</div>`}`);
		if (had) v.$body.find(".hs-rp-q").trigger("focus").get(0).setSelectionRange(q.length, q.length);
	}
	wrapper.hs_reports_goto = function (g) {
		group = g || "";
		wrapper.hs_reports_group = group;
		if (data) render();
		$(document).trigger("hs-module-tab");
	};
	function load() {
		const want = (frappe.route_options || {}).hs_group;
		if (want !== undefined) { group = want || ""; wrapper.hs_reports_group = group; frappe.route_options = null; }
		frappe.xcall("hipersign_trading.api.reports.get_reports").then((r) => { data = r; render(); $(document).trigger("hs-module-tab"); });
	}
	v.$body.on("input", ".hs-rp-q", frappe.utils.debounce(function () { q = ($(this).val() || "").toLowerCase().trim(); render(); }, 200));
	v.$body.on("click", ".hs-rp-chips [data-g]", function () { wrapper.hs_reports_goto($(this).attr("data-g")); });
	v.$body.on("click keydown", ".hs-rp-card", function (e) {
		if (e.type === "keydown" && e.key !== "Enter") return;
		if ($(e.target).closest(".hs-rp-star").length) return;
		frappe.set_route("query-report", $(this).attr("data-report"));
	});
	v.$body.on("click", ".hs-rp-star", function (e) {
		e.stopPropagation();
		const n = $(this).attr("data-fav"), on = !data.favourites.includes(n);
		frappe.xcall("hipersign_trading.api.reports.set_favourite", { report: n, on: on ? 1 : 0 }).then((f) => { data.favourites = f; render(); });
	});
	wrapper.hs_reload = load;
	load();
};
frappe.pages["hipersign-reports"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once && (frappe.route_options || {}).hs_group !== undefined) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
