"""v1.4 — the prototype's navigation on the ERPNext desk.

One sidebar, “Hipersign ERP”, holds the prototype's menu groups (Overview, Sales, Purchasing, Inventory & Delivery,
Finance & Tax, People & Assets, Admin). One desktop tile opens it. Our desk script keeps that sidebar on screen for
every page it lists, so the menu stays put the way it does in the prototype.

Optionally (Hipersign Settings → Look & menus) every other desktop tile is hidden; the ones we hide are remembered
and shown again when the option is switched off or the app is uninstalled.

Works with both Frappe 16 desk models:
  · up to 16.29 — Desktop Icon + Workspace Sidebar: we write the "Hipersign ERP" Workspace Sidebar;
  · 16.30 and later — per-module "Sidebar" documents (v1.8.1): we write a Sidebar named "Hipersign ERP" (module Hipersign
    Trading, not standard, so no app file backs it and migrate never reaps it). Frappe's upgrade merges the old Workspace
    Sidebars of our module into one Sidebar ("Hipersign Trading", frozen at the day of the upgrade); we replace that one
    with ours, so the module has one sidebar and it follows the code. A site's own changes to it are Custom Sidebar
    layers, which Frappe keeps and applies on top.
On a desk with neither model nothing happens.
"""

import json
import re

import frappe

from hipersign_trading.features import field

SETTINGS = "Hipersign Settings"
SIDEBAR = "Hipersign ERP"
TILE = "Hipersign ERP"
MODULE = "Hipersign Trading"
# v1.8.1: the Workspace Sidebars of our module on Frappe ≤16.29 — what Frappe ≥16.30 merges into one converted Sidebar
LEGACY_SIDEBARS = ("Hipersign ERP", "Hipersign Documents", "Hipersign Finance", "Hipersign HR", "Hipersign Sales", "Hipersign Trading",
	"Hipersign Warehouse")
LOGO = "/assets/hipersign_trading/images/hipersign-logo.png"

# v1.5.6: the prototype's menu — its 32 entries, names and order. Each module entry opens its page (or, until the page
# exists, its first list); the ERPNext lists behind it stay one click away as sub-items (NAV_SUB), shown by hs_nav.js.
# (group label, icon, [(label, link_type, link_to, icon, feature or None, extra)])
NAV = [
	("Overview", "house", [
		("Home", "Page", "hipersign-home", "house", None, {}),
		("Messages", "Page", "hipersign-messages", "message-square", None, {}),
		("Approvals", "Page", "hipersign-approvals", "inbox", None, {}),
		("Insights & Alerts", "Page", "hipersign-alerts", "sparkles", None, {}),
		("Trade Journey", "Page", "hipersign-journey", "workflow", None, {}),
		("Reports", "Page", "hipersign-reports", "chart-column", None, {}),  # v1.8.4: every report in one Hipersign page
	]),
	("Sales", "tag", [
		("CRM & Leads", "Page", "hipersign-crm", "users", "crm", {}),
		("Quotations & Orders", "Page", "hipersign-orders", "tag", None, {}),
		("Order Tracker", "Page", "sales-order-tracker", "list-checks", "tracker", {}),
		("Exports & Re-exports", "Page", "hipersign-exports", "globe", "exports", {}),
		("Customer Portal", "Page", "hipersign-portal", "share-2", "portal", {}),
	]),
	("Purchasing", "shopping-cart", [
		("Purchase Orders", "Page", "hipersign-purchasing", "shopping-cart", None, {}),
		("Quotation Comparison", "Page", "hipersign-compare", "scale", None, {}),  # v1.7.3
		("Imports & Shipments", "Page", "hipersign-imports", "ship", "imports", {}),
		("Goods Receiving", "Page", "hipersign-receiving", "scan-line", None, {}),
		("Landed Cost & Margin", "Page", "hipersign-landed", "layers", "imports", {}),
	]),
	("Inventory & Delivery", "package", [
		("Warehouse & Stock", "Page", "hipersign-stock", "warehouse", None, {}),
		("Dispatch & Delivery", "Page", "hipersign-dispatch", "truck", None, {}),
		("Driver App", "URL", "/driver", "map-pin", "trips", {}),
	]),
	# v1.8.0 (prototype p19): contracting and fit-out — before Finance & Tax, as on the prototype
	("Projects", "hard-hat", [
		("Projects", "Page", "hipersign-projects", "chart-gantt", "projects", {}),
		("Estimating & BOQ", "Page", "hipersign-boq", "calculator", "projects", {}),
		("Site & procurement", "Page", "hipersign-site", "hard-hat", "projects", {}),
		("Progress & billing", "Page", "hipersign-billing", "receipt", "projects", {}),
		("Subcontractors", "Page", "hipersign-subcontract", "briefcase", "projects", {}),
		("Timesheets & labour", "Page", "hipersign-timesheets", "clock", "projects", {}),
		("Project costing", "Page", "hipersign-costing", "chart-column", "projects", {}),
		("Project Tracker", "Page", "project-tracker", "list-checks", "projects", {}),
	]),
	# v1.8.0 (prototype p19): assemblers and factories — after Projects, before Finance & Tax, as on the prototype
	("Manufacturing", "factory", [
		("Production", "Page", "hipersign-production", "wrench", "manufacturing", {}),
		("Planning", "Page", "hipersign-planning", "kanban", "manufacturing", {}),
		("BOMs & routings", "Page", "hipersign-boms", "layers", "manufacturing", {}),
		("Shop floor", "Page", "hipersign-shopfloor", "scan-line", "manufacturing", {}),
		("Quality", "Page", "hipersign-quality", "shield-check", "manufacturing", {}),
		("Costing", "Page", "hipersign-mfg-costing", "calculator", "manufacturing", {}),
		("Production Tracker", "Page", "production-tracker", "list-checks", "manufacturing", {}),
	]),
	("Finance & Tax", "banknote", [
		("Finance", "Page", "hipersign-fin", "banknote", None, {}),
		("Accounting", "Page", "hipersign-accounts", "book-open", None, {}),
		("LCs & Guarantees", "Page", "hipersign-lc", "file-text", "lc", {}),
		("VAT & E-invoicing", "Page", "hipersign-vat", "percent", None, {}),
		("Corporate Tax", "Page", "hipersign-tax", "landmark", "ctax", {}),
		("Group & Countries", "Page", "hipersign-group", "building-2", "group", {}),
		("KYC & Compliance", "Page", "hipersign-kyc", "shield", "kyc", {}),
		("Company Compliance", "Page", "hipersign-codocs", "badge-check", "codocs", {}),
	]),
	("People & Assets", "users", [
		("HR & Payroll", "Page", "hipersign-people", "user", "hr", {}),
		("Fixed Assets", "Page", "hipersign-assets", "building", "assets", {}),
	]),
	("Admin", "sliders-horizontal", [
		# v1.8.4 (#37): Workflows & Settings, Document Centre and Data Migration are Hipersign pages (keys kept for the menu builder)
		("Workflows & Settings", "Page", "hipersign-settings-hub", "sliders-horizontal", None, {"key": "hipersign-settings"}),
		("Menu builder", "Page", "hipersign-menu", "menu", None, {}),  # v1.8.0
		("Document Centre", "Page", "hipersign-doccentre", "file-warning", None, {"key": "missing-documents"}),
		("Data Migration", "Page", "hipersign-migration", "upload", None, {"key": "data-import"}),
		("Test Centre", "Page", "hipersign-tests", "flask-conical", None, {}),
	]),
	("Add-ons", "puzzle", [
		("Add-ons & Pricing", "Page", "hipersign-addons", "puzzle", None, {}),
	]),
]

