// Hipersign ERP v1.8.0 (prototype p19) — Manufacturing: the Shop floor (tablet view of the job cards), the Production
// Tracker (every sales order through the 22 steps), the panel buttons and the seven "New …" windows. Data from
// hipersign_trading.api.module_mfg (get_floor, get_tracker); every button runs hipersign_trading.api.manufacturing.act.
frappe.provide("hipersign.mfg");

(function () {
	const MF = hipersign.mfg;
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const ACT = "hipersign_trading.api.manufacturing.act";
	const fd = (d) => (d ? frappe.datetime.str_to_user(String(d).slice(0, 10)) : "");
	const fds = (d) => (d ? moment(String(d).slice(0, 10)).format("DD MMM") : "");
	const nf = (v) => format_number(v || 0, null, 0);
	const pr = (dt, name, fmt) => `/printview?doctype=${encodeURIComponent(dt)}&name=${encodeURIComponent(name)}&format=${encodeURIComponent(fmt)}`;
	MF.run = (action, name, args) => frappe.xcall(ACT, { action, name, args: args || {} });
	const open = (dt, name) => (hipersign.panel && hipersign.panel.has(dt) ? hipersign.panel.open(dt, name) : frappe.set_route("Form", dt, name));
	MF.new = (key, values) => (hipersign.cm && hipersign.cm.DOCS && hipersign.cm.DOCS[key] ? hipersign.cm.doc(key, values || {}) : frappe.new_doc(key.split(":")[0], values || {}));

	// ---------------------------------------------------------------- Shop floor — tablet view
	MF.floor = function (wrapper) {
		const ui = hipersign.ui;
		const v = ui.page(wrapper, { band: "shopfloor", title: __("Shop floor"), desc: __("Tablet view for the line: job cards by workstation — start and stop, quantity, scrap and operator. Every tap updates the work order, the tracker and the cost.") });
		v.page.set_title(__("Shop floor"));
		v.$wrap.addClass("hsx-mod hsf");
		const st = { ws: "all", data: null };
		v.$actions.html(`<button class="btn btn-sm btn-default hsf-ticket">${frappe.utils.icon("printer", "sm")} ${__("Job ticket")}</button>
			<button class="btn btn-sm btn-primary hsf-new">${frappe.utils.icon("add", "sm")} ${__("New job card")}</button>`);
		v.$actions.on("click", ".hsf-new", () => MF.new("Job Card"));
		v.$actions.on("click", ".hsf-ticket", () => { const w = (st.data || {}).ticket_wo; if (w) window.open(frappe.urllib.get_full_url(pr("Work Order", w, "Hipersign Job Ticket"))); });
		const tone = { Completed: "done", "Work in progress": "cur", "On hold": "late", Open: "wait" };
		const pill = { Completed: "green", "Work in progress": "blue", "On hold": "red", Open: "grey" };
		function card(c, d) {
			const hrs = `${Math.floor(c.mins / 60)}h ${String(c.mins % 60).padStart(2, "0")}`;
			const ops = (d.operators || []).map((o) => `<option value="${esc(o.name)}" ${o.name === c.operator ? "selected" : ""}>${esc(o.employee_name)}</option>`).join("");
			const w = d.can_write && c.live;
			return `<div class="hsf-card st-${tone[c.state] || "wait"}" data-jc="${esc(c.jc)}">
				<div class="hsf-h"><span class="hsx-code">${esc(c.jc)}</span><span class="hsx-pill ${pill[c.state] || "grey"}">${esc(__(c.state))}</span><span class="text-muted small hsf-ws">${esc(c.ws_name)}</span></div>
				<div class="hsf-t"><b>${__("Op")} ${esc(c.op)} · ${esc(c.op_name)}</b><span class="text-muted small"><a class="hsf-wo" data-wo="${esc(c.wo)}">${esc(c.wo)}</a> · ${esc(c.item)}${c.late ? ` <span class="hsx-pill red">${__("Late")}</span>` : ""}</span></div>
				<div class="hsf-num"><div><span>${__("Done")}</span><b>${nf(c.done)}</b></div><div><span>${__("Planned")}</span><b>${nf(c.planned)}</b></div>
					<div><span>${__("Scrap")}</span><b class="${c.scrap ? "text-danger" : ""}">${nf(c.scrap)}</b>${flt(c.loss) > flt(c.scrap) ? `<small class="text-muted" title="${esc(__("The job card's process loss counts the scrap of the operations before this one too"))}">${__("+{0} earlier · loss {1}", [nf(c.loss - c.scrap), nf(c.loss)])}</small>` : ""}</div><div><span>${__("Time")}</span><b>${hrs}</b></div></div>
				<div class="hsf-bar"><span class="hp-bar"><span style="width:${Math.min(100, c.pct)}%"></span></span><b>${Math.round(c.pct)}%</b></div>
				<div class="hsf-row"><select class="form-control hsf-op" ${w ? "" : "disabled"} aria-label="${__("Operator")}"><option value="">${__("— operator —")}</option>${ops}</select>
					${c.started && c.state === "Work in progress" ? `<span class="small text-muted">${frappe.utils.icon("clock", "xs")} ${__("started {0}", [esc(c.started)])}</span>` : ""}</div>
				${w ? `<div class="hsf-btns">${c.state === "Work in progress" ? `<button class="btn btn-default" data-a="jc_pause">${frappe.utils.icon("clock", "sm")} ${__("Pause")}</button>`
					: `<button class="btn btn-success" data-a="jc_start">→ ${__("Start")}</button>`}
					<button class="btn btn-default" data-a="jc_qty" data-n="10" ${c.paused ? "disabled" : ""}>+10</button><button class="btn btn-default" data-a="jc_qty" data-n="50" ${c.paused ? "disabled" : ""}>+50</button>
					<button class="btn btn-default hsf-scrap" data-a="jc_scrap" ${c.paused ? "disabled" : ""}>${__("Scrap +1")}</button>
					<button class="btn btn-primary" data-a="jc_done">${frappe.utils.icon("check", "sm")} ${__("Complete")}</button></div>
					${c.paused ? `<div class="small text-muted hsf-paused">${__("Paused — tap Start to resume before recording quantities or scrap.")}</div>` : ""}` : ""}</div>`;
		}
		function draw() {
			const d = st.data;
			const segs = [{ id: "all", name: __("All workstations") }].concat(d.workstations);
			const cards = d.cards.filter((c) => st.ws === "all" || c.ws === st.ws);
			v.$body.html(`<div class="hsx-chips hsf-seg">${segs.map((s) => `<button data-ws="${esc(s.id)}" class="${s.id === st.ws ? "on" : ""}">${esc(s.name)}</button>`).join("")}</div>
				${cards.length ? `<div class="hsf-grid">${cards.map((c) => card(c, d)).join("")}</div>` : `<div class="hsx-card"><div class="hsx-empty"><b>${__("No job cards on this workstation")}</b> ${__("Pick another workstation.")}</div></div>`}`);
		}
		function load() { return frappe.xcall("hipersign_trading.api.module_mfg.get_floor", {}).then((d) => { st.data = d; draw(); }); }
		v.$body.on("click", "[data-ws]", function () { st.ws = $(this).attr("data-ws"); draw(); });
		v.$body.on("click", ".hsf-wo", function (e) { e.stopPropagation(); open("Work Order", $(this).attr("data-wo")); });
		v.$body.on("click", ".hsf-btns [data-a]", function () {
			const $b = $(this), jc = $b.closest("[data-jc]").attr("data-jc"), a = $b.attr("data-a");
			const go = () => { $b.closest(".hsf-btns").find("button").prop("disabled", true);
				MF.run(a, jc, { n: +$b.attr("data-n") || 1, employee: $b.closest("[data-jc]").find(".hsf-op").val() || undefined })
					.then((r) => { frappe.show_alert({ message: (r && r.message) || __("Done"), indicator: "green" }, 5); load(); }).catch(() => load()); };
			return a === "jc_done" ? frappe.confirm(__("Complete {0}? The remaining units are recorded as done, less the scrap.", [jc]), go) : go();
		});
		v.$body.on("change", ".hsf-op", function () {
			const jc = $(this).closest("[data-jc]").attr("data-jc");
			MF.run("jc_operator", jc, { employee: $(this).val() }).then((r) => frappe.show_alert({ message: r.message, indicator: "green" }, 4));
		});
		$(document).on("hs-scope-change hp-changed", () => { if ($(wrapper).is(":visible")) load(); });
		wrapper.hs_reload = load;
		load();
	};

	// ---------------------------------------------------------------- Production Tracker
	MF.tracker = function (wrapper) {
		const ui = hipersign.ui;
		const v = ui.page(wrapper, { band: "prod_tracker", title: __("Production Tracker"), desc: __("Every sales order and its work order through the 22 manufacturing steps — status, % and date per step, with red flags. Hover a step for who does it and the facts behind it.") });
		v.page.set_title(__("Production Tracker"));
		v.$wrap.addClass("hsx-mod");
		const st = { filter: "open", q: "" };
		v.$actions.html(`<button class="btn btn-sm btn-primary hsm-new">${frappe.utils.icon("add", "sm")} ${__("New work order")}</button>`);
		v.$actions.on("click", ".hsm-new", () => MF.new("Work Order"));
		function card(o, r) {
			const P = hipersign.projects;
			return `<article class="hsp-trk"><div class="hsp-trk-h">
				<div class="f"><span>${__("Sales order")}</span><a class="hsm-open" data-dt="Sales Order" data-name="${esc(o.name)}">${esc(o.name)}</a></div>
				<div class="f wide"><span>${__("Customer · product")}</span><b>${esc(o.customer)}</b><small>${esc(o.city || "")}${o.city ? " · " : ""}${nf(o.qty)} × ${esc(o.item)}</small></div>
				<div class="f"><span>${__("Work order")}</span>${o.wo ? `<a class="hsm-open" data-dt="Work Order" data-name="${esc(o.wo)}">${esc(o.wo)}</a><small>${esc(o.wo_state || "")}</small>` : `<b>—</b><small>${__("Forecast")}</small>`}</div>
				<div class="f"><span>${__("Due")}</span><b class="${o.late ? "text-danger" : ""}">${esc(fd(o.due))}</b><small>${__("Ordered {0}", [esc(fds(o.date))])}</small></div>
				<div class="f"><span>${__("Produced")}</span><b>${nf(o.done)}</b><small>${o.wo ? `${Math.round(o.pct)}% · ${__("{0} scrap", [nf(o.scrap)])}` : "—"}</small></div>
				<div class="f"><span>${__("Order value")}</span><b>${format_number(o.value, null, 2)}</b><small>${esc(r.currency)}${o.export ? " · " + __("export 0% VAT") : " " + __("excl. VAT")}</small></div>
				<div class="f act"><span class="hsx-pill ${esc(o.tone)}">${esc(o.status)}</span>${o.flags.length ? `<span class="hsx-pill red">${__("{0} red flags", [o.flags.length])}</span>` : ""}
					${o.wo ? `<a class="btn btn-xs btn-default" target="_blank" title="${__("Job ticket")}" href="${pr("Work Order", o.wo, "Hipersign Job Ticket")}">${frappe.utils.icon("printer", "xs")}</a>` : ""}</div></div>
				<div class="hsp-pay"><i style="width:${Math.min(100, o.pct)}%"></i></div>
				${P.phase_html(r.steps, r.phases, o.states)}
				${o.flags.length ? `<div class="hsp-flags">${o.flags.map((f) => `<button class="hsp-tf hsm-open" data-dt="${esc((f.open || ["Sales Order", o.name])[0])}" data-name="${esc((f.open || ["Sales Order", o.name])[1])}">${frappe.utils.icon("flag", "xs")} <b>${__("Step {0}", [f.step + 1])}</b> ${esc(f.text)}</button>`).join("")}</div>` : ""}
			</article>`;
		}
		function load() {
			frappe.xcall("hipersign_trading.api.module_mfg.get_tracker", { filter: st.filter, q: st.q }).then((r) => {
				const segs = [["open", __("Open {0}", [r.counts.open])], ["mat", __("Planning & materials")], ["prod", __("In production")], ["ship", __("Finish & ship")],
					["flags", __("Red flags {0}", [r.counts.flags])], ["done", __("Closed")], ["all", __("All")]];
				v.$body.html(`<div class="hsx-kpis">${r.kpis.map((k) => ui.kpi(Object.assign({}, k, { route: null }))).join("")}</div>
					<div class="hsx-chips hsp-filters"><input class="form-control hsx-q" placeholder="${__("Order, customer, product or work order")}" style="max-width:240px" value="${esc(st.q)}">
					${segs.map(([k, l]) => `<button data-f="${k}" class="${k === st.filter ? "on" : ""}">${esc(l)}</button>`).join("")}</div>
					<div class="hsp-legend">${[["done", __("Completed")], ["cur", __("In progress")], ["wait", __("Pending")], ["late", __("Red flag")]].map(([c, l]) => `<span><i class="st-${c}"></i>${esc(l)}</span>`).join("")}
					<span class="text-muted">· ${__("5 phases · 22 steps · hover or tap a step for details")}</span></div>
					${r.orders.length ? `<div class="hsp-list">${r.orders.map((o) => card(o, r)).join("")}</div>` : `<div class="hsx-card"><div class="hsx-empty"><b>${__("No orders match")}</b> ${__("Choose another filter.")}</div></div>`}`);
			});
		}
		v.$body.on("click", "[data-f]", function () { st.filter = $(this).attr("data-f"); load(); });
		v.$body.on("input", ".hsx-q", frappe.utils.debounce(function () { st.q = $(this).val(); load(); }, 350));
		v.$body.on("click", ".hsm-open", function () { open($(this).attr("data-dt"), $(this).attr("data-name")); });
		$(document).on("hs-scope-change hp-changed", () => { if ($(wrapper).is(":visible")) load(); });
		wrapper.hs_reload = load;
		load();
	};
})();

// ---------------------------------------------------------------- panels: the Manufacturing records, the window and open buttons
(function () {
	if (!hipersign.panel || hipersign.panel.__hsm) return;
	hipersign.panel.__hsm = true;
	["Work Order", "BOM", "Job Card", "Quality Inspection", "Production Plan"].forEach((dt) => { if (!hipersign.panel.TYPES.includes(dt)) hipersign.panel.TYPES.push(dt); });
	hipersign.panel.clients.mf_new = function (p, args) {
		hipersign.panel.close();
		hipersign.mfg.new(args.key, args.values || {});
	};
	hipersign.panel.clients.mf_open = function (p, args) { hipersign.panel.open(args.doctype, args.name, { keep: true }); };
})();

// ---------------------------------------------------------------- the seven "New …" windows (Quick / Standard / Detailed), + New and the lists
(function () {
	const C = hipersign.cm;
	if (!C || !C.DOCS) return;
	const L = (dt, filters, extra) => Object.assign({ dt, filters: filters || {} }, extra || {});
	const Q = (dt, what) => L(dt, {}, { query: "mfg:" + what });
	const today = () => frappe.datetime.get_today();
	const plus = (n) => frappe.datetime.add_days(today(), n);
	const yymm = () => moment().format("YYMM");
	Object.assign(C.DOCS, {
		BOM: { title: __("New BOM"), sub: __("Quick: product and components with quantities — routing copied from the active version. Standard adds the change note; Detailed the routing."),
			fields: [
				{ f: "item", label: __("Product"), t: "select", src: Q("BOM", "products"), req: 1, m: "q", w: 2, blank: __("— choose —"), fill: "mfg_bom" },
				{ f: "hs_change_note", label: __("Change note"), m: "s", w: 2, ph: __("e.g. alternate diffuser from a second supplier") },
				{ f: "routing", label: __("Routing"), t: "select", src: L("Routing"), m: "d", w: 2, blank: __("— copy the routing of the active version —") },
			], rows: { cols: [{ f: "item_code", label: __("Component"), t: "select", src: Q("Item", "components"), w: 4 }, { f: "qty", label: __("Qty per unit"), t: "number" }], n: 4 },
			actions: [{ label: __("Save draft"), action: "save" }, { label: __("Make active"), action: "submit", primary: 1 }] },
		"Work Order": { title: __("New work order"), sub: __("Quick: product and quantity — BOM, routing, workstations and due date from defaults. Standard adds the sales order and dates; Detailed the BOM version and warehouse."),
			fields: [
				{ f: "production_item", label: __("Product"), t: "select", src: Q("Work Order", "products"), req: 1, m: "q", w: 2, blank: __("— choose —") },
				{ f: "qty", label: __("Quantity"), t: "number", req: 1, m: "q", def: 500 },
				{ f: "sales_order", label: __("Sales order"), t: "select", src: Q("Sales Order", "orders"), m: "s", w: 2, blank: __("— make to stock —") },
				{ f: "planned_start_date", label: __("Start"), t: "date", m: "s", def: () => plus(1) },
				{ f: "expected_delivery_date", label: __("Due"), t: "date", m: "s", def: () => plus(8) },
				{ f: "bom_no", label: __("BOM"), t: "select", src: L("BOM", { is_active: 1, docstatus: 1, company: ["is", "set"] }), m: "d", blank: __("— the active default —") },
				{ f: "fg_warehouse", label: __("Finished goods warehouse"), t: "select", src: Q("Warehouse", "warehouses"), m: "d", blank: __("— finished goods store —") },
			], actions: [{ label: __("Save draft"), action: "save" }, { label: __("Release"), action: "submit", primary: 1 }] },
		"Production Plan": { title: __("New production plan"), sub: __("Quick: pick the sales orders — MRP proposes work orders and material requests. Standard adds the horizon and warehouse; Detailed forecast, safety stock and sub-assemblies."),
			fields: [
				{ f: "_orders", label: __("Sales orders"), t: "select", src: Q("Sales Order", "orders"), m: "q", w: 2, blank: __("All open sales orders without a work order") },
				{ f: "to_date", label: __("Plan up to"), t: "date", m: "s", def: () => plus(30) },
				{ f: "for_warehouse", label: __("Raw material warehouse"), t: "select", src: Q("Warehouse", "warehouses"), m: "s", blank: __("— components store —") },
				{ f: "_fc", label: __("Include forecast orders"), t: "check", m: "d", def: 1 },
				{ f: "_ss", label: __("Keep safety stock of components"), t: "check", m: "d", def: 1 },
				{ f: "_sub", label: __("Also plan sub-assemblies (drivers)"), t: "check", m: "d", def: 1 },
			], actions: [{ label: __("Run MRP and plan"), action: "save", primary: 1 }] },
		"Job Card": { title: __("New job card"), sub: __("Quick: work order and operation — workstation from the routing. Standard adds the operator; Detailed the planned start and remarks."),
			fields: [
				{ f: "work_order", label: __("Work order"), t: "select", src: Q("Work Order", "wo_released"), req: 1, m: "q", w: 2, blank: __("— choose —"), fill: "mfg_wo_ops" },
				// v1.8.4: only the operations of the chosen work order's routing (filled when the work order is picked)
				{ f: "operation", label: __("Operation"), t: "select", opts: [], req: 1, m: "q", w: 2, blank: __("— pick the work order first —") },
				{ f: "hs_operator", label: __("Operator"), t: "select", src: Q("Employee", "operators"), m: "s", blank: "—" },
				{ f: "_qty", label: __("Quantity (blank: what is left)"), t: "number", m: "s" },
				{ f: "_start", label: __("Planned start"), m: "d", def: "07:30" },
				{ f: "remarks", label: __("Remarks"), t: "textarea", m: "d", w: 2 },
			], actions: [{ label: __("Create job card"), action: "save", primary: 1 }] },
		"Quality Inspection": { title: __("New quality inspection"), sub: __("Quick: type, reference, sample size and fails — the result follows AQL. Standard adds the item and lot; Detailed the defect and rework."),
			fields: [
				{ f: "hs_qc_stage", label: __("Inspection type"), t: "select", opts: [["Incoming", __("Incoming")], ["In-process", __("In-process")], ["Final", __("Final")]], m: "q", def: "In-process", redraw: 1 },
				{ f: "_receipt", label: __("Goods receipt"), t: "select", src: Q("Purchase Receipt", "receipts"), m: "q", blank: __("— choose —"), show: (v) => v.hs_qc_stage === "Incoming" },
				{ f: "hs_work_order", label: __("Work order"), t: "select", src: Q("Work Order", "wo_released"), m: "q", blank: __("— choose —"), show: (v) => v.hs_qc_stage !== "Incoming" },
				{ f: "_op", label: __("Operation"), t: "select", opts: [["10", "10"], ["20", "20"], ["30", "30"], ["40", "40"], ["50", "50"]], m: "q", def: "30", show: (v) => v.hs_qc_stage === "In-process" },
				{ f: "sample_size", label: __("Sample size"), t: "number", m: "q", def: 50 },
				{ f: "hs_fails", label: __("Fails"), t: "number", m: "q", def: 0 },
				{ f: "item_code", label: __("Item"), t: "select", src: Q("Item", "components"), m: "s", blank: __("— from the reference —") },
				{ f: "hs_lot_qty", label: __("Lot / batch quantity"), t: "number", m: "s" },
				{ f: "remarks", label: __("Defect / remarks"), m: "d", w: 2 },
				{ f: "hs_rework_qty", label: __("Units to rework"), t: "number", m: "d", def: 0 },
				{ f: "hs_rejected_qty", label: __("Units rejected"), t: "number", m: "d", def: 0 },
			], actions: [{ label: __("Save as pending"), action: "save" }, { label: __("Record result"), action: "submit", primary: 1 }] },
		"Stock Entry:manufacture": { doctype: "Stock Entry", preset: { _mfg: "manufacture" }, title: __("Manufacture entry"),
			sub: __("Quick: work order and quantity made — WIP is consumed and finished goods received at material + labour and overhead. Standard adds the batch and date; Detailed the serial range and warehouse."),
			fields: [
				{ f: "work_order", label: __("Work order"), t: "select", src: Q("Work Order", "wo_manufacture"), req: 1, m: "q", w: 2, blank: __("— choose —") },
				{ f: "_qty", label: __("Quantity made (good units)"), t: "number", m: "q", hint: __("Blank: everything still to receive (the scrap is booked as process loss)") },
				{ f: "_batch", label: __("Batch"), m: "s", ph: () => `B${yymm()}-P60-02` },
				{ f: "posting_date", label: __("Date"), t: "date", m: "s", def: today },
				{ f: "hs_serial_from", label: __("Serial numbers from"), m: "d", ph: "HLI-P60-26110401" },
				{ f: "to_warehouse", label: __("Warehouse"), t: "select", src: Q("Warehouse", "warehouses"), m: "d", blank: __("— finished goods store —") },
			], actions: [{ label: __("Receive finished goods"), action: "submit", primary: 1 }] },
		"Stock Entry:wip": { doctype: "Stock Entry", preset: { _mfg: "wip" }, title: __("Material transfer to WIP"),
			sub: __("Quick: work order — every component of the BOM is picked for the full quantity. Standard shows the stores; Detailed a partial quantity and the picker."),
			fields: [
				{ f: "work_order", label: __("Work order"), t: "select", src: Q("Work Order", "wo_transfer"), req: 1, m: "q", w: 2, blank: __("— choose —") },
				{ f: "from_warehouse", label: __("From warehouse"), t: "select", src: Q("Warehouse", "warehouses"), m: "s", blank: __("— components store —") },
				{ f: "to_warehouse", label: __("To warehouse"), t: "select", src: Q("Warehouse", "warehouses"), m: "s", blank: __("— work in progress —") },
				{ f: "_pct", label: __("Quantity to issue (% of the work order)"), t: "number", m: "d", def: 100 },
				{ f: "hs_picked_by", label: __("Picked by"), m: "d" },
			], actions: [{ label: __("Issue to WIP"), action: "submit", primary: 1 }] },
	});
	// a placeholder may be a function (the batch of this month)
	Object.values(C.DOCS).forEach((s) => (s.fields || []).forEach((df) => { if (typeof df.ph === "function") df.ph = df.ph(); }));
	["BOM", "Work Order", "Production Plan", "Job Card", "Quality Inspection"].forEach((dt) => {
		if (hipersign.fm && !hipersign.fm.COVERED.includes(dt)) hipersign.fm.COVERED.push(dt);
	});

	// + New (topbar and the create page): the Manufacturing group when the module is on
	if (hipersign.create && hipersign.create.GROUPS && !hipersign.create.__hsm) {
		hipersign.create.__hsm = true;
		const _groups = hipersign.create.GROUPS;
		hipersign.create.GROUPS = () => {
			const g = _groups();
			const at = g.findIndex(([l]) => l === __("Supplier bills"));
			g.splice(at < 0 ? g.length : at, 0, [__("Manufacturing"), [
				[__("BOM"), "list", { dt: "BOM", feature: "manufacturing" }],
				[__("Work order"), "tool", { dt: "Work Order", feature: "manufacturing" }],
				[__("Production plan"), "calendar", { dt: "Production Plan", feature: "manufacturing" }],
				[__("Job card"), "file", { dt: "Job Card", feature: "manufacturing" }],
				[__("Quality inspection"), "check", { dt: "Quality Inspection", feature: "manufacturing" }],
				[__("Manufacture entry"), "stock", { dt: "Stock Entry", win: "Stock Entry:manufacture", feature: "manufacturing" }],
				[__("Material transfer to WIP"), "share", { dt: "Stock Entry", win: "Stock Entry:wip", feature: "manufacturing" }],
			]]);
			return g;
		};
		if (!hipersign.create.__hsp) {
			const _open = hipersign.create.open;
			hipersign.create.open = function (a, mode) {
				if (a && a.win && C.DOCS[a.win]) return C.doc(a.win, Object.assign({}, a.values || {}));
				return _open.apply(this, arguments);
			};
		}
	}
})();

// the ERPNext lists of the Manufacturing records open their page (the page's menu keeps the classic list)
if (hipersign.nav && hipersign.nav.LIST_PAGE) Object.assign(hipersign.nav.LIST_PAGE, {
	"Work Order": ["hipersign-production", "wo"], BOM: ["hipersign-boms", "ver"], "Production Plan": ["hipersign-planning", "pp"],
	"Quality Inspection": ["hipersign-quality", "inc"], "Job Card": ["hipersign-shopfloor"],
});
