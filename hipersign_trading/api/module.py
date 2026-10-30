"""v1.6.0: module pages — the prototype's page per module: KPI row, tabs, filter chips and a list whose rows open the
record panel. The page follows the top bar's scope (group, country or company) and period.

get_module(key) returns the header, KPIs and tabs; get_rows(key, tab, chip, …) returns one tab's list (or the CRM
board). Everything is read with the user's own permissions (frappe.get_list).
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, today

from hipersign_trading.api.home import period_range
from hipersign_trading.api.ui import get_period, scope_companies

MODULES = ("sales", "crm", "purchasing", "imports", "receiving", "lc", "dispatch", "finance", "stock", "vat", "exports", "accounts", "codocs", "assets", "hr", "kyc", "tax", "group")
MORE = ("exports", "accounts", "codocs", "assets")
PEOPLE = ("hr", "kyc", "tax", "group")


def _scope():
	cos = scope_companies()
	start, end, label = period_range(get_period())
	cur = frappe.get_cached_value("Company", cos[0], "default_currency") if cos else "AED"
	return cos, start, end, label, cur


def _fields(doctype, fields):
	"""The fields the doctype has (custom fields may be missing on an older site); a missing one reads as empty."""
	meta = frappe.get_meta(doctype)
	std = {"name", "docstatus", "owner", "creation", "modified"}
	return [f for f in fields if f in std or meta.has_field(f)]


def _perm(doctype):
	return bool(frappe.has_permission(doctype, "read"))


def _sum(doctype, field, filters, fn=None):
	"""Sum a field (or fn(row)) over the records the user may read. Frappe 16 refuses SQL functions in get_list fields,
	so the rows are read and added up here."""
	if not _perm(doctype):
		return 0
	fields = [field] if not fn else field
	rows = frappe.get_list(doctype, filters=filters, fields=fields, limit_page_length=0)
	return sum(flt(fn(r)) if fn else flt(r.get(field)) for r in rows)


def _count(doctype, filters):
	return frappe.db.count(doctype, filters) if _perm(doctype) else 0


def kpi(label, value, sub="", tone="blue", icon=None, money=False, currency=None, route=None, tab=None, chip=None):
	return {"label": label, "value": value, "sub": sub, "tone": tone, "icon": icon, "money": money, "currency": currency,
		"route": route, "tab": tab, "chip": chip}


# ---------------------------------------------------------------- Quotations & Orders
SO_CHIPS = [("all", "All"), ("approval", "Awaiting approval"), ("deliver", "To deliver"), ("bill", "To bill"), ("completed", "Completed"), ("draft", "Draft")]
QT_CHIPS = [("all", "All"), ("open", "Open"), ("ordered", "Ordered"), ("lost", "Lost"), ("expired", "Expired"), ("draft", "Draft")]


def sales_module():
	cos, start, end, label, cur = _scope()
	co = ["in", cos]
	inv = {"company": co, "docstatus": 1, "posting_date": ["between", [start, end]]}
	sales = _sum("Sales Invoice", "base_net_total", inv)
	n_inv = _count("Sales Invoice", dict(inv, is_return=0))
	open_so = {"company": co, "docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Bill", "To Deliver"]]}
	open_val = _sum("Sales Order", ["base_grand_total", "per_billed"], open_so, lambda r: flt(r.base_grand_total) * (100 - flt(r.per_billed)) / 100)
	to_deliver = _count("Sales Order", {"company": co, "docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]})
	waiting = _count("Sales Order", {"company": co, "docstatus": 0, "workflow_state": ["like", "Pending%"]}) if frappe.get_meta("Sales Order").has_field("workflow_state") else 0
	q_period = {"company": co, "docstatus": 1, "transaction_date": ["between", [add_days(end, -90), end]]}
	q_total = _count("Quotation", q_period)
	q_ordered = _count("Quotation", dict(q_period, status="Ordered"))
	q_open = _count("Quotation", {"company": co, "docstatus": 1, "status": ["in", ["Open", "Replied", "Partially Ordered"]]})
	over = _over_limit(cos)
	return {
		"title": _("Quotations & Orders"),
		"desc": _("Manage customer orders, agreed pricing and fulfilment. Discounts, margins below landed cost and credit limits are checked before an order is confirmed."),
		"new": [{"label": _("New quotation"), "doctype": "Quotation"}, {"label": _("New sales order"), "doctype": "Sales Order", "primary": 1}],
		"kpis": [
			kpi(_("Sales — {0}").format(label), sales, _("{0} invoices, net of VAT").format(n_inv), "blue", "chart-column", True, cur, ["List", "Sales Invoice"]),
			kpi(_("Open orders (incl. VAT)"), open_val, _("Not yet invoiced"), "violet", "list", True, cur, tab="orders", chip="bill"),
			kpi(_("Orders to deliver"), to_deliver, _("Approved, stock to dispatch"), "blue", "truck", tab="orders", chip="deliver"),
			kpi(_("Awaiting approval"), waiting, _("Discount, margin or credit"), "amber", "inbox", tab="orders", chip="approval"),
			kpi(_("Quotation conversion"), f"{round(q_ordered / q_total * 100) if q_total else 0}%", _("{0} quotations open").format(q_open), "green", "trending-up", tab="quotes", chip="open"),
			kpi(_("Customers over limit"), len(over), _("Exposure above credit limit"), "red", "triangle-alert", tab="credit", chip="over"),
		],
		"tabs": [
			{"key": "orders", "label": _("Sales orders"), "chips": [[k, _(v)] for k, v in SO_CHIPS]},
			{"key": "quotes", "label": _("Quotations"), "chips": [[k, _(v)] for k, v in QT_CHIPS]},
			{"key": "credit", "label": _("Customers & credit"), "chips": [["all", _("All")], ["over", _("Over limit")], ["overdue", _("Overdue")]]},
			{"key": "pricing", "label": _("Price lists & pricing rules"), "chips": [["lists", _("Price lists")], ["rules", _("Pricing rules")]]},
		],
	}


def _items_text(doctype, names):
	if not names:
		return {}
	child = {"Sales Order": "Sales Order Item", "Quotation": "Quotation Item"}[doctype]
	rows = frappe.get_all(child, filters={"parent": ["in", names]}, fields=["parent", "item_name", "qty"], order_by="idx asc")
	out = {}
	for r in rows:
		out.setdefault(r.parent, []).append(f"{flt(r.qty):g} × {r.item_name}")
	return {k: v[:2] + ([_("+{0} more").format(len(v) - 2)] if len(v) > 2 else []) for k, v in out.items()}


def sales_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	co = ["in", cos]
	if tab == "orders":
		f = {"company": co, "docstatus": ["<", 2]}
		f.update({"approval": {"docstatus": 0, "workflow_state": ["like", "Pending%"]}, "deliver": {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]},
			"bill": {"docstatus": 1, "status": ["in", ["To Bill", "To Deliver and Bill"]]}, "completed": {"docstatus": 1, "status": ["in", ["Completed", "Closed"]]},
			"draft": {"docstatus": 0}}.get(chip, {}))
		if chip == "draft" and frappe.get_meta("Sales Order").has_field("workflow_state"):
			f["workflow_state"] = ["not like", "Pending%"]
		or_f = [["customer_name", "like", f"%{q}%"], ["name", "like", f"%{q}%"], ["po_no", "like", f"%{q}%"]] if q else None
		rows = frappe.get_list("Sales Order", filters=f, or_filters=or_f, fields=_fields("Sales Order", ["name", "customer", "customer_name", "customer_group", "po_no",
			"transaction_date", "delivery_date", "per_delivered", "status", "docstatus", "grand_total", "currency", "workflow_state", "hs_is_export"]),
			order_by="transaction_date desc, creation desc", limit=200)
		items = _items_text("Sales Order", [r.name for r in rows])
		return {"cols": [{"label": _("SO No.")}, {"label": _("Customer")}, {"label": _("Items")}, {"label": _("Order date")}, {"label": _("Delivery date")},
			{"label": _("Delivered")}, {"label": _("Status")}, {"label": _("Total"), "cls": "num"}],
			"rows": [{"dt": "Sales Order", "name": r.name, "cells": [
				{"code": r.name}, {"main": r.customer_name, "sub": " · ".join(x for x in [_("Export") if cint(r.hs_is_export) else r.customer_group, r.po_no] if x)},
				{"lines": items.get(r.name, [])}, {"date": r.transaction_date}, {"date": r.delivery_date},
				{"bar": flt(r.per_delivered)} if r.docstatus == 1 else "—", {"pill": _status(r)}, {"money": r.grand_total, "currency": r.currency}]} for r in rows]}
	if tab == "quotes":
		f = {"company": co, "docstatus": ["<", 2]}
		f.update({"open": {"docstatus": 1, "status": ["in", ["Open", "Replied", "Partially Ordered"]]}, "ordered": {"docstatus": 1, "status": "Ordered"},
			"lost": {"docstatus": 1, "status": "Lost"}, "expired": {"status": "Expired"}, "draft": {"docstatus": 0}}.get(chip, {}))
		or_f = [["customer_name", "like", f"%{q}%"], ["name", "like", f"%{q}%"], ["party_name", "like", f"%{q}%"]] if q else None
		rows = frappe.get_list("Quotation", filters=f, or_filters=or_f, fields=_fields("Quotation", ["name", "party_name", "customer_name", "quotation_to",
			"transaction_date", "valid_till", "status", "docstatus", "grand_total", "currency", "hs_subject"]), order_by="transaction_date desc, creation desc", limit=200)
		items = _items_text("Quotation", [r.name for r in rows])
		return {"cols": [{"label": _("Quotation")}, {"label": _("Customer / lead")}, {"label": _("Items")}, {"label": _("Date")}, {"label": _("Valid till")},
			{"label": _("Status")}, {"label": _("Value"), "cls": "num"}],
			"rows": [{"dt": "Quotation", "name": r.name, "cells": [
				{"code": r.name}, {"main": r.customer_name or r.party_name, "sub": " · ".join(x for x in [_(r.quotation_to), r.hs_subject] if x)},
				{"lines": items.get(r.name, [])}, {"date": r.transaction_date},
				{"date": r.valid_till, "late": bool(r.valid_till and getdate(r.valid_till) < getdate(today()) and r.status in ("Open", "Replied"))},
				{"pill": _status(r)}, {"money": r.grand_total, "currency": r.currency}]} for r in rows]}
	if tab == "credit":
		return _credit_rows(cos, chip, q)
	if tab == "pricing":
		if chip == "rules":
			rows = frappe.get_list("Pricing Rule", filters={"selling": 1, "disable": 0}, fields=["name", "title", "applicable_for", "customer", "customer_group",
				"apply_on", "rate_or_discount", "discount_percentage", "rate", "valid_from", "valid_upto", "priority"], order_by="modified desc", limit=100) if _perm("Pricing Rule") else []
			return {"cols": [{"label": _("Rule")}, {"label": _("For")}, {"label": _("Applies to")}, {"label": _("Discount / rate")}, {"label": _("Valid")}],
				"rows": [{"dt": "Pricing Rule", "name": r.name, "cells": [{"main": r.title or r.name}, {"main": r.customer or r.customer_group or _("Everyone"), "sub": _(r.applicable_for or "")},
					_(r.apply_on), f"{flt(r.discount_percentage):g}%" if r.rate_or_discount == "Discount Percentage" else {"money": r.rate},
					" – ".join(x for x in [frappe.utils.formatdate(r.valid_from), frappe.utils.formatdate(r.valid_upto)] if x) or _("Always")]} for r in rows]}
		rows = frappe.get_list("Price List", filters={"selling": 1}, fields=["name", "currency", "enabled"], order_by="name asc") if _perm("Price List") else []
		counts = {}
		for r in frappe.get_all("Item Price", filters={"price_list": ["in", [x.name for x in rows] or [""]]}, pluck="price_list"):
			counts[r] = counts.get(r, 0) + 1
		return {"cols": [{"label": _("Price list")}, {"label": _("Currency")}, {"label": _("Items priced"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Price List", "name": r.name, "cells": [{"main": r.name}, r.currency, counts.get(r.name, 0), {"pill": _("Enabled") if r.enabled else _("Disabled"), "tone": "green" if r.enabled else "grey"}]} for r in rows]}
	return {"cols": [], "rows": []}


def _status(r):
	if r.docstatus == 0:
		ws = r.get("workflow_state")
		return ws if ws and ws.startswith("Pending") else "Draft"
	if r.docstatus == 2:
		return "Cancelled"
	return r.status


def _over_limit(cos):
	if not (_perm("Customer") and _perm("Sales Invoice")):
		return []
	out = []
	limits = frappe.get_all("Customer Credit Limit", filters={"company": ["in", cos], "credit_limit": [">", 0], "parenttype": "Customer"},
		fields=["parent", "company", "credit_limit"])
	if not limits:
		return []
	bal = {}
	for r in frappe.get_all("Sales Invoice", filters={"docstatus": 1, "company": ["in", cos], "customer": ["in", [l.parent for l in limits]], "outstanding_amount": ["!=", 0]},
			fields=["customer", "company", "outstanding_amount", "conversion_rate"]):
		bal[(r.customer, r.company)] = bal.get((r.customer, r.company), 0) + flt(r.outstanding_amount) * flt(r.conversion_rate or 1)
	for l in limits:
		if bal.get((l.parent, l.company), 0) > flt(l.credit_limit):
			out.append(l.parent)
	return out


def _credit_rows(cos, chip, q):
	if not _perm("Customer"):
		return {"cols": [], "rows": []}
	f = {"disabled": 0}
	if q:
		f["customer_name"] = ["like", f"%{q}%"]
	custs = frappe.get_list("Customer", filters=f, fields=_fields("Customer", ["name", "customer_name", "customer_group", "payment_terms", "hs_kyc_status"]),
		order_by="customer_name asc", limit=300)
	names = [c.name for c in custs] or [""]
	limits = {}
	for l in frappe.get_all("Customer Credit Limit", filters={"parent": ["in", names], "company": ["in", cos], "parenttype": "Customer"}, fields=["parent", "credit_limit"]):
		limits[l.parent] = limits.get(l.parent, 0) + flt(l.credit_limit)
	out, overdue = {}, {}
	if _perm("Sales Invoice"):
		for r in frappe.get_all("Sales Invoice", filters={"docstatus": 1, "company": ["in", cos], "customer": ["in", names], "outstanding_amount": ["!=", 0]},
				fields=["customer", "outstanding_amount", "conversion_rate", "due_date"]):
			r.o = flt(r.outstanding_amount) * flt(r.conversion_rate or 1)
			out[r.customer] = out.get(r.customer, 0) + flt(r.o)
			if r.due_date and getdate(r.due_date) < getdate(today()) and flt(r.o) > 0:
				overdue[r.customer] = overdue.get(r.customer, 0) + flt(r.o)
	rows = []
	for c in custs:
		lim, o = limits.get(c.name, 0), out.get(c.name, 0)
		if chip == "over" and not (lim and o > lim):
			continue
		if chip == "overdue" and not overdue.get(c.name):
			continue
		if chip == "all" and not (lim or o):
			continue
		rows.append({"dt": "Customer", "name": c.name, "cells": [{"main": c.customer_name, "sub": c.customer_group}, c.payment_terms or "—",
			{"money": lim} if lim else _("No limit"), {"money": o}, {"money": lim - o, "neg": lim and o > lim} if lim else "—",
			{"money": overdue.get(c.name, 0), "neg": bool(overdue.get(c.name))} if overdue.get(c.name) else "—",
			{"pill": _(c.hs_kyc_status), "tone": {"Verified": "green", "Pending": "orange", "Expired": "red", "Blocked": "red"}.get(c.hs_kyc_status, "grey")} if c.hs_kyc_status else "—"]})
	rows.sort(key=lambda r: -flt(r["cells"][3]["money"]))
	return {"cols": [{"label": _("Customer")}, {"label": _("Terms")}, {"label": _("Credit limit"), "cls": "num"}, {"label": _("Outstanding"), "cls": "num"},
		{"label": _("Available"), "cls": "num"}, {"label": _("Overdue"), "cls": "num"}, {"label": _("KYC")}], "rows": rows}


# ---------------------------------------------------------------- CRM & Leads
def _leads(filters=None, owner=None, source=None):
	f = dict(filters or {})
	if owner == "mine":
		f["lead_owner"] = frappe.session.user
	elif owner:
		f["lead_owner"] = owner
	src = "utm_source" if frappe.get_meta("Lead").has_field("utm_source") else "source"
	if source:
		f[src] = source
	return frappe.get_list("Lead", filters=f, fields=["name", "company_name", "lead_name", "lead_owner", f"{src} as source", "hs_pipeline_stage as stage",
		"hs_estimated_value as value", "hs_probability as prob", "hs_next_follow_up as follow", "hs_next_action as action", "hs_interested_in as interest",
		"hs_expected_close as close", "modified", "mobile_no", "hs_lost_reason as lost_reason"], order_by="modified desc", limit=500) if _perm("Lead") else []


def crm_module(owner=None, source=None):
	from hipersign_trading.api.crm import STAGES

	cos, start, end, label, cur = _scope()
	leads = _leads(owner=owner, source=source)
	open_ = [l for l in leads if (l.stage or "New") in STAGES]
	t = getdate(today())
	due = [l for l in open_ if l.follow and getdate(l.follow) <= t]
	overdue = [l for l in due if getdate(l.follow) < t]
	won_month = [l for l in leads if l.stage == "Won" and getdate(l.modified) >= start]
	closed = [l for l in leads if l.stage in ("Won", "Lost") and getdate(l.modified) >= add_months(t, -3)]
	won = [l for l in closed if l.stage == "Won"]
	return {
		"title": _("CRM & Leads"),
		"desc": _("Capture every enquiry, follow it up on time and turn it into quotations and orders — one pipeline for the whole sales team."),
		"new": [{"label": _("New lead"), "doctype": "Lead", "primary": 1}],
		"kpis": [
			kpi(_("Open leads"), len(open_), _("{0} pipeline value").format(_fmt(sum(flt(l.value) for l in open_), cur)), "blue", "users", tab="pipeline"),
			kpi(_("Weighted pipeline"), sum(flt(l.value) * flt(l.prob) / 100 for l in open_), _("Value × stage probability"), "violet", "trending-up", True, cur, tab="pipeline"),
			kpi(_("Follow-ups due"), len(due), _("{0} overdue · {1} today").format(len(overdue), len(due) - len(overdue)), "red", "clock", tab="follow"),
			kpi(_("Won — {0}").format(label), sum(flt(l.value) for l in won_month), _("{0} leads converted").format(len(won_month)), "green", "check", True, cur, tab="leads", chip="won"),
			kpi(_("Win rate"), f"{round(len(won) / len(closed) * 100) if closed else 0}%", _("{0} leads closed in 3 months").format(len(closed)), "navy", "chart-column", tab="sources"),
		],
		"tabs": [
			{"key": "pipeline", "label": _("Pipeline"), "chips": []},
			{"key": "leads", "label": _("All leads"), "chips": [["open", _("Open")], ["won", _("Won")], ["lost", _("Lost")], ["all", _("All")]]},
			{"key": "follow", "label": _("Follow-ups ({0})").format(len(due)), "chips": []},
			{"key": "sources", "label": _("Sources & performance"), "chips": []},
		],
		"filters": {"owners": _owners(), "sources": _sources()},
		"note": _("Drag a card to move it to another stage, or open it to log a call, meeting or WhatsApp. Won and Lost show the last two months."),
	}


def _fmt(v, cur):
	"""AED 616.5K — the prototype's compact amounts."""
	v = flt(v)
	for n, u in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
		if abs(v) >= n:
			return f"{cur} {v / n:.1f}".rstrip("0").rstrip(".") + u
	return f"{cur} {v:,.0f}"


