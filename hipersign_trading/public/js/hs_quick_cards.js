// Hipersign ERP v1.5.6 — quick cards: the prototype's short "New …" cards for 13 masters.
// They replace Frappe's quick entry for these doctypes (from a Link field's "Create a new …", the + New panel and the
// lists' New · Quick), save through hipersign_trading.api.quick_cards.create, and hand what was typed to the full
// form ("Standard / Detailed form") and back (Form mode → Quick on a draft).
frappe.provide("hipersign.qc");

const M = "@meta"; // Select options read from the doctype, so edited Hipersign lists show

// fieldname = the value sent to the server; doc = the field on the full form that holds the same value
hipersign.qc.CARDS = {
	Lead: { title: __("New lead"), sub: __("Company, contact and what they are interested in"), fields: [
		{ fieldname: "company_name", label: __("Company / client"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "lead_name", label: __("Contact person"), fieldtype: "Data", reqd: 1, doc: "first_name" },
		{ fieldname: "mobile_no", label: __("Mobile / WhatsApp"), fieldtype: "Data", options: "Phone", reqd: 1 },
		{ fieldname: "email_id", label: __("Email"), fieldtype: "Data", options: "Email" },
		{ fieldname: "hs_emirate", label: __("Emirate"), fieldtype: "Select", options: M },
		{ fieldtype: "Column Break" },
		{ fieldname: "hs_interested_in", label: __("Interested in"), fieldtype: "Small Text", reqd: 1 },
		{ fieldname: "utm_source", label: __("Source"), fieldtype: "Link", options: "UTM Source" },
		{ fieldname: "hs_estimated_value", label: __("Estimated value (AED)"), fieldtype: "Currency" },
		{ fieldtype: "Section Break" },
		{ fieldname: "hs_expected_close", label: __("Expected close"), fieldtype: "Date" },
		{ fieldname: "lead_owner", label: __("Owner"), fieldtype: "Link", options: "User", get_query: () => ({ query: "hipersign_trading.api.crm.sales_users" }), default_fn: () => frappe.session.user },
		{ fieldname: "hs_pipeline_stage", label: __("Stage"), fieldtype: "Select", options: M, default: "New" },
		{ fieldtype: "Column Break" },
		{ fieldname: "hs_next_follow_up", label: __("Next follow-up"), fieldtype: "Date", default_fn: () => frappe.datetime.add_days(frappe.datetime.get_today(), 2) },
		{ fieldname: "hs_next_action", label: __("Next action"), fieldtype: "Data" },
	] },
	Customer: { title: __("New customer"), sub: __("Customer master — pricing group, terms and credit"), fields: [
		{ fieldname: "customer_name", label: __("Company / client name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "customer_group", label: __("Customer group"), fieldtype: "Link", options: "Customer Group", description: __("Decides the selling rate"),
			get_query: () => ({ filters: { is_group: 0 } }) },
		{ fieldname: "hs_market", label: __("Market"), fieldtype: "Select", options: "Local\nExport", default: "Local" },
		{ fieldname: "hs_emirate", label: __("Emirate / city (UAE)"), fieldtype: "Select", options: M, default: "Dubai", depends_on: "eval:doc.hs_market!=='Export'" },
		{ fieldname: "hs_country_city", label: __("Country (city) — export"), fieldtype: "Data", depends_on: "eval:doc.hs_market==='Export'" },
		{ fieldname: "default_currency", label: __("Invoice currency"), fieldtype: "Link", options: "Currency", depends_on: "eval:doc.hs_market==='Export'" },
		{ fieldtype: "Column Break" },
		{ fieldname: "contact_person", label: __("Contact person"), fieldtype: "Data", reqd: 1, nodoc: 1 },
		{ fieldname: "mobile_no", label: __("Mobile / WhatsApp"), fieldtype: "Data", options: "Phone", reqd: 1 },
		{ fieldname: "email_id", label: __("Email"), fieldtype: "Data", options: "Email" },
		{ fieldname: "tax_id", label: __("TRN"), fieldtype: "Data", description: __("15 digits — needed before the first tax invoice") },
		{ fieldtype: "Section Break" },
		{ fieldname: "credit_limit", label: __("Credit limit (AED)"), fieldtype: "Currency", nodoc: 1, description: __("New or higher limits go to the Finance Manager for approval") },
		{ fieldname: "payment_terms", label: __("Payment terms"), fieldtype: "Link", options: "Payment Terms Template" },
		{ fieldtype: "Column Break" },
		{ fieldname: "hs_lead_source", label: __("Lead source"), fieldtype: "Link", options: "UTM Source" },
	] },
	Supplier: { title: __("New supplier"), sub: __("Supplier register"), fields: [
		{ fieldname: "supplier_name", label: __("Supplier name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "hs_supplier_kind", label: __("Supplier type"), fieldtype: "Select", options: M, default: "Goods supplier",
			description: __("Goods suppliers appear on purchase orders; the rest are import service providers") },
		{ fieldname: "country", label: __("Country (city)"), fieldtype: "Data", reqd: 1, nodoc: 1, placeholder: "China (Ningbo)" },
		{ fieldname: "default_currency", label: __("Order currency"), fieldtype: "Link", options: "Currency", default: "USD" },
		{ fieldname: "payment_terms", label: __("Payment terms"), fieldtype: "Link", options: "Payment Terms Template" },
		{ fieldname: "hs_incoterm", label: __("Default incoterm"), fieldtype: "Link", options: "Incoterm" },
		{ fieldtype: "Column Break" },
		{ fieldname: "contact_person", label: __("Contact person"), fieldtype: "Data", reqd: 1, nodoc: 1 },
		{ fieldname: "mobile_no", label: __("Phone / WhatsApp"), fieldtype: "Data", options: "Phone" },
		{ fieldname: "email_id", label: __("Email"), fieldtype: "Data", options: "Email" },
		{ fieldname: "tax_id", label: __("TRN (UAE suppliers)"), fieldtype: "Data", description: __("15 digits — optional") },
		{ fieldname: "bank", label: __("Supplier bank"), fieldtype: "Link", options: "Bank", nodoc: 1 },
		{ fieldname: "iban", label: __("Supplier bank IBAN"), fieldtype: "Data", nodoc: 1, description: __("Optional — for payments") },
	] },
	Item: { title: __("New item"), sub: __("Item master — pricing, HS code and barcode"), fields: [
		{ fieldname: "item_name", label: __("Item name (English)"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "hs_item_name_ar", label: __("Item name (Arabic)"), fieldtype: "Data", description: __("Shown on bilingual documents") },
		{ fieldname: "item_group", label: __("Category"), fieldtype: "Link", options: "Item Group", get_query: () => ({ filters: { is_group: 0 } }) },
		{ fieldname: "stock_uom", label: __("Unit"), fieldtype: "Link", options: "UOM", default: "Nos" },
		{ fieldname: "customs_tariff_number", label: __("HS code"), fieldtype: "Data", description: __("Used for customs and duty") },
		{ fieldtype: "Column Break" },
		{ fieldname: "country_of_origin", label: __("Country of origin"), fieldtype: "Link", options: "Country" },
		{ fieldname: "standard_cost", label: __("Standard cost (AED)"), fieldtype: "Currency", reqd: 1, doc: "valuation_rate" },
		{ fieldname: "standard_rate", label: __("Standard selling price (AED)"), fieldtype: "Currency", reqd: 1, nodoc: 1 },
		{ fieldname: "is_stock_item", label: __("Kept in stock"), fieldtype: "Check", default: 1, description: __("Untick for a service (installation, freight, labour…)") },
		{ fieldname: "reorder_level", label: __("Reorder level"), fieldtype: "Int", default: 20, nodoc: 1, depends_on: "is_stock_item" },
		{ fieldname: "default_warehouse", label: __("Default warehouse"), fieldtype: "Link", options: "Warehouse", nodoc: 1, depends_on: "is_stock_item",
			get_query: () => ({ filters: { is_group: 0 } }) },
	] },
	Warehouse: { title: __("New warehouse"), sub: __("Stock location"), fields: [
		{ fieldname: "warehouse_name", label: __("Warehouse name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "warehouse_type", label: __("Type"), fieldtype: "Link", options: "Warehouse Type" },
		{ fieldname: "hs_emirate", label: __("Emirate"), fieldtype: "Select", options: M, default: "Dubai" },
		{ fieldtype: "Column Break" },
		{ fieldname: "address_line_1", label: __("Location / address"), fieldtype: "Data", reqd: 1 },
		{ fieldname: "hs_capacity_pallets", label: __("Capacity (pallet positions)"), fieldtype: "Int" },
		{ fieldname: "hs_in_charge", label: __("Warehouse in-charge"), fieldtype: "Data" },
	] },
	Driver: { title: __("New driver & vehicle"), sub: __("Delivery driver and the vehicle they drive"), fields: [
		{ fieldname: "full_name", label: __("Driver name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "cell_number", label: __("Mobile"), fieldtype: "Data", options: "Phone" },
		{ fieldtype: "Column Break" },
		{ fieldname: "license_plate", label: __("Vehicle plate"), fieldtype: "Data", reqd: 1, nodoc: 1, placeholder: "DXB K 12345" },
		{ fieldname: "hs_vehicle_type", label: __("Vehicle type"), fieldtype: "Select", options: "@meta:Vehicle", default: "Van", nodoc: 1 },
	] },
	Employee: { title: __("New employee"), sub: __("Employee master — salary for WPS and UAE document expiries"), size: "large", fields: [
		{ fieldname: "employee_name", label: __("Full name"), fieldtype: "Data", reqd: 1, doc: "first_name", name_field: 1 },
		{ fieldname: "designation", label: __("Designation"), fieldtype: "Link", options: "Designation", reqd: 1 },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldtype: "Column Break" },
		{ fieldname: "date_of_joining", label: __("Joining date"), fieldtype: "Date", default_fn: () => frappe.datetime.get_today() },
		{ fieldname: "gender", label: __("Gender"), fieldtype: "Link", options: "Gender", reqd: 1 },
		{ fieldname: "date_of_birth", label: __("Date of birth"), fieldtype: "Date", reqd: 1 },
		{ fieldtype: "Column Break" },
		{ fieldname: "cell_number", label: __("Mobile"), fieldtype: "Data", options: "Phone", reqd: 1 },
		{ fieldname: "personal_email", label: __("Email"), fieldtype: "Data", options: "Email" },
		{ fieldtype: "Section Break", label: __("Salary") },
		{ fieldname: "hs_basic_salary", label: __("Basic salary (AED)"), fieldtype: "Currency", reqd: 1 },
		{ fieldname: "hs_housing_allowance", label: __("Housing allowance"), fieldtype: "Currency" },
		{ fieldtype: "Column Break" },
		{ fieldname: "hs_transport_allowance", label: __("Transport allowance"), fieldtype: "Currency" },
		{ fieldname: "hs_other_allowance", label: __("Other allowance"), fieldtype: "Currency" },
		{ fieldtype: "Column Break" },
		{ fieldname: "iban", label: __("Salary account IBAN (WPS)"), fieldtype: "Data" },
		{ fieldtype: "Section Break", label: __("Document expiries") },
		{ fieldname: "hs_visa_expiry", label: __("Residence visa expiry"), fieldtype: "Date" },
		{ fieldname: "hs_emirates_id_expiry", label: __("Emirates ID expiry"), fieldtype: "Date" },
		{ fieldtype: "Column Break" },
		{ fieldname: "hs_labour_card_expiry", label: __("Labour card expiry"), fieldtype: "Date" },
		{ fieldname: "valid_upto", label: __("Passport expiry"), fieldtype: "Date" },
	] },
	Asset: { title: __("New fixed asset"), sub: __("Asset register — cost, custodian and renewals"), size: "large", fields: [
		{ fieldname: "asset_name", label: __("Asset name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "asset_category", label: __("Category"), fieldtype: "Link", options: "Asset Category", reqd: 1 },
		{ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Location", reqd: 1 },
		{ fieldname: "custodian", label: __("Custodian"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" },
		{ fieldtype: "Column Break" },
		{ fieldname: "purchase_date", label: __("Purchase date"), fieldtype: "Date", default_fn: () => frappe.datetime.get_today() },
		{ fieldname: "net_purchase_amount", label: __("Cost (AED, excl. VAT)"), fieldtype: "Currency", reqd: 1 },
		{ fieldname: "residual_value", label: __("Residual value (AED)"), fieldtype: "Currency", nodoc: 1 },
		{ fieldname: "useful_life", label: __("Useful life (months)"), fieldtype: "Int", default: 60, nodoc: 1 },
		{ fieldtype: "Section Break", label: __("Vehicles and renewals") },
		{ fieldname: "hs_plate_no", label: __("Plate no. (vehicles)"), fieldtype: "Data" },
		{ fieldname: "hs_registration_expiry", label: __("Registration (Mulkiya) expiry"), fieldtype: "Date" },
		{ fieldtype: "Column Break" },
		{ fieldname: "insurance_end_date", label: __("Insurance expiry"), fieldtype: "Date" },
		{ fieldname: "hs_next_service", label: __("Next service"), fieldtype: "Date" },
	] },
	Contact: { title: __("New contact"), sub: __("A person at a customer or supplier"), link: 1, fields: [
		{ fieldname: "full_name", label: __("Contact name"), fieldtype: "Data", reqd: 1, doc: "first_name", name_field: 1 },
		{ fieldname: "designation", label: __("Designation"), fieldtype: "Data", options: "", placeholder: __("e.g. Purchasing, Accounts, Site engineer") },
		{ fieldname: "mobile_no", label: __("Mobile / WhatsApp"), fieldtype: "Data", options: "Phone", reqd: 1 },
		{ fieldtype: "Column Break" },
		{ fieldname: "email_id", label: __("Email"), fieldtype: "Data", options: "Email" },
		{ fieldname: "hs_receives_reports", label: __("Receives reports & statements"), fieldtype: "Check", default: 1 },
		{ fieldname: "is_primary_contact", label: __("Primary contact"), fieldtype: "Check" },
	] },
	Address: { title: __("New address"), sub: __("Billing, delivery or site address"), link: 1, fields: [
		{ fieldname: "address_title", label: __("Address name"), fieldtype: "Data", reqd: 1, name_field: 1, placeholder: __("e.g. JLT site, Main office") },
		{ fieldname: "address_type", label: __("Type"), fieldtype: "Select", options: M, default: "Delivery" },
		{ fieldname: "address_line1", label: __("Address"), fieldtype: "Data", reqd: 1 },
		{ fieldtype: "Column Break" },
		{ fieldname: "hs_emirate", label: __("Emirate"), fieldtype: "Select", options: M, default: "Dubai" },
		{ fieldname: "hs_site_contact", label: __("Site contact & phone"), fieldtype: "Data" },
		{ fieldname: "address_line2", label: __("Map pin / landmark"), fieldtype: "Data" },
	] },
	"Customer Group": { title: __("New customer group"), sub: __("Pricing group — discount, terms and credit"), fields: [
		{ fieldname: "customer_group_name", label: __("Group name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "discount_percentage", label: __("Discount on Standard Selling (%)"), fieldtype: "Percent", nodoc: 1 },
		{ fieldtype: "Column Break" },
		{ fieldname: "payment_terms", label: __("Default payment terms"), fieldtype: "Link", options: "Payment Terms Template" },
		{ fieldname: "credit_limit", label: __("Default credit limit (AED)"), fieldtype: "Currency", nodoc: 1 },
	] },
	"Payment Terms Template": { title: __("New payment terms"), sub: __("Advance and balance"), fields: [
		{ fieldname: "template_name", label: __("Template name"), fieldtype: "Data", reqd: 1, name_field: 1, placeholder: __("e.g. 30% advance, balance 60 days") },
		{ fieldname: "advance_percent", label: __("Advance (%)"), fieldtype: "Percent", nodoc: 1 },
		{ fieldtype: "Column Break" },
		{ fieldname: "credit_days", label: __("Balance due in (days)"), fieldtype: "Int", default: 30, nodoc: 1 },
		{ fieldname: "based_on", label: __("Counted from"), fieldtype: "Select", options: "Invoice date\nMonth end", default: "Invoice date", nodoc: 1 },
	] },
	"Bank Account": { title: __("New bank account"), sub: __("Company bank account — shown on invoices"), fields: [
		{ fieldname: "bank", label: __("Bank"), fieldtype: "Data", reqd: 1, nodoc: 1, placeholder: "Emirates NBD" },
		{ fieldname: "account_name", label: __("Account name"), fieldtype: "Data", reqd: 1, name_field: 1 },
		{ fieldname: "iban", label: __("IBAN"), fieldtype: "Data", reqd: 1, placeholder: "AE07 0331 2345 6789 0123 456" },
		{ fieldtype: "Column Break" },
		{ fieldname: "swift", label: __("SWIFT / BIC"), fieldtype: "Data", nodoc: 1 },
		{ fieldname: "currency", label: __("Currency"), fieldtype: "Link", options: "Currency", default: "AED", nodoc: 1 },
		{ fieldname: "is_default", label: __("Default account for invoices"), fieldtype: "Check" },
	] },
};

hipersign.qc.has = (dt) => !!hipersign.qc.CARDS[dt];

// card value ↔ full-form field
hipersign.qc.doc_field = (dt, df) => {
	if (df.nodoc || !df.fieldname) return null;
	const f = df.doc || df.fieldname;
	return frappe.meta.has_field(dt, f) ? f : null;
};
hipersign.qc.from_doc = function (dt, doc) {
	const out = {};
	(hipersign.qc.CARDS[dt].fields || []).forEach((df) => {
		const f = hipersign.qc.doc_field(dt, df);
		if (f && doc[f] !== undefined && doc[f] !== null && doc[f] !== "") out[df.fieldname] = doc[f];
	});
	if (dt === "Lead" && doc.last_name && out.lead_name) out.lead_name += " " + doc.last_name;
	if (dt === "Employee" && doc.last_name && out.employee_name) out.employee_name += " " + doc.last_name;
	if (dt === "Contact" && doc.last_name && out.full_name) out.full_name += " " + doc.last_name;
	return out;
};
hipersign.qc.full_form = function (dt, values) {
	frappe.model.with_doctype(dt, () => {
		const doc = frappe.model.get_new_doc(dt);
		(hipersign.qc.CARDS[dt].fields || []).forEach((df) => {
			const f = hipersign.qc.doc_field(dt, df), v = values[df.fieldname];
			if (f && v !== undefined && v !== null && v !== "") doc[f] = v;
		});
		Object.entries(values || {}).forEach(([k, v]) => { if (!(k in doc) && frappe.meta.has_field(dt, k)) doc[k] = v; });
		frappe.set_route("Form", dt, doc.name);
	});
};

hipersign.qc.resolve = function (dt, fields) {
	return fields.map((df) => {
		const f = Object.assign({}, df);
		if (typeof f.options === "string" && f.options.startsWith(M)) {
			const src = f.options.slice(M.length + 1) || dt, field = frappe.meta.get_docfield(src, f.fieldname === "hs_vehicle_type" ? "hs_vehicle_type" : f.fieldname);
			f.options = (field && field.options) || "";
		}
		if (f.default_fn) { f.default = f.default_fn(); delete f.default_fn; }
		delete f.doc; delete f.nodoc; delete f.name_field;
		return f;
	});
};

// the record a new address or contact belongs to: the form it was opened from, or what the caller passed
hipersign.qc.link_of = function (values) {
	if (values.link_doctype && values.link_name) return [values.link_doctype, values.link_name];
	const dl = frappe.dynamic_link;
	if (dl && dl.doc && dl.doc.name && !String(dl.doc.name).startsWith("new-")) return [dl.doctype || dl.doc.doctype, dl.doc.name];
	if (window.cur_frm && ["Customer", "Supplier", "Lead"].includes(cur_frm.doctype) && !cur_frm.is_new()) return [cur_frm.doctype, cur_frm.doc.name];
	return [null, null];
};

hipersign.qc.open = function (dt, opts) {
	opts = opts || {};
	const card = hipersign.qc.CARDS[dt];
	const values = Object.assign({}, opts.values || {});
	return new Promise((resolve) => frappe.model.with_doctype(dt, () => {
		const deps = [];
		if (dt === "Driver") deps.push(new Promise((r) => frappe.model.with_doctype("Vehicle", r)));
		Promise.all(deps).then(() => {
			const fields = hipersign.qc.resolve(dt, card.fields);
			const name_field = card.fields.find((f) => f.name_field);
			if (opts.name_value && name_field && !values[name_field.fieldname]) values[name_field.fieldname] = opts.name_value;
			let link = [null, null];
			if (card.link) {
				link = hipersign.qc.link_of(values);
				fields.push({ fieldtype: "Section Break" },
					{ fieldname: "link_doctype", label: __("For"), fieldtype: "Select", options: "\nCustomer\nSupplier\nLead", default: link[0] || "" },
					{ fieldtype: "Column Break" },
					{ fieldname: "link_name", label: __("Name"), fieldtype: "Dynamic Link", options: "link_doctype", default: link[1] || "" });
			}
			fields.forEach((f) => { if (f.fieldname && values[f.fieldname] !== undefined) f.default = values[f.fieldname]; });
			const service = dt === "Item" && values.is_stock_item !== undefined && !+values.is_stock_item;
			const d = new frappe.ui.Dialog({
				title: service ? __("New service") : card.title,
				size: card.size || "large",
				fields: [{ fieldtype: "HTML", fieldname: "hs_sub", options: `<p class="text-muted small" style="margin-top:-6px">${frappe.utils.escape_html(card.sub || "")}</p>` }, ...fields],
				primary_action_label: __("Save"),
				primary_action: (v) => {
					d.disable_primary_action();
					frappe.xcall("hipersign_trading.api.quick_cards.create", { doctype: dt, values: v, link_doctype: v.link_doctype || null, link_name: v.link_name || null })
						.then((r) => {
							d.hide();
							frappe.model.sync(r.doc);
							frappe.show_alert({ message: __("{0} {1} saved", [__(dt), r.title]), indicator: "green" }, 5);
							if (opts.after_insert) opts.after_insert(r.doc);
							else if (opts.open !== false) frappe.set_route("Form", dt, r.name);
							if (window.cur_frm && link[1] && cur_frm.doc.name === link[1]) cur_frm.reload_doc();
							if (window.cur_list && cur_list.doctype === dt) cur_list.refresh();
							resolve(r.doc);
						})
						.catch(() => {})
						.finally(() => d.enable_primary_action());
				},
				secondary_action_label: __("Standard / Detailed form"),
				secondary_action: () => {
					const v = d.get_values(true) || {};
					d.hide();
					const go = () => hipersign.qc.full_form(dt, v);
					if (hipersign.fm && hipersign.fm.COVERED.includes(dt)) hipersign.fm.remember(dt, "Standard").then(go); else go();
				},
			});
			d.$wrapper.addClass("hs-quick-card");
			d.show();
			resolve(d);
		});
	}));
};

// Frappe's quick entry → the card (Link "Create a new …", frappe.new_doc, the list's New in Quick mode)
hipersign.qc._orig_make_quick_entry = frappe.ui.form.make_quick_entry;
frappe.ui.form.make_quick_entry = function (doctype, after_insert, init_callback, doc, force, skip_insert) {
	if (!hipersign.qc.has(doctype) || skip_insert || init_callback || (frappe.boot.hipersign || {}).no_quick_cards) {
		return hipersign.qc._orig_make_quick_entry.apply(this, arguments);
	}
	const from_link = frappe._from_link;
	const ro = frappe.route_options || {};
	frappe.route_options = null;
	const quick = from_link || after_insert || !hipersign.fm || !hipersign.fm.COVERED.includes(doctype) || hipersign.fm.mode(doctype) === "Quick";
	if (!quick) {
		const vals = Object.assign({}, ro);
		delete vals.name_field;
		return new Promise((resolve) => { hipersign.qc.full_form(doctype, vals); resolve(); });
	}
	const values = Object.assign({}, ro);
	const name_value = values.name_field;
	delete values.name_field;
	if (doc) Object.assign(values, hipersign.qc.from_doc(doctype, doc));
	return hipersign.qc.open(doctype, {
		values, name_value,
		after_insert: after_insert ? (d) => { frappe._from_link = null; after_insert(d); } : null,
		open: !from_link,
	});
};
