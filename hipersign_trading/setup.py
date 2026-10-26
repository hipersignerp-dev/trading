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
	frappe.db.commit()


def after_migrate():
	ensure_settings()
	ensure_cheque_mode()


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
