"""Payment Entry rules.

Bank charges & short payments: when the customer's transfer arrives short (AED 1,000 invoiced,
AED 980 credited), the difference is a deduction row on the Payment Entry (bank charges, or the
short-payment write-off account) and the invoice is settled in full. Up to the limit in Hipersign
Settings (the lower of an amount and a % of the invoices) anyone may book it; above it only the
role on the settings — otherwise the balance stays open on the invoice.

Supplier payments: never more than is still owed on the bill, counting debit notes and cheques
already issued but not yet in the books (cheques recorded before v1.3).
"""

import frappe
from frappe import _
from frappe.utils import flt

from hipersign_trading.utils import settings


def short_payment_limit(allocated):
	s = settings()
	lim = flt(s.get("sp_auto_limit"))
	pct = flt(s.get("sp_auto_pct"))
	vals = [v for v in (lim, flt(allocated) * pct / 100 if pct else None) if v is not None]
	return min(vals) if vals else 0


def validate(doc, method=None):
	if doc.payment_type == "Receive" and doc.party_type == "Customer":
		_check_deductions(doc)
	if doc.payment_type == "Pay" and doc.party_type == "Supplier":
		_check_supplier_overpayment(doc)


def _check_deductions(doc):
	s = settings()
	accounts = {a for a in (s.get("bank_charges_account"), s.get("sp_writeoff_account")) if a}
	if not accounts or not doc.get("deductions"):
		return
	total = sum(flt(d.amount) for d in doc.deductions if d.account in accounts)
	if total <= 0:
		return
	allocated = sum(flt(r.allocated_amount) for r in doc.get("references") or [])
	lim = short_payment_limit(allocated)
	role = s.get("sp_approver_role") or "Accounts Manager"
	if total > lim + 0.005 and not ({role, "System Manager"} & set(frappe.get_roles())):
		frappe.throw(_("The difference of {0} is above the limit of {1} for these invoices (Hipersign Settings → Payments & pricing). "
			"Only the {2} can absorb it as bank charges — keep the balance open on the invoice, or ask them.").format(
			frappe.format(total, {"fieldtype": "Currency", "options": doc.paid_to_account_currency}),
			frappe.format(lim, {"fieldtype": "Currency", "options": doc.paid_to_account_currency}), _(role)), title=_("Above the bank-charge limit"))


def _check_supplier_overpayment(doc):
	for r in doc.get("references") or []:
		if r.reference_doctype != "Purchase Invoice" or not r.reference_name:
			continue
		unposted = sum(flt(x) for x in frappe.get_all("Post Dated Cheque", filters={"direction": "Issued", "reference_doctype": "Purchase Invoice",
			"reference_name": r.reference_name, "status": "Issued", "posted": 0}, pluck="amount"))
		out = flt(frappe.db.get_value("Purchase Invoice", r.reference_name, "outstanding_amount"))
		if unposted and flt(r.allocated_amount) > out - unposted + 0.005:
			frappe.throw(_("Row {0}: {1} — only {2} is still owed after cheques already issued ({3}). Reduce the amount.").format(
				r.idx, r.reference_name, frappe.format(max(0, out - unposted), "Currency"), frappe.format(unposted, "Currency")))


@frappe.whitelist()
def short_payment_info(allocated, company=None):
	s = settings()
	role = s.get("sp_approver_role") or "Accounts Manager"
	return {"limit": short_payment_limit(allocated), "bank_charges_account": s.get("bank_charges_account"), "writeoff_account": s.get("sp_writeoff_account"),
		"cost_center": frappe.get_cached_value("Company", company, "cost_center") if company else None,
		"approver_role": role, "can_override": bool({role, "System Manager"} & set(frappe.get_roles()))}
