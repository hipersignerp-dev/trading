"""v1.8.0 (prototype p19): the Projects engine — contracting and fit-out from enquiry to profit report.

One place for
  · the 26 process steps in 6 phases (who, documents, approval, trigger) and "Complete step N" with its approvals and log,
  · the money rules: advance invoice, progress certificate → progress invoice (gross this period less advance recovery and
    retention, plus VAT), retention release, variations raising the revised contract, subcontract claim → supplier bill
    less retention and back-charges, project material request → PO → receipt on site,
  · the figures every Projects page shows (contract, work done, certified, billed, collected, retention, advance, cost,
    forecast, margin), the step states and the red flags.

Built on ERPNext: Project, Task, Timesheet, Material Request, Purchase Order / Receipt / Invoice, Sales Order / Invoice,
Payment Entry, Stock Entry, Bank Guarantee (bonds), GL Entry (cost by project). The app adds Project BOQ, Progress Certificate,
Variation Order, Subcontract Order / Claim, Back Charge, Daily Site Report and the Project Step Log.

Posting (VAT through the company's template, api.create._tax_template):
  progress invoice  Dr Receivable (net + VAT) · Dr Advances from Customers (recovery) · Dr Retention Receivable (retention)
                    Cr Contract Revenue (gross this period) · Cr VAT (5% of net)
  advance invoice   Dr Receivable · Cr Advances from Customers · Cr VAT
  retention invoice Dr Receivable · Cr Retention Receivable · Cr VAT
  subcontract bill  Dr Subcontract Costs (certified this claim) · Dr VAT input · Cr Payable (net + VAT) · Cr Retention Payable
                    · Cr Subcontract Costs (agreed back-charges)
The deductions are tax-table rows ("Actual"), so the invoice stays one ERPNext document with the right totals and no
negative item rates.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, now_datetime, today

# ---------------------------------------------------------------- the process
# (name, short, what happens, who, documents, approval, next trigger)
STEPS = [
	("Enquiry / tender received", "Enquiry", "Tender invitation, drawings, specifications and the client’s BOQ are logged as a new project in Tender status, with the submission deadline.", "Estimator", "Tender register entry, enquiry file", "Bid / no-bid decision by the Managing Director", "Bid approved → site visit booked"),
	("Site visit & survey", "Site visit", "Estimator and site engineer survey the site: access, working hours, existing services, measurements and photos.", "Estimator · Site Engineer", "Site survey report, photos", "None", "Survey saved → BOQ pricing starts"),
	("BOQ & estimate (cost build-up, margin)", "BOQ & estimate", "Each BOQ line is priced from material, labour, plant and subcontract rates; site overheads and margin are added to reach the selling rate.", "Quantity Surveyor", "Priced BOQ, cost build-up", "Margin below 12% needs the Managing Director", "Estimate approved → tender submission"),
	("Tender submission / quotation", "Tender", "The priced BOQ, method statement, programme and company documents go to the client as the tender or quotation.", "Estimator", "Tender letter, priced BOQ, quotation", "Managing Director signs the tender letter", "Submitted → clarifications and negotiation"),
	("Negotiation & award (LOA)", "Award", "Clarifications, value engineering and the final negotiated price; the client issues a Letter of Award.", "Managing Director · Quantity Surveyor", "Revised BOQ, Letter of Award", "Managing Director accepts the LOA", "LOA received → contract"),
	("Contract signed (sales order, payment terms, retention %, advance %)", "Contract", "The contract becomes a sales order with the contract value, payment terms, retention %, advance % and defects liability period.", "Managing Director", "Signed contract, sales order", "Managing Director + Finance Manager", "Contract signed → bonds requested from the bank"),
	("Advance payment guarantee & performance bond", "Bonds", "The bank issues the advance payment guarantee (equal to the advance) and the performance bond (usually 10%) against the facility.", "Finance Manager", "APG, performance bond", "Finance Manager", "Bonds delivered → advance invoice"),
	("Advance invoice & receipt", "Advance", "The advance is invoiced with VAT and received; it is recovered pro rata from each progress invoice.", "Accountant", "Advance tax invoice, receipt voucher", "Finance Manager", "Advance received → mobilisation"),
	("Mobilisation (site team, insurance, permits)", "Mobilise", "Site team assigned, contractor’s all-risk insurance, authority and building-management permits, site office and stores set up.", "Project Manager", "CAR policy, permits, mobilisation checklist", "Project Manager", "Permits approved → budget and schedule"),
	("Project budget & schedule (tasks, milestones, cost heads)", "Budget", "Budget per cost head from the estimate; tasks and milestones from the programme; the baseline is frozen.", "Project Manager · Quantity Surveyor", "Project budget, baseline programme", "Managing Director approves the budget", "Budget approved → material requests"),
	("Material requests from BOQ", "Material req.", "Site raises material requests against BOQ lines; quantities are checked against the BOQ allowance.", "Site Engineer", "Material request", "Project Manager (over the BOQ quantity → Managing Director)", "Request approved → procurement"),
	("Procurement (RFQ, comparison, PO)", "Procure", "Purchasing asks three suppliers, compares them and places the PO charged to the project and cost head.", "Buyer", "RFQ, comparison, purchase order", "Purchase Manager / Finance Manager by amount", "PO approved → delivery to site"),
	("Deliveries to site & site stock", "Deliveries", "Goods are delivered straight to site or transferred from the main store; site stock is tracked per project.", "Storekeeper · Site Engineer", "Delivery note, site receipt, transfer", "None", "Received → available for installation"),
	("Subcontract orders", "Subcontract", "MEP and joinery packages are let as subcontract orders with their own BOQ, retention and payment terms.", "Project Manager · Quantity Surveyor", "Subcontract order", "Managing Director", "Order signed → subcontractor mobilises"),
	("Execution & daily site reports, timesheets", "Execution", "Daily site report with manpower, work done, issues and photos; timesheets post labour cost to tasks.", "Site Engineer · Foreman", "Daily site report, timesheets", "Project Manager", "Month end → progress measurement"),
	("Monthly progress measurement", "Measure", "The QS measures the work done on every BOQ line — as a percentage or a quantity — at month end.", "Quantity Surveyor", "Measurement sheet", "Project Manager", "Measurement submitted to the consultant"),
	("Consultant certification (progress certificate)", "Certify", "The consultant checks the measurement and issues the interim payment certificate (IPC) with the certified amount.", "Consultant · Quantity Surveyor", "Interim payment certificate", "Consultant signs", "IPC received → progress invoice"),
	("Progress invoice (less advance recovery and retention)", "Invoice", "Invoice for the work certified this period, less advance recovery and retention, plus VAT.", "Accountant", "Progress tax invoice", "Finance Manager", "Invoice sent → collection"),
	("Variations (request, approval, billing)", "Variations", "Client changes are priced as variation orders; approved variations are added to the contract and billed in the next certificate.", "Quantity Surveyor · Project Manager", "Variation request, variation order", "Client / consultant; Managing Director for omissions", "VO approved → contract value updated"),
	("Subcontractor claims & payments", "Sub claims", "Subcontractors claim monthly; the QS certifies, retention and back-charges are deducted and payment is released.", "Quantity Surveyor · Accountant", "Subcontractor claim, payment certificate", "Project Manager + Finance Manager", "Certified → payment run"),
	("Cost control (budget vs actual, forecast)", "Cost control", "Budget vs committed vs actual per cost head, with the forecast to complete and the forecast margin, reviewed monthly.", "Project Manager · Finance Manager", "Cost report", "Monthly review by the Managing Director", "Overrun → corrective action or a variation"),
	("Practical completion & snag list", "Completion", "Joint inspection; snags are listed, assigned and closed; the consultant issues the completion certificate.", "Project Manager", "Snag list, completion certificate", "Consultant", "Completion certificate → handover"),
	("Handover & as-built documents", "Handover", "Keys, O&M manuals, warranties, as-built drawings and training are handed over.", "Project Manager", "Handover certificate, as-built set", "Client", "Handover → final account"),
	("Final account", "Final acct", "Re-measurement and all variations agreed; final contract value and the balance due.", "Quantity Surveyor", "Final account statement", "Client + Managing Director", "Agreed → final invoice; defects period starts"),
	("Retention release (after defects liability period)", "Retention", "Half the retention at completion (if agreed) and the balance at the end of the defects liability period; a retention invoice is raised.", "Accountant · Quantity Surveyor", "Retention invoice, release certificate", "Consultant releases", "Retention received → closure"),
	("Project closure & profit report", "Closure", "Accounts closed, bonds returned, final cost and profit compared with the estimate; lessons learned.", "Managing Director", "Profit report, close-out report", "Managing Director", "Project closed"),
]
PHASES = [("Win the job", 0, 5), ("Contract & security", 5, 8), ("Mobilise & plan", 8, 10), ("Buy & build", 10, 15), ("Measure, bill & control", 15, 21), ("Complete & close", 21, 26)]
HEADS = ["Materials", "Labour", "Subcontract", "Plant & equipment", "Site overheads"]
SHARE = {"Materials": "mat_share", "Labour": "lab_share", "Subcontract": "sub_share", "Plant & equipment": "plant_share", "Site overheads": "ovh_share"}
PLANT_PCT = 1.2  # plant & equipment budget, % of the contract value (the prototype's allowance on top of the BOQ lines)
STATUS_TONE = {"Tender": "violet", "Mobilising": "orange", "Execution": "blue", "Handover": "green", "Closed": "grey"}

MD, FM, PM, QS, SE, BUY = "Managing Director", "Accounts Manager", "Project Manager", "Quantity Surveyor", "Site Engineer", "Purchase Manager"
# who may complete each step (System Manager always may); the approval column of STEPS in roles
STEP_ROLES = {0: [MD], 1: [MD, PM, QS, SE], 2: [QS, MD], 3: [MD], 4: [MD], 5: [MD], 6: [FM, MD], 7: [FM, "Accounts User", MD], 8: [PM, MD],
	9: [MD], 10: [PM, MD], 11: [BUY, FM, PM, MD], 12: [PM, SE, "Stock Manager", "Stock User", MD], 13: [MD], 14: [PM, MD], 15: [PM, QS, MD],
	16: [QS, PM, MD], 17: [FM, "Accounts User", MD], 18: [QS, PM, MD], 19: [PM, FM, MD], 20: [MD], 21: [PM, MD], 22: [PM, MD], 23: [MD],
	24: [FM, QS, MD], 25: [MD]}

ITEMS = {
	"works": ("PRJ-WORKS", "Contract works — per BOQ", 1, 0),
	"advance": ("PRJ-ADVANCE", "Advance payment", 1, 0),
	"retention": ("PRJ-RETENTION", "Retention release", 1, 0),
	"variation": ("PRJ-VARIATION", "Variation works", 1, 0),
	"subcontract": ("PRJ-SUBCONTRACT", "Subcontract works — per certified claim", 0, 1),
}


def status_of(step):
	step = cint(step)
	return "Closed" if step >= 26 else "Handover" if step >= 21 else "Execution" if step >= 10 else "Mobilising" if step >= 5 else "Tender"


def _has(*roles):
	have = set(frappe.get_roles())
	return "System Manager" in have or bool(have & set(roles))


def _need(roles, what):
	if not _has(*roles):
		frappe.throw(_("{0} needs the {1}.").format(what, " / ".join(_(r) for r in roles)), frappe.PermissionError)


class _elevated:
	"""v1.8.4: the follow-on documents of a project action (the contract sales order a variation changes, the subcontractor's
	bill and its payment) are made by the system once the user's role has been checked — a PM or MD who may approve the step
	need not also hold every ERPNext permission on the sales order / purchase invoice / payment. The real user is recorded."""

	def __enter__(self):
		self.user = frappe.session.user
		if self.user != "Administrator":
			frappe.set_user("Administrator")
		return self.user

	def __exit__(self, *a):
		if frappe.session.user != self.user:
			frappe.set_user(self.user)
		return False


# ---------------------------------------------------------------- accounts, items, warehouses
def _account(company, name, root_type, parent, account_type=""):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	full = f"{name} - {abbr}"
	if frappe.db.exists("Account", full):
		return full
	got = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
	if got:
		return got
	a = frappe.get_doc({"doctype": "Account", "account_name": name, "company": company, "parent_account": parent, "root_type": root_type,
		"report_type": "Balance Sheet" if root_type in ("Asset", "Liability", "Equity") else "Profit and Loss", "account_type": account_type})
	a.flags.ignore_permissions = True
	a.insert()
	return a.name


def _group(company, root_type, prefer=()):
	for name in prefer:
		g = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 1})
		if g:
			return g
	return frappe.db.get_value("Account", {"company": company, "root_type": root_type, "is_group": 1}, "name", order_by="lft desc")


def accounts(company):
	"""The project accounts of a company (created the first time they are needed)."""
	cache = _local("hs_pj_acc")
	if company in cache:
		return cache[company]
	co = frappe.get_cached_doc("Company", company)
	recv_parent = frappe.db.get_value("Account", co.default_receivable_account, "parent_account") if co.default_receivable_account else None
	pay_parent = frappe.db.get_value("Account", co.default_payable_account, "parent_account") if co.default_payable_account else None
	inc = _group(company, "Income", ("Direct Income", "Income"))
	exp = _group(company, "Expense", ("Direct Expenses", "Expenses"))
	a = frappe._dict(
		revenue=_account(company, "Contract Revenue", "Income", inc, "Income Account"),
		advances=_account(company, "Advances from Customers", "Liability", pay_parent or _group(company, "Liability", ("Current Liabilities",))),
		retention=_account(company, "Retention Receivable", "Asset", recv_parent or _group(company, "Asset", ("Current Assets",))),
		retention_payable=_account(company, "Retention Payable", "Liability", pay_parent or _group(company, "Liability", ("Current Liabilities",))),
		heads={
			"Materials": _account(company, "Project Materials", "Expense", exp, "Expense Account"),
			"Labour": _account(company, "Project Labour", "Expense", exp, "Expense Account"),
			"Subcontract": _account(company, "Subcontract Costs", "Expense", exp, "Expense Account"),
			"Plant & equipment": _account(company, "Plant & Equipment Hire", "Expense", exp, "Expense Account"),
			"Site overheads": _account(company, "Site Overheads", "Expense", exp, "Expense Account"),
		},
	)
	cache[company] = a
	return a


def item(kind):
	code, name, sales, purchase = ITEMS[kind]
	if not frappe.db.exists("Item", code):
		group = "Services" if frappe.db.exists("Item Group", "Services") else frappe.db.get_value("Item Group", {"is_group": 0}) or "All Item Groups"
		frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "stock_uom": "Nos" if frappe.db.exists("UOM", "Nos") else "Unit",
			"is_stock_item": 0, "is_sales_item": sales, "is_purchase_item": purchase, "include_item_in_manufacturing": 0}).insert(ignore_permissions=True)
	return code


def site_warehouse(project):
	"""The project's site store (created at mobilisation or on the first delivery to site)."""
	p = frappe.get_doc("Project", project) if isinstance(project, str) else project
	if p.get("hs_site_warehouse") and frappe.db.exists("Warehouse", p.hs_site_warehouse):
		return p.hs_site_warehouse
	abbr = frappe.get_cached_value("Company", p.company, "abbr")
	name = f"Site {p.name} - {abbr}"
	if not frappe.db.exists("Warehouse", name):
		parent = frappe.db.get_value("Warehouse", {"company": p.company, "is_group": 1}, "name", order_by="lft asc")
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": f"Site {p.name}", "company": p.company, "parent_warehouse": parent}).insert(ignore_permissions=True)
	frappe.db.set_value("Project", p.name, "hs_site_warehouse", name, update_modified=False)
	return name


