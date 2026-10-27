// Landed Cost & Margin — what each shipment really cost, and what each item really earns.
frappe.pages["hipersign-landed"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Landed Cost & Margin"),
		desc: __("Freight, insurance, duty, clearing and handling spread onto the goods — the real cost of every unit, and the margin it earns against the price."),
	});
	const st = { d: null };
	v.$actions.html(`<button class="btn btn-xs btn-default" data-hs-route='["List","Landed Cost Voucher"]'>${__("Landed cost vouchers")}</button>`);
	const m = (x) => ui.money(x);

	function stack(s) {
		if (!s) return `<div class="hsx-empty">${__("No import shipments yet.")}</div>`;
		const part = (l, x, cls) => `<div class="${cls || ""}"><span>${ui.esc(l)}</span><b>${m(x)}</b></div>`;
		const items = s.items.length
			? ui.table([{ label: __("Item") }, { label: __("Qty"), cls: "n" }, { label: __("Landed unit cost"), cls: "n" }],
				s.items.map((i) => ({ cells: [ui.esc(i.item), format_number(i.qty), m(i.unit)] })))
			: "";
		return `<div class="hsx-stack">${part(__("Goods"), s.goods)}<i>+</i>${part(__("Freight"), s.freight)}<i>+</i>${part(__("Duty & clearing"), s.duty_clearing)}<i>+</i>${part(__("Insurance & handling"), s.insurance_handling)}<i>=</i>${part(__("Landed cost"), s.landed, "tot")}</div>
			<div style="margin-top:12px">${items}</div>`;
	}

	function render() {
		const d = st.d;
		const k = d.kpis;
		const kp = [
			{ label: __("Import charges this month"), value: k.charges_month, money: 1, icon: "ship", tone: "blue" },
			{ label: __("Average landed uplift"), value: `${k.uplift}%`, sub: __("charges ÷ goods value"), icon: "trending-up", tone: "violet" },
			{ label: __("Gross margin"), value: `${k.gross_margin}%`, sub: __("{0} · target {1}%", [k.period, d.target]), icon: "chart", tone: k.gross_margin >= d.target ? "green" : "amber" },
			{ label: __("Items below target margin"), value: k.below_target, sub: __("sold in the last 60 days"), icon: "circle-alert", tone: k.below_target ? "red" : "green" },
			{ label: __("Charges not yet in stock cost"), value: k.not_in_stock, money: 1, sub: __("received shipments without a landed cost voucher"), icon: "receipt", tone: k.not_in_stock ? "amber" : "green" },
		];
		const ships = ui.table(
			[{ label: __("Shipment") }, { label: __("Status") }, { label: __("Goods"), cls: "n" }, { label: __("Freight"), cls: "n" }, { label: __("Insurance"), cls: "n" },
				{ label: __("Duty"), cls: "n" }, { label: __("Clearing"), cls: "n" }, { label: __("Handling & other"), cls: "n" }, { label: __("Uplift"), cls: "n" }, { label: __("In stock cost") }],
			d.shipments.map((s) => ({
				cells: [`<b>${ui.esc(s.name)}</b>`, ui.pill(__(s.status), "blue"), m(s.goods), m(s.freight), m(s.insurance), m(s.duty), m(s.clearing), m(s.handling + s.other), `${s.uplift}%`,
					s.lcv ? ui.pill(__("Applied"), "green") : ui.pill(__("Not yet"), "amber")],
				route: ["Form", "Import Shipment", s.name],
			})),
			__("No import shipments yet.")
		);
		const margins = ui.table(
			[{ label: __("Item") }, { label: __("Landed cost"), cls: "n" }, { label: __("List price"), cls: "n" }, { label: __("Average sold"), cls: "n" }, { label: __("Qty sold (60 days)"), cls: "n" }, { label: __("Margin"), cls: "n" }],
			d.margins.map((r) => ({
				cells: [`<b>${ui.esc(r.item)}</b><span class="sub">${ui.esc(r.item_code)}</span>`, m(r.landed), r.list ? m(r.list) : "—", r.avg ? m(r.avg) : "—", r.qty ? format_number(r.qty) : "—",
					ui.pill(`${r.margin}%${r.sold ? "" : " " + __("(list)")}`, r.margin < 0 ? "red" : r.margin < d.target ? "amber" : "green")],
				route: ["Form", "Item", r.item_code],
			})),
			__("No stock items.")
		);
		const shipOpts = d.shipments.map((s) => `<option value="${ui.esc(s.name)}">${ui.esc(s.name)}</option>`).join("");
		v.$body.html(
			`<div class="hsx-kpis">${kp.map(ui.kpi).join("")}</div>
			<div class="hsx-grid2">
				${ui.card(__("Landed cost of a shipment"), `<div class="hsx-stackwrap">${stack(d.stack)}</div>`, { icon: "package", actions: d.shipments.length ? `<select class="hsx-select hsx-ship">${shipOpts}</select>` : "" })}
				${ui.card(__("Price helper"), `<div class="hsx-form">
					<label>${__("Item")}<select class="hsx-pi">${d.items.map((i) => `<option value="${ui.esc(i.value)}">${ui.esc(i.label)}</option>`).join("")}</select></label>
					<label>${__("Target margin %")}<input type="number" class="hsx-pm" value="${d.target}" min="0" max="95" step="1"></label></div>
					<div class="hsx-note hsx-pr">${__("Pick an item to see the lowest price that keeps the margin.")}</div>`, { icon: "calculator" })}
			</div>
			${ui.card(__("Shipments and their charges"), ships, { icon: "ship" })}
			${ui.card(__("Item margins after landed cost"), margins, { icon: "trending-up", sub: __("lowest first · from sales in the last 60 days, otherwise the list price") })}`
		);
		if (d.stack) v.$body.find(".hsx-ship").val(d.stack.name);
		price();
	}

	function price() {
		const item = v.$body.find(".hsx-pi").val();
		if (!item) return;
		frappe.xcall("hipersign_trading.api.landed.price_helper", { item_code: item, margin: v.$body.find(".hsx-pm").val() }).then((r) => {
			v.$body.find(".hsx-pr").html(
				__("Landed cost {0} → sell at <b>{1}</b> or more to keep {2}% margin.", [m(r.landed), m(r.minimum), r.margin]) +
					(r.list ? "<br>" + __("Current list price {0} gives {1}% margin.", [m(r.list), r.list_margin]) : "<br>" + __("No list price yet."))
			);
		});
	}

	v.$body.on("change", ".hsx-pi, .hsx-pm", price);
	v.$body.on("change", ".hsx-ship", function () {
		frappe.xcall("hipersign_trading.api.landed.get_stack", { shipment: $(this).val() }).then((s) => v.$body.find(".hsx-stackwrap").html(stack(s)));
	});

	function load() {
		if (!st.d) ui.loading(v.$body);
		frappe.xcall("hipersign_trading.api.landed.get_landed").then((d) => {
			st.d = d;
			render();
		});
	}
	wrapper.hs_load = load;
	load();
};

frappe.pages["hipersign-landed"].on_page_show = function (wrapper) {
	if (wrapper.hs_shown && wrapper.hs_load) wrapper.hs_load();
	wrapper.hs_shown = 1;
};
