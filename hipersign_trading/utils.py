import frappe
from frappe.utils import flt

from hipersign_trading.constants import SETTINGS


def settings():
	return frappe.get_cached_doc(SETTINGS)


def is_export_customer(customer):
	return bool(customer) and frappe.db.get_value("Customer", customer, "hs_market") == "Export"


def valuation_rate(item_code, warehouse=None):
	"""Landed (moving-average) cost of an item, preferring the warehouse it ships from."""
	if not frappe.db.get_value("Item", item_code, "is_stock_item"):
		return flt(frappe.db.get_value("Item", item_code, "valuation_rate"))
	if warehouse:
		v = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate")
		if v:
			return flt(v)
	rows = frappe.get_all(
		"Bin", filters={"item_code": item_code, "actual_qty": [">", 0]}, fields=["actual_qty", "stock_value"]
	)
	qty, value = sum(flt(r.actual_qty) for r in rows), sum(flt(r.stock_value) for r in rows)
	if qty > 0:
		return value / qty
	return flt(frappe.db.get_value("Item", item_code, "valuation_rate"))


def has_any_role(*roles):
	user_roles = set(frappe.get_roles())
	return bool(user_roles.intersection(roles)) or "System Manager" in user_roles
