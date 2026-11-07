"""v1.8.0 (prototype p19): the Manufacturing pages — Production, Planning, BOMs & routings, Quality and Costing on the module
page renderer (hs_module.js), plus the data of the Shop floor (tablet view) and the Production Tracker (hs_manufacturing.js).
Figures, step states and red flags come from api.manufacturing (one place for the rules)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

from hipersign_trading.api import manufacturing as M
from hipersign_trading.api.module import _perm, _scope, kpi

KEYS = ("mf_prod", "mf_plan", "mf_bom", "mf_qc", "mf_cost")
ACT = "hipersign_trading.api.manufacturing.act"


def _cos():
	return M.companies(_scope()[0])


def _cur(cos=None):
	return M.currency(cos if cos is not None else _cos())


def _m(v, cur):
	"""v1.8.4: amounts in KPI sub-lines and card notes are compact ("AED 5.3M"), as on the other pages — they showed full
	precision ("AED 5,320,401.99") and pushed the cards wide."""
	from hipersign_trading.api.module import _fmt

	return _fmt(v, cur or "")


def _short(v, cur):
	v = flt(v)
	return f"{cur} {v / 1e6:.2f}M" if abs(v) >= 1e6 else f"{cur} {v / 1e3:.1f}K" if abs(v) >= 1e4 else f"{cur} {v:,.0f}"


def _btn(label, action, name, primary=False, args=None, confirm=None):
	return {"button": label, "act": action, "name": name, "args": args or {}, "primary": 1 if primary else 0, "confirm": confirm, "method": ACT}


def _icell(code):
	it = M.item_info(code)
	return {"main": it.item_name, "sub": f"{code} · {_(it.item_group or '')}"}


def _wocell(f):
	return {"main": f.name, "sub": f.item_name}


def _empty():
	return _("No manufacturing company in this scope yet — create a BOM and a work order (Manufacturing must be switched on).")


def _pill(state):
	return {"pill": _(state), "tone": M.STATE_TONE.get(state, "grey")}


def how_block():
	return {"type": "how", "span": 3, "title": _("How it works — the manufacturing process"), "sub": _("22 steps from sales order to closed work order"),
		"phases": [{"name": _(n), "a": a, "b": b} for n, a, b in M.PHASES],
		"steps": [{"name": _(s[0]), "short": _(s[1]), "what": _(s[2]), "who": _(s[3]), "docs": _(s[4]), "approval": _(s[5]), "next": _(s[6])} for s in M.STEPS]}


# ================================================================ Production
def _wos(cos):
	return [M.wo_fig(n) for n in M.wo_names(cos)]


def _output(cos, day):
	return flt(frappe.db.sql("""select sum(sed.transfer_qty) from `tabStock Entry` se join `tabStock Entry Detail` sed on sed.parent = se.name where se.docstatus = 1
		and se.purpose = 'Manufacture' and sed.is_finished_item = 1 and se.company in %s and se.posting_date = %s""", (tuple(cos or [""]), day))[0][0])


def _plan_day(W, day):
	"""The day's plan: every open work order spread evenly over its working days (Friday off)."""
	d = getdate(day)
	if d.weekday() == 4:
		return 0
	t = 0.0
	for f in W:
		if f.state in ("Draft", "Cancelled") or not f.start or not f.due:
			continue
		if f.start <= d and (d <= f.due or f.late):  # a late order stays in the plan until it is finished
			days = max(1, sum(1 for k in range(date_diff(f.due, f.start) + 1) if getdate(add_days(f.start, k)).weekday() != 4))
			t += f.qty / days
	return round(t)


def _wip(cos):
	whs = [M.whs(c).wip for c in cos]
	return flt(frappe.db.sql("select sum(stock_value) from `tabBin` where warehouse in %s", (tuple(whs or [""]),))[0][0])


def mf_prod_module():
	cos = _cos()
	cur = _cur(cos)
	W = _wos(cos)
	open_ = [f for f in W if f.state in ("In process", "Final QC")]
	late = [f for f in W if f.late]
	last = add_days(today(), -1)
	out = _output(cos, last) + _output(cos, today())
	plan = _plan_day(W, last) or _plan_day(W, today())
	recent = [f for f in W if f.start and f.start >= getdate(add_days(today(), -60))]
	scrap, made = sum(f.scrap for f in recent), sum(f.done for f in recent)
	L = sorted(M.load(cos), key=lambda x: -x.pct) if cos else []
	co = cos[0] if cos else ""
	loc = frappe.db.get_value("Address", frappe.db.get_value("Dynamic Link", {"link_doctype": "Company", "link_name": co, "parenttype": "Address"}, "parent"), "city") if co else ""
	return {
		"title": _("Production"),
		"desc": _("{0} — today's work orders, output against plan, work in progress, late orders and the load on every workstation.").format(" · ".join(x for x in [co, loc] if x)),
		"new": [{"label": _("Manufacture entry"), "doctype": "Stock Entry:manufacture"}, {"label": _("New work order"), "doctype": "Work Order", "primary": 1}],
		"links": [[_("Production Tracker"), ["production-tracker"]], [_("Shop floor"), ["hipersign-shopfloor"]]],
		"kpis": [
			kpi(_("Work orders in process"), len(open_), _("{0} released or planned").format(len([f for f in W if f.state in ("Not started", "Draft")])), "blue", "wrench", tab="wo"),
			kpi(_("Output — last day vs plan"), f"{out:,.0f} / {plan:,.0f}", _("Units received to finished goods"), "green" if out >= plan else "amber", "package"),
			kpi(_("Work in progress (WIP)"), _wip(cos), _("Materials issued, not yet finished"), "violet", "layers", True, cur),
			kpi(_("Late work orders"), len(late), ", ".join(f.name[-4:] for f in late) or _("None"), "red" if late else "green", "triangle-alert", tab="wo"),
			kpi(_("Scrap rate — 60 days"), f"{scrap / max(1, made + scrap) * 100:.1f}%", _("{0} units scrapped").format(f"{scrap:,.0f}"), "amber", "chart-column",
				route=["hipersign-quality"]),
			kpi(_("Busiest workstation"), L[0].name if L else "—", _("{0}% loaded · next 3 days").format(round(L[0].pct) if L else 0), "navy", "activity", tab="load"),
		],
		"tabs": [{"key": "today", "label": _("Today"), "chips": []}, {"key": "wo", "label": _("Work orders"), "chips": [["all", _("All")], ["open", _("Open")],
			["late", _("Late or on hold")], ["done", _("Completed")]]}, {"key": "load", "label": _("Workstation load"), "chips": []},
			{"key": "ent", "label": _("Stock entries"), "chips": []}, {"key": "how", "label": _("How it works"), "chips": []}],
		"nosearch": 0,
	}


