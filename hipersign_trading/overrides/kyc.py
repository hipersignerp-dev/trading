"""KYC on customers and suppliers: trade licence expiry, status, and the sales-order block."""

import frappe
from frappe import _
from frappe.utils import getdate, today

from hipersign_trading.utils import settings


def party_before_save(doc, method=None):
	"""A verified party whose licence has expired becomes Expired automatically."""
	if not doc.meta.has_field("hs_kyc_status"):
		return
	exp = doc.get("hs_trade_licence_expiry")
	if exp and getdate(exp) < getdate(today()) and doc.hs_kyc_status in ("Verified", "Pending"):
		doc.hs_kyc_status = "Expired"
	elif exp and getdate(exp) >= getdate(today()) and doc.hs_kyc_status == "Expired":
		doc.hs_kyc_status = "Verified"
	if doc.doctype == "Customer" and doc.hs_kyc_status == "Verified" and not doc.get("hs_kyc_verified_on"):
		doc.hs_kyc_verified_on = today()


def kyc_problem(customer):
	c = frappe.db.get_value("Customer", customer, ["hs_kyc_status", "hs_trade_licence_expiry", "is_internal_customer"], as_dict=True)
	if not c or c.is_internal_customer:
		return None
	if c.hs_kyc_status == "Blocked":
		return _("KYC is blocked for this customer")
	if c.hs_trade_licence_expiry and getdate(c.hs_trade_licence_expiry) < getdate(today()):
		return _("the trade licence expired on {0}").format(frappe.format(c.hs_trade_licence_expiry, "Date"))
	return None


def sales_order_before_submit(doc, method=None):
	if not frappe.get_meta("Customer").has_field("hs_kyc_status") or not settings().get("kyc_block_orders"):
		return
	problem = kyc_problem(doc.customer)
	if problem:
		frappe.throw(_("{0} cannot be confirmed: {1}. Update the customer's KYC (new licence copy and expiry date) and submit again. Drafts and quotations are still allowed.").format(
			doc.name, problem), title=_("KYC"))
