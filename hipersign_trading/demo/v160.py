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


def v160_deal_demo(c):
	if frappe.conf.get("hipersign_demo_site"):
		frappe.db.set_single_value("Hipersign Settings", "deal_demo", 1)


STEPS = [v160_month_sales, v160_deal_demo]
