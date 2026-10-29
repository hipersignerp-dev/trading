"""v1.6.0: the guided tour — the prototype's 13 chapters, stored as data in tour/tour.json.

Each step opens a page, highlights one part of it and explains it. The tour only reads and points, so it is safe on
any site. Steps whose page the user cannot open, or whose feature is switched off, are left out.
"""

import json
import os

import frappe
from frappe import _


def _load():
	with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "tour", "tour.json"), encoding="utf-8") as f:
		return json.load(f)


def _route_ok(route):
	from hipersign_trading.api.home import _route_ok as ok

	if route and route[0] == "Form":
		return bool(frappe.has_permission(route[1], "read"))
	return ok(route)


@frappe.whitelist()
def get_tour():
	data = _load()
	from hipersign_trading.features import FEATURES, feature_on

	out = []
	for s in data["steps"]:
		f = s.get("feature")
		if f == "compliance":
			f = "codocs"
		if f and f in FEATURES and not feature_on(f):
			continue
		if not _route_ok(s["route"]):
			continue
		out.append(dict(s, title=_(s["title"]), text=_(s["text"])))
	used = sorted({s["chapter"] for s in out})
	return {"chapters": [{"n": i, "label": _(c)} for i, c in enumerate(data["chapters"]) if i in used], "steps": out}
