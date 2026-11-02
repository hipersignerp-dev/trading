# Copyright (c) 2026, Hipersign
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

SHARES = ("mat_share", "lab_share", "sub_share", "plant_share", "ovh_share")


class ProjectBOQ(Document):
	"""A priced bill of quantities: the tender while it is priced and submitted, the contract BOQ once awarded.
	Each line carries its cost build-up (shares of the selling rate) and its progress (certified % and measured %)."""

	def validate(self):
		sec_names = {}
		for i, r in enumerate(self.items, 1):
			r.section = (r.section or "A").strip().upper()[:3]
			if r.section_name:
				sec_names.setdefault(r.section, r.section_name)
			r.section_name = r.section_name or sec_names.get(r.section) or ""
			if not r.item_no:
				r.item_no = r.section + str(sum(1 for x in self.items[:i] if (x.section or "A").strip().upper()[:3] == r.section))
			r.amount = flt(flt(r.qty) * flt(r.rate), 2)
			r.cost_rate = flt(flt(r.rate) * sum(flt(r.get(s)) for s in SHARES) / 100, 2)
			r.measured_pct = min(100, max(flt(r.certified_pct), flt(r.measured_pct)))
		if self.items:
			self.total_amount = flt(sum(flt(r.amount) for r in self.items), 2)
			self.direct_cost = flt(sum(flt(r.cost_rate) * flt(r.qty) for r in self.items), 2)
			self.overheads = flt(self.total_amount * flt(self.overhead_pct) / 100, 2)
			self.tender_value = self.total_amount
			if self.total_amount:
				self.margin_pct = flt((self.total_amount - self.direct_cost - self.overheads) / self.total_amount * 100, 2)
			self.work_done = flt(sum(flt(r.amount) * flt(r.measured_pct) / 100 for r in self.items), 2)
		if self.project and not self.customer:
			self.customer = frappe.db.get_value("Project", self.project, "customer")
		if self.customer and not self.client_name:
			self.client_name = frappe.db.get_value("Customer", self.customer, "customer_name")
		if not self.title:
			self.title = (self.project and frappe.db.get_value("Project", self.project, "project_name")) or self.client_name or _("Tender")
