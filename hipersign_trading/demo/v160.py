"""v1.6.0 demo data.

- sales delivered and invoiced this month, so "This month" on Home and on Quotations & Orders shows a real trading
  month (the 1.5.6 data had little revenue in the current month and the month's salaries and rent made it a loss)
- the Live deal demo switched on (demo sites only)

Every step skips what is already there, so the loader can be run again.
"""

import frappe
from frappe.utils import add_days, flt, get_first_day, getdate, today

from hipersign_trading.demo.v156 import _pay

# customer, [(item, qty)], day of the month, paid
MONTH_SALES = [
	("Gulf Trading LLC", [("ITM-001", 60), ("ITM-002", 400)], 2, True),
	("Al Noor LLC", [("ITM-003", 180), ("ITM-004", 30)], 5, True),
	("Future Build", [("ITM-001", 45), ("ITM-004", 40)], 9, False),
	("Horizon Trading", [("ITM-003", 220), ("ITM-002", 300)], 14, False),
	("Gulf Projects", [("ITM-004", 35), ("ITM-001", 25)], 19, False),
]


def v160_month_sales(c):
	if frappe.db.exists("Sales Invoice", {"company": c.company, "remarks": ["like", "Month sales %"]}):
		return
	start = get_first_day(today())
	tax = frappe.db.get_single_value("Hipersign Settings", "local_tax_template")
	for i, (cust, lines, day, paid) in enumerate(MONTH_SALES):
		if not frappe.db.exists("Customer", cust):
			continue
		d = add_days(start, day - 1)
		if getdate(d) > getdate(today()):
			d = add_days(today(), -(len(MONTH_SALES) - i))
			if getdate(d) < start:
				d = today()
		items = []
		for code, qty in lines:
			if not frappe.db.exists("Item", code):
				continue
			wh = frappe.db.get_value("Item Default", {"parent": code, "company": c.company}, "default_warehouse") or c.wh("Main Warehouse")
			if flt(frappe.db.get_value("Bin", {"item_code": code, "warehouse": wh}, "actual_qty")) < qty:
				continue
			rate = flt(frappe.db.get_value("Item Price", {"item_code": code, "price_list": "Standard Selling"}, "price_list_rate"))
			if rate:
				items.append({"item_code": code, "qty": qty, "rate": rate, "price_list_rate": rate, "warehouse": wh})
		if not items:
			continue
		si = frappe.get_doc({"doctype": "Sales Invoice", "customer": cust, "company": c.company, "posting_date": d, "set_posting_time": 1,
			"due_date": add_days(d, 30), "update_stock": 1, "remarks": f"Month sales {i + 1}", "taxes_and_charges": tax, "items": items})
		si.set_missing_values()
		si.set("taxes", [])
		if tax:
			si.append_taxes_from_master()
		si.flags.ignore_permissions = True
		si.insert()
		si.submit()
		if paid:
			_pay(c, si, add_days(d, 3) if getdate(add_days(d, 3)) <= getdate(today()) else today())


def _prices(c):
	"""make_so needs the selling price list the loader keeps on its context; a re-run that skips the early steps has none."""
	if not c.get("selling_pl"):
		c.selling_pl = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"


def v160_company_accounts(c):
	"""FX-01: the demo chart has no Exchange Gain/Loss or Round Off account, so month-end revaluation stopped with
	"Please set Unrealized Exchange Gain/Loss Account". Add them under the indirect expenses and set them on each company."""
	for company in frappe.get_all("Company", filters={"is_group": 0}, pluck="name"):
		co = frappe.get_cached_doc("Company", company)
		parent = frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": "Expense", "account_name": ["like", "%Indirect%"]}) \
			or frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": "Expense", "parent_account": ["is", "set"]})
		if not parent:
			continue

		def account(name):
			got = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
			if got:
				return got
			a = frappe.get_doc({"doctype": "Account", "account_name": name, "company": company, "parent_account": parent, "root_type": "Expense",
				"report_type": "Profit and Loss", "account_type": "Round Off" if name == "Round Off" else ""})
			a.flags.ignore_permissions = True
			a.insert()
			return a.name

		vals = {}
		if not co.exchange_gain_loss_account:
			vals["exchange_gain_loss_account"] = account("Exchange Gain/Loss")
		if not co.get("unrealized_exchange_gain_loss_account"):
			vals["unrealized_exchange_gain_loss_account"] = vals.get("exchange_gain_loss_account") or co.exchange_gain_loss_account or account("Exchange Gain/Loss")
		if not co.round_off_account:
			vals["round_off_account"] = account("Round Off")
		if vals:
			frappe.db.set_value("Company", company, vals)
	from hipersign_trading.setup import ensure_cheque_accounts

	ensure_cheque_accounts()