def _owners():
	users = frappe.get_all("Lead", filters={"lead_owner": ["is", "set"]}, pluck="lead_owner", distinct=True) if _perm("Lead") else []
	return [[u, frappe.utils.get_fullname(u)] for u in users]


def _sources():
	dt = "UTM Source" if frappe.db.exists("DocType", "UTM Source") else "Lead Source"
	return frappe.get_all(dt, pluck="name", order_by="name asc")


def _initials(user):
	name = frappe.utils.get_fullname(user) if user else ""
	return "".join(p[0] for p in name.split()[:2]).upper()


def crm_rows(tab, chip, q=None, owner=None, source=None):
	from hipersign_trading.api.crm import STAGES

	leads = _leads(owner=owner, source=source)
	if q:
		ql = q.lower()
		leads = [l for l in leads if ql in (l.company_name or "").lower() or ql in (l.lead_name or "").lower() or ql in (l.interest or "").lower()]
	t = getdate(today())
	card = lambda l: {"dt": "Lead", "name": l.name, "title": l.company_name or l.lead_name, "interest": l.interest, "value": flt(l.value),
		"follow": str(l.follow) if l.follow else None, "overdue": bool(l.follow and getdate(l.follow) < t and (l.stage or "New") in STAGES),
		"source": l.source, "owner": _initials(l.lead_owner), "owner_name": frappe.utils.get_fullname(l.lead_owner) if l.lead_owner else "", "stage": l.stage or "New"}
	if tab == "pipeline":
		cols = []
		for s in list(STAGES) + ["Won", "Lost"]:
			ls = [l for l in leads if (l.stage or "New") == s and (s not in ("Won", "Lost") or getdate(l.modified) >= add_months(t, -2))]
			ls.sort(key=lambda l: (getdate(l.follow) if l.follow else getdate("2999-12-31")))
			cols.append({"stage": s, "label": _(s), "count": len(ls), "value": sum(flt(l.value) for l in ls), "cards": [card(l) for l in ls]})
		return {"board": cols}
	if tab == "follow":
		rows = sorted([l for l in leads if l.follow and (l.stage or "New") in STAGES and getdate(l.follow) <= add_days(t, 7)], key=lambda l: getdate(l.follow))
		return {"cols": [{"label": _("Follow up")}, {"label": _("Lead")}, {"label": _("Next action")}, {"label": _("Stage")}, {"label": _("Owner")}, {"label": _("Value"), "cls": "num"}],
			"rows": [{"dt": "Lead", "name": l.name, "cells": [{"date": l.follow, "late": getdate(l.follow) < t}, {"main": l.company_name or l.lead_name, "sub": l.mobile_no},
				l.action or l.interest or "—", {"pill": _(l.stage or "New")}, frappe.utils.get_fullname(l.lead_owner) if l.lead_owner else "—", {"money": l.value}]} for l in rows]}
	if tab == "sources":
		by = {}
		for l in leads:
			k = l.source or _("Not set")
			b = by.setdefault(k, {"n": 0, "open": 0, "won": 0, "lost": 0, "won_v": 0})
			b["n"] += 1
			if (l.stage or "New") in STAGES:
				b["open"] += flt(l.value)
			elif l.stage == "Won":
				b["won"] += 1
				b["won_v"] += flt(l.value)
			elif l.stage == "Lost":
				b["lost"] += 1
		rows = sorted(by.items(), key=lambda kv: -kv[1]["n"])
		return {"cols": [{"label": _("Source")}, {"label": _("Leads"), "cls": "num"}, {"label": _("Open pipeline"), "cls": "num"}, {"label": _("Won"), "cls": "num"},
			{"label": _("Won value"), "cls": "num"}, {"label": _("Lost"), "cls": "num"}, {"label": _("Win rate"), "cls": "num"}],
			"rows": [{"cells": [{"main": k}, v["n"], {"money": v["open"]}, v["won"], {"money": v["won_v"]}, v["lost"],
				f"{round(v['won'] / (v['won'] + v['lost']) * 100)}%" if v["won"] + v["lost"] else "—"]} for k, v in rows]}
	sel = {"open": lambda l: (l.stage or "New") in STAGES, "won": lambda l: l.stage == "Won", "lost": lambda l: l.stage == "Lost"}.get(chip, lambda l: True)
	rows = [l for l in leads if sel(l)]
	return {"cols": [{"label": _("Lead")}, {"label": _("Interested in")}, {"label": _("Stage")}, {"label": _("Source")}, {"label": _("Owner")},
		{"label": _("Next follow-up")}, {"label": _("Value"), "cls": "num"}],
		"rows": [{"dt": "Lead", "name": l.name, "cells": [{"main": l.company_name or l.lead_name, "sub": l.lead_name if l.company_name else ""}, l.interest or "—",
			{"pill": _(l.stage or "New")}, l.source or "—", frappe.utils.get_fullname(l.lead_owner) if l.lead_owner else "—",
			{"date": l.follow, "late": bool(l.follow and getdate(l.follow) < t and (l.stage or "New") in STAGES)} if l.follow else "—", {"money": l.value}]} for l in rows]}