def main_store(company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	for n in (f"Main Store - {abbr}", f"Stores - {abbr}"):
		if frappe.db.exists("Warehouse", n):
			return n
	return frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "warehouse_name": ["not like", "Site %"]})


def _vat_template(company, buying=False):
	from hipersign_trading.api.create import _tax_template

	tpl = _tax_template(company, buying)
	if not tpl:
		return None, 0, None
	dt = "Purchase Taxes and Charges" if buying else "Sales Taxes and Charges"
	row = frappe.get_all(dt, filters={"parent": tpl, "parenttype": dt + " Template"}, fields=["account_head", "rate"], order_by="idx asc", limit=1)
	return tpl, flt(row[0].rate) if row else 0, row[0].account_head if row else None


def vat_rate(company, buying=False):
	return _vat_template(company, buying)[1]


# ---------------------------------------------------------------- per-request cache
def _local(key):
	v = getattr(frappe.local, key, None)
	if v is None:
		v = {}
		setattr(frappe.local, key, v)
	return v


def _c():
	return _local("hs_pj")


def clear_cache():
	frappe.local.hs_pj = None


def project(name):
	c = _c().setdefault("p", {})
	if name not in c:
		c[name] = frappe.get_doc("Project", name)
	return c[name]


def boq(name):
	"""The project's BOQ: the awarded (contract) one, else the latest."""
	c = _c().setdefault("boq", {})
	if name not in c:
		rows = frappe.get_all("Project BOQ", filters={"project": name}, fields=["name", "status"], order_by="modified desc")
		pick = next((r.name for r in rows if r.status == "Awarded"), None) or (rows[0].name if rows else None)
		c[name] = frappe.get_doc("Project BOQ", pick) if pick else None
	return c[name]


def lines(name):
	b = boq(name)
	return list(b.items) if b else []


def approved_vos(name):
	return flt(sum(flt(v.amount) for v in frappe.get_all("Variation Order", filters={"project": name, "status": "Approved"}, fields=["amount"])))


def contract(p):
	return flt(p.get("hs_contract_value"))


def revised(p):
	return flt(contract(p) + approved_vos(p.name), 2)


def work(name, now=True):
	"""BOQ work done: Σ amount × measured % (now) or certified % (last certificate)."""
	f = "measured_pct" if now else "certified_pct"
	return flt(sum(flt(r.amount) * flt(r.get(f)) / 100 for r in lines(name)), 2)


def update_revised_contract(name):
	"""A variation was approved, rejected or changed: the project's revised contract value follows."""
	if not name or not frappe.db.exists("Project", name):
		return
	vo = approved_vos(name)
	cv = flt(frappe.db.get_value("Project", name, "hs_contract_value"))
	frappe.db.set_value("Project", name, {"hs_variations": vo, "hs_revised_contract": flt(cv + vo, 2)}, update_modified=False)
	clear_cache()


# ---------------------------------------------------------------- invoices and money per project
def invoices(name):
	c = _c().setdefault("inv", {})
	if name in c:
		return c[name]
	rows = frappe.get_all("Sales Invoice", filters={"project": name, "docstatus": 1, "hs_project_bill": ["is", "set"], "is_return": 0},
		fields=["name", "company", "hs_project_bill", "hs_progress_certificate", "posting_date", "due_date", "base_net_total", "base_grand_total",
			"outstanding_amount", "conversion_rate"], order_by="posting_date asc, name asc")
	out = []
	if rows:
		acc = accounts(rows[0].company)
		taxes = frappe.get_all("Sales Taxes and Charges", filters={"parenttype": "Sales Invoice", "parent": ["in", [r.name for r in rows]]},
			fields=["parent", "account_head", "base_tax_amount"])
		for r in rows:
			tx = [t for t in taxes if t.parent == r.name]
			adv = -sum(flt(t.base_tax_amount) for t in tx if t.account_head == acc.advances)
			ret = -sum(flt(t.base_tax_amount) for t in tx if t.account_head == acc.retention)
			vat = sum(flt(t.base_tax_amount) for t in tx if t.account_head not in (acc.advances, acc.retention))
			total = flt(r.base_grand_total)
			paid = flt(total - flt(r.outstanding_amount) * flt(r.conversion_rate or 1), 2)
			out.append(frappe._dict(name=r.name, kind=r.hs_project_bill, cert=r.hs_progress_certificate, date=r.posting_date, due=r.due_date,
				gross=flt(r.base_net_total), adv=flt(adv, 2), ret=flt(ret, 2), vat=flt(vat, 2), net=flt(flt(r.base_net_total) - adv - ret, 2), total=total,
				paid=paid, out=flt(total - paid, 2), over=flt(total - paid) > 0.5 and r.due_date and getdate(r.due_date) < getdate(today())))
	c[name] = out
	return out


