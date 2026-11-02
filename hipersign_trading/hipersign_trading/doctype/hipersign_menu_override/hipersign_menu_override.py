# Copyright (c) 2026, Hipersign
# v1.8.0: one menu-builder change (hipersign_trading/menu.py applies them at boot)
import frappe
from frappe import _
from frappe.model.document import Document

from hipersign_trading.menu import valid_link


class HipersignMenuOverride(Document):
	def validate(self):
		if self.scope != "Company":
			self.company = None
		if self.scope != "Role":
			self.role = None
		if self.scope == "Company" and not self.company:
			frappe.throw(_("Choose the company this menu change applies to"))
		if self.scope == "Role" and not self.role:
			frappe.throw(_("Choose the role this menu change applies to"))
		self.item_key = (self.item_key or "").strip()
		if self.item_type == "Custom Link":
			if not (self.label_en or "").strip():
				frappe.throw(_("A custom link needs an English label"))
			if not valid_link(self.link_url):
				frappe.throw(_("Use a web address (https://…), a desk path (/app/…) or #page"))
		dup = frappe.db.exists(self.doctype, {"scope": self.scope, "company": self.company, "role": self.role, "item_key": self.item_key,
			"name": ["!=", self.name or ""]})
		if dup:
			frappe.throw(_("This menu entry already has a change for this scope ({0})").format(dup))

	def on_update(self):
		from hipersign_trading.menu import clear_cache

		clear_cache()

	def on_trash(self):
		from hipersign_trading.menu import clear_cache

		clear_cache()
