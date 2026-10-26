# Copyright (c) 2026, Hipersign
import frappe
from frappe.model.document import Document


from frappe import _


class HipersignGroupMember(Document):
	def validate(self):
		if not self.company and not (self.site_url and self.remote_company):
			frappe.throw(_("Choose the company on this site, or enter the site URL and the company name on that site."))
		if self.company and not self.currency:
			self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if self.site_url:
			self.site_url = self.site_url.rstrip("/")

	@frappe.whitelist()
	def sync_now(self, period_end=None):
		from hipersign_trading.group import sync_member

		return sync_member(self.name, period_end)
