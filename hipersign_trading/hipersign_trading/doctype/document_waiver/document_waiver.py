# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


from frappe import _
from frappe.utils import getdate, now_datetime, today


class DocumentWaiver(Document):
	def validate(self):
		if self.is_new():
			self.requested_by = self.requested_by or frappe.session.user
			self.status = "Pending"
			if getdate(self.due_date) < getdate(today()):
				frappe.throw(_("The date the document is expected cannot be in the past."))
		if not self.approver_role and self.rule:
			self.approver_role = frappe.db.get_value("Hipersign Document Rule", self.rule, "approver_role")
		if not self.approver_role:
			from hipersign_trading.doc_rules import default_approver

			self.approver_role = default_approver(self.reference_doctype)

	def can_decide(self, user=None):
		roles = frappe.get_roles(user)
		return "System Manager" in roles or (self.approver_role in roles)

	@frappe.whitelist()
	def approve(self, note=None):
		if self.status != "Pending":
			frappe.throw(_("Only a pending request can be approved."))
		if not self.can_decide():
			frappe.throw(_("Only the {0} can approve this exception.").format(self.approver_role))
		self.self_approved = 1 if self.requested_by == frappe.session.user else 0
		self.status, self.decided_by, self.decided_on, self.decision_note = "Approved", frappe.session.user, now_datetime(), note
		self.save(ignore_permissions=True)
		self.add_comment("Info", _("Exception approved{0}").format(" — " + note if note else ""))
		from hipersign_trading.doc_rules import notify

		notify(self, _("Exception approved: {0} for {1} {2}").format(self.document_type, self.reference_doctype, self.reference_name), self.requested_by)

	@frappe.whitelist()
	def reject(self, note=None):
		if self.status != "Pending":
			frappe.throw(_("Only a pending request can be rejected."))
		if not self.can_decide():
			frappe.throw(_("Only the {0} can reject this exception.").format(self.approver_role))
		if self.requested_by == frappe.session.user and "System Manager" not in frappe.get_roles():
			frappe.throw(_("You cannot decide your own request."))
		self.status, self.decided_by, self.decided_on, self.decision_note = "Rejected", frappe.session.user, now_datetime(), note
		self.save(ignore_permissions=True)
		from hipersign_trading.doc_rules import notify

		notify(self, _("Exception rejected: {0} for {1} {2}").format(self.document_type, self.reference_doctype, self.reference_name), self.requested_by)
