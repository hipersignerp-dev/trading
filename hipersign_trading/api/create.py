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
from frappe.utils import add_days, cint, flt, getdate, today

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
def options(kind):
	"""Choice lists for one form."""
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


def _vat_rate(company, buying=False):
	dt = "Purchase Taxes and Charges Template" if buying else "Sales Taxes and Charges Template"
	tpl = None
	if not buying:
		tpl = frappe.db.get_single_value("Hipersign Settings", "local_tax_template") if frappe.get_meta("Hipersign Settings").has_field("local_tax_template") else None
		if tpl and frappe.db.get_value(dt, tpl, "company") != company:
			tpl = None
	tpl = tpl or frappe.db.get_value(dt, {"company": company, "is_default": 1, "disabled": 0}, "name") or frappe.db.get_value(dt, {"company": company, "disabled": 0, "title": ["like", "%5%"]}, "name") \
		or frappe.db.get_value(dt, {"company": company, "disabled": 0}, "name")
	if not tpl:
		return 0
	return flt(frappe.db.get_value(dt.replace(" Template", ""), {"parent": tpl}, "rate"))


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


def _lines(doc, lines, kind, need):
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
		doc.append("items", row)
	if not doc.get("items"):
		frappe.throw(_("Add at least one line with an item and a quantity"))


def _keep_rates(doc, lines):
	"""ERPNext re-prices lines on set_missing_values; keep the rate and discount the user typed."""
	typed = [r for r in lines if r.get("item_code") and flt(r.get("qty")) > 0]
	for row, r in zip(doc.items, typed):
		if r.get("rate") not in (None, "") and flt(r["rate"]) != flt(row.rate):
			row.price_list_rate = row.price_list_rate or flt(r["rate"])
			row.rate = flt(r["rate"])
			row.discount_percentage = 0
			row.margin_type = None
		if flt(r.get("discount")):
			row.discount_percentage = flt(r["discount"])
			if flt(row.price_list_rate):
				row.rate = flt(row.price_list_rate) * (1 - flt(r["discount"]) / 100)


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
	elif kind == "sales_order":
		doc.customer = values.party
		doc.delivery_date = need
		doc.po_no = values.get("po_no") or None
		doc.po_date = values.get("po_date") or None
		doc.shipping_address_name = values.get("shipping_address") or None
		doc.customer_address = values.get("billing_address") or None
		doc.set_warehouse = values.get("set_warehouse") or None
		for f in ("incoterm", "named_place", "hs_payment_method", "hs_shipment_mode"):
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
	_lines(doc, lines, kind, need)
	if values.get("sales_person") and doc.meta.has_field("sales_team"):
		doc.append("sales_team", {"sales_person": values.sales_person, "allocated_percentage": 100})
	doc.flags.hs_quick = True
	doc.set_missing_values()
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
	if (q or {}).get("query") == "hipersign_trading.api.crm.sales_users":
		from hipersign_trading.api.crm import sales_users

		return [{"name": r[0], "label": r[1] if len(r) > 1 and r[1] else r[0]} for r in sales_users("User", "", "name", 0, LIMIT, {})]
	title = meta.title_field if meta.title_field and meta.title_field != "name" and meta.has_field(meta.title_field) else None
	return _names(doctype, filters, title, f"{title} asc" if title else "name asc")
