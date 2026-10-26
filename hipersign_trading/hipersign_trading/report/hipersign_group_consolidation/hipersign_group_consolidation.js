// Copyright (c) 2026, Hipersign
frappe.query_reports["Hipersign Group Consolidation"] = {
	filters: [
		{ fieldname: "period_end", label: __("Up to"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "currency", label: __("Presentation currency"), fieldtype: "Link", options: "Currency" },
		{ fieldname: "show", label: __("Show"), fieldtype: "Select", options: "Both\nProfit and Loss\nBalance Sheet", default: "Both" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return data && data.bold ? `<b>${value}</b>` : value;
	},
	onload(report) {
		report.page.add_inner_button(__("Sync all members"), () =>
			frappe.xcall("hipersign_trading.api.group.sync_all_now", { period_end: report.get_filter_value("period_end") })
				.then((r) => { frappe.show_alert({ message: r, indicator: "green" }); report.refresh(); }));
	},
};
