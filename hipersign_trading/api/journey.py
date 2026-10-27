"""v1.5 — Trade Journey: one purchase followed from the supplier order to the customer's payment."""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def purchase_orders():
	pos = frappe.get_all("Purchase Order", filters={"docstatus": ["<", 2]},
		fields=["name", "supplier_name", "status", "transaction_date"] + (["workflow_state"] if frappe.get_meta("Purchase Order").has_field("workflow_state") else []),
		order_by="transaction_date desc, creation desc", limit=60)
	shipped = set(frappe.get_all("Import Shipment PO", filters={"purchase_order": ["in", [p.name for p in pos] or [""]]}, pluck="purchase_order"))
	for p in pos:
		p.has_import = p.name in shipped
		p.per_received = frappe.db.get_value("Purchase Order", p.name, "per_received")
	return pos


def _fmt(v, cur=None):
	from hipersign_trading.utils import money

	return money(v, cur)


@frappe.whitelist()
def chain(po):
	p = frappe.get_doc("Purchase Order", po)
	p.check_permission("read")
	cur = p.currency
	company_cur = frappe.get_cached_value("Company", p.company, "default_currency")
	items = [(i.item_code, i.item_name, flt(i.qty), flt(i.base_net_rate)) for i in p.items]
	stages = []
	stages.append({"n": "01", "title": _("Supplier purchasing"), "status": _(p.get("workflow_state") or p.status), "done": p.docstatus == 1,
		"rows": [[_("Purchase order"), p.name, ["Form", "Purchase Order", p.name]], [_("Supplier"), p.supplier_name],
			[_("Items"), ", ".join(f"{frappe.format(q, 'Float')} × {n}" for _c, n, q, _r in items[:3]) + (" …" if len(items) > 3 else "")],
			[_("Value"), _fmt(p.grand_total, cur) + (f" = {_fmt(p.base_grand_total, company_cur)}" if cur != company_cur else "")],
			[_("Incoterm"), " ".join(x for x in (p.get("incoterm"), p.get("named_place")) if x) or "—"]]})
	# 2 import shipment
	sh_name = frappe.db.get_value("Import Shipment PO", {"purchase_order": po}, "parent")
	sh = frappe.get_doc("Import Shipment", sh_name) if sh_name else None
	if sh:
		req = [d for d in sh.documents if d.required]
		stages.append({"n": "02", "title": _("Import & shipment"), "status": _(sh.status), "done": sh.status in ("Cleared", "Received at Warehouse"),
			"rows": [[_("Shipment"), sh.name, ["Form", "Import Shipment", sh.name]], [_("Mode"), " · ".join(x for x in (_(sh.mode or ""), sh.vessel_flight) if x) or "—"],
				[_("BL / AWB"), sh.bl_awb or "—"], [_("ETA"), frappe.format(sh.eta, "Date") if sh.eta else "—"],
				[_("Bill of Entry"), sh.bill_of_entry or _("Pending")], [_("Documents"), _("{0} of {1}").format(sum(1 for d in req if d.received), len(req))]]})
	else:
		stages.append({"n": "02", "title": _("Import & shipment"), "status": _("Local purchase"), "done": True, "rows": [], "empty": _("No import shipment — a local supplier.")})
	# 3 receipts
	prs = sorted({r.parent for r in frappe.get_all("Purchase Receipt Item", filters={"purchase_order": po, "docstatus": 1}, fields=["parent"])})
	pr_docs = [frappe.get_doc("Purchase Receipt", n) for n in prs]
	recv = sum(flt(i.qty) for d in pr_docs for i in d.items if i.purchase_order == po)
	ordered = sum(q for _c, _n, q, _r in items)
	stages.append({"n": "03", "title": _("Goods receiving"), "status": _("Received") if recv >= ordered and recv else (_("Partly received") if recv else _("Awaiting")), "done": recv >= ordered and recv > 0,
		"rows": [[_("Receipt"), d.name, ["Form", "Purchase Receipt", d.name]] for d in pr_docs] + ([[_("Received"), f"{frappe.format(recv, 'Float')} / {frappe.format(ordered, 'Float')}"]] if pr_docs else []),
		"empty": None if pr_docs else _("No receipt yet.")})
	# 4 landed cost
	goods = flt(p.base_net_total)
	charges = flt(sh.total_charges) if sh else 0
	lcv = sh.landed_cost_voucher if sh else None
	if not lcv and prs:
		lcv = frappe.db.get_value("Landed Cost Purchase Receipt", {"receipt_document": ["in", prs], "docstatus": 1}, "parent")
	first = items[0] if items else None
	unit = None
	if first and pr_docs:
		vr = [flt(i.valuation_rate) for d in pr_docs for i in d.items if i.item_code == first[0]]
		unit = vr[0] if vr else None
	stages.append({"n": "04", "title": _("Landed cost"), "status": _("Applied") if lcv else _("Not applied"), "done": bool(lcv),
		"rows": [[_("Goods"), _fmt(goods, company_cur)], [_("Freight, insurance, duty, clearing, handling"), _fmt(charges, company_cur)],
			[_("Landed uplift"), f"{round(charges / goods * 100, 1) if goods else 0}%"],
			[_("Landed unit cost — {0}").format(first[1]) if first else _("Landed unit cost"), _fmt(unit, company_cur) if unit else "—"]]
			+ ([[_("Landed cost voucher"), lcv, ["Form", "Landed Cost Voucher", lcv]]] if lcv else [])})
	# 5-7 sales of the received stock
	codes = [c for c, _n, _q, _r in items]
	since = min((d.posting_date for d in pr_docs), default=None)
	sos = []
	if since:
		so = frappe.qb.DocType("Sales Order")
		soi = frappe.qb.DocType("Sales Order Item")
		sos = [r[0] for r in (frappe.qb.from_(soi).join(so).on(so.name == soi.parent).select(so.name).distinct()
			.where((soi.item_code.isin(codes)) & (so.docstatus == 1) & (so.transaction_date >= since) & (so.company == p.company))
			.orderby(so.transaction_date).limit(8)).run()]
	so_docs = [frappe.get_doc("Sales Order", n) for n in sos]
	stages.append({"n": "05", "title": _("Sales orders using this stock"), "status": _("{0} orders").format(len(so_docs)), "done": bool(so_docs),
		"rows": [[d.customer_name, d.name, ["Form", "Sales Order", d.name]] for d in so_docs], "empty": None if so_docs else _("No sales after receipt yet.")})
	dns = sorted({r.parent for r in frappe.get_all("Delivery Note Item", filters={"against_sales_order": ["in", sos], "docstatus": 1}, fields=["parent"])}) if sos else []
	dn_docs = [frappe.get_doc("Delivery Note", n) for n in dns]
	delivered = sum(1 for d in dn_docs if d.get("hs_delivery_status") == "Delivered")
	stages.append({"n": "06", "title": _("Dispatch & delivery"), "status": f"{delivered}/{len(dn_docs)} " + _("delivered"), "done": bool(dn_docs) and delivered == len(dn_docs),
		"rows": [[d.customer_name, f"{d.name} · {_(d.get('hs_delivery_status') or d.status)}", ["Form", "Delivery Note", d.name]] for d in dn_docs],
		"empty": None if dn_docs else _("Nothing dispatched yet.")})
	sis = sorted(({r.parent for r in frappe.get_all("Sales Invoice Item", filters={"sales_order": ["in", sos], "docstatus": 1}, fields=["parent"])} if sos else set())
		| ({r.parent for r in frappe.get_all("Sales Invoice Item", filters={"delivery_note": ["in", dns], "docstatus": 1}, fields=["parent"])} if dns else set()))
	si_docs = [frappe.get_doc("Sales Invoice", n) for n in sis]
	paid = sum(1 for d in si_docs if flt(d.outstanding_amount) <= 0.01)
	stages.append({"n": "07", "title": _("Invoice & payment"), "status": _("{0} invoices").format(len(si_docs)), "done": bool(si_docs) and paid == len(si_docs),
		"rows": [[d.customer_name, f"{d.name} · {_fmt(d.grand_total, d.currency)} · " + (_("paid") if flt(d.outstanding_amount) <= 0.01 else _("{0} open").format(_fmt(d.outstanding_amount, d.currency))),
			["Form", "Sales Invoice", d.name]] for d in si_docs], "empty": None if si_docs else _("Not invoiced yet.")})
	return {"po": po, "stages": stages}