# the live site's lists under each entry: (label, link_type, link_to, feature or None)
NAV_SUB = {
	"CRM & Leads": [("Leads", "DocType", "Lead", None), ("Opportunities", "DocType", "Opportunity", None)],
	"Quotations & Orders": [("Quotations", "DocType", "Quotation", None), ("Sales Orders", "DocType", "Sales Order", None),
		("Customers", "DocType", "Customer", None)],
	"Exports & Re-exports": [("Export Shipments", "DocType", "Export Shipment", None)],
	"Purchase Orders": [("Purchase Requests", "DocType", "Material Request", "rfq"), ("Supplier Quotations", "DocType", "Supplier Quotation", "rfq"),
		("Purchase Orders", "DocType", "Purchase Order", None), ("Smart Reorder", "Report", "Hipersign Smart Reorder", None),
		("Suppliers", "DocType", "Supplier", None)],
	"Imports & Shipments": [("Import Shipments", "DocType", "Import Shipment", None), ("Landed Cost Vouchers", "DocType", "Landed Cost Voucher", None)],
	"Goods Receiving": [("Purchase Receipts", "DocType", "Purchase Receipt", None)],
	"Warehouse & Stock": [("Items", "DocType", "Item", None), ("Stock Balance", "Report", "Stock Balance", None),
		("Stock Transfers", "DocType", "Stock Entry", None), ("Stock Count", "DocType", "Stock Reconciliation", None),
		("Pick Lists", "DocType", "Pick List", "multiwh"), ("Serial & Warranty", "Page", "serial-lookup", "serial"),
		("Warranty Claims", "DocType", "Warranty Claim", "serial")],
	"Dispatch & Delivery": [("Delivery Notes", "DocType", "Delivery Note", None), ("Delivery Trips", "DocType", "Delivery Trip", "trips")],
	"Finance": [("Sales Invoices", "DocType", "Sales Invoice", None), ("Payments", "DocType", "Payment Entry", None),
		("Post-dated Cheques", "DocType", "Post Dated Cheque", "pdc"), ("Bank Reconciliation", "DocType", "Bank Reconciliation Tool", "recon"),
		("Purchase Invoices", "DocType", "Purchase Invoice", None)],
	"Accounting": [("Journal Entries", "DocType", "Journal Entry", None), ("General Ledger", "Report", "General Ledger", None),
		("Profit and Loss", "Report", "Profit and Loss Statement", None), ("Balance Sheet", "Report", "Balance Sheet", None),
		("Currency Revaluation", "DocType", "Exchange Rate Revaluation", "fx")],
	"LCs & Guarantees": [("Letters of Credit", "DocType", "Letter of Credit", None), ("Bank Guarantees", "DocType", "Bank Guarantee", None)],
	"VAT & E-invoicing": [("Tax Returns", "DocType", "Tax Return", None), ("VAT 201", "Report", "UAE VAT 201", None)],
	"Group & Countries": [("Group Members", "DocType", "Hipersign Group Member", None), ("Group Consolidation", "Report", "Hipersign Group Consolidation", None)],
	"KYC & Compliance": [("Missing Documents", "Report", "Missing Documents", None)],
	"Company Compliance": [("Company Documents", "DocType", "Company Document", None), ("Company Deadlines", "DocType", "Company Deadline", None)],
	"HR & Payroll": [("Employees", "DocType", "Employee", None), ("Leave", "DocType", "Leave Application", None),
		("Expense Claims", "DocType", "Expense Claim", None), ("Payroll", "DocType", "Payroll Entry", None)],
	"Fixed Assets": [("Assets", "DocType", "Asset", None)],
	"Workflows & Settings": [("Hipersign Settings", "DocType", "Hipersign Settings", None), ("Approval Workflows", "DocType", "Workflow", None),
		("Document Rules", "DocType", "Hipersign Document Rule", None), ("Editable Lists", "DocType", "Hipersign List Value", None),
		("Users", "DocType", "User", None), ("System Settings", "DocType", "System Settings", None)],
	"Document Centre": [("Missing Documents", "Report", "Missing Documents", None), ("Document Waivers", "DocType", "Document Waiver", None)],
	# v1.8.0: Projects
	"Projects": [("Projects", "DocType", "Project", None), ("Project Step Log", "DocType", "Project Step Log", None), ("Bank Guarantees (bonds)", "DocType", "Bank Guarantee", None)],
	"Estimating & BOQ": [("Project BOQs & tenders", "DocType", "Project BOQ", None)],
	"Site & procurement": [("Material Requests", "DocType", "Material Request", None), ("Purchase Orders", "DocType", "Purchase Order", None),
		("Stock Entries", "DocType", "Stock Entry", None)],
	"Progress & billing": [("Progress Certificates", "DocType", "Progress Certificate", None), ("Variation Orders", "DocType", "Variation Order", None),
		("Sales Invoices", "DocType", "Sales Invoice", None)],
	"Subcontractors": [("Subcontract Orders", "DocType", "Subcontract Order", None), ("Subcontract Claims", "DocType", "Subcontract Claim", None),
		("Back Charges", "DocType", "Back Charge", None)],
	"Timesheets & labour": [("Timesheets", "DocType", "Timesheet", None), ("Tasks", "DocType", "Task", None), ("Daily Site Reports", "DocType", "Daily Site Report", None),
		("Activity Costs", "DocType", "Activity Cost", None)],
	# v1.8.0: Manufacturing
	"Production": [("Work Orders", "DocType", "Work Order", None), ("Manufacturing Step Log", "DocType", "Manufacturing Step Log", None),
		("Stock Entries", "DocType", "Stock Entry", None)],
	"Planning": [("Production Plans", "DocType", "Production Plan", None), ("Material Requests", "DocType", "Material Request", None),
		("Purchase Orders", "DocType", "Purchase Order", None)],
	"BOMs & routings": [("BOMs", "DocType", "BOM", None), ("Routings", "DocType", "Routing", None), ("Operations", "DocType", "Operation", None),
		("Workstations", "DocType", "Workstation", None)],
	"Shop floor": [("Job Cards", "DocType", "Job Card", None)],
	"Quality": [("Quality Inspections", "DocType", "Quality Inspection", None), ("Inspection Templates", "DocType", "Quality Inspection Template", None)],
	"Costing": [("Work Orders", "DocType", "Work Order", None), ("Stock Ledger", "Report", "Stock Ledger", None)],
}

