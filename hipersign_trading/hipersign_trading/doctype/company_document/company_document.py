# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


from frappe import _
from frappe.utils import add_days, date_diff, getdate, today


class CompanyDocument(Document):
	def validate(self):
		if self.issue_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.issue_date):
			frappe.throw(_("The expiry date is before the issue date."))
		if self.has_value_changed("expiry_date"):
			self.last_reminder = ""
		self.status = status_of(self)

	@frappe.whitelist()
	def renew(self, expiry_date, document_number=None, issue_date=None):
		"""The renewed licence arrived: new dates, renewal closed, reminders start again."""
		self.check_permission("write")
		if self.expiry_date and getdate(expiry_date) <= getdate(self.expiry_date):
			frappe.throw(_("The new expiry date must be after the current one ({0}).").format(frappe.format(self.expiry_date, "Date")))
		old = self.expiry_date
		self.issue_date, self.expiry_date = issue_date or today(), expiry_date
		if document_number:
			self.document_number = document_number
		self.renewal_status, self.last_reminder = "Renewed", ""
		self.save()
		self.add_comment("Info", _("Renewed — valid until {0} (was {1})").format(frappe.format(expiry_date, "Date"), frappe.format(old, "Date") if old else "—"))


def status_of(doc):
	if not doc.expiry_date:
		return "No expiry"
	if doc.renewal_status == "Submitted to authority" and getdate(doc.expiry_date) >= add_days(getdate(today()), -60):
		return "Submitted to authority"
	left = date_diff(doc.expiry_date, today())
	if left < 0:
		return "Expired"
	before = frappe.db.get_value("Company Document Type", doc.document_type, "renew_before_days") or 60
	return "Due for renewal" if left <= before else "Valid"
