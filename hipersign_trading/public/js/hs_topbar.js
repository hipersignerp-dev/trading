// Hipersign ERP — the prototype's top bar above every desk page (v1.5.4; v1.5.6: menu toggle, real search, one scope and one
// period drop-down, the "+ New" panel, the grouped bell, Switch user, the demo and view-only banners).
// Only with the Hipersign desk theme (html.hs-theme). Hidden on the app launcher (/desk), which has its own header.
frappe.provide("hipersign.topbar");
frappe.provide("hipersign.create");

const hs_esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
const hs_icon = (n, size) => frappe.utils.icon(n, size || "sm");

// ---------------------------------------------------------------- the prototype's "Create new" groups
// [label, icon, action] — action: {dt, values, mode?} opens a document; {route} opens a page; {fn} runs a function
hipersign.create.GROUPS = () => [
	[__("Sales"), [
		[__("Lead"), "users", { dt: "Lead" }],
		[__("Quotation"), "file", { dt: "Quotation" }],
		[__("Sales order"), "list", { dt: "Sales Order" }],
		[__("Customer"), "users", { dt: "Customer" }],
		[__("Customer group"), "tag", { dt: "Customer Group" }],
	]],
	[__("Purchasing & imports"), [
		[__("Purchase order"), "buying", { dt: "Purchase Order" }],
		[__("Supplier"), "organization", { dt: "Supplier" }],
		[__("Service provider"), "share", { dt: "Supplier", values: { hs_supplier_kind: "Freight & Shipping" }, label: "Service provider" }],
		[__("Import shipment"), "share", { dt: "Import Shipment", feature: "imports" }],
		[__("Letter of credit"), "file", { dt: "Letter of Credit", feature: "lc" }],
		[__("Bank guarantee"), "file", { dt: "Bank Guarantee", feature: "lc" }],
	]],
	[__("Exports"), [
		[__("Export order"), "globe", { dt: "Sales Order", values: { hs_is_export: 1 }, feature: "exports", full: 1 }],
		[__("Export shipment"), "share", { dt: "Export Shipment", feature: "exports" }],
	]],
	[__("Products, services & stock"), [
		[__("Purchase request"), "list", { dt: "Material Request", values: { material_request_type: "Purchase" }, feature: "rfq" }],
		[__("Stock item"), "stock", { dt: "Item", values: { is_stock_item: 1 } }],
		[__("Service"), "tool", { dt: "Item", values: { is_stock_item: 0 }, kind: "service" }],
		[__("Warehouse"), "organization", { dt: "Warehouse" }],
		[__("Stock transfer"), "stock", { dt: "Stock Entry", values: { stock_entry_type: "Material Transfer", purpose: "Material Transfer" }, full: 1 }],
		[__("Stock count"), "list", { dt: "Stock Reconciliation", full: 1 }],
	]],
	[__("Warranty"), [
		[__("Serial number look-up"), "search", { route: ["serial-lookup"], feature: "serial" }],
		[__("Warranty claim"), "tool", { dt: "Warranty Claim", feature: "serial" }],
	]],
	[__("Supplier bills"), [[__("Supplier bill"), "file", { dt: "Purchase Invoice" }]]],
	[__("Accounting"), [
		[__("Journal entry"), "file", { dt: "Journal Entry" }],
		[__("Account"), "list", { route: ["Tree", "Account"] }],
	]],
	[__("Cheques"), [
		[__("Cheque received (PDC)"), "money-coins-1", { dt: "Post Dated Cheque", values: { direction: "Received" }, feature: "pdc" }],
		[__("Cheque issued (PDC)"), "money-coins-1", { dt: "Post Dated Cheque", values: { direction: "Issued" }, feature: "pdc" }],
	]],
	[__("Returns"), [
		[__("Credit note (sales return)"), "file", { dt: "Sales Invoice", values: { is_return: 1 }, full: 1, label: "Credit note" }],
		[__("Debit note (purchase return)"), "file", { dt: "Purchase Invoice", values: { is_return: 1 }, full: 1, label: "Debit note" }],
	]],
	[__("Delivery"), [
		[__("Driver & vehicle"), "users", { dt: "Driver", feature: "trips" }],
		[__("Delivery trip"), "share", { dt: "Delivery Trip", feature: "trips", full: 1 }],
	]],
	[__("Finance"), [
		[__("Invoice"), "file", { dt: "Sales Invoice" }],
		[__("Receive payment"), "money-coins-1", { dt: "Payment Entry", values: { payment_type: "Receive", party_type: "Customer" } }],
		[__("Bank account"), "money-coins-1", { dt: "Bank Account" }],
		[__("Payment terms"), "calendar", { dt: "Payment Terms Template" }],
		[__("Currency"), "money-coins-1", { dt: "Currency Exchange" }],
		[__("Credit limit request"), "money-coins-1", { dt: "Credit Limit Request" }],
	]],
	[__("People & assets"), [
		[__("Expense claim"), "file", { dt: "Expense Claim", feature: "hr" }],
		[__("Employee advance"), "money-coins-1", { dt: "Employee Advance", feature: "hr" }],
		[__("Employee"), "users", { dt: "Employee" }],
		[__("Leave request"), "calendar", { dt: "Leave Application", feature: "hr" }],
		[__("Fixed asset"), "organization", { dt: "Asset", feature: "assets" }],
	]],
	[__("Administration"), [[__("User"), "users", { dt: "User", admin: 1 }]]],
];

