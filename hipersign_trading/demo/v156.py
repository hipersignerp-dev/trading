"""v1.5.6 demo data: what the end-to-end run and the audit found empty or wrong on the old site.

- UAE VAT Settings, so the VAT 201 return is not zero (VAT-01)
- the import-charge bills behind the landed cost, so operating expenses are not negative (HOM-01 / DSH-01)
- VAT on the inter-company purchase invoice and the link back to the sales invoice (GRP-03)
- sales and purchase history from January, so the monthly chart covers the year; monthly rent and utilities
- a bank statement to reconcile (BNK-01 / BNK-02)
- salary structures and last month's payroll (WPS-01), leave, attendance, expense claims, employee advances
- fixed assets with depreciation and a vehicle due for service
- vehicles and two delivery trips; a credit limit request
- more conversations, with @mentions and incoming emails
- the view-only demo account (Demo Viewer)

Every step skips what is already there, so the loader can be run again.
"""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

VIEWER = "viewer@demo.hipersignerp.com"


def _acc(c, name):
	full = f"{name} - {c.abbr}"
	return full if frappe.db.exists("Account", full) else None


def _cc(c):
	return frappe.get_cached_value("Company", c.company, "cost_center")


# ---------------------------------------------------------------- VAT
def v156_vat_settings(c):
	if frappe.db.exists("UAE VAT Settings", c.company):
		return
	vat = _acc(c, "VAT 5%") or frappe.db.get_value("Account", {"company": c.company, "account_type": "Tax", "account_name": ["like", "%VAT 5%"]})
	if not vat:
		return
	frappe.get_doc({"doctype": "UAE VAT Settings", "company": c.company, "uae_vat_accounts": [{"account": vat}]}).insert()


# ---------------------------------------------------------------- import charges
def _charge_item():
	code = "IMP-CHARGES"
	if not frappe.db.exists("Item", code):
		frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": "Import charges (freight, duty, clearing)", "item_group": "Services"
			if frappe.db.exists("Item Group", "Services") else frappe.db.get_value("Item Group", {"is_group": 0}), "stock_uom": "Nos",
			"is_stock_item": 0, "is_sales_item": 0, "is_purchase_item": 1}).insert()
	return code


def v156_import_charge_bills(c):
	"""One supplier bill per provider for each shipment whose landed cost is applied, booked to the same
	"Expenses Included In Valuation" account the landed cost voucher credits — the two cancel out."""
	eiiv = frappe.get_cached_value("Company", c.company, "expenses_included_in_valuation") or _acc(c, "Expenses Included In Valuation")
	if not eiiv:
		return
	item = _charge_item()
	for shp in frappe.get_all("Import Shipment", filters={"company": c.company, "landed_cost_voucher": ["is", "set"]}, pluck="name"):
		doc = frappe.get_doc("Import Shipment", shp)
		lcv_date = frappe.db.get_value("Landed Cost Voucher", doc.landed_cost_voucher, "posting_date") or today()
		by_provider = {}
		for ch in doc.charges:
			if ch.purchase_invoice or not ch.provider:
				continue
			by_provider.setdefault(ch.provider, []).append(ch)
		for provider, rows in by_provider.items():
			pi = frappe.get_doc({"doctype": "Purchase Invoice", "supplier": provider, "company": c.company, "posting_date": lcv_date,
				"set_posting_time": 1, "bill_no": f"{provider[:3].upper()}-{shp[-4:]}", "bill_date": lcv_date, "due_date": add_days(lcv_date, 30),
				"remarks": f"Import charges for {shp}",
				"items": [{"item_code": item, "item_name": f"{r.charge_type} — {shp}", "qty": 1, "rate": flt(r.amount), "expense_account": eiiv,
					"cost_center": _cc(c)} for r in rows]})
			pi.set_missing_values()
			pi.set("taxes", [])
			pi.insert()
			pi.submit()
			for r in rows:
				frappe.db.set_value("Shipment Charge", r.name, "purchase_invoice", pi.name, update_modified=False)


