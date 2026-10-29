"""Install / migrate hooks — creates the records the fixtures depend on and applies branding.

Nothing here touches existing business data. It only adds roles, workflow states and
action names (if missing), and sets branding on the site the app is installed on.
"""

import frappe

from hipersign_trading.constants import NEW_ROLES, SETTINGS, WEB_ROLES, WORKFLOW_ACTIONS, WORKFLOW_STATES

LOGO = "/assets/hipersign_trading/images/hipersign-logo.png"


def before_install():
	ensure_workflow_masters()


def before_migrate():
	ensure_workflow_masters()


def after_install():
	ensure_settings()
	apply_branding()
	set_credit_controller()
	ensure_cheque_mode()
	v13_defaults(new_site=True)
	frappe.db.commit()


def after_migrate():
	ensure_settings()
	ensure_cheque_mode()
	v13_defaults(new_site=False)
	# the menu follows the app's code: rebuild the Hipersign sidebar on every migrate (v1.5 added its pages)
	from hipersign_trading import navigation

	navigation.apply()


def v13_defaults(new_site):
	"""Masters and settings v1.3 needs. On a new site the set-up wizard asks: single company or group, and the pack."""
	from hipersign_trading import compliance, doc_rules, lists

	lists.seed()
	doc_rules.seed()
	compliance.seed()
	ensure_cheque_accounts()
	s = frappe.get_single(SETTINGS)
	if new_site and not s.company_mode:
		s.db_set("company_mode", "Single company")
	if s.get("feat_serial") or not s.setup_done:
		enable_serials()
	from hipersign_trading.features import apply_effects

	apply_effects(frappe.get_single(SETTINGS))
	gulf_currency_codes()
	sales_can_read_invoices()


# v1.5.6: ERPNext 16 reads the customer's invoices when the Customer form opens (the dashboard totals) with the user's own
# permissions, and gives Sales User / Sales Manager no access to Sales Invoice — so sales staff could not open any customer.
# They get read, print and report on invoices (no create, change or submit).
def sales_can_read_invoices():
	from frappe.permissions import add_permission, update_permission_property

	for role in ("Sales User", "Sales Manager"):
		if not frappe.db.exists("Role", role):
			continue
		exists = frappe.db.get_value("Custom DocPerm", {"parent": "Sales Invoice", "role": role, "permlevel": 0, "if_owner": 0})
		if exists:
			continue
		frappe.flags.mute_messages = True
		try:
			add_permission("Sales Invoice", role, 0)
			for ptype in ("print", "report", "export"):
				update_permission_property("Sales Invoice", role, 0, ptype, 1, validate=False)
		finally:
			frappe.flags.mute_messages = False
	frappe.clear_cache(doctype="Sales Invoice")


# v1.5.6: Gulf currencies show their code ("AED 1,250.00"), as on the prototype and on UAE invoices, instead of
# the Arabic abbreviation; a symbol the site changed to something else is left alone
GULF_SYMBOLS = {"AED": "د.إ", "SAR": "ر.س", "OMR": "ر.ع.", "QAR": "ر.ق", "KWD": "د.ك", "BHD": ".د.ب"}


def gulf_currency_codes():
	for code, arabic in GULF_SYMBOLS.items():
		sym = frappe.db.get_value("Currency", code, "symbol")
		if sym is not None and (sym or "").strip() in (arabic, arabic.strip("."), ""):
			frappe.db.set_value("Currency", code, "symbol", code, update_modified=False)
	frappe.clear_cache(doctype="Currency")


def enable_serials():
	"""ERPNext v16 switches serial / batch numbers off by default; the serial & warranty feature needs them."""
	if frappe.get_meta("Stock Settings").has_field("enable_serial_and_batch_no_for_item"):
		frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)


def ensure_cheque_accounts():
	"""Cheques in hand (asset) and cheques issued (liability) for posting post-dated cheques when received / issued."""
	s = frappe.get_single(SETTINGS)
	company = s.company or frappe.defaults.get_global_default("company")
	if not company or not frappe.db.exists("Company", company):
		return
	changed = False
	for field, name, root, parent_hint in (("pdc_receivable_account", "Post-dated cheques in hand", "Asset", "Current Assets"),
		("pdc_payable_account", "Post-dated cheques issued", "Liability", "Current Liabilities")):
		if s.get(field) and frappe.db.exists("Account", s.get(field)):
			continue
		acc = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
		if not acc:
			parent = frappe.db.get_value("Account", {"company": company, "account_name": parent_hint, "is_group": 1}) or frappe.db.get_value(
				"Account", {"company": company, "root_type": root, "is_group": 1}, order_by="lft asc")
			if not parent:
				continue
			a = frappe.get_doc({"doctype": "Account", "account_name": name, "company": company, "parent_account": parent, "root_type": root,
				"report_type": "Balance Sheet", "account_currency": frappe.get_cached_value("Company", company, "default_currency")})
			a.flags.ignore_root_company_validation = True  # the company may sit under a group company's chart
			acc = a.insert(ignore_permissions=True).name
		s.set(field, acc)
		changed = True
	if changed:
		s.flags.ignore_mandatory = True
		frappe.flags.hs_no_effects = True
		try:
			s.save(ignore_permissions=True)
		finally:
			frappe.flags.hs_no_effects = False