def certs(name):
	c = _c().setdefault("ipc", {})
	if name not in c:
		c[name] = frappe.get_all("Progress Certificate", filters={"project": name}, fields=["name", "certificate_no", "status", "period_to", "measured_on",
			"certified_on", "work_to_date", "previous_certified", "this_period", "advance_recovery", "retention", "total_due", "sales_invoice", "consultant"],
			order_by="certificate_no asc, creation asc")
	return c[name]


def fig(name):
	"""Every money figure of a project — the prototype's pjFig."""
	c = _c().setdefault("fig", {})
	if name in c:
		return c[name]
	p = project(name)
	inv = invoices(name)
	cs = [x for x in certs(name) if x.status in ("Certified", "Invoiced")]
	certified = flt(cs[-1].work_to_date) if cs else 0
	prog = [i for i in inv if i.kind == "Progress"]
	billed_gross = sum(i.gross for i in prog)
	billed_tot = sum(i.total for i in inv)
	collected = sum(i.paid for i in inv)
	ret_released = sum(i.gross for i in inv if i.kind == "Retention" and i.paid > 0.5)
	ret_held = flt(sum(i.ret for i in prog) - ret_released, 2)
	adv_amt = sum(i.gross for i in inv if i.kind == "Advance")
	adv_rec = sum(i.adv for i in inv)
	cv = contract(p)
	vo = approved_vos(name)
	rev = flt(cv + vo, 2)
	step = cint(p.get("hs_step"))
	w = work(name, True)
	done = rev if step >= 26 else flt(w + (vo * w / cv if cv else 0), 2)
	pct = 100 if step >= 26 else (min(100, done / rev * 100) if rev else 0)
	cost = cost_of(name)
	margin = (rev - cost.fac) / rev * 100 if rev else 0
	bud_margin = (cv - cost.budget) / cv * 100 if cv else 0
	overdue = sum(i.out for i in inv if i.over)
	vos_pend = sum(flt(v.amount) for v in frappe.get_all("Variation Order", filters={"project": name, "status": ["in", ["Pending client", "Draft"]]}, fields=["amount"]))
	r = frappe._dict(inv=inv, certified=certified, billed_gross=billed_gross, billed_tot=billed_tot, collected=collected, ret_held=ret_held, ret_released=ret_released,
		adv_amt=adv_amt, adv_rec=adv_rec, adv_left=flt(adv_amt - adv_rec, 2), contract=cv, vo=vo, rev=rev, pct=pct, done=done, cost=cost.actual, budget=cost.budget,
		fac=cost.fac, committed=cost.committed, margin=margin, bud_margin=bud_margin, overdue=overdue, out=flt(billed_tot - collected, 2), vos_pend=vos_pend, step=step,
		status=status_of(step), currency=frappe.get_cached_value("Company", p.company, "default_currency"))
	c[name] = r
	return r


def _gl_by_head(name, company):
	acc = accounts(company)
	inv = {v: k for k, v in acc.heads.items()}
	rows = frappe.db.sql("""select account, sum(debit - credit) from `tabGL Entry` where is_cancelled = 0 and project = %s and account in %s group by account""",
		(name, tuple(inv)))
	out = {h: 0.0 for h in HEADS}
	for a, v in rows:
		out[inv[a]] += flt(v)
	return out


def timesheet_cost(name, submitted_only=True):
	return flt(frappe.db.sql("""select sum(td.costing_amount) from `tabTimesheet Detail` td join `tabTimesheet` t on t.name = td.parent
		where td.project = %s and t.docstatus = %s""", (name, 1 if submitted_only else 0))[0][0])


def cost_of(name):
	"""Budget, earned, actual, committed, forecast to complete and forecast at completion per cost head (pjCost).
	Actual = GL entries of the project on the cost-head accounts + approved timesheets (labour)."""
	c = _c().setdefault("cost", {})
	if name in c:
		return c[name]
	p = project(name)
	step = cint(p.get("hs_step"))
	H = {h: frappe._dict(budget=0.0, earned=0.0, actual=0.0, committed=0.0, ftc=0.0, fac=0.0) for h in HEADS}
	for r in lines(name):
		pct = 1 if step >= 26 else flt(r.measured_pct) / 100
		for h, f in SHARE.items():
			b = flt(r.amount) * flt(r.get(f)) / 100
			H[h].budget += b
			H[h].earned += b * pct
	cv = contract(p)
	frac = 1 if step >= 26 else (work(name, True) / cv if cv else 0)
	plant = cv * PLANT_PCT / 100
	H["Plant & equipment"].budget += plant
	H["Plant & equipment"].earned += plant * frac
	gl = _gl_by_head(name, p.company)
	gl["Labour"] += timesheet_cost(name)
	po_open = sum(flt(x.base_net_total) * (100 - flt(x.per_received)) / 100 for x in frappe.get_all("Purchase Order",
		filters={"hs_project": name, "docstatus": ["<", 2], "status": ["not in", ["Closed", "Completed", "Cancelled"]]}, fields=["base_net_total", "per_received"]))
	sco = sum(flt(x.order_value) for x in frappe.get_all("Subcontract Order", filters={"project": name, "status": ["in", ["Active", "Completed"]]}, fields=["order_value"]))
	for h in HEADS:
		x = H[h]
		x.actual = flt(gl[h], 2)
		f = x.actual / x.earned if x.earned > 0.5 and x.actual > 0 else 1
		x.ftc = 0 if step >= 26 else flt(max(0, x.budget - x.earned) * f, 2)
		x.fac = flt(x.actual + x.ftc, 2)
		x.committed = flt(max(sco, x.actual) if h == "Subcontract" else x.actual + po_open if h == "Materials" else x.actual, 2)
		x.budget = flt(x.budget, 2)
		x.earned = flt(x.earned, 2)
	r = frappe._dict(H=H, budget=flt(sum(H[h].budget for h in HEADS), 2), actual=flt(sum(H[h].actual for h in HEADS), 2),
		fac=flt(sum(H[h].fac for h in HEADS), 2), committed=flt(sum(H[h].committed for h in HEADS), 2))
	r.ftc = flt(r.fac - r.actual, 2)
	c[name] = r
	return r


# ---------------------------------------------------------------- certificates and claims (called from the doctypes)
def ipc_compute(doc):
	"""Progress certificate: the measurement (BOQ lines) → work to date → this period → advance recovery, retention, VAT."""
	frozen = not doc.is_new() and doc.status in ("Certified", "Invoiced") and frappe.db.get_value("Progress Certificate", doc.name, "status") in ("Certified", "Invoiced")
	if frozen:
		return
	p = frappe.get_doc("Project", doc.project)
	doc.company = doc.company or p.company
	doc.consultant = doc.consultant or p.get("hs_consultant")
	if doc.advance_pct in (None, ""):
		doc.advance_pct = flt(p.get("hs_advance_pct"))
	if doc.retention_pct in (None, ""):
		doc.retention_pct = flt(p.get("hs_retention_pct"))
	if not doc.certificate_no:
		doc.certificate_no = cint(frappe.db.sql("select max(certificate_no) from `tabProgress Certificate` where project = %s and name != %s", (doc.project, doc.name or ""))[0][0]) + 1
	cv = flt(p.get("hs_contract_value"))
	if not doc.flags.hs_keep:
		b = frappe.get_all("Project BOQ", filters={"project": doc.project}, fields=["name", "status"], order_by="modified desc")
		pick = next((r.name for r in b if r.status == "Awarded"), None) or (b[0].name if b else None)
		doc.set("items", [])
		if pick:
			for r in frappe.get_doc("Project BOQ", pick).items:
				doc.append("items", {"item_no": r.item_no, "description": r.description, "amount": r.amount, "previous_pct": r.certified_pct,
					"cumulative_pct": r.measured_pct, "this_period_amount": flt(flt(r.amount) * (flt(r.measured_pct) - flt(r.certified_pct)) / 100, 2),
					"to_date_amount": flt(flt(r.amount) * flt(r.measured_pct) / 100, 2)})
		bw = flt(sum(flt(r.to_date_amount) for r in doc.items), 2)
		vo = flt(sum(flt(v.amount) for v in frappe.get_all("Variation Order", filters={"project": doc.project, "status": "Approved"}, fields=["amount"])))
		doc.boq_work_to_date = bw
		doc.variations_to_date = flt(vo * bw / cv, 2) if cv else 0
		doc.work_to_date = flt(bw + doc.variations_to_date, 2)
	prev = frappe.get_all("Progress Certificate", filters={"project": doc.project, "name": ["!=", doc.name or ""], "certificate_no": ["<", doc.certificate_no],
		"status": ["in", ["Certified", "Invoiced"]]}, fields=["work_to_date"], order_by="certificate_no desc", limit=1)
	doc.previous_certified = flt(prev[0].work_to_date) if prev else 0
	doc.this_period = flt(flt(doc.work_to_date) - flt(doc.previous_certified), 2)
	# the advance still to recover: advance invoiced less what the earlier certificates recovered
	adv_inv = frappe.get_all("Sales Invoice", filters={"project": doc.project, "docstatus": 1, "hs_project_bill": "Advance"}, fields=["base_net_total"])
	adv_left = None
	if adv_inv:
		rec = frappe.get_all("Progress Certificate", filters={"project": doc.project, "name": ["!=", doc.name or ""], "certificate_no": ["<", doc.certificate_no],
			"status": ["in", ["Certified", "Invoiced"]]}, fields=["advance_recovery"])
		adv_left = sum(flt(i.base_net_total) for i in adv_inv) - sum(flt(r.advance_recovery) for r in rec)
	adv = flt(doc.this_period * flt(doc.advance_pct) / 100, 2)
	doc.advance_recovery = flt(max(0, min(adv, adv_left)), 2) if adv_left is not None else adv
	doc.retention = flt(doc.this_period * flt(doc.retention_pct) / 100, 2)
	doc.net_amount = flt(doc.this_period - doc.advance_recovery - doc.retention, 2)
	if doc.vat_rate in (None, ""):
		doc.vat_rate = vat_rate(doc.company)
	doc.vat_amount = flt(doc.net_amount * flt(doc.vat_rate) / 100, 2)
	doc.total_due = flt(doc.net_amount + doc.vat_amount, 2)
	doc.measured_on = doc.measured_on or today()


