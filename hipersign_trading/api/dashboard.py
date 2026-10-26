"""Number card methods for the Hipersign workspace (gross and net profit)."""

import frappe
from frappe.utils import flt, get_first_day, today


def _period(filters=None):
	return get_first_day(today()), today()


def _company():
	return frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")


@frappe.whitelist()
def gross_profit(filters=None):
	start, end = _period(filters)
	company = _company()
	sales = flt(
		frappe.db.sql(
			"""select sum(base_net_total) from `tabSales Invoice`
			where docstatus=1 and company=%s and posting_date between %s and %s""",
			(company, start, end),
		)[0][0]
	)
	cogs = -flt(
		frappe.db.sql(
			"""select sum(stock_value_difference) from `tabStock Ledger Entry`
			where is_cancelled=0 and company=%s and posting_date between %s and %s
			and voucher_type in ('Delivery Note','Sales Invoice')""",
			(company, start, end),
		)[0][0]
	)
	return {"value": sales - cogs, "fieldtype": "Currency", "route": ["query-report", "Gross Profit"]}


@frappe.whitelist()
def net_profit(filters=None):
	start, end = _period(filters)
	company = _company()
	rows = frappe.db.sql(
		"""select acc.root_type, sum(gle.credit - gle.debit) as amt
		from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
		where gle.is_cancelled=0 and gle.company=%s and gle.posting_date between %s and %s
		and acc.root_type in ('Income','Expense')
		group by acc.root_type""",
		(company, start, end),
		as_dict=True,
	)
	value = sum(flt(r.amt) for r in rows)
	return {"value": value, "fieldtype": "Currency", "route": ["query-report", "Profit and Loss Statement"]}
