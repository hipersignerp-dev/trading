"""v1.8.0 (prototype p19): the Projects create windows (hs_projects.js → api.create.save_doc): project, BOQ lines, task,
timesheet, progress certificate, variation, subcontract order, material request to site and site transfer.
The _pre_ / _after_ hooks here are picked up by api.create.save_doc like its own."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, today

from hipersign_trading.api import projects as P

DOCTYPES = {"Project", "Project BOQ", "Task", "Timesheet", "Progress Certificate", "Variation Order", "Subcontract Order", "Daily Site Report"}


def _step_logs(p, upto):
	for i in range(upto):
		P._log(p, i, _("Recorded when the project was created (already awarded)"))


def pre_project(doc, v, rows):
	st = cint(v.get("_stage"))
	doc.hs_step = st
	doc.hs_enquiry_date = today()
	doc.status = "Open"
	doc.percent_complete_method = "Manual"
	if st >= 5:
		doc.hs_award_date = today()
	if not doc.get("company"):
		doc.company = v.get("company")


def after_project(doc, v, rows):
	cv = flt(doc.hs_contract_value)
	st = cint(doc.hs_step)
	b = frappe.get_doc({"doctype": "Project BOQ", "title": doc.project_name, "project": doc.name, "customer": doc.customer, "company": doc.company,
		"status": "Awarded" if st >= 5 else "Being priced", "received_on": today(), "due_date": doc.get("hs_tender_due"), "revision": 0, "target_margin": 17, "overhead_pct": 4,
		"items": [{"section": "A", "section_name": _("Preliminaries"), "item_no": "A1", "description": _("Preliminaries & general"), "unit": "LS", "qty": 1, "rate": flt(cv * 0.06, 2), "ovh_share": 80},
			{"section": "B", "section_name": _("Works"), "item_no": "B1", "description": _("Fit-out works (to be detailed in the BOQ)"), "unit": "LS", "qty": 1, "rate": flt(cv * 0.94, 2),
				"mat_share": 50, "lab_share": 30}]})
	b.insert()
	if st >= 5:
		_step_logs(doc, st)
	doc.add_comment("Info", _("Created at step {0} — {1}").format(st + 1, _(P.STEPS[st][0])))
	frappe.flags.hs_create_msg = _("{0} created · {1}").format(doc.name, _("tender stage — price the BOQ next") if st < 5 else _("contract stage — request the bonds next"))


def pre_project_boq(doc, v, rows):
	"""BOQ lines for a project: added to its BOQ (a new BOQ when it has none)."""
	if not v.get("project"):
		frappe.throw(_("Choose the project"))
	lines = [r for r in rows if r.get("description") and flt(r.get("qty")) and flt(r.get("rate"))]
	if not lines:
		frappe.throw(_("Add at least one BOQ line with quantity and rate"))
	p = frappe.get_doc("Project", v.project)
	sec_txt = (v.get("_section") or "E — Additional works").strip()
	sec = (sec_txt[:1] or "E").upper()
	sec_name = sec_txt.split("—", 1)[-1].split("-", 1)[-1].strip() if ("—" in sec_txt or " - " in sec_txt) else sec_txt
	name = frappe.db.get_value("Project BOQ", {"project": p.name, "status": "Awarded"}) or frappe.db.get_value("Project BOQ", {"project": p.name}, order_by="modified desc")
	b = frappe.get_doc("Project BOQ", name) if name else doc
	if not name:
		b.update({"title": p.project_name, "project": p.name, "customer": p.customer, "company": p.company, "status": "Awarded" if cint(p.hs_step) >= 5 else "Being priced"})
	n = len([r for r in b.items if r.section == sec])
	for r in lines:
		n += 1
		b.append("items", {"section": sec, "section_name": sec_name, "item_no": f"{sec}{n}", "description": r["description"], "unit": r.get("unit") or "Nos",
			"qty": flt(r["qty"]), "rate": flt(r["rate"]), "mat_share": 48, "lab_share": 32})
	for f in ("revision", "target_margin", "notes"):
		if v.get(f) not in (None, ""):
			b.set(f, v.get(f))
	if name:
		b.save()
		b.flags.hs_done = b
	if cint(p.hs_step) < 5:
		frappe.flags.hs_boq_contract = p.name
	total = sum(flt(r["qty"]) * flt(r["rate"]) for r in lines)
	frappe.flags.hs_create_msg = _("{0} BOQ lines added to {1} · {2}").format(len(lines), p.name, P._money(total))
	return b


def after_project_boq(doc, v, rows):
	pj = frappe.flags.get("hs_boq_contract")
	frappe.flags.hs_boq_contract = None
	if pj:
		frappe.db.set_value("Project", pj, "hs_contract_value", flt(doc.total_amount))


def pre_task(doc, v, rows):
	if v.get("project"):
		doc.company = frappe.db.get_value("Project", v.project, "company")


def pre_timesheet(doc, v, rows):
	"""Hours of one employee on one day for a project and task — site work plus overtime at 125%."""
	if not v.get("employee") or not v.get("_project"):
		frappe.throw(_("Choose the employee and the project"))
	doc.employee = v.employee
	doc.company = frappe.db.get_value("Employee", v.employee, "company") or frappe.db.get_value("Project", v._project, "company")
	doc.parent_project = v._project
	day = getdate(v.get("_date") or today())
	hrs, ot = flt(v.get("_hours") or 8), flt(v.get("_ot"))

	def rate(act):
		return flt(frappe.db.get_value("Activity Cost", {"employee": v.employee, "activity_type": act}, "costing_rate")) \
			or flt(frappe.db.get_value("Activity Type", act, "costing_rate"))

	for act in ("Site work", "Overtime"):
		if not frappe.db.exists("Activity Type", act):
			frappe.get_doc({"doctype": "Activity Type", "activity_type": act, "costing_rate": 0}).insert(ignore_permissions=True)
	start = get_datetime(f"{day} 07:00:00")
	doc.append("time_logs", {"activity_type": "Site work", "from_time": start, "hours": hrs, "to_time": frappe.utils.add_to_date(start, hours=hrs), "project": v._project,
		"task": v.get("_task") or None, "costing_rate": rate("Site work"), "is_billable": 0, "description": v.get("note")})
	if ot:
		s2 = frappe.utils.add_to_date(start, hours=hrs)
		doc.append("time_logs", {"activity_type": "Overtime", "from_time": s2, "hours": ot, "to_time": frappe.utils.add_to_date(s2, hours=ot), "project": v._project,
			"task": v.get("_task") or None, "costing_rate": rate("Overtime") or rate("Site work") * 1.25, "is_billable": 0})
	cost = sum(flt(r.hours) * flt(r.costing_rate) for r in doc.time_logs)
	frappe.flags.hs_create_msg = _("{0} h · {1} — sent for approval").format(f"{hrs + ot:g}", P._money(cost))


def pre_progress_certificate(doc, v, rows):
	p = frappe.get_doc("Project", v.project)
	op = frappe.db.get_value("Progress Certificate", {"project": p.name, "status": ["in", ["Draft", "Submitted to consultant"]]})
	if op:
		frappe.throw(_("{0} is still open — measure on it first (Progress & billing → Measurement).").format(op))
	if not 10 <= cint(p.hs_step) < 26:
		frappe.throw(_("{0} is not in execution yet — certificates start after the budget (step 10).").format(p.name))
	doc.company = p.company
	doc.status = "Submitted to consultant" if v.get("_action") == "submit" else "Draft"
	doc.measured_on = today()
	if not v.get("consultant"):
		doc.consultant = p.get("hs_consultant")


def after_progress_certificate(doc, v, rows):
	if flt(doc.this_period) <= 0:
		frappe.msgprint(_("Nothing is measured beyond the last certificate yet — enter the measurement on the BOQ lines (Progress & billing → Measurement); the certificate follows."),
			indicator="orange", alert=True)
	frappe.flags.hs_create_msg = _("{0} {1} — {2} this period").format(doc.name, _("sent to {0}").format(doc.consultant or _("the consultant"))
		if doc.status != "Draft" else _("saved as draft"), P._money(doc.this_period))


def pre_variation_order(doc, v, rows):
	doc.company = frappe.db.get_value("Project", v.project, "company")
	doc.status = "Pending client" if v.get("_action") == "submit" else "Draft"
	if doc.status == "Pending client":
		doc.sent_on = today()
	doc.raised_on = today()


def pre_subcontract_order(doc, v, rows):
	doc.company = frappe.db.get_value("Project", v.project, "company")
	doc.status = "Pending signature" if v.get("_action") == "submit" else "Draft"
	doc.order_date = today()


def pre_daily_site_report(doc, v, rows):
	"""v1.8.0: the daily site report — on the project's company, reported by the user unless another name is given."""
	if not v.get("project") or not frappe.db.exists("Project", v.project):
		frappe.throw(_("Choose the project"))
	if not (v.get("work_done") or "").strip():
		frappe.throw(_("Describe the work done"))
	if cint(v.get("manpower_own")) < 0 or cint(v.get("manpower_sub")) < 0:
		frappe.throw(_("Manpower cannot be negative"))
	day = getdate(v.get("report_date") or today())
	if day > getdate(today()):
		frappe.throw(_("A daily site report cannot be dated in the future"))
	doc.company = frappe.db.get_value("Project", v.project, "company")
	if not v.get("reported_by"):
		doc.reported_by = frappe.utils.get_fullname(frappe.session.user)
	if frappe.db.exists("Daily Site Report", {"project": v.project, "report_date": day}):
		frappe.msgprint(_("{0} already has a report for {1} — this one is added beside it.").format(v.project, frappe.utils.formatdate(day)), indicator="orange", alert=True)
	man = cint(v.get("manpower_own")) + cint(v.get("manpower_sub"))
	frappe.flags.hs_create_msg = _("{0} saved · {1} on site").format("{0}", _("{0} people").format(man))


