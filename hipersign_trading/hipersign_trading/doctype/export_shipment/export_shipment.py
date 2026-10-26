# Copyright (c) 2026, Hipersign
"""Export shipment — pack, declare, clear, ship and prove the export (0% VAT), with margin and re-export duty refund."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, today

from hipersign_trading.constants import EXPORT_DOCUMENTS, EXPORT_STATUSES
from hipersign_trading.utils import settings, valuation_rate


class ExportShipment(Document):
	def validate(self):
		if not self.documents:
			for d in EXPORT_DOCUMENTS:
				self.append("documents", {"document_type": d, "required": 1})
		self.set_required_documents()
		self.total_charges = sum(flt(c.amount) for c in self.charges)
		self.validate_steps()
		self.calculate_margin()
		self.duty_refund_estimate = self.estimate_duty_refund()

	def set_required_documents(self):
		pay = frappe.db.get_value("Sales Order", self.sales_order, "hs_payment_method") or ""
		for d in self.documents:
			if d.document_type == "Insurance Certificate":
				d.required = 1 if self.incoterm in ("CIF", "CIP", "DDP") else 0
			if d.document_type == "LC Documents":
				d.required = 1 if "LC" in pay else 0

	def doc_row(self, name):
		return next((d for d in self.documents if d.document_type.startswith(name)), None)

	def mark_document(self, name, ref=None):
		row = self.doc_row(name)
		if row and not row.received:
			row.received, row.received_on = 1, today()
			if ref:
				row.reference_no = ref
			self.save(ignore_permissions=True)

	def validate_steps(self):
		idx = EXPORT_STATUSES.index(self.status)
		need = lambda step: idx >= EXPORT_STATUSES.index(step)
		if need("Export Declaration"):
			if not self.sales_invoice:
				frappe.throw(_("Create the export invoice first — customs needs the commercial invoice."))
			if not self.declaration_no:
				frappe.throw(_("Enter the export declaration number."))
			self._tick("Commercial Invoice", self.sales_invoice)
			self._tick("Export / Re-export Declaration", self.declaration_no)
		if need("Shipped"):
			if not self.bl_awb_cmr:
				frappe.throw(_("Enter the bill of lading, airway bill or truck CMR number."))
			if not self.coo_no:
				frappe.throw(_("The certificate of origin is required before shipping."))
			self._tick("Bill of Lading", self.bl_awb_cmr)
			self._tick("Certificate of Origin", self.coo_no)
			if not self.shipped_on:
				self.shipped_on = today()
			self.proof_due_on = add_days(self.shipped_on, settings().proof_of_export_days or 90)
		if need("Delivered") and not self.delivered_on:
			self.delivered_on = today()
		if need("Documents Complete"):
			missing = [d.document_type for d in self.documents if d.required and not d.received]
			if missing:
				frappe.throw(_("Still missing: {0}").format(", ".join(missing)))
			if not self.proof_of_export_on:
				self.proof_of_export_on = today()

	def _tick(self, name, ref):
		row = self.doc_row(name)
		if row and not row.received:
			row.received, row.received_on, row.reference_no = 1, today(), ref

	def calculate_margin(self):
		so = frappe.get_doc("Sales Order", self.sales_order) if self.sales_order else None
		if not so:
			return
		self.net_sales = flt(so.base_net_total)
		if self.delivery_note and frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus") == 1:
			self.cost_of_goods = -flt(
				frappe.db.sql(
					"select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no=%s and is_cancelled=0",
					self.delivery_note,
				)[0][0]
			)
		else:
			self.cost_of_goods = sum(flt(i.stock_qty) * valuation_rate(i.item_code, i.warehouse) for i in so.items)
		self.gross_profit = flt(self.net_sales) - flt(self.cost_of_goods) - flt(self.total_charges)
		self.margin_pct = (self.gross_profit / self.net_sales * 100) if self.net_sales else 0

	def estimate_duty_refund(self):
		if not self.re_export_of:
			return 0
		imp = frappe.get_doc("Import Shipment", self.re_export_of)
		so_items = {i.item_code: flt(i.stock_qty) for i in frappe.get_doc("Sales Order", self.sales_order).items}
		value = 0
		for row in imp.purchase_orders:
			po = frappe.get_doc("Purchase Order", row.purchase_order)
			for i in po.items:
				if i.item_code in so_items:
					value += min(so_items[i.item_code], flt(i.stock_qty)) * flt(i.base_rate)
		return value * flt(settings().customs_duty_pct) / 100

	@frappe.whitelist()
	def make_delivery_note(self):
		"""Pack: create the delivery note from the export order (stock is issued when it is submitted)."""
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

		dn = make_delivery_note(self.sales_order)
		dn.hs_export_shipment = self.name
		dn.insert()
		self.db_set("delivery_note", dn.name)
		return dn.name

	@frappe.whitelist()
	def make_sales_invoice(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		if not self.delivery_note or frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus") != 1:
			frappe.throw(_("Submit the delivery note (pack the goods) first."))
		si = make_sales_invoice(self.delivery_note)
		si.hs_export_shipment = self.name
		si.insert()
		self.db_set("sales_invoice", si.name)
		return si.name

	@frappe.whitelist()
	def advance(self):
		idx = EXPORT_STATUSES.index(self.status)
		if idx == 0 and not (self.delivery_note and frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus") == 1):
			frappe.throw(_("Pack the goods first — create and submit the delivery note."))
		if idx < len(EXPORT_STATUSES) - 1:
			self.status = EXPORT_STATUSES[idx + 1]
			self.save()
		return self.status