# v1.8.4 (#34/#37): where each sub-item opens — a Hipersign page and its tab, instead of the old-theme Frappe list, form or
# report. (entry label, sub-item label) → (page, tab or None). Reports open the Reports page on that report's group.
SUB_TABS = {
	("CRM & Leads", "Leads"): ("hipersign-crm", "leads"), ("CRM & Leads", "Opportunities"): ("hipersign-crm", "opps"),
	("Quotations & Orders", "Quotations"): ("hipersign-orders", "quotes"), ("Quotations & Orders", "Sales Orders"): ("hipersign-orders", "orders"),
	("Quotations & Orders", "Customers"): ("hipersign-orders", "credit"),
	("Exports & Re-exports", "Export Shipments"): ("hipersign-exports", "board"),
	("Purchase Orders", "Purchase Requests"): ("hipersign-purchasing", "requests"), ("Purchase Orders", "Supplier Quotations"): ("hipersign-purchasing", "quotes"),
	("Purchase Orders", "Purchase Orders"): ("hipersign-purchasing", "orders"), ("Purchase Orders", "Smart Reorder"): ("hipersign-purchasing", "reorder"),
	("Purchase Orders", "Suppliers"): ("hipersign-purchasing", "suppliers"),
	("Imports & Shipments", "Import Shipments"): ("hipersign-imports", "all"), ("Imports & Shipments", "Landed Cost Vouchers"): ("hipersign-landed", None),
	("Goods Receiving", "Purchase Receipts"): ("hipersign-receiving", "receipts"),
	("Warehouse & Stock", "Items"): ("hipersign-stock", "items"), ("Warehouse & Stock", "Stock Balance"): ("hipersign-stock", "warehouses"),
	("Warehouse & Stock", "Stock Transfers"): ("hipersign-stock", "transfers"), ("Warehouse & Stock", "Stock Count"): ("hipersign-stock", "counts"),
	("Warehouse & Stock", "Pick Lists"): ("hipersign-stock", "picks"), ("Warehouse & Stock", "Warranty Claims"): ("hipersign-stock", "claims"),
	("Dispatch & Delivery", "Delivery Notes"): ("hipersign-dispatch", "notes"), ("Dispatch & Delivery", "Delivery Trips"): ("hipersign-dispatch", "trips"),
	("Finance", "Sales Invoices"): ("hipersign-fin", "receivables"), ("Finance", "Payments"): ("hipersign-fin", "payments"),
	("Finance", "Post-dated Cheques"): ("hipersign-fin", "cheques"), ("Finance", "Bank Reconciliation"): ("hipersign-fin", "bankrec"),
	("Finance", "Purchase Invoices"): ("hipersign-fin", "payables"),
	("Accounting", "Journal Entries"): ("hipersign-accounts", "je"), ("Accounting", "General Ledger"): ("hipersign-accounts", "gl"),
	("Accounting", "Profit and Loss"): ("hipersign-fin", "pl"), ("Accounting", "Balance Sheet"): ("hipersign-accounts", "bs"),
	("Accounting", "Currency Revaluation"): ("hipersign-accounts", "reval"),
	("LCs & Guarantees", "Letters of Credit"): ("hipersign-lc", "lcs"), ("LCs & Guarantees", "Bank Guarantees"): ("hipersign-lc", "bgs"),
	("VAT & E-invoicing", "Tax Returns"): ("hipersign-vat", "history"), ("VAT & E-invoicing", "VAT 201"): ("hipersign-vat", "return"),
	("Group & Countries", "Group Members"): ("hipersign-group", "structure"), ("Group & Countries", "Group Consolidation"): ("hipersign-group", "pl"),
	("KYC & Compliance", "Missing Documents"): ("hipersign-doccentre", "missing"),
	("Company Compliance", "Company Documents"): ("hipersign-codocs", "register"), ("Company Compliance", "Company Deadlines"): ("hipersign-codocs", "deadlines"),
	("HR & Payroll", "Employees"): ("hipersign-people", "employees"), ("HR & Payroll", "Leave"): ("hipersign-people", "leave"),
	("HR & Payroll", "Expense Claims"): ("hipersign-people", "expenses"), ("HR & Payroll", "Payroll"): ("hipersign-people", "payroll"),
	("Fixed Assets", "Assets"): ("hipersign-assets", "register"),
	("Workflows & Settings", "Hipersign Settings"): ("hipersign-settings-hub", None), ("Workflows & Settings", "Approval Workflows"): ("hipersign-settings-hub", None),
	("Workflows & Settings", "Document Rules"): ("hipersign-doccentre", "rules"), ("Workflows & Settings", "Editable Lists"): ("hipersign-settings-hub", None),
	("Workflows & Settings", "Users"): ("hipersign-settings-hub", None), ("Workflows & Settings", "System Settings"): ("hipersign-settings-hub", None),
	("Document Centre", "Missing Documents"): ("hipersign-doccentre", "missing"), ("Document Centre", "Document Waivers"): ("hipersign-doccentre", "waivers"),
	("Projects", "Projects"): ("hipersign-projects", "port"), ("Projects", "Project Step Log"): ("hipersign-projects", "log"),
	("Projects", "Bank Guarantees (bonds)"): ("hipersign-lc", "bgs"),
	("Estimating & BOQ", "Project BOQs & tenders"): ("hipersign-boq", "boq"),
	("Site & procurement", "Material Requests"): ("hipersign-site", "mr"), ("Site & procurement", "Purchase Orders"): ("hipersign-site", "po"),
	("Site & procurement", "Stock Entries"): ("hipersign-site", "del"),
	("Progress & billing", "Progress Certificates"): ("hipersign-billing", "ipc"), ("Progress & billing", "Variation Orders"): ("hipersign-billing", "vo"),
	("Progress & billing", "Sales Invoices"): ("hipersign-billing", "inv"),
	("Subcontractors", "Subcontract Orders"): ("hipersign-subcontract", "sco"), ("Subcontractors", "Subcontract Claims"): ("hipersign-subcontract", "claims"),
	("Subcontractors", "Back Charges"): ("hipersign-subcontract", "bc"),
	("Timesheets & labour", "Timesheets"): ("hipersign-timesheets", "ts"), ("Timesheets & labour", "Tasks"): ("hipersign-timesheets", "task"),
	("Timesheets & labour", "Daily Site Reports"): ("hipersign-timesheets", "dsr"), ("Timesheets & labour", "Activity Costs"): ("hipersign-timesheets", "crew"),
	("Production", "Work Orders"): ("hipersign-production", "wo"), ("Production", "Manufacturing Step Log"): ("hipersign-production", "log"),
	("Production", "Stock Entries"): ("hipersign-production", "ent"),
	("Planning", "Production Plans"): ("hipersign-planning", "pp"), ("Planning", "Material Requests"): ("hipersign-planning", "mr"),
	("Planning", "Purchase Orders"): ("hipersign-planning", "po"),
	("BOMs & routings", "BOMs"): ("hipersign-boms", "tree"), ("BOMs & routings", "Routings"): ("hipersign-boms", "routing"),
	("BOMs & routings", "Operations"): ("hipersign-boms", "routing"), ("BOMs & routings", "Workstations"): ("hipersign-boms", "ws"),
	("Shop floor", "Job Cards"): ("hipersign-shopfloor", None),
	("Quality", "Quality Inspections"): ("hipersign-quality", "inc"), ("Quality", "Inspection Templates"): ("hipersign-quality", "tpl"),
	("Costing", "Work Orders"): ("hipersign-mfg-costing", "cost"), ("Costing", "Stock Ledger"): ("hipersign-stock", "moves"),
}
# the chip a sub-item opens with, where the tab has several (Routings vs Operations)
SUB_CHIPS = {("BOMs & routings", "Operations"): "ops"}
# v1.8.4: a Reports sub-item under each module group opens the Reports page on that group
REPORT_GROUP = {"Quotations & Orders": "sales", "Purchase Orders": "purchasing", "Warehouse & Stock": "stock", "Finance": "finance", "Accounting": "finance",
	"VAT & E-invoicing": "tax", "HR & Payroll": "hr", "Projects": "projects", "Production": "manufacturing"}

