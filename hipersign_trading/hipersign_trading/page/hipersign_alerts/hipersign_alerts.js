// Insights & Alerts — early warnings from deterministic rules over the live records, with evidence and a recommended action.
frappe.pages["hipersign-alerts"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Insights & Alerts"),
		desc: __("Early warnings from shipments, stock, margins, credit and receivables. Each shows its evidence, the rule and a recommended action."),
	});
	const st = { status: "Open", category: "", data: null };
	v.$actions.html(`<span class="hsx-banner">${__("Deterministic rules — no AI model connected")}</span>`);

	function card(a, i) {
		const tone = { High: "red", Medium: "amber", Low: "grey" }[a.severity] || "grey";
		return `<article class="hsx-alert ${a.severity} ${a.status !== "Open" ? "done" : ""}">
			<div class="hsx-alert-h"><b>${ui.esc(a.title)}</b>${ui.pill(__(a.severity), tone)}${a.status !== "Open" ? ui.pill(__(a.status), a.status === "Actioned" ? "green" : "grey") : ""}</div>
			<div class="text-muted small">${ui.esc(__(a.category))}</div>
			<div class="hsx-ev">${(a.evidence || []).map((e) => `<span>${ui.esc(e[0])}: <b>${ui.esc(e[1])}</b></span>`).join("")}</div>
			<p><b>${__("Consequence")}:</b> ${ui.esc(a.consequence || "")}</p>
			<p><b>${__("Recommended")}:</b> ${ui.esc(a.recommendation || "")}</p>
			${a.state_note ? `<p style="color:var(--x-green)">${ui.icon("check")} ${ui.esc(a.state_note)}</p>` : ""}
			<div class="acts">${
				a.status === "Open"
					? `<button class="btn btn-xs btn-primary" data-i="${i}" data-s="Actioned">${__("Mark actioned")}</button><button class="btn btn-xs btn-default" data-i="${i}" data-s="Dismissed">${__("Dismiss")}</button>`
					: `<button class="btn btn-xs btn-default" data-i="${i}" data-s="Open">${__("Reopen")}</button>`
			}${a.doctype && a.name ? `<button class="btn btn-xs btn-default" data-hs-route='${ui.esc(JSON.stringify(["Form", a.doctype, a.name]))}'>${__("Open source")} →</button>` : ""}</div>
		</article>`;
	}

	function render() {
		const all = st.data.alerts;
		const open = all.filter((a) => a.status === "Open");
		const rows = all.filter((a) => (st.status === "All" || a.status === st.status) && (!st.category || a.category === st.category));
		const cats = [...new Set(all.map((a) => a.category))];
		const kp = [
			{ label: __("Open alerts"), value: open.length, icon: "sparkles", tone: "violet" },
			{ label: __("High severity"), value: open.filter((a) => a.severity === "High").length, icon: "circle-alert", tone: "red" },
			{ label: __("Actioned"), value: all.filter((a) => a.status === "Actioned").length, icon: "check", tone: "green" },
			{ label: __("Rules monitored"), value: st.data.rules, icon: "layers", tone: "blue" },
		];
		const by = cats
			.map((c) => [c, open.filter((a) => a.category === c).length])
			.filter((x) => x[1])
			.sort((a, b) => b[1] - a[1]);
		const max = by.reduce((m, x) => Math.max(m, x[1]), 1);
		const bars = by.length
			? by.map(([c, n]) => `<div style="margin:6px 0;cursor:pointer" data-cat="${ui.esc(c)}"><div style="display:flex;justify-content:space-between;font-size:12.5px"><span>${ui.esc(__(c))}</span><b>${n}</b></div>
				<div class="hsx-progress"><i style="width:${(n / max) * 100}%;background:var(--x-violet)"></i></div></div>`).join("")
			: `<div class="hsx-empty">${__("No open alerts.")}</div>`;
		v.$body.html(
			`<div class="hsx-kpis">${kp.map(ui.kpi).join("")}</div>
			<div class="hsx-grid2" style="grid-template-columns:minmax(0,2.2fr) minmax(0,1fr)"><div>
				<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">${ui.seg("status", [["Open", __("Open")], ["Actioned", __("Actioned")], ["Dismissed", __("Dismissed")], ["All", __("All")]], st.status)}
				<select class="hsx-select hsx-cat"><option value="">${__("All categories")}</option>${cats.map((c) => `<option value="${ui.esc(c)}">${ui.esc(__(c))}</option>`).join("")}</select></div>
				<div class="hsx-alerts">${rows.map((a) => card(a, all.indexOf(a))).join("") || ui.card("", `<div class="hsx-empty"><b>${__("No alerts in this view")}</b><br>${__("Change the filter to see others.")}</div>`)}</div>
			</div><div>
				${ui.card(__("Open by category"), bars)}
				<div style="height:16px"></div>
				${ui.card(__("How alerts work"), `<ul class="small" style="margin:0;padding-left:18px;line-height:1.7">
					<li>${__("Rules run on the live records each time you open this page.")}</li>
					<li>${__("Marking an alert actioned or dismissed sticks until the situation changes.")}</li>
					<li>${__("You see the alerts for records you are allowed to open.")}</li>
					<li>${__("Thresholds (stock, margin, reminder days) are set in Hipersign Settings.")}</li></ul>`)}
			</div></div>`
		);
		v.$body.find(".hsx-cat").val(st.category);
	}

	v.$body.on("click", "[data-seg=status] button", function () {
		st.status = $(this).attr("data-v");
		render();
	});
	v.$body.on("change", ".hsx-cat", function () {
		st.category = $(this).val();
		render();
	});
	v.$body.on("click", "[data-cat]", function () {
		st.category = $(this).attr("data-cat");
		st.status = "Open";
		render();
	});
	v.$body.on("click", "button[data-s]", function () {
		const a = st.data.alerts[cint($(this).attr("data-i"))];
		const status = $(this).attr("data-s");
		const save = (note) =>
			frappe.xcall("hipersign_trading.alerts.set_state", { key: a.key, status, note: note || null }).then(() => {
				a.status = status;
				a.state_note = note || null;
				render();
			});
		if (status === "Actioned") frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("What was done? (optional)") }, (r) => save(r.note), __("Mark actioned"));
		else save();
	});

	function load() {
		if (!st.data) ui.loading(v.$body);
		frappe.xcall("hipersign_trading.alerts.get_alerts").then((r) => {
			st.data = r;
			render();
		});
	}
	wrapper.hs_load = load;
	wrapper.hs_state = st;
	load();
};

frappe.pages["hipersign-alerts"].on_page_show = function (wrapper) {
	const o = frappe.route_options;
	if (o && o.category && wrapper.hs_state) {
		wrapper.hs_state.category = o.category;
		wrapper.hs_state.status = "Open";
		frappe.route_options = null;
	}
	if (wrapper.hs_shown && wrapper.hs_load) wrapper.hs_load();
	wrapper.hs_shown = 1;
};