def pre_material_request_site(doc, v, rows):
	"""Material request to site, against a BOQ line: Purchase, delivered to the project's site store; over the remaining BOQ
	quantity it is flagged for the Managing Director."""
	pj, line = (str(v.get("_boq") or "").split("|") + [""])[:2]
	if not pj or not frappe.db.exists("Project", pj):
		frappe.throw(_("Choose the project and BOQ line"))
	if not v.get("item_code") or not flt(v.get("qty")):
		frappe.throw(_("Choose the material and the quantity"))
	p = frappe.get_doc("Project", pj)
	doc.company = p.company
	doc.material_request_type = "Purchase"
	doc.transaction_date = today()
	doc.hs_project = pj
	need = v.get("schedule_date") or add_days(today(), 10)
	doc.schedule_date = need
	wh = P.site_warehouse(p) if v.get("_from") != "Main store" else (P.main_store(p.company) or P.site_warehouse(p))
	doc.append("items", {"item_code": v.item_code, "qty": flt(v.qty), "schedule_date": need, "warehouse": wh, "project": pj, "hs_boq_item": line})
	b = P.boq(pj)
	row = next((r for r in (b.items if b else []) if r.item_no == line), None)
	uom = frappe.get_cached_value("Item", v.item_code, "stock_uom")
	if row and (row.unit or "") == (uom or "") and flt(v.qty) > flt(row.qty) * (1 - flt(row.measured_pct) / 100) * 1.05:
		doc.hs_over_boq = 1
	if v.get("_note"):
		doc.terms = v._note
	frappe.flags.hs_create_msg = _("{0} sent for approval").replace("{0}", "{0}") + (_(" — over the remaining BOQ quantity, goes to the Managing Director") if doc.get("hs_over_boq") else "")
	doc.flags.hs_ready = True


