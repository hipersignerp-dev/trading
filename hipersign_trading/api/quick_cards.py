"""v1.5.6: quick cards — the prototype's short "New …" cards for 13 masters.

Each card sends its values here; the record (and what goes with it — the customer's contact and address, the
item's prices and reorder level, the driver's vehicle …) is created through the normal document engine, so
naming, validation, permissions, credit-limit approval and the view-only demo guard all apply as on the full form.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from hipersign_trading.utils import user_company

CARDS = ("Lead", "Customer", "Supplier", "Item", "Address", "Contact", "Warehouse", "Employee", "Asset", "Customer Group",
	"Payment Terms Template", "Bank Account", "Driver")


def _v(values, key, default=None):
	val = values.get(key)
	if isinstance(val, str):
		val = val.strip()
	return default if val in (None, "") else val


def _need(values, *keys):
	for k in keys:
		if not _v(values, k):
			frappe.throw(_("Fill in {0}").format(k.replace("_", " ")), title=_("Missing information"))


def _split(full):
	parts = (full or "").strip().split()
	return (parts[0] if parts else ""), " ".join(parts[1:])


def _check_trn(trn):
	if trn and not (trn.isdigit() and len(trn) == 15):
		frappe.throw(_("TRN must be 15 digits"))


def _check_email(email):
	if email and not frappe.utils.validate_email_address(email):
		frappe.throw(_("Check the email address"))


def _contact(name, mobile=None, email=None, links=(), designation=None, primary=1, reports=1):
	first, last = _split(name)
	c = frappe.get_doc({"doctype": "Contact", "first_name": first or name, "last_name": last, "designation": designation,
		"is_primary_contact": primary, "links": [{"link_doctype": dt, "link_name": dn} for dt, dn in links]})
	if c.meta.has_field("hs_receives_reports"):
		c.hs_receives_reports = cint(reports)
	if mobile:
		c.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
	if email:
		c.append("email_ids", {"email_id": email, "is_primary": 1})
	c.insert()
	return c


def _address(title, line1, links=(), address_type="Billing", emirate=None, country="United Arab Emirates", city=None, line2=None, site_contact=None, phone=None):
	a = frappe.get_doc({"doctype": "Address", "address_title": title, "address_type": address_type, "address_line1": line1, "address_line2": line2,
		"city": city or emirate or line1, "country": country, "phone": phone, "is_primary_address": 1, "is_shipping_address": 1,
		"links": [{"link_doctype": dt, "link_name": dn} for dt, dn in links]})
	if a.meta.has_field("hs_emirate") and emirate:
		a.hs_emirate = emirate
	if a.meta.has_field("hs_site_contact") and site_contact:
		a.hs_site_contact = site_contact
	a.insert()
	return a


def _leaf(doctype, preferred=None):
	"""A non-group record of a tree (the settings' default when it is one)."""
	if preferred and not frappe.db.get_value(doctype, preferred, "is_group"):
		return preferred
	return frappe.db.get_value(doctype, {"is_group": 0}, order_by="creation asc") or preferred


def _company(values=None):
	"""The company a new record belongs to: the one chosen, else the user's, never a group (holding) company."""
	company = _v(values or {}, "company") or user_company()
	if company and frappe.db.get_value("Company", company, "is_group"):
		child = frappe.db.get_value("Company", {"parent_company": company, "is_group": 0}, order_by="creation asc")
		company = child or company
	return company


def _country(text):
	"""'China (Ningbo)' → ('China', 'Ningbo') when China is a Country."""
	text = (text or "").strip()
	name, city = text, ""
	if "(" in text and text.endswith(")"):
		name, city = text[: text.index("(")].strip(), text[text.index("(") + 1 : -1].strip()
	match = frappe.db.get_value("Country", {"name": ["like", name]}) if name else None
	return match, city or (name if not match else "")


@frappe.whitelist(methods=["POST"])
def create(doctype, values, link_doctype=None, link_name=None):
	if doctype not in CARDS:
		frappe.throw(_("No quick card for {0}").format(doctype))
	values = frappe.parse_json(values) if isinstance(values, str) else frappe._dict(values or {})
	values = frappe._dict(values)
	frappe.has_permission(doctype, "create", throw=True)
	doc = CARD_FN[doctype](values, link_doctype, link_name)
	return {"doctype": doc.doctype, "name": doc.name, "title": doc.get(doc.meta.title_field or "name") or doc.name, "doc": doc.as_dict()}


# ---------------------------------------------------------------- sales
def _lead(v, *_a):
	_need(v, "company_name", "lead_name", "mobile_no", "hs_interested_in")
	_check_email(_v(v, "email_id"))
	first, last = _split(v.lead_name)
	d = frappe.get_doc({"doctype": "Lead", "company_name": v.company_name, "first_name": first, "last_name": last, "mobile_no": v.mobile_no,
		"whatsapp_no": v.mobile_no, "email_id": _v(v, "email_id"), "hs_interested_in": v.hs_interested_in, "hs_estimated_value": flt(v.get("hs_estimated_value")),
		"hs_expected_close": _v(v, "hs_expected_close"), "hs_pipeline_stage": _v(v, "hs_pipeline_stage", "New"),
		"hs_next_follow_up": _v(v, "hs_next_follow_up"), "hs_next_action": _v(v, "hs_next_action"),
		"lead_owner": _v(v, "lead_owner", frappe.session.user), "country": "United Arab Emirates"})
	if d.meta.has_field("hs_emirate"):
		d.hs_emirate = _v(v, "hs_emirate")
		d.city = _v(v, "hs_emirate")
	if _v(v, "utm_source") and d.meta.has_field("utm_source"):
		d.utm_source = v.utm_source
	d.insert()
	if d.hs_next_follow_up:
		frappe.get_doc({"doctype": "ToDo", "allocated_to": d.lead_owner or frappe.session.user, "reference_type": "Lead", "reference_name": d.name,
			"date": d.hs_next_follow_up, "description": _("Follow up {0}: {1}").format(d.company_name, d.hs_next_action or d.hs_interested_in),
			"priority": "Medium"}).insert(ignore_permissions=True)
	return d


def _customer(v, *_a):
	_need(v, "customer_name", "contact_person", "mobile_no")
	_check_trn(_v(v, "tax_id"))
	_check_email(_v(v, "email_id"))
	if frappe.db.exists("Customer", {"customer_name": v.customer_name}):
		frappe.throw(_("{0} is already a customer").format(v.customer_name))
	if len("".join(ch for ch in v.mobile_no if ch.isdigit())) < 9:
		frappe.throw(_("Enter a valid mobile / WhatsApp number"))
	export = _v(v, "hs_market") == "Export"
	if export and not _v(v, "hs_country_city"):
		frappe.throw(_("Enter the country for an export customer"))
	country, city = _country(v.get("hs_country_city")) if export else ("United Arab Emirates", _v(v, "hs_emirate"))
	c = frappe.get_doc({"doctype": "Customer", "customer_name": v.customer_name, "customer_type": "Company",
		"customer_group": _v(v, "customer_group") or _leaf("Customer Group", frappe.db.get_single_value("Selling Settings", "customer_group")),
		"territory": _leaf("Territory", frappe.db.get_single_value("Selling Settings", "territory")),
		"tax_id": _v(v, "tax_id"), "payment_terms": _v(v, "payment_terms"), "default_currency": _v(v, "default_currency") if export else None,
		"hs_market": "Export" if export else "Local", "hs_country_city": _v(v, "hs_country_city") if export else None})
	if c.meta.has_field("hs_emirate") and not export:
		c.hs_emirate = _v(v, "hs_emirate")
	if c.meta.has_field("hs_lead_source"):
		c.hs_lead_source = _v(v, "hs_lead_source")
	if flt(v.get("credit_limit")) > 0:
		c.append("credit_limits", {"company": _company(v), "credit_limit": flt(v.credit_limit)})
	c.insert()
	contact = _contact(v.contact_person, v.mobile_no, _v(v, "email_id"), [("Customer", c.name)], designation=_v(v, "designation", "Purchasing"))
	addr = _address(_("Main office"), (city or country or "—"), [("Customer", c.name)], emirate=None if export else _v(v, "hs_emirate"),
		country=country or "United Arab Emirates", city=city)
	c.db_set({"customer_primary_contact": contact.name, "customer_primary_address": addr.name, "mobile_no": v.mobile_no, "email_id": _v(v, "email_id")})
	return c


# ---------------------------------------------------------------- buying
def _supplier(v, *_a):
	_need(v, "supplier_name", "country", "contact_person")
	_check_trn(_v(v, "tax_id"))
	_check_email(_v(v, "email_id"))
	if frappe.db.exists("Supplier", {"supplier_name": v.supplier_name}):
		frappe.throw(_("{0} is already in the supplier register").format(v.supplier_name))
	country, city = _country(v.country)
	s = frappe.get_doc({"doctype": "Supplier", "supplier_name": v.supplier_name, "supplier_type": "Company",
		"supplier_group": _v(v, "supplier_group") or _leaf("Supplier Group", frappe.db.get_single_value("Buying Settings", "supplier_group")),
		"country": country, "default_currency": _v(v, "default_currency"), "payment_terms": _v(v, "payment_terms"), "tax_id": _v(v, "tax_id")})
	if s.meta.has_field("hs_supplier_kind"):
		s.hs_supplier_kind = _v(v, "hs_supplier_kind", "Goods supplier")
	if s.meta.has_field("hs_incoterm"):
		s.hs_incoterm = _v(v, "hs_incoterm")
	s.insert()
	contact = _contact(v.contact_person, _v(v, "mobile_no"), _v(v, "email_id"), [("Supplier", s.name)], designation="Sales")
	addr = _address(_("Head office"), city or country or v.country, [("Supplier", s.name)], country=country or "United Arab Emirates", city=city or None)
	s.db_set({"supplier_primary_contact": contact.name, "supplier_primary_address": addr.name})
	if _v(v, "iban"):
		bank = _v(v, "bank") or _ensure_bank(_("Supplier bank"))
		frappe.get_doc({"doctype": "Bank Account", "account_name": s.supplier_name, "bank": bank, "iban": v.iban.replace(" ", ""),
			"party_type": "Supplier", "party": s.name, "is_default": 1}).insert(ignore_permissions=True)  # part of the new supplier
	return s


def _ensure_bank(name, swift=None):
	if not frappe.db.exists("Bank", name):
		frappe.get_doc({"doctype": "Bank", "bank_name": name, "swift_number": swift}).insert(ignore_permissions=True)
	elif swift and not frappe.db.get_value("Bank", name, "swift_number"):
		frappe.db.set_value("Bank", name, "swift_number", swift)
	return name


def _item(v, *_a):
	_need(v, "item_name")
	if flt(v.get("standard_cost")) <= 0 or flt(v.get("standard_rate")) <= 0:
		frappe.throw(_("Enter the standard cost and the standard selling price"))
	company = _company(v)
	code = v.get("item_code") or v.item_name
	if frappe.db.exists("Item", code):
		frappe.throw(_("Item {0} already exists").format(code))
	hs = _v(v, "customs_tariff_number")
	if hs and not frappe.db.exists("Customs Tariff Number", hs):
		frappe.get_doc({"doctype": "Customs Tariff Number", "tariff_number": hs, "description": v.item_name}).insert(ignore_permissions=True)
	wh = _v(v, "default_warehouse")
	i = frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": v.item_name, "item_group": _v(v, "item_group") or "All Item Groups",
		"stock_uom": _v(v, "stock_uom", "Nos"), "is_stock_item": cint(v.get("is_stock_item", 1)), "include_item_in_manufacturing": 0, "valuation_rate": flt(v.standard_cost),
		"customs_tariff_number": hs, "country_of_origin": _country(v.get("country_of_origin"))[0],
		"hs_item_name_ar": _v(v, "hs_item_name_ar")})
	if not i.is_stock_item:
		wh = None
	if wh:
		i.append("item_defaults", {"company": frappe.db.get_value("Warehouse", wh, "company") or company, "default_warehouse": wh})
		if cint(v.get("reorder_level")) > 0:
			i.append("reorder_levels", {"warehouse": wh, "warehouse_reorder_level": cint(v.reorder_level),
				"warehouse_reorder_qty": cint(v.reorder_level), "material_request_type": "Purchase"})
	i.insert()
	for pl, rate in (("Standard Buying", v.standard_cost), ("Standard Selling", v.standard_rate)):
		if frappe.db.exists("Price List", pl):
			frappe.get_doc({"doctype": "Item Price", "item_code": i.name, "price_list": pl, "price_list_rate": flt(rate), "uom": i.stock_uom}).insert()
	return i


