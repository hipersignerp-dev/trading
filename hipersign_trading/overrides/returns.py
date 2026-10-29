"""Credit notes (sales returns) and debit notes (purchase returns) need a manager's approval.

ERPNext makes a return as a Sales / Purchase Invoice with “Is Return” ticked. Anyone with
access can draft one; only the Sales Manager (credit note) or Purchase Manager (debit note)
can submit it, and a reason is required for the VAT audit trail.
"""

import frappe
from frappe import _

from hipersign_trading.utils import has_any_role


def _check(doc, roles, label):
	if not doc.get("is_return"):
		return
	unlink_outstanding(doc)
	if doc.meta.has_field("hs_return_reason") and not doc.get("hs_return_reason"):
		frappe.throw(_("Select the return reason before submitting the {0}.").format(label))
	if not has_any_role(*roles):
		frappe.throw(
			_("{0} {1} must be approved by the {2}. Save it and ask them to submit it.").format(
				label, doc.name, " / ".join(roles)
			),
			title=_("Approval needed"),
		)


def sales_return_before_submit(doc, method=None):
	_check(doc, ["Sales Manager", "Accounts Manager"], _("Credit note"))


def purchase_return_before_submit(doc, method=None):
	_check(doc, ["Purchase Manager", "Accounts Manager"], _("Debit note"))


def unlink_outstanding(doc, method=None):
	"""v1.5.6 (RET-02): a return made against an invoice reduces that invoice's balance.

	ERPNext ticks "Update Outstanding for Self" on new returns, which books the credit on the return itself and leaves
	the original invoice showing the full amount due.
	"""
	if doc.get("is_return") and doc.get("return_against") and doc.meta.has_field("update_outstanding_for_self"):
		if doc.get("update_outstanding_for_self"):
			doc.update_outstanding_for_self = 0
