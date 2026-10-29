"""v1.6.0: the Live deal demo — plays one deal end to end on a demo site.

lead → quotation → sales order → purchase order → letter of credit → import shipment → customs → goods receipt →
landed cost → advance → delivery → tax invoice → cheque. Each step creates (and submits) the real ERPNext record, so
the figures on Home, the reports and the ledgers move. Steps whose feature is switched off are skipped (a Starter site
plays the local part only). Reset cancels and deletes, newest first, only the records this run made.

Only on demo sites (site config hipersign_demo_site) with "Live deal demo" ticked in Hipersign Settings, and only for
a System Manager — it posts real accounting entries.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate, random_string, today

KEY = "hs_deal_run"
STEPS = [
	("lead", "Lead", None), ("quote", "Quotation", None), ("order", "Sales order", None), ("po", "Purchase order", None),
	("lc", "Letter of credit", "lc"), ("shipment", "Import shipment", "imports"), ("customs", "Customs clearance", "imports"),
	("receipt", "Goods receipt", None), ("landed", "Landed cost", "imports"), ("advance", "Advance received", "advances"),
	("delivery", "Delivery note", None), ("invoice", "Tax invoice", None), ("cheque", "Cheque received", "pdc"),
]
QTY = 20


def enabled():
	if not frappe.conf.get("hipersign_demo_site"):
		return False
	try:
		return bool(frappe.get_cached_doc("Hipersign Settings").get("deal_demo"))
	except Exception:
		return False


def _guard():
	if not enabled():
		frappe.throw(_("The Live deal demo is only available on a demo site, switched on in Hipersign Settings."))
	frappe.only_for("System Manager")


def _steps():
	from hipersign_trading.features import feature_on

	return [s for s in STEPS if not s[2] or feature_on(s[2])]


def _state():
	raw = frappe.db.get_default(KEY)
	return json.loads(raw) if raw else None


def _save(st):
	frappe.db.set_default(KEY, json.dumps(st, default=str) if st else "")


def _company():
	from hipersign_trading.api.quick_cards import _company as qc_company

	return qc_company()


def _attach_docs(doc):
	"""Attach a demo copy of every document the record's rules ask for (bill of entry, delivery proof …)."""
	from hipersign_trading.doc_rules import checklist

	for r in checklist(doc):
		if r["attached"] or r["level"] == "Optional":
			continue
		f = frappe.get_doc({"doctype": "File", "file_name": f"{r['document_type']} — {doc.name}.txt".replace("/", "-"), "attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name, "is_private": 1, "content": f"Live deal demo — {r['document_type']} for {doc.doctype} {doc.name}"})
		if f.meta.has_field("hs_document_type"):
			f.hs_document_type = r["document_type"]
		f.insert(ignore_permissions=True)


def _with_docs(doc, action):
	"""Run save / submit / insert; when a document rule asks for a document, attach the demo copy and run it again."""
	from hipersign_trading.doc_rules import DocumentNeeded

	try:
		return action()
	except DocumentNeeded:
		frappe.clear_last_message()
		if doc.is_new():
			frappe.flags.hs_skip_doc_rules = True
			try:
				out = action()
			finally:
				frappe.flags.hs_skip_doc_rules = False
			_attach_docs(doc)
			return out
		_attach_docs(doc)
		# attaching touches the record; carry on from its current version
		doc.modified = frappe.db.get_value(doc.doctype, doc.name, "modified")
		return action()


def _finish(doc):
	"""Submit the record, going through its approval workflow when it has one (the demo administrator approves)."""
	from frappe.model.workflow import apply_workflow, get_transitions, get_workflow_name

	if doc.docstatus == 1:
		return doc
	wf = get_workflow_name(doc.doctype)
	n = 0
	while wf and doc.docstatus == 0 and n < 6:
		n += 1
		trans = get_transitions(doc)
		if not trans:
			break
		pick = next((t for t in trans if "reject" not in t.action.lower() and ("approve" in t.action.lower() or "submit" in t.action.lower())), None) \
			or next((t for t in trans if "reject" not in t.action.lower()), None)
		if not pick:
			break
		doc = _with_docs(doc, lambda d=doc, a=pick.action: apply_workflow(d, a))
		doc = frappe.get_doc(doc.doctype, doc.name) if not hasattr(doc, "docstatus") else doc
		doc.reload()
	if doc.docstatus == 0 and doc.meta.is_submittable:
		_with_docs(doc, doc.submit)
	return doc


def _pick(st):
	"""The deal's parties and item, from the demo data."""
	company = _company()
	item = "ITM-001" if frappe.db.exists("Item", "ITM-001") else frappe.db.get_value("Item", {"is_stock_item": 1, "disabled": 0, "is_sales_item": 1, "has_serial_no": 0})
	supplier = "Global Supplies Co. Ltd" if frappe.db.exists("Supplier", "Global Supplies Co. Ltd") else frappe.db.get_value("Supplier", {"disabled": 0})
	wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "warehouse_name": "Main Warehouse"}) or frappe.db.get_value("Warehouse", {"company": company, "is_group": 0})
	sell = flt(frappe.db.get_value("Item Price", {"item_code": item, "price_list": "Standard Selling"}, "price_list_rate")) or 1000
	cost = flt(frappe.db.get_value("Item Price", {"item_code": item, "price_list": "Standard Buying"}, "price_list_rate")) or flt(frappe.db.get_value("Item", item, "valuation_rate")) or sell * 0.7
	st["ctx"].update({"company": company, "item": item, "supplier": supplier, "warehouse": wh, "sell": sell, "cost": cost,
		"customer_name": f"Oasis Hospitality Group {st['run'][-4:].upper()}"})