# ---------------------------------------------------------------- inter-company
def v156_intercompany(c):
	"""The FZE's purchase invoice carries the 5% VAT the LLC charged, and the LLC's sales invoice links back to it."""
	from hipersign_trading.demo import data as D

	fze = D.GROUP["companies"][0][0]
	si_name = frappe.db.get_value("Sales Invoice", {"customer": fze, "company": c.company, "docstatus": 1})
	if not si_name:
		return
	si = frappe.get_doc("Sales Invoice", si_name)
	pi_name = frappe.db.get_value("Purchase Invoice", {"inter_company_invoice_reference": si.name, "docstatus": 1}) or frappe.db.get_value(
		"Purchase Invoice", {"bill_no": si.name, "docstatus": 1})
	if not pi_name:
		return
	if not si.get("inter_company_invoice_reference"):
		frappe.db.set_value("Sales Invoice", si.name, "inter_company_invoice_reference", pi_name, update_modified=False)
	pi = frappe.get_doc("Purchase Invoice", pi_name)
	if flt(pi.total_taxes_and_charges) or not flt(si.total_taxes_and_charges):
		return
	# replace it with one that has the VAT (cancel, amend)
	abbr = frappe.get_cached_value("Company", pi.company, "abbr")
	vat = frappe.db.get_value("Account", {"company": pi.company, "account_type": "Tax", "is_group": 0, "account_name": ["like", "%VAT%"]})
	if not vat:
		parent = frappe.db.get_value("Account", {"company": pi.company, "is_group": 1, "account_name": "Duties and Taxes"}) or frappe.db.get_value(
			"Account", {"company": pi.company, "is_group": 1, "root_type": "Liability"})
		vat = frappe.get_doc({"doctype": "Account", "account_name": "Input VAT 5%", "company": pi.company, "parent_account": parent,
			"account_type": "Tax", "tax_rate": 5, "root_type": "Liability"}).insert().name
	pi.cancel()
	new = frappe.copy_doc(pi)
	new.amended_from = pi.name
	new.set("taxes", [{"charge_type": "On Net Total", "account_head": vat, "description": "VAT 5%", "rate": 5,
		"cost_center": frappe.get_cached_value("Company", pi.company, "cost_center"), "category": "Total", "add_deduct_tax": "Add"}])
	new.posting_date, new.set_posting_time = pi.posting_date, 1
	new.insert()
	new.submit()
	frappe.db.set_value("Sales Invoice", si.name, "inter_company_invoice_reference", new.name, update_modified=False)
	_ = abbr


# ---------------------------------------------------------------- history from January
SERVICE_SALES = [("SRV-001", 32), ("SRV-002", 2), ("SRV-004", 9), ("SRV-005", 60), ("SRV-006", 6), ("SRV-003", 24)]
SERVICE_RATE = {"SRV-001": 450, "SRV-002": 6500, "SRV-003": 250, "SRV-004": 750, "SRV-005": 180, "SRV-006": 600}


def v156_history(c):
	"""Service invoices and supplier bills for each month before the demo's trading history, plus monthly rent and utilities."""
	if frappe.db.exists("Sales Invoice", {"company": c.company, "remarks": ["like", "History %"]}):
		return
	first_trade = frappe.db.sql("select min(posting_date) from `tabSales Invoice` where company=%s and docstatus=1", c.company)[0][0] or getdate(today())
	start = getdate(f"{getdate(today()).year}-01-01")
	customers = [x for x in frappe.get_all("Customer", filters={"is_internal_customer": 0, "disabled": 0, "hs_market": "Local"}, pluck="name")][:6]
	suppliers = [s for s in ("Swift Port Handling", "Oceanic Freight Forwarders", "Al Bahar Customs Clearing") if frappe.db.exists("Supplier", s)]
	item = _charge_item()
	expense = _acc(c, "Others - Office Various Expenses") or frappe.get_cached_value("Company", c.company, "default_expense_account")
	tax = frappe.db.get_single_value("Hipersign Settings", "local_tax_template")
	m = start
	k = 0
	while m < get_first_day(first_trade) and customers:
		for j in range(3 + (k % 3)):
			cust = customers[(k + j) % len(customers)]
			code, qty = SERVICE_SALES[(k + j) % len(SERVICE_SALES)]
			if not frappe.db.exists("Item", code):
				continue
			d = add_days(m, 4 + j * 7)
			si = frappe.get_doc({"doctype": "Sales Invoice", "customer": cust, "company": c.company, "posting_date": d, "set_posting_time": 1,
				"due_date": add_days(d, 30), "remarks": f"History {m.strftime('%b %Y')}", "taxes_and_charges": tax,
				"items": [{"item_code": code, "qty": qty + (k % 4), "rate": SERVICE_RATE[code], "price_list_rate": SERVICE_RATE[code]}]})
			si.set_missing_values()
			si.set("taxes", [])
			if tax:
				si.append_taxes_from_master()
			si.insert()
			si.submit()
			_pay(c, si, add_days(d, 25))
		for j, sup in enumerate(suppliers):
			d = add_days(m, 10 + j * 5)
			pi = frappe.get_doc({"doctype": "Purchase Invoice", "supplier": sup, "company": c.company, "posting_date": d, "set_posting_time": 1,
				"bill_no": f"H-{m.strftime('%y%m')}-{j}", "bill_date": d, "due_date": add_days(d, 30), "remarks": f"History {m.strftime('%b %Y')}",
				"items": [{"item_code": item, "item_name": "Logistics and handling services", "qty": 1, "rate": 2200 + 450 * ((k + j) % 4),
					"expense_account": expense, "cost_center": _cc(c)}]})
			pi.set_missing_values()
			pi.set("taxes", [])
			pi.insert()
			pi.submit()
		k += 1
		m = add_months(m, 1)
	_opening_capital(c, start)
	_monthly_overheads(c, start)


