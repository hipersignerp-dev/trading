"""Demo data loader for a Hipersign demo site.

Run ONLY on a separate demo site, after the ERPNext setup wizard is complete:

    bench --site hipersign-demo.localhost execute hipersign_trading.demo.load

It is safe to run twice: records that already exist are skipped. Each block runs in its own
savepoint, so one failure does not stop the rest; a summary is printed at the end.
"""

import zlib

import frappe
from frappe.utils import add_days, flt, getdate, today

from hipersign_trading.constants import SERIAL_ITEMS
from hipersign_trading.demo import data as D

LOG = []
HS_WORKFLOWS = [
	"Hipersign Purchase Order Approval",
	"Hipersign Sales Order Approval",
	"Hipersign Supplier Payment Approval",
	"Hipersign Stock Count Approval",
	"Hipersign Credit Limit Approval",
]


def load_from_button(user=None):
	"""Background job behind Hipersign Settings → Load demo data."""
	frappe.flags.hs_force_demo = True
	try:
		load()
		frappe.db.set_default("hs_demo_loaded", 1)
		frappe.db.commit()
		msg = ("The demo switched this site to the Enterprise pack, group of companies, so every feature has sample data. "
			"Change it any time in Hipersign Settings → Setup & features.\n\n" + "\n".join(LOG))
		ind = "green" if not any(x.startswith("✗") for x in LOG) else "orange"
	except Exception:
		frappe.log_error(title="Hipersign demo data")
		msg, ind = "Demo data could not be loaded — see the Error Log.", "red"
	finally:
		frappe.cache.delete_value("hs_demo_running")
	if user:
		frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "subject": "Hipersign demo data loaded" if ind != "red" else "Hipersign demo data failed",
			"email_content": "<pre>" + frappe.utils.escape_html(msg) + "</pre>"}).insert(ignore_permissions=True)
		frappe.db.commit()


def load():
	if frappe.conf.get("hipersign_demo_site") is not True and not frappe.flags.hs_force_demo:
		print(
			"Refusing to load demo data: add  \"hipersign_demo_site\": true  to this site's site_config.json first.\n"
			"   bench --site <demo-site> set-config -p hipersign_demo_site true"
		)
		return
	LOG.clear()
	ctx = context()
	frappe.flags.hs_apply_credit_limit = True
	frappe.flags.mute_emails = True
	frappe.flags.hs_skip_doc_rules = True  # documents are attached in v13_documents; history is not blocked
	frappe.flags.hs_demo_loading = True  # history is created in any order: a re-run must not trip over today's KYC blocks
	paused = pause_workflows()
	try:
		for step in (
			taxes_and_settings, currencies, banks, item_groups_and_uoms, warehouses, items, customer_groups_and_pricing,
			payment_terms, customers, suppliers, lead_sources_and_leads, demo_users, opening_stock, purchasing_and_imports,
			opening_stock_serialised, quotations, sales_orders, exports, returns_and_credit_notes, post_dated_cheques,
			people_and_documents, drivers_and_deliveries, warranty_claims, portal_user, home_workspaces,
		):
			run(step, ctx)
		from hipersign_trading.demo import v12, v13

		for step in (
			v12.v12_masters, v12.v12_advances, v12.v12_collections, v12.v12_purchasing, v12.v12_reservations,
			v12.v12_trade_finance, v12.v12_tax_returns, v12.v12_revaluation, v12.v12_group,
		):
			run(step, ctx)
		for step in v13.STEPS:
			run(step, ctx)
		from hipersign_trading.demo import v15

		for step in v15.STEPS:
			run(step, ctx)
	finally:
		resume_workflows(paused)
		frappe.flags.hs_apply_credit_limit = False
		frappe.flags.hs_skip_doc_rules = False
		frappe.flags.hs_demo_loading = False
	run(set_pending_states, ctx)
	frappe.db.commit()
	print("\n".join(LOG))
	print("\nDone. Take a backup now so you can reset the demo later:\n   bench --site %s backup --with-files" % frappe.local.site)


# ------------------------------------------------------------------ framework
def run(step, ctx):
	sp = "hs_" + step.__name__
	frappe.db.savepoint(sp)
	try:
		step(ctx)
		LOG.append(f"✓ {step.__name__}")
	except Exception as e:
		frappe.db.rollback(save_point=sp)
		LOG.append(f"✗ {step.__name__}: {e}")
		frappe.log_error(title=f"Hipersign demo: {step.__name__}")


def context():
	company = frappe.db.get_single_value("Hipersign Settings", "company") or frappe.defaults.get_global_default("company")
	if not company:
		frappe.throw("Complete the ERPNext setup wizard first (company, UAE, AED).")
	abbr = frappe.get_cached_value("Company", company, "abbr")
	ensure_fiscal_years([add_days(today(), -200), today()], company)
	return frappe._dict(company=company, abbr=abbr, t=today(), wh=lambda n: f"{n} - {abbr}", d=lambda n: add_days(today(), n))


def ensure_fiscal_years(dates, company):
	from erpnext.accounts.utils import get_fiscal_year

	for dt in dates:
		try:
			get_fiscal_year(dt, company=company)
		except Exception:
			y = getdate(dt).year
			if not frappe.db.exists("Fiscal Year", str(y)):
				frappe.get_doc({"doctype": "Fiscal Year", "year": str(y), "year_start_date": f"{y}-01-01", "year_end_date": f"{y}-12-31"}).insert()


def get_or_insert(doc, key=None):
	key = key or {k: doc[k] for k in ("name",) if k in doc}
	name = frappe.db.exists(doc["doctype"], key) if key else None
	if name:
		return frappe.get_doc(doc["doctype"], name)
	d = frappe.get_doc(doc)
	d.insert(ignore_permissions=True)
	return d


def pause_workflows():
	active = [w for w in HS_WORKFLOWS if frappe.db.get_value("Workflow", w, "is_active")]
	for w in active:
		frappe.db.set_value("Workflow", w, "is_active", 0)
	frappe.clear_cache()
	return active


def resume_workflows(active):
	for w in active:
		frappe.db.set_value("Workflow", w, "is_active", 1)
	frappe.clear_cache()


def backdate(doc, date):
	if doc.meta.has_field("set_posting_time"):
		doc.set_posting_time = 1
	for f in ("posting_date", "transaction_date"):
		if doc.meta.has_field(f):
			doc.set(f, date)


