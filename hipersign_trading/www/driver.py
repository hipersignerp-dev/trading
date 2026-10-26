import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/driver"
		raise frappe.Redirect
	context.no_header = 1
	context.no_breadcrumbs = 1
	context.title = "Hipersign Driver"
	context.full_name = frappe.utils.get_fullname()
	return context
