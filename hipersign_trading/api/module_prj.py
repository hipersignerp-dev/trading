"""v1.8.0 (prototype p19): the Projects pages — Projects, Estimating & BOQ, Site & procurement, Progress & billing,
Subcontractors, Timesheets & labour and Project costing — on the module page renderer (hs_module.js), plus the Project
Tracker's data. Figures, step states and red flags come from api.projects (one place for the rules)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

from hipersign_trading.api import projects as P
from hipersign_trading.api.module import _perm, _scope, kpi

KEYS = ("pj_home", "pj_boq", "pj_site", "pj_bill", "pj_sub", "pj_time", "pj_cost")
ACT = "hipersign_trading.api.projects.act"


def _names(include_closed=True):
	cos = _scope()[0]
	return P.project_names(cos, include_closed)


def _cur(names=None):
	names = names if names is not None else _names()
	if names:
		return frappe.get_cached_value("Company", P.project(names[0]).company, "default_currency")
	return _scope()[4]


def _pcell(name):
	p = P.project(name)
	return {"main": p.project_name, "sub": f"{p.name} · {p.customer or ''}"}


def _pct(v):
	return f"{flt(v):.1f}%"


def _btn(label, action, name, primary=False, args=None, confirm=None):
	return {"button": label, "act": action, "name": name, "args": args or {}, "primary": 1 if primary else 0, "confirm": confirm}


def _chips(names, closed=True):
	"""The project picker as chips: live projects first (largest first), then tenders and closed ones."""
	ps = [P.project(n) for n in names]
	ps.sort(key=lambda p: (0 if 10 <= cint(p.hs_step) < 26 else 1 if 5 <= cint(p.hs_step) < 10 else 2 if cint(p.hs_step) < 5 else 3, -flt(p.hs_contract_value)))
	return [[p.name, f"{p.name[-3:]} · {p.project_name.split(' — ')[0]}"] for p in ps if closed or cint(p.hs_step) < 26]


def _pick(chip, names):
	return chip if chip in names else (_chips(names)[0][0] if names else None)


def _status_pill(step):
	s = P.status_of(step)
	return {"pill": _(s), "tone": P.STATUS_TONE[s]}


def _empty_note():
	return _("No projects yet — create one with New project (Projects & contracting must be switched on).")


# ================================================================ Projects
def pj_home_module():
	names = _names()
	cur = _cur(names)
	con = [n for n in names if P.fig(n).step >= 5]
	F = [P.fig(n) for n in con]
	live = [n for n in con if P.fig(n).step < 26]
	nfl = sum(len(P.flags(n)) for n in names)
	rev = sum(f.rev for f in F)
	done = sum(f.rev * f.pct / 100 for f in F)
	at_risk = len([n for n in names if P.flags(n)])
	by = {}
	for n in names:
		by[P.fig(n).status] = by.get(P.fig(n).status, 0) + 1
	tone = {"Tender": "violet", "Mobilising": "orange", "Execution": "blue", "Handover": "green", "Closed": "grey"}
	return {
		"title": _("Projects"),
		"desc": _("Fit-out and contracting projects from enquiry to profit report — contract value, progress, billing, collection, cost and margin on one screen."),
		"new": [{"label": _("New project"), "doctype": "Project", "primary": 1}],
		"links": [[_("Project Tracker"), ["project-tracker"]]],
		"kpis": [
			kpi(_("Contract value (incl. variations)"), rev, _("{0} contracts · {1} live").format(len(con), len(live)), "navy", "file-text", True, cur, ["project-tracker"]),
			kpi(_("Work done"), f"{done / rev * 100:.0f}%" if rev else "0%", _("{0} measured").format(frappe.format(done, {"fieldtype": "Currency", "options": cur})), "blue", "chart-gantt"),
			kpi(_("Certified"), sum(f.certified for f in F), _("By the consultants"), "violet", "check", True, cur, ["hipersign-billing"]),
			kpi(_("Collected"), sum(f.collected for f in F), _("{0} outstanding · {1} overdue").format(_m(sum(f.out for f in F), cur), _m(sum(f.overdue for f in F), cur)),
				"green", "banknote", True, cur, ["hipersign-billing"]),
			kpi(_("Cost to date"), sum(f.cost for f in F), _("Forecast at completion {0}").format(_m(sum(f.fac for f in F), cur)), "amber", "calculator", True, cur, ["hipersign-costing"]),
			kpi(_("Red flags"), nfl, _("{0} projects at risk").format(at_risk), "red" if nfl else "green", "flag", tab="flags"),
		],
		"cards": [
			{"title": _("Contract value by project"), "sub": _("incl. approved variations"), "type": "bars", "currency": cur,
				"rows": [[f"{n[-3:]} · {P.project(n).project_name.split(' — ')[0]}", P.fig(n).rev] for n in con]},
			{"title": _("Where the projects are"), "type": "donut", "count": 1, "center": str(len(names)), "center_label": _("projects"),
				"rows": [[_(s), by[s], tone[s]] for s in ("Tender", "Mobilising", "Execution", "Handover", "Closed") if by.get(s)]},
		],
		"tabs": [
			{"key": "port", "label": _("Portfolio"), "chips": [[k, _(v)] for k, v in (("all", "All"), ("Tender", "Tender"), ("Mobilising", "Mobilising"),
				("Execution", "Execution"), ("Handover", "Handover"), ("Closed", "Closed"), ("risk", "At risk"))]},
			{"key": "how", "label": _("How it works"), "chips": []},
			{"key": "flags", "label": _("Red flags") + (f" ({nfl})" if nfl else ""), "chips": []},
		],
		"nosearch": 0,
	}


def _m(v, cur):
	"""v1.8.4: amounts in KPI sub-lines and card notes are compact ("AED 5.3M"), as on the other pages — they showed full
	precision ("AED 5,320,401.99") and pushed the cards wide."""
	from hipersign_trading.api.module import _fmt

	return _fmt(v, cur or "")


def how_block():
	return {"type": "how", "span": 3, "title": _("How it works — the project process"),
		"sub": _("26 steps from enquiry to profit report · who does what, documents, approvals and triggers"),
		"phases": [{"name": _(n), "a": a, "b": b} for n, a, b in P.PHASES],
		"steps": [{"name": _(s[0]), "short": _(s[1]), "what": _(s[2]), "who": _(s[3]), "docs": _(s[4]), "approval": _(s[5]), "next": _(s[6])} for s in P.STEPS]}


def pj_home_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	if tab == "how":
		return {"blocks": [how_block()]}
	if tab == "flags":
		rows = []
		for n in names:
			for f in P.flags(n):
				o = f.get("open") or ["Project", n]
				rows.append({"dt": "Project", "name": n, "cells": [_pcell(n), {"pill": _(f["lvl"]), "tone": "red" if f["lvl"] == "High" else "orange"}, f["text"],
					{"main": str(f["step"] + 1), "sub": _(P.STEPS[f["step"]][1])}, {"button": _("Open"), "open": o}]})
		return {"title": _("Red flags — every project"), "cols": [{"label": _("Project")}, {"label": _("Level")}, {"label": _("Issue")}, {"label": _("Process step")}, {"label": ""}],
			"rows": rows, "empty": _("No red flags — all projects are on track."), "nototal": 1}
	chip = chip or "all"
	rows = []
	for n in names:
		F = P.fig(n)
		fl = P.flags(n)
		if chip == "risk" and not fl:
			continue
		if chip not in ("all", "risk") and F.status != chip:
			continue
		if q and q.lower() not in f"{n} {P.project(n).project_name} {P.project(n).customer}".lower():
			continue
		stage = _("All 26 steps done") if F.step >= 26 else f"{F.step + 1}. {_(P.STEPS[F.step][1])}"
		rows.append({"dt": "Project", "name": n, "cells": [_pcell(n), dict(_status_pill(F.step), sub=stage), {"money": F.rev, "currency": cur}, {"bar": F.pct},
			{"money": F.certified, "currency": cur}, {"money": F.billed_tot, "currency": cur}, {"money": F.collected, "currency": cur}, {"money": F.cost, "currency": cur},
			{"main": _pct(F.margin), "sub": _("budget {0}").format(_pct(F.bud_margin)), "late": F.margin < F.bud_margin - 1},
			{"pill": _("{0} flags").format(len(fl)) if fl else _("None"), "tone": "red" if fl else "green"}]})
	return {"title": _("Project portfolio"), "cols": [{"label": _("Project")}, {"label": _("Stage")}, {"label": _("Contract value"), "cls": "num"}, {"label": _("% complete")},
		{"label": _("Certified"), "cls": "num"}, {"label": _("Billed / invoiced"), "cls": "num"}, {"label": _("Collected / paid"), "cls": "num"}, {"label": _("Cost to date"), "cls": "num"},
		{"label": _("Margin %")}, {"label": _("Flags")}], "rows": rows, "empty": _empty_note()}


# ================================================================ Estimating & BOQ
def pj_boq_module():
	names = _names()
	cur = _cur(names)
	T = frappe.get_list("Project BOQ", fields=["name", "status", "tender_value", "margin_pct", "due_date", "title"], limit_page_length=0) if _perm("Project BOQ") else []
	opn = [t for t in T if t.status in ("Being priced", "Submitted")]
	dec = [t for t in T if t.status == "Awarded" or (t.status or "").startswith("Lost")]
	won = [t for t in dec if t.status == "Awarded"]
	nxt = sorted([t for t in opn if t.due_date and getdate(t.due_date) >= getdate(today())], key=lambda t: t.due_date)
	con = [n for n in names if P.fig(n).step >= 5]
	return {
		"title": _("Estimating & BOQ"),
		"desc": _("Price the BOQ line by line from material, labour and subcontract rates, add overheads and margin, submit the tender and turn the award into the contract BOQ."),
		"new": [{"label": _("New BOQ"), "doctype": "Project BOQ", "primary": 1}],
		"kpis": [
			kpi(_("Tenders open"), len(opn), _("{0} tender value").format(_m(sum(flt(t.tender_value) for t in opn), cur)), "violet", "file-text", tab="tend"),
			kpi(_("Win rate"), f"{len(won) / len(dec) * 100:.0f}%" if dec else "—", _("{0} won of {1} decided").format(len(won), len(dec)), "green", "flag"),
			kpi(_("BOQ value — contracts"), sum(P.boq(n).total_amount for n in con if P.boq(n)), _("{0} priced BOQs").format(len(con)), "navy", "calculator", True, cur, tab="boq"),
			kpi(_("Average tender margin"), _pct(sum(flt(t.margin_pct) for t in T) / len(T)) if T else "—", _("After overheads"), "blue", "chart-column", tab="cost"),
			kpi(_("Next tender due"), frappe.utils.formatdate(nxt[0].due_date, "dd MMM") if nxt else "—", nxt[0].title if nxt else "—", "amber", "clock", tab="tend"),
		],
		"tabs": [
			{"key": "boq", "label": _("Bill of quantities"), "chips": _chips(names)},
			{"key": "cost", "label": _("Cost build-up"), "chips": _chips(names)},
			{"key": "tend", "label": _("Tenders & quotations") + (f" ({len(opn)})" if opn else ""), "chips": [["all", _("All")], ["open", _("Open")], ["won", _("Awarded")], ["lost", _("Lost")]]},
		],
	}


def _boq_rows(b, mode, cur):
	rows, secs = [], []
	for r in b.items:
		if r.section not in secs:
			secs.append(r.section)
	shares = lambda r: sum(flt(r.get(f)) for f in P.SHARE.values()) / 100
	for s in secs:
		sl = [r for r in b.items if r.section == s]
		head = f"{s} · {sl[0].section_name or ''}"
		if mode == "cost":
			rows.append({"cls": "hsx-grp-row", "cells": [{"main": head}] + [""] * 9})
		else:
			rows.append({"cls": "hsx-grp-row", "cells": [{"main": head}, "", "", "", {"main": frappe.format(sum(flt(r.amount) for r in sl), {"fieldtype": "Currency", "options": cur})}, ""]})
		for r in sl:
			if mode == "cost":
				rows.append({"cells": [{"main": f"{r.item_no} {r.description}"}, r.unit, flt(r.qty), {"money": flt(r.rate) * flt(r.mat_share) / 100}, {"money": flt(r.rate) * flt(r.lab_share) / 100},
					{"money": flt(r.rate) * flt(r.sub_share) / 100}, {"money": flt(r.rate) * flt(r.ovh_share) / 100}, {"money": r.cost_rate}, {"money": r.rate},
					{"text": _pct((1 - shares(r)) * 100)}]})
			else:
				rows.append({"cells": [{"main": f"{r.item_no} {r.description}"}, r.unit, flt(r.qty), {"money": r.rate}, {"money": r.amount, "currency": cur}, {"bar": flt(r.measured_pct)}]})
	return rows


def pj_boq_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	if tab == "tend":
		f = {"all": {}, "open": {"status": ["in", ["Being priced", "Submitted"]]}, "won": {"status": "Awarded"}, "lost": {"status": ["like", "Lost%"]}}.get(chip or "all", {})
		T = frappe.get_list("Project BOQ", filters=f, fields=["name", "title", "client_name", "revision", "received_on", "due_date", "tender_value", "margin_pct", "status", "project"],
			order_by="received_on desc", limit_page_length=0) if _perm("Project BOQ") else []
		tone = lambda s: "green" if s == "Awarded" else "red" if s.startswith("Lost") else "violet" if s == "Submitted" else "orange"
		return {"title": _("Tenders & quotations"), "cols": [{"label": _("Tender")}, {"label": _("Client")}, {"label": _("Received")}, {"label": _("Due")}, {"label": _("Tender value"), "cls": "num"},
			{"label": _("Margin %")}, {"label": _("Status")}, {"label": ""}],
			"rows": [{"dt": "Project BOQ", "name": t.name, "cells": [{"main": t.title, "sub": f"{t.name} · Rev {cint(t.revision)}"}, t.client_name, {"date": t.received_on},
				{"date": t.due_date, "late": t.status == "Being priced" and t.due_date and date_diff(t.due_date, today()) <= 7}, {"money": t.tender_value, "currency": cur},
				{"text": _pct(t.margin_pct)}, {"pill": _(t.status), "tone": tone(t.status or "")},
				{"url": f"/printview?doctype=Project%20BOQ&name={t.name}&format=Hipersign%20BOQ%20Tender", "label": _("BOQ")}]} for t in T], "empty": _("No tenders yet.")}
	pj = _pick(chip, names)
	if not pj:
		return {"cols": [], "rows": [], "empty": _empty_note()}
	p = P.project(pj)
	b = P.boq(pj)
	if not b:
		return {"blocks": [{"type": "note", "span": 3, "text": _("{0} has no BOQ yet.").format(pj), "actions": [{"label": _("New BOQ"), "new": "Project BOQ", "values": {"project": pj}}]}]}
	if tab == "cost":
		return {"title": _("Cost build-up — {0}").format(p.project_name), "nototal": 1, "cols": [{"label": _("Item")}, {"label": _("Unit")}, {"label": _("Qty"), "cls": "num"},
			{"label": _("Material rate"), "cls": "num"}, {"label": _("Labour rate"), "cls": "num"}, {"label": _("Subcontract rate"), "cls": "num"}, {"label": _("Overhead rate"), "cls": "num"},
			{"label": _("Cost rate"), "cls": "num"}, {"label": _("Selling rate"), "cls": "num"}, {"label": _("Margin %")}], "rows": _boq_rows(b, "cost", cur)}
	step = cint(p.hs_step)
	total = flt(b.total_amount)
	direct = flt(b.direct_cost)
	ov = flt(b.overheads)
	acts = [{"label": _("Print BOQ"), "url": f"/printview?doctype=Project%20BOQ&name={b.name}&format=Hipersign%20BOQ%20Tender"}]
	if step <= 3:
		acts.append({"label": _("Submit tender") if step == 3 else _("Complete step {0}").format(step + 1), "method": ACT, "args": {"action": "step", "name": pj}, "primary": 1})
	flow = ["Enquiry", "Site visit", "BOQ & estimate", "Tender / quotation", "Negotiation", "Letter of Award", "Contract (sales order)"]
	return {"blocks": [
		# v1.8.4: "From tender to contract" as the prototype's stepper across the top (it was a plain list beside the BOQ)
		{"type": "flow", "span": 3, "title": _("From tender to contract"), "steps": [_(x) for x in flow], "at": min(step, 6) if step < 7 else 7,
			"note": (_("{0} — contract signed; the BOQ became the contract BOQ and the sales order").format(p.project_name) if step >= 5
				else _("{0} — currently at step {1} · {2}").format(p.project_name, step + 1, _(P.STEPS[step][0])))},
		{"type": "table", "span": 2, "title": _("Bill of quantities — {0}").format(p.project_name), "sub": _("{0} lines by section · qty × rate").format(len(b.items)),
			"cols": [{"label": _("Item")}, {"label": _("Unit")}, {"label": _("Qty"), "cls": "num"}, {"label": _("Rate"), "cls": "num"}, {"label": _("Amount"), "cls": "num"}, {"label": _("Done")}],
			"rows": _boq_rows(b, "boq", cur) + [{"cls": "hsx-tot-row", "cells": [{"main": _("Total BOQ · {0} lines").format(len(b.items))}, "", "", "", {"money": total, "currency": cur},
				{"bar": flt(b.work_done) / total * 100 if total else 0}]}]},
		{"type": "statement", "span": 1, "title": _("Estimate summary — {0}").format(b.name), "actions": acts, "lines": [
			{"label": _("Direct cost"), "value": direct, "currency": cur}, {"label": _("Site overheads & plant"), "value": ov, "currency": cur},
			{"label": _("Total cost"), "value": direct + ov, "currency": cur},
			{"label": _("Margin"), "value": total - direct - ov, "currency": cur, "sub": _pct((total - direct - ov) / total * 100 if total else 0)},
			{"label": _("Tender / contract value"), "value": total, "currency": cur, "total": 1}]},
	]}


# ================================================================ Site & procurement
def _mrs(names):
	if not names or not _perm("Material Request"):
		return []
	# v1.8.0: a request rejected at approval stays on the list (cancelled, with the rejected lines and the reason)
	rows = frappe.get_list("Material Request", filters={"hs_project": ["in", names]}, fields=["name", "hs_project", "transaction_date", "schedule_date",
		"docstatus", "per_ordered", "per_received", "owner", "hs_over_boq", "hs_rejected_lines", "material_request_type"], order_by="transaction_date desc, name desc", limit_page_length=0)
	rows = [m for m in rows if m.docstatus < 2 or m.hs_rejected_lines]
	# a purchase order raised from the request (still a draft waiting for approval) counts as ordered
	po = {}
	for r in frappe.get_all("Purchase Order Item", filters={"material_request": ["in", [m.name for m in rows] or [""]], "docstatus": ["<", 2]}, fields=["material_request", "parent"]):
		po.setdefault(r.material_request, r.parent)
	for m in rows:
		m.po = po.get(m.name)
	return rows


def _pos(names):
	if not names or not _perm("Purchase Order"):
		return []
	return frappe.get_list("Purchase Order", filters={"hs_project": ["in", names], "docstatus": ["<", 2]}, fields=["name", "supplier", "hs_project", "hs_cost_head", "transaction_date",
		"schedule_date", "base_net_total", "per_received", "status", "docstatus", "workflow_state"], order_by="transaction_date desc, name desc", limit_page_length=0)


def _site_whs(names):
	return [w for w in (frappe.db.get_value("Project", n, "hs_site_warehouse") for n in names) if w]


def _deliveries(names):
	out = []
	if not names:
		return out
	for r in frappe.db.sql("""select pr.name, pr.posting_date, pr.project, pri.item_name, pri.qty, pri.uom, pri.base_net_amount, pr.supplier_name, pr.owner, pri.purchase_order
		from `tabPurchase Receipt` pr join `tabPurchase Receipt Item` pri on pri.parent = pr.name where pr.docstatus = 1 and pr.is_return = 0 and pr.project in %s
		order by pr.posting_date desc""", (tuple(names),), as_dict=True):
		out.append(frappe._dict(dt="Purchase Receipt", name=r.name, date=r.posting_date, project=r.project, item=r.item_name, qty=r.qty, uom=r.uom, value=r.base_net_amount,
			frm=_("Supplier direct — {0}").format(r.supplier_name), po=r.purchase_order, by=frappe.utils.get_fullname(r.owner)))
	whs = _site_whs(names)
	if whs:
		for r in frappe.db.sql("""select se.name, se.posting_date, se.project, sed.item_name, sed.qty, sed.uom, sed.basic_amount, sed.s_warehouse, se.owner
			from `tabStock Entry` se join `tabStock Entry Detail` sed on sed.parent = se.name where se.docstatus = 1 and se.purpose = 'Material Transfer' and sed.t_warehouse in %s
			order by se.posting_date desc""", (tuple(whs),), as_dict=True):
			out.append(frappe._dict(dt="Stock Entry", name=r.name, date=r.posting_date, project=r.project, item=r.item_name, qty=r.qty, uom=r.uom, value=r.basic_amount,
				frm=r.s_warehouse, po=None, by=frappe.utils.get_fullname(r.owner)))
	out.sort(key=lambda x: (getdate(x.date), x.name), reverse=True)
	return out


def _returns(names):
	out = []
	if not names:
		return out
	for r in frappe.db.sql("""select pr.name, pr.posting_date, pr.project, pri.item_name, pri.qty, pri.uom, pri.base_net_amount, pr.supplier_name, pr.remarks
		from `tabPurchase Receipt` pr join `tabPurchase Receipt Item` pri on pri.parent = pr.name where pr.docstatus = 1 and pr.is_return = 1 and pr.project in %s""", (tuple(names),), as_dict=True):
		out.append(frappe._dict(dt="Purchase Receipt", name=r.name, date=r.posting_date, project=r.project, item=r.item_name, qty=abs(flt(r.qty)), uom=r.uom, value=abs(flt(r.base_net_amount)),
			to=r.supplier_name, reason=r.remarks or _("Returned to supplier"), state=_("Returned to supplier")))
	whs = _site_whs(names)
	if whs:
		for r in frappe.db.sql("""select se.name, se.posting_date, se.project, sed.item_name, sed.qty, sed.uom, sed.basic_amount, sed.t_warehouse, se.remarks
			from `tabStock Entry` se join `tabStock Entry Detail` sed on sed.parent = se.name where se.docstatus = 1 and se.purpose = 'Material Transfer' and sed.s_warehouse in %s
			and sed.t_warehouse not in %s""", (tuple(whs), tuple(whs)), as_dict=True):
			out.append(frappe._dict(dt="Stock Entry", name=r.name, date=r.posting_date, project=r.project, item=r.item_name, qty=r.qty, uom=r.uom, value=r.basic_amount, to=r.t_warehouse,
				reason=r.remarks or _("Surplus back to the store"), state=_("Received in store")))
	out.sort(key=lambda x: getdate(x.date), reverse=True)
	return out


def _site_stock(names):
	whs = {w: n for n in names for w in [frappe.db.get_value("Project", n, "hs_site_warehouse")] if w}
	if not whs:
		return []
	rows = frappe.db.sql("""select sle.warehouse, sle.item_code, sle.voucher_type, sle.voucher_no, sum(sle.actual_qty) qty from `tabStock Ledger Entry` sle
		where sle.is_cancelled = 0 and sle.warehouse in %s group by sle.warehouse, sle.item_code, sle.voucher_type, sle.voucher_no""", (tuple(whs),), as_dict=True)
	purpose = {r.name: r.purpose for r in frappe.get_all("Stock Entry", filters={"name": ["in", list({r.voucher_no for r in rows if r.voucher_type == "Stock Entry"}) or [""]]}, fields=["name", "purpose"])}
	agg = {}
	for r in rows:
		k = (r.warehouse, r.item_code)
		a = agg.setdefault(k, frappe._dict(recv=0, used=0, ret=0))
		q = flt(r.qty)
		if q > 0:
			a.recv += q
		elif r.voucher_type == "Stock Entry" and purpose.get(r.voucher_no) == "Material Issue":
			a.used -= q
		else:
			a.ret -= q
	out = []
	for (w, it), a in agg.items():
		bin_ = frappe.db.get_value("Bin", {"warehouse": w, "item_code": it}, ["actual_qty", "valuation_rate", "stock_value"], as_dict=True) or {}
		info = frappe.get_cached_value("Item", it, ["item_name", "stock_uom"], as_dict=True)
		out.append(frappe._dict(project=whs[w], item=info.item_name, uom=info.stock_uom, recv=a.recv, used=a.used, ret=a.ret, bal=flt(bin_.get("actual_qty")), value=flt(bin_.get("stock_value"))))
	return out


def _mr_state(m):
	if m.docstatus == 2:
		return _("Rejected"), "red"
	if m.docstatus == 0:
		return _("Pending approval"), "orange"
	if flt(m.per_received) >= 100:
		return _("Delivered"), "green"
	if flt(m.per_ordered) > 0 or m.get("po"):
		return _("Ordered"), "blue"
	return _("Approved"), "blue"


def pj_site_module():
	names = _names()
	cur = _cur(names)
	M, PO = [m for m in _mrs(names) if m.docstatus < 2], _pos(names)
	DL = _deliveries(names)
	ST = _site_stock(names)
	late = [x for x in PO if x.docstatus == 1 and x.schedule_date and getdate(x.schedule_date) < getdate(today()) and flt(x.per_received) < 100]
	d30 = [d for d in DL if getdate(d.date) >= getdate(add_days(today(), -30))]
	pend = [m for m in M if m.docstatus == 0]
	return {
		"title": _("Site & procurement"),
		"desc": _("Material requests from the BOQ, purchase orders per project, deliveries to site, site stock and returns — every cost lands on the right project and cost head."),
		"new": [{"label": _("Daily site report"), "doctype": "Daily Site Report"}, {"label": _("Site transfer"), "doctype": "Stock Entry:site"},
			{"label": _("Material request"), "doctype": "Material Request:project", "primary": 1}],
		"kpis": [
			kpi(_("Open material requests"), len([m for m in M if flt(m.per_received) < 100]), _("{0} awaiting approval").format(len(pend)), "blue", "list", tab="mr"),
			kpi(_("Project purchase orders"), sum(flt(x.base_net_total) for x in PO), _("{0} open · {1} to approve").format(len([x for x in PO if flt(x.per_received) < 100]),
				len([x for x in PO if x.docstatus == 0])), "violet", "shopping-cart", True, cur, tab="po"),
			kpi(_("Deliveries to site — 30 days"), len(d30), _m(sum(flt(d.value) for d in d30), cur), "green", "truck", tab="del"),
			kpi(_("Site stock value"), sum(s.value for s in ST), _("{0} items on {1} sites").format(len(ST), len({s.project for s in ST})), "navy", "package", True, cur, tab="stock"),
			kpi(_("Late deliveries"), len(late), _("ETA passed, not received"), "red" if late else "green", "triangle-alert", tab="po"),
		],
		"tabs": [{"key": "mr", "label": _("Material requests") + (f" ({len(pend)})" if pend else ""), "chips": []}, {"key": "po", "label": _("Purchase orders"), "chips": []},
			{"key": "del", "label": _("Deliveries to site"), "chips": []}, {"key": "stock", "label": _("Site stock"), "chips": []}, {"key": "ret", "label": _("Returns"), "chips": []}],
	}


def pj_site_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	if tab == "mr":
		M = _mrs(names)
		items, n_lines = {}, {}
		for r in frappe.get_all("Material Request Item", filters={"parent": ["in", [m.name for m in M] or [""]]}, fields=["parent", "item_name", "qty", "uom", "hs_boq_item"], order_by="idx asc"):
			items.setdefault(r.parent, r)
			n_lines[r.parent] = n_lines.get(r.parent, 0) + 1
		rows = []
		for m in M:
			it = items.get(m.name) or frappe._dict()
			st, tone = _mr_state(m)
			# v1.8.0: approve all, or line by line (approve, reduce or reject each line with a reason); Create PO opens the app's order window
			act = {"buttons": [_btn(_("Approve"), "mr_approve", m.name, True), {"button": _("Lines…"), "js": "mr_review", "name": m.name}]} if m.docstatus == 0 else \
				{"button": _("Create PO"), "make": "erpnext.stock.doctype.material_request.material_request.make_purchase_order", "source": m.name} \
				if m.docstatus == 1 and m.material_request_type == "Purchase" and flt(m.per_ordered) < 100 and not m.po else ""
			sub = _("over BOQ") if m.hs_over_boq else None
			if m.hs_rejected_lines:
				sub = _("lines rejected") if m.docstatus == 2 else _("partly approved")
			elif m.po and m.docstatus == 1:
				sub = m.po
			rows.append({"dt": "Material Request", "name": m.name, "cells": [{"main": m.name, "sub": f"{frappe.utils.formatdate(m.transaction_date)} · {frappe.utils.get_fullname(m.owner)}"},
				{"main": P.project(m.hs_project).project_name, "sub": _("{0} · line {1}").format(m.hs_project, it.hs_boq_item or "—")}, it.item_name or "—",
				f"{flt(it.qty):,.0f} {it.uom or ''}" + (f" (+{n_lines[m.name] - 1})" if n_lines.get(m.name, 0) > 1 else ""), {"date": m.schedule_date},
				{"pill": st, "tone": tone, **({"sub": sub} if sub else {})}, act]})
		return {"title": _("Material requests from the BOQ"), "nototal": 1, "cols": [{"label": _("Request")}, {"label": _("Project · BOQ line")}, {"label": _("Material")}, {"label": _("Qty")},
			{"label": _("Needed")}, {"label": _("Status")}, {"label": ""}], "rows": rows, "empty": _("No material requests yet."),
			"actions": [{"label": _("New material request"), "new": "Material Request:project", "primary": 1}]}
	if tab == "po":
		PO = _pos(names)
		first = {}
		for r in frappe.get_all("Purchase Order Item", filters={"parent": ["in", [x.name for x in PO] or [""]]}, fields=["parent", "item_name", "qty", "uom", "rate"], order_by="idx asc"):
			first.setdefault(r.parent, r)
		rows = []
		for x in PO:
			it = first.get(x.name) or frappe._dict()
			late = x.docstatus == 1 and x.schedule_date and getdate(x.schedule_date) < getdate(today()) and flt(x.per_received) < 100
			st = x.workflow_state if x.docstatus == 0 and x.workflow_state else (_("Pending approval") if x.docstatus == 0 else _("Received") if flt(x.per_received) >= 100 else _(x.status))
			act = {"button": _("Approve"), "open": ["Purchase Order", x.name], "primary": 1} if x.docstatus == 0 else \
				_btn(_("Receive at site"), "po_receive", x.name, confirm=_("Receive what is still to come on {0} at the project's site store?").format(x.name)) if flt(x.per_received) < 100 else ""
			country = frappe.get_cached_value("Supplier", x.supplier, "country") or ""
			rows.append({"dt": "Purchase Order", "name": x.name, "cells": [{"main": x.name, "sub": frappe.utils.formatdate(x.transaction_date)}, {"main": x.supplier, "sub": country},
				{"main": x.hs_project, "sub": _(x.hs_cost_head or "Materials")}, {"main": it.item_name or "—", "sub": f"{flt(it.qty):,.0f} {it.uom or ''} × {flt(it.rate):,.2f}"},
				{"money": x.base_net_total, "currency": cur}, {"date": x.schedule_date, "late": late}, {"bar": flt(x.per_received)},
				{"pill": st, "tone": "orange" if x.docstatus == 0 else "green" if flt(x.per_received) >= 100 else "blue"}, act]})
		return {"title": _("Purchase orders per project"), "cols": [{"label": _("PO")}, {"label": _("Supplier")}, {"label": _("Project · cost head")}, {"label": _("Material")},
			{"label": _("Value"), "cls": "num"}, {"label": _("ETA")}, {"label": _("Received")}, {"label": _("Status")}, {"label": ""}], "rows": rows,
			"empty": _("No project purchase orders yet.")}
	if tab == "del":
		return {"title": _("Deliveries to site"), "cols": [{"label": _("Delivery")}, {"label": _("Date")}, {"label": _("Project")}, {"label": _("Material")}, {"label": _("Qty")},
			{"label": _("From")}, {"label": _("Value"), "cls": "num"}, {"label": _("Received by")}],
			"rows": [{"dt": d.dt, "name": d.name, "cells": [{"code": d.name}, {"date": d.date}, d.project or "—", d.item, f"{flt(d.qty):,.0f} {d.uom or ''}",
				{"main": d.frm, "sub": d.po or ""}, {"money": d.value, "currency": cur}, d.by]} for d in _deliveries(names)], "empty": _("No deliveries to site yet.")}
	if tab == "stock":
		return {"title": _("Site stock"), "cols": [{"label": _("Project")}, {"label": _("Material")}, {"label": _("Received"), "cls": "num"}, {"label": _("Used"), "cls": "num"},
			{"label": _("Returned"), "cls": "num"}, {"label": _("Balance"), "cls": "num"}, {"label": _("Site value"), "cls": "num"}],
			"rows": [{"dt": "Project", "name": s.project, "cells": [{"main": s.project, "sub": P.project(s.project).project_name}, s.item, flt(s.recv), flt(s.used), flt(s.ret),
				{"main": f"{s.bal:,.0f} {s.uom}"}, {"money": s.value, "currency": cur}]} for s in _site_stock(names)], "empty": _("Nothing in the site stores.")}
	return {"title": _("Returns from site"), "cols": [{"label": _("Return")}, {"label": _("Date")}, {"label": _("Material")}, {"label": _("Qty")}, {"label": _("Reason")},
		{"label": _("Returned to")}, {"label": _("Value"), "cls": "num"}, {"label": _("Status")}],
		"rows": [{"dt": r.dt, "name": r.name, "cells": [{"code": r.name}, {"date": r.date}, r.item, f"{flt(r.qty):,.0f} {r.uom or ''}", r.reason, r.to, {"money": r.value, "currency": cur},
			{"pill": r.state, "tone": "green"}]} for r in _returns(names)], "empty": _("No returns from site.")}


# ================================================================ Progress & billing
def _ipcs(names):
	if not names or not _perm("Progress Certificate"):
		return []
	return frappe.get_list("Progress Certificate", filters={"project": ["in", names]}, fields=["name", "project", "certificate_no", "status", "period_to", "certified_on", "measured_on",
		"work_to_date", "this_period", "retention", "advance_recovery", "total_due", "sales_invoice", "consultant"], order_by="period_to desc, certificate_no desc", limit_page_length=0)


def _ipc_action(c):
	if c.status == "Draft":
		return _btn(_("Submit"), "ipc_submit", c.name)
	if c.status == "Submitted to consultant":
		return _btn(_("Record certification"), "ipc_certify", c.name, True)
	if c.status == "Certified" and not c.sales_invoice:
		return _btn(_("Create invoice"), "ipc_invoice", c.name, True, confirm=_("Create and submit the progress invoice for {0}?").format(c.name))
	return {"url": f"/printview?doctype=Progress%20Certificate&name={c.name}&format=Hipersign%20Interim%20Payment%20Certificate", "label": _("Print")}


def pj_bill_module():
	names = _names()
	cur = _cur(names)
	C = _ipcs(names)
	I = [i for n in names for i in P.fig(n).inv]
	y0 = getdate(today()).replace(month=1, day=1)
	vos = frappe.get_list("Variation Order", filters={"project": ["in", names or [""]]}, fields=["status", "amount"], limit_page_length=0) if _perm("Variation Order") else []
	over = [i for i in I if i.over]
	return {
		"title": _("Progress & billing"),
		"desc": _("Monthly measurement per BOQ line, consultant certification, progress invoices less advance recovery and retention, retention release and variations."),
		"new": [{"label": _("New variation"), "doctype": "Variation Order"}, {"label": _("New progress certificate"), "doctype": "Progress Certificate", "primary": 1}],
		"kpis": [
			kpi(_("Certified this year"), sum(flt(c.this_period) for c in C if c.status in ("Certified", "Invoiced") and c.certified_on and getdate(c.certified_on) >= y0),
				_("{0} certificate(s) with the consultant").format(len([c for c in C if c.status == "Submitted to consultant"])), "violet", "check", True, cur, tab="ipc"),
			kpi(_("Invoiced (incl. VAT)"), sum(i.total for i in I), _("{0} outstanding").format(_m(sum(i.out for i in I), cur)), "navy", "receipt", True, cur, tab="inv"),
			kpi(_("Overdue"), sum(i.out for i in over), _("{0} invoice(s)").format(len(over)), "red" if over else "green", "triangle-alert", True, cur, tab="inv"),
			kpi(_("Retention held by clients"), sum(P.fig(n).ret_held for n in names), _("Released after the defects period"), "amber", "lock", True, cur, tab="ret"),
			kpi(_("Advance to recover"), sum(P.fig(n).adv_left for n in names), _("Deducted pro rata from progress invoices"), "blue", "banknote", True, cur, tab="adv"),
			kpi(_("Variations"), sum(flt(v.amount) for v in vos if v.status == "Approved"), _("approved · {0} pending").format(_m(sum(flt(v.amount) for v in vos if v.status in ("Pending client", "Draft")), cur)),
				"green", "pencil", True, cur, tab="vo"),
		],
		"tabs": [
			{"key": "ipc", "label": _("Progress certificates"), "chips": [["all", _("All")], ["open", _("Open")], ["certified", _("Certified")], ["invoiced", _("Invoiced")]]},
			{"key": "meas", "label": _("Measurement"), "chips": _chips([n for n in names if 10 <= P.fig(n).step < 26] or names, False)},
			{"key": "inv", "label": _("Progress invoices") + (f" ({len(over)})" if over else ""), "chips": [["all", _("All")], ["Advance", _("Advance")], ["Progress", _("Progress")],
				["Retention", _("Retention")], ["open", _("Outstanding")]]},
			{"key": "ret", "label": _("Retention"), "chips": []},
			{"key": "adv", "label": _("Advance recovery"), "chips": []},
			{"key": "vo", "label": _("Variations") + (f" ({len([v for v in vos if v.status == 'Pending client'])})" if any(v.status == "Pending client" for v in vos) else ""),
				"chips": [["all", _("All")], ["Pending client", _("Pending client")], ["Approved", _("Approved")], ["Draft", _("Draft")], ["Rejected", _("Rejected")]]},
		],
	}


def pj_bill_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	if tab == "ipc":
		C = _ipcs(names)
		C = [c for c in C if chip in (None, "all") or (chip == "open" and c.status in ("Draft", "Submitted to consultant")) or (chip == "certified" and c.status == "Certified")
			or (chip == "invoiced" and c.status == "Invoiced")]
		tone = {"Certified": "green", "Invoiced": "green", "Draft": "grey"}
		return {"title": _("Progress certificates (interim payment certificates)"), "cols": [{"label": _("Certificate")}, {"label": _("Project")}, {"label": _("Cumulative"), "cls": "num"},
			{"label": _("This period"), "cls": "num"}, {"label": _("Retention"), "cls": "num"}, {"label": _("Advance recovery"), "cls": "num"}, {"label": _("Net due incl. VAT"), "cls": "num"},
			{"label": _("Status")}, {"label": ""}],
			"rows": [{"dt": "Progress Certificate", "name": c.name, "cells": [{"main": c.name, "sub": frappe.utils.formatdate(c.certified_on or c.period_to)},
				{"main": P.project(c.project).project_name, "sub": c.consultant or ""}, {"money": c.work_to_date, "currency": cur}, {"money": c.this_period, "currency": cur},
				{"money": c.retention, "currency": cur}, {"money": c.advance_recovery, "currency": cur}, {"money": c.total_due, "currency": cur},
				{"pill": _(c.status), "tone": tone.get(c.status, "orange"), **({"sub": c.sales_invoice} if c.sales_invoice else {})}, _ipc_action(c)]} for c in C],
			"empty": _("No progress certificates yet."), "nototal": 0}
	if tab == "meas":
		pj = _pick(chip, names)
		if not pj or not P.boq(pj):
			return {"cols": [], "rows": [], "empty": _empty_note()}
		p = P.project(pj)
		edit = 10 <= cint(p.hs_step) < 26
		open_c = [c for c in _ipcs([pj]) if c.status in ("Draft", "Submitted to consultant")]
		rows = []
		for r in P.boq(pj).items:
			rows.append({"cells": [{"main": f"{r.item_no} {r.description}"}, f"{flt(r.qty):,.0f} {r.unit or ''}", {"money": r.amount}, {"text": f"{flt(r.certified_pct):g}%"},
				{"input": flt(r.measured_pct), "min": flt(r.certified_pct), "max": 100, "act": "measure", "name": pj, "args": {"item_no": r.item_no}} if edit else {"text": f"{flt(r.measured_pct):g}%"},
				flt(flt(r.qty) * flt(r.measured_pct) / 100, 1), {"money": flt(r.amount) * (flt(r.measured_pct) - flt(r.certified_pct)) / 100},
				{"money": flt(r.amount) * flt(r.measured_pct) / 100}]})
		return {"title": _("Measurement — {0}").format(p.project_name) + (f" · {open_c[0].name}" if open_c else ""), "cols": [{"label": _("BOQ line")}, {"label": _("Qty")},
			{"label": _("Amount"), "cls": "num"}, {"label": _("Previous %")}, {"label": _("Cumulative % now")}, {"label": _("Qty to date"), "cls": "num"},
			{"label": _("Work this period"), "cls": "num"}, {"label": _("Work to date"), "cls": "num"}], "rows": rows}
	if tab == "inv":
		I = sorted([i for n in names for i in P.fig(n).inv], key=lambda i: (getdate(i.date), i.name), reverse=True)
		I = [i for i in I if chip in (None, "all") or i.kind == chip or (chip == "open" and i.out > 0.5)]
		pj_of = {i.name: n for n in names for i in P.fig(n).inv}
		return {"title": _("Progress, advance and retention invoices"), "cols": [{"label": _("Invoice")}, {"label": _("Type")}, {"label": _("Project")}, {"label": _("Gross"), "cls": "num"},
			{"label": _("Advance recovery"), "cls": "num"}, {"label": _("Retention"), "cls": "num"}, {"label": _("VAT"), "cls": "num"}, {"label": _("Total"), "cls": "num"},
			{"label": _("Outstanding"), "cls": "num"}, {"label": ""}],
			"rows": [{"dt": "Sales Invoice", "name": i.name, "cells": [{"main": i.name, "sub": _("{0} · due {1}").format(frappe.utils.formatdate(i.date), frappe.utils.formatdate(i.due))},
				{"pill": _(i.kind), "tone": {"Advance": "blue", "Retention": "orange"}.get(i.kind, "violet"), **({"sub": i.cert} if i.cert else {})}, pj_of[i.name],
				{"money": i.gross, "currency": cur}, {"money": i.adv, "currency": cur}, {"money": i.ret, "currency": cur}, {"money": i.vat, "currency": cur}, {"money": i.total, "currency": cur},
				{"money": i.out, "currency": cur, "neg": bool(i.over)},
				_btn(_("Record receipt"), "receive", i.name, confirm=_("Record the receipt of {0} against {1}?").format(_m(i.out, cur), i.name)) if i.out > 0.5 else {"pill": _("Paid"), "tone": "green"}]}
				for i in I], "empty": _("No project invoices yet.")}
	if tab == "ret":
		rows = []
		for n in names:
			F = P.fig(n)
			if F.step < 8:
				continue
			p = P.project(n)
			fin = p.expected_end_date
			due = _("Fully released") if F.step >= 26 else (_("50% at completion · balance {0}").format(frappe.utils.formatdate(add_days(fin, 30 * cint(p.hs_dlp_months)))) if F.step >= 21 and fin
				else _("At completion and after {0}-month DLP").format(cint(p.hs_dlp_months)))
			rows.append({"dt": "Project", "name": n, "cells": [_pcell(n), {"text": f"{flt(p.hs_retention_pct):g}%"}, {"money": sum(i.ret for i in F.inv if i.kind == "Progress"), "currency": cur},
				{"money": F.ret_released, "currency": cur}, {"money": F.ret_held, "currency": cur}, {"pill": due, "tone": "green"} if F.step >= 26 else due,
				_btn(_("Retention invoice"), "retention_invoice", n, confirm=_("Raise the retention release invoice for {0}?").format(n)) if 21 <= F.step < 26 and F.ret_held > 0.5 else ""]})
		return {"title": _("Retention"), "cols": [{"label": _("Project")}, {"label": _("Retention %")}, {"label": _("Deducted to date"), "cls": "num"}, {"label": _("Released"), "cls": "num"},
			{"label": _("Held by client"), "cls": "num"}, {"label": _("Release due")}, {"label": ""}], "rows": rows, "empty": _("No contracts past the advance yet.")}
	if tab == "adv":
		rows = []
		for n in names:
			F = P.fig(n)
			if F.step < 5:
				continue
			p = P.project(n)
			apg = [b for b in P.bonds(n) if "Advance" in (b.hs_bond_type or "")]
			soon = apg and apg[0].end_date and date_diff(apg[0].end_date, today()) <= 30 and (apg[0].hs_bond_status or "Active") != "Returned"
			rows.append({"dt": "Project", "name": n, "cells": [_pcell(n), {"text": f"{flt(p.hs_advance_pct):g}%"}, {"money": F.adv_amt, "currency": cur}, {"money": F.adv_rec, "currency": cur},
				{"money": F.adv_left, "currency": cur}, {"bar": F.adv_rec / F.adv_amt * 100 if F.adv_amt else 0},
				{"main": apg[0].bank_guarantee_number or apg[0].name, "sub": _("exp. {0} · {1}").format(frappe.utils.formatdate(apg[0].end_date), _(apg[0].hs_bond_status or "Active")), "late": bool(soon)} if apg else "—",
				_btn(_("Raise advance invoice"), "advance_invoice", n, True, confirm=_("Raise the advance invoice for {0}?").format(n)) if not F.adv_amt and flt(p.hs_advance_pct) else ""]})
		return {"title": _("Advance recovery"), "cols": [{"label": _("Project")}, {"label": _("Advance %")}, {"label": _("Advance received"), "cls": "num"}, {"label": _("Recovered"), "cls": "num"},
			{"label": _("Balance to recover"), "cls": "num"}, {"label": _("Recovered")}, {"label": _("APG")}, {"label": ""}], "rows": rows}
	V = frappe.get_list("Variation Order", filters=dict({"project": ["in", names or [""]]}, **({"status": chip} if chip and chip != "all" else {})),
		fields=["name", "project", "title", "amount", "status", "raised_on", "sent_on"], order_by="raised_on desc", limit_page_length=0) if _perm("Variation Order") else []
	rows = []
	for v in V:
		wait = date_diff(today(), v.sent_on or v.raised_on) if v.status == "Pending client" else None
		act = _btn(_("Send to client"), "vo_submit", v.name) if v.status == "Draft" else _btn(_("Client approved"), "vo_approve", v.name, True,
			confirm=_("Record the client's approval of {0}? The contract value goes up by {1}.").format(v.name, _m(v.amount, cur))) if v.status == "Pending client" else ""
		rows.append({"dt": "Variation Order", "name": v.name, "cells": [{"main": v.name, "sub": frappe.utils.formatdate(v.raised_on)}, v.project, v.title,
			{"money": v.amount, "currency": cur, "neg": flt(v.amount) < 0},
			{"pill": _(v.status), "tone": {"Approved": "green", "Draft": "grey", "Rejected": "red"}.get(v.status, "orange"), **({"sub": _("{0} days waiting").format(wait)} if wait is not None else {})}, act]})
	return {"title": _("Variations"), "cols": [{"label": _("Variation")}, {"label": _("Project")}, {"label": _("Description")}, {"label": _("Amount"), "cls": "num"}, {"label": _("Status")},
		{"label": ""}], "rows": rows, "empty": _("No variations.")}


# ================================================================ Subcontractors
def _scos(names):
	if not names or not _perm("Subcontract Order"):
		return []
	return frappe.get_list("Subcontract Order", filters={"project": ["in", names]}, fields=["name", "project", "supplier", "package", "order_value", "retention_pct", "status",
		"behind_programme", "order_date"], order_by="order_date desc", limit_page_length=0)


def _claims(scos):
	if not scos or not _perm("Subcontract Claim"):
		return []
	return frappe.get_list("Subcontract Claim", filters={"subcontract_order": ["in", [s.name for s in scos]]}, fields=["name", "subcontract_order", "project", "supplier", "claim_no",
		"claim_date", "claimed_to_date", "certified_to_date", "this_certified", "retention", "back_charges", "net_amount", "total", "status", "purchase_invoice"],
		order_by="claim_date desc, claim_no desc", limit_page_length=0)


def _sco_fig(s, CL, BC):
	cl = sorted([c for c in CL if c.subcontract_order == s.name], key=lambda c: cint(c.claim_no))
	cert = [c for c in cl if c.status in ("Certified", "Paid")]
	return frappe._dict(claimed=flt(cl[-1].claimed_to_date) if cl else 0, cert=flt(cert[-1].certified_to_date) if cert else 0,
		paid=sum(flt(c.this_certified) - flt(c.retention) - flt(c.back_charges) for c in cl if c.status == "Paid"),
		ret=sum(flt(c.retention) for c in cert), due=sum(flt(c.net_amount) for c in cl if c.status == "Certified"),
		bc=sum(flt(b.amount) for b in BC if b.subcontract_order == s.name and b.status in ("Agreed", "Deducted")))


def _bcs(scos):
	if not scos or not _perm("Back Charge"):
		return []
	return frappe.get_list("Back Charge", filters={"subcontract_order": ["in", [s.name for s in scos]]}, fields=["name", "subcontract_order", "supplier", "date", "reason", "amount", "status",
		"deducted_in"], order_by="date desc", limit_page_length=0)


def pj_sub_module():
	names = _names()
	cur = _cur(names)
	SC = _scos(names)
	CL = _claims(SC)
	BC = _bcs(SC)
	F = [_sco_fig(s, CL, BC) for s in SC]
	return {
		"title": _("Subcontractors"),
		"desc": _("Subcontract orders for MEP and joinery packages, their monthly claims, certification, retention and back-charges."),
		"new": [{"label": _("New subcontract order"), "doctype": "Subcontract Order", "primary": 1}],
		"kpis": [
			kpi(_("Subcontract value"), sum(flt(s.order_value) for s in SC), _("{0} orders · {1} active").format(len(SC), len([s for s in SC if s.status == "Active"])), "navy", "briefcase", True, cur, tab="sco"),
			kpi(_("Claimed to date"), sum(f.claimed for f in F), _("{0} claim(s) to certify").format(len([c for c in CL if c.status == "Submitted"])), "violet", "file-text", True, cur, tab="claims"),
			kpi(_("Certified"), sum(f.cert for f in F), _("By our QS"), "blue", "check", True, cur, tab="claims"),
			kpi(_("Paid"), sum(f.paid for f in F), _("{0} certified, unpaid").format(_m(sum(f.due for f in F), cur)), "green", "banknote", True, cur, tab="claims"),
			kpi(_("Retention held"), sum(f.ret for f in F), _("of certified claims"), "amber", "lock", True, cur, tab="ret"),
			kpi(_("Back-charges"), sum(flt(b.amount) for b in BC), _("{0} disputed").format(len([b for b in BC if b.status == "Disputed"])), "red", "triangle-alert", True, cur, tab="bc"),
		],
		"tabs": [{"key": "sco", "label": _("Subcontract orders"), "chips": []},
			{"key": "claims", "label": _("Claims") + (f" ({len([c for c in CL if c.status == 'Submitted'])})" if any(c.status == "Submitted" for c in CL) else ""), "chips": []},
			{"key": "ret", "label": _("Retention"), "chips": []}, {"key": "bc", "label": _("Back-charges"), "chips": []}],
	}


def pj_sub_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	SC = _scos(names)
	CL = _claims(SC)
	BC = _bcs(SC)
	if tab == "claims":
		sco = {s.name: s for s in SC}
		rows = []
		for c in CL:
			act = _btn(_("Certify"), "claim_certify", c.name, True) if c.status == "Submitted" else \
				_btn(_("Pay"), "claim_pay", c.name, confirm=_("Book the supplier bill (if not yet) and pay {0}?").format(c.name)) if c.status == "Certified" else \
				({"button": c.purchase_invoice, "open": ["Purchase Invoice", c.purchase_invoice]} if c.purchase_invoice else "")
			cert = c.status in ("Certified", "Paid")
			rows.append({"dt": "Subcontract Claim", "name": c.name, "cells": [{"main": c.name, "sub": frappe.utils.formatdate(c.claim_date)},
				{"main": sco[c.subcontract_order].supplier, "sub": f"{c.subcontract_order} · {c.project}"}, {"money": c.claimed_to_date, "currency": cur},
				{"money": c.certified_to_date, "currency": cur} if cert else "—", {"money": c.this_certified, "currency": cur} if cert else "—",
				{"money": c.retention, "currency": cur} if cert else "—", {"pill": _(c.status), "tone": {"Paid": "green", "Certified": "blue"}.get(c.status, "orange")}, act]})
		return {"title": _("Subcontractor claims"), "sub": _("Claim → QS certification (less retention and back-charges) → payment"), "nototal": 1,
			"cols": [{"label": _("Claim")}, {"label": _("Subcontractor")}, {"label": _("Claimed to date"), "cls": "num"}, {"label": _("Certified to date"), "cls": "num"},
				{"label": _("This claim"), "cls": "num"}, {"label": _("Retention"), "cls": "num"}, {"label": _("Status")}, {"label": ""}], "rows": rows, "empty": _("No claims yet.")}
	if tab == "ret":
		rows = []
		for s in SC:
			f = _sco_fig(s, CL, BC)
			if not f.cert:
				continue
			rows.append({"dt": "Subcontract Order", "name": s.name, "cells": [{"main": s.supplier, "sub": s.name}, {"money": f.cert, "currency": cur}, {"money": f.ret, "currency": cur},
				_("Half released at completion; balance after our DLP") if s.status == "Completed" else _("After practical completion of the main contract")]})
		return {"title": _("Retention held from subcontractors"), "cols": [{"label": _("Subcontractor")}, {"label": _("Certified"), "cls": "num"}, {"label": _("Retention held"), "cls": "num"},
			{"label": _("Release")}], "rows": rows, "empty": _("Nothing certified yet.")}
	if tab == "bc":
		return {"title": _("Back-charges"), "cols": [{"label": _("Back-charge")}, {"label": _("Date")}, {"label": _("Subcontractor")}, {"label": _("Reason")}, {"label": _("Amount"), "cls": "num"},
			{"label": _("Status")}], "rows": [{"dt": "Back Charge", "name": b.name, "cells": [{"code": b.name}, {"date": b.date}, b.supplier, b.reason, {"money": b.amount, "currency": cur},
				{"pill": _(b.status), "tone": "red" if b.status == "Disputed" else "green", **({"sub": b.deducted_in} if b.deducted_in else {})}]} for b in BC], "empty": _("No back-charges.")}
	rows = []
	for s in SC:
		f = _sco_fig(s, CL, BC)
		st = {"pill": _(s.status), "tone": {"Active": "blue", "Completed": "green"}.get(s.status, "orange")}
		if s.behind_programme:
			st["sub"] = _("Behind programme")
			st["late"] = 1
		rows.append({"dt": "Subcontract Order", "name": s.name, "cells": [{"main": s.name, "sub": frappe.utils.formatdate(s.order_date)}, {"main": s.supplier, "sub": s.package}, s.project,
			{"money": s.order_value, "currency": cur}, {"bar": f.cert / flt(s.order_value) * 100 if flt(s.order_value) else 0}, {"money": f.ret, "currency": cur}, st,
			_btn(_("Signed by both parties"), "sco_sign", s.name, True) if s.status in ("Pending signature", "Draft") else ""]})
	return {"title": _("Subcontract orders"), "cols": [{"label": _("Order")}, {"label": _("Subcontractor")}, {"label": _("Project")}, {"label": _("Order value"), "cls": "num"},
		{"label": _("Certified")}, {"label": _("Retention"), "cls": "num"}, {"label": _("Status")}, {"label": ""}], "rows": rows, "empty": _("No subcontract orders yet.")}


# ================================================================ Timesheets & labour
def _ts_rows(names, days=None):
	if not names or not _perm("Timesheet"):
		return []
	cond = " and date(td.from_time) >= %(d)s" if days else ""
	return frappe.db.sql(f"""select t.name, t.employee, t.employee_name, t.docstatus, td.project, td.task, td.activity_type, td.hours, td.costing_amount, td.costing_rate,
		date(td.from_time) as date from `tabTimesheet Detail` td join tabTimesheet t on t.name = td.parent where t.docstatus < 2 and td.project in %(p)s{cond}
		order by td.from_time desc""", {"p": tuple(names), "d": add_days(today(), -days) if days else None}, as_dict=True)


def _ot(r):
	return "overtime" in (r.activity_type or "").lower()


def pj_time_module():
	names = _names()
	cur = _cur(names)
	mon = _ts_rows(names, 30)
	last = max((r.date for r in mon), default=None)
	day = [r for r in mon if r.date == last]
	hrs = sum(flt(r.hours) for r in mon)
	cost = sum(flt(r.costing_amount) for r in mon)
	todo = len({r.name for r in _ts_rows(names) if r.docstatus == 0})
	return {
		"title": _("Timesheets & labour"),
		"desc": _("Daily hours by project and task, overtime, crew and labour cost — posted to the project cost heads."),
		"new": [{"label": _("New task"), "doctype": "Task"}, {"label": _("New timesheet"), "doctype": "Timesheet", "primary": 1}],
		"kpis": [
			kpi(_("Hours — last 30 days"), f"{hrs:,.0f}", _("{0} overtime hours").format(f"{sum(flt(r.hours) for r in mon if _ot(r)):,.0f}"), "blue", "clock", tab="ts"),
			kpi(_("Labour cost — last 30 days"), cost, _("Charged to tasks and cost heads"), "violet", "banknote", True, cur, tab="task"),
			kpi(_("Crew on site (last working day)"), len({r.employee for r in day}), _("{0} sites").format(len({r.project for r in day})), "navy", "users", tab="crew"),
			kpi(_("Average cost per hour"), f"{cur} {cost / hrs:,.2f}" if hrs else "—", _("Incl. 25% overtime premium"), "green", "calculator"),
			kpi(_("To approve"), todo, _("Timesheets"), "amber", "inbox", tab="ts"),
		],
		"tabs": [{"key": "ts", "label": _("Timesheets"), "chips": [["all", _("All")], ["draft", _("To approve")], ["approved", _("Approved")]]},
			{"key": "task", "label": _("By project & task"), "chips": []}, {"key": "crew", "label": _("Crew"), "chips": []}, {"key": "dsr", "label": _("Daily site reports"), "chips": []}],
	}


def pj_time_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	if tab == "task":
		tasks = frappe.get_list("Task", filters={"project": ["in", names or [""]], "type": ["!=", "Snag"]}, fields=["name", "subject", "project", "exp_start_date", "exp_end_date", "progress",
			"hs_task_owner", "hs_boq_item", "status"], order_by="project asc, name asc", limit_page_length=0) if _perm("Task") else []
		ts = _ts_rows(names)
		rows = []
		for t in tasks:
			xs = [r for r in ts if r.task == t.name]
			plan = 0
			if t.exp_start_date and t.exp_end_date:
				span = max(1, date_diff(t.exp_end_date, t.exp_start_date))
				plan = min(100, max(0, date_diff(today(), t.exp_start_date) / span * 100))
			rows.append({"dt": "Task", "name": t.name, "cells": [{"main": t.subject, "sub": f"{t.name} · {t.project} · {t.hs_task_owner or ''} · BOQ {t.hs_boq_item or '—'}"},
				f"{frappe.utils.formatdate(t.exp_start_date, 'dd MMM')} → {frappe.utils.formatdate(t.exp_end_date, 'dd MMM')}", {"text": f"{plan:.0f}%"},
				{"bar": flt(t.progress), "late": flt(t.progress) < plan - 8}, f"{sum(flt(r.hours) for r in xs):,.0f}", {"money": sum(flt(r.costing_amount) for r in xs), "currency": cur}]})
		return {"title": _("Hours and labour cost by project & task"), "sub": _("Planned % is where the task should be today"), "cols": [{"label": _("Task")}, {"label": _("Dates")},
			{"label": _("Planned %")}, {"label": _("Actual")}, {"label": _("Hours"), "cls": "num"}, {"label": _("Labour cost"), "cls": "num"}], "rows": rows, "empty": _("No tasks yet.")}
	if tab == "crew":
		mon = _ts_rows(names, 30)
		emps = {}
		for r in mon:
			e = emps.setdefault(r.employee, frappe._dict(name=r.employee_name, project=r.project, hrs=0, cost=0, rate=0))
			e.hrs += flt(r.hours)
			e.cost += flt(r.costing_amount)
			if not _ot(r):
				e.rate = flt(r.costing_rate)
		return {"title": _("Crew"), "cols": [{"label": _("Name")}, {"label": _("Trade")}, {"label": _("Project")}, {"label": _("Rate / hour"), "cls": "num"}, {"label": _("Hours — 30 days"), "cls": "num"},
			{"label": _("Labour cost"), "cls": "num"}],
			"rows": [{"dt": "Employee", "name": k, "cells": [{"main": e.name}, frappe.db.get_value("Employee", k, "designation") or "—", e.project, {"text": f"{e.rate:,.2f}"}, f"{e.hrs:,.0f}",
				{"money": e.cost, "currency": cur}]} for k, e in emps.items()], "empty": _("No hours booked in the last 30 days.")}
	if tab == "dsr":
		R = frappe.get_list("Daily Site Report", filters={"project": ["in", names or [""]]}, fields=["name", "project", "report_date", "manpower_own", "manpower_sub", "work_done", "issues",
			"reported_by"], order_by="report_date desc", limit_page_length=30) if _perm("Daily Site Report") else []
		return {"blocks": [{"type": "list", "span": 3, "title": _("Daily site reports"), "items": [{"dt": "Daily Site Report", "name": r.name,
			"label": f"{frappe.utils.formatdate(r.report_date)} · {P.project(r.project).project_name} — {r.reported_by or ''}",
			"sub": _("Manpower: {0} own · {1} subcontractor · Work done: {2} · Issues: {3}").format(cint(r.manpower_own), cint(r.manpower_sub), r.work_done or "—", r.issues or "—")} for r in R],
			"empty": _("No daily site reports yet."), "foot": [{"label": _("New daily site report"), "new": "Daily Site Report"}]}]}
	ts = _ts_rows(names)
	ts = [r for r in ts if chip in (None, "all") or (chip == "draft" and r.docstatus == 0) or (chip == "approved" and r.docstatus == 1)][:60]
	tasks = {t.name: t.subject for t in frappe.get_all("Task", filters={"name": ["in", list({r.task for r in ts if r.task}) or [""]]}, fields=["name", "subject"])}
	acts = [{"label": _("Approve submitted"), "method": ACT, "args": {"action": "timesheets", "name": "all"}, "primary": 1}] if any(r.docstatus == 0 for r in ts) else []
	return {"title": _("Timesheets"), "sub": _("Latest 60 lines"), "actions": acts,
		"cols": [{"label": _("Timesheet")}, {"label": _("Date")}, {"label": _("Employee")}, {"label": _("Project · task")}, {"label": _("Hours"), "cls": "num"}, {"label": _("Overtime"), "cls": "num"},
			{"label": _("Labour cost"), "cls": "num"}, {"label": _("Status")}],
		"rows": [{"dt": "Timesheet", "name": r.name, "cells": [{"code": r.name}, {"date": r.date}, {"main": r.employee_name, "sub": frappe.db.get_value("Employee", r.employee, "designation") or ""},
			{"main": r.project, "sub": tasks.get(r.task, "")}, "" if _ot(r) else flt(r.hours), flt(r.hours) if _ot(r) else "—", {"money": r.costing_amount, "currency": cur},
			{"pill": _("Approved") if r.docstatus == 1 else _("Submitted"), "tone": "green" if r.docstatus == 1 else "orange"}]} for r in ts],
		"empty": _("No timesheets yet.")}


# ================================================================ Project costing
def pj_cost_module():
	names = _names()
	return {
		"title": _("Project costing"),
		"desc": _("Budget vs committed vs actual by cost head, the forecast to complete and the forecast margin — reviewed every month."),
		"new": [],
		"links": [[_("Project Tracker"), ["project-tracker"]]],
		"kpis": _cost_kpis(_pick(None, names)) if names else [],
		"tabs": [{"key": "heads", "label": _("By cost head"), "chips": _chips(names)}, {"key": "all", "label": _("All projects"), "chips": []}],
		"nosearch": 1,
	}


def _cost_kpis(pj):
	if not pj:
		return []
	C = P.cost_of(pj)
	F = P.fig(pj)
	cur = F.currency
	return [
		kpi(_("Budget"), C.budget, _("From the estimate"), "navy", "calculator", True, cur),
		kpi(_("Committed"), C.committed, _("POs and subcontracts"), "violet", "file-text", True, cur),
		kpi(_("Actual cost to date"), C.actual, _("{0}% of the work done").format(round(F.pct)), "blue", "banknote", True, cur),
		kpi(_("Forecast at completion"), C.fac, ("+" if C.fac > C.budget else "") + _m(C.fac - C.budget, cur) + " " + _("vs budget"), "red" if C.fac > C.budget else "green", "trending-up", True, cur),
		kpi(_("Forecast margin"), _pct(F.margin), _("Budget {0} · revised contract {1}").format(_pct(F.bud_margin), _m(F.rev, cur)), "amber" if F.margin < F.bud_margin - 1 else "green", "chart-column"),
	]


def pj_cost_rows(tab, chip, q=None):
	names = _names()
	cur = _cur(names)
	if tab == "all":
		rows = []
		for n in names:
			C, F = P.cost_of(n), P.fig(n)
			rows.append({"dt": "Project", "name": n, "cells": [_pcell(n), {"money": C.budget, "currency": cur}, {"money": C.committed, "currency": cur}, {"money": C.actual, "currency": cur},
				{"money": C.fac, "currency": cur}, {"money": F.rev, "currency": cur}, {"text": _pct(F.margin), "tone": "red" if F.margin < F.bud_margin - 1 else "green"}]})
		return {"title": _("All projects — cost and margin"), "cols": [{"label": _("Project")}, {"label": _("Budget"), "cls": "num"}, {"label": _("Committed"), "cls": "num"},
			{"label": _("Actual"), "cls": "num"}, {"label": _("Forecast cost"), "cls": "num"}, {"label": _("Revised contract"), "cls": "num"}, {"label": _("Forecast margin %")}], "rows": rows}
	pj = _pick(chip, names)
	if not pj:
		return {"cols": [], "rows": [], "empty": _empty_note()}
	C, F, p = P.cost_of(pj), P.fig(pj), P.project(pj)
	hs = [h for h in P.HEADS if C.H[h].budget or C.H[h].actual]
	rows = []
	for h in hs:
		x = C.H[h]
		v = x.budget - x.fac
		rows.append({"cells": [{"main": _(h)}, {"money": x.budget}, {"money": x.committed}, {"money": x.actual}, {"money": x.ftc}, {"money": x.fac},
			{"text": ("−" if v < 0 else "+") + f"{abs(v):,.0f}", "tone": "red" if v < -0.5 else "green"}, {"bar": x.actual / x.budget * 100 if x.budget else 0}]})
	rows.append({"cls": "hsx-tot-row", "cells": [{"main": _("Total")}, {"money": C.budget}, {"money": C.committed}, {"money": C.actual}, {"money": C.ftc}, {"money": C.fac},
		{"text": ("−" if C.budget < C.fac else "+") + f"{abs(C.budget - C.fac):,.0f}", "tone": "red" if C.fac > C.budget else "green"}, {"bar": C.actual / C.budget * 100 if C.budget else 0}]})
	return {"kpis": _cost_kpis(pj), "blocks": [
		{"type": "table", "span": 3, "title": _("Budget vs committed vs actual — {0}").format(p.project_name), "sub": _("Actual = cost booked to the project (GL) + approved timesheets"),
			"cols": [{"label": _("Cost head")}, {"label": _("Budget"), "cls": "num"}, {"label": _("Committed"), "cls": "num"}, {"label": _("Actual"), "cls": "num"},
				{"label": _("Forecast to complete"), "cls": "num"}, {"label": _("Forecast at completion"), "cls": "num"}, {"label": _("Variance"), "cls": "num"}, {"label": _("Spent")}], "rows": rows},
		{"type": "card", "span": 2, "card": {"title": _("Forecast at completion by cost head"), "sub": _("budget {0}").format(_m(C.budget, cur)), "type": "bars", "currency": cur,
			"rows": [[f"{_(h)} · {_('budget')} {frappe.format(C.H[h].budget, {'fieldtype': 'Float', 'precision': 0})}", C.H[h].fac] for h in hs]}},
		{"type": "statement", "span": 1, "title": _("Project profit — {0}").format(p.project_name), "lines": [
			{"label": _("Revised contract value"), "value": F.rev, "currency": cur}, {"label": _("Forecast cost at completion"), "value": C.fac, "currency": cur},
			{"label": _("Forecast profit"), "value": F.rev - C.fac, "currency": cur, "total": 1}, {"label": _("Forecast margin"), "text": _pct(F.margin)},
			{"label": _("Budget margin"), "text": _pct(F.bud_margin)}, {"label": _("Pending variations (not in forecast)"), "value": F.vos_pend, "currency": cur, "muted": 1}]},
	]}


# ================================================================ Project Tracker
@frappe.whitelist()
def get_tracker(filter=None, q=None):
	"""Every project on one line through the 26 steps in 6 phases — status, % and date per step — with its red flags."""
	names = _names()
	cur = _cur(names)
	out = []
	for n in names:
		F = P.fig(n)
		p = P.project(n)
		fl = P.flags(n)
		if filter == "open" and F.step >= 26 or filter == "flags" and not fl or filter in ("Tender", "Mobilising", "Execution", "Handover", "Closed") and F.status != filter:
			continue
		if q and q.lower() not in f"{n} {p.project_name} {p.customer}".lower():
			continue
		st = P.states(n)
		out.append({"name": n, "title": p.project_name, "client": p.customer, "location": p.get("hs_location"), "finish": p.expected_end_date, "status": F.status,
			"tone": P.STATUS_TONE[F.status], "rev": F.rev, "pct": F.pct, "billed": F.billed_tot, "certified": F.certified, "collected": F.collected, "overdue": F.overdue, "out": F.out,
			"margin": F.margin, "bud_margin": F.bud_margin, "flags": fl,
			"states": [{"st": s.st, "pct": s.pct, "date": s.date, "tag": s.tag, "info": s.info, "by": s.by} for s in st]})
	allf = [P.fig(n) for n in names]
	nfl = sum(len(P.flags(n)) for n in names)
	return {"currency": cur, "projects": out, "steps": [{"name": _(s[0]), "short": _(s[1]), "who": _(s[3]), "docs": _(s[4])} for s in P.STEPS],
		"phases": [{"name": _(a), "a": b, "b": c} for a, b, c in P.PHASES],
		"counts": {"all": len(names), "open": len([f for f in allf if f.step < 26]), "flags": len([n for n in names if P.flags(n)])},
		"kpis": [kpi(_("Projects tracked"), len(names), _("{0} open").format(len([f for f in allf if f.step < 26])), "blue", "list"),
			kpi(_("Contract value"), sum(f.rev for f in allf), _("Incl. approved variations"), "navy", "file-text", True, cur),
			kpi(_("Certified"), sum(f.certified for f in allf), _("{0}% of contract value").format(round(sum(f.certified for f in allf) / sum(f.rev for f in allf) * 100) if sum(f.rev for f in allf) else 0),
				"violet", "check", True, cur),
			kpi(_("Collected"), sum(f.collected for f in allf), _("{0} retention held").format(_m(sum(f.ret_held for f in allf), cur)), "green", "banknote", True, cur),
			kpi(_("Red flags"), nfl, _("{0} projects need attention").format(len([n for n in names if P.flags(n)])), "red" if nfl else "green", "flag")]}