def _wo_rows(W, cur):
	rows = []
	for f in W:
		st = _pill(f.state)
		if f.hold and f.state in ("Draft", "Not started"):
			st["sub"], st["late"] = _("On hold — {0}").format(f.hold), 1
		elif f.late:
			st["sub"], st["late"] = _("Late"), 1
		so = M.so_fig(f.so) if f.so and frappe.db.exists("Sales Order", f.so) else None
		rows.append({"dt": "Work Order", "name": f.name, "cells": [_wocell(f), {"main": f.so, "sub": so.customer_name} if so else "—", flt(f.qty), {"bar": f.pct},
			{"main": f"{f.done:,.0f}", "sub": _("{0} scrap").format(f"{f.scrap:,.0f}")},
			{"main": f"{M._fds(f.start)} → {M._fds(f.due)}", "late": f.late, "sub": _("late") if f.late else ""},
			{"money": f.std.total * f.qty, "currency": cur}, st]})
	return rows


def _wo_cols():
	return [{"label": _("Work order")}, {"label": _("Sales order")}, {"label": _("Qty"), "cls": "num"}, {"label": _("Produced")}, {"label": _("Done · scrap")},
		{"label": _("Start → due")}, {"label": _("Std cost value"), "cls": "num"}, {"label": _("Status")}]


def mf_prod_rows(tab, chip, q=None):
	cos = _cos()
	cur = _cur(cos)
	if not cos:
		return {"cols": [], "rows": [], "empty": _empty()}
	if tab == "how":
		return {"blocks": [how_block()]}
	W = _wos(cos)
	if tab == "wo":
		sel = {"open": lambda f: f.state not in ("Completed", "Closed", "Cancelled"), "late": lambda f: f.late or (f.hold and f.state in ("Draft", "Not started")),
			"done": lambda f: f.state in ("Completed", "Closed")}.get(chip or "all", lambda f: True)
		W = [f for f in W if sel(f) and (not q or q.lower() in f"{f.name} {f.item_name} {f.so or ''} {f.customer or ''}".lower())]
		return {"title": _("Work orders"), "cols": _wo_cols(), "rows": _wo_rows(W, cur), "empty": _("No work orders."), "nototal": 0}
	if tab == "load":
		L = M.load(cos)
		return {"blocks": [
			{"type": "card", "span": 1, "card": {"title": _("Workstation load — next 3 working days"), "sub": _("% of capacity"), "type": "bars", "count": 1, "pct": 1,
				"rows": [[x.name, round(x.pct)] for x in L]}},
			{"type": "table", "span": 2, "title": _("Workstations"), "sub": _("Open work orders, remaining quantity × routing minutes"),
				"cols": [{"label": _("Workstation")}, {"label": _("Capacity h/day"), "cls": "num"}, {"label": _("Hours booked"), "cls": "num"}, {"label": _("Load")},
					{"label": _("Rate / hour"), "cls": "num"}],
				"rows": [{"dt": "Workstation", "name": x.ws, "cells": [{"main": x.name, "sub": x.ws}, flt(x.cap), flt(x.hrs, 1), {"bar": x.pct}, {"money": x.lab + x.ovh, "currency": cur}]}
					for x in L]}]}
	if tab == "ent":
		ses = frappe.get_list("Stock Entry", filters={"company": ["in", cos], "docstatus": 1, "purpose": ["in", ["Manufacture", "Material Transfer for Manufacture"]]},
			fields=["name", "purpose", "posting_date", "work_order", "fg_completed_qty", "process_loss_qty", "total_incoming_value", "total_outgoing_value", "hs_picked_by"],
			order_by="posting_date desc, name desc", limit_page_length=60) if _perm("Stock Entry") else []
		rows = []
		for e in ses:
			mf = e.purpose == "Manufacture"
			fg = frappe.db.get_value("Stock Entry Detail", {"parent": e.name, "is_finished_item": 1}, ["item_name", "qty", "batch_no"], as_dict=True) if mf else None
			n = frappe.db.count("Stock Entry Detail", {"parent": e.name})
			rows.append({"dt": "Stock Entry", "name": e.name, "cells": [{"code": e.name}, {"pill": _("Manufacture") if mf else _("Transfer to WIP"), "tone": "green" if mf else "blue"},
				{"date": e.posting_date}, e.work_order, (_("{0} × {1} · batch {2}").format(f"{flt(fg.qty):,.0f}", fg.item_name, fg.batch_no or "—") if fg else "—") if mf
				else _("{0} components").format(n), {"money": e.total_incoming_value if mf else e.total_outgoing_value, "currency": cur}]})
		return {"title": _("Manufacture entries & material transfers"), "cols": [{"label": _("Entry")}, {"label": _("Type")}, {"label": _("Date")}, {"label": _("Work order")},
			{"label": _("Detail")}, {"label": _("Value"), "cls": "num"}], "rows": rows, "empty": _("No entries yet."),
			"actions": [{"label": _("Transfer to WIP"), "new": "Stock Entry:wip"}, {"label": _("Manufacture entry"), "new": "Stock Entry:manufacture", "primary": 1}]}
	# today
	live = [f for f in W if f.state in ("In process", "Final QC")]
	tiles = [{"dt": "Work Order", "name": f.name, "code": f.name, "pill": _(f.state), "tone": f.tone, "late": _("Late") if f.late else "", "title": f.item_name,
		"big": f"{f.done:,.0f}", "of": f"{f.qty:,.0f}", "bar": f.pct, "chips": [{"label": f"{o.idx * 10} {M.ws_rates(o.ws).workstation_name.split(' ')[0]}",
		"st": {"Completed": "done", "Work in progress": "cur", "On hold": "hold"}.get(o.state, ""), "title": o.op} for o in f.ops]} for f in live]
	days = [add_days(today(), -k) for k in range(6, -1, -1)]
	late = [f for f in W if f.late or (f.hold and f.state in ("Draft", "Not started"))]
	return {"blocks": [
		{"type": "tiles", "span": 3, "title": _("Today on the floor"), "sub": _("Live from the job cards"), "tiles": tiles, "empty": _("Nothing in process.")},
		{"type": "card", "span": 1, "card": {"title": _("Output vs plan — last 7 days"), "sub": _("Units to finished goods · Friday off"), "type": "cols", "count": 1,
			"labels": [getdate(d).strftime("%d %b") for d in days], "series": [{"name": _("Plan (units)"), "color": "grey", "data": [_plan_day(W, d) for d in days]},
			{"name": _("Output"), "color": "blue", "data": [_output(cos, d) for d in days]}]}},
		{"type": "table", "span": 2, "title": _("Late or on hold"), "cols": _wo_cols(), "rows": _wo_rows(late, cur), "empty": _("Nothing late or on hold.")},
	]}


