"""Install / migrate hooks — creates the records the fixtures depend on and applies branding.

Nothing here touches existing business data. It only adds roles, workflow states and
action names (if missing), and sets branding on the site the app is installed on.
"""

import frappe

from hipersign_trading.constants import NEW_ROLES, SETTINGS, WEB_ROLES, WORKFLOW_ACTIONS, WORKFLOW_STATES

LOGO = "/assets/hipersign_trading/images/hipersign-logo.png"
MARK = "/assets/hipersign_trading/images/hipersign-mark.png"  # v1.7.3: square mark (tab icon, collapsed menu)


def before_install():
	ensure_workflow_masters()


def before_migrate():
	ensure_workflow_masters()


def after_install():
	ensure_settings()
	ensure_languages()
	default_print_formats()
	apply_branding()
	set_credit_controller()
	ensure_cheque_mode()
	v13_defaults(new_site=True)
	ensure_default_app()
	retire_old_workspaces()
	frappe.db.commit()


def after_migrate():
	ensure_settings()
	ensure_languages()
	ensure_cheque_mode()
	default_print_formats()
	v13_defaults(new_site=False)
	ensure_default_app()
	retire_old_workspaces()
	try:  # v1.8.4: each company's own document series
		from hipersign_trading.naming import ensure_series

		ensure_series()
	except Exception:
		frappe.log_error(title="Hipersign naming series")
	ensure_tool_permissions()
	# v1.7.3: the square mark as the browser-tab icon where the site still uses our wordmark there
	if frappe.db.get_single_value("Website Settings", "favicon") == LOGO:
		frappe.db.set_single_value("Website Settings", "favicon", MARK)
	# the menu follows the app's code: rebuild the Hipersign sidebar on every migrate (v1.5 added its pages)
	from hipersign_trading import navigation

	navigation.apply()


# v1.8.4 (#30): the six old Frappe workspaces from 1.0–1.4. Hipersign Home and the Hipersign menu replaced them; a link to
# one of them lands on Hipersign Home (hs_nav.js). Hidden on every migrate, never deleted.
OLD_WORKSPACES = ("Hipersign Trading", "Hipersign Sales", "Hipersign Warehouse", "Hipersign Finance", "Hipersign HR", "Hipersign Documents")


def retire_old_workspaces():
	try:
		for name in OLD_WORKSPACES:
			if frappe.db.exists("Workspace", name) and not frappe.db.get_value("Workspace", name, "is_hidden"):
				frappe.db.set_value("Workspace", name, "is_hidden", 1, update_modified=False)
		frappe.db.sql("update `tabUser` set default_workspace = null where default_workspace in %(old)s", {"old": OLD_WORKSPACES})
	except Exception:
		frappe.log_error(title="Hipersign old workspaces")


def ensure_default_app():
	"""v1.8.4 (#29): after login everyone goes to the Hipersign app (Hipersign Home), not Frappe's apps screen. Only set when
	the site has no default app yet; a user's own default app still wins."""
	try:
		if frappe.get_meta("System Settings").has_field("default_app") and not frappe.db.get_single_value("System Settings", "default_app"):
			frappe.db.set_single_value("System Settings", "default_app", "hipersign_trading")
	except Exception:
		frappe.log_error(title="Hipersign default app")


# v1.8.0: the top bar switches between English, Arabic and Simplified Chinese — make sure both Language records exist
LANGUAGES = (("ar", "العربية"), ("zh", "简体中文"))


def ensure_languages():
	if not frappe.db.table_exists("Language"):
		return
	for code, name in LANGUAGES:
		try:
			if frappe.db.exists("Language", code):
				if frappe.get_meta("Language").has_field("enabled") and not frappe.db.get_value("Language", code, "enabled"):
					frappe.db.set_value("Language", code, "enabled", 1, update_modified=False)
				continue
			doc = frappe.new_doc("Language")
			doc.language_code = code
			doc.language_name = name
			if doc.meta.has_field("enabled"):
				doc.enabled = 1
			doc.flags.ignore_permissions = True
			doc.insert()
		except Exception:
			frappe.log_error(title=f"Hipersign: Language {code}")


