"""v1.7.0: the prototype's create forms ("New lead", "New quotation", "New sales order" …) — one modal, drawn by
public/js/hs_create.js from a field list, with the line table, totals and credit check inside the modal.

options()      the choice lists a form needs (customers, items with price and stock, price lists, terms …)
party()        what changes when the customer or supplier is picked: contacts, addresses, group discount, terms,
               credit limit and exposure, price list, currency
rates()        the price each line will really get (ERPNext pricing: price list + the group's pricing rule), the stock
               available and the valuation rate for the margin column
save()         builds the ERPNext document and saves it — or submits it through the approval workflow

Everything is read and written with the user's own permissions.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, nowtime, today

from hipersign_trading.api.quick import _rate_preview, _submit
from hipersign_trading.utils import user_company

LIMIT = 500


def _names(doctype, filters=None, label=None, order_by=None, extra=None):
	if not frappe.has_permission(doctype, "read"):
		return []
	fields = ["name"] + ([label] if label else []) + (extra or [])
	rows = frappe.get_list(doctype, filters=filters or {}, fields=fields, order_by=order_by or "name asc", limit_page_length=LIMIT)
	return [dict(r, label=(r.get(label) or r.name) if label else r.name) for r in rows]


def _meta_options(doctype, fieldname):
	df = frappe.get_meta(doctype).get_field(fieldname)
	return [o for o in (df.options or "").split("\n") if o] if df else []


def _sales_people():
	return [{"name": r.name, "label": r.sales_person_name or r.name} for r in frappe.get_all("Sales Person", filters={"is_group": 0, "enabled": 1},
		fields=["name", "sales_person_name"], order_by="sales_person_name asc")]


def _company():
	return user_company()


@frappe.whitelist()
def options(kind, company=None):
	"""Choice lists for one form. v1.8.0: a window opened from a document of another company of the group (Create PO from
	a project's material request) passes that company."""
	if not company or not frappe.db.exists("Company", company) or not frappe.has_permission("Company", "read", company):
		company = _company()
	ccy = frappe.get_cached_value("Company", company, "default_currency") if company else "AED"
	o = {"company": company, "currency": ccy, "today": today()}
	selling = kind in ("quotation", "sales_order", "delivery_note", "invoice", "receive_payment", "lead", "customer")
	buying = kind in ("purchase_order", "supplier")
	if kind in ("quotation", "sales_order", "delivery_note", "invoice", "receive_payment"):
		o["customers"] = _names("Customer", {"disabled": 0}, "customer_name", "customer_name asc", ["customer_group", "default_currency"])
	if kind == "quotation":
		o["leads"] = _names("Lead", {"status": ["not in", ["Converted", "Do Not Contact"]]}, "company_name", "modified desc")
	if kind in ("purchase_order",):
		o["suppliers"] = _names("Supplier", {"disabled": 0, "hs_supplier_kind": ["in", ["", "Goods supplier", None]]} if frappe.get_meta("Supplier").has_field("hs_supplier_kind") else {"disabled": 0},
			"supplier_name", "supplier_name asc", ["default_currency"])
		if not o["suppliers"]:
			o["suppliers"] = _names("Supplier", {"disabled": 0}, "supplier_name", "supplier_name asc", ["default_currency"])
		# the suppliers ordered from most often first (service providers rarely get purchase orders)
		used = dict(frappe.db.sql("select supplier, count(*) from `tabPurchase Order` where docstatus < 2 group by supplier"))
		o["suppliers"].sort(key=lambda r: (-used.get(r["name"], 0), r["label"]))
	if kind in ("quotation", "sales_order", "delivery_note", "invoice", "purchase_order"):
		o["items"] = _items(buying=kind == "purchase_order")
		pl_filter = {"enabled": 1, "buying": 1} if buying else {"enabled": 1, "selling": 1}
		pls = frappe.get_all("Price List", filters=pl_filter, fields=["name", "currency"], order_by="name asc")
		counts = {r[0]: r[1] for r in frappe.db.sql("select price_list, count(*) from `tabItem Price` group by price_list")}
		o["price_lists"] = [{"name": p.name, "label": f"{p.name} · {p.currency} · {_('{0} items').format(counts.get(p.name, 0))}", "currency": p.currency} for p in pls]
		o["default_price_list"] = frappe.db.get_single_value("Buying Settings" if buying else "Selling Settings", "buying_price_list" if buying else "selling_price_list")
		o["terms"] = _names("Payment Terms Template", None, None, "name asc")
		o["warehouses"] = _names("Warehouse", {"company": company, "is_group": 0, "disabled": 0}, None, "name asc")
		o["currencies"] = [c.name for c in frappe.get_all("Currency", filters={"enabled": 1}, order_by="name asc")]
		o["incoterms"] = [c.name for c in frappe.get_all("Incoterm", order_by="name asc")] if frappe.db.table_exists("Incoterm") else []
		o["vat_rate"] = _vat_rate(company, buying)
	if selling and kind != "lead":
		o["sales_people"] = _sales_people()
	if kind == "quotation":
		o["delivery_periods"] = _meta_options("Quotation", "hs_delivery_period")
		o["warranty"] = _meta_options("Quotation", "hs_warranty_months")
		o["groups"] = _names("Customer Group", {"is_group": 0}, None, "name asc")
		o["sources"] = _names("UTM Source", None, None, "name asc")
		o["emirates"] = _meta_options("Customer", "hs_emirate")
	if kind == "purchase_order":
		o["modes"] = _meta_options("Purchase Order", "hs_shipment_mode")
		o["cost_centers"] = _names("Cost Center", {"company": company, "is_group": 0}, "cost_center_name", "cost_center_name asc")
	if kind == "receive_payment":
		o["modes"] = [m.name for m in frappe.get_all("Mode of Payment", filters={"enabled": 1}, order_by="name asc")]
		o["accounts"] = _names("Account", {"company": company, "account_type": ["in", ["Bank", "Cash"]], "is_group": 0}, "account_name", "account_name asc")
	return o


def _items(buying=False):
	f = {"disabled": 0, "has_variants": 0, ("is_purchase_item" if buying else "is_sales_item"): 1}
	rows = frappe.get_list("Item", filters=f, fields=["name", "item_name", "stock_uom", "is_stock_item", "item_group", "standard_rate", "valuation_rate"],
		order_by="name asc", limit_page_length=LIMIT)
	stock = {r[0]: flt(r[1]) for r in frappe.db.sql("select item_code, sum(actual_qty - reserved_stock) from tabBin group by item_code")}
	return [{"name": r.name, "label": f"{r.name} — {r.item_name}", "item_name": r.item_name, "uom": r.stock_uom, "stock": r.is_stock_item,
		"available": stock.get(r.name, 0) if r.is_stock_item else None, "group": r.item_group} for r in rows]


def _is_foreign(company, buying, party):
	"""Export customers (zero-rated) and overseas suppliers (no UAE VAT on the order) get no VAT template."""
	if not party:
		return False
	if not buying:
		if not frappe.db.exists("Customer", party):
			return False
		c = frappe.db.get_value("Customer", party, ["tax_category", "hs_market"] if frappe.get_meta("Customer").has_field("hs_market") else ["tax_category"], as_dict=True) or {}
		return (c.get("hs_market") == "Export") or "export" in (c.get("tax_category") or "").lower()
	country = frappe.db.get_value("Supplier", party, "country")
	return bool(country) and country != frappe.get_cached_value("Company", company, "country")


def _tax_template(company, buying=False, party=None):
	"""v1.7.1: the company's VAT template for a quick document — the export / zero-rated one for export customers,
	none for overseas suppliers, otherwise Hipersign Settings' local template, the default, or the company's standard VAT."""
	dt = "Purchase Taxes and Charges Template" if buying else "Sales Taxes and Charges Template"
	tpls = frappe.get_all(dt, filters={"company": company, "disabled": 0}, fields=["name", "title", "is_default"], order_by="is_default desc, name asc")
	if not tpls:
		return None

	def find(*words, exclude=("zero", "exempt", "excise", "export", "reverse")):
		for t in tpls:
			n = (t.title or t.name).lower()
			if all(w in n for w in words) and not any(x in n for x in exclude):
				return t.name

	if _is_foreign(company, buying, party):
		return None if buying else (find("export", exclude=()) or find("zero", exclude=()))
	if not buying and frappe.get_meta("Hipersign Settings").has_field("local_tax_template"):
		tpl = frappe.db.get_single_value("Hipersign Settings", "local_tax_template")
		if tpl and frappe.db.get_value(dt, tpl, "company") == company:
			return tpl
	default = next((t.name for t in tpls if t.is_default), None)
	return default or find("vat") or find("gst") or find("tax") or find()


def _template_rate(template, buying=False):
	if not template:
		return 0
	dt = "Purchase Taxes and Charges" if buying else "Sales Taxes and Charges"
	return flt(sum(flt(r) for r in frappe.get_all(dt, filters={"parent": template, "parenttype": dt + " Template"}, pluck="rate")))


def _vat_rate(company, buying=False, party=None):
	return _template_rate(_tax_template(company, buying, party), buying)


def _apply_tax(doc, company, buying, party):
	"""Fill the VAT rows when ERPNext's own rules (tax rule, party template) left the document without taxes."""
	if doc.get("taxes"):
		return
	# v1.7.3: a template picked on the form (Detailed mode) wins over the company's default
	tpl = doc.get("taxes_and_charges") or _tax_template(company, buying, party)
	if not tpl:
		return
	from erpnext.controllers.accounts_controller import get_taxes_and_charges

	doc.taxes_and_charges = tpl
	for row in get_taxes_and_charges("Purchase Taxes and Charges Template" if buying else "Sales Taxes and Charges Template", tpl) or []:
		doc.append("taxes", row)


@frappe.whitelist()
def party(kind, name):
	"""Contacts, addresses, group discount, terms, credit and price list for the picked customer / supplier / lead."""
	buying = kind == "purchase_order"
	if kind == "quotation" and frappe.db.exists("Lead", name) and not frappe.db.exists("Customer", name):
		ld = frappe.db.get_value("Lead", name, ["company_name", "lead_name", "mobile_no", "email_id"], as_dict=True)
		return {"lead": 1, "contacts": [{"name": "", "label": " · ".join(x for x in [ld.lead_name, ld.mobile_no] if x)}], "addresses": [], "group": "", "discount": 0}
	dt = "Supplier" if buying else "Customer"
	doc = frappe.get_doc(dt, name)
	doc.check_permission("read")
	company = _company()
	out = {"currency": doc.get("default_currency") or frappe.get_cached_value("Company", company, "default_currency"),
		"price_list": doc.get("default_price_list") or "", "terms": doc.get("payment_terms") or "", "incoterm": doc.get("hs_incoterm") or doc.get("hs_default_incoterm") or ""}
	links = frappe.get_all("Dynamic Link", filters={"link_doctype": dt, "link_name": name, "parenttype": ["in", ["Contact", "Address"]]}, fields=["parent", "parenttype"])
	cids = [l.parent for l in links if l.parenttype == "Contact"]
	aids = [l.parent for l in links if l.parenttype == "Address"]
	out["contacts"] = [{"name": c.name, "label": " · ".join(x for x in [c.full_name or c.first_name, c.designation] if x)}
		for c in frappe.get_all("Contact", filters={"name": ["in", cids or [""]]}, fields=["name", "full_name", "first_name", "designation", "is_primary_contact"], order_by="is_primary_contact desc")]
	out["addresses"] = [{"name": a.name, "label": " — ".join(x for x in [a.address_title, ", ".join(y for y in [a.address_line1, a.city] if y)] if x), "type": a.address_type,
		"shipping": a.is_shipping_address, "billing": a.is_primary_address}
		for a in frappe.get_all("Address", filters={"name": ["in", aids or [""]], "disabled": 0}, fields=["name", "address_title", "address_line1", "city", "address_type", "is_shipping_address", "is_primary_address"])]
	if not buying:
		out["group"] = doc.customer_group
		out["discount"] = flt(frappe.db.get_value("Pricing Rule", {"applicable_for": "Customer Group", "customer_group": doc.customer_group, "disable": 0, "selling": 1},
			"discount_percentage")) if doc.customer_group else 0
		limit = 0
		for r in doc.get("credit_limits") or []:
			if r.company == company:
				limit = flt(r.credit_limit)
		if not limit and doc.customer_group:
			limit = flt(frappe.db.get_value("Customer Credit Limit", {"parent": doc.customer_group, "parenttype": "Customer Group", "company": company}, "credit_limit"))
		out["credit_limit"] = limit
		out["exposure"] = _exposure(name, company)
		out["sales_person"] = (doc.get("sales_team") or [{}])[0].get("sales_person") if doc.get("sales_team") else ""
		out["market"] = doc.get("hs_market") or "Local"
	else:
		out["country"] = doc.country
	out["vat_rate"] = _vat_rate(company, buying, name)
	return out


def _exposure(customer, company):
	"""Unpaid invoices plus orders not yet invoiced (in company currency)."""
	unpaid = flt(frappe.db.sql("""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice` where customer=%s and company=%s and docstatus=1""", (customer, company))[0][0])
	open_so = flt(frappe.db.sql("""select sum(base_grand_total * (100 - per_billed) / 100) from `tabSales Order` where customer=%s and company=%s and docstatus=1
		and status not in ('Closed', 'Completed', 'On Hold')""", (customer, company))[0][0])
	return unpaid + open_so


@frappe.whitelist()
def rates(kind, party=None, items=None):
	"""Price, stock and valuation for the line items (the rate the saved document will use)."""
	items = frappe.parse_json(items) if isinstance(items, str) else (items or [])
	dt = {"quotation": "Quotation", "sales_order": "Sales Order", "purchase_order": "Purchase Order", "delivery_note": "Delivery Note", "invoice": "Sales Invoice"}.get(kind, "Sales Order")
	if kind == "quotation" and party and not frappe.db.exists("Customer", party):
		party = None
	out = {}
	from hipersign_trading.utils import valuation_rate

	for code in {i for i in items if i}:
		rate, pl, listed = _rate_preview(dt if dt in ("Purchase Order",) else "Sales Order", party, code)
		out[code] = {"rate": rate, "listed": listed, "valuation": flt(valuation_rate(code)) if dt != "Purchase Order" else 0}
	return out


# ---------------------------------------------------------------- save
DOCTYPES = {"quotation": "Quotation", "sales_order": "Sales Order", "purchase_order": "Purchase Order", "delivery_note": "Delivery Note", "invoice": "Sales Invoice"}


def no_negative(lines, label="item_code"):
	"""v1.8.4: a line typed with a minus quantity was dropped and the user then got "Add at least one line…" —
	now it says which line and why."""
	for r in lines or []:
		if r and flt(r.get("qty")) < 0:
			frappe.throw(_("Line {0}: the quantity cannot be negative ({1}). Type the quantity as a positive number; returns have their own window.")
				.format(r.get(label) or r.get("_item") or "", r.get("qty")), title=_("Negative quantity"))


def _lines(doc, lines, kind, need):
	no_negative(lines)
	for r in lines:
		if not r.get("item_code") or flt(r.get("qty")) <= 0:
			continue
		row = {"item_code": r["item_code"], "qty": flt(r["qty"])}
		if r.get("rate") not in (None, ""):
			row["rate"] = flt(r["rate"])
		if flt(r.get("discount")):
			row["discount_percentage"] = flt(r["discount"])
		if r.get("description"):
			row["description"] = r["description"]
		if kind == "sales_order":
			row["delivery_date"] = need
		if kind == "purchase_order":
			row["schedule_date"] = need
		if r.get("warehouse"):
			row["warehouse"] = r["warehouse"]
		# v1.8.0: Create PO from a material request — the order line stays linked to the request line (ordered quantity, project)
		if kind == "purchase_order" and r.get("material_request_item"):
			mri = frappe.db.get_value("Material Request Item", r["material_request_item"], ["parent", "item_code", "project", "warehouse"], as_dict=True)
			if mri and mri.item_code == r["item_code"] and frappe.has_permission("Material Request", "read", mri.parent):
				row.update({"material_request": mri.parent, "material_request_item": r["material_request_item"], "warehouse": r.get("warehouse") or mri.warehouse})
				if mri.project:
					row["project"] = mri.project
		doc.append("items", row)
	if not doc.get("items"):
		frappe.throw(_("Add at least one line with an item and a quantity"))


def _keep_rates(doc, lines):
	"""ERPNext re-prices lines on set_missing_values; keep the rate and discount the user typed.
	v1.8.2: the typed rate is the price before the line discount — it becomes the line's price-list rate, so a typed rate
	with a discount saves as rate × (1 − discount), exactly as the window showed (before, ERPNext's list price was kept)."""
	typed = [r for r in lines if r.get("item_code") and flt(r.get("qty")) > 0]
	for row, r in zip(doc.items, typed):
		has_rate = r.get("rate") not in (None, "")
		disc = flt(r.get("discount"))
		if not has_rate and not disc:
			continue
		base = flt(r["rate"]) if has_rate else (flt(row.price_list_rate) or flt(row.rate))
		row.price_list_rate = base
		row.discount_percentage = disc
		row.discount_amount = 0
		row.margin_type = None
		row.margin_rate_or_amount = 0
		row.rate = base * (1 - disc / 100)


@frappe.whitelist()
def save(kind, values, lines=None, action="save"):
	values = frappe._dict(frappe.parse_json(values) if isinstance(values, str) else (values or {}))
	lines = frappe.parse_json(lines) if isinstance(lines, str) else (lines or [])
	if kind == "receive_payment":
		return _receive(values)
	if kind not in DOCTYPES:
		frappe.throw(_("Unknown form {0}").format(kind))
	dt = DOCTYPES[kind]
	frappe.has_permission(dt, "create", throw=True)
	company = values.get("company") or _company()
	doc = frappe.new_doc(dt)
	doc.company = company
	need = values.get("delivery_date") or values.get("schedule_date") or add_days(today(), 3 if kind == "sales_order" else 30)
	if kind == "quotation":
		if values.get("new_party"):
			values.party = _new_prospect(values)
		is_lead = frappe.db.exists("Lead", values.party) and not frappe.db.exists("Customer", values.party)
		doc.quotation_to, doc.party_name = ("Lead" if is_lead else "Customer"), values.party
		doc.valid_till = values.get("valid_till") or add_days(today(), 14)
		for f in ("hs_subject", "hs_enquiry_ref", "hs_enquiry_date", "hs_delivery_period", "hs_warranty_months", "incoterm"):
			if values.get(f) and doc.meta.has_field(f):
				doc.set(f, values[f])
		# v1.8.4: a quotation has no sales team — the sales person was dropped; it is kept on hs_sales_person
		if values.get("sales_person") and doc.meta.has_field("hs_sales_person"):
			doc.hs_sales_person = values.sales_person
	elif kind == "sales_order":
		doc.customer = values.party
		doc.delivery_date = need
		doc.po_no = values.get("po_no") or None
		doc.po_date = values.get("po_date") or None
		doc.shipping_address_name = values.get("shipping_address") or None
		doc.customer_address = values.get("billing_address") or None
		doc.set_warehouse = values.get("set_warehouse") or None
		for f in ("incoterm", "named_place", "hs_payment_method", "hs_shipment_mode", "hs_is_export"):  # v1.7.3: + New → Export order
			if values.get(f) and doc.meta.has_field(f):
				doc.set(f, values[f])
	elif kind == "purchase_order":
		doc.supplier = values.party
		doc.schedule_date = need
		doc.transaction_date = values.get("transaction_date") or today()
		doc.set_warehouse = values.get("set_warehouse") or None
		doc.cost_center = values.get("cost_center") or None
		for f in ("incoterm", "hs_shipment_mode", "hs_port_of_loading", "hs_port_of_discharge", "order_confirmation_no"):
			if values.get(f) and doc.meta.has_field(f):
				doc.set(f, values[f])
	if values.get("contact_person"):
		doc.contact_person = values.contact_person
	if values.get("payment_terms") and doc.meta.has_field("payment_terms_template"):
		doc.payment_terms_template = values.payment_terms
	if values.get("currency"):
		doc.currency = values.currency
	pl = values.get("price_list")
	if pl and frappe.db.get_value("Price List", pl, "enabled"):
		doc.set("buying_price_list" if kind == "purchase_order" else "selling_price_list", pl)
	if values.get("remarks"):
		doc.set("terms" if kind == "quotation" else "remarks" if doc.meta.has_field("remarks") else "terms", values.remarks)
	if values.get("terms_text") and doc.meta.has_field("terms"):
		doc.terms = values.terms_text
	_extra_fields(doc, values)
	_lines(doc, lines, kind, need)
	if values.get("sales_person") and doc.meta.has_field("sales_team"):
		doc.append("sales_team", {"sales_person": values.sales_person, "allocated_percentage": 100})
	doc.flags.hs_quick = True
	doc.set_missing_values()
	_apply_tax(doc, company, kind == "purchase_order", values.get("party"))
	_keep_rates(doc, lines)
	if doc.get("currency") and doc.currency != frappe.get_cached_value("Company", company, "default_currency") and not flt(doc.get("conversion_rate")):
		from erpnext.setup.utils import get_exchange_rate

		doc.conversion_rate = flt(get_exchange_rate(doc.currency, frappe.get_cached_value("Company", company, "default_currency"), today())) or 1
	doc.calculate_taxes_and_totals()
	doc.insert()
	msg = _("{0} {1} saved").format(_(dt), doc.name)
	needs = None
	if action == "submit" and kind in ("sales_order", "purchase_order"):
		from hipersign_trading.doc_rules import DocumentNeeded

		frappe.db.savepoint("hs_create_submit")
		try:
			doc = _submit(doc)
			state = doc.get("workflow_state") or (_("Submitted") if doc.docstatus == 1 else _("Draft"))
			msg = _("{0} {1} · {2}").format(_(dt), doc.name, _(state))
		except DocumentNeeded as e:
			frappe.db.rollback(save_point="hs_create_submit")
			frappe.local.message_log = []
			needs = frappe.utils.strip_html(str(e))
			msg = _("{0} {1} saved as a draft — attach the document needed, then submit").format(_(dt), doc.name)
	return {"doctype": dt, "name": doc.name, "message": msg, "needs_documents": needs, "state": doc.get("workflow_state") or ("Submitted" if doc.docstatus == 1 else "Draft")}


# v1.7.3: values the form handles itself (not fields of the same name)
_HANDLED = {"party", "price_list", "payment_terms", "remarks", "terms_text", "shipping_address", "billing_address", "sales_person", "record_as",
	"items", "name", "doctype", "docstatus", "owner", "creation", "modified", "modified_by"}


def _cast(df, val):
	"""A form value as the field's type (the modal sends text)."""
	if df.fieldtype == "Check":
		return cint(val)
	if df.fieldtype in ("Int",):
		return cint(val)
	if df.fieldtype in ("Float", "Currency", "Percent"):
		return flt(val)
	return val


def _extra_fields(doc, values):
	"""v1.7.3: Detailed mode — the other fields the user filled (project, tax template, letter head …) go onto the
	field of the same name, unless the form already set it."""
	for k, val in values.items():
		if k in _HANDLED or k.startswith(("_", "new_")) or val in (None, ""):
			continue
		df = doc.meta.get_field(k)
		if not df or df.read_only or df.fieldtype in ("Table", "Table MultiSelect", "Section Break", "Column Break", "Tab Break", "HTML", "Button"):
			continue
		doc.set(k, _cast(df, val))


def _new_prospect(v):
	"""“+ Add new prospect / client…” on the quotation: a Lead (prospect) or a Customer (ready to order)."""
	if v.get("record_as") == "Customer":
		from hipersign_trading.api.quick_cards import create

		r = create("Customer", {"customer_name": v.new_party, "customer_group": v.get("new_group"), "contact_person": v.get("new_contact"),
			"mobile_no": v.get("new_mobile"), "email_id": v.get("new_email"), "tax_id": v.get("new_trn"), "hs_emirate": v.get("new_emirate"),
			"hs_lead_source": v.get("new_source")})
		return r["name"]
	ld = frappe.get_doc({"doctype": "Lead", "company_name": v.new_party, "first_name": v.get("new_contact") or v.new_party, "mobile_no": v.get("new_mobile"),
		"email_id": v.get("new_email"), "hs_emirate": v.get("new_emirate"), "utm_source": v.get("new_source"), "hs_pipeline_stage": "Proposal",
		"hs_interested_in": v.get("hs_subject") or _("Quotation")})
	ld.insert()
	return ld.name


def _receive(v):
	from hipersign_trading.api.quick import quick_receive

	return quick_receive(v.party, v.amount, v.get("mode_of_payment"), v.get("reference_no"))


@frappe.whitelist()
def link_options(doctype, query=None):
	"""Choices for a Link field on a create card (the card's own filters apply)."""
	if not frappe.has_permission(doctype, "read"):
		return []
	q = frappe.parse_json(query) if query else {}
	filters = (q or {}).get("filters") or {}
	meta = frappe.get_meta(doctype)
	if meta.has_field("disabled") and "disabled" not in filters:
		filters["disabled"] = 0
	if (q or {}).get("query") == "trip_notes":
		return _trip_notes()
	if str((q or {}).get("query") or "").startswith("mfg:"):  # v1.8.0: the Manufacturing windows
		from hipersign_trading.api.create_mfg import choices

		return choices(q["query"])
	if (q or {}).get("query") == "boq_lines":  # v1.8.0: material request to site
		from hipersign_trading.api.create_prj import boq_lines

		return boq_lines()
	if (q or {}).get("query") == "hipersign_trading.api.crm.sales_users":
		from hipersign_trading.api.crm import sales_users

		return [{"name": r[0], "label": r[1] if len(r) > 1 and r[1] else r[0]} for r in sales_users("User", "", "name", 0, LIMIT, {})]
	if meta.has_field("company") and "company" not in filters and doctype not in ("User",):
		filters["company"] = _company()
	title = meta.title_field if meta.title_field and meta.title_field != "name" and meta.has_field(meta.title_field) else None
	rows = _names(doctype, filters, title, "modified desc" if meta.is_submittable else (f"{title} asc" if title else "name asc"))
	if meta.is_submittable or meta.autoname and "naming_series" in (meta.autoname or "") or doctype in ("Employee", "Item"):
		# documents and coded masters: "PUR-ORD-2026-00003 — EuroSafe Systems GmbH", as on the prototype
		for r in rows:
			if r["label"] != r["name"]:
				r["label"] = f"{r['name']} — {r['label']}"
	return rows


# ---------------------------------------------------------------- v1.7.0 part 2: the other create forms (one save for all)
SIMPLE = {"Import Shipment", "Export Shipment", "Material Request", "Stock Entry", "Stock Reconciliation", "Journal Entry", "Post Dated Cheque",
	"Expense Claim", "Leave Application", "Letter of Credit", "Bank Guarantee", "Company Document",
	# v1.7.3
	"Credit Limit Request", "Purchase Invoice", "Payment Entry", "Warranty Claim", "Delivery Trip", "Employee Advance",
	"Sales Invoice"}  # Sales Invoice: only the credit note window (returns); new invoices start from the delivery (C.PICK)
# v1.8.0: the Projects windows (api.create_prj)
SIMPLE |= {"Project", "Project BOQ", "Task", "Timesheet", "Progress Certificate", "Variation Order", "Subcontract Order", "Daily Site Report"}
# v1.8.0: the Manufacturing windows (api.create_mfg)
SIMPLE |= {"BOM", "Work Order", "Production Plan", "Job Card", "Quality Inspection"}


def _prj_hook(kind, doctype, v):
	"""v1.8.0: the Projects windows' hooks live in api.create_prj (material request to site and site transfer by their flag)."""
	from hipersign_trading.api import create_mfg, create_prj

	key = frappe.scrub(doctype)
	if v.get("_mfg") or doctype in create_mfg.DOCTYPES:  # v1.8.0: Manufacturing (manufacture entry and transfer to WIP by their flag)
		return getattr(create_mfg, f"{kind}_{key}" + (f"_{v._mfg}" if v.get("_mfg") else ""), None)
	if doctype in ("Material Request", "Stock Entry") and v.get("_site"):
		key += "_site"
	elif doctype not in create_prj.DOCTYPES:
		return None
	return getattr(create_prj, f"{kind}_{key}", None)


@frappe.whitelist()
def save_doc(doctype, values, rows=None, action="save"):
	if doctype not in SIMPLE:
		frappe.throw(_("Unknown form"))
	frappe.has_permission(doctype, "create", throw=True)
	v = frappe._dict(frappe.parse_json(values) if isinstance(values, str) else (values or {}))
	rows = [r for r in (frappe.parse_json(rows) if isinstance(rows, str) else (rows or [])) if any(x not in (None, "", 0, "0") for x in r.values())]
	doc = frappe.new_doc(doctype)
	meta = doc.meta
	# v1.7.3: the doctype's own defaults (today's date, a ticked box) — a value the user typed replaces them
	defaults = {k: doc.get(k) for k in v}
	if meta.has_field("company"):
		doc.company = v.get("company") or _company()
	v._action = action
	frappe.flags.hs_create_msg = None
	pre = _prj_hook("pre", doctype, v) or globals().get("_pre_" + frappe.scrub(doctype))
	if pre:
		# v1.7.3: a hook may hand back the document ERPNext's own mapper made (bill from an order, debit note, receipt)
		doc = pre(doc, v, rows) or doc
	if doc.flags.get("hs_done"):  # v1.8.0: the hook saved an existing record (BOQ lines added to the project's BOQ)
		d = doc.flags.hs_done
		return {"doctype": d.doctype, "name": d.name, "message": frappe.flags.hs_create_msg or _("{0} {1} saved").format(_(d.doctype), d.name)}
	for k, val in v.items():
		if val in (None, "") or k.startswith("_"):
			continue
		df = meta.get_field(k)
		if not df or df.fieldtype in ("Table", "Table MultiSelect") or df.read_only:
			continue
		cur = doc.get(k)
		if not cur or (not doc.flags.hs_ready and defaults.get(k) not in (None, "") and str(cur) == str(defaults.get(k))):
			doc.set(k, _cast(df, val))
	post = globals().get("_post_" + frappe.scrub(doctype))
	if post:
		post(doc, v, rows)
	if hasattr(doc, "set_missing_values") and not doc.flags.hs_ready:
		try:
			doc.set_missing_values()
		except Exception:
			frappe.clear_last_message()
	doc.insert()
	after = _prj_hook("after", doctype, v) or globals().get("_after_" + frappe.scrub(doctype))
	if after:
		after(doc, v, rows)
	label = _("Debit Note") if doctype == "Purchase Invoice" and doc.get("is_return") else _(doctype)
	msg = (frappe.flags.hs_create_msg or "").replace("{0}", doc.name) or _("{0} {1} saved").format(label, doc.name)
	needs = None
	if action == "submit" and meta.is_submittable:
		from hipersign_trading.doc_rules import DocumentNeeded

		frappe.db.savepoint("hs_simple_submit")
		try:
			doc = _submit(doc)
			msg = _("{0} {1} · {2}").format(label, doc.name, _(doc.get("workflow_state") or ("Submitted" if doc.docstatus == 1 else "Draft")))
		except DocumentNeeded as e:
			frappe.db.rollback(save_point="hs_simple_submit")
			frappe.local.message_log = []
			needs = frappe.utils.strip_html(str(e))
			msg = _("{0} {1} saved as a draft — attach the document needed, then submit").format(label, doc.name)
	return {"doctype": doctype, "name": doc.name, "message": msg, "needs_documents": needs}


def _pre_import_shipment(doc, v, rows):
	doc.status = "Booked"
	pos = [v.get("purchase_order")] if v.get("purchase_order") else [r.get("purchase_order") for r in rows]
	for po in [p for p in pos if p]:
		doc.append("purchase_orders", {"purchase_order": po})


def _pre_export_shipment(doc, v, rows):
	doc.status = "Booked"
	if v.get("etd") and v.get("_transit_days"):
		doc.eta = add_days(v.etd, cint(v._transit_days))


def _pre_material_request(doc, v, rows):
	doc.material_request_type = "Purchase"
	doc.transaction_date = v.get("transaction_date") or today()
	need = v.get("schedule_date") or add_days(today(), 7)
	for r in rows:
		if r.get("item_code") and flt(r.get("qty")) > 0:
			doc.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "schedule_date": need})
	if v.get("_reason") or v.get("_department"):
		doc.terms = " — ".join(x for x in [v.get("_department"), v.get("_reason")] if x)