# ---------------------------------------------------------------- parties' details
def _address_(v, link_doctype=None, link_name=None):
	_need(v, "address_title", "address_line1")
	links = [(link_doctype, link_name)] if link_doctype and link_name else []
	return _address(v.address_title, v.address_line1, links, address_type=_v(v, "address_type", "Shipping"), emirate=_v(v, "hs_emirate"),
		line2=_v(v, "address_line2"), site_contact=_v(v, "hs_site_contact"))



def _contact_(v, link_doctype=None, link_name=None):
	_need(v, "full_name", "mobile_no")
	_check_email(_v(v, "email_id"))
	links = [(link_doctype, link_name)] if link_doctype and link_name else []
	return _contact(v.full_name, v.mobile_no, _v(v, "email_id"), links, designation=_v(v, "designation"),
		primary=cint(v.get("is_primary_contact")), reports=cint(v.get("hs_receives_reports")))


# ---------------------------------------------------------------- stock and delivery
def _warehouse(v, *_a):
	_need(v, "warehouse_name", "address_line_1")
	company = _company(v)
	w = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": v.warehouse_name, "company": company, "warehouse_type": _v(v, "warehouse_type"),
		"address_line_1": v.address_line_1, "city": _v(v, "hs_emirate")})
	for f in ("hs_emirate", "hs_capacity_pallets", "hs_in_charge"):
		if w.meta.has_field(f) and v.get(f):
			w.set(f, v.get(f))
	parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["in", ["", None]]})
	if parent:
		w.parent_warehouse = parent
	w.insert()
	return w


