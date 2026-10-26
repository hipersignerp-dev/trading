# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


from frappe import _


class HipersignListValue(Document):
	def validate(self):
		self.value = (self.value or "").strip()
		dup = frappe.db.exists("Hipersign List Value", {"list_name": self.list_name, "value": self.value, "name": ["!=", self.name]})
		if dup:
			frappe.throw(_("{0} is already in the {1} list.").format(self.value, self.list_name))

	def on_update(self):
		if self.flags.hs_no_apply:
			return
		from hipersign_trading.lists import apply

		apply(self.list_name)

	def on_trash(self):
		from hipersign_trading.lists import used

		if used(self.list_name, self.value):
			frappe.throw(_("{0} is used on existing documents — deactivate it instead.").format(self.value))

	def after_delete(self):
		from hipersign_trading.lists import apply

		apply(self.list_name)
