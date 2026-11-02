// Hipersign ERP v1.8.0 (prototype p19) — Projects: the 26-step process stepper on the project panel and the Project Tracker's
// phase strip. Data from hipersign_trading.api.projects (states, flags) and api.module_prj.get_tracker.
frappe.provide("hipersign.projects");

(function () {
	const P = hipersign.projects;
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const LABEL = { done: __("Completed"), cur: __("In progress"), wait: __("Pending"), late: __("Red flag") };
	const TONE = { done: "green", cur: "blue", wait: "grey", late: "red" };
	const fd = (d) => (d ? frappe.datetime.str_to_user(String(d).slice(0, 10)) : "");
	const fds = (d) => (d ? moment(String(d).slice(0, 10)).format("DD MMM") : "");
	const info = (rows) => (rows || []).map(([a, b, tone]) => `<div><span>${esc(a)}</span><span class="${tone === "neg" ? "text-danger" : tone === "pos" ? "text-success" : ""}">${esc(b)}</span></div>`).join("");

	// the stepper: 6 phases of steps, one selected step's details below (what, who, documents, approval, trigger, facts, buttons)
	P.stepper_html = function (s, k) {
		const sel = s.sel;
		const done = s.states.filter((x) => x.st === "done").length;
		const strip = s.phases.map((ph, pi) => `<div class="hsp-ph"><div class="hsp-ph-h">${pi + 1} · ${esc(ph.name)}</div><div class="hsp-ph-s">${s.steps.slice(ph.a, ph.b).map((st, j) => {
			const i = ph.a + j, x = s.states[i];
			return `<button type="button" class="hsp-st st-${x.st} ${i === sel ? "sel" : ""}" data-ps="${i}" data-k="${k}" title="${esc(st.name)}"><span class="hsp-dot">${x.st === "done" ? "✓" : i + 1}</span>
				<span class="hsp-l">${esc(st.short)}</span>${x.st !== "wait" ? `<span class="hsp-p">${Math.round(x.pct || 0)}%</span>` : ""}</button>`;
		}).join("")}</div></div>`).join("");
		const st = s.steps[sel], x = s.states[sel];
		const btns = (s.buttons || {})[sel] || [];
		const detail = `<div class="hsp-detail"><div class="hsp-dh"><span class="hsp-dot st-${x.st}">${x.st === "done" ? "✓" : sel + 1}</span><div style="flex:1;min-width:0"><b>${sel + 1}. ${esc(st.name)}</b>
			<div class="small text-muted"><span class="hsx-pill ${TONE[x.st]}">${esc(LABEL[x.st])}</span> · ${Math.round(x.pct || 0)}%${x.date ? " · " + esc(fd(x.date)) : ""}${x.tag ? " · " + esc(x.tag) : ""}${x.by ? " · " + esc(x.by) : ""}</div></div>
			<span>${sel > 0 ? `<button type="button" class="btn btn-default btn-xs" data-ps="${sel - 1}" data-k="${k}">‹</button>` : ""} ${sel < s.steps.length - 1 ? `<button type="button" class="btn btn-default btn-xs" data-ps="${sel + 1}" data-k="${k}">›</button>` : ""}</span></div>
			<div class="hsp-kv"><div><span>${__("What happens")}</span><span>${esc(st.what)}</span></div><div><span>${__("Who")}</span><span>${esc(st.who)}</span></div>
			<div><span>${__("Documents")}</span><span>${esc(st.docs)}</span></div><div><span>${__("Approval")}</span><span>${esc(st.approval)}</span></div>
			<div><span>${__("Next trigger")}</span><span>${esc(st.next)}</span></div></div>
			${(x.info || []).length ? `<div class="hsp-facts">${info(x.info)}</div>` : ""}
			${btns.length ? `<div class="hp-btns" style="margin-top:10px">${btns.map((a, i) => `<button type="button" class="btn btn-xs ${a.kind === "primary" ? "btn-primary" : "btn-default"} hsp-act" data-k="${k}" data-sel="${sel}" data-i="${i}">${esc(a.label)}</button>`).join("")}</div>` : ""}</div>`;
		return `<div class="hsp-stepper"><div class="hsp-top"><b class="small">${__("{0} of {1} steps completed", [done, s.steps.length])}</b><span class="small text-muted">${__("Click a step to see what happens, who does it, documents and approval")}</span></div>
			<div class="hsp-strip">${strip}</div>${detail}</div>`;
	};

	// the tracker row: one card per project with the phases, each step's status, % and date, and a pop-up per step
	P.phase_html = function (steps, phases, states) {
		return `<div class="hsp-ptk">${phases.map((ph, pi) => {
			const xs = states.slice(ph.a, ph.b), dn = xs.filter((x) => x.st === "done").length, late = xs.some((x) => x.st === "late"), cur = xs.some((x) => x.st === "cur");
			const pct = xs.reduce((a, x) => a + (x.pct || 0), 0) / xs.length;
			const badge = late ? `<span class="hsx-pill red">${__("Attention")}</span>` : dn === xs.length ? `<span class="hsx-pill green">${__("Done")}</span>`
				: cur ? `<span class="hsx-pill blue">${Math.round(pct)}%</span>` : `<span class="hsx-pill grey">${__("Pending")}</span>`;
			return `<div class="hsp-ptk-ph ${late ? "late" : dn === xs.length ? "done" : cur ? "cur" : ""}"><div class="hsp-ptk-h"><b>${pi + 1} · ${esc(ph.name)}</b>${badge}</div>
				<div class="hsp-ptk-s" style="grid-template-columns:repeat(${ph.b - ph.a},minmax(0,1fr))">${steps.slice(ph.a, ph.b).map((st, j) => {
					const i = ph.a + j, x = states[i];
					return `<div class="hsp-stg st-${x.st}" tabindex="0"><span class="hsp-dot">${x.st === "done" ? "✓" : i + 1}</span><b>${esc(st.short)}</b>
						<span class="hsp-chip">${x.st === "wait" ? "—" : Math.round(x.pct || 0) + "%"}</span><span class="hsp-dt">${x.date ? esc(fds(x.date)) : "&nbsp;"}</span>
						<div class="hsp-pop ${j >= ph.b - ph.a - 2 && ph.b - ph.a > 2 ? "pr" : ""}"><div class="hsp-pop-h"><span class="hsp-dot">${i + 1}</span>${esc(st.name)} <span class="hsx-pill ${TONE[x.st]}">${esc(LABEL[x.st])}</span></div>
						<div class="hsp-pr"><span>${__("Who")}</span><span>${esc(st.who)}</span></div><div class="hsp-pr"><span>${__("Documents")}</span><span>${esc(st.docs)}</span></div>
						${x.tag ? `<div class="hsp-pr"><span>${__("Status")}</span><span>${esc(x.tag)}</span></div>` : ""}${(x.info || []).slice(0, 4).map(([a, b, t]) => `<div class="hsp-pr"><span>${esc(a)}</span><span class="${t === "neg" ? "text-danger" : ""}">${esc(b)}</span></div>`).join("")}</div></div>`;
				}).join("")}</div></div>`;
		}).join("")}</div>`;
	};

	// ---------------------------------------------------------------- Project Tracker page
	P.tracker = function (wrapper) {
		const ui = hipersign.ui;
		const v = ui.page(wrapper, { title: __("Project Tracker"), desc: __("Every project on one line through the 26 process steps — status, % and date per step, with red flags. Hover a step for who does it, the documents and the facts behind the status.") });
		v.page.set_title(__("Project Tracker"));
		v.$wrap.addClass("hsx-mod");
		const st = { filter: "open", q: "" };
		v.$actions.html(`<button class="btn btn-sm btn-primary hsp-new">${frappe.utils.icon("add", "sm")} ${__("New project")}</button>`);
		v.$actions.on("click", ".hsp-new", () => (hipersign.fm ? hipersign.fm.new("Project") : frappe.new_doc("Project")));
		const money = (x, cur) => format_number(x, null, 0);
		function card(p, r) {
			const cur = r.currency;
			const paid = p.rev ? Math.min(100, (p.collected / (p.rev * 1.05)) * 100) : 0, inv = p.rev ? Math.min(100 - paid, ((p.billed - p.collected) / (p.rev * 1.05)) * 100) : 0;
			return `<article class="hsp-trk"><div class="hsp-trk-h">
				<div class="f"><span>${__("Project")}</span><a class="hsp-open" data-name="${esc(p.name)}">${esc(p.name)}</a></div>
				<div class="f wide"><span>${__("Project · client")}</span><b>${esc(p.title)}</b><small>${esc(p.client || "")}${p.location ? " · " + esc(p.location) : ""}</small></div>
				<div class="f"><span>${__("Contract value")}</span><b>${money(p.rev)}</b><small>${esc(cur)} ${__("incl. variations")}</small></div>
				<div class="f"><span>${__("Complete")}</span><b>${Math.round(p.pct)}%</b><small>${__("Finish")} ${esc(fd(p.finish))}</small></div>
				<div class="f"><span>${__("Billed")}</span><b>${money(p.billed)}</b><small>${__("Certified")} ${esc(ui.money(p.certified, cur, true))}</small></div>
				<div class="f"><span>${__("Collected")}</span><b class="${p.collected ? "text-success" : ""}">${money(p.collected)}</b><small class="${p.overdue ? "text-danger" : ""}">${p.overdue ? esc(ui.money(p.overdue, cur, true)) + " " + __("overdue") : esc(ui.money(p.out, cur, true)) + " " + __("outstanding")}</small></div>
				<div class="f"><span>${__("Margin")}</span><b class="${p.margin < p.bud_margin - 1 ? "text-danger" : ""}">${p.margin.toFixed(1)}%</b><small>${__("budget")} ${p.bud_margin.toFixed(1)}%</small></div>
				<div class="f act"><span class="hsx-pill ${esc(p.tone)}">${esc(__(p.status))}</span>${p.flags.length ? `<span class="hsx-pill red">${__("{0} red flags", [p.flags.length])}</span>` : ""}</div></div>
				<div class="hsp-pay"><i style="width:${paid}%"></i><i class="inv" style="width:${Math.max(0, inv)}%"></i></div>
				${P.phase_html(r.steps, r.phases, p.states)}
				${p.flags.length ? `<div class="hsp-flags">${p.flags.map((f) => `<button class="hsp-tf" data-dt="${esc((f.open || ["Project", p.name])[0])}" data-name="${esc((f.open || ["Project", p.name])[1])}">${frappe.utils.icon("flag", "xs")} <b>${__("Step {0}", [f.step + 1])}</b> ${esc(f.text)}</button>`).join("")}</div>` : ""}
			</article>`;
		}
		function load() {
			frappe.xcall("hipersign_trading.api.module_prj.get_tracker", { filter: st.filter, q: st.q }).then((r) => {
				const segs = [["open", __("Open {0}", [r.counts.open])], ["Tender", __("Tender")], ["Mobilising", __("Mobilising")], ["Execution", __("Execution")], ["Handover", __("Handover")],
					["Closed", __("Closed")], ["flags", __("Red flags {0}", [r.counts.flags])], ["all", __("All")]];
				v.$body.html(`<div class="hsx-kpis">${r.kpis.map((k) => ui.kpi(Object.assign({}, k, { route: null }))).join("")}</div>
					<div class="hsx-chips hsp-filters"><input class="form-control hsx-q" placeholder="${__("Project, client or number")}" style="max-width:220px" value="${esc(st.q)}">
					${segs.map(([k, l]) => `<button data-f="${k}" class="${k === st.filter ? "on" : ""}">${esc(l)}</button>`).join("")}</div>
					<div class="hsp-legend">${[["done", __("Completed")], ["cur", __("In progress")], ["wait", __("Pending")], ["late", __("Red flag")]].map(([c, l]) => `<span><i class="st-${c}"></i>${esc(l)}</span>`).join("")}
					<span class="text-muted">· ${__("6 phases · 26 steps · hover or tap a step for details")}</span></div>
					${r.projects.length ? `<div class="hsp-list">${r.projects.map((p) => card(p, r)).join("")}</div>` : `<div class="hsx-card"><div class="hsx-empty"><b>${__("No projects match these filters")}</b> ${__("Clear a filter to see more projects.")}</div></div>`}`);
			});
		}
		v.$body.on("click", "[data-f]", function () { st.filter = $(this).attr("data-f"); load(); });
		v.$body.on("input", ".hsx-q", frappe.utils.debounce(function () { st.q = $(this).val(); load(); }, 350));
		const open = (dt, name) => (hipersign.panel && hipersign.panel.has(dt) ? hipersign.panel.open(dt, name) : frappe.set_route("Form", dt, name));
		v.$body.on("click", ".hsp-open", function () { open("Project", $(this).attr("data-name")); });
		v.$body.on("click", ".hsp-tf", function () { open($(this).attr("data-dt"), $(this).attr("data-name")); });
		$(document).on("hs-scope-change hp-changed", () => { if ($(wrapper).is(":visible")) load(); });
		wrapper.hs_reload = load;
		load();
	};
})();

