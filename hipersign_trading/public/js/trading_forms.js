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
					frappe.xcall("frappe.desk.form.utils.add_comment", {
						reference_doctype: "Lead", reference_name: frm.doc.name, content: `<b>${v.type}</b> — ${frappe.utils.escape_html(v.text)}`,
						comment_email: frappe.session.user, comment_by: frappe.session.user_fullname,
					}).then(() => {
						frm.set_value({ hs_pipeline_stage: v.stage, hs_next_follow_up: v.next, hs_next_action: v.next_action });
						frm.save();
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
				frappe.call({ method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry", args: { dt: "Sales Order", dn: frm.doc.name } })
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