def _driver(v, *_a):
	_need(v, "full_name", "license_plate")
	plate = v.license_plate.strip()
	if not frappe.db.exists("Vehicle", plate):
		vt = _v(v, "hs_vehicle_type", "Van")
		veh = frappe.get_doc({"doctype": "Vehicle", "license_plate": plate, "make": _v(v, "make", "—"), "model": _v(v, "model", vt), "last_odometer": 0,
			"fuel_type": "Diesel", "uom": frappe.db.get_value("UOM", {"name": ["in", ["Litre", "Liter", "Nos"]]}) or "Nos", "company": _company()})
		if veh.meta.has_field("hs_vehicle_type"):
			veh.hs_vehicle_type = vt
		veh.insert()
	d = frappe.get_doc({"doctype": "Driver", "full_name": v.full_name, "cell_number": _v(v, "cell_number"), "status": "Active"})
	d.insert()
	d.add_comment("Comment", _("Drives {0}").format(plate))
	return d


# ---------------------------------------------------------------- people and assets
def _employee(v, *_a):
	_need(v, "employee_name", "designation", "cell_number", "gender", "date_of_birth")
	if flt(v.get("hs_basic_salary")) <= 0:
		frappe.throw(_("Enter the basic salary"))
	company = _company(v)
	if not frappe.db.exists("Designation", v.designation):
		frappe.get_doc({"doctype": "Designation", "designation_name": v.designation}).insert(ignore_permissions=True)
	first, last = _split(v.employee_name)
	e = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last, "company": company, "status": "Active",
		"gender": v.gender, "date_of_birth": v.date_of_birth, "date_of_joining": _v(v, "date_of_joining", today()), "designation": v.designation,
		"department": _v(v, "department"), "cell_number": v.cell_number, "personal_email": _v(v, "personal_email"),
		"salary_mode": "Bank" if _v(v, "iban") else "Cash", "iban": _v(v, "iban"), "valid_upto": _v(v, "valid_upto"),
		"hs_visa_expiry": _v(v, "hs_visa_expiry"), "hs_emirates_id_expiry": _v(v, "hs_emirates_id_expiry"), "hs_labour_card_expiry": _v(v, "hs_labour_card_expiry")})
	parts = ("hs_basic_salary", "hs_housing_allowance", "hs_transport_allowance", "hs_other_allowance")
	for f in parts:
		if e.meta.has_field(f):
			e.set(f, flt(v.get(f)))
	e.insert()
	_salary_assignment(e, sum(flt(v.get(f)) for f in parts))
	return e