# ================================================================ Planning
def mf_plan_module():
	cos = _cos()
	cur = _cur(cos)
	SO = [M.so_fig(s) for s in M.so_names(cos)] if cos and _perm("Sales Order") else []  # v1.8.2: buyers have no Sales Order read
	opn = [s for s in SO if s.step < 18]
	W = _wos(cos) if cos else []
	SH = M.shortages(cos) if cos else []
	mrs = frappe.get_list("Material Request", filters={"company": ["in", cos or [""]], "docstatus": ["<", 2], "material_request_type": "Purchase",
		"status": ["not in", ["Ordered", "Received", "Stopped", "Cancelled"]]}, fields=["name", "docstatus"], limit_page_length=0) if _perm("Material Request") else []
	short = [x for x in SH if x.short > 0]
	waiting = [x for x in SH if x.short_now > 0 and x.short <= 0]
	return {
		"title": _("Planning"),
		"desc": _("Sales orders and forecast → production plan → work orders and material requests, with component shortages and suggested purchase orders."),
		"new": [{"label": _("New production plan"), "doctype": "Production Plan", "primary": 1}],
		"links": [[_("Production Tracker"), ["production-tracker"]]],
		"kpis": [
			kpi(_("Open demand"), _("{0} units").format(f"{sum(s.qty for s in opn):,.0f}"), _("{0} orders incl. forecast").format(len(opn)), "navy", "tag", tab="demand"),
			kpi(_("Planned production"), f"{sum(max(0, f.qty - f.done - f.scrap) for f in W if f.state not in ('Completed', 'Closed', 'Cancelled')):,.0f}",
				_("Units on open work orders"), "blue", "wrench"),
			kpi(_("Component shortages"), len(short), (", ".join(x.item for x in short) or _("None")) + (_(" · {0} waiting for open POs").format(len(waiting)) if waiting else ""),
				"red" if short else "green", "triangle-alert", tab="short"),
			kpi(_("Suggested purchase orders"), sum(x.sug * x.cost for x in SH), _("{0} components from Shenzhen / Ningbo").format(len([x for x in SH if x.sug])), "violet",
				"shopping-cart", True, cur, tab="short"),
			kpi(_("Material requests open"), len(mrs), _("{0} awaiting approval").format(len([m for m in mrs if m.docstatus == 0])), "amber", "list", tab="mr"),
		],
		"tabs": ([{"key": "demand", "label": _("Demand"), "chips": []}] if _perm("Sales Order") else []) + [{"key": "pp", "label": _("Production plans"), "chips": []},
			{"key": "short", "label": _("Shortages") + (f" ({len(short)})" if short else ""), "chips": []}, {"key": "mr", "label": _("Material requests"), "chips": []},
			{"key": "po", "label": _("Purchase orders"), "chips": []}],
	}


