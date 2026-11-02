# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document
from frappe.utils import today


class VariationOrder(Document):
	def validate(self):
		self.raised_on = self.raised_on or today()
		if not self.raised_by:
			self.raised_by = frappe.utils.get_fullname(self.owner or frappe.session.user)

	def on_update(self):
		from hipersign_trading.api.projects import update_revised_contract

		update_revised_contract(self.project)

	def on_trash(self):
		if self.status == "Approved":
			frappe.throw(frappe._("An approved variation is part of the contract — reject it instead."))