def _pay(c, si, date):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if getdate(date) > getdate(today()):
		return
	if flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount")) <= 0:
		return  # settled already (e.g. an advance applied automatically)
	bank = frappe.get_cached_value("Company", c.company, "default_bank_account") or _acc(c, "Emirates NBD Current")
	pe = get_payment_entry("Sales Invoice", si.name)
	pe.posting_date = date
	pe.paid_to = pe.paid_to or bank
	pe.paid_amount = pe.paid_amount or flt(si.outstanding_amount)
	pe.received_amount = pe.received_amount or pe.paid_amount
	pe.reference_no, pe.reference_date = f"TT-{si.name[-5:]}", date
	pe.insert()
	pe.submit()


def _opening_capital(c, start):
	"""The bank balance the company brought into the year (the prototype's opening balances at go-live)."""
	bank = frappe.get_cached_value("Company", c.company, "default_bank_account") or _acc(c, "Emirates NBD Current")
	equity = (_acc(c, "Share Capital") or _acc(c, "Capital Stock") or _acc(c, "Owner's Equity") or frappe.db.get_value("Account",
		{"company": c.company, "root_type": "Equity", "is_group": 0, "account_type": ["not in", ["Temporary"]], "account_name": ["not like", "%Retained%"]}))
	if not bank or not equity or frappe.db.exists("Journal Entry", {"company": c.company, "cheque_no": "OPEN-CAP"}):
		return
	je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Opening Entry", "is_opening": "Yes", "company": c.company, "posting_date": start,
		"cheque_no": "OPEN-CAP", "cheque_date": start, "user_remark": "Opening bank balance brought forward",
		"accounts": [{"account": bank, "debit_in_account_currency": 1650000}, {"account": equity, "credit_in_account_currency": 1650000}]})
	je.flags.hs_system_entry = True
	je.insert()
	je.submit()


def _monthly_overheads(c, start):
	"""Rent and utilities each month to date, paid from the bank — the prototype's operating expenses."""
	bank = frappe.get_cached_value("Company", c.company, "default_bank_account") or _acc(c, "Emirates NBD Current")
	rows = [(_acc(c, "Office Rent"), 4500), (_acc(c, "Warehouse Rent"), 6000), (_acc(c, "Water & Electricity"), 1250), (_acc(c, "Telephone"), 420)]
	rows = [r for r in rows if r[0]]
	if not bank or not rows:
		return
	m = getdate(start)
	while get_last_day(m) <= getdate(today()) or m.month == getdate(today()).month and m.year == getdate(today()).year:
		d = min(add_days(get_first_day(m), 2), getdate(today()))
		je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Bank Entry", "company": c.company, "posting_date": d,
			"cheque_no": f"OH-{m.strftime('%y%m')}", "cheque_date": d, "user_remark": f"Rent and utilities — {m.strftime('%B %Y')}",
			"accounts": [{"account": a, "debit_in_account_currency": amt, "cost_center": _cc(c)} for a, amt in rows]
				+ [{"account": bank, "credit_in_account_currency": sum(a for _x, a in rows)}]})
		je.flags.hs_system_entry = True
		je.insert()
		je.submit()
		if m.month == getdate(today()).month and m.year == getdate(today()).year:
			break
		m = add_months(m, 1)