def mf_plan_rows(tab, chip, q=None):
	cos = _cos()
	cur = _cur(cos)
	if not cos:
		return {"cols": [], "rows": [], "empty": _empty()}
	if tab == "pp":
		P = frappe.get_list("Production Plan", filters={"company": ["in", cos], "docstatus": ["<", 2]}, fields=["name", "posting_date", "owner", "status", "docstatus"],
			order_by="posting_date desc, name desc", limit_page_length=0) if _perm("Production Plan") else []
		rows = []
		for p in P:
			sos = frappe.get_all("Production Plan Sales Order", filters={"parent": p.name}, pluck="sales_order")
			wos = frappe.get_all("Work Order", filters={"production_plan": p.name, "docstatus": ["<", 2]}, pluck="name", order_by="name asc")
			mrs = frappe.db.sql_list("select distinct parent from `tabMaterial Request Item` where production_plan = %s and docstatus < 2", p.name)
			st = "Draft" if p.docstatus == 0 else p.status
			rows.append({"dt": "Production Plan", "name": p.name, "cells": [{"main": p.name, "sub": f"{frappe.utils.formatdate(p.posting_date)} · {frappe.utils.get_fullname(p.owner)}"},
				{"lines": sos}, {"lines": wos}, {"lines": mrs}, {"pill": _(st), "tone": "green" if st == "Completed" else "blue" if st != "Draft" else "grey"}]})
		return {"title": _("Production plans"), "sub": _("Sales orders → production plan → work orders + material requests"), "nototal": 1,
			"cols": [{"label": _("Plan")}, {"label": _("Sales orders")}, {"label": _("Work orders")}, {"label": _("Material requests")}, {"label": _("Status")}], "rows": rows,
			"empty": _("No production plans yet."), "actions": [{"label": _("Plan all open orders"), "method": ACT, "args": {"action": "plan", "name": "open"}, "primary": 1}]}
	if tab == "short":
		SH = M.shortages(cos)
		rows = []
		for x in SH:
			act = _btn(_("Raise PO"), "raise_po", x.item, True, {"qty": x.sug, "company": x.company},
				_("Order {0} × {1} from {2}?").format(f"{x.sug:,.0f}", M.item_info(x.item).item_name, x.supplier or "—")) if x.sug else \
				({"pill": _("Covered by {0}").format(x.po), "tone": "blue", "sub": _("ETA {0}").format(M._fds(x.eta))} if x.short_now > 0 and x.po else "")
			rows.append({"dt": "Item", "name": x.item, "cells": [_icell(x.item), flt(x.need), flt(x.stock), flt(x.on_order) or "—",
				{"text": f"{x.short_now:,.0f}", "tone": "red" if x.short_now else "green"}, {"text": f"{x.short:,.0f}", "tone": "red" if x.short else "green"},
				{"main": f"{x.sug:,.0f} · {x.supplier or '—'}", "sub": _("{0} · by air, 7 days").format(_m(x.sug * x.cost, cur))} if x.sug else "—", act]})
		return {"title": _("Material availability & shortages (MRP)"), "sub": _("Open work orders not yet issued, against usable stock and open purchase orders"), "nototal": 1,
			"cols": [{"label": _("Component")}, {"label": _("Required"), "cls": "num"}, {"label": _("In stock (usable)"), "cls": "num"}, {"label": _("On order"), "cls": "num"},
				{"label": _("Short now")}, {"label": _("Shortage after POs")}, {"label": _("Suggested PO")}, {"label": ""}], "rows": rows,
			"empty": _("No open work orders waiting for components."), "actions": [{"label": _("Run MRP"), "method": ACT, "args": {"action": "mrp", "name": "all"}}]}
	if tab == "mr":
		R = frappe.db.sql("""select mr.name, mr.transaction_date, mr.docstatus, mr.status, mr.terms, mri.item_code, mri.qty, mri.schedule_date, mri.ordered_qty
			from `tabMaterial Request` mr join `tabMaterial Request Item` mri on mri.parent = mr.name where mr.company in %s and mr.docstatus < 2
			and mr.material_request_type = 'Purchase' order by mr.transaction_date desc, mr.name desc""", (tuple(cos),), as_dict=True) if _perm("Material Request") else []
		rows = []
		for m in R:
			po = frappe.db.get_value("Purchase Order Item", {"material_request": m.name, "docstatus": ["<", 2]}, "parent")
			st = _("Pending approval") if m.docstatus == 0 else _(m.status)
			act = _btn(_("Approve"), "mr_approve", m.name, True) if m.docstatus == 0 else (_btn(_("Order"), "mr_po", m.name) if not po and m.status not in ("Stopped", "Cancelled") else "")
			rows.append({"dt": "Material Request", "name": m.name, "cells": [{"main": m.name, "sub": frappe.utils.formatdate(m.transaction_date)}, _icell(m.item_code), flt(m.qty),
				{"date": m.schedule_date}, (m.terms or "").replace(" freight", "") or "—", po or "—", {"pill": st, "tone": "orange" if m.docstatus == 0 else "blue"}, act]})
		return {"title": _("Material requests"), "sub": _("Imported components go through Trading → Purchase Orders and Imports & Shipments"), "nototal": 1,
			"cols": [{"label": _("Request")}, {"label": _("Component")}, {"label": _("Qty"), "cls": "num"}, {"label": _("Needed")}, {"label": _("Mode")}, {"label": _("Purchase order")},
				{"label": _("Status")}, {"label": ""}], "rows": rows, "empty": _("No material requests.")}
	if tab == "po":
		comps = [r.name for r in frappe.get_all("Item", filters={"is_purchase_item": 1, "include_item_in_manufacturing": 1}, fields=["name"])]
		R = frappe.db.sql("""select po.name, po.supplier, po.status, po.docstatus, po.schedule_date, po.workflow_state, pi.item_code, pi.qty, pi.received_qty, pi.base_net_amount
			from `tabPurchase Order` po join `tabPurchase Order Item` pi on pi.parent = po.name where po.company in %s and po.docstatus < 2 and pi.item_code in %s
			order by po.transaction_date desc, po.name desc limit 60""", (tuple(cos), tuple(comps or [""])), as_dict=True) if _perm("Purchase Order") else []
		rows = []
		for p in R:
			mode = frappe.db.get_value("Material Request", frappe.db.get_value("Purchase Order Item", {"parent": p.name}, "material_request"), "terms") or ""
			st = p.workflow_state if p.docstatus == 0 and p.workflow_state else _("Draft") if p.docstatus == 0 else _("Received") if flt(p.received_qty) >= flt(p.qty) else _(p.status)
			act = _btn(_("Receive"), "po_receive", p.name, confirm=_("Receive {0} into the components store?").format(p.name)) if p.docstatus == 1 and flt(p.received_qty) < flt(p.qty) else ""
			rows.append({"dt": "Purchase Order", "name": p.name, "cells": [{"code": p.name}, p.supplier, M.item_info(p.item_code).item_name, flt(p.qty),
				{"money": p.base_net_amount, "currency": cur}, mode.replace(" freight", "") or "—", {"date": p.schedule_date, "late": p.docstatus == 1 and flt(p.received_qty) < flt(p.qty)
				and p.schedule_date and getdate(p.schedule_date) < getdate(today())}, {"pill": st, "tone": "green" if st == _("Received") else "blue"}, act]})
		return {"title": _("Component purchase orders (imports from China)"), "cols": [{"label": _("PO")}, {"label": _("Supplier")}, {"label": _("Component")},
			{"label": _("Qty"), "cls": "num"}, {"label": _("Value"), "cls": "num"}, {"label": _("Mode")}, {"label": _("ETA")}, {"label": _("Status")}, {"label": ""}], "rows": rows,
			"empty": _("No component purchase orders.")}
	# demand
	rows = []
	for s in ([M.so_fig(n) for n in M.so_names(cos)] if _perm("Sales Order") else []):
		if q and q.lower() not in f"{s.name} {s.customer_name} {s.item_name}".lower():
			continue
		i = min(M.N - 1, s.step)
		rows.append({"dt": "Sales Order", "name": s.name, "cells": [{"main": s.name, "sub": _("Forecast") if s.forecast else ""},
			{"main": s.customer_name, "sub": " · ".join(x for x in [s.city, _("export") if s.export else ""] if x)}, s.item_name, flt(s.qty), {"date": s.due},
			{"money": s.qty * s.rate, "currency": cur}, s.wo or "—", {"main": f"{min(M.N, s.step + 1)}", "sub": _(M.STEPS[i][1])}]})
	return {"title": _("Demand — sales orders and forecast"), "cols": [{"label": _("Order")}, {"label": _("Customer")}, {"label": _("Product")}, {"label": _("Qty"), "cls": "num"},
		{"label": _("Due")}, {"label": _("Order value"), "cls": "num"}, {"label": _("Work order")}, {"label": _("Step")}], "rows": rows, "empty": _("No orders for manufactured products."),
		"actions": [{"label": _("Plan all open orders"), "method": ACT, "args": {"action": "plan", "name": "open"}, "primary": 1}]}


# ================================================================ BOMs & routings
def _products(cos):
	return [r.item for r in frappe.get_all("BOM", filters={"company": ["in", cos or [""]], "docstatus": 1, "is_active": 1, "is_default": 1}, fields=["item"], order_by="item asc")]