def _salary_assignment(emp, base):
	"""Payroll picks the new employee up when the standard structure exists (base = the monthly package)."""
	ss = frappe.db.get_value("Salary Structure", {"docstatus": 1, "is_active": "Yes", "company": emp.company}, "name", order_by="creation desc")
	if not ss or base <= 0:
		return
	try:
		payable = frappe.db.get_value("Company", emp.company, "default_payroll_payable_account")
		a = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": emp.name, "salary_structure": ss, "company": emp.company,
			"from_date": emp.date_of_joining, "base": base, "currency": frappe.db.get_value("Company", emp.company, "default_currency"),
			"payroll_payable_account": payable})
		a.insert()
		a.submit()
	except Exception:
		frappe.clear_last_message()
		frappe.log_error(title=f"Quick card: salary assignment for {emp.name}")


def _asset(v, *_a):
	_need(v, "asset_name", "asset_category", "location")
	cost = flt(v.get("net_purchase_amount"))
	if cost <= 0:
		frappe.throw(_("Enter the cost"))
	company = _company(v)
	cat = v.asset_category
	code = frappe.db.get_value("Item", {"asset_category": cat, "is_fixed_asset": 1, "disabled": 0})
	if not code:
		code = "FA-" + cat.upper().replace(" ", "-").replace("&", "AND")[:20]
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": cat, "item_group": frappe.db.get_value("Item Group", {"is_group": 0}),
				"stock_uom": "Nos", "is_stock_item": 0, "is_fixed_asset": 1, "asset_category": cat}).insert()
	purchased = _v(v, "purchase_date", today())
	life = cint(v.get("useful_life")) or 60
	a = frappe.get_doc({"doctype": "Asset", "item_code": code, "asset_name": v.asset_name, "asset_category": cat, "company": company,
		"location": v.location, "custodian": _v(v, "custodian"), "supplier": _v(v, "supplier"), "asset_type": "Existing Asset", "is_existing_asset": 1,
		"purchase_date": purchased, "available_for_use_date": purchased, "gross_purchase_amount": cost, "purchase_amount": cost,
		"net_purchase_amount": cost, "insurance_end_date": _v(v, "insurance_end_date"), "calculate_depreciation": 1,
		"finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": life, "frequency_of_depreciation": 1,
			"expected_value_after_useful_life": flt(v.get("residual_value")),
			"depreciation_start_date": frappe.utils.get_last_day(frappe.utils.add_months(getdate(purchased), 0))}]})
	for f in ("hs_plate_no", "hs_registration_expiry", "hs_next_service"):
		if a.meta.has_field(f) and v.get(f):
			a.set(f, v.get(f))
	a.insert()
	return a


