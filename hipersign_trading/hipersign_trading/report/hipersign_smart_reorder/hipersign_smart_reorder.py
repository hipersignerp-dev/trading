# Copyright (c) 2026, Hipersign
"""Smart reorder: what to buy now, from whom and how much.

For every stock item: average daily sales over the history window (adjusted for the last 30 days' trend),
lead time (item → default supplier → country of origin), safety stock, reorder point, and projected stock
(on hand − reserved for orders + on order). When projected stock is at or below the reorder point the report
suggests enough for the cover period, rounded up to whole purchase units (e.g. cartons) and never below the
item's minimum order quantity, from the item's default supplier.
"""

import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, today

from hipersign_trading.constants import LEAD_DAYS_BY_ORIGIN, LEAD_DAYS_DEFAULT
from hipersign_trading.utils import settings, user_company


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = suggestions(filters)
	if filters.get("only_to_order"):
		rows = [r for r in rows if r["suggested_qty"] > 0]
	return columns(), rows, None, chart(rows)


def columns():
	c = lambda fn, label, ft="Float", w=110, opt=None: {"fieldname": fn, "label": _(label), "fieldtype": ft, "width": w, **({"options": opt} if opt else {})}
	return [
		c("item_code", "Item", "Link", 180, "Item"), c("item_name", "Item name", "Data", 180), c("supplier", "Supplier", "Link", 170, "Supplier"),
		c("daily_demand", "Sells / day", "Float", 90), c("trend", "Trend", "Data", 80), c("lead_time", "Lead time (days)", "Int", 100),
		c("safety_stock", "Safety stock"), c("reorder_point", "Reorder point"), c("actual_qty", "On hand"), c("reserved_qty", "Reserved"),
		c("ordered_qty", "On order"), c("projected_qty", "Projected"), c("cover_days", "Lasts (days)", "Int", 90),
		c("pack", "Purchase unit", "Data", 120), c("min_order_qty", "Min. order"), c("suggested_qty", "Suggested qty", "Float", 110),
		c("suggested_value", "Value (company currency)", "Currency", 140), c("urgent", "Urgent", "Check", 70),
	]


def lead_time(item, supplier):
	if cint(item.lead_time_days):
		return cint(item.lead_time_days)
	if supplier and frappe.get_meta("Supplier").has_field("hs_lead_time_days"):
		d = cint(frappe.db.get_value("Supplier", supplier, "hs_lead_time_days"))
		if d:
			return d
	return LEAD_DAYS_BY_ORIGIN.get(item.country_of_origin, LEAD_DAYS_DEFAULT)


def default_supplier(item_code, company):
	sup = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "default_supplier")
	if sup:
		return sup
	last = frappe.db.sql("""select po.supplier from `tabPurchase Order Item` poi join `tabPurchase Order` po on po.name = poi.parent
		where poi.item_code=%s and po.docstatus=1 order by po.transaction_date desc limit 1""", item_code)
	return last[0][0] if last else None


def purchase_pack(item):
	"""Sales units per purchase unit, from the item's UOM conversion table."""
	if item.purchase_uom and item.purchase_uom != item.stock_uom:
		f = flt(frappe.db.get_value("UOM Conversion Detail", {"parent": item.name, "uom": item.purchase_uom}, "conversion_factor"))
		if f > 1:
			return item.purchase_uom, f
	return item.stock_uom, 1


