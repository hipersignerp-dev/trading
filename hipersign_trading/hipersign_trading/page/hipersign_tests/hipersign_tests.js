// Test Centre — the demo-site test scripts, with a result and a note for each, kept on the site for everyone.
frappe.pages["hipersign-tests"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Test Centre"),
		desc: __("Walk through each test script on the demo data: open the screen, do the steps, compare with the expected result and record Pass, Fail or Blocked."),
	});
	const st = { tests: [], section: "", result: "" };
	const can_reset = frappe.user.has_role(["System Manager", "Managing Director"]);
	v.$actions.html(
		`<select class="hsx-select hsx-sec"><option value="">${__("All sections")}</option></select>` +
			`<select class="hsx-select hsx-resf"><option value="">${__("All results")}</option>${["Not run", "Pass", "Fail", "Blocked"].map((r) => `<option value="${r}">${__(r)}</option>`).join("")}</select>` +
			(can_reset ? `<button class="btn btn-xs btn-default hsx-reset">${__("Clear all results")}</button>` : "")
	);
	v.$actions.on("change", ".hsx-sec", function () {
		st.section = $(this).val();
		render();
	});
	v.$actions.on("change", ".hsx-resf", function () {
		st.result = $(this).val();
		render();
	});
	v.$actions.on("click", ".hsx-reset", () =>
		frappe.confirm(__("Clear every recorded result?"), () => frappe.xcall("hipersign_trading.api.centre.reset_results").then(load))
	);
	const md = (s) => ui.esc(s).replace(/\*([^*]+)\*/g, "<i>$1</i>");

	function render() {
		const t = st.tests;
		const n = (r) => t.filter((x) => x.result === r).length;
		const run = t.length - n("Not run");
		const kp = [
			{ label: __("Tests"), value: t.length, sub: __("{0} sections", [new Set(t.map((x) => x.section)).size]), icon: "flask-conical", tone: "blue" },
			{ label: __("Run"), value: `${run} / ${t.length}`, sub: `${t.length ? Math.round((run / t.length) * 100) : 0}%`, icon: "play", tone: "violet" },
			{ label: __("Passed"), value: n("Pass"), icon: "check", tone: "green" },
			{ label: __("Failed"), value: n("Fail"), icon: "circle-alert", tone: n("Fail") ? "red" : "green" },
			{ label: __("Blocked"), value: n("Blocked"), icon: "clock", tone: n("Blocked") ? "amber" : "green" },
		];
		const $s = v.$actions.find(".hsx-sec");
		if ($s.find("option").length === 1) [...new Set(t.map((x) => x.section))].forEach((s) => $s.append(`<option value="${ui.esc(s)}">${ui.esc(__(s))}</option>`));
		const rows = t.filter((x) => (!st.section || x.section === st.section) && (!st.result || x.result === st.result));
		const sections = [...new Set(rows.map((x) => x.section))];
		const html = sections
			.map((sec) => {
				const list = rows.filter((x) => x.section === sec);
				const done = list.filter((x) => x.result !== "Not run").length;
				return ui.card(
					__(sec),
					ui.table(
						[{ label: __("ID") }, { label: __("Role") }, { label: __("Steps") }, { label: __("Expected") }, { label: __("Result") }, { label: __("Notes") }],
						list.map((x) => ({
							cells: [
								`<b>${ui.esc(x.id)}</b>${x.route ? `<br><button class="btn btn-xs btn-default" style="margin-top:4px" data-hs-route='${ui.esc(JSON.stringify(x.route))}'>${__("Start")} →</button>` : ""}`,
								ui.esc(__(x.role || "")),
								md(x.steps),
								md(x.expected),
								`<div class="hsx-res" data-id="${ui.esc(x.id)}">${["Pass", "Fail", "Blocked"].map((r) => `<button class="${r} ${x.result === r ? "on" : ""}" data-r="${r}">${__(r)}</button>`).join("")}</div>
								${x.by ? `<span class="sub">${ui.esc(x.by)} · ${frappe.datetime.str_to_user(x.on)}</span>` : ""}`,
								`<input class="form-control input-xs hsx-tnote" data-id="${ui.esc(x.id)}" value="${ui.esc(x.notes || "")}" placeholder="${__("Note")}" style="min-width:150px">`,
							],
						}))
					),
					{ sub: `${done} / ${list.length}`, actions: `<div class="hsx-progress" style="width:120px"><i style="width:${(done / list.length) * 100}%"></i></div>` }
				);
			})
			.join("");
		v.$body.html(`<div class="hsx-kpis">${kp.map(ui.kpi).join("")}</div>${html || ui.card("", `<div class="hsx-empty">${__("No tests match.")}</div>`)}`);
	}

	function save(id, result, notes) {
		const x = st.tests.find((t) => t.id === id);
		return frappe.xcall("hipersign_trading.api.centre.set_result", { test_id: id, result, notes }).then(() => {
			x.result = result;
			if (notes != null) x.notes = notes;
			x.by = frappe.session.user_fullname;
			x.on = frappe.datetime.get_today();
		});
	}
	v.$body.on("click", ".hsx-res button", function () {
		const id = $(this).closest(".hsx-res").attr("data-id");
		const x = st.tests.find((t) => t.id === id);
		const r = $(this).attr("data-r");
		save(id, x.result === r ? "Not run" : r, null).then(render);
	});
	v.$body.on("change", ".hsx-tnote", function () {
		const id = $(this).attr("data-id");
		const x = st.tests.find((t) => t.id === id);
		save(id, x.result, $(this).val()).then(() => frappe.show_alert({ message: __("Note saved"), indicator: "green" }, 2));
	});

	function load() {
		ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.centre.get_tests").then((t) => {
			st.tests = t;
			render();
		});
	}
	load();
};
