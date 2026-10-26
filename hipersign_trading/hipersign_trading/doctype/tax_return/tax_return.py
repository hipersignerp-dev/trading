# Copyright (c) 2026, Hipersign
"""VAT 201 and corporate tax returns, prepared in ERPNext and filed by hand on EmaraTax.

Prepared (figures fetched) → Pending Finance Manager → Approved (figures frozen; the VAT period is locked
with an Accounting Period so no invoice, payment or journal can be posted into it) → Submitted on EmaraTax
(reference recorded) → Paid. A rejected return goes back to Prepared.
"""

import calendar

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt, getdate, today

from hipersign_trading.constants import LOCKED_DOCTYPES
from hipersign_trading.utils import has_any_role, settings

CT_RATE = 9


class TaxReturn(Document):
	def validate(self):
		if getdate(self.period_to) < getdate(self.period_from):
			frappe.throw(_("Period to is before period from."))
		dup = frappe.db.exists("Tax Return", {"name": ["!=", self.name], "company": self.company, "tax_type": self.tax_type,
			"period_from": self.period_from, "status": ["!=", "Rejected"]})
		if dup:
			frappe.throw(_("{0} for this period already exists: {1}").format(self.tax_type, dup))
		self.title = f"{self.tax_type} {getdate(self.period_from).strftime('%b %Y') if self.tax_type == 'VAT 201' else getdate(self.period_to).year}"
		self.due_date = due_date(self.tax_type, self.period_to)
		if not self.status:
			self.status = "Prepared"
		if self.status == "Prepared":
			self.prepared_by = self.prepared_by or frappe.session.user
			if self.tax_type == "VAT 201":
				self.fetch_vat()
			else:
				self.fetch_corporate_tax()
		elif self.figures_changed():
			frappe.throw(_("Figures are frozen once the return is sent for approval."))

	def figures_changed(self):
		"""Adjustments or relief edited after the return left Prepared (compares values, not row objects)."""
		prev = self.get_doc_before_save()
		if not prev:
			return False
		rows = lambda d: [tuple((k, str(r.get(k))) for k in sorted(r.as_dict(no_default_fields=True)) if k not in ("name", "idx", "modified", "creation"))
			for r in d.get("adjustments") or []]
		return rows(prev) != rows(self) or bool(prev.get("small_business_relief")) != bool(self.get("small_business_relief"))

	# ---------------------------------------------------------------- figures
	def fetch_vat(self):
		f = frappe._dict(company=self.company, from_date=self.period_from, to_date=self.period_to)
		try:
			from erpnext.regional.report.uae_vat_201 import uae_vat_201 as r

			by_emirate = r.get_total_emiratewise(f)
			self.standard_rated_sales = sum(flt(x[1]) for x in by_emirate)
			self.output_vat = sum(flt(x[2]) for x in by_emirate)
			self.reverse_charge_base = flt(r.get_reverse_charge_total(f))
			self.reverse_charge_vat = flt(r.get_reverse_charge_tax(f))
			self.zero_rated_sales = flt(r.get_zero_rated_total(f))
			self.exempt_sales = flt(r.get_exempt_total(f))
			self.standard_rated_expenses = flt(r.get_standard_rated_expenses_total(f))
			self.input_vat = flt(r.get_standard_rated_expenses_tax(f)) + flt(r.get_reverse_charge_recoverable_tax(f))
			self.vat_lines = frappe.as_json([{"emirate": x[0], "amount": flt(x[1]), "vat": flt(x[2])} for x in by_emirate])
		except Exception:
			# Fallback when the UAE regional set-up is missing: invoice totals by tax template.
			frappe.clear_last_message()
			self.fetch_vat_from_invoices()
		self.net_vat = flt(self.output_vat) + flt(self.reverse_charge_vat) - flt(self.input_vat)

	def fetch_vat_from_invoices(self):
		args = (self.company, self.period_from, self.period_to)
		si = frappe.db.sql("""select coalesce(sum(case when total_taxes_and_charges <> 0 then base_net_total end), 0),
			coalesce(sum(base_total_taxes_and_charges), 0), coalesce(sum(case when total_taxes_and_charges = 0 then base_net_total end), 0)
			from `tabSales Invoice` where docstatus=1 and company=%s and posting_date between %s and %s""", args)[0]
		pi = frappe.db.sql("""select coalesce(sum(case when total_taxes_and_charges <> 0 then base_net_total end), 0),
			coalesce(sum(base_total_taxes_and_charges), 0)
			from `tabPurchase Invoice` where docstatus=1 and company=%s and posting_date between %s and %s""", args)[0]
		self.standard_rated_sales, self.output_vat, self.zero_rated_sales = flt(si[0]), flt(si[1]), flt(si[2])
		self.standard_rated_expenses, self.input_vat = flt(pi[0]), flt(pi[1])
		self.exempt_sales = self.reverse_charge_base = self.reverse_charge_vat = 0

	def fetch_corporate_tax(self):
		row = frappe.db.sql("""select coalesce(sum(gle.credit - gle.debit), 0) from `tabGL Entry` gle
			join `tabAccount` acc on acc.name = gle.account
			where gle.is_cancelled=0 and gle.company=%s and gle.posting_date between %s and %s
			and acc.root_type in ('Income', 'Expense')""", (self.company, self.period_from, self.period_to))[0]
		self.accounting_profit = flt(row[0])
		self.taxable_income = flt(self.accounting_profit) + flt(self.adjustments)
		if self.small_business_relief:
			self.tax_payable = 0
		else:
			self.tax_payable = flt(max(0, flt(self.taxable_income) - flt(self.ct_threshold)) * CT_RATE / 100, 2)

	# ---------------------------------------------------------------- workflow
	def _move(self, status, text):
		self.status = status
		self.save()
		self.add_comment("Info", text)

	@frappe.whitelist()
	def refresh_figures(self):
		self.check_permission("write")
		if self.status != "Prepared":
			frappe.throw(_("Figures can be refreshed only while the return is Prepared."))
		self.save()

	@frappe.whitelist()
	def send_for_approval(self):
		self.check_permission("write")
		if self.status != "Prepared":
			frappe.throw(_("Only a prepared return can be sent for approval."))
		if getdate(self.period_to) >= getdate(today()):
			frappe.throw(_("The period ends on {0} — prepare the return after it closes.").format(frappe.format(self.period_to, "Date")))
		self.save()
		self._move("Pending Finance Manager", _("Sent to the Finance Manager by {0}").format(frappe.session.user))

	@frappe.whitelist()
	def approve(self):
		if not has_any_role("Accounts Manager"):
			frappe.throw(_("Only the Finance Manager (Accounts Manager) can approve a tax return."))
		if self.status != "Pending Finance Manager":
			frappe.throw(_("The return is not waiting for approval."))
		self.approved_by, self.approved_on = frappe.session.user, today()
		if self.tax_type == "VAT 201" and settings().get("lock_filed_periods"):
			self.accounting_period = lock_period(self.company, self.period_from, self.period_to, self.title)
		self._move("Approved", _("Approved and locked by {0}").format(frappe.session.user))

	@frappe.whitelist()
	def reject(self, reason=None):
		if not has_any_role("Accounts Manager"):
			frappe.throw(_("Only the Finance Manager (Accounts Manager) can return a tax return for correction."))
		if self.status != "Pending Finance Manager":
			frappe.throw(_("The return is not waiting for approval."))
		self._move("Prepared", _("Returned for correction: {0}").format(reason or "—"))

	@frappe.whitelist()
	def mark_submitted(self, reference, submitted_on=None):
		self.check_permission("write")
		if self.status != "Approved":
			frappe.throw(_("Only an approved return can be filed."))
		if not reference:
			frappe.throw(_("Enter the EmaraTax reference number."))
		self.emaratax_reference, self.submitted_on = reference, submitted_on or today()
		self._move("Submitted", _("Filed on EmaraTax — reference {0}").format(reference))

	@frappe.whitelist()
	def mark_paid(self, reference, paid_on=None):
		self.check_permission("write")
		if self.status != "Submitted":
			frappe.throw(_("Record the payment after the return is filed."))
		self.payment_reference, self.paid_on = reference, paid_on or today()
		self._move("Paid", _("Paid — reference {0}").format(reference))


def due_date(tax_type, period_to):
	"""VAT: day N of the following month (28th by default). Corporate tax: 9 months after the year end."""
	end = getdate(period_to)
	if tax_type == "Corporate Tax":
		d = getdate(add_months(end, 9))
		return d.replace(day=calendar.monthrange(d.year, d.month)[1])
	nxt = getdate(add_months(end.replace(day=1), 1))
	day = min(int(settings().get("vat_due_day") or 28), calendar.monthrange(nxt.year, nxt.month)[1])
	return nxt.replace(day=day)


def lock_period(company, start, end, title):
	"""An ERPNext Accounting Period that closes invoices, payments and journals for the filed VAT period."""
	existing = frappe.db.get_value("Accounting Period", {"company": company, "start_date": start, "end_date": end})
	if existing:
		return existing
	ap = frappe.get_doc({"doctype": "Accounting Period", "period_name": f"{title} — {company}", "company": company,
		"start_date": start, "end_date": end, "closed_documents": [{"document_type": d, "closed": 1} for d in LOCKED_DOCTYPES]})
	ap.insert(ignore_permissions=True)
	return ap.name