def _pre_stock_entry(doc, v, rows):
	doc.stock_entry_type = "Material Transfer"
	doc.purpose = "Material Transfer"
	if v.get("from_warehouse") and v.get("from_warehouse") == v.get("to_warehouse"):
		frappe.throw(_("From and To are the same warehouse — choose where the stock goes."))  # v1.8.2
	if any(r.get("item_code") and flt(r.get("qty")) < 0 for r in rows):
		frappe.throw(_("Quantities must be more than zero."))
	for r in rows:
		if r.get("item_code") and flt(r.get("qty")) > 0:
			doc.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "s_warehouse": v.get("from_warehouse"), "t_warehouse": v.get("to_warehouse")})
	if v.get("_reason") or v.get("_requested_by"):
		doc.remarks = " — ".join(x for x in [v.get("_requested_by"), v.get("_reason")] if x)
	if v.get("posting_date") and getdate(v.posting_date) != getdate(today()):
		doc.set_posting_time = 1


def _pre_stock_reconciliation(doc, v, rows):
	doc.purpose = "Stock Reconciliation"
	from hipersign_trading.utils import valuation_rate

	for r in rows:
		if r.get("item_code") and r.get("warehouse") and r.get("qty") not in (None, ""):
			doc.append("items", {"item_code": r["item_code"], "warehouse": r["warehouse"], "qty": flt(r["qty"]),
				"valuation_rate": flt(valuation_rate(r["item_code"], r["warehouse"])) or None})
	if not doc.get("items"):
		frappe.throw(_("Enter the item, warehouse and counted quantity"))
	if v.get("_reason") and doc.meta.has_field("remarks"):
		doc.remarks = v._reason
	# v1.7.3: a count dated in the past (Detailed mode)
	if v.get("posting_date") and getdate(v.posting_date) != getdate(today()):
		doc.set_posting_time = 1


