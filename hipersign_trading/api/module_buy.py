"""v1.6.0: the purchasing module pages (prototype "Supplier Purchasing"): KPI row, ordered-by-supplier and currency-mix
cards, and the tabs purchase requests · supplier quotations · purchase orders · smart reorder · suppliers.

Same shape as api/module.py (get_module / get_rows dispatch there). Read with the user's own permissions.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from hipersign_trading.api.module import _fields, _fmt, _perm, _scope, _sum, kpi

PO_CHIPS = [("all", "All"), ("open", "Open"), ("approval", "Awaiting approval"), ("overdue", "Overdue"), ("draft", "Draft")]
OPEN_PO = ["To Receive and Bill", "To Receive", "To Bill"]
CUR_COLORS = {"USD": "blue", "EUR": "violet", "CNY": "orange", "AED": "green", "GBP": "navy", "SAR": "teal", "OMR": "red"}


def _country(names):
	return dict(frappe.get_all("Supplier", filters={"name": ["in", names or [""]]}, fields=["name", "country"], as_list=True)) if _perm("Supplier") else {}


def _shipments(pos):
	"""{po: (shipment, status)} — the latest import shipment carrying each order."""
	if not pos or not frappe.db.table_exists("Import Shipment PO"):
		return {}
	out = {}
	for r in frappe.get_all("Import Shipment PO", filters={"purchase_order": ["in", pos], "parenttype": "Import Shipment"}, fields=["parent", "purchase_order"],
			order_by="creation asc"):
		out[r.purchase_order] = r.parent
	st = dict(frappe.get_all("Import Shipment", filters={"name": ["in", list(out.values()) or [""]]}, fields=["name", "status"], as_list=True))
	return {po: (sh, st.get(sh)) for po, sh in out.items()}


def _po_items(names):
	if not names:
		return {}
	out = {}
	for r in frappe.get_all("Purchase Order Item", filters={"parent": ["in", names]}, fields=["parent", "item_name", "qty"], order_by="idx asc"):
		out.setdefault(r.parent, []).append(f"{flt(r.qty):g} × {r.item_name}")
	return {k: v[:3] + ([_("+{0} more").format(len(v) - 3)] if len(v) > 3 else []) for k, v in out.items()}


def _reorder_rows(cos):
	try:
		from frappe.desk.query_report import run

		if not frappe.get_cached_doc("Report", "Hipersign Smart Reorder").is_permitted():
			return []
		return run("Hipersign Smart Reorder", filters={"company": cos[0], "only_to_order": 1}).get("result") or []
	except Exception:
		frappe.clear_last_message()
		return []


def purchasing_module():
	cos, start, end, label, cur = _scope()
	co = ["in", cos]
	t = today()
	open_f = {"company": co, "docstatus": 1, "status": ["in", OPEN_PO]}
	open_rows = frappe.get_list("Purchase Order", filters=open_f, fields=["base_grand_total", "per_received", "schedule_date"], limit_page_length=0) if _perm("Purchase Order") else []
	not_received = sum(flt(r.base_grand_total) * (100 - flt(r.per_received)) / 100 for r in open_rows)
	overdue = [r for r in open_rows if r.schedule_date and getdate(r.schedule_date) < getdate(t) and flt(r.per_received) < 100]
	waiting = frappe.db.count("Purchase Order", {"company": co, "docstatus": 0, "workflow_state": ["like", "Pending%"]}) \
		if _perm("Purchase Order") and frappe.get_meta("Purchase Order").has_field("workflow_state") else 0
	period = {"company": co, "docstatus": 1, "transaction_date": ["between", [start, end]]}
	ordered = frappe.get_list("Purchase Order", filters=period, fields=["supplier", "supplier_name", "currency", "base_grand_total"], limit_page_length=0) if _perm("Purchase Order") else []
	reorder = _reorder_rows(cos)
	by_sup, by_cur = {}, {}
	for r in ordered:
		by_sup[r.supplier_name or r.supplier] = by_sup.get(r.supplier_name or r.supplier, 0) + flt(r.base_grand_total)
		by_cur[r.currency] = by_cur.get(r.currency, 0) + flt(r.base_grand_total)
	n_req = frappe.db.count("Material Request", {"company": co, "docstatus": ["<", 2], "material_request_type": "Purchase", "status": ["not in", ["Ordered", "Stopped", "Cancelled"]]}) \
		if _perm("Material Request") else 0
	n_sq = frappe.db.count("Supplier Quotation", {"company": co, "docstatus": ["<", 2], "status": ["not in", ["Ordered", "Stopped", "Cancelled", "Expired"]]}) \
		if _perm("Supplier Quotation") else 0
	return {
		"title": _("Supplier Purchasing"),
		"desc": _("Manage supplier orders, purchasing requirements and agreed commercial terms — in the supplier's currency, approved before they are placed."),
		"new": [{"label": _("New purchase order"), "doctype": "Purchase Order", "primary": 1}],
		"kpis": [
			kpi(_("Open purchase orders"), len(open_rows), _("{0} not yet received").format(_fmt(not_received, cur)), "blue", "list", tab="orders", chip="open"),
			kpi(_("Awaiting approval"), waiting, _("Purchase / Finance Manager"), "violet", "inbox", tab="orders", chip="approval"),
			kpi(_("Ordered — {0}").format(label), sum(flt(r.base_grand_total) for r in ordered), _("{0} orders").format(len(ordered)), "navy", "chart-column", True, cur, tab="orders", chip="all"),
			kpi(_("Overdue deliveries"), len(overdue), _("Expected date passed"), "red", "clock", tab="orders", chip="overdue"),
			kpi(_("Reorder suggestions"), len(reorder), _("Based on sales speed & lead time"), "amber", "flag", tab="reorder"),
		],
		"cards": [
			{"title": _("Ordered by supplier"), "sub": _("{0} · {1} at order rate").format(label, cur), "type": "bars",
				"rows": [[k, v] for k, v in sorted(by_sup.items(), key=lambda kv: -kv[1])[:6]], "currency": cur, "wide": 1},
			{"title": _("Order currency mix"), "sub": _("Converted to {0}").format(cur), "type": "donut", "center": len(ordered), "center_label": _("orders"),
				"rows": [[c, v, CUR_COLORS.get(c, "grey")] for c, v in sorted(by_cur.items(), key=lambda kv: -kv[1])], "currency": cur},
		],
		"tabs": [
			{"key": "requests", "label": _("Purchase requests ({0})").format(n_req), "chips": [["open", _("Open")], ["all", _("All")]]},
			{"key": "quotes", "label": _("Supplier quotations ({0})").format(n_sq), "chips": []},
			{"key": "orders", "label": _("Purchase orders"), "chips": [[k, _(v)] for k, v in PO_CHIPS]},
			{"key": "reorder", "label": _("Smart reorder"), "chips": []},
			{"key": "suppliers", "label": _("Suppliers"), "chips": [["all", _("All")], ["import", _("Overseas")], ["local", _("Local")]]},
		],
		"default_tab": "orders",
	}


def purchasing_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	co = ["in", cos]
	t = getdate(today())
	if tab == "orders":
		if not _perm("Purchase Order"):
			return {"cols": [], "rows": []}
		f = {"company": co, "docstatus": ["<", 2]}
		f.update({"open": {"docstatus": 1, "status": ["in", OPEN_PO]}, "approval": {"docstatus": 0, "workflow_state": ["like", "Pending%"]},
			"overdue": {"docstatus": 1, "status": ["in", OPEN_PO], "schedule_date": ["<", today()], "per_received": ["<", 100]},
			"draft": {"docstatus": 0}}.get(chip, {}))
		if chip == "draft" and frappe.get_meta("Purchase Order").has_field("workflow_state"):
			f["workflow_state"] = ["not like", "Pending%"]
		or_f = [["supplier_name", "like", f"%{q}%"], ["name", "like", f"%{q}%"]] if q else None
		rows = frappe.get_list("Purchase Order", filters=f, or_filters=or_f, fields=_fields("Purchase Order", ["name", "supplier", "supplier_name", "transaction_date",
			"schedule_date", "grand_total", "base_grand_total", "currency", "per_received", "status", "docstatus", "workflow_state"]),
			order_by="transaction_date desc, creation desc", limit=200)
		names = [r.name for r in rows]
		items, ships, country = _po_items(names), _shipments(names), _country([r.supplier for r in rows])
		from hipersign_trading.api.module import _status

		out = []
		for r in rows:
			sh = ships.get(r.name)
			late = bool(r.docstatus == 1 and r.schedule_date and getdate(r.schedule_date) < t and flt(r.per_received) < 100)
			out.append({"dt": "Purchase Order", "name": r.name, "cells": [
				{"code": r.name}, {"main": r.supplier_name or r.supplier, "sub": country.get(r.supplier) or ""}, {"lines": items.get(r.name, [])},
				{"date": r.transaction_date},
				{"money": r.grand_total, "currency": r.currency, "sub": _fmt_base(r, cur)},
				{"date": r.schedule_date, "late": late},
				{"link": ["Import Shipment", sh[0]], "pill": sh[1]} if sh else (_("Local") if not _foreign(r, cur) and r.docstatus == 1 else "—"),
				{"bar": flt(r.per_received)} if r.docstatus == 1 else "—",
				{"pill": _status(r)}]})
		return {"cols": [{"label": _("PO No.")}, {"label": _("Supplier")}, {"label": _("Items"), "cls": "items"}, {"label": _("Order date")}, {"label": _("Value"), "cls": "num"},
			{"label": _("Expected")}, {"label": _("Shipment")}, {"label": _("Received")}, {"label": _("Status")}], "rows": out}
	if tab == "requests":
		if not _perm("Material Request"):
			return {"cols": [], "rows": []}
		f = {"company": co, "docstatus": ["<", 2], "material_request_type": "Purchase"}
		if chip != "all":
			f["status"] = ["not in", ["Ordered", "Stopped", "Cancelled"]]
		rows = frappe.get_list("Material Request", filters=f, fields=["name", "transaction_date", "schedule_date", "status", "docstatus", "per_ordered", "owner"],
			order_by="transaction_date desc", limit=200)
		items = {}
		for r in frappe.get_all("Material Request Item", filters={"parent": ["in", [x.name for x in rows] or [""]]}, fields=["parent", "item_name", "qty"], order_by="idx"):
			items.setdefault(r.parent, []).append(f"{flt(r.qty):g} × {r.item_name}")
		return {"cols": [{"label": _("Request")}, {"label": _("Items")}, {"label": _("Requested by")}, {"label": _("Date")}, {"label": _("Required by")},
			{"label": _("Ordered")}, {"label": _("Status")}],
			"rows": [{"dt": "Material Request", "name": r.name, "cells": [{"code": r.name}, {"lines": items.get(r.name, [])[:3]}, frappe.utils.get_fullname(r.owner),
				{"date": r.transaction_date}, {"date": r.schedule_date, "late": bool(r.schedule_date and getdate(r.schedule_date) < t and r.status not in ("Ordered",))},
				{"bar": flt(r.per_ordered)} if r.docstatus == 1 else "—", {"pill": _("Draft") if r.docstatus == 0 else r.status}]} for r in rows],
			"actions": [{"label": _("Supplier Quotation Comparison"), "route": ["query-report", "Supplier Quotation Comparison"]}] if _perm("Supplier Quotation") else []}
	if tab == "quotes":
		if not _perm("Supplier Quotation"):
			return {"cols": [], "rows": []}
		rows = frappe.get_list("Supplier Quotation", filters={"company": co, "docstatus": ["<", 2]}, fields=["name", "supplier", "supplier_name", "transaction_date",
			"valid_till", "grand_total", "base_grand_total", "currency", "status", "docstatus"], order_by="transaction_date desc", limit=200)
		rfq = {}
		for r in frappe.get_all("Supplier Quotation Item", filters={"parent": ["in", [x.name for x in rows] or [""]]}, fields=["parent", "request_for_quotation", "lead_time_days"]):
			rfq.setdefault(r.parent, [r.request_for_quotation, r.lead_time_days])
		return {"cols": [{"label": _("Quotation")}, {"label": _("Supplier")}, {"label": _("RFQ")}, {"label": _("Date")}, {"label": _("Valid till")},
			{"label": _("Lead time")}, {"label": _("Value"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Supplier Quotation", "name": r.name, "cells": [{"code": r.name}, {"main": r.supplier_name or r.supplier}, (rfq.get(r.name) or [""])[0] or "—",
				{"date": r.transaction_date}, {"date": r.valid_till, "late": bool(r.valid_till and getdate(r.valid_till) < t)},
				f"{cint((rfq.get(r.name) or [0, 0])[1])} {_('days')}" if (rfq.get(r.name) or [0, 0])[1] else "—",
				{"money": r.grand_total, "currency": r.currency, "sub": _fmt_base(r, cur)}, {"pill": _("Draft") if r.docstatus == 0 else r.status}]} for r in rows],
			"actions": [{"label": _("Compare offers"), "route": ["query-report", "Supplier Quotation Comparison"]}]}
	if tab == "reorder":
		rows = _reorder_rows(cos)
		return {"cols": [{"label": _("Item")}, {"label": _("Supplier")}, {"label": _("Daily demand"), "cls": "num"}, {"label": _("Trend")}, {"label": _("Lead time"), "cls": "num"},
			{"label": _("Stock + on order"), "cls": "num"}, {"label": _("Suggested order"), "cls": "num"}],
			"rows": [{"dt": "Item", "name": r.get("item_code"), "cells": [{"main": r.get("item_name"), "sub": r.get("item_code")}, r.get("supplier") or "—",
				flt(r.get("daily_demand"), 1), _(str(r.get("trend") or "")).capitalize() or "—", f"{cint(r.get('lead_time'))} {_('days')}",
				flt(r.get("projected_qty") or r.get("available") or (flt(r.get("actual_qty")) + flt(r.get("ordered_qty")))),
				{"main": f"{flt(r.get('suggested_qty')):g}", "sub": r.get("purchase_uom") or ""}]} for r in rows],
			"actions": [{"label": _("Open Smart reorder (create POs)"), "route": ["query-report", "Hipersign Smart Reorder"], "options": {"company": cos[0], "only_to_order": 1}, "primary": 1}],
			"empty": _("Nothing to reorder — stock and open orders cover the expected demand.")}
	if tab == "suppliers":
		if not _perm("Supplier"):
			return {"cols": [], "rows": []}
		f = {"disabled": 0}
		if q:
			f["supplier_name"] = ["like", f"%{q}%"]
		sups = frappe.get_list("Supplier", filters=f, fields=_fields("Supplier", ["name", "supplier_name", "country", "default_currency", "payment_terms",
			"hs_lead_time_days", "hs_incoterm", "hs_supplier_kind", "supplier_group"]), order_by="supplier_name asc", limit=300)
		company_country = frappe.get_cached_value("Company", cos[0], "country") if cos else None
		if chip == "import":
			sups = [s for s in sups if s.country and s.country != company_country]
		elif chip == "local":
			sups = [s for s in sups if not s.country or s.country == company_country]
		names = [s.name for s in sups] or [""]
		open_v, payable = {}, {}
		if _perm("Purchase Order"):
			for r in frappe.get_all("Purchase Order", filters={"supplier": ["in", names], "docstatus": 1, "status": ["in", OPEN_PO], "company": co},
					fields=["supplier", "base_grand_total", "per_received"]):
				open_v[r.supplier] = open_v.get(r.supplier, 0) + flt(r.base_grand_total) * (100 - flt(r.per_received)) / 100
		if _perm("Purchase Invoice"):
			for r in frappe.get_all("Purchase Invoice", filters={"supplier": ["in", names], "docstatus": 1, "outstanding_amount": ["!=", 0], "company": co},
					fields=["supplier", "outstanding_amount", "conversion_rate"]):
				payable[r.supplier] = payable.get(r.supplier, 0) + flt(r.outstanding_amount) * flt(r.conversion_rate or 1)
		return {"cols": [{"label": _("Supplier")}, {"label": _("Type")}, {"label": _("Currency")}, {"label": _("Terms")}, {"label": _("Incoterm")},
			{"label": _("Lead time"), "cls": "num"}, {"label": _("Open orders"), "cls": "num"}, {"label": _("Payable"), "cls": "num"}],
			"rows": [{"dt": "Supplier", "name": s.name, "cells": [{"main": s.supplier_name, "sub": s.country or ""}, _(s.hs_supplier_kind or s.supplier_group or "") or "—",
				s.default_currency or cur, s.payment_terms or "—", s.hs_incoterm or "—", f"{cint(s.hs_lead_time_days)} {_('days')}" if s.hs_lead_time_days else "—",
				{"money": open_v.get(s.name, 0)} if open_v.get(s.name) else "—", {"money": payable.get(s.name, 0)} if payable.get(s.name) else "—"]} for s in sups]}
	return {"cols": [], "rows": []}


def _foreign(r, cur):
	return (r.currency or cur) != cur


def _fmt_base(r, cur):
	if not _foreign(r, cur):
		return ""
	return f"{cur} {flt(r.base_grand_total):,.2f}"


# ---------------------------------------------------------------- Import & Shipment (v1.6.0 step 2)
SHIP_COLS = [("booked", "Booked & shipped", ["Booked", "Shipped"]), ("transit", "In transit", ["In Transit"]),
	("port", "At port & customs", ["Arrived at Port", "Under Customs Clearance"]), ("done", "Cleared & received", ["Cleared", "Received at Warehouse"])]
OPEN_SHIP = ["Booked", "Shipped", "In Transit", "Arrived at Port", "Under Customs Clearance", "Cleared"]


def _ships(cos, filters=None, q=None):
	if not _perm("Import Shipment"):
		return []
	f = {"company": ["in", cos], "docstatus": ["<", 2]}
	f.update(filters or {})
	rows = frappe.get_list("Import Shipment", filters=f, fields=["name", "status", "mode", "port_of_loading", "port_of_discharge", "eta", "etd", "goods_value",
		"total_charges", "bl_awb", "bill_of_entry", "cleared_on", "arrived_on", "modified"], order_by="eta asc", limit=300)
	names = [r.name for r in rows] or [""]
	sup, missing = {}, {}
	for p in frappe.get_all("Import Shipment PO", filters={"parent": ["in", names], "parenttype": "Import Shipment"}, fields=["parent", "supplier", "purchase_order"], order_by="idx"):
		sup.setdefault(p.parent, []).append(p.supplier or frappe.db.get_value("Purchase Order", p.purchase_order, "supplier_name"))
	for dd in frappe.get_all("Shipment Document", filters={"parent": ["in", names], "parenttype": "Import Shipment", "required": 1, "received": 0}, fields=["parent", "document_type"]):
		missing.setdefault(dd.parent, []).append(dd.document_type)
	for r in rows:
		r.suppliers = list(dict.fromkeys(x for x in sup.get(r.name, []) if x))
		r.missing = missing.get(r.name, [])
	if q:
		ql = q.lower()
		rows = [r for r in rows if ql in r.name.lower() or any(ql in s.lower() for s in r.suppliers) or ql in (r.bl_awb or "").lower()]
	return rows


def imports_module():
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	open_ = _ships(cos, {"status": ["in", OPEN_SHIP]})
	soon = [r for r in open_ if r.eta and t <= getdate(r.eta) <= frappe.utils.add_days(t, 7) and r.status in ("Booked", "Shipped", "In Transit")]
	port = [r for r in open_ if r.status in ("Arrived at Port", "Under Customs Clearance")]
	cleared = [r for r in open_ if r.status == "Cleared"]
	gaps = [r for r in open_ if r.missing]
	charges = 0
	if frappe.db.table_exists("Shipment Charge"):
		charges = sum(flt(c.amount) for c in frappe.get_all("Shipment Charge", filters={"parenttype": "Import Shipment", "date": ["between", [start, end]]}, fields=["amount"]))
	return {
		"title": _("Import & Shipment"),
		"desc": _("Coordinate shipment information, import documentation and associated costs — from booking to customs clearance."),
		"new": [{"label": _("New shipment"), "doctype": "Import Shipment", "primary": 1}],
		"kpis": [
			kpi(_("Open shipments"), len(open_), _("{0} goods value").format(_fmt(sum(flt(r.goods_value) for r in open_), cur)), "blue", "ship", tab="board"),
			kpi(_("Arriving in 7 days"), len(soon), _("By ETA"), "violet", "clock", tab="all", chip="soon"),
			kpi(_("At port / customs"), len(port), _("Demurrage risk after free days"), "amber", "flag", tab="all", chip="port"),
			kpi(_("Cleared, awaiting receipt"), len(cleared), _("Ready for goods receiving"), "green", "check", tab="all", chip="cleared"),
			kpi(_("Missing documents"), len(gaps), _("Shipments with gaps"), "red", "file", tab="all", chip="gaps"),
			kpi(_("Import charges — {0}").format(label), charges, _("Freight, duty, insurance, clearing, handling"), "navy", "layers", True, cur, route=["hipersign-landed"]),
		],
		"tabs": [
			{"key": "board", "label": _("Shipment board"), "chips": []},
			{"key": "all", "label": _("All shipments"), "chips": [["open", _("Open")], ["soon", _("Arriving in 7 days")], ["port", _("At port / customs")],
				["cleared", _("Cleared")], ["gaps", _("Missing documents")], ["all", _("All")]]},
		],
	}


def _route(r):
	return " → ".join(x for x in [r.port_of_loading, r.port_of_discharge] if x)


def imports_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "board":
		rows = _ships(cos, {"modified": [">=", frappe.utils.add_months(today(), -3)]}, q)
		cols = []
		for key, title, sts in SHIP_COLS:
			rs = [r for r in rows if r.status in sts and (key != "done" or r.status == "Cleared" or getdate(r.modified) >= frappe.utils.add_days(t, -45))]
			cols.append({"key": key, "label": title, "count": len(rs), "cards": [{"dt": "Import Shipment", "name": r.name, "code": r.name, "pill": r.status,
				"title": ", ".join(r.suppliers) or "—", "lines": [" · ".join(x for x in [_(r.mode or ""), _route(r)] if x),
				" · ".join(x for x in [_("ETA {0}").format(frappe.utils.formatdate(r.eta, "dd MMM")) if r.eta else "", _fmt(r.goods_value, cur) if r.goods_value else ""] if x)],
				"warn": _("{0} missing").format(", ".join(r.missing)) if r.missing else ""} for r in rs]})
		return {"kanban": cols}
	f = {}
	if chip in ("open", "soon", "port", "cleared", "gaps"):
		f["status"] = ["in", OPEN_SHIP]
	rows = _ships(cos, f, q)
	if chip == "soon":
		rows = [r for r in rows if r.eta and t <= getdate(r.eta) <= frappe.utils.add_days(t, 7) and r.status in ("Booked", "Shipped", "In Transit")]
	elif chip == "port":
		rows = [r for r in rows if r.status in ("Arrived at Port", "Under Customs Clearance")]
	elif chip == "cleared":
		rows = [r for r in rows if r.status == "Cleared"]
	elif chip == "gaps":
		rows = [r for r in rows if r.missing]
	return {"cols": [{"label": _("Shipment")}, {"label": _("Supplier")}, {"label": _("Mode · route")}, {"label": _("ETA")}, {"label": _("Goods value"), "cls": "num"},
		{"label": _("Charges"), "cls": "num"}, {"label": _("Documents")}, {"label": _("Status")}],
		"rows": [{"dt": "Import Shipment", "name": r.name, "cells": [{"code": r.name}, {"main": ", ".join(r.suppliers) or "—", "sub": r.bl_awb or ""},
			{"main": _(r.mode or ""), "sub": _route(r)}, {"date": r.eta, "late": bool(r.eta and getdate(r.eta) < t and r.status in ("Booked", "Shipped", "In Transit"))},
			{"money": r.goods_value}, {"money": r.total_charges} if flt(r.total_charges) else "—",
			{"pill": _("{0} missing").format(len(r.missing)), "tone": "orange"} if r.missing else {"pill": _("Complete"), "tone": "green"},
			{"pill": r.status}]} for r in rows]}


# ---------------------------------------------------------------- Goods Receiving (v1.6.0 step 3)
def receiving_module():
	cos, start, end, label, cur = _scope()
	waiting = _awaiting(cos)
	ready = [w for w in waiting if w["ok"]]
	blocked = [w for w in waiting if not w["ok"]]
	recs = _receipts(cos, start, end)
	acc = sum(r.acc for r in recs)
	rej = sum(r.rej for r in recs)
	return {
		"title": _("Goods Receiving"),
		"desc": _("Record incoming goods and check deliveries against the purchase order — quantities, damages and the receiving warehouse."),
		"new": [{"label": _("New goods receipt"), "doctype": "Purchase Receipt", "primary": 1}],
		"kpis": [
			kpi(_("Ready to receive"), len(ready), _("Cleared imports & local orders"), "green", "check", tab="awaiting", chip="ready"),
			kpi(_("Awaiting clearance"), len(blocked), _("Receipt blocked until cleared"), "amber", "lock", tab="awaiting", chip="blocked"),
			kpi(_("Receipts — {0}").format(label), len(recs), _("{0} units counted").format(f"{acc + rej:,.0f}"), "blue", "package", tab="receipts"),
			kpi(_("Rejected — {0}").format(label), f"{rej:,.0f}", _("Moved to Rejected Warehouse"), "red", "triangle-alert", tab="receipts"),
			kpi(_("Acceptance rate"), f"{acc / (acc + rej) * 100:.1f}%" if acc + rej else "—", _("Accepted ÷ received"), "violet", "check"),
		],
		"tabs": [
			{"key": "awaiting", "label": _("Awaiting receipt ({0})").format(len(waiting)), "chips": [["all", _("All")], ["ready", _("Ready to receive")], ["blocked", _("Awaiting clearance")]]},
			{"key": "receipts", "label": _("Recent receipts"), "chips": []},
		],
	}


def _awaiting(cos):
	if not _perm("Purchase Order"):
		return []
	pos = frappe.get_list("Purchase Order", filters={"company": ["in", cos], "docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]], "per_received": ["<", 100]},
		fields=["name", "supplier", "supplier_name", "schedule_date", "currency"], order_by="schedule_date asc", limit=200)
	names = [p.name for p in pos]
	ships = _shipments(names)
	boe = dict(frappe.get_all("Import Shipment", filters={"name": ["in", [s[0] for s in ships.values()] or [""]]}, fields=["name", "bill_of_entry"], as_list=True))
	left = {}
	for r in frappe.get_all("Purchase Order Item", filters={"parent": ["in", names or [""]]}, fields=["parent", "item_name", "qty", "received_qty"], order_by="idx"):
		if flt(r.qty) > flt(r.received_qty):
			left.setdefault(r.parent, []).append(f"{flt(r.qty) - flt(r.received_qty):g} × {r.item_name}")
	block = frappe.db.get_single_value("Hipersign Settings", "block_receipt_before_clearance")
	out = []
	for p in pos:
		sh = ships.get(p.name)
		if sh and sh[1] in ("Cleared", "Received at Warehouse"):
			ok, check = True, _("Cleared") + (f" — BOE {boe.get(sh[0])}" if boe.get(sh[0]) else "")
		elif sh:
			ok, check = not block, _("Shipment {0}").format(_(sh[1] or "").lower())
		else:
			ok, check = True, _("Local supplier — deliver to warehouse")
		out.append({"po": p, "ship": sh, "ok": ok, "check": check, "left": left.get(p.name, [])})
	return out


def _receipts(cos, start, end):
	if not _perm("Purchase Receipt"):
		return []
	recs = frappe.get_list("Purchase Receipt", filters={"company": ["in", cos], "docstatus": 1, "is_return": 0, "posting_date": ["between", [start, end]]},
		fields=["name", "posting_date", "supplier", "supplier_name", "base_grand_total", "set_warehouse"], order_by="posting_date desc", limit=100)
	agg = {}
	for i in frappe.get_all("Purchase Receipt Item", filters={"parent": ["in", [r.name for r in recs] or [""]]}, fields=["parent", "qty", "rejected_qty", "warehouse", "purchase_order"]):
		a = agg.setdefault(i.parent, {"acc": 0, "rej": 0, "wh": [], "po": []})
		a["acc"] += flt(i.qty)
		a["rej"] += flt(i.rejected_qty)
		if i.warehouse and i.warehouse not in a["wh"]:
			a["wh"].append(i.warehouse)
		if i.purchase_order and i.purchase_order not in a["po"]:
			a["po"].append(i.purchase_order)
	for r in recs:
		a = agg.get(r.name, {"acc": 0, "rej": 0, "wh": [], "po": []})
		r.acc, r.rej, r.wh, r.po = a["acc"], a["rej"], a["wh"], a["po"]
	return recs


def receiving_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "awaiting":
		rows = _awaiting(cos)
		if chip == "ready":
			rows = [w for w in rows if w["ok"]]
		elif chip == "blocked":
			rows = [w for w in rows if not w["ok"]]
		if q:
			rows = [w for w in rows if q.lower() in (w["po"].supplier_name or "").lower() or q.lower() in w["po"].name.lower()]
		can = _perm("Purchase Receipt") and frappe.has_permission("Purchase Receipt", "create")
		return {"cols": [{"label": _("PO")}, {"label": _("Supplier")}, {"label": _("Outstanding"), "cls": "items"}, {"label": _("Shipment")}, {"label": _("Expected")},
			{"label": _("Check")}, {"label": ""}],
			"rows": [{"dt": "Purchase Order", "name": w["po"].name, "cells": [{"code": w["po"].name}, {"main": w["po"].supplier_name or w["po"].supplier}, {"lines": w["left"][:3]},
				{"link": ["Import Shipment", w["ship"][0]], "pill": w["ship"][1]} if w["ship"] else _("Local"),
				{"date": w["po"].schedule_date, "late": bool(w["po"].schedule_date and getdate(w["po"].schedule_date) < t)},
				{"text": w["check"], "tone": "green" if w["ok"] else "orange"},
				({"button": _("Receive"), "primary": 1, "make": "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt", "source": w["po"].name} if w["ok"] and can
					else {"button": _("Open shipment"), "open": ["Import Shipment", w["ship"][0]]} if w["ship"] else "")]} for w in rows],
			"empty": _("Nothing waiting — every open purchase order is received.")}
	if tab == "receipts":
		recs = _receipts(cos, frappe.utils.add_days(today(), -90), today())
		return {"cols": [{"label": _("Receipt")}, {"label": _("Date")}, {"label": _("PO")}, {"label": _("Supplier")}, {"label": _("Accepted"), "cls": "num"},
			{"label": _("Rejected"), "cls": "num"}, {"label": _("Warehouse")}, {"label": _("Value ({0})").format(cur), "cls": "num"}],
			"rows": [{"dt": "Purchase Receipt", "name": r.name, "cells": [{"code": r.name}, {"date": r.posting_date},
				{"link": ["Purchase Order", r.po[0]]} if r.po else "—", r.supplier_name or r.supplier, f"{r.acc:,.0f}",
				{"text": f"{r.rej:,.0f}", "tone": "red" if r.rej else ""}, ", ".join(w.rsplit(" - ", 1)[0] for w in r.wh) or "—", {"money": r.base_grand_total}]} for r in recs],
			"empty": _("No receipts in the last 90 days.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- LCs & Guarantees (v1.6.0 step 4)
LC_OPEN = ["Applied", "Issued", "Documents Presented", "Accepted"]


def _lcs(cos, filters=None):
	if not frappe.db.table_exists("Letter of Credit") or not _perm("Letter of Credit"):
		return []
	f = {"company": ["in", cos]}
	f.update(filters or {})
	return frappe.get_list("Letter of Credit", filters=f, fields=["name", "lc_number", "lc_type", "supplier", "customer", "party_name", "purchase_order", "import_shipment",
		"status", "issuing_bank", "currency", "amount", "base_amount", "margin_amount", "margin_entry", "margin_release_entry", "tenor", "latest_shipment_date", "expiry_date",
		"maturity_date", "trust_receipt", "tr_amount", "tr_due", "tr_interest", "tr_repaid_on", "discrepancies", "documents_presented_on"], order_by="creation desc", limit=300)


def _bgs(cos):
	if not _perm("Bank Guarantee"):
		return []
	f = {"docstatus": 1}
	if frappe.get_meta("Bank Guarantee").has_field("company"):
		f["company"] = ["in", cos]
	return frappe.get_list("Bank Guarantee", filters=f, fields=["name", "bg_type", "bank_guarantee_number", "name_of_beneficiary", "customer", "supplier", "amount",
		"start_date", "end_date", "bank", "margin_money"], order_by="end_date asc", limit=200)


def lc_module():
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	lcs = _lcs(cos)
	open_ = [l for l in lcs if l.status in LC_OPEN]
	bgs = [b for b in _bgs(cos) if not b.end_date or getdate(b.end_date) >= t]
	m_lc = sum(flt(l.margin_amount) for l in lcs if l.margin_entry and not l.margin_release_entry)
	m_bg = sum(flt(b.margin_money) for b in bgs)
	due = [l for l in open_ if l.maturity_date and not l.trust_receipt and t <= getdate(l.maturity_date) <= frappe.utils.add_days(t, 30)] + \
		[l for l in lcs if l.trust_receipt and not l.tr_repaid_on and l.tr_due and getdate(l.tr_due) <= frappe.utils.add_days(t, 30)]
	expiring = [l for l in open_ if l.status == "Issued" and l.expiry_date and t <= getdate(l.expiry_date) <= frappe.utils.add_days(t, 14)]
	applied = [l for l in open_ if l.status == "Applied"]
	return {
		"title": _("LCs & Guarantees"),
		"desc": _("Import letters of credit, trust receipts and bank guarantees — application, approval, bank issue, documents, extension, release and settlement — with cash due."),
		"new": [{"label": _("New LC application"), "doctype": "Letter of Credit", "primary": 1}, {"label": _("New bank guarantee"), "doctype": "Bank Guarantee"}],
		"kpis": [
			kpi(_("Open letters of credit"), sum(flt(l.base_amount) for l in open_), _("{0} LCs · issued to accepted").format(len(open_)), "blue", "file", True, cur, tab="lcs", chip="open"),
			kpi(_("Cash margin held"), m_lc + m_bg, _("LCs {0} · guarantees {1}").format(_fmt(m_lc, cur), _fmt(m_bg, cur)), "violet", "lock", True, cur, tab="lcs", chip="open"),
			kpi(_("Payments due in 30 days"), sum(flt(l.tr_amount if l.trust_receipt and not l.tr_repaid_on else l.base_amount) for l in due),
				_("{0} maturities & trust receipts").format(len(due)), "amber", "clock", True, cur, tab="due"),
			kpi(_("Expiring in 14 days"), len(expiring), _("Issued, documents not yet presented"), "red", "triangle-alert", tab="lcs", chip="expiring"),
			kpi(_("Awaiting approval"), len(applied), _("Applied — Finance Manager / MD"), "navy", "inbox", tab="lcs", chip="applied"),
		],
		"tabs": [
			{"key": "lcs", "label": _("Letters of credit"), "chips": [["open", _("Open")], ["applied", _("Applied")], ["expiring", _("Expiring")], ["all", _("All")]]},
			{"key": "bgs", "label": _("Bank guarantees ({0})").format(len(bgs)), "chips": []},
			{"key": "tr", "label": _("Trust receipts"), "chips": []},
			{"key": "due", "label": _("Payments due"), "chips": []},
		],
		"note": _("The bank issues the LC (SWIFT MT700) from its own portal — the ERP keeps the application, approvals, bank reference, documents, charges and payments."),
	}


def _lc_cells(l, cur, t):
	party = l.supplier or l.customer or l.party_name
	ship = frappe.db.get_value("Import Shipment", l.import_shipment, "status") if l.import_shipment else None
	if not ship and l.purchase_order:
		sh = _shipments([l.purchase_order]).get(l.purchase_order)
		if sh:
			l.import_shipment, ship = sh
	exp_late = bool(l.expiry_date and getdate(l.expiry_date) <= frappe.utils.add_days(t, 14) and l.status in ("Issued",))
	status = "Discrepant" if l.discrepancies and l.status == "Documents Presented" else l.status
	nxt = {"Applied": _("Approve & send to bank"), "Issued": _("Documents received"), "Documents Presented": _("Accept documents"),
		"Accepted": _("Settle at maturity")}.get(l.status)
	return [{"main": l.lc_number or l.name, "sub": l.name if l.lc_number else ""},
		{"main": party or "—", "sub": " · ".join(x for x in [l.purchase_order, l.issuing_bank] if x)},
		{"money": l.amount, "currency": l.currency, "sub": f"{cur} {flt(l.base_amount):,.2f}" if l.currency != cur else ""},
		_(l.tenor or "") or "—",
		{"main": frappe.utils.formatdate(l.latest_shipment_date, "dd MMM yyyy") if l.latest_shipment_date else "—",
			"sub": _("expires {0}").format(frappe.utils.formatdate(l.expiry_date, "dd MMM yyyy")) if l.expiry_date else "", "late": exp_late},
		{"link": ["Import Shipment", l.import_shipment], "pill": ship} if l.import_shipment else "—",
		{"pill": status, "tone": "red" if status == "Discrepant" else None},
		{"button": nxt, "open": ["Letter of Credit", l.name], "primary": 1} if nxt else ""]


def lc_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "lcs":
		lcs = _lcs(cos)
		if chip == "open":
			lcs = [l for l in lcs if l.status in LC_OPEN]
		elif chip == "applied":
			lcs = [l for l in lcs if l.status == "Applied"]
		elif chip == "expiring":
			lcs = [l for l in lcs if l.status == "Issued" and l.expiry_date and t <= getdate(l.expiry_date) <= frappe.utils.add_days(t, 14)]
		if q:
			ql = q.lower()
			lcs = [l for l in lcs if ql in (l.lc_number or l.name).lower() or ql in (l.supplier or l.party_name or "").lower()]
		return {"cols": [{"label": _("LC")}, {"label": _("Supplier · order")}, {"label": _("Amount"), "cls": "num"}, {"label": _("Terms")}, {"label": _("Ship by · expiry")},
			{"label": _("Shipment")}, {"label": _("Status")}, {"label": ""}],
			"rows": [{"dt": "Letter of Credit", "name": l.name, "cells": _lc_cells(l, cur, t)} for l in lcs], "empty": _("No letters of credit here.")}
	if tab == "bgs":
		bgs = _bgs(cos)
		return {"cols": [{"label": _("Guarantee")}, {"label": _("Type")}, {"label": _("Beneficiary")}, {"label": _("Bank")}, {"label": _("Amount"), "cls": "num"},
			{"label": _("Margin"), "cls": "num"}, {"label": _("Valid")}, {"label": _("Status")}],
			"rows": [{"dt": "Bank Guarantee", "name": b.name, "cells": [{"main": b.bank_guarantee_number or b.name, "sub": b.name if b.bank_guarantee_number else ""},
				_(b.bg_type or ""), b.name_of_beneficiary or b.customer or b.supplier or "—", b.bank or "—", {"money": b.amount}, {"money": b.margin_money} if b.margin_money else "—",
				{"main": frappe.utils.formatdate(b.end_date, "dd MMM yyyy") if b.end_date else "—", "sub": _("from {0}").format(frappe.utils.formatdate(b.start_date, "dd MMM yyyy")) if b.start_date else ""},
				{"pill": _("Expired") if b.end_date and getdate(b.end_date) < t else (_("Expiring") if b.end_date and getdate(b.end_date) <= frappe.utils.add_days(t, 30) else _("Valid")),
					"tone": "red" if b.end_date and getdate(b.end_date) < t else ("orange" if b.end_date and getdate(b.end_date) <= frappe.utils.add_days(t, 30) else "green")}]} for b in bgs],
			"empty": _("No bank guarantees.")}
	if tab == "tr":
		lcs = [l for l in _lcs(cos) if l.trust_receipt]
		return {"cols": [{"label": _("LC")}, {"label": _("Supplier")}, {"label": _("Trust receipt"), "cls": "num"}, {"label": _("Due")}, {"label": _("Interest"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Letter of Credit", "name": l.name, "cells": [{"main": l.lc_number or l.name}, l.supplier or l.party_name or "—", {"money": l.tr_amount},
				{"date": l.tr_due, "late": bool(l.tr_due and getdate(l.tr_due) < t and not l.tr_repaid_on)}, {"money": l.tr_interest},
				{"pill": _("Repaid") if l.tr_repaid_on else _("Open"), "tone": "green" if l.tr_repaid_on else "blue"}]} for l in lcs], "empty": _("No trust receipts.")}
	if tab == "due":
		rows = []
		for l in _lcs(cos):
			if l.status in LC_OPEN and l.maturity_date and not l.trust_receipt:
				rows.append((getdate(l.maturity_date), l, _("LC maturity"), flt(l.base_amount)))
			if l.trust_receipt and not l.tr_repaid_on and l.tr_due:
				rows.append((getdate(l.tr_due), l, _("Trust receipt"), flt(l.tr_amount) + flt(l.tr_interest)))
		rows.sort(key=lambda r: r[0])
		return {"cols": [{"label": _("Due")}, {"label": _("What")}, {"label": _("LC")}, {"label": _("Supplier")}, {"label": _("Bank")}, {"label": _("Amount ({0})").format(cur), "cls": "num"}],
			"rows": [{"dt": "Letter of Credit", "name": l.name, "cells": [{"date": d_, "late": d_ < t}, w, l.lc_number or l.name, l.supplier or l.party_name or "—", l.issuing_bank or "—",
				{"money": a}]} for d_, l, w, a in rows], "empty": _("Nothing due.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Dispatch & Delivery (v1.6.0 step 5)
SO_TO_DELIVER = ["To Deliver and Bill", "To Deliver"]
MK_DN = "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note"


def _so_items(names):
	out = {}
	for r in frappe.get_all("Sales Order Item", filters={"parent": ["in", names or [""]]}, fields=["parent", "item_name", "qty", "delivered_qty"], order_by="idx"):
		if flt(r.qty) > flt(r.delivered_qty):
			out.setdefault(r.parent, []).append(f"{flt(r.qty) - flt(r.delivered_qty):g} × {r.item_name}")
	return out


def _dispatch_data(cos):
	t = getdate(today())
	so = frappe.get_list("Sales Order", filters={"company": ["in", cos], "docstatus": 1, "status": ["in", SO_TO_DELIVER]},
		fields=["name", "customer_name", "delivery_date", "base_grand_total", "hs_is_export"] if frappe.get_meta("Sales Order").has_field("hs_is_export")
		else ["name", "customer_name", "delivery_date", "base_grand_total"], order_by="delivery_date asc", limit=200) if _perm("Sales Order") else []
	picks, pick_so = [], {}
	if _perm("Pick List"):
		picks = frappe.get_list("Pick List", filters={"company": ["in", cos], "docstatus": ["<", 2], "status": ["in", ["Draft", "Open"]]},
			fields=["name", "customer", "status", "docstatus", "owner"], order_by="creation desc", limit=100)
		for r in frappe.get_all("Pick List Item", filters={"parent": ["in", [p.name for p in picks] or [""]]}, fields=["parent", "sales_order"]):
			if r.sales_order:
				pick_so.setdefault(r.parent, set()).add(r.sales_order)
	dn_f = {"company": ["in", cos], "docstatus": ["<", 2], "is_return": 0}
	dns = frappe.get_list("Delivery Note", filters=dn_f, fields=["name", "customer_name", "posting_date", "docstatus", "per_billed", "status", "hs_delivery_status",
		"delivery_trip", "driver_name", "vehicle_no", "hs_received_by", "hs_pod_time", "base_grand_total"], order_by="posting_date desc", limit=200) if _perm("Delivery Note") else []
	return so, picks, pick_so, dns, t


def dispatch_module():
	cos, start, end, label, cur = _scope()
	so, picks, pick_so, dns, t = _dispatch_data(cos)
	ready = [d for d in dns if d.docstatus == 1 and (d.hs_delivery_status or "Ready to Dispatch") == "Ready to Dispatch"]
	out = [d for d in dns if d.docstatus == 1 and d.hs_delivery_status == "Out for Delivery"]
	done = [d for d in dns if d.docstatus == 1 and d.hs_delivery_status == "Delivered" and start <= getdate(d.hs_pod_time or d.posting_date) <= end]
	units = sum(flt(r.qty) for r in frappe.get_all("Delivery Note Item", filters={"parent": ["in", [d.name for d in done] or [""]]}, fields=["qty"]))
	# on time: delivered on or before the order's delivery date
	on_time = 0
	for d in done:
		so_name = frappe.db.get_value("Delivery Note Item", {"parent": d.name}, "against_sales_order")
		promised = frappe.db.get_value("Sales Order", so_name, "delivery_date") if so_name else None
		if not promised or getdate(d.hs_pod_time or d.posting_date) <= getdate(promised):
			on_time += 1
	return {
		"title": _("Dispatch & Delivery"),
		"desc": _("Coordinate picking, dispatch and customer delivery documentation — with drivers, trips and proof of delivery."),
		"new": [{"label": _("New delivery note"), "doctype": "Delivery Note", "primary": 1}, {"label": _("New delivery trip"), "doctype": "Delivery Trip"}],
		"kpis": [
			kpi(_("Orders to deliver"), len(so), _("{0} incl. VAT").format(_fmt(sum(flt(s.base_grand_total) for s in so), cur)), "blue", "list", tab="board"),
			kpi(_("Ready to dispatch"), len(ready), _("Delivery note made, not yet out"), "violet", "package", tab="notes", chip="ready"),
			kpi(_("Out for delivery"), len(out), _("On a delivery trip"), "amber", "truck", tab="notes", chip="out"),
			kpi(_("Delivered — {0}").format(label), len(done), _("{0} units").format(f"{units:,.0f}"), "green", "check", tab="notes", chip="delivered"),
			kpi(_("On-time delivery"), f"{round(on_time / len(done) * 100)}%" if done else "—", _("Delivered on or before the promised date"), "navy", "clock"),
		],
		"tabs": [
			{"key": "board", "label": _("Dispatch board"), "chips": []},
			{"key": "trips", "label": _("Delivery trips"), "chips": []},
			{"key": "notes", "label": _("Delivery notes"), "chips": [["all", _("All")], ["ready", _("Ready to dispatch")], ["out", _("Out for delivery")],
				["delivered", _("Delivered")], ["bill", _("Not invoiced")]]},
		],
	}


def dispatch_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	so, picks, pick_so, dns, t = _dispatch_data(cos)
	if tab == "board":
		picked = set().union(*pick_so.values()) if pick_so else set()
		items = _so_items([s.name for s in so])
		can_dn = frappe.has_permission("Delivery Note", "create")
		unbilled = {d.name for d in _to_bill(cos)}
		def promised(s):
			return _("Promised {0}").format(frappe.utils.formatdate(s.delivery_date, "dd MMM")) if s.delivery_date else ""
		cols = [
			{"label": _("To deliver"), "count": len([s for s in so if s.name not in picked]), "cards": [{"dt": "Sales Order", "name": s.name, "code": s.name, "title": s.customer_name,
				"lines": [", ".join(items.get(s.name, [])[:2]), promised(s)], "warn": _("Late") if s.delivery_date and getdate(s.delivery_date) < t else "",
				"button": {"label": _("Delivery note"), "make": MK_DN, "source": s.name} if can_dn else None} for s in so if s.name not in picked]},
			{"label": _("Picking & packing"), "count": len(picks), "cards": [{"dt": "Pick List", "name": p.name, "code": p.name, "pill": _("Draft") if p.docstatus == 0 else p.status,
				"title": p.customer or ", ".join(sorted(pick_so.get(p.name, []))), "lines": [", ".join(sorted(pick_so.get(p.name, []))), frappe.utils.get_fullname(p.owner)]} for p in picks]},
			{"label": _("Ready to dispatch"), "count": 0, "cards": []},
			{"label": _("Out for delivery"), "count": 0, "cards": []},
			{"label": _("Delivered (last 10 days)"), "count": 0, "cards": []},
		]
		for d in dns:
			if d.docstatus != 1:
				continue
			st = d.hs_delivery_status or "Ready to Dispatch"
			card = {"dt": "Delivery Note", "name": d.name, "code": d.name, "title": d.customer_name,
				"lines": [x for x in [" · ".join(y for y in [d.driver_name, d.vehicle_no, d.delivery_trip] if y)] if x]}
			if st == "Ready to Dispatch":
				cols[2]["cards"].append(card)
			elif st == "Out for Delivery":
				cols[3]["cards"].append(card)
			elif st == "Delivered" and getdate(d.hs_pod_time or d.posting_date) >= frappe.utils.add_days(t, -10):
				card["lines"] = [" · ".join(x for x in [frappe.utils.formatdate(d.hs_pod_time or d.posting_date, "dd MMM"), _("received by {0}").format(d.hs_received_by) if d.hs_received_by else ""] if x)]
				card["warn"] = _("Not invoiced") if d.name in unbilled else ""
				cols[4]["cards"].append(card)
		for c in cols[2:]:
			c["count"] = len(c["cards"])
		return {"kanban": cols, "kanban_cols": 5}
	if tab == "trips":
		if not _perm("Delivery Trip"):
			return {"cols": [], "rows": []}
		trips = frappe.get_list("Delivery Trip", filters={"company": ["in", cos], "docstatus": ["<", 2]}, fields=["name", "driver", "driver_name", "vehicle", "departure_time",
			"total_distance", "uom", "status", "docstatus"], order_by="departure_time desc", limit=100)
		stops = {}
		for r in frappe.get_all("Delivery Stop", filters={"parent": ["in", [x.name for x in trips] or [""]]}, fields=["parent"]):
			stops[r.parent] = stops.get(r.parent, 0) + 1
		phone = dict(frappe.get_all("Driver", filters={"name": ["in", [x.driver for x in trips if x.driver] or [""]]}, fields=["name", "cell_number"], as_list=True)) if _perm("Driver") else {}
		return {"cols": [{"label": _("Trip")}, {"label": _("Driver")}, {"label": _("Vehicle")}, {"label": _("Departure")}, {"label": _("Stops"), "cls": "num"},
			{"label": _("Distance"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Delivery Trip", "name": r.name, "cells": [{"code": r.name}, {"main": r.driver_name or "—", "sub": phone.get(r.driver) or ""}, r.vehicle or "—",
				frappe.utils.format_datetime(r.departure_time, "dd MMM yyyy HH:mm") if r.departure_time else "—", stops.get(r.name, 0),
				f"{flt(r.total_distance):g} {r.uom or 'km'}" if r.total_distance else "—", {"pill": _("Draft") if r.docstatus == 0 else r.status}]} for r in trips],
			"empty": _("No delivery trips yet.")}
	if tab == "notes":
		rows = [d for d in dns if d.docstatus == 1]
		if chip == "ready":
			rows = [d for d in rows if (d.hs_delivery_status or "Ready to Dispatch") == "Ready to Dispatch"]
		elif chip == "out":
			rows = [d for d in rows if d.hs_delivery_status == "Out for Delivery"]
		elif chip == "delivered":
			rows = [d for d in rows if d.hs_delivery_status == "Delivered"]
		elif chip == "bill":
			unbilled = {d.name for d in _to_bill(cos)}
			rows = [d for d in rows if d.name in unbilled]
		if q:
			rows = [d for d in rows if q.lower() in (d.customer_name or "").lower() or q.lower() in d.name.lower()]
		so_of = {}
		for r in frappe.get_all("Delivery Note Item", filters={"parent": ["in", [d.name for d in rows] or [""]]}, fields=["parent", "against_sales_order"]):
			if r.against_sales_order:
				so_of.setdefault(r.parent, r.against_sales_order)
		inv = {}
		for r in frappe.get_all("Sales Invoice Item", filters={"delivery_note": ["in", [d.name for d in rows] or [""]], "docstatus": 1}, fields=["parent", "delivery_note"]):
			inv.setdefault(r.delivery_note, r.parent)
		return {"cols": [{"label": _("Delivery note")}, {"label": _("Order")}, {"label": _("Customer")}, {"label": _("Date")}, {"label": _("Transport")},
			{"label": _("Value ({0})").format(cur), "cls": "num"}, {"label": _("Status")}, {"label": _("Invoice")}],
			"rows": [{"dt": "Delivery Note", "name": d.name, "cells": [{"code": d.name}, {"link": ["Sales Order", so_of[d.name]]} if so_of.get(d.name) else "—", {"main": d.customer_name},
				{"date": d.posting_date}, {"main": d.delivery_trip or "—", "sub": " — ".join(x for x in [d.driver_name, d.vehicle_no] if x)} if (d.delivery_trip or d.driver_name) else "—",
				{"money": d.base_grand_total}, {"pill": d.hs_delivery_status or "Ready to Dispatch"},
				{"link": ["Sales Invoice", inv[d.name]]} if inv.get(d.name) else {"text": _("To bill"), "tone": "orange"}]} for d in rows],
			"empty": _("No delivery notes here.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Finance & Management Visibility (v1.6.0 step 6)
FIN_ROLES = {"System Manager", "Managing Director", "Accounts Manager", "Accounts User", "Auditor"}


def _invoices(cos, filters=None):
	if not _perm("Sales Invoice"):
		return []
	f = {"company": ["in", cos], "docstatus": 1, "is_return": 0}
	f.update(filters or {})
	return frappe.get_list("Sales Invoice", filters=f, fields=["name", "customer", "customer_name", "posting_date", "due_date", "grand_total", "outstanding_amount",
		"currency", "conversion_rate", "base_grand_total", "base_net_total", "status"], order_by="posting_date desc", limit=500)


def _to_bill(cos):
	"""v1.6.1 (FIN-02): delivery notes with something left to invoice. ERPNext's per_billed falls below 100 when a credit
	note is issued against an invoice, so a fully invoiced delivery looked unbilled; count non-return invoice lines."""
	if not _perm("Delivery Note"):
		return []
	dns = frappe.get_list("Delivery Note", filters={"company": ["in", cos], "docstatus": 1, "is_return": 0, "per_billed": ["<", 100], "status": ["!=", "Closed"]},
		fields=["name", "customer_name", "posting_date", "base_grand_total", "grand_total", "per_billed"], order_by="posting_date asc", limit=300)
	if not dns:
		return []
	items = frappe.get_all("Delivery Note Item", filters={"parent": ["in", [d.name for d in dns]]}, fields=["name", "parent", "amount", "billed_amt"])
	billed = dict(frappe.db.sql("""select i.dn_detail, sum(i.amount) from `tabSales Invoice Item` i join `tabSales Invoice` s on s.name = i.parent
		where s.docstatus = 1 and s.is_return = 0 and i.dn_detail in %s group by i.dn_detail""", (tuple(i.name for i in items) or ("",),)))
	left, total = {}, {}
	for i in items:
		done = max(flt(billed.get(i.name)), flt(i.billed_amt))
		left[i.parent] = left.get(i.parent, 0) + max(0, flt(i.amount) - done)
		total[i.parent] = total.get(i.parent, 0) + flt(i.amount)
	out = []
	for d in dns:
		if left.get(d.name, 0) > 0.01 and total.get(d.name):
			share = left[d.name] / total[d.name]
			d.billed_pct = round((1 - share) * 100, 1)
			d.to_bill = flt(d.base_grand_total) * share
			out.append(d)
	return out


def finance_module():
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	inv_p = _invoices(cos, {"posting_date": ["between", [start, end]]})
	open_inv = _invoices(cos, {"outstanding_amount": [">", 0]})
	base = lambda r: flt(r.outstanding_amount) * flt(r.conversion_rate or 1)
	overdue = [r for r in open_inv if r.due_date and getdate(r.due_date) < t]
	pay = frappe.get_list("Purchase Invoice", filters={"company": ["in", cos], "docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["outstanding_amount", "conversion_rate", "due_date"], limit_page_length=0) if _perm("Purchase Invoice") else []
	pay_total = sum(flt(p.outstanding_amount) * flt(p.conversion_rate or 1) for p in pay)
	pay_30 = sum(flt(p.outstanding_amount) * flt(p.conversion_rate or 1) for p in pay if p.due_date and getdate(p.due_date) <= frappe.utils.add_days(t, 30))
	cash = None
	if set(frappe.get_roles()) & FIN_ROLES:
		from hipersign_trading.api.home import ledger

		cash = sum(ledger(c, start, end)["cash"] for c in cos)
	to_bill = _to_bill(cos)
	ages = [0, 0, 0, 0, 0]
	for r in open_inv:
		dd = (t - getdate(r.due_date)).days if r.due_date else -1
		ages[0 if dd <= 0 else 1 if dd <= 30 else 2 if dd <= 60 else 3 if dd <= 90 else 4] += base(r)
	n_pdc = frappe.db.count("Post Dated Cheque", {"company": ["in", cos], "status": ["in", ["In Hand", "Deposited", "Issued"]]}) \
		if frappe.db.table_exists("Post Dated Cheque") and _perm("Post Dated Cheque") else 0
	n_ret = len(frappe.get_list("Sales Invoice", filters={"company": ["in", cos], "is_return": 1, "docstatus": ["<", 2], "posting_date": [">=", frappe.utils.add_days(t, -90)]},
		pluck="name")) if _perm("Sales Invoice") else 0
	kpis = [
		kpi(_("Invoiced — {0}").format(label), sum(flt(r.base_net_total) for r in inv_p), _("Net of VAT"), "blue", "file", True, cur, tab="receivables", chip="all"),
		kpi(_("Outstanding receivables"), sum(base(r) for r in open_inv), _("{0} invoices").format(len(open_inv)), "violet", "clock", True, cur, tab="receivables", chip="open"),
		kpi(_("Overdue receivables"), sum(base(r) for r in overdue), _("{0} past due").format(len(overdue)), "red", "triangle-alert", True, cur, tab="receivables", chip="overdue"),
		kpi(_("Payables"), pay_total, _("{0} due in 30 days").format(_fmt(pay_30, cur)), "amber", "shopping-cart", True, cur, tab="payables"),
	]
	if cash is not None:
		kpis.append(kpi(_("Cash & bank"), cash, _("After receipts & payments"), "green", "banknote", True, cur, route=["query-report", "General Ledger"]))
	kpis.append(kpi(_("Delivered, not invoiced"), len(to_bill), _("{0} to bill").format(_fmt(sum(d.to_bill for d in to_bill), cur)),
		"navy", "flag", tab="tobill"))
	return {
		"title": _("Finance & Management Visibility"),
		"desc": _("Customer balances, supplier obligations, cash and profit — from the same documents the warehouse and sales teams use."),
		"new": [{"label": _("New invoice"), "doctype": "Sales Invoice"}, {"label": _("Receive payment"), "doctype": "Payment Entry", "primary": 1}],
		"kpis": kpis,
		"cards": [{"title": _("Receivables ageing"), "sub": _("Days past due"), "type": "bars", "currency": cur, "wide": 0,
			"rows": [[_("Not due"), ages[0]], ["1–30", ages[1]], ["31–60", ages[2]], ["61–90", ages[3]], ["90+", ages[4]]]}],
		"tabs": [
			{"key": "receivables", "label": _("Receivables"), "chips": [["open", _("Open")], ["overdue", _("Overdue")], ["all", _("All")]]},
			{"key": "payables", "label": _("Payables"), "chips": [["open", _("Open")], ["due", _("Due in 30 days")]]},
			{"key": "tobill", "label": _("To bill ({0})").format(len(to_bill)), "chips": []},
			{"key": "returns", "label": _("Returns & credit notes ({0})").format(n_ret), "chips": []},
			{"key": "cheques", "label": _("Cheques (PDC) ({0})").format(n_pdc), "chips": [["open", _("Open")], ["all", _("All")]]},
		],
		"links": [[_("Bank reconciliation"), ["bank-reconciliation-tool"]], [_("Cash flow"), ["query-report", "Cash Flow"]], [_("Profit & loss"), ["query-report", "Profit and Loss Statement"]]],
	}


def finance_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	can_pe = frappe.has_permission("Payment Entry", "create")
	if tab == "receivables":
		f = {"outstanding_amount": [">", 0]} if chip in ("open", "overdue") else {"posting_date": [">=", frappe.utils.add_days(t, -120)]}
		rows = _invoices(cos, f)
		if chip == "overdue":
			rows = [r for r in rows if r.due_date and getdate(r.due_date) < t]
		if q:
			rows = [r for r in rows if q.lower() in (r.customer_name or "").lower() or q.lower() in r.name.lower()]
		rows.sort(key=lambda r: (getdate(r.due_date) if r.due_date else t))
		def st(r):
			if flt(r.outstanding_amount) <= 0:
				return {"pill": _("Paid"), "tone": "green"}
			if r.due_date and getdate(r.due_date) < t:
				return {"pill": _("Overdue"), "tone": "red"}
			return {"pill": _("Part paid") if flt(r.outstanding_amount) < flt(r.grand_total) else _("Unpaid"), "tone": "orange" if flt(r.outstanding_amount) >= flt(r.grand_total) else "blue"}
		return {"cols": [{"label": _("Invoice")}, {"label": _("Customer")}, {"label": _("Date")}, {"label": _("Due")}, {"label": _("Total"), "cls": "num"},
			{"label": _("Outstanding"), "cls": "num"}, {"label": _("Status")}, {"label": ""}],
			"rows": [{"dt": "Sales Invoice", "name": r.name, "cells": [{"code": r.name}, {"main": r.customer_name}, {"date": r.posting_date},
				{"main": frappe.utils.formatdate(r.due_date, "dd MMM yyyy") if r.due_date else "—",
					"sub": _("{0} d overdue").format((t - getdate(r.due_date)).days) if r.due_date and getdate(r.due_date) < t and flt(r.outstanding_amount) > 0 else "", "late": True},
				{"money": r.grand_total, "currency": r.currency if r.currency != cur else None}, {"money": r.outstanding_amount, "currency": r.currency if r.currency != cur else None},
				st(r), {"button": _("Receive"), "primary": 1, "make": "hipersign_trading.api.panel.pay_sales_invoice", "source": r.name}
				if can_pe and flt(r.outstanding_amount) > 0 else ""]} for r in rows], "empty": _("No invoices here.")}
	if tab == "payables":
		if not _perm("Purchase Invoice"):
			return {"cols": [], "rows": []}
		rows = frappe.get_list("Purchase Invoice", filters={"company": ["in", cos], "docstatus": 1, "outstanding_amount": [">", 0]}, fields=["name", "supplier", "supplier_name",
			"bill_no", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency"], order_by="due_date asc", limit=300)
		if chip == "due":
			rows = [r for r in rows if r.due_date and getdate(r.due_date) <= frappe.utils.add_days(t, 30)]
		return {"cols": [{"label": _("Bill")}, {"label": _("Supplier")}, {"label": _("Supplier ref")}, {"label": _("Date")}, {"label": _("Due")}, {"label": _("Total"), "cls": "num"},
			{"label": _("Outstanding"), "cls": "num"}, {"label": ""}],
			"rows": [{"dt": "Purchase Invoice", "name": r.name, "cells": [{"code": r.name}, {"main": r.supplier_name or r.supplier}, r.bill_no or "—", {"date": r.posting_date},
				{"date": r.due_date, "late": bool(r.due_date and getdate(r.due_date) < t)}, {"money": r.grand_total, "currency": r.currency if r.currency != cur else None},
				{"money": r.outstanding_amount, "currency": r.currency if r.currency != cur else None},
				{"button": _("Pay"), "make": "hipersign_trading.api.panel.pay_purchase_invoice", "source": r.name} if can_pe else ""]} for r in rows],
			"empty": _("Nothing to pay.")}
	if tab == "tobill":
		dns = _to_bill(cos)
		can = frappe.has_permission("Sales Invoice", "create")
		return {"cols": [{"label": _("Delivery note")}, {"label": _("Customer")}, {"label": _("Delivered")}, {"label": _("Billed")}, {"label": _("To bill ({0})").format(cur), "cls": "num"}, {"label": ""}],
			"rows": [{"dt": "Delivery Note", "name": d.name, "cells": [{"code": d.name}, {"main": d.customer_name}, {"date": d.posting_date}, {"bar": d.billed_pct},
				{"money": d.to_bill},
				{"button": _("Invoice"), "primary": 1, "make": "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice", "source": d.name} if can else ""]} for d in dns],
			"empty": _("Everything delivered is invoiced.")}
	if tab == "returns":
		rows = frappe.get_list("Sales Invoice", filters={"company": ["in", cos], "is_return": 1, "docstatus": ["<", 2], "posting_date": [">=", frappe.utils.add_days(t, -90)]},
			fields=_fields("Sales Invoice", ["name", "customer_name", "posting_date", "return_against", "grand_total", "docstatus", "hs_return_reason"]), order_by="posting_date desc", limit=100) \
			if _perm("Sales Invoice") else []
		return {"cols": [{"label": _("Credit note")}, {"label": _("Customer")}, {"label": _("Date")}, {"label": _("Against")}, {"label": _("Reason")}, {"label": _("Amount"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Sales Invoice", "name": r.name, "cells": [{"code": r.name}, {"main": r.customer_name}, {"date": r.posting_date},
				{"link": ["Sales Invoice", r.return_against]} if r.return_against else "—", r.get("hs_return_reason") or "—", {"money": r.grand_total},
				{"pill": _("Waiting for Sales Manager") if r.docstatus == 0 else _("Issued"), "tone": "orange" if r.docstatus == 0 else "green"}]} for r in rows],
			"empty": _("No credit notes in the last 90 days.")}
	if tab == "cheques":
		if not (frappe.db.table_exists("Post Dated Cheque") and _perm("Post Dated Cheque")):
			return {"cols": [], "rows": []}
		f = {"company": ["in", cos]}
		if chip == "open":
			f["status"] = ["in", ["In Hand", "Deposited", "Issued", "Bounced"]]
		rows = frappe.get_list("Post Dated Cheque", filters=f, fields=["name", "cheque_no", "direction", "party", "amount", "cheque_date", "status", "drawn_on", "reference_name"],
			order_by="cheque_date asc", limit=200)
		return {"cols": [{"label": _("Cheque")}, {"label": _("Direction")}, {"label": _("Party")}, {"label": _("Bank")}, {"label": _("Cheque date")}, {"label": _("Against")},
			{"label": _("Amount"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Post Dated Cheque", "name": r.name, "cells": [{"main": r.cheque_no, "sub": r.name}, _(r.direction), r.party, r.drawn_on or "—",
				{"date": r.cheque_date, "late": bool(r.status == "In Hand" and r.cheque_date and getdate(r.cheque_date) <= t)}, r.reference_name or "—", {"money": r.amount},
				{"pill": r.status, "tone": {"In Hand": "blue", "Deposited": "violet", "Cleared": "green", "Bounced": "red", "Issued": "orange", "Replaced": "grey"}.get(r.status, "grey")}]}
				for r in rows], "empty": _("No cheques here.")}
	return {"cols": [], "rows": []}