# ---------------------------------------------------------------- API
@frappe.whitelist()
def get_module(key, owner=None, source=None):
	if key in MORE:
		from hipersign_trading.api import module_more

		return getattr(module_more, key + "_module")()
	if key in PEOPLE:
		from hipersign_trading.api import module_people

		return getattr(module_people, key + "_module")()
	if key == "sales":
		return sales_module()
	if key == "crm":
		return crm_module(owner or None, source or None)
	if key == "purchasing":
		from hipersign_trading.api.module_buy import purchasing_module

		return purchasing_module()
	if key == "imports":
		from hipersign_trading.api.module_buy import imports_module

		return imports_module()
	if key == "receiving":
		from hipersign_trading.api.module_buy import receiving_module

		return receiving_module()
	if key == "lc":
		from hipersign_trading.api.module_buy import lc_module

		return lc_module()
	if key == "dispatch":
		from hipersign_trading.api.module_buy import dispatch_module

		return dispatch_module()
	if key == "finance":
		from hipersign_trading.api.module_buy import finance_module

		return finance_module()
	if key == "stock":
		from hipersign_trading.api.module_ops import stock_module

		return stock_module()
	if key == "vat":
		from hipersign_trading.api.module_ops import vat_module

		return vat_module()
	frappe.throw(_("Unknown module"))


