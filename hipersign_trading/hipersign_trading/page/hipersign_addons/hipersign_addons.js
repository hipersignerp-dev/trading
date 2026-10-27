// Add-ons & Pricing — the optional extras a client can add, with development hours, cost and third-party fees.
// The selection, client name, rate and contingency are kept in this browser; print the estimate to share it.
frappe.pages["hipersign-addons"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Add-ons & Pricing"),
		desc: __("Optional extras for messaging, tracking, payments and compliance. Tick what the client wants — hours and cost add up, needed add-ons are included automatically."),
	});
	const KEY = "hs_addons_v1";
	let cat = { addons: [], categories: [], default_rate: 100, can_rate: false };
	let st = { picked: {}, rate: null, contingency: 0, client: "", q: "", cat: "" };
	try {
		Object.assign(st, JSON.parse(localStorage.getItem(KEY) || "{}"));
	} catch (e) {
		/* private window — keep in memory */
	}
	const keep = () => {
		try {
			localStorage.setItem(KEY, JSON.stringify({ picked: st.picked, rate: st.rate, contingency: st.contingency, client: st.client }));
		} catch (e) {
			/* ignore */
		}
	};
	const byId = (id) => cat.addons.find((a) => a.id === id);
	const money = (x) => "AED " + format_number(Math.round(x), null, 0);
	const rate = () => (st.rate == null ? flt(cat.default_rate) : flt(st.rate));
	const hours = (a) => (a.alt && st.picked[a.alt.if] ? [a.alt.lo, a.alt.hi, true] : [a.lo, a.hi, false]);
	function totals() {
		const sel = cat.addons.filter((a) => st.picked[a.id]);
		let lo = 0, hi = 0;
		sel.forEach((a) => {
			const [l, h] = hours(a);
			lo += l;
			hi += h;
		});
		const k = 1 + flt(st.contingency) / 100;
		return { sel, lo: Math.round(lo * k), hi: Math.round(hi * k), rate: rate() };
	}
	const weeks = (h) => Math.max(1, Math.ceil(h / 30));

	function pick(id, on) {
		const a = byId(id);
		if (on) {
			st.picked[id] = true;
			const add = (a.deps || []).filter((d) => !st.picked[d]);
			if (a.depsAny && !a.depsAny.some((d) => st.picked[d])) add.push(a.depsAny[0]);
			add.forEach((d) => (st.picked[d] = true));
			if (add.length) frappe.show_alert({ message: __("Also added: {0} (needed)", [add.map((d) => byId(d).name).join(", ")]), indicator: "blue" });
		} else {
			delete st.picked[id];
			const drop = cat.addons.filter((x) => st.picked[x.id] && ((x.deps || []).includes(id) || (x.depsAny && !x.depsAny.some((d) => st.picked[d]))));
			drop.forEach((x) => delete st.picked[x.id]);
			if (drop.length) frappe.show_alert({ message: __("Also removed: {0} (needs {1})", [drop.map((x) => x.name).join(", "), a.name]), indicator: "orange" });
		}
		keep();
		render();
	}

	function card(a, T) {
		const on = !!st.picked[a.id];
		const [l, h, saved] = hours(a);
		const need = (a.deps || []).filter((d) => !st.picked[d]).map((d) => byId(d).name)
			.concat(a.depsAny && !a.depsAny.some((d) => st.picked[d]) ? [__("one of: {0}", [a.depsAny.map((d) => byId(d).name).join(" " + __("or") + " ")])] : []);
		return `<label class="hsx-ao ${on ? "on" : ""}"><input type="checkbox" data-id="${a.id}" ${on ? "checked" : ""}><div style="min-width:0;flex:1">
			<div class="h"><b>${ui.esc(__(a.name))}</b><span>${l}–${h} h${saved ? ` <span style="color:var(--x-green)">${__("combined")}</span>` : ""}</span></div>
			<p>${ui.esc(__(a.desc))}</p>
			<div class="f"><span class="cost">${T.rate ? money(l * T.rate) + " – " + money(h * T.rate) : ""}</span><span>${ui.icon("info", "xs")} ${ui.esc(__(a.fees || "—"))}</span></div>
			${need.length ? `<div class="dep">${__("Needs {0} — added automatically when you tick this", [ui.esc(need.join(", "))])}</div>` : ""}</div></label>`;
	}

	function render() {
		const T = totals();
		const q = (st.q || "").toLowerCase();
		const list = cat.addons.filter((a) => (!st.cat || a.cat === st.cat) && (!q || (a.name + " " + a.desc).toLowerCase().includes(q)));
		const groups = cat.categories
			.filter(([k]) => !st.cat || k === st.cat)
			.map(([k, l]) => {
				const items = list.filter((a) => a.cat === k);
				return items.length ? `<div><h4 style="margin:4px 0 10px;font-size:14px">${ui.esc(__(l))}</h4><div class="hsx-ao-grid">${items.map((a) => card(a, T)).join("")}</div></div>` : "";
			})
			.join('<div style="height:16px"></div>');
		const summary = T.sel.length
			? `<div class="hsx-ao-sum">${T.sel.map((a) => { const [l, h] = hours(a); return `<div class="row"><span>${ui.esc(__(a.name))}</span><span>${l}–${h} h <a href="#" data-rm="${a.id}" title="${__("Remove")}">×</a></span></div>`; }).join("")}</div>
				<div class="hsx-ao-tot"><div><span>${__("Development time")}</span><b>${T.lo}–${T.hi} ${__("hours")}</b><span>${(weeks(T.lo) === weeks(T.hi) ? (weeks(T.hi) === 1 ? __("about 1 week at 30 h a week") : __("about {0} weeks at 30 h a week", [weeks(T.hi)])) : __("about {0}–{1} weeks at 30 h a week", [weeks(T.lo), weeks(T.hi)]))}</span></div>
				${T.rate ? `<div><span>${__("Estimated cost (excl. VAT)")}</span><b>${money(T.lo * T.rate)} – ${money(T.hi * T.rate)}</b><span>${__("at {0} per hour", [money(T.rate)])}${st.contingency ? " · " + __("incl. {0}% contingency", [st.contingency]) : ""}</span></div>` : ""}</div>
				<div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap"><button class="btn btn-sm btn-primary hsx-print">${ui.icon("printer")} ${__("Print / PDF estimate")}</button><button class="btn btn-sm btn-default hsx-clear">${__("Clear")}</button></div>
				<p class="text-muted small" style="margin:10px 0 0">${__("Third-party fees (Meta, SMS, maps, GPS subscriptions, gateways) are paid by the client directly to the provider and are not included.")}</p>`
			: `<div class="hsx-empty"><b>${__("Nothing selected yet")}</b><br>${__("Tick the add-ons the client is interested in — hours and cost add up here.")}</div>`;
		const settings = `<div class="hsx-form" style="grid-template-columns:1fr 1fr">
			<label>${__("Hourly rate (AED)")}<input type="number" min="0" step="10" class="hsx-rate" value="${rate()}" ${cat.can_rate ? "" : "readonly"}></label>
			<label>${__("Contingency")}<select class="hsx-cont" ${cat.can_rate ? "" : "disabled"}>${[[0, __("None")], [10, "10%"], [15, "15%"], [20, "20%"]].map(([x, l]) => `<option value="${x}" ${flt(st.contingency) === x ? "selected" : ""}>${l}</option>`).join("")}</select></label>
			<label style="grid-column:1/-1">${__("Client name (for the estimate)")}<input class="hsx-client" value="${ui.esc(st.client || "")}" placeholder="${__("e.g. Al Noor LLC")}"></label></div>
			${cat.can_rate ? "" : `<p class="text-muted small" style="margin:8px 0 0">${__("Only the Administrator or Managing Director can change the rate.")}</p>`}`;
		v.$body.html(`<div class="hsx-ao-wrap"><div>
				<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">${ui.seg("cat", [["", __("All")]].concat(cat.categories.map(([k, l]) => [k, __(l)])), st.cat)}
				<input class="form-control input-sm hsx-q" style="max-width:240px" placeholder="${__("Search add-ons")}" value="${ui.esc(st.q || "")}"></div>
				${groups || `<div class="hsx-empty">${__("No add-ons match.")}</div>`}</div>
			<div class="side">${ui.card(__("Your selection"), summary, { icon: "calculator" })}${ui.card(__("Pricing settings"), settings, { icon: "sliders-horizontal" })}</div></div>`);
	}

	function print_estimate() {
		const T = totals();
		const no = "EST-" + frappe.datetime.now_date().replace(/-/g, "") + "-" + String(Math.floor(Math.random() * 900) + 100);
		const rows = T.sel.map((a, i) => { const [l, h] = hours(a); return `<tr><td>${i + 1}</td><td><b>${ui.esc(__(a.name))}</b><br><small>${ui.esc(__(a.desc))}</small><br><small><i>${ui.esc(__(a.fees || ""))}</i></small></td><td style="text-align:right">${l}–${h} h</td>${T.rate ? `<td style="text-align:right">${format_number(l * T.rate, null, 0)} – ${format_number(h * T.rate, null, 0)}</td>` : ""}</tr>`; }).join("");
		const w = window.open("", "_blank");
		if (!w) return frappe.msgprint(__("Allow pop-ups to print the estimate."));
		w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${no}</title><style>body{font-family:system-ui,sans-serif;color:#0f1d3a;margin:32px}h1{font-size:20px;margin:0}table{width:100%;border-collapse:collapse;margin-top:16px;font-size:13px}th,td{border-bottom:1px solid #dfe5f1;padding:8px;vertical-align:top}th{text-align:left;background:#f4f6fb}tfoot td{font-weight:700}small{color:#5a6785}</style></head><body>
			<img src="/assets/hipersign_trading/images/hipersign-logo.png" style="height:36px"><h1>${__("Add-on estimate")} ${no}</h1>
			<p><b>${__("Prepared for")}:</b> ${ui.esc(st.client || "—")} · <b>${__("Date")}:</b> ${frappe.datetime.str_to_user(frappe.datetime.get_today())} · <b>${__("Valid for")}:</b> ${__("30 days")}</p>
			<table><thead><tr><th>#</th><th>${__("Add-on")}</th><th style="text-align:right">${__("Development time")}</th>${T.rate ? `<th style="text-align:right">${__("Estimated cost (AED, excl. VAT)")}</th>` : ""}</tr></thead><tbody>${rows}</tbody>
			<tfoot><tr><td></td><td>${__("Total")}${st.contingency ? " (" + __("incl. {0}% contingency", [st.contingency]) + ")" : ""}</td><td style="text-align:right">${T.lo}–${T.hi} h</td>${T.rate ? `<td style="text-align:right">${format_number(T.lo * T.rate, null, 0)} – ${format_number(T.hi * T.rate, null, 0)}</td>` : ""}</tr></tfoot></table>
			<p><small>${__("Third-party fees (Meta, SMS, maps, GPS subscriptions, gateways) are paid by the client directly to the provider and are not included.")}</small></p>
			<script>window.onload=()=>window.print()<\/script></body></html>`);
		w.document.close();
	}

	v.$body.on("change", ".hsx-ao input[type=checkbox]", function () {
		pick($(this).attr("data-id"), this.checked);
	});
	v.$body.on("click", "[data-rm]", function (e) {
		e.preventDefault();
		pick($(this).attr("data-rm"), false);
	});
	v.$body.on("click", "[data-seg=cat] button", function () {
		st.cat = $(this).attr("data-v");
		render();
	});
	v.$body.on("input", ".hsx-q", frappe.utils.debounce(function () {
		st.q = $(this).val();
		const pos = this.selectionStart;
		render();
		const el = v.$body.find(".hsx-q")[0];
		el.focus();
		el.setSelectionRange(pos, pos);
	}, 250));
	v.$body.on("change", ".hsx-rate", function () {
		st.rate = flt($(this).val());
		keep();
		render();
	});
	v.$body.on("change", ".hsx-cont", function () {
		st.contingency = cint($(this).val());
		keep();
		render();
	});
	v.$body.on("change", ".hsx-client", function () {
		st.client = $(this).val();
		keep();
	});
	v.$body.on("click", ".hsx-clear", () => {
		st.picked = {};
		keep();
		render();
	});
	v.$body.on("click", ".hsx-print", print_estimate);

	ui.loading(v.$body);
	frappe.xcall("hipersign_trading.api.centre.get_addons").then((d) => {
		cat = d;
		if (!cat.can_rate) st.rate = null;
		render();
	});
};