# ---------------------------------------------------------------- bank statement
def v156_bank_statement(c):
	"""An Emirates NBD statement for the last 45 days: the receipts, payments and cheques in the books, plus a bank charge,
	a profit credit and one transfer nobody has identified — the prototype's reconciliation tab."""
	ba = frappe.db.get_value("Bank Account", {"company": c.company, "account": _acc(c, "Emirates NBD Current")}) or frappe.db.get_value(
		"Bank Account", {"company": c.company, "is_company_account": 1})
	if not ba or frappe.db.exists("Bank Transaction", {"bank_account": ba}):
		return
	gl_account = frappe.db.get_value("Bank Account", ba, "account")
	since = add_days(today(), -45)
	lines = []
	for pe in frappe.get_all("Payment Entry", filters={"company": c.company, "docstatus": 1, "posting_date": [">=", since],
		"paid_to": gl_account}, fields=["name", "posting_date", "paid_amount", "party_name", "reference_no"]):
		lines.append((add_days(pe.posting_date, 1), f"INWARD TT {pe.party_name or ''} {pe.reference_no or ''}".strip(), flt(pe.paid_amount), 0, pe.reference_no or pe.name))
	for pe in frappe.get_all("Payment Entry", filters={"company": c.company, "docstatus": 1, "posting_date": [">=", since],
		"paid_from": gl_account}, fields=["name", "posting_date", "paid_amount", "party_name", "reference_no"]):
		lines.append((add_days(pe.posting_date, 1), f"OUTWARD TT {pe.party_name or ''}".strip(), 0, flt(pe.paid_amount), pe.reference_no or pe.name))
	for je in frappe.db.sql("""select je.name, je.posting_date, je.cheque_no, jea.debit_in_account_currency dr, jea.credit_in_account_currency cr
		from `tabJournal Entry` je join `tabJournal Entry Account` jea on jea.parent = je.name
		where je.company=%s and je.docstatus=1 and je.posting_date >= %s and jea.account=%s""", (c.company, since, gl_account), as_dict=True):
		lines.append((je.posting_date, f"{'CHQ DEP' if je.dr else 'CHQ PAID'} {je.cheque_no or je.name}", flt(je.dr), flt(je.cr), je.cheque_no or je.name))
	lines.sort(key=lambda x: getdate(x[0]))
	lines = lines[-34:]
	lines += [(add_days(today(), -6), "SERVICE CHARGES — TT FEES OCT", 0, 157.5, "BC-1026"),
		(add_days(today(), -3), "PROFIT CREDIT — CALL ACCOUNT", 412.35, 0, "PC-1026"),
		(add_days(today(), -2), "INWARD TT REF 77Q3-UNIDENTIFIED", 18375.0, 0, "77Q3"),
		(add_days(today(), -1), "SERVICE CHARGES — CHQ RETURN FEE", 0, 52.5, "BC-1027")]
	for d, desc, dep, wd, ref in lines:
		if getdate(d) > getdate(today()):
			continue
		bt = frappe.get_doc({"doctype": "Bank Transaction", "date": d, "bank_account": ba, "company": c.company, "description": desc,
			"deposit": dep, "withdrawal": wd, "reference_number": ref, "currency": frappe.db.get_value("Account", gl_account, "account_currency") or "AED"})
		bt.insert()
		bt.submit()


# ---------------------------------------------------------------- payroll and HR
def _holiday_list(c):
	name = f"UAE {getdate(today()).year}"
	if not frappe.db.exists("Holiday List", name):
		y = getdate(today()).year
		hl = frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": name, "from_date": f"{y}-01-01", "to_date": f"{y}-12-31",
			"holidays": [{"holiday_date": d, "description": t} for d, t in ((f"{y}-01-01", "New Year"), (f"{y}-03-20", "Eid Al Fitr"),
				(f"{y}-05-27", "Arafat Day"), (f"{y}-05-28", "Eid Al Adha"), (f"{y}-12-02", "National Day"), (f"{y}-12-03", "National Day"))]})
		hl.insert()
		try:
			hl.weekly_off = "Saturday"
			hl.get_weekly_off_dates()
			hl.weekly_off = "Sunday"
			hl.get_weekly_off_dates()
			hl.save()
		except Exception:
			frappe.clear_last_message()
	frappe.db.set_value("Company", c.company, "default_holiday_list", name)
	# HRMS 16 reads holiday lists from Holiday List Assignment
	if frappe.db.exists("DocType", "Holiday List Assignment") and not frappe.db.exists("Holiday List Assignment",
		{"applicable_for": "Company", "assigned_to": c.company, "docstatus": 1}):
		hla = frappe.get_doc({"doctype": "Holiday List Assignment", "holiday_list": name, "applicable_for": "Company", "assigned_to": c.company,
			"from_date": f"{getdate(today()).year}-01-01"})
		hla.insert()
		hla.submit()
	for e in frappe.get_all("Employee", filters={"company": c.company, "holiday_list": ["is", "not set"]}, pluck="name"):
		frappe.db.set_value("Employee", e, "holiday_list", name, update_modified=False)
	return name


