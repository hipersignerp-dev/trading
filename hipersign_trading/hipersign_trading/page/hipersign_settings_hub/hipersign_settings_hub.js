// v1.8.4 (#37): Workflows & Settings — one Hipersign page for the settings an administrator changes: Hipersign Settings
// (features, look & menus, approval rules), approval workflows, document rules, editable lists, users, system settings,
// the menu builder and the licence summary. Each card opens the place where it is changed.
frappe.pages["hipersign-settings-hub"].on_page_load = function (wrapper) {
	const ui = hipersign.ui, esc = ui.esc;
	const v = ui.page(wrapper, { title: __("Workflows & Settings"), desc: __("Features, look and menus, approval rules and workflows, document rules, lists and users — everything an administrator sets, in one place.") });
	const CARDS = [
		{ icon: "sliders-horizontal", title: __("Hipersign Settings"), text: __("Business pack and features, company defaults, numbering and the Hipersign look."), route: ["Form", "Hipersign Settings"], count: null },
		{ icon: "palette", title: __("Look & menus"), text: __("Chart style, brand colour, ERP theme and the graphs at the top of pages."), route: ["Form", "Hipersign Settings"], options: { hs_section: "look" } },
		{ icon: "menu", title: __("Menu builder"), text: __("Rename, hide or reorder menu entries per company, role or site."), route: ["hipersign-menu"] },
		{ icon: "workflow", title: __("Approval workflows"), text: __("Who approves quotations, orders, purchase orders and payments, and at which amounts."), route: ["List", "Workflow"], dt: "Workflow", f: { is_active: 1 }, unit: __("active") },
		{ icon: "file-check", title: __("Document rules"), text: __("Which documents a record needs before it can be submitted (trade licence, VAT certificate…)."), route: ["hipersign-doccentre"], options: { hs_tab: "rules" }, dt: "Hipersign Document Rule", unit: __("rules") },
		{ icon: "list", title: __("Editable lists"), text: __("The drop-down values your team can change: lead sources, reasons, document types…"), route: ["List", "Hipersign List Value"], dt: "Hipersign List Value", unit: __("values") },
		{ icon: "users", title: __("Users"), text: __("Logins, roles and which companies each person sees."), route: ["List", "User"], dt: "User", f: { enabled: 1, user_type: "System User" }, unit: __("desk users") },
		{ icon: "settings", title: __("System settings"), text: __("Language, time zone, date and number format, password policy."), route: ["Form", "System Settings"] },
		{ icon: "flask-conical", title: __("Test Centre"), text: __("Prepared test scripts per role, with results."), route: ["hipersign-tests"] },
	];
	function render(lic) {
		const can = (c) => !c.dt || frappe.model.can_read(c.dt);
		v.$body.html(`${lic ? `<div class="hsx-card hs-sh-lic"><div class="hsx-card-b"><b>${esc(__("Licence"))}</b>
			<span>${esc(__("Users"))}: ${lic.users}${lic.max_users ? " / " + lic.max_users : ""}</span><span>${esc(__("Companies"))}: ${lic.companies}${lic.max_companies ? " / " + lic.max_companies : ""}</span>
			<span>${esc(__("Modules"))}: ${lic.features ? lic.features.length : esc(__("All"))}</span>${(frappe.boot.hipersign || {}).super_admin ? `<a class="btn btn-xs btn-default" data-sa="1">${esc(__("Super Admin"))}</a>` : ""}</div></div>` : ""}
			<div class="hs-sh-grid">${CARDS.filter(can).map((c, i) => `<button type="button" class="hsx-card hs-sh-card" data-i="${i}">
				<span class="hs-sh-ic">${frappe.utils.icon(c.icon, "md")}</span><span class="hs-sh-t"><b>${esc(c.title)}</b><span>${esc(c.text)}</span>
				${c.dt ? `<small class="hs-sh-n" data-n="${i}"></small>` : ""}</span>${frappe.utils.icon("right", "sm")}</button>`).join("")}</div>`);
		CARDS.forEach((c, i) => {
			if (!c.dt || !can(c)) return;
			frappe.xcall("frappe.client.get_count", { doctype: c.dt, filters: c.f || {} }).then((n) => v.$body.find(`[data-n="${i}"]`).text(`${n} ${c.unit || ""}`)).catch(() => {});
		});
	}
	v.$body.on("click", ".hs-sh-card", function () {
		const c = CARDS[+$(this).attr("data-i")];
		frappe.route_options = c.options || null;
		frappe.set_route(...c.route);
	});
	v.$body.on("click", "[data-sa]", () => frappe.set_route("hipersign-super-admin"));
	frappe.xcall("hipersign_trading.licence.licence_summary").then(render).catch(() => render(null));
};
