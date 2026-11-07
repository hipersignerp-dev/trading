"""v1.8.4: document numbers follow each company's own series, as in the demo — a new sales order of the lighting factory is
MSO-2026-0227, not SAL-ORD-2026-00022; a project purchase order of Golden Dragon is PJPO-2026-037. Companies without their
own series keep ERPNext's. The series are added to the doctypes' naming-series options and their counters start after the
highest number already used (after_migrate)."""

import re

import frappe
from frappe.utils import getdate, today

HLI, GDI = "Hipersign Lighting Industries FZE", "Golden Dragon Interiors LLC"
SERIES = {
	HLI: {"Sales Order": "MSO-.YYYY.-.####", "Purchase Order": "PO-LI-.YYYY.-.####", "Material Request": "MMR-.YYYY.-.###",
		"Purchase Receipt": "GRN-LI-.####", "Delivery Note": "DN-LI-.####", "Sales Invoice": "INV-LI-.####"},
	GDI: {"Purchase Order": "PJPO-.YYYY.-.###", "Material Request": "PMR-.YYYY.-.###", "Purchase Receipt": "GRN-.YYYY.-.####"},
}
DOCTYPES = sorted({dt for m in SERIES.values() for dt in m})


def company_series(doc, method=None):
	"""before_insert: the company's own series, unless the user picked another one or the record is a return."""
	s = SERIES.get(doc.get("company") or "", {}).get(doc.doctype)
	if not s or doc.get("is_return") or doc.get("amended_from"):
		return
	default = (frappe.get_meta(doc.doctype).get_field("naming_series").options or "").split("\n")[0].strip()
	if not doc.get("naming_series") or doc.naming_series == default:
		doc.naming_series = s


def _prefix(series, year):
	"""'MSO-.YYYY.-.####' → ('MSO-2026-', 4)."""
	parts = [p for p in series.split(".") if p != ""]
	digits = len(parts[-1]) if parts and set(parts[-1]) == {"#"} else 5
	pre = "".join(str(year) if p == "YYYY" else p for p in parts[:-1])
	return pre, digits


def ensure_series():
	"""Options on the naming-series fields, and counters past the highest number in use (so nothing clashes)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for dt in DOCTYPES:
		f = frappe.get_meta(dt).get_field("naming_series")
		if not f:
			continue
		opts = [o for o in (f.options or "").split("\n") if o.strip()]
		add = [s[dt] for s in SERIES.values() if dt in s and s[dt] not in opts]
		if add:
			make_property_setter(dt, "naming_series", "options", "\n".join(opts + add), "Text", validate_fields_for_doctype=False)
	year = getdate(today()).year
	for m in SERIES.values():
		for dt, s in m.items():
			pre, _d = _prefix(s, year)
			names = frappe.get_all(dt, filters={"name": ["like", pre + "%"]}, pluck="name")
			top = max([int(n[len(pre):]) for n in names if re.fullmatch(r"\d+", n[len(pre):] or "")] or [0])
			cur = frappe.db.sql("select current from `tabSeries` where name = %s", pre)
			if not cur:
				frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (pre, top))
			elif int(cur[0][0] or 0) < top:
				frappe.db.sql("update `tabSeries` set current = %s where name = %s", (top, pre))