def _ref(st, key):
	return next((d for d in st["done"] if d["key"] == key), None)


# ---------------------------------------------------------------- the steps
def s_lead(st, c):
	d = frappe.get_doc({"doctype": "Lead", "company_name": c["customer_name"], "first_name": "Rania", "last_name": "Saeed", "mobile_no": "+971 50 555 " + str(abs(hash(st["run"])) % 9000 + 1000),
		"hs_interested_in": _("{0} × {1} for a hotel refurbishment").format(QTY, frappe.db.get_value("Item", c["item"], "item_name")),
		"hs_estimated_value": QTY * c["sell"], "hs_pipeline_stage": "Qualified", "country": "United Arab Emirates", "company": c["company"]})
	if d.meta.has_field("hs_emirate"):
		d.hs_emirate = "Dubai"
	d.insert()
	return d, _("Lead captured from a referral and qualified")


def s_quote(st, c):
	from erpnext.crm.doctype.lead.lead import make_quotation

	q = make_quotation(_ref(st, "lead")["name"])
	q.company = c["company"]
	q.valid_till = add_days(today(), 15)
	q.items = []
	q.append("items", {"item_code": c["item"], "qty": QTY, "rate": c["sell"]})
	_with_docs(q, q.insert)
	q = _finish(q)
	return q, _("Quotation sent and accepted")


def s_order(st, c):
	from erpnext.selling.doctype.quotation.quotation import make_sales_order

	so = make_sales_order(_ref(st, "quote")["name"])
	so.delivery_date = add_days(today(), 10)
	so.set_warehouse = c["warehouse"]
	for it in so.items:
		it.delivery_date = so.delivery_date
		it.warehouse = c["warehouse"]
	so.po_no = f"OHG/PO/{st['run'][-4:].upper()}"
	_with_docs(so, so.insert)
	c["customer"] = so.customer
	so = _finish(so)
	return so, _("Customer created from the lead; order approved and stock reserved")


def s_po(st, c):
	cur = frappe.db.get_value("Supplier", c["supplier"], "default_currency") or frappe.get_cached_value("Company", c["company"], "default_currency")
	from erpnext.setup.utils import get_exchange_rate

	co_cur = frappe.get_cached_value("Company", c["company"], "default_currency")
	rate = 1 if cur == co_cur else flt(get_exchange_rate(cur, co_cur, today())) or 1
	po = frappe.get_doc({"doctype": "Purchase Order", "supplier": c["supplier"], "company": c["company"], "currency": cur, "conversion_rate": rate,
		"schedule_date": add_days(today(), 7), "set_warehouse": c["warehouse"], "ignore_pricing_rule": 1,
		"items": [{"item_code": c["item"], "qty": QTY, "rate": flt(c["cost"] / rate, 2), "schedule_date": add_days(today(), 7), "warehouse": c["warehouse"]}]})
	if po.meta.has_field("incoterm") and frappe.db.exists("Incoterm", "FOB"):
		po.incoterm = "FOB"
	_with_docs(po, po.insert)
	po = _finish(po)
	c["po_currency"], c["po_rate"] = cur, rate
	return po, _("Purchase order placed with the supplier")


