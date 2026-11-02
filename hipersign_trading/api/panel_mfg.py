"""v1.8.0 (prototype p19): record panels for the Manufacturing records — the work order with the 22-step process stepper,
operations and job cards, materials and cost; the factory's sales order with the same stepper; the BOM with its tree,
routing and cost roll-up; the job card with the shop-floor buttons; the quality inspection with its readings and
certificate; the production plan. The buttons run hipersign_trading.api.manufacturing actions through api.panel.action
("mf:<action>")."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from hipersign_trading.api import manufacturing as M
from hipersign_trading.api.panel import _base, act, d, kv, link, money, pill, section

PF = {"Work Order": "Hipersign Job Ticket", "BOM": "Hipersign Bill of Materials", "Quality Inspection": "Hipersign QC Certificate", "label": "Hipersign Finished Goods Label"}


def _print_url(dt, name, fmt):
	return f"/printview?doctype={frappe.utils.quote(dt)}&name={frappe.utils.quote(name)}&format={frappe.utils.quote(fmt)}"


def _cur(company):
	return frappe.get_cached_value("Company", company, "default_currency")


def _wo_steps(wo):
	"""Made to stock: no sales order to follow — the steps the work order's own status has reached."""
	f = M.wo_fig(wo)
	reach = {"Draft": 7, "Not started": 8, "In process": 10, "Final QC": 13, "Completed": 15, "Closed": 22}.get(f.state, 7)
	return [frappe._dict(st="done" if i < reach else "cur" if i == reach else "wait", pct=100 if i < reach else 30 if i == reach else 0, date=None,
		tag=_("Done") if i < reach else _("In progress") if i == reach else _("Pending"), info=[], by=None) for i in range(M.N)]


def _buttons(so, wo, step):
	"""Under each step: open the screen for it, print what it prints, raise the document it needs, complete it."""
	b = {}
	go = {3: ["hipersign-planning"], 4: ["hipersign-planning"], 5: ["hipersign-planning"], 6: ["hipersign-quality"], 10: ["hipersign-shopfloor"],
		11: ["hipersign-quality"], 12: ["hipersign-quality"], 19: ["hipersign-mfg-costing"], 20: ["hipersign-mfg-costing"]}
	f = M.wo_fig(wo) if wo else None
	for i in range(M.N):
		row = []
		if i in go:
			row.append(act(_("Open screen"), route=go[i]))
		if wo and i == 8 and f.state in ("Not started", "In process") and not f.issued:
			row.append(act(_("Transfer to WIP"), client="mf_new", args={"key": "Stock Entry:wip", "values": {"work_order": wo}}))
		if wo and i == 9:
			row.append(act(_("Job ticket"), url=_print_url("Work Order", wo, PF["Work Order"])))
		if wo and i == 13:
			q = frappe.db.get_value("Quality Inspection", {"hs_work_order": wo, "hs_qc_stage": "Final", "docstatus": 1, "hs_certificate_no": ["is", "set"]}, "name")
			if q:
				row.append(act(_("QC certificate"), url=_print_url("Quality Inspection", q, PF["Quality Inspection"])))
			else:
				row.append(act(_("Final inspection"), client="mf_new", args={"key": "Quality Inspection", "values": {"hs_qc_stage": "Final", "hs_work_order": wo}}))
		if wo and i == 14 and f.state in ("In process", "Final QC"):
			row.append(act(_("Manufacture entry"), client="mf_new", args={"key": "Stock Entry:manufacture", "values": {"work_order": wo}}))
		if wo and i == 15:
			row.append(act(_("FG label"), url=_print_url("Work Order", wo, PF["label"])))
		if so and i == step and step < M.N:
			row.append(act(_("Complete step {0}").format(i + 1), "primary", action="mf:step", confirm=_("Complete step {0} — {1}?").format(i + 1, _(M.STEPS[i][0]))))
		if row:
			b[i] = row
	return b


def stepper(so, wo):
	step = M.so_fig(so).step if so else None
	st = M.states(so) if so else _wo_steps(wo)
	cur_i = next((i for i, x in enumerate(st) if x.st in ("cur", "late")), M.N - 1)
	return {"title": _("Process — 22 steps"), "kind": "stepper", "rows": [], "actions": [], "sel": min(cur_i, step if step is not None and step < M.N else cur_i),
		"steps": [{"name": _(s[0]), "short": _(s[1]), "what": _(s[2]), "who": _(s[3]), "docs": _(s[4]), "approval": _(s[5]), "next": _(s[6])} for s in M.STEPS],
		"phases": [{"name": _(n), "a": a, "b": b} for n, a, b in M.PHASES],
		"states": [{"st": x.st, "pct": x.pct, "date": x.date, "tag": x.tag, "info": x.info, "by": x.by} for x in st], "buttons": _buttons(so, wo, step)}