hipersign.create.allowed = function (a) {
	const info = (frappe.boot && frappe.boot.hipersign) || {};
	if (a.feature && info.features && info.features[a.feature] === false) return false;
	if (a.admin && !frappe.user.has_role("System Manager")) return false;
	if (a.route) return true;
	if (!frappe.boot.user.can_create || !a.dt) return false;
	return frappe.boot.user.can_create.includes(a.dt);
};

// the groups the user may use: [[group, [[label, icon, action], ...]], ...]
hipersign.create.visible = () =>
	hipersign.create.GROUPS().map(([g, items]) => [g, items.filter(([, , a]) => hipersign.create.allowed(a))]).filter(([, items]) => items.length);

hipersign.create.has_modes = (dt) => hipersign.fm && (hipersign.fm.COVERED || []).includes(dt);

// open an entry; mode = "Quick" | "Standard" | "Detailed" | undefined (the user's default)
hipersign.create.open = function (a, mode) {
	if (a.route) return frappe.set_route(...a.route);
	const values = Object.assign({}, a.values || {});
	// v1.5.6: credit / debit notes and other preset documents always open the full form with their values set,
	// so "Is Return" stays ticked (the quick dialog used to drop it)
	if (a.full || !hipersign.create.has_modes(a.dt)) return hipersign.create.new_doc(a.dt, values);
	if (mode) return hipersign.fm.remember(a.dt, mode).then(() => hipersign.fm.new(a.dt, values));
	return hipersign.fm.new(a.dt, values);
};

hipersign.create.new_doc = function (dt, values) {
	frappe.model.with_doctype(dt, () => {
		const doc = frappe.model.get_new_doc(dt);
		Object.entries(values || {}).forEach(([k, v]) => { if (frappe.meta.has_field(dt, k) || k === "is_return") doc[k] = v; });
		frappe.set_route("Form", dt, doc.name);
	});
};

// ---------------------------------------------------------------- roles shown under the user's name
hipersign.topbar.ROLES = [
	["Managing Director", "Managing Director"], ["Accounts Manager", "Finance Manager"], ["Sales Manager", "Sales Manager"],
	["Purchase Manager", "Purchase Manager"], ["Stock Manager", "Warehouse Manager"], ["HR Manager", "HR Manager"],
	["Logistics Coordinator", "Logistics"], ["Accounts User", "Accountant"], ["Sales User", "Sales Executive"],
	["Purchase User", "Buyer"], ["Stock User", "Storekeeper"], ["Driver", "Driver"], ["Demo Viewer", "View-only demo"], ["System Manager", "Administrator"],
];

hipersign.topbar.role = function () {
	if (frappe.session.user === "Administrator") return __("Administrator");
	const roles = frappe.user_roles || [];
	const hit = hipersign.topbar.ROLES.find(([r]) => roles.includes(r));
	return hit ? __(hit[1]) : "";
};

hipersign.topbar.hidden_here = function () {
	let r = "";
	try {
		r = frappe.get_route_str ? frappe.get_route_str() : "";
	} catch (e) {
		r = (window.location.pathname || "").replace(/^\/(app|desk)\/?/, "");
	}
	return !r || r === "desktop" || r === "desk";
};

hipersign.topbar.state = { scope: null, period: "month", company: null, data: null };

hipersign.topbar.sync = function () {
	const hide = hipersign.topbar.hidden_here();
	$(".main-section > header.hs-topbar-host").toggle(!hide);
	document.documentElement.classList.toggle("hs-topbar-on", !hide && !!$(".hs-topbar").length);
	$(".hs-banners").toggle(!hide);
};