def claim_compute(doc):
	"""Subcontract claim: certified to date → this claim → less retention and agreed back-charges → VAT."""
	sco = frappe.get_doc("Subcontract Order", doc.subcontract_order)
	doc.project, doc.supplier, doc.company = sco.project, sco.supplier, sco.company
	if doc.retention_pct in (None, ""):
		doc.retention_pct = flt(sco.retention_pct)
	if not doc.claim_no:
		doc.claim_no = cint(frappe.db.sql("select max(claim_no) from `tabSubcontract Claim` where subcontract_order = %s and name != %s", (sco.name, doc.name or ""))[0][0]) + 1
	doc.claim_date = doc.claim_date or today()
	if doc.status in ("Paid",) and not doc.is_new():
		return
	prev = frappe.get_all("Subcontract Claim", filters={"subcontract_order": sco.name, "name": ["!=", doc.name or ""], "claim_no": ["<", doc.claim_no],
		"status": ["in", ["Certified", "Paid"]]}, fields=["certified_to_date"], order_by="claim_no desc", limit=1)
	doc.previous_certified = flt(prev[0].certified_to_date) if prev else 0
	if flt(doc.certified_to_date):
		doc.this_certified = flt(flt(doc.certified_to_date) - doc.previous_certified, 2)
		doc.retention = flt(doc.this_certified * flt(doc.retention_pct) / 100, 2)
	else:
		doc.this_certified = doc.retention = 0
	bcs = frappe.get_all("Back Charge", filters={"subcontract_order": sco.name, "status": ["in", ["Agreed", "Deducted"]]}, fields=["amount", "status", "deducted_in"])
	doc.back_charges = flt(sum(flt(b.amount) for b in bcs if b.deducted_in == doc.name or (doc.status == "Submitted" and b.status == "Agreed" and not b.deducted_in)), 2) \
		if flt(doc.this_certified) and not doc.flags.hs_no_bc else 0
	doc.net_amount = flt(doc.this_certified - doc.retention - doc.back_charges, 2)
	doc.vat_amount = flt(doc.net_amount * vat_rate(doc.company, True) / 100, 2)
	doc.total = flt(doc.net_amount + doc.vat_amount, 2)


# ---------------------------------------------------------------- step states (pjStates) and red flags (pjFlags)
def _lerp(a, b, f):
	return add_days(a, round(date_diff(b, a) * f))


def plan_date(p, i):
	enq = p.get("hs_enquiry_date") or p.creation
	award = p.get("hs_award_date") or add_days(enq, 40)
	start = p.get("expected_start_date") or add_days(award, 30)
	finish = p.get("expected_end_date") or add_days(start, 180)
	if i <= 4:
		return _lerp(enq, award, (i + 1) / 5)
	if i <= 9:
		return _lerp(award, start, (i - 4) / 5)
	if i <= 20:
		return _lerp(start, finish, (i - 9) / 11)
	return _lerp(finish, add_days(finish, 30 * cint(p.get("hs_dlp_months") or 12) + 30), (i - 20) / 5)


def bonds(name):
	if not frappe.db.exists("DocType", "Bank Guarantee"):
		return []
	return frappe.get_all("Bank Guarantee", filters={"project": name, "docstatus": ["<", 2]}, fields=["name", "hs_bond_type", "bank_guarantee_number", "bank",
		"amount", "end_date", "hs_bond_status", "docstatus"], order_by="start_date asc, name asc")


def _money(v, cur="AED"):
	return f"{cur} {flt(v):,.2f}"


def _short(v, cur="AED"):
	v = flt(v)
	return f"{cur} {v / 1e6:.2f}M" if abs(v) >= 1e6 else f"{cur} {v / 1e3:.0f}K" if abs(v) >= 1e4 else f"{cur} {v:,.0f}"


def _fd(d):
	return getdate(d).strftime("%d %b %Y") if d else "—"


def _fds(d):
	return getdate(d).strftime("%d %b") if d else "—"


def states(name):
	p = project(name)
	F = fig(name)
	cur = F.currency
	step = F.step
	logs = {r.step: r for r in frappe.get_all("Project Step Log", filters={"project": name}, fields=["step", "completed_on", "completed_by"], order_by="completed_on asc")}
	out = []
	for i in range(26):
		st = "done" if i < step else "cur" if i == step else "wait"
		lg = logs.get(i + 1)
		out.append(frappe._dict(st=st, pct=100 if i < step else 40 if i == step else 0, date=(lg.completed_on if lg else plan_date(p, i)) if i < step else None,
			plan=plan_date(p, i), tag=_("Done") if i < step else _("In progress") if i == step else _("Planned {0}").format(_fds(plan_date(p, i))), info=[],
			by=frappe.utils.get_fullname(lg.completed_by) if lg else None))

	def s(i, **kw):
		out[i].update(kw)

	out[0].info = [[_("Received"), _fd(p.get("hs_enquiry_date"))], [_("Client"), p.get("customer") or "—"]]
	out[3].info = [[_("Tender value"), _money(F.contract, cur)]]
	if step > 4:
		out[4].info = [[_("LOA"), _fd(p.get("hs_award_date"))]]
	out[5].info = [[_("Contract"), _money(F.contract, cur)], [_("Retention"), f"{flt(p.get('hs_retention_pct')):g}%"], [_("Advance"), f"{flt(p.get('hs_advance_pct')):g}%"]]
	bl = bonds(name)
	if bl:
		out[6].info = [[_("APG") if "Advance" in (b.hs_bond_type or "") else _(b.hs_bond_type or "Bond"), f"{_short(b.amount, cur)} · {_('exp.')} {_fds(b.end_date)}"] for b in bl]
	out[7].info = [[_("Advance"), _money(F.adv_amt, cur)], [_("Recovered"), _money(F.adv_rec, cur)]]
	if step == 3:
		b = boq(name)
		due = p.get("hs_tender_due")
		s(3, pct=80, tag=_("Due {0}").format(_fds(due)) if due else _("Pricing"), info=[[_("Tender value"), _money(F.contract, cur)],
			[_("Margin"), f"{flt(b.margin_pct if b else 0):.1f}%"], [_("Due"), _fd(due)]])
	if 10 <= step < 21:
		mrs = frappe.get_all("Material Request", filters={"hs_project": name, "docstatus": ["<", 2]}, fields=["name", "docstatus", "status", "per_ordered"])
		pend = [m for m in mrs if m.docstatus == 0]
		s(10, st="cur", pct=(len([m for m in mrs if flt(m.per_ordered) > 0]) / len(mrs) * 100) if mrs else 0, tag=_("{0} pending").format(len(pend)), date=None,
			info=[[_("Requests"), len(mrs)], [_("Pending approval"), len(pend)]])
		pos = frappe.get_all("Purchase Order", filters={"hs_project": name, "docstatus": ["<", 2]}, fields=["name", "docstatus", "base_net_total", "per_received", "schedule_date", "status"])
		po_v = sum(flt(x.base_net_total) for x in pos)
		rc_v = sum(flt(x.base_net_total) * flt(x.per_received) / 100 for x in pos)
		mat_b = cost_of(name).H["Materials"].budget
		s(11, st="cur", pct=min(100, po_v / mat_b * 100) if mat_b else 0, tag=_("{0} POs").format(len(pos)), date=None,
			info=[[_("Ordered"), _money(po_v, cur)], [_("Awaiting approval"), len([x for x in pos if x.docstatus == 0])]])
		late = [x for x in pos if x.docstatus == 1 and x.schedule_date and getdate(x.schedule_date) < getdate(today()) and flt(x.per_received) < 100]
		dls = frappe.db.count("Purchase Receipt", {"project": name, "docstatus": 1}) + frappe.db.count("Stock Entry", {"project": name, "docstatus": 1, "purpose": "Material Transfer"})
		s(12, st="late" if late else "cur", pct=rc_v / po_v * 100 if po_v else 0, tag=_("{0} late").format(len(late)) if late else _("{0} deliveries").format(dls), date=None,
			info=[[_("Received"), _money(rc_v, cur)]] + [[x.name, _("ETA {0} passed").format(_fds(x.schedule_date)), "neg"] for x in late])
		scs = frappe.get_all("Subcontract Order", filters={"project": name, "status": ["!=", "Cancelled"]}, fields=["name", "supplier", "status", "behind_programme", "order_value", "order_date"])
		pend_sc = any(x.status in ("Pending signature", "Draft") for x in scs)
		s(13, st="cur" if pend_sc else "done", pct=50 if pend_sc else 100, date=scs[-1].order_date if scs else None, tag=_("{0} orders").format(len(scs)),
			info=[[x.name, x.supplier] for x in scs])
		hrs = flt(frappe.db.sql("""select sum(td.hours) from `tabTimesheet Detail` td join tabTimesheet t on t.name = td.parent where td.project = %s and t.docstatus < 2
			and date(td.from_time) >= %s""", (name, add_days(today(), -7)))[0][0])
		crew = frappe.db.sql("""select count(distinct t.employee) from `tabTimesheet Detail` td join tabTimesheet t on t.name = td.parent where td.project = %s and t.docstatus < 2
			and date(td.from_time) >= %s""", (name, add_days(today(), -30)))[0][0]
		behind = [x for x in scs if x.behind_programme]
		s(14, st="late" if behind else "cur", pct=F.pct, tag=_("{0}% complete").format(round(F.pct)),
			info=[[_("Hours last 7 days"), f"{hrs:,.0f}"], [_("Crew"), _("{0} + subcontractors").format(crew)]] + [[x.name, _("Behind programme"), "neg"] for x in behind])
		cs = certs(name)
		last = cs[-1] if cs else None
		s(15, st="cur", pct=100 if last and last.status not in ("Certified", "Invoiced") else 30, date=last.measured_on if last else None,
			tag=_("IPC-{0:02d} measured").format(cint(last.certificate_no)) if last else _("Month end"),
			info=[[_("Measured"), _fd(last.measured_on)], [_("Cumulative"), _money(last.work_to_date, cur)]] if last else [])
		cert = [x for x in cs if x.status in ("Certified", "Invoiced")]
		s(16, st="cur", pct=F.certified / F.rev * 100 if F.rev else 0, tag=_("IPC-{0:02d} certified").format(cint(cert[-1].certificate_no)) if cert else _("None yet"),
			date=cert[-1].certified_on if cert else None, info=[[_("Certified to date"), _money(F.certified, cur)]])
		s(17, st="late" if F.overdue > 0 else "cur", pct=F.billed_gross / F.rev * 100 if F.rev else 0,
			tag=_("{0} overdue").format(_short(F.overdue, cur)) if F.overdue > 0 else _("Billed {0}").format(_short(F.billed_gross, cur)),
			info=[[_("Billed (gross)"), _money(F.billed_gross, cur)], [_("Collected"), _money(F.collected, cur)], [_("Overdue"), _money(F.overdue, cur), "neg" if F.overdue else ""]])
		vos = frappe.get_all("Variation Order", filters={"project": name}, fields=["name", "status", "amount", "sent_on", "raised_on"], order_by="raised_on asc")
		old = [v for v in vos if v.status == "Pending client" and date_diff(today(), v.sent_on or v.raised_on) > 30]
		appr = [v for v in vos if v.status == "Approved"]
		s(18, st="late" if old else "cur", pct=len(appr) / len(vos) * 100 if vos else 100, tag=_("{0} of {1} approved").format(len(appr), len(vos)),
			info=[[v.name, f"{_(v.status)} · {_short(v.amount, cur)}"] for v in vos])
		cl = frappe.get_all("Subcontract Claim", filters={"project": name}, fields=["status", "this_certified", "retention"])
		sc_v = sum(flt(x.order_value) for x in scs)
		sc_p = sum(flt(x.this_certified) for x in cl if x.status == "Paid")
		s(19, st="cur", pct=sc_p / sc_v * 100 if sc_v else 0, tag=_("{0} open claims").format(len([x for x in cl if x.status != "Paid"])),
			info=[[_("Paid to subcontractors"), _money(sc_p, cur)], [_("Claims to certify"), len([x for x in cl if x.status == "Submitted"])]])
		over = F.margin < F.bud_margin - 1
		s(20, st="late" if over else "cur", pct=F.cost / F.fac * 100 if F.fac else 0, tag=_("Margin {0:.1f}%").format(F.margin),
			info=[[_("Budget margin"), f"{F.bud_margin:.1f}%"], [_("Forecast margin"), f"{F.margin:.1f}%", "neg" if over else "pos"], [_("Cost to date"), _money(F.cost, cur)]])
	if step == 22:
		sn = snags(name)
		op = [x for x in sn if x.status not in ("Completed", "Cancelled", "Closed")]
		s(21, info=[[_("Snags"), _("{0} listed · {1} open").format(len(sn), len(op))]])
		s(22, st="late" if op else "cur", pct=70, tag=_("{0} snags open").format(len(op)), info=[[_("Open snags"), len(op)]])
		s(23, st="cur", pct=40, tag=_("Re-measurement"), info=[[_("Variations agreed"), _money(F.vo, cur)]])
		s(24, st="cur", pct=0, tag=_("50% invoiced") if any(i.kind == "Retention" for i in F.inv) else _("Due"),
			info=[[i.name, f"{_money(i.total, cur)} · {_('due')} {_fds(i.due)}"] for i in F.inv if i.kind == "Retention"])
	if step >= 26:
		out[24].info = [[i.name, f"{_money(i.total, cur)} · {_('paid')}"] for i in F.inv if i.kind == "Retention"]
		out[25].info = [[_("Final value"), _money(F.rev, cur)], [_("Final margin"), f"{F.margin:.1f}%"]]
	for f in flags(name):
		if out[f["step"]].st != "done":
			out[f["step"]].st = "late"
	return out


