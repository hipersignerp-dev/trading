"""v1.5.6 (CRM-01): logging a lead activity saves the note, the stage, the next follow-up and the next action together."""

import frappe
from frappe import _
from frappe.utils import escape_html

ACTIVITIES = ("Call", "Meeting", "Site visit", "WhatsApp", "Email", "Note")
STAGES = ("New", "Contacted", "Qualified", "Proposal", "Negotiation")


@frappe.whitelist(methods=["POST"])
def log_activity(lead, text, activity="Call", stage=None, next_follow_up=None, next_action=None):
	doc = frappe.get_doc("Lead", lead)
	doc.check_permission("write")
	if activity not in ACTIVITIES:
		frappe.throw(_("Unknown activity {0}").format(activity))
	if stage and stage not in STAGES:
		frappe.throw(_("Unknown stage {0}").format(stage))
	if not (text or "").strip():
		frappe.throw(_("Write what happened."))
	if stage:
		doc.hs_pipeline_stage = stage
	doc.hs_next_follow_up = next_follow_up or None
	doc.hs_next_action = next_action or None
	doc.save()
	doc.add_comment("Comment", f"<b>{escape_html(_(activity))}</b> — {escape_html(text)}")
	return {"stage": doc.hs_pipeline_stage, "next_follow_up": doc.hs_next_follow_up, "next_action": doc.hs_next_action}


SALES_ROLES = ("Sales User", "Sales Manager", "Hipersign Sales Manager")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def sales_users(doctype, txt, searchfield, start, page_len, filters):
	"""Lead owner choices: enabled system users who sell (not the view-only demo login)."""
	return frappe.db.sql(
		"""select distinct u.name, u.full_name from `tabUser` u
		join `tabHas Role` r on r.parent = u.name and r.parenttype = 'User'
		where u.enabled = 1 and u.user_type = 'System User' and r.role in %(roles)s
		and u.name not in (select parent from `tabHas Role` where role = 'Demo Viewer' and parenttype = 'User')
		and (u.name like %(txt)s or u.full_name like %(txt)s)
		order by u.full_name limit %(start)s, %(page_len)s""",
		{"roles": SALES_ROLES, "txt": f"%{txt}%", "start": int(start or 0), "page_len": int(page_len or 20)},
	)
