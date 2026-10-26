"""Internal estimated margin on quotations (never printed)."""

import frappe
from frappe.utils import flt

from hipersign_trading.utils import valuation_rate


def validate(doc, method=None):
	net = sum(flt(i.base_net_amount) for i in doc.items)
	cost = sum(flt(i.stock_qty or i.qty) * valuation_rate(i.item_code, i.warehouse) for i in doc.items)
	doc.hs_estimated_gross_profit = net - cost
	doc.hs_estimated_margin = ((net - cost) / net * 100) if net else 0

	if doc.quotation_to == "Lead" and doc.party_name and doc.docstatus < 2:
		stage = frappe.db.get_value("Lead", doc.party_name, "hs_pipeline_stage")
		if stage in ("New", "Contacted", "Qualified"):
			frappe.db.set_value("Lead", doc.party_name, {"hs_pipeline_stage": "Proposal", "hs_probability": 60})