def _pre_journal_entry(doc, v, rows):
	doc.voucher_type = v.get("voucher_type") or "Journal Entry"
	doc.posting_date = v.get("posting_date") or today()
	doc.user_remark = v.get("user_remark")
	dr = cr = 0
	for r in rows:
		if not r.get("account"):
			continue
		d, c = flt(r.get("debit")), flt(r.get("credit"))
		if not d and not c:
			continue
		row = {"account": r["account"], "debit_in_account_currency": d, "credit_in_account_currency": c}
		at = frappe.get_cached_value("Account", r["account"], "account_type")
		if at in ("Receivable", "Payable") and r.get("party"):
			row.update({"party_type": "Customer" if at == "Receivable" else "Supplier", "party": r["party"]})
		doc.append("accounts", row)
		dr += d
		cr += c
	if abs(dr - cr) > 0.005:
		frappe.throw(_("Debits ({0}) and credits ({1}) must be equal").format(frappe.format(dr, "Currency"), frappe.format(cr, "Currency")))


def _pre_post_dated_cheque(doc, v, rows):
	inv_dt = "Sales Invoice" if v.get("direction") != "Issued" else "Purchase Invoice"
	if v.get("_invoice"):
		inv = frappe.db.get_value(inv_dt, v._invoice, ["customer" if inv_dt == "Sales Invoice" else "supplier", "company"], as_dict=True)
		doc.party_type = "Customer" if inv_dt == "Sales Invoice" else "Supplier"
		doc.party = inv.get("customer") or inv.get("supplier")
		doc.company = inv.company
		doc.reference_doctype, doc.reference_name = inv_dt, v._invoice
	doc.direction = v.get("direction") or "Received"
	doc.received_on = v.get("received_on") or today()
	doc.status = "In Hand" if doc.direction == "Received" else "Issued"