// ---------------------------------------------------------------- render
hipersign.topbar.render = function () {
	if (!document.documentElement.classList.contains("hs-theme") || frappe.session.user === "Guest") return;
	const $host = $(".main-section > header").first();
	if (!$host.length) return;
	if ($host.find(".hs-topbar").length) return hipersign.topbar.sync();
	const name = frappe.user.full_name ? frappe.user.full_name() : frappe.session.user;
	const ar = (frappe.boot.lang || "en").startsWith("ar");
	$host.addClass("hs-topbar-host").html(`
		<div class="hs-topbar">
			<button type="button" class="hs-tb-icon hs-tb-menu" title="${hs_esc(__("Menu"))}" aria-label="${hs_esc(__("Menu"))}">${hs_icon("menu")}</button>
			<div class="hs-tb-search">
				${hs_icon("search")}
				<input type="search" autocomplete="off" spellcheck="false" placeholder="${hs_esc(__("Search items, orders, customers, shipments…"))}" aria-label="${hs_esc(__("Search"))}">
				<kbd>/</kbd>
				<div class="hs-tb-results" hidden></div>
			</div>
			<span class="hs-tb-sp"></span>
			<div class="dropdown hs-tb-scope" hidden>
				<button type="button" class="hs-tb-pick" data-toggle="dropdown">${hs_icon("organization")}<span class="hs-tb-scope-l"></span>${hs_icon("chevron-down", "xs")}</button>
				<div class="dropdown-menu dropdown-menu-right hs-tb-menu-list hs-tb-scope-menu"></div>
			</div>
			<span class="hs-tb-scope-fixed" hidden></span>
			<div class="dropdown hs-tb-period">
				<button type="button" class="hs-tb-pick" data-toggle="dropdown">${hs_icon("calendar")}<span class="hs-tb-period-l"></span>${hs_icon("chevron-down", "xs")}</button>
				<div class="dropdown-menu dropdown-menu-right hs-tb-menu-list">
					${[["month", __("This month")], ["last_month", __("Last month")], ["ytd", __("Year to date")]]
						.map(([k, l]) => `<a class="dropdown-item" data-period="${k}">${hs_esc(l)}</a>`).join("")}
				</div>
			</div>
			<div class="hs-tb-newwrap">
				<button type="button" class="btn btn-primary hs-tb-new" aria-haspopup="true" aria-expanded="false">${hs_icon("add")}<span>${hs_esc(__("New"))}</span></button>
				<div class="hs-tb-panel hs-tb-create" hidden></div>
			</div>
			<button type="button" class="hs-tb-icon hs-tb-lang" title="${hs_esc(ar ? "English" : "العربية")}">${ar ? "EN" : "ع"}</button>
			<div class="hs-tb-bellwrap">
				<button type="button" class="hs-tb-icon hs-tb-bell" title="${hs_esc(__("Notifications"))}">${hs_icon("notification")}<span class="hs-tb-dot" hidden></span></button>
				<div class="hs-tb-panel hs-tb-notif" hidden></div>
			</div>
			<div class="dropdown hs-tb-user">
				<button type="button" class="hs-tb-userbtn" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
					${frappe.avatar(frappe.session.user, "avatar-medium")}
					<span class="hs-tb-ut"><b>${hs_esc(name)}</b><span>${hs_esc(hipersign.topbar.role())}</span></span>${hs_icon("chevron-down")}
				</button>
				<div class="dropdown-menu dropdown-menu-right hs-tb-usermenu"></div>
			</div>
		</div>`);
	hipersign.topbar.user_menu(null);
	hipersign.topbar.banners();
	hipersign.topbar.sync();
	hipersign.topbar.refresh(true);
};

hipersign.topbar.period_label = (p) => ({ month: __("This month"), last_month: __("Last month"), ytd: __("Year to date") })[p] || __("This month");

hipersign.topbar.refresh = function (force) {
	const now = Date.now();
	if (!force && hipersign.topbar._at && now - hipersign.topbar._at < 60000) return;
	hipersign.topbar._at = now;
	return frappe.xcall("hipersign_trading.api.ui.topbar").then((r) => {
		if (!r) return;
		const st = hipersign.topbar.state;
		Object.assign(st, { data: r, scope: r.scope, period: r.period, company: r.company });
		$(".hs-topbar .hs-tb-dot").text(r.unread > 99 ? "99+" : r.unread).prop("hidden", !r.unread);
		$(".hs-topbar .hs-tb-period-l").text(hipersign.topbar.period_label(r.period));
		hipersign.topbar.scope_menu(r);
		hipersign.topbar.user_menu(r.switch);
		if (r.company) frappe.defaults.set_user_default_local("Company", r.company);
	});
};

// ---------------------------------------------------------------- scope (group / country / company)
hipersign.topbar.scope_label = function (r) {
	const s = r.scope || "";
	if (s === "group") return __("Whole group · {0} companies", [r.company_rows.length]);
	if (s.startsWith("country:")) {
		const c = s.slice(8);
		return __("{0} · {1} companies", [__(c), r.company_rows.filter((x) => x.country === c).length]);
	}
	return r.company || "";
};

