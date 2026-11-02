"""v1.8.0 (prototype p19, homeModules): the industry modules on Home — a Projects card and a Manufacturing card, each with
four figures that open their page and the open projects / work orders below. A card shows only when its feature is switched
on and the user may open the module's page. A QC Inspector (Quality, not Production) gets a Quality card instead."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, today

from hipersign_trading.features import feature_on


def _page_ok(page):
	try:
		return bool(frappe.db.exists("Page", page)) and frappe.get_cached_doc("Page", page).is_permitted()
	except Exception:
		return False


def _go(page, tab=None):
	"""A route the user may open (None when the page is not theirs)."""
	if not _page_ok(page):
		return None
	return {"route": [page], "options": {"hs_tab": tab} if tab else None}


def _wos(n):
	return _("{0} WO").format(n) if n == 1 else _("{0} WOs").format(n)


def _co_title(cos):
	if len(cos) == 1:
		return cos[0]
	return _("{0} companies").format(len(cos)) if cos else ""


def projects_card():
	if not feature_on("projects") or not _page_ok("hipersign-projects"):
		return None
	from hipersign_trading.api import module_prj as MP
	from hipersign_trading.api import projects as P

	names = MP._names()
	if not names:
		return None
	cur = MP._cur(names)
	F = [P.fig(n) for n in names if P.fig(n).step >= 5]
	rev = sum(f.rev for f in F)
	done = sum(f.rev * f.pct / 100 for f in F)
	nfl = sum(len(P.flags(n)) for n in names)
	cos = sorted({P.project(n).company for n in names})
	rows = []
	for n in names:
		f = P.fig(n)
		if f.step >= 26:
			continue
		st = min(25, int(f.step))
		rows.append({"doctype": "Project", "name": n, "title": P.project(n).project_name, "sub": f"{st + 1}. {_(P.STEPS[st][1])}", "pct": flt(f.pct, 1),
			"flags": len(P.flags(n))})
	return {
		"key": "projects", "icon": "chart-gantt", "title": _("Projects — {0}").format(_co_title(cos)),
		"tracker": _go("project-tracker"),
		"kpis": [
			{"label": _("Contract value"), "value": rev, "money": 1, "currency": cur, **(_go("hipersign-projects") or {})},
			{"label": _("Work done"), "value": f"{done / rev * 100:.0f}%" if rev else "0%", **(_go("hipersign-projects") or {})},
			{"label": _("Collected"), "value": sum(f.collected for f in F), "money": 1, "currency": cur, **(_go("hipersign-billing", "inv") or {})},
			{"label": _("Red flags"), "value": nfl, "neg": 1 if nfl else 0, **(_go("project-tracker") or {})},
		],
		"rows": rows[:8],
	}


def manufacturing_card():
	if not feature_on("manufacturing") or not _page_ok("hipersign-production"):
		return None
	from hipersign_trading.api import manufacturing as M
	from hipersign_trading.api import module_mfg as MM

	cos = MM._cos()
	if not cos:
		return None
	W = [M.wo_fig(n) for n in M.wo_names(cos)]
	late = [w for w in W if w.late]
	short = [x for x in M.shortages(cos) if x.short]
	nfl = sum(len(M.flags(s)) for s in M.so_names(cos))
	rows = [{"doctype": "Work Order", "name": w.name, "title": f"{w.name} · {w.item_name}",
		"sub": _("{0} · due {1}").format(_(w.state), frappe.utils.formatdate(w.due, "dd MMM") if w.due else "—"),
		"pct": flt(w.done / w.qty * 100, 1) if w.qty else 0, "alert": 1 if (w.late or w.hold) else 0}
		for w in W if w.state in ("In process", "Final QC", "Not started")]
	return {
		"key": "manufacturing", "icon": "wrench", "title": _("Manufacturing — {0}").format(_co_title(cos)),
		"tracker": _go("production-tracker"),
		"kpis": [
			{"label": _("In process"), "value": _wos(len([w for w in W if w.state in ("In process", "Final QC")])), **(_go("hipersign-production") or {})},
			{"label": _("Late"), "value": len(late), "neg": 1 if late else 0, **(_go("hipersign-production", "wo") or {})},
			{"label": _("Shortages"), "value": len(short), "neg": 1 if short else 0, **(_go("hipersign-planning", "short") or {})},
			{"label": _("Red flags"), "value": nfl, "neg": 1 if nfl else 0, **(_go("production-tracker") or {})},
		],
		"rows": rows[:8],
	}


def quality_card():
	"""For the QC Inspector (and others who reach Quality but not Production): what waits for inspection."""
	if not feature_on("manufacturing") or not _page_ok("hipersign-quality") or _page_ok("hipersign-production"):
		return None
	from hipersign_trading.api import manufacturing as M
	from hipersign_trading.api import module_mfg as MM

	cos = MM._cos()
	if not cos:
		return None
	Q = MM._qis(cos)
	pend = [q for q in Q if q.docstatus == 0]
	dec = [q for q in Q if q.docstatus == 1 and q.report_date and getdate(q.report_date) >= getdate(add_days(today(), -30))]
	rework = sum(flt(q.hs_rework_qty) - flt(q.hs_rework_done) for q in Q)
	W = [M.wo_fig(n) for n in M.wo_names(cos)]
	fqc = [w for w in W if w.state == "Final QC"]
	stage = {"Incoming": _("Incoming"), "In-process": _("In-process"), "Final": _("Final")}
	rows = [{"doctype": "Quality Inspection", "name": q.name, "title": f"{q.name} · {q.item_name or q.item_code}",
		"sub": " · ".join(x for x in [stage.get(q.hs_qc_stage, _(q.hs_qc_stage or "")), q.hs_work_order or q.reference_name or ""] if x), "pct": None, "alert": 0} for q in pend]
	rows += [{"doctype": "Work Order", "name": w.name, "title": f"{w.name} · {w.item_name}", "sub": _("Final QC · due {0}").format(frappe.utils.formatdate(w.due, "dd MMM") if w.due else "—"),
		"pct": flt(w.done / w.qty * 100, 1) if w.qty else 0, "alert": 1 if w.late else 0} for w in fqc]
	return {
		"key": "quality", "icon": "shield-check", "title": _("Quality — {0}").format(_co_title(cos)),
		"tracker": _go("production-tracker"),
		"kpis": [
			{"label": _("To inspect"), "value": len(pend), "neg": 0, **(_go("hipersign-quality") or {})},
			{"label": _("Pass rate — 30 days"), "value": f"{len([q for q in dec if q.hs_result == 'Accepted']) / max(1, len(dec)) * 100:.0f}%", **(_go("hipersign-quality", "fin") or {})},
			{"label": _("Rework open"), "value": f"{rework:,.0f}", "neg": 1 if rework > 0 else 0, **(_go("hipersign-quality", "rej") or {})},
			{"label": _("In final QC"), "value": _wos(len(fqc)), **(_go("hipersign-shopfloor") or {})},
		],
		"rows": rows[:8],
		"empty": _("Nothing waiting for inspection."),
	}


def modules():
	out = []
	for fn in (projects_card, manufacturing_card, quality_card):
		try:
			c = fn()
		except frappe.PermissionError:
			c = None
			frappe.clear_last_message()
		if c:
			out.append(c)
	return out
