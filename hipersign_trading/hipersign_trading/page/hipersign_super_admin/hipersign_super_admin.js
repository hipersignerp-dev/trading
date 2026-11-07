// v1.8.3: Super Admin — Hipersign's own console on a client site. Only super admins (the users in the site config's
// hipersign_super_admins, or Administrator when it is not set) can open it: the licence (users and companies allowed, which modules may be
// switched on, Frappe/ERPNext pop-ups for the client's admins), with what is in use today.
frappe.pages["hipersign-super-admin"].on_page_load = function (wrapper) {
	const ui = hipersign.ui, esc = ui.esc;
	const v = ui.page(wrapper, {
		title: __("Super Admin"),
		desc: __("The client's licence: how many users and companies, which modules, and who sees Frappe and ERPNext pop-ups. Only Hipersign's super admins can open this page."),
	});
	let st = null, dirty = {};
	const val = (k) => (k in dirty ? dirty[k] : st.licence[k]);
	const meter = (used, max, label) => {
		const pct = max ? Math.min(1, used / max) : 0, col = !max ? "blue" : used > max ? "red" : used >= max ? "amber" : "green";
		return `<div class="hsx-card hs-bw"><div class="hsx-card-h"><h3>${esc(label)}</h3></div><div class="hsx-card-b">
			${hipersign.chart.gauge(pct, max ? `${used}/${max}` : String(used), max ? __("in use of the licence") : __("no limit set"), { color: col })}</div></div>`;
	};
	function render() {
		const L = st.licence, u = st.usage;
		const feats = new Set(dirty.licensed_features || st.licensed_features);
		const limit = !!val("limit_features");
		const groups = st.groups.map((g) => {
			const fs = st.features.filter((f) => f.group === g);
			if (!fs.length) return "";
			return `<div class="hs-sa-g"><b>${esc(g)}</b>${fs.map((f) => `<label class="hs-sa-f ${limit ? "" : "off"}"><input type="checkbox" data-feat="${esc(f.key)}" ${feats.has(f.key) || !limit ? "checked" : ""} ${limit ? "" : "disabled"}>
				<span>${esc(f.label)}<small>${esc(f.desc)}</small></span>${f.on ? `<span class="hsx-pill green">${esc(__("On"))}</span>` : ""}</label>`).join("")}</div>`;
		}).join("");
		const urow = (x) => `<tr class="${x.enabled ? "" : "text-muted"}"><td><b>${esc(x.full_name || x.name)}</b><div class="small text-muted">${esc(x.name)}</div></td>
			<td>${esc((x.roles || []).join(", "))}</td><td>${x.counted ? `<span class="hsx-pill blue">${esc(__("Counted"))}</span>` : `<span class="hsx-pill">${esc(x.why || __("Not counted"))}</span>`}</td>
			<td class="small text-muted">${x.last_active ? esc(frappe.datetime.comment_when(x.last_active)) : "—"}</td></tr>`;
		v.$body.html(`
			<div class="hs-band" style="--bn:3">${meter(u.users, u.max_users, __("Users"))}${meter(u.companies, u.max_companies, __("Companies"))}
				<div class="hsx-card hs-bw hs-dark"><div class="hsx-card-h"><h3>${esc(__("Licence"))}</h3></div><div class="hsx-card-b">
				<div class="hs-big">${esc(L.licensee || __("Not named"))}</div>
				<div class="hs-drow"><span>${esc(__("Valid until"))}</span><b>${L.valid_until ? esc(frappe.datetime.str_to_user(L.valid_until)) : "—"}</b></div>
				<div class="hs-drow"><span>${esc(__("Modules"))}</span><b>${limit ? esc(__("{0} of {1}", [feats.size, st.features.length])) : esc(__("All"))}</b></div>
				<div class="hs-drow"><span>${esc(__("Frappe pop-ups"))}</span><b>${val("show_frappe_popups_to_all") ? esc(__("Everyone")) : esc(__("Super admins only"))}</b></div></div></div></div>
			<div class="hsx-card"><div class="hsx-card-h"><h3>${esc(__("Licence"))}</h3></div><div class="hsx-card-b hs-sa-form">
				<label>${esc(__("Licensed to"))}<input class="form-control" data-k="licensee" value="${esc(val("licensee") || "")}"></label>
				<label>${esc(__("Valid until"))}<input class="form-control" type="date" data-k="valid_until" value="${esc(val("valid_until") || "")}"></label>
				<label>${esc(__("Users allowed"))} <small>${esc(__("0 = no limit"))}</small><input class="form-control" type="number" min="0" data-k="max_users" value="${cint(val("max_users"))}"></label>
				<label>${esc(__("Companies allowed"))} <small>${esc(__("0 = no limit"))}</small><input class="form-control" type="number" min="0" data-k="max_companies" value="${cint(val("max_companies"))}"></label>
				<label class="hs-sa-chk"><input type="checkbox" data-k="show_frappe_popups_to_all" ${val("show_frappe_popups_to_all") ? "checked" : ""}> ${esc(__("Show Frappe and ERPNext pop-ups to the client's admins too"))}
					<small>${esc(__("Off: update notices, What's new, onboarding tours and Frappe prompts appear only for super admins. Errors and validation messages always show."))}</small></label>
				<label class="hs-sa-wide">${esc(__("Notes"))}<textarea class="form-control" rows="2" data-k="notes">${esc(val("notes") || "")}</textarea></label>
			</div></div>
			<div class="hsx-card"><div class="hsx-card-h"><h3>${esc(__("Modules"))}</h3></div><div class="hsx-card-b">
				<label class="hs-sa-chk"><input type="checkbox" data-k="limit_features" ${limit ? "checked" : ""}> ${esc(__("Only the modules ticked below"))}
					<small>${esc(__("Modules left out cannot be switched on in Hipersign Settings › Features and disappear from the menu. No data is deleted."))}</small></label>
				<div class="hs-sa-grid">${groups}</div></div></div>
			<div class="hsx-card"><div class="hsx-card-h"><h3>${esc(__("Users"))} <small>${esc(__("{0} counted · portal customers, driver-only logins and super admins are not counted", [u.users]))}</small></h3></div>
				<div class="hsx-card-b flush"><div class="hsx-tw"><table class="hsx-t"><thead><tr><th>${esc(__("User"))}</th><th>${esc(__("Roles"))}</th><th>${esc(__("Licence"))}</th><th>${esc(__("Last active"))}</th></tr></thead>
				<tbody>${st.users.map(urow).join("")}</tbody></table></div></div></div>
			<div class="hsx-card"><div class="hsx-card-h"><h3>${esc(__("Super admins"))}</h3></div><div class="hsx-card-b">
				<p>${st.super_admins.map((x) => `<span class="hsx-pill blue">${esc(x)}</span>`).join(" ")}</p>
				<p class="small text-muted">${esc(__("Set in Press › Site › Config as hipersign_super_admins (a list of logins). When it is set, only those logins are super admins — Administrator too becomes an ordinary admin. The client cannot change this from the ERP."))}</p></div></div>`);
		v.$actions.html(`<button class="btn btn-primary btn-sm hs-sa-save" ${Object.keys(dirty).length ? "" : "disabled"}>${esc(__("Save licence"))}</button>`);
	}
	function load() {
		frappe.xcall("hipersign_trading.api.superadmin.get_state").then((r) => { st = r; dirty = {}; render(); })
			.catch(() => v.$body.html(`<div class="hsx-empty">${esc(__("Only Hipersign's super admins can open this page."))}</div>`));
	}
	v.$wrap.on("change input", "[data-k]", function () {
		const k = $(this).attr("data-k");
		dirty[k] = this.type === "checkbox" ? (this.checked ? 1 : 0) : $(this).val();
		if (this.type === "checkbox") render(); else v.$actions.find(".hs-sa-save").prop("disabled", false);
	});
	v.$wrap.on("change", "[data-feat]", function () {
		const s = new Set(dirty.licensed_features || st.licensed_features);
		this.checked ? s.add($(this).attr("data-feat")) : s.delete($(this).attr("data-feat"));
		dirty.licensed_features = [...s];
		render();
	});
	v.$wrap.on("click", ".hs-sa-save", function () {
		const go = () => frappe.xcall("hipersign_trading.api.superadmin.save", { values: dirty }).then((r) => {
			st = r; dirty = {}; render();
			frappe.show_alert({ message: __("Licence saved"), indicator: "green" });
		});
		const out = dirty.licensed_features && st.features.filter((f) => f.on && !dirty.licensed_features.includes(f.key));
		if (val("limit_features") && out && out.length) frappe.confirm(__("These modules are on now and will be switched off: {0}. No data is deleted. Continue?", [out.map((f) => f.label).join(", ")]), go);
		else go();
	});
	load();
	$(wrapper).on("show", load);
};