# ------------------------------------------------------------------ masters
def taxes_and_settings(c):
	# ERPNext v16: serial / batch numbers are off by default; export customers invoice in USD on the AED receivable
	for dt, field in (("Stock Settings", "enable_serial_and_batch_no_for_item"), ("Accounts Settings", "allow_multi_currency_invoices_against_single_party_account")):
		if frappe.get_meta(dt).has_field(field):
			frappe.db.set_single_value(dt, field, 1)
	parent = frappe.db.get_value("Account", {"company": c.company, "account_name": "Duties and Taxes", "is_group": 1}) or frappe.db.get_value(
		"Account", {"company": c.company, "root_type": "Liability", "is_group": 1}, order_by="lft desc"
	)
	vat = frappe.db.get_value("Account", {"company": c.company, "account_name": "VAT 5%"})
	if not vat:
		vat = frappe.get_doc({"doctype": "Account", "account_name": "VAT 5%", "parent_account": parent, "company": c.company, "account_type": "Tax", "tax_rate": 5}).insert().name
	def tmpl(doctype, title, rate):
		name = frappe.db.exists(doctype, {"title": title, "company": c.company})
		if name:
			return name
		return frappe.get_doc({"doctype": doctype, "title": title, "company": c.company,
			"taxes": [{"charge_type": "On Net Total", "account_head": vat, "description": title, "rate": rate}]}).insert().name
	local = tmpl("Sales Taxes and Charges Template", "UAE VAT 5%", 5)
	export = tmpl("Sales Taxes and Charges Template", "Zero Rated Export", 0)
	c.purchase_tax = tmpl("Purchase Taxes and Charges Template", "UAE VAT 5% Purchase", 5)
	s = frappe.get_single("Hipersign Settings")
	s.company = c.company
	s.local_tax_template, s.export_tax_template = local, export
	s.landed_cost_expense_account = frappe.get_cached_value("Company", c.company, "expenses_included_in_valuation")
	s.bank_charges_account = bank_charges_account(c)
	s.save()
	# serial numbers are picked first-in-first-out on delivery
	ss = frappe.get_meta("Stock Settings")
	if ss.has_field("auto_create_serial_and_batch_bundle_for_outward"):
		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 1)
	if ss.has_field("pick_serial_and_batch_based_on"):
		frappe.db.set_single_value("Stock Settings", "pick_serial_and_batch_based_on", "FIFO")
	c.local_tax, c.export_tax = local, export


def bank_charges_account(c):
	acc = frappe.db.get_value("Account", {"company": c.company, "account_name": ["like", "%Bank Charges%"], "is_group": 0})
	if acc:
		return acc
	parent = frappe.db.get_value("Account", {"company": c.company, "account_name": "Indirect Expenses", "is_group": 1}) or frappe.db.get_value(
		"Account", {"company": c.company, "root_type": "Expense", "is_group": 1}, order_by="lft")
	return frappe.get_doc({"doctype": "Account", "account_name": "Bank Charges", "parent_account": parent, "company": c.company,
		"root_type": "Expense", "account_type": "Chargeable"}).insert().name


def currencies(c):
	for cur, rate in D.FX.items():
		frappe.db.set_value("Currency", cur, "enabled", 1)
		if not frappe.db.exists("Currency Exchange", {"from_currency": cur, "to_currency": "AED", "date": c.d(-200)}):
			frappe.get_doc({"doctype": "Currency Exchange", "date": c.d(-200), "from_currency": cur, "to_currency": "AED",
				"exchange_rate": rate, "for_buying": 1, "for_selling": 1}).insert()


def banks(c):
	group = frappe.db.get_value("Account", {"company": c.company, "account_type": "Bank", "is_group": 1}) or frappe.db.get_value(
		"Account", {"company": c.company, "account_name": "Bank Accounts", "is_group": 1})
	for bank, swift, acc_name, gl_name, iban, cur, default in [
		("Emirates NBD", "EBILAEAD", "Current account — AED", "Emirates NBD Current", "AE18 0260 0010 1234 5678 901", "AED", 1),
		("Mashreq Bank", "BOMLAEAD", "USD account — import payments", "Mashreq USD", "AE49 0350 0000 1234 5678 902", "USD", 0),
	]:
		get_or_insert({"doctype": "Bank", "bank_name": bank, "swift_number": swift}, {"name": bank})
		gl = frappe.db.get_value("Account", {"company": c.company, "account_name": gl_name})
		if not gl:
			gl = frappe.get_doc({"doctype": "Account", "account_name": gl_name, "parent_account": group, "company": c.company,
				"account_type": "Bank", "account_currency": cur}).insert().name
		if not frappe.db.exists("Bank Account", {"iban": iban.replace(" ", "")}) and not frappe.db.exists("Bank Account", {"iban": iban}):
			frappe.get_doc({"doctype": "Bank Account", "account_name": acc_name, "bank": bank, "is_company_account": 1,
				"company": c.company, "account": gl, "iban": iban.replace(" ", ""), "is_default": default}).insert()
		if default:
			c.bank_gl = gl
			frappe.db.set_single_value("Hipersign Settings", "cheque_bank_account", gl)
			# ERPNext's UAE chart makes a credit-card account the company bank and "Trade in Opening Fees" the
			# receivable: the demo company banks with Emirates NBD and invoices customers on Trade Receivable
			frappe.db.set_value("Company", c.company, "default_bank_account", gl)
			rec = frappe.db.get_value("Account", {"company": c.company, "account_name": "Trade Receivable", "is_group": 0, "account_type": "Receivable"})
			if rec and "Opening" in (frappe.get_cached_value("Company", c.company, "default_receivable_account") or ""):
				frappe.db.set_value("Company", c.company, "default_receivable_account", rec)
			frappe.clear_document_cache("Company", c.company)


def item_groups_and_uoms(c):
	for g in sorted({i[3] for i in D.ITEMS} | {"Services"}):
		get_or_insert({"doctype": "Item Group", "item_group_name": g, "parent_item_group": "All Item Groups"}, {"name": g})
	for u in ["Nos", "Set", "Job", "Year", "Trip", "Visit", "Hour", "Session"]:
		get_or_insert({"doctype": "UOM", "uom_name": u, "must_be_whole_number": 0}, {"name": u})


def warehouses(c):
	parent = frappe.db.get_value("Warehouse", {"company": c.company, "is_group": 1, "parent_warehouse": ["in", ["", None]]}) or f"All Warehouses - {c.abbr}"
	for name, loc in D.WAREHOUSES:
		if not frappe.db.exists("Warehouse", c.wh(name)):
			frappe.get_doc({"doctype": "Warehouse", "warehouse_name": name, "company": c.company, "parent_warehouse": parent, "address_line_1": loc}).insert()


