"""v1.5 — Hipersign Home: the prototype's management view on live ERPNext data.

Everything is computed from the ledger and the documents, per company in its own currency, then translated into the
group currency (profit at the average rate, balances at the closing rate). Companies on other sites (Hipersign Group
Member with a site URL) come from their last synced trial balance.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

from hipersign_trading.utils import money, settings


# ---------------------------------------------------------------- periods
def period_range(period):
	t = getdate(today())
	if period == "last_month":
		start = get_first_day(add_months(t, -1))
		return start, get_last_day(start), start.strftime("%b %Y")
	if period == "ytd":
		start = getdate(f"{t.year}-01-01")
		try:
			from erpnext.accounts.utils import get_fiscal_year

			start = getdate(get_fiscal_year(t)[1])
		except Exception:
			pass
		return start, t, _("{0} to date").format(start.year)
	start = get_first_day(t)
	return start, t, _("{0} to date").format(t.strftime("%b %Y"))


def _companies(company=None, country=None):
	if company:
		return [company]
	f = {"is_group": 0}
	country = country or frappe.flags.get("hs_country")
	if country:
		f["country"] = country
	return frappe.get_all("Company", filters=f, pluck="name", order_by="creation asc")


# ---------------------------------------------------------------- ledger figures for one company
def ledger(company, start, end):
	acc = frappe.qb.DocType("Account")
	gl = frappe.qb.DocType("GL Entry")
	base = (frappe.qb.from_(gl).join(acc).on(acc.name == gl.account)
		.where((gl.company == company) & (gl.is_cancelled == 0)))

	def pl(cond):
		r = base.select(Sum(gl.debit - gl.credit)).where(cond).where((gl.posting_date >= start) & (gl.posting_date <= end)).run()
		return flt(r[0][0]) if r else 0.0

	def bal(cond):
		r = base.select(Sum(gl.debit - gl.credit)).where(cond).where(gl.posting_date <= end).run()
		return flt(r[0][0]) if r else 0.0

	revenue = -pl(acc.root_type == "Income")
	expenses = pl(acc.root_type == "Expense")
	cogs = pl((acc.root_type == "Expense") & (acc.account_type == "Cost of Goods Sold"))
	return {
		"revenue": revenue, "cogs": cogs, "gross": revenue - cogs, "opex": expenses - cogs, "profit": revenue - expenses,
		"cash": bal(acc.account_type.isin(["Bank", "Cash"])),
		"receivables": bal(acc.account_type == "Receivable"),
		"payables": -bal(acc.account_type == "Payable"),
		"stock": bal(acc.account_type == "Stock"),
	}


def intercompany_sales(company, start, end):
	si = frappe.qb.DocType("Sales Invoice")
	cu = frappe.qb.DocType("Customer")
	r = (frappe.qb.from_(si).join(cu).on(cu.name == si.customer).select(Sum(si.base_net_total))
		.where((si.company == company) & (si.docstatus == 1) & (cu.is_internal_customer == 1))
		.where((si.posting_date >= start) & (si.posting_date <= end))).run()
	return flt(r[0][0]) if r else 0.0


def group_view(period, company=None):
	"""The group block: totals and one row per company, in the group currency."""
	from hipersign_trading.group import average_rate, rate

	# a missing exchange rate is shown as a zero row, not as a pop-up for every month
	muted, frappe.flags.mute_messages = frappe.flags.mute_messages, True
	try:
		return _group_view(period, company, average_rate, rate)
	finally:
		frappe.flags.mute_messages = muted


def _group_view(period, company, average_rate, rate):
	gcur = settings().get("group_currency") or "AED"
	start, end, label = period_range(period)
	ystart, yend, _y = period_range("ytd")
	rows, tot = [], {k: 0.0 for k in ("revenue", "profit", "cash", "receivables", "payables", "stock", "ic")}
	for c in _companies(company):
		cur = frappe.get_cached_value("Company", c, "default_currency")
		y = ledger(c, ystart, yend)
		p = ledger(c, start, end) if (start, end) != (ystart, yend) else y
		av, cl = average_rate(cur, gcur, ystart, yend), rate(cur, gcur, yend)
		ic = intercompany_sales(c, ystart, yend)
		row = {
			"company": c, "currency": cur, "country": frappe.get_cached_value("Company", c, "country"),
			"role": frappe.get_cached_value("Company", c, "hs_group_role") if frappe.get_meta("Company").has_field("hs_group_role") else None,
			"revenue_local": y["revenue"], "revenue": y["revenue"] * av,
			"gross_margin": (y["gross"] / y["revenue"] * 100) if y["revenue"] else 0,
			"profit": y["profit"] * av, "cash": y["cash"] * cl,
			"period_revenue": p["revenue"] * av, "period_profit": p["profit"] * av,
		}
		rows.append(row)
		tot["revenue"] += row["revenue"]
		tot["ic"] += ic * av
		tot["profit"] += row["profit"]
		tot["cash"] += row["cash"]
		tot["receivables"] += y["receivables"] * cl
		tot["payables"] += y["payables"] * cl
		tot["stock"] += y["stock"] * cl
	# companies kept on other sites, from their last synced trial balance
	if not company and frappe.db.table_exists("Hipersign Group Member"):
		for m in frappe.get_all("Hipersign Group Member", filters={"active": 1, "company": ["in", ["", None]]}, fields=["name", "currency", "country"]):
			tb = frappe.db.get_value("Group Trial Balance", {"member": m.name}, "name", order_by="period_end desc")
			if not tb:
				continue
			t = frappe.get_doc("Group Trial Balance", tb)
			cur = t.currency or m.currency or gcur
			inc = -sum(flt(a.period_movement) for a in t.accounts if a.root_type == "Income")
			exp = sum(flt(a.period_movement) for a in t.accounts if a.root_type == "Expense")
			av, cl = average_rate(cur, gcur, t.year_start or ystart, t.period_end), rate(cur, gcur, t.period_end)
			row = {"company": m.name, "currency": cur, "country": m.country, "role": _("Synced {0}").format(frappe.format(t.period_end, "Date")),
				"revenue_local": inc, "revenue": inc * av, "gross_margin": 0, "profit": (inc - exp) * av, "cash": 0, "remote": 1}
			rows.append(row)
			tot["revenue"] += row["revenue"]
			tot["profit"] += row["profit"]
	tot["revenue_after_ic"] = tot["revenue"] - tot["ic"]
	return {"currency": gcur, "rows": rows, "totals": tot, "label": label}


# ---------------------------------------------------------------- the lifecycle strip and the KPI grid
def _count(dt, filters):
	try:
		return frappe.db.count(dt, filters)
	except Exception:
		return 0


def _sum(dt, field, filters):
	try:
		r = frappe.get_all(dt, filters=filters, fields=[{"SUM": field, "as": "s"}])
		return flt(r[0].s) if r else 0.0
	except Exception:
		return 0.0


def _co(f, company):
	if company:
		f = dict(f, company=company)
	elif frappe.flags.get("hs_country"):
		f = dict(f, company=["in", _companies()])
	return f


def lifecycle(company, start, end):
	wh = frappe.get_all("Warehouse", filters={"company": company} if company else {}, pluck="name")
	stock_value = flt(frappe.db.sql("select sum(stock_value) from tabBin where warehouse in %s", [tuple(wh) or ("",)])[0][0]) if wh else 0
	low = 0
	for r in frappe.get_all("Item Reorder", fields=["parent", "warehouse", "warehouse_reorder_level"]):
		if r.warehouse in wh and flt(frappe.db.get_value("Bin", {"item_code": r.parent, "warehouse": r.warehouse}, "projected_qty")) <= flt(r.warehouse_reorder_level):
			low += 1
	open_po = _co({"docstatus": 1, "status": ["not in", ["Completed", "Closed", "Delivered"]], "per_received": ["<", 100]}, company)
	ar = _co({"docstatus": 1, "outstanding_amount": [">", 0]}, company)
	return [
		{"n": "01", "icon": "shopping-cart", "title": _("Supplier purchasing"), "big": _("{0} open POs").format(_count("Purchase Order", open_po)),
			"small": _sum("Purchase Order", "base_grand_total", open_po), "small_is_money": 1, "route": ["List", "Purchase Order"], "options": {"per_received": ["<", 100], "docstatus": 1}},
		{"n": "02", "icon": "ship", "title": _("Import & shipment"),
			"big": _("{0} shipments open").format(_count("Import Shipment", _co({"status": ["not in", ["Received at Warehouse"]]}, company))),
			"small": _("{0} at port / customs").format(_count("Import Shipment", _co({"status": ["in", ["Arrived at Port", "Under Customs Clearance"]]}, company))),
			"route": ["List", "Import Shipment"]},
		{"n": "03", "icon": "scan-line", "title": _("Goods receiving"),
			"big": _("{0} ready to receive").format(_count("Import Shipment", _co({"status": "Cleared"}, company))),
			"small": _("{0} receipts this month").format(_count("Purchase Receipt", _co({"docstatus": 1, "posting_date": [">=", get_first_day(today())]}, company))),
			"route": ["List", "Purchase Receipt"]},
		{"n": "04", "icon": "package", "title": _("Warehouse & inventory"), "big": stock_value, "big_is_money": 1,
			"small": _("{0} items low / out").format(low), "route": ["query-report", "Stock Projected Qty"]},
		{"n": "05", "icon": "tag", "title": _("Sales & orders"),
			"big": _("{0} orders to deliver").format(_count("Sales Order", _co({"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]}, company))),
			"small": _("{0} open").format(money(_sum("Sales Order", "base_grand_total", _co({"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]}, company)), precision=0)),
			"route": ["hipersign-orders"]},
		{"n": "06", "icon": "truck", "title": _("Dispatch & delivery"),
			"big": _("{0} notes not delivered").format(_count("Delivery Note", _co({"docstatus": 1, "hs_delivery_status": ["in", ["", "Ready to Dispatch", "Out for Delivery", "Failed"]]}, company))),
			"small": _("{0} out for delivery").format(_count("Delivery Note", _co({"docstatus": 1, "hs_delivery_status": "Out for Delivery"}, company))),
			"route": ["List", "Delivery Note"]},
		{"n": "07", "icon": "banknote", "title": _("Finance & visibility"), "big": _sum("Sales Invoice", "outstanding_amount", ar), "big_is_money": 1, "big_suffix": _("receivable"),
			"small": _("{0} overdue").format(money(_sum("Sales Invoice", "outstanding_amount", dict(ar, due_date=["<", today()])), precision=0)),
			"route": ["query-report", "Accounts Receivable"]},
	]


# v1.5.6 (SET-05): what a switched-off feature contributes to Home disappears with it
STAGE_FEATURE = {"02": "imports", "03": None}
KPI_FEATURE = {"Post-dated cheques in hand": "pdc", "Shipments in transit": "imports", "Export shipments": "exports", "Sales pipeline (CRM)": "crm"}


def _feature_filter(rows, key, mapping):
	from hipersign_trading.features import feature_on

	if key == "label":  # KPI labels are translated
		mapping = {_(k): v for k, v in mapping.items()}
	return [r for r in rows if not mapping.get(r.get(key)) or feature_on(mapping[r.get(key)])]


def kpis(company, start, end, label):
	cos = _companies(company)
	led = {"revenue": 0, "cogs": 0, "gross": 0, "opex": 0, "profit": 0, "cash": 0, "receivables": 0, "payables": 0, "stock": 0}
	for c in cos:
		for k, v in ledger(c, start, end).items():
			led[k] += v  # same-currency sites; the group block does the translation
	period = {"posting_date": ["between", [start, end]], "docstatus": 1}
	sales = _sum("Sales Invoice", "base_net_total", _co(period, company))
	n_inv = _count("Sales Invoice", _co(dict(period, is_return=0), company))
	purch = _sum("Purchase Order", "base_net_total", _co({"transaction_date": ["between", [start, end]], "docstatus": 1}, company))
	ar = _co({"docstatus": 1, "outstanding_amount": [">", 0]}, company)
	overdue = dict(ar, due_date=["<", today()])
	pay30 = _co({"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<=", add_days(today(), 30)]}, company)
	pdc = _co({"status": ["in", ["In Hand", "Deposited"]], "direction": "Received"}, company)
	target = flt(settings().get("target_margin")) or 20
	gm = (led["gross"] / led["revenue"] * 100) if led["revenue"] else 0
	nm = (led["profit"] / led["revenue"] * 100) if led["revenue"] else 0
	leads_open = {"hs_pipeline_stage": ["not in", ["Won", "Lost"]]} if frappe.get_meta("Lead").has_field("hs_pipeline_stage") else {}
	from hipersign_trading.api.approvals import pending

	appr = pending(company)
	return [
		{"label": _("Total sales (net)"), "icon": "tag", "value": sales, "money": 1, "sub": _("{0} · {1} invoices").format(label, n_inv), "tone": "blue", "route": ["List", "Sales Invoice"]},
		{"label": _("Total purchases"), "icon": "shopping-cart", "value": purch, "money": 1, "sub": _("{0} · orders placed").format(label), "tone": "violet", "route": ["List", "Purchase Order"]},
		{"label": _("Gross profit"), "icon": "trending-up", "value": led["gross"], "money": 1, "sub": _("{0}% margin after landed cost · target {1}%").format(round(gm, 1), round(target)), "tone": "green" if gm >= target else "amber", "route": ["query-report", "Gross Profit"]},
		{"label": _("Net profit (before tax)"), "icon": "chart", "value": led["profit"], "money": 1, "sub": _("{0}% net margin · after {1} expenses").format(round(nm, 1), money(led["opex"], precision=0)), "tone": "green" if led["profit"] >= 0 else "red", "route": ["query-report", "Profit and Loss Statement"]},
		{"label": _("Stock value"), "icon": "package", "value": led["stock"], "money": 1, "sub": _("Valued at landed cost"), "tone": "blue", "route": ["query-report", "Stock Projected Qty"]},
		{"label": _("Outstanding receivables"), "icon": "clock", "value": _sum("Sales Invoice", "outstanding_amount", ar), "money": 1, "sub": _("{0} open invoices").format(_count("Sales Invoice", ar)), "tone": "blue", "route": ["query-report", "Accounts Receivable"]},
		{"label": _("Overdue receivables"), "icon": "circle-alert", "value": _sum("Sales Invoice", "outstanding_amount", overdue), "money": 1, "sub": _("{0} past due").format(_count("Sales Invoice", overdue)), "tone": "red", "route": ["List", "Sales Invoice"], "options": {"status": "Overdue"}},
		{"label": _("Payables due ≤ 30 days"), "icon": "receipt", "value": _sum("Purchase Invoice", "outstanding_amount", pay30), "money": 1, "sub": _("Suppliers & service providers"), "tone": "amber", "route": ["query-report", "Accounts Payable"]},
		{"label": _("Cash & bank"), "icon": "banknote", "value": led["cash"], "money": 1, "sub": _("After receipts, payments, salaries & expenses"), "tone": "green", "route": ["query-report", "General Ledger"]},
		{"label": _("Post-dated cheques in hand"), "icon": "wallet", "value": _sum("Post Dated Cheque", "amount", pdc), "money": 1,
			"sub": _("{0} to deposit this week · {1} bounced").format(_count("Post Dated Cheque", dict(pdc, status="In Hand", cheque_date=["<=", add_days(today(), 7)])),
				_count("Post Dated Cheque", _co({"status": "Bounced"}, company))), "tone": "violet", "route": ["List", "Post Dated Cheque"]},
		{"label": _("Shipments in transit"), "icon": "ship", "value": _count("Import Shipment", _co({"status": ["in", ["Shipped", "In Transit", "Arrived at Port", "Under Customs Clearance", "Cleared"]]}, company)),
			"sub": _("{0} at port / customs / cleared").format(_count("Import Shipment", _co({"status": ["in", ["Arrived at Port", "Under Customs Clearance", "Cleared"]]}, company))), "tone": "blue", "route": ["List", "Import Shipment"]},
		{"label": _("Export shipments"), "icon": "globe", "value": _count("Export Shipment", _co({"status": ["!=", "Documents Complete"]}, company)),
			"sub": _("{0} awaiting proof of export (0% VAT)").format(_count("Export Shipment", _co({"status": ["in", ["Shipped", "Delivered"]], "proof_of_export_on": ["is", "not set"]}, company))), "tone": "blue", "route": ["List", "Export Shipment"]},
		{"label": _("Sales pipeline (CRM)"), "icon": "sparkles", "value": _sum("Lead", "hs_estimated_value", leads_open) if leads_open else 0, "money": 1,
			"sub": _("{0} open leads · {1} follow-ups due").format(_count("Lead", leads_open), _count("Lead", dict(leads_open, hs_next_follow_up=["<=", today()])) if leads_open else 0), "tone": "violet", "route": ["hipersign-crm"]},
		{"label": _("Open sales orders"), "icon": "list", "value": _sum("Sales Order", "base_grand_total", _co({"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]}, company)), "money": 1,
			"sub": _("{0} orders incl. VAT").format(_count("Sales Order", _co({"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]}, company))), "tone": "blue", "route": ["hipersign-orders"]},
		{"label": _("Pending approvals"), "icon": "inbox", "value": len(appr), "sub": _("POs, orders, payments, stock, exceptions"), "tone": "amber", "route": ["hipersign-approvals"]},
	]


def pl_block(company, start, end):
	led = {"revenue": 0, "cogs": 0, "gross": 0, "opex": 0, "profit": 0}
	for c in _companies(company):
		x = ledger(c, start, end)
		for k in led:
			led[k] += x[k]
	return led


def monthly(company):
	"""Sales vs purchases for the last 12 months (net, company currency)."""
	labels, sales, purchases = [], [], []
	t = get_first_day(today())
	for i in range(11, -1, -1):
		s = get_first_day(add_months(t, -i))
		e = get_last_day(s)
		labels.append(s.strftime("%b"))
		f = {"docstatus": 1, "posting_date": ["between", [s, e]]}
		sales.append(round(_sum("Sales Invoice", "base_net_total", _co(f, company)), 2))
		purchases.append(round(_sum("Purchase Invoice", "base_net_total", _co(f, company)), 2))
	return {"labels": labels, "sales": sales, "purchases": purchases}


def work_today(company):
	u = frappe.session.user
	rows = []

	def add(n, label, route, options=None):
		if n:
			rows.append({"n": n, "label": label, "route": route, "options": options or {}})

	add(_count("ToDo", {"allocated_to": u, "status": "Open"}), _("open to-dos for you"), ["List", "ToDo"], {"allocated_to": u, "status": "Open"})
	add(len(__import__("hipersign_trading.api.approvals", fromlist=["x"]).pending(company, mine=True)), _("approvals waiting for you"), ["hipersign-approvals"])
	add(_count("Notification Log", {"for_user": u, "read": 0}), _("unread notifications"), ["List", "Notification Log"])
	if frappe.get_meta("Lead").has_field("hs_next_follow_up"):
		add(_count("Lead", {"hs_next_follow_up": ["<=", today()], "hs_pipeline_stage": ["not in", ["Won", "Lost"]]}), _("lead follow-ups due"), ["List", "Lead"])
	add(_count("Post Dated Cheque", _co({"status": "In Hand", "direction": "Received", "cheque_date": ["<=", today()]}, company)), _("cheques ready to deposit"), ["List", "Post Dated Cheque"], {"status": "In Hand"})
	add(_count("Delivery Note", _co({"docstatus": 1, "per_billed": ["<", 100], "is_return": 0}, company)), _("deliveries to invoice"), ["List", "Delivery Note"], {"per_billed": ["<", 100], "docstatus": 1})
	if frappe.db.table_exists("Bank Transaction"):
		add(_count("Bank Transaction", _co({"docstatus": 1, "status": "Unreconciled"}, company)), _("bank lines to reconcile"), ["bank-reconciliation-tool"] if frappe.db.exists("Page", "bank-reconciliation-tool") else ["Form", "Bank Reconciliation Tool"])
	add(_count("Import Shipment", _co({"status": "Cleared"}, company)), _("shipments to receive"), ["List", "Import Shipment"], {"status": "Cleared"})
	add(_count("Warranty Claim", {"status": "Open"}), _("open warranty claims"), ["List", "Warranty Claim"], {"status": "Open"})
	if frappe.db.table_exists("Leave Application"):
		add(_count("Leave Application", _co({"status": "Open", "docstatus": 0}, company)), _("leave requests"), ["List", "Leave Application"], {"status": "Open"})
	add(_count("ToDo", {"status": "Open", "reference_type": ["in", ["Company Document", "Company Deadline"]]}), _("compliance to-dos"), ["List", "ToDo"], {"status": "Open"})
	return rows


def top_alerts(company):
	from hipersign_trading.alerts import can_see, evaluate

	al = [a for a in evaluate(company) if a["status"] == "Open" and can_see(a)]
	groups = {}
	for a in al:
		g = groups.setdefault(a["category"], {"category": a["category"], "count": 0, "high": 0, "top": None})
		g["count"] += 1
		g["high"] += 1 if a["severity"] == "High" else 0
		if not g["top"]:
			g["top"] = a
	out = sorted(groups.values(), key=lambda g: (-g["high"], -g["count"]))
	return {"total": len(al), "groups": out}


FINANCE_ROLES = {"System Manager", "Managing Director", "Accounts Manager", "Accounts User"}


def _route_ok(route):
	"""A figure is shown only to people who can open what it summarises (the prototype's figures by role)."""
	if not route:
		return True
	from hipersign_trading.utils import can_read

	if route[0] == "List":
		return can_read(route[1])
	if route[0] == "query-report":
		return frappe.db.exists("Report", route[1]) and frappe.get_cached_doc("Report", route[1]).is_permitted()
	if frappe.db.exists("Page", route[0]):
		return frappe.get_cached_doc("Page", route[0]).is_permitted()
	return True


def _group_on():
	from hipersign_trading.features import feature_on

	return feature_on("group")


@frappe.whitelist()
def get_home(period=None, company=None, country=None):
	"""v1.5.6: scope and period come from the top bar (the user's defaults) unless the page passes them."""
	from hipersign_trading.api.ui import get_period, get_scope

	if not period:
		period = get_period()
	if not company and not country:
		scope = get_scope()[0]
		if scope.startswith("company:"):
			company = scope.split(":", 1)[1]
		elif scope.startswith("country:"):
			country = scope.split(":", 1)[1]
	company = company or None
	if country and not company:
		cos = _companies(country=country)
		if len(cos) == 1:
			company, country = cos[0], None
	frappe.flags.hs_country = country if not company else None
	start, end, label = period_range(period)
	n_companies = len(_companies())
	scope_label = company or (_("{0} · {1} companies").format(_(country), n_companies) if country else _("Whole group"))
	finance = bool(FINANCE_ROLES & set(frappe.get_roles()))
	return {
		"period": {"key": period, "label": label, "start": str(start), "end": str(end)},
		"scope_label": scope_label,
		"company": company, "companies": _companies(), "currency": frappe.get_cached_value("Company", company or _companies()[0], "default_currency") if _companies() else "AED",
		"group": group_view(period, company) if finance and _group_on() and not company and (n_companies > 1 or frappe.db.count("Hipersign Group Member", {"active": 1}) > 1) else None,
		"lifecycle": _feature_filter([s for s in lifecycle(company, start, end) if _route_ok(s["route"])], "n", STAGE_FEATURE),
		"work": [w for w in work_today(company) if _route_ok(w["route"])],
		"alerts": top_alerts(company),
		"kpis": _feature_filter([k for k in kpis(company, start, end, label) if _route_ok(k.get("route"))], "label", KPI_FEATURE),
		"pl": pl_block(company, start, end) if finance else None,
		"monthly": monthly(company) if finance or _route_ok(["List", "Sales Invoice"]) else None,
		"target_margin": flt(settings().get("target_margin")) or 20,
	}
