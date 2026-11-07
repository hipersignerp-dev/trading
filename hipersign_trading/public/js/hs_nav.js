// Hipersign ERP v1.4 — the prototype's look and menu on the ERPNext desk.
// 1. The Hipersign theme: a class on <html> switches the colours, fonts and cards (hipersign_theme.css).
// 2. The Hipersign ERP sidebar stays on screen for every page it lists, like the prototype's left menu.
// 3. After login the user lands on Hipersign Home instead of the desktop of tiles.
frappe.provide("hipersign.nav");

(function () {
	const info = (frappe.boot && frappe.boot.hipersign) || {};
	if ((info.theme || "Hipersign") === "Hipersign" && frappe.session && frappe.session.user !== "Guest") {
		document.documentElement.classList.add("hs-theme");
	}
	// v1.8.0: Simplified Chinese gets a CJK font stack (hipersign_theme.css); Arabic keeps Frappe's right-to-left layout
	if (((frappe.boot && frappe.boot.lang) || "").toLowerCase().startsWith("zh")) document.documentElement.classList.add("hs-lang-zh");
})();

// v1.8.0: the sidebar shows translated or renamed labels (menu builder); sub-items and badges are keyed by the NAV label
hipersign.nav.base = (name) => ((frappe.boot.hipersign || {}).nav_alias || {})[name] || name;

hipersign.nav.SIDEBAR = "Hipersign ERP";
// v1.8.1: Frappe 16.30+ sends the sidebars as module_sidebars (keyed by the Sidebar's name) and calls the one on screen
// current_module; up to 16.29 workspace_sidebar_item (keyed by the lowercased title) and sidebar_title
hipersign.nav.data = function () {
	const b = frappe.boot || {};
	if (b.module_sidebars) return b.module_sidebars[hipersign.nav.SIDEBAR] || null;
	return (b.workspace_sidebar_item && b.workspace_sidebar_item[hipersign.nav.SIDEBAR.toLowerCase()]) || null;
};
hipersign.nav.current = (sb) => (sb ? sb.current_module || sb.sidebar_title : null);
hipersign.nav.ours = () => hipersign.nav.current(frappe.app && frappe.app.sidebar) === hipersign.nav.SIDEBAR;
hipersign.nav.key = (s) => (s || "").toString().toLowerCase().replace(/[-_]/g, " ").trim();

// every target the Hipersign sidebar links to (v1.5.6: and every sub-item under its entries), normalised, so a route
// can be matched against it
hipersign.nav.targets = function () {
	const sb = hipersign.nav.data();
	if (!sb) return null;
	if (!hipersign.nav._targets) {
		hipersign.nav._targets = new Set((sb.items || []).filter((i) => i.link_to).map((i) => hipersign.nav.key(i.link_to)));
		Object.values((frappe.boot.hipersign || {}).nav_sub || {}).forEach((rows) => rows.forEach((r) => hipersign.nav._targets.add(hipersign.nav.key(r.target))));
		// v1.5.6: pages opened from the top bar (Create New, Test Centre…) and every document of the + New panel keep the
		// Hipersign menu instead of falling back to an older workspace sidebar
		["hipersign-create", "hipersign-tests", "hipersign-addons", "serial-lookup", "hipersign-landed", "hipersign-journey", "hipersign-messages",
			"hipersign-alerts", "hipersign-approvals", "sales-order-tracker", "Hipersign Settings", "Hipersign Lists",
			// v1.8.4 (#37): every report (opened from the Reports page) and what Workflows & Settings / Data Migration open
			"query-report", "Data Import", "Workflow", "User", "System Settings", "Hipersign List Value", "Hipersign Document Rule", "Document Waiver",
			"Opening Invoice Creation Tool"].forEach((t) => hipersign.nav._targets.add(hipersign.nav.key(t)));
		try {
			(hipersign.create && hipersign.create.GROUPS ? hipersign.create.GROUPS() : []).forEach(([, items]) => items.forEach(([, , a]) => {
				if (a.dt) hipersign.nav._targets.add(hipersign.nav.key(a.dt));
			}));
		} catch (e) { /* the top bar loads later on some pages */ }
	}
	return hipersign.nav._targets;
};

hipersign.nav.lists_route = function (route) {
	const targets = hipersign.nav.targets();
	if (!targets || !route || !route.length) return false;
	const k = hipersign.nav.key;
	// ["List", "Sales Order"], ["Form", "Sales Order", "SO-1"], ["query-report", "General Ledger"], ["Workspaces", "hipersign-trading"], ["sales-order-tracker"]
	const cands = route.length === 1 ? [route[0]] : [route[1], route[0]];
	return cands.some((c) => c && targets.has(k(c)));
};

