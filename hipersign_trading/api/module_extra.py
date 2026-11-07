"""v1.8.4 (#34/#37): every sidebar sub-item opens a Hipersign page or a tab of one.

Most sub-items already have a tab on their module page (navigation.SUB_TABS points them there). The few lists that had
no tab get one here — Opportunities, Pick lists, Warranty claims, Payments, the Projects and Manufacturing step logs,
Routings & operations, Inspection templates — added to the module definitions by get_module(), with rows from rows().
The Document Centre is a page of its own (key "doccentre"): missing documents, exceptions (Document Waiver) and rules.
Same row format as the module pages (hs_module.js): a row opens the record panel (or the form), chips filter, search
matches the shown text."""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from hipersign_trading.api.module import _fields, _perm, _scope, kpi
from hipersign_trading.utils import can_read


def _match(q, *vals):
	return not q or any(q.lower() in str(v or "").lower() for v in vals)


def _companies(doctype, f, cos):
	if frappe.get_meta(doctype).has_field("company"):
		f["company"] = ["in", cos]
	return f


PILL = {"Open": "blue", "Draft": "grey", "Submitted": "blue", "Completed": "green", "Closed": "grey", "Cancelled": "red", "Lost": "red",
	"Converted": "green", "Quotation": "violet", "Replied": "blue", "Pending": "orange", "Approved": "green", "Rejected": "red",
	"Received": "green", "Work In Progress": "blue", "Resolved": "green", "To Bill": "blue"}


def _pill(s):
	return {"pill": s or "—", "tone": PILL.get(s or "", "grey")} if s else "—"


# ---------------------------------------------------------------- extra tabs per module key
# (key, tab key, label, feature or None, doctype, chips)
def _extra():
	"""Built per call so the labels follow the user's language."""
	return {
		"crm": [("opps", _("Opportunities"), None, "Opportunity", [["open", _("Open")], ["all", _("All")], ["won", _("Converted")], ["lost", _("Lost")]])],
		"stock": [("picks", _("Pick lists"), "multiwh", "Pick List", [["open", _("Open")], ["all", _("All")]]),
			("claims", _("Warranty claims"), "serial", "Warranty Claim", [["open", _("Open")], ["all", _("All")]])],
		"finance": [("payments", _("Payments"), None, "Payment Entry", [["all", _("All")], ["in", _("Received")], ["out", _("Paid")], ["draft", _("Draft")]])],
		"pj_home": [("log", _("Step log"), None, "Project Step Log", [])],
		"mf_prod": [("log", _("Step log"), None, "Manufacturing Step Log", [])],
		"mf_bom": [("routing", _("Routings & operations"), None, "Routing", [["routing", _("Routings")], ["ops", _("Operations")]])],
		"mf_qc": [("tpl", _("Inspection templates"), None, "Quality Inspection Template", [])],
	}


def _feature_on(feature):
	if not feature:
		return True
	try:
		from hipersign_trading.features import feature_on

		return feature_on(feature)
	except Exception:
		return True


def _tabs_for(key):
	return [t for t in _extra().get(key, []) if _feature_on(t[2]) and frappe.db.exists("DocType", t[3]) and _perm(t[3])]


def extend(key, m):
	"""Add this module's extra tabs (the user may read) after its own."""
	try:
		have = {t["key"] for t in m.get("tabs") or []}
		for tk, label, feature, dt, chips in _tabs_for(key):
			if tk not in have:
				m.setdefault("tabs", []).append({"key": tk, "label": label, "chips": chips})
	except Exception:
		frappe.log_error(title=f"Hipersign extra tabs {key}")
	return m


def has_tab(key, tab):
	if key in PAGES:
		return True
	return any(t[0] == tab for t in _extra().get(key, []))


def rows(key, tab, chip=None, q=None):
	if key in PAGES:
		return doccentre_rows(tab, chip, q)
	spec = next((t for t in _extra().get(key, []) if t[0] == tab), None)
	if not spec or not frappe.db.exists("DocType", spec[3]) or not _perm(spec[3]):
		return {"cols": [], "rows": [], "empty": _("You do not have access to this list.")}
	return globals()["_rows_" + key + "_" + tab](chip or (spec[4][0][0] if spec[4] else None), q)


def _cols(*labels):
	return [{"label": l} if isinstance(l, str) else l for l in labels]


