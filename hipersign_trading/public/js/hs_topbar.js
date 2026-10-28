// Hipersign ERP v1.5.4 (1.5.5: hidden on the app launcher) — the prototype's top bar above every desk page: search, company, + New, Arabic / English,
// notifications with an unread count, and the user menu. Only with the Hipersign desk theme (html.hs-theme).
// Search and notifications open Frappe's own search dialog and notification panel, so nothing is duplicated.
frappe.provide("hipersign.topbar");

hipersign.topbar.ROLES = [
	["System Manager", "Administrator"], ["Managing Director", "Managing Director"], ["Accounts Manager", "Finance Manager"],
	["Sales Manager", "Sales Manager"], ["Purchase Manager", "Purchase Manager"], ["Stock Manager", "Warehouse Manager"],
	["HR Manager", "HR Manager"], ["Logistics Coordinator", "Logistics"], ["Accounts User", "Accountant"],
	["Sales User", "Sales Executive"], ["Purchase User", "Buyer"], ["Stock User", "Storekeeper"], ["Driver", "Driver"],
];

hipersign.topbar.role = function () {
	if (frappe.session.user === "Administrator") return __("Administrator");
	const roles = frappe.user_roles || [];
	const hit = hipersign.topbar.ROLES.find(([r]) => roles.includes(r));
	return hit ? __(hit[1]) : "";
};

// the app launcher (/desk) has its own header and no menu: no top bar there
hipersign.topbar.hidden_here = function () {
	const r = frappe.get_route_str ? frappe.get_route_str() : "";
	return !r || r === "desktop" || r === "desk";
};

hipersign.topbar.sync = function () {
	const hide = hipersign.topbar.hidden_here();
	$(".main-section > header.hs-topbar-host").toggle(!hide);
	document.documentElement.classList.toggle("hs-topbar-on", !hide && !!$(".hs-topbar").length);
};

hipersign.topbar.render = function () {
	if (!document.documentElement.classList.contains("hs-theme") || frappe.session.user === "Guest") return;
	const $host = $(".main-section > header").first();
	if (!$host.length) return;
	if ($host.find(".hs-topbar").length) return hipersign.topbar.sync();
	const esc = (s) => frappe.utils.escape_html(s || "");
	const icon = (n) => frappe.utils.icon(n, "sm");
	const name = frappe.user.full_name ? frappe.user.full_name() : frappe.session.user;
	const ar = (frappe.boot.lang || "en").startsWith("ar");
	$host.addClass("hs-topbar-host").html(`
		<div class="hs-topbar">
			<button type="button" class="hs-tb-search" title="${esc(__("Search"))}">${icon("search")}<span>${esc(__("Search items, orders, customers, shipments…"))}</span><kbd>Ctrl+K</kbd></button>
			<span class="hs-tb-sp"></span>
			<select class="hs-tb-company" title="${esc(__("Company"))}"></select>
			<button type="button" class="btn btn-primary hs-tb-new">${icon("plus")}<span>${esc(__("New"))}</span></button>
			<button type="button" class="hs-tb-icon hs-tb-lang" title="${esc(ar ? "English" : "العربية")}">${ar ? "EN" : "ع"}</button>
			<button type="button" class="hs-tb-icon hs-tb-bell" title="${esc(__("Notifications"))}">${icon("bell")}<span class="hs-tb-dot" hidden></span></button>
			<div class="dropdown hs-tb-user">
				<button type="button" class="hs-tb-userbtn" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
					${frappe.avatar(frappe.session.user, "avatar-medium")}
					<span class="hs-tb-ut"><b>${esc(name)}</b><span>${esc(hipersign.topbar.role())}</span></span>${icon("chevron-down")}
				</button>
				<div class="dropdown-menu dropdown-menu-right">
					<a class="dropdown-item" data-act="settings">${esc(__("My Settings"))}</a>
					<a class="dropdown-item" data-act="theme">${esc(__("Toggle Theme"))}</a>
					<div class="dropdown-divider"></div>
					<a class="dropdown-item" data-act="logout">${esc(__("Log out"))}</a>
				</div>
			</div>
		</div>`);
	hipersign.topbar.sync();
	hipersign.topbar.refresh(true);
};

hipersign.topbar.refresh = function (force) {
	const now = Date.now();
	if (!force && hipersign.topbar._at && now - hipersign.topbar._at < 60000) return;
	hipersign.topbar._at = now;
	frappe.xcall("hipersign_trading.api.ui.topbar").then((r) => {
		if (!r) return;
		const $dot = $(".hs-topbar .hs-tb-dot");
		$dot.text(r.unread > 99 ? "99+" : r.unread).prop("hidden", !r.unread);
		const $sel = $(".hs-topbar .hs-tb-company");
		if ((r.companies || []).length > 1) {
			$sel.html(r.companies.map((c) => `<option value="${frappe.utils.escape_html(c)}">${frappe.utils.escape_html(c)}</option>`).join(""));
			$sel.val(r.company || r.companies[0]).show();
		} else {
			$sel.hide();
		}
	});
};

// the sidebar's own Search and Notification entries do the work (hidden by the theme while the top bar is on)
hipersign.topbar.open_search = function () {
	const $a = $(".body-sidebar .navbar-search-bar .item-anchor").first();
	if ($a.length) $a[0].click();
	else if (frappe.searchdialog && frappe.searchdialog.search) frappe.searchdialog.search.init_search("", "global_search");
};

hipersign.topbar.open_notifications = function () {
	const $a = $(".body-sidebar .sidebar-notification .item-anchor").first();
	// after this click has finished: Frappe closes the panel on any click outside it, and the bell is outside it
	if ($a.length) setTimeout(() => $a[0].click(), 0);
	else frappe.set_route("List", "Notification Log");
	setTimeout(() => hipersign.topbar.refresh(true), 1500);
};

$(document).on("click", ".hs-topbar .hs-tb-search", () => hipersign.topbar.open_search());
$(document).on("click", ".hs-topbar .hs-tb-bell", (e) => {
	e.stopPropagation();
	hipersign.topbar.open_notifications();
});
$(document).on("click", ".hs-topbar .hs-tb-new", () => frappe.set_route("hipersign-create"));
$(document).on("change", ".hs-topbar .hs-tb-company", function () {
	const company = $(this).val();
	frappe.xcall("hipersign_trading.api.ui.set_company", { company }).then(() => {
		frappe.defaults.set_user_default_local("Company", company);
		frappe.show_alert({ message: __("New documents will use {0}", [company]), indicator: "green" });
	});
});
$(document).on("click", ".hs-topbar .hs-tb-lang", () => {
	const to = (frappe.boot.lang || "en").startsWith("ar") ? "en" : "ar";
	frappe.xcall("hipersign_trading.api.ui.set_language", { language: to }).then(() => window.location.reload());
});
$(document).on("click", ".hs-topbar .hs-tb-user [data-act]", function (e) {
	e.preventDefault();
	const act = $(this).attr("data-act");
	if (act === "settings") frappe.set_route("Form", "User", frappe.session.user);
	else if (act === "theme") new frappe.ui.ThemeSwitcher().show();
	else if (act === "logout") frappe.app.logout();
});

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