# count badges, as in the prototype
NAV_BADGES = ("Messages", "Approvals", "Insights & Alerts", "CRM & Leads")

LINK_DOCTYPE = {"DocType": "DocType", "Report": "Report", "Page": "Page", "Workspace": "Workspace"}


def model():
	"""v1.8.1: which desk menu model this Frappe has —
	"sidebar": Frappe 16.30+ (per-module Sidebar documents; Workspace Sidebar is only an archive there),
	"workspace_sidebar": Frappe 16 up to 16.29 (Workspace Sidebar + Desktop Icon), or None (neither: the menu is left to Frappe)."""
	if frappe.db.exists("DocType", "Sidebar"):
		if frappe.db.table_exists("Sidebar") and frappe.db.table_exists("Sidebar Item") and frappe.get_meta("Sidebar").has_field("items"):
			return "sidebar"
		return None
	if frappe.db.table_exists("Workspace Sidebar") and frappe.db.table_exists("Desktop Icon") \
		and frappe.get_meta("Workspace Sidebar").has_field("items"):
		return "workspace_sidebar"
	return None


def supported():
	"""Whether the app manages the desk menu here (v1.8.1: on both Frappe 16 menu models)."""
	return model() is not None


def item_doctype():
	"""The child doctype of the sidebar rows on this Frappe."""
	return "Sidebar Item" if model() == "sidebar" else "Workspace Sidebar Item"


