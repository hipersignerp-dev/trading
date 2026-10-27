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

// every target the Hipersign sidebar links to, normalised, so a route can be matched against it
hipersign.nav.targets = function () {
	const sb = frappe.boot.workspace_sidebar_item && frappe.boot.workspace_sidebar_item[hipersign.nav.SIDEBAR.toLowerCase()];
	if (!sb) return null;
	if (!hipersign.nav._targets) {
		hipersign.nav._targets = new Set((sb.items || []).filter((i) => i.link_to).map((i) => hipersign.nav.key(i.link_to)));
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