hipersign.topbar.scope_menu = function (r) {
	const rows = r.company_rows || [];
	const $dd = $(".hs-topbar .hs-tb-scope"), $fixed = $(".hs-topbar .hs-tb-scope-fixed");
	if (rows.length < 2) {
		$dd.prop("hidden", true);
		$fixed.prop("hidden", !r.company).text(r.company || "");
		return;
	}
	$fixed.prop("hidden", true);
	$dd.prop("hidden", false).find(".hs-tb-scope-l").text(hipersign.topbar.scope_label(r));
	const multi_country = (r.countries || []).length > 1;
	let html = `<a class="dropdown-item ${r.scope === "group" ? "active" : ""}" data-scope="group"><b>${hs_esc(__("Whole group"))}</b> <span class="text-muted">· ${rows.length} ${hs_esc(__("companies"))}</span></a>`;
	(r.countries || [null]).forEach((country) => {
		const cos = rows.filter((x) => !country || x.country === country);
		if (multi_country && country) {
			html += `<div class="dropdown-divider"></div><a class="dropdown-item hs-tb-country ${r.scope === "country:" + country ? "active" : ""}" data-scope="country:${hs_esc(country)}">${hs_esc(__(country))} <span class="text-muted">· ${cos.length}</span></a>`;
		}
		html += cos.map((c) => `<a class="dropdown-item hs-tb-co ${r.scope === "company:" + c.name ? "active" : ""}" data-scope="company:${hs_esc(c.name)}">${hs_esc(c.name)} <span class="text-muted">${hs_esc(c.currency || "")}</span></a>`).join("");
	});
	$dd.find(".hs-tb-scope-menu").html(html);
};

hipersign.topbar.set_scope = function (scope) {
	return frappe.xcall("hipersign_trading.api.ui.set_scope", { scope }).then((r) => {
		frappe.defaults.set_user_default_local("Company", r.company);
		const st = hipersign.topbar.state;
		st.scope = r.scope;
		st.company = r.company;
		if (st.data) {
			st.data.scope = r.scope;
			st.data.company = r.company;
			hipersign.topbar.scope_menu(st.data);
		}
		frappe.show_alert({ message: r.scope.startsWith("company:") ? __("Working in {0}", [r.company]) : __("Showing {0} · new documents use {1}", [hipersign.topbar.scope_label(st.data || r), r.company]), indicator: "green" });
		$(document).trigger("hs-scope-change", [st]);
	});
};

hipersign.topbar.set_period = function (period) {
	return frappe.xcall("hipersign_trading.api.ui.set_period", { period }).then(() => {
		hipersign.topbar.state.period = period;
		$(".hs-topbar .hs-tb-period-l").text(hipersign.topbar.period_label(period));
		$(document).trigger("hs-scope-change", [hipersign.topbar.state]);
	});
};

// what a Hipersign page should show: {company, country, period}
hipersign.topbar.filters = function () {
	const st = hipersign.topbar.state;
	const s = st.scope || "";
	return {
		period: st.period || "month",
		company: s.startsWith("company:") ? s.slice(8) : null,
		country: s.startsWith("country:") ? s.slice(8) : null,
		group: s === "group",
	};
};

// ---------------------------------------------------------------- search
hipersign.topbar.search = frappe.utils.debounce(function () {
	const $box = $(".hs-topbar .hs-tb-search"), $res = $box.find(".hs-tb-results");
	const q = $box.find("input").val().trim();
	if (q.length < 2) return $res.prop("hidden", true).empty();
	const token = (hipersign.topbar._q = q);
	frappe.xcall("hipersign_trading.api.ui.search", { q }).then((rows) => {
		if (token !== hipersign.topbar._q) return;
		const items = (rows || []).map((r, i) => `<a class="hs-tb-res" data-i="${i}" data-dt="${hs_esc(r.doctype)}" data-name="${hs_esc(r.name)}">
			<span class="hs-tb-type">${hs_esc(r.type)}</span><span class="hs-tb-rt"><b>${hs_esc(r.name)}</b>${r.title ? " — " + hs_esc(r.title) : ""}${r.extra ? `<span class="text-muted"> · ${hs_esc(__(r.extra))}</span>` : ""}</span></a>`).join("");
		$res.html((items || `<div class="hs-tb-none">${hs_esc(__("No records match {0}", [q]))}</div>`) +
			`<a class="hs-tb-res hs-tb-all" data-all="1">${hs_icon("search")}<span>${hs_esc(__("Search everywhere for “{0}”", [q]))}</span></a>`).prop("hidden", false);
		$res.find(".hs-tb-res").first().addClass("on");
	});
}, 220);

hipersign.topbar.open_result = function ($a) {
	const q = $(".hs-topbar .hs-tb-search input").val().trim();
	$(".hs-topbar .hs-tb-results").prop("hidden", true);
	if ($a.data("all")) {
		if (frappe.searchdialog && frappe.searchdialog.search) frappe.searchdialog.search.init_search(q, "global_search");
		return;
	}
	const dt = $a.attr("data-dt"), name = $a.attr("data-name");
	$(".hs-topbar .hs-tb-search input").val("").blur();
	if (hipersign.panel && hipersign.panel.open && hipersign.panel.has(dt)) return hipersign.panel.open(dt, name);
	frappe.set_route("Form", dt, name);
};