# v1.6.0 (QTN-01): ERPNext 16 makes its "… with Item Image" formats the default, so Print, Email and the WhatsApp link
# sent the English-only ERPNext layout. Our bilingual formats become the default unless the site chose its own.
PRINT_DEFAULTS = {"Quotation": "Hipersign Quotation", "Sales Order": "Hipersign Order Confirmation", "Sales Invoice": "Hipersign Tax Invoice",
	"Delivery Note": "Hipersign Delivery Note", "Purchase Order": "Hipersign Purchase Order",
	# v1.7.3: the other documents the prototype prints (Salary Slip only where HRMS is installed)
	"Purchase Receipt": "Hipersign Goods Receipt Note", "Payment Entry": "Hipersign Payment Voucher",
	"Delivery Trip": "Hipersign Delivery Trip Sheet", "Export Shipment": "Hipersign Packing List", "Salary Slip": "Hipersign Payslip",
	"Request for Quotation": "Hipersign Request for Quotation", "Pick List": "Hipersign Pick List",
	# v1.8.0: the project prints (progress and retention invoices are chosen on the Projects screens)
	"Project BOQ": "Hipersign BOQ Tender", "Progress Certificate": "Hipersign Interim Payment Certificate", "Variation Order": "Hipersign Variation Order",
	"Subcontract Order": "Hipersign Subcontract Order",
	# v1.8.0: the manufacturing prints (the finished-goods label is chosen on the work order)
	"Work Order": "Hipersign Job Ticket", "BOM": "Hipersign Bill of Materials", "Quality Inspection": "Hipersign QC Certificate"}


def default_print_formats():
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for dt, pf in PRINT_DEFAULTS.items():
		if not frappe.db.exists("Print Format", pf) or not frappe.db.exists("DocType", dt):
			continue
		current = frappe.get_meta(dt).default_print_format
		if current == pf:
			continue
		if current and frappe.db.exists("Print Format", current) and frappe.db.get_value("Print Format", current, "standard") != "Yes":
			continue  # the site's own format stays
		make_property_setter(dt, None, "default_print_format", pf, "Data", for_doctype=True, validate_fields_for_doctype=False)


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
	sales_can_draft_credit_notes()
	finance_can_approve_orders()
	stock_can_read_addresses()
	stock_can_log_warranty_claims()
	projects_roles_can_work()
	manufacturing_roles_can_work()


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


def sales_can_draft_credit_notes():
	"""v1.6.0 (RET-01/02): create and write for Sales User, also submit for Sales Manager — on credit notes only
	(overrides.returns.sales_invoice_permission refuses ordinary invoices to sales staff)."""
	from frappe.permissions import update_permission_property

	sales_can_read_invoices()
	for role, ptypes in (("Sales User", ("create", "write")), ("Sales Manager", ("create", "write", "submit"))):
		if not frappe.db.exists("Custom DocPerm", {"parent": "Sales Invoice", "role": role, "permlevel": 0, "if_owner": 0}):
			continue
		for ptype in ptypes:
			update_permission_property("Sales Invoice", role, 0, ptype, 1, validate=False)
	frappe.clear_cache(doctype="Sales Invoice")


def finance_can_approve_orders():
	"""v1.6.0 (SAL-03, PUR-01): the approval workflows send large or over-credit orders to the Finance Manager
	(Accounts Manager), but ERPNext gives that role only read on Sales Order and Purchase Order, so Approve failed
	with "no access". Accounts Manager gets write and submit there; the workflow still decides what can be approved."""
	from frappe.permissions import add_permission, update_permission_property

	if not frappe.db.exists("Role", "Accounts Manager"):
		return
	for dt in ("Sales Order", "Purchase Order"):
		frappe.flags.mute_messages = True
		try:
			if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": "Accounts Manager", "permlevel": 0, "if_owner": 0}):
				add_permission(dt, "Accounts Manager", 0)
			for ptype in ("read", "write", "submit", "print", "report", "export"):
				update_permission_property(dt, "Accounts Manager", 0, ptype, 1, validate=False)
		finally:
			frappe.flags.mute_messages = False
		frappe.clear_cache(doctype=dt)


def stock_can_read_addresses():
	"""v1.6.0 (IMP-02): ERPNext renders the supplier's and customer's address when a receipt or delivery note is made from
	an order, with the user's own permissions; Stock User has no read on Address or Contact, so a storekeeper could not
	make a Purchase Receipt (or a Delivery Note) from an order at all. The receipt also reads its stock and expense
	accounts. Stock users get read on Address, Contact and Account."""
	from frappe.permissions import add_permission, update_permission_property

	for dt in ("Address", "Contact", "Account"):
		for role in ("Stock User", "Stock Manager"):
			if not frappe.db.exists("Role", role):
				continue
			frappe.flags.mute_messages = True
			try:
				if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0, "if_owner": 0}):
					add_permission(dt, role, 0)
				update_permission_property(dt, role, 0, "read", 1, validate=False)
			finally:
				frappe.flags.mute_messages = False
		frappe.clear_cache(doctype=dt)