def _component(name, abbr, account):
	if not frappe.db.exists("Salary Component", name):
		frappe.get_doc({"doctype": "Salary Component", "salary_component": name, "salary_component_abbr": abbr, "type": "Earning",
			"depends_on_payment_days": 1, "accounts": [{"company": frappe.defaults.get_global_default("company"), "account": account}] if account else []}).insert()


PAY = {"Managing Director": 42000, "Finance Manager": 26000, "Sales Manager": 24000, "Purchase Manager": 23000, "Warehouse Manager": 16000,
	"HR Manager": 18000, "Sales Executive": 11000, "Accountant": 12000, "Storekeeper": 6500, "Buyer": 9500, "Logistics Coordinator": 9000, "Driver": 4200}


def v156_payroll(c):
	if "hrms" not in frappe.get_installed_apps() or frappe.db.exists("Salary Structure", "UAE Staff"):
		return
	_holiday_list(c)
	payable = _acc(c, "Payroll Payable") or _acc(c, "Other Payable")
	for name, abbr, acc in (("Basic Salary", "B", _acc(c, "Basic Salary")), ("Housing Allowance", "HA", _acc(c, "Housing Allowance")),
		("Transport Allowance", "TA", _acc(c, "Transportation Allowance"))):
		_component(name, abbr, acc)
	ss = frappe.get_doc({"doctype": "Salary Structure", "name": "UAE Staff", "__newname": "UAE Staff", "company": c.company, "is_active": "Yes",
		"payroll_frequency": "Monthly", "currency": "AED", "payment_account": frappe.get_cached_value("Company", c.company, "default_bank_account"),
		"earnings": [
			{"salary_component": "Basic Salary", "abbr": "B", "amount_based_on_formula": 1, "formula": "base * 0.6"},
			{"salary_component": "Housing Allowance", "abbr": "HA", "amount_based_on_formula": 1, "formula": "base * 0.3"},
			{"salary_component": "Transport Allowance", "abbr": "TA", "amount_based_on_formula": 1, "formula": "base * 0.1"}]})
	ss.insert()
	ss.submit()
	month_start = get_first_day(add_months(today(), -1))
	for e in frappe.get_all("Employee", filters={"company": c.company, "status": "Active"}, fields=["name", "designation", "date_of_joining"]):
		base = PAY.get(e.designation) or 9000
		from_date = max(getdate(e.date_of_joining), getdate(add_months(month_start, -2)))
		ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": e.name, "salary_structure": ss.name, "company": c.company,
			"from_date": from_date, "base": base, "currency": "AED", "payroll_payable_account": payable})
		ssa.insert()
		ssa.submit()
	pe = frappe.get_doc({"doctype": "Payroll Entry", "company": c.company, "posting_date": get_last_day(month_start), "payroll_frequency": "Monthly",
		"start_date": month_start, "end_date": get_last_day(month_start), "currency": "AED", "exchange_rate": 1,
		"payroll_payable_account": payable, "cost_center": _cc(c), "payment_account": frappe.get_cached_value("Company", c.company, "default_bank_account")})
	pe.insert()
	pe.fill_employee_details()
	pe.save()
	# HRMS rolls back (and commits) the whole transaction when one slip fails, which would undo the rest of the demo
	# data; with its test flag on it raises instead, and our step's savepoint handles the failure
	in_test = frappe.in_test
	frappe.in_test = True
	try:
		pe.submit()
		pe.reload()
		pe.submit_salary_slips()
	finally:
		frappe.in_test = in_test