hipersign.nav.hook = function () {
	const sb = frappe.app && frappe.app.sidebar;
	if (!sb || sb.__hs_nav || typeof sb.set_workspace_sidebar !== "function") return;
	const info = (frappe.boot && frappe.boot.hipersign) || {};
	if (info.keep_sidebar === false || !hipersign.nav.targets()) return;
	sb.__hs_nav = true;
	const original = sb.set_workspace_sidebar.bind(sb);
	sb.set_workspace_sidebar = function (router) {
		try {
			const route = frappe.get_route() || [];
			if (hipersign.nav.lists_route(route)) {
				if (hipersign.nav.current(this) !== hipersign.nav.SIDEBAR) frappe.app.sidebar.setup(hipersign.nav.SIDEBAR);
				if (typeof this.set_active_workspace_item === "function") this.set_active_workspace_item();
				else if (typeof this.highlight_active_item === "function") this.highlight_active_item(); // 16.30+
				return;
			}
		} catch (e) {
			console.error(e);
		}
		return original(router);
	};
	// the prototype's brand block at the top of the menu
	if (typeof sb.setup === "function") {
		const setup = sb.setup.bind(sb);
		sb.setup = function (...args) {
			const out = setup(...args);
			setTimeout(hipersign.nav.brand, 0);
			return out;
		};
	}
	// apply once for the page already on screen
	if ((frappe.get_route() || []).length) sb.set_workspace_sidebar();
	hipersign.nav.brand();
};

hipersign.nav.brand = function () {
	const sb = frappe.app && frappe.app.sidebar;
	const $h = $(".body-sidebar .sidebar-header");
	if (!sb || !$h.length) return;
	const ours = hipersign.nav.current(sb) === hipersign.nav.SIDEBAR;
	$h.toggleClass("hs-brand", ours);
	if (ours) {
		// a group with nothing this user may open (e.g. Admin for a sales user) is not shown
		$(".body-sidebar .section-item").each(function () {
			$(this).toggle($(this).find(".nested-container .sidebar-item-container").length > 0);
		});
	}
	if (ours) hipersign.nav.decorate();
	if (ours && !$h.find(".hs-brand-logo").length) {
		$h.find(".sidebar-item-icon, .header-logo").hide(); // .header-logo: Frappe 16.30+
		$h.find(".title-container").hide();
		// v1.7.3: the wordmark when the menu is open, the square mark when it is collapsed (no squeezed logo)
		$h.prepend(`<span class="hs-brand-logo"><img class="hs-logo-full" src="/assets/hipersign_trading/images/hipersign-logo.png" alt="Hipersign ERP"><img class="hs-logo-mark" src="/assets/hipersign_trading/images/hipersign-mark.png" alt="Hipersign ERP"></span>`);
	} else if (!ours) {
		$h.find(".hs-brand-logo").remove();
		$h.find(".sidebar-item-icon, .header-logo, .title-container").show();
	}
};

hipersign.nav.at_desk_root = function () {
	const parts = (window.location.pathname || "").split("/").filter(Boolean).map((p) => decodeURIComponent(p).toLowerCase());
	if (!parts.length || !["app", "desk"].includes(parts[0])) return false;
	if (parts.length === 1) return true;
	if (parts.length > 2) return false;
	const x = parts[1];
	if (["home", "desktop", "apps"].includes(x)) return true;
	const slug = (t) => (frappe.router && frappe.router.slug ? frappe.router.slug(t) : String(t).toLowerCase().replace(/[ _]/g, "-"));
	const dts = [].concat((frappe.boot.user && frappe.boot.user.can_read) || []);
	if (dts.some((d) => slug(d) === x)) return false; // /desk/sales-order is the Sales Order list
	if ((frappe.boot.page_info || {})[x]) return false; // /desk/hipersign-crm is a page
	const modules = Object.keys(frappe.boot.module_sidebars || {}).concat(Object.keys(frappe.workspaces || {}), frappe.boot.allowed_modules || []);
	return modules.some((m) => slug(typeof m === "string" ? m : m.module_name || "") === x);
};