def before_uninstall():
	"""Remove what the app added to ERPNext's own forms; keep every business record.

	Custom fields, property setters, the app's workflows and roles are removed (the values in ERPNext's own
	documents stay in the database columns until they are dropped). The app's own records (shipments, LCs,
	cheques, tax returns, waivers, company documents…) disappear with their document types, so a full copy is
	saved first as JSON in the site's private files.
	"""
	import json
	import os

	from frappe.utils import get_site_path, now_datetime

	from hipersign_trading.constants import MODULE, NEW_ROLES

	backup = {}
	for dt in frappe.get_all("DocType", filters={"module": MODULE, "istable": 0, "issingle": 0}, pluck="name"):
		try:
			backup[dt] = [frappe.get_doc(dt, n).as_dict(convert_dates_to_str=True) for n in frappe.get_all(dt, pluck="name")]
		except Exception:
			backup[dt] = []
	path = get_site_path("private", "files", f"hipersign_trading_records_{now_datetime():%Y%m%d_%H%M%S}.json")
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w") as f:
		json.dump(backup, f, default=str, indent=1)
	print(f"Hipersign Trading records saved to {path}")
	for dt in ("Custom Field", "Property Setter"):
		for n in frappe.get_all(dt, filters={"module": MODULE}, pluck="name"):
			frappe.delete_doc(dt, n, ignore_permissions=True, force=True)
	# the desktop tiles we hid come back; our menu and tile go
	from hipersign_trading import navigation

	navigation.remove()
	for wf in frappe.get_all("Workflow", filters={"name": ["like", "Hipersign %"]}, pluck="name"):
		frappe.delete_doc("Workflow", wf, ignore_permissions=True, force=True)
	for kb in frappe.get_all("Kanban Board", filters={"name": "Hipersign Lead Pipeline"}, pluck="name"):
		frappe.delete_doc("Kanban Board", kb, ignore_permissions=True, force=True)
	hrms = "hrms" in frappe.get_installed_apps()
	for role in NEW_ROLES + ["Driver"]:
		if (hrms and role in ("HR Manager", "HR User")) or not frappe.db.exists("Role", role):
			continue
		frappe.db.savepoint("hs_role")
		try:
			frappe.delete_doc("Role", role, ignore_permissions=True, force=True)
		except Exception:
			frappe.db.rollback(save_point="hs_role")
	# workspaces of ERPNext that the feature switches hid come back
	for ws in json.loads(frappe.db.get_single_value("Hipersign Settings", "hs_hidden_by_features") or "[]"):
		if ws.startswith("ws:") and frappe.db.exists("Workspace", ws[3:]):
			frappe.db.set_value("Workspace", ws[3:], "is_hidden", 0)
	frappe.db.commit()


def ensure_workflow_masters():
	for role in NEW_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	for role in WEB_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert(ignore_permissions=True)
	for state, style in WORKFLOW_STATES.items():
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
				ignore_permissions=True
			)
	for action in WORKFLOW_ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True
			)


def ensure_settings():
	if not frappe.db.exists("DocType", SETTINGS):
		return
	s = frappe.get_single(SETTINGS)
	if not s.company:
		s.company = frappe.defaults.get_global_default("company")
	# Settings added in a later version start at their default values on upgraded sites.
	for df in s.meta.fields:
		if df.default is not None and df.fieldtype not in ("Section Break", "Column Break", "Tab Break") and s.get(df.fieldname) in (None, ""):
			s.set(df.fieldname, df.default)
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)


def apply_branding():
	"""Show Hipersign ERP instead of the platform name in the desk, login page and browser tab."""
	for doctype, values in {
		"Website Settings": {"app_name": "Hipersign ERP", "app_logo": LOGO, "favicon": LOGO, "splash_image": LOGO},
		"Navbar Settings": {"app_logo": LOGO},
		"System Settings": {"app_name": "Hipersign ERP"},
	}.items():
		meta = frappe.get_meta(doctype)
		for field, value in values.items():
			if meta.has_field(field):
				frappe.db.set_single_value(doctype, field, value)


def set_credit_controller():
	"""Let the Finance Manager (Accounts Manager) release orders above the credit limit."""
	meta = frappe.get_meta("Accounts Settings")
	if meta.has_field("credit_controller"):
		frappe.db.set_single_value("Accounts Settings", "credit_controller", "Accounts Manager")


def ensure_cheque_mode():
	"""Post-dated cheques create Payment Entries with mode of payment “Cheque”."""
	if not frappe.db.exists("Mode of Payment", "Cheque"):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "Cheque", "type": "Bank"}).insert(ignore_permissions=True)