// ---------------------------------------------------------------- the project panel: the stepper section and its buttons
(function () {
	const P = hipersign.projects;
	if (!hipersign.panel || hipersign.panel.__hsp) return;
	hipersign.panel.__hsp = true;
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const _section = hipersign.panel.section;
	hipersign.panel.section = function (s, k) {
		if (s.kind !== "stepper") return _section.apply(this, arguments);
		return `<div class="hp-card hsp-card" data-k="${k}"><div class="hp-ch"><h4>${esc(s.title)}</h4></div>${P.stepper_html(s, k)}</div>`;
	};
	const _bind = hipersign.panel.bind;
	hipersign.panel.bind = function ($p, p) {
		_bind.apply(this, arguments);
		$p.off("click.hsp");
		$p.on("click.hsp", ".hsp-card [data-ps]", function (e) {
			e.preventDefault();
			const k = +$(this).attr("data-k"), s = p.sections[k];
			s.sel = +$(this).attr("data-ps");
			$p.find(`.hsp-card[data-k="${k}"]`).replaceWith(hipersign.panel.section(s, k));
		});
		$p.on("click.hsp", ".hsp-act", function () {
			const s = p.sections[+$(this).attr("data-k")];
			hipersign.panel.run(p, ((s.buttons || {})[+$(this).attr("data-sel")] || [])[+$(this).attr("data-i")], $(this));
		});
	};
	hipersign.panel.clients.pj_new = function (p, args) {
		hipersign.panel.close();
		hipersign.fm ? hipersign.fm.new(args.doctype, args.values || {}) : frappe.new_doc(args.doctype, args.values || {});
	};
})();