hipersign.nav.go_home = function () {
	const info = (frappe.boot && frappe.boot.hipersign) || {};
	if (!info.open_home || sessionStorage.getItem("hs_home_opened")) return;
	sessionStorage.setItem("hs_home_opened", "1");
	// v1.8.2: decided from the address the browser asked for, not frappe.get_route(): on app_ready Frappe 16.54 has not routed
	// yet (the route is still empty), so a deep link (/app/sales-order, /desk/customer) was sent to Home. Only the bare desk
	// root goes home: /app, /desk, /app|desk/home|apps|desktop, or /desk/<module> when <module> is a workspace, not a DocType.
	if (!hipersign.nav.at_desk_root()) return;
	// v1.5: the prototype's Home page; the workspace when the page is not there (or not allowed for the user)
	if (info.home_page) frappe.set_route(info.home_page);
	else if (frappe.workspaces && frappe.workspaces[frappe.router.slug(info.home_workspace || "Hipersign Trading")]) {
		frappe.set_route(frappe.router.slug(info.home_workspace || "Hipersign Trading"));
	}
};

$(document).on("app_ready", () => {
	setTimeout(() => {
		hipersign.nav.hook();
		hipersign.nav.go_home();
	}, 0);
});
$(document).on("page-change", () => setTimeout(hipersign.nav.hook, 0));

// v1.8.4 (#30): the six old Frappe workspaces (Hipersign Trading, Sales, Warehouse, Finance, HR, Documents) are retired
// (hidden); any link, bookmark or tile that still opens one lands on Hipersign Home instead.
hipersign.nav.OLD_WORKSPACES = ["hipersign-trading", "hipersign-sales", "hipersign-warehouse", "hipersign-finance", "hipersign-hr", "hipersign-documents"];
hipersign.nav.leave_old_workspace = function () {
	const r = frappe.get_route() || [], slug = (t) => String(t || "").toLowerCase().replace(/[ _]/g, "-");
	const ws = r[0] === "Workspaces" ? slug(r[1]) : r.length === 1 ? slug(r[0]) : "";
	if (!hipersign.nav.OLD_WORKSPACES.includes(ws)) return;
	const home = ((frappe.boot && frappe.boot.hipersign) || {}).home_page || "hipersign-home";
	frappe.set_route(home);
};
$(document).on("page-change", () => setTimeout(hipersign.nav.leave_old_workspace, 0));
if (frappe.router && frappe.router.on) frappe.router.on("change", () => setTimeout(hipersign.nav.leave_old_workspace, 0));

// ---------------------------------------------------------------- v1.5.6: sub-items, count badges, Book a demo
hipersign.nav.open_subs = function () {
	try { return JSON.parse(localStorage.getItem("hs_nav_open") || "[]"); } catch (e) { return []; }
};

hipersign.nav.decorate = function () {
	const info = frappe.boot.hipersign || {};
	const subs = info.nav_sub || {};
	const open = new Set(hipersign.nav.open_subs());
	const route = frappe.get_route() || [];
	const here = hipersign.nav.key(route.length > 1 ? route[1] : route[0]);
	// v1.8.2: Frappe 16.30+ draws no icon on the rows inside a group, so the collapsed rail was empty below Home. The row's own
	// icon (Sidebar Item) is added for the rail only (hs_shell.css shows it with html.hs-rail); 16.29 rows already have one.
	const icons = {};
	((hipersign.nav.data() || {}).items || []).forEach((i) => { if (i.icon && i.label) icons[i.label] = i.icon; });
	$(".body-sidebar .sidebar-item-container").each(function () {
		const $c = $(this), name = $c.attr("item-name");
		if (!name || $c.hasClass("section-item")) return;
		const $a = $c.children(".standard-sidebar-item").first().find(".item-anchor").first();
		if ($a.length && !$a.children(".sidebar-item-icon").length && icons[name]) {
			$a.prepend(`<span class="sidebar-item-icon hs-rail-icon" item-icon="${frappe.utils.escape_html(icons[name])}">${frappe.utils.icon(icons[name], "sm")}</span>`);
		}
	});
	$(".body-sidebar .sidebar-item-container").each(function () {
		const $c = $(this), name = $c.attr("item-name");
		if (!name || $c.hasClass("section-item") || $c.attr("data-hs-dec")) return;
		$c.attr("data-hs-dec", "1");
		const rows = subs[name] || subs[hipersign.nav.base(name)];
		if (!rows || !rows.length) return;
		const $row = $c.children(".standard-sidebar-item").first();
		$(`<span class="hs-sub-toggle" title="${frappe.utils.escape_html(__("Lists"))}">${frappe.utils.icon("right", "xs")}</span>`).appendTo($row);
		const active = rows.some((r) => hipersign.nav.key(r.target) === here);
		// v1.8.4 (#34/#37): a sub-item opens its Hipersign page on a tab (data-tab / data-chip) or the Reports page on a group
		const $sub = $(`<div class="hs-sub">${rows.map((r) => `<a data-route='${frappe.utils.escape_html(JSON.stringify(r.route))}'
			${r.tab ? `data-tab="${frappe.utils.escape_html(r.tab)}"` : ""} ${r.chip ? `data-chip="${frappe.utils.escape_html(r.chip)}"` : ""}
			${r.group ? `data-group="${frappe.utils.escape_html(r.group)}"` : ""}
			class="${hipersign.nav.sub_on(r.route, r.tab, r.group) ? "on" : ""}">${frappe.utils.escape_html(__(r.label))}</a>`).join("")}</div>`);
		$sub.insertAfter($c);
		$c.toggleClass("hs-sub-open", open.has(name) || active);
	});
	hipersign.nav.badges();
	hipersign.nav.book_box();
	// Frappe's "Add Sidebar Item" is for administrators only
	if (!frappe.user.has_role("System Manager")) $(".body-sidebar .add-sidebar-item, .body-sidebar [data-action='add-sidebar-item']").hide();
};

