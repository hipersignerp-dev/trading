# Copyright (c) 2026, Hipersign
"""Records missing a Required or Blocking document, with any exception asked for (Document Centre)."""

import frappe
from frappe import _

from hipersign_trading.doc_rules import missing_rows


def execute(filters=None):
	f = frappe._dict(filters or {})
	rows = missing_rows(f.reference_doctype, f.document_type)
	if f.company:
		rows = [r for r in rows if not r.company or r.company == f.company]
	if f.level:
		rows = [r for r in rows if r.level == f.level]
	columns = [
		{"fieldname": "reference_doctype", "label": _("Record type"), "fieldtype": "Link", "options": "DocType", "width": 140},
		{"fieldname": "reference_name", "label": _("Record"), "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 170},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 190},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "document_type", "label": _("Missing"), "fieldtype": "Link", "options": "Hipersign Document Type", "width": 190},
		{"fieldname": "level", "label": _("Rule"), "fieldtype": "Data", "width": 90},
		{"fieldname": "waiver", "label": _("Exception"), "fieldtype": "Link", "options": "Document Waiver", "width": 140},
		{"fieldname": "waiver_status", "label": _("Exception status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "due", "label": _("Promised by"), "fieldtype": "Date", "width": 100},
	]
	chart = None
	if rows:
		by = {}
		for r in rows:
			by[r.document_type] = by.get(r.document_type, 0) + 1
		top = sorted(by.items(), key=lambda x: -x[1])[:8]
		chart = {"data": {"labels": [_(k) for k, v in top], "datasets": [{"name": _("Missing"), "values": [v for k, v in top]}]}, "type": "bar", "colors": ["#e24c4c"]}
	summary = [{"value": len(rows), "label": _("Missing documents"), "datatype": "Int", "indicator": "Red" if rows else "Green"},
		{"value": len({(r.reference_doctype, r.reference_name) for r in rows}), "label": _("Records"), "datatype": "Int"},
		{"value": len([r for r in rows if r.waiver]), "label": _("With an exception"), "datatype": "Int", "indicator": "Orange"}]
	return columns, rows, None, chart, summary
