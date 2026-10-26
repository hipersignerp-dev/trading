# Copyright (c) 2026, Hipersign
"""Import shipment — tracks a supplier order from booking to customs clearance and landed cost."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from hipersign_trading.constants import IMPORT_DOCUMENTS, IMPORT_STATUSES
from hipersign_trading.utils import settings


class ImportShipment(Document):
	def validate(self):
		if not self.documents:
			for d in IMPORT_DOCUMENTS:
				self.append("documents", {"document_type": d, "required": 1})
		self.goods_value = sum(flt(r.base_grand_total) for r in self.purchase_orders)
		self.total_charges = sum(flt(c.amount) for c in self.charges)
		self.validate_status()

	def validate_status(self):
		s = settings()
		idx = IMPORT_STATUSES.index(self.status)
		before = self.get_doc_before_save()
		if before and IMPORT_STATUSES.index(before.status) > idx and not frappe.has_permission(self.doctype, "delete"):
			frappe.throw(_("Status cannot move backwards"))
		if idx >= IMPORT_STATUSES.index("Cleared"):
			if s.require_boe_to_clear and not self.bill_of_entry:
				frappe.throw(_("Enter the Bill of Entry number before clearing"), title=_("Cannot clear"))
			missing = [d.document_type for d in self.documents if d.required and not d.received]
			if s.require_docs_to_clear and missing:
				frappe.throw(_("Missing documents: {0}").format(", ".join(missing)), title=_("Cannot clear"))
			if not self.cleared_on:
				self.cleared_on = today()
		if idx >= IMPORT_STATUSES.index("Arrived at Port") and not self.arrived_on:
			self.arrived_on = today()

	def purchase_receipts(self):
		pos = [r.purchase_order for r in self.purchase_orders]
		if not pos:
			return []
		return sorted(
			set(
				frappe.get_all(
					"Purchase Receipt Item",
					filters={"purchase_order": ["in", pos], "docstatus": 1},
					pluck="parent",
				)
			)
		)

	def all_pos_received(self):
		return all(
			flt(frappe.db.get_value("Purchase Order", r.purchase_order, "per_received")) >= 100
			for r in self.purchase_orders
		)

	@frappe.whitelist()
	def make_landed_cost_voucher(self):
		"""Spread freight, duty, insurance, clearing and handling over the received goods."""
		if self.landed_cost_voucher:
			return self.landed_cost_voucher
		prs = self.purchase_receipts()
		if not prs:
			frappe.throw(_("Receive the goods first — no submitted purchase receipt is linked to this shipment."))
		if not self.charges:
			frappe.throw(_("Add the import charges first."))
		account = (
			settings().landed_cost_expense_account
			or frappe.get_cached_value("Company", self.company, "expenses_included_in_valuation")
			or frappe.db.get_value("Account", {"company": self.company, "is_group": 0, "account_type": "Expenses Included In Valuation"})
		)
		if not account:
			frappe.throw(_("Set the landed cost account in Hipersign Settings (or “Expenses Included In Valuation” on the company)."))
		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = self.company
		lcv.distribute_charges_based_on = "Amount"
		for pr in prs:
			d = frappe.db.get_value("Purchase Receipt", pr, ["supplier", "base_grand_total", "posting_date"], as_dict=True)
			lcv.append(
				"purchase_receipts",
				{"receipt_document_type": "Purchase Receipt", "receipt_document": pr, "supplier": d.supplier,
				 "grand_total": d.base_grand_total, "posting_date": d.posting_date},
			)
		lcv.get_items_from_purchase_receipts()
		for c in self.charges:
			lcv.append("taxes", {"description": f"{c.charge_type} — {self.name}", "expense_account": account, "amount": c.amount})
		lcv.insert()
		self.db_set("landed_cost_voucher", lcv.name)
		return lcv.name
