// Customer Portal — the prototype's preview page (v1.7.0): the customer's portal (/portal) in a browser frame,
// for any customer picked at the top right.
frappe.pages["hipersign-portal"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, { title: __("Customer Portal"), desc: __("What your customers see when they log in — orders, invoices, statement, proof of delivery and warranty, all from the same records.") });
	v.$wrap.addClass("hsx-mod");
	const $sel = $(`<select class="form-control" style="min-width:240px"></select>`).appendTo(v.$actions);
	v.$body.html(`<div class="hsx-bnote" style="border:1px dashed var(--x-line,#e2e8f0);border-radius:10px;padding:9px 14px;margin-bottom:14px"></div>
		<div class="hsx-browser"><div class="hsx-browser-bar"><i></i><i></i><i></i><span></span><a target="_blank" class="btn btn-default btn-xs">${__("Open in a new tab")}</a></div>
		<iframe style="width:100%;height:1400px;border:0;display:block;background:#fff"></iframe></div>`);
	v.$body.find("iframe").on("load", function () { try { this.style.height = Math.max(600, this.contentWindow.document.documentElement.scrollHeight + 10) + "px"; } catch (e) { /* other origin */ } });
	const show = (c, label) => {
		const url = `/portal?embed=1&customer=${encodeURIComponent(c)}`;
		v.$body.find("iframe").attr("src", url);
		v.$body.find(".hsx-browser-bar span").text(`portal · ${label}`);
		v.$body.find(".hsx-browser-bar a").attr("href", `/portal?customer=${encodeURIComponent(c)}`);
		v.$body.find(".hsx-bnote").html(`${frappe.utils.icon("eye", "xs")} ${__("Preview — showing exactly what {0} would see. Accepting a quotation or paying here is reflected in the ERP immediately.", [`<b>${frappe.utils.escape_html(label)}</b>`])}`);
	};
	frappe.xcall("frappe.client.get_list", { doctype: "Customer", filters: { disabled: 0, is_internal_customer: 0 }, fields: ["name", "customer_name"], order_by: "customer_name asc", limit_page_length: 500 })
		.then((rows) => {
			$sel.html(rows.map((r) => `<option value="${frappe.utils.escape_html(r.name)}">${frappe.utils.escape_html(r.customer_name)}</option>`).join(""));
			const pick = rows.find((r) => r.name === "Gulf Trading LLC") || rows[0];
			if (!pick) return v.$body.html(`<div class="hsx-empty">${__("There are no customers yet.")}</div>`);
			$sel.val(pick.name);
			show(pick.name, pick.customer_name);
		});
	$sel.on("change", () => show($sel.val(), $sel.find("option:selected").text()));
};