def mf_bom_module():
	cos = _cos()
	cur = _cur(cos)
	P = _products(cos)
	B = frappe.get_list("BOM", filters={"company": ["in", cos or [""]], "docstatus": 1}, fields=["name", "is_active", "is_default"], limit_page_length=0) if cos and _perm("BOM") else []
	comps = {r.item_code for r in frappe.get_all("BOM Item", filters={"parent": ["in", [b.name for b in B] or [""]]}, fields=["item_code"])} - set(P)
	k = [kpi(_("Active BOMs"), len([b for b in B if b.is_active]), _("{0} versions kept").format(len(B)), "navy", "layers", tab="ver"),
		kpi(_("Components"), len(comps), _("Imported from Shenzhen, Dongguan, Zhongshan, Ningbo"), "violet", "package", tab="wu")]
	for p in P[:4]:
		s = M.std(p)
		k.append(kpi(_("Standard cost — {0}").format(M.item_info(p).item_name.replace("LED ", "")), s.total, _("Material {0}% · labour & overhead {1}%").format(
			round(s.mat / s.total * 100) if s.total else 0, round((s.lab + s.ovh) / s.total * 100) if s.total else 0), "blue", "calculator", True, cur, tab="tree", chip=p))
	return {
		"title": _("BOMs & routings"),
		"desc": _("Bills of materials with sub-assemblies, routings by workstation, standard cost roll-up, versions and where-used."),
		"new": [{"label": _("New BOM"), "doctype": "BOM", "primary": 1}],
		"kpis": k,
		"tabs": [{"key": "tree", "label": _("BOM tree & cost"), "chips": [[p, M.item_info(p).item_name] for p in P]}, {"key": "ver", "label": _("Versions"), "chips": []},
			{"key": "wu", "label": _("Where used"), "chips": [[c, c] for c in sorted(comps)]}, {"key": "ws", "label": _("Workstations"), "chips": []}],
		"nosearch": 1,
	}


def _print(dt, name, fmt):
	return f"/printview?doctype={frappe.utils.quote(dt)}&name={frappe.utils.quote(name)}&format={frappe.utils.quote(fmt)}"


