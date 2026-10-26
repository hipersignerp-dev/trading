import frappe

from hipersign_trading.api.serials import customer_units
from hipersign_trading.portal import portal_customer

no_cache = 1


def get_context(context):
	customer, customers = portal_customer()
	context.show_sidebar = 1
	context.title = "Warranty"
	context.customer = frappe.get_cached_doc("Customer", customer)
	context.units = customer_units(customer)
	context.claims = frappe.get_all("Warranty Claim", filters={"customer": customer}, fields=["name", "serial_no", "item_name", "complaint_date", "status"], order_by="complaint_date desc", limit=50)
	return context