def _s():
	return frappe.get_single(SETTINGS)


def _on(s, feature):
	if not feature or not s.get("setup_done"):
		return True
	return bool(s.get(field(feature)))


def slug(s):
	"""A stable key from a label or a target: "Finance & Tax" → "finance-tax", "/driver" → "driver"."""
	return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def group_key(group, extra=None):
	"""v1.8.0: stable key of a NAV group — used by the menu builder (Hipersign Menu Override.item_key)."""
	return (extra or {}).get("key") or "g:" + slug(group)


def item_key(ltype, target, extra=None):
	"""v1.8.0: stable key of a NAV item — its target (page name, doctype, report or URL), unless extra["key"] sets one.
	New NAV groups and items (Projects, Manufacturing …) get keys this way with no other change."""
	return (extra or {}).get("key") or slug(target)


def nav_groups(s=None, check=True):
	"""The menu as data: [{key, label, icon, items: [{key, label, link_type, target, icon, feature}]}] for the features
	switched on, skipping anything this site lacks (check=False: every NAV entry, for the menu builder)."""
	s = s if s is not None else (_s() if check else None)
	out = []
	for group, gicon, links in NAV:
		items = []
		for label, ltype, target, icon, feature, extra in links:
			if check and not _on(s, feature):
				continue
			if check and ltype in LINK_DOCTYPE and not frappe.db.exists(LINK_DOCTYPE[ltype], target):
				continue
			items.append({"key": item_key(ltype, target, extra), "label": label, "link_type": ltype, "target": target, "icon": icon,
				"feature": feature, "extra": extra})
		out.append({"key": group_key(group), "label": group, "icon": gicon, "items": items})
	return out


