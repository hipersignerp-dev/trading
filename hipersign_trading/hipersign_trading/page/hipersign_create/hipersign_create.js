// Create New — one place to add any record or document.
const HS_CREATE = [
	[__("Sales"), [["Lead", "users"], ["Quotation", "file"], ["Sales Order", "list"], ["Customer", "users"], ["Customer Group", "tag"]]],
	[__("Purchasing & imports"), [["Purchase Order", "buying"], ["Supplier", "organization"], ["Import Shipment", "share"]]],
	[__("Exports"), [["Export Shipment", "share"]]],
	[__("Products, services & stock"), [["Item", "stock"], ["Warehouse", "organization"], ["Stock Entry", "stock"], ["Stock Reconciliation", "list"]]],
	[__("Delivery"), [["Delivery Trip", "share"], ["Driver", "users"], ["Vehicle", "share"]]],
	[__("Returns & warranty"), [["Sales Invoice", "file", { is_return: 1 }, __("Credit note")], ["Purchase Invoice", "file", { is_return: 1 }, __("Debit note")], ["Warranty Claim", "tool"]]],
	[__("People & assets"), [["Employee", "users"], ["Leave Application", "calendar"], ["Asset", "organization"]]],
	[__("Finance"), [["Payment Entry", "money-coins-1"], ["Post Dated Cheque", "money-coins-1"], ["Bank Account", "money-coins-1"], ["Payment Terms Template", "calendar"], ["Currency Exchange", "money-coins-1"], ["Credit Limit Request", "money-coins-1"]]],
	[__("Administration"), [["User", "users"]]],
];
frappe.pages["hipersign-create"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Create New"), single_column: true });
	const html = HS_CREATE.map(([group, items]) => {
		const tiles = items
			.filter(([dt]) => frappe.boot.user.can_create.includes(dt) || frappe.model.can_create(dt))
			.map(([dt, icon, pre, label], k) => `<button class="hs-tile" data-dt="${dt}" data-pre='${pre ? JSON.stringify(pre) : ""}'>${frappe.utils.icon(icon, "md")}<b>${label || __(dt)}</b></button>`)
			.join("");
		return tiles ? `<div class="hs-group"><h5>${group}</h5><div class="hs-tiles">${tiles}</div></div>` : "";
	}).join("");
	$(`<div class="hs-create">${html}</div>`).appendTo(page.main).on("click", ".hs-tile", function () {
		const pre = $(this).attr("data-pre");
		frappe.new_doc($(this).attr("data-dt"), pre ? JSON.parse(pre) : undefined);
	});
};