// ---------------------------------------------------------------- + New panel
hipersign.topbar.create_panel = function () {
	const groups = hipersign.create.visible();
	const chip = (dt) => (hipersign.create.has_modes(dt) ? `<span class="hs-chip" data-chip="${hs_esc(dt)}" title="${hs_esc(__("Form mode — click to change"))}">${hs_esc(__(hipersign.fm.mode(dt)).toUpperCase())} ▾</span>` : "");
	let k = 0;
	hipersign.topbar._entries = [];
	const html = groups.map(([g, items]) => `<div class="hs-tb-sec">${hs_esc(g)}</div><div class="hs-tb-grid">${items.map(([l, icon, a]) => {
		hipersign.topbar._entries[k] = a;
		return `<button type="button" class="hs-tb-item" data-k="${k++}">${hs_icon(icon)}<span>${hs_esc(l)}</span>${a.full ? "" : chip(a.dt)}</button>`;
	}).join("")}</div>`).join("");
	return `<div class="hs-tb-ph"><b>${hs_esc(__("Create new"))}</b><a class="hs-tb-allnew">${hs_esc(__("All"))} ${hs_icon("right", "xs")}</a></div><div class="hs-tb-pb">${html}</div>`;
};

hipersign.topbar.toggle_panel = function (cls, html) {
	const $p = $(`.hs-topbar .${cls}`);
	const open = $p.prop("hidden");
	$(".hs-topbar .hs-tb-panel").prop("hidden", true);
	if (!open) return false;
	if (html !== undefined) $p.html(html);
	$p.prop("hidden", false);
	return true;
};

hipersign.topbar.mode_menu = function (dt, $anchor) {
	$(".hs-tb-modes").remove();
	const cur = hipersign.fm.mode(dt);
	const $m = $(`<div class="hs-tb-modes">${hipersign.fm.MODES.map((m) => `<a data-mode="${m}" class="${m === cur ? "on" : ""}">${hs_esc(__(m))}${m === cur ? " ✓" : ""}</a>`).join("")}</div>`);
	$m.appendTo("body");
	const r = $anchor[0].getBoundingClientRect();
	$m.css({ top: r.bottom + 4, left: Math.min(r.left, window.innerWidth - 180) });
	$m.on("click", "a", function (e) {
		e.stopPropagation();
		const m = $(this).attr("data-mode");
		$m.remove();
		hipersign.fm.remember(dt, m).then(() => {
			$(`.hs-topbar [data-chip="${dt}"]`).text(__(m).toUpperCase() + " ▾");
			frappe.show_alert({ message: __("{0} now opens in {1}", [__(dt), __(m)]), indicator: "green" });
		});
	});
};

// ---------------------------------------------------------------- bell
hipersign.topbar.bell = function () {
	const $p = $(".hs-topbar .hs-tb-notif");
	if (!hipersign.topbar.toggle_panel("hs-tb-notif", `<div class="hs-tb-ph"><b>${hs_esc(__("Notifications"))}</b></div><div class="hs-tb-pb"><div class="hs-tb-none">${hs_esc(__("Loading…"))}</div></div>`)) return;
	frappe.xcall("hipersign_trading.api.ui.bell").then((r) => {
		const groups = (r && r.groups) || [];
		const body = groups.length
			? groups.map((g) => `<div class="hs-tb-sec">${hs_esc(g.label)} · ${g.unread && g.unread === g.count ? `<span class="hs-tb-new-n">${hs_esc(__("{0} new", [g.unread]))}</span>`
				: g.count + (g.unread ? ` <span class="hs-tb-new-n">${hs_esc(__("{0} new", [g.unread]))}</span>` : "")}</div>` +
				g.items.map((i) => `<a class="hs-tb-note ${i.unread ? "unread" : ""}" data-dt="${hs_esc(i.doctype || "")}" data-name="${hs_esc(i.name || "")}" data-log="${hs_esc(i.log || "")}">
					<span class="hs-tb-fdot hs-${hs_esc(g.key)}"></span><div><b>${hs_esc(i.title)}</b>${i.text ? `<p>${hs_esc(i.text)}</p>` : ""}</div></a>`).join("") +
				(g.count > g.items.length ? `<a class="hs-tb-note more" data-route='${hs_esc(JSON.stringify(g.route))}'><span></span><div><b>${hs_esc(__("{0} more", [g.count - g.items.length]))}</b><p>${hs_esc(__("Open the full list"))}</p></div></a>` : "")).join("")
			: `<div class="hs-tb-none">${hs_esc(__("You're all caught up."))}</div>`;
		$p.html(`<div class="hs-tb-ph"><b>${hs_esc(__("Notifications"))}</b>${r && r.unread ? `<a class="hs-tb-readall">${hs_esc(__("Mark all read"))}</a>` : ""}</div>
			<div class="hs-tb-pb">${body}</div><div class="hs-tb-pf"><a class="hs-tb-alln">${hs_esc(__("Open the full list"))}</a></div>`);
	});
};

