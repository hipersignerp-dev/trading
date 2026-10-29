"""v1.5.6: the Customer and Supplier forms open for every user who may read them.

ERPNext 16 loads the party's invoice totals (the form dashboard) with the user's own permissions. A user who may
read customers but not sales invoices (a storekeeper, logistics, HR) got "Insufficient Permission for Sales Invoice"
and the form did not open. Those users now see the form without the invoice totals.
"""

import frappe
from erpnext.buying.doctype.supplier.supplier import Supplier
from erpnext.selling.doctype.customer.customer import Customer


def _safe(doc, load):
	try:
		load()
	except frappe.PermissionError:
		frappe.clear_last_message()
		frappe.local.message_log = [m for m in (frappe.local.message_log or []) if "Insufficient Permission" not in str(m)]
		doc.set_onload("dashboard_info", [])


class HipersignCustomer(Customer):
	def load_dashboard_info(self):
		_safe(self, super().load_dashboard_info)


class HipersignSupplier(Supplier):
	def load_dashboard_info(self):
		_safe(self, super().load_dashboard_info)
