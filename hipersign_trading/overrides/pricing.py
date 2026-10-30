"""v1.6.0 (SAL-02): a sales person's extra discount survives saving.

ERPNext re-applies the customer group's pricing rule on every save and puts its discount back on the line, so a 15%
discount typed on an order for a Contractor (5% rule) silently became 5% — the order never reached the Sales Manager.
The rule stays the floor: a higher discount typed by the user is kept (and the approval rules then see it); a lower
one still gets the rule's discount, as before.
"""

import frappe
from frappe.utils import flt


def remember(doc, method=None):
	if doc.docstatus != 0:
		return
	doc.flags.hs_typed_discount = {i.idx: flt(i.discount_percentage) for i in doc.get("items") or []}


def keep(doc):
	typed = doc.flags.pop("hs_typed_discount", None)
	if not typed or doc.docstatus != 0:
		return
	changed = False
	for i in doc.get("items") or []:
		d = typed.get(i.idx)
		if d and d > flt(i.discount_percentage) and d <= 100 and flt(i.price_list_rate):
			i.discount_percentage = d
			i.rate = flt(flt(i.price_list_rate) * (1 - d / 100.0), i.precision("rate"))
			changed = True
	if changed:
		doc.calculate_taxes_and_totals()