hipersign.nav.badges = function (force) {
	const now = Date.now();
	if (!force && hipersign.nav._b_at && now - hipersign.nav._b_at < 60000) return hipersign.nav.paint_badges();
	hipersign.nav._b_at = now;
	frappe.xcall("hipersign_trading.api.nav.counts").then((r) => {
		hipersign.nav._badges = r || {};
		hipersign.nav.paint_badges();
	});
};

hipersign.nav.paint_badges = function () {
	const b = hipersign.nav._badges || {};
	$(".body-sidebar .sidebar-item-container").each(function () {
		const $c = $(this), name = $c.attr("item-name");
		if (!name || $c.hasClass("section-item")) return;
		const n = b[name] || b[hipersign.nav.base(name)];
		const $row = $c.children(".standard-sidebar-item").first();
		$row.find(".hs-badge-n").remove();
		$c.toggleClass("hs-has-badge", !!n);
		if (n) {
			const $badge = $(`<span class="hs-badge-n">${n > 99 ? "99+" : n}</span>`);
			const $t = $row.find(".hs-sub-toggle");
			$t.length ? $badge.insertBefore($t) : $badge.appendTo($row);
		}
	});
};

hipersign.nav.book_box = function () {
	const info = frappe.boot.hipersign || {};
	const $sb = $(".body-sidebar");
	if (!info.demo_site || info.view_only || $sb.find(".hs-book-box").length) return;
	const $host = $sb.find(".sidebar-items, .body-sidebar-top").first();
	if (!$host.length) return;
	$(`<div class="hs-book-box"><b>${__("See it run your business")}</b>
		<button class="btn btn-sm btn-block hs-book">${__("Book a demo")}</button>
		<div class="hs-book-icons"><a href="https://wa.me/971544276655?text=${encodeURIComponent("Hello Hipersign, I would like a demo of Hipersign ERP.")}" target="_blank" rel="noopener" title="WhatsApp">${frappe.utils.icon("message-square", "sm")}</a>
		<a href="mailto:sales@hipersignerp.com?subject=${encodeURIComponent("Hipersign ERP demo")}" title="${__("Email")}">${frappe.utils.icon("mail", "sm")}</a></div></div>`).appendTo($host);
};