def rows_from_groups(groups):
	"""Workspace Sidebar rows from nav_groups(): the first Overview link on top (what the desktop tile opens), then a
	section per group. Rows carry "hs_key" (dropped when the sidebar is saved; used by the boot-time menu overrides)."""
	rows = []
	has_filters = None
	for g in groups:
		kept = []
		for it in g["items"]:
			row = {"type": "Link", "label": it["label"], "link_type": it["link_type"], "icon": it["icon"], "child": 1, "indent": 0,
				"collapsible": 1, "hs_key": it["key"]}
			if it["link_type"] == "URL":
				row["url"] = it["target"]
			else:
				row["link_to"] = it["target"]
			if (it.get("extra") or {}).get("filters"):
				if has_filters is None:
					has_filters = frappe.get_meta(item_doctype()).has_field("filters")
				if has_filters:
					row["filters"] = json.dumps(it["extra"]["filters"])
			kept.append(row)
		if not kept:
			continue
		if g["key"] == "g:overview":
			# the first link is what the desktop tile opens: Home, at the top, outside any section
			# (v1.8.1: at the very top even when the menu builder moves another group above Overview)
			rows.insert(0, dict(kept[0], child=0))
			kept = kept[1:]
		rows.append({"type": "Section Break", "label": g["label"], "icon": g["icon"], "indent": 1, "collapsible": 1,
			"keep_closed": 0 if g["key"] in ("g:overview", "g:sales") else 1, "hs_key": g["key"]})
		rows.extend(kept)
	return rows


def sidebar_items(s=None):
	"""The rows of the Hipersign ERP sidebar for the features switched on, skipping anything this site lacks."""
	return rows_from_groups(nav_groups(s or _s()))


def _route(ltype, target):
	if ltype == "DocType":
		return ["List", target] if not frappe.get_meta(target).issingle else ["Form", target]
	if ltype == "Report":
		return ["query-report", target]
	if ltype == "Page":
		return [target]
	if ltype == "Workspace":
		return ["Workspaces", target]
	return None


def sub_items():
	"""The sub-items each user may open, for the desk menu (boot info)."""
	from hipersign_trading.utils import can_read

	s = _s()
	out = {}
	for entry, rows in NAV_SUB.items():
		kept = []
		for label, ltype, target, feature in rows:
			if not _on(s, feature):
				continue
			if ltype in LINK_DOCTYPE and not frappe.db.exists(LINK_DOCTYPE[ltype], target):
				continue
			if ltype == "DocType" and not can_read(target):
				continue
			if ltype == "Report" and not frappe.get_cached_doc("Report", target).is_permitted():
				continue
			if ltype == "Page" and not frappe.get_cached_doc("Page", target).is_permitted():
				continue
			row = {"label": label, "route": _route(ltype, target), "target": target}
			# v1.8.4 (#34/#37): open the Hipersign page and tab, when the user may open that page
			to = SUB_TABS.get((entry, label))
			if to and frappe.db.exists("Page", to[0]) and frappe.get_cached_doc("Page", to[0]).is_permitted():
				row.update({"route": [to[0]], "target": to[0], "tab": to[1], "chip": SUB_CHIPS.get((entry, label))})
			kept.append(row)
		if entry in REPORT_GROUP and frappe.db.exists("Page", "hipersign-reports"):
			kept.append({"label": "Reports", "route": ["hipersign-reports"], "target": "hipersign-reports", "group": REPORT_GROUP[entry]})
		if kept:
			out[entry] = kept
	return out


