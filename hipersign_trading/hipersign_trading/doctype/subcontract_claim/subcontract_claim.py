# Copyright (c) 2026, Hipersign
from frappe.model.document import Document


class SubcontractClaim(Document):
	def validate(self):
		from hipersign_trading.api.projects import claim_compute

		claim_compute(self)