def _pre_expense_claim(doc, v, rows):
	doc.posting_date = v.get("posting_date") or today()
	for r in rows:
		if r.get("expense_type") and flt(r.get("amount")) > 0:
			acc = frappe.db.get_value("Expense Claim Account", {"parent": r["expense_type"], "company": doc.company}, "default_account") \
				or frappe.get_cached_value("Company", doc.company, "default_expense_account") \
				or frappe.db.get_value("Account", {"company": doc.company, "root_type": "Expense", "is_group": 0, "account_name": ["like", "%Miscellaneous%"]}, "name")
			doc.append("expenses", {"expense_date": r.get("expense_date") or today(), "expense_type": r["expense_type"], "description": r.get("description"),
				"amount": flt(r["amount"]), "sanctioned_amount": flt(r["amount"]), "cost_center": v.get("cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center"), "default_account": acc})
	if not doc.get("expenses"):
		frappe.throw(_("Add at least one expense with a type and an amount"))
	emp = frappe.db.get_value("Employee", v.get("employee"), ["expense_approver", "reports_to", "company"], as_dict=True) if v.get("employee") else None
	if emp:
		doc.company = emp.company or doc.company
		doc.expense_approver = v.get("expense_approver") or emp.expense_approver or (frappe.db.get_value("Employee", emp.reports_to, "user_id") if emp.reports_to else None)
	doc.remark = v.get("_purpose")
	doc.currency = doc.currency or frappe.get_cached_value("Company", doc.company, "default_currency")
	doc.exchange_rate = doc.exchange_rate or 1


