"""Feature packs and switches — Hipersign Settings → Features.

Small companies switch off what they do not need. Switching a feature off
  · stops its rules (document events) and its daily reminders,
  · deactivates its approval workflows,
  · hides its links in the Hipersign workspaces (and whole workspaces that only serve it),
  · hides its buttons on the forms (the desk script reads the switches from the boot info).
No data is ever deleted, and switching the feature back on restores everything.

Core sales, buying, stock, delivery, invoicing, VAT and accounting cannot be switched off.
"""

import json

import frappe
from frappe import _

from hipersign_trading.constants import SETTINGS

# key: (label, group, description, depends on, doctypes, reports, pages, workspaces, erpnext workspaces, workflows)
FEATURES = {
	"crm": ("CRM & leads", "Sales", "Lead pipeline, follow-ups, lead sources", [], ["Lead"], [], [], [], ["CRM"], []),
	"tracker": ("Order tracker", "Sales", "Sales order tracker page", [], [], [], ["sales-order-tracker"], [], [], []),
	"portal": ("Customer portal", "Sales", "Statement of account and warranty pages for customers", [], [], [], [], [], [], []),
	"exports": ("Exports & re-exports", "Sales", "Export shipments, proof of export for 0% VAT", [], ["Export Shipment"], [], [], [], [], []),
	"rfq": ("Purchase requests & RFQs", "Buying", "Material requests and supplier quotation comparison", [], ["Material Request", "Request for Quotation", "Supplier Quotation"], [], [], [], [], []),
	"imports": ("Imports & landed cost", "Buying", "Import shipments, customs, landed cost", [], ["Import Shipment", "Landed Cost Voucher"], [], [], [], [], []),
	"lc": ("LCs & trade finance", "Buying", "Letters of credit, cash margin, trust receipts", ["imports"], ["Letter of Credit"], [], [], [], [], []),
	"multiwh": ("Multiple warehouses", "Stock", "Transfers, reservations and pick lists", [], ["Stock Reservation Entry", "Pick List"], [], [], [], [], []),
	"serial": ("Serial numbers & warranty", "Stock", "Serial tracking and warranty claims", [], ["Serial No", "Warranty Claim"], [], ["serial-lookup"], [], [], []),
	"trips": ("Delivery trips & driver app", "Stock", "Delivery trips and the driver web app", [], ["Delivery Trip", "Driver"], [], [], [], [], []),
	"advances": ("Advances & payment schedules", "Finance", "Advance before delivery, collection stages", [], [], [], [], [], [], []),
	"pdc": ("Post-dated cheques", "Finance", "Cheques in hand and issued, deposit and bounce", [], ["Post Dated Cheque"], [], [], [], [], []),
	"recon": ("Bank reconciliation", "Finance", "Statement import and matching", [], ["Bank Reconciliation Tool", "Bank Transaction"], [], [], [], [], []),
	"fx": ("Multi-currency & revaluation", "Finance", "Month-end revaluation reminder", [], ["Exchange Rate Revaluation"], [], [], [], [], []),
	"ctax": ("Corporate tax", "Finance", "Corporate tax return", [], [], [], [], [], [], []),
	"approvals": ("Approval workflows", "Controls", "Approval routes — off: documents are approved at once", [], [], [], [], [], [],
		["Hipersign Purchase Order Approval", "Hipersign Sales Order Approval", "Hipersign Supplier Payment Approval",
		 "Hipersign Stock Count Approval", "Hipersign Credit Limit Approval"]),
	"kyc": ("KYC & licence checks", "Controls", "Customer and supplier licences; orders blocked when expired", [], [], [], [], [], [], []),
	"codocs": ("Company compliance", "Controls", "Company licences, deadlines and reminders", [], ["Company Document", "Company Deadline"], [], [], [], [], []),
	"group": ("Group companies", "Group", "Several companies and countries, consolidation", [], ["Hipersign Group Member", "Group Trial Balance"], ["Hipersign Group Consolidation"], [], [], [], []),
	"hr": ("HR documents & WPS", "People & assets", "Employee documents and WPS file", [], [], [], [], ["Hipersign HR"], [], []),
	"assets": ("Fixed assets", "People & assets", "Asset register and depreciation", [], ["Asset"], [], [], [], ["Assets"], []),
}
GROUPS = ["Sales", "Buying", "Stock", "Finance", "Controls", "Group", "People & assets"]
STANDARD_ON = ["crm", "tracker", "exports", "rfq", "imports", "multiwh", "advances", "pdc", "recon", "fx", "approvals", "kyc"]
PACKS = {
	"Starter": {"on": [], "doc_level": "Off", "form_mode": "Quick", "desc": "Small local trader, one company"},
	"Standard": {"on": STANDARD_ON, "doc_level": "Recommended", "form_mode": "Standard", "desc": "Growing importer or exporter"},
	"Enterprise": {"on": list(FEATURES), "doc_level": "Full", "form_mode": "Detailed", "desc": "Groups and larger traders — everything"},
}


