"""Form modes — Quick, Standard, Detailed — and the Quick dialogs.

Which mode a New document opens in: the user's own last choice → a row in Hipersign Settings
for one of the user's roles → a row for everyone → the pack (Starter Quick, Standard Standard,
Enterprise Detailed). Quick documents are created through the normal document engine
(insert / workflow / submit), so price lists, credit limit, KYC, margin, approval and document
rules all apply exactly as on the full form.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, today

from hipersign_trading.utils import settings

COVERED = ["Quotation", "Sales Order", "Purchase Order", "Sales Invoice", "Payment Entry", "Customer", "Item", "Lead"]
PACK_MODE = {"Starter": "Quick", "Standard": "Standard", "Enterprise": "Detailed"}
MODES = ("Quick", "Standard", "Detailed")


def _key(doctype):
	return "hs_fm::" + doctype


def pack_mode():
	from hipersign_trading.features import pack_of

	s = settings()
	pk = s.get("feature_pack") if s.get("feature_pack") in PACK_MODE else pack_of(s)
	return PACK_MODE.get(pk, "Detailed")


def mode_for(doctype, user=None):
	user = user or frappe.session.user
	own = frappe.defaults.get_user_default(_key(doctype), user=user)
	if own in MODES:
		return own
	rows = settings().get("form_modes") or []
	roles = set(frappe.get_roles(user))
	for r in rows:
		if r.document_type == doctype and r.role and r.role in roles:
			return r.mode
	for r in rows:
		if r.document_type == doctype and not r.role:
			return r.mode
	return pack_mode()


@frappe.whitelist()
def form_modes():
	return {dt: mode_for(dt) for dt in COVERED}


@frappe.whitelist()
def set_form_mode(doctype, mode):
	if doctype not in COVERED or mode not in MODES:
		frappe.throw(_("Unknown form mode"))
	frappe.defaults.set_user_default(_key(doctype), mode)
	return mode


@frappe.whitelist()
def clear_form_modes():
	frappe.only_for("System Manager")
	n = 0
	for dt in COVERED:
		for d in frappe.get_all("DefaultValue", filters={"defkey": _key(dt)}, pluck="name"):
			frappe.delete_doc("DefaultValue", d, ignore_permissions=True)
			n += 1
	frappe.clear_cache()
	return n


# ---------------------------------------------------------------- Quick quotation / order / purchase order
def _rate_preview(doctype, party, item_code):
	if doctype == "Purchase Order":
		pl = (party and frappe.db.get_value("Supplier", party, "default_price_list")) or frappe.db.get_single_value("Buying Settings", "buying_price_list")
	else:
		pl = (party and frappe.db.get_value("Customer", party, "default_price_list")) or frappe.db.get_single_value("Selling Settings", "selling_price_list")
	r = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": pl}, "price_list_rate") if pl else None
	if r is None:
		r = frappe.db.get_value("Item", item_code, "standard_rate" if doctype != "Purchase Order" else "last_purchase_rate")
	return flt(r), pl, r is not None


@frappe.whitelist()
def find_items(doctype, txt, party=None):
	"""Smart line entry: “200 cam” → items matching cam, with the price the document will use."""
	words = [w for w in (txt or "").lower().split() if w]
	if not words:
		return []
	item = frappe.qb.DocType("Item")
	q = frappe.qb.from_(item).select(item.name, item.item_name, item.stock_uom, item.is_stock_item).where(item.disabled == 0).where(item.has_variants == 0)
	q = q.where(item.is_purchase_item == 1) if doctype == "Purchase Order" else q.where(item.is_sales_item == 1)
	for w in words:
		q = q.where((item.name.like(f"%{w}%")) | (item.item_name.like(f"%{w}%")) | (item.item_group.like(f"%{w}%")))
	out = []
	for code, name, uom, stock in q.limit(8).run():
		rate, pl, listed = _rate_preview(doctype, party, code)
		qty = flt(frappe.db.sql("select sum(actual_qty) from tabBin where item_code=%s", code)[0][0]) if stock else None
		out.append({"item_code": code, "item_name": name, "uom": uom, "rate": rate, "price_list": pl, "listed": listed, "stock": qty})
	return out


@frappe.whitelist()
def last_order(customer):
	so = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": 1}, fields=["name", "transaction_date"], order_by="transaction_date desc, creation desc", limit=1)
	if not so:
		return None
	items = frappe.get_all("Sales Order Item", filters={"parent": so[0].name}, fields=["item_code", "item_name", "qty"], order_by="idx asc")
	return {"name": so[0].name, "date": so[0].transaction_date, "items": items}


def _submit(doc):
	"""Submit the way the user would: through the approval workflow when one is active."""
	from frappe.model.workflow import apply_workflow, get_transitions, get_workflow_name

	if get_workflow_name(doc.doctype):
		acts = [t.action for t in get_transitions(doc)]
		for a in ("Submit", "Submit for Approval"):
			if a in acts:
				doc = apply_workflow(doc, a)
				return doc
		return doc
	doc.submit()
	return doc


@frappe.whitelist()
def quick_create(doctype, data, action="save"):
	"""Create a quotation, sales order or purchase order from the Quick dialog."""
	if doctype not in ("Quotation", "Sales Order", "Purchase Order"):
		frappe.throw(_("Quick entry is not available for {0}").format(doctype))
	data = frappe.parse_json(data) if isinstance(data, str) else frappe._dict(data or {})
	lines = [r for r in (data.get("items") or []) if r.get("item_code") and flt(r.get("qty")) > 0]
	if not data.get("party"):
		frappe.throw(_("Choose the {0}").format(_("supplier") if doctype == "Purchase Order" else _("customer")))
	if not lines:
		frappe.throw(_("Add at least one item with a quantity"))
	company = data.get("company") or settings().get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
	doc = frappe.new_doc(doctype)
	doc.company = company
	need = add_days(today(), 3 if doctype == "Sales Order" else 30)
	if doctype == "Quotation":
		doc.quotation_to, doc.party_name = "Customer", data.party
		doc.valid_till = add_days(today(), 14)
		if data.get("lead"):
			doc.quotation_to, doc.party_name = "Lead", data.lead
	elif doctype == "Sales Order":
		doc.customer = data.party
		doc.delivery_date = need
		doc.po_no = data.get("po_no") or None
	else:
		doc.supplier = data.party
		doc.schedule_date = need
	for r in lines:
		row = {"item_code": r["item_code"], "qty": flt(r["qty"])}
		if doctype == "Sales Order":
			row["delivery_date"] = need
		if doctype == "Purchase Order":
			row["schedule_date"] = need
		doc.append("items", row)
	doc.flags.hs_quick = True
	doc.set_missing_values()
	doc.insert()
	msg = _("{0} {1} created").format(_(doctype), doc.name)
	needs = None
	if action == "submit" and doctype in ("Sales Order", "Purchase Order"):
		from hipersign_trading.doc_rules import DocumentNeeded

		frappe.db.savepoint("hs_quick_submit")
		try:
			doc = _submit(doc)
			state = doc.get("workflow_state") or (_("Submitted") if doc.docstatus == 1 else _("Draft"))
			msg = _("{0} {1} · {2}").format(_(doctype), doc.name, _(state))
		except DocumentNeeded as e:
			# keep the draft: the user attaches the document (or asks for an exception) on the form and submits there
			frappe.db.rollback(save_point="hs_quick_submit")
			frappe.local.message_log = []
			needs = frappe.utils.strip_html(str(e))
			msg = _("{0} {1} saved as a draft — attach the document needed, then submit").format(_(doctype), doc.name)
	return {"name": doc.name, "message": msg, "grand_total": doc.grand_total, "currency": doc.currency, "needs_documents": needs}


# ---------------------------------------------------------------- Quick invoice
@frappe.whitelist()
def to_bill(company=None):
	dn = frappe.qb.DocType("Delivery Note")
	q = (frappe.qb.from_(dn).select(dn.name, dn.customer, dn.customer_name, dn.posting_date, dn.base_grand_total, dn.currency)
		.where(dn.docstatus == 1).where(dn.is_return == 0).where(dn.per_billed < 100).orderby(dn.posting_date))
	if company:
		q = q.where(dn.company == company)
	rows = [dict(name=r[0], customer=r[1], customer_name=r[2], date=r[3], amount=r[4], currency=r[5]) for r in q.limit(200).run()]
	return [r for r in rows if _billable(r["name"])][:100]


def _billable(delivery_note):
	"""Something on the note is still to bill — not already invoiced from its sales order."""
	return bool(frappe.db.sql("""select 1 from `tabDelivery Note Item` dni
		left join `tabSales Order Item` soi on soi.name = dni.so_detail
		where dni.parent = %s and (dni.so_detail is null or dni.so_detail = '' or soi.billed_amt < soi.amount - 0.01)
		and dni.amount > ifnull((select sum(sii.amount) from `tabSales Invoice Item` sii where sii.dn_detail = dni.name and sii.docstatus = 1), 0) + 0.01
		limit 1""", delivery_note))


@frappe.whitelist()
def quick_invoice(delivery_note):
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	frappe.get_doc("Delivery Note", delivery_note).check_permission("read")
	si = make_sales_invoice(delivery_note)
	si.insert()
	si.submit()
	return {"name": si.name, "message": _("Sales Invoice {0} · {1}").format(si.name, frappe.format(si.grand_total, {"fieldtype": "Currency", "options": si.currency}))}


# ---------------------------------------------------------------- Quick receive payment
@frappe.whitelist()
def open_invoices(customer, company=None):
	f = {"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]}
	if company:
		f["company"] = company
	return frappe.get_all("Sales Invoice", filters=f, fields=["name", "due_date", "posting_date", "outstanding_amount", "currency", "grand_total"],
		order_by="due_date asc, posting_date asc, name asc")


@frappe.whitelist()
def quick_receive(customer, amount, mode_of_payment=None, reference_no=None, company=None):
	"""One Payment Entry, applied to the customer's oldest invoices first."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter the amount received"))
	invs = open_invoices(customer, company)
	out = sum(flt(i.outstanding_amount) for i in invs)
	if amount > out + 0.005:
		frappe.throw(_("{0} is more than the {1} the customer owes — record the extra as an advance on a full Payment Entry.").format(
			frappe.format(amount, "Currency"), frappe.format(out, "Currency")))
	if not invs:
		frappe.throw(_("The customer has no open invoices."))
	pe = get_payment_entry("Sales Invoice", invs[0].name, party_amount=amount)
	pe.set("references", [])
	left = amount
	for i in invs:
		if left <= 0.005:
			break
		a = min(left, flt(i.outstanding_amount))
		pe.append("references", {"reference_doctype": "Sales Invoice", "reference_name": i.name, "total_amount": i.grand_total,
			"outstanding_amount": i.outstanding_amount, "allocated_amount": a, "due_date": i.due_date})
		left -= a
	pe.paid_amount = pe.received_amount = amount
	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment
		acc = frappe.db.get_value("Mode of Payment Account", {"parent": mode_of_payment, "company": pe.company}, "default_account")
		if acc:
			pe.paid_to = acc
	pe.reference_no = reference_no or _("Quick receipt")
	pe.reference_date = today()
	pe.insert()
	pe = _submit(pe)
	return {"name": pe.name, "message": _("Payment {0} · {1} invoice(s)").format(pe.name, len(pe.references))}
