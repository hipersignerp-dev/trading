// Copyright (c) 2026, Hipersign
frappe.query_reports["Missing Documents"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "reference_doctype", label: __("Record type"), fieldtype: "Link", options: "DocType",
			get_query: () => ({ query: "hipersign_trading.api.docs.ruled_doctypes" }) },
		{ fieldname: "document_type", label: __("Document"), fieldtype: "Link", options: "Hipersign Document Type" },
		{ fieldname: "level", label: __("Rule"), fieldtype: "Select", options: "\nBlock\nRequired" },
	],
};
