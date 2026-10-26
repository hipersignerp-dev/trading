// Copyright (c) 2026, Hipersign
frappe.listview_settings["Company Document"] = {
	add_fields: ["status", "expiry_date"],
	get_indicator(doc) {
		const c = { Valid: "green", "Due for renewal": "orange", Expired: "red", "Submitted to authority": "blue", "No expiry": "gray" }[doc.status];
		return [__(doc.status), c || "gray", "status,=," + doc.status];
	},
};
