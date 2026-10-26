// Sales Order Tracker — every order from quotation to payment on one line.
frappe.pages["sales-order-tracker"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Sales Order Tracker"), single_column: true });
	const tracker = new HipersignTracker(page);
	wrapper.hs_tracker = tracker;
	tracker.refresh();
};
frappe.pages["sales-order-tracker"].on_page_show = function (wrapper) {
	wrapper.hs_tracker && wrapper.hs_tracker.refresh();
};

const HS_BUCKETS = ["", "Approval", "To deliver", "To invoice", "Awaiting payment", "Overdue", "Completed"];
const HS_REPORTS = [
	["soa", __("Statement of Account")],
	["order", __("Order status (order confirmation)")],
	["delivery", __("Delivery status (delivery note)")],
	["invoice", __("Invoice copy")],
];

class HipersignTracker {
	constructor(page) {
		this.page = page;
		this.search = page.add_field({ fieldtype: "Data", fieldname: "search", label: __("Customer, order or PO no."), change: () => this.refresh() });
		this.status = page.add_field({ fieldtype: "Select", fieldname: "status", label: __("Status"), options: HS_BUCKETS.join("\n"), change: () => this.refresh() });
		this.month = page.add_field({ fieldtype: "Data", fieldname: "month", label: __("Month (YYYY-MM)"), change: () => this.refresh() });
		page.set_primary_action(__("New sales order"), () => frappe.new_doc("Sales Order"), "add");
		this.$body = $(`<div class="hs-tracker"></div>`).appendTo(page.main);
	}
	refresh() {
		frappe
			.xcall("hipersign_trading.api.tracker.get_orders", {
				search: this.search.get_value(),
				status: this.status.get_value(),
				month: this.month.get_value(),
			})
			.then((r) => this.render(r));
	}
	money(v, cur) {
		return format_currency(v, cur);
	}
	render(r) {
		const t = r.totals;
		const kpi = (l, v, cls = "") => `<div class="hs-kpi ${cls}"><span>${l}</span><b>${v}</b></div>`;
		let html = `<div class="hs-kpis">${kpi(__("Sales value"), this.money(t.value))}${kpi(__("Paid"), this.money(t.paid), "green")}${kpi(__("Remaining"), this.money(t.remaining))}${kpi(__("Overdue"), this.money(t.overdue), "red")}</div>`;
		if (!r.orders.length) html += `<div class="text-muted" style="padding:30px;text-align:center">${__("No orders match the filters.")}</div>`;
		html += r.orders.map((o) => this.row(o)).join("");
		this.$body.html(html);
		this.$body.find("[data-popup]").each(function () {
			$(this).popover({ trigger: "hover focus", html: true, placement: "top", container: "body", content: decodeURIComponent($(this).attr("data-popup")) });
		});
		this.$body.find("[data-act]").on("click", (e) => this.action($(e.currentTarget)));
		this.$body.find("select.hs-report").on("change", (e) => {
			const el = $(e.currentTarget), v = el.val();
			el.val("");
			v && this.report(el.attr("data-so"), v);
		});
	}
	row(o) {
		const pct = o.value ? Math.round((o.paid / o.value) * 100) : 0;
		const stages = o.stages
			.map((s) => {
				const info = `<b>${__(s.name)}</b><br>` + s.info.map((x) => `${frappe.utils.escape_html(String(x[0]))}: ${frappe.utils.escape_html(String(x[1]))}`).join("<br>");
				return `<div class="hs-stage ${s.state}" tabindex="0" data-popup="${encodeURIComponent(info)}"><i></i><span>${__(s.name)}</span><small>${frappe.utils.escape_html(s.tag || "")}</small></div>`;
			})
			.join("");
		return `<div class="hs-row">
			<div class="hs-row-h">
				<div><a href="/app/sales-order/${o.name}"><b>${o.name}</b></a> ${o.export ? `<span class="indicator-pill blue">${__("Export")}</span>` : ""}
					<div class="text-muted small">${frappe.utils.escape_html(o.customer_name)} · PO ${frappe.utils.escape_html(o.po_no || "—")} · ${frappe.datetime.str_to_user(o.date)} → ${frappe.datetime.str_to_user(o.delivery_date)}</div></div>
				<div class="hs-money"><span>${__("Value")} <b>${this.money(o.value, o.currency)}</b></span><span>${__("Paid")} <b class="text-success">${this.money(o.paid, o.currency)}</b></span><span>${__("Remaining")} <b>${this.money(o.remaining, o.currency)}</b></span><span class="indicator-pill ${o.bucket === "Overdue" ? "red" : o.bucket === "Completed" ? "green" : "orange"}">${__(o.bucket)}</span></div>
				<div class="hs-actions">
					<select class="hs-report form-control input-xs" data-so="${o.name}"><option value="">${__("Reports…")}</option>${HS_REPORTS.map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select>
					<button class="btn btn-default btn-xs" data-act="email" data-so="${o.name}" title="${__("Email")}">${frappe.utils.icon("mail", "sm")}</button>
					<button class="btn btn-default btn-xs hs-wa" data-act="wa" data-so="${o.name}" title="WhatsApp">WA</button>
				</div>
			</div>
			<div class="hs-paybar"><i style="width:${pct}%"></i></div>
			<div class="hs-stages">${stages}</div>
		</div>`;
	}
	report(so, kind) {
		frappe.db.get_value("Sales Order", so, ["customer", "company"]).then(({ message: m }) => {
			if (kind === "soa") return frappe.set_route("query-report", "General Ledger", { company: m.company, party_type: "Customer", party: [m.customer], group_by: "Group by Voucher (Consolidated)" });
			if (kind === "order") return window.open(frappe.urllib.get_full_url(`/printview?doctype=Sales%20Order&name=${encodeURIComponent(so)}&format=Hipersign%20Order%20Confirmation`));
			const dt = kind === "delivery" ? "Delivery Note" : "Sales Invoice";
			const item = kind === "delivery" ? "against_sales_order" : "sales_order";
			frappe.db.get_list(`${dt} Item`, { filters: { [item]: so, docstatus: 1 }, fields: ["parent"], limit: 1 }).then((rows) => {
				if (!rows.length) return frappe.msgprint(__("No {0} yet for {1}", [__(dt), so]));
				window.open(frappe.urllib.get_full_url(`/printview?doctype=${encodeURIComponent(dt)}&name=${encodeURIComponent(rows[0].parent)}&format=${encodeURIComponent(kind === "delivery" ? "Hipersign Delivery Note" : "Hipersign Tax Invoice")}`));
			});
		});
	}
	action($el) {
		const so = $el.attr("data-so");
		if ($el.attr("data-act") === "email") {
			frappe.model.with_doc("Sales Order", so).then((doc) => {
				new frappe.views.CommunicationComposer({ doc, frm: null, subject: `${__("Order confirmation")} ${so}`, recipients: doc.contact_email, attach_document_print: true, print_format: "Hipersign Order Confirmation" });
			});
		} else hipersign.send_whatsapp("Sales Order", so, "Hipersign Order Confirmation");
	}
}
