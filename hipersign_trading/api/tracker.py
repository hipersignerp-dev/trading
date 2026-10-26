"""Data for the Sales Order Tracker page: seven stages per order, payment summary and popups."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

STAGES = ["Quotation", "Approval", "Stock Ready", "Picked", "Delivered", "Invoiced", "Paid"]


@frappe.whitelist()
def get_orders(search=None, status=None, sales_person=None, month=None, limit=60):
	filters = {"docstatus": ["<", 2], "company": frappe.defaults.get_user_default("Company")}
	if not filters["company"]:
		filters.pop("company")
	if month:
		filters["transaction_date"] = ["like", f"{month}%"]
	if sales_person:
		filters["owner"] = sales_person
	or_filters = None
	if search:
		or_filters = {
			"name": ["like", f"%{search}%"],
			"customer_name": ["like", f"%{search}%"],
			"po_no": ["like", f"%{search}%"],
		}
	orders = frappe.get_list(
		"Sales Order",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "customer", "customer_name", "po_no", "transaction_date", "delivery_date", "currency",
			"grand_total", "base_grand_total", "advance_paid", "per_delivered", "per_billed", "status",
			"docstatus", "owner", "hs_is_export",
		],
		order_by="transaction_date desc, name desc",
		limit_page_length=int(limit),
	)
	out = []
	for so in orders:
		row = build_row(so)
		if status and row["bucket"] != status:
			continue
		out.append(row)
	totals = {
		"value": sum(r["value"] for r in out),
		"paid": sum(r["paid"] for r in out),
		"remaining": sum(r["remaining"] for r in out),
		"overdue": sum(r["overdue"] for r in out),
	}
	return {"orders": out, "totals": totals}


def build_row(so):
	name = so.name
	items = frappe.get_all(
		"Sales Order Item",
		filters={"parent": name},
		fields=["item_code", "item_name", "qty", "delivered_qty", "warehouse", "prevdoc_docname"],
	)
	quotation = next((i.prevdoc_docname for i in items if i.prevdoc_docname), None)
	dns = frappe.db.sql(
		"""select distinct dn.name, dn.posting_date, dn.status, dn.driver_name, dn.vehicle_no
		from `tabDelivery Note` dn join `tabDelivery Note Item` dni on dni.parent = dn.name
		where dni.against_sales_order=%s and dn.docstatus=1""",
		name,
		as_dict=True,
	)
	picks = frappe.db.sql(
		"""select distinct pl.name, pl.status from `tabPick List` pl join `tabPick List Item` pli on pli.parent = pl.name
		where pli.sales_order=%s and pl.docstatus<2""",
		name,
		as_dict=True,
	)
	invs = frappe.db.sql(
		"""select distinct si.name, si.posting_date, si.due_date, si.grand_total, si.outstanding_amount, si.total_advance
		from `tabSales Invoice` si join `tabSales Invoice Item` sii on sii.parent = si.name
		where sii.sales_order=%s and si.docstatus=1""",
		name,
		as_dict=True,
	)
	value = flt(so.grand_total)
	inv_paid = sum(flt(i.grand_total) - flt(i.outstanding_amount) for i in invs)
	unallocated_adv = max(0, flt(so.advance_paid) - sum(flt(i.total_advance) for i in invs))
	paid = min(value, inv_paid + unallocated_adv) if invs else min(value, flt(so.advance_paid))
	overdue = sum(
		flt(i.outstanding_amount) for i in invs if i.due_date and getdate(i.due_date) < getdate(today())
	)
	wf = frappe.db.get_value("Sales Order", name, "workflow_state") if frappe.get_meta("Sales Order").has_field("workflow_state") else None

	stock_short = []
	for i in items:
		rem = flt(i.qty) - flt(i.delivered_qty)
		if rem > 0 and frappe.db.get_value("Item", i.item_code, "is_stock_item"):
			avail = flt(frappe.db.get_value("Bin", {"item_code": i.item_code, "warehouse": i.warehouse}, "actual_qty"))
			if avail < rem:
				stock_short.append(_("{0}: {1} of {2} in stock").format(i.item_name, avail, rem))

	def st(done, cur=False, warn=False, info=None, tag=""):
		return {"state": "done" if done else "warn" if warn else "cur" if cur else "wait", "info": info or [], "tag": tag}

	approved = so.docstatus == 1
	stages = [
		st(True, info=[[_("Quotation"), quotation or _("Direct order — PO {0}").format(so.po_no or "—")]], tag=quotation and _("Converted") or _("Direct")),
		st(approved, cur=not approved, info=[[_("State"), wf or so.status]], tag=wf or (_("Approved") if approved else _("Draft"))),
		st(approved and not stock_short, warn=bool(stock_short) and approved, cur=approved, info=[[_("Stock"), x] for x in stock_short] or [[_("Stock"), _("Available")]], tag=_("Short") if stock_short else _("Ready")),
		st(bool(picks) or bool(dns), info=[[_("Pick list"), p.name + " · " + p.status] for p in picks], tag=_("Picked") if picks else ""),
		st(flt(so.per_delivered) >= 100, cur=0 < flt(so.per_delivered) < 100, info=[[d.name, f"{d.posting_date} · {d.driver_name or ''} {d.vehicle_no or ''}"] for d in dns], tag=f"{flt(so.per_delivered):.0f}%"),
		st(flt(so.per_billed) >= 100, cur=0 < flt(so.per_billed) < 100, info=[[i.name, _("due {0}").format(i.due_date)] for i in invs], tag=f"{flt(so.per_billed):.0f}%"),
		st(value and paid >= value - 0.01, warn=overdue > 0, cur=paid > 0, info=[[_("Paid"), frappe.format_value(paid, {"fieldtype": "Currency", "options": so.currency})], [_("Overdue"), frappe.format_value(overdue, {"fieldtype": "Currency", "options": so.currency})]], tag=_("Overdue") if overdue else ""),
	]
	if so.docstatus == 0:
		bucket = "Approval"
	elif overdue > 0:
		bucket = "Overdue"
	elif flt(so.per_delivered) < 100:
		bucket = "To deliver"
	elif flt(so.per_billed) < 100:
		bucket = "To invoice"
	elif paid < value - 0.01:
		bucket = "Awaiting payment"
	else:
		bucket = "Completed"
	return {
		"name": name, "customer": so.customer, "customer_name": so.customer_name, "po_no": so.po_no,
		"date": so.transaction_date, "delivery_date": so.delivery_date, "currency": so.currency,
		"value": value, "paid": paid, "remaining": max(0, value - paid), "overdue": overdue,
		"per_billed": flt(so.per_billed), "bucket": bucket, "export": so.hs_is_export,
		"stages": [dict(s, name=STAGES[k]) for k, s in enumerate(stages)],
		"invoices": [i.name for i in invs], "delivery_notes": [d.name for d in dns], "quotation": quotation,
	}