def suggestions(filters=None):
	filters = frappe._dict(filters or {})
	s = settings()
	window = cint(filters.get("history_days") or s.get("reorder_history_days") or 60)
	cover = cint(filters.get("cover_days") or s.get("reorder_cover_days") or 60)
	safety = flt(s.get("reorder_safety_factor") if s.get("reorder_safety_factor") is not None else 0.5)
	company = filters.get("company") or user_company()
	item_filters = {"is_stock_item": 1, "disabled": 0}
	if filters.get("item_group"):
		item_filters["item_group"] = filters.item_group
	items = frappe.get_all("Item", filters=item_filters,
		fields=["name", "item_name", "stock_uom", "purchase_uom", "min_order_qty", "lead_time_days", "country_of_origin", "valuation_rate"])
	start, recent = add_days(today(), -window), add_days(today(), -30)
	out_qty = {r[0]: (flt(r[1]), flt(r[2])) for r in frappe.db.sql(
		"""select item_code, -sum(actual_qty), -sum(case when posting_date >= %s then actual_qty else 0 end)
		from `tabStock Ledger Entry` where is_cancelled=0 and actual_qty < 0 and posting_date >= %s
		and voucher_type in ('Delivery Note', 'Sales Invoice') group by item_code""", (recent, start))}
	bins = {r[0]: (flt(r[1]), flt(r[2]), flt(r[3])) for r in frappe.db.sql(
		"""select item_code, sum(actual_qty), sum(reserved_qty), sum(ordered_qty) from `tabBin` group by item_code""")}
	rows = []
	for it in items:
		if filters.get("supplier") and default_supplier(it.name, company) != filters.supplier:
			continue
		sold, sold30 = out_qty.get(it.name, (0, 0))
		avg = sold / window if window else 0
		trend = (sold30 / 30) / avg if avg else 1
		adj = avg * min(1.5, max(0.6, trend))
		sup = default_supplier(it.name, company)
		lt = lead_time(it, sup)
		ss = math.ceil(adj * lt * safety)
		rop = math.ceil(adj * lt + ss)
		on_hand, reserved, ordered = bins.get(it.name, (0, 0, 0))
		proj = on_hand - reserved + ordered
		uom, pack = purchase_pack(it)
		need = max(0, rop + adj * cover - proj)
		sugg = 0
		if proj <= rop and need > 0:
			sugg = max(flt(it.min_order_qty), math.ceil(need / pack) * pack)
		cover_days = int(proj / adj) if adj > 0 else None
		rows.append({
			"item_code": it.name, "item_name": it.item_name, "supplier": sup, "daily_demand": flt(adj, 2),
			"trend": _("rising") if trend > 1.15 else _("slowing") if trend < 0.85 else _("steady"),
			"lead_time": lt, "safety_stock": ss, "reorder_point": rop, "actual_qty": on_hand, "reserved_qty": reserved, "ordered_qty": ordered,
			"projected_qty": proj, "cover_days": cover_days, "pack": f"1 {uom} = {flt(pack):g} {it.stock_uom}" if pack > 1 else it.stock_uom,
			"min_order_qty": flt(it.min_order_qty), "suggested_qty": sugg, "suggested_value": flt(sugg * flt(it.valuation_rate), 2),
			"urgent": 1 if cover_days is not None and cover_days < lt else 0, "stock_uom": it.stock_uom,
		})
	rows.sort(key=lambda r: (r["suggested_qty"] <= 0, r["cover_days"] if r["cover_days"] is not None else 99999))
	return rows


def chart(rows):
	top = [r for r in rows if r["suggested_qty"] > 0][:10]
	if not top:
		return None
	return {"data": {"labels": [r["item_code"] for r in top], "datasets": [{"name": _("Suggested value"), "values": [r["suggested_value"] for r in top]}]},
		"type": "bar", "colors": ["#2563eb"]}


@frappe.whitelist()
def make_purchase_orders(items, company=None):
	"""Draft purchase orders, one per supplier, for the ticked suggestions. Approval follows the PO workflow."""
	frappe.has_permission("Purchase Order", "create", throw=True)
	items = frappe.parse_json(items) if isinstance(items, str) else items
	company = company or user_company()
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	by_sup = {}
	for r in items:
		if not r.get("supplier") or flt(r.get("suggested_qty")) <= 0:
			continue
		by_sup.setdefault(r["supplier"], []).append(r)
	if not by_sup:
		frappe.throw(_("Pick rows that have a supplier and a suggested quantity."))
	made = []
	for sup, rows in by_sup.items():
		lt = max(cint(r.get("lead_time")) for r in rows)
		po = frappe.get_doc({"doctype": "Purchase Order", "supplier": sup, "company": company, "transaction_date": today(),
			"schedule_date": add_days(today(), lt or 30),
			"items": [{"item_code": r["item_code"], "qty": flt(r["suggested_qty"]), "schedule_date": add_days(today(), lt or 30)} for r in rows]})
		po.set_missing_values()
		# v1.5.6 (RO-01): a foreign-currency supplier (e.g. CNY) needs the rate filled before insert
		if po.currency and po.currency != company_currency and not flt(po.conversion_rate):
			from erpnext.setup.utils import get_exchange_rate

			po.conversion_rate = flt(get_exchange_rate(po.currency, company_currency, po.transaction_date, "for_buying"))
			if not po.conversion_rate:
				frappe.throw(_("No exchange rate from {0} to {1}. Add it in Currency Exchange and try again.").format(po.currency, company_currency))
		po.insert()
		po.add_comment("Info", _("Created from Smart reorder"))
		made.append(po.name)
	return made
