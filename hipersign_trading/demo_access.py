"""v1.5.6: the view-only demo account.

A login with the "Demo Viewer" role (and not System Manager) may open every page, list, report, form and print, and
may use Switch user on a demo site, but cannot change anything. The block follows the original login, so it holds
while the viewer is switched to another demo user (whose own roles could write).

Two layers:
  1. before_request: write requests (REST writes, Frappe's save / submit / delete methods, uploads, workflow actions
     and every Hipersign method that is not on the read list) are refused before they run;
  2. document events on every doctype: anything that still tries to insert, save, submit, cancel or delete a
     document is refused, except the system's own housekeeping records.
"""

import frappe
from frappe import _

VIEWER_ROLE = "Demo Viewer"
MESSAGE = "This is a view-only demo — book a demo to try it with your data."

# housekeeping the desk writes for every user (logins, list settings, notifications read, the top bar scope)
SYSTEM_DOCTYPES = {
	"Activity Log", "Access Log", "Route History", "Error Log", "Scheduled Job Log", "Sessions", "DefaultValue", "User Settings",
	"Notification Log", "Prepared Report", "Report Snapshot", "View Log", "Console Log", "Deleted Document", "Comment Like",
}

# Frappe and ERPNext methods that write (anything else from Frappe only reads, or is caught by the document guard below)
WRITE_METHODS = {
	"frappe.client.insert", "frappe.client.insert_many", "frappe.client.save", "frappe.client.set_value", "frappe.client.delete",
	"frappe.client.submit", "frappe.client.cancel", "frappe.client.rename_doc", "frappe.client.bulk_update", "frappe.client.attach_file",
	"frappe.desk.form.save.savedocs", "frappe.desk.form.save.cancel", "frappe.desk.form.save.discard", "frappe.desk.reportview.delete_items",
	"frappe.desk.reportview.delete_bulk", "frappe.model.workflow.apply_workflow", "frappe.model.workflow.bulk_workflow_approval",
	"frappe.desk.form.utils.add_comment", "frappe.desk.form.utils.update_comment", "frappe.desk.form.assign_to.add",
	"frappe.desk.form.assign_to.remove", "frappe.desk.form.assign_to.add_multiple", "frappe.handler.upload_file", "upload_file", "uploadfile",
	"frappe.model.rename_doc.update_document_title", "frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs",
	"frappe.core.doctype.communication.email.make", "frappe.desk.form.document_follow.follow_document", "frappe.desk.like.toggle_like",
	"frappe.desk.doctype.tag.tag.add_tag", "frappe.desk.doctype.tag.tag.remove_tag", "frappe.desk.form.linked_with.cancel_all_linked_docs",
	"frappe.core.doctype.data_import.data_import.form_start_import", "frappe.core.doctype.user.user.impersonate",
	"run_doc_method", "runserverobj", "frappe.handler.run_doc_method", "frappe.desk.page.backups.backups.schedule_files_backup",
	"frappe.integrations.frappe_providers.frappecloud_billing.current_site_info",
}

# Hipersign methods that change nothing (or only the viewer's own session and view)
HIPERSIGN_READ = {
	"alerts.get_alerts", "api.approvals.get_approvals", "api.centre.get_addons", "api.centre.get_tests", "api.dashboard.gross_profit",
	"api.dashboard.net_profit", "api.docs.doc_info", "api.docs.document_types", "api.docs.ruled_doctypes", "api.driver.my_stops",
	"api.group.trial_balance", "api.home.get_home", "api.journey.chain", "api.journey.purchase_orders", "api.landed.get_landed",
	"api.landed.get_stack", "api.landed.price_helper", "api.messages.conversations", "api.messages.thread", "api.nav.counts",
	"api.pricing.price_list_info", "api.quick.find_items", "api.quick.form_modes", "api.quick.last_order", "api.quick.open_invoices",
	"api.quick.to_bill", "api.quick.set_form_mode", "api.serials.lookup", "api.setup.demo_status", "api.share.whatsapp_link",
	"api.tracker.get_orders", "api.ui.bell", "api.ui.mark_all_read", "api.ui.search", "api.ui.set_company", "api.ui.set_language",
	"api.ui.set_period", "api.ui.set_scope", "api.ui.switch_user", "api.ui.topbar", "api.wps.download_sif", "doc_rules.missing_count",
	"overrides.payment_entry.short_payment_info", "api.crm.get_pipeline", "api.crm.sales_users",
	# v1.7.0: the create modals read their choices before anything is saved
	"api.create.options", "api.create.party", "api.create.rates", "api.create.link_options", "api.create_flow.prepare",
}


def view_only(user=None):
	"""True for a Demo Viewer login, also while it is switched to another demo user."""
	cache = getattr(frappe.local, "hs_view_only", None)
	if cache is not None and user is None:
		return cache
	if frappe.session.user in ("Guest", "Administrator") and not frappe.session.data.get("impersonated_by"):
		value = False
	else:
		orig = user or frappe.session.data.get("impersonated_by") or frappe.session.user
		roles = set(frappe.get_roles(orig))
		value = VIEWER_ROLE in roles and "System Manager" not in roles
	if user is None:
		frappe.local.hs_view_only = value
	return value


def refuse():
	frappe.throw(_(MESSAGE), frappe.PermissionError, title=_("View-only demo"))


def before_request():
	try:
		if not getattr(frappe, "session", None) or frappe.session.user == "Guest" or not view_only():
			return
	except Exception:
		return
	req = getattr(frappe.local, "request", None)
	if not req:
		return
	path = req.path or ""
	if path.startswith(("/api/resource", "/api/v2/document")) and req.method in ("POST", "PUT", "PATCH", "DELETE"):
		refuse()
	if path.startswith("/api/method/"):
		cmd = path[len("/api/method/"):]
	else:
		cmd = frappe.form_dict.get("cmd") or ""
	if not cmd:
		return
	if cmd.startswith("hipersign_trading."):
		short = cmd[len("hipersign_trading."):]
		if short in HIPERSIGN_READ or short.split(".")[-1].startswith(("get_", "list_", "load", "preview")):
			return
		refuse()
	# whitelisted ERPNext methods that change a status with db_set (no document save to catch)
	if cmd in WRITE_METHODS or cmd.endswith((".submit_cancel_or_update_docs", ".make_payment_request", ".send_whatsapp", ".update_status",
		".close_or_unclose_sales_orders", ".close_or_unclose_purchase_orders", ".set_multiple_status", ".update_clearance_date",
		".reconcile_vouchers", ".create_payment_entry_bts", ".create_journal_entry_bts", ".update_bank_transaction")):
		refuse()


def doc_guard(doc, method=None):
	if doc.doctype in SYSTEM_DOCTYPES or getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
		return
	try:
		if view_only():
			refuse()
	except frappe.PermissionError:
		raise
	except Exception:
		return


def boot(bootinfo):
	"""The desk shows the view-only banner and answers changing buttons with the message."""
	try:
		if view_only():
			bootinfo.setdefault("hipersign", {})
			bootinfo["hipersign"]["view_only"] = True
			bootinfo["hipersign"]["view_only_message"] = _(MESSAGE)
	except Exception:
		pass