def items(c):
	buying = frappe.db.get_single_value("Buying Settings", "buying_price_list") or "Standard Buying"
	selling = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	c.selling_pl = selling
	for code, name, ar, grp, uom, hs, origin, reorder, sell, cost, wh, _q in D.ITEMS:
		get_or_insert({"doctype": "Customs Tariff Number", "tariff_number": hs, "description": name}, {"name": hs})
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "description": name, "item_group": grp,
				"stock_uom": uom, "is_stock_item": 1, "valuation_rate": cost, "customs_tariff_number": hs,
				"country_of_origin": origin, "hs_item_name_ar": ar,
				"item_defaults": [{"company": c.company, "default_warehouse": c.wh(wh)}],
				**serial_fields(code),
				"reorder_levels": [{"warehouse": c.wh(wh), "warehouse_reorder_level": reorder, "warehouse_reorder_qty": reorder, "material_request_type": "Purchase"}],
				**hsn_fields(hs, name),
			}).insert()
		price(code, selling, sell)
		price(code, buying, cost)
	for code, name, ar, uom, sell, cost in D.SERVICES:
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "description": name, "item_group": "Services",
				"stock_uom": uom, "is_stock_item": 0, "valuation_rate": cost, "hs_item_name_ar": ar, **hsn_fields("998719", "Other support services")}).insert()
		price(code, selling, sell)


def hsn_fields(code, description):
	"""Sites with India Compliance installed require an HSN/SAC code on every item: use the item's HS code."""
	if not frappe.get_meta("Item").has_field("gst_hsn_code") or not frappe.db.table_exists("GST HSN Code"):
		return {}
	code = "".join(ch for ch in str(code) if ch.isdigit())[:8]
	if len(code) < 6:
		return {}
	try:
		if not frappe.db.exists("GST HSN Code", code):
			frappe.get_doc({"doctype": "GST HSN Code", "hsn_code": code, "description": description}).insert(ignore_permissions=True)
	except Exception:
		return {}  # the item is still created when the site does not insist on HSN codes
	return {"gst_hsn_code": code}


def serials_on():
	return not frappe.conf.get("hipersign_demo_no_serials")


def serial_fields(code):
	"""ITM-004/005/007/011/013 carry serial numbers and a warranty, as in the prototype."""
	from hipersign_trading.api.serials import warranty_days

	if code not in SERIAL_ITEMS or not serials_on():
		return {}
	pre, months = SERIAL_ITEMS[code]
	return {"has_serial_no": 1, "serial_no_series": f"{pre}-.######", "warranty_period": warranty_days(months)}


def price(item, price_list, rate):
	if not frappe.db.exists("Item Price", {"item_code": item, "price_list": price_list}):
		frappe.get_doc({"doctype": "Item Price", "item_code": item, "price_list": price_list, "price_list_rate": rate}).insert()


def customer_groups_and_pricing(c):
	for g, disc in D.GROUP_DISCOUNT.items():
		get_or_insert({"doctype": "Customer Group", "customer_group_name": g, "parent_customer_group": "All Customer Groups"}, {"name": g})
		if disc and not frappe.db.exists("Pricing Rule", {"title": f"{g} group discount"}):
			frappe.get_doc({"doctype": "Pricing Rule", "title": f"{g} group discount", "apply_on": "Item Group",
				"item_groups": [{"item_group": "All Item Groups"}], "applicable_for": "Customer Group", "customer_group": g,
				"selling": 1, "rate_or_discount": "Discount Percentage", "discount_percentage": disc, "company": c.company}).insert()


def payment_terms(c):
	for template, terms in D.PAYMENT_TERMS:
		rows = []
		for term, portion, days in terms:
			get_or_insert({"doctype": "Payment Term", "payment_term_name": term, "invoice_portion": portion,
				"due_date_based_on": "Day(s) after invoice date", "credit_days": days}, {"name": term})
			rows.append({"payment_term": term, "invoice_portion": portion, "due_date_based_on": "Day(s) after invoice date", "credit_days": days})
		get_or_insert({"doctype": "Payment Terms Template", "template_name": template, "terms": rows}, {"name": template})


def party_contact(doctype, party, person, mobile, email, city, country, line):
	if frappe.db.get_value(doctype, party, "customer_primary_contact" if doctype == "Customer" else "supplier_primary_contact"):
		return
	first, _, last = person.partition(" ")
	ct = frappe.get_doc({"doctype": "Contact", "first_name": first, "last_name": last, "is_primary_contact": 1,
		"email_ids": [{"email_id": email, "is_primary": 1}], "phone_nos": [{"phone": mobile, "is_primary_mobile_no": 1}],
		"links": [{"link_doctype": doctype, "link_name": party}]}).insert()
	ad = frappe.get_doc({"doctype": "Address", "address_title": party, "address_type": "Billing", "address_line1": line,
		"city": city, "country": country, "is_primary_address": 1, "is_shipping_address": 1,
		"links": [{"link_doctype": doctype, "link_name": party}]}).insert()
	if doctype == "Customer":
		frappe.db.set_value("Customer", party, {"customer_primary_contact": ct.name, "mobile_no": mobile, "email_id": email, "customer_primary_address": ad.name})
	else:
		frappe.db.set_value("Supplier", party, {"supplier_primary_contact": ct.name, "mobile_no": mobile, "email_id": email, "supplier_primary_address": ad.name})


def customers(c):
	for name, grp, limit, terms, emirate, trn, person, mobile, email in D.CUSTOMERS:
		if not frappe.db.exists("Customer", name):
			frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Company", "customer_group": grp,
				"territory": "All Territories", "tax_id": trn, "payment_terms": terms, "hs_market": "Local",
				"credit_limits": [{"company": c.company, "credit_limit": limit}]}).insert()
		party_contact("Customer", name, person, mobile, email, emirate, "United Arab Emirates", f"Business district, {emirate}")
	for name, cc, country, cur, person, mobile, email, inc, place, pay, mode in D.EXPORT_CUSTOMERS:
		if not frappe.db.exists("Customer", name):
			frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Company", "customer_group": "Export",
				"territory": "All Territories", "default_currency": cur, "payment_terms": "Net 30 days", "hs_market": "Export",
				"hs_country_city": cc, "hs_default_incoterm": inc if frappe.db.exists("Incoterm", inc) else None,
				"hs_default_named_place": place, "hs_default_payment_method": pay, "hs_default_mode": mode,
				"credit_limits": [{"company": c.company, "credit_limit": 400000}]}).insert()
		party_contact("Customer", name, person, mobile, email, place, country, f"{place}, {country}")