def ensure_sidebar(s=None):
	m = model()
	if not m:
		return
	s = s or _s()
	if m == "sidebar":
		return ensure_module_sidebar(s)
	meta = frappe.get_meta("Workspace Sidebar Item")
	items = [{k: v for k, v in r.items() if meta.has_field(k) or k in ("type",)} for r in sidebar_items(s)]
	if frappe.db.exists("Workspace Sidebar", SIDEBAR):
		doc = frappe.get_doc("Workspace Sidebar", SIDEBAR)
		doc.set("items", [])
	else:
		doc = frappe.new_doc("Workspace Sidebar")
		doc.title = SIDEBAR
	for r in items:
		doc.append("items", r)
	for k, v in (("header_icon", "house"), ("module", "Hipersign Trading"), ("app", "hipersign_trading"), ("standard", 0)):
		if doc.meta.has_field(k):
			doc.set(k, v)
	doc.flags.ignore_links = True
	doc.flags.ignore_permissions = True
	doc.save() if not doc.is_new() else doc.insert()


# ---------------------------------------------------------------- v1.8.1: Frappe 16.30+ (Sidebar documents)
SYSTEM_WRITE_FLAGS = ("in_import", "in_fixtures", "in_migrate", "in_install", "in_patch")
ROW_FIELDS = ("type", "label", "link_type", "link_to", "url", "icon", "child", "indent", "collapsible", "keep_closed", "filters")


class _system_write:
	"""A Sidebar belongs to its app: Frappe lets it be written only in developer mode or while the system places app
	content (install, migrate, patch). Install and migrate already say so; a settings save (feature switches) is the
	app placing its own menu too, so it is marked the same way for the duration of the write."""

	def __enter__(self):
		self.set = not any(frappe.flags.get(f) for f in SYSTEM_WRITE_FLAGS)
		if self.set:
			frappe.flags.in_patch = True
		return self

	def __exit__(self, *exc):
		if self.set:
			frappe.flags.in_patch = False
		return False


def _row_sig(rows):
	def val(r, f):
		if f in ("child", "indent", "collapsible", "keep_closed"):
			return int(r.get(f) or 0)
		if f in ("link_type", "link_to", "url") and r.get("type") != "Link":
			return None  # a section break links nowhere (the column default says DocType)
		return r.get(f) or None

	return [tuple(val(r, f) for f in ROW_FIELDS) for r in rows]


def converted_sidebars():
	"""Sidebars Frappe made of our module's old Workspace Sidebars on its upgrade (not standard, merged from ours)."""
	out = []
	for r in frappe.get_all("Sidebar", filters={"module": MODULE, "standard": 0, "name": ["!=", SIDEBAR]}, fields=["name", "merged_from"]):
		merged = r.merged_from or ""
		if r.name in LEGACY_SIDEBARS or any(n in merged for n in LEGACY_SIDEBARS):
			out.append(r.name)
	return out


def drop_converted(keys=()):
	"""Remove the converted sidebars: ours replaces them. Rows that are not in our menu are written to the Error Log
	(title "Hipersign menu: converted sidebar replaced") — and stay in Frappe's Workspace Sidebar archive."""
	for name in converted_sidebars():
		doc = frappe.get_doc("Sidebar", name)
		extra = [{f: r.get(f) for f in ("type", "label", "link_type", "link_to", "url")} for r in doc.items
			if r.type == "Link" and (r.link_type, r.link_to or r.url) not in keys]
		if extra:
			frappe.log_error(title="Hipersign menu: converted sidebar replaced",
				message=f"Frappe's converted sidebar “{name}” (merged from {doc.merged_from}) was replaced by “{SIDEBAR}”. "
				"Rows that were not in the Hipersign menu (still in the Workspace Sidebar archive):\n" + json.dumps(extra, indent=1))
		frappe.delete_doc("Sidebar", name, ignore_permissions=True, force=True)


def ensure_module_sidebar(s):
	"""Frappe 16.30+: our module's one Sidebar, "Hipersign ERP", from nav_groups() — rebuilt on install, migrate and
	settings change. Unchanged rows are not written again."""
	meta = frappe.get_meta("Sidebar Item")
	rows = [{k: v for k, v in r.items() if meta.has_field(k) or k == "type"} for r in sidebar_items(s)]
	keys = {(r.get("link_type"), r.get("link_to") or r.get("url")) for r in rows}
	with _system_write():
		drop_converted(keys)
		if frappe.db.exists("Sidebar", SIDEBAR):
			doc = frappe.get_doc("Sidebar", SIDEBAR)
			same = _row_sig(rows) == _row_sig([r.as_dict() for r in doc.items]) and doc.module == MODULE \
				and doc.app == "hipersign_trading" and doc.header_icon == "house" and not doc.standard
			if same:
				return
			doc.set("items", [])
		else:
			doc = frappe.new_doc("Sidebar")
			doc.title = SIDEBAR
		doc.module = MODULE
		doc.app = "hipersign_trading"
		doc.header_icon = "house"
		doc.standard = 0
		for r in rows:
			doc.append("items", r)
		doc.flags.ignore_links = True
		doc.flags.ignore_permissions = True
		doc.save() if not doc.is_new() else doc.insert()


