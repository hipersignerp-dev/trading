// Hipersign ERP v1.8.0 — Admin → Menu builder (prototype p19 "Menu builder").
// Show or hide, rename in English / العربية / 中文 and reorder every menu group and screen, add custom links — for the
// whole site, one company or one role (role beats company beats site). Saved in Hipersign Menu Override; every change
// is logged in Hipersign Menu Log. The rules: hipersign_trading/menu.py.
frappe.pages["hipersign-menu"].on_page_load = function (wrapper) {
	const ui = hipersign.ui, esc = ui.esc, ic = ui.icon;
	const v = ui.page(wrapper, { band: "menu",
		title: __("Menu builder"),
		desc: __("Show or hide, rename in English, Arabic and Chinese, and reorder any menu group or screen — for the whole site, one company or one role. Users see the new menu the next time they load the desk."),
	});
	const LANGS = [["en", "English"], ["ar", "العربية"], ["zh", "中文"]];
	const st = { scope: "Site", company: null, role: null, data: null, own: {}, dirty: false, preview: [] };

	v.$actions.html(`<button class="btn btn-default btn-sm hsm-reset">${ic("refresh")} ${esc(__("Reset to standard"))}</button>
		<button class="btn btn-primary btn-sm hsm-save" disabled>${esc(__("Save"))}</button>`);

	// ---------------------------------------------------------------- state helpers
	const inh = (k) => ((st.data && st.data.inherited.items) || {})[k] || {};
	const own = (k) => st.own[k] || {};
	const std = (k) => (st.data.std || {})[k] || {};
	const kind = (k) => (k.startsWith("g:") ? "Group" : "Item");
	const row = (k) => {
		if (!st.own[k]) st.own[k] = { item_type: kind(k), visibility: "Standard", sort_order: 0 };
		return st.own[k];
	};
	const hidden = (k) => {
		const o = own(k).visibility;
		return o === "Hidden" ? true : o === "Shown" ? false : !!inh(k).hidden;
	};
	const sortOf = (k, i) => own(k).sort_order || inh(k).sort || (i + 1) * 10;
	const links = () => {
		const out = {};
		Object.entries((st.data && st.data.inherited.links) || {}).forEach(([k, l]) => (out[k] = { key: k, label_en: l.label, link_url: l.url, icon: l.icon, parent_group: l.parent_group, inherited: 1 }));
		Object.entries(st.own).forEach(([k, r]) => { if (r.item_type === "Custom Link") out[k] = Object.assign({ key: k }, r); });
		return out;
	};
	// the tree in the order this scope gives it: [{key, label, icon, items: [{key, label, icon, link}]}]
	function model() {
		const G = st.data.groups.map((g, gi) => ({ key: g.key, label: g.label, icon: g.icon, s: sortOf(g.key, gi), items: g.items.map((it, ii) => ({ key: it.key, label: it.label, icon: it.icon, s: sortOf(it.key, ii) })) }));
		Object.values(links()).forEach((l, n) => {
			const g = G.find((x) => x.key === l.parent_group) || G[G.length - 1];
			g.items.push({ key: l.key, label: l.label_en, icon: l.icon || "link", link: l, s: own(l.key).sort_order || inh(l.key).sort || 10000 + n });
		});
		G.sort((a, b) => a.s - b.s);
		G.forEach((g) => g.items.sort((a, b) => a.s - b.s));
		return G;
	}
	function changed(redraw) {
		const was = st.dirty;
		st.dirty = true;
		v.$actions.find(".hsm-save").prop("disabled", false);
		// typing a name does not rebuild the tree (the cursor stays in the next box)
		if (redraw !== false || !was) draw();
		preview();
	}

	// ---------------------------------------------------------------- render
	function input(k, lang, def) {
		const r = own(k), isLink = r.item_type === "Custom Link";
		const ph = isLink ? (lang === "en" ? "" : r.label_en || "") : ((inh(k).labels || {})[lang] || std(k)[lang] || def);
		return `<input class="form-control input-xs hsm-in" data-k="${esc(k)}" data-lang="${lang}" ${lang === "ar" ? 'dir="rtl"' : ""} value="${esc(r["label_" + lang] || "")}"
			placeholder="${esc(ph)}" aria-label="${esc(def)} — ${esc(LANGS.find((x) => x[0] === lang)[1])}">`;
	}
	function line(type, x, i, n) {
		const off = hidden(x.key), l = x.link;
		const tag = l ? `<span class="hsx-pill ${l.inherited ? "grey" : "blue"}">${esc(l.inherited ? __("Custom link · whole site") : __("Custom link"))}</span>` : "";
		return `<div class="hsm-row ${type === "g" ? "hsm-g" : "hsm-i"} ${off ? "off" : ""}" data-k="${esc(x.key)}">
			<label class="hsm-sw" title="${esc(off ? __("Hidden — switch on to show") : __("Shown — switch off to hide"))}"><input type="checkbox" class="hsm-vis" data-k="${esc(x.key)}" ${off ? "" : "checked"}><span></span></label>
			<span class="hsm-n">${type === "i" && x.icon ? ic(x.icon) : ""}<b title="${esc(x.label)}">${esc(l ? x.label : __(x.label))}</b>${tag}${l ? `<small class="text-muted">${esc(l.link_url)}</small>` : ""}</span>
			<span class="hsm-ins">${LANGS.map(([lg]) => (l && l.inherited ? `<span class="text-muted small">${lg === "en" ? esc(l.label_en) : ""}</span>` : input(x.key, lg, x.label))).join("")}</span>
			<span class="hsm-btns"><button class="btn btn-xs btn-default hsm-mv" data-d="-1" ${i === 0 ? "disabled" : ""} title="${esc(__("Move up"))}" aria-label="${esc(__("Move up"))}">${ic("chevron-up", "xs")}</button><button class="btn btn-xs btn-default hsm-mv" data-d="1" ${i === n - 1 ? "disabled" : ""} title="${esc(__("Move down"))}" aria-label="${esc(__("Move down"))}">${ic("chevron-down", "xs")}</button>${l && !l.inherited ? `<button class="btn btn-xs btn-default hsm-del" title="${esc(__("Remove link"))}" aria-label="${esc(__("Remove link"))}">${ic("delete", "xs")}</button>` : ""}</span>
		</div>`;
	}
	function scopeBar() {
		const d = st.data;
		const hint = { Site: __("Applies to everyone unless a company or role changes it"), Company: __("Applies when this company is selected at the top"), Role: __("Applies to users with this role — wins over company and site") }[st.scope];
		return `<div class="hsm-scope">${ui.seg("hsm-scope", [["Site", __("Whole site")], ["Company", __("Company")], ["Role", __("Role")]], st.scope)}
			${st.scope === "Company" ? `<select class="form-control input-sm hsm-co" aria-label="${esc(__("Company"))}">${d.companies.map((c) => `<option ${c === st.company ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>` : ""}
			${st.scope === "Role" ? `<select class="form-control input-sm hsm-ro" aria-label="${esc(__("Role"))}">${d.roles.map((r) => `<option value="${esc(r)}" ${r === st.role ? "selected" : ""}>${esc(__(r))}</option>`).join("")}</select>` : ""}
			<span class="text-muted small">${esc(hint)}</span>${st.dirty ? `<span class="hsx-pill orange">${esc(__("Unsaved changes"))}</span>` : ""}</div>`;
	}
	function draw() {
		if (!st.data) return;
		const G = model();
		const tree = G.map((g, gi) => line("g", g, gi, G.length) + g.items.map((it, ii) => line("i", it, ii, g.items.length)).join("")).join("");
		const head = `<div class="hsm-row hsm-head"><span></span><span>${esc(__("Menu item"))}</span><span class="hsm-ins">${LANGS.map(([, l]) => `<span>${esc(l)}</span>`).join("")}</span><span></span></div>`;
		const add = ui.card(__("Add a custom link"), `<div class="hsm-add">
			${LANGS.map(([lg, l]) => `<label>${esc(__("Label"))} (${esc(l)})<input class="form-control input-sm hsm-l-${lg}" ${lg === "ar" ? 'dir="rtl"' : ""} placeholder="${esc({ en: "Supplier portal", ar: "بوابة الموردين", zh: "供应商门户" }[lg])}"></label>`).join("")}
			<label class="hsm-wide">${esc(__("Link — web address, /app/… or #page"))}<input class="form-control input-sm hsm-url" placeholder="https://… · /app/… · #hipersign-home"></label>
			<label>${esc(__("Under menu group"))}<select class="form-control input-sm hsm-grp">${G.map((g) => `<option value="${esc(g.key)}">${esc(__(g.label))}</option>`).join("")}</select></label>
			<label>${esc(__("Icon"))}<input class="form-control input-sm hsm-icon" placeholder="link"></label>
			<div class="hsm-wide"><button class="btn btn-default btn-sm hsm-addl">${ic("add")} ${esc(__("Add link"))}</button></div></div>`, { icon: "link", sub: st.data.scope_label });
		const pv = ui.card(__("Preview"), `<div class="hsm-pv">${previewHtml()}</div>
			<p class="hsx-note">${esc(__("What a user in this scope sees (before role permissions), in the language you work in."))}</p>`, { icon: "eye" });
		const help = ui.card(__("How it is applied"), `<dl class="hsm-help">
			<dt>${esc(__("Precedence"))}</dt><dd>${esc(__("Role → company → whole site; the most specific wins"))}</dd>
			<dt>${esc(__("Hidden screens"))}</dt><dd>${esc(__("Gone from the sidebar, + New and the top-bar search; a direct link still opens them for users who may see them"))}</dd>
			<dt>${esc(__("Roles"))}</dt><dd>${esc(__("A menu never grants access — role permissions still decide"))}</dd>
			<dt>${esc(__("Languages"))}</dt><dd>${esc(__("Empty boxes keep the standard translation"))}</dd>
			<dt>${esc(__("New modules"))}</dt><dd>${esc(__("Groups and screens added by later releases appear here by themselves"))}</dd></dl>`, { icon: "info" });
		const log = ui.card(__("Change log"), ui.table([{ label: __("When") }, { label: __("Scope") }, { label: __("Change") }, { label: __("By") }],
			(st.data.log || []).map((x) => ({ cells: [`<span class="small">${esc(frappe.datetime.str_to_user(x.creation))}</span>`, esc(x.scope_label), esc(x.change), esc(frappe.user.full_name(x.owner))] })),
			__("No changes yet — every change to the menu is logged here.")), { icon: "activity" });
		const top = $(wrapper).find(".hsm-tree").scrollTop();
		v.$body.html(scopeBar() + `<div class="hsx-grid2 hsm-grid">${ui.card(`${__("Menu")} — ${st.data.scope_label}`, `<div class="hsm-tree">${head}${tree}</div>`,
			{ icon: "menu", sub: __("switch to hide · type a name to rename · arrows to reorder") })}<div class="hsm-side">${pv}${add}${help}</div></div>${log}`);
		$(wrapper).find(".hsm-tree").scrollTop(top || 0);
	}

	function previewHtml() {
		return st.preview.map((g) => `<div class="hsm-pv-g">${esc(g.label)}</div>${g.items.map((i) => `<div class="hsm-pv-i">${ic(i.icon || "link")}<span>${esc(i.label)}</span>${i.custom ? ic("external-link", "xs") : ""}</div>`).join("")}`).join("")
			|| `<div class="hsx-empty">${esc(__("Nothing to show."))}</div>`;
	}

	// ---------------------------------------------------------------- server
	function load() {
		ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.menu.get_builder", { scope: st.scope, company: st.company, role: st.role }).then((d) => {
			st.data = d;
			st.own = JSON.parse(JSON.stringify(d.own || {}));
			st.dirty = false;
			v.$actions.find(".hsm-save").prop("disabled", true);
			// v1.8.4 (#28): the server picks the company / role when none is chosen yet
			if (st.scope === "Company") st.company = d.company || st.company || d.companies[0];
			if (st.scope === "Role") st.role = d.role || st.role || d.roles[0];
			draw();
			preview();
		}).catch((e) => {
			// v1.8.4 (#28): show why instead of spinning; the scope switch stays usable
			const why = (e && (e.message || (e._server_messages && JSON.parse(JSON.parse(e._server_messages)[0]).message))) || __("The menu could not be loaded.");
			v.$body.html(`<div class="hsx-empty">${esc(__("The menu could not be loaded for this scope."))}<br><small>${esc(frappe.utils.strip_html(String(why)))}</small><br>
				<button class="btn btn-default btn-sm hsm-retry" style="margin-top:10px">${esc(__("Try again"))}</button>
				<button class="btn btn-default btn-sm hsm-site" style="margin-top:10px">${esc(__("Back to whole site"))}</button></div>`);
		});
	}
	v.$body.on("click", ".hsm-retry", () => load());
	v.$body.on("click", ".hsm-site", () => { st.scope = "Site"; st.dirty = false; load(); });
	const preview = frappe.utils.debounce(() => {
		if (!st.data) return;
		frappe.xcall("hipersign_trading.api.menu.preview", { scope: st.scope, company: st.company, role: st.role, config: JSON.stringify(st.own) })
			.then((p) => { st.preview = p || []; v.$body.find(".hsm-pv").html(previewHtml()); })
			.catch(() => {});
	}, 300);
	function switchScope(fn) {
		const go = () => { fn(); load(); };
		st.dirty ? frappe.confirm(__("Leave this scope without saving your changes?"), go) : go();
	}

	// ---------------------------------------------------------------- events
	v.$body.on("click", "[data-seg='hsm-scope'] button", function () {
		const s = $(this).attr("data-v");
		if (s === st.scope) return;
		switchScope(() => { st.scope = s; st.company = st.company || null; st.role = st.role || null; });
	});
	v.$body.on("change", ".hsm-co", function () { const c = $(this).val(); switchScope(() => (st.company = c)); });
	v.$body.on("change", ".hsm-ro", function () { const r = $(this).val(); switchScope(() => (st.role = r)); });
	v.$body.on("change", ".hsm-vis", function () {
		const k = $(this).attr("data-k"), want = !this.checked, r = row(k);
		r.visibility = want === !!inh(k).hidden ? "Standard" : want ? "Hidden" : "Shown";
		changed();
	});
	v.$body.on("change", ".hsm-in", function () {
		const k = $(this).attr("data-k"), lg = $(this).attr("data-lang"), r = row(k);
		r["label_" + lg] = $(this).val().trim();
		changed(false);
	});
	v.$body.on("click", ".hsm-mv", function () {
		const k = $(this).closest(".hsm-row").attr("data-k"), d = +$(this).attr("data-d");
		const G = model(), sibs = k.startsWith("g:") ? G : (G.find((g) => g.items.some((i) => i.key === k)) || { items: [] }).items;
		const keys = sibs.map((x) => x.key), i = keys.indexOf(k), j = i + d;
		if (i < 0 || j < 0 || j >= keys.length) return;
		keys.splice(i, 1);
		keys.splice(j, 0, k);
		keys.forEach((key, n) => (row(key).sort_order = (n + 1) * 10));
		changed();
	});
	v.$body.on("click", ".hsm-del", function () {
		const k = $(this).closest(".hsm-row").attr("data-k");
		delete st.own[k];
		changed();
	});
	v.$body.on("click", ".hsm-addl", function () {
		const $b = v.$body, val = (c) => ($b.find(c).val() || "").trim();
		const en = val(".hsm-l-en"), url = val(".hsm-url");
		if (!en || !url) return frappe.show_alert({ message: __("Enter a label and a link"), indicator: "orange" });
		if (!/^(https?:\/\/\S+|\/\S*|#[\w\-/]+)$/.test(url)) return frappe.show_alert({ message: __("Use a web address (https://…), a desk path (/app/…) or #page"), indicator: "orange" });
		const key = "link-" + Date.now().toString(36);
		st.own[key] = { item_type: "Custom Link", visibility: "Standard", sort_order: 0, label_en: en, label_ar: val(".hsm-l-ar"), label_zh: val(".hsm-l-zh"),
			link_url: url, parent_group: val(".hsm-grp"), icon: val(".hsm-icon") || "link" };
		changed();
	});
	v.$actions.on("click", ".hsm-save", function () {
		const btn = this;
		$(btn).prop("disabled", true);
		frappe.xcall("hipersign_trading.api.menu.save", { scope: st.scope, company: st.company, role: st.role, config: JSON.stringify(st.own) }).then((r) => {
			frappe.show_alert({ message: r.changes ? __("Menu saved — {0} changes. Users see it the next time they load the desk.", [r.changes]) : __("Nothing changed"), indicator: "green" }, 6);
			st.own = JSON.parse(JSON.stringify(r.own || {}));
			st.data.own = r.own;
			st.data.log = r.log;
			st.dirty = false;
			draw();
			preview();
		}).catch(() => $(btn).prop("disabled", false));
	});
	v.$actions.on("click", ".hsm-reset", () => {
		frappe.confirm(__("Remove every menu change for {0}? Other scopes keep theirs.", [esc(st.data ? st.data.scope_label : "")]), () =>
			frappe.xcall("hipersign_trading.api.menu.reset", { scope: st.scope, company: st.company, role: st.role }).then((r) => {
				frappe.show_alert({ message: __("Menu reset to standard — {0}", [st.data.scope_label]), indicator: "green" });
				load();
			}));
	});
	$(window).on("beforeunload.hsm", () => (st.dirty ? true : undefined));
	load();
};
