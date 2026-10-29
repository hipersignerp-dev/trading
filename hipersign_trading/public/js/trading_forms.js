// Form behaviour for Hipersign trading flows.
frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (frm.doc.hs_approval_reason && frm.doc.docstatus === 0) {
			frm.dashboard.add_comment(__("Approval needed: {0}", [frm.doc.hs_approval_reason.replace(/\n/g, " · ")]), "orange", true);
		}
		if (frm.doc.docstatus === 1 && frm.doc.hs_is_export) {
			frm.add_custom_button(__("Export shipment"), () => {
				frappe.db.get_value("Export Shipment", { sales_order: frm.doc.name }, "name").then(({ message }) => {
					if (message && message.name) return frappe.set_route("Form", "Export Shipment", message.name);
					frappe.new_doc("Export Shipment", { sales_order: frm.doc.name, company: frm.doc.company });
				});
			}, __("Create"));
		}
	},
});

frappe.ui.form.on("Lead", {
	setup(frm) {
		frm.set_query("lead_owner", () => ({ query: "hipersign_trading.api.crm.sales_users" }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("WhatsApp"), () => hipersign.send_whatsapp("Lead", frm.doc.name), __("Contact"));
		frm.add_custom_button(__("Log activity"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Log activity"),
				fields: [
					{ fieldtype: "Select", fieldname: "type", label: __("Activity"), options: "Call\nMeeting\nSite visit\nWhatsApp\nEmail\nNote", default: "Call" },
					{ fieldtype: "Select", fieldname: "stage", label: __("Stage after this"), options: "New\nContacted\nQualified\nProposal\nNegotiation", default: frm.doc.hs_pipeline_stage },
					{ fieldtype: "Small Text", fieldname: "text", label: __("What happened"), reqd: 1 },
					{ fieldtype: "Date", fieldname: "next", label: __("Next follow-up"), default: frappe.datetime.add_days(frappe.datetime.get_today(), 3) },
					{ fieldtype: "Data", fieldname: "next_action", label: __("Next action") },
				],
				primary_action_label: __("Save"),
				primary_action(v) {
					// v1.5.6 (CRM-01): one server call saves the note, stage, next follow-up and next action together
					frappe.xcall("hipersign_trading.api.crm.log_activity", {
						lead: frm.doc.name, activity: v.type, text: v.text, stage: v.stage, next_follow_up: v.next, next_action: v.next_action,
					}).then(() => {
						frm.reload_doc();
						d.hide();
					});
				},
			});
			d.show();
		}, __("Contact"));
	},
});

frappe.ui.form.on("Customer", {
	hs_market(frm) {
		if (frm.doc.hs_market === "Export" && !frm.doc.default_currency) frm.set_value("default_currency", "USD");
	},
});

// ---------------------------------------------------------------- v1.2
frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		const st = frm.doc.hs_advance_status;
		if (frm.doc.docstatus === 1 && ["Waiting", "Part received"].includes(st)) {
			frm.dashboard.add_comment(__("Advance of {0} not fully received — picking and delivery are on hold until it is.",
				[format_currency(frm.doc.hs_advance_required, frm.doc.currency)]), "orange", true);
			frm.add_custom_button(__("Receive advance"), () => {
				frappe.call({ method: "hipersign_trading.overrides.advances.advance_payment_entry", args: { sales_order: frm.doc.name } })
					.then((r) => { const doc = frappe.model.sync(r.message)[0]; frappe.set_route("Form", doc.doctype, doc.name); });
			}, __("Create"));
		} else if (frm.doc.docstatus === 1 && st === "Received") {
			frm.dashboard.add_comment(__("Advance received — the order can be delivered."), "green", true);
		}
	},
});

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.is_return || !(frm.doc.outstanding_amount > 0)) return;
		if (frm.doc.hs_collection_stage) frm.dashboard.add_comment(__("Collection stage: {0}{1}", [__(frm.doc.hs_collection_stage),
			frm.doc.hs_promise_date ? " · " + __("promised {0}", [frappe.datetime.str_to_user(frm.doc.hs_promise_date)]) : ""]), "orange", true);
		frm.add_custom_button(__("Promise to pay"), () => frappe.prompt([
			{ fieldtype: "Date", fieldname: "d", label: __("Customer promised to pay on"), reqd: 1 },
			{ fieldtype: "Currency", fieldname: "a", label: __("Amount"), default: frm.doc.outstanding_amount },
			{ fieldtype: "Small Text", fieldname: "n", label: __("Note") }],
			(v) => frappe.db.set_value("Sales Invoice", frm.doc.name, { hs_promise_date: v.d, hs_promise_amount: v.a, hs_collection_note: v.n })
				.then(() => frm.reload_doc()), __("Promise to pay")), __("Collection"));
		frm.add_custom_button(__("Send reminder on WhatsApp"), () => hipersign.send_whatsapp("Sales Invoice", frm.doc.name), __("Collection"));
	},
});

frappe.ui.form.on("Customer", {
	refresh(frm) {
		const s = frm.doc.hs_kyc_status;
		if (["Expired", "Blocked"].includes(s)) frm.dashboard.add_comment(__("KYC {0} — new sales orders are blocked until it is resolved.", [__(s).toLowerCase()]), "red", true);
		if (frm.doc.is_internal_customer) frm.dashboard.add_comment(__("Group company — invoices to this customer can be mirrored as a purchase invoice in {0}.", [frm.doc.represents_company || ""]), "blue", true);
	},
});

// ---------------------------------------------------------------- v1.5.6: ERPNext's Stock Reservation dialog offers only the
// order's own company's warehouses (it used to list every company's)
$(document).on("shown.bs.modal", ".modal", () => {
	const d = window.cur_dialog, frm = window.cur_frm;
	if (!d || d.__hs_wh || !frm || frm.doctype !== "Sales Order" || !d.fields_dict || !d.fields_dict.set_warehouse || !d.fields_dict.items) return;
	d.__hs_wh = true;
	const q = () => ({ filters: [["Warehouse", "is_group", "!=", 1], ["Warehouse", "company", "=", frm.doc.company]] });
	d.fields_dict.set_warehouse.get_query = q;
	d.fields_dict.set_warehouse.df.get_query = q;
	const wh = (d.fields_dict.items.df.fields || []).find((f) => f.fieldname === "warehouse");
	if (wh) wh.get_query = q;
	if (d.fields_dict.items.grid) d.fields_dict.items.grid.refresh();
});

// ---------------------------------------------------------------- v1.5.6: trading-only Create menus
// ERPNext offers manufacturing, project and maintenance documents from sales and buying forms; a trading company does
// not use them, so they are taken out of the Create menu (they stay available from their own lists).
hipersign.TRIM_CREATE = ["Work Order", "Production Plan", "Project", "Request for Raw Materials", "Subscription", "Maintenance Visit",
	"Maintenance Schedule", "Subcontracting Order", "Subcontracting Inward Order", "Installation Note", "Quality Inspection", "Blanket Order"];
hipersign.trim_create = function (frm) {
	const run = () => hipersign.TRIM_CREATE.forEach((l) => {
		try { frm.remove_custom_button(__(l), __("Create")); } catch (e) { /* not on this form */ }
	});
	run();
	setTimeout(run, 300);
	setTimeout(run, 1200);
};
["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Purchase Order", "Purchase Receipt", "Purchase Invoice", "Material Request", "Supplier Quotation"]
	.forEach((dt) => frappe.ui.form.on(dt, { refresh: hipersign.trim_create }));
