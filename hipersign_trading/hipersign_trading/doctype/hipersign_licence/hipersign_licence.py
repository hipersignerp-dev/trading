import frappe
from frappe import _
from frappe.model.document import Document


class HipersignLicence(Document):
	def validate(self):
		# v1.8.3: only Hipersign (super admins) changes what the licence allows
		from hipersign_trading.licence import is_super_admin

		if not is_super_admin() and not frappe.flags.in_install and not frappe.flags.in_migrate:
			frappe.throw(_("Only Hipersign can change the licence."), frappe.PermissionError)
		self.max_users = max(0, self.max_users or 0)
		self.max_companies = max(0, self.max_companies or 0)