def suppliers(c):
	for g in ["Goods Suppliers", "Logistics & Customs"]:
		get_or_insert({"doctype": "Supplier Group", "supplier_group_name": g, "parent_supplier_group": "All Supplier Groups"}, {"name": g})
	for name, grp, country, cur, terms, person, mobile, email in D.SUPPLIERS:
		if not frappe.db.exists("Supplier", name):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "supplier_group": grp, "country": country,
				"default_currency": cur, "payment_terms": terms}).insert()
		party_contact("Supplier", name, person, mobile, email, country, country, country)


def lead_source_field():
	"""ERPNext v15 uses Lead.source (Lead Source); newer versions use Lead.utm_source (UTM Source)."""
	meta = frappe.get_meta("Lead")
	if meta.has_field("utm_source"):
		return "utm_source", "UTM Source"
	return "source", "Lead Source"


def lead_sources_and_leads(c):
	field, src_doctype = lead_source_field()
	for s in D.LEAD_SOURCES:
		if not frappe.db.exists(src_doctype, s):
			if src_doctype == "Lead Source":
				frappe.get_doc({"doctype": "Lead Source", "source_name": s}).insert()
			else:
				frappe.get_doc({"doctype": "UTM Source", "description": s}).insert(set_name=s)
	for company, person, mobile, email, emirate, src, interest, value, close, owner, stage, fu, action in D.LEADS:
		if frappe.db.exists("Lead", {"company_name": company}):
			continue
		first, _, last = person.partition(" ")
		frappe.get_doc({"doctype": "Lead", "first_name": first, "last_name": last, "company_name": company, "email_id": email,
			"mobile_no": mobile, "city": emirate, "country": "United Arab Emirates", field: src,
			"lead_owner": user_email(owner) if frappe.db.exists("User", user_email(owner)) else "Administrator",
			"status": "Lost Quotation" if stage == "Lost" else "Open", "hs_pipeline_stage": stage, "hs_interested_in": interest,
			"hs_estimated_value": value, "hs_expected_close": c.d(close), "hs_next_follow_up": c.d(fu) if fu is not None else None,
			"hs_next_action": action, "hs_lost_reason": "Price — chose a cheaper offer" if stage == "Lost" else None}).insert()


def user_email(key):
	u = next(x for x in D.DEMO_USERS if x[0] == key)
	return f"{u[1].lower()}.{u[2].lower().replace(' ', '').replace(chr(39), '')}@{D.DEMO_EMAIL_DOMAIN}"


def demo_users(c):
	for key, first, last, roles in D.DEMO_USERS:
		email = user_email(key)
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first, "last_name": last, "send_welcome_email": 0,
				"user_type": "Website User" if roles == ["Driver"] else "System User",
				"roles": [{"role": r} for r in roles if frappe.db.exists("Role", r)]}).insert(ignore_permissions=True)
	# Leads created before the users existed get their owners now.
	for company, *_rest in D.LEADS:
		owner = _rest[8]
		frappe.db.set_value("Lead", {"company_name": company}, "lead_owner", user_email(owner))


# ------------------------------------------------------------------ transactions
def opening_account(c):
	"""The balance-sheet account opening stock is booked against (charts without “Temporary Opening” get one)."""
	acc = frappe.db.get_value("Account", {"company": c.company, "account_name": "Temporary Opening", "is_group": 0}) or frappe.db.get_value(
		"Account", {"company": c.company, "account_type": "Temporary", "is_group": 0, "root_type": ["in", ["Asset", "Liability"]]})
	if acc:
		return acc
	parent = frappe.db.get_value("Account", {"company": c.company, "account_type": "Temporary", "is_group": 1}) or frappe.db.get_value(
		"Account", {"company": c.company, "root_type": "Asset", "is_group": 1, "account_name": ["like", "%Current Assets%"]}) or frappe.db.get_value(
		"Account", {"company": c.company, "root_type": "Asset", "is_group": 1}, order_by="lft asc")
	a = frappe.get_doc({"doctype": "Account", "account_name": "Temporary Opening", "company": c.company, "parent_account": parent,
		"account_type": "Temporary", "root_type": frappe.db.get_value("Account", parent, "root_type"), "report_type": "Balance Sheet"})
	a.flags.ignore_root_company_validation = True
	return a.insert(ignore_permissions=True).name


def opening_stock(c):
	if frappe.db.exists("Stock Reconciliation", {"company": c.company, "purpose": "Opening Stock", "docstatus": 1}):
		return
	temp = opening_account(c)
	sr = frappe.get_doc({"doctype": "Stock Reconciliation", "company": c.company, "purpose": "Opening Stock", "expense_account": temp,
		"items": [{"item_code": code, "warehouse": c.wh(wh), "qty": q, "valuation_rate": cost} for code, _n, _a, _g, _u, _h, _o, _r, _s, cost, wh, q in D.ITEMS
			if not frappe.db.get_value("Item", code, "has_serial_no")]})
	backdate(sr, c.d(-150))
	sr.insert()
	sr.submit()


def opening_stock_serialised(c):
	"""Serialised items come in by stock entry, so ERPNext numbers each unit from the item's series."""
	codes = [x for x in D.ITEMS if frappe.db.get_value("Item", x[0], "has_serial_no")]
	if not codes or frappe.db.exists("Stock Entry", {"remarks": "Hipersign opening stock — serialised items", "docstatus": 1}):
		return
	temp = opening_account(c)
	se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": c.company,
		"remarks": "Hipersign opening stock — serialised items",
		"items": [{"item_code": code, "t_warehouse": c.wh(wh), "qty": q, "basic_rate": cost, "expense_account": temp, "allow_zero_valuation_rate": 0}
			for code, _n, _a, _g, _u, _h, _o, _r, _s, cost, wh, q in codes]})
	if se.meta.has_field("is_opening"):
		se.is_opening = "Yes"
	backdate(se, c.d(-150))
	se.insert()
	se.submit()
	_opening_reclass(c, se, temp)


