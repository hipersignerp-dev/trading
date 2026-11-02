"""v1.8.0 (prototype p19): record panels for the Projects records — the project with its 26-step process stepper, money,
payment terms, bonds, red flags, documents and history; progress certificate, variation, subcontract order and claim, BOQ.
The buttons run hipersign_trading.api.projects actions through api.panel.action ("pj:<action>")."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, today

from hipersign_trading.api import projects as P
from hipersign_trading.api.panel import _base, act, d, kv, link, money, pill, section

PF = {"Project BOQ": "Hipersign BOQ Tender", "Progress Certificate": "Hipersign Interim Payment Certificate", "Variation Order": "Hipersign Variation Order",
	"Subcontract Order": "Hipersign Subcontract Order"}


def _print_url(dt, name, fmt):
	return f"/printview?doctype={frappe.utils.quote(dt)}&name={frappe.utils.quote(name)}&format={frappe.utils.quote(fmt)}"


def _page_ok(page):
	ok = getattr(frappe.local, "hs_page_ok", None)
	if ok is None:
		ok = frappe.local.hs_page_ok = {}
	if page not in ok:
		ok[page] = bool(frappe.db.exists("Page", page)) and frappe.get_cached_doc("Page", page).is_permitted()
	return ok[page]


def _step_buttons(p, F):
	"""The buttons under each step of the stepper: open the screen for it, raise the document it needs, complete it."""
	b = {}
	go = {2: ["hipersign-boq"], 10: ["hipersign-site"], 11: ["hipersign-site"], 12: ["hipersign-site"], 13: ["hipersign-subcontract"], 14: ["hipersign-timesheets"],
		15: ["hipersign-billing"], 16: ["hipersign-billing"], 17: ["hipersign-billing"], 18: ["hipersign-billing"], 19: ["hipersign-subcontract"], 20: ["hipersign-costing"],
		24: ["hipersign-billing"]}
	bq = P.boq(p.name)
	for i in range(26):
		row = []
		if i in go and _page_ok(go[i][0]):  # v1.8.0: only a screen the user may open (no Site & procurement for the QS)
			row.append(act(_("Open screen"), route=go[i]))
		if i == 3 and bq:
			row.append(act(_("Tender print"), url=_print_url("Project BOQ", bq.name, PF["Project BOQ"])))
		if i == 7 and F.step >= 5 and not F.adv_amt and flt(p.hs_advance_pct):
			row.append(act(_("Raise advance invoice"), action="pj:advance_invoice", confirm=_("Raise the advance invoice for {0}?").format(p.name)))
		if i == 24 and 21 <= F.step < 26 and F.ret_held > 0.5:
			row.append(act(_("Raise retention invoice"), action="pj:retention_invoice", confirm=_("Raise the retention release invoice for {0}?").format(p.name)))
		if i == F.step and F.step < 26:
			row.append(act(_("Complete step {0}").format(i + 1), "primary", action="pj:step", confirm=_("Complete step {0} — {1}?").format(i + 1, _(P.STEPS[i][0]))))
		if row:
			b[i] = row
	return b


def project(doc):
	if not flt(doc.get("hs_contract_value")) and not frappe.db.exists("Project BOQ", {"project": doc.name}):
		# a plain ERPNext project (no contract): the essentials only
		p = _base(doc, f"{doc.name} — {doc.project_name}", _("Project"))
		p["facts"] = kv(("Customer", doc.customer), ("Status", pill(doc.status)), ("Start", d(doc.expected_start_date)), ("End", d(doc.expected_end_date)),
			("% complete", {"bar": flt(doc.percent_complete)}))
		return p
	F = P.fig(doc.name)
	cur = F.currency
	p = _base(doc, f"{doc.name} — {doc.project_name}", " · ".join(x for x in [doc.customer, doc.get("hs_location")] if x))
	p["status"] = pill(_(F.status), P.STATUS_TONE[F.status])
	team = " · ".join(x for x in [f"{doc.hs_project_manager} (PM)" if doc.get("hs_project_manager") else "", f"{doc.hs_quantity_surveyor} (QS)" if doc.get("hs_quantity_surveyor") else "",
		f"{doc.hs_site_engineer} ({_('site')})" if doc.get("hs_site_engineer") else ""] if x)
	p["facts"] = kv(("Client", link("Customer", doc.customer) if doc.customer else ""), ("Consultant", doc.get("hs_consultant")), ("Location", doc.get("hs_location")),
		("Contract value", money(F.contract, cur)), ("Approved variations", money(F.vo, cur)), ("Revised contract", money(F.rev, cur)),
		("Programme", f"{d(doc.expected_start_date)} → {d(doc.expected_end_date)}"), ("Project team", team), ("Sales order", link("Sales Order", doc.sales_order) if doc.sales_order else ""))
	st = P.states(doc.name)
	cur_i = next((i for i, x in enumerate(st) if x.st in ("cur", "late")), 25)
	stepper = {"title": _("Process — 26 steps"), "kind": "stepper", "rows": [], "actions": [], "sel": min(cur_i, cint(F.step) if F.step < 26 else 25),
		"steps": [{"name": _(s[0]), "short": _(s[1]), "what": _(s[2]), "who": _(s[3]), "docs": _(s[4]), "approval": _(s[5]), "next": _(s[6])} for s in P.STEPS],
		"phases": [{"name": _(n), "a": a, "b": b} for n, a, b in P.PHASES],
		"states": [{"st": x.st, "pct": x.pct, "date": x.date, "tag": x.tag, "info": x.info, "by": x.by} for x in st], "buttons": _step_buttons(doc, F)}
	fl = P.flags(doc.name)
	sections = [stepper,
		section("Money", kv(("Work done", f"{F.pct:.0f}% · {frappe.format(F.done, {'fieldtype': 'Currency', 'options': cur})}"), ("Certified to date", money(F.certified, cur)),
			("Billed (incl. VAT)", money(F.billed_tot, cur)), ("Collected", money(F.collected, cur)),
			("Outstanding", pill(f"{frappe.format(F.out, {'fieldtype': 'Currency', 'options': cur})} · {frappe.format(F.overdue, {'fieldtype': 'Currency', 'options': cur})} {_('overdue')}", "red")
				if F.overdue else money(F.out, cur)),
			("Retention held by client", money(F.ret_held, cur)), ("Advance to recover", money(F.adv_left, cur)), ("Cost to date", money(F.cost, cur)),
			("Forecast at completion", money(F.fac, cur)), ("Forecast margin", pill(f"{F.margin:.1f}% · {_('budget')} {F.bud_margin:.1f}%", "red" if F.margin < F.bud_margin - 1 else "green")))),
		section("Payment terms", kv(("Terms", doc.get("hs_payment_terms")), ("Retention", f"{flt(doc.hs_retention_pct):g}%"), ("Advance", f"{flt(doc.hs_advance_pct):g}%"),
			("Defects liability", _("{0} months").format(cint(doc.hs_dlp_months))))),
	]
	bl = P.bonds(doc.name)
	if bl:
		sections.append(section("Bonds & guarantees", cols=["Bond", "Bank", "Amount", "Expiry", "Status"], kind="table", rows=[[link("Bank Guarantee", b.name, f"{_(b.hs_bond_type or 'Bond')} · {b.bank_guarantee_number or b.name}"),
			b.bank or "—", money(b.amount, cur), pill(d(b.end_date), "red") if (b.hs_bond_status or "Active") != "Returned" and b.end_date and date_diff(b.end_date, today()) <= 30 else d(b.end_date),
			pill(_(b.hs_bond_status or "Active"), "green" if (b.hs_bond_status or "Active") != "Returned" else "grey")] for b in bl]))
	sections.append(section("Red flags", cols=["Level", "Issue", "Step"], kind="table", rows=[[pill(_(f["lvl"]), "red" if f["lvl"] == "High" else "orange"), f["text"],
		f"{f['step'] + 1} · {_(P.STEPS[f['step']][1])}"] for f in fl]) if fl else section("Red flags", kv(("Status", pill(_("No red flags — on track"), "green")))))
	docs = []
	bq = P.boq(doc.name)
	if bq:
		docs.append(act(_("BOQ / tender"), url=_print_url("Project BOQ", bq.name, PF["Project BOQ"])))
	cs = P.certs(doc.name)
	if cs:
		docs.append(act(_("Progress certificate {0}").format(cs[-1].certificate_no), url=_print_url("Progress Certificate", cs[-1].name, PF["Progress Certificate"])))
	prog = [i for i in F.inv if i.kind == "Progress"]
	if prog:
		docs.append(act(_("Progress invoice"), url=_print_url("Sales Invoice", prog[-1].name, "Hipersign Progress Invoice")))
	ret = [i for i in F.inv if i.kind == "Retention"]
	if ret:
		docs.append(act(_("Retention invoice"), url=_print_url("Sales Invoice", ret[-1].name, "Hipersign Retention Invoice")))
	vo = frappe.get_all("Variation Order", filters={"project": doc.name}, pluck="name", order_by="raised_on asc", limit=1)
	if vo:
		docs.append(act(_("Variation {0}").format(vo[0]), url=_print_url("Variation Order", vo[0], PF["Variation Order"])))
	sco = frappe.get_all("Subcontract Order", filters={"project": doc.name}, pluck="name", order_by="order_date asc", limit=1)
	if sco:
		docs.append(act(_("Subcontract order"), url=_print_url("Subcontract Order", sco[0], PF["Subcontract Order"])))
	sections.append(section("Prints", kv(("Documents", _("{0} prints").format(len(docs)))), actions=docs))
	p["sections"] = sections
	hist = [[d(x.completed_on), _("Step {0} completed — {1} ({2})").format(x.step, _(x.step_name or ""), frappe.utils.get_fullname(x.completed_by))]
		for x in frappe.get_all("Project Step Log", filters={"project": doc.name}, fields=["step", "step_name", "completed_on", "completed_by"], order_by="completed_on asc")]
	p["history"] = (hist + p["history"])[-14:] if hist else p["history"]
	acts = []
	if F.step < 26:
		if F.step >= 10 and frappe.has_permission("Progress Certificate", "create"):
			acts.append(act(_("Progress certificate"), client="pj_new", args={"doctype": "Progress Certificate", "values": {"project": doc.name}}))
		if F.step >= 5 and frappe.has_permission("Variation Order", "create"):
			acts.append(act(_("Variation"), client="pj_new", args={"doctype": "Variation Order", "values": {"project": doc.name}}))
	if bq:
		acts.append(act(_("Print BOQ"), url=_print_url("Project BOQ", bq.name, PF["Project BOQ"])))
	if F.step < 26 and frappe.has_permission("Project", "write", doc):
		acts.append(act(_("Complete step {0}").format(F.step + 1), "primary", action="pj:step", confirm=_("Complete step {0} — {1}?").format(F.step + 1, _(P.STEPS[F.step][0]))))
	p["actions"] = acts
	return p


def progress_certificate(doc):
	cur = frappe.get_cached_value("Company", doc.company, "default_currency")
	pj = frappe.get_cached_value("Project", doc.project, "project_name")
	p = _base(doc, f"{doc.name} — {_('progress certificate')}", f"{doc.project} · {pj}")
	p["status"] = pill(_(doc.status), {"Certified": "green", "Invoiced": "green", "Draft": "grey"}.get(doc.status, "orange"))
	steps = ["Measured", "Submitted", "Certified", "Invoiced", "Paid"]
	paid = doc.sales_invoice and flt(frappe.db.get_value("Sales Invoice", doc.sales_invoice, "outstanding_amount")) <= 0.5
	p["progress"] = {"steps": [_(s) for s in steps], "current": {"Draft": 0, "Submitted to consultant": 1, "Certified": 2, "Invoiced": 3}.get(doc.status, 0) + (2 if paid else 0)}
	p["facts"] = kv(("Project", link("Project", doc.project, f"{doc.project} {pj}")), ("Consultant", doc.consultant), ("Measured on", d(doc.measured_on)), ("Certificate date", d(doc.certified_on or doc.period_to)),
		("Invoice", link("Sales Invoice", doc.sales_invoice) if doc.sales_invoice else "—"))
	p["sections"] = [section("Certificate", kv(("Work done to date", money(doc.work_to_date, cur)), ("of which variations", money(doc.variations_to_date, cur)),
		("Less previous certificates", money(doc.previous_certified, cur)), ("Work done this period", money(doc.this_period, cur)),
		(_("Less advance recovery ({0}%)").format(f"{flt(doc.advance_pct):g}"), money(doc.advance_recovery, cur)), (_("Less retention ({0}%)").format(f"{flt(doc.retention_pct):g}"), money(doc.retention, cur)),
		("Net", money(doc.net_amount, cur)), (_("VAT {0}%").format(f"{flt(doc.vat_rate):g}"), money(doc.vat_amount, cur)), ("Amount due", money(doc.total_due, cur)))),
		section("Measurement", cols=["Item", "Description", "Amount", "Previous %", "Cumulative %", "This period"], kind="table",
			rows=[[r.item_no, r.description, money(r.amount, cur), f"{flt(r.previous_pct):g}%", f"{flt(r.cumulative_pct):g}%", money(r.this_period_amount, cur)] for r in doc.items])]
	a = [act(_("Print certificate"), print_format=PF["Progress Certificate"])]
	if doc.status == "Draft":
		a.append(act(_("Send to consultant"), "primary", action="pj:ipc_submit"))
	elif doc.status == "Submitted to consultant":
		a.append(act(_("Record certification"), "primary", action="pj:ipc_certify"))
	elif doc.status == "Certified" and not doc.sales_invoice:
		a.append(act(_("Create invoice"), "primary", action="pj:ipc_invoice", confirm=_("Create and submit the progress invoice for {0}?").format(doc.name)))
	p["actions"] = a
	return p


def variation_order(doc):
	cur = frappe.get_cached_value("Company", doc.company, "default_currency")
	pr = frappe.get_doc("Project", doc.project)
	p = _base(doc, f"{doc.name} — {_('variation')}", f"{doc.project} · {pr.customer or ''}")
	p["status"] = pill(_(doc.status), {"Approved": "green", "Draft": "grey", "Rejected": "red"}.get(doc.status, "orange"))
	p["progress"] = {"steps": [_("Draft"), _("Sent to client"), _("Approved"), _("Billed")], "current": {"Draft": 0, "Pending client": 1, "Approved": 3, "Rejected": 1}.get(doc.status, 0)}
	rev = P.revised(pr)
	p["facts"] = kv(("Project", link("Project", doc.project, f"{doc.project} {pr.project_name}")), ("Description", doc.title), ("Amount", money(doc.amount, cur)),
		("Reason", _(doc.reason or "")), ("Instruction", doc.instruction_ref), ("Raised", f"{d(doc.raised_on)} · {doc.raised_by or ''}"),
		("Waiting", _("{0} days with the client").format(date_diff(today(), doc.sent_on or doc.raised_on)) if doc.status == "Pending client" else ""),
		("Contract after this variation", money(rev + (0 if doc.status == "Approved" else flt(doc.amount)), cur)))
	a = [act(_("Print variation order"), print_format=PF["Variation Order"])]
	if doc.status == "Draft":
		a.append(act(_("Send to client"), "primary", action="pj:vo_submit"))
	elif doc.status == "Pending client":
		a += [act(_("Rejected"), action="pj:vo_reject", confirm=_("Record that the client rejected {0}?").format(doc.name)),
			act(_("Client approved"), "primary", action="pj:vo_approve", confirm=_("Record the client's approval of {0}?").format(doc.name))]
	p["actions"] = a
	return p


def subcontract_order(doc):
	cur = frappe.get_cached_value("Company", doc.company, "default_currency")
	p = _base(doc, f"{doc.name} — {_('subcontract order')}", doc.package)
	p["status"] = pill(_(doc.status), {"Active": "blue", "Completed": "green"}.get(doc.status, "orange"))
	cl = frappe.get_all("Subcontract Claim", filters={"subcontract_order": doc.name}, fields=["name", "claim_date", "claimed_to_date", "certified_to_date", "status"], order_by="claim_no asc")
	p["facts"] = kv(("Subcontractor", link("Supplier", doc.supplier)), ("Project", link("Project", doc.project)), ("Order value", money(doc.order_value, cur)),
		("Retention", f"{flt(doc.retention_pct):g}%"), ("Terms", doc.terms), ("Programme", pill(_("Behind programme"), "red") if doc.behind_programme else pill(_("On programme"), "green")))
	sec = [section("Claims", cols=["Claim", "Date", "Claimed", "Certified", "Status"], kind="table", rows=[[link("Subcontract Claim", c.name), d(c.claim_date), money(c.claimed_to_date, cur),
		money(c.certified_to_date, cur) if flt(c.certified_to_date) else "—", pill(_(c.status))] for c in cl])]
	if doc.behind_programme and doc.programme_note:
		sec.insert(0, section("Programme", kv(("Note", doc.programme_note))))
	p["sections"] = sec
	a = [act(_("Print subcontract order"), print_format=PF["Subcontract Order"])]
	if doc.status in ("Pending signature", "Draft"):
		a.append(act(_("Signed by both parties"), "primary", action="pj:sco_sign"))
	p["actions"] = a
	return p


def subcontract_claim(doc):
	cur = frappe.get_cached_value("Company", doc.company, "default_currency")
	p = _base(doc, f"{doc.name} — {_('subcontractor claim')}", f"{doc.supplier} · {doc.subcontract_order}")
	p["status"] = pill(_(doc.status), {"Paid": "green", "Certified": "blue"}.get(doc.status, "orange"))
	p["progress"] = {"steps": [_("Claimed"), _("Certified"), _("Billed"), _("Paid")], "current": {"Submitted": 0, "Certified": 2 if doc.purchase_invoice else 1, "Paid": 4}.get(doc.status, 0)}
	p["facts"] = kv(("Subcontract order", link("Subcontract Order", doc.subcontract_order)), ("Project", link("Project", doc.project)), ("Claim no.", doc.claim_no), ("Date", d(doc.claim_date)),
		("Supplier bill", link("Purchase Invoice", doc.purchase_invoice) if doc.purchase_invoice else "—"))
	p["sections"] = [section("Payment certificate", kv(("Claimed to date", money(doc.claimed_to_date, cur)), ("Certified to date", money(doc.certified_to_date, cur)),
		("Previously certified", money(doc.previous_certified, cur)), ("Certified this claim", money(doc.this_certified, cur)),
		(_("Less retention ({0}%)").format(f"{flt(doc.retention_pct):g}"), money(doc.retention, cur)), ("Less back-charges", money(doc.back_charges, cur)), ("Net", money(doc.net_amount, cur)),
		("VAT", money(doc.vat_amount, cur)), ("Total payable", money(doc.total, cur))))]
	a = []
	if doc.status == "Submitted":
		a.append(act(_("Certify"), "primary", action="pj:claim_certify"))
	elif doc.status == "Certified":
		if not doc.purchase_invoice:
			a.append(act(_("Book supplier bill"), action="pj:claim_bill"))
		a.append(act(_("Pay"), "primary", action="pj:claim_pay", confirm=_("Pay {0}?").format(doc.name)))
	p["actions"] = a
	return p


def project_boq(doc):
	cur = frappe.get_cached_value("Company", doc.company, "default_currency")
	p = _base(doc, f"{doc.name} — {doc.title}", f"{doc.client_name or ''} · Rev {cint(doc.revision)}")
	p["status"] = pill(_(doc.status), "green" if doc.status == "Awarded" else "red" if (doc.status or "").startswith("Lost") else "orange")
	p["facts"] = kv(("Project", link("Project", doc.project) if doc.project else ""), ("Received", d(doc.received_on)), ("Due", d(doc.due_date)), ("Tender value", money(doc.tender_value, cur)),
		("Direct cost", money(doc.direct_cost, cur)), ("Overheads", money(doc.overheads, cur)), ("Margin", f"{flt(doc.margin_pct):.1f}%"))
	p["sections"] = [section("Bill of quantities", cols=["Item", "Description", "Unit", "Qty", "Rate", "Amount", "Done"], kind="table",
		rows=[[r.item_no, r.description, r.unit, flt(r.qty), money(r.rate, cur), money(r.amount, cur), {"bar": flt(r.measured_pct)}] for r in doc.items])]
	p["actions"] = [act(_("Print BOQ"), print_format=PF["Project BOQ"])]
	return p


BUILDERS = {"Project": project, "Progress Certificate": progress_certificate, "Variation Order": variation_order, "Subcontract Order": subcontract_order,
	"Subcontract Claim": subcontract_claim, "Project BOQ": project_boq}


def action(doc, action, args):
	"""pj:<action> buttons on these panels → api.projects.act (the same rules as the pages)."""
	if not action.startswith("pj:"):
		return None
	return P.act(action[3:], doc.name, args)