def stock_can_log_warranty_claims():
	"""v1.6.0 (SER-02): the Serial & Warranty Look-up's Register warranty claim is for the warehouse team, but ERPNext
	gives Warranty Claim only to the Maintenance roles."""
	from frappe.permissions import add_permission, update_permission_property

	if not frappe.db.exists("DocType", "Warranty Claim"):
		return
	for role in ("Stock User", "Stock Manager"):
		if not frappe.db.exists("Role", role):
			continue
		frappe.flags.mute_messages = True
		try:
			if not frappe.db.exists("Custom DocPerm", {"parent": "Warranty Claim", "role": role, "permlevel": 0, "if_owner": 0}):
				add_permission("Warranty Claim", role, 0)
			for ptype in ("read", "write", "create", "print", "report"):
				update_permission_property("Warranty Claim", role, 0, ptype, 1, validate=False)
		finally:
			frappe.flags.mute_messages = False
	frappe.clear_cache(doctype="Warranty Claim")


# v1.5.6: Gulf currencies show their code ("AED 1,250.00"), as on the prototype and on UAE invoices, instead of
# the Arabic abbreviation; a symbol the site changed to something else is left alone
GULF_SYMBOLS = {"AED": "د.إ", "SAR": "ر.س", "OMR": "ر.ع.", "QAR": "ر.ق", "KWD": "د.ك", "BHD": ".د.ب"}


# v1.8.0: what the Projects roles (prototype p19) need on ERPNext's records — the project manager runs the project, the
# quantity surveyor prices and certifies, the site engineer requests, receives and books hours; the demo viewer reads.
PROJECT_PERMS = {
	"Project": {"Project Manager": "rwc", "Quantity Surveyor": "rw", "Site Engineer": "r", "Managing Director": "rwc", "Accounts Manager": "r", "Accounts User": "r", "Demo Viewer": "r"},
	"Task": {"Project Manager": "rwc", "Quantity Surveyor": "r", "Site Engineer": "rwc", "Managing Director": "r", "Demo Viewer": "r"},
	"Timesheet": {"Project Manager": "rwcs", "Site Engineer": "rwc", "Managing Director": "r", "Accounts User": "r", "Demo Viewer": "r"},
	"Activity Type": {"Project Manager": "r", "Site Engineer": "r"},
	"Activity Cost": {"Project Manager": "rwc", "Site Engineer": "r"},
	"Material Request": {"Project Manager": "rwcs", "Site Engineer": "rwc", "Quantity Surveyor": "r"},
	"Purchase Order": {"Project Manager": "r", "Site Engineer": "r", "Quantity Surveyor": "r"},
	"Purchase Receipt": {"Project Manager": "rwcs", "Site Engineer": "rwcs"},
	"Stock Entry": {"Project Manager": "rwcs", "Site Engineer": "rwcs"},
	"Sales Invoice": {"Project Manager": "r", "Quantity Surveyor": "r"},
	"Purchase Invoice": {"Project Manager": "r", "Quantity Surveyor": "r"},
	"Bank Guarantee": {"Project Manager": "r", "Quantity Surveyor": "r"},
	"Employee": {"Project Manager": "r", "Site Engineer": "r"},
	"Item": {"Project Manager": "r", "Quantity Surveyor": "r", "Site Engineer": "r"},
	"Warehouse": {"Project Manager": "r", "Site Engineer": "r"},
	"Supplier": {"Project Manager": "r", "Quantity Surveyor": "r", "Site Engineer": "r"},
	"Customer": {"Project Manager": "r", "Quantity Surveyor": "r"},
	"Company": {"Project Manager": "r", "Quantity Surveyor": "r", "Site Engineer": "r"},
}