def _pre_leave_application(doc, v, rows):
	doc.posting_date = v.get("posting_date") or today()
	doc.status = "Open"
	emp = frappe.db.get_value("Employee", v.get("employee"), ["leave_approver", "reports_to", "company"], as_dict=True) if v.get("employee") else None
	if emp:
		doc.company = emp.company or doc.company
		doc.leave_approver = v.get("leave_approver") or emp.leave_approver or (frappe.db.get_value("Employee", emp.reports_to, "user_id") if emp.reports_to else None)


def _pre_letter_of_credit(doc, v, rows):
	doc.lc_type = "Import"
	doc.status = "Applied"
	if v.get("purchase_order"):
		po = frappe.db.get_value("Purchase Order", v.purchase_order, ["supplier", "currency", "grand_total", "company", "conversion_rate"], as_dict=True)
		doc.supplier, doc.currency, doc.company = po.supplier, po.currency, po.company
		doc.amount = flt(v.get("amount")) or po.grand_total
		doc.exchange_rate = po.conversion_rate
		doc.base_amount = flt(doc.amount) * flt(po.conversion_rate or 1)
		ship = frappe.get_all("Import Shipment PO", filters={"purchase_order": v.purchase_order, "parenttype": "Import Shipment"}, pluck="parent", limit=1)
		if ship:
			doc.import_shipment = ship[0]
	if flt(v.get("margin_pct")):
		doc.margin_amount = flt(doc.base_amount or doc.amount) * flt(v.margin_pct) / 100


def _pre_bank_guarantee(doc, v, rows):
	doc.bg_type = "Providing"
	cv, pct = flt(v.get("_contract_value")), flt(v.get("_pct")) or 10
	doc.amount = flt(v.get("amount")) or cv * pct / 100
	doc.start_date = v.get("start_date") or today()
	if v.get("_valid_to"):
		from frappe.utils import date_diff

		# v1.8.4: the end date was lost — ERPNext only sets it in the browser form; keep it, validity as the form counts it
		if getdate(v._valid_to) < getdate(doc.start_date):
			frappe.throw(_("Valid to must be on or after Valid from"))
		doc.validity = date_diff(v._valid_to, doc.start_date) + 1
		doc.end_date = v._valid_to
	if flt(v.get("_margin_pct")):
		doc.margin_money = doc.amount * flt(v._margin_pct) / 100
	doc.more_information = " — ".join(x for x in [v.get("_bg_kind"), v.get("_contract")] if x)
	if v.get("customer"):
		doc.name_of_beneficiary = frappe.db.get_value("Customer", v.customer, "customer_name")


# ---------------------------------------------------------------- v1.7.3: credit limit, supplier bill, debit note, receipt, warranty, trip, advance
def _pre_credit_limit_request(doc, v, rows):
	doc.company = v.get("company") or doc.company
	if flt(v.get("requested_limit")) < 0:
		frappe.throw(_("Credit limit cannot be negative"))


def _bill_mapped(src):
	"""The supplier bill ERPNext makes from a purchase order or a goods receipt (not saved)."""
	if frappe.db.exists("Purchase Order", src):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

		sdt = "Purchase Order"
	elif frappe.db.exists("Purchase Receipt", src):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		sdt = "Purchase Receipt"
	else:
		frappe.throw(_("{0} is not a purchase order or goods receipt").format(src))
	frappe.get_doc(sdt, src).check_permission("read")
	return make_purchase_invoice(src), sdt


def _taxes_rate(doc):
	return flt(sum(flt(t.rate) for t in (doc.get("taxes") or []) if t.charge_type == "On Net Total"))


def _supplier_due(supplier, company, posting_date=None, bill_date=None):
	from erpnext.accounts.party import get_due_date

	try:
		return get_due_date(posting_date or today(), "Supplier", supplier, company, bill_date or posting_date or today())
	except Exception:
		frappe.clear_last_message()
		return None


def _pre_purchase_invoice(doc, v, rows):
	"""Supplier bill — matched to its purchase order / goods receipt (ERPNext's mapper), or typed lines; the company's VAT."""
	if cint(v.get("is_return")) or v.get("_return_against"):
		return _debit_note(v, rows)
	if v.get("_source"):
		doc, sdt = _bill_mapped(v._source)
		want = {cint(r["_i"]): r for r in rows if r.get("_i") not in (None, "")}
		no_negative(rows, "_item")
		keep = []
		for i, row in enumerate(doc.items):
			r = want.get(i)
			if not r or flt(r.get("qty")) <= 0:
				continue
			row.qty = flt(r["qty"])
			if r.get("rate") not in (None, ""):
				row.rate = flt(r["rate"])
			keep.append((row, r))
		doc.set("items", [k[0] for k in keep])
		for r in rows:
			if r.get("_i") in (None, "") and r.get("item_code") and flt(r.get("qty")) > 0:
				keep.append((doc.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "rate": flt(r.get("rate"))}), r))
	else:
		if not v.get("supplier"):
			frappe.throw(_("Choose the supplier"))
		doc.supplier = v.supplier
		keep = []
		for r in rows:
			if r.get("item_code") and flt(r.get("qty")) > 0:
				keep.append((doc.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "rate": flt(r.get("rate"))}), r))
	if not doc.get("items"):
		frappe.throw(_("Add at least one line with an item and a quantity"))
	if not v.get("bill_no"):
		frappe.throw(_("Enter the supplier's bill number"))
	company = doc.company = doc.company or v.get("company") or _company()
	doc.bill_no = v.bill_no
	doc.bill_date = v.get("bill_date") or today()
	doc.posting_date = v.get("posting_date") or today()
	if getdate(doc.posting_date) != getdate(today()):
		doc.set_posting_time = 1
	for f in ("currency", "payment_terms_template", "taxes_and_charges", "update_stock", "set_warehouse", "cost_center", "project"):
		if v.get(f) not in (None, ""):
			doc.set(f, cint(v[f]) if f == "update_stock" else v[f])
	if v.get("taxes_and_charges"):
		doc.set("taxes", [])
	doc.run_method("set_missing_values")
	# ERPNext re-prices the lines from the price list; keep the bill's own rates and quantities
	for row, r in keep:
		row.qty = flt(r["qty"])
		if r.get("rate") not in (None, ""):
			row.rate = flt(r["rate"])
			row.price_list_rate = row.price_list_rate or row.rate
			row.discount_percentage = 0
	_apply_tax(doc, company, True, doc.supplier)
	if v.get("due_date"):
		auto = _supplier_due(doc.supplier, company, doc.posting_date, doc.bill_date)
		if not auto or getdate(auto) != getdate(v.due_date):
			doc.payment_terms_template = None
		doc.due_date = v.due_date
		doc.set("payment_schedule", [])
	doc.calculate_taxes_and_totals()
	doc.flags.hs_ready = True
	return doc


