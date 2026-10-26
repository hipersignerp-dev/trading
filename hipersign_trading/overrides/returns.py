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
