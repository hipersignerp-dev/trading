"""v1.7.0: the prototype's HR & Payroll, KYC & Compliance, Corporate Tax and Group & Countries pages.

Same shape as api/module.py (get_module / get_rows dispatch there). Read with the user's own permissions.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, formatdate, get_first_day, getdate, today

from hipersign_trading.api.module import _fields, _fmt, _perm, _scope, kpi


def _d(v):
	return formatdate(v, "dd MMM yyyy") if v else "—"


def _hr():
	return frappe.db.table_exists("Employee") and _perm("Employee")


# ---------------------------------------------------------------- HR & Payroll
DOCS = (("hs_visa_expiry", "Visa"), ("hs_emirates_id_expiry", "Emirates ID"), ("hs_labour_card_expiry", "Labour card"), ("valid_upto", "Passport"))


def _employees(cos):
	if not _hr():
		return []
	rows = frappe.get_list("Employee", filters={"company": ["in", cos], "status": "Active"}, fields=_fields("Employee", ["name", "employee_name", "designation",
		"department", "date_of_joining", "hs_basic_salary", "hs_visa_expiry", "hs_emirates_id_expiry", "hs_labour_card_expiry", "valid_upto", "company", "user_id"]),
		order_by="date_of_joining asc", limit=500)
	if not rows:
		return rows
	names = [r.name for r in rows]
	gross = {}
	if frappe.db.table_exists("Salary Structure Assignment"):
		for s in frappe.get_all("Salary Structure Assignment", filters={"employee": ["in", names], "docstatus": 1, "from_date": ["<=", today()]},
			fields=["employee", "base"], order_by="from_date asc"):
			gross[s.employee] = flt(s.base)
	t = getdate(today())
	att = {a.employee: a for a in frappe.get_all("Attendance", filters={"employee": ["in", names], "attendance_date": t, "docstatus": ["<", 2]},
		fields=["employee", "status", "late_entry"])} if frappe.db.table_exists("Attendance") else {}
	leave = {l.employee: l for l in frappe.get_all("Leave Application", filters={"employee": ["in", names], "status": "Approved", "docstatus": 1,
		"from_date": ["<=", t], "to_date": [">=", t]}, fields=["employee", "leave_type"])} if frappe.db.table_exists("Leave Application") else {}
	for r in rows:
		r.gross = gross.get(r.name, 0)
		r.basic = flt(r.get("hs_basic_salary")) or round(r.gross * 0.6, 2)
		r.years = date_diff(t, r.date_of_joining) / 365.25 if r.date_of_joining else 0
		# UAE end-of-service: 21 days' basic per year for the first five years, 30 days after; nothing before one year
		y = r.years
		r.gratuity = 0 if y < 1 else round(r.basic / 30 * (21 * min(y, 5) + 30 * max(0, y - 5)), 2)
		a, lv = att.get(r.name), leave.get(r.name)
		r.today = (_("On leave"), "orange") if lv else ((_("Late"), "orange") if a and a.late_entry else (_(a.status), "green" if a.status == "Present" else "red") if a else (_("Not marked"), "grey"))
		r.on_leave = bool(lv) or bool(a and a.status == "On Leave")
		r.absent = bool(a and a.status == "Absent")
		r.late = bool(a and a.late_entry)
		exp = sorted([(getdate(r.get(f)), lab) for f, lab in DOCS if r.get(f) and date_diff(r.get(f), t) <= 60])
		r.doc_warn = exp
	return rows


def _dept(d):
	return (d or "").rsplit(" - ", 1)[0] or "—"


def hr_module():
	cos, start, end, label, cur = _scope()
	if not _hr():
		return {"title": _("HR & Payroll"), "desc": _("You have no access to employee records — ask the HR Manager."), "new": [], "kpis": [], "tabs": [], "nosearch": 1}
	emps = _employees(cos)
	t = getdate(today())
	leave_open = frappe.db.count("Leave Application", {"company": ["in", cos], "status": "Open", "docstatus": 0}) if _perm("Leave Application") else 0
	claims = frappe.get_list("Expense Claim", filters={"company": ["in", cos], "docstatus": 0}, fields=["total_claimed_amount"], limit=500) \
		if frappe.db.table_exists("Expense Claim") and _perm("Expense Claim") else []
	docs_exp = [e for e in emps if e.doc_warn]
	return {
		"title": _("HR & Payroll"),
		"desc": _("Employees, attendance, leave and monthly payroll with the UAE WPS salary file — plus document expiry and end-of-service gratuity."),
		"new": [{"label": _("Leave request"), "doctype": "Leave Application"}, {"label": _("Add employee"), "doctype": "Employee", "primary": 1}],
		"kpis": [
			kpi(_("Headcount"), len(emps), _("{0} departments").format(len({e.department for e in emps if e.department})), "blue", "users", tab="employees"),
			kpi(_("Monthly payroll (gross)"), sum(e.gross for e in emps), _("Feeds Profit & loss"), "navy", "banknote", True, cur, tab="payroll"),
			kpi(_("On leave today"), len([e for e in emps if e.on_leave]), _("{0} absent · {1} late").format(len([e for e in emps if e.absent]), len([e for e in emps if e.late])),
				"violet", "clock", tab="attendance"),
			kpi(_("Leave requests"), leave_open, _("Waiting for the HR Manager"), "amber", "inbox", tab="leave"),
			kpi(_("Documents expiring"), len(docs_exp), _("Visa, Emirates ID, labour card, passport ≤ 60 days"), "red", "triangle-alert", tab="docs"),
			kpi(_("Gratuity liability"), sum(e.gratuity for e in emps), _("End-of-service benefit accrued"), "violet", "scale", True, cur, tab="docs"),
		],
		"tabs": [
			{"key": "employees", "label": _("Employees"), "chips": []},
			{"key": "attendance", "label": _("Attendance"), "chips": []},
			{"key": "leave", "label": _("Leave") + (f" ({leave_open})" if leave_open else ""), "chips": [["open", _("To approve")], ["all", _("All")]]},
			{"key": "payroll", "label": _("Payroll & WPS"), "chips": []},
			{"key": "expenses", "label": _("Expenses & advances") + (f" ({len(claims)})" if claims else ""), "chips": []},
			{"key": "docs", "label": _("Documents & gratuity"), "chips": []},
		],
		"default_tab": "employees",
	}


def hr_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "employees":
		emps = _employees(cos)
		if q:
			emps = [e for e in emps if q.lower() in (e.employee_name + (e.designation or "")).lower()]
		return {"cols": [{"label": _("Employee")}, {"label": _("Department")}, {"label": _("Joined")}, {"label": _("Gross / month"), "cls": "num"}, {"label": _("Today")}, {"label": _("Documents")}],
			"rows": [{"dt": "Employee", "name": e.name, "cells": [{"main": e.employee_name, "sub": f"{e.name} · {e.designation or ''}"}, {"pill": _dept(e.department), "tone": "blue"},
				{"main": _d(e.date_of_joining), "sub": _("{0} yrs").format(f"{e.years:.1f}")}, {"money": e.gross}, {"pill": e.today[0], "tone": e.today[1]},
				{"text": "⚠ " + e.doc_warn[0][1], "tone": "red"} if e.doc_warn else {"text": _("Valid"), "tone": ""}]} for e in emps],
			"actions": [{"label": _("Add employee"), "primary": 1, "route": ["Form", "Employee", "new"]}], "empty": _("No active employees.")}
	if tab == "attendance":
		if not _perm("Attendance"):
			return {"cols": [], "rows": [], "empty": _("Not permitted")}
		rows = frappe.get_list("Attendance", filters={"company": ["in", cos], "docstatus": ["<", 2], "attendance_date": [">=", add_days(t, -30)]},
			fields=["name", "employee", "employee_name", "attendance_date", "status", "late_entry", "early_exit", "in_time", "out_time"], order_by="attendance_date desc, employee_name asc", limit=300)
		return {"title": _("Attendance — last 30 days"), "cols": [{"label": _("Date")}, {"label": _("Employee")}, {"label": _("In")}, {"label": _("Out")}, {"label": _("Status")}],
			"rows": [{"dt": "Attendance", "name": a.name, "cells": [{"date": a.attendance_date}, {"main": a.employee_name, "sub": a.employee},
				frappe.utils.format_datetime(a.in_time, "HH:mm") if a.get("in_time") else "—", frappe.utils.format_datetime(a.out_time, "HH:mm") if a.get("out_time") else "—",
				{"pill": _("Late") if a.late_entry else _(a.status), "tone": "orange" if a.late_entry or a.status in ("Half Day", "On Leave") else "green" if a.status == "Present" else "red"}]} for a in rows],
			"actions": [{"label": _("Mark attendance"), "route": ["Form", "Attendance", "new"]}], "empty": _("No attendance marked in the last 30 days.")}
	if tab == "leave":
		f = {"company": ["in", cos], "docstatus": ["<", 2]}
		if chip != "all":
			f.update({"status": "Open", "docstatus": 0})
		rows = frappe.get_list("Leave Application", filters=f, fields=["name", "employee", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "status",
			"description", "leave_approver"], order_by="from_date asc", limit=200) if _perm("Leave Application") else []
		return {"cols": [{"label": _("Request")}, {"label": _("Employee")}, {"label": _("Type")}, {"label": _("From")}, {"label": _("To")}, {"label": _("Days"), "cls": "num"}, {"label": _("Status")}, {"label": ""}],
			"rows": [{"dt": "Leave Application", "name": l.name, "cells": [{"code": l.name}, {"main": l.employee_name, "sub": (l.description or "")[:50]}, _(l.leave_type), {"date": l.from_date},
				{"date": l.to_date}, flt(l.total_leave_days), {"pill": _(l.status), "tone": {"Open": "orange", "Approved": "green", "Rejected": "red"}.get(l.status, "grey")},
				{"button": _("Review"), "open": ["Leave Application", l.name], "primary": 1} if l.status == "Open" else ""]} for l in rows], "empty": _("No leave requests waiting.")}
	if tab == "payroll":
		runs = frappe.get_list("Payroll Entry", filters={"company": ["in", cos], "docstatus": ["<", 2]}, fields=["name", "start_date", "end_date", "posting_date", "docstatus", "company"],
			order_by="start_date desc", limit=24) if frappe.db.table_exists("Payroll Entry") and _perm("Payroll Entry") else []
		slips = {}
		for s in frappe.get_all("Salary Slip", filters={"payroll_entry": ["in", [r.name for r in runs] or [""]], "docstatus": ["<", 2]}, fields=["payroll_entry", "gross_pay", "net_pay", "total_deduction"]):
			x = slips.setdefault(s.payroll_entry, [0, 0, 0, 0])
			x[0] += 1
			x[1] += flt(s.gross_pay)
			x[2] += flt(s.total_deduction)
			x[3] += flt(s.net_pay)
		rows = []
		for r in runs:
			n, g, dd, net = slips.get(r.name, [0, 0, 0, 0])
			rows.append({"dt": "Payroll Entry", "name": r.name, "cells": [{"main": formatdate(r.start_date, "MMMM yyyy"), "sub": r.name}, n, {"money": g}, {"money": dd}, {"money": net},
				{"pill": _("Posted") if r.docstatus == 1 else _("Draft"), "tone": "green" if r.docstatus == 1 else "orange"},
				{"button": _("WPS file"), "make": "wps", "source": r.name} if r.docstatus == 1 else ""]})
		return {"title": _("Payroll runs"), "cols": [{"label": _("Month")}, {"label": _("Employees"), "cls": "num"}, {"label": _("Gross"), "cls": "num"}, {"label": _("Deductions"), "cls": "num"},
			{"label": _("Net (WPS)"), "cls": "num"}, {"label": _("Status")}, {"label": ""}], "rows": rows,
			"actions": [{"label": _("Run payroll"), "primary": 1, "route": ["Form", "Payroll Entry", "new"]}], "empty": _("No payroll runs yet — use Run payroll.")}
	if tab == "expenses":
		rows = []
		if frappe.db.table_exists("Expense Claim") and _perm("Expense Claim"):
			for c in frappe.get_list("Expense Claim", filters={"company": ["in", cos], "docstatus": ["<", 2]}, fields=["name", "employee_name", "posting_date", "total_claimed_amount",
				"total_sanctioned_amount", "approval_status", "status", "docstatus", "remark"], order_by="posting_date desc", limit=100):
				st = _("Paid") if c.status == "Paid" else _("Approved, to pay") if c.docstatus == 1 else _("Awaiting approval") if c.docstatus == 0 else _(c.status)
				rows.append({"dt": "Expense Claim", "name": c.name, "cells": [{"code": c.name}, {"main": c.employee_name, "sub": (c.remark or "")[:50]}, _("Expense claim"), {"date": c.posting_date},
					{"money": c.total_claimed_amount}, {"pill": st, "tone": "green" if c.status == "Paid" else "blue" if c.docstatus == 1 else "orange"}]})
		if frappe.db.table_exists("Employee Advance") and _perm("Employee Advance"):
			for a in frappe.get_list("Employee Advance", filters={"company": ["in", cos], "docstatus": ["<", 2]}, fields=["name", "employee_name", "posting_date", "advance_amount",
				"paid_amount", "claimed_amount", "return_amount", "status", "purpose"], order_by="posting_date desc", limit=100):
				rows.append({"dt": "Employee Advance", "name": a.name, "cells": [{"code": a.name}, {"main": a.employee_name, "sub": (a.purpose or "")[:50]}, _("Advance"), {"date": a.posting_date},
					{"money": a.advance_amount}, {"pill": _(a.status), "tone": "orange" if a.status in ("Draft", "Unpaid") else "blue"}]})
		return {"cols": [{"label": _("Document")}, {"label": _("Employee")}, {"label": _("Type")}, {"label": _("Date")}, {"label": _("Amount"), "cls": "num"}, {"label": _("Status")}], "rows": rows,
			"actions": [{"label": _("New expense claim"), "primary": 1, "route": ["Form", "Expense Claim", "new"]}, {"label": _("Request advance"), "route": ["Form", "Employee Advance", "new"]}],
			"empty": _("No expense claims or advances.")}
	if tab == "docs":
		emps = _employees(cos)
		rows = []
		for e in emps:
			nxt = sorted([(getdate(e.get(f)), lab) for f, lab in DOCS if e.get(f)])
			first = nxt[0] if nxt else None
			left = date_diff(first[0], t) if first else None
			rows.append({"dt": "Employee", "name": e.name, "cells": [{"main": e.employee_name, "sub": e.designation or ""},
				*[{"date": e.get(f), "late": bool(e.get(f) and date_diff(e.get(f), t) <= 60)} for f, _lab in DOCS],
				{"pill": _("{0} in {1} days").format(first[1], left) if left is not None and 0 <= left <= 60 else _("{0} expired").format(first[1]) if left is not None and left < 0 else _("Valid"),
					"tone": "red" if left is not None and left < 0 else "orange" if left is not None and left <= 60 else "green"},
				{"main": f"{e.years:.1f} " + _("yrs"), "sub": _("basic {0}").format(frappe.format(e.basic, {"fieldtype": "Currency", "options": cur}))}, {"money": e.gratuity}]})
		return {"cols": [{"label": _("Employee")}, {"label": _("Visa")}, {"label": _("Emirates ID")}, {"label": _("Labour card")}, {"label": _("Passport")}, {"label": _("Next expiry")},
			{"label": _("Service")}, {"label": _("Gratuity"), "cls": "num"}], "rows": rows, "empty": _("No active employees.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- KYC & Compliance
def _parties(dt, cos):
	if not _perm(dt):
		return []
	fields = _fields(dt, ["name", "customer_name" if dt == "Customer" else "supplier_name", "hs_trade_licence_no", "hs_licence_authority", "hs_trade_licence_expiry", "hs_kyc_status",
		"hs_kyc_notes", "tax_id", "disabled", "is_internal_customer" if dt == "Customer" else "is_internal_supplier", "hs_supplier_kind", "customer_group", "supplier_group"])
	rows = frappe.get_list(dt, filters={"disabled": 0}, fields=fields, order_by="name asc", limit=500)
	t = getdate(today())
	files = {}
	for f in frappe.get_all("File", filters={"attached_to_doctype": dt, "attached_to_name": ["in", [r.name for r in rows] or [""]]}, fields=["attached_to_name", "hs_document_type"]):
		files.setdefault(f.attached_to_name, set()).add(f.hs_document_type or "")
	lim, exp = {}, {}
	if dt == "Customer":
		for c in frappe.get_all("Customer Credit Limit", filters={"parent": ["in", [r.name for r in rows] or [""]], "company": ["in", cos]}, fields=["parent", "credit_limit"]):
			lim[c.parent] = lim.get(c.parent, 0) + flt(c.credit_limit)
		for r in frappe.db.sql("""select customer, sum(outstanding_amount) from `tabSales Invoice` where docstatus=1 and company in %s and outstanding_amount > 0 group by customer""", (tuple(cos),)):
			exp[r[0]] = flt(r[1])
	for r in rows:
		r.title = r.get("customer_name") or r.get("supplier_name") or r.name
		ex = r.get("hs_trade_licence_expiry")
		left = date_diff(ex, t) if ex else None
		r.lic = (_("Missing"), "red") if not r.get("hs_trade_licence_no") else (_("Expired"), "red") if left is not None and left < 0 else \
			(_("Expiring"), "orange") if left is not None and left <= 30 else (_("Valid"), "green")
		r.trn = (_("Valid"), "green") if r.get("tax_id") else (_("Missing"), "red")
		have = files.get(r.name, set())
		r.files = have
		r.limit, r.exposure = lim.get(r.name, 0), exp.get(r.name, 0)
		r.over = bool(r.limit and r.exposure > r.limit)
		st = r.get("hs_kyc_status") or "Pending"
		if st == "Blocked" or (r.lic[0] == _("Expired") and dt == "Customer"):
			r.state = (_("Blocked"), "red")
		elif st == "Verified" and r.lic[1] == "green" and r.trn[1] == "green":
			r.state = (_("Verified"), "green")
		else:
			r.state = (_("Action needed"), "orange")
		r.missing = [x for x, ok in ((_("Trade licence"), r.get("hs_trade_licence_no")), (_("TRN"), r.get("tax_id"))) if not ok]
		r.left = left
	return [r for r in rows if not (r.get("is_internal_customer") or r.get("is_internal_supplier"))]


def kyc_module():
	cos, start, end, label, cur = _scope()
	cs, ss = _parties("Customer", cos), _parties("Supplier", cos)
	allp = cs + ss
	return {
		"title": _("KYC & Compliance"),
		"desc": _("Trade licences, TRN, Emirates IDs of signatories, credit insurance and verified bank details for every customer and supplier — with expiry warnings and order blocking."),
		"new": [],
		"kpis": [
			kpi(_("Blocked"), len([p for p in allp if p.state[1] == "red"]), _("Expired licence — no new orders"), "red", "lock", tab="customers"),
			kpi(_("Expiring in 30 days"), len([p for p in allp if p.left is not None and 0 <= p.left <= 30]), _("Licence or registration"), "amber", "clock", tab="customers"),
			kpi(_("Missing documents"), sum(len(p.missing) for p in allp), _("Licence or TRN not on file"), "violet", "file", tab="suppliers"),
			kpi(_("Over credit limit"), len([p for p in cs if p.over]), _("Open invoices above the credit limit"), "navy", "shield", tab="customers"),
		],
		"tabs": [{"key": "customers", "label": _("Customers"), "chips": []}, {"key": "suppliers", "label": _("Suppliers"), "chips": []}, {"key": "rules", "label": _("Rules"), "chips": []}],
		"default_tab": "customers",
	}


def kyc_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	if tab in ("customers", "suppliers"):
		dt = "Customer" if tab == "customers" else "Supplier"
		ps = _parties(dt, cos)
		ps.sort(key=lambda p: ({"red": 0, "orange": 1, "green": 2}[p.state[1]], p.title))
		if q:
			ps = [p for p in ps if q.lower() in p.title.lower()]
		rows = []
		for p in ps:
			lic = [{"pill": p.lic[0], "tone": p.lic[1]}]
			if p.get("hs_trade_licence_no"):
				lic.append(" · ".join(x for x in [p.hs_trade_licence_no, p.get("hs_licence_authority"), _("expires {0}").format(_d(p.hs_trade_licence_expiry)) if p.get("hs_trade_licence_expiry") else ""] if x))
			cells = [{"main": p.title, "sub": p.name if p.name != p.title else (_(p.get("hs_supplier_kind") or "") if dt == "Supplier" else _(p.get("customer_group") or ""))},
				{"main": lic[1] if len(lic) > 1 else _("No licence on file"), "sub": p.lic[0], "late": p.lic[1] != "green"},
				{"main": p.get("tax_id") or _("No TRN — needed on tax invoices"), "sub": p.trn[0], "late": p.trn[1] != "green"}]
			if dt == "Customer":
				cells.append({"money": p.exposure, "sub": _("limit {0}").format(_fmt(p.limit, cur)) if p.limit else _("no limit"), "neg": p.over})
			cells += [{"pill": p.state[0], "tone": p.state[1]}, {"button": _("Update"), "open": [dt, p.name], "primary": 1}]
			rows.append({"dt": dt, "name": p.name, "cells": cells})
		cols = [{"label": _("Party")}, {"label": _("Licence / registration")}, {"label": _("TRN")}] + ([{"label": _("Exposure"), "cls": "num"}] if dt == "Customer" else []) + \
			[{"label": _("Status")}, {"label": ""}]
		return {"title": _("Customer compliance files") if dt == "Customer" else _("Supplier compliance files"), "cols": cols, "rows": rows, "empty": _("Nothing here.")}
	if tab == "rules":
		rs = frappe.get_all("Hipersign Document Rule", filters={"active": 1}, fields=["name", "reference_doctype", "document_type", "level", "min_amount"], order_by="reference_doctype asc") \
			if frappe.db.table_exists("Hipersign Document Rule") else []
		rows = [{"cells": [{"main": _("Expired trade licence blocks new orders")}, _("Customer"), _("Sales order, delivery"), {"pill": _("Block"), "tone": "red"}]},
			{"cells": [{"main": _("Licence expiring within 30 days warns the salesperson")}, _("Customer, supplier"), _("All documents"), {"pill": _("Warn"), "tone": "orange"}]}]
		rows += [{"dt": "Hipersign Document Rule", "name": r.name, "cells": [{"main": _(r.document_type), "sub": _("from {0}").format(_fmt(r.min_amount, cur)) if flt(r.min_amount) else ""},
			_(r.reference_doctype), _("Before submit"), {"pill": _(r.level), "tone": "red" if r.level == "Required" else "orange"}]} for r in rs]
		return {"cols": [{"label": _("Rule")}, {"label": _("Applies to")}, {"label": _("When")}, {"label": _("Effect")}], "rows": rows,
			"actions": [{"label": _("Add rule"), "route": ["Form", "Hipersign Document Rule", "new"]}]}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Corporate Tax
def _ct_company(cos):
	uae = [c for c in cos if frappe.get_cached_value("Company", c, "country") == "United Arab Emirates"]
	return uae[0] if uae else cos[0]


def _ct_figures(company, frm, to):
	r = frappe.db.sql("""select a.root_type, a.account_type, sum(gle.credit - gle.debit) from `tabGL Entry` gle join tabAccount a on a.name = gle.account
		where gle.is_cancelled = 0 and gle.company = %s and gle.posting_date between %s and %s and a.root_type in ('Income', 'Expense')
		group by a.root_type, a.account_type""", (company, frm, to))
	f = frappe._dict(revenue=0, cogs=0, dep=0, opex=0)
	for root, typ, amt in r:
		if root == "Income":
			f.revenue += flt(amt)
		elif typ in ("Cost of Goods Sold", "Stock Adjustment"):
			f.cogs += -flt(amt)
		elif typ == "Depreciation":
			f.dep += -flt(amt)
		else:
			f.opex += -flt(amt)
	f.profit = f.revenue - f.cogs - f.dep - f.opex
	return f


def _ct_state(chip=None):
	cos, start, end, label, cur = _scope()
	co = _ct_company(cos)
	cur = frappe.get_cached_value("Company", co, "default_currency")
	t = getdate(today())
	ys, ye = getdate(f"{t.year}-01-01"), getdate(f"{t.year}-12-31")
	ytd = _ct_figures(co, ys, t)
	months = max(1, (t.year - ys.year) * 12 + t.month - (1 if t.day < 28 else 0))
	k = 12 / months if chip != "ytd" else 1
	f = frappe._dict({x: flt(ytd[x]) * k for x in ("revenue", "cogs", "dep", "opex", "profit")})
	ret = frappe.db.get_value("Tax Return", {"company": co, "tax_type": "Corporate Tax", "period_from": ys, "status": ["!=", "Rejected"]},
		["name", "status", "adjustments", "small_business_relief", "ct_threshold", "due_date"], as_dict=True) if _perm("Tax Return") else None
	adj = flt(ret.adjustments) if ret else 0
	threshold = flt(ret.ct_threshold) if ret and ret.ct_threshold else 375000
	sbr = bool(ret and ret.small_business_relief) and f.revenue <= 3000000
	taxable = f.profit + adj
	payable = 0 if sbr else max(0, taxable - threshold) * 0.09
	from hipersign_trading.hipersign_trading.doctype.tax_return.tax_return import due_date

	return frappe._dict(co=co, cur=cur, f=f, ytd=ytd, months=months, ret=ret, adj=adj, threshold=threshold, sbr=sbr, taxable=taxable, payable=payable,
		due=getdate(due_date("Corporate Tax", ye)), year=t.year, chip=chip or "forecast")


def tax_module():
	s = _ct_state()
	t = getdate(today())
	left = date_diff(s.due, t)
	return {
		"title": _("UAE Corporate Tax"),
		"desc": _("Corporate tax computed from the same ledger as your VAT and financial reports — adjustments, small business relief, provision, approval and filing in one place."),
		"new": [],
		"kpis": [
			kpi(_("Revenue — FY {0} forecast").format(s.year), s.f.revenue, _("Above AED 3M — no small business relief") if s.f.revenue > 3000000 else _("Small business relief possible"),
				"blue", "tag", True, s.cur),
			kpi(_("Accounting profit"), s.f.profit, _("After landed cost of sales & expenses"), "navy", "chart-column", True, s.cur),
			kpi(_("Taxable income"), s.taxable, _("After tax adjustments"), "violet", "file-text", True, s.cur),
			kpi(_("Corporate tax payable"), s.payable, _("9% above {0} {1} · effective {2}%").format(s.cur, frappe.utils.fmt_money(s.threshold, 0),
				f"{(s.payable / s.taxable * 100) if s.taxable > 0 else 0:.1f}"), "amber", "scale", True, s.cur),
			kpi(_("Return & payment due"), _d(s.due), _("{0} days left · 9 months after year end").format(left), "red", "clock"),
		],
		"tabs": [{"key": "computation", "label": _("Computation FY {0}").format(s.year), "chips": [["forecast", _("Full-year forecast")], ["ytd", _("Year to date ({0})").format(
			_("Jan–{0}").format(formatdate(t, "MMM")))]]}],
		"default_tab": "computation",
		"nosearch": 1,
	}


STEPS = ["Prepared", "Pending Finance Manager", "Approved", "Submitted", "Paid"]


def tax_rows(tab, chip, q=None):
	s = _ct_state(chip)
	f, cur = s.f, s.cur
	at = STEPS.index(s.ret.status) if s.ret and s.ret.status in STEPS else 0
	lines = [
		{"label": _("Revenue"), "value": f.revenue, "currency": cur},
		{"label": _("Cost of sales (landed)"), "value": f.cogs, "currency": cur, "sign": "−"},
		{"label": _("Operating expenses"), "value": f.opex, "currency": cur, "sign": "−"},
		{"label": _("Depreciation"), "value": f.dep, "currency": cur, "sign": "−"},
		{"label": _("Accounting profit before tax"), "value": f.profit, "currency": cur, "hl": "blue"},
		{"label": _("Add: non-deductible items and other adjustments"), "value": s.adj, "currency": cur, "sign": "+" if s.adj >= 0 else "−"},
		{"label": _("Taxable income"), "value": s.taxable, "currency": cur, "hl": "violet"},
		{"label": _("0% on first {0} {1}").format(cur, frappe.utils.fmt_money(s.threshold, 0)), "value": 0, "currency": cur},
		{"label": _("9% on {0} {1}").format(cur, frappe.utils.fmt_money(max(0, s.taxable - s.threshold), 2)), "value": 0 if s.sbr else max(0, s.taxable - s.threshold) * 0.09, "currency": cur},
	]
	if s.sbr:
		lines.append({"label": _("Small business relief elected"), "text": _("No tax"), "muted": 1})
	lines.append({"label": _("Corporate tax payable"), "value": s.payable, "currency": cur, "total": 1})
	adj_items = [{"label": _("Client entertainment (50% disallowed)"), "sub": _("Add back")}, {"label": _("Fines & penalties"), "sub": _("Add back")},
		{"label": _("Donations to non-approved bodies"), "sub": _("Add back")}, {"label": _("Exempt income (UAE dividends)"), "sub": _("Deduct")},
		{"label": _("Tax losses brought forward"), "sub": _("Deduct, capped at 75% of taxable income")}]
	if s.ret:
		adj_items = [{"label": _("Adjustments on the return"), "sub": _("Entered on {0}").format(s.ret.name), "value": {"money": s.adj}, "dt": "Tax Return", "name": s.ret.name}] + adj_items[:0]
	foot = [{"label": _("Open return {0}").format(s.ret.name), "primary": 1, "open": ["Tax Return", s.ret.name], "icon": "check"}] if s.ret else \
		[{"label": _("Prepare FY {0} return").format(s.year), "primary": 1, "method": "hipersign_trading.api.module_people.ct_prepare", "args": {"company": s.co},
			"confirm": _("Create the FY {0} corporate tax return for {1}? Its figures come from the ledger and stay editable until it is sent for approval.").format(s.year, s.co), "icon": "check"}]
	foot.append({"label": _("Profit and Loss report"), "route": ["query-report", "Profit and Loss Statement"], "options": {"company": s.co}})
	return {"blocks": [
		{"type": "note", "text": _("Forecast annualises Jan–{0} actuals ({1} months); switch to year to date to see the ledger position · {2}").format(formatdate(today(), "MMM"), s.months, s.co)
			if s.chip != "ytd" else _("Ledger position, 1 Jan to today · {0}").format(s.co)},
		{"type": "steps", "steps": [_("Draft"), _("Finance review"), _("Approved"), _("Filed"), _("Paid")], "at": at},
		{"type": "statement", "span": 2, "title": _("Tax computation — FY {0}").format(s.year), "sub": _("12-month forecast") if s.chip != "ytd" else _("year to date"), "lines": lines},
		{"type": "list", "span": 1, "title": _("Tax adjustments"), "items": adj_items, "foot": foot,
			"note": _("Adjustments are entered on the return; the threshold and small business relief are set there too.")},
	]}


@frappe.whitelist()
def ct_prepare(company):
	frappe.has_permission("Tax Return", "create", throw=True)
	t = getdate(today())
	ys = f"{t.year}-01-01"
	ex = frappe.db.get_value("Tax Return", {"company": company, "tax_type": "Corporate Tax", "period_from": ys, "status": ["!=", "Rejected"]})
	if ex:
		return {"message": _("{0} already exists").format(ex), "name": ex}
	d = frappe.get_doc({"doctype": "Tax Return", "tax_type": "Corporate Tax", "company": company, "period_from": ys, "period_to": f"{t.year}-12-31", "ct_threshold": 375000})
	d.insert()
	return {"message": _("{0} prepared").format(d.name), "name": d.name}


# ---------------------------------------------------------------- Group & Countries
def _companies():
	return frappe.get_all("Company", fields=["name", "abbr", "country", "default_currency", "parent_company", "is_group"], order_by="lft asc" if frappe.get_meta("Company").has_field("lft") else "name asc")


def _co_figures(co, frm, to):
	r = frappe.db.sql("""select a.root_type, sum(gle.credit - gle.debit) from `tabGL Entry` gle join tabAccount a on a.name = gle.account
		where gle.is_cancelled = 0 and gle.company = %s and gle.posting_date between %s and %s and a.root_type in ('Income', 'Expense') group by a.root_type""", (co, frm, to))
	inc = sum(flt(x[1]) for x in r if x[0] == "Income")
	exp = -sum(flt(x[1]) for x in r if x[0] == "Expense")
	cash = flt(frappe.db.sql("""select sum(gle.debit - gle.credit) from `tabGL Entry` gle join tabAccount a on a.name = gle.account
		where gle.is_cancelled = 0 and gle.company = %s and gle.posting_date <= %s and a.account_type in ('Bank', 'Cash')""", (co, to))[0][0])
	stock = flt(frappe.db.sql("""select sum(stock_value_difference) from `tabStock Ledger Entry` where is_cancelled = 0 and company = %s and posting_date <= %s""", (co, to))[0][0])
	return frappe._dict(revenue=inc, profit=inc - exp, cash=cash, stock=stock)


def _group_state():
	from hipersign_trading.group import rate

	t = getdate(today())
	ys = getdate(f"{t.year}-01-01")
	cur = frappe.db.get_single_value("Hipersign Settings", "group_currency") if frappe.get_meta("Hipersign Settings").has_field("group_currency") else None
	cur = cur or "AED"
	mem = {m.company: m for m in frappe.get_all("Hipersign Group Member", filters={"active": 1}, fields=["name", "company", "ownership_pct", "is_parent", "site_url", "currency"])} \
		if frappe.db.table_exists("Hipersign Group Member") else {}
	cos = [c for c in _companies() if not c.is_group]
	for c in cos:
		c.f = _co_figures(c.name, ys, t)
		c.rate = rate(c.default_currency, cur, t) if c.default_currency != cur else 1
		c.own = flt((mem.get(c.name) or {}).get("ownership_pct") or 100)
		c.site = (mem.get(c.name) or {}).get("site_url")
	ic = frappe.db.sql("""select si.name, si.company, si.customer, si.posting_date, si.grand_total, si.currency, si.inter_company_invoice_reference
		from `tabSales Invoice` si join tabCustomer c on c.name = si.customer where si.docstatus = 1 and c.is_internal_customer = 1 and si.is_return = 0
		order by si.posting_date desc limit 100""", as_dict=True)
	return frappe._dict(cur=cur, cos=cos, ic=ic, year=t.year, group=[c for c in _companies() if c.is_group])


def group_module():
	if not _perm("GL Entry") and not _perm("Account"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	g = _group_state()
	rev = sum(c.f.revenue * c.rate for c in g.cos)
	prof = sum(c.f.profit * c.rate for c in g.cos)
	nci = sum(c.f.profit * c.rate * (1 - c.own / 100) for c in g.cos)
	tobook = [x for x in g.ic if not x.inter_company_invoice_reference]
	countries = sorted({c.country for c in g.cos if c.country})
	return {
		"title": _("Group & Countries"),
		"desc": _("{0} companies in {1} countries — rolled up here: the group, each country and each company, with inter-company trading on both sides and consolidated statements in {2}.").format(
			len(g.cos), len(countries), g.cur),
		"new": [],
		"kpis": [
			kpi(_("Revenue — {0} to date").format(g.year), rev, _("All companies, in {0}").format(g.cur), "blue", "chart-column", True, g.cur, tab="dashboard"),
			kpi(_("Profit for the year"), prof, _("Owners {0} · NCI {1}").format(_fmt(prof - nci, g.cur), _fmt(nci, g.cur)), "green", "trending-up", True, g.cur, tab="pl"),
			kpi(_("Companies"), len(g.cos), " · ".join(countries), "navy", "building", tab="structure"),
			kpi(_("Inter-company to book"), len(tobook), _("{0} not mirrored").format(_fmt(sum(flt(x.grand_total) for x in tobook), g.cur)), "amber", "workflow", tab="ic"),
			kpi(_("Cash & bank"), sum(c.f.cash * c.rate for c in g.cos), _("All companies, today"), "violet", "banknote", True, g.cur, tab="dashboard"),
			kpi(_("Stock"), sum(c.f.stock * c.rate for c in g.cos), _("At valuation"), "teal", "package", True, g.cur, tab="dashboard"),
		],
		"tabs": [
			{"key": "structure", "label": _("Structure"), "chips": []},
			{"key": "dashboard", "label": _("Dashboard"), "chips": []},
			{"key": "ic", "label": _("Inter-company") + (f" ({len(tobook)})" if tobook else ""), "chips": []},
			{"key": "pl", "label": _("Consolidated P&L"), "chips": []},
			{"key": "bs", "label": _("Consolidated balance sheet"), "chips": []},
			{"key": "books", "label": _("Company books & items"), "chips": []},
		],
		"default_tab": "structure",
		"nosearch": 1,
	}


def group_rows(tab, chip, q=None):
	g = _group_state()
	if tab == "structure":
		by = {}
		for c in g.cos:
			by.setdefault(c.country or _("Other"), []).append(c)
		parent = g.group[0].name if g.group else ""
		return {"blocks": [{"type": "groups", "title": _("Group structure"), "sub": _("Click a company to open it"),
			"banner": {"title": parent or _("Group"), "sub": _("· presentation currency {0}").format(g.cur)},
			"groups": [{"title": _(country), "sub": _("{0} companies").format(len(cs)) if len(cs) != 1 else _("1 company"),
				"cards": [{"dt": "Company", "name": c.name, "title": c.name, "tag": c.default_currency, "meta": (_("{0}% owned").format(f"{c.own:g}") if c.own < 100 else _("100% owned")) + f" · {c.abbr}",
					"lines": [_("Revenue {0} · profit {1}").format(_fmt(c.f.revenue, c.default_currency), _fmt(c.f.profit, c.default_currency))] + ([_("site {0}").format(c.site)] if c.site else [])}
					for c in cs]} for country, cs in by.items()]}]}
	if tab == "dashboard":
		return {"title": _("Companies — {0} to date, in {1}").format(g.year, g.cur), "cols": [{"label": _("Company")}, {"label": _("Country")}, {"label": _("Revenue"), "cls": "num"},
			{"label": _("Profit"), "cls": "num"}, {"label": _("Margin")}, {"label": _("Cash & bank"), "cls": "num"}, {"label": _("Stock"), "cls": "num"}],
			"rows": [{"dt": "Company", "name": c.name, "cells": [{"main": c.name, "sub": f"{c.abbr} · {c.default_currency}"}, _(c.country or ""), {"money": c.f.revenue * c.rate},
				{"money": c.f.profit * c.rate, "neg": c.f.profit < 0}, {"text": f"{c.f.profit / c.f.revenue * 100:.1f}%" if c.f.revenue else "—"}, {"money": c.f.cash * c.rate}, {"money": c.f.stock * c.rate}]}
				for c in g.cos]}
	if tab == "ic":
		return {"cols": [{"label": _("Invoice")}, {"label": _("From")}, {"label": _("To")}, {"label": _("Date")}, {"label": _("Amount"), "cls": "num"}, {"label": _("Other side")}],
			"rows": [{"dt": "Sales Invoice", "name": x.name, "cells": [{"code": x.name}, x.company, x.customer, {"date": x.posting_date}, {"money": x.grand_total, "currency": x.currency},
				{"link": ["Purchase Invoice", x.inter_company_invoice_reference]} if x.inter_company_invoice_reference else {"text": _("Not booked"), "tone": "orange"}]} for x in g.ic],
			"empty": _("No inter-company invoices.")}
	if tab in ("pl", "bs"):
		from hipersign_trading.group import consolidate

		try:
			c = consolidate(today(), g.cur)
		except Exception:
			frappe.log_error(title="Hipersign: consolidation")
			c = {"members": [], "lines": {}, "elim": {}, "notes": [_("The consolidation could not be built — sync the trial balances first.")]}
		rep = "Profit and Loss" if tab == "pl" else "Balance Sheet"
		mems = [m["member"] for m in c["members"]]
		keys = sorted([k for k in c["lines"] if k[0] == rep], key=lambda k: (["Income", "Expense", "Asset", "Liability", "Equity"].index(k[1]) if k[1] in ("Income", "Expense", "Asset", "Liability", "Equity") else 9, k[2]))
		sign = -1 if rep == "Profit and Loss" else 1
		rows, last = [], None
		for k in keys:
			if k[1] != last:
				rows.append({"cls": "hsx-grp-row", "cells": [{"main": _(k[1])}] + [""] * (len(mems) + 2)})
				last = k[1]
			vals = [flt(c["lines"][k].get(m)) for m in mems]
			el = flt(c["elim"].get(k))
			s = -1 if k[1] in ("Liability", "Equity") else sign
			rows.append({"cells": [k[2]] + [{"money": v * s} if v else "—" for v in vals] + [{"money": el * s} if el else "—", {"money": (sum(vals) + el) * s}]})
		return {"title": (_("Consolidated profit & loss") if tab == "pl" else _("Consolidated balance sheet")) + f" — {g.cur}",
			"cols": [{"label": _("Line")}] + [{"label": frappe.get_cached_value("Company", m, "abbr") or m, "cls": "num"} for m in mems] + [{"label": _("Eliminations"), "cls": "num"}, {"label": _("Group"), "cls": "num"}],
			"rows": rows, "empty": " ".join(c.get("notes") or []) or _("No trial balances synced yet."),
			"actions": [{"label": _("Full consolidation report"), "route": ["query-report", "Hipersign Group Consolidation"]}]}
	if tab == "books":
		return {"cols": [{"label": _("Company")}, {"label": _("Abbreviation")}, {"label": _("Currency")}, {"label": _("Country")}, {"label": _("Accounts"), "cls": "num"}, {"label": _("Parent")}],
			"rows": [{"dt": "Company", "name": c.name, "cells": [{"main": c.name}, {"code": c.abbr}, c.default_currency, _(c.country or ""), frappe.db.count("Account", {"company": c.name}),
				c.parent_company or "—"]} for c in _companies()]}
	return {"cols": [], "rows": []}