$(document).on("click", ".body-sidebar .hs-sub-toggle", function (e) {
	e.preventDefault();
	e.stopPropagation();
	const $c = $(this).closest(".sidebar-item-container");
	const name = $c.attr("item-name");
	$c.toggleClass("hs-sub-open");
	const open = new Set(hipersign.nav.open_subs());
	$c.hasClass("hs-sub-open") ? open.add(name) : open.delete(name);
	try { localStorage.setItem("hs_nav_open", JSON.stringify([...open])); } catch (err) { /* ignore */ }
});
// v1.8.4: the page and tab on screen now (module pages keep their tab in wrapper.hs_module; the Reports page its group)
hipersign.nav.here_tab = function () {
	const w = (window.cur_page && cur_page.page) || null;
	return (w && w.hs_module && w.hs_module.tab) || (w && w.hs_reports_group) || null;
};
hipersign.nav.sub_on = function (route, tab, group) {
	const now = frappe.get_route() || [];
	const r = route || [];
	if (hipersign.nav.key(r.length > 1 ? r[1] : r[0]) !== hipersign.nav.key(now.length > 1 ? now[1] : now[0])) return false;
	if (!tab && !group) return true;
	return hipersign.nav.here_tab() === (tab || group);
};
$(document).on("click", ".body-sidebar .hs-sub a", function (e) {
	e.preventDefault();
	const route = JSON.parse($(this).attr("data-route"));
	const tab = $(this).attr("data-tab"), chip = $(this).attr("data-chip"), group = $(this).attr("data-group");
	const now = frappe.get_route() || [];
	// already on that page: switch the tab in place (set_route to the same page would not reload it)
	if (route.length === 1 && now[0] === route[0] && window.cur_page && cur_page.page) {
		const w = cur_page.page;
		if (tab && w.hs_module && w.hs_module.goto) { w.hs_module.goto(tab, chip); return hipersign.nav.mark_sub(); }
		if (group && w.hs_reports_goto) { w.hs_reports_goto(group); return hipersign.nav.mark_sub(); }
		if (!tab && !group) return;
	}
	frappe.route_options = tab ? Object.assign({ hs_tab: tab }, chip ? { hs_chip: chip } : {}) : group ? { hs_group: group } : null;
	frappe.set_route(...route);
});
hipersign.nav.mark_sub = function () {
	$(".body-sidebar .hs-sub a").each(function () {
		$(this).toggleClass("on", hipersign.nav.sub_on(JSON.parse($(this).attr("data-route")), $(this).attr("data-tab"), $(this).attr("data-group")));
	});
};
$(document).on("hs-module-tab", () => hipersign.nav.mark_sub());
$(document).on("page-change", () => setTimeout(() => {
	if (hipersign.nav.ours()) {
		const route = frappe.get_route() || [];
		const here = hipersign.nav.key(route.length > 1 ? route[1] : route[0]);
		hipersign.nav.mark_sub();
		hipersign.nav.decorate();
	}
}, 50));

