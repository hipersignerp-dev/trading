# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


from frappe import _


class HipersignDocumentRule(Document):
	def validate(self):
		meta = frappe.get_meta(self.reference_doctype)
		if self.event == "On submit" and not meta.is_submittable:
			frappe.throw(_("{0} is not submitted — choose “When status changes to” and the status field.").format(self.reference_doctype))
		if self.event == "When status changes to":
			if not self.when_field or not meta.has_field(self.when_field):
				frappe.throw(_("{0} has no field {1}.").format(self.reference_doctype, self.when_field or "—"))
			if not self.when_value:
				frappe.throw(_("Enter the status value."))
		if self.min_amount and not meta.has_field(self.amount_field or ""):
			frappe.throw(_("{0} has no field {1}.").format(self.reference_doctype, self.amount_field or "—"))
		dup = frappe.db.exists("Hipersign Document Rule", {"reference_doctype": self.reference_doctype, "document_type": self.document_type,
			"event": self.event, "when_value": self.when_value, "name": ["!=", self.name]})
		if dup:
			frappe.throw(_("A rule for {0} on {1} already exists: {2}").format(self.document_type, self.reference_doctype, dup))

	def on_update(self):
		frappe.cache.delete_value("hs_doc_rules")

	def on_trash(self):
		frappe.cache.delete_value("hs_doc_rules")
