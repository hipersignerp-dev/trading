"""Group consolidation endpoints."""

import frappe
from frappe import _
from frappe.utils import today


@frappe.whitelist()
def trial_balance(company, period_end=None):
	"""Called by the group site with an API key of a user who has the Accounts Manager role on this site."""
	if not ({"Accounts Manager", "System Manager"} & set(frappe.get_roles())):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} not found on this site").format(company))
	from hipersign_trading.group import trial_balance as tb

	return tb(company, period_end or today())


@frappe.whitelist()
def sync_all_now(period_end=None):
	frappe.only_for(("Accounts Manager", "System Manager", "Managing Director"))
	from hipersign_trading.group import sync_member

	done, failed = [], []
	for m in frappe.get_all("Hipersign Group Member", filters={"active": 1}, pluck="name"):
		try:
			sync_member(m, period_end or today())
			done.append(m)
		except Exception as e:
			failed.append(f"{m} ({str(e)[:60]})")
	return _("Synced {0} of {1}").format(len(done), len(done) + len(failed)) + (" · " + _("failed: {0}").format(", ".join(failed)) if failed else "")
