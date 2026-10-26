"""Credit limit control — new or higher limits go to the Finance Manager (rule AR7)."""

import frappe
from frappe import _
from frappe.utils import flt

from hipersign_trading.utils import has_any_role, settings


def before_save(doc, method=None):
	if frappe.flags.hs_apply_credit_limit or frappe.flags.in_install or frappe.flags.in_import:
		return
	if not settings().credit_limit_approval or has_any_role("Accounts Manager", "Managing Director"):
		return
	old = {}
	if not doc.is_new():
		before = doc.get_doc_before_save() or frappe.get_doc("Customer", doc.name)
		old = {r.company: flt(r.credit_limit) for r in before.get("credit_limits", [])}
	raised = []
	for row in doc.get("credit_limits", []):
		prev = old.get(row.company, 0)
		if flt(row.credit_limit) > prev:
			raised.append((row.company, prev, flt(row.credit_limit)))
			row.credit_limit = prev
	if raised:
		doc.flags.hs_credit_requests = raised


def on_update(doc, method=None):
	for company, prev, new in doc.flags.get("hs_credit_requests") or []:
		req = frappe.get_doc(
			{
				"doctype": "Credit Limit Request",
				"customer": doc.name,
				"company": company,
				"current_limit": prev,
				"requested_limit": new,
				"reason": _("Raised on the customer record by {0}").format(frappe.session.user),
			}
		)
		req.insert(ignore_permissions=True)
		try:
			from frappe.model.workflow import apply_workflow

			apply_workflow(req, "Submit for Approval")
		except Exception:
			frappe.log_error(title="Credit Limit Request: could not move to Pending Finance Manager")
		frappe.msgprint(
			_("Credit limit {0} for {1} was sent to the Finance Manager for approval ({2}).").format(
				frappe.format_value(new, {"fieldtype": "Currency"}), doc.customer_name, req.name
			),
			indicator="orange",
			alert=True,
		)
