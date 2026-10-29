// Approvals — every document waiting for a decision, the rule that routed it and who must act.
frappe.pages["hipersign-approvals"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Approvals"),
		desc: __("Every document waiting for a decision, the rule that routed it and who must act. Approving here moves the source document to its next state."),
	});
	const st = { type: "", mine: 0, items: [] };
	v.$actions.html(
		`<select class="hsx-select hsx-type"><option value="">${__("All document types")}</option></select>` +
			`<select class="hsx-select hsx-mine"><option value="0">${__("All approvers")}</option><option value="1">${__("Only items I can approve")}</option></select>` +
			`<button class="btn btn-xs btn-default hsx-refresh">${ui.icon("refresh-cw")} ${__("Refresh")}</button>`
	);
	v.$actions.on("change", ".hsx-type", function () {
		st.type = $(this).val();
		render();
	});
	v.$actions.on("change", ".hsx-mine", function () {
		st.mine = cint($(this).val());
		render();
	});
	v.$actions.on("click", ".hsx-refresh", () => load());

	function render() {
		const all = st.items;
		const rows = all.filter((x) => (!st.type || x.type === st.type) && (!st.mine || x.can_act));
		const oldest = all.reduce((m, x) => Math.max(m, x.days || 0), 0);
		const kp = [
			{ label: __("Awaiting decision"), value: all.length, icon: "inbox", tone: "violet" },
			{ label: __("Waiting on you"), value: all.filter((x) => x.can_act).length, icon: "user", tone: "blue" },
			{ label: __("Value pending"), value: all.reduce((s, x) => s + flt(x.value), 0), money: 1, icon: "banknote", tone: "navy" },
			{ label: __("Oldest item"), value: all.length ? __("{0} days", [oldest]) : "—", icon: "clock", tone: "amber" },
		];
		const $t = v.$actions.find(".hsx-type");
		const types = [...new Set(all.map((x) => x.type))].sort();
		$t.html(`<option value="">${__("All document types")}</option>` + types.map((t) => `<option>${ui.esc(t)}</option>`).join("")).val(st.type);

		const table = ui.table(
			[{ label: __("Type") }, { label: __("Document") }, { label: __("Description") }, { label: __("Value"), cls: "n" }, { label: __("Waiting for") }, { label: "", cls: "n" }],
			rows.map((x, i) => ({
				cells: [
					ui.pill(x.type, "violet"),
					`<a class="hsx-doc" data-hs-route='${ui.esc(JSON.stringify(["Form", x.doctype, x.name]))}'><b>${ui.esc(x.name)}</b></a>`,
					`<b>${ui.esc(x.description || "")}</b><span class="sub">${__("by {0} · {1} · {2} days", [ui.esc(x.by_name || x.by), frappe.datetime.str_to_user(x.since), x.days])}</span>`,
					x.value ? ui.money(x.value) : "—",
					`<b>${ui.esc(x.waiting_for.map((r) => __(r)).join(" / "))}</b><span class="sub">${ui.esc(x.reason || "")}</span>`,
					x.can_act
						? `<div style="display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap">${x.actions
								.map((a) => `<button class="btn btn-xs ${/reject|return|decline/i.test(a) ? "btn-danger" : "btn-primary"}" data-i="${i}" data-a="${ui.esc(a)}">${ui.esc(__(a))}</button>`)
								.join("")}</div>`
						: `<span class="text-muted small">${__("Not your step")}</span>`,
				],
			})),
			st.mine ? __("Nothing is waiting for you.") : __("All caught up — nothing is waiting for approval.")
		);
		v.$body.html(
			`<div class="hsx-kpis">${kp.map(ui.kpi).join("")}</div>` +
				ui.card(__("Approval queue"), table, { icon: "inbox", sub: __("{0} shown", [rows.length]) }) +
				ui.card(
					__("Routing rules in force"),
					`<p class="text-muted" style="margin:0 0 8px">${__("Thresholds, approvers and the rule that routes each document are kept in Hipersign Settings and the workflows.")}</p>
					<button class="btn btn-xs btn-default" data-hs-route='["Form","Hipersign Settings"]'>${__("Hipersign Settings")}</button>
					<button class="btn btn-xs btn-default" data-hs-route='["List","Workflow"]'>${__("Workflows")}</button>`,
					{ icon: "workflow" }
				)
		);
		v.$body.data("rows", rows);
	}

	v.$body.on("click", "button[data-a]", function () {
		const x = v.$body.data("rows")[cint($(this).attr("data-i"))];
		const action = $(this).attr("data-a");
		const negative = /reject|return|decline/i.test(action);
		const d = new frappe.ui.Dialog({
			title: __("{0} — {1}", [__(action), x.name]),
			fields: [
				{ fieldtype: "HTML", options: `<p>${ui.esc(x.type)} · ${ui.esc(x.description || "")}${x.value ? " · " + ui.money(x.value) : ""}</p>` },
				{ fieldname: "note", fieldtype: "Small Text", label: negative ? __("Reason") : __("Note (optional)"), reqd: negative ? 1 : 0 },
			],
			primary_action_label: __(action),
			primary_action(vals) {
				d.disable_primary_action();
				frappe
					.xcall("hipersign_trading.api.approvals.act", { kind: x.kind, doctype: x.doctype, name: x.name, action, note: vals.note || null })
					.then(() => {
						d.hide();
						frappe.show_alert({ message: __("{0}: {1}", [x.name, __(action)]), indicator: negative ? "orange" : "green" });
						load();
					})
					.catch(() => d.enable_primary_action());
			},
		});
		d.show();
	});

	function load() {
		if (!st.items.length) ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.approvals.get_approvals", { mine: 0 }).then((r) => {
			st.items = r.items;
			render();
		});
	}
	wrapper.hs_load = load;
	load();
};

frappe.pages["hipersign-approvals"].on_page_show = function (wrapper) {
	if (wrapper.hs_shown && wrapper.hs_load) wrapper.hs_load();
	wrapper.hs_shown = 1;
};