def _debit_note(v, rows):
	"""Debit note (purchase return) against a submitted supplier bill — ERPNext's make_debit_note, the quantities returned."""
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note

	src = v.get("_return_against")
	if not src:
		frappe.throw(_("Choose the supplier bill"))
	frappe.get_doc("Purchase Invoice", src).check_permission("read")
	dn = make_debit_note(src)
	want = {cint(r["_i"]): r for r in rows if r.get("_i") not in (None, "")}
	keep = []
	for i, row in enumerate(dn.items):
		r = want.get(i)
		if r and flt(r.get("qty")) < 0:  # v1.8.4: a minus is not turned into a return of that size silently
			frappe.throw(_("{0}: type the quantity returned as a positive number (e.g. 5, not −5)").format(row.item_name or row.item_code))
		q = abs(flt(r.get("qty"))) if r else 0
		if q <= 0:
			continue
		if q > abs(flt(row.qty)) + 0.0001:
			frappe.throw(_("{0}: only {1} can be returned").format(row.item_name or row.item_code, abs(flt(row.qty))))
		row.qty = -q
		row.stock_qty = -q * flt(row.conversion_factor or 1)
		if row.get("received_qty"):
			row.received_qty = -q
		keep.append(row)
	if not keep:
		frappe.throw(_("Enter the quantity returned on at least one line"))
	dn.set("items", keep)
	# the returned amount comes off the supplier bill's outstanding (not a separate open debit)
	if dn.meta.has_field("update_outstanding_for_self"):
		dn.update_outstanding_for_self = 0
	for f in ("hs_return_reason", "hs_supplier_rma", "remarks", "cost_center", "project"):
		if v.get(f) and dn.meta.has_field(f):
			dn.set(f, v[f])
	if v.get("posting_date"):
		dn.posting_date = v.posting_date
		if getdate(v.posting_date) != getdate(today()):
			dn.set_posting_time = 1
	dn.run_method("set_missing_values")
	dn.calculate_taxes_and_totals()
	dn.flags.hs_ready = True
	return dn


def _bank_charges_account(company):
	for like in ("Bank Charges%", "%Bank Charges%", "%bank%charge%"):
		acc = frappe.db.get_value("Account", {"company": company, "is_group": 0, "root_type": "Expense", "account_name": ["like", like]}, "name")
		if acc:
			return acc


def _pre_payment_entry(doc, v, rows):
	"""Receive payment — quick_receive's receipt (oldest invoices first), then the account, dates and bank charges."""
	from hipersign_trading.api.quick import receive_entry

	if not v.get("customer"):
		frappe.throw(_("Choose the customer"))
	if cint(v.get("_advance")):
		pe = _advance_entry(v)  # v1.8.4: Receive advance (Finance › Customer advances) — not applied to invoices
	else:
		pe = receive_entry(v.customer, v.get("amount"), v.get("mode_of_payment"), v.get("reference_no"), v.get("company"))
	if v.get("paid_to"):
		pe.paid_to = v.paid_to
		pe.paid_to_account_currency = frappe.get_cached_value("Account", v.paid_to, "account_currency")
	if v.get("posting_date"):
		pe.posting_date = v.posting_date
	pe.reference_date = v.get("reference_date") or pe.posting_date or today()
	for f in ("cost_center", "project"):
		if v.get(f):
			pe.set(f, v[f])
	if v.get("remarks"):
		pe.custom_remarks = 1
		pe.remarks = v.remarks
	charges = flt(v.get("_bank_charges"))
	if charges > 0:
		acc = _bank_charges_account(pe.company)
		if not acc:
			frappe.throw(_("No bank charges expense account in {0}").format(pe.company))
		if charges >= flt(pe.paid_amount):
			frappe.throw(_("Bank charges must be less than the amount received"))
		pe.paid_amount = flt(pe.paid_amount) - charges
		pe.received_amount = flt(pe.received_amount) - charges
		pe.append("deductions", {"account": acc, "cost_center": v.get("cost_center") or frappe.get_cached_value("Company", pe.company, "cost_center"),
			"amount": charges, "description": _("Bank charges")})
	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.set_exchange_rate()
	pe.set_amounts()
	pe.flags.hs_ready = True
	return pe


