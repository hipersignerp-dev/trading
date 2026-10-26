# Copyright (c) 2026, Hipersign
"""Letters of credit for imports (and export LCs received), with the cash margin and trust receipt finance.

The LC itself is a bank undertaking, not money: nothing posts to the ledger when it is issued.
Two draft Journal Entries can be made from the form for the accountant to check and submit:
the cash margin the bank blocks (Dr LC margin deposit, Cr bank) and a trust receipt loan that pays the
supplier on maturity (Dr supplier, Cr trust receipt loan). Paying the supplier itself stays a normal Payment Entry.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, getdate, today

from hipersign_trading.constants import LC_OPEN, LC_TENORS
from hipersign_trading.utils import settings


class LetterofCredit(Document):
	def validate(self):
		if self.lc_type == "Import" and not self.supplier:
			frappe.throw(_("Select the supplier the LC is opened for."))
		if self.lc_type == "Export" and not self.customer:
			frappe.throw(_("Select the customer whose bank opened the LC."))
		if self.purchase_order and not self.supplier:
			self.supplier = frappe.db.get_value("Purchase Order", self.purchase_order, "supplier")
		self.party_name = (
			frappe.db.get_value("Supplier", self.supplier, "supplier_name") if self.lc_type == "Import"
			else frappe.db.get_value("Customer", self.customer, "customer_name")
		)
		if flt(self.amount) <= 0:
			frappe.throw(_("LC amount must be more than zero."))
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if self.currency == company_currency:
			self.exchange_rate = 1
		self.base_amount = flt(self.amount) * flt(self.exchange_rate or 1)
		self.margin_amount = flt(self.base_amount * flt(self.margin_pct) / 100, 2)
		if self.issue_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.issue_date):
			frappe.throw(_("The expiry date is before the issue date."))
		if self.latest_shipment_date and self.expiry_date and getdate(self.latest_shipment_date) > getdate(self.expiry_date):
			frappe.throw(_("The latest shipment date must be on or before the expiry date."))
		base = self.accepted_on or self.documents_presented_on
		self.maturity_date = add_days(base, LC_TENORS.get(self.tenor, 0)) if base else None
		if self.trust_receipt:
			self.tr_amount = flt(self.tr_amount) or self.base_amount
			self.tr_start = self.tr_start or self.maturity_date or self.accepted_on
			if self.tr_start:
				self.tr_due = add_days(self.tr_start, self.tr_days or 0)
			self.tr_interest = flt(flt(self.tr_amount) * flt(self.tr_rate) / 100 * flt(self.tr_days) / 365, 2)
		if self.paid_on and getdate(self.paid_on) > getdate(today()):
			frappe.throw(_("The paid date cannot be in the future — record the payment on the day the bank pays."))
		self.check_status()

	def on_update(self):
		"""The bank releases the cash margin when the LC is paid, expires or is cancelled."""
		if self.status in ("Paid", "Expired", "Cancelled") and self.margin_entry and not self.margin_release_entry \
				and frappe.db.get_value("Journal Entry", self.margin_entry, "docstatus") == 1 and not frappe.flags.in_import:
			self.make_margin_release_entry()

	def check_status(self):
		order = ["Applied", "Issued", "Documents Presented", "Accepted", "Paid"]
		need = {"Issued": "issue_date", "Documents Presented": "documents_presented_on", "Accepted": "accepted_on", "Paid": "paid_on"}
		if self.status in need and not self.get(need[self.status]):
			frappe.throw(_("Enter the {0} for status {1}.").format(self.meta.get_label(need[self.status]).lower(), _(self.status)))
		if self.status in ("Issued",) and not self.lc_number:
			frappe.throw(_("Enter the LC number the bank issued."))
		if self.status in order and self.status != "Applied" and not self.expiry_date:
			frappe.throw(_("Enter the expiry date."))
		if self.status in LC_OPEN and self.expiry_date and getdate(self.expiry_date) < getdate(today()) and self.status in ("Applied", "Issued"):
			frappe.msgprint(_("This LC expired on {0}. Set the status to Expired or ask the bank for an amendment.").format(
				frappe.format(self.expiry_date, "Date")), indicator="orange", alert=True)

	def _je(self, title, rows, remark):
		je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": self.company, "posting_date": today(),
			"title": title, "user_remark": remark, "accounts": rows})
		je.insert()
		return je.name

	@frappe.whitelist()
	def make_margin_entry(self):
		self.check_permission("write")
		s = settings()
		if self.margin_entry:
			frappe.throw(_("Margin entry {0} already exists.").format(self.margin_entry))
		if not s.lc_margin_account:
			frappe.throw(_("Set the LC margin deposit account in Hipersign Settings first."))
		bank = frappe.get_cached_value("Company", self.company, "default_bank_account")
		if not bank:
			frappe.throw(_("Set a default bank account on company {0}.").format(self.company))
		amt = flt(self.margin_amount, 2)
		if amt <= 0:
			frappe.throw(_("There is no cash margin on this LC."))
		self.margin_entry = self._je(_("LC margin {0}").format(self.lc_number or self.name), [
			{"account": s.lc_margin_account, "debit_in_account_currency": amt},
			{"account": bank, "credit_in_account_currency": amt}], _("Cash margin blocked by {0} for LC {1}").format(self.issuing_bank, self.lc_number or self.name))
		self.save()
		return self.margin_entry

	@frappe.whitelist()
	def make_margin_release_entry(self):
		"""Draft entry for the accountant: Dr bank, Cr LC margin deposit (the bank returns or applies the margin)."""
		self.check_permission("write")
		s = settings()
		if self.margin_release_entry:
			return self.margin_release_entry
		if not self.margin_entry:
			frappe.throw(_("No margin was blocked for this LC."))
		bank = frappe.get_cached_value("Company", self.company, "default_bank_account")
		amt = flt(frappe.db.get_value("Journal Entry", self.margin_entry, "total_debit"), 2) or flt(self.margin_amount, 2)
		je = self._je(_("LC margin release {0}").format(self.lc_number or self.name), [
			{"account": bank, "debit_in_account_currency": amt},
			{"account": s.lc_margin_account, "credit_in_account_currency": amt}],
			_("Cash margin released by {0} for LC {1} ({2})").format(self.issuing_bank, self.lc_number or self.name, _(self.status)))
		self.db_set("margin_release_entry", je)
		frappe.msgprint(_("Draft margin release entry {0} created — check and submit it.").format(je), alert=True)
		return je

	@frappe.whitelist()
	def make_trust_receipt_entry(self):
		self.check_permission("write")
		s = settings()
		if not self.trust_receipt:
			frappe.throw(_("Tick “Settled by a trust receipt loan” first."))
		if self.tr_entry:
			frappe.throw(_("Trust receipt entry {0} already exists.").format(self.tr_entry))
		if not s.trust_receipt_account:
			frappe.throw(_("Set the trust receipt loan account in Hipersign Settings first."))
		if self.lc_type != "Import":
			frappe.throw(_("Trust receipts finance import LCs only."))
		payable = frappe.get_cached_value("Company", self.company, "default_payable_account")
		amt = flt(self.tr_amount, 2)
		self.tr_entry = self._je(_("Trust receipt {0}").format(self.lc_number or self.name), [
			{"account": payable, "party_type": "Supplier", "party": self.supplier, "debit_in_account_currency": amt},
			{"account": s.trust_receipt_account, "credit_in_account_currency": amt}],
			_("Supplier paid by {0} under LC {1}; trust receipt loan due {2}").format(self.issuing_bank, self.lc_number or self.name, self.tr_due))
		self.save()
		return self.tr_entry


def days_to(d):
	return date_diff(d, today()) if d else None