def snags(name):
	return frappe.get_all("Task", filters={"project": name, "type": "Snag"}, fields=["name", "subject", "status", "hs_task_owner"]) \
		if frappe.db.exists("Task Type", "Snag") else []


def flags(name):
	c = _c().setdefault("flags", {})
	if name in c:
		return c[name]
	p = project(name)
	F = fig(name)
	cur = F.currency
	fl = []

	def add(lvl, t, step, open_=None):
		fl.append({"lvl": lvl, "text": t, "step": step, "open": open_})

	for v in frappe.get_all("Variation Order", filters={"project": name, "status": "Pending client"}, fields=["name", "amount", "sent_on", "raised_on"]):
		d = date_diff(today(), v.sent_on or v.raised_on)
		if d > 30:
			add("High", _("{0} pending client approval for {1} days ({2})").format(v.name, d, _short(v.amount, cur)), 18, ["Variation Order", v.name])
	for i in F.inv:
		if i.over:
			add("High", _("{0} overdue {1} days — {2} outstanding").format(i.name, date_diff(today(), i.due), _money(i.out, cur)), 17, ["Sales Invoice", i.name])
	for b in bonds(name):
		if b.docstatus == 1 and (b.hs_bond_status or "Active") != "Returned" and b.end_date and date_diff(b.end_date, today()) <= 30:
			add("High", _("{0} {1} expires {2} — ask the bank to extend").format(_(b.hs_bond_type or "Bond"), b.bank_guarantee_number or b.name, _fd(b.end_date)), 6, ["Bank Guarantee", b.name])
	for x in frappe.get_all("Subcontract Order", filters={"project": name, "behind_programme": 1, "status": ["in", ["Active", "Pending signature"]]}, fields=["name", "supplier", "package"]):
		add("Medium", _("{0} behind programme on {1}").format(x.supplier, (x.package or "").split(" — ")[0].lower()), 14, ["Subcontract Order", x.name])
	for x in frappe.get_all("Purchase Order", filters={"hs_project": name, "docstatus": 1, "per_received": ["<", 100], "schedule_date": ["<", today()],
			"status": ["not in", ["Closed", "Completed"]]}, fields=["name", "schedule_date"]):
		it = frappe.db.get_value("Purchase Order Item", {"parent": x.name}, "item_name") or ""
		add("Medium", _("{0} {1} — ETA {2} passed").format(x.name, it.lower(), _fds(x.schedule_date)), 12, ["Purchase Order", x.name])
	if 10 <= F.step < 26 and F.margin < F.bud_margin - 1:
		add("Medium", _("Forecast margin {0:.1f}% vs budget {1:.1f}% — labour and materials over budget").format(F.margin, F.bud_margin), 20, None)
	due = p.get("hs_tender_due")
	if F.step == 3 and due and date_diff(due, today()) <= 7:
		add("Medium", _("Tender due {0} — {1} days left").format(_fd(due), date_diff(due, today())), 3, None)
	if F.step == 22:
		o = len([x for x in snags(name) if x.status not in ("Completed", "Cancelled", "Closed")])
		if o:
			add("Medium", _("{0} snags still open — handover certificate on hold").format(o), 22, ["Project", name])
	c[name] = fl
	return fl


# ---------------------------------------------------------------- which projects a page shows
def project_names(cos=None, include_closed=True):
	"""Projects of the scope's companies that carry a contract (or tender) value; when the scope has none, every project the user
	may read (so the Projects pages of a trading company in a group still show the contracting company's projects)."""
	f = {"hs_contract_value": [">", 0]}
	if not include_closed:
		f["hs_step"] = ["<", 26]
	fields = ["name", "hs_step", "hs_contract_value"]
	rows = frappe.get_list("Project", filters=dict(f, company=["in", cos]) if cos else f, fields=fields, limit_page_length=0)
	if not rows and cos:
		rows = frappe.get_list("Project", filters=f, fields=fields, limit_page_length=0)
	# live work first (execution, mobilising, handover), then tenders, then closed — largest first
	rank = {"Execution": 0, "Mobilising": 1, "Handover": 2, "Tender": 3, "Closed": 4}
	rows.sort(key=lambda r: (rank[status_of(r.hs_step)], -flt(r.hs_contract_value), r.name))
	return [r.name for r in rows]


# ---------------------------------------------------------------- documents the actions make
def _si(p, kind, item_kind, rate, description, income_account, deductions=(), posting_date=None, due_days=30, cert=None):
	"""A project sales invoice: one line, the deduction rows (advance recovery, retention) and VAT on what is left."""
	tpl, rate_vat, vat_acc = _vat_template(p.company)
	cc = frappe.get_cached_value("Company", p.company, "cost_center")
	d = posting_date or today()
	si = frappe.get_doc({"doctype": "Sales Invoice", "customer": p.customer, "company": p.company, "project": p.name, "posting_date": d, "set_posting_time": 1,
		"due_date": add_days(d, due_days), "hs_project_bill": kind, "hs_progress_certificate": cert, "currency": frappe.get_cached_value("Company", p.company, "default_currency"),
		"items": [{"item_code": item(item_kind), "qty": 1, "rate": flt(rate, 2), "description": description, "income_account": income_account, "project": p.name, "cost_center": cc}]})
	taxes = []
	for desc, acc, amt in deductions:
		if flt(amt):
			taxes.append({"charge_type": "Actual", "account_head": acc, "description": desc, "tax_amount": -flt(amt, 2), "cost_center": cc})
	if vat_acc and rate_vat:
		taxes.append({"charge_type": "On Previous Row Total", "row_id": len(taxes), "rate": rate_vat, "account_head": vat_acc, "description": _("VAT {0}%").format(f"{rate_vat:g}"), "cost_center": cc}
			if taxes else {"charge_type": "On Net Total", "rate": rate_vat, "account_head": vat_acc, "description": _("VAT {0}%").format(f"{rate_vat:g}"), "cost_center": cc})
	si.set("taxes", taxes)
	si.flags.hs_project_bill = True
	si.set_missing_values()
	si.set("taxes", taxes)
	si.taxes_and_charges = None
	for i in si.items:
		i.income_account, i.project = income_account, p.name
	si.insert()
	si.submit()
	clear_cache()
	return si