def _opening_reclass(c, se, temp):
	"""Some ERPNext versions post a stock entry's receipt to Stock Adjustment whatever the row says: move it to the opening account."""
	adj = frappe.get_cached_value("Company", c.company, "stock_adjustment_account")
	if not adj or adj == temp:
		return
	amt = flt(frappe.db.sql("select sum(credit) - sum(debit) from `tabGL Entry` where voucher_no=%s and account=%s and is_cancelled=0", (se.name, adj))[0][0])
	if abs(amt) < 0.01:
		return
	je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": c.company, "posting_date": se.posting_date,
		"user_remark": f"Opening stock of serialised items ({se.name}) moved from Stock Adjustment to {temp}",
		"accounts": [{"account": adj, "debit_in_account_currency": amt if amt > 0 else 0, "credit_in_account_currency": -amt if amt < 0 else 0},
			{"account": temp, "credit_in_account_currency": amt if amt > 0 else 0, "debit_in_account_currency": -amt if amt < 0 else 0}]})
	je.flags.hs_system_entry = True
	je.insert()
	je.submit()


def make_po(c, supplier, lines, days_ago, incoterm=None, place=None, submit=True):
	cur = frappe.db.get_value("Supplier", supplier, "default_currency") or "AED"
	rate = 1 if cur == "AED" else D.FX[cur]
	po = frappe.get_doc({"doctype": "Purchase Order", "supplier": supplier, "company": c.company, "currency": cur, "conversion_rate": rate,
		"price_list_currency": "AED", "plc_conversion_rate": 1, "ignore_pricing_rule": 1,
		"schedule_date": c.d(-days_ago + 35), "set_warehouse": c.wh("Main Warehouse"),
		"items": [{"item_code": it, "qty": q, "rate": flt(r, 2), "schedule_date": c.d(-days_ago + 35), "warehouse": c.wh("Main Warehouse")} for it, q, r in lines]})
	if po.meta.has_field("incoterm") and incoterm and frappe.db.exists("Incoterm", incoterm):
		po.incoterm, po.named_place = incoterm, place
	if cur == "AED":
		po.taxes_and_charges = c.get("purchase_tax")
	backdate(po, c.d(-days_ago))
	po.insert()
	if submit:
		po.submit()
	return po


def make_shipment(c, po, status, days_ago, bl, boe=None, docs_ok=True, eta_in=0):
	shp = frappe.get_doc({"doctype": "Import Shipment", "company": c.company, "mode": "Sea", "bl_awb": bl, "vessel_flight": "MSC Aurora V.618",
		"forwarder": "Oceanic Freight Forwarders", "port_of_loading": "Yantian, Shenzhen" if po.currency != "EUR" else "Hamburg",
		"port_of_discharge": "Jebel Ali", "etd": c.d(-days_ago), "eta": c.d(eta_in), "status": "Booked",
		"purchase_orders": [{"purchase_order": po.name}]})
	shp.insert()
	for d in shp.documents:
		d.received = 1 if docs_ok or d.document_type != "Certificate of Origin" else 0
	shp.bill_of_entry = boe
	for typ, sup_, amt in [("Freight & Shipping", "Oceanic Freight Forwarders", 6800), ("Customs Duty", "Al Bahar Customs Clearing", round(po.base_grand_total * 0.05, 2)),
		("Insurance", "Emirates Cargo Insurance", 900), ("Clearing Charges", "Al Bahar Customs Clearing", 750), ("Handling", "Swift Port Handling", 480)]:
		shp.append("charges", {"charge_type": typ, "provider": sup_, "amount": amt, "date": c.d(-days_ago + 20)})
	shp.status = status
	from hipersign_trading.constants import IMPORT_STATUSES

	idx = IMPORT_STATUSES.index(status) if status in IMPORT_STATUSES else -1
	if idx >= IMPORT_STATUSES.index("Arrived at Port"):
		shp.arrived_on = c.d(eta_in)
	if idx >= IMPORT_STATUSES.index("Cleared"):
		shp.cleared_on = c.d(eta_in + 1)
	shp.save()
	return shp


def purchasing_and_imports(c):
	if frappe.db.exists("Import Shipment", {"bl_awb": "MSKU-YTN-2209415"}):
		return
	# 1. Received import (used later for the Kenya re-export): cameras from China, cleared, received, landed cost applied
	po1 = make_po(c, "Global Supplies Co. Ltd", [("ITM-003", 600, 210 * 0.96 / D.FX["USD"]), ("ITM-001", 300, 820 * 0.96 / D.FX["USD"])], 80, "FOB", "Yantian")
	s1 = make_shipment(c, po1, "Cleared", 75, "MSKU-YTN-2209415", boe="101-2026-0418331", eta_in=-40)
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
	pr = make_purchase_receipt(po1.name)
	backdate(pr, c.d(-38))
	pr.hs_import_shipment = s1.name
	pr.insert()
	pr.submit()
	lcv = frappe.get_doc("Landed Cost Voucher", frappe.get_doc("Import Shipment", s1.name).make_landed_cost_voucher())
	lcv.posting_date = c.d(-37)
	lcv.save()
	lcv.submit()
	# 2. At customs — the golden-path shipment (BOE pending)
	po2 = make_po(c, "Global Supplies Co. Ltd", [("ITM-001", 200, 200)], 40, "FOB", "Yantian")
	make_shipment(c, po2, "Under Customs Clearance", 32, "MSKU-YTN-2210377", boe=None, docs_ok=False, eta_in=-2)
	# 3. In transit from Germany
	po3 = make_po(c, "EuroSafe Systems GmbH", [("ITM-005", 40, 1450 * 0.96 / D.FX["EUR"]), ("ITM-013", 4, 4200 * 0.96 / D.FX["EUR"])], 20, "FCA", "Frankfurt")
	make_shipment(c, po3, "In Transit", 12, "176-55120934", eta_in=6)
	# 4. Local supplier, received
	po4 = make_po(c, "Gulf Electrical Trading LLC", [("ITM-008", 500, 46 * 0.96), ("ITM-009", 1500, 6.5 * 0.96)], 25)
	pr4 = make_purchase_receipt(po4.name)
	backdate(pr4, c.d(-18))
	pr4.insert()
	pr4.submit()
	# 5. Waiting for approval (left as draft; state set at the end)
	po5 = make_po(c, "Shenzhen Brightway Electronics", [("ITM-006", 2000, 58 * 0.96 / D.FX["CNY"])], 1, "FOB", "Yantian", submit=False)
	c.pending_po = po5.name