# ---------------------------------------------------------------- CRM › Opportunities
def _rows_crm_opps(chip, q):
	cos = _scope()[0]
	f = _companies("Opportunity", {}, cos)
	if chip == "open":
		f["status"] = ["in", ["Open", "Replied", "Quotation"]]
	elif chip == "won":
		f["status"] = "Converted"
	elif chip == "lost":
		f["status"] = ["in", ["Lost", "Closed"]]
	fl = _fields("Opportunity", ["name", "party_name", "customer_name", "opportunity_from", "status", "opportunity_amount", "currency", "expected_closing",
		"transaction_date", "opportunity_owner", "sales_stage", "probability"])
	rs = frappe.get_list("Opportunity", filters=f, fields=fl, order_by="transaction_date desc", limit=200)
	t = getdate(today())
	return {"cols": _cols(_("Opportunity"), _("Customer / lead"), _("Stage"), {"label": _("Value"), "cls": "num"}, _("Expected close"), _("Owner"), _("Status")),
		"rows": [{"dt": "Opportunity", "name": r.name, "cells": [{"code": r.name}, {"main": r.get("customer_name") or r.get("party_name") or "—", "sub": _(r.get("opportunity_from") or "")},
			r.get("sales_stage") or "—", {"money": r.get("opportunity_amount"), "currency": r.get("currency")},
			{"date": r.get("expected_closing"), "late": bool(r.get("expected_closing") and getdate(r.expected_closing) < t and r.status in ("Open", "Replied"))},
			frappe.utils.get_fullname(r.get("opportunity_owner")) if r.get("opportunity_owner") else "—", _pill(r.status)]}
			for r in rs if _match(q, r.name, r.get("customer_name"), r.get("party_name"), r.get("sales_stage"))],
		"empty": _("No opportunities.")}


# ---------------------------------------------------------------- Warehouse & Stock › Pick lists, Warranty claims
def _rows_stock_picks(chip, q):
	cos = _scope()[0]
	f = _companies("Pick List", {"docstatus": ["<", 2]}, cos)
	if chip == "open":
		f["status"] = ["not in", ["Completed", "Cancelled"]]
	fl = _fields("Pick List", ["name", "purpose", "customer", "status", "parent_warehouse", "creation", "docstatus"])
	rs = frappe.get_list("Pick List", filters=f, fields=fl, order_by="creation desc", limit=200)
	n = {}
	for r in frappe.get_all("Pick List Item", filters={"parent": ["in", [x.name for x in rs] or [""]]}, fields=["parent", "qty", "picked_qty"]):
		x = n.setdefault(r.parent, frappe._dict(n=0, qty=0, picked=0))
		x.n += 1
		x.qty += flt(r.qty)
		x.picked += flt(r.picked_qty)
	return {"cols": _cols(_("Pick list"), _("For"), _("Warehouse"), {"label": _("Lines"), "cls": "num"}, {"label": _("Picked"), "cls": "num"}, _("Created"), _("Status")),
		"rows": [{"dt": "Pick List", "name": r.name, "cells": [{"code": r.name}, {"main": r.get("customer") or "—", "sub": _(r.get("purpose") or "")},
			r.get("parent_warehouse") or "—", (n.get(r.name) or {}).get("n") or 0,
			f"{flt((n.get(r.name) or {}).get('picked')):,.0f} / {flt((n.get(r.name) or {}).get('qty')):,.0f}", {"date": str(r.creation)[:10]},
			_pill(r.get("status") or ("Draft" if r.docstatus == 0 else "Submitted"))]} for r in rs if _match(q, r.name, r.get("customer"), r.get("parent_warehouse"))],
		"empty": _("No pick lists.")}


def _rows_stock_claims(chip, q):
	cos = _scope()[0]
	f = _companies("Warranty Claim", {}, cos)
	if chip == "open":
		f["status"] = ["in", ["Open", "Work In Progress"]]
	fl = _fields("Warranty Claim", ["name", "customer", "customer_name", "serial_no", "item_code", "item_name", "status", "complaint_date", "warranty_amc_status",
		"complaint", "resolution_date"])
	rs = frappe.get_list("Warranty Claim", filters=f, fields=fl, order_by="complaint_date desc", limit=200)
	return {"cols": _cols(_("Claim"), _("Customer"), _("Item / serial"), _("Warranty"), _("Reported"), _("Resolved"), _("Status")),
		"rows": [{"dt": "Warranty Claim", "name": r.name, "cells": [{"code": r.name}, r.get("customer_name") or r.get("customer") or "—",
			{"main": r.get("item_name") or r.get("item_code") or "—", "sub": r.get("serial_no") or ""}, _(r.get("warranty_amc_status") or "—"),
			{"date": r.get("complaint_date")}, {"date": str(r.resolution_date)[:10] if r.get("resolution_date") else None}, _pill(r.status)]}
			for r in rs if _match(q, r.name, r.get("customer_name"), r.get("customer"), r.get("serial_no"), r.get("item_code"), r.get("item_name"))],
		"empty": _("No warranty claims.")}


