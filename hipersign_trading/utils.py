import frappe
from frappe.utils import flt

from hipersign_trading.constants import SETTINGS


def settings():
	return frappe.get_cached_doc(SETTINGS)


def user_company(user=None):
	"""The company the user works in: the top bar scope (user default "Company"), else Hipersign Settings, else the global default."""
	company = frappe.defaults.get_user_default("Company", user=user)
	if not company or not frappe.db.exists("Company", company):
		company = settings().get("company") or frappe.defaults.get_global_default("company")
	return company


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


def money(v, currency=None, precision=2):
	"""An amount the way the prototype writes it: currency code first (AED 1,234.50), never the local symbol."""
	from frappe.utils import flt, fmt_money

	currency = currency or frappe.db.get_default("currency") or "AED"
	return f"{currency} {fmt_money(flt(v), precision=precision)}"


def can_read(doctype, name=None):
	"""Read permission without the "does not have doctype access" pop-ups Frappe queues even when asked not to."""
	import frappe.permissions

	log = getattr(frappe.local, "message_log", None)
	n = len(log) if log is not None else 0
	try:
		return frappe.permissions.has_permission(doctype, "read", name, print_logs=False)
	except Exception:
		return False
	finally:
		if log is not None:
			del frappe.local.message_log[n:]
