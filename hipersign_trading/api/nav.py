"""v1.5.6: the count badges on the menu (Messages, Approvals, Insights & Alerts, CRM & Leads), as in the prototype."""

import frappe
from frappe.utils import add_days, today

from hipersign_trading.utils import user_company


@frappe.whitelist()
def counts():
	user = frappe.session.user
	out = {}
	try:
		out["Messages"] = frappe.db.count("Notification Log", {"for_user": user, "read": 0, "type": ["in", ["Mention", "Alert"]]}) + (
			frappe.db.count("Communication", {"sent_or_received": "Received", "communication_type": "Communication", "seen": 0,
				"creation": [">=", add_days(today(), -30)]}) if frappe.has_permission("Communication") else 0)
	except Exception:
		frappe.clear_last_message()
	try:
		from hipersign_trading.api.approvals import pending

		out["Approvals"] = len(pending(user_company(), mine=True))
	except Exception:
		frappe.clear_last_message()
	try:
		from hipersign_trading.alerts import can_see, evaluate

		out["Insights & Alerts"] = sum(1 for a in evaluate(user_company()) if a["status"] == "Open" and a["severity"] == "High" and can_see(a))
	except Exception:
		frappe.clear_last_message()
	if frappe.has_permission("Lead") and frappe.get_meta("Lead").has_field("hs_next_follow_up"):
		f = {"hs_next_follow_up": ["<=", today()], "hs_pipeline_stage": ["not in", ["Won", "Lost"]]}
		if not set(frappe.get_roles()) & {"Sales Manager", "System Manager", "Managing Director"}:
			f["lead_owner"] = user
		out["CRM & Leads"] = len(frappe.get_list("Lead", filters=f, pluck="name", limit_page_length=500))
	return {k: v for k, v in out.items() if v}
