// v1.8.4 (#37): Data Migration — bring a business's data in, step by step: customers, suppliers, items, opening stock,
// opening balances, employees and prices. Each card starts a Frappe Data Import for that list (template download, upload,
// preview, import); recent imports and their status are listed below.
frappe.pages["hipersign-migration"].on_page_load = function (wrapper) {
	const ui = hipersign.ui, esc = ui.esc;
	const v = ui.page(wrapper, { title: __("Data Migration"), desc: __("Move your data in, in this order: masters first, then opening stock and balances. Each step gives a template to fill, checks it and imports it.") });
	const STEPS = [
		{ dt: "Customer", icon: "users", title: __("Customers"), text: __("Names, contacts, TRN, credit limits and payment terms.") },
		{ dt: "Supplier", icon: "truck", title: __("Suppliers"), text: __("Local and overseas suppliers with currency and terms.") },
		{ dt: "Item", icon: "package", title: __("Items"), text: __("Products with codes, units, groups, HS codes and reorder levels.") },
		{ dt: "Item Price", icon: "tag", title: __("Prices"), text: __("Selling and buying price lists.") },
		{ dt: "Stock Reconciliation", icon: "warehouse", title: __("Opening stock"), text: __("Quantity and valuation per item and warehouse on your start date.") },
		{ dt: "Journal Entry", icon: "book-open", title: __("Opening balances"), text: __("Trial balance on the start date: bank, fixed assets, loans, capital.") },
		{ dt: "Opening Invoice Creation Tool", icon: "receipt", title: __("Open invoices"), text: __("Unpaid customer and supplier invoices on the start date."), form: true },
		{ dt: "Employee", icon: "user", title: __("Employees"), text: __("Staff with joining date, department, visa and labour card details.") },
	];
	function render(recent) {
		v.$body.html(`<div class="hs-mg-grid">${STEPS.filter((s) => frappe.model.can_create(s.dt) || s.form).map((s, i) => `<div class="hsx-card hs-mg-card">
			<div class="hs-mg-n">${i + 1}</div><div class="hs-mg-t"><b>${frappe.utils.icon(s.icon, "sm")} ${esc(s.title)}</b><span>${esc(s.text)}</span></div>
			<button class="btn btn-sm btn-primary" data-dt="${esc(s.dt)}" data-form="${s.form ? 1 : ""}">${esc(s.form ? __("Open") : __("Start import"))}</button></div>`).join("")}</div>
			<div class="hsx-card"><div class="hsx-card-h"><h3>${frappe.utils.icon("upload", "sm")} ${esc(__("Recent imports"))}</h3></div><div class="hsx-card-b flush">
			${recent.length ? `<div class="hsx-tw"><table class="hsx-t"><thead><tr><th>${esc(__("Import"))}</th><th>${esc(__("List"))}</th><th>${esc(__("Type"))}</th><th>${esc(__("Started"))}</th><th>${esc(__("Status"))}</th></tr></thead>
			<tbody>${recent.map((r) => `<tr data-imp="${esc(r.name)}" style="cursor:pointer"><td><span class="hsx-code">${esc(r.name)}</span></td><td>${esc(__(r.reference_doctype))}</td>
				<td>${esc(__(r.import_type || ""))}</td><td>${esc(frappe.datetime.comment_when(r.creation))}</td>
				<td><span class="hsx-pill ${r.status === "Success" ? "green" : r.status === "Error" || r.status === "Partial Success" ? "orange" : "grey"}">${esc(__(r.status || "Pending"))}</span></td></tr>`).join("")}</tbody></table></div>`
				: `<div class="hsx-empty">${esc(__("No imports yet."))}</div>`}</div></div>`);
	}
	v.$body.on("click", "[data-dt]", function () {
		const dt = $(this).attr("data-dt");
		if ($(this).attr("data-form")) return frappe.set_route("Form", dt);
		frappe.new_doc("Data Import", { reference_doctype: dt, import_type: "Insert New Records" });
	});
	v.$body.on("click", "[data-imp]", function () { frappe.set_route("Form", "Data Import", $(this).attr("data-imp")); });
	const load = () => frappe.xcall("frappe.client.get_list", { doctype: "Data Import", fields: ["name", "reference_doctype", "import_type", "status", "creation"],
		order_by: "creation desc", limit_page_length: 20 }).then(render).catch(() => render([]));
	wrapper.hs_reload = load;
	load();
};
frappe.pages["hipersign-migration"].on_page_show = function (wrapper) {
	if (wrapper.hs_reload && wrapper.hs_loaded_once) wrapper.hs_reload();
	wrapper.hs_loaded_once = true;
};
