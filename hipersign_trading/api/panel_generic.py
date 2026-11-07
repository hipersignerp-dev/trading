"""v1.8.4: a record panel for the masters and the less common documents that module lists show — price list, warehouse,
bank transaction, account, company, attendance, cost centre, workstation, operation, routing, task, timesheet… Before,
a click on such a row left the Hipersign page for the full ERPNext form. The panel shows the record's main fields
(the ones the list view, the title and the required fields use), its child tables as counts, the history and
"Open full form" for everything else."""

import frappe
from frappe import _
from frappe.utils import cstr

from hipersign_trading.api.panel import _base, act, d, kv, money, section

# the doctypes that get this panel (they have no panel of their own); keep in step with hs_panel.js GENERIC
GENERIC = (
	"Price List", "Warehouse", "Bank Transaction", "Account", "Company", "Attendance", "Cost Center", "Workstation", "Operation", "Routing",
	"Task", "Timesheet", "Supplier Quotation", "Stock Reconciliation", "Quality Inspection Template", "Pricing Rule", "Period Closing Voucher",
	"Opportunity", "Exchange Rate Revaluation", "Accounting Period", "Daily Site Report", "Back Charge", "Document Waiver",
	"Company Document Type", "Hipersign Document Rule", "Bank Account", "Holiday List", "Salary Structure", "Shift Type", "Vehicle", "Driver",
	"Customer Group", "Supplier Group", "Item Group", "Payment Terms Template", "Sales Taxes and Charges Template", "Purchase Taxes and Charges Template",
)

SKIP = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold", "Heading", "Image", "Attach Image", "Signature", "Password",
	"Code", "Text Editor", "HTML Editor", "Markdown Editor", "Geolocation", "JSON"}


def _value(doc, df):
	v = doc.get(df.fieldname)
	if v in (None, "", 0) and df.fieldtype not in ("Check",):
		return None
	if df.fieldtype == "Check":
		return _("Yes") if v else None
	if df.fieldtype in ("Currency",):
		cur = doc.get(df.options) if df.options and doc.meta.has_field(df.options) else None
		return money(v, cur)
	if df.fieldtype in ("Date",):
		return d(v)
	if df.fieldtype in ("Datetime",):
		return frappe.format(v, df)
	if df.fieldtype in ("Float", "Int", "Percent"):
		return frappe.format(v, df)
	if df.fieldtype in ("Select",):
		return _(cstr(v))
	if df.fieldtype in ("Small Text", "Text", "Long Text"):
		s = cstr(v).strip()
		return s[:300] + ("…" if len(s) > 300 else "")
	return cstr(v)


def generic(doc):
	meta = doc.meta
	title = doc.get(meta.title_field) if meta.title_field and doc.get(meta.title_field) else doc.name
	p = _base(doc, title if title == doc.name else f"{title} · {doc.name}", _(doc.doctype))
	main, rest = [], []
	for df in meta.fields:
		if df.fieldtype in SKIP or df.hidden or df.fieldtype in ("Table", "Table MultiSelect") or df.fieldname == meta.title_field:
			continue
		if df.permlevel and not frappe.has_permission(doc.doctype, "read", doc):
			continue
		v = _value(doc, df)
		if v is None:
			continue
		(main if (df.in_list_view or df.bold or df.reqd or df.in_standard_filter) else rest).append((_(df.label or df.fieldname), v))
	p["facts"] = kv(*main[:6])
	p["sections"] = [section("Details", kv(*(main[6:] + rest)[:16]))]
	tables = [(df.label or df.fieldname, len(doc.get(df.fieldname) or [])) for df in meta.fields if df.fieldtype == "Table" and not df.hidden]
	tables = [(_(lab), n) for lab, n in tables if n]
	if tables:
		p["sections"].append(section("Lines", kv(*[(lab, _("{0} rows").format(n)) for lab, n in tables])))
	p["actions"] = [act("Open full form", kind="primary" if p["can_edit"] else "default", route=["Form", doc.doctype, doc.name])]
	return p


BUILDERS = {dt: generic for dt in GENERIC}