# v1.8.0: what the Manufacturing roles (prototype p19) need — the production manager plans, releases, issues, runs the shop
# floor and receives finished goods; the QC inspector inspects incoming lots, operations and batches; the demo viewer reads.
_PM, _QC, _DV = "Production Manager", "QC Inspector", "Demo Viewer"
MFG_PERMS = {
	"BOM": {_PM: "rwcs", _QC: "r", _DV: "r", "Managing Director": "r", "Accounts Manager": "r"},
	"Routing": {_PM: "rwc", _DV: "r"}, "Operation": {_PM: "rwc", _QC: "r", _DV: "r"}, "Workstation": {_PM: "rwc", _QC: "r", _DV: "r"},
	"Workstation Operating Component": {_PM: "r", _DV: "r"},
	"Work Order": {_PM: "rwcs", _QC: "r", _DV: "r", "Managing Director": "r", "Accounts Manager": "r", "Accounts User": "r", "Sales Manager": "r", "Stock User": "r"},
	"Job Card": {_PM: "rwcs", _QC: "r", _DV: "r", "Manufacturing User": "rwcs", "Managing Director": "r"},
	"Production Plan": {_PM: "rwcs", _DV: "r", "Managing Director": "r", "Purchase Manager": "r"},
	"Quality Inspection": {_PM: "r", _QC: "rwcs", _DV: "r", "Managing Director": "r"},
	"Quality Inspection Template": {_PM: "r", _QC: "rwc", _DV: "r"}, "Quality Inspection Parameter": {_PM: "r", _QC: "rwc", _DV: "r"},
	"Stock Entry": {_PM: "rwcs", _QC: "r", _DV: "r"}, "Material Request": {_PM: "rwcs", _DV: "r"},
	"Purchase Order": {_PM: "rwc", _DV: "r"}, "Purchase Receipt": {_PM: "r", _QC: "r", _DV: "r"},
	"Sales Order": {_PM: "r", _QC: "r", _DV: "r"}, "Delivery Note": {_PM: "r", _DV: "r"}, "Sales Invoice": {_PM: "r"},
	"Batch": {_PM: "rwc", _QC: "r", _DV: "r"}, "Item": {_PM: "rw", _QC: "r", _DV: "r"}, "Warehouse": {_PM: "r", _QC: "r", _DV: "r"},
	"Bin": {_PM: "r", _QC: "r", _DV: "r"}, "Customer": {_PM: "r", _QC: "r"}, "Supplier": {_PM: "r", _QC: "r"},
	"Employee": {_PM: "r", _QC: "r"}, "Company": {_PM: "r", _QC: "r"}, "UOM": {_PM: "r", _QC: "r"},
	"Stock Ledger Entry": {_PM: "r", _DV: "r"},
}


def manufacturing_roles_can_work():
	_grant(MFG_PERMS)


def projects_roles_can_work():
	_grant(PROJECT_PERMS)


def _grant(table):
	from frappe.permissions import add_permission, update_permission_property

	ptype = {"r": ("read", "print", "report", "export"), "w": ("write",), "c": ("create",), "s": ("submit",)}
	for dt, roles in table.items():
		if not frappe.db.exists("DocType", dt):
			continue
		changed = False
		for role, flags in roles.items():
			if not frappe.db.exists("Role", role):
				continue
			if not frappe.db.get_value("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0, "if_owner": 0}):
				frappe.flags.mute_messages = True
				try:
					add_permission(dt, role, 0)
				finally:
					frappe.flags.mute_messages = False
				changed = True
			name = frappe.db.get_value("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0, "if_owner": 0})
			if not name:
				continue
			for f in flags:
				for pt in ptype[f]:
					if pt == "submit" and not frappe.get_meta(dt).is_submittable:
						continue
					if not frappe.db.get_value("Custom DocPerm", name, pt):
						update_permission_property(dt, role, 0, pt, 1, validate=False)
						changed = True
		if changed:
			frappe.clear_cache(doctype=dt)


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
		"Website Settings": {"app_name": "Hipersign ERP", "app_logo": LOGO, "favicon": MARK, "splash_image": LOGO},
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


# v1.8.4 (#27): ERPNext 16 gives the Bank Reconciliation Tool to the System Manager only, so the accountants (and the
# Finance page's "Open reconciliation tool") got "not permitted". The accounts roles may use it.
TOOL_ROLES = {"Bank Reconciliation Tool": ("Accounts Manager", "Accounts User")}


def ensure_tool_permissions():
	from frappe.permissions import add_permission, update_permission_property

	for dt, roles in TOOL_ROLES.items():
		if not frappe.db.exists("DocType", dt):
			continue
		for role in roles:
			if not frappe.db.exists("Role", role):
				continue
			try:
				if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}):
					add_permission(dt, role, 0)
				for ptype in ("read", "write", "create"):
					update_permission_property(dt, role, 0, ptype, 1, validate=False)
			except Exception:
				frappe.log_error(title=f"Hipersign permissions {dt} {role}")
