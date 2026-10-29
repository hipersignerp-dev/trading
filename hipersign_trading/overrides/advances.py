"""Customer advances and payment schedules.

A sales order whose payment terms include a line flagged “Advance” (Payment Term → hs_is_advance) cannot be
picked or delivered until that advance is received (Payment Entry against the sales order), unless the rule
is switched off in Hipersign Settings. The order shows Advance required and Advance status.
Advances are applied to the tax invoice with ERPNext's own “Get advances” / allocate advances automatically.
"""

import frappe
from frappe import _
from frappe.utils import flt

from hipersign_trading.utils import settings
from hipersign_trading.features import feature_on


def advance_terms():
	return set(frappe.get_all("Payment Term", filters={"hs_is_advance": 1}, pluck="name")) if frappe.get_meta("Payment Term").has_field("hs_is_advance") else set()


def position(so):
	"""(required, received) in company currency."""
	adv = advance_terms()
	required = sum(flt(r.base_payment_amount) or flt(r.payment_amount) * flt(so.conversion_rate or 1) for r in so.get("payment_schedule") or [] if r.payment_term in adv)
	company_currency = frappe.get_cached_value("Company", so.company, "default_currency")
	paid = flt(so.get("advance_paid"))
	received = paid if (so.get("party_account_currency") or company_currency) == company_currency else paid * flt(so.conversion_rate or 1)
	return flt(required, 2), flt(received, 2)


def status_of(required, received):
	if required <= 0:
		return "Not required"
	if received + 0.5 >= required:
		return "Received"
	return "Part received" if received > 0 else "Waiting"


def set_fields(so):
	if not so.meta.has_field("hs_advance_status"):
		return
	required, received = position(so)
	so.hs_advance_required = required / flt(so.conversion_rate or 1) if so.conversion_rate else required
	so.hs_advance_status = status_of(required, received)


def refresh(so_name):
	so = frappe.get_doc("Sales Order", so_name)
	if not so.meta.has_field("hs_advance_status"):
		return
	before = (so.hs_advance_required, so.hs_advance_status)
	set_fields(so)
	if before != (so.hs_advance_required, so.hs_advance_status):
		so.db_set({"hs_advance_required": so.hs_advance_required, "hs_advance_status": so.hs_advance_status}, update_modified=False)


def check_hold(sales_orders, what):
	if not settings().get("advance_before_delivery"):
		return
	for name in sorted({s for s in sales_orders if s}):
		so = frappe.get_doc("Sales Order", name)
		required, received = position(so)
		if status_of(required, received) in ("Waiting", "Part received"):
			from hipersign_trading.overrides.kyc import _use_waiver

			if _use_waiver("Sales Order", name, "Advance payment"):
				continue
			frappe.throw(
				_("{0} is on hold: the advance of {1} for {2} has not been received ({3} received). Record the advance as a Payment Entry against the order first — or ask for an exception on the order (Documents → Request exception).").format(
					what, frappe.format_value(required - received, {"fieldtype": "Currency"}), name, frappe.format_value(received, {"fieldtype": "Currency"})),
				title=_("Advance before delivery"),
			)


def dn_before_submit(doc, method=None):
	if not feature_on("advances"):
		return
	if doc.get("is_return"):
		return
	check_hold([i.against_sales_order for i in doc.items], _("Delivery"))


def pick_list_before_submit(doc, method=None):
	if not feature_on("advances"):
		return
	check_hold([r.sales_order for r in doc.get("locations") or []], _("Picking"))


def payment_entry_changed(doc, method=None):
	for r in doc.get("references") or []:
		if r.reference_doctype == "Sales Order" and r.reference_name:
			refresh(r.reference_name)


def on_hold(sales_order):
	"""v1.5.6: True while the order's advance is still due and no approved exception lets it go ahead."""
	if not feature_on("advances") or not settings().get("advance_before_delivery") or not sales_order or not frappe.db.exists("Sales Order", sales_order):
		return False
	so = frappe.get_doc("Sales Order", sales_order)
	required, received = position(so)
	if status_of(required, received) not in ("Waiting", "Part received"):
		return False
	return not frappe.db.exists("Document Waiver", {"reference_doctype": "Sales Order", "reference_name": sales_order,
		"document_type": "Advance payment", "status": ["in", ["Approved", "Used"]]})


@frappe.whitelist()
def advance_payment_entry(sales_order):
	"""v1.5.6 (ADV-02): "Receive advance" pre-fills the advance still due, not the whole order."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	so = frappe.get_doc("Sales Order", sales_order)
	so.check_permission("read")
	required, received = position(so)
	due = max(0.0, required - received)
	if due <= 0:
		frappe.throw(_("The advance on {0} has been received.").format(so.name))
	rate = flt(so.conversion_rate or 1)
	in_order_currency = due / rate if (so.get("party_account_currency") or so.currency) == so.currency and rate else due
	return get_payment_entry("Sales Order", so.name, party_amount=flt(in_order_currency, 2))