def pre_stock_entry_site(doc, v, rows):
	"""Site transfer: from the main store (or another site) to the project's site store, charged to the project."""
	if not v.get("project") or not v.get("item_code") or not flt(v.get("qty")):
		frappe.throw(_("Choose the project, the material and the quantity"))
	p = frappe.get_doc("Project", v.project)
	doc.company = p.company
	doc.stock_entry_type = doc.purpose = "Material Transfer"
	doc.project = p.name
	src = v.get("from_warehouse") or P.main_store(p.company)
	if frappe.get_cached_value("Warehouse", src, "company") != p.company:  # v1.8.2
		frappe.throw(_("{0} belongs to another company — {1} can only take stock from its own stores.").format(src, p.company))
	dst = P.site_warehouse(p)
	if src == dst:
		frappe.throw(_("The material is already in {0}.").format(dst))
	doc.append("items", {"item_code": v.item_code, "qty": flt(v.qty), "s_warehouse": src, "t_warehouse": dst, "project": p.name,
		"cost_center": frappe.get_cached_value("Company", p.company, "cost_center")})
	doc.remarks = " · ".join(x for x in [_("Site transfer"), v.get("_vehicle")] if x)
	if v.get("posting_date"):
		doc.posting_date, doc.set_posting_time = v.posting_date, 1
	doc.flags.hs_ready = True


def boq_lines():
	"""Choices for "Project · BOQ line" on the material request to site: the open projects' BOQ lines."""
	out = []
	for pj in P.project_names(None, include_closed=False):
		b = P.boq(pj)
		for r in (b.items if b else []):
			out.append({"name": f"{pj}|{r.item_no}", "label": f"{pj[-3:]} · {r.item_no} — {r.description}"})
	return out
