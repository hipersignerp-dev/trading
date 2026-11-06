"""v1.8.3 (prototype p20): the look — chart style preset and brand colour (Hipersign Settings › Look & menus, for the
whole site) and each user's own chart types (bars, line, area or table, chosen on the chart itself)."""

import json

import frappe

STYLES = {"Hipersign": "hip", "Soft": "soft", "Glow": "glow", "Classic": "classic"}
TYPES = {"bar", "line", "area", "table"}
KEY = "hs_chart_types"


def boot_look():
	s = frappe.get_cached_doc("Hipersign Settings")
	return {
		"chart_style": STYLES.get(s.get("chart_style") or "Hipersign", "hip"),
		"brand_colour": s.get("chart_brand_colour") or None,
		"bands": 0 if s.get("graph_bands") == 0 else 1,
	}


def chart_types():
	try:
		v = frappe.defaults.get_user_default(KEY)
		return json.loads(v) if v else {}
	except Exception:
		return {}


@frappe.whitelist(methods=["POST"])
def set_chart_type(key, chart_type):
	"""The chart type a user picked on one chart, kept for that user."""
	if chart_type not in TYPES or not key or len(key) > 40:
		frappe.throw(frappe._("Unknown chart type"))
	t = chart_types()
	t[key] = chart_type
	if len(t) > 400:  # keep the stored list small
		t = dict(list(t.items())[-400:])
	frappe.defaults.set_user_default(KEY, json.dumps(t, separators=(",", ":")))
	return t


@frappe.whitelist(methods=["POST"])
def reset_chart_types():
	frappe.defaults.clear_user_default(KEY)
	return {}