def v156_hr(c):
	if "hrms" not in frappe.get_installed_apps() or frappe.db.exists("Leave Application", {"description": ["like", "Demo: %"]}):
		return
	_holiday_list(c)
	emps = frappe.get_all("Employee", filters={"company": c.company, "status": "Active"}, fields=["name", "employee_name", "user_id"], order_by="creation asc")
	if not emps:
		return
	y = getdate(today()).year
	approver = frappe.db.get_value("User", {"name": ["like", "lina.farah@%"]}) or "Administrator"
	for e in emps:
		if not frappe.db.exists("Leave Allocation", {"employee": e.name, "leave_type": "Privilege Leave", "docstatus": 1}):
			la = frappe.get_doc({"doctype": "Leave Allocation", "employee": e.name, "leave_type": "Privilege Leave", "from_date": f"{y}-01-01",
				"to_date": f"{y}-12-31", "new_leaves_allocated": 30, "company": c.company})
			la.insert()
			la.submit()
	for i, (e, days_ahead, length, why) in enumerate(((emps[0], 12, 4, "Family visit"), (emps[min(2, len(emps) - 1)], 20, 6, "Annual leave — home country"))):
		frappe.get_doc({"doctype": "Leave Application", "employee": e.name, "leave_type": "Privilege Leave", "from_date": c.d(days_ahead),
			"to_date": c.d(days_ahead + length - 1), "description": f"Demo: {why}", "leave_approver": approver, "status": "Open",
			"company": c.company, "posting_date": today()}).insert()
	for e in emps[:3]:
		for d, st in ((c.d(-1), "Present"), (c.d(-2), "Present")):
			if not frappe.db.exists("Attendance", {"employee": e.name, "attendance_date": d}):
				at = frappe.get_doc({"doctype": "Attendance", "employee": e.name, "attendance_date": d, "status": st, "company": c.company})
				at.insert()
				at.submit()
	payable = _acc(c, "Other Payable")
	for typ, acc in (("Travel", _acc(c, "Conveyance Expenses")), ("Food", _acc(c, "Meals"))):
		t = frappe.get_doc("Expense Claim Type", typ)
		if acc and not any(r.company == c.company for r in t.accounts):
			t.append("accounts", {"company": c.company, "default_account": acc})
			t.save()
	for e, typ, amt, desc in ((emps[-1], "Travel", 420, "Taxi to Jebel Ali port — customs inspection"), (emps[0], "Food", 189, "Client lunch — Al Noor LLC")):
		ec = frappe.get_doc({"doctype": "Expense Claim", "employee": e.name, "company": c.company, "posting_date": c.d(-3), "payable_account": payable,
			"currency": "AED", "exchange_rate": 1,
			"expense_approver": approver, "expenses": [{"expense_date": c.d(-4), "expense_type": typ, "description": desc, "amount": amt, "sanctioned_amount": amt}]})
		ec.insert()
	adv = _acc(c, "Employee Advances") or frappe.db.get_value("Account", {"company": c.company, "account_name": ["like", "%Advance%"], "root_type": "Asset", "is_group": 0})
	if adv:
		frappe.get_doc({"doctype": "Employee Advance", "employee": emps[-1].name, "company": c.company, "posting_date": c.d(-5), "currency": "AED",
			"purpose": "Cash for site visit expenses — Abu Dhabi", "advance_amount": 1500, "advance_account": adv, "exchange_rate": 1}).insert()


# ---------------------------------------------------------------- fixed assets
ASSETS = [("Delivery van — Toyota Hiace (DXB 4471)", "Vehicles", "Motor Vehicles", 118000, 420, 60),
	("Delivery van — Nissan Urvan (DXB 8820)", "Vehicles", "Motor Vehicles", 104000, 300, 60),
	("Forklift — Toyota 2.5 t", "Material handling", "Furniture and Equipment", 86000, 520, 96),
	("Warehouse racking — Main Warehouse", "Warehouse racking", "Furniture and Equipment", 64000, 610, 120),
	("Laptops — sales and finance (12)", "IT equipment", "Computer Hardware & Software", 54000, 200, 36),
	("Office fit-out — Al Quoz", "Furniture & fit-out", "Furniture and Equipment", 72000, 650, 84)]
DEP = {"Motor Vehicles": ("Acc. Depreciation of Motor Vehicles", "Depreciation Of Motor Vehicles"),
	"Furniture and Equipment": ("Acc.Deprn.of Furniture & Office Equipment", "Depreciation Of Furniture & Office Equipment"),
	"Computer Hardware & Software": ("Acc. Deprn.Computer Hardware & Software", "Depreciation Of Computer Hard & Soft")}


