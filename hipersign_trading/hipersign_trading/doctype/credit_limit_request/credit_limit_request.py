# Copyright (c) 2026, Hipersign
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CreditLimitRequest(Document):
	def validate(self):
		if flt(self.requested_limit) < 0:
			frappe.throw(_("Credit limit cannot be negative"))
		if not self.current_limit:
			from erpnext.selling.doctype.customer.customer import get_credit_limit

			self.current_limit = flt(get_credit_limit(self.customer, self.company))

	def on_submit(self):
		"""Approved by the Finance Manager — apply the new limit to the customer."""
		cust = frappe.get_doc("Customer", self.customer)
		row = next((r for r in cust.credit_limits if r.company == self.company), None)
		if row:
			row.credit_limit = self.requested_limit
		else:
			cust.append("credit_limits", {"company": self.company, "credit_limit": self.requested_limit})
		frappe.flags.hs_apply_credit_limit = True
		try:
			cust.save(ignore_permissions=True)
		finally:
			frappe.flags.hs_apply_credit_limit = False
		cust.add_comment("Info", _("Credit limit set to {0} — {1} approved by {2}").format(
			frappe.format_value(self.requested_limit, {"fieldtype": "Currency"}), self.name, frappe.session.user))
