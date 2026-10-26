"""Helpers for the customer portal pages (/statement, /warranty)."""

import frappe
from frappe import _


def portal_customer():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.local.request.path
		raise frappe.Redirect
	from erpnext.controllers.website_list_for_contact import get_customers_suppliers

	customers, _s = get_customers_suppliers("Sales Invoice", frappe.session.user)
	if not customers:
		frappe.throw(_("Your login is not linked to a customer account. Please contact us."), frappe.PermissionError)
	name = frappe.form_dict.get("customer")
	return name if name in customers else customers[0], customers
