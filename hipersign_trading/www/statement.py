import frappe
from frappe.utils import flt, getdate, today

from hipersign_trading.portal import portal_customer, preview_context

no_cache = 1


def get_context(context):
	customer, customers = portal_customer()
	context.show_sidebar = 1
	context.title = "Statement of account"
	context.customer = frappe.get_cached_doc("Customer", customer)
	preview_context(context, customer, customers)
	context.customers = customers
	rows = []
	for si in frappe.get_all("Sales Invoice", filters={"customer": customer, "docstatus": 1},
			fields=["name", "posting_date", "grand_total", "outstanding_amount", "due_date", "is_return", "return_against"], order_by="posting_date"):
		rows.append({"date": si.posting_date, "ref": si.name, "doctype": "Sales Invoice",
			"desc": ("Credit note against " + si.return_against) if si.is_return else "Tax invoice",
			"debit": 0 if si.is_return else flt(si.grand_total), "credit": -flt(si.grand_total) if si.is_return else 0,
			"due": None if si.is_return else si.due_date, "open": flt(si.outstanding_amount)})
	for pe in frappe.get_all("Payment Entry", filters={"party_type": "Customer", "party": customer, "docstatus": 1, "payment_type": "Receive"},
			fields=["name", "posting_date", "paid_amount", "mode_of_payment", "reference_no"], order_by="posting_date"):
		rows.append({"date": pe.posting_date, "ref": pe.name, "doctype": None, "desc": "Payment received" + (f" — {pe.mode_of_payment}" if pe.mode_of_payment else "") + (f" {pe.reference_no}" if pe.reference_no else ""),
			"debit": 0, "credit": flt(pe.paid_amount), "due": None, "open": 0})
	rows.sort(key=lambda r: (getdate(r["date"]), r["ref"]))
	bal = 0
	for r in rows:
		bal += r["debit"] - r["credit"]
		r["balance"] = bal
	context.rows = rows
	context.balance = bal
	context.overdue = sum(r["open"] for r in rows if r["due"] and getdate(r["due"]) < getdate(today()) and r["open"] > 0)
	context.pdcs = frappe.get_all("Post Dated Cheque", filters={"party": customer, "direction": "Received", "status": ["in", ["In Hand", "Deposited"]]},
		fields=["cheque_no", "cheque_date", "amount", "status"], order_by="cheque_date") if frappe.db.table_exists("Post Dated Cheque") else []
	context.currency = frappe.get_cached_value("Company", frappe.defaults.get_global_default("company"), "default_currency") or "AED"
	return context
