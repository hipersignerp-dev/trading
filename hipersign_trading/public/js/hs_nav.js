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
})();

hipersign.nav.SIDEBAR = "Hipersign ERP";
hipersign.nav.key = (s) => (s || "").toString().toLowerCase().replace(/[-_]/g, " ").trim();

// every target the Hipersign sidebar links to (v1.5.6: and every sub-item under its entries), normalised, so a route
// can be matched against it
hipersign.nav.targets = function () {
	const sb = frappe.boot.workspace_sidebar_item && frappe.boot.workspace_sidebar_item[hipersign.nav.SIDEBAR.toLowerCase()];
	if (!sb) return null;
	if (!hipersign.nav._targets) {
		hipersign.nav._targets = new Set((sb.items || []).filter((i) => i.link_to).map((i) => hipersign.nav.key(i.link_to)));
		Object.values((frappe.boot.hipersign || {}).nav_sub || {}).forEach((rows) => rows.forEach((r) => hipersign.nav._targets.add(hipersign.nav.key(r.target))));
		// v1.5.6: pages opened from the top bar (Create New, Test Centre…) and every document of the + New panel keep the
		// Hipersign menu instead of falling back to an older workspace sidebar
		["hipersign-create", "hipersign-tests", "hipersign-addons", "serial-lookup", "hipersign-landed", "hipersign-journey", "hipersign-messages",
			"hipersign-alerts", "hipersign-approvals", "sales-order-tracker", "Hipersign Settings", "Hipersign Lists"].forEach((t) => hipersign.nav._targets.add(hipersign.nav.key(t)));
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
				if (this.sidebar_title !== hipersign.nav.SIDEBAR) frappe.app.sidebar.setup(hipersign.nav.SIDEBAR);
				if (typeof this.set_active_workspace_item === "function") this.set_active_workspace_item();
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
	const ours = sb.sidebar_title === hipersign.nav.SIDEBAR;
	$h.toggleClass("hs-brand", ours);
	if (ours) {
		// a group with nothing this user may open (e.g. Admin for a sales user) is not shown
		$(".body-sidebar .section-item").each(function () {
			$(this).toggle($(this).find(".nested-container .sidebar-item-container").length > 0);
		});
	}
	if (ours) hipersign.nav.decorate();
	if (ours && !$h.find(".hs-brand-logo").length) {
		$h.find(".sidebar-item-icon").hide();
		$h.find(".title-container").hide();
		$h.prepend(`<span class="hs-brand-logo"><img src="/assets/hipersign_trading/images/hipersign-logo.png" alt="Hipersign ERP"></span>`);
	} else if (!ours) {
		$h.find(".hs-brand-logo").remove();
		$h.find(".sidebar-item-icon, .title-container").show();
	}
};

hipersign.nav.go_home = function () {
	const info = (frappe.boot && frappe.boot.hipersign) || {};
	if (!info.open_home || sessionStorage.getItem("hs_home_opened")) return;
	sessionStorage.setItem("hs_home_opened", "1");
	const route = frappe.get_route() || [];
	const on_desktop = !route.length || !route[0] || ["desktop", "home", "apps"].includes((route[0] || "").toLowerCase());
	if (!on_desktop) return;
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
	$(".body-sidebar .sidebar-item-container").each(function () {
		const $c = $(this), name = $c.attr("item-name");
		if (!name || $c.hasClass("section-item") || $c.attr("data-hs-dec")) return;
		$c.attr("data-hs-dec", "1");
		const rows = subs[name];
		if (!rows || !rows.length) return;
		const $row = $c.children(".standard-sidebar-item").first();
		$(`<span class="hs-sub-toggle" title="${frappe.utils.escape_html(__("Lists"))}">${frappe.utils.icon("right", "xs")}</span>`).appendTo($row);
		const active = rows.some((r) => hipersign.nav.key(r.target) === here);
		const $sub = $(`<div class="hs-sub">${rows.map((r) => `<a data-route='${frappe.utils.escape_html(JSON.stringify(r.route))}' class="${hipersign.nav.key(r.target) === here ? "on" : ""}">${frappe.utils.escape_html(__(r.label))}</a>`).join("")}</div>`);
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
		const n = b[name];
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
$(document).on("click", ".body-sidebar .hs-sub a", function (e) {
	e.preventDefault();
	frappe.set_route(...JSON.parse($(this).attr("data-route")));
});
$(document).on("page-change", () => setTimeout(() => {
	const sb = frappe.app && frappe.app.sidebar;
	if (sb && sb.sidebar_title === hipersign.nav.SIDEBAR) {
		const route = frappe.get_route() || [];
		const here = hipersign.nav.key(route.length > 1 ? route[1] : route[0]);
		$(".body-sidebar .hs-sub a").each(function () {
			const r = JSON.parse($(this).attr("data-route"));
			$(this).toggleClass("on", hipersign.nav.key(r.length > 1 ? r[1] : r[0]) === here);
		});
		hipersign.nav.decorate();
	}
}, 50));
