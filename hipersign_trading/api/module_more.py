"""v1.7.0: the prototype's Exports & Re-exports, Accounting, Company Compliance and Fixed Assets pages.

Same shape as api/module.py (get_module / get_rows dispatch there). Read with the user's own permissions.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, date_diff, flt, formatdate, get_first_day, get_last_day, getdate, today  # noqa: F401

from hipersign_trading.api.module import _fields, _fmt, _perm, _scope, kpi

EXP_OPEN = ["Booked", "Packed", "Export Declaration", "Customs Cleared", "Shipped", "Delivered"]
EXP_COLS = [("booked", "Booked & packed", ["Booked", "Packed"]), ("customs", "Customs", ["Export Declaration", "Customs Cleared"]),
	("way", "On the way", ["Shipped", "Delivered"]), ("done", "Documents complete", ["Documents Complete"])]
EXP_TONE = {"Booked": "grey", "Packed": "orange", "Export Declaration": "orange", "Customs Cleared": "violet", "Shipped": "blue", "Delivered": "blue",
	"Documents Complete": "green"}


def _d(v):
	return formatdate(v, "dd MMM yyyy") if v else "—"


def _ok(dt):
	return frappe.db.table_exists(dt) and _perm(dt)


# ---------------------------------------------------------------- Exports & Re-exports
def _exports(cos, filters=None):
	if not _ok("Export Shipment"):
		return []
	f = {"company": ["in", cos]}
	f.update(filters or {})
	rows = frappe.get_list("Export Shipment", filters=f, fields=_fields("Export Shipment", ["name", "sales_order", "customer", "customer_name", "currency", "status", "mode",
		"incoterm", "forwarder", "port_of_loading", "destination", "etd", "eta", "proof_due_on", "proof_of_export_on", "bl_awb_cmr", "declaration_no",
		"re_export_of", "duty_refund_estimate", "duty_refund_status", "total_charges", "net_sales", "cost_of_goods", "gross_profit", "margin_pct", "modified"]),
		order_by="etd desc, modified desc", limit=300)
	if not rows:
		return rows
	so = {r.name: r for r in frappe.get_all("Sales Order", filters={"name": ["in", [x.sales_order for x in rows if x.sales_order] or [""]]},
		fields=["name", "grand_total", "currency", "base_grand_total"])}
	docs = {}
	for d in frappe.get_all("Shipment Document", filters={"parent": ["in", [x.name for x in rows]], "parenttype": "Export Shipment"}, fields=["parent", "required", "received"]):
		x = docs.setdefault(d.parent, [0, 0])
		if d.required:
			x[0] += 1
			x[1] += 1 if d.received else 0
	for r in rows:
		s = so.get(r.sales_order) or frappe._dict()
		r.value, r.ccy, r.base = flt(s.grand_total), s.currency or r.currency, flt(s.base_grand_total)
		need, got = docs.get(r.name, [0, 0])
		r.docs_pending = max(0, need - got)
	return rows


def exports_module():
	cos, start, end, label, cur = _scope()
	rows = _exports(cos)
	open_ = [r for r in rows if r.status in EXP_OPEN]
	customs = [r for r in rows if r.status in ("Packed", "Export Declaration")]
	way = [r for r in rows if r.status in ("Shipped", "Delivered")]
	proof = [r for r in rows if r.status in ("Shipped", "Delivered") and not r.get("proof_of_export_on")]
	sales = flt(frappe.db.sql("""select sum(base_net_total) from `tabSales Invoice` where docstatus=1 and is_return=0 and company in %s and posting_date between %s and %s
		and (coalesce(hs_zero_rated, 0) = 1 or customer in (select name from tabCustomer where hs_market='Export'))""", (tuple(cos), start, end))[0][0]) \
		if _perm("Sales Invoice") and frappe.get_meta("Sales Invoice").has_field("hs_zero_rated") else 0
	with_m = [r for r in rows if flt(r.get("net_sales"))]
	margin = (sum(flt(r.gross_profit) for r in with_m) / sum(flt(r.net_sales) for r in with_m) * 100) if with_m else None
	n_orders = len(_export_orders(cos))
	return {
		"title": _("Export & Re-export"),
		"desc": _("Book export shipments from confirmed orders, clear customs, keep the export documents, and protect 0% VAT with proof of export — for sea, air and land (GCC trucking)."),
		"new": [{"label": _("New export order"), "doctype": "Sales Order"}, {"label": _("New export shipment"), "doctype": "Export Shipment", "primary": 1}],
		"kpis": [
			kpi(_("Export sales"), sales, _("{0} · zero-rated").format(label), "blue", "globe", True, cur, tab="orders"),
			kpi(_("Open export shipments"), len(open_), _("{0} goods value").format(_fmt(sum(r.base for r in open_), cur)), "navy", "ship", tab="board"),
			kpi(_("Awaiting customs"), len(customs), _("Packed or declaration filed"), "amber", "flag", tab="board"),
			kpi(_("On the way"), len(way), _("Shipped or delivered"), "violet", "truck", tab="board"),
			kpi(_("Proof of export pending"), len(proof), _("Needed to support 0% VAT"), "red", "triangle-alert", tab="docs"),
			kpi(_("Export margin"), f"{margin:.1f}%" if margin is not None else "—", _("After landed cost and export charges"), "green", "trending-up", tab="costs"),
		],
		"tabs": [
			{"key": "board", "label": _("Shipment board"), "chips": []},
			{"key": "orders", "label": _("Export orders") + (f" ({n_orders})" if n_orders else ""), "chips": []},
			{"key": "docs", "label": _("Documents & VAT proof") + (f" ({len(proof)})" if proof else ""), "chips": []},
			{"key": "costs", "label": _("Costs & margin"), "chips": []},
			{"key": "reexports", "label": _("Re-exports"), "chips": []},
		],
		"default_tab": "board",
	}


def _export_orders(cos):
	if not _perm("Sales Order"):
		return []
	cond = "coalesce(so.hs_is_export, 0) = 1 or c.hs_market = 'Export'" if frappe.get_meta("Sales Order").has_field("hs_is_export") else "c.hs_market = 'Export'"
	return frappe.db.sql(f"""select so.name, so.customer, so.customer_name, so.transaction_date, so.delivery_date, so.grand_total, so.currency, so.status,
		so.per_delivered, so.per_billed, so.incoterm, c.hs_country_city from `tabSales Order` so join tabCustomer c on c.name = so.customer
		where so.docstatus = 1 and so.company in %s and ({cond}) order by so.transaction_date desc limit 200""", (tuple(cos),), as_dict=True)


def _route(r):
	return " → ".join(x for x in [r.port_of_loading, r.destination] if x) or "—"


def exports_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "board":
		rows = _exports(cos, {"modified": [">=", add_months(today(), -4)]})
		cols = []
		for key, title, sts in EXP_COLS:
			rs = [r for r in rows if r.status in sts]
			cards = []
			for r in rs:
				warn = []
				if r.docs_pending:
					warn.append(_("{0} documents pending").format(r.docs_pending) if r.docs_pending > 1 else _("1 document pending"))
				if r.status in ("Shipped", "Delivered") and not r.get("proof_of_export_on") and r.get("proof_due_on"):
					warn.append(_("Proof of export by {0}").format(formatdate(r.proof_due_on, "dd MMM")))
				cards.append({"dt": "Export Shipment", "name": r.name, "code": r.name, "pill": r.status, "title": r.customer_name or r.customer,
					"lines": [f"{_(r.mode or '')} · {_route(r)}", f"{frappe.format(r.value, {'fieldtype': 'Currency', 'options': r.ccy})} · ETA {formatdate(r.eta, 'dd MMM') if r.eta else '—'}"],
					"warn": " · ".join(warn)})
			cols.append({"key": key, "label": _(title), "count": len(rs), "cards": cards})
		allr = rows
		return {"kanban": cols, "kanban_cols": 4, "after": {"title": _("All export shipments"),
			"cols": [{"label": _("Shipment")}, {"label": _("Order / customer")}, {"label": _("Mode · ref.")}, {"label": _("Route")}, {"label": _("Incoterm")}, {"label": _("ETD")},
				{"label": _("Value"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Export Shipment", "name": r.name, "cells": [{"code": r.name}, {"main": r.sales_order or "—", "sub": r.customer_name or ""},
				{"main": _(r.mode or "—"), "sub": r.bl_awb_cmr or ""}, _route(r), r.incoterm or "—", {"date": r.etd}, {"money": r.value, "currency": r.ccy if r.ccy != cur else None},
				{"pill": r.status, "tone": EXP_TONE.get(r.status, "grey")}]} for r in allr]}}
	if tab == "orders":
		rows = _export_orders(cos)
		ship = {r.sales_order: r for r in _exports(cos)}
		return {"cols": [{"label": _("Order")}, {"label": _("Customer")}, {"label": _("Destination")}, {"label": _("Incoterm")}, {"label": _("Delivery")},
			{"label": _("Value"), "cls": "num"}, {"label": _("Delivered")}, {"label": _("Export shipment")}],
			"rows": [{"dt": "Sales Order", "name": r.name, "cells": [{"code": r.name}, {"main": r.customer_name}, r.hs_country_city or "—", r.incoterm or "—",
				{"date": r.delivery_date}, {"money": r.grand_total, "currency": r.currency if r.currency != cur else None}, {"bar": flt(r.per_delivered)},
				{"link": ["Export Shipment", ship[r.name].name], "pill": ship[r.name].status} if ship.get(r.name) else
				{"button": _("Book shipment"), "open": ["Export Shipment", "new"]} if False else {"text": _("Not booked"), "tone": "orange"}]} for r in rows],
			"empty": _("No export orders.")}
	if tab == "docs":
		rows = [r for r in _exports(cos) if r.status != "Booked"]
		return {"cols": [{"label": _("Shipment")}, {"label": _("Customer")}, {"label": _("Declaration")}, {"label": _("BL / AWB / CMR")}, {"label": _("Documents")},
			{"label": _("Proof due")}, {"label": _("Proof of export")}],
			"rows": [{"dt": "Export Shipment", "name": r.name, "cells": [{"code": r.name}, {"main": r.customer_name}, r.declaration_no or "—", r.bl_awb_cmr or "—",
				{"text": _("{0} pending").format(r.docs_pending), "tone": "orange"} if r.docs_pending else {"text": _("Complete"), "tone": "green"},
				{"date": r.get("proof_due_on"), "late": bool(r.get("proof_due_on") and getdate(r.proof_due_on) < t and not r.get("proof_of_export_on"))},
				{"pill": _("Received"), "tone": "green"} if r.get("proof_of_export_on") else {"pill": _("Pending"), "tone": "red" if r.status in ("Shipped", "Delivered") else "grey"}]}
				for r in rows], "empty": _("No shipments past booking yet.")}
	if tab == "costs":
		rows = _exports(cos)
		return {"cols": [{"label": _("Shipment")}, {"label": _("Customer")}, {"label": _("Net sales ({0})").format(cur), "cls": "num"}, {"label": _("Landed cost"), "cls": "num"},
			{"label": _("Export charges"), "cls": "num"}, {"label": _("Gross profit"), "cls": "num"}, {"label": _("Margin")}],
			"rows": [{"dt": "Export Shipment", "name": r.name, "cells": [{"code": r.name}, {"main": r.customer_name}, {"money": r.get("net_sales")}, {"money": r.get("cost_of_goods")},
				{"money": r.get("total_charges")}, {"money": r.get("gross_profit")},
				{"text": f"{flt(r.get('margin_pct')):.1f}%", "tone": "green" if flt(r.get("margin_pct")) >= 10 else "orange" if flt(r.get("margin_pct")) > 0 else "red"} if r.get("net_sales") else "—"]}
				for r in rows], "empty": _("No export shipments.")}
	if tab == "reexports":
		rows = [r for r in _exports(cos) if r.get("re_export_of")]
		return {"cols": [{"label": _("Shipment")}, {"label": _("Customer")}, {"label": _("Re-export of")}, {"label": _("Duty refund estimate"), "cls": "num"}, {"label": _("Refund status")}],
			"rows": [{"dt": "Export Shipment", "name": r.name, "cells": [{"code": r.name}, {"main": r.customer_name}, {"link": ["Import Shipment", r.re_export_of]},
				{"money": r.get("duty_refund_estimate")}, {"pill": _(r.get("duty_refund_status") or "Not claimed"), "tone": "orange"}]} for r in rows],
			"empty": _("No re-exports — set “Re-export of import” on an export shipment to claim the duty back.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Accounting
def _gl_sum(cos, frm, to, by="account"):
	return frappe.db.sql(f"""select gle.{by} k, sum(gle.debit) dr, sum(gle.credit) cr from `tabGL Entry` gle
		where gle.is_cancelled = 0 and gle.company in %s and gle.posting_date between %s and %s group by gle.{by}""", (tuple(cos), frm, to), as_dict=True)


def _opening(cos, before):
	return {r[0]: flt(r[1]) for r in frappe.db.sql("""select account, sum(debit - credit) from `tabGL Entry` where is_cancelled = 0 and company in %s
		and posting_date < %s group by account""", (tuple(cos), before))}


def accounts_module():
	cos, start, end, label, cur = _scope()
	if not _perm("GL Entry") and not _perm("Account"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	mv = _gl_sum(cos, start, end)
	dr, cr = sum(flt(r.dr) for r in mv), sum(flt(r.cr) for r in mv)
	ys = f"{getdate(today()).year}-01-01"
	pl = frappe.db.sql("""select sum(gle.credit - gle.debit) from `tabGL Entry` gle join tabAccount a on a.name = gle.account
		where gle.is_cancelled = 0 and gle.company in %s and gle.posting_date between %s and %s and a.root_type in ('Income', 'Expense')""", (tuple(cos), ys, today()))[0][0]
	draft_je = frappe.db.count("Journal Entry", {"company": ["in", cos], "docstatus": 0}) if _perm("Journal Entry") else 0
	closed = frappe.db.sql("""select max(end_date) from `tabAccounting Period` ap join `tabClosed Document` cd on cd.parent = ap.name
		where ap.company in %s and cd.closed = 1""", (tuple(cos),))[0][0] if frappe.db.table_exists("Closed Document") else None
	return {
		"title": _("Accounting"),
		"desc": _("Chart of accounts, journal entries, general ledger, trial balance and balance sheet — every invoice, bill, payment, stock movement and payroll posts here automatically."),
		"new": [{"label": _("New journal entry"), "doctype": "Journal Entry", "primary": 1}],
		"kpis": [
			kpi(_("Trial balance — {0}").format(label), _("Balanced") if abs(dr - cr) < 0.01 else _("Out by {0}").format(_fmt(dr - cr, cur)),
				_("Debits {0} = credits {1}").format(_fmt(dr, cur), _fmt(cr, cur)), "green" if abs(dr - cr) < 0.01 else "red", "scale", tab="tb"),
			kpi(_("Profit — year to date"), flt(pl), _("Income less expenses, {0}").format(getdate(today()).year), "navy", "trending-up", True, cur, tab="bs"),
			kpi(_("Journal entries to post"), draft_je, _("Draft or awaiting approval"), "amber", "inbox", tab="je"),
			kpi(_("Books closed until"), formatdate(closed, "dd MMM yyyy") if closed else _("Not closed"), _("Earlier dates are locked"), "violet", "lock", tab="closing"),
		],
		"tabs": [
			{"key": "tb", "label": _("Trial balance"), "chips": []},
			{"key": "bs", "label": _("Balance sheet"), "chips": []},
			{"key": "gl", "label": _("General ledger"), "chips": []},
			{"key": "je", "label": _("Journal entries") + (f" ({draft_je})" if draft_je else ""), "chips": [["all", _("All")], ["draft", _("To post")]]},
			{"key": "cc", "label": _("Cost centres"), "chips": []},
			{"key": "reval", "label": _("Currency revaluation"), "chips": []},
			{"key": "coa", "label": _("Chart of accounts"), "chips": []},
			{"key": "closing", "label": _("Period closing"), "chips": []},
		],
		"default_tab": "tb",
		"note": _("Postings are created automatically from invoices, bills, payments, stock and payroll · {0}").format(label),
	}


def _acc_info(names):
	return {a.name: a for a in frappe.get_all("Account", filters={"name": ["in", list(names) or [""]]},
		fields=["name", "account_name", "account_number", "root_type", "account_type", "parent_account", "is_group"])}


def _drcr(v):
	v = flt(v)
	return {"text": f"{abs(v):,.2f} {'Dr' if v >= 0 else 'Cr'}", "tone": ""} if abs(v) >= 0.005 else "—"


def accounts_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	if tab == "tb":
		mv = {r.k: r for r in _gl_sum(cos, start, end)}
		op = _opening(cos, start)
		names = set(mv) | {k for k, v in op.items() if abs(v) >= 0.005}
		info = _acc_info(names)
		order = {"Asset": 0, "Liability": 1, "Equity": 2, "Income": 3, "Expense": 4}
		rows = sorted(names, key=lambda n: (order.get((info.get(n) or {}).get("root_type"), 9), (info.get(n) or {}).get("account_number") or "", n))
		out = []
		for n in rows:
			a = info.get(n) or frappe._dict(account_name=n)
			o = op.get(n, 0) if a.get("root_type") in ("Asset", "Liability", "Equity") else 0
			m = mv.get(n) or frappe._dict(dr=0, cr=0)
			if q and q.lower() not in n.lower():
				continue
			out.append({"dt": "Account", "name": n, "cells": [{"main": a.account_name, "sub": " · ".join(x for x in [a.get("account_number"), _(a.get("root_type") or "")] if x)},
				_drcr(o), {"money": m.dr} if flt(m.dr) else "—", {"money": m.cr} if flt(m.cr) else "—", _drcr(o + flt(m.dr) - flt(m.cr))]})
		return {"title": _("Trial balance — {0}").format(label), "cols": [{"label": _("Account")}, {"label": _("Opening"), "cls": "num"}, {"label": _("Debit"), "cls": "num"},
			{"label": _("Credit"), "cls": "num"}, {"label": _("Closing"), "cls": "num"}], "rows": out, "empty": _("No postings.")}
	if tab == "bs":
		bal = _opening(cos, add_days(today(), 1))
		info = _acc_info(bal.keys())
		grp = {}
		for n, v in bal.items():
			a = info.get(n)
			if not a or a.root_type not in ("Asset", "Liability", "Equity") or abs(v) < 0.005:
				continue
			k = (a.root_type, a.parent_account)
			grp[k] = grp.get(k, 0) + v
		profit = -sum(v for n, v in bal.items() if (info.get(n) or {}).get("root_type") in ("Income", "Expense"))
		rows = []
		for rt, sign in (("Asset", 1), ("Liability", -1), ("Equity", -1)):
			items = sorted([(p, v) for (r, p), v in grp.items() if r == rt], key=lambda x: -abs(x[1]))
			tot = sum(v for _p, v in items) * sign + (profit if rt == "Equity" else 0)
			rows.append({"cells": [{"main": _(rt if rt != "Equity" else "Equity")}, "", {"money": tot}]})
			for p, v in items:
				rows.append({"dt": "Account", "name": p, "cells": [{"text": "   " + (frappe.db.get_value("Account", p, "account_name") or p)}, "", {"money": v * sign}]})
			if rt == "Equity":
				rows.append({"cells": [{"text": "   " + _("Current year profit")}, "", {"money": profit}]})
		return {"title": _("Balance sheet — today"), "cols": [{"label": _("Line")}, {"label": ""}, {"label": _("Amount ({0})").format(cur), "cls": "num"}], "rows": rows}
	if tab == "gl":
		gl = frappe.get_list("GL Entry", filters={"company": ["in", cos], "is_cancelled": 0, "posting_date": ["between", [start, end]]},
			fields=["posting_date", "account", "debit", "credit", "voucher_type", "voucher_no", "party", "remarks"], order_by="posting_date desc, creation desc", limit=200) \
			if _perm("GL Entry") else []
		if q:
			gl = [g for g in gl if q.lower() in (g.account + (g.voucher_no or "") + (g.party or "")).lower()]
		return {"title": _("General ledger — {0}").format(label), "cols": [{"label": _("Date")}, {"label": _("Account")}, {"label": _("Document")}, {"label": _("Party")},
			{"label": _("Debit"), "cls": "num"}, {"label": _("Credit"), "cls": "num"}],
			"rows": [{"dt": g.voucher_type, "name": g.voucher_no, "cells": [{"date": g.posting_date}, g.account, {"main": g.voucher_no, "sub": _(g.voucher_type)}, g.party or "—",
				{"money": g.debit} if flt(g.debit) else "—", {"money": g.credit} if flt(g.credit) else "—"]} for g in gl], "empty": _("No postings in this period.")}
	if tab == "je":
		f = {"company": ["in", cos], "docstatus": ["<", 2]}
		if chip == "draft":
			f["docstatus"] = 0
		jes = frappe.get_list("Journal Entry", filters=f, fields=_fields("Journal Entry", ["name", "posting_date", "title", "voucher_type", "total_debit", "docstatus",
			"user_remark", "workflow_state", "owner"]), order_by="posting_date desc", limit=200) if _perm("Journal Entry") else []
		return {"cols": [{"label": _("Entry")}, {"label": _("Date")}, {"label": _("Memo")}, {"label": _("Type")}, {"label": _("Amount"), "cls": "num"}, {"label": _("By")}, {"label": _("Status")}],
			"rows": [{"dt": "Journal Entry", "name": j.name, "cells": [{"code": j.name}, {"date": j.posting_date}, {"main": j.title or "—", "sub": (j.user_remark or "")[:80]},
				_(j.voucher_type), {"money": j.total_debit}, frappe.utils.get_fullname(j.owner),
				{"pill": _(j.get("workflow_state") or ("Draft" if j.docstatus == 0 else "Posted")), "tone": "orange" if j.docstatus == 0 else "green"}]} for j in jes],
			"empty": _("No journal entries.")}
	if tab == "cc":
		r = frappe.db.sql("""select gle.cost_center, a.root_type, sum(gle.credit - gle.debit) amt from `tabGL Entry` gle join tabAccount a on a.name = gle.account
			where gle.is_cancelled = 0 and gle.company in %s and gle.posting_date between %s and %s and a.root_type in ('Income', 'Expense')
			group by gle.cost_center, a.root_type""", (tuple(cos), start, end), as_dict=True)
		cc = {}
		for x in r:
			c = cc.setdefault(x.cost_center or _("Not set"), {"inc": 0, "exp": 0})
			c["inc" if x.root_type == "Income" else "exp"] += flt(x.amt)
		return {"title": _("Cost centres — {0}").format(label), "cols": [{"label": _("Cost centre")}, {"label": _("Income"), "cls": "num"}, {"label": _("Expenses"), "cls": "num"},
			{"label": _("Profit"), "cls": "num"}, {"label": _("Margin")}],
			"rows": [{"dt": "Cost Center", "name": k, "cells": [{"main": k}, {"money": v["inc"]}, {"money": -v["exp"]}, {"money": v["inc"] + v["exp"]},
				{"text": f"{(v['inc'] + v['exp']) / v['inc'] * 100:.1f}%" if v["inc"] else "—"}]} for k, v in sorted(cc.items(), key=lambda kv: -kv[1]["inc"])],
			"empty": _("No income or expenses in this period.")}
	if tab == "reval":
		rs = frappe.get_list("Exchange Rate Revaluation", filters={"company": ["in", cos]}, fields=["name", "posting_date", "total_gain_loss", "docstatus"],
			order_by="posting_date desc", limit=50) if _perm("Exchange Rate Revaluation") else []
		return {"cols": [{"label": _("Revaluation")}, {"label": _("Date")}, {"label": _("Gain / loss ({0})").format(cur), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Exchange Rate Revaluation", "name": r.name, "cells": [{"code": r.name}, {"date": r.posting_date},
				{"text": f"{flt(r.total_gain_loss):,.2f}", "tone": "green" if flt(r.total_gain_loss) >= 0 else "red"},
				{"pill": _("Draft") if r.docstatus == 0 else _("Posted"), "tone": "orange" if r.docstatus == 0 else "green"}]} for r in rs],
			"actions": [{"label": _("New revaluation"), "route": ["Form", "Exchange Rate Revaluation", "new"]}], "empty": _("No revaluations yet.")}
	if tab == "coa":
		accs = frappe.get_list("Account", filters={"company": cos[0]}, fields=["name", "account_name", "account_number", "root_type", "account_type", "is_group", "lft"],
			order_by="lft asc", limit_page_length=0) if _perm("Account") else []
		if q:
			accs = [a for a in accs if q.lower() in a.name.lower()]
		return {"title": _("Chart of accounts — {0}").format(cos[0]), "cols": [{"label": _("Account")}, {"label": _("Number")}, {"label": _("Type")}, {"label": _("Root")}],
			"rows": [{"dt": "Account", "name": a.name, "cells": [{"main": a.account_name} if a.is_group else a.account_name, a.account_number or "—", _(a.account_type or "—"), _(a.root_type or "")]}
				for a in accs], "actions": [{"label": _("Add account"), "route": ["Form", "Account", "new"]}]}
	if tab == "closing":
		aps = frappe.get_list("Accounting Period", filters={"company": ["in", cos]}, fields=["name", "start_date", "end_date", "company"], order_by="end_date desc", limit=50) \
			if _perm("Accounting Period") else []
		pcv = frappe.get_list("Period Closing Voucher", filters={"company": ["in", cos]}, fields=["name", "period_end_date as posting_date", "docstatus"], order_by="period_end_date desc", limit=20) \
			if _perm("Period Closing Voucher") else []
		rows = [{"dt": "Accounting Period", "name": a.name, "cells": [{"main": a.name}, a.company, {"date": a.start_date}, {"date": a.end_date}, {"pill": _("Locked"), "tone": "violet"}]} for a in aps]
		rows += [{"dt": "Period Closing Voucher", "name": p.name, "cells": [{"main": p.name}, _("Year-end closing"), "", {"date": p.posting_date},
			{"pill": _("Posted") if p.docstatus == 1 else _("Draft"), "tone": "green" if p.docstatus == 1 else "orange"}]} for p in pcv]
		return {"cols": [{"label": _("Period")}, {"label": _("Company")}, {"label": _("From")}, {"label": _("To")}, {"label": _("Status")}], "rows": rows,
			"empty": _("No periods closed yet — approving a VAT return locks its month.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Company Compliance
def _cdocs(cos):
	if not _ok("Company Document"):
		return []
	rows = frappe.get_list("Company Document", filters={"company": ["in", cos]}, fields=["name", "company", "document_type", "document_number", "authority",
		"issue_date", "expiry_date", "responsible_user", "renewal_status", "renewal_cost", "attachment", "notes", "status"], order_by="expiry_date asc", limit=500)
	types = {t.name: t for t in frappe.get_all("Company Document Type", fields=["name", "has_expiry", "renew_before_days"])}
	t = getdate(today())
	for r in rows:
		ty = types.get(r.document_type) or frappe._dict(renew_before_days=60)
		left = date_diff(r.expiry_date, t) if r.expiry_date else None
		r.left = left
		if not r.expiry_date:
			r.state, r.tone = _("No expiry"), "grey"
		elif left < 0:
			r.state, r.tone = _("Expired"), "red"
		elif r.renewal_status in ("Submitted to authority", "In progress"):
			r.state, r.tone = _(r.renewal_status), "blue"
		elif left <= cint(ty.renew_before_days or 60):
			r.state, r.tone = _("Due for renewal"), "orange"
		else:
			r.state, r.tone = _("Valid"), "green"
	return rows


def _deadlines(cos):
	if not _ok("Company Deadline"):
		return []
	return frappe.get_list("Company Deadline", filters={"company": ["in", cos]}, fields=["name", "company", "title", "category", "due_date", "repeat", "status",
		"responsible_user", "done_on"], order_by="due_date asc", limit=300)


def _abbr(cos):
	return {c.name: c.abbr for c in frappe.get_all("Company", filters={"name": ["in", cos]}, fields=["name", "abbr"])}


def codocs_module():
	cos, start, end, label, cur = _scope()
	allc = [c.name for c in frappe.get_all("Company", filters={"is_group": 0})] if len(cos) == 1 else cos
	docs = _cdocs(allc)
	dls = _deadlines(allc)
	t = getdate(today())
	due = [d for d in docs if d.state == _("Due for renewal")]
	expired = [d for d in docs if d.state == _("Expired")]
	od = [d for d in dls if d.status != "Done" and d.due_date and getdate(d.due_date) < t]
	soon = [d for d in dls if d.status != "Done" and d.due_date and 0 <= date_diff(d.due_date, t) <= 30]
	todos = frappe.db.count("ToDo", {"status": "Open", "allocated_to": frappe.session.user, "reference_type": ["in", ["Company Document", "Company Deadline"]]})
	ab = _abbr(allc)
	return {
		"title": _("Company Compliance"),
		"desc": _("Every licence, registration, contract and policy of each group company, with expiry dates, owners and files — and the recurring filing deadlines, with reminders before anything lapses."),
		"new": [{"label": _("Add document"), "doctype": "Company Document", "primary": 1}],
		"kpis": [
			kpi(_("Company documents"), len(docs), _("{0} valid · {1} with the authority").format(len([d for d in docs if d.tone == "green"]), len([d for d in docs if d.tone == "blue"])),
				"navy", "shield", tab="register"),
			kpi(_("Due for renewal"), len(due), _("Within the reminder window"), "amber", "clock", tab="renewals"),
			kpi(_("Expired / overdue"), len(expired) + len(od), _("{0} documents · {1} deadlines").format(len(expired), len(od)), "red", "triangle-alert", tab="deadlines"),
			kpi(_("Deadlines in 30 days"), len(soon), _("VAT, corporate tax, WPS, audits"), "violet", "calendar", tab="deadlines"),
			kpi(_("My ToDos"), todos, _("Reminders assigned to you"), "blue", "check", tab="todos"),
		],
		"tabs": [
			{"key": "register", "label": _("Register"), "chips": [["all", _("All companies")]] + [[c, ab.get(c, c)] for c in allc]},
			{"key": "calendar", "label": _("Calendar"), "chips": []},
			{"key": "deadlines", "label": _("Deadlines") + (f" ({_('{0} overdue').format(len(od))})" if od else ""), "chips": [["open", _("Open")], ["all", _("All")]]},
			{"key": "renewals", "label": _("Renewals"), "chips": []},
			{"key": "todos", "label": _("Reminders & ToDos") + (f" ({todos})" if todos else ""), "chips": []},
			{"key": "types", "label": _("Document types"), "chips": []},
		],
		"default_tab": "register",
	}


def _doc_cells(d, ab):
	left = d.left
	return [{"main": _(d.document_type), "sub": (d.notes or "")[:60]}, {"code": d.document_number} if d.document_number else "—", d.authority or "—",
		{"main": _d(d.expiry_date), "sub": (_("{0} days ago").format(-left) if left < 0 else _("{0} days").format(left)) if left is not None else "", "late": bool(left is not None and left < 30)},
		{"main": frappe.utils.get_fullname(d.responsible_user) if d.responsible_user else "—", "sub": ab.get(d.company, d.company)},
		{"pill": d.state, "tone": d.tone}, {"text": _("On file"), "tone": "green"} if d.attachment else {"text": _("Missing"), "tone": "red"}]


DOC_COLS = [{"label": _("Document")}, {"label": _("Number")}, {"label": _("Issued by")}, {"label": _("Expiry")}, {"label": _("Owner · company")}, {"label": _("Status")}, {"label": _("File")}]


def codocs_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	allc = [c.name for c in frappe.get_all("Company", filters={"is_group": 0})] if len(cos) == 1 else cos
	ab = _abbr(allc)
	t = getdate(today())
	if tab == "register":
		docs = _cdocs([chip] if chip and chip != "all" else allc)
		if q:
			docs = [d for d in docs if q.lower() in (d.document_type + (d.document_number or "") + (d.authority or "")).lower()]
		return {"cols": DOC_COLS, "rows": [{"dt": "Company Document", "name": d.name, "cells": _doc_cells(d, ab)} for d in docs],
			"empty": _("No company documents yet — use Add document.")}
	if tab == "renewals":
		docs = [d for d in _cdocs(allc) if d.tone in ("orange", "red", "blue")]
		return {"cols": DOC_COLS, "rows": [{"dt": "Company Document", "name": d.name, "cells": _doc_cells(d, ab)} for d in docs], "empty": _("Nothing due for renewal.")}
	if tab == "deadlines":
		dls = _deadlines(allc)
		if chip != "all":
			dls = [d for d in dls if d.status != "Done"]
		return {"cols": [{"label": _("Deadline")}, {"label": _("Company")}, {"label": _("Category")}, {"label": _("Due")}, {"label": _("Repeats")}, {"label": _("Owner")}, {"label": _("Status")}],
			"rows": [{"dt": "Company Deadline", "name": d.name, "cells": [{"main": d.title}, ab.get(d.company, d.company), _(d.category or "—"),
				{"date": d.due_date, "late": bool(d.status != "Done" and d.due_date and getdate(d.due_date) < t)}, _(d.repeat or "—"),
				frappe.utils.get_fullname(d.responsible_user) if d.responsible_user else "—",
				{"pill": _("Done") if d.status == "Done" else (_("Overdue") if d.due_date and getdate(d.due_date) < t else _("Open")),
					"tone": "green" if d.status == "Done" else "red" if d.due_date and getdate(d.due_date) < t else "blue"}]} for d in dls], "empty": _("No deadlines.")}
	if tab == "calendar":
		items = [(d.expiry_date, _("Expiry"), _(d.document_type), ab.get(d.company, d.company), "Company Document", d.name, d.tone) for d in _cdocs(allc) if d.expiry_date and date_diff(d.expiry_date, t) <= 180]
		items += [(d.due_date, _("Deadline"), d.title, ab.get(d.company, d.company), "Company Deadline", d.name, "violet") for d in _deadlines(allc) if d.status != "Done" and d.due_date and date_diff(d.due_date, t) <= 180]
		items.sort(key=lambda x: getdate(x[0]))
		return {"title": _("Next six months"), "cols": [{"label": _("Date")}, {"label": _("What")}, {"label": _("Item")}, {"label": _("Company")}],
			"rows": [{"dt": dt, "name": n, "cells": [{"date": dte, "late": getdate(dte) < t}, {"pill": what, "tone": tone}, {"main": item}, co]} for dte, what, item, co, dt, n, tone in items],
			"empty": _("Nothing due in the next six months.")}
	if tab == "todos":
		tds = frappe.get_all("ToDo", filters={"status": "Open", "reference_type": ["in", ["Company Document", "Company Deadline"]]},
			fields=["name", "description", "date", "allocated_to", "reference_type", "reference_name"], order_by="date asc", limit=200)
		return {"cols": [{"label": _("To do")}, {"label": _("For")}, {"label": _("Due")}, {"label": _("About")}],
			"rows": [{"dt": "ToDo", "name": x.name, "cells": [{"main": frappe.utils.strip_html(x.description or "")[:90]}, frappe.utils.get_fullname(x.allocated_to), {"date": x.date},
				{"link": [x.reference_type, x.reference_name]}]} for x in tds], "empty": _("No open reminders.")}
	if tab == "types":
		ts = frappe.get_all("Company Document Type", fields=["name", "country", "authority", "has_expiry", "renew_before_days"], order_by="name asc")
		return {"cols": [{"label": _("Document type")}, {"label": _("Country")}, {"label": _("Authority")}, {"label": _("Expires")}, {"label": _("Remind before")}],
			"rows": [{"dt": "Company Document Type", "name": x.name, "cells": [{"main": _(x.name)}, x.country or "—", x.authority or "—", _("Yes") if x.has_expiry else _("No"),
				_("{0} days").format(x.renew_before_days) if x.renew_before_days else "—"]} for x in ts],
			"actions": [{"label": _("Add type"), "route": ["Form", "Company Document Type", "new"]}]}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Fixed Assets
def _assets(cos, cat=None):
	if not _perm("Asset"):
		return []
	f = {"company": ["in", cos], "docstatus": ["<", 2], "status": ["not in", ["Scrapped", "Sold"]]}
	if cat and cat != "all":
		f["asset_category"] = cat
	try:
		frappe.get_list("Asset", limit=1)
	except frappe.PermissionError:
		frappe.clear_messages()
		return []
	rows = frappe.get_list("Asset", filters=f, fields=_fields("Asset", ["name", "asset_name", "asset_category", "location", "custodian", "purchase_date", "net_purchase_amount",
		"value_after_depreciation", "status", "docstatus", "hs_plate_no", "hs_registration_expiry", "hs_next_service", "insurance_end_date", "total_number_of_depreciations",
		"frequency_of_depreciation", "opening_accumulated_depreciation"]), order_by="purchase_date asc", limit=500)
	t = getdate(today())
	month_dep = {r[0]: flt(r[1]) for r in frappe.db.sql("""select ads.asset, sum(ds.depreciation_amount) from `tabDepreciation Schedule` ds
		join `tabAsset Depreciation Schedule` ads on ads.name = ds.parent where ads.docstatus = 1 and ds.schedule_date between %s and %s group by ads.asset""",
		(get_first_day(t), get_last_day(t)))} if frappe.db.table_exists("Depreciation Schedule") else {}
	per = {}
	for r in frappe.db.sql("""select ads.asset, ds.depreciation_amount from `tabDepreciation Schedule` ds join `tabAsset Depreciation Schedule` ads on ads.name = ds.parent
		where ads.docstatus = 1 and ds.schedule_date > %s order by ds.schedule_date asc""", t, as_dict=True) if frappe.db.table_exists("Depreciation Schedule") else []:
		per.setdefault(r.asset, flt(r.depreciation_amount))
	life = {r.parent: cint(r.total_number_of_depreciations) * cint(r.frequency_of_depreciation or 1) for r in frappe.get_all("Asset Finance Book",
		filters={"parenttype": "Asset", "parent": ["in", [x.name for x in rows] or [""]]}, fields=["parent", "total_number_of_depreciations", "frequency_of_depreciation"])}
	emp = {e.name: e.employee_name for e in frappe.get_all("Employee", fields=["name", "employee_name"])} if frappe.db.table_exists("Employee") else {}
	for r in rows:
		r.life = life.get(r.name)
		r.custodian_name = emp.get(r.custodian) or r.custodian or ""
		r.monthly = per.get(r.name, 0)
		r.month_dep = month_dep.get(r.name, 0)
		flags = []
		if r.get("hs_registration_expiry") and date_diff(r.hs_registration_expiry, t) <= 30:
			flags.append((_("Registration (Mulkiya) renewal"), "orange" if date_diff(r.hs_registration_expiry, t) >= 0 else "red"))
		if r.get("insurance_end_date") and date_diff(r.insurance_end_date, t) <= 30:
			flags.append((_("Insurance renewal"), "orange" if date_diff(r.insurance_end_date, t) >= 0 else "red"))
		if r.get("hs_next_service") and date_diff(r.hs_next_service, t) < 0:
			flags.append((_("Service overdue"), "red"))
		elif r.get("hs_next_service") and date_diff(r.hs_next_service, t) <= 14:
			flags.append((_("Service due"), "orange"))
		flags.sort(key=lambda x: 0 if x[1] == "red" else 1)
		r.flags_ = flags
		r.state = flags[0] if flags else ((_("Draft"), "grey") if r.docstatus == 0 else (_("In use"), "green") if flt(r.value_after_depreciation) > 0 or r.monthly else (_("Fully depreciated"), "grey"))
	return rows


def assets_module():
	cos, start, end, label, cur = _scope()
	rows = _assets(cos)
	live = [r for r in rows if r.docstatus == 1]
	t = getdate(today())
	svc = [r for r in rows if r.get("hs_next_service") and date_diff(r.hs_next_service, t) <= 14]
	svc_od = [r for r in svc if date_diff(r.hs_next_service, t) < 0]
	ren = [r for r in rows if any(r.get(f) and date_diff(r.get(f), t) <= 30 for f in ("hs_registration_expiry", "insurance_end_date"))]
	cats = sorted({r.asset_category for r in rows if r.asset_category})
	n_maint = len({r.name for r in rows if r.flags_})
	return {
		"title": _("Fixed Assets"),
		"desc": _("Vehicles, forklifts, racking and IT — who has them, what they are worth, and when they need service, registration or insurance renewal."),
		"new": [{"label": _("Add asset"), "doctype": "Asset", "primary": 1}],
		"kpis": [
			kpi(_("Assets in use"), len(live), _("{0} at cost").format(_fmt(sum(flt(r.net_purchase_amount) for r in live), cur)), "blue", "building", tab="register"),
			kpi(_("Net book value"), sum(flt(r.value_after_depreciation) for r in live), _("After accumulated depreciation"), "navy", "scale", True, cur, tab="depreciation"),
			kpi(_("Depreciation this month"), sum(r.month_dep for r in live), _("Posted to Profit & loss"), "violet", "chart-column", True, cur, tab="depreciation"),
			kpi(_("Service due / overdue"), len(svc), _("{0} overdue").format(len(svc_od)), "red", "wrench", tab="maintenance"),
			kpi(_("Renewals ≤ 30 days"), len(ren), _("Vehicle registration & insurance"), "amber", "flag", tab="maintenance"),
		],
		"tabs": [
			{"key": "register", "label": _("Register"), "chips": [["all", _("All categories")]] + [[c, _(c)] for c in cats]},
			{"key": "maintenance", "label": _("Maintenance & renewals") + (f" ({n_maint})" if n_maint else ""), "chips": []},
			{"key": "depreciation", "label": _("Depreciation"), "chips": []},
		],
		"default_tab": "register",
	}


def assets_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	rows = _assets(cos, chip if tab == "register" else None)
	if q:
		rows = [r for r in rows if q.lower() in (r.asset_name + (r.get("hs_plate_no") or "") + (r.asset_category or "")).lower()]
	if tab == "register":
		return {"title": _("Asset register"), "cols": [{"label": _("Asset")}, {"label": _("Location · custodian")}, {"label": _("Purchased")}, {"label": _("Cost"), "cls": "num"},
			{"label": _("Net book value"), "cls": "num"}, {"label": _("Monthly dep."), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Asset", "name": r.name, "cells": [{"main": r.asset_name + (f"  ·  {r.hs_plate_no}" if r.get("hs_plate_no") else ""), "sub": f"{r.name} · {_(r.asset_category or '')}"},
				{"main": r.location or "—", "sub": r.custodian_name}, {"date": r.purchase_date}, {"money": r.net_purchase_amount}, {"money": r.value_after_depreciation},
				{"money": r.monthly} if r.monthly else {"text": _("Fully depreciated") if r.docstatus == 1 else "—", "tone": ""}, {"pill": r.state[0], "tone": r.state[1]}]} for r in rows],
			"empty": _("No assets yet — use Add asset.")}
	if tab == "maintenance":
		out = []
		for r in rows:
			for what, f in ((_("Service"), "hs_next_service"), (_("Registration (Mulkiya)"), "hs_registration_expiry"), (_("Insurance"), "insurance_end_date")):
				if r.get(f):
					left = date_diff(r.get(f), today())
					out.append((getdate(r.get(f)), {"dt": "Asset", "name": r.name, "cells": [{"main": r.asset_name, "sub": r.get("hs_plate_no") or r.name}, what, {"date": r.get(f), "late": left < 0},
						{"pill": _("Overdue") if left < 0 else _("Due in {0} days").format(left) if left <= 30 else _("Planned"), "tone": "red" if left < 0 else "orange" if left <= 30 else "green"}]}))
		out.sort(key=lambda x: x[0])
		return {"cols": [{"label": _("Asset")}, {"label": _("What")}, {"label": _("Due")}, {"label": _("Status")}], "rows": [x[1] for x in out],
			"empty": _("No service or renewal dates recorded — add them on the asset (next service, registration, insurance).")}
	if tab == "depreciation":
		return {"cols": [{"label": _("Asset")}, {"label": _("Category")}, {"label": _("Cost"), "cls": "num"}, {"label": _("Accumulated"), "cls": "num"},
			{"label": _("Net book value"), "cls": "num"}, {"label": _("This month"), "cls": "num"}, {"label": _("Life (months)"), "cls": "num"}],
			"rows": [{"dt": "Asset", "name": r.name, "cells": [{"main": r.asset_name, "sub": r.name}, _(r.asset_category or ""), {"money": r.net_purchase_amount},
				{"money": flt(r.net_purchase_amount) - flt(r.value_after_depreciation)}, {"money": r.value_after_depreciation}, {"money": r.month_dep} if r.month_dep else "—",
				r.life or "—"]} for r in rows if r.docstatus == 1], "empty": _("No submitted assets.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- Finance: the prototype's extra tabs (v1.7.0)
FIN_EXTRA = ("advances", "collections", "bankrec", "cashflow", "pl")


def vat_payable(cos, start, end):
	out = frappe.db.sql("""select sum(base_total_taxes_and_charges) from `tabSales Invoice` where docstatus = 1 and company in %s and posting_date between %s and %s""",
		(tuple(cos), start, end))[0][0]
	inp = frappe.db.sql("""select sum(base_total_taxes_and_charges) from `tabPurchase Invoice` where docstatus = 1 and company in %s and posting_date between %s and %s""",
		(tuple(cos), start, end))[0][0]
	return flt(out) - flt(inp)


def finance_extra(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "advances":
		pes = frappe.get_list("Payment Entry", filters={"company": ["in", cos], "docstatus": 1, "payment_type": "Receive", "party_type": "Customer", "unallocated_amount": [">", 0]},
			fields=["name", "party", "party_name", "posting_date", "paid_amount", "unallocated_amount", "mode_of_payment", "reference_no", "paid_from_account_currency"],
			order_by="posting_date desc", limit=200) if _perm("Payment Entry") else []
		so_adv = frappe.get_list("Sales Order", filters={"company": ["in", cos], "docstatus": 1, "advance_paid": [">", 0], "per_billed": ["<", 100]},
			fields=["name", "customer_name", "transaction_date", "advance_paid", "grand_total", "currency"], order_by="transaction_date desc", limit=100) if _perm("Sales Order") else []
		rows = [{"dt": "Payment Entry", "name": p.name, "cells": [{"code": p.name}, {"main": p.party_name or p.party, "sub": " ".join(x for x in [p.mode_of_payment, p.reference_no] if x)},
			{"date": p.posting_date}, {"money": p.paid_amount}, {"money": p.unallocated_amount}, {"pill": _("Not applied"), "tone": "orange"}]} for p in pes]
		rows += [{"dt": "Sales Order", "name": s.name, "cells": [{"code": s.name}, {"main": s.customer_name, "sub": _("Advance against the order")}, {"date": s.transaction_date},
			{"money": s.advance_paid, "currency": s.currency if s.currency != cur else None}, {"money": s.advance_paid}, {"pill": _("Held on order"), "tone": "blue"}]} for s in so_adv]
		return {"title": _("Customer advances"), "cols": [{"label": _("Receipt / order")}, {"label": _("Customer")}, {"label": _("Received")}, {"label": _("Amount"), "cls": "num"},
			{"label": _("Unapplied"), "cls": "num"}, {"label": _("Status")}], "rows": rows,
			"actions": [{"label": _("Receive advance"), "primary": 1, "route": ["Form", "Payment Entry", "new"], "options": {"payment_type": "Receive", "party_type": "Customer"}}],
			"empty": _("No customer advances waiting to be applied.")}
	if tab == "collections":
		inv = frappe.get_list("Sales Invoice", filters={"company": ["in", cos], "docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<=", add_days(t, 7)]},
			fields=["name", "customer", "customer_name", "due_date", "outstanding_amount", "currency", "posting_date"], order_by="due_date asc", limit=300) if _perm("Sales Invoice") else []
		by = {}
		for i in inv:
			x = by.setdefault(i.customer, frappe._dict(customer=i.customer, name=i.customer_name, n=0, amt=0, oldest=i.due_date, inv=[]))
			x.n += 1
			x.amt += flt(i.outstanding_amount)
			x.inv.append(i.name)
			x.oldest = min(getdate(x.oldest), getdate(i.due_date))
		rows = []
		for x in sorted(by.values(), key=lambda x: x.oldest):
			late = date_diff(t, x.oldest)
			stage = _("Final notice") if late > 60 else _("2nd reminder") if late > 30 else _("1st reminder") if late > 0 else _("Due soon")
			rows.append({"dt": "Customer", "name": x.customer, "cells": [{"main": x.name, "sub": ", ".join(x.inv[:3]) + ("…" if len(x.inv) > 3 else "")}, x.n, {"money": x.amt},
				{"main": _d(x.oldest), "sub": _("{0} days late").format(late) if late > 0 else _("due in {0} days").format(-late), "late": late > 0},
				{"pill": stage, "tone": "red" if late > 30 else "orange" if late > 0 else "blue"}, {"url": f"/portal?tab=statement&customer={frappe.utils.quote(x.customer)}", "label": _("Statement")}]})
		return {"title": _("Collections — overdue and due in the next 7 days"), "cols": [{"label": _("Customer")}, {"label": _("Invoices"), "cls": "num"}, {"label": _("Outstanding"), "cls": "num"},
			{"label": _("Oldest due")}, {"label": _("Next step")}, {"label": ""}], "rows": rows, "empty": _("Nothing overdue or due this week.")}
	if tab == "bankrec":
		bts = frappe.get_list("Bank Transaction", filters={"company": ["in", cos], "docstatus": 1, "status": ["in", ["Unreconciled", "Pending"]]},
			fields=["name", "date", "description", "deposit", "withdrawal", "unallocated_amount", "bank_account", "reference_number"], order_by="date desc", limit=200) \
			if frappe.db.table_exists("Bank Transaction") and _perm("Bank Transaction") else []
		return {"title": _("Bank statement lines to match"), "cols": [{"label": _("Date")}, {"label": _("Description")}, {"label": _("Account")}, {"label": _("In"), "cls": "num"},
			{"label": _("Out"), "cls": "num"}, {"label": _("To match"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Bank Transaction", "name": b.name, "cells": [{"date": b.date}, {"main": b.description or "—", "sub": b.reference_number or ""}, b.bank_account,
				{"money": b.deposit} if flt(b.deposit) else "—", {"money": b.withdrawal} if flt(b.withdrawal) else "—", {"money": b.unallocated_amount},
				{"pill": _("Unmatched"), "tone": "orange"}]} for b in bts],
			"actions": [{"label": _("Open reconciliation tool"), "primary": 1, "route": ["bank-reconciliation-tool"]}, {"label": _("Import statement"), "route": ["Form", "Bank Statement Import", "new"]}],
			"empty": _("All bank lines are matched.")}
	if tab == "cashflow":
		r = frappe.db.sql("""select date_format(gle.posting_date, '%%Y-%%m') m, sum(gle.debit) i, sum(gle.credit) o from `tabGL Entry` gle join tabAccount a on a.name = gle.account
			where gle.is_cancelled = 0 and gle.company in %s and a.account_type in ('Bank', 'Cash') and gle.posting_date >= %s and gle.voucher_type != 'Period Closing Voucher'
			group by m order by m""", (tuple(cos), get_first_day(add_months(t, -5))), as_dict=True)
		opening = flt(frappe.db.sql("""select sum(gle.debit - gle.credit) from `tabGL Entry` gle join tabAccount a on a.name = gle.account where gle.is_cancelled = 0
			and gle.company in %s and a.account_type in ('Bank', 'Cash') and gle.posting_date < %s""", (tuple(cos), get_first_day(add_months(t, -5))))[0][0])
		rows, bal = [], opening
		for x in r:
			bal += flt(x.i) - flt(x.o)
			rows.append({"cells": [{"main": formatdate(x.m + "-01", "MMMM yyyy")}, {"money": x.i}, {"money": x.o}, {"money": flt(x.i) - flt(x.o), "neg": flt(x.i) < flt(x.o)}, {"money": bal}]})
		dues_in = flt(frappe.db.sql("""select sum(outstanding_amount) from `tabSales Invoice` where docstatus=1 and company in %s and outstanding_amount > 0 and due_date <= %s""",
			(tuple(cos), add_days(t, 30)))[0][0])
		dues_out = flt(frappe.db.sql("""select sum(outstanding_amount) from `tabPurchase Invoice` where docstatus=1 and company in %s and outstanding_amount > 0 and due_date <= %s""",
			(tuple(cos), add_days(t, 30)))[0][0])
		rows.append({"cells": [{"main": _("Next 30 days (expected)")}, {"money": dues_in}, {"money": dues_out}, {"money": dues_in - dues_out, "neg": dues_in < dues_out}, {"money": bal + dues_in - dues_out}]})
		return {"title": _("Cash flow — bank and cash, last six months"), "cols": [{"label": _("Month")}, {"label": _("Money in"), "cls": "num"}, {"label": _("Money out"), "cls": "num"},
			{"label": _("Net"), "cls": "num"}, {"label": _("Closing balance"), "cls": "num"}], "rows": rows,
			"actions": [{"label": _("Cash Flow report"), "route": ["query-report", "Cash Flow"]}]}
	if tab == "pl":
		ys = getdate(f"{t.year}-01-01")
		cols_p = [(label, start, end), (_("Year to date"), ys, t)]
		figs = []
		for _l, a, b in cols_p:
			r = frappe.db.sql("""select a.root_type, a.account_type, a.parent_account, sum(gle.credit - gle.debit) amt from `tabGL Entry` gle join tabAccount a on a.name = gle.account
				where gle.is_cancelled = 0 and gle.company in %s and gle.posting_date between %s and %s and a.root_type in ('Income', 'Expense')
				and gle.voucher_type != 'Period Closing Voucher' group by a.root_type, a.account_type, a.parent_account""", (tuple(cos), a, b), as_dict=True)
			f = frappe._dict(rev=0, cogs=0, exp={})
			for x in r:
				if x.root_type == "Income":
					f.rev += flt(x.amt)
				elif x.account_type in ("Cost of Goods Sold", "Stock Adjustment"):
					f.cogs += -flt(x.amt)
				else:
					k = (frappe.db.get_value("Account", x.parent_account, "account_name") or x.parent_account or _("Other")) if x.parent_account else _("Other")
					f.exp[k] = f.exp.get(k, 0) - flt(x.amt)
			figs.append(f)
		keys = sorted({k for f in figs for k in f.exp}, key=lambda k: -figs[1].exp.get(k, 0))
		def line(lab, vals, **kw):
			return dict({"cells": [{"main": lab} if kw.get("b") else lab] + [{"money": v, "neg": v < 0} for v in vals]}, **({"cls": "hsx-grp-row"} if kw.get("b") else {}))
		rows = [line(_("Revenue"), [f.rev for f in figs], b=1), line(_("Cost of sales (landed)"), [-f.cogs for f in figs]),
			line(_("Gross profit"), [f.rev - f.cogs for f in figs], b=1)]
		rows += [line("   " + k, [-f.exp.get(k, 0) for f in figs]) for k in keys]
		rows.append(line(_("Net profit"), [f.rev - f.cogs - sum(f.exp.values()) for f in figs], b=1))
		gm = [((f.rev - f.cogs) / f.rev * 100) if f.rev else 0 for f in figs]
		rows.append({"cells": [_("Gross margin")] + [{"text": f"{g:.1f}%"} for g in gm]})
		return {"title": _("Profit & loss"), "cols": [{"label": _("Line")}] + [{"label": l, "cls": "num"} for l, _a, _b in cols_p], "rows": rows,
			"actions": [{"label": _("Profit and Loss report"), "route": ["query-report", "Profit and Loss Statement"]}]}
	return {"cols": [], "rows": []}
