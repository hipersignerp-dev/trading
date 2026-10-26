// Copyright (c) 2026, Hipersign
frappe.views.calendar["Company Document"] = {
	field_map: { start: "expiry_date", end: "expiry_date", id: "name", title: "document_type", allDay: 1 },
	gantt: false,
	get_events_method: "frappe.desk.calendar.get_events",
};
