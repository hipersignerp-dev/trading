# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


class ProgressCertificate(Document):
	"""Interim payment certificate: measured by our QS, certified by the consultant, then invoiced.
	The figures are worked out by hipersign_trading.api.projects (one place for the money rules)."""

	def validate(self):
		from hipersign_trading.api.projects import ipc_compute

		ipc_compute(self)
