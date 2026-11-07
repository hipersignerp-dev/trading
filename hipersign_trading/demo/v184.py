"""v1.8.4 demo data (fixes from the audit):
- #40: every company of the group on this site is a Hipersign Group Member — Golden Dragon Interiors LLC and Hipersign
  Lighting Industries FZE were left out, so the group view missed the two companies that earn most of the UAE profit.
- Balance sheet: the opening stock was booked against Temporary Opening and never closed to equity, so Current Assets
  showed about −2.8M. An opening entry moves what is left on Temporary Opening to the company's opening equity.
Both are idempotent: a re-run changes nothing that is already right."""

import frappe
from frappe.utils import flt, today


def v184_group_members(c):
	from hipersign_trading.group import sync_member

	holding = frappe.db.get_value("Company", c.company, "parent_company")
	if not holding:
		return
	for co in frappe.get_all("Company", filters={"parent_company": holding}, fields=["name", "country", "default_currency", "hs_ownership_pct"]
			if frappe.get_meta("Company").has_field("hs_ownership_pct") else ["name", "country", "default_currency"]):
		if frappe.db.exists("Hipersign Group Member", {"company": co.name}):
			continue
		frappe.get_doc({"doctype": "Hipersign Group Member", "member_name": co.name, "company": co.name, "ownership_pct": flt(co.get("hs_ownership_pct")) or 100,
			"is_parent": 0, "active": 1, "country": co.country, "currency": co.default_currency}).insert(ignore_permissions=True)
		try:
			sync_member(co.name, today())
		except Exception:
			frappe.clear_last_message()
			frappe.log_error(title=f"Hipersign demo: group sync {co.name}")


def _equity_account(company):
	for like in ("Opening Balance Equity%", "Previous Years Results%", "Retained Earnings%"):
		a = frappe.db.get_value("Account", {"company": company, "root_type": "Equity", "is_group": 0, "account_name": ["like", like]})
		if a:
			return a
	return frappe.db.get_value("Account", {"company": company, "root_type": "Equity", "is_group": 0})


def v184_close_temporary_opening(c):
	skip = frappe.flags.hs_skip_doc_rules
	frappe.flags.hs_skip_doc_rules = True  # an opening entry by the system, not a manual entry needing a document
	try:
		_close_temporary_opening()
	finally:
		frappe.flags.hs_skip_doc_rules = skip


def _close_temporary_opening():
	for co in frappe.get_all("Company", pluck="name"):
		tmp = frappe.get_all("Account", filters={"company": co, "account_type": "Temporary", "is_group": 0}, pluck="name")
		for acc in tmp:
			bal, first = frappe.db.sql("""select sum(debit - credit), min(posting_date) from `tabGL Entry` where account = %s and is_cancelled = 0""", acc)[0]
			bal = flt(bal, 2)
			if abs(bal) < 0.01:
				continue
			eq = _equity_account(co)
			if not eq:
				continue
			cc = frappe.get_cached_value("Company", co, "cost_center")
			je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Opening Entry", "is_opening": "Yes", "company": co, "posting_date": first or today(),
				"user_remark": "Opening stock financed by the owners — Temporary Opening closed to opening equity",
				"accounts": [{"account": acc, "debit_in_account_currency": -bal if bal < 0 else 0, "credit_in_account_currency": bal if bal > 0 else 0, "cost_center": cc},
					{"account": eq, "debit_in_account_currency": bal if bal > 0 else 0, "credit_in_account_currency": -bal if bal < 0 else 0, "cost_center": cc}]})
			je.flags.ignore_permissions = True
			je.insert()
			je.submit()


STEPS = [v184_group_members, v184_close_temporary_opening]
