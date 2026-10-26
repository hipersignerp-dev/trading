"""Sales order checks: export zero-rating, discount and below-landed-cost approval, credit approval."""

import frappe
from frappe import _
from frappe.utils import flt

from hipersign_trading.utils import is_export_customer, settings, valuation_rate


def validate(doc, method=None):
	s = settings()
	apply_export_terms(doc, s)
	reasons_sm, reasons_fin = [], []

	max_disc = max([flt(i.discount_percentage) for i in doc.items] or [0])
	if max_disc > flt(s.so_max_discount):
		reasons_sm.append(_("Discount {0}% is above the {1}% limit").format(max_disc, s.so_max_discount))

	if s.block_below_landed_cost:
		below = [
			i.item_name
			for i in doc.items
			if frappe.db.get_value("Item", i.item_code, "is_stock_item")
			and flt(i.base_net_rate) < valuation_rate(i.item_code, i.warehouse)
		]
		if below:
			reasons_sm.append(_("Selling below landed cost: {0}").format(", ".join(below)))

	limit, exposure = credit_position(doc)
	if exposure > limit:
		reasons_fin.append(
			_("Credit exposure {0} exceeds the limit {1}").format(fmt(exposure), fmt(limit))
			if limit
			else _("New customer — no credit limit set yet")
		)

	hold = overdue_hold(doc, s)
	if hold:
		reasons_fin.append(hold)

	from hipersign_trading.overrides.advances import set_fields

	set_fields(doc)

	doc.hs_needs_sales_manager = 1 if reasons_sm else 0
	doc.hs_needs_finance = 1 if reasons_fin else 0
	doc.hs_approval_reason = "\n".join(reasons_sm + reasons_fin)


def apply_export_terms(doc, s):
	export = is_export_customer(doc.customer)
	doc.hs_is_export = 1 if export else 0
	template = s.export_tax_template if export else s.local_tax_template
	if template and doc.taxes_and_charges != template:
		doc.taxes_and_charges = template
		doc.set("taxes", [])
		doc.append_taxes_from_master()
		doc.calculate_taxes_and_totals()


def credit_position(doc):
	from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding

	limit = flt(get_credit_limit(doc.customer, doc.company))
	outstanding = flt(get_customer_outstanding(doc.customer, doc.company))
	return limit, outstanding + (0 if doc.docstatus == 1 else flt(doc.base_grand_total))


def overdue_hold(doc, s):
	"""Customers with an invoice overdue beyond the hold limit need the Finance Manager for new orders."""
	days = int(s.get("collection_hold_days") or 0)
	if not days:
		return None
	from frappe.utils import add_days, today

	inv = frappe.db.get_value("Sales Invoice", {"customer": doc.customer, "company": doc.company, "docstatus": 1,
		"outstanding_amount": [">", 0], "due_date": ["<", add_days(today(), -days)]}, ["name", "due_date"], as_dict=True, order_by="due_date asc")
	if inv:
		from frappe.utils import date_diff

		return _("{0} is {1} days overdue — collections hold").format(inv.name, date_diff(today(), inv.due_date))
	return None


def fmt(v):
	return frappe.format_value(v, {"fieldtype": "Currency"})


def on_submit(doc, method=None):
	"""A submitted order from a CRM lead marks the lead as Won."""
	lead = doc.get("hs_lead") or frappe.db.get_value("Customer", doc.customer, "lead_name")
	if lead and frappe.db.exists("Lead", lead):
		if frappe.db.get_value("Lead", lead, "hs_pipeline_stage") != "Won":
			frappe.db.set_value("Lead", lead, {"hs_pipeline_stage": "Won", "hs_probability": 100, "hs_next_follow_up": None})
			frappe.get_doc("Lead", lead).add_comment("Info", _("Won — sales order {0}").format(doc.name))
