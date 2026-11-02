# Copyright (c) 2026, Hipersign
from frappe.model.document import Document
from frappe.utils import today


class SubcontractOrder(Document):
	def validate(self):
		self.order_date = self.order_date or today()