// ---------------------------------------------------------------- the nine "New …" windows (Quick / Standard / Detailed), + New and the topbar
(function () {
	const C = hipersign.cm;
	if (!C || !C.DOCS) return;
	const L = (dt, filters, extra) => Object.assign({ dt, filters: filters || {} }, extra || {});
	const today = () => frappe.datetime.get_today();
	const plus = (n) => frappe.datetime.add_days(today(), n);
	const OPEN = L("Project", { hs_step: ["<", 26], hs_contract_value: [">", 0] });
	Object.assign(C.DOCS, {
		Project: { title: __("New project"), sub: __("A tender or an awarded contract — Quick: name, client and value; the stage, team, terms and dates follow from defaults"), fields: [
			{ f: "project_name", label: __("Project name"), req: 1, m: "q", w: 2, ph: __("e.g. Dubai Hills show apartment") },
			{ f: "customer", label: __("Client"), t: "select", src: L("Customer", { disabled: 0 }), req: 1, m: "q", blank: __("— choose —") },
			{ f: "hs_contract_value", label: __("Contract / tender value"), t: "number", req: 1, m: "q" },
			{ f: "_stage", label: __("Starts at"), t: "select", opts: [["0", __("1. Enquiry / tender received")], ["5", __("6. Contract signed (already awarded)")]], def: "0", m: "s" },
			{ f: "hs_consultant", label: __("Consultant"), m: "s" },
			{ f: "hs_location", label: __("Location"), m: "s", def: "Dubai" },
			{ f: "hs_retention_pct", label: __("Retention %"), t: "number", m: "s", def: 10 },
			{ f: "hs_advance_pct", label: __("Advance %"), t: "number", m: "s", def: 10 },
			{ f: "expected_start_date", label: __("Start on site"), t: "date", m: "s", def: () => plus(30) },
			{ f: "expected_end_date", label: __("Completion date"), t: "date", m: "s", def: () => plus(210) },
			{ f: "hs_project_manager", label: __("Project manager"), m: "d" },
			{ f: "hs_quantity_surveyor", label: __("Quantity surveyor"), m: "d" },
			{ f: "hs_site_engineer", label: __("Site engineer"), m: "d" },
			{ f: "hs_dlp_months", label: __("Defects liability (months)"), t: "number", m: "d", def: 12 },
			{ f: "hs_tender_due", label: __("Tender due date"), t: "date", m: "d", def: () => plus(14) },
			{ f: "company", label: __("Company"), t: "select", src: L("Company", { is_group: 0 }), m: "d", blank: __("— my company —") },
			{ f: "hs_payment_terms", label: __("Payment terms"), t: "textarea", m: "d", w: 2, def: __("Monthly progress payments on consultant certificates, 30 days · advance against APG · retention released after the DLP") },
		], actions: [{ label: __("Create project"), action: "save", primary: 1 }] },
		"Project BOQ": { title: __("New BOQ"), sub: __("BOQ lines for a project or tender — description, unit, quantity and rate; added to the project's BOQ"), fields: [
			{ f: "project", label: __("Project / tender"), t: "select", src: OPEN, req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "revision", label: __("Revision"), t: "number", m: "s", def: 0 },
			{ f: "_section", label: __("Section"), m: "s", def: __("E — Additional works") },
			{ f: "target_margin", label: __("Target margin %"), t: "number", m: "d", def: 17 },
			{ f: "notes", label: __("Notes / exclusions"), t: "textarea", m: "d", w: 2, def: __("Excludes authority fees and loose furniture.") },
		], rows: { cols: [{ f: "description", label: __("Description"), w: 3 }, { f: "unit", label: __("Unit") }, { f: "qty", label: __("Qty"), t: "number" }, { f: "rate", label: __("Rate"), t: "number" }],
			n: 2, net: ["qty", "rate"], total: __("BOQ lines") }, actions: [{ label: __("Add to BOQ"), action: "save", primary: 1 }] },
		Task: { title: __("New task"), sub: __("A programme task on a project, with owner and dates"), fields: [
			{ f: "project", label: __("Project"), t: "select", src: OPEN, req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "subject", label: __("Task"), req: 1, m: "q", w: 2 },
			{ f: "exp_start_date", label: __("Start"), t: "date", m: "s", def: today },
			{ f: "exp_end_date", label: __("End"), t: "date", m: "s", def: () => plus(30) },
			{ f: "hs_task_owner", label: __("Owner"), m: "s" },
			{ f: "hs_boq_item", label: __("BOQ line"), m: "d", ph: "A1" },
			{ f: "progress", label: __("% done"), t: "number", m: "d", def: 0 },
		], actions: [{ label: __("Save"), action: "save", primary: 1 }] },
		Timesheet: { title: __("New timesheet"), sub: __("Hours of one employee on a project — site work and overtime at 125%; approved by the project manager"), fields: [
			{ f: "employee", label: __("Employee"), t: "select", src: L("Employee", { status: "Active" }), req: 1, m: "q", blank: __("— choose —") },
			{ f: "_project", label: __("Project"), t: "select", src: OPEN, req: 1, m: "q", blank: __("— choose —") },
			{ f: "_hours", label: __("Hours"), t: "number", m: "q", def: 8 },
			{ f: "_date", label: __("Date"), t: "date", m: "s", def: today },
			{ f: "_task", label: __("Task"), t: "select", src: L("Task", { status: ["not in", ["Completed", "Cancelled"]] }), m: "s", blank: "—" },
			{ f: "_ot", label: __("Overtime hours"), t: "number", m: "d", def: 0 },
			{ f: "note", label: __("Work done"), t: "textarea", m: "d", w: 2 },
		], actions: [{ label: __("Submit for approval"), action: "save", primary: 1 }] },
		"Progress Certificate": { title: __("New progress certificate"), sub: __("The measurement on the BOQ lines becomes the certificate: work this period, less advance recovery and retention, plus VAT"), fields: [
			{ f: "project", label: __("Project"), t: "select", src: L("Project", { hs_step: ["between", [10, 25]] }), req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "period_to", label: __("Period to"), t: "date", m: "q", def: () => frappe.datetime.month_end() },
			{ f: "basis", label: __("Measured by"), t: "select", opts: "@meta", m: "s", def: "% complete" },
			{ f: "consultant", label: __("Consultant"), m: "s", ph: __("From the project") },
			{ f: "retention_pct", label: __("Retention % (contract default)"), t: "number", m: "d" },
			{ f: "advance_pct", label: __("Advance recovery % (contract default)"), t: "number", m: "d" },
			{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
		], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Send to consultant"), action: "submit", primary: 1 }] },
		"Variation Order": { title: __("New variation"), sub: __("A change priced for the client — negative for an omission; approved variations raise the contract"), fields: [
			{ f: "project", label: __("Project"), t: "select", src: OPEN, req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "title", label: __("Description"), req: 1, m: "q", w: 2 },
			{ f: "amount", label: __("Amount"), t: "number", req: 1, m: "q", hint: __("Negative for an omission") },
			{ f: "reason", label: __("Reason"), t: "select", opts: "@meta", m: "s", def: "Client instruction" },
			{ f: "instruction_ref", label: __("Instruction reference"), m: "s", def: "SI-" },
			{ f: "time_impact_days", label: __("Time impact (days)"), t: "number", m: "d", def: 0 },
			{ f: "notes", label: __("Build-up / notes"), t: "textarea", m: "d", w: 2 },
		], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Send to client"), action: "submit", primary: 1 }] },
		"Subcontract Order": { title: __("New subcontract order"), sub: __("MEP, joinery and other packages — with retention and payment terms"), fields: [
			{ f: "project", label: __("Project"), t: "select", src: OPEN, req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "supplier", label: __("Subcontractor"), t: "select", src: L("Supplier", { disabled: 0 }), req: 1, m: "q", blank: __("— choose —") },
			{ f: "package", label: __("Package / scope"), req: 1, m: "q" },
			{ f: "order_value", label: __("Order value (excl. VAT)"), t: "number", req: 1, m: "q" },
			{ f: "retention_pct", label: __("Retention %"), t: "number", m: "s", def: 10 },
			{ f: "advance_pct", label: __("Advance %"), t: "number", m: "s", def: 0 },
			{ f: "start_date", label: __("Start"), t: "date", m: "d", def: () => plus(7) },
			{ f: "terms", label: __("Payment terms"), t: "textarea", m: "d", w: 2, def: __("Monthly claims, certified by our QS within 7 days, paid 30 days after certification · 10% retention") },
		], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Send for signature"), action: "submit", primary: 1 }] },
		"Material Request:project": { doctype: "Material Request", preset: { _site: 1 }, title: __("Material request to site"),
			sub: __("Against a BOQ line — checked against what is left on the line; over it, the Managing Director approves"), fields: [
			{ f: "_boq", label: __("Project · BOQ line"), t: "select", src: L("Project BOQ", {}, { query: "boq_lines" }), req: 1, m: "q", w: 2, blank: __("— choose —") },
			{ f: "item_code", label: __("Material"), t: "select", src: L("Item", { disabled: 0, is_stock_item: 1, is_purchase_item: 1 }), req: 1, m: "q", blank: __("— choose —") },
			{ f: "qty", label: __("Quantity"), t: "number", req: 1, m: "q" },
			{ f: "schedule_date", label: __("Needed on site"), t: "date", m: "s", def: () => plus(10) },
			{ f: "_from", label: __("Deliver from"), t: "select", opts: [["Supplier direct", __("Supplier direct")], ["Main store", __("Main store")]], m: "d", def: "Supplier direct" },
			{ f: "_note", label: __("Notes"), t: "textarea", m: "d", w: 2 },
		], actions: [{ label: __("Send for approval"), action: "save", primary: 1 }] },
		"Stock Entry:site": { doctype: "Stock Entry", preset: { _site: 1 }, title: __("Site transfer"), sub: __("From the main store (or another site) to a project's site store — charged to the project"), fields: [
			{ f: "from_warehouse", label: __("From"), t: "select", src: L("Warehouse", { is_group: 0 }), req: 1, m: "q" },
			{ f: "project", label: __("To project"), t: "select", src: OPEN, req: 1, m: "q", blank: __("— choose —") },
			{ f: "item_code", label: __("Material"), t: "select", src: L("Item", { disabled: 0, is_stock_item: 1 }), req: 1, m: "q", blank: __("— choose —") },
			{ f: "qty", label: __("Quantity"), t: "number", req: 1, m: "q" },
			{ f: "_vehicle", label: __("Vehicle / driver"), m: "d" },
			{ f: "posting_date", label: __("Date"), t: "date", m: "d", def: today },
		], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Transfer"), action: "submit", primary: 1 }] },
	});
	["Project", "Project BOQ", "Task", "Timesheet", "Progress Certificate", "Variation Order", "Subcontract Order"].forEach((dt) => {
		if (hipersign.fm && !hipersign.fm.COVERED.includes(dt)) hipersign.fm.COVERED.push(dt);
	});

	// + New (topbar and the create page): the Projects group when the module is on
	if (hipersign.create && hipersign.create.GROUPS && !hipersign.create.__hsp) {
		hipersign.create.__hsp = true;
		const _groups = hipersign.create.GROUPS;
		hipersign.create.GROUPS = () => {
			const g = _groups();
			const at = g.findIndex(([l]) => l === __("Supplier bills"));
			g.splice(at < 0 ? g.length : at, 0, [__("Projects"), [
				[__("Project"), "projects", { dt: "Project", feature: "projects" }],
				[__("BOQ"), "list", { dt: "Project BOQ", feature: "projects" }],
				[__("Task"), "check", { dt: "Task", feature: "projects" }],
				[__("Timesheet"), "timer", { dt: "Timesheet", feature: "projects" }],
				[__("Progress certificate"), "file", { dt: "Progress Certificate", feature: "projects" }],
				[__("Variation"), "edit", { dt: "Variation Order", feature: "projects" }],
				[__("Subcontract order"), "file", { dt: "Subcontract Order", feature: "projects" }],
				[__("Material request to site"), "stock", { dt: "Material Request", win: "Material Request:project", feature: "projects" }],
				[__("Site transfer"), "share", { dt: "Stock Entry", win: "Stock Entry:site", feature: "projects" }],
			]]);
			return g;
		};
		const _open = hipersign.create.open;
		hipersign.create.open = function (a, mode) {
			if (a && a.win && C.DOCS[a.win]) return C.doc(a.win, Object.assign({}, a.values || {}));
			return _open.apply(this, arguments);
		};
	}
})();

// the ERPNext lists of the Projects records open their page (the page's menu keeps the classic list)
if (hipersign.nav && hipersign.nav.LIST_PAGE) Object.assign(hipersign.nav.LIST_PAGE, {
	"Progress Certificate": ["hipersign-billing", "ipc"], "Variation Order": ["hipersign-billing", "vo"], "Project BOQ": ["hipersign-boq", "tend"],
	"Subcontract Order": ["hipersign-subcontract", "sco"], "Subcontract Claim": ["hipersign-subcontract", "claims"], "Back Charge": ["hipersign-subcontract", "bc"],
	"Daily Site Report": ["hipersign-timesheets", "dsr"],
});
