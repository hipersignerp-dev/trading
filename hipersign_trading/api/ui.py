"""v1.5.4 — the prototype's top bar: unread notifications, the user's company, Arabic / English."""

import frappe
from frappe import _


@frappe.whitelist()
def topbar():
	user = frappe.session.user
	return {
		"unread": frappe.db.count("Notification Log", {"for_user": user, "read": 0}),
		"companies": frappe.get_list("Company", pluck="name", order_by="lft asc", limit_page_length=50),
		"company": frappe.defaults.get_user_default("Company"),
		"language": frappe.db.get_value("User", user, "language") or frappe.local.lang,
	}


@frappe.whitelist()
def set_company(company):
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} not found").format(company))
	frappe.get_doc("Company", company).check_permission("read")
	frappe.defaults.set_user_default("Company", company)
	return company


@frappe.whitelist()
def set_language(language):
	if language not in ("en", "ar"):
		frappe.throw(_("Language must be English or Arabic"))
	frappe.db.set_value("User", frappe.session.user, "language", language)
	frappe.clear_cache(user=frappe.session.user)
	return language