def v156_assets(c):
	if frappe.db.count("Asset", {"company": c.company}):
		return
	loc = "Al Quoz Warehouse"
	if not frappe.db.exists("Location", loc):
		frappe.get_doc({"doctype": "Location", "location_name": loc}).insert()
	for name, cat, fa, cost, age, life in ASSETS:
		if not frappe.db.exists("Asset Category", cat):
			acc, exp = DEP[fa]
			frappe.get_doc({"doctype": "Asset Category", "asset_category_name": cat, "enable_cwip_accounting": 0,
				"finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": life, "frequency_of_depreciation": 1}],
				"accounts": [{"company_name": c.company, "fixed_asset_account": _acc(c, fa), "accumulated_depreciation_account": _acc(c, acc),
					"depreciation_expense_account": _acc(c, exp)}]}).insert()
		code = "FA-" + cat.upper().replace(" ", "-").replace("&", "AND")[:20]
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": cat, "item_group": frappe.db.get_value("Item Group", {"is_group": 0}),
				"stock_uom": "Nos", "is_stock_item": 0, "is_fixed_asset": 1, "asset_category": cat}).insert()
		purchased = c.d(-age)
		months_used = max(0, int(age / 30.4) - 1)
		a = frappe.get_doc({"doctype": "Asset", "item_code": code, "asset_name": name, "asset_category": cat, "company": c.company, "location": loc,
			"is_existing_asset": 1, "purchase_date": purchased, "available_for_use_date": purchased, "gross_purchase_amount": cost,
			"purchase_amount": cost, "net_purchase_amount": cost, "opening_accumulated_depreciation": round(cost / life * months_used, 2), "opening_number_of_booked_depreciations": months_used,
			"calculate_depreciation": 1, "finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": life,
				"frequency_of_depreciation": 1, "depreciation_start_date": get_last_day(c.d(0))}]})
		if "van" in name.lower() and frappe.get_meta("Asset").has_field("hs_next_service"):
			a.hs_next_service = c.d(-3 if "Hiace" in name else 25)
		a.insert()
		a.submit()


# ---------------------------------------------------------------- delivery
def v156_trips(c):
	from hipersign_trading.demo import data as D

	if frappe.db.count("Delivery Trip"):
		return
	vehicles = []
	for name, mobile, vehicle, key in D.DRIVERS:
		plate = (vehicle or "").split("—")[-1].strip() or vehicle
		if plate and not frappe.db.exists("Vehicle", plate):
			frappe.get_doc({"doctype": "Vehicle", "license_plate": plate, "make": "Toyota" if "4471" in plate else "Nissan", "model": "Hiace" if "4471" in plate else "Urvan",
				"last_odometer": 48210, "fuel_type": "Diesel", "uom": "Litre" if frappe.db.exists("UOM", "Litre") else "Nos", "company": c.company}).insert()
		vehicles.append((frappe.db.get_value("Driver", {"full_name": name}), plate))
	dns = frappe.get_all("Delivery Note", filters={"company": c.company, "docstatus": 1, "is_return": 0}, fields=["name", "customer", "posting_date", "hs_delivery_status"],
		order_by="posting_date desc", limit=6)
	if not dns or not vehicles:
		return
	groups = [[d for d in dns if d.hs_delivery_status == "Out for Delivery"][:3] or dns[:2], [d for d in dns if d.hs_delivery_status == "Delivered"][:3]]
	for i, stops in enumerate(groups):
		if not stops:
			continue
		def address(cust):
			return frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "link_name": cust, "parenttype": "Address"}, "parent")

		stops = [d for d in stops if address(d.customer)]
		if not stops:
			continue
		driver, plate = vehicles[i % len(vehicles)]
		trip = frappe.get_doc({"doctype": "Delivery Trip", "company": c.company, "driver": driver, "vehicle": plate,
			"departure_time": f"{c.d(0 if i == 0 else -2)} 08:30:00",
			"delivery_stops": [{"customer": d.customer, "address": address(d.customer), "delivery_note": d.name, "visited": 1 if i == 1 else 0} for d in stops]})
		trip.insert()
		trip.submit()


def v156_credit_requests(c):
	if not frappe.db.exists("DocType", "Credit Limit Request") or frappe.db.count("Credit Limit Request"):
		return
	for cust, limit, reason in (("Future Build Contracting", 350000, "Two new villa projects in Dubai South — orders of AED 120K a month expected"),
		("Star Vision Electronics", 120000, "Seasonal stock-up before Q4 promotions")):
		if frappe.db.exists("Customer", cust):
			doc = frappe.get_doc({"doctype": "Credit Limit Request", "customer": cust, "company": c.company, "requested_limit": limit})
			if doc.meta.has_field("reason"):
				doc.reason = reason
			doc.insert()