def work_order(doc):
	f = M.wo_fig(doc.name)
	cur = _cur(doc.company)
	p = _base(doc, f"{doc.name} — {_('work order')}", f.item_name)
	p["status"] = pill(_(f.state), M.STATE_TONE.get(f.state, "grey"))
	so = doc.sales_order if doc.sales_order and frappe.db.exists("Sales Order", doc.sales_order) else None
	main = so and M.main_wo(so) == doc.name
	p["facts"] = kv(("Product", f"{f.item_name} · {doc.production_item}"), ("BOM", f"{doc.bom_no} · {_('routing')} {len(doc.operations)} {_('operations')}"),
		("Quantity", _("{0} · produced {1} · scrap {2}").format(f"{f.qty:,.0f}", f"{f.done:,.0f}", f"{f.scrap:,.0f}")),
		("Start → due", f"{d(f.start)} → {d(f.due)}"), ("Sales order", link("Sales Order", so, f"{so} · {M.so_fig(so).customer_name}") if so else _("Made to stock")),
		("Standard cost", _("{0} per unit · {1}").format(frappe.format(f.std.total, {"fieldtype": "Currency", "options": cur}),
			frappe.format(f.std.total * f.qty, {"fieldtype": "Currency", "options": cur}))),
		("Status", pill(f.hold, "red") if f.hold and f.state in ("Draft", "Not started") else pill(_("Late"), "red") if f.late else pill(_(f.state), M.STATE_TONE.get(f.state))))
	sections = [stepper(so if main else None, doc.name)]
	sections.append(section("Operations & job cards", kind="table", cols=["Op", "Workstation", "Job card", "Operator", "Done", "Scrap", "Time"],
		rows=[[f"{o.idx * 10} · {o.op}", M.ws_rates(o.ws).workstation_name, link("Job Card", o.jc.name) if o.jc else "—",
			frappe.db.get_value("Employee", o.jc.hs_operator, "employee_name") if o.jc and o.jc.hs_operator else "—", {"bar": o.done / f.qty * 100 if f.qty else 0},
			f"{o.scrap:,.0f}", f"{int(o.mins // 60)}h {int(o.mins % 60):02d}"] for o in f.ops]))
	sections.append(section("Materials", kind="table", cols=["Component", "Required", "Issued", "Consumed", "Cost"],
		rows=[[f"{M.item_info(r.item_code).item_name} · {r.item_code}", f"{flt(r.required_qty):,.1f}", f"{flt(r.transferred_qty):,.1f}", f"{flt(r.consumed_qty):,.1f}",
			money(flt(r.required_qty) * (M.std(r.item_code).total if M.bom_of(r.item_code) else M.leaf_cost(r.item_code)), cur)] for r in doc.required_items]))
	if f.state in ("Completed", "Closed"):
		A = M.actual(doc.name)
		sections.append(section("Cost — actual vs standard", kv(("Standard", money(A.std, cur)), ("Material", money(A.mat, cur)), ("Labour", money(A.lab, cur)),
			("Overhead", money(A.ovh, cur)), ("Actual", money(A.total, cur)), ("Variance", pill(frappe.format(A.var, {"fieldtype": "Currency", "options": cur}), "red" if A.var > 0 else "green")))))
	if so and main:
		fl = M.flags(so)
		if fl:
			sections.append(section("Red flags", cols=["Level", "Issue", "Step"], kind="table", rows=[[pill(_(x["lvl"]), "red" if x["lvl"] == "High" else "orange"), x["text"],
				f"{x['step'] + 1} · {_(M.STEPS[x['step']][1])}"] for x in fl]))
	sections.append(section("Prints", kv(("Documents", _("Job ticket, finished-goods label"))), actions=[act(_("Job ticket"), url=_print_url("Work Order", doc.name, PF["Work Order"])),
		act(_("FG label"), url=_print_url("Work Order", doc.name, PF["label"]))]))
	p["sections"] = sections
	if so and main:
		hist = [[d(x.completed_on), _("Step {0} completed — {1} ({2})").format(x.step, _(x.step_name or ""), frappe.utils.get_fullname(x.completed_by))]
			for x in frappe.get_all("Manufacturing Step Log", filters={"sales_order": so}, fields=["step", "step_name", "completed_on", "completed_by"], order_by="completed_on asc")]
		p["history"] = (hist + p["history"])[-14:] if hist else p["history"]
	a = [act(_("Job ticket"), url=_print_url("Work Order", doc.name, PF["Work Order"])), act(_("FG label"), url=_print_url("Work Order", doc.name, PF["label"]))]
	if doc.docstatus == 0 and frappe.has_permission("Work Order", "submit", doc):
		a.append(act(_("Release"), "primary", action="mf:release", confirm=_("Release {0} to the shop floor?").format(doc.name)))
	if f.state in ("Not started", "In process") and not f.issued and frappe.has_permission("Stock Entry", "create"):
		a.append(act(_("Transfer to WIP"), client="mf_new", args={"key": "Stock Entry:wip", "values": {"work_order": doc.name}}))
	if f.state in ("In process", "Final QC") and frappe.has_permission("Stock Entry", "create"):
		a.append(act(_("Manufacture entry"), "primary", client="mf_new", args={"key": "Stock Entry:manufacture", "values": {"work_order": doc.name}}))
	if f.state == "Completed" and frappe.has_permission("Work Order", "write", doc):
		a.append(act(_("Close work order"), action="mf:close", confirm=_("Close {0}?").format(doc.name)))
	if so and main and M.so_fig(so).step < M.N:
		st = M.so_fig(so).step
		a.append(act(_("Complete step {0}").format(st + 1), "primary", action="mf:step", confirm=_("Complete step {0} — {1}?").format(st + 1, _(M.STEPS[st][0]))))
	p["actions"] = a
	return p