def make_advance_invoice(name, posting_date=None):
	p = frappe.get_doc("Project", name)
	if frappe.db.exists("Sales Invoice", {"project": name, "docstatus": 1, "hs_project_bill": "Advance"}):
		frappe.throw(_("{0} already has its advance invoice.").format(name))
	amt = flt(p.hs_contract_value) * flt(p.hs_advance_pct) / 100
	if not amt:
		frappe.throw(_("{0} has no advance (advance % is 0).").format(name))
	acc = accounts(p.company)
	return _si(p, "Advance", "advance", amt, _("Advance payment {0}% of the contract value — {1}").format(f"{flt(p.hs_advance_pct):g}", p.project_name), acc.advances,
		posting_date=posting_date, due_days=10)


def make_progress_invoice(ipc_name, posting_date=None):
	c = frappe.get_doc("Progress Certificate", ipc_name)
	if c.status != "Certified":
		frappe.throw(_("{0} must be certified by the consultant before it is invoiced.").format(c.name))
	if c.sales_invoice and frappe.db.get_value("Sales Invoice", c.sales_invoice, "docstatus") == 1:
		frappe.throw(_("{0} is already invoiced ({1}).").format(c.name, c.sales_invoice))
	p = frappe.get_doc("Project", c.project)
	acc = accounts(p.company)
	si = _si(p, "Progress", "works", c.this_period, _("Work done this period — progress certificate {0} (no. {1}), period to {2}").format(c.name, c.certificate_no, _fd(c.period_to)),
		acc.revenue, [(_("Less advance recovery ({0}%)").format(f"{flt(c.advance_pct):g}"), acc.advances, c.advance_recovery),
			(_("Less retention ({0}%)").format(f"{flt(c.retention_pct):g}"), acc.retention, c.retention)], posting_date=posting_date, cert=c.name)
	frappe.db.set_value("Progress Certificate", c.name, {"sales_invoice": si.name, "status": "Invoiced"}, update_modified=False)
	return si


def make_retention_invoice(name, amount=None, posting_date=None, label=None):
	p = frappe.get_doc("Project", name)
	F = fig(name)
	amt = flt(amount) or flt(F.ret_held / 2 if not any(i.kind == "Retention" for i in F.inv) else F.ret_held - sum(i.gross for i in F.inv if i.kind == "Retention" and i.paid <= 0.5), 2)
	if amt <= 0:
		frappe.throw(_("No retention left to release on {0}.").format(name))
	acc = accounts(p.company)
	return _si(p, "Retention", "retention", amt, label or _("Retention released — {0}").format(p.project_name), acc.retention, posting_date=posting_date)


def receive(si_name, posting_date=None, amount=None, reference=None):
	"""A receipt against a project invoice (the bank / cash account of the mode of payment)."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry("Sales Invoice", si_name, party_amount=flt(amount) or None)
	d = posting_date or today()
	pe.posting_date, pe.reference_no, pe.reference_date = d, reference or f"TT/{si_name}", d
	pe.insert()
	pe.submit()
	clear_cache()
	return pe


def pay(pi_name, posting_date=None, reference=None):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry("Purchase Invoice", pi_name)
	d = posting_date or today()
	pe.posting_date, pe.reference_no, pe.reference_date = d, reference or f"PAY/{pi_name}", d
	pe.flags.ignore_workflow = True
	pe.insert()
	pe.submit()
	return pe


def make_claim_bill(claim_name, posting_date=None):
	"""A certified subcontract claim → the subcontractor's bill (Purchase Invoice) less retention and back-charges, plus VAT."""
	cl = frappe.get_doc("Subcontract Claim", claim_name)
	if cl.status != "Certified":
		frappe.throw(_("{0} must be certified first.").format(cl.name))
	if cl.purchase_invoice and frappe.db.get_value("Purchase Invoice", cl.purchase_invoice, "docstatus") == 1:
		return frappe.get_doc("Purchase Invoice", cl.purchase_invoice)
	acc = accounts(cl.company)
	tpl, rate_vat, vat_acc = _vat_template(cl.company, True)
	cc = frappe.get_cached_value("Company", cl.company, "cost_center")
	d = posting_date or today()
	sco = frappe.get_doc("Subcontract Order", cl.subcontract_order)
	pi = frappe.get_doc({"doctype": "Purchase Invoice", "supplier": cl.supplier, "company": cl.company, "project": cl.project, "posting_date": d, "set_posting_time": 1,
		"bill_no": cl.name, "bill_date": cl.claim_date, "due_date": add_days(d, 30), "hs_subcontract_claim": cl.name,
		"currency": frappe.get_cached_value("Company", cl.company, "default_currency"),
		"items": [{"item_code": item("subcontract"), "qty": 1, "rate": flt(cl.this_certified, 2), "expense_account": acc.heads["Subcontract"], "project": cl.project, "cost_center": cc,
			"description": _("{0} — claim {1}, certified this claim ({2})").format(sco.package, cl.claim_no, cl.subcontract_order)}]})
	taxes = []
	for desc, acct, amt in ((_("Less retention ({0}%)").format(f"{flt(cl.retention_pct):g}"), acc.retention_payable, cl.retention),
			(_("Less back-charges"), acc.heads["Subcontract"], cl.back_charges)):
		if flt(amt):
			taxes.append({"category": "Total", "add_deduct_tax": "Deduct", "charge_type": "Actual", "account_head": acct, "description": desc, "tax_amount": flt(amt, 2), "cost_center": cc})
	if vat_acc and rate_vat:
		taxes.append(dict({"category": "Total", "add_deduct_tax": "Add", "rate": rate_vat, "account_head": vat_acc, "description": _("VAT {0}%").format(f"{rate_vat:g}"), "cost_center": cc},
			**({"charge_type": "On Previous Row Total", "row_id": len(taxes)} if taxes else {"charge_type": "On Net Total"})))
	pi.set_missing_values()
	pi.set("taxes", taxes)
	pi.taxes_and_charges = None
	for i in pi.items:
		i.expense_account, i.project = acc.heads["Subcontract"], cl.project
	pi.flags.ignore_workflow = True
	pi.insert()
	pi.submit()
	frappe.db.set_value("Subcontract Claim", cl.name, "purchase_invoice", pi.name, update_modified=False)
	return pi


def make_sales_order(name):
	"""Contract signed → the contract as a sales order (contract value, project, payment terms)."""
	p = frappe.get_doc("Project", name)
	if p.sales_order and frappe.db.exists("Sales Order", p.sales_order):
		return frappe.get_doc("Sales Order", p.sales_order)
	if not p.customer:
		frappe.throw(_("Set the client (customer) on {0} first.").format(name))
	tpl = _vat_template(p.company)[0]
	so = frappe.get_doc({"doctype": "Sales Order", "customer": p.customer, "company": p.company, "project": p.name, "transaction_date": today(),
		"delivery_date": p.expected_end_date or add_days(today(), 180), "po_no": p.name, "taxes_and_charges": tpl,
		"items": [{"item_code": item("works"), "qty": 1, "rate": flt(p.hs_contract_value), "description": _("{0} — contract works as per the contract BOQ").format(p.project_name),
			"delivery_date": p.expected_end_date or add_days(today(), 180), "project": p.name}]})
	so.set_missing_values()
	so.taxes_and_charges = tpl
	so.set("taxes", [])
	if tpl:
		so.append_taxes_from_master()
	so.insert()
	wf = frappe.db.get_value("Workflow", {"document_type": "Sales Order", "is_active": 1})
	if not wf:
		# the document rules may want the signed contract / LPO attached first: then the order stays a draft
		from hipersign_trading.doc_rules import DocumentNeeded

		frappe.db.savepoint("hs_pj_so")
		try:
			so.submit()
		except DocumentNeeded:
			frappe.db.rollback(save_point="hs_pj_so")
			frappe.local.message_log = []
			so = frappe.get_doc("Sales Order", so.name)
	frappe.db.set_value("Project", name, "sales_order", so.name, update_modified=False)
	return so


def _vo_on_sales_order(vo, by=None):
	"""An approved variation adds a line to the contract sales order (positive variations; omissions stay on the project).
	v1.8.4: returns the reason when the order could not be updated (it used to fail silently)."""
	so_name = frappe.db.get_value("Project", vo.project, "sales_order")
	if not so_name or flt(vo.amount) <= 0:
		return
	so = frappe.get_doc("Sales Order", so_name)
	if so.docstatus != 1 or so.status in ("Closed", "Completed"):
		return
	from erpnext.controllers.accounts_controller import update_child_qty_rate

	rows = [{"docname": r.name, "item_code": r.item_code, "qty": r.qty, "rate": r.rate, "conversion_factor": r.conversion_factor, "delivery_date": r.delivery_date,
		"uom": r.uom} for r in so.items]
	wh = so.get("set_warehouse") or next((r.warehouse for r in so.items if r.get("warehouse")), None) or main_store(so.company)
	code = item("variation")
	if wh and not frappe.db.exists("Item Default", {"parent": code, "company": so.company}):
		it = frappe.get_doc("Item", code)  # ERPNext's "update items" asks the item for a warehouse, even for a service
		it.append("item_defaults", {"company": so.company, "default_warehouse": wh})
		it.save(ignore_permissions=True)
	rows.append({"item_code": item("variation"), "qty": 1, "rate": flt(vo.amount), "conversion_factor": 1, "delivery_date": so.delivery_date, "uom": None, "warehouse": wh})
	frappe.db.savepoint("hs_vo_so")
	try:
		update_child_qty_rate("Sales Order", frappe.as_json(rows), so.name)
		if by and by != "Administrator":
			frappe.get_doc("Sales Order", so.name).add_comment("Info", _("Variation {0} added to the contract by {1}").format(vo.name, frappe.utils.get_fullname(by)))
	except Exception as e:
		if frappe.flags.hs_debug:
			raise
		frappe.db.rollback(save_point="hs_vo_so")
		frappe.clear_last_message()
		frappe.log_error(title=f"Hipersign variation {vo.name} → {so.name}")
		return frappe.utils.strip_html(str(e)) or _("see the error log")


