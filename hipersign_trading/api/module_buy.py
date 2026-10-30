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
			kpi(_("Ordered — {0}").format(label), sum(flt(r.base_grand_total) for r in ordered), _("{0} orders").format(len(ordered)), "navy", "chart", True, cur, tab="orders", chip="all"),
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
