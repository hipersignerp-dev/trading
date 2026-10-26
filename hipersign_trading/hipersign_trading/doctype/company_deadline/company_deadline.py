# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


from frappe import _
from frappe.utils import add_months, today

STEP = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}


class CompanyDeadline(Document):
	@frappe.whitelist()
	def mark_done(self):
		self.check_permission("write")
		if self.status == "Done":
			return self.next_deadline
		self.status, self.done_on = "Done", today()
		if STEP.get(self.repeat) and not self.next_deadline:
			nxt = frappe.copy_doc(self)
			nxt.update({"due_date": add_months(self.due_date, STEP[self.repeat]), "status": "Open", "done_on": None, "next_deadline": None, "last_reminder": ""})
			nxt.insert(ignore_permissions=True)
			self.next_deadline = nxt.name
		self.save()
		self.add_comment("Info", _("Done{0}").format(" — next due " + frappe.format(frappe.db.get_value("Company Deadline", self.next_deadline, "due_date"), "Date") if self.next_deadline else ""))
		return self.next_deadline