def s_lc(st, c):
	po = frappe.get_doc("Purchase Order", _ref(st, "po")["name"])
	bank = frappe.db.get_value("Bank", {}) or "Emirates NBD"
	lc = frappe.get_doc({"doctype": "Letter of Credit", "lc_type": "Import", "supplier": po.supplier, "purchase_order": po.name, "company": po.company,
		"issuing_bank": bank, "lc_number": f"LIVE-ILC-{st['run'][-4:].upper()}", "currency": po.currency, "amount": po.grand_total,
		"exchange_rate": po.conversion_rate, "margin_pct": 10, "issue_date": today(), "latest_shipment_date": add_days(today(), 20),
		"expiry_date": add_days(today(), 45), "tenor": "At sight", "status": "Issued"})
	_with_docs(lc, lc.insert)
	return lc, _("Letter of credit issued by the bank")


def s_shipment(st, c):
	po = _ref(st, "po")["name"]
	shp = frappe.get_doc({"doctype": "Import Shipment", "company": c["company"], "mode": "Sea", "bl_awb": f"LIVE-{st['run'][-6:].upper()}",
		"vessel_flight": "MSC Aurora V.702", "port_of_loading": "Yantian, Shenzhen", "port_of_discharge": "Jebel Ali", "etd": today(),
		"eta": add_days(today(), 1), "status": "Booked", "purchase_orders": [{"purchase_order": po}]})
	_with_docs(shp, shp.insert)
	base = flt(frappe.db.get_value("Purchase Order", po, "base_grand_total"))
	for typ, amt in (("Freight & Shipping", round(base * 0.04, 2)), ("Customs Duty", round(base * 0.05, 2)), ("Clearing Charges", 450)):
		row = {"charge_type": typ, "amount": amt, "date": today()}
		shp.append("charges", row)
	shp.status = "In Transit"
	_with_docs(shp, shp.save)
	lc = _ref(st, "lc")
	if lc:
		frappe.db.set_value("Letter of Credit", lc["name"], "import_shipment", shp.name)
	return shp, _("Goods shipped — bill of lading and freight recorded")


def s_customs(st, c):
	shp = frappe.get_doc("Import Shipment", _ref(st, "shipment")["name"])
	for d in shp.get("documents") or []:
		d.received = 1
	shp.bill_of_entry = f"101-2026-{st['run'][-6:].upper()}"
	shp.arrived_on = today()
	shp.cleared_on = today()
	shp.status = "Cleared"
	_with_docs(shp, shp.save)
	return shp, _("Arrived at Jebel Ali and cleared by customs (duty paid)")


def s_receipt(st, c):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	pr = make_purchase_receipt(_ref(st, "po")["name"])
	if _ref(st, "shipment") and pr.meta.has_field("hs_import_shipment"):
		pr.hs_import_shipment = _ref(st, "shipment")["name"]
	_with_docs(pr, pr.insert)
	_with_docs(pr, pr.submit)
	return pr, _("Goods received into the warehouse")


def s_landed(st, c):
	shp = frappe.get_doc("Import Shipment", _ref(st, "shipment")["name"])
	lcv = frappe.get_doc("Landed Cost Voucher", shp.make_landed_cost_voucher())
	lcv.posting_date = today()
	lcv.save()
	_with_docs(lcv, lcv.submit)
	return lcv, _("Freight, duty and clearing spread over the goods — the landed cost")


def s_advance(st, c):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	so = frappe.get_doc("Sales Order", _ref(st, "order")["name"])
	amt = flt(so.grand_total * 0.3, 2)
	pe = get_payment_entry("Sales Order", so.name, party_amount=amt)
	pe.reference_no = f"TT-{st['run'][-6:].upper()}"
	pe.reference_date = today()
	_with_docs(pe, pe.insert)
	_with_docs(pe, pe.submit)
	return pe, _("30% advance received by bank transfer")


def s_delivery(st, c):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	dn = make_delivery_note(_ref(st, "order")["name"])
	for it in dn.items:
		it.warehouse = it.warehouse or c["warehouse"]
	_with_docs(dn, dn.insert)
	dn = _finish(dn)
	return dn, _("Delivered to the customer's site")


def s_invoice(st, c):
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	si = make_sales_invoice(_ref(st, "delivery")["name"])
	si.allocate_advances_automatically = 1
	_with_docs(si, si.insert)
	si = _finish(si)
	return si, _("Tax invoice issued; the advance is set against it")


