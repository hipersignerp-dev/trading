"""v1.7.3: supplier quotations compared side by side, as on the prototype (RFQ → quotes per supplier → award per item → POs).
Replaces the link to ERPNext's Supplier Quotation Comparison report, which runs as a background "prepared report"."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def _aed(amount, currency, company):
	base = frappe.get_cached_value("Company", company, "default_currency")
	if not currency or currency == base:
		return flt(amount)
	from erpnext.setup.utils import get_exchange_rate

	return flt(amount) * flt(get_exchange_rate(currency, base, today()) or 1)


@frappe.whitelist()
def open_rfqs():
	"""RFQs with at least one supplier quotation — the page's start list."""
	if not frappe.has_permission("Supplier Quotation", "read"):
		return []
	rows = frappe.db.sql("""select sqi.request_for_quotation rfq, count(distinct sq.name) quotes, max(sq.transaction_date) last
		from `tabSupplier Quotation Item` sqi join `tabSupplier Quotation` sq on sq.name = sqi.parent
		where sq.docstatus < 2 and ifnull(sqi.request_for_quotation, '') != '' group by sqi.request_for_quotation order by last desc limit 50""", as_dict=True)
	for r in rows:
		r.update(frappe.db.get_value("Request for Quotation", r.rfq, ["transaction_date", "status", "company", "docstatus"], as_dict=True) or {})
		r["suppliers"] = len(frappe.get_all("Request for Quotation Supplier", filters={"parent": r.rfq}))
		r["ordered"] = bool(frappe.db.exists("Purchase Order Item", {"supplier_quotation": ["in", frappe.get_all("Supplier Quotation Item", filters={"request_for_quotation": r.rfq}, pluck="parent") or [""]], "docstatus": ["<", 2]}))
	return rows


@frappe.whitelist()
def rfq_compare(rfq):
	"""Items × suppliers: unit price in the supplier's currency and in the company currency, lead time, terms; the best price marked."""
	doc = frappe.get_doc("Request for Quotation", rfq)
	doc.check_permission("read")
	company = doc.company
	base = frappe.get_cached_value("Company", company, "default_currency")
	meta = frappe.get_meta("Supplier Quotation")
	fields = ["name", "supplier", "supplier_name", "currency", "valid_till", "transaction_date", "docstatus", "status", "grand_total"] \
		+ [f for f in ("payment_terms_template", "incoterm", "terms") if meta.has_field(f)]
	sqs = frappe.get_all("Supplier Quotation", filters={"name": ["in", frappe.get_all("Supplier Quotation Item", filters={"request_for_quotation": rfq}, pluck="parent") or [""]],
		"docstatus": ["<", 2]}, fields=fields, order_by="transaction_date asc")
	sups = []
	for q in sqs:
		lines = frappe.get_all("Supplier Quotation Item", filters={"parent": q.name}, fields=["item_code", "qty", "rate", "amount", "lead_time_days", "request_for_quotation_item"])
		sups.append({"quotation": q.name, "supplier": q.supplier, "name": q.supplier_name or q.supplier, "currency": q.currency, "valid_till": q.valid_till,
			"expired": bool(q.valid_till and getdate(q.valid_till) < getdate(today())), "submitted": q.docstatus == 1, "terms": q.get("payment_terms_template") or frappe.utils.strip_html(q.get("terms") or "")[:80],
			"incoterm": q.get("incoterm") or "", "lines": {l.item_code: {"rate": flt(l.rate), "aed": _aed(l.rate, q.currency, company), "lead": l.lead_time_days or 0} for l in lines}})
	items = []
	for it in doc.items:
		offers = [(s["quotation"], s["lines"][it.item_code]["aed"]) for s in sups if it.item_code in s["lines"] and not s["expired"]]
		best = min(offers, key=lambda x: x[1])[0] if offers else None
		items.append({"item_code": it.item_code, "item_name": it.item_name, "qty": flt(it.qty), "uom": it.uom, "best": best})
	for s in sups:
		s["total_aed"] = sum(s["lines"][i["item_code"]]["aed"] * i["qty"] for i in items if i["item_code"] in s["lines"])
		s["covers"] = sum(1 for i in items if i["item_code"] in s["lines"])
	return {"rfq": rfq, "company": company, "base": base, "date": doc.transaction_date, "status": doc.status, "items": items, "suppliers": sups,
		"can_award": frappe.has_permission("Purchase Order", "create")}


@frappe.whitelist()
def award(rfq, picks):
	"""Create one draft purchase order per chosen supplier quotation with the items picked for it (prototype "Award")."""
	frappe.has_permission("Purchase Order", "create", throw=True)
	picks = frappe.parse_json(picks) if isinstance(picks, str) else picks
	by = {}
	for item, sq in (picks or {}).items():
		if sq:
			by.setdefault(sq, set()).add(item)
	if not by:
		frappe.throw(_("Choose a supplier for at least one item"))
	from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order

	out = []
	for sq, items in by.items():
		q = frappe.get_doc("Supplier Quotation", sq)
		if q.docstatus == 0:
			q.submit()
		po = make_purchase_order(sq)
		po.set("items", [r for r in po.items if r.item_code in items])
		for r in po.items:
			r.schedule_date = r.schedule_date or frappe.utils.add_days(today(), 30)
		po.schedule_date = min(r.schedule_date for r in po.items)
		po.insert()
		out.append(po.name)
	return {"pos": out, "message": _("{0} created from {1}").format(", ".join(out), rfq)}