# ---------------------------------------------------------------- Finance › Payments
def _rows_finance_payments(chip, q):
	cos, start, end, label, cur = _scope()
	f = {"company": ["in", cos], "docstatus": ["<", 2]}
	if chip == "in":
		f.update({"payment_type": "Receive", "docstatus": 1})
	elif chip == "out":
		f.update({"payment_type": "Pay", "docstatus": 1})
	elif chip == "draft":
		f["docstatus"] = 0
	rs = frappe.get_list("Payment Entry", filters=f, fields=["name", "posting_date", "payment_type", "party_type", "party", "party_name", "mode_of_payment",
		"paid_amount", "paid_from_account_currency", "received_amount", "paid_to_account_currency", "reference_no", "docstatus"], order_by="posting_date desc, creation desc", limit=200)
	return {"cols": _cols(_("Payment"), _("Date"), _("Type"), _("Party"), _("Mode"), _("Reference"), {"label": _("Amount"), "cls": "num"}, _("Status")),
		"rows": [{"dt": "Payment Entry", "name": r.name, "cells": [{"code": r.name}, {"date": r.posting_date},
			{"text": _("Received") if r.payment_type == "Receive" else _("Paid") if r.payment_type == "Pay" else _(r.payment_type), "tone": "green" if r.payment_type == "Receive" else ""},
			{"main": r.party_name or r.party or "—", "sub": _(r.party_type or "")}, _(r.mode_of_payment or "—"), r.reference_no or "—",
			{"money": r.received_amount if r.payment_type == "Receive" else r.paid_amount,
				"currency": r.paid_to_account_currency if r.payment_type == "Receive" else r.paid_from_account_currency},
			_pill("Draft" if r.docstatus == 0 else "Submitted")]} for r in rs if _match(q, r.name, r.party_name, r.party, r.reference_no, r.mode_of_payment)],
		"empty": _("No payments.")}


# ---------------------------------------------------------------- Projects / Manufacturing › Step logs
def _rows_pj_home_log(chip, q):
	rs = frappe.get_list("Project Step Log", fields=["name", "project", "step", "step_name", "completed_by", "completed_on", "note"], order_by="completed_on desc", limit=200)
	return {"cols": _cols(_("Project"), _("Step"), _("Done by"), _("When"), _("Note")),
		"rows": [{"dt": "Project", "name": r.project, "cells": [{"code": r.project}, {"main": _(r.step_name or ""), "sub": _("Step {0}").format(r.step) if r.step else ""},
			frappe.utils.get_fullname(r.completed_by) if r.completed_by else "—", {"date": str(r.completed_on)[:10] if r.completed_on else None}, r.note or "—"]}
			for r in rs if r.project and _match(q, r.project, r.step_name, r.note)], "empty": _("No steps recorded yet.")}


def _rows_mf_prod_log(chip, q):
	# the factory pages follow their own company scope (module_mfg), so the log is not cut to the top bar's companies
	rs = frappe.get_list("Manufacturing Step Log", fields=["name", "sales_order", "work_order", "step", "step_name",
		"completed_by", "completed_on", "note"], order_by="completed_on desc", limit=200)
	return {"cols": _cols(_("Order"), _("Work order"), _("Step"), _("Done by"), _("When"), _("Note")),
		"rows": [{"dt": "Work Order" if r.work_order else "Sales Order", "name": r.work_order or r.sales_order, "cells": [{"code": r.sales_order or "—"}, r.work_order or "—",
			{"main": _(r.step_name or ""), "sub": _("Step {0}").format(r.step) if r.step else ""}, frappe.utils.get_fullname(r.completed_by) if r.completed_by else "—",
			{"date": str(r.completed_on)[:10] if r.completed_on else None}, r.note or "—"]}
			for r in rs if (r.work_order or r.sales_order) and _match(q, r.sales_order, r.work_order, r.step_name, r.note)], "empty": _("No steps recorded yet.")}


