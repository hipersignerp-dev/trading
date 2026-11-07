"""v1.8.4 (#37): the Reports page — every report this user may open, grouped (Sales, Purchasing, Stock, Finance, VAT & tax,
HR, Projects, Manufacturing), with search and favourites. A report opens in Frappe's report view, styled by the Hipersign
theme (hs_reports.css)."""

import json

import frappe
from frappe import _

FAV_KEY = "hs_report_favs"

# (group key, label, icon, [report names]) — the reports a trading, projects and factory business uses; reports this site
# lacks or the user may not open are left out
GROUPS = [
	("sales", "Sales", "tag", ["Sales Analytics", "Sales Order Analysis", "Sales Register", "Item-wise Sales Register", "Quotation Trends", "Sales Order Trends",
		"Customer Ledger Summary", "Accounts Receivable", "Accounts Receivable Summary", "Sales Person-wise Transaction Summary", "Customer Acquisition and Loyalty",
		"Lead Details", "Lost Opportunity", "Inactive Customers"]),
	("purchasing", "Purchasing", "shopping-cart", ["Purchase Analytics", "Purchase Order Analysis", "Purchase Register", "Item-wise Purchase Register",
		"Purchase Order Trends", "Supplier Quotation Comparison", "Supplier Ledger Summary", "Accounts Payable", "Accounts Payable Summary", "Hipersign Smart Reorder",
		"Procurement Tracker", "Landed Cost Report"]),
	("stock", "Stock", "warehouse", ["Stock Balance", "Stock Ledger", "Stock Projected Qty", "Stock Ageing", "Warehouse wise Item Balance Age and Value",
		"Stock Analytics", "Batch-Wise Balance History", "Serial No Ledger", "Item Shortage Report", "Delivery Note Trends", "Purchase Receipt Trends",
		"Stock and Account Value Comparison", "Itemwise Recommended Reorder Level"]),
	("finance", "Finance", "banknote", ["General Ledger", "Trial Balance", "Profit and Loss Statement", "Balance Sheet", "Cash Flow", "Gross Profit",
		"Accounts Receivable", "Accounts Payable", "Bank Clearance Summary", "Bank Reconciliation Statement", "Payment Period Based On Invoice Date",
		"Budget Variance Report", "Hipersign Group Consolidation", "Consolidated Financial Statement", "Share Balance"]),
	("tax", "VAT & tax", "percent", ["UAE VAT 201", "Tax Withholding Details", "Sales Register", "Purchase Register", "Missing Documents"]),
	("hr", "HR & payroll", "user", ["Monthly Attendance Sheet", "Employee Leave Balance", "Employee Leave Balance Summary", "Salary Register",
		"Employee Advance Summary", "Employee Analytics", "Employee Birthday", "Employees working on a holiday"]),
	("projects", "Projects", "hard-hat", ["Project Summary", "Daily Timesheet Summary", "Project wise Stock Tracking", "Delayed Tasks Summary",
		"Timesheet Billing Summary"]),
	("manufacturing", "Manufacturing", "factory", ["Production Planning Report", "Work Order Summary", "BOM Stock Report", "BOM Explorer",
		"Job Card Summary", "Downtime Analysis", "Quality Inspection Summary", "Cost of Poor Quality Report", "Production Analytics", "Work Order Stock Report",
		"BOM Operations Time"]),
]


def _favs():
	try:
		return json.loads(frappe.defaults.get_user_default(FAV_KEY) or "[]")
	except Exception:
		return []


@frappe.whitelist()
def get_reports():
	names = {n for g in GROUPS for n in g[3]}
	meta = {r.name: r for r in frappe.get_all("Report", filters={"name": ["in", list(names)], "disabled": 0},
		fields=["name", "ref_doctype", "report_type", "module", "add_total_row"])}
	allowed = {}
	for n, r in meta.items():
		try:
			if frappe.get_cached_doc("Report", n).is_permitted() and (not r.ref_doctype or frappe.has_permission(r.ref_doctype, "read")):
				allowed[n] = r
		except Exception:
			pass
	groups = []
	for key, label, icon, reps in GROUPS:
		items = [{"name": n, "label": _(n), "doctype": _(allowed[n].ref_doctype or ""), "type": allowed[n].report_type} for n in reps if n in allowed]
		if items:
			groups.append({"key": key, "label": _(label), "icon": icon, "reports": items})
	return {"groups": groups, "favourites": [f for f in _favs() if f in allowed]}


@frappe.whitelist(methods=["POST"])
def set_favourite(report, on=1):
	favs = [f for f in _favs() if f != report]
	if frappe.utils.cint(on):
		if not frappe.db.exists("Report", report):
			frappe.throw(_("Unknown report"))
		favs.insert(0, report)
	frappe.defaults.set_user_default(FAV_KEY, json.dumps(favs[:40]))
	return favs