def sales_order(doc):
	"""The trading panel of the order, with the manufacturing stepper when the order's product is made here."""
	from hipersign_trading.api.panel import sales_order as base

	p = base(doc)
	it = doc.items[0].item_code if doc.items else None
	if not (it and M.bom_of(it)) or not frappe.db.exists("DocType", "Manufacturing Step Log"):
		return p
	F = M.so_fig(doc.name)
	if not p.get("facts"):
		p["facts"] = []
	p["facts"] = kv(("Product", F.item_name), ("Quantity", f"{F.qty:,.0f}"), ("Work order", link("Work Order", F.wo) if F.wo else "—"),
		("VAT", _("0% — export with proof of export") if F.export else "5%"), ("Status", pill(M.so_status(F.step, F.forecast)))) + p["facts"]
	p["sections"] = [stepper(doc.name, F.wo)] + p.get("sections", [])
	fl = M.flags(doc.name)
	if fl:
		p["sections"].insert(1, section("Red flags", cols=["Level", "Issue", "Step"], kind="table", rows=[[pill(_(x["lvl"]), "red" if x["lvl"] == "High" else "orange"),
			x["text"], f"{x['step'] + 1} · {_(M.STEPS[x['step']][1])}"] for x in fl]))
	if F.step < M.N:
		p["actions"] = [act(_("Complete step {0}").format(F.step + 1), "primary", action="mf:step", confirm=_("Complete step {0} — {1}?").format(F.step + 1,
			_(M.STEPS[F.step][0])))] + [a for a in p.get("actions", []) if a.get("kind") != "primary"]
	if F.wo:
		p["actions"].append(act(_("Open {0}").format(F.wo), client="mf_open", args={"doctype": "Work Order", "name": F.wo}))
	return p