def mf_bom_rows(tab, chip, q=None):
	cos = _cos()
	cur = _cur(cos)
	if not cos:
		return {"cols": [], "rows": [], "empty": _empty()}
	P = _products(cos)
	if tab == "ver":
		B = frappe.get_list("BOM", filters={"company": ["in", cos], "docstatus": 1}, fields=["name", "item", "item_name", "is_active", "is_default", "creation", "hs_change_note", "total_cost"],
			order_by="item asc, name desc", limit_page_length=0)
		rows = [{"dt": "BOM", "name": b.name, "cells": [{"code": b.name}, b.item_name, {"text": f"v{cint(b.name.split('-')[-1])}"}, frappe.db.count("BOM Item", {"parent": b.name}),
			{"money": M.std_of_bom(b.name).total, "currency": cur} if b.is_active and b.is_default else "—", {"date": getdate(b.creation)}, b.hs_change_note or "",
			{"pill": _("Active") if b.is_active and b.is_default else _("Superseded") if not b.is_active else _("Alternate"), "tone": "green" if b.is_active and b.is_default else "grey"},
			{"url": _print("BOM", b.name, "Hipersign Bill of Materials"), "label": _("Print")}]} for b in B]
		return {"title": _("Versions"), "nototal": 1, "cols": [{"label": _("BOM")}, {"label": _("Product")}, {"label": _("Version")}, {"label": _("Components"), "cls": "num"},
			{"label": _("Std cost"), "cls": "num"}, {"label": _("Since")}, {"label": _("Change note")}, {"label": _("Status")}, {"label": ""}], "rows": rows,
			"actions": [{"label": _("New BOM"), "new": "BOM", "primary": 1}]}
	if tab == "wu":
		comp = chip
		if not comp:
			return {"cols": [], "rows": [], "empty": _("Pick a component.")}
		R = frappe.db.sql("""select b.name, b.item, b.item_name, b.is_active, b.is_default, bi.qty, b.quantity from `tabBOM Item` bi join `tabBOM` b on b.name = bi.parent
			where bi.item_code = %s and b.docstatus = 1 and b.company in %s order by b.item, b.name""", (comp, tuple(cos)), as_dict=True)
		return {"title": _("Where used — {0}").format(M.item_info(comp).item_name), "sub": _("Which products are affected by a component change or shortage"), "nototal": 1,
			"cols": [{"label": _("BOM")}, {"label": _("Product")}, {"label": _("Qty per unit"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "BOM", "name": r.name, "cells": [{"code": r.name}, r.item_name, flt(flt(r.qty) / (flt(r.quantity) or 1), 3),
				{"pill": _("Active") if r.is_active and r.is_default else _("Superseded"), "tone": "green" if r.is_active and r.is_default else "grey"}]} for r in R],
			"empty": _("Not used in any BOM.")}
	if tab == "ws":
		rows = []
		for w in frappe.get_all("Workstation", filters={"disabled": 0}, fields=["name"], order_by="name asc"):
			ops = frappe.db.sql("""select b.item, bo.idx from `tabBOM Operation` bo join `tabBOM` b on b.name = bo.parent where bo.workstation = %s and b.is_active = 1 and b.is_default = 1
				and b.docstatus = 1 and b.company in %s order by b.item, bo.idx""", (w.name, tuple(cos)), as_dict=True)
			if not ops:
				continue
			r = M.ws_rates(w.name)
			rows.append({"dt": "Workstation", "name": w.name, "cells": [{"main": r.workstation_name, "sub": r.hs_name_zh or ""}, flt(r.cap), {"money": r.lab, "currency": cur},
				{"money": r.ovh, "currency": cur}, ", ".join(f"{o.item} op {o.idx * 10}" for o in ops)]})
		return {"title": _("Workstations"), "nototal": 1, "cols": [{"label": _("Workstation")}, {"label": _("Capacity h/day"), "cls": "num"}, {"label": _("Labour rate"), "cls": "num"},
			{"label": _("Overhead rate"), "cls": "num"}, {"label": _("Operations")}], "rows": rows, "empty": _("No workstations in use.")}
	# tree
	pid = chip if chip in P else (P[0] if P else None)
	if not pid:
		return {"cols": [], "rows": [], "empty": _("No active BOM yet — create one with New BOM.")}
	b = M.bom_of(pid)
	st = M.std(pid)
	T = M.bom_tree(b)
	price = flt(frappe.db.get_value("Item Price", {"item_code": pid, "selling": 1}, "price_list_rate")) or flt(frappe.db.get_value("Item", pid, "standard_rate"))
	bd = M.bom(b)
	rows = [{"cells": [{"main": ("└ " if r.d else "") + M.item_info(r.item).item_name, "sub": " · ".join(x for x in [r.item, _("sub-assembly") if r.sub else "",
		M.default_supplier(r.item, bd.company) or _("Made in-house")] if x)}, flt(r.qty, 2), {"money": r.unit}, {"money": r.ext} if not r.d else {"text": f"({r.ext:,.2f})"}],
		"cls": "hsx-sub-row" if r.d else ""} for r in T]
	rows.append({"cls": "hsx-tot-row", "cells": [{"main": _("Material cost — roll-up")}, "", "", {"money": st.mat}]})
	return {"blocks": [
		{"type": "table", "span": 2, "title": _("BOM tree — {0} · {1}").format(M.item_info(pid).item_name, b), "sub": _("Sub-assemblies expanded, cost per unit"),
			"cols": [{"label": _("Component")}, {"label": _("Qty per unit"), "cls": "num"}, {"label": _("Unit cost"), "cls": "num"}, {"label": _("Cost"), "cls": "num"}], "rows": rows,
			"actions": [{"label": _("Print BOM"), "url": _print("BOM", b, "Hipersign Bill of Materials")}, {"label": _("New BOM"), "new": "BOM", "values": {"item": pid}}]},
		{"type": "statement", "span": 1, "title": _("Cost roll-up"), "lines": [
			{"label": _("Material (from BOM)"), "value": st.mat, "currency": cur}, {"label": _("Labour (from routing)"), "value": st.lab, "currency": cur},
			{"label": _("Overhead (from routing)"), "value": st.ovh, "currency": cur}, {"label": _("Standard cost per unit"), "value": st.total, "currency": cur, "total": 1},
			{"label": _("Selling price"), "value": price, "currency": cur}, {"label": _("Standard margin"), "text": f"{(1 - st.total / price) * 100:.1f}%" if price else "—"}]},
		{"type": "table", "span": 2, "title": _("Routing"), "cols": [{"label": _("Op")}, {"label": _("Operation")}, {"label": _("Workstation")}, {"label": _("Minutes"), "cls": "num"}],
			"rows": [{"cells": [{"code": str(o.idx * 10)}, o.operation, M.ws_rates(o.workstation).workstation_name, flt(o.time_in_mins / (flt(bd.quantity) or 1), 2)]}
				for o in bd.operations]},
		{"type": "note", "span": 1, "text": bd.get("hs_change_note") or ""},
	]}


# ================================================================ Quality
STAGE = {"inc": "Incoming", "ip": "In-process", "fin": "Final"}


def _qis(cos, stage=None):
	if not _perm("Quality Inspection"):
		return []
	f = {"company": ["in", cos or [""]], "docstatus": ["<", 2], "hs_qc_stage": ["is", "set"]}
	if stage:
		f["hs_qc_stage"] = stage
	return frappe.get_list("Quality Inspection", filters=f, fields=["name", "report_date", "inspected_by", "reference_type", "reference_name", "item_code", "item_name",
		"sample_size", "status", "docstatus", "remarks", "hs_qc_stage", "hs_work_order", "hs_operation", "hs_result", "hs_lot_qty", "hs_fails", "hs_rejected_qty",
		"hs_rework_qty", "hs_rework_done", "hs_certificate_no"], order_by="report_date desc, name desc", limit_page_length=0)


def mf_qc_module():
	cos = _cos()
	Q = _qis(cos)
	last = [q for q in Q if q.report_date and getdate(q.report_date) >= getdate(add_days(today(), -30))]
	dec = [q for q in last if q.docstatus == 1]
	W = _wos(cos) if cos else []
	pend = len([q for q in Q if q.docstatus == 0])
	return {
		"title": _("Quality"),
		"desc": _("Incoming, in-process and final inspection with AQL sampling, rejects, rework and test certificates per batch."),
		"new": [{"label": _("New quality inspection"), "doctype": "Quality Inspection", "primary": 1}],
		"kpis": [
			kpi(_("Inspections — 30 days"), len(last), _("{0} pending").format(len([q for q in last if q.docstatus == 0])), "navy", "shield"),
			kpi(_("Pass rate"), f"{len([q for q in dec if q.hs_result == 'Accepted']) / max(1, len(dec)) * 100:.0f}%", _("Lots and batches accepted first time"), "green", "check"),
			kpi(_("Rejected units"), f"{sum(flt(q.hs_rejected_qty) for q in Q) + sum(f.scrap for f in W):,.0f}", _("Incoming rejects + production scrap"), "red", "x", tab="rej"),
			kpi(_("Rework open"), f"{sum(flt(q.hs_rework_qty) - flt(q.hs_rework_done) for q in Q):,.0f}", _("Units waiting for rework"), "amber", "wrench", tab="rej"),
			kpi(_("Test certificates"), len([q for q in Q if q.hs_certificate_no]), _("Issued per batch"), "violet", "file-text", tab="fin"),
		],
		"tabs": [{"key": "inc", "label": _("Incoming") + (f" ({pend})" if pend else ""), "chips": []}, {"key": "ip", "label": _("In-process"), "chips": []},
			{"key": "fin", "label": _("Final"), "chips": []}, {"key": "rej", "label": _("Rejects & rework"), "chips": []}],
	}


def _qi_tone(r):
	return {"Accepted": "green", "Accepted with deviation": "green", "Pending": "orange", "Rework": "orange"}.get(r, "red")


def mf_qc_rows(tab, chip, q=None):
	cos = _cos()
	cur = _cur(cos)
	if not cos:
		return {"cols": [], "rows": [], "empty": _empty()}
	if tab == "rej":
		rows = []
		for x in _qis(cos):
			if flt(x.hs_rejected_qty):
				rows.append({"dt": "Quality Inspection", "name": x.name, "cells": [{"code": x.name}, x.item_name, {"pill": _("Supplier reject"), "tone": "red"}, flt(x.hs_rejected_qty),
					x.remarks or "", {"money": flt(x.hs_rejected_qty) * M.leaf_cost(x.item_code), "currency": cur}, ""]})
			if flt(x.hs_rework_qty):
				left = flt(x.hs_rework_qty) - flt(x.hs_rework_done)
				rows.append({"dt": "Quality Inspection", "name": x.name, "cells": [{"code": x.name}, x.item_name, {"pill": _("Rework"), "tone": "orange"}, left, x.remarks or "",
					{"money": left * 1.8, "currency": cur}, _btn(_("Rework done +4"), "qi_rework", x.name, args={"n": 4}) if left > 0 else {"pill": _("Done"), "tone": "green"}]})
		for f in _wos(cos):
			if f.scrap:
				rows.append({"dt": "Work Order", "name": f.name, "cells": [{"code": f.name}, f.item_name, {"pill": _("Scrap"), "tone": "red"}, f.scrap,
					_("Production scrap recorded on the job cards"), {"money": f.scrap * f.std.mat, "currency": cur}, ""]})
		return {"title": _("Rejects, scrap & rework"), "cols": [{"label": _("Source")}, {"label": _("Item")}, {"label": _("Type")}, {"label": _("Qty"), "cls": "num"},
			{"label": _("Reason")}, {"label": _("Cost"), "cls": "num"}, {"label": ""}], "rows": rows, "empty": _("No rejects, scrap or rework.")}
	stage = STAGE.get(tab, "Incoming")
	rows = []
	for x in _qis(cos, stage):
		res = x.hs_result or ("Pending" if x.docstatus == 0 else x.status)
		ref = f"{x.hs_work_order} · {_('op')} {x.hs_operation.split(' ')[0]}" if x.hs_work_order and x.hs_operation else x.hs_work_order or x.reference_name
		act = _btn(_("Accept"), "qi_accept", x.name, True) if x.docstatus == 0 else ({"url": _print("Quality Inspection", x.name, "Hipersign QC Certificate"),
			"label": _("Certificate")} if x.hs_certificate_no else "")
		rows.append({"dt": "Quality Inspection", "name": x.name, "cells": [{"main": x.name, "sub": f"{frappe.utils.formatdate(x.report_date)} · {frappe.utils.get_fullname(x.inspected_by)}"},
			ref, x.item_name, flt(x.hs_lot_qty), flt(x.sample_size), {"text": str(cint(x.hs_fails)), "tone": "red" if cint(x.hs_fails) else ""},
			{"pill": _(res), "tone": _qi_tone(res), **({"sub": x.remarks} if x.remarks else {})}, act]})
	return {"title": _("{0} inspection").format(_(stage)), "nototal": 1, "cols": [{"label": _("Inspection")}, {"label": _("Reference")}, {"label": _("Item")},
		{"label": _("Lot / batch qty"), "cls": "num"}, {"label": _("Sample"), "cls": "num"}, {"label": _("Fails")}, {"label": _("Result")}, {"label": ""}], "rows": rows,
		"empty": _("No inspections yet."), "actions": [{"label": _("New quality inspection"), "new": "Quality Inspection", "values": {"hs_qc_stage": stage}, "primary": 1}]}


# ================================================================ Costing
def mf_cost_module():
	cos = _cos()
	cur = _cur(cos)
	W = [f for f in _wos(cos) if f.state in ("Completed", "Closed")] if cos else []
	A = [M.actual(f.name) for f in W]
	vm, vl, vo = sum(a.mat - a.std_mat for a in A), sum(a.lab - a.std_lab for a in A), sum(a.ovh - a.std_ovh for a in A)
	std, act = sum(a.std for a in A), sum(a.total for a in A)
	return {
		"title": _("Costing"),
		"desc": _("Standard vs actual cost per work order — material, labour and overhead variances — and margin per product."),
		"new": [],
		"links": [[_("Cost roll-up"), ["hipersign-boms"]]],
		"kpis": [
			kpi(_("Standard cost — closed WOs"), std, _("{0} work orders").format(len(W)), "navy", "calculator", True, cur),
			kpi(_("Actual cost"), act, ("+" if act > std else "") + _m(act - std, cur) + " " + _("vs standard"), "blue", "banknote", True, cur),
			kpi(_("Material variance"), vm, _("Price and usage incl. scrap"), "red" if vm > 0 else "green", "package", True, cur),
			kpi(_("Labour variance"), vl, _("Efficiency vs routing minutes"), "amber" if vl > 0 else "green", "users", True, cur),
			kpi(_("Overhead variance"), vo, _("Absorbed on machine hours"), "amber" if vo > 0 else "green", "layers", True, cur),
		],
		"tabs": [{"key": "cost", "label": _("Actual vs standard"), "chips": []}, {"key": "how", "label": _("How it works"), "chips": []}],
		"nosearch": 1,
	}


def mf_cost_rows(tab, chip, q=None):
	cos = _cos()
	cur = _cur(cos)
	if not cos:
		return {"cols": [], "rows": [], "empty": _empty()}
	if tab == "how":
		return {"blocks": [how_block()]}
	P = _products(cos)
	prod = []
	for p in P:
		s = M.std(p)
		price = flt(frappe.db.get_value("Item Price", {"item_code": p, "selling": 1}, "price_list_rate")) or flt(frappe.db.get_value("Item", p, "standard_rate"))
		prod.append({"dt": "Item", "name": p, "cells": [_icell(p), {"money": s.mat}, {"money": s.lab}, {"money": s.ovh}, {"money": s.total}, {"money": price},
			{"text": f"{(1 - s.total / price) * 100:.1f}%" if price else "—"}]})
	W = [f for f in _wos(cos) if f.state in ("Completed", "Closed")]
	rows, labels, sm, sl, so = [], [], [], [], []
	for f in W:
		a = M.actual(f.name)
		rev = 0.0
		if f.so:
			rate = flt(frappe.db.get_value("Sales Order Item", {"parent": f.so, "item_code": f.item}, "base_net_rate"))
			rev = rate * a.qty
		if not rev:
			rev = (flt(frappe.db.get_value("Item Price", {"item_code": f.item, "selling": 1}, "price_list_rate")) or f.std.total) * a.qty
		rows.append({"dt": "Work Order", "name": f.name, "cells": [_wocell(f), flt(a.qty), {"money": a.std, "currency": cur}, {"money": a.mat, "currency": cur},
			{"money": a.lab, "currency": cur}, {"money": a.ovh, "currency": cur}, {"money": a.total, "currency": cur},
			{"text": ("+" if a.var > 0 else "−") + f"{abs(a.var):,.2f}", "tone": "red" if a.var > 0 else "green"}, {"text": f"{(rev - a.total) / rev * 100:.1f}%" if rev else "—"}]})
		labels.append(f.name[-4:])
		sm.append(round(a.mat - a.std_mat))
		sl.append(round(a.lab - a.std_lab))
		so.append(round(a.ovh - a.std_ovh))
	return {"blocks": [
		{"type": "table", "span": 3, "title": _("Standard cost and margin per product"), "sub": _("{0} per unit").format(cur), "cols": [{"label": _("Product")}, {"label": _("Material"), "cls": "num"},
			{"label": _("Labour"), "cls": "num"}, {"label": _("Overhead"), "cls": "num"}, {"label": _("Standard cost"), "cls": "num"}, {"label": _("Selling price"), "cls": "num"},
			{"label": _("Margin")}], "rows": prod},
		{"type": "table", "span": 2, "title": _("Work orders — actual vs standard"), "sub": _("Actual = materials consumed + labour and overhead from the job cards' hours"),
			"cols": [{"label": _("Work order")}, {"label": _("Produced"), "cls": "num"}, {"label": _("Standard cost"), "cls": "num"}, {"label": _("Actual material"), "cls": "num"},
				{"label": _("Actual labour"), "cls": "num"}, {"label": _("Actual overhead"), "cls": "num"}, {"label": _("Actual cost"), "cls": "num"}, {"label": _("Variance")},
				{"label": _("Margin")}], "rows": rows, "empty": _("No completed work orders yet.")},
		{"type": "card", "span": 1, "card": {"title": _("Variance by work order"), "sub": _("{0} · positive = over standard").format(cur), "type": "cols", "count": 1, "labels": labels,
			"series": [{"name": _("Material"), "color": "violet", "data": sm}, {"name": _("Labour"), "color": "orange", "data": sl}, {"name": _("Overhead"), "color": "blue", "data": so}]}},
	]}


# ================================================================ Shop floor (tablet view)
@frappe.whitelist()
def get_floor(ws=None):
	"""The job cards of the open work orders by workstation: done, planned, scrap, time, operator, running since, state."""
	cos = _cos()
	W = [M.wo_fig(n) for n in M.wo_names(cos, include_drafts=False)] if cos else []
	cards, used = [], set()
	for f in W:
		if f.state in ("Closed", "Cancelled", "Stopped") or (f.state == "Completed" and (not f.due or getdate(f.due) < getdate(add_days(today(), -10)))):
			continue
		for o in f.ops:
			if not o.jc:
				continue
			used.add(o.ws)
			if ws and ws != "all" and o.ws != ws:
				continue
			run = M.open_log(o.live.name) if o.live else None
			opr = o.jc.hs_operator
			cards.append({"jc": o.jc.name, "live": 1 if o.live else 0, "state": o.state, "wo": f.name, "item": f.item_name, "op": f"{o.idx * 10}", "op_name": o.op,
				"ws": o.ws, "ws_name": M.ws_rates(o.ws).workstation_name, "done": o.done, "planned": f.qty, "scrap": o.scrap,
				# v1.8.4: the loss the job card records (ERPNext's process loss = this operation's scrap + the scrap before it)
				"loss": o.loss, "paused": 1 if o.live and o.live.is_paused else 0, "mins": round(o.mins),
				"pct": min(100, o.done / f.qty * 100) if f.qty else 0, "operator": opr, "operator_name": frappe.db.get_value("Employee", opr, "employee_name") if opr else "",
				"started": frappe.utils.get_datetime(run.from_time).strftime("%H:%M") if run else None, "late": f.late})
	order = {"Work in progress": 0, "On hold": 1, "Open": 2, "Completed": 3}
	cards.sort(key=lambda c: (order.get(c["state"], 4), c["wo"], c["op"]))
	wss = [{"id": w, "name": M.ws_rates(w).workstation_name} for w in sorted(used, key=lambda x: M.ws_rates(x).workstation_name)]
	ops = frappe.get_all("Employee", filters={"company": ["in", cos or [""]], "status": "Active", "designation": "Operator"}, fields=["name", "employee_name"], order_by="employee_name asc") \
		if frappe.has_permission("Employee", "read") else []
	if not ops:
		ops = [{"name": c["operator"], "employee_name": c["operator_name"]} for c in cards if c["operator"]]
		ops = list({o["name"]: o for o in ops}.values())
	first = next((c["wo"] for c in cards if c["live"]), cards[0]["wo"] if cards else None)
	return {"cards": cards, "workstations": wss, "operators": ops, "can_write": bool(frappe.has_permission("Job Card", "write")), "ticket_wo": first}


# ================================================================ Production Tracker
@frappe.whitelist()
def get_tracker(filter=None, q=None):
	"""Every sales order and its work order through the 22 steps in 5 phases — status, % and date per step — with red flags."""
	cos = _cos()
	cur = _cur(cos)
	S = [M.so_fig(n) for n in M.so_names(cos)] if cos else []
	out = []
	sel = {"open": lambda s: s.step < 22, "mat": lambda s: 1 <= s.step < 7, "prod": lambda s: 7 <= s.step < 13, "ship": lambda s: 13 <= s.step < 22,
		"flags": lambda s: bool(M.flags(s.name)), "done": lambda s: s.step >= 22}.get(filter or "open", lambda s: True)
	for s in S:
		if not sel(s):
			continue
		if q and q.lower() not in f"{s.name} {s.customer_name} {s.item_name} {s.wo or ''}".lower():
			continue
		f = M.wo_fig(s.wo) if s.wo else None
		fl = M.flags(s.name)
		st = M.states(s.name)
		status = M.so_status(s.step, s.forecast)
		out.append({"name": s.name, "customer": s.customer_name, "city": s.city, "export": s.export, "item": s.item_name, "qty": s.qty, "due": s.due, "date": s.date,
			"value": s.qty * s.rate, "wo": s.wo, "wo_state": _(f.state) if f else None, "done": f.done if f else 0, "scrap": f.scrap if f else 0, "pct": f.pct if f else 0,
			"late": bool(f and f.late), "status": status, "tone": "grey" if s.step >= 22 else "green" if s.step >= 18 else "blue" if s.step >= 7 else "orange",
			"flags": fl, "states": [{"st": x.st, "pct": x.pct, "date": x.date, "tag": x.tag, "info": x.info, "by": x.by} for x in st]})
	nfl = sum(len(M.flags(s.name)) for s in S)
	W = [M.wo_fig(n) for n in M.wo_names(cos)] if cos else []
	dl = [s for s in S if s.step >= 18]
	return {"currency": cur, "orders": out, "steps": [{"name": _(x[0]), "short": _(x[1]), "who": _(x[3]), "docs": _(x[4])} for x in M.STEPS],
		"phases": [{"name": _(a), "a": b, "b": c} for a, b, c in M.PHASES],
		"counts": {"all": len(S), "open": len([s for s in S if s.step < 22]), "flags": len([s for s in S if M.flags(s.name)])},
		"kpis": [kpi(_("Orders tracked"), len(S), _("{0} open").format(len([s for s in S if s.step < 22])), "blue", "list"),
			kpi(_("Order value"), sum(s.qty * s.rate for s in S), _("{0} units").format(f"{sum(s.qty for s in S):,.0f}"), "navy", "tag", True, cur),
			kpi(_("In production"), len([s for s in S if 7 <= s.step < 13]), _("{0} units to finish").format(f"{sum(max(0, f.qty - f.done - f.scrap) for f in W if f.state == 'In process'):,.0f}"),
				"blue", "wrench"),
			kpi(_("Delivered"), len(dl), _short(sum(s.qty * s.rate for s in dl), cur), "green", "truck"),
			kpi(_("Red flags"), nfl, _("{0} orders need attention").format(len([s for s in S if M.flags(s.name)])), "red" if nfl else "green", "flag")]}
