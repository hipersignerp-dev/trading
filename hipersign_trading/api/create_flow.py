"""v1.7.0: the prototype's "from a document" modals — Pick & deliver (SO → delivery note), Receive goods (PO → purchase
receipt), Receive payment (invoice → receipt), Pay supplier (bill → payment) and Create invoice (delivery → tax invoice).

prepare(kind, source)  what the modal shows: header badges, the line table, the fields and their defaults
commit(kind, source, values, lines)  ERPNext's own mapper makes the document, the modal's values are applied, it is
                       saved and submitted the way the user would (approval workflow and document rules included)
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowtime, today

from hipersign_trading.api.quick import _submit
from hipersign_trading.utils import user_company

KINDS = {
	"deliver": ("Sales Order", "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note"),
	"receive": ("Purchase Order", "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt"),
	"receive_payment": ("Sales Invoice", None),
	"pay_supplier": ("Purchase Invoice", None),
	"invoice": ("Delivery Note", "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice"),
}
MAKE_TO_KIND = {
	"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note": "deliver",
	"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt": "receive",
	"hipersign_trading.api.panel.pay_sales_invoice": "receive_payment",
	"hipersign_trading.api.panel.pay_purchase_invoice": "pay_supplier",
	"erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice": "invoice",
}


def _warehouses(company):
	return frappe.get_all("Warehouse", filters={"company": company, "is_group": 0, "disabled": 0}, pluck="name", order_by="name asc")


def _free(item_code, warehouse):
	b = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, ["actual_qty", "reserved_stock"], as_dict=True)
	return flt(b.actual_qty) - flt(b.reserved_stock) if b else 0


def _banks(company, currency=None):
	rows = frappe.get_all("Account", filters={"company": company, "account_type": ["in", ["Bank", "Cash"]], "is_group": 0, "disabled": 0},
		fields=["name", "account_name", "account_currency", "account_type"], order_by="account_type asc, account_name asc")
	if currency:
		rows.sort(key=lambda r: (r.account_currency != currency, r.account_type != "Bank"))
	return [{"name": r.name, "label": f"{r.account_name} · {r.account_currency}"} for r in rows]


def _modes():
	return [m.name for m in frappe.get_all("Mode of Payment", filters={"enabled": 1}, order_by="name asc")]


@frappe.whitelist()
def kind_for(method):
	return MAKE_TO_KIND.get(method)


@frappe.whitelist()
def prepare(kind, source):
	if kind not in KINDS:
		frappe.throw(_("Unknown form"))
	sdt = KINDS[kind][0]
	doc = frappe.get_doc(sdt, source)
	doc.check_permission("read")
	return globals()["_prep_" + kind](doc)


def _prep_deliver(so):
	whs = _warehouses(so.company)
	lines = []
	for i, r in enumerate(so.items):
		pending = flt(r.stock_qty) - flt(r.delivered_qty) * flt(r.conversion_factor or 1)
		if pending <= 0:
			continue
		stock = frappe.get_cached_value("Item", r.item_code, "is_stock_item")
		free = {w: _free(r.item_code, w) for w in whs} if stock else {}
		best = r.warehouse if r.warehouse and free.get(r.warehouse, 0) > 0 else (max(free, key=free.get) if free else r.warehouse)
		lines.append({"i": i, "item_code": r.item_code, "item_name": r.item_name, "uom": r.uom, "ordered": flt(r.qty), "delivered": flt(r.delivered_qty),
			"pending": pending, "qty": min(pending, max(0, free.get(best, 0))) if stock else pending, "stock": stock,
			"warehouse": best, "options": [[w, f"{w} ({flt(free[w]):g} {_('free')})"] for w in whs] if stock else []})
	addrs = [{"name": a.parent, "label": frappe.db.get_value("Address", a.parent, "address_title") or a.parent}
		for a in frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": so.customer, "parenttype": "Address"}, fields=["parent"])]
	mobile = frappe.db.get_value("Contact", so.contact_person, "mobile_no") if so.contact_person else ""
	dn_status = frappe.get_meta("Delivery Note").get_field("hs_delivery_status")
	return {"title": _("Pick & deliver — {0}").format(so.name), "sub": _("Pick list and delivery note"),
		"badges": [[so.customer_name, "blue"], [_("Promised {0}").format(frappe.format(so.delivery_date, "Date")), "muted"]],
		"cols": [_("Item"), _("UOM"), _("Ordered"), _("Delivered"), _("Pending"), _("Qty now"), _("From warehouse (available)")],
		"lines": lines,
		"fields": [
			{"f": "posting_date", "label": _("Posting date"), "t": "date", "v": today()},
			{"f": "posting_time", "label": _("Posting time"), "t": "time", "v": nowtime()[:5]},
			{"f": "po_no", "label": _("Customer's PO no."), "v": so.po_no or ""},
			{"f": "po_date", "label": _("Customer's PO date"), "t": "date", "v": str(so.po_date or so.transaction_date)},
			{"f": "shipping_address_name", "label": _("Shipping address"), "t": "select", "list": addrs, "v": so.shipping_address_name or (addrs[0]["name"] if addrs else ""), "w": 2},
			{"f": "contact_person", "label": _("Site contact"), "v": frappe.db.get_value("Contact", so.contact_person, "full_name") if so.contact_person else "", "ro": 1},
			{"f": "contact_mobile", "label": _("Contact mobile"), "t": "tel", "v": mobile or ""},
			{"f": "print_without_amount", "label": _("Print"), "t": "select", "list": [["0", _("With amounts")], ["1", _("Without amounts (site copy)")]], "v": "0"},
			{"f": "hs_delivery_status", "label": _("Then"), "t": "select", "list": [["Ready to Dispatch", _("Leave ready to dispatch")], ["Out for Delivery", _("Out for delivery now")]] if dn_status else [], "v": "Ready to Dispatch"},
			{"f": "instructions", "label": _("Delivery instructions"), "t": "textarea", "w": 2, "ph": _("Gate, access hours, offloading, call before arrival")},
		],
		"note": _("Submitting the delivery note issues stock at the moving-average (landed) rate. Partial delivery is allowed."),
		"button": _("Create delivery note"), "icon": "truck"}


def _prep_receive(po):
	ship = None
	sh = frappe.get_all("Import Shipment PO", filters={"purchase_order": po.name, "parenttype": "Import Shipment"}, pluck="parent", limit=1) if frappe.db.table_exists("Import Shipment PO") else []
	if sh:
		ship = frappe.db.get_value("Import Shipment", sh[0], ["name", "status", "bl_awb"], as_dict=True)
	block = ship and ship.status not in ("Cleared", "Received at Warehouse")
	whs = _warehouses(po.company)
	lines = []
	for i, r in enumerate(po.items):
		out = flt(r.qty) - flt(r.received_qty)
		if out <= 0:
			continue
		lines.append({"i": i, "item_code": r.item_code, "item_name": r.item_name, "barcode": frappe.db.get_value("Item Barcode", {"parent": r.item_code}, "barcode") or "",
			"ordered": flt(r.qty), "received": flt(r.received_qty), "pending": out, "qty": out, "rejected": 0, "warehouse": r.warehouse or po.set_warehouse,
			"options": [[w, w] for w in whs], "stock": 1})
	sup = po.supplier_name
	return {"title": _("Receive goods — {0}").format(po.name), "sub": _("Scan, inspect and receive — the supplier invoice is drafted from the receipt"),
		"badges": [[po.name, "blue"], [f"{ship.name} · {_(ship.status)}" if ship else _("Local delivery"), "orange" if block else "grey"], [sup, "muted"]],
		"blocked": _("{0} is “{1}”. Goods can be received only after customs clearance.").format(ship.name, _(ship.status)) if block else None,
		"scan": 1, "cols": [_("Item"), _("Ordered"), _("Received"), _("Outstanding"), _("Accepted"), _("Rejected"), _("Warehouse")], "lines": lines,
		"fields": [
			{"f": "posting_date", "label": _("Receipt date"), "t": "date", "v": today()},
			{"f": "posting_time", "label": _("Posting time"), "t": "time", "v": nowtime()[:5]},
			{"f": "supplier_delivery_note", "label": _("Supplier's delivery note / invoice no."), "ph": _("From the supplier paperwork")},
			{"f": "lr_date", "label": _("Supplier's document date"), "t": "date", "v": today()},
			{"f": "transporter_name", "label": _("Transporter"), "v": ""},
			{"f": "lr_no", "label": _("Vehicle / container no."), "v": (ship.bl_awb if ship else "") or ""},
			{"f": "remarks", "label": _("Quality inspection / remarks"), "v": _("Visual check OK; cartons sealed"), "w": 2},
		],
		"note": _("Rejected units go to the rejected warehouse and are not billed. The supplier bill is made from the receipt (Create supplier bill)."),
		"button": _("Submit purchase receipt"), "icon": "check"}


def _prep_receive_payment(si):
	out = flt(si.outstanding_amount)
	return {"title": _("Receive payment — {0}").format(si.name), "sub": _("Allocated against the invoice"),
		"fields": [
			{"f": "customer", "label": _("Customer"), "v": si.customer_name, "ro": 1},
			{"f": "outstanding", "label": _("Outstanding"), "v": frappe.format(out, {"fieldtype": "Currency", "options": si.currency}), "ro": 1},
			{"f": "amount", "label": _("Amount credited by the bank ({0})").format(si.currency), "t": "number", "v": out},
			{"f": "date", "label": _("Date"), "t": "date", "v": today()},
			{"f": "mode_of_payment", "label": _("Mode"), "t": "select", "list": _modes(), "v": "Wire Transfer" if "Wire Transfer" in _modes() else (_modes() or [""])[0]},
			{"f": "paid_to", "label": _("Deposit to"), "t": "select", "list": _banks(si.company, si.currency)},
			{"f": "reference_no", "label": _("Bank reference / transaction no."), "ph": _("From the bank advice — can be added later"), "w": 2},
		],
		"note": _("Less than the outstanding leaves the invoice part paid; bank charges deducted can be booked on the full payment form."),
		"button": _("Record receipt"), "icon": "check"}


def _prep_pay_supplier(pi):
	out = flt(pi.outstanding_amount)
	iban = frappe.db.get_value("Bank Account", {"party_type": "Supplier", "party": pi.supplier}, "iban") or _("Not on file — add it on the supplier")
	return {"title": _("Pay supplier — {0}").format(pi.name), "sub": _("Payment approval workflow"),
		"fields": [
			{"f": "supplier", "label": _("Supplier"), "v": pi.supplier_name, "ro": 1},
			{"f": "invoice", "label": _("Invoice"), "v": " · ".join(x for x in [pi.name, pi.bill_no] if x), "ro": 1},
			{"f": "amount", "label": _("Amount ({0})").format(pi.currency), "t": "number", "v": out},
			{"f": "date", "label": _("Payment date"), "t": "date", "v": today()},
			{"f": "paid_from", "label": _("Pay from"), "t": "select", "list": _banks(pi.company, pi.currency), "w": 2},
			{"f": "mode_of_payment", "label": _("Payment mode"), "t": "select", "list": _modes(), "v": "Wire Transfer" if "Wire Transfer" in _modes() else (_modes() or [""])[0]},
			{"f": "reference_no", "label": _("Reference / transfer no."), "ph": _("Bank reference — can be added after payment")},
			{"f": "iban", "label": _("Payee bank / IBAN"), "v": iban, "ro": 1, "w": 2},
		],
		"note": _("Large payments wait for the Finance Manager before the bank balance changes."),
		"button": _("Submit payment"), "icon": "check"}


def _prep_invoice(dn):
	return {"title": _("Create invoice — {0}").format(dn.name), "sub": _("Tax invoice for what was delivered"),
		"badges": [[dn.customer_name, "blue"], [_("Delivered {0}").format(frappe.format(dn.posting_date, "Date")), "muted"]],
		"cols": [_("Item"), _("Qty"), _("Rate"), _("Amount")],
		"lines": [{"i": i, "item_code": r.item_code, "item_name": r.item_name, "qty": flt(r.qty), "rate": flt(r.rate), "amount": flt(r.amount), "ro": 1} for i, r in enumerate(dn.items)],
		"fields": [
			{"f": "posting_date", "label": _("Invoice date"), "t": "date", "v": today()},
			{"f": "due_date", "label": _("Due date"), "t": "date", "v": ""},
		],
		"note": _("Payment terms, VAT and the customer's TRN come from the order."), "button": _("Create tax invoice"), "icon": "check"}


# ---------------------------------------------------------------- commit
@frappe.whitelist(methods=["POST"])
def commit(kind, source, values=None, lines=None):
	values = frappe._dict(frappe.parse_json(values) if isinstance(values, str) else (values or {}))
	lines = frappe.parse_json(lines) if isinstance(lines, str) else (lines or [])
	if kind not in KINDS:
		frappe.throw(_("Unknown form"))
	return globals()["_commit_" + kind](source, values, lines)


def _finish(doc, verb):
	from hipersign_trading.doc_rules import DocumentNeeded

	doc.insert()
	frappe.db.savepoint("hs_flow_submit")
	try:
		doc = _submit(doc)
		state = doc.get("workflow_state") or (_("Submitted") if doc.docstatus == 1 else _("Draft"))
		return {"doctype": doc.doctype, "name": doc.name, "message": _("{0} {1} · {2}").format(_(doc.doctype), doc.name, _(state))}
	except DocumentNeeded as e:
		frappe.db.rollback(save_point="hs_flow_submit")
		frappe.local.message_log = []
		return {"doctype": doc.doctype, "name": doc.name, "needs_documents": frappe.utils.strip_html(str(e)),
			"message": _("{0} {1} saved as a draft — attach the document needed, then submit").format(_(doc.doctype), doc.name)}


def _commit_deliver(source, v, lines):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	dn = make_delivery_note(source)
	want = {int(r["i"]): r for r in lines}
	so_rows = frappe.get_all("Sales Order Item", filters={"parent": source}, fields=["name", "idx"], order_by="idx asc")
	idx_of = {r.name: r.idx - 1 for r in so_rows}
	keep = []
	for row in dn.items:
		r = want.get(idx_of.get(row.so_detail))
		if not r or flt(r.get("qty")) <= 0:
			continue
		row.qty = flt(r["qty"])
		if r.get("warehouse"):
			row.warehouse = r["warehouse"]
		keep.append(row)
	if not keep:
		frappe.throw(_("Enter a quantity to deliver on at least one line"))
	dn.set("items", keep)
	for f in ("posting_date", "posting_time", "po_no", "po_date", "shipping_address_name", "hs_delivery_status"):
		if v.get(f) and dn.meta.has_field(f):
			dn.set(f, v[f])
	if v.get("posting_date") and getdate(v.posting_date) != getdate(today()):
		dn.set_posting_time = 1
	dn.print_without_amount = 1 if str(v.get("print_without_amount")) == "1" else 0
	if v.get("instructions"):
		dn.instructions = v.instructions
	dn.run_method("set_missing_values")
	dn.calculate_taxes_and_totals()
	return _finish(dn, "deliver")


def _commit_receive(source, v, lines):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	pr = make_purchase_receipt(source)
	want = {int(r["i"]): r for r in lines}
	po_rows = frappe.get_all("Purchase Order Item", filters={"parent": source}, fields=["name", "idx"], order_by="idx asc")
	idx_of = {r.name: r.idx - 1 for r in po_rows}
	keep = []
	rej_wh = frappe.db.get_value("Warehouse", {"company": pr.company, "is_rejected_warehouse": 1}, "name") if frappe.get_meta("Warehouse").has_field("is_rejected_warehouse") else None
	rej_wh = rej_wh or frappe.db.get_value("Warehouse", {"company": pr.company, "warehouse_name": ["like", "%Reject%"]}, "name")
	for row in pr.items:
		r = want.get(idx_of.get(row.purchase_order_item))
		if not r:
			continue
		acc, rej = flt(r.get("qty")), flt(r.get("rejected"))
		if acc + rej <= 0:
			continue
		row.qty, row.rejected_qty, row.received_qty = acc, rej, acc + rej
		if r.get("warehouse"):
			row.warehouse = r["warehouse"]
		if rej and rej_wh:
			row.rejected_warehouse = rej_wh
		keep.append(row)
	if not keep:
		frappe.throw(_("Enter an accepted or rejected quantity on at least one line"))
	pr.set("items", keep)
	for f in ("posting_date", "posting_time", "supplier_delivery_note", "lr_no", "lr_date", "transporter_name", "remarks"):
		if v.get(f) and pr.meta.has_field(f):
			pr.set(f, v[f])
	if v.get("posting_date") and getdate(v.posting_date) != getdate(today()):
		pr.set_posting_time = 1
	pr.run_method("set_missing_values")
	pr.calculate_taxes_and_totals()
	return _finish(pr, "receive")


def _pe(source_dt, source, v, to_field):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	amt = flt(v.get("amount"))
	if amt <= 0:
		frappe.throw(_("Enter the amount"))
	pe = get_payment_entry(source_dt, source, party_amount=amt)
	if v.get("date"):
		pe.posting_date = v.date
	if v.get("mode_of_payment"):
		pe.mode_of_payment = v.mode_of_payment
	if v.get(to_field):
		pe.set(to_field, v[to_field])
		pe.set(to_field + "_account_currency", frappe.get_cached_value("Account", v[to_field], "account_currency"))
	pe.reference_no = v.get("reference_no") or _("To be added")
	pe.reference_date = v.get("date") or today()
	if pe.references:
		pe.references[0].allocated_amount = min(amt, flt(pe.references[0].outstanding_amount))
	pe.paid_amount = amt
	pe.received_amount = amt if pe.paid_from_account_currency == pe.paid_to_account_currency else pe.received_amount
	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.set_exchange_rate()
	pe.set_amounts()
	return _finish(pe, "pay")


def _commit_receive_payment(source, v, lines):
	return _pe("Sales Invoice", source, v, "paid_to")


def _commit_pay_supplier(source, v, lines):
	return _pe("Purchase Invoice", source, v, "paid_from")


def _commit_invoice(source, v, lines):
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	si = make_sales_invoice(source)
	if v.get("posting_date"):
		si.posting_date = v.posting_date
		si.set_posting_time = 1
	if v.get("due_date"):
		si.due_date = v.due_date
		si.payment_schedule = []
	si.run_method("set_missing_values")
	si.calculate_taxes_and_totals()
	return _finish(si, "invoice")