def v160_reservation(c):
	"""ADV-03 on sites loaded with 1.5.x: the advance order's stock was never reserved; reserve it now."""
	from hipersign_trading.demo.v12 import v12_reservations

	frappe.db.savepoint("hs_v160_sre")
	try:
		v12_reservations(c)
	except Exception:
		frappe.db.rollback(save_point="hs_v160_sre")
		frappe.clear_last_message()


def v160_portal(c):
	from hipersign_trading.demo import portal_user

	portal_user(c)


def v160_pending_lpos(c):
	"""SAL-03 / KYC-02: the orders waiting for the Finance Manager or the Sales Manager carry their customer LPO, so
	approving them shows the credit / KYC rule the script is about — not the LPO rule (the demo attached LPOs to
	submitted orders only). The pending LPO exception (DOC-03) moves to a plain draft order of its own."""
	from hipersign_trading.demo import make_so
	from hipersign_trading.demo.v13 import _attach

	_prices(c)

	pending = frappe.get_all("Sales Order", filters={"docstatus": 0, "company": c.company, "po_no": ["is", "set"],
		"workflow_state": ["in", ["Pending Sales Manager", "Pending Finance Manager"]]}, fields=["name", "po_no"])
	for so in pending:
		wv = frappe.db.get_value("Document Waiver", {"reference_doctype": "Sales Order", "reference_name": so.name, "status": "Pending"})
		if wv:
			draft = frappe.db.get_value("Sales Order", {"po_no": "GTL/PO/0919", "docstatus": 0})
			if not draft:
				frappe.db.savepoint("hs_v160_gtl")
				try:
					draft = make_so(c, "Gulf Trading LLC", [("ITM-001", 45), ("ITM-004", 20)], 1, "GTL/PO/0919", submit=False).name
				except Exception:
					frappe.db.rollback(save_point="hs_v160_gtl")
					frappe.clear_last_message()
					continue
			frappe.db.set_value("Document Waiver", wv, "reference_name", draft, update_modified=False)
		_attach("Sales Order", so.name, "Customer LPO", f"LPO {so.po_no}.pdf")


def v160_horizon_overdue(c):
	"""COL-02: Horizon Trading must have an invoice more than the hold limit overdue. The 1.5.6 bank-charge example
	(TT/BNK/55120) settles HT-5101, so a second old invoice, HT-5174, stays open."""
	from frappe.utils import add_days, getdate

	days = int(frappe.db.get_single_value("Hipersign Settings", "collection_hold_days") or 60)
	if frappe.db.exists("Sales Invoice", {"customer": "Horizon Trading", "company": c.company, "docstatus": 1, "outstanding_amount": [">", 0],
			"due_date": ["<", add_days(today(), -days)]}):
		return
	if frappe.db.exists("Sales Order", {"po_no": "HT-5174"}) or not frappe.db.exists("Customer", "Horizon Trading"):
		return
	from hipersign_trading.demo.v12 import _demo

	_prices(c)
	frappe.db.savepoint("hs_v160_ht")
	try:
		_demo().make_so(c, "Horizon Trading", [("ITM-003", 40)], 128, "HT-5174", deliver=125, invoice=125)
	except Exception:
		frappe.db.rollback(save_point="hs_v160_ht")
		frappe.clear_last_message()


def v160_deal_demo(c):
	if frappe.conf.get("hipersign_demo_site"):
		frappe.db.set_single_value("Hipersign Settings", "deal_demo", 1)


STEPS = [v160_company_accounts, v160_reservation, v160_portal, v160_pending_lpos, v160_horizon_overdue, v160_month_sales, v160_deal_demo]
