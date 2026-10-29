"""Helpers for the customer portal pages (/statement, /warranty)."""

import frappe
from frappe import _


def portal_customer():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.local.request.path
		raise frappe.Redirect
	# v1.5.6: staff who may read customers open the portal as a preview of any customer (the menu's Customer Portal)
	if frappe.session.data.get("user_type") == "System User" and frappe.has_permission("Customer", "read"):
		customers = frappe.get_all("Customer", filters={"disabled": 0, "is_internal_customer": 0}, order_by="customer_name asc", pluck="name", limit=500)
		if not customers:
			frappe.throw(_("There are no customers yet."))
		frappe.local.flags.hs_portal_preview = True
		name = frappe.form_dict.get("customer")
		if name not in customers:
			with_invoices = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "customer": ["in", customers]}, fields=["customer"], order_by="posting_date desc", limit=1)
			name = with_invoices[0].customer if with_invoices and with_invoices[0].customer in customers else customers[0]
		return name, customers
	from erpnext.controllers.website_list_for_contact import get_customers_suppliers

	customers, _s = get_customers_suppliers("Sales Invoice", frappe.session.user)
	if not customers:
		frappe.throw(_("Your login is not linked to a customer account. Please contact us."), frappe.PermissionError)
	name = frappe.form_dict.get("customer")
	return name if name in customers else customers[0], customers


def preview_context(context, customer, customers):
	"""The preview banner and customer picker shown to staff above the customer's own page."""
	context.hs_preview = bool(frappe.local.flags.get("hs_portal_preview"))
	if context.hs_preview:
		names = dict(frappe.get_all("Customer", filters={"name": ["in", customers]}, fields=["name", "customer_name"], as_list=True))
		context.hs_preview_customers = [{"name": c, "label": names.get(c) or c} for c in customers]
		context.hs_preview_customer = customer