# ---------------------------------------------------------------- set-up masters
def _customer_group(v, *_a):
	_need(v, "customer_group_name")
	g = frappe.get_doc({"doctype": "Customer Group", "customer_group_name": v.customer_group_name, "parent_customer_group": "All Customer Groups",
		"payment_terms": _v(v, "payment_terms")})
	if flt(v.get("credit_limit")) > 0:
		g.append("credit_limits", {"company": _company(v), "credit_limit": flt(v.credit_limit)})
	g.insert()
	disc = flt(v.get("discount_percentage"))
	if disc:
		frappe.get_doc({"doctype": "Pricing Rule", "title": _("{0} group discount").format(g.name), "apply_on": "Item Group",
			"items": [], "item_groups": [{"item_group": "All Item Groups"}], "selling": 1, "applicable_for": "Customer Group", "customer_group": g.name,
			"rate_or_discount": "Discount Percentage", "discount_percentage": disc, "price_or_product_discount": "Price",
			"for_price_list": "Standard Selling" if frappe.db.exists("Price List", "Standard Selling") else None, "company": _company(v)}).insert()
	return g


def _payment_terms_template(v, *_a):
	_need(v, "template_name")
	adv = flt(v.get("advance_percent"))
	if adv < 0 or adv > 100:
		frappe.throw(_("Advance must be between 0 and 100%"))
	days = cint(v.get("credit_days"))
	based = "Day(s) after the end of the invoice month" if v.get("based_on") == "Month end" else "Day(s) after invoice date"
	rows = []
	if adv:
		rows.append({"payment_term": _term(_("Advance"), "Day(s) after invoice date", 0, advance=1), "description": _("Advance"),
			"invoice_portion": adv, "due_date_based_on": "Day(s) after invoice date", "credit_days": 0})
	if adv < 100:
		label = (_("Balance {0} days") if adv else _("Net {0} days")).format(days) + (" " + _("from month end") if v.get("based_on") == "Month end" else "")
		rows.append({"payment_term": _term(label, based, days), "description": _("Balance") if adv else _("Payment"),
			"invoice_portion": 100 - adv, "due_date_based_on": based, "credit_days": days})
	return frappe.get_doc({"doctype": "Payment Terms Template", "template_name": v.template_name, "allocate_payment_based_on_payment_terms": 1, "terms": rows}).insert()


