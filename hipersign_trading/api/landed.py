"""v1.5 — Import Costs & Profitability: what each shipment really cost and what each item really earns."""

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, get_first_day, today

from hipersign_trading.utils import settings

GROUPS = {
	"Freight & Shipping": "freight", "Insurance": "insurance", "Customs Duty": "duty", "Clearing Charges": "clearing", "Handling": "handling",
}


def _bucket(charge_type):
	for k, v in GROUPS.items():
		if (charge_type or "").startswith(k.split(" ")[0]):
			return v
	return "other"


def shipments(company=None):
	f = {} if not company else {"company": company}
	out = []
	for s in frappe.get_all("Import Shipment", filters=f, fields=["name", "status", "goods_value", "total_charges", "landed_cost_voucher", "company", "eta"],
			order_by="creation desc", limit=40):
		row = {"name": s.name, "status": s.status, "goods": flt(s.goods_value), "lcv": s.landed_cost_voucher, "company": s.company,
			"freight": 0, "insurance": 0, "duty": 0, "clearing": 0, "handling": 0, "other": 0}
		for c in frappe.get_all("Shipment Charge", filters={"parent": s.name, "parenttype": "Import Shipment"}, fields=["charge_type", "amount"]):
			row[_bucket(c.charge_type)] += flt(c.amount)
		row["charges"] = sum(row[k] for k in ("freight", "insurance", "duty", "clearing", "handling", "other"))
		row["uplift"] = round(row["charges"] / row["goods"] * 100, 1) if row["goods"] else 0
		out.append(row)
	return out


def stack(name):
	s = frappe.get_doc("Import Shipment", name)
	s.check_permission("read")
	row = next((r for r in shipments() if r["name"] == name), None) or {}
	# the items in the shipment's purchase orders, with the charges spread by value
	lines = {}
	for p in s.purchase_orders:
		if not p.purchase_order:
			continue
		for i in frappe.get_all("Purchase Order Item", filters={"parent": p.purchase_order}, fields=["item_code", "item_name", "qty", "base_net_amount"]):
			x = lines.setdefault(i.item_code, {"item": i.item_name, "qty": 0, "value": 0})
			x["qty"] += flt(i.qty)
			x["value"] += flt(i.base_net_amount)
	goods = sum(x["value"] for x in lines.values()) or flt(s.goods_value)
	charges = row.get("charges", flt(s.total_charges))
	items = [{"item": x["item"], "qty": x["qty"], "unit": (x["value"] + (charges * x["value"] / goods if goods else 0)) / x["qty"] if x["qty"] else 0}
		for x in sorted(lines.values(), key=lambda v: -v["value"])]
	return {"name": name, "status": s.status, "goods": goods, "freight": row.get("freight", 0), "duty_clearing": row.get("duty", 0) + row.get("clearing", 0),
		"insurance_handling": row.get("insurance", 0) + row.get("handling", 0) + row.get("other", 0), "landed": goods + charges, "items": items[:6]}


def item_margins(company=None):
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	q = (frappe.qb.from_(sii).join(si).on(si.name == sii.parent)
		.select(sii.item_code, Sum(sii.stock_qty), Sum(sii.base_net_amount), Sum(sii.incoming_rate * sii.stock_qty))
		.where((si.docstatus == 1) & (si.is_return == 0) & (si.posting_date >= add_days(today(), -60))).groupby(sii.item_code))
	if company:
		q = q.where(si.company == company)
	sold = {r[0]: (flt(r[1]), flt(r[2]), flt(r[3])) for r in q.run()}
	pl = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	out = []
	for it in frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0}, fields=["name", "item_name", "valuation_rate"]):
		landed = _landed_rate(it.name) or flt(it.valuation_rate)
		lp = flt(frappe.db.get_value("Item Price", {"item_code": it.name, "price_list": pl}, "price_list_rate"))
		q_, sales, cost = sold.get(it.name, (0, 0, 0))
		avg = sales / q_ if q_ else 0
		if q_ and sales:
			margin = (sales - cost) / sales * 100 if cost else ((avg - landed) / avg * 100 if avg else 0)
		else:
			margin = (lp - landed) / lp * 100 if lp else 0
		out.append({"item_code": it.name, "item": it.item_name, "landed": landed, "list": lp, "avg": avg, "qty": q_, "margin": round(margin, 1), "sold": bool(q_)})
	out.sort(key=lambda r: r["margin"])
	return out


def _landed_rate(item_code):
	r = frappe.get_all("Bin", filters={"item_code": item_code, "actual_qty": [">", 0]}, fields=[{"SUM": "stock_value", "as": "v"}, {"SUM": "actual_qty", "as": "q"}])
	if r and flt(r[0].q):
		return flt(r[0].v) / flt(r[0].q)
	return 0.0


@frappe.whitelist()
def get_landed(company=None, shipment=None):
	company = company or None
	ships = shipments(company)
	target = flt(settings().get("target_margin")) or 20
	month = frappe.get_all("Shipment Charge", filters={"parenttype": "Import Shipment", "date": [">=", get_first_day(today())]}, fields=[{"SUM": "amount", "as": "s"}])
	recent = [s for s in ships if s["goods"]]
	uplift = round(sum(s["charges"] for s in recent) / sum(s["goods"] for s in recent) * 100, 1) if recent else 0
	not_in_stock = sum(s["charges"] for s in ships if s["status"] == "Received at Warehouse" and not s["lcv"])
	margins = item_margins(company)
	from hipersign_trading.api.home import ledger, period_range

	start, end, label = period_range("month")
	led = {"revenue": 0, "gross": 0}
	for c in ([company] if company else frappe.get_all("Company", filters={"is_group": 0}, pluck="name")):
		x = ledger(c, start, end)
		led["revenue"] += x["revenue"]
		led["gross"] += x["gross"]
	ship = shipment or (ships[0]["name"] if ships else None)
	return {
		"kpis": {"charges_month": flt(month[0].s) if month else 0, "uplift": uplift, "gross_margin": round(led["gross"] / led["revenue"] * 100, 1) if led["revenue"] else 0,
			"below_target": sum(1 for m in margins if m["sold"] and m["margin"] < target), "not_in_stock": not_in_stock, "period": label},
		"target": target, "shipments": ships, "stack": stack(ship) if ship else None, "margins": margins,
		"items": [{"value": m["item_code"], "label": f"{m['item_code']} — {m['item']}"} for m in sorted(margins, key=lambda m: m["item_code"])],
	}


@frappe.whitelist()
def price_helper(item_code, margin=None):
	margin = flt(margin) or flt(settings().get("target_margin")) or 20
	landed = _landed_rate(item_code) or flt(frappe.db.get_value("Item", item_code, "valuation_rate"))
	pl = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	lp = flt(frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": pl}, "price_list_rate"))
	minimum = landed / (1 - margin / 100) if margin < 100 else 0
	return {"landed": landed, "minimum": minimum, "list": lp, "list_margin": round((lp - landed) / lp * 100, 1) if lp else None, "margin": margin}


@frappe.whitelist()
def get_stack(shipment):
	return stack(shipment)
