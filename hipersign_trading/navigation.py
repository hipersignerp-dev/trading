"""v1.4 — the prototype's navigation on the ERPNext desk.

One sidebar, “Hipersign ERP”, holds the prototype's menu groups (Overview, Sales, Purchasing, Inventory & Delivery,
Finance & Tax, People & Assets, Admin). One desktop tile opens it. Our desk script keeps that sidebar on screen for
every page it lists, so the menu stays put the way it does in the prototype.

Optionally (Hipersign Settings → Look & menus) every other desktop tile is hidden; the ones we hide are remembered
and shown again when the option is switched off or the app is uninstalled.

Works with the Frappe 16 desk model that has Desktop Icon + Workspace Sidebar (Frappe 16.x up to the sidebar
rework). On a desk without those doctypes nothing happens.
"""

import json
import re

import frappe

from hipersign_trading.features import field

SETTINGS = "Hipersign Settings"
SIDEBAR = "Hipersign ERP"
TILE = "Hipersign ERP"
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
		("Workflows & Settings", "DocType", "Hipersign Settings", "sliders-horizontal", None, {}),
		("Menu builder", "Page", "hipersign-menu", "menu", None, {}),  # v1.8.0
		("Document Centre", "Report", "Missing Documents", "file-warning", None, {}),
		("Data Migration", "DocType", "Data Import", "upload", None, {}),
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
}

# count badges, as in the prototype
NAV_BADGES = ("Messages", "Approvals", "Insights & Alerts", "CRM & Leads")

LINK_DOCTYPE = {"DocType": "DocType", "Report": "Report", "Page": "Page", "Workspace": "Workspace"}


def supported():
	"""Frappe 16 up to the sidebar rework (16.29 is what the Hipersign servers run). Later Frappe 16 releases
	replace Workspace Sidebar with per-module “Sidebar” documents and archive the old ones: there the menu is
	left to Frappe (the theme still applies)."""
	if frappe.db.exists("DocType", "Sidebar"):
		return False
	return frappe.db.table_exists("Workspace Sidebar") and frappe.db.table_exists("Desktop Icon") \
		and frappe.get_meta("Workspace Sidebar").has_field("items")


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
					has_filters = frappe.get_meta("Workspace Sidebar Item").has_field("filters")
				if has_filters:
					row["filters"] = json.dumps(it["extra"]["filters"])
			kept.append(row)
		if not kept:
			continue
		if g["key"] == "g:overview":
			# the first link is what the desktop tile opens: Home, at the top, outside any section
			rows.append(dict(kept[0], child=0))
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
			kept.append({"label": label, "route": _route(ltype, target), "target": target})
		if kept:
			out[entry] = kept
	return out


def ensure_sidebar(s=None):
	if not supported():
		return
	s = s or _s()
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
	for dt, name in (("Desktop Icon", TILE), ("Workspace Sidebar", SIDEBAR)):
		if frappe.db.exists(dt, name):
			frappe.delete_doc(dt, name, ignore_permissions=True, force=True)
	frappe.cache.delete_key("desktop_icons")