def _advance_entry(v):
	"""v1.8.4: a customer advance — against a sales order when one is chosen (the advance due on it is the default amount),
	otherwise left unallocated on the customer, to be applied to an invoice later."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	amount = flt(v.get("amount"))
	if v.get("sales_order"):
		so = frappe.get_doc("Sales Order", v.sales_order)
		so.check_permission("read")
		if so.customer != v.customer:
			frappe.throw(_("{0} is an order of {1}.").format(so.name, so.customer_name))
		if amount <= 0:
			from hipersign_trading.overrides.advances import position

			required, received = position(so)
			amount = max(0.0, flt(required) - flt(received)) or flt(so.grand_total) - flt(so.advance_paid)
		pe = get_payment_entry("Sales Order", so.name, party_amount=amount)
	else:
		if amount <= 0:
			frappe.throw(_("Enter the amount received"))
		company = v.get("company") or frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1, pluck="name")[0]
		pe = frappe.new_doc("Payment Entry")
		pe.update({"payment_type": "Receive", "party_type": "Customer", "party": v.customer, "company": company, "posting_date": today(),
			"paid_amount": amount, "received_amount": amount})
		pe.setup_party_account_field()
		pe.set_missing_values()
	pe.paid_amount = pe.received_amount = amount
	if v.get("mode_of_payment"):
		pe.mode_of_payment = v.mode_of_payment
		acc = frappe.db.get_value("Mode of Payment Account", {"parent": v.mode_of_payment, "company": pe.company}, "default_account")
		if acc:
			pe.paid_to = acc
	if not pe.get("paid_to"):
		pe.paid_to = frappe.get_cached_value("Company", pe.company, "default_bank_account") or frappe.get_cached_value("Company", pe.company, "default_cash_account")
	if pe.get("paid_to"):
		pe.paid_to_account_currency = frappe.get_cached_value("Account", pe.paid_to, "account_currency")
	pe.reference_no = v.get("reference_no") or _("Advance")
	pe.reference_date = today()
	return pe


def _serial_info(serial_no):
	sn = frappe.db.get_value("Serial No", serial_no, ["item_code", "item_name", "customer", "warranty_expiry_date", "amc_expiry_date", "status",
		"reference_doctype", "reference_name"], as_dict=True) or frappe._dict()
	if sn.warranty_expiry_date:
		sn.state = "Under Warranty" if getdate(sn.warranty_expiry_date) >= getdate(today()) else "Out of Warranty"
	elif sn.amc_expiry_date and getdate(sn.amc_expiry_date) >= getdate(today()):
		sn.state = "Under AMC"
	return sn


def _pre_warranty_claim(doc, v, rows):
	doc.status = "Open"
	doc.complaint_date = v.get("complaint_date") or today()
	if v.get("serial_no"):
		sn = _serial_info(v.serial_no)
		doc.item_code = v.get("item_code") or sn.item_code
		doc.customer = v.get("customer") or sn.customer
		doc.warranty_expiry_date = v.get("warranty_expiry_date") or sn.warranty_expiry_date
		doc.amc_expiry_date = v.get("amc_expiry_date") or sn.amc_expiry_date
		doc.warranty_amc_status = v.get("warranty_amc_status") or sn.get("state")
	if not (v.get("customer") or doc.customer):
		frappe.throw(_("Choose the customer"))


def _trip_notes():
	"""Delivery notes ready to dispatch: submitted, not a return, not on a delivery trip yet."""
	dn = frappe.qb.DocType("Delivery Note")
	q = (frappe.qb.from_(dn).select(dn.name, dn.customer_name, dn.posting_date).where(dn.docstatus == 1).where(dn.is_return == 0)
		.orderby(dn.posting_date, order=frappe.qb.desc).limit(LIMIT))
	if frappe.get_meta("Delivery Note").has_field("hs_delivery_status"):
		q = q.where(dn.hs_delivery_status.isnull() | dn.hs_delivery_status.isin(["", "Ready to Dispatch"]))
	company = _company()
	if company:
		q = q.where(dn.company == company)
	on_trip = set(frappe.db.sql_list("""select ds.delivery_note from `tabDelivery Stop` ds join `tabDelivery Trip` dt on dt.name = ds.parent
		where dt.docstatus < 2 and ifnull(ds.delivery_note, '') != ''"""))
	return [{"name": r[0], "label": f"{r[0]} — {r[1]}"} for r in q.run() if r[0] not in on_trip and frappe.has_permission("Delivery Note", "read", r[0])]


def _dn_stop(name):
	d = frappe.db.get_value("Delivery Note", name, ["customer", "customer_name", "shipping_address_name", "customer_address", "contact_person"], as_dict=True)
	if not d:
		return {}
	addr = d.shipping_address_name or d.customer_address
	label = ", ".join(x for x in (frappe.db.get_value("Address", addr, ["address_line1", "city"]) or []) if x) if addr else ""
	return {"customer": d.customer, "_customer": d.customer_name or d.customer, "address": addr, "_address": label or addr or _("No address"), "contact": d.contact_person}


def _pre_delivery_trip(doc, v, rows):
	t = (v.get("_departure_time") or nowtime()[:5])[:5]
	doc.departure_time = get_datetime(f"{v.get('_departure_date') or today()} {t}:00")
	doc.driver = v.get("driver")
	doc.vehicle = v.get("vehicle")
	for r in rows:
		if not r.get("delivery_note"):
			continue
		st = _dn_stop(r["delivery_note"])
		if not st.get("address"):
			frappe.throw(_("{0} has no delivery address — add one on the delivery note").format(r["delivery_note"]))
		doc.append("delivery_stops", {"delivery_note": r["delivery_note"], "customer": st["customer"], "address": st["address"], "contact": st.get("contact")})
	if not doc.get("delivery_stops"):
		frappe.throw(_("Add at least one delivery note as a stop"))


def _after_delivery_trip(doc, v, rows):
	if v.get("_route_note"):
		doc.add_comment("Comment", _("Route: {0}").format(v._route_note))


def _pre_employee_advance(doc, v, rows):
	emp = frappe.db.get_value("Employee", v.get("employee"), ["company"], as_dict=True) if v.get("employee") else None
	if emp and emp.company:
		doc.company = emp.company
	doc.posting_date = v.get("posting_date") or today()
	doc.currency = v.get("currency") or frappe.get_cached_value("Company", doc.company, "default_currency")
	doc.exchange_rate = 1 if doc.currency == frappe.get_cached_value("Company", doc.company, "default_currency") else (doc.get("exchange_rate") or 1)
	doc.advance_amount = flt(v.get("advance_amount"))
	if doc.advance_amount <= 0:
		frappe.throw(_("Enter the advance amount"))
	doc.repay_unclaimed_amount_from_salary = cint(v.get("repay_unclaimed_amount_from_salary"))
	# the company's default, else a receivable "Employee Advances" account (HRMS asks for one on submit when neither exists)
	doc.advance_account = v.get("advance_account") or frappe.get_cached_value("Company", doc.company, "default_employee_advance_account") \
		or frappe.db.get_value("Account", {"company": doc.company, "is_group": 0, "account_type": "Receivable", "account_name": ["like", "%Employee Advance%"]}, "name")


@frappe.whitelist()
def submit_saved(doctype, name):
	"""v1.7.2: submit a record the create modal saved a moment ago, once its attached documents are in
	(the modal saves, uploads the files with their document types, then submits — so a blocking rule is met)."""
	if doctype not in set(DOCTYPES.values()) | SIMPLE:
		frappe.throw(_("Unknown form"))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")
	if doc.docstatus != 0:
		return {"doctype": doctype, "name": name, "message": _("{0} {1} is already submitted").format(_(doctype), name)}
	from hipersign_trading.doc_rules import DocumentNeeded

	try:
		doc = _submit(doc)
	except DocumentNeeded as e:
		frappe.local.message_log = []
		return {"doctype": doctype, "name": name, "needs_documents": frappe.utils.strip_html(str(e)),
			"message": _("{0} {1} saved as a draft — attach the document needed, then submit").format(_(doctype), name)}
	state = doc.get("workflow_state") or (_("Submitted") if doc.docstatus == 1 else _("Draft"))
	return {"doctype": doctype, "name": name, "message": _("{0} {1} · {2}").format(_(doctype), name, _(state))}


def _mode(v):
	v = (v or "").lower()
	return "Air" if "air" in v else "Land" if ("land" in v or "road" in v or "truck" in v) else "Sea" if v else None


@frappe.whitelist()
def fill_doc(kind, name, values=None):
	"""v1.7.2: what the prototype fills in when the source document is picked on a create form.
	v1.7.3: also the other values on the form (values), the lines to fill in (rows) and values that always follow the pick (force)."""
	out, note = {}, ""
	values = frappe._dict(frappe.parse_json(values) if isinstance(values, str) else (values or {}))
	if kind in _FILL:
		return _FILL[kind](name, values)
	if kind == "mfg_wo_ops" and name:  # v1.8.4: a job card offers only the operations of the work order's routing
		from hipersign_trading.api.create_mfg import fill_wo_ops

		return fill_wo_ops(name, values)
	if kind == "mfg_bom" and name:  # v1.8.0: a new BOM version starts from the active one's components
		from hipersign_trading.api.create_mfg import fill_bom

		return fill_bom(name, values)
	if kind == "export_from_so" and name:
		so = frappe.get_doc("Sales Order", name)
		so.check_permission("read")
		g = lambda f: so.get(f) if so.meta.has_field(f) else None
		cust = frappe.get_cached_doc("Customer", so.customer)
		city = frappe.db.get_value("Address", so.shipping_address_name or so.customer_address, ["city", "country"], as_dict=True) if (so.shipping_address_name or so.customer_address) else None
		dest = ", ".join(x for x in [(city or {}).get("city"), (city or {}).get("country")] if x) or cust.get("hs_country_city") or ""
		out = {"mode": _mode(g("hs_shipment_mode")), "destination": g("named_place") or dest, "incoterm": g("incoterm") or cust.get("hs_incoterm") or None}
		terms = so.payment_terms_template or cust.payment_terms or ""
		note = _("Payment: {0} · Invoice currency {1} · The export invoice is zero-rated (0% VAT).").format(terms or _("as agreed"), so.currency)
	elif kind == "import_from_po" and name:
		po = frappe.get_doc("Purchase Order", name)
		po.check_permission("read")
		g = lambda f: po.get(f) if po.meta.has_field(f) else None
		out = {"mode": _mode(g("hs_shipment_mode")), "port_of_loading": g("hs_port_of_loading"), "port_of_discharge": g("hs_port_of_discharge")}
		note = _("{0} · {1} {2} · incoterm {3}").format(po.supplier, po.currency, frappe.format(po.grand_total, {"fieldtype": "Float", "precision": 2}), g("incoterm") or "—")
	elif kind == "lc_from_po" and name:
		po = frappe.get_doc("Purchase Order", name)
		po.check_permission("read")
		out = {"amount": flt(po.grand_total)}
		note = _("{0} {1} · incoterm {2} — the supplier's payment terms are replaced by the LC. Insurance only when the supplier insures (CIF / CIP).").format(
			po.currency, frappe.format(po.grand_total, {"fieldtype": "Float", "precision": 2}), po.get("incoterm") or "—")
	return {"values": {k: v for k, v in out.items() if v not in (None, "")}, "note": note}


@frappe.whitelist()
def stock_now(item_code):
	"""v1.7.2: on-hand stock of an item in the user's company (the purchase request's "In stock" column)."""
	company = _company()
	whs = frappe.get_all("Warehouse", filters={"company": company, "is_group": 0}, pluck="name")
	if not item_code or not whs:
		return 0
	return flt(frappe.db.sql("select sum(actual_qty) from `tabBin` where item_code=%s and warehouse in %s", (item_code, tuple(whs)))[0][0])


# ---------------------------------------------------------------- v1.7.3: what the new windows fill in
def _money(v, ccy=None):
	from frappe.utils import fmt_money

	return fmt_money(flt(v), 2, ccy or frappe.get_cached_value("Company", _company(), "default_currency"))


def _fill_credit(name, v):
	if not name:
		return {"values": {}, "note": ""}
	from erpnext.selling.doctype.customer.customer import get_credit_limit

	frappe.get_doc("Customer", name).check_permission("read")
	company = v.get("company") or _company()
	limit = flt(get_credit_limit(name, company))
	overdue = flt(frappe.db.sql("""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice` where customer=%s and company=%s and docstatus=1
		and outstanding_amount > 0 and due_date < %s""", (name, company, today()))[0][0])
	exp = _exposure(name, company)
	note = _("Current limit {0} · exposure {1} · overdue {2}").format(_money(limit) if limit else _("not set"), _money(exp), _money(overdue))
	return {"values": {"_current_limit": limit}, "force": ["_current_limit"], "note": note}


def _fill_supplier_bill(name, v):
	if not name:
		return {"values": {}, "note": ""}
	frappe.get_doc("Supplier", name).check_permission("read")
	company = v.get("company") or _company()
	s = frappe.db.get_value("Supplier", name, ["payment_terms", "tax_id", "default_currency"], as_dict=True)
	due = _supplier_due(name, company, v.get("posting_date"), v.get("bill_date"))
	vat = _vat_rate(company, True, name)
	note = " · ".join(x for x in [_("Terms: {0}").format(s.payment_terms) if s.payment_terms else _("No payment terms"),
		_("TRN {0}").format(s.tax_id) if s.tax_id else _("No TRN on file"), _("VAT {0}%").format(vat)] if x)
	return {"values": {"due_date": str(due) if due else None, "_vat_rate": vat}, "force": ["_vat_rate"], "note": note}


def _fill_bill_source(name, v):
	if not name:
		return {"values": {}, "note": ""}
	pi, sdt = _bill_mapped(name)
	if not pi.get("items"):
		return {"values": {}, "rows": [], "note": _("Everything on {0} is already billed").format(name)}
	company = pi.company or _company()
	vat = _taxes_rate(pi) if pi.get("taxes") else _vat_rate(company, True, pi.supplier)
	rows = [{"_i": i, "item_code": r.item_code, "qty": flt(r.qty), "rate": flt(r.rate)} for i, r in enumerate(pi.items)]
	due = _supplier_due(pi.supplier, company, v.get("posting_date"), v.get("bill_date"))
	note = _("{0} · {1} · {2} lines to bill · {3}").format(_(sdt), pi.supplier_name or pi.supplier, len(rows), _money(sum(r["qty"] * r["rate"] for r in rows), pi.currency))
	return {"values": {"supplier": pi.supplier, "currency": pi.currency, "due_date": str(due) if due else None, "_vat_rate": vat},
		"force": ["supplier", "currency", "_vat_rate"], "rows": rows, "note": note}


def _fill_debit(name, v):
	if not name:
		return {"values": {}, "rows": [], "note": ""}
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note

	src = frappe.get_doc("Purchase Invoice", name)
	src.check_permission("read")
	dn = make_debit_note(name)
	rows = [{"_i": i, "item_code": r.item_code, "_item": f"{r.item_code} — {r.item_name}" if r.item_name and r.item_name != r.item_code else r.item_code,
		"_can": abs(flt(r.qty)), "qty": "", "rate": flt(r.rate)} for i, r in enumerate(dn.items) if abs(flt(r.qty)) > 0]
	# v1.8.4: the return quantities start empty (they defaulted to the whole bill) — "Can return" shows what is left
	note = _("{0} · bill {1} · {2} · {3}").format(src.supplier_name or src.supplier, src.bill_no or "—", frappe.format(src.posting_date, "Date"), _money(src.grand_total, src.currency)) + " · " + _("type the quantity returned on each line")
	if not rows:
		note = _("Everything on {0} has already been returned").format(name)
	return {"values": {"_vat_rate": _taxes_rate(src)}, "force": ["_vat_rate"], "rows": rows, "note": note}


def _pre_sales_invoice(doc, v, rows):
	"""v1.7.3: credit note (sales return) against a submitted tax invoice — ERPNext's make_sales_return, the quantities returned."""
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

	src = v.get("_return_against")
	if not src:
		frappe.throw(_("Choose the tax invoice the credit note is against"))
	frappe.get_doc("Sales Invoice", src).check_permission("read")
	cn = make_sales_return(src)
	want = {cint(r["_i"]): r for r in rows if r.get("_i") not in (None, "")}
	keep = []
	for i, row in enumerate(cn.items):
		r = want.get(i)
		if r and flt(r.get("qty")) < 0:  # v1.8.4: a minus is not turned into a return of that size silently
			frappe.throw(_("{0}: type the quantity returned as a positive number (e.g. 5, not −5)").format(row.item_name or row.item_code))
		q = abs(flt(r.get("qty"))) if r else 0
		if q <= 0:
			continue
		if q > abs(flt(row.qty)) + 0.0001:
			frappe.throw(_("{0}: only {1} can be returned").format(row.item_name or row.item_code, abs(flt(row.qty))))
		row.qty = -q
		row.stock_qty = -q * flt(row.conversion_factor or 1)
		keep.append(row)
	if not keep:
		frappe.throw(_("Enter the quantity returned on at least one line"))
	cn.set("items", keep)
	if cn.meta.has_field("update_outstanding_for_self"):
		cn.update_outstanding_for_self = 0
	for f in ("hs_return_reason", "remarks", "cost_center", "project"):
		if v.get(f) and cn.meta.has_field(f):
			cn.set(f, v[f])
	if v.get("posting_date"):
		cn.posting_date = v.posting_date
		if getdate(v.posting_date) != getdate(today()):
			cn.set_posting_time = 1
	cn.run_method("set_missing_values")
	cn.calculate_taxes_and_totals()
	cn.flags.hs_ready = True
	return cn


def _fill_credit_note(name, v):
	if not name:
		return {"values": {}, "rows": [], "note": ""}
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

	src = frappe.get_doc("Sales Invoice", name)
	src.check_permission("read")
	cn = make_sales_return(name)
	rows = [{"_i": i, "item_code": r.item_code, "_item": f"{r.item_code} — {r.item_name}" if r.item_name and r.item_name != r.item_code else r.item_code,
		"_can": abs(flt(r.qty)), "qty": "", "rate": flt(r.rate)} for i, r in enumerate(cn.items) if abs(flt(r.qty)) > 0]
	note = _("{0} · {1} · {2} · outstanding {3}").format(src.customer_name or src.customer, frappe.format(src.posting_date, "Date"), _money(src.grand_total, src.currency),
		_money(src.outstanding_amount, src.currency)) + " · " + _("type the quantity returned on each line")
	if not rows:
		note = _("Everything on {0} has already been credited").format(name)
	return {"values": {"_vat_rate": _taxes_rate(src)}, "force": ["_vat_rate"], "rows": rows, "note": note}


def _fill_receivable(name, v):
	from hipersign_trading.api.quick import open_invoices

	customer = v.get("customer")
	if not customer:
		return {"values": {}, "note": ""}
	frappe.get_doc("Customer", customer).check_permission("read")
	invs = open_invoices(customer, v.get("company"))
	owed = sum(flt(i.outstanding_amount) for i in invs)
	if not [i for i in invs if flt(i.outstanding_amount) > 0]:
		return {"values": {"amount": 0}, "note": _("{0} has no open invoices — record an advance on the full payment form.").format(customer)}
	amount = flt(v.get("amount")) if v.get("amount") not in (None, "") and name != customer else owed
	left = amount - sum(flt(i.outstanding_amount) for i in invs if flt(i.outstanding_amount) < 0)
	parts = []
	for i in invs:
		if flt(i.outstanding_amount) < 0:
			parts.append(_("{0} credit note {1}").format(i.name, _money(i.outstanding_amount, i.currency)))
			continue
		if left <= 0.005:
			break
		a = min(left, flt(i.outstanding_amount))
		parts.append(f"{i.name} {_money(a, i.currency)}" + (" " + _("(part)") if a < flt(i.outstanding_amount) - 0.005 else ""))
		left -= a
	note = _("Owes {0} on {1} invoice(s). Applied oldest first: {2}").format(_money(owed), len([i for i in invs if flt(i.outstanding_amount) > 0]), " · ".join(parts))
	if amount > owed + 0.005:
		note += " — " + _("more than the customer owes; record the extra as an advance on the full payment form.")
	return {"values": {"amount": owed}, "note": note}


def _fill_serial(name, v):
	if not name:
		return {"values": {}, "note": ""}
	frappe.get_doc("Serial No", name).check_permission("read")
	sn = _serial_info(name)
	out = {"customer": sn.customer, "item_code": sn.item_code, "warranty_expiry_date": str(sn.warranty_expiry_date) if sn.warranty_expiry_date else None,
		"amc_expiry_date": str(sn.amc_expiry_date) if sn.amc_expiry_date else None, "warranty_amc_status": sn.get("state")}
	note = " · ".join(x for x in [sn.item_name or sn.item_code, _("with {0}").format(sn.customer) if sn.customer else _("not delivered to a customer"),
		f"{_(sn.reference_doctype)} {sn.reference_name}" if sn.reference_name else "",
		_("warranty until {0}").format(frappe.format(sn.warranty_expiry_date, "Date")) if sn.warranty_expiry_date else _("no warranty date"), _(sn.get("state") or "")] if x)
	return {"values": {k: x for k, x in out.items() if x}, "force": [k for k, x in out.items() if x], "note": note}


def _fill_driver(name, v):
	if not name:
		return {"values": {}, "note": ""}
	frappe.get_doc("Driver", name).check_permission("read")
	veh = frappe.db.get_value("Delivery Trip", {"driver": name, "docstatus": ["<", 2]}, "vehicle", order_by="creation desc")
	if not veh:
		for c in frappe.get_all("Comment", filters={"reference_doctype": "Driver", "reference_name": name}, pluck="content", order_by="creation desc"):
			plate = frappe.utils.strip_html(c or "").replace("Drives", "").strip()
			if plate and frappe.db.exists("Vehicle", plate):
				veh = plate
				break
	mobile = frappe.db.get_value("Driver", name, "cell_number")
	return {"values": {"vehicle": veh} if veh else {}, "note": " · ".join(x for x in [_("Mobile {0}").format(mobile) if mobile else "", _("Usually drives {0}").format(veh) if veh else ""] if x)}


def _fill_trip_stop(name, v):
	if not name:
		return {"values": {"customer": "", "_customer": "", "address": "", "_address": ""}}
	frappe.get_doc("Delivery Note", name).check_permission("read")
	return {"values": _dn_stop(name)}


_FILL = {"credit_of_customer": _fill_credit, "supplier_bill": _fill_supplier_bill, "bill_source": _fill_bill_source, "debit_from_bill": _fill_debit, "credit_from_invoice": _fill_credit_note,
	"receivable": _fill_receivable, "serial_claim": _fill_serial, "driver_vehicle": _fill_driver, "trip_stop": _fill_trip_stop}