def s_cheque(st, c):
	si = frappe.get_doc("Sales Invoice", _ref(st, "invoice")["name"])
	amt = flt(si.outstanding_amount)
	if amt <= 0:
		amt = flt(si.grand_total) * 0.7
	p = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Received", "party_type": "Customer", "party": si.customer, "company": si.company,
		"cheque_no": st["run"][-6:].upper(), "cheque_date": add_days(today(), 30), "amount": flt(amt, 2), "drawn_on": "Emirates NBD",
		"received_on": today(), "reference_doctype": "Sales Invoice", "reference_name": si.name, "status": "In Hand"})
	_with_docs(p, p.insert)
	return p, _("Post-dated cheque received for the balance")


RUNNERS = {k: globals()["s_" + k] for k, _l, _f in STEPS}


# ---------------------------------------------------------------- API
@frappe.whitelist()
def get_state():
	if not enabled():
		return {"enabled": False}
	st = _state()
	steps = _steps()
	return {"enabled": True, "steps": [{"key": k, "label": _(l)} for k, l, _f in steps], "run": st, "summary": _summary(st) if st and len(st["done"]) >= len(steps) else None}


@frappe.whitelist(methods=["POST"])
def play_next():
	_guard()
	st = _state()
	if not st:
		st = {"run": "D" + random_string(6), "done": [], "ctx": {}, "started": nowdate()}
		_pick(st)
	steps = _steps()
	done = {d["key"] for d in st["done"]}
	nxt = next((s for s in steps if s[0] not in done), None)
	if not nxt:
		return get_state()
	key, label, _f = nxt
	if key == "customs" and not _ref(st, "shipment"):
		st["done"].append({"key": key, "label": _(label), "skipped": 1})
		_save(st)
		return play_next()
	doc, msg = RUNNERS[key](st, st["ctx"])
	st["done"].append({"key": key, "label": _(label), "doctype": doc.doctype, "name": doc.name, "message": msg})
	_save(st)
	frappe.db.commit()
	out = get_state()
	out["last"] = st["done"][-1]
	return out


@frappe.whitelist(methods=["POST"])
def reset():
	"""Cancel and delete what this run made, newest first, then the customer the order created."""
	_guard()
	st = _state()
	if not st:
		return get_state()
	seen = set()
	for d in reversed(st["done"]):
		if not d.get("name") or (d["doctype"], d["name"]) in seen:
			continue
		seen.add((d["doctype"], d["name"]))
		_remove(d["doctype"], d["name"])
	cust = st["ctx"].get("customer")
	if cust and frappe.db.exists("Customer", cust):
		for dt in ("Contact", "Address"):
			for n in frappe.get_all("Dynamic Link", filters={"parenttype": dt, "link_doctype": "Customer", "link_name": cust}, pluck="parent"):
				frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
		frappe.delete_doc("Customer", cust, force=1, ignore_permissions=True)
	_save(None)
	frappe.db.commit()
	return get_state()


def _remove(doctype, name):
	if not frappe.db.exists(doctype, name):
		return
	doc = frappe.get_doc(doctype, name)
	if doctype == "Post Dated Cheque":
		for f in ("receipt_entry", "clearing_entry", "reversal_entry", "charges_entry"):
			je = doc.get(f)
			if je and frappe.db.exists("Journal Entry", je):
				doc.db_set(f, None)
				_remove("Journal Entry", je)
	if doctype == "Letter of Credit":
		for f in ("margin_entry", "tr_entry", "margin_release_entry"):
			je = doc.get(f)
			if je and frappe.db.exists("Journal Entry", je):
				doc.db_set(f, None)
				_remove("Journal Entry", je)
	if doc.docstatus == 1:
		doc.flags.ignore_links = True
		doc.cancel()
	frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)


def _summary(st):
	inv = _ref(st, "invoice")
	dn = _ref(st, "delivery")
	if not inv:
		return None
	si = frappe.db.get_value("Sales Invoice", inv["name"], ["base_net_total", "currency", "outstanding_amount"], as_dict=True)
	cogs = -flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no=%s and is_cancelled=0", dn["name"])[0][0]) if dn else 0
	adv = _ref(st, "advance")
	chq = _ref(st, "cheque")
	cash = (flt(frappe.db.get_value("Payment Entry", adv["name"], "base_received_amount")) if adv else 0) + (flt(frappe.db.get_value("Post Dated Cheque", chq["name"], "amount")) if chq else 0)
	cur = frappe.get_cached_value("Company", st["ctx"]["company"], "default_currency")
	return {"revenue": flt(si.base_net_total), "landed_cost": cogs, "profit": flt(si.base_net_total) - cogs,
		"margin": round((flt(si.base_net_total) - cogs) / flt(si.base_net_total) * 100, 1) if si.base_net_total else 0, "cash": cash, "currency": cur}
