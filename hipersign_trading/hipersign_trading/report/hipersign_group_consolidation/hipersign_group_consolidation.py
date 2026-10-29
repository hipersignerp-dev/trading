# Copyright (c) 2026, Hipersign
"""Consolidated profit and loss and balance sheet of the group, translated into one currency."""

import frappe
from frappe import _
from frappe.utils import today

from hipersign_trading.group import consolidate

ORDER = {"Income": 0, "Expense": 1, "Asset": 2, "Liability": 3, "Equity": 4}


def execute(filters=None):
	f = frappe._dict(filters or {})
	c = consolidate(f.period_end or today(), f.currency)
	cur = c["currency"]
	columns = [{"fieldname": "line", "label": _("Line"), "fieldtype": "Data", "width": 300}]
	for m in c["members"]:
		columns.append({"fieldname": frappe.scrub(m["member"]), "label": m["member"], "fieldtype": "Currency", "options": "currency", "width": 150})
	columns += [{"fieldname": "elimination", "label": _("Eliminations"), "fieldtype": "Currency", "options": "currency", "width": 130},
		{"fieldname": "group", "label": _("Group"), "fieldtype": "Currency", "options": "currency", "width": 150},
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "hidden": 1}]
	show = f.show or "Both"
	data, totals = [], {}
	keys = sorted(set(c["lines"]) | set(c["elim"]), key=lambda k: (ORDER.get(k[1], 9), k[2]))
	current = None
	for k in keys:
		report_type, root, name = k
		if show == "Profit and Loss" and report_type != "Profit and Loss" or show == "Balance Sheet" and report_type == "Profit and Loss":
			continue
		if root != current:
			if current:
				data.append(_total(current, totals.get(current, {}), c, cur))
			data.append({"line": _(root), "indent": 0, "bold": 1})
			current = root
		sign = -1 if root in ("Income", "Liability", "Equity") else 1
		row = {"line": name, "indent": 1, "currency": cur}
		tot = 0
		for m in c["members"]:
			v = sign * c["lines"].get(k, {}).get(m["member"], 0)
			row[frappe.scrub(m["member"])] = v
			tot += v
			totals.setdefault(root, {})[m["member"]] = totals.get(root, {}).get(m["member"], 0) + v
		e = sign * c["elim"].get(k, 0)
		row["elimination"], row["group"] = e, tot + e
		totals.setdefault(root, {})["_e"] = totals.get(root, {}).get("_e", 0) + e
		data.append(row)
	if current:
		data.append(_total(current, totals.get(current, {}), c, cur))
	if show != "Balance Sheet":
		p = {"line": _("Profit for the year"), "bold": 1, "currency": cur}
		g = 0
		for m in c["members"]:
			p[frappe.scrub(m["member"])] = m["profit"]
			g += m["profit"]
		inc, exp = totals.get("Income", {}), totals.get("Expense", {})
		p["elimination"] = inc.get("_e", 0) - exp.get("_e", 0)
		p["group"] = g + p["elimination"]
		data.append(p)
		nci = sum(m.get("nci_profit", 0) for m in c["members"])
		if nci:
			data.append({"line": _("— attributable to minority (non-controlling) interests"), "indent": 1, "group": nci, "currency": cur})
			data.append({"line": _("— attributable to the owners of the group"), "indent": 1, "group": p["group"] - nci, "currency": cur})
	if show != "Profit and Loss":
		nci = sum(m.get("nci", 0) for m in c["members"])
		if nci:
			data.append({"line": _("of which minority (non-controlling) interests in equity"), "indent": 1, "group": nci, "currency": cur})
	msg = "<br>".join(frappe.utils.escape_html(n) for n in c["notes"]) if c["notes"] else None
	rates = ", ".join(f"{m['member']}: {m['currency']} {round(m['closing_rate'], 4)} closing / {round(m['average_rate'], 4)} average" for m in c["members"] if m["currency"] != cur)
	if rates:
		msg = ((msg + "<br>") if msg else "") + _("Rates to {0} — {1}").format(cur, rates)
	for row in data:  # v1.5.6: whole cents only, so translation leftovers never print as 2.9e-10
		for k, v in list(row.items()):
			if isinstance(v, float):
				row[k] = 0.0 if abs(v) < 0.005 else round(v, 2)
	return columns, data, msg


def _total(root, t, c, cur):
	row = {"line": _("Total {0}").format(_(root).lower()), "bold": 1, "currency": cur}
	g = 0
	for m in c["members"]:
		row[frappe.scrub(m["member"])] = t.get(m["member"], 0)
		g += t.get(m["member"], 0)
	row["elimination"] = t.get("_e", 0)
	row["group"] = g + t.get("_e", 0)
	return row
