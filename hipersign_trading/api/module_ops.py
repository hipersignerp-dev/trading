"""v1.6.0: the Warehouse & Stock and UAE VAT module pages (prototype "Warehouse & Inventory" and "UAE VAT & E-invoicing").

Same shape as api/module.py (get_module / get_rows dispatch there). Read with the user's own permissions.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

from hipersign_trading.api.module import _fields, _fmt, _perm, _scope, kpi

GROUP_COLORS = ["blue", "violet", "orange", "green", "teal", "navy", "red", "grey"]


# ---------------------------------------------------------------- Warehouse & Stock
def _warehouses(cos):
	return frappe.get_all("Warehouse", filters={"company": ["in", cos], "is_group": 0, "disabled": 0}, pluck="name")


def _bins(cos):
	"""Stock per item and warehouse in the user's companies (Bin is read with the user's Item permission)."""
	if not (_perm("Item") and _perm("Bin")):
		return []
	whs = _warehouses(cos)
	if not whs:
		return []
	return frappe.get_all("Bin", filters={"warehouse": ["in", whs]}, fields=["item_code", "warehouse", "actual_qty", "reserved_qty",
		"reserved_stock", "ordered_qty", "projected_qty", "stock_value", "valuation_rate"])


def _items(codes):
	if not codes:
		return {}
	rows = frappe.get_all("Item", filters={"name": ["in", list(codes)]}, fields=_fields("Item", ["name", "item_name", "item_group", "brand", "stock_uom",
		"hs_model", "hs_item_name_ar", "disabled"]))
	return {r.name: r for r in rows}


def _reorder_levels(codes, whs):
	out = {}
	if not codes:
		return out
	for r in frappe.get_all("Item Reorder", filters={"parent": ["in", list(codes)], "warehouse": ["in", whs or [""]]},
			fields=["parent", "warehouse_reorder_level"]):
		out[r.parent] = out.get(r.parent, 0) + flt(r.warehouse_reorder_level)
	return out


def _sold_recently(codes, days=180):
	if not codes:
		return set()
	return set(frappe.db.sql_list("""select distinct i.item_code from `tabSales Invoice Item` i join `tabSales Invoice` s on s.name = i.parent
		where s.docstatus = 1 and s.posting_date >= %s and i.item_code in %s""", (add_days(today(), -days), tuple(codes))))


def _stock_summary(cos):
	bins = _bins(cos)
	whs = _warehouses(cos)
	per = {}
	for b in bins:
		r = per.setdefault(b.item_code, frappe._dict(qty=0, reserved=0, ordered=0, value=0, whs=[]))
		r.qty += flt(b.actual_qty)
		r.reserved += flt(b.reserved_stock) or flt(b.reserved_qty)
		r.ordered += flt(b.ordered_qty)
		r.value += flt(b.stock_value)
		if flt(b.actual_qty):
			r.whs.append(b.warehouse)
	stock_items = set(frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0, "has_variants": 0}, pluck="name")) if _perm("Item") else set()
	for code in stock_items:
		per.setdefault(code, frappe._dict(qty=0, reserved=0, ordered=0, value=0, whs=[]))
	levels = _reorder_levels(per.keys(), whs)
	for code, r in per.items():
		r.level = levels.get(code, 0)
		r.status = "Out of Stock" if r.qty <= 0 else "Low Stock" if r.level and r.qty - r.reserved <= r.level else "In Stock"
	return per, bins, whs


STOCK_TONE = {"In Stock": "green", "Low Stock": "orange", "Out of Stock": "red"}


def stock_module():
	cos, start, end, label, cur = _scope()
	per, bins, whs = _stock_summary(cos)
	in_stock = [c for c, r in per.items() if r.qty > 0]
	low = [c for c, r in per.items() if r.status == "Low Stock"]
	out = [c for c, r in per.items() if r.status == "Out of Stock"]
	sold = _sold_recently(in_stock)
	slow = sum(per[c].value for c in in_stock if c not in sold)
	n_counts = frappe.db.count("Stock Reconciliation", {"company": ["in", cos], "docstatus": 0}) if _perm("Stock Reconciliation") else 0
	n_transfer = frappe.db.count("Stock Entry", {"company": ["in", cos], "docstatus": 0, "purpose": "Material Transfer"}) if _perm("Stock Entry") else 0
	by_wh, by_grp = {}, {}
	items = _items(per.keys())
	for b in bins:
		by_wh[b.warehouse] = by_wh.get(b.warehouse, 0) + flt(b.stock_value)
	for c, r in per.items():
		g = (items.get(c) or {}).get("item_group") or _("Other")
		if r.value:
			by_grp[g] = by_grp.get(g, 0) + r.value
	total = sum(r.value for r in per.values())
	grp = sorted(by_grp.items(), key=lambda kv: -kv[1])
	tabs = [
		{"key": "items", "label": _("Stock items"), "chips": [["all", _("All")], ["low", _("Low stock ({0})").format(len(low))], ["out", _("Out of stock ({0})").format(len(out))],
			["reserved", _("Reserved")]]},
		{"key": "moves", "label": _("Stock movements"), "chips": [["all", _("All")], ["in", _("In")], ["out", _("Out")]]},
		{"key": "transfers", "label": _("Transfers") + (f" ({n_transfer})" if n_transfer else ""), "chips": [["all", _("All")], ["draft", _("Draft")]]},
		{"key": "counts", "label": _("Stock counts") + (f" ({n_counts})" if n_counts else ""), "chips": []},
	]
	if frappe.db.table_exists("Stock Reservation Entry") and _perm("Stock Reservation Entry"):
		tabs.append({"key": "reservations", "label": _("Reservations"), "chips": []})
	tabs += [{"key": "warehouses", "label": _("Warehouses"), "chips": []}, {"key": "ageing", "label": _("Ageing"), "chips": []}]
	return {
		"title": _("Warehouse & Inventory"),
		"desc": _("Know what you have and where it is — stock, locations, movements, counts and ageing across every warehouse."),
		"new": [{"label": _("Stock transfer"), "doctype": "Stock Entry"}, {"label": _("Stock count"), "doctype": "Stock Reconciliation"}],
		"kpis": [
			kpi(_("Stock value"), total, _("Moving average incl. landed cost"), "violet", "chart-column", True, cur, tab="warehouses"),
			kpi(_("Items in stock"), f"{len(in_stock)} / {len(per)}", _("{0} units").format(f"{sum(r.qty for r in per.values()):,.0f}"), "blue", "layers", tab="items", chip="all"),
			kpi(_("Below reorder level"), len(low), _("See reorder suggestions"), "amber", "flag", tab="items", chip="low"),
			kpi(_("Out of stock"), len(out), _("Zero available"), "red", "triangle-alert", tab="items", chip="out"),
			kpi(_("Slow-moving value"), slow, _("No sales > 180 days"), "amber", "clock", True, cur, tab="ageing"),
			kpi(_("Counts awaiting approval"), n_counts, _("Warehouse Manager"), "navy", "inbox", tab="counts"),
		],
		"cards": [
			{"title": _("Stock value by warehouse"), "sub": cur, "type": "bars", "currency": cur, "wide": 1,
				"rows": [[w, v] for w, v in sorted(by_wh.items(), key=lambda kv: -kv[1]) if v][:6]},
			{"title": _("Value by category"), "sub": cur, "type": "donut", "center": _fmt(total, "").strip(), "center_label": cur, "currency": cur,
				"rows": [[g, v, GROUP_COLORS[i % len(GROUP_COLORS)]] for i, (g, v) in enumerate(grp[:7])]},
		],
		"tabs": tabs,
		"default_tab": "items",
		"links": [[_("Stock balance"), ["query-report", "Stock Balance"]], [_("Stock ledger"), ["query-report", "Stock Ledger"]]],
	}


def _match(q, *vals):
	return not q or any(q.lower() in (v or "").lower() for v in vals)


def stock_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	t = getdate(today())
	if tab == "items":
		per, bins, whs = _stock_summary(cos)
		items = _items(per.keys())
		rows = []
		for code, r in sorted(per.items()):
			it = items.get(code)
			if not it or it.disabled:
				continue
			if chip == "low" and r.status != "Low Stock" or chip == "out" and r.status != "Out of Stock" or chip == "reserved" and not r.reserved:
				continue
			if not _match(q, code, it.item_name, it.item_group, it.brand):
				continue
			sub = " · ".join(x for x in [it.brand, it.get("hs_model")] if x)
			rows.append({"dt": "Item", "name": code, "cells": [{"code": code},
				{"main": it.item_name, "sub": " ".join(x for x in [sub, it.get("hs_item_name_ar")] if x)}, it.item_group or "—", ", ".join(r.whs) or "—",
				{"main": f"{r.qty:,.0f}"}, {"text": f"{r.reserved:,.0f}", "tone": "violet"} if r.reserved else "—", {"main": f"{r.qty - r.reserved:,.0f}"},
				f"{r.ordered:,.0f}" if r.ordered else "—", {"money": r.value / r.qty if r.qty else 0}, {"money": r.value},
				{"pill": _(r.status), "tone": STOCK_TONE[r.status]}]})
		return {"cols": [{"label": _("Item code")}, {"label": _("Description")}, {"label": _("Category")}, {"label": _("Warehouse")},
			{"label": _("On hand"), "cls": "num"}, {"label": _("Reserved"), "cls": "num"}, {"label": _("Free"), "cls": "num"}, {"label": _("On order"), "cls": "num"},
			{"label": _("Valuation rate"), "cls": "num"}, {"label": _("Value ({0})").format(cur), "cls": "num"}, {"label": _("Status")}],
			"rows": rows, "empty": _("No items here.")}
	if tab == "moves":
		if not _perm("Stock Ledger Entry"):
			return {"cols": [], "rows": []}
		f = {"company": ["in", cos], "is_cancelled": 0, "posting_date": [">=", add_days(t, -60)]}
		if chip == "in":
			f["actual_qty"] = [">", 0]
		elif chip == "out":
			f["actual_qty"] = ["<", 0]
		sle = frappe.get_list("Stock Ledger Entry", filters=f, fields=["posting_date", "posting_time", "voucher_type", "voucher_no", "item_code", "warehouse",
			"actual_qty", "qty_after_transaction", "stock_value_difference"], order_by="posting_date desc, posting_time desc, creation desc", limit=200)
		names = _items({s.item_code for s in sle})
		sle = [s for s in sle if _match(q, s.item_code, s.voucher_no, (names.get(s.item_code) or {}).get("item_name"))]
		return {"cols": [{"label": _("Date")}, {"label": _("Document")}, {"label": _("Item")}, {"label": _("Warehouse")}, {"label": _("In / out"), "cls": "num"},
			{"label": _("Balance"), "cls": "num"}, {"label": _("Value change"), "cls": "num"}],
			"rows": [{"dt": s.voucher_type, "name": s.voucher_no, "cells": [{"date": s.posting_date}, {"main": s.voucher_no, "sub": _(s.voucher_type)},
				{"main": (names.get(s.item_code) or {}).get("item_name") or s.item_code, "sub": s.item_code}, s.warehouse,
				{"text": f"{flt(s.actual_qty):+,.0f}", "tone": "green" if flt(s.actual_qty) > 0 else "red"}, f"{flt(s.qty_after_transaction):,.0f}",
				{"money": s.stock_value_difference}]} for s in sle], "empty": _("No stock movements in the last 60 days.")}
	if tab == "transfers":
		if not _perm("Stock Entry"):
			return {"cols": [], "rows": []}
		f = {"company": ["in", cos], "purpose": "Material Transfer", "docstatus": ["<", 2]}
		if chip == "draft":
			f["docstatus"] = 0
		ses = frappe.get_list("Stock Entry", filters=f, fields=["name", "posting_date", "from_warehouse", "to_warehouse", "total_outgoing_value", "docstatus", "remarks"],
			order_by="posting_date desc", limit=100)
		qty = {}
		for r in frappe.get_all("Stock Entry Detail", filters={"parent": ["in", [s.name for s in ses] or [""]]}, fields=["parent", "qty", "s_warehouse", "t_warehouse"]):
			x = qty.setdefault(r.parent, frappe._dict(n=0, qty=0, s=r.s_warehouse, t=r.t_warehouse))
			x.n += 1
			x.qty += flt(r.qty)
		return {"cols": [{"label": _("Transfer")}, {"label": _("Date")}, {"label": _("From")}, {"label": _("To")}, {"label": _("Lines"), "cls": "num"},
			{"label": _("Qty"), "cls": "num"}, {"label": _("Value"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Stock Entry", "name": s.name, "cells": [{"code": s.name}, {"date": s.posting_date}, s.from_warehouse or (qty.get(s.name) or {}).get("s") or "—",
				s.to_warehouse or (qty.get(s.name) or {}).get("t") or "—", (qty.get(s.name) or {}).get("n") or 0, f"{flt((qty.get(s.name) or {}).get('qty')):,.0f}",
				{"money": s.total_outgoing_value}, {"pill": _("Draft") if s.docstatus == 0 else _("Done"), "tone": "grey" if s.docstatus == 0 else "green"}]}
				for s in ses if _match(q, s.name, s.from_warehouse, s.to_warehouse)], "empty": _("No transfers yet.")}
	if tab == "counts":
		if not _perm("Stock Reconciliation"):
			return {"cols": [], "rows": []}
		rs = frappe.get_list("Stock Reconciliation", filters={"company": ["in", cos], "docstatus": ["<", 2]}, fields=["name", "posting_date", "purpose", "difference_amount",
			"docstatus", "owner", "set_warehouse"], order_by="docstatus asc, posting_date desc", limit=100)
		n = {}
		for r in frappe.get_all("Stock Reconciliation Item", filters={"parent": ["in", [x.name for x in rs] or [""]]}, fields=["parent", "warehouse"]):
			x = n.setdefault(r.parent, frappe._dict(n=0, wh=r.warehouse))
			x.n += 1
		return {"cols": [{"label": _("Count")}, {"label": _("Date")}, {"label": _("Warehouse")}, {"label": _("Lines"), "cls": "num"}, {"label": _("Counted by")},
			{"label": _("Difference"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Stock Reconciliation", "name": r.name, "cells": [{"code": r.name}, {"date": r.posting_date},
				r.set_warehouse or (n.get(r.name) or {}).get("wh") or "—", (n.get(r.name) or {}).get("n") or 0, frappe.utils.get_fullname(r.owner),
				{"money": r.difference_amount}, {"pill": _("Opening stock") if r.purpose == "Opening Stock" else _("Awaiting approval") if r.docstatus == 0 else _("Posted"),
					"tone": "orange" if r.docstatus == 0 else "green"}]} for r in rs], "empty": _("No stock counts yet.")}
	if tab == "reservations":
		sre = frappe.get_list("Stock Reservation Entry", filters={"company": ["in", cos], "docstatus": 1, "status": ["not in", ["Delivered", "Cancelled"]]},
			fields=["name", "item_code", "warehouse", "voucher_type", "voucher_no", "reserved_qty", "delivered_qty", "status", "creation"], order_by="creation desc", limit=200)
		names = _items({s.item_code for s in sre})
		cust = dict(frappe.get_all("Sales Order", filters={"name": ["in", [s.voucher_no for s in sre] or [""]]}, fields=["name", "customer_name"], as_list=True))
		return {"cols": [{"label": _("Item")}, {"label": _("Warehouse")}, {"label": _("Order")}, {"label": _("Customer")}, {"label": _("Reserved"), "cls": "num"},
			{"label": _("Delivered"), "cls": "num"}, {"label": _("Status")}],
			"rows": [{"dt": "Sales Order", "name": s.voucher_no, "cells": [{"main": (names.get(s.item_code) or {}).get("item_name") or s.item_code, "sub": s.item_code},
				s.warehouse, {"link": ["Sales Order", s.voucher_no]}, cust.get(s.voucher_no) or "—", f"{flt(s.reserved_qty):,.0f}", f"{flt(s.delivered_qty):,.0f}",
				{"pill": _(s.status), "tone": "violet" if s.status == "Reserved" else "blue"}]} for s in sre
				if _match(q, s.item_code, s.voucher_no, cust.get(s.voucher_no))], "empty": _("Nothing is reserved.")}
	if tab == "warehouses":
		per, bins, whs = _stock_summary(cos)
		agg = {w: frappe._dict(n=0, qty=0, value=0) for w in whs}
		for b in bins:
			a = agg.setdefault(b.warehouse, frappe._dict(n=0, qty=0, value=0))
			if flt(b.actual_qty):
				a.n += 1
			a.qty += flt(b.actual_qty)
			a.value += flt(b.stock_value)
		total = sum(a.value for a in agg.values()) or 1
		info = {w.name: w for w in frappe.get_all("Warehouse", filters={"name": ["in", list(agg) or [""]]}, fields=["name", "warehouse_type", "company", "city"])}
		return {"cols": [{"label": _("Warehouse")}, {"label": _("Company")}, {"label": _("Items"), "cls": "num"}, {"label": _("Units"), "cls": "num"},
			{"label": _("Value ({0})").format(cur), "cls": "num"}, {"label": _("Share")}],
			"rows": [{"dt": "Warehouse", "name": w, "cells": [{"main": w, "sub": " · ".join(x for x in [(info.get(w) or {}).get("warehouse_type"), (info.get(w) or {}).get("city")] if x)},
				(info.get(w) or {}).get("company") or "—", a.n, f"{a.qty:,.0f}", {"money": a.value}, {"bar": a.value / total * 100}]}
				for w, a in sorted(agg.items(), key=lambda kv: -kv[1].value) if _match(q, w)], "empty": _("No warehouses.")}
	if tab == "ageing":
		per, bins, whs = _stock_summary(cos)
		codes = [c for c, r in per.items() if r.qty > 0]
		last_in = dict(frappe.db.sql("""select item_code, max(posting_date) from `tabStock Ledger Entry` where is_cancelled = 0 and (actual_qty > 0 or voucher_type = 'Stock Reconciliation')
			and warehouse in %s and item_code in %s group by item_code""", (tuple(whs or [""]), tuple(codes or [""])))) if codes else {}
		last_sale = dict(frappe.db.sql("""select i.item_code, max(s.posting_date) from `tabSales Invoice Item` i join `tabSales Invoice` s on s.name = i.parent
			where s.docstatus = 1 and s.is_return = 0 and i.item_code in %s group by i.item_code""", (tuple(codes or [""]),))) if codes else {}
		names = _items(codes)

		def band(days):
			return "0–30" if days <= 30 else "31–90" if days <= 90 else "91–180" if days <= 180 else "180+"

		rows = []
		for c in codes:
			age = (t - getdate(last_in[c])).days if last_in.get(c) else 999
			since = (t - getdate(last_sale[c])).days if last_sale.get(c) else None
			slow = since is None or since > 180
			rows.append((age, {"dt": "Item", "name": c, "cells": [{"code": c}, {"main": (names.get(c) or {}).get("item_name") or c},
				{"date": last_in.get(c)} if last_in.get(c) else "—", {"main": band(age), "sub": _("{0} days").format(age) if age < 999 else ""},
				{"date": last_sale.get(c)} if last_sale.get(c) else {"text": _("Never"), "tone": "red"}, f"{per[c].qty:,.0f}", {"money": per[c].value},
				{"pill": _("Slow-moving") if slow else _("Moving"), "tone": "orange" if slow else "green"}]}))
		rows.sort(key=lambda x: -x[0])
		return {"cols": [{"label": _("Item code")}, {"label": _("Item")}, {"label": _("Last received")}, {"label": _("Age")}, {"label": _("Last sold")},
			{"label": _("On hand"), "cls": "num"}, {"label": _("Value ({0})").format(cur), "cls": "num"}, {"label": _("Status")}],
			"rows": [r for _a, r in rows if _match(q, r["name"], r["cells"][1]["main"])], "empty": _("Nothing in stock.")}
	return {"cols": [], "rows": []}


# ---------------------------------------------------------------- UAE VAT & E-invoicing
TAX_TONE = {"Prepared": "blue", "Pending Finance Manager": "orange", "Approved": "violet", "Submitted": "blue", "Paid": "green", "Rejected": "red"}
EMIRATES = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Umm Al Quwain", "Ras Al Khaimah", "Fujairah"]


def _vat_figures(cos, start, end):
	"""The VAT 201 boxes for the period, computed the same way the Tax Return does (not saved)."""
	tot = frappe._dict(standard_rated_sales=0, output_vat=0, zero_rated_sales=0, exempt_sales=0, reverse_charge_base=0, reverse_charge_vat=0,
		standard_rated_expenses=0, input_vat=0, lines={})
	for co in cos:
		tr = frappe.new_doc("Tax Return")
		tr.update({"tax_type": "VAT 201", "company": co, "period_from": start, "period_to": end})
		try:
			tr.fetch_vat()
		except Exception:
			frappe.clear_last_message()
			continue
		for k in list(tot):
			if k != "lines":
				tot[k] += flt(tr.get(k))
		for ln in json.loads(tr.vat_lines or "[]"):
			x = tot.lines.setdefault(ln["emirate"], [0, 0])
			x[0] += flt(ln["amount"])
			x[1] += flt(ln["vat"])
	if "" in tot.lines or None in tot.lines:
		_split_by_address(tot, cos, start, end)
	tot.net = tot.output_vat + tot.reverse_charge_vat - tot.input_vat
	return tot


def _emirate(*texts):
	for t in texts:
		t = (t or "").lower().replace("-", " ")
		for em in EMIRATES:
			if em.lower() in t or (em == "Ras Al Khaimah" and "rak" in t.split()) or (em == "Umm Al Quwain" and "umm al" in t):
				return em
	return None


def _split_by_address(tot, cos, start, end):
	"""Invoices without an emirate are placed by the customer's address (else the company's emirate), as the prototype does."""
	blank = tot.lines.pop("", None) or [0, 0]
	none = tot.lines.pop(None, None) or [0, 0]
	left = [blank[0] + none[0], blank[1] + none[1]]
	home = {}
	for co in cos:
		addr = frappe.db.sql("""select a.city, a.state, a.address_line1 from `tabAddress` a join `tabDynamic Link` l on l.parent = a.name
			where l.link_doctype = 'Company' and l.link_name = %s limit 1""", co, as_dict=True)
		home[co] = _emirate(*(addr[0].values() if addr else [])) or "Dubai"
	rows = frappe.db.sql("""select s.company, s.base_net_total amt, s.base_total_taxes_and_charges vat, a.city, a.state, a.address_line1
		from `tabSales Invoice` s left join `tabAddress` a on a.name = coalesce(s.shipping_address_name, s.customer_address)
		where s.docstatus = 1 and s.company in %s and s.posting_date between %s and %s and s.base_total_taxes_and_charges <> 0
		and coalesce(s.vat_emirate, '') = ''""", (tuple(cos), start, end), as_dict=True) \
		if frappe.get_meta("Sales Invoice").has_field("vat_emirate") else []
	placed = [0, 0]
	for r in rows:
		em = _emirate(r.state, r.city, r.address_line1) or home.get(r.company, "Dubai")
		x = tot.lines.setdefault(em, [0, 0])
		x[0] += flt(r.amt)
		x[1] += flt(r.vat)
		placed[0] += flt(r.amt)
		placed[1] += flt(r.vat)
	rest = [left[0] - placed[0], left[1] - placed[1]]
	if abs(rest[0]) > 0.01 or abs(rest[1]) > 0.01:
		x = tot.lines.setdefault(home.get(cos[0], "Dubai") if cos else "Dubai", [0, 0])
		x[0] += rest[0]
		x[1] += rest[1]


def _trn_missing(cos, start, end):
	if not _perm("Sales Invoice"):
		return []
	return frappe.db.sql_list("""select distinct s.customer_name from `tabSales Invoice` s join `tabCustomer` c on c.name = s.customer
		where s.docstatus = 1 and s.company in %s and s.posting_date between %s and %s and s.total_taxes_and_charges <> 0
		and c.customer_type = 'Company' and coalesce(c.tax_id, '') = ''""", (tuple(cos), start, end))


def vat_module():
	cos, start, end, label, cur = _scope()
	v = _vat_figures(cos, start, end)
	from hipersign_trading.hipersign_trading.doctype.tax_return.tax_return import due_date

	due = due_date("VAT 201", end)
	left = (getdate(due) - getdate(today())).days if due else None
	returns = frappe.get_list("Tax Return", filters={"company": ["in", cos], "tax_type": "VAT 201"}, fields=["name", "status", "period_from"],
		order_by="period_from desc", limit=24) if frappe.db.table_exists("Tax Return") and _perm("Tax Return") else []
	pending = [r for r in returns if r.status in ("Prepared", "Pending Finance Manager", "Approved")]
	this = next((r for r in returns if getdate(r.period_from) == getdate(start)), None)
	missing = _trn_missing(cos, start, end)
	return {
		"title": _("UAE VAT & E-invoicing"),
		"desc": _("Prepare, approve, lock and file the VAT 201 return, record the payment, and get ready for UAE e-invoicing — from the same invoices and bills."),
		"new": [{"label": _("Prepare VAT return"), "doctype": "Tax Return", "primary": 1}],
		"kpis": [
			kpi(_("Output VAT — {0}").format(label), v.output_vat + v.reverse_charge_vat, _("On {0} of sales").format(_fmt(v.standard_rated_sales, cur)), "blue",
				"file", True, cur, tab="sales"),
			kpi(_("Input VAT — {0}").format(label), v.input_vat, _("Recoverable on purchases"), "green", "shopping-cart", True, cur, tab="purchases"),
			kpi(_("Net VAT payable"), v.net, _("Due {0}").format(frappe.utils.formatdate(due, "dd MMM yyyy")) + (f" · {_('{0} days left').format(left)}" if left is not None and left >= 0 else ""),
				"red" if left is not None and left < 7 else "violet", "receipt", True, cur, tab="return"),
			kpi(_("Return status"), _(this.status) if this else _("Period open"), (_("1 return in progress") if len(pending) == 1 else _("{0} returns in progress").format(len(pending))) if pending else _("Nothing waiting"),
				"amber" if pending else "navy", "inbox", tab="history"),
			kpi(_("Buyer TRN missing"), len(missing), ", ".join(missing[:2]) or _("All B2B invoices carry a TRN"), "red" if missing else "green", "triangle-alert", tab="readiness"),
		],
		"tabs": [
			{"key": "return", "label": _("VAT 201 — {0}").format(label), "chips": []},
			{"key": "history", "label": _("Return history"), "chips": []},
			{"key": "sales", "label": _("Sales invoices"), "chips": [["all", _("All")], ["std", _("Standard rated")], ["zero", _("Zero rated")], ["notrn", _("TRN missing")]]},
			{"key": "purchases", "label": _("Purchase bills"), "chips": []},
			{"key": "readiness", "label": _("E-invoicing readiness"), "chips": []},
		],
		"default_tab": "return",
		"links": [[_("UAE VAT 201 report"), ["query-report", "UAE VAT 201"]], [_("Corporate tax"), ["List", "Tax Return"], {"tax_type": "Corporate Tax"}]],
	}


def vat_rows(tab, chip, q=None):
	cos, start, end, label, cur = _scope()
	if tab == "return":
		v = _vat_figures(cos, start, end)
		rows = []
		if v.lines:
			for i, em in enumerate(EMIRATES):
				a, t = v.lines.get(em, [0, 0])
				rows.append([f"1{'abcdefg'[i]}", _("Standard rated supplies — {0}").format(_(em)), a, t])
		else:
			rows.append(["1", _("Standard rated supplies"), v.standard_rated_sales, v.output_vat])
		rows += [["3", _("Supplies subject to reverse charge"), v.reverse_charge_base, v.reverse_charge_vat],
			["4", _("Zero-rated supplies"), v.zero_rated_sales, 0], ["5", _("Exempt supplies"), v.exempt_sales, 0],
			["8", _("Total output"), v.standard_rated_sales + v.reverse_charge_base + v.zero_rated_sales + v.exempt_sales, v.output_vat + v.reverse_charge_vat],
			["9", _("Standard rated expenses"), v.standard_rated_expenses, v.input_vat],
			["11", _("Total input"), None, v.input_vat], ["", _("Net VAT payable"), None, v.net]]
		return {"cols": [{"label": _("Box")}, {"label": _("Description")}, {"label": _("Amount ({0})").format(cur), "cls": "num"}, {"label": _("VAT ({0})").format(cur), "cls": "num"}],
			"rows": [{"cells": [{"code": b} if b else "", {"main": d} if b in ("8", "11", "") else d, {"money": a} if a is not None else "", {"money": t}]} for b, d, a, t in rows]}
	if tab == "history":
		if not (frappe.db.table_exists("Tax Return") and _perm("Tax Return")):
			return {"cols": [], "rows": []}
		rs = frappe.get_list("Tax Return", filters={"company": ["in", cos], "tax_type": "VAT 201"}, fields=_fields("Tax Return", ["name", "company", "period_from", "period_to",
			"due_date", "net_vat", "status", "emaratax_reference", "paid_on"]), order_by="period_from desc", limit=36)
		return {"cols": [{"label": _("Period")}, {"label": _("Company")}, {"label": _("Due")}, {"label": _("Net VAT"), "cls": "num"}, {"label": _("Status")},
			{"label": _("Acknowledgement")}, {"label": _("Paid")}],
			"rows": [{"dt": "Tax Return", "name": r.name, "cells": [{"main": getdate(r.period_from).strftime("%B %Y"), "sub": r.name}, r.company,
				{"date": r.due_date, "late": bool(r.due_date and r.status not in ("Paid",) and getdate(r.due_date) < getdate(today()))}, {"money": r.net_vat},
				{"pill": _(r.status), "tone": TAX_TONE.get(r.status, "grey")}, r.emaratax_reference or "—", {"date": r.paid_on} if r.paid_on else "—"]} for r in rs],
			"empty": _("No VAT returns yet — use “Prepare VAT return”.")}
	if tab == "sales":
		if not _perm("Sales Invoice"):
			return {"cols": [], "rows": []}
		inv = frappe.get_list("Sales Invoice", filters={"company": ["in", cos], "docstatus": 1, "posting_date": ["between", [start, end]]},
			fields=["name", "customer", "customer_name", "posting_date", "base_net_total", "base_total_taxes_and_charges", "base_grand_total", "is_return", "tax_id"],
			order_by="posting_date desc", limit=500)
		info = {c.name: c for c in frappe.get_all("Customer", filters={"name": ["in", list({i.customer for i in inv}) or [""]]}, fields=["name", "tax_id", "customer_type"])}
		rows = []
		for i in inv:
			c = info.get(i.customer) or frappe._dict()
			trn = i.tax_id or c.tax_id
			b2b = c.customer_type == "Company"
			zero = not flt(i.base_total_taxes_and_charges)
			if chip == "std" and zero or chip == "zero" and not zero or chip == "notrn" and (trn or not b2b or zero):
				continue
			if not _match(q, i.name, i.customer_name):
				continue
			rows.append({"dt": "Sales Invoice", "name": i.name, "cells": [{"code": i.name}, {"main": i.customer_name, "sub": _("Credit note") if i.is_return else ""},
				{"code": trn} if trn else ({"text": _("Missing"), "tone": "red"} if b2b and not zero else "—"), {"date": i.posting_date},
				{"money": i.base_net_total}, {"money": i.base_total_taxes_and_charges}, {"pill": _("Zero rated") if zero else _("Standard 5%"), "tone": "grey" if zero else "blue"}]})
		return {"cols": [{"label": _("Invoice")}, {"label": _("Customer")}, {"label": _("Buyer TRN")}, {"label": _("Date")}, {"label": _("Net ({0})").format(cur), "cls": "num"},
			{"label": _("VAT"), "cls": "num"}, {"label": _("Treatment")}], "rows": rows, "empty": _("No invoices in this period.")}
	if tab == "purchases":
		if not _perm("Purchase Invoice"):
			return {"cols": [], "rows": []}
		inv = frappe.get_list("Purchase Invoice", filters={"company": ["in", cos], "docstatus": 1, "posting_date": ["between", [start, end]]},
			fields=["name", "supplier", "supplier_name", "bill_no", "posting_date", "base_net_total", "base_total_taxes_and_charges", "currency"], order_by="posting_date desc", limit=500)
		trn = dict(frappe.get_all("Supplier", filters={"name": ["in", list({i.supplier for i in inv}) or [""]]}, fields=["name", "tax_id"], as_list=True))
		return {"cols": [{"label": _("Bill")}, {"label": _("Supplier")}, {"label": _("Supplier TRN")}, {"label": _("Date")}, {"label": _("Net ({0})").format(cur), "cls": "num"},
			{"label": _("Input VAT"), "cls": "num"}, {"label": _("Treatment")}],
			"rows": [{"dt": "Purchase Invoice", "name": i.name, "cells": [{"code": i.name}, {"main": i.supplier_name, "sub": i.bill_no or ""},
				{"code": trn[i.supplier]} if trn.get(i.supplier) else "—", {"date": i.posting_date}, {"money": i.base_net_total}, {"money": i.base_total_taxes_and_charges},
				{"pill": _("Import") if i.currency != cur else _("Standard 5%") if flt(i.base_total_taxes_and_charges) else _("No VAT"),
					"tone": "violet" if i.currency != cur else "blue" if flt(i.base_total_taxes_and_charges) else "grey"}]}
				for i in inv if _match(q, i.name, i.supplier_name, i.bill_no)], "empty": _("No supplier bills in this period.")}
	if tab == "readiness":
		def chk(label, ok, sub=""):
			return {"cells": [{"main": label, "sub": sub}, {"pill": _("Ready") if ok else _("Open"), "tone": "green" if ok else "orange"}]}

		co_trn = all(frappe.get_cached_value("Company", c, "tax_id") for c in cos)
		missing = _trn_missing(cos, add_days(start, -90), end)
		items = frappe.get_all("Item", filters={"disabled": 0, "is_sales_item": 1}, fields=_fields("Item", ["name", "customs_tariff_number", "hs_item_name_ar"])) if _perm("Item") else []
		no_hs = [i.name for i in items if not i.get("customs_tariff_number") or ("hs_item_name_ar" in i and not i.get("hs_item_name_ar"))]
		vat_set = all(frappe.db.exists("UAE VAT Settings", c) for c in cos)
		rows = [
			chk(_("Company TRN on all tax documents"), co_trn, "" if co_trn else _("Set the Tax ID on each company")),
			chk(_("Customer TRN captured for B2B buyers"), not missing, _("{0} customer(s) missing: {1}").format(len(missing), ", ".join(missing[:3])) if missing else ""),
			chk(_("Item HS codes & Arabic descriptions"), not no_hs, _("{0} item(s) incomplete").format(len(no_hs)) if no_hs else ""),
			chk(_("UAE VAT Settings (VAT accounts) per company"), vat_set, "" if vat_set else _("Needed for the emirate split in box 1")),
			chk(_("PINT AE (Peppol) mapping of Sales Invoice fields"), False, _("In implementation")),
			chk(_("Accredited Service Provider selected"), False, _("Not selected")),
		]
		return {"cols": [{"label": _("Check")}, {"label": _("Status")}], "rows": rows}
	return {"cols": [], "rows": []}