def so_lines(c, customer, lines):
	grp = frappe.db.get_value("Customer", customer, "customer_group")
	disc = D.GROUP_DISCOUNT.get(grp, 0)
	cur = frappe.db.get_value("Customer", customer, "default_currency") or "AED"
	fx = 1 if cur == "AED" else D.FX[cur]
	out = []
	for it, q, *extra in lines:
		pl = flt(frappe.db.get_value("Item Price", {"item_code": it, "price_list": c.selling_pl}, "price_list_rate")) / fx
		d = extra[0] if extra else disc
		out.append({"item_code": it, "qty": q, "price_list_rate": pl, "discount_percentage": d, "rate": flt(pl * (1 - d / 100), 2),
			"delivery_date": c.d(5)})
	return out, cur, fx


def make_so(c, customer, lines, days_ago, po_no, submit=True, deliver=None, invoice=None, pay=None):
	items_, cur, fx = so_lines(c, customer, lines)
	so = frappe.get_doc({"doctype": "Sales Order", "customer": customer, "company": c.company, "po_no": po_no, "currency": cur,
		"conversion_rate": fx, "selling_price_list": c.selling_pl, "price_list_currency": "AED", "plc_conversion_rate": 1,
		"ignore_pricing_rule": 1, "delivery_date": c.d(-days_ago + 5), "set_warehouse": None, "items": items_})
	for i in so.items:
		i.delivery_date = c.d(-days_ago + 5)
	backdate(so, c.d(-days_ago))
	so.insert()
	if not submit:
		return so
	so.submit()
	if deliver is not None:
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		dn = make_delivery_note(so.name)
		backdate(dn, c.d(-deliver))
		dn.insert()
		dn.submit()
		if invoice is not None:
			from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
			si = make_sales_invoice(dn.name)
			backdate(si, c.d(-invoice))
			si.set("payment_schedule", [])
			si.insert()
			si.submit()
			if pay:
				from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
				pe = get_payment_entry("Sales Invoice", si.name)
				pe.posting_date = c.d(-pay[0])
				pe.reference_no, pe.reference_date = f"TT-{si.name[-4:]}", c.d(-pay[0])
				amt = flt(min(flt(si.outstanding_amount), flt(si.grand_total) * pay[1]), 2)
				pe.paid_amount = pe.received_amount = amt
				pe.references[0].allocated_amount = amt
				pe.insert()
				pe.submit()
	return so


def quotations(c):
	if frappe.db.exists("Quotation", {"hs_subject": "Access control — Star Vision showroom"}):
		return
	for party, to, lines, subj, ago in [
		("Star Vision", "Customer", [("ITM-011", 20), ("ITM-003", 40), ("SRV-001", 20)], "Access control — Star Vision showroom", 1),
		("Dubai Municipality Projects", "Customer", [("ITM-013", 4), ("ITM-001", 24), ("SRV-004", 1)], "Video wall — operations room", 9),
	]:
		items_, cur, fx = so_lines(c, party, lines)
		q = frappe.get_doc({"doctype": "Quotation", "quotation_to": to, "party_name": party, "company": c.company, "currency": cur,
			"conversion_rate": fx, "selling_price_list": c.selling_pl, "price_list_currency": "AED", "plc_conversion_rate": 1,
			"ignore_pricing_rule": 1, "valid_till": c.d(-ago + 14), "hs_subject": subj, "items": items_,
			"taxes_and_charges": c.get("local_tax")})
		backdate(q, c.d(-ago))
		q.insert()
		q.submit()
	lead = frappe.db.get_value("Lead", {"company_name": "Palm Crest Facilities"})
	if lead:
		lines = []
		for it, qty in (("ITM-011", 180), ("SRV-001", 60)):
			rate = flt(frappe.db.get_value("Item Price", {"item_code": it, "price_list": c.selling_pl}, "price_list_rate"))
			lines.append({"item_code": it, "qty": qty, "rate": rate, "price_list_rate": rate})
		q = frappe.get_doc({"doctype": "Quotation", "quotation_to": "Lead", "party_name": lead, "company": c.company, "currency": "AED", "conversion_rate": 1,
			"selling_price_list": c.selling_pl, "price_list_currency": "AED", "plc_conversion_rate": 1, "ignore_pricing_rule": 1,
			"valid_till": c.d(12), "hs_subject": "Access control — 3 residential towers", "items": lines,
			"taxes_and_charges": c.get("local_tax") or frappe.db.get_single_value("Hipersign Settings", "local_tax_template")})
		backdate(q, c.d(-2))
		q.set_missing_values()
		q.set("taxes", [])
		if q.taxes_and_charges:
			q.append_taxes_from_master()
		q.insert()


def sales_orders(c):
	if frappe.db.exists("Sales Order", {"po_no": "ANL/PO/7719"}):
		return
	make_so(c, "Al Noor LLC", [("ITM-003", 200), ("ITM-011", 40), ("ITM-012", 40)], 38, "ANL/PO/7719", deliver=33, invoice=33, pay=(15, 0.5))
	make_so(c, "Gulf Projects", [("ITM-005", 30), ("ITM-006", 400)], 53, "GP-2026-311", deliver=49, invoice=49, pay=(12, 0.3))
	make_so(c, "Gulf Trading LLC", [("ITM-001", 150), ("ITM-004", 40)], 42, "GT/8812", deliver=40, invoice=40, pay=(8, 1))
	make_so(c, "Horizon Trading", [("ITM-008", 900), ("ITM-009", 2500), ("ITM-010", 1200)], 25, "HT-5520", deliver=22, invoice=22)
	make_so(c, "Future Build", [("ITM-001", 60), ("ITM-010", 400), ("SRV-003", 2)], 4, "FB/PO/0932")
	make_so(c, "Star Vision", [("ITM-002", 600), ("ITM-006", 300)], 14, "SV-2241", deliver=11)
	c.pending_sm = make_so(c, "Gulf Projects", [("ITM-007", 100, 15)], 2, "GP-2026-344", submit=False).name
	c.pending_fin = make_so(c, "Elite Systems", [("ITM-004", 80), ("ITM-005", 20)], 3, "ES-0419", submit=False).name