def bom(doc):
	cur = _cur(doc.company)
	s = M.std_of_bom(doc.name) if doc.docstatus == 1 else frappe._dict(mat=flt(doc.raw_material_cost), lab=0, ovh=flt(doc.operating_cost), total=flt(doc.total_cost))
	ver = cint(doc.name.split("-")[-1]) if doc.name.split("-")[-1].isdigit() else 1
	p = _base(doc, f"{doc.name} — {doc.item_name}", _("Bill of materials · v{0}").format(ver))
	p["status"] = pill(_("Active") if doc.is_active and doc.is_default else _("Superseded") if not doc.is_active else _("Alternate"),
		"green" if doc.is_active and doc.is_default else "grey")
	p["facts"] = kv(("Product", f"{doc.item_name} · {doc.item}"), ("Quantity", f"{flt(doc.quantity):g} {doc.uom or ''}"), ("Change note", doc.get("hs_change_note")),
		("Routing", doc.routing))
	rows = []
	if doc.docstatus == 1:
		for r in M.bom_tree(doc.name):
			rows.append([("└ " if r.d else "") + M.item_info(r.item).item_name, r.item, f"{r.qty:,.2f}", money(r.unit, cur), money(r.ext, cur) if not r.d else f"({r.ext:,.2f})"])
	else:
		rows = [[r.item_name, r.item_code, f"{flt(r.qty):,.2f}", money(r.rate, cur), money(r.amount, cur)] for r in doc.items]
	p["sections"] = [section("BOM tree", kind="table", cols=["Component", "Code", "Qty per unit", "Unit cost", "Cost"], rows=rows),
		section("Routing", kind="table", cols=["Op", "Operation", "Workstation", "Minutes"], rows=[[str(o.idx * 10), o.operation, M.ws_rates(o.workstation).workstation_name,
			f"{flt(o.time_in_mins) / (flt(doc.quantity) or 1):,.2f}"] for o in doc.operations]),
		section("Cost roll-up", kv(("Material (from BOM)", money(s.mat, cur)), ("Labour (from routing)", money(s.lab, cur)), ("Overhead (from routing)", money(s.ovh, cur)),
			("Standard cost per unit", money(s.total, cur))))]
	p["actions"] = [act(_("Print BOM"), url=_print_url("BOM", doc.name, PF["BOM"]))]
	if frappe.has_permission("BOM", "create"):
		p["actions"].append(act(_("New version"), client="mf_new", args={"key": "BOM", "values": {"item": doc.item}}))
	return p


def job_card(doc):
	w = M.wo_fig(doc.work_order) if doc.work_order else None
	p = _base(doc, f"{doc.name} — {_('job card')}", f"{_('Op')} {cint(doc.operation_row_id) * 10 or ''} · {doc.operation} · {M.ws_rates(doc.workstation).workstation_name}")
	run = M.open_log(doc.name) if doc.docstatus == 0 else None
	state = "Completed" if doc.docstatus == 1 else "On hold" if doc.is_paused else M.JC_STATE.get(doc.status, "Open")
	p["status"] = pill(_(state), {"Completed": "green", "Work in progress": "blue", "On hold": "red"}.get(state, "grey"))
	done = sum(flt(r.completed_qty) for r in doc.time_logs)
	p["facts"] = kv(("Work order", link("Work Order", doc.work_order, f"{doc.work_order} · {w.item_name}") if w else ""), ("Planned", f"{flt(doc.for_quantity):,.0f}"),
		("Done", f"{done:,.0f}"), ("Scrap", f"{flt(doc.hs_scrap_qty):,.0f}"), ("Time", f"{int(flt(doc.total_time_in_mins) // 60)}h {int(flt(doc.total_time_in_mins) % 60):02d}"),
		("Operator", frappe.db.get_value("Employee", doc.hs_operator, "employee_name") if doc.hs_operator else "—"),
		("Running since", frappe.utils.get_datetime(run.from_time).strftime("%H:%M") if run else ""))
	p["sections"] = [section("Time logs", kind="table", cols=["From", "To", "Minutes", "Quantity"], rows=[[str(r.from_time or "")[:16], str(r.to_time or "")[:16] or _("running"),
		f"{flt(r.time_in_mins):,.0f}", f"{flt(r.completed_qty):,.0f}"] for r in doc.time_logs])]
	a = []
	if doc.docstatus == 0 and frappe.has_permission("Job Card", "write", doc):
		a.append(act(_("Pause"), action="mf:jc_pause") if run else act(_("Start"), "primary", action="mf:jc_start"))
		a += [act("+10", action="mf:jc_qty", args={"n": 10}), act("+50", action="mf:jc_qty", args={"n": 50}), act(_("Scrap +1"), action="mf:jc_scrap"),
			act(_("Complete"), "primary", action="mf:jc_done", confirm=_("Complete {0}? The remaining units are recorded as done.").format(doc.name))]
	a.append(act(_("Shop floor"), route=["hipersign-shopfloor"]))
	p["actions"] = a
	return p