def ensure_tile():
	if not supported():
		return
	vals = {"label": TILE, "icon_type": "Link", "link_type": "Workspace Sidebar", "link_to": SIDEBAR, "app": "hipersign_trading",
		"icon": "house", "idx": -1, "hidden": 0, "standard": 1, "bg_color": "blue", "restrict_removal": 1}
	meta = frappe.get_meta("Desktop Icon")
	if meta.has_field("icon_image"):
		vals["icon_image"] = LOGO
	vals = {k: v for k, v in vals.items() if meta.has_field(k)}
	if frappe.db.exists("Desktop Icon", TILE):
		doc = frappe.get_doc("Desktop Icon", TILE)
		doc.update({k: v for k, v in vals.items() if k != "hidden"})
		doc.hidden = 0
	else:
		doc = frappe.new_doc("Desktop Icon")
		doc.update(vals)
	doc.flags.ignore_links = True
	doc.flags.ignore_permissions = True
	doc.save() if not doc.is_new() else doc.insert()


def _ours(icon):
	"""v1.5.6: with "only Hipersign tiles" on, the one Hipersign ERP tile stays and nothing else — sister apps' tiles
	(branding, mobile) used to show a second Hipersign tile on the desktop."""
	return icon.name == TILE


def apply_desktop(s=None):
	"""Show only the Hipersign tile (and our sister apps' tiles) when the option is on; undo exactly what we hid."""
	if not supported():
		return
	s = s or _s()
	hidden_before = set(json.loads(s.get("hs_hidden_icons") or "[]"))
	want = bool(s.get("only_hipersign_tiles"))
	hide_now = set()
	for icon in frappe.get_all("Desktop Icon", filters={"owner": ["in", ["Administrator", None]]}, fields=["name", "app", "hidden", "parent_icon"]):
		if _ours(icon):
			continue
		if want and not icon.hidden:
			hide_now.add(icon.name)
		elif want and icon.name in hidden_before:
			hide_now.add(icon.name)
	for name in hide_now:
		frappe.db.set_value("Desktop Icon", name, "hidden", 1, update_modified=False)
	for name in hidden_before - hide_now:
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "hidden", 0, update_modified=False)
	frappe.db.set_single_value(SETTINGS, "hs_hidden_icons", json.dumps(sorted(hide_now)))
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")


DEFAULTS = (("desk_theme", "Hipersign"), ("only_hipersign_tiles", 1), ("open_home_after_login", 1), ("keep_hipersign_sidebar", 1),
	("hide_getting_started", 1))


def ensure_defaults():
	"""Settings added in 1.4 get their defaults once (a single doctype keeps no defaults of its own)."""
	if not frappe.get_meta(SETTINGS).has_field("desk_theme"):
		return
	have = {r[0] for r in frappe.db.sql("select field from `tabSingles` where doctype = %s", SETTINGS)}
	for f, v in DEFAULTS:
		if f not in have:
			frappe.db.set_single_value(SETTINGS, f, v)


def apply(s=None):
	"""Called on install, migrate and whenever the settings change. Never stops a settings save."""
	frappe.db.savepoint("hs_nav")
	try:
		_apply()
	except Exception:
		frappe.db.rollback(save_point="hs_nav")
		frappe.log_error(title="Hipersign menu and desktop")


def _apply():
	ensure_defaults()
	s = frappe.get_doc(SETTINGS)  # fresh: defaults may have just been written
	if frappe.get_meta("System Settings").has_field("enable_onboarding") and frappe.get_meta(SETTINGS).has_field("hide_getting_started"):
		want = 0 if s.get("hide_getting_started") else 1
		if frappe.db.get_single_value("System Settings", "enable_onboarding") != want:
			frappe.db.set_single_value("System Settings", "enable_onboarding", want)
	if supported():
		ensure_sidebar(s)
		ensure_tile()
		apply_desktop(s)
	frappe.clear_cache()


def remove():
	"""Uninstall: give back the tiles we hid and remove our sidebar and tile."""
	if not supported():
		try:
			if frappe.db.get_single_value(SETTINGS, "hide_getting_started"):
				frappe.db.set_single_value("System Settings", "enable_onboarding", 1)
		except Exception:
			pass
		return
	try:
		hidden = json.loads(frappe.db.get_single_value(SETTINGS, "hs_hidden_icons") or "[]")
	except Exception:
		hidden = []
	for name in hidden:
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "hidden", 0, update_modified=False)
	try:
		if frappe.db.get_single_value(SETTINGS, "hide_getting_started") and frappe.get_meta("System Settings").has_field("enable_onboarding"):
			frappe.db.set_single_value("System Settings", "enable_onboarding", 1)
	except Exception:
		pass
	sidebar_dt = "Sidebar" if model() == "sidebar" else "Workspace Sidebar"
	with _system_write():
		for dt, name in (("Desktop Icon", TILE), (sidebar_dt, SIDEBAR)):
			if frappe.db.exists(dt, name):
				frappe.delete_doc(dt, name, ignore_permissions=True, force=True)
	frappe.cache.delete_key("desktop_icons")