// ---------------------------------------------------------------- user menu and Switch user
hipersign.topbar.user_menu = function (sw) {
	const items = [];
	if (sw && sw.switched) items.push(`<a class="dropdown-item hs-tb-back" data-user="${hs_esc(sw.original)}"><b>${hs_esc(__("Back to {0}", [sw.original === "Administrator" ? __("Administrator") : sw.original]))}</b></a><div class="dropdown-divider"></div>`);
	if (sw && sw.users && sw.users.length) {
		items.push(`<div class="hs-tb-sec">${hs_esc(__("Switch user"))}</div>`);
		items.push(sw.users.filter((u) => u.user !== frappe.session.user).map((u) =>
			`<a class="dropdown-item hs-tb-switch" data-user="${hs_esc(u.user)}">${frappe.avatar(u.user, "avatar-xs")}<span><b>${hs_esc(u.full_name || u.user)}</b><span class="text-muted"> · ${hs_esc(u.role || "")}</span></span></a>`).join(""));
		items.push(`<div class="dropdown-divider"></div>`);
	}
	if (frappe.user.has_role("System Manager") && !(frappe.boot.hipersign || {}).view_only) {
		items.push(`<a class="dropdown-item" data-act="add_user">${hs_esc(__("Add user"))}</a><a class="dropdown-item" data-act="users">${hs_esc(__("Manage users"))}</a>`);
	}
	if (hipersign.tour) items.push(`<a class="dropdown-item" data-act="tour">${hs_esc(__("Take the guided tour"))}</a>`);
	if ((frappe.boot.hipersign || {}).demo_site) items.push(`<a class="dropdown-item" data-act="present">${hs_esc(hipersign.topbar.presenting() ? __("Leave presentation mode") : __("Presentation mode"))}</a>`);
	items.push(`<a class="dropdown-item" data-act="settings">${hs_esc(__("My settings"))}</a>`);
	items.push(`<a class="dropdown-item" data-act="theme">${hs_esc(__("Toggle theme"))}</a><div class="dropdown-divider"></div>`);
	items.push(`<a class="dropdown-item" data-act="logout">${hs_esc(__("Log out"))}</a>`);
	$(".hs-topbar .hs-tb-usermenu").html(items.join(""));
};

hipersign.topbar.switch_to = function (user) {
	frappe.xcall("hipersign_trading.api.ui.switch_user", { user }).then((r) => {
		window.location.href = (r && r.home) || "/app";
	});
};

// ---------------------------------------------------------------- demo, view-only and presentation banners
hipersign.topbar.presenting = () => {
	try { return localStorage.getItem("hs_present") === "1"; } catch (e) { return false; }
};

hipersign.topbar.banners = function () {
	const info = frappe.boot.hipersign || {};
	$(".hs-banners").remove();
	document.documentElement.classList.toggle("hs-presenting", hipersign.topbar.presenting());
	const parts = [];
	if (info.view_only) {
		parts.push(`<div class="hs-banner hs-banner-view">${hs_icon("lock")}<span>${hs_esc(__("View-only demo — look around freely; nothing you do here is saved."))}</span>
			<button type="button" class="btn btn-xs btn-primary hs-book">${hs_esc(__("Book a demo"))}</button></div>`);
	} else if (info.demo_site && !hipersign.topbar.presenting()) {
		const pack = info.pack || "";
		parts.push(`<div class="hs-banner hs-banner-demo"><b>${hs_esc(__("DEMO"))}</b><span>${hs_esc(__("Demonstration environment"))}</span>
			${pack ? `<span class="hs-chip">${hs_esc(__("Pack"))}: ${hs_esc(__(pack))}</span>` : ""}
			${frappe.user.has_role("System Manager") ? `<a class="hs-banner-a" data-route='["Form","Hipersign Settings"]'>${hs_esc(__("Change pack"))}</a>` : ""}
			<a class="hs-banner-a" data-route='["hipersign-tests"]'>${hs_esc(__("Test Centre"))}</a>
			<a class="hs-banner-a hs-present">${hs_esc(__("Presentation mode"))}</a></div>`);
	}
	if (!parts.length) return;
	$(`<div class="hs-banners">${parts.join("")}</div>`).insertAfter($(".main-section > header.hs-topbar-host").first());
};

hipersign.topbar.book_demo = function () {
	const d = new frappe.ui.Dialog({
		title: __("Book a free demo"),
		fields: [
			{ fieldtype: "HTML", options: `<p>${hs_esc(__("See Hipersign ERP running your trading business — purchasing, imports, stock, sales, exports, finance, HR and assets — with your own data in a free, personalised demo."))}</p>` },
			{ fieldtype: "Data", fieldname: "name", label: __("Your name"), reqd: 1 },
			{ fieldtype: "Data", fieldname: "company", label: __("Company"), reqd: 1 },
			{ fieldtype: "Data", fieldname: "mobile", label: __("Mobile / WhatsApp"), options: "Phone" },
			{ fieldtype: "Select", fieldname: "interest", label: __("Interested in"), options: ["Complete ERP", "Trading & inventory", "Import / export", "Finance, VAT & Corporate Tax", "HR & payroll", "Migration from another system"].join("\n"), default: "Complete ERP" },
			{ fieldtype: "Select", fieldname: "time", label: __("Preferred time"), options: ["This week", "Next week", "Morning", "Afternoon"].join("\n"), default: "This week" },
			{ fieldtype: "HTML", options: `<div class="hs-book-contacts small">+971 54 427 6655 · +971 50 976 2927 · India +91 94957 71084 · <a href="mailto:sales@hipersignerp.com">sales@hipersignerp.com</a> · <a href="https://www.hipersignerp.com" target="_blank" rel="noopener">www.hipersignerp.com</a></div>` },
		],
		primary_action_label: __("Send on WhatsApp"),
		primary_action(v) { hipersign.topbar.book_send(v, "wa"); d.hide(); },
		secondary_action_label: __("Send by email"),
		secondary_action() { const v = d.get_values(); if (v) { hipersign.topbar.book_send(v, "email"); d.hide(); } },
	});
	d.show();
};

