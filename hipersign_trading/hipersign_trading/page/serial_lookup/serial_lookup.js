// Serial & warranty look-up — who bought it, when, and is it still covered?
frappe.pages["serial-lookup"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Serial & Warranty Look-up"), single_column: true });
	const field = page.add_field({ fieldname: "serial", fieldtype: "Link", options: "Serial No", label: __("Scan or type a serial number"), change: () => show(field.get_value()) });
	const out = $('<div class="hs-serial" style="margin-top:16px"></div>').appendTo(page.main);
	const row = (l, v) => `<tr><td class="text-muted" style="width:40%">${l}</td><td><b>${v || "—"}</b></td></tr>`;
	function show(sn) {
		if (!sn) return out.empty();
		frappe.call("hipersign_trading.api.serials.lookup", { serial_no: sn }).then(({ message: r }) => {
			const color = r.status === "Under warranty" ? "green" : r.status === "Warranty expired" ? "red" : "blue";
			const dl = r.delivery;
			out.html(`<div class="row"><div class="col-md-6"><div class="frappe-card p-3"><h5>${frappe.utils.escape_html(r.serial_no)} <span class="indicator-pill ${color}">${__(r.status)}</span></h5>
				<table class="table table-sm">${row(__("Item"), frappe.utils.escape_html(r.item_name))}${row(__("Received"), r.received ? frappe.datetime.str_to_user(r.received.date) + " · " + r.received.voucher_no : "")}
				${row(__("Warehouse"), r.warehouse)}${row(__("Warranty"), r.warranty_days ? __("{0} days from delivery", [r.warranty_days]) : "")}</table></div></div>
				<div class="col-md-6"><div class="frappe-card p-3"><h5>${__("Customer")}</h5><table class="table table-sm">${row(__("Customer"), dl ? frappe.utils.escape_html(dl.customer) : __("In our stock"))}
				${row(__("Delivered"), dl ? `${frappe.datetime.str_to_user(dl.date)} · <a href="/app/${frappe.router.slug(dl.voucher_type)}/${dl.voucher_no}">${dl.voucher_no}</a>` : "")}
				${row(__("Warranty until"), r.warranty_until ? frappe.datetime.str_to_user(r.warranty_until) : "")}
				${row(__("Claims"), (r.claims || []).map((c) => `<a href="/app/warranty-claim/${c.name}">${c.name}</a> · ${__(c.status)}`).join("<br>"))}</table>
				${dl ? `<button class="btn btn-primary btn-sm hs-claim">${__("Register warranty claim")}</button>` : ""}</div></div></div>`);
			out.find(".hs-claim").on("click", () => frappe.new_doc("Warranty Claim", { serial_no: r.serial_no, customer: dl.customer, item_code: r.item_code, complaint_date: frappe.datetime.get_today() }));
		});
	}
	wrapper.hs_show = (sn) => { field.set_value(sn); };
	const q = frappe.utils.get_url_arg("serial") || (frappe.route_options && frappe.route_options.serial);
	if (q) setTimeout(() => field.set_value(q), 200);
};
frappe.pages["serial-lookup"].on_page_show = function (wrapper) {
	if (frappe.route_options && frappe.route_options.serial && wrapper.hs_show) { wrapper.hs_show(frappe.route_options.serial); frappe.route_options = null; }
};