def _term(name, based_on, days, advance=0):
	"""The Payment Term master a template row points to (made once, then reused)."""
	if not frappe.db.exists("Payment Term", name):
		t = frappe.get_doc({"doctype": "Payment Term", "payment_term_name": name, "due_date_based_on": based_on, "credit_days": days, "invoice_portion": 0})
		if t.meta.has_field("hs_is_advance"):
			t.hs_is_advance = advance
		t.insert(ignore_permissions=True)
	return name


def _bank_account(v, *_a):
	_need(v, "bank", "account_name", "iban")
	iban = v.iban.replace(" ", "").upper()
	company = _company(v)
	bank = _ensure_bank(v.bank, _v(v, "swift"))
	currency = _v(v, "currency") or frappe.db.get_value("Company", company, "default_currency")
	parent = frappe.db.get_value("Account", {"company": company, "account_type": "Bank", "is_group": 1}) or frappe.db.get_value(
		"Account", {"company": company, "account_name": "Bank Accounts", "is_group": 1})
	label = f"{bank} {currency} {iban[-4:]}"
	gl = frappe.db.get_value("Account", {"company": company, "account_name": label})
	if not gl:
		acc = frappe.get_doc({"doctype": "Account", "account_name": label, "company": company, "parent_account": parent, "account_type": "Bank",
			"account_currency": currency, "root_type": "Asset", "report_type": "Balance Sheet"})
		# a group's member company keeps its own bank accounts (ERPNext would ask to add it in the holding company first)
		acc.flags.ignore_root_company_validation = True
		gl = acc.insert(ignore_permissions=True).name
	return frappe.get_doc({"doctype": "Bank Account", "account_name": v.account_name, "bank": bank, "iban": iban, "is_company_account": 1,
		"company": company, "account": gl, "is_default": cint(v.get("is_default"))}).insert()


CARD_FN = {
	"Lead": _lead, "Customer": _customer, "Supplier": _supplier, "Item": _item, "Address": _address_, "Contact": _contact_,
	"Warehouse": _warehouse, "Employee": _employee, "Asset": _asset, "Customer Group": _customer_group,
	"Payment Terms Template": _payment_terms_template, "Bank Account": _bank_account, "Driver": _driver,
}
