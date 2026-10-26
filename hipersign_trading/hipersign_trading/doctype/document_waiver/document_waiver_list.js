// Copyright (c) 2026, Hipersign
frappe.listview_settings["Document Waiver"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const c = { Pending: "orange", Approved: "green", Rejected: "red", Received: "blue", Overdue: "red", Used: "gray" }[doc.status];
		return [__(doc.status), c || "gray", "status,=," + doc.status];
	},
};