# ---------------------------------------------------------------- conversations
def v156_messages(c):
	if frappe.db.exists("Comment", {"content": ["like", "%[hs156]%"]}):
		return
	def user(prefix):
		return frappe.db.get_value("User", {"name": ["like", f"{prefix}@%"]})

	omar, priya, sara, fatima, imran = user("omar.haddad"), user("priya.menon"), user("sara.alhashimi"), user("fatima.alzaabi"), user("imran.sheikh")
	so = frappe.db.get_value("Sales Order", {"company": c.company, "docstatus": 1}, "name", order_by="transaction_date desc")
	shp = frappe.db.get_value("Import Shipment", {"company": c.company, "status": "Under Customs Clearance"})
	inv = frappe.db.get_value("Sales Invoice", {"company": c.company, "docstatus": 1, "outstanding_amount": [">", 0]}, "name", order_by="due_date asc")
	posts = []
	if so and omar and priya:
		posts += [("Sales Order", so, priya, f"Customer asked to split the delivery into two drops. @{_mention(omar)} can we agree a second date? [hs156]"),
			("Sales Order", so, omar, f"Yes — second drop next Thursday. @{_mention(priya)} please update the delivery date. [hs156]")]
	if shp and fatima and imran:
		posts += [("Import Shipment", shp, imran, f"Customs are holding it for the Certificate of Origin. @{_mention(fatima)} can the supplier courier the original? [hs156]")]
	if inv and sara:
		posts += [("Sales Invoice", inv, sara, "Customer promised to pay by Thursday — follow up if nothing arrives. [hs156]")]
	for dt, dn, who, text in posts:
		frappe.set_user(who)
		try:
			frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": dt, "reference_name": dn, "content": _html(text),
				"comment_email": who, "comment_by": frappe.db.get_value("User", who, "full_name")}).insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
	if so:
		cust = frappe.db.get_value("Sales Order", so, "customer")
		frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Email", "sent_or_received": "Received",
			"subject": f"Re: {so} — delivery schedule", "content": "Dear team, please confirm the second delivery date and send the updated delivery note. Regards, Procurement",
			"sender": "procurement@customer.example", "reference_doctype": "Sales Order", "reference_name": so, "seen": 0,
			"timeline_links": [{"link_doctype": "Customer", "link_name": cust}]}).insert(ignore_permissions=True)
	frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Email", "sent_or_received": "Received",
		"subject": "Price enquiry — 4MP cameras and 24-port PoE switches", "content": "Hello, please quote 120 × 4MP cameras and 6 × 24-port PoE switches delivered to Sharjah.",
		"sender": "buyer@newprospect.example", "seen": 0}).insert(ignore_permissions=True)


def _mention(user):
	return frappe.db.get_value("User", user, "full_name") or user


def _html(text):
	import re

	# @Full Name → Frappe's mention span, so the mention is a real one (notification + Mentions folder)
	def rep(m):
		name = m.group(1)
		uid = frappe.db.get_value("User", {"full_name": name})
		return f'<span class="mention" data-id="{uid}" data-value="{name}" data-denotation-char="@">@{name}</span>' if uid else m.group(0)

	return "<p>" + re.sub(r"@([A-Z][\w']+(?: [A-Z][\w']+){0,2})", rep, frappe.utils.escape_html(text)) + "</p>"


# ---------------------------------------------------------------- the view-only demo account
def v156_viewer(c):
	if frappe.db.exists("User", VIEWER):
		return
	md = frappe.db.get_value("User", {"name": ["like", "khalid.almansoori@%"]})
	roles = [r.role for r in frappe.get_doc("User", md).roles] if md else ["Managing Director", "Sales Manager", "Purchase Manager", "Accounts Manager", "Stock Manager"]
	u = frappe.get_doc({"doctype": "User", "email": VIEWER, "first_name": "Demo", "last_name": "Visitor", "send_welcome_email": 0, "user_type": "System User",
		"roles": [{"role": r} for r in set(roles) - {"System Manager"}] + [{"role": "Demo Viewer"}]})
	u.flags.no_welcome_mail = True
	u.insert(ignore_permissions=True)


STEPS = [v156_vat_settings, v156_import_charge_bills, v156_intercompany, v156_history, v156_bank_statement, v156_payroll, v156_hr, v156_assets,
	v156_trips, v156_credit_requests, v156_messages, v156_viewer]