def exports(c):
	if frappe.db.exists("Export Shipment", {"bl_awb_cmr": "MSKU-JEA-7741290"}):
		return
	def export_so(customer, lines, ago, po):
		so = make_so(c, customer, lines, ago, po, submit=False)
		cust = frappe.get_doc("Customer", customer)
		if so.meta.has_field("incoterm") and cust.hs_default_incoterm:
			so.incoterm, so.named_place = cust.hs_default_incoterm, cust.hs_default_named_place
		so.save()
		so.submit()
		return so
	shp_import = frappe.db.get_value("Import Shipment", {"bl_awb": "MSKU-YTN-2209415"})
	so = export_so("Nairobi Secure Tech Ltd", [("ITM-001", 40), ("ITM-003", 80)], 15, "NST-LC-0457")
	e = frappe.get_doc({"doctype": "Export Shipment", "company": c.company, "sales_order": so.name, "mode": "Sea",
		"port_of_loading": "Jebel Ali Port", "destination": "Mombasa, Kenya", "forwarder": "Oceanic Freight Forwarders",
		"etd": c.d(-6), "eta": c.d(10), "re_export_of": shp_import}).insert()
	dn = frappe.get_doc("Delivery Note", e.make_delivery_note())
	backdate(dn, c.d(-11))
	dn.save()
	dn.submit()
	e.reload()
	si = frappe.get_doc("Sales Invoice", e.make_sales_invoice())
	backdate(si, c.d(-11))
	si.set("payment_schedule", [])
	si.save()
	si.submit()
	e.reload()
	for typ, sup_, amt in [("Freight & Shipping", "Oceanic Freight Forwarders", 6200), ("Insurance", "Emirates Cargo Insurance", 900),
		("Clearing Charges", "Al Bahar Customs Clearing", 750), ("Handling", "Swift Port Handling", 480)]:
		e.append("charges", {"charge_type": typ, "provider": sup_, "amount": amt, "date": c.d(-8)})
	e.declaration_no, e.coo_no, e.bl_awb_cmr = "204-261011-31877", "DCCI-88133", "MSKU-JEA-7741290"
	for d in e.documents:
		if d.document_type == "Insurance Certificate":
			d.received = 1
	e.status = "Shipped"
	e.shipped_on = c.d(-6)
	e.save()
	so2 = export_so("Muscat Integrated Systems LLC", [("ITM-006", 300), ("ITM-002", 200)], 1, "MIS/PO/2260")
	frappe.get_doc({"doctype": "Export Shipment", "company": c.company, "sales_order": so2.name, "mode": "Land",
		"port_of_loading": "Hatta border (Oman)", "destination": "Muscat, Oman", "forwarder": "Oceanic Freight Forwarders",
		"etd": c.d(3), "eta": c.d(5)}).insert()
	export_so("Riyadh Smart Buildings Co.", [("ITM-005", 6), ("ITM-007", 20)], 5, "RSB-PO-7781")


# ------------------------------------------------------------------ v1.1: returns, cheques, people, delivery, warranty, portal
def invoice_of(customer, po_no):
	so = frappe.db.get_value("Sales Order", {"customer": customer, "po_no": po_no, "docstatus": 1})
	if not so:
		return None
	return frappe.db.get_value("Sales Invoice Item", {"sales_order": so, "docstatus": 1}, "parent")


def returns_and_credit_notes(c):
	"""One approved credit note (damaged speakers into the Rejected Warehouse) and one waiting for the Sales Manager."""
	if frappe.db.exists("Sales Invoice", {"is_return": 1, "docstatus": ["<", 2]}):
		return
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	for customer, po_no, item, qty, reason, wh, submit in [
		("Gulf Projects", "GP-2026-311", "ITM-006", 20, "Damaged in transit", c.wh("Rejected Warehouse"), True),
		("Al Noor LLC", "ANL/PO/7719", "ITM-012", 5, "Wrong item supplied", None, False),
	]:
		si = invoice_of(customer, po_no)
		if not si:
			continue
		cn = make_return_doc("Sales Invoice", si)
		cn.items = [r for r in cn.items if r.item_code == item][:1]
		if not cn.items:
			continue
		cn.items[0].qty = -qty
		cn.hs_return_reason = reason
		backdate(cn, c.d(-14 if submit else -1))
		cn.set("payment_schedule", [])
		cn.insert()
		if not submit:
			continue
		cn.submit()
		# goods come back on a delivery-note return (stock), the credit note settles the money
		dn = frappe.db.get_value("Sales Invoice Item", {"parent": si, "item_code": item}, "delivery_note")
		if dn:
			ret = make_return_doc("Delivery Note", dn)
			ret.items = [r for r in ret.items if r.item_code == item][:1]
			ret.items[0].qty = -qty
			if wh:
				ret.items[0].warehouse = wh
			backdate(ret, c.d(-14))
			ret.insert()
			ret.submit()


def post_dated_cheques(c):
	bank = c.get("bank_gl") or frappe.db.get_single_value("Hipersign Settings", "cheque_bank_account")
	rows = [
		("Horizon Trading", "HT-5520", "000418", "Emirates NBD", 0.5, -2, "deposit"),
		("Horizon Trading", "HT-5520", "000419", "Emirates NBD", 0.5, 40, None),
		("Al Noor LLC", "ANL/PO/7719", "102774", "ADCB", 0.6, 26, None),
		("Gulf Projects", "GP-2026-311", "553019", "Mashreq", 0.4, -1, "deposited"),
	]
	for customer, po_no, no, drawn, frac, days_, action in rows:
		if frappe.db.exists("Post Dated Cheque", {"cheque_no": no, "party": customer, "status": ["!=", "Cancelled"]}):
			continue
		si = invoice_of(customer, po_no)
		if not si:
			continue
		out = flt(frappe.db.get_value("Sales Invoice", si, "outstanding_amount"))
		open_ = {"reference_name": si, "status": ["in", ["In Hand", "Deposited"]]}
		held = sum(flt(x) for x in frappe.get_all("Post Dated Cheque", filters={**open_, "posted": 0}, pluck="amount"))
		posted = sum(flt(x) for x in frappe.get_all("Post Dated Cheque", filters={**open_, "posted": 1}, pluck="amount"))
		amt = min(round((out + posted) * frac / 100) * 100, out - held)
		if amt <= 0:
			continue
		p = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Received", "party_type": "Customer", "party": customer, "company": c.company,
			"cheque_no": no, "cheque_date": c.d(days_), "drawn_on": drawn, "amount": amt, "bank_account": bank, "received_on": c.d(-20),
			"reference_doctype": "Sales Invoice", "reference_name": si}).insert()
		if action == "deposited":
			p.deposit()
	# a cheque issued to a local supplier against its invoice
	pr = frappe.db.get_value("Purchase Receipt", {"supplier": "Gulf Electrical Trading LLC", "docstatus": 1})
	if pr and not frappe.db.exists("Purchase Invoice", {"supplier": "Gulf Electrical Trading LLC", "bill_no": "GET/INV/20419", "docstatus": ["<", 2]}):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(pr)
		backdate(pi, c.d(-17))
		pi.bill_no, pi.bill_date = "GET/INV/20419", c.d(-18)
		pi.set("payment_schedule", [])
		pi.insert()
		pi.submit()
		frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Issued", "party_type": "Supplier", "party": "Gulf Electrical Trading LLC",
			"company": c.company, "cheque_no": "700112", "cheque_date": c.d(16), "amount": flt(pi.grand_total), "bank_account": bank,
			"received_on": c.d(-10), "reference_doctype": "Purchase Invoice", "reference_name": pi.name}).insert()


