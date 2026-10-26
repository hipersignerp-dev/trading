# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


class HipersignSettings(Document):
	def on_update(self):
		frappe.clear_cache(doctype="Hipersign Settings")