# ---------------------------------------------------------------- the actions (buttons on the pages and the project panel)
def _log(p, i, note=None, user=None, when=None):
	frappe.get_doc({"doctype": "Project Step Log", "project": p.name, "step": i + 1, "step_name": STEPS[i][0], "completed_by": user or frappe.session.user,
		"completed_on": when or now_datetime(), "note": note}).insert(ignore_permissions=True)


def complete_step(name, note=None):
	p = frappe.get_doc("Project", name)
	p.check_permission("write")
	i = cint(p.hs_step)
	if i >= 26:
		frappe.throw(_("{0} is closed — all 26 steps are done.").format(name))
	roles = list(STEP_ROLES.get(i, [MD]))
	if i == 2:
		b = boq(name)
		if b and flt(b.margin_pct) < 12:
			roles = [MD]
	_need(roles, _("Step {0} ({1})").format(i + 1, _(STEPS[i][1])))
	msg = ""
	if i == 3:
		for b in frappe.get_all("Project BOQ", filters={"project": name, "status": "Being priced"}, pluck="name"):
			frappe.db.set_value("Project BOQ", b, "status", "Submitted")
	if i == 4:
		for b in frappe.get_all("Project BOQ", filters={"project": name, "status": ["in", ["Being priced", "Submitted"]]}, pluck="name"):
			frappe.db.set_value("Project BOQ", b, "status", "Awarded")
		p.hs_award_date = p.hs_award_date or today()
	if i == 5:
		so = make_sales_order(name)
		p.sales_order = so.name
		msg = _("Contract sales order {0} {1}").format(so.name, _("submitted") if so.docstatus == 1 else _("created — submit it for approval"))
	if i == 7 and flt(p.hs_advance_pct) and not frappe.db.exists("Sales Invoice", {"project": name, "docstatus": 1, "hs_project_bill": "Advance"}):
		frappe.throw(_("Raise the advance invoice first (Progress & billing → Advance recovery, or the button on this step)."))
	if i == 8:
		site_warehouse(p)
	p.hs_step = i + 1
	if p.hs_step >= 26:
		p.status = "Completed"
		p.percent_complete = 100
	elif p.status != "Open":
		p.status = "Open"
	p.flags.ignore_mandatory = True
	p.save()
	_log(p, i, note)
	p.add_comment("Info", _("Step {0} completed — {1}").format(i + 1, _(STEPS[i][0])))
	clear_cache()
	nxt = _(STEPS[p.hs_step][0]) if p.hs_step < 26 else None
	return {"message": (_("{0} closed — profit report ready").format(name) if not nxt else _("Done: {0} → next: {1}").format(_(STEPS[i][1]), nxt)) + (f" · {msg}" if msg else ""),
		"step": p.hs_step}


def measure(project_name, item_no, pct):
	"""The QS enters the cumulative % of a BOQ line; an open certificate (draft or with the consultant) follows."""
	b = boq(project_name)
	if not b:
		frappe.throw(_("{0} has no BOQ.").format(project_name))
	b.check_permission("write")
	_need([QS, PM, MD], _("Measurement"))
	row = next((r for r in b.items if r.item_no == item_no), None)
	if not row:
		frappe.throw(_("BOQ line {0} not found.").format(item_no))
	v = min(100, max(flt(row.certified_pct), flt(pct)))
	# one line at a time (two quick edits must not collide on the whole BOQ's timestamp)
	frappe.db.set_value("Project BOQ Item", row.name, "measured_pct", v, update_modified=False)
	row.measured_pct = v
	b.db_set("work_done", flt(sum(flt(r.amount) * flt(r.measured_pct) / 100 for r in b.items), 2))
	clear_cache()
	for c in frappe.get_all("Progress Certificate", filters={"project": project_name, "status": ["in", ["Draft", "Submitted to consultant"]]}, pluck="name"):
		for attempt in range(3):  # a second edit a moment ago may be recalculating the same certificate
			try:
				frappe.get_doc("Progress Certificate", c).save()
				break
			except frappe.TimestampMismatchError:
				frappe.clear_last_message()
	return {"message": _("{0} → {1}% · this period {2}").format(item_no, f"{v:g}", _money(flt(row.amount) * (v - flt(row.certified_pct)) / 100))}


def _ipc_status(name, new, roles, what):
	c = frappe.get_doc("Progress Certificate", name)
	c.check_permission("write")
	_need(roles, what)
	return c


@frappe.whitelist(methods=["POST"])
def act(action, name, args=None):
	"""Every Projects button: one entry point (the view-only demo refuses it as a write)."""
	args = frappe._dict(frappe.parse_json(args) if isinstance(args, str) else (args or {}))
	fn = ACTIONS.get(action)
	if not fn:
		frappe.throw(_("Unknown action"))
	r = fn(name, args) or {}
	clear_cache()
	return r


def _a_step(name, a):
	return complete_step(name, a.get("note"))


def _a_measure(name, a):
	return measure(name, a.item_no, a.pct)


def _a_ipc_submit(name, a):
	c = _ipc_status(name, "Submitted to consultant", [QS, PM, MD], _("Sending a certificate to the consultant"))
	if c.status != "Draft":
		frappe.throw(_("{0} is {1}.").format(c.name, _(c.status)))
	c.status, c.measured_on = "Submitted to consultant", today()
	c.save()
	return {"message": _("{0} sent to {1} for certification").format(c.name, c.consultant or _("the consultant"))}


def _a_ipc_certify(name, a):
	c = _ipc_status(name, "Certified", [QS, PM, MD], _("Recording the consultant's certification"))
	if c.status != "Submitted to consultant":
		frappe.throw(_("{0} is {1} — send it to the consultant first.").format(c.name, _(c.status)))
	c.save()  # the latest measurement
	c.reload()
	c.status, c.certified_on = "Certified", a.get("date") or today()
	c.save()
	b = boq(c.project)
	if b:
		measured = {r.item_no: r.cumulative_pct for r in c.items}
		for r in b.items:
			if r.item_no in measured:
				r.certified_pct = measured[r.item_no]
				r.measured_pct = max(flt(r.measured_pct), flt(r.certified_pct))
		b.save()
	return {"message": _("{0} certified · {1} this period — create the progress invoice next").format(c.name, _money(c.this_period))}


def _a_ipc_invoice(name, a):
	frappe.has_permission("Sales Invoice", "create", throw=True)
	si = make_progress_invoice(name)
	return {"message": _("{0} created — {1} incl. VAT, less advance recovery and retention").format(si.name, _money(si.grand_total)), "open": ["Sales Invoice", si.name]}


def _a_advance_invoice(name, a):
	frappe.has_permission("Sales Invoice", "create", throw=True)
	si = make_advance_invoice(name)
	return {"message": _("Advance invoice {0} — {1} incl. VAT").format(si.name, _money(si.grand_total)), "open": ["Sales Invoice", si.name]}


def _a_retention_invoice(name, a):
	frappe.has_permission("Sales Invoice", "create", throw=True)
	si = make_retention_invoice(name, a.get("amount"))
	return {"message": _("Retention invoice {0} — {1} incl. VAT").format(si.name, _money(si.grand_total)), "open": ["Sales Invoice", si.name]}


def _a_receive(name, a):
	frappe.has_permission("Payment Entry", "create", throw=True)
	pe = receive(name)
	return {"message": _("Receipt {0} recorded — {1} paid").format(pe.name, name)}


def _a_vo(name, a, new):
	v = frappe.get_doc("Variation Order", name)
	v.check_permission("write")
	if new == "Pending client":
		if v.status != "Draft":
			frappe.throw(_("{0} is {1}.").format(name, _(v.status)))
		v.sent_on = today()
	else:
		if v.status != "Pending client":
			frappe.throw(_("{0} is {1} — send it to the client first.").format(name, _(v.status)))
		if new == "Approved" and flt(v.amount) < 0:
			_need([MD], _("Approving an omission"))
		else:
			_need([PM, MD], _("Recording the client's decision on a variation"))  # v1.8.4
		v.approved_on = today()
	v.status = new
	v.save()
	v.add_comment("Info", {"Pending client": _("Sent to the client for approval"), "Approved": _("Approved by the client — added to the contract"),
		"Rejected": _("Rejected by the client")}[new])
	if new == "Approved":
		with _elevated() as who:  # v1.8.4: the contract sales order is updated for every user who may approve, not only Administrator
			err = _vo_on_sales_order(v, who)
		if err:
			frappe.msgprint(_("{0} is approved, but the contract sales order could not be updated: {1}").format(name, err), indicator="orange", alert=True)
	clear_cache()
	return {"message": _("{0} approved · contract value now {1}").format(name, _money(revised(project(v.project)))) if new == "Approved"
		else _("{0}: {1}").format(name, _(new))}


def _a_claim_certify(name, a):
	cl = frappe.get_doc("Subcontract Claim", name)
	cl.check_permission("write")
	_need([QS, PM, MD], _("Certifying a subcontract claim"))
	if cl.status != "Submitted":
		frappe.throw(_("{0} is {1}.").format(name, _(cl.status)))
	cl.certified_to_date = flt(a.get("certified") or cl.certified_to_date or cl.claimed_to_date)
	cl.save()
	cl.reload()
	for b in frappe.get_all("Back Charge", filters={"subcontract_order": cl.subcontract_order, "status": "Agreed", "deducted_in": ["is", "not set"]}, pluck="name"):
		frappe.db.set_value("Back Charge", b, {"status": "Deducted", "deducted_in": cl.name})
	cl.status = "Certified"
	cl.save()
	return {"message": _("{0} certified {1} less retention {2} and back-charges {3}").format(name, _money(cl.this_certified), _money(cl.retention), _money(cl.back_charges))}