def people_and_documents(c):
	if frappe.db.exists("Employee", {"first_name": "Priya", "last_name": "Menon"}):
		return
	for first, last, gender, desig, dept, joined, pp, visa, eid, lc in D.EMPLOYEES:
		get_or_insert({"doctype": "Designation", "designation_name": desig}, {"name": desig})
		dep = frappe.db.get_value("Department", {"department_name": dept, "company": c.company}) or frappe.get_doc(
			{"doctype": "Department", "department_name": dept, "company": c.company}).insert().name
		uid = None
		for key, f, l, _r in D.DEMO_USERS:
			if f == first and l == last and key != "driver":
				uid = user_email(key)
		e = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last, "gender": gender, "company": c.company,
			"date_of_birth": add_days(today(), -365 * 32), "date_of_joining": c.d(-joined), "designation": desig, "department": dep,
			"status": "Active", "passport_number": f"P{zlib.crc32((first + last).encode()) % 10**7:07d}", "valid_upto": c.d(pp),
			"hs_emirates_id": f"784-19{zlib.crc32(last.encode()) % 90 + 10}-{zlib.crc32(first.encode()) % 10**7:07d}-1", "hs_emirates_id_expiry": c.d(eid),
			"hs_visa_expiry": c.d(visa), "hs_labour_card_no": f"{zlib.crc32((first + 'lc').encode()) * 10**4 % 10**14:014d}", "hs_labour_card_expiry": c.d(lc),
			"hs_wps_routing_code": "302620122", "iban": "AE070331234567890123456"})
		if uid and frappe.db.exists("User", uid):
			e.user_id = uid
		e.insert()


def drivers_and_deliveries(c):
	for name, mobile, vehicle, key in D.DRIVERS:
		if not frappe.db.exists("Driver", {"full_name": name}):
			frappe.get_doc({"doctype": "Driver", "full_name": name, "cell_number": mobile, "status": "Active",
				"hs_user": user_email(key) if key and frappe.db.exists("User", user_email(key)) else None}).insert()
	rashid = frappe.db.get_value("Driver", {"full_name": "Rashid Khan"})
	for dn in frappe.get_all("Delivery Note", filters={"docstatus": 1, "is_return": 0}, fields=["name", "customer", "contact_display", "posting_date"]):
		inv = frappe.db.get_value("Sales Invoice Item", {"delivery_note": dn.name, "docstatus": 1}, "parent")
		if inv:
			frappe.db.set_value("Delivery Note", dn.name, {"hs_delivery_status": "Delivered", "hs_driver": rashid,
				"hs_received_by": dn.contact_display or "Site supervisor", "hs_pod_time": f"{dn.posting_date} 14:20:00"}, update_modified=False)
		else:
			frappe.db.set_value("Delivery Note", dn.name, {"hs_delivery_status": "Out for Delivery", "hs_driver": rashid}, update_modified=False)


def warranty_claims(c):
	if not serials_on() or frappe.db.exists("Warranty Claim", {"complaint": ["like", "Reader does not power up%"]}):
		return
	from hipersign_trading.api.serials import customer_units

	for customer, item, complaint, status in [
		("Al Noor LLC", "ITM-011", "Reader does not power up after installation", "Work In Progress"),
		("Gulf Trading LLC", "ITM-004", "Ports 13–24 not passing PoE", "Open"),
	]:
		units = [u for u in customer_units(customer) if u.item_code == item]
		if not units:
			continue
		frappe.get_doc({"doctype": "Warranty Claim", "status": status, "complaint_date": c.d(-3), "customer": customer, "serial_no": units[-1].serial_no,
			"item_code": item, "complaint": complaint, "company": c.company,
			"hs_supplier_rma": "RMA-ACR-7731" if status == "Work In Progress" else None}).insert()


def portal_user(c):
	"""Gulf Trading LLC can log in to the customer portal: orders, invoices, statement, warranty."""
	email = f"portal.gulftrading@{D.DEMO_EMAIL_DOMAIN}"
	if frappe.db.exists("User", email):
		return
	frappe.get_doc({"doctype": "User", "email": email, "first_name": "Yousef", "last_name": "Karim (portal)", "send_welcome_email": 0,
		"user_type": "Website User", "roles": [{"role": "Customer"}]}).insert(ignore_permissions=True)
	frappe.get_doc({"doctype": "Contact", "first_name": "Yousef", "last_name": "Karim (portal)", "user": email,
		"email_ids": [{"email_id": email, "is_primary": 1}], "links": [{"link_doctype": "Customer", "link_name": "Gulf Trading LLC"}]}).insert(ignore_permissions=True)


def home_workspaces(c):
	if not frappe.get_meta("User").has_field("default_workspace"):
		return
	for key, ws in D.DEFAULT_WORKSPACE.items():
		email = user_email(key)
		if frappe.db.exists("User", email) and frappe.db.exists("Workspace", ws):
			frappe.db.set_value("User", email, "default_workspace", ws)


def set_pending_states(c):
	"""Drafts that are waiting for approval show the right workflow state."""
	for doctype, name, state in [("Purchase Order", c.get("pending_po"), "Pending Purchase Manager"),
		("Sales Order", c.get("pending_sm"), "Pending Sales Manager"), ("Sales Order", c.get("pending_fin"), "Pending Finance Manager")]:
		if name and frappe.get_meta(doctype).has_field("workflow_state"):
			frappe.db.set_value(doctype, name, "workflow_state", state)
	for doctype in ["Purchase Order", "Sales Order", "Payment Entry", "Stock Reconciliation"]:
		if frappe.get_meta(doctype).has_field("workflow_state"):
			frappe.db.sql(f"update `tab{doctype}` set workflow_state=%s where docstatus=1 and ifnull(workflow_state,'')=''",
				"Paid" if doctype == "Payment Entry" else "Approved")