def quality_inspection(doc):
	res = doc.get("hs_result") or ("Pending" if doc.docstatus == 0 else doc.status)
	p = _base(doc, f"{doc.name} — {_(doc.get('hs_qc_stage') or doc.inspection_type)} {_('inspection')}", f"{doc.item_name} · {doc.reference_type} {doc.reference_name}")
	p["status"] = pill(_(res), {"Accepted": "green", "Accepted with deviation": "green", "Pending": "orange", "Rework": "orange"}.get(res, "red"))
	p["facts"] = kv(("Reference", link(doc.reference_type, doc.reference_name) if doc.reference_name else ""), ("Work order", link("Work Order", doc.hs_work_order) if doc.get("hs_work_order") else ""),
		("Operation", doc.get("hs_operation")), ("Lot / batch quantity", f"{flt(doc.hs_lot_qty):,.0f}"), ("Sample (AQL 1.0)", _("{0} · {1} fails").format(f"{flt(doc.sample_size):,.0f}",
		cint(doc.hs_fails))), ("Rejected", f"{flt(doc.hs_rejected_qty):,.0f}" if flt(doc.hs_rejected_qty) else ""),
		("Rework", _("{0} of {1} done").format(f"{flt(doc.hs_rework_done):,.0f}", f"{flt(doc.hs_rework_qty):,.0f}") if flt(doc.hs_rework_qty) else ""),
		("Certificate", doc.get("hs_certificate_no")), ("Inspected by", frappe.utils.get_fullname(doc.inspected_by) if doc.inspected_by else ""), ("Remarks", doc.remarks))
	if doc.readings:
		p["sections"] = [section("Tests", kind="table", cols=["Test", "Specification", "Result", "Status"], rows=[[r.specification, r.value or "", r.reading_value or r.reading_1 or "",
			pill(_(r.status or "Accepted"), "green" if (r.status or "Accepted") == "Accepted" else "red")] for r in doc.readings])]
	a = []
	if doc.get("hs_certificate_no"):
		a.append(act(_("QC certificate"), url=_print_url("Quality Inspection", doc.name, PF["Quality Inspection"])))
	if doc.docstatus == 0 and frappe.has_permission("Quality Inspection", "submit", doc):
		a += [act(_("Reject"), action="mf:qi_reject", confirm=_("Reject {0}?").format(doc.name)), act(_("Accept"), "primary", action="mf:qi_accept")]
	if doc.docstatus == 1 and flt(doc.hs_rework_qty) > flt(doc.hs_rework_done):
		a.append(act(_("Rework done +4"), action="mf:qi_rework", args={"n": 4}))
	p["actions"] = a
	return p


def production_plan(doc):
	p = _base(doc, f"{doc.name} — {_('production plan')}", frappe.utils.formatdate(doc.posting_date))
	wos = frappe.get_all("Work Order", filters={"production_plan": doc.name, "docstatus": ["<", 2]}, pluck="name", order_by="name asc")
	mrs = frappe.db.sql_list("select distinct parent from `tabMaterial Request Item` where production_plan = %s and docstatus < 2", doc.name)
	p["facts"] = kv(("Sales orders", ", ".join(r.sales_order for r in doc.sales_orders) or "—"), ("Planned by", frappe.utils.get_fullname(doc.owner)))
	p["sections"] = [section("Items to make", kind="table", cols=["Item", "BOM", "Planned", "Produced"], rows=[[f"{r.item_code}", r.bom_no, f"{flt(r.planned_qty):,.0f}",
		f"{flt(r.produced_qty):,.0f}"] for r in doc.po_items]),
		section("Work orders", kind="table", cols=["Work order", "Product", "Qty", "Status"], rows=[[link("Work Order", w), M.wo_fig(w).item_name, f"{M.wo_fig(w).qty:,.0f}",
			pill(_(M.wo_fig(w).state), M.STATE_TONE.get(M.wo_fig(w).state))] for w in wos]),
		section("Material requests", kind="table", cols=["Request"], rows=[[link("Material Request", m)] for m in mrs])]
	return p


BUILDERS = {"Work Order": work_order, "Sales Order": sales_order, "BOM": bom, "Job Card": job_card, "Quality Inspection": quality_inspection,
	"Production Plan": production_plan}


def action(doc, action, args):
	"""mf:<action> buttons on these panels → api.manufacturing.act (the same rules as the pages)."""
	if not action.startswith("mf:"):
		return None
	return M.act(action[3:], doc.name, args)