# ---------------------------------------------------------------- BOMs › Routings & operations, Quality › Inspection templates
def _rows_mf_bom_routing(chip, q):
	if chip == "ops":
		if not _perm("Operation"):
			return {"cols": [], "rows": []}
		rs = frappe.get_list("Operation", fields=_fields("Operation", ["name", "workstation", "description", "is_corrective_operation"]), order_by="name asc", limit=300)
		return {"cols": _cols(_("Operation"), _("Default workstation"), _("Description")),
			"rows": [{"dt": "Operation", "name": r.name, "cells": [{"code": r.name}, r.get("workstation") or "—", (r.get("description") or "—")[:120]]}
				for r in rs if _match(q, r.name, r.get("workstation"), r.get("description"))], "empty": _("No operations.")}
	rs = frappe.get_list("Routing", fields=_fields("Routing", ["name", "routing_name", "disabled", "modified"]), order_by="name asc", limit=200)
	ops = {}
	for r in frappe.get_all("BOM Operation", filters={"parenttype": "Routing", "parent": ["in", [x.name for x in rs] or [""]]},
		fields=["parent", "operation", "workstation", "time_in_mins", "idx"], order_by="idx asc"):
		ops.setdefault(r.parent, []).append(r)
	return {"cols": _cols(_("Routing"), _("Operations"), {"label": _("Minutes"), "cls": "num"}, _("Status")),
		"rows": [{"dt": "Routing", "name": r.name, "cells": [{"code": r.name},
			{"lines": [f"{o.idx}. {o.operation} · {o.workstation or '—'}" for o in ops.get(r.name, [])][:6]},
			f"{sum(flt(o.time_in_mins) for o in ops.get(r.name, [])):,.0f}", _pill("Disabled" if r.get("disabled") else "Open") if r.get("disabled") else {"pill": _("Active"), "tone": "green"}]}
			for r in rs if _match(q, r.name, *[o.operation for o in ops.get(r.name, [])])], "empty": _("No routings.")}


def _rows_mf_qc_tpl(chip, q):
	rs = frappe.get_list("Quality Inspection Template", fields=["name", "modified"], order_by="name asc", limit=200)
	params = {}
	for r in frappe.get_all("Item Quality Inspection Parameter", filters={"parent": ["in", [x.name for x in rs] or [""]]}, fields=["parent", "specification"]):
		params.setdefault(r.parent, []).append(r.specification)
	used = {}
	for r in frappe.get_all("Item", filters={"quality_inspection_template": ["in", [x.name for x in rs] or [""]]}, fields=["quality_inspection_template", "name"]):
		used[r.quality_inspection_template] = used.get(r.quality_inspection_template, 0) + 1
	return {"cols": _cols(_("Template"), _("Checks"), {"label": _("Items"), "cls": "num"}, _("Changed")),
		"rows": [{"dt": "Quality Inspection Template", "name": r.name, "cells": [{"code": r.name}, {"lines": [_(p) for p in params.get(r.name, [])][:6]},
			used.get(r.name, 0), {"date": str(r.modified)[:10]}]} for r in rs if _match(q, r.name, *params.get(r.name, []))],
		"empty": _("No inspection templates.")}


# ---------------------------------------------------------------- Document Centre (a page of its own)
PAGES = ("doccentre",)


def _blocks(r):
	return (r.get("level") or "").startswith("Block")


def _missing():
	"""Missing documents of the records this user may open, in the top bar's companies."""
	from hipersign_trading.doc_rules import missing_rows

	try:
		rows = missing_rows(None, None)
	except Exception:
		return []
	cos = _scope()[0]
	ok = {}
	out = []
	for r in rows:
		dt = r.get("reference_doctype")
		if dt not in ok:
			ok[dt] = bool(dt and can_read(dt))
		if ok[dt] and (not r.get("company") or r.get("company") in cos):
			out.append(r)
	return out


