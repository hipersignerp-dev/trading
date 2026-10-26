// Copyright (c) 2026, Hipersign
frappe.views.calendar["Company Deadline"] = {
	field_map: { start: "due_date", end: "due_date", id: "name", title: "title", allDay: 1 },
	gantt: false,
	get_events_method: "frappe.desk.calendar.get_events",
};
