// Smart reorder: suggestions and one-click draft purchase orders per supplier.
frappe.query_reports["Hipersign Smart Reorder"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "only_to_order", label: __("Only items to order"), fieldtype: "Check", default: 1 },
		{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" },
		{ fieldname: "item_group", label: __("Item group"), fieldtype: "Link", options: "Item Group" },
		{ fieldname: "cover_days", label: __("Order enough for (days)"), fieldtype: "Select", options: "\n30\n45\n60\n90" },
		{ fieldname: "history_days", label: __("Sales history (days)"), fieldtype: "Select", options: "\n30\n60\n90\n180" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.fieldname === "cover_days" && data.urgent) value = `<span style="color:var(--red-600);font-weight:600">${value}</span>`;
		if (data && column.fieldname === "suggested_qty" && data.suggested_qty > 0) value = `<b>${value}</b>`;
		return value;
	},
	onload(report) {
		report.page.add_inner_button(__("Create purchase orders"), () => {
			const rows = (report.data || []).filter((r) => r.suggested_qty > 0 && r.supplier);
			if (!rows.length) return frappe.msgprint(__("Nothing to order with a supplier set."));
			frappe.confirm(__("Create draft purchase orders for {0} items from {1} suppliers?", [rows.length, new Set(rows.map((r) => r.supplier)).size]), () => {
				frappe.call({ method: "hipersign_trading.hipersign_trading.report.hipersign_smart_reorder.hipersign_smart_reorder.make_purchase_orders",
					args: { items: rows, company: report.get_filter_value("company") }, freeze: true }).then((r) => {
					frappe.msgprint(__("Draft purchase orders created: {0}", [(r.message || []).map((n) => `<a href="${frappe.utils.get_form_link("Purchase Order", n)}">${n}</a>`).join(", ")]));
				});
			});
		});
	},
};