hipersign.topbar.book_send = function (v, ch) {
	const msg = `Hello Hipersign, I would like a demo of Hipersign ERP.\nName: ${v.name}\nCompany: ${v.company}${v.mobile ? "\nMobile: " + v.mobile : ""}\nInterested in: ${v.interest}\nPreferred time: ${v.time}`;
	const url = ch === "wa" ? "https://wa.me/971544276655?text=" + encodeURIComponent(msg)
		: "mailto:sales@hipersignerp.com?subject=" + encodeURIComponent("Demo request — " + v.company) + "&body=" + encodeURIComponent(msg);
	window.open(url, "_blank", "noopener");
	frappe.show_alert({ message: ch === "wa" ? __("WhatsApp opened with your request — press send there") : __("Email opened with your request — press send there"), indicator: "green" });
};

// ---------------------------------------------------------------- menu toggle (icon rail on desktop, slide-in on a phone)
hipersign.topbar.narrow = () => window.matchMedia("(max-width: 900px)").matches;
hipersign.topbar.rail = function (on) {
	document.documentElement.classList.toggle("hs-rail", !!on);
	try { localStorage.setItem("hs_rail", on ? "1" : "0"); } catch (e) { /* private window */ }
};
hipersign.topbar.toggle_menu = function () {
	if (hipersign.topbar.narrow()) {
		const open = !document.documentElement.classList.contains("hs-menu-open");
		document.documentElement.classList.toggle("hs-menu-open", open);
		if (open && !$(".hs-menu-backdrop").length) $(`<div class="hs-menu-backdrop"></div>`).appendTo("body");
		if (!open) $(".hs-menu-backdrop").remove();
		return;
	}
	hipersign.topbar.rail(!document.documentElement.classList.contains("hs-rail"));
};
(function () {
	try { if (localStorage.getItem("hs_rail") === "1") document.documentElement.classList.add("hs-rail"); } catch (e) { /* ignore */ }
})();

// ---------------------------------------------------------------- events
$(document).on("click", ".hs-topbar .hs-tb-menu", () => hipersign.topbar.toggle_menu());
$(document).on("click", ".hs-menu-backdrop", () => hipersign.topbar.toggle_menu());
$(document).on("click", ".body-sidebar a", () => {
	if (document.documentElement.classList.contains("hs-menu-open")) hipersign.topbar.toggle_menu();
});

$(document).on("input", ".hs-topbar .hs-tb-search input", () => hipersign.topbar.search());
$(document).on("focus", ".hs-topbar .hs-tb-search input", function () { if ($(this).val().trim().length >= 2) hipersign.topbar.search(); });
$(document).on("keydown", ".hs-topbar .hs-tb-search input", function (e) {
	const $res = $(".hs-topbar .hs-tb-results"), $items = $res.find(".hs-tb-res");
	let i = $items.index($items.filter(".on"));
	if (e.key === "ArrowDown" || e.key === "ArrowUp") {
		e.preventDefault();
		i = Math.max(0, Math.min($items.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)));
		$items.removeClass("on").eq(i).addClass("on");
	} else if (e.key === "Enter") {
		e.preventDefault();
		const $on = $items.filter(".on");
		if ($on.length) hipersign.topbar.open_result($on.first());
	} else if (e.key === "Escape") {
		$res.prop("hidden", true);
		$(this).blur();
	}
});
$(document).on("mousedown", ".hs-topbar .hs-tb-res", function (e) {
	e.preventDefault();
	hipersign.topbar.open_result($(this));
});
$(document).on("blur", ".hs-topbar .hs-tb-search input", () => setTimeout(() => $(".hs-topbar .hs-tb-results").prop("hidden", true), 150));
// "/" focuses the search field, as in the prototype (not while typing somewhere else); Ctrl+K stays Frappe's palette
$(document).on("keydown", (e) => {
	if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
	const t = e.target;
	if (t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName))) return;
	const $in = $(".hs-topbar .hs-tb-search input");
	if (!$in.is(":visible")) return;
	e.preventDefault();
	$in.focus();
});

$(document).on("click", ".hs-topbar [data-scope]", function (e) {
	e.preventDefault();
	hipersign.topbar.set_scope($(this).attr("data-scope"));
});
$(document).on("click", ".hs-topbar [data-period]", function (e) {
	e.preventDefault();
	hipersign.topbar.set_period($(this).attr("data-period"));
});

