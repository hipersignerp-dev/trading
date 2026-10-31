"""v1.7.0: the customer portal in the prototype's design — one page with the customer's orders (with the order
journey), quotations, invoices, statement, deliveries and warranty. Staff open it as a preview of any customer
(the desk's Customer Portal page shows it in a frame)."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from hipersign_trading.portal import portal_customer, preview_context

no_cache = 1
TABS = [("orders", "My orders"), ("quotations", "Quotations"), ("invoices", "Invoices"), ("statement", "Statement"), ("deliveries", "Deliveries"), ("warranty", "Warranty")]


def get_context(context):
	customer, customers = portal_customer()
	c = frappe.get_cached_doc("Customer", customer)
	context.no_header = 1
	context.title = _("Customer portal")
	context.customer = c
	preview_context(context, customer, customers)
	context.embed = frappe.form_dict.get("embed") == "1"
	tab = frappe.form_dict.get("tab") or "orders"
	context.tab = tab if tab in dict(TABS) else "orders"
	context.tabs = [(k, _(l)) for k, l in TABS]
	company = frappe.defaults.get_global_default("company")
	cur = c.default_currency or frappe.get_cached_value("Company", company, "default_currency") or "AED"
	context.currency = cur
	contact = frappe.db.get_value("Contact", {"user": frappe.session.user}, ["first_name", "last_name"], as_dict=True) if not context.hs_preview else None
	if not contact and c.customer_primary_contact:
		contact = frappe.db.get_value("Contact", c.customer_primary_contact, ["first_name", "last_name"], as_dict=True)
	context.welcome = " ".join(x for x in [(contact or {}).get("first_name"), (contact or {}).get("last_name")] if x)
	t = getdate(today())

	invs = frappe.get_all("Sales Invoice", filters={"customer": customer, "docstatus": 1}, fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount",
		"is_return", "return_against", "currency", "status"], order_by="posting_date desc", limit=500)
	balance = sum(flt(i.outstanding_amount) for i in invs)
	overdue = sum(flt(i.outstanding_amount) for i in invs if i.due_date and getdate(i.due_date) < t and flt(i.outstanding_amount) > 0)
	limit = sum(flt(x.credit_limit) for x in frappe.get_all("Customer Credit Limit", filters={"parent": customer, "parenttype": "Customer"}, fields=["credit_limit"]))
	open_so = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]},
		fields=["name", "grand_total", "per_billed"])
	open_val = sum(flt(s.grand_total) * (1 - flt(s.per_billed) / 100) for s in open_so)
	from hipersign_trading.api.serials import customer_units

	units = customer_units(customer)
	context.kpis = [
		("list", _("Open orders"), str(len(open_so)), ""),
		("file-text", _("Balance due"), frappe.format(balance, {"fieldtype": "Currency", "options": cur}), ""),
		("triangle-alert", _("Overdue"), frappe.format(overdue, {"fieldtype": "Currency", "options": cur}), "red" if overdue else ""),
		("check", _("Credit available"), frappe.format(max(0, limit - balance - open_val), {"fieldtype": "Currency", "options": cur}) if limit else _("On account"), ""),
		("shield", _("Units under warranty"), str(len([u for u in units if u.active])), ""),
	]

	if context.tab == "orders":
		from hipersign_trading.api.tracker import build_row

		sos = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": 1}, fields=["name", "customer", "customer_name", "po_no", "transaction_date",
			"delivery_date", "currency", "grand_total", "base_grand_total", "conversion_rate", "advance_paid", "per_delivered", "per_billed", "status", "docstatus", "owner",
			"hs_is_export" if frappe.get_meta("Sales Order").has_field("hs_is_export") else "name as hs_is_export"], order_by="transaction_date desc", limit=20)
		rows = []
		for so in sos:
			r = build_row(so)
			r["city"] = frappe.db.get_value("Address", frappe.db.get_value("Sales Order", so.name, "shipping_address_name"), "city") if frappe.db.get_value("Sales Order", so.name, "shipping_address_name") else ""
			rows.append(r)
		context.orders = rows
	elif context.tab == "quotations":
		context.quotations = frappe.get_all("Quotation", filters={"party_name": customer, "quotation_to": "Customer", "docstatus": 1}, fields=["name", "transaction_date",
			"valid_till", "grand_total", "currency", "status"], order_by="transaction_date desc", limit=50)
	elif context.tab == "invoices":
		context.invoices = invs
	elif context.tab == "statement":
		rows = []
		for si in reversed(invs):
			rows.append({"date": si.posting_date, "ref": si.name, "doctype": "Sales Invoice", "desc": (_("Credit note against {0}").format(si.return_against)) if si.is_return else _("Tax invoice"),
				"debit": 0 if si.is_return else flt(si.grand_total), "credit": -flt(si.grand_total) if si.is_return else 0})
		for pe in frappe.get_all("Payment Entry", filters={"party_type": "Customer", "party": customer, "docstatus": 1, "payment_type": "Receive"},
			fields=["name", "posting_date", "paid_amount", "mode_of_payment", "reference_no"], order_by="posting_date"):
			rows.append({"date": pe.posting_date, "ref": pe.name, "doctype": None, "desc": _("Payment received") + (f" — {pe.mode_of_payment}" if pe.mode_of_payment else "")
				+ (f" {pe.reference_no}" if pe.reference_no else ""), "debit": 0, "credit": flt(pe.paid_amount)})
		rows.sort(key=lambda r: (getdate(r["date"]), r["ref"]))
		bal = 0
		for r in rows:
			bal += r["debit"] - r["credit"]
			r["balance"] = bal
		context.statement = rows
		context.pdcs = frappe.get_all("Post Dated Cheque", filters={"party": customer, "direction": "Received", "status": ["in", ["In Hand", "Deposited"]]},
			fields=["cheque_no", "cheque_date", "amount", "status"], order_by="cheque_date") if frappe.db.table_exists("Post Dated Cheque") else []
	elif context.tab == "deliveries":
		context.deliveries = frappe.get_all("Delivery Note", filters={"customer": customer, "docstatus": 1, "is_return": 0}, fields=["name", "posting_date", "status",
			"grand_total", "currency", "driver_name", "vehicle_no", "lr_no"] + (["hs_delivery_status"] if frappe.get_meta("Delivery Note").has_field("hs_delivery_status") else []),
			order_by="posting_date desc", limit=50)
	elif context.tab == "warranty":
		context.units = units
		context.claims = frappe.get_all("Warranty Claim", filters={"customer": customer}, fields=["name", "serial_no", "item_name", "complaint_date", "status"],
			order_by="complaint_date desc", limit=50) if frappe.db.table_exists("Warranty Claim") else []
	context.fmt = lambda v: frappe.format(v, {"fieldtype": "Currency", "options": cur})
	context.fdate = lambda v: frappe.format(v, {"fieldtype": "Date"}) if v else "—"
	return context
