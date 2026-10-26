frappe.listview_settings["Post Dated Cheque"] = {
	add_fields: ["status", "cheque_date", "direction"],
	get_indicator(doc) {
		const c = { "In Hand": "blue", Deposited: "purple", Cleared: "green", Bounced: "red", Replaced: "gray", Issued: "orange", Cancelled: "gray" };
		const late = ["In Hand", "Issued"].includes(doc.status) && doc.cheque_date <= frappe.datetime.get_today();
		return [__(late && doc.status === "In Hand" ? "Due to deposit" : doc.status), late ? "orange" : c[doc.status] || "gray", "status,=," + doc.status];
	},
};