$(document).on("click", ".hs-topbar .hs-tb-new", (e) => {
	e.stopPropagation();
	const open = hipersign.topbar.toggle_panel("hs-tb-create", hipersign.topbar.create_panel());
	$(e.currentTarget).attr("aria-expanded", open ? "true" : "false");
});
$(document).on("click", ".hs-topbar .hs-tb-create .hs-tb-item", function (e) {
	if ($(e.target).closest("[data-chip]").length) return;
	const a = hipersign.topbar._entries[+$(this).attr("data-k")];
	$(".hs-topbar .hs-tb-panel").prop("hidden", true);
	if (a) hipersign.create.open(a);
});
$(document).on("click", ".hs-topbar .hs-tb-create [data-chip]", function (e) {
	e.stopPropagation();
	hipersign.topbar.mode_menu($(this).attr("data-chip"), $(this));
});
$(document).on("click", ".hs-topbar .hs-tb-allnew", () => {
	$(".hs-topbar .hs-tb-panel").prop("hidden", true);
	frappe.set_route("hipersign-create");
});

$(document).on("click", ".hs-topbar .hs-tb-bell", (e) => {
	e.stopPropagation();
	hipersign.topbar.bell();
});
$(document).on("click", ".hs-topbar .hs-tb-note", function () {
	const route = $(this).attr("data-route");
	const dt = $(this).attr("data-dt"), name = $(this).attr("data-name"), log = $(this).attr("data-log");
	$(".hs-topbar .hs-tb-panel").prop("hidden", true);
	if (log) frappe.xcall("frappe.desk.doctype.notification_log.notification_log.mark_as_read", { docname: log }).then(() => hipersign.topbar.refresh(true));
	if (route) return frappe.set_route(...JSON.parse(route));
	if (dt && name) frappe.set_route("Form", dt, name);
});
$(document).on("click", ".hs-topbar .hs-tb-readall", (e) => {
	e.stopPropagation();
	frappe.xcall("hipersign_trading.api.ui.mark_all_read").then(() => {
		$(".hs-topbar .hs-tb-dot").prop("hidden", true);
		$(".hs-topbar .hs-tb-note").removeClass("unread");
		$(e.currentTarget).remove();
	});
});
$(document).on("click", ".hs-topbar .hs-tb-alln", () => {
	$(".hs-topbar .hs-tb-panel").prop("hidden", true);
	frappe.set_route("List", "Notification Log");
});
$(document).on("click", (e) => {
	if (!$(e.target).closest(".hs-tb-newwrap, .hs-tb-bellwrap, .hs-tb-modes").length) {
		$(".hs-topbar .hs-tb-panel").prop("hidden", true);
		$(".hs-tb-modes").remove();
	}
});

$(document).on("click", ".hs-topbar .hs-tb-lang", () => {
	const to = (frappe.boot.lang || "en").startsWith("ar") ? "en" : "ar";
	frappe.xcall("hipersign_trading.api.ui.set_language", { language: to }).then(() => window.location.reload());
});
$(document).on("click", ".hs-topbar .hs-tb-switch, .hs-topbar .hs-tb-back", function (e) {
	e.preventDefault();
	hipersign.topbar.switch_to($(this).attr("data-user"));
});
$(document).on("click", ".hs-topbar .hs-tb-user [data-act]", function (e) {
	e.preventDefault();
	const act = $(this).attr("data-act");
	if (act === "settings") frappe.set_route("Form", "User", frappe.session.user);
	else if (act === "theme") new frappe.ui.ThemeSwitcher().show();
	else if (act === "logout") frappe.app.logout();
	else if (act === "add_user") frappe.new_doc("User");
	else if (act === "users") frappe.set_route("List", "User");
	else if (act === "tour") hipersign.tour.start();
	else if (act === "present") {
		try { localStorage.setItem("hs_present", hipersign.topbar.presenting() ? "0" : "1"); } catch (err) { /* ignore */ }
		hipersign.topbar.banners();
		hipersign.topbar.user_menu((hipersign.topbar.state.data || {}).switch);
		$(document).trigger("hs-present-change");
	}
});
$(document).on("click", ".hs-banners [data-route]", function () { frappe.set_route(...JSON.parse($(this).attr("data-route"))); });
$(document).on("click", ".hs-banners .hs-present", () => {
	try { localStorage.setItem("hs_present", "1"); } catch (err) { /* ignore */ }
	hipersign.topbar.banners();
	$(document).trigger("hs-present-change");
});
$(document).on("click", ".hs-book", () => hipersign.topbar.book_demo());

$(document).on("app_ready", () => {
	setTimeout(hipersign.topbar.render, 0);
	if (frappe.realtime && frappe.realtime.on) frappe.realtime.on("notification", () => hipersign.topbar.refresh(true));
});
$(document).on("page-change", () => {
	setTimeout(() => {
		hipersign.topbar.render();
		hipersign.topbar.refresh();
	}, 0);
});
