# Copyright (c) 2026, Hipersign
"""Post-dated cheques received from customers and issued to suppliers.

The cheque is a promise, not money: nothing is posted to the ledger until it clears.
On clearing, a Payment Entry (mode “Cheque”) is created against the invoice, so
receivables / payables and the bank balance move on the day the bank credits or debits it.
A bounced cheque cancels nothing that was not posted; it books the bank's return charges
and raises an alert, and the invoice stays open.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from hipersign_trading.utils import settings


class PostDatedCheque(Document):
	def validate(self):
		self.party_type = "Customer" if self.direction == "Received" else "Supplier"
		if self.is_new() or not self.status:
			self.status = "In Hand" if self.direction == "Received" else "Issued"
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be more than zero."))
		self.party_name = frappe.db.get_value(self.party_type, self.party, "customer_name" if self.party_type == "Customer" else "supplier_name")
		if not self.bank_account:
			self.bank_account = settings().get("cheque_bank_account") or frappe.get_cached_value("Company", self.company, "default_bank_account")
		if self.reference_doctype and self.reference_name:
			party_field = "customer" if self.party_type == "Customer" else "supplier"
			if frappe.db.get_value(self.reference_doctype, self.reference_name, party_field) != self.party:
				frappe.throw(_("{0} {1} does not belong to {2}.").format(self.reference_doctype, self.reference_name, self.party_name))
		dup = frappe.db.exists(
			"Post Dated Cheque",
			{"name": ["!=", self.name], "direction": self.direction, "cheque_no": self.cheque_no, "party": self.party, "status": ["!=", "Cancelled"]},
		)
		if dup:
			frappe.throw(_("Cheque {0} from {1} is already recorded as {2}.").format(self.cheque_no, self.party_name, dup))

	def _log(self, text):
		self.add_comment("Info", text)

	@frappe.whitelist()
	def deposit(self):
		self.check_permission("write")
		if self.direction != "Received" or self.status != "In Hand":
			frappe.throw(_("Only a cheque in hand can be deposited."))
		if getdate(self.cheque_date) > getdate(today()):
			frappe.throw(_("The cheque is dated {0} — the bank will not accept it before then.").format(frappe.format(self.cheque_date, "Date")))
		self.status, self.deposited_on = "Deposited", today()
		self.save()
		self._log(_("Deposited to {0}").format(self.bank_account or _("the bank")))

	@frappe.whitelist()
	def clear(self, cleared_on=None):
		self.check_permission("write")
		if self.status not in ("Deposited", "Issued"):
			frappe.throw(_("Only a deposited or issued cheque can be cleared."))
		self.payment_entry = self._make_payment(cleared_on or today())
		self.status, self.cleared_on = "Cleared", cleared_on or today()
		self.save()
		self._log(_("Cleared — Payment Entry {0}").format(self.payment_entry))
		return self.payment_entry

	@frappe.whitelist()
	def bounce(self, reason=None):
		self.check_permission("write")
		if self.direction != "Received" or self.status != "Deposited":
			frappe.throw(_("Only a deposited cheque can bounce."))
		s = settings()
		charge = flt(s.get("bounce_charge"))
		if charge and s.get("bank_charges_account") and self.bank_account:
			je = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"voucher_type": "Bank Entry",
					"company": self.company,
					"posting_date": today(),
					"cheque_no": self.cheque_no,
					"cheque_date": self.cheque_date,
					"user_remark": _("Returned cheque charges — {0} ({1})").format(self.cheque_no, self.party_name),
					"accounts": [
						{"account": s.bank_charges_account, "debit_in_account_currency": charge},
						{"account": self.bank_account, "credit_in_account_currency": charge},
					],
				}
			)
			je.insert()
			je.submit()
			self.charges_entry, self.bank_charges = je.name, charge
		self.status, self.bounced_on = "Bounced", today()
		self.save()
		if frappe.get_meta("Customer").has_field("hs_cheque_bounces"):
			n = frappe.db.get_value("Customer", self.party, "hs_cheque_bounces") or 0
			frappe.db.set_value("Customer", self.party, "hs_cheque_bounces", n + 1)
		self._log(_("Returned unpaid by the bank{0}. The invoice is open again.").format(" — " + reason if reason else ""))

	@frappe.whitelist()
	def replace(self, cheque_no, cheque_date, amount=None, drawn_on=None):
		"""A bounced cheque replaced by a new one from the customer."""
		self.check_permission("write")
		if self.status != "Bounced":
			frappe.throw(_("Only a bounced cheque can be replaced."))
		new = frappe.copy_doc(self)
		new.update({"cheque_no": cheque_no, "cheque_date": cheque_date, "amount": flt(amount) or self.amount, "drawn_on": drawn_on or self.drawn_on,
			"status": "In Hand", "received_on": today(), "deposited_on": None, "cleared_on": None, "bounced_on": None,
			"payment_entry": None, "charges_entry": None, "bank_charges": 0, "replaced_by": None})
		new.insert()
		self.status, self.replaced_by = "Replaced", new.name
		self.save()
		return new.name

	@frappe.whitelist()
	def cancel_cheque(self, reason=None):
		self.check_permission("write")
		if self.status in ("Cleared", "Cancelled"):
			frappe.throw(_("This cheque cannot be cancelled."))
		self.status = "Cancelled"
		self.save()
		self._log(_("Cancelled{0}").format(" — " + reason if reason else ""))

	def _make_payment(self, date):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		if self.reference_doctype and self.reference_name:
			pe = get_payment_entry(self.reference_doctype, self.reference_name, party_amount=self.amount, bank_account=self.bank_account)
			if pe.get("references"):
				pe.references[0].allocated_amount = min(flt(self.amount), flt(pe.references[0].outstanding_amount))
		else:
			pe = frappe.new_doc("Payment Entry")
			pe.update({"payment_type": "Receive" if self.direction == "Received" else "Pay", "company": self.company,
				"party_type": self.party_type, "party": self.party})
			pe.setup_party_account_field()
			pe.set_missing_values()
			if self.direction == "Received":
				pe.paid_to = self.bank_account
			else:
				pe.paid_from = self.bank_account
		pe.posting_date = date
		pe.mode_of_payment = "Cheque"
		pe.reference_no, pe.reference_date = self.cheque_no, self.cheque_date
		pe.paid_amount = pe.received_amount = flt(self.amount)
		if self.direction == "Received" and self.bank_account:
			pe.paid_to = self.bank_account
		elif self.bank_account:
			pe.paid_from = self.bank_account
		if pe.meta.has_field("clearance_date"):
			pe.clearance_date = date
		pe.remarks = _("Post-dated cheque {0} ({1})").format(self.cheque_no, self.name)
		pe.flags.ignore_permissions = True
		pe.insert()
		pe.submit()
		return pe.name