def _a_claim_bill(name, a):
	# v1.8.4: the PM, MD or accounts raise the subcontractor's bill from a certified claim (their company only)
	frappe.get_doc("Subcontract Claim", name).check_permission("read")
	_need([PM, MD, FM, "Accounts User"], _("Billing a subcontract claim"))
	with _elevated():
		pi = make_claim_bill(name)
	return {"message": _("Supplier bill {0} — {1} payable").format(pi.name, _money(pi.grand_total)), "open": ["Purchase Invoice", pi.name]}


def _a_claim_pay(name, a):
	# v1.8.4: paying a certified claim — MD, the project manager or accounts (their company only)
	cl = frappe.get_doc("Subcontract Claim", name)
	cl.check_permission("read")
	_need([PM, MD, FM, "Accounts User"], _("Paying a subcontract claim"))
	with _elevated():
		if not cl.purchase_invoice:
			make_claim_bill(name)
			cl.reload()
		pe = pay(cl.purchase_invoice)
	frappe.db.set_value("Subcontract Claim", name, {"status": "Paid", "paid_on": today()})
	return {"message": _("{0} paid — {1}").format(name, pe.name)}


def _a_sco_sign(name, a):
	s = frappe.get_doc("Subcontract Order", name)
	s.check_permission("write")
	_need([MD, PM], _("Signing a subcontract order"))
	s.status = "Active"
	s.save()
	return {"message": _("{0} signed — the subcontractor can mobilise").format(name)}


def _a_mr_approve(name, a):
	m = frappe.get_doc("Material Request", name)
	m.check_permission("submit")
	_need([MD] if m.get("hs_over_boq") else [PM, MD, BUY], _("Approving this material request"))
	m.submit()
	return {"message": _("{0} approved — create the PO or request quotations").format(name)}


def _a_mr_review(name, a):
	"""v1.8.0: partial approval — each line approved at its quantity (or less) or rejected; a reason is needed for what is cut.
	The rest is approved (submitted); when nothing is left the request is rejected (closed and kept, with the reason)."""
	m = frappe.get_doc("Material Request", name)
	if m.docstatus != 0:
		frappe.throw(_("{0} is already decided.").format(name))
	m.check_permission("submit")
	_need([MD] if m.get("hs_over_boq") else [PM, MD, BUY], _("Approving this material request"))
	lines = a.get("lines") or []
	if isinstance(lines, str):
		lines = frappe.parse_json(lines)
	want = {str(x.get("name")): x for x in lines}
	reason = (a.get("reason") or "").strip()
	keep, notes, total = [], [], len(m.items)
	for r in m.items:
		x = want.get(r.name) or {}
		q = flt(r.qty) if cint(x.get("reject")) == 0 and x.get("qty") in (None, "") else (0 if cint(x.get("reject")) else flt(x.get("qty")))
		ref = f"{r.get('hs_boq_item') + ' · ' if r.get('hs_boq_item') else ''}{r.item_name or r.item_code}"
		if q > flt(r.qty) + 1e-6:
			frappe.throw(_("{0}: you can approve at most the {1} {2} requested.").format(ref, f"{flt(r.qty):g}", r.uom))
		if q <= 0:
			notes.append(_("{0} — {1} {2} rejected").format(ref, f"{flt(r.qty):g}", r.uom))
			continue
		if q < flt(r.qty):
			notes.append(_("{0} — {1} of {2} {3} approved").format(ref, f"{q:g}", f"{flt(r.qty):g}", r.uom))
			r.qty = q
			r.stock_qty = q * flt(r.conversion_factor or 1)
		keep.append(r)
	if notes and not reason:
		frappe.throw(_("Give the reason for the lines you reject or reduce."))
	text = "\n".join(notes + ([_("Reason: {0}").format(reason)] if notes else [])) or None
	if not keep:
		m.hs_rejected_lines = text
		m.flags.ignore_permissions = True
		m.submit()
		m.cancel()
		m.add_comment("Comment", _("Rejected") + "<br>" + frappe.utils.escape_html(text or "").replace("\n", "<br>"))
		return {"message": _("{0} rejected — the site engineer sees the reason").format(name)}
	for i, r in enumerate(keep, 1):
		r.idx = i
	m.set("items", keep)
	m.hs_rejected_lines = text
	m.save()
	m.submit()
	if text:
		m.add_comment("Comment", _("Partly approved") + "<br>" + frappe.utils.escape_html(text).replace("\n", "<br>"))
		return {"message": _("{0} approved — {1} of {2} lines; what was cut is noted with the reason").format(name, len(keep), total)}
	return {"message": _("{0} approved — create the PO or request quotations").format(name)}


@frappe.whitelist()
def mr_lines(name):
	"""The lines of a material request waiting for approval (the partial approval window)."""
	m = frappe.get_doc("Material Request", name)
	m.check_permission("read")
	return {"name": m.name, "project": m.get("hs_project"), "over_boq": cint(m.get("hs_over_boq")), "docstatus": m.docstatus,
		"lines": [{"name": r.name, "item_code": r.item_code, "item_name": r.item_name, "boq": r.get("hs_boq_item"), "qty": flt(r.qty), "uom": r.uom,
			"need": str(r.schedule_date or "")} for r in m.items]}


@frappe.whitelist()
def mr_po_preset(name):
	""""Create PO" from an approved material request: what the app's purchase order window opens with — the lines still to
	order (linked to the request), the supplier who last supplied them, the request's company, project and date needed."""
	m = frappe.get_doc("Material Request", name)
	m.check_permission("read")
	frappe.has_permission("Purchase Order", "create", throw=True)
	if m.docstatus != 1 or m.material_request_type != "Purchase":
		frappe.throw(_("{0} must be an approved purchase request.").format(name))
	items, sup = [], None
	for r in m.items:
		left = flt(r.stock_qty) - flt(r.ordered_qty)
		if left <= 0:
			continue
		last = frappe.db.sql("""select po.supplier, pi.rate from `tabPurchase Order Item` pi join `tabPurchase Order` po on po.name = pi.parent
			where pi.item_code = %s and po.company = %s and po.docstatus = 1 order by po.transaction_date desc, po.creation desc limit 1""", (r.item_code, m.company), as_dict=True)
		if last and not sup:
			sup = last[0].supplier
		if not sup:
			sup = frappe.db.get_value("Item Default", {"parent": r.item_code, "company": m.company}, "default_supplier")
		rate = flt(last[0].rate) if last else flt(frappe.db.get_value("Item", r.item_code, "last_purchase_rate")) or flt(frappe.db.get_value("Item", r.item_code, "valuation_rate"))
		items.append({"item_code": r.item_code, "item_name": r.item_name, "qty": flt(left / flt(r.conversion_factor or 1), 3), "rate": rate or None, "warehouse": r.warehouse,
			"project": r.get("project") or m.get("hs_project"), "material_request": m.name, "material_request_item": r.name})
	if not items:
		frappe.throw(_("Everything on {0} is already ordered.").format(name))
	need = max((getdate(r.schedule_date) for r in m.items if r.schedule_date), default=None)
	out = {"company": m.company, "items": items, "schedule_date": str(need) if need and need >= getdate(today()) else None, "_mr": m.name,
		"project": m.get("hs_project") or None}
	if sup:
		out["party"] = sup
	return {k: v for k, v in out.items() if v is not None}


def _a_po_receive(name, a):
	"""Receive a project PO at the project's site store (what is still to come)."""
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	frappe.has_permission("Purchase Receipt", "create", throw=True)
	po = frappe.get_doc("Purchase Order", name)
	if po.docstatus != 1:
		frappe.throw(_("{0} must be approved first.").format(name))
	pj = po.get("hs_project") or next((i.project for i in po.items if i.project), None)
	pr = make_purchase_receipt(name)
	if pj:
		wh = site_warehouse(pj)
		pr.project, pr.set_warehouse = pj, wh
		for i in pr.items:
			i.warehouse, i.project = wh, pj
	pr.posting_date = a.get("date") or today()
	pr.set_posting_time = 1
	pr.insert()
	pr.submit()
	return {"message": _("{0} — received at {1}").format(pr.name, pr.items[0].warehouse if pr.items else "")}


def _a_timesheets(name, a):
	_need([PM, MD], _("Approving timesheets"))
	names = frappe.get_list("Timesheet", filters={"docstatus": 0, "parent_project": ["is", "set"]}, pluck="name")
	n = 0
	for t in names:
		d = frappe.get_doc("Timesheet", t)
		d.submit()
		n += 1
	return {"message": _("{0} timesheets approved — labour cost posted to the projects").format(n)}


ACTIONS = {
	"step": _a_step, "measure": _a_measure, "ipc_submit": _a_ipc_submit, "ipc_certify": _a_ipc_certify, "ipc_invoice": _a_ipc_invoice,
	"advance_invoice": _a_advance_invoice, "retention_invoice": _a_retention_invoice, "receive": _a_receive,
	"vo_submit": lambda n, a: _a_vo(n, a, "Pending client"), "vo_approve": lambda n, a: _a_vo(n, a, "Approved"), "vo_reject": lambda n, a: _a_vo(n, a, "Rejected"),
	"claim_certify": _a_claim_certify, "claim_bill": _a_claim_bill, "claim_pay": _a_claim_pay, "sco_sign": _a_sco_sign, "mr_approve": _a_mr_approve, "mr_review": _a_mr_review,
	"po_receive": _a_po_receive, "timesheets": _a_timesheets,
}


# ---------------------------------------------------------------- document events
def po_project(doc, method=None):
	"""A purchase order made from a project material request carries the project (header) and the Materials cost head."""
	if doc.meta.has_field("hs_project") and not doc.get("hs_project"):
		pj = {i.project for i in doc.items if i.get("project")}
		if len(pj) == 1:
			doc.hs_project = pj.pop()
	if doc.get("hs_project") and not doc.get("hs_cost_head"):
		doc.hs_cost_head = "Materials"
	if doc.get("hs_project"):
		for i in doc.items:
			i.project = i.project or doc.hs_project


def mr_project(doc, method=None):
	if doc.meta.has_field("hs_project") and not doc.get("hs_project"):
		pj = {i.project for i in doc.items if i.get("project")}
		if len(pj) == 1:
			doc.hs_project = pj.pop()