// ---------------------------------------------------------------- v1.7.2: lists that have a prototype page open the page
// (search, links and the awesome bar). The page's ⋯ menu keeps "Classic list" for the ERPNext list with filters and bulk edit.
hipersign.nav.LIST_PAGE = {
	"Export Shipment": ["hipersign-exports", "board"], "Journal Entry": ["hipersign-accounts", "je"], "Period Closing Voucher": ["hipersign-accounts", "closing"],
	"Company Document": ["hipersign-codocs", "register"], "Company Deadline": ["hipersign-codocs", "deadlines"], Asset: ["hipersign-assets", "register"],
	"Asset Maintenance Log": ["hipersign-assets", "maintenance"], Employee: ["hipersign-people", "employees"], "Leave Application": ["hipersign-people", "leave"],
	"Expense Claim": ["hipersign-people", "expenses"], "Payroll Entry": ["hipersign-people", "payroll"], Attendance: ["hipersign-people", "attendance"],
	"Tax Return": ["hipersign-tax", null],
	// v1.8.4 (#34/#37): every list the sidebar used to open in the old theme now opens its Hipersign page and tab
	Lead: ["hipersign-crm", "leads"], Opportunity: ["hipersign-crm", "opps"], Quotation: ["hipersign-orders", "quotes"], "Sales Order": ["hipersign-orders", "orders"],
	Customer: ["hipersign-orders", "credit"], "Supplier Quotation": ["hipersign-purchasing", "quotes"], "Purchase Order": ["hipersign-purchasing", "orders"],
	Supplier: ["hipersign-purchasing", "suppliers"], "Import Shipment": ["hipersign-imports", "all"], "Landed Cost Voucher": ["hipersign-landed", null],
	"Purchase Receipt": ["hipersign-receiving", "receipts"], Item: ["hipersign-stock", "items"], "Stock Reconciliation": ["hipersign-stock", "counts"],
	"Pick List": ["hipersign-stock", "picks"], "Warranty Claim": ["hipersign-stock", "claims"], "Delivery Note": ["hipersign-dispatch", "notes"],
	"Delivery Trip": ["hipersign-dispatch", "trips"], "Sales Invoice": ["hipersign-fin", "receivables"], "Payment Entry": ["hipersign-fin", "payments"],
	"Post Dated Cheque": ["hipersign-fin", "cheques"], "Purchase Invoice": ["hipersign-fin", "payables"], "Exchange Rate Revaluation": ["hipersign-accounts", "reval"],
	"Letter of Credit": ["hipersign-lc", "lcs"], "Bank Guarantee": ["hipersign-lc", "bgs"], "Hipersign Group Member": ["hipersign-group", "structure"],
	"Document Waiver": ["hipersign-doccentre", "waivers"], "Hipersign Document Rule": ["hipersign-doccentre", "rules"], Project: ["hipersign-projects", "port"],
	"Project Step Log": ["hipersign-projects", "log"], "Project BOQ": ["hipersign-boq", "boq"], "Progress Certificate": ["hipersign-billing", "ipc"],
	"Variation Order": ["hipersign-billing", "vo"], "Subcontract Order": ["hipersign-subcontract", "sco"], "Subcontract Claim": ["hipersign-subcontract", "claims"],
	"Back Charge": ["hipersign-subcontract", "bc"], Timesheet: ["hipersign-timesheets", "ts"], Task: ["hipersign-timesheets", "task"],
	"Daily Site Report": ["hipersign-timesheets", "dsr"], "Work Order": ["hipersign-production", "wo"], "Manufacturing Step Log": ["hipersign-production", "log"],
	"Production Plan": ["hipersign-planning", "pp"], BOM: ["hipersign-boms", "tree"], Routing: ["hipersign-boms", "routing"], Workstation: ["hipersign-boms", "ws"],
	"Job Card": ["hipersign-shopfloor", null], "Quality Inspection": ["hipersign-quality", "inc"], "Quality Inspection Template": ["hipersign-quality", "tpl"],
};
hipersign.nav.classic = {};
hipersign.nav.classic_menu = function (page, route) {
	if (!page || page.__hs_classic) return;
	page.__hs_classic = true;
	Object.entries(hipersign.nav.LIST_PAGE).filter(([dt, [pg]]) => pg === route && frappe.model.can_read(dt)).forEach(([dt]) =>
		page.add_menu_item(__("Classic list — {0}", [__(dt)]), () => { hipersign.nav.classic[dt] = 1; frappe.set_route("List", dt); }));
};
$(document).on("page-change", () => {
	const r = frappe.get_route() || [];
	if (r[0] !== "List" || !r[1] || (r[2] && r[2] !== "List")) return;
	const map = hipersign.nav.LIST_PAGE[r[1]];
	if (!map || hipersign.nav.classic[r[1]] || (frappe.boot.hipersign || {}).no_list_pages) return;
	// v1.8.1: only to a page this user may open (boot page_info) — otherwise the list stays a list
	if (frappe.boot.page_info && !frappe.boot.page_info[map[0]]) return;
	// a list opened with filters (from a link or a report) stays a list
	if (frappe.route_options && Object.keys(frappe.route_options).length) return;
	if (window.location.search && window.location.search.length > 1) return;
	frappe.route_options = map[1] ? { hs_tab: map[1] } : null;
	frappe.route_flags.replace_route = true; // Back does not bounce through the list again
	frappe.set_route(map[0]);
});

// ---------------------------------------------------------------- v1.8.2: Escape closes the top bar's open panel (+ New, the bell)
// and the phone menu. Frappe's own dialogs keep Escape when one is open.
$(document).on("keydown.hs_nav_esc", (e) => {
	if (e.key !== "Escape" || $(".modal.show").length) return;
	const $open = $(".hs-topbar .hs-tb-panel").filter(function () { return !this.hidden; });
	if ($open.length) {
		$open.prop("hidden", true);
		$(".hs-tb-modes").remove();
		return;
	}
	if (document.documentElement.classList.contains("hs-menu-open") && hipersign.topbar && hipersign.topbar.toggle_menu) hipersign.topbar.toggle_menu();
});
// v1.8.2: on a phone the page title's ☰ (Frappe's own sidebar toggle) opens the same Hipersign menu drawer as the top bar's ☰
document.addEventListener("click", (e) => {
	const t = e.target && e.target.closest && e.target.closest(".page-head .sidebar-toggle-btn");
	if (!t || !document.documentElement.classList.contains("hs-theme") || !hipersign.topbar || !hipersign.topbar.narrow || !hipersign.topbar.narrow()) return;
	e.preventDefault();
	e.stopImmediatePropagation();
	hipersign.topbar.toggle_menu();
}, true);
