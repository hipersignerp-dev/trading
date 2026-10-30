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