def field(key):
	return "feat_" + key


def _s():
	return frappe.get_cached_doc(SETTINGS)


def feature_on(key):
	"""True when the feature is switched on (features added later default to on)."""
	if not frappe.db.exists("DocType", SETTINGS):
		return True
	s = _s()
	if not s.meta.has_field(field(key)) or not s.get("setup_done"):
		return True
	return bool(s.get(field(key)))


def doc_level():
	s = _s() if frappe.db.exists("DocType", SETTINGS) else None
	return (s and s.get("document_level")) or "Full"


def pack_of(s=None):
	s = s or _s()
	# v1.5.6 (SET-04): Group follows the company mode, not the pack, so "Starter" on a group site stays Starter
	on = {k for k in FEATURES if s.get(field(k))} - {"group"}
	for name, p in PACKS.items():
		if on == set(p["on"]) - {"group"} and (s.get("document_level") or "Full") == p["doc_level"]:
			return name
	return "Custom"


def set_switches(s, pack):
	"""Every switch, the document level and the pack name from a pack, on the settings document in memory."""
	p = PACKS[pack]
	for k in FEATURES:
		s.set(field(k), 1 if k in p["on"] else 0)
	if s.get("company_mode") == "Group":
		s.set(field("group"), 1)
	s.document_level = p["doc_level"]
	s.feature_pack = pack


def apply_pack(pack, company_mode=None, save=True):
	"""Set every switch from a pack. Group companies follow the company mode when it is given."""
	if pack not in PACKS:
		frappe.throw(_("Unknown pack {0}").format(pack))
	s = frappe.get_doc(SETTINGS)
	if company_mode:
		s.company_mode = company_mode
	set_switches(s, pack)
	s.flags.hs_pack_applied = pack
	if save:
		s.flags.ignore_mandatory = True
		s.save(ignore_permissions=True)
	return s


def enforce_dependencies(s):
	changed = True
	while changed:
		changed = False
		for k, f in FEATURES.items():
			if s.get(field(k)) and any(not s.get(field(d)) for d in f[3]):
				s.set(field(k), 0)
				changed = True


def apply_effects(s=None):
	"""Make the switches take effect: workflows, workspace links, whole workspaces. Safe to run repeatedly."""
	s = s or frappe.get_doc(SETTINGS)
	hidden_before = set(json.loads(s.get("hs_hidden_by_features") or "[]"))
	hide_now = set()
	for k, f in FEATURES.items():
		on = bool(s.get(field(k))) if s.get("setup_done") else True
		for wf in f[9]:
			if frappe.db.exists("Workflow", wf):
				frappe.db.set_value("Workflow", wf, "is_active", 1 if on else 0, update_modified=False)
		if not on:
			hide_now.update("ws:" + w for w in f[7] + f[8])
	# whole workspaces (our own and ERPNext's) — restore only what we hid ourselves
	for key in hidden_before | hide_now:
		name = key[3:]
		if frappe.db.exists("Workspace", name):
			frappe.db.set_value("Workspace", name, "is_hidden", 1 if key in hide_now else 0, update_modified=False)
	# links inside the Hipersign workspaces
	off_targets = set()
	for k, f in FEATURES.items():
		if s.get("setup_done") and not s.get(field(k)):
			off_targets.update(f[4] + f[5] + f[6])
	for ws in frappe.get_all("Workspace", filters={"module": "Hipersign Trading"}, pluck="name"):
		for row in frappe.get_all("Workspace Link", filters={"parent": ws, "parenttype": "Workspace", "type": "Link"}, fields=["name", "link_to"]):
			frappe.db.set_value("Workspace Link", row.name, "hidden", 1 if row.link_to in off_targets else 0, update_modified=False)
	frappe.db.set_single_value(SETTINGS, "hs_hidden_by_features", json.dumps(sorted(hide_now)))
	# v1.4: the prototype's menu follows the switches, and the desktop shows only Hipersign when asked
	from hipersign_trading import navigation

	navigation.apply(frappe.get_doc(SETTINGS))
	frappe.clear_cache()


def boot_info():
	s = _s()
	return {
		"setup_needed": not s.get("setup_done"),
		"features": {k: feature_on(k) for k in FEATURES},
		"labels": {k: f[0] for k, f in FEATURES.items()},
		"doc_level": doc_level(),
		"pack": s.get("feature_pack") or pack_of(s),
		"company_mode": s.get("company_mode") or "Single company",
	}