@frappe.whitelist()
def get_rows(key, tab, chip=None, q=None, owner=None, source=None):
	if key in MORE:
		from hipersign_trading.api import module_more

		return getattr(module_more, key + "_rows")(tab, chip or None, q or None)
	if key in PEOPLE:
		from hipersign_trading.api import module_people

		return getattr(module_people, key + "_rows")(tab, chip or None, q or None)
	if key == "sales":
		return sales_rows(tab, chip or "all", q or None)
	if key == "crm":
		return crm_rows(tab, chip or "open", q or None, owner or None, source or None)
	if key == "purchasing":
		from hipersign_trading.api.module_buy import purchasing_rows

		return purchasing_rows(tab, chip or "all", q or None)
	if key == "imports":
		from hipersign_trading.api.module_buy import imports_rows

		return imports_rows(tab, chip or "open", q or None)
	if key == "receiving":
		from hipersign_trading.api.module_buy import receiving_rows

		return receiving_rows(tab, chip or "all", q or None)
	if key == "lc":
		from hipersign_trading.api.module_buy import lc_rows

		return lc_rows(tab, chip or "open", q or None)
	if key == "dispatch":
		from hipersign_trading.api.module_buy import dispatch_rows

		return dispatch_rows(tab, chip or "all", q or None)
	if key == "finance":
		from hipersign_trading.api.module_buy import finance_rows

		return finance_rows(tab, chip or "open", q or None)
	if key == "stock":
		from hipersign_trading.api.module_ops import stock_rows

		return stock_rows(tab, chip or "all", q or None)
	if key == "vat":
		from hipersign_trading.api.module_ops import vat_rows

		return vat_rows(tab, chip or "all", q or None)
	frappe.throw(_("Unknown module"))