def page_module(key):
	miss = _missing()
	pend = frappe.db.count("Document Waiver", {"status": "Pending"}) if _perm("Document Waiver") else 0
	blocking = len([r for r in miss if _blocks(r)])
	rules = frappe.db.count("Hipersign Document Rule") if frappe.db.exists("DocType", "Hipersign Document Rule") and _perm("Hipersign Document Rule") else 0
	tabs = [{"key": "missing", "label": _("Missing documents") + (f" ({len(miss)})" if miss else ""), "chips": [["all", _("All")], ["blocking", _("Blocking")], ["required", _("Required")], ["exception", _("With an exception")]]}]
	if _perm("Document Waiver"):
		tabs.append({"key": "waivers", "label": _("Exceptions") + (f" ({pend})" if pend else ""), "chips": [["pending", _("Pending")], ["all", _("All")], ["approved", _("Approved")], ["rejected", _("Rejected")]]})
	if rules:
		tabs.append({"key": "rules", "label": _("Document rules"), "chips": []})
	return {
		"title": _("Document Centre"),
		"desc": _("Which records still miss a required document (trade licence, VAT certificate, packing list…), the exceptions asked for, and the rules behind them."),
		"new": [{"label": _("New exception"), "doctype": "Document Waiver"}] if frappe.has_permission("Document Waiver", "create") else [],
		"kpis": [
			kpi(_("Missing documents"), len(miss), _("{0} records").format(len({(r.reference_doctype, r.reference_name) for r in miss})), "red" if miss else "green", "triangle-alert", tab="missing", chip="all"),
			kpi(_("Blocking"), blocking, _("Stop the record being submitted"), "red" if blocking else "green", "ban", tab="missing", chip="blocking"),
			kpi(_("Exceptions waiting"), pend, _("Asked for, not yet decided"), "amber", "inbox", tab="waivers", chip="pending"),
			kpi(_("Document rules"), rules, _("Required or blocking documents"), "blue", "list-checks", tab="rules"),
		],
		"tabs": tabs,
	}


def doccentre_rows(tab, chip, q):
	if tab == "waivers":
		f = {}
		if chip in ("pending", "approved", "rejected"):
			f["status"] = chip.title()
		rs = frappe.get_list("Document Waiver", filters=f, fields=["name", "reference_doctype", "reference_name", "document_type", "status", "due_date", "reason",
			"requested_by", "decided_by"], order_by="creation desc", limit=200)
		return {"cols": _cols(_("Exception"), _("Record"), _("Missing"), _("Promised by"), _("Asked by"), _("Reason"), _("Status")),
			"rows": [{"dt": "Document Waiver", "name": r.name, "cells": [{"code": r.name}, {"main": r.reference_name or "—", "sub": _(r.reference_doctype or "")},
				_(r.document_type or "—"), {"date": r.due_date, "late": bool(r.due_date and getdate(r.due_date) < getdate(today()) and r.status == "Pending")},
				frappe.utils.get_fullname(r.requested_by) if r.requested_by else "—", (r.reason or "—")[:100], _pill(r.status)]}
				for r in rs if _match(q, r.name, r.reference_name, r.document_type, r.reason)], "empty": _("No exceptions.")}
	if tab == "rules":
		dt = "Hipersign Document Rule"
		fl = _fields(dt, ["name", "reference_doctype", "document_type", "level", "enabled", "condition", "description"])
		rs = frappe.get_list(dt, fields=fl, order_by="name asc", limit=300)
		return {"cols": _cols(_("Rule"), _("Record type"), _("Document"), _("Level"), _("Status")),
			"rows": [{"dt": dt, "name": r.name, "cells": [{"code": r.name}, _(r.get("reference_doctype") or "—"), _(r.get("document_type") or "—"),
				{"pill": _(r.get("level") or "—"), "tone": "red" if (r.get("level") or "").startswith("Block") else "orange"},
				{"pill": _("On") if r.get("enabled", 1) else _("Off"), "tone": "green" if r.get("enabled", 1) else "grey"}]}
				for r in rs if _match(q, r.name, r.get("reference_doctype"), r.get("document_type"))], "empty": _("No document rules.")}
	rs = _missing()
	if chip == "blocking":
		rs = [r for r in rs if _blocks(r)]
	elif chip == "required":
		rs = [r for r in rs if not _blocks(r)]
	elif chip == "exception":
		rs = [r for r in rs if r.get("waiver")]
	return {"cols": _cols(_("Record"), _("Party"), _("Date"), {"label": _("Amount"), "cls": "num"}, _("Missing"), _("Rule"), _("Exception")),
		"rows": [{"dt": r.reference_doctype, "name": r.reference_name, "cells": [{"main": r.reference_name, "sub": _(r.reference_doctype)}, r.get("party") or "—",
			{"date": r.get("date")}, {"money": r.get("amount")} if r.get("amount") else "—", _(r.get("document_type") or "—"),
			{"pill": _(r.get("level") or "—"), "tone": "red" if _blocks(r) else "orange"},
			{"pill": _(r.get("waiver_status") or ""), "tone": PILL.get(r.get("waiver_status") or "", "grey"), "sub": r.get("waiver") or ""} if r.get("waiver") else "—"]}
			for r in rs[:300] if _match(q, r.reference_name, r.get("party"), r.get("document_type"))], "empty": _("Nothing missing — every record has its documents.")}
