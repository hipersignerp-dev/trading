"""External documents on records (Phase 2) and exceptions to the blocking rules.

Hipersign Document Rule says which document a record needs (customer LPO on a sales order above
AED 50,000, the supplier's invoice on a purchase invoice, the bank's LC copy when an LC is issued…).
Files are attached on the form with a document type (File.hs_document_type).

  Block     the next step (submit, or the status change) stops until the file is attached,
            or an exception (Document Waiver) is approved by the role on the rule
  Required  shown as missing on the form and in the Missing Documents report, nothing stops
  Optional  offered in the documents box
  Off       ignored

The Documents level in Hipersign Settings softens every rule: Off → all optional,
Recommended → Block counts as Required, Full → as set.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, today

from hipersign_trading.features import doc_level


class DocumentNeeded(frappe.ValidationError):
	pass


DEFAULT_APPROVER = {
	"Sales Order": "Sales Manager", "Delivery Note": "Stock Manager", "Sales Invoice": "Sales Manager", "Quotation": "Sales Manager",
	"Purchase Order": "Purchase Manager", "Purchase Receipt": "Stock Manager", "Purchase Invoice": "Accounts Manager",
	"Payment Entry": "Accounts Manager", "Journal Entry": "Accounts Manager", "Letter of Credit": "Accounts Manager",
	"Import Shipment": "Purchase Manager", "Export Shipment": "Sales Manager", "Company Document": "Managing Director",
}

# default rules installed with the app: (doctype, document, level, min amount, event, when field, when value, only returns, why)
DEFAULT_RULES = [
	("Sales Order", "Customer LPO", "Block", 50000, "On submit", None, None, 0, "Orders from AED 50,000 need the customer's purchase order"),
	("Sales Order", "Customer KYC documents", "Optional", 0, "On submit", None, None, 0, "Exceptions to the KYC block are asked for against this document"),
	("Sales Order", "Advance payment", "Optional", 0, "On submit", None, None, 0, "Exceptions to the advance-before-delivery hold are asked for against this document"),
	("Quotation", "Customer RFQ / BOQ", "Optional", 0, "On submit", None, None, 0, ""),
	("Delivery Note", "Signed delivery note", "Required", 0, "When status changes to", "hs_delivery_status", "Delivered", 0, "Proof of delivery"),
	("Sales Invoice", "Return request", "Required", 0, "On submit", None, None, 1, "Credit notes need the customer's return request"),
	("Purchase Order", "Supplier order confirmation", "Required", 0, "On submit", None, None, 0, "The supplier's confirmation of price and date"),
	("Purchase Order", "Proforma invoice", "Optional", 0, "On submit", None, None, 0, ""),
	("Purchase Receipt", "Supplier delivery note", "Required", 0, "On submit", None, None, 0, ""),
	("Purchase Receipt", "Damage photos", "Optional", 0, "On submit", None, None, 0, ""),
	("Purchase Invoice", "Supplier invoice", "Block", 0, "On submit", None, None, 0, "The supplier's tax invoice must be on file before the bill is booked"),
	("Payment Entry", "Bank advice / transfer copy", "Optional", 0, "On submit", None, None, 0, ""),
	("Journal Entry", "Supporting document", "Block", 10000, "On submit", None, None, 0, "Manual entries from AED 10,000 need a supporting document"),
	("Letter of Credit", "Bank's LC copy", "Block", 0, "When status changes to", "status", "Issued", 0, "The bank's issued LC (MT700) before the LC is marked issued"),
	("Import Shipment", "Bill of lading / AWB", "Required", 0, "When status changes to", "status", "Shipped", 0, ""),
	("Import Shipment", "Bill of entry", "Block", 0, "When status changes to", "status", "Cleared", 0, "Customs clearance needs the bill of entry"),
	("Export Shipment", "Exit / export certificate", "Required", 0, "When status changes to", "status", "Shipped", 0, "Proof of export for 0% VAT"),
]
EXTRA_TYPES = ["Advance payment", "Trade licence", "TRN certificate", "Emirates ID", "Insurance certificate", "Certificate of origin", "Packing list", "Commercial invoice"]

LEVEL_ORDER = {"Off": 0, "Optional": 1, "Required": 2, "Block": 3}


def effective(level):
	lv = doc_level()
	if lv == "Off":
		return "Optional" if level != "Off" else "Off"
	if lv == "Recommended" and level == "Block":
		return "Required"
	return level


def default_approver(doctype):
	return DEFAULT_APPROVER.get(doctype, "System Manager")


def rules_for(doctype):
	cache = frappe.cache.get_value("hs_doc_rules")
	if cache is None:
		cache = {}
		if frappe.db.table_exists("Hipersign Document Rule"):
			for r in frappe.get_all("Hipersign Document Rule", filters={"active": 1}, fields=["*"], order_by="creation asc"):
				cache.setdefault(r.reference_doctype, []).append(r)
		frappe.cache.set_value("hs_doc_rules", cache)
	return [frappe._dict(r) for r in cache.get(doctype, [])]


def applies(rule, doc):
	if rule.only_returns and not doc.get("is_return"):
		return False
	if flt(rule.min_amount) and flt(doc.get(rule.amount_field or "base_grand_total")) < flt(rule.min_amount):
		return False
	return True


def attached(doctype, name, document_type):
	return bool(frappe.db.exists("File", {"attached_to_doctype": doctype, "attached_to_name": name, "hs_document_type": document_type}))


def approved_waiver(doctype, name, document_type):
	return frappe.db.get_value("Document Waiver", {"reference_doctype": doctype, "reference_name": name, "document_type": document_type,
		"status": ["in", ["Approved", "Used"]]}, "name")


def checklist(doc):
	"""Every rule that applies to the record now, with what is on file — for the documents box and the report."""
	out = []
	for r in rules_for(doc.doctype):
		lvl = effective(r.level)
		if lvl == "Off" or not applies(r, doc):
			continue
		ok = not doc.is_new() and attached(doc.doctype, doc.name, r.document_type)
		wv = None if ok or doc.is_new() else frappe.db.get_value("Document Waiver", {"reference_doctype": doc.doctype, "reference_name": doc.name,
			"document_type": r.document_type, "status": ["not in", ["Rejected"]]}, ["name", "status", "due_date"], as_dict=True)
		out.append({"rule": r.name, "document_type": r.document_type, "level": lvl, "set_level": r.level, "event": r.event, "when_value": r.when_value,
			"note": r.note, "attached": ok, "waiver": wv, "approver_role": r.approver_role or default_approver(doc.doctype)})
	return out


APP_JOURNAL_LINKS = {
	"Letter of Credit": ("margin_entry", "tr_entry", "margin_release_entry"),
	"Post Dated Cheque": ("receipt_entry", "clearing_entry", "reversal_entry", "charges_entry"),
}


def _app_journal(doc):
	"""A journal entry an LC or a post-dated cheque made (it may be submitted later, from the journal's own form)."""
	if doc.doctype != "Journal Entry" or doc.is_new():
		return False
	for dt, fields in APP_JOURNAL_LINKS.items():
		if not frappe.db.table_exists(dt):
			continue
		for f in fields:
			if frappe.db.exists(dt, {f: doc.name}):
				return True
	return False


def _app_journal_names():
	names = set()
	for dt, fields in APP_JOURNAL_LINKS.items():
		if not frappe.db.table_exists(dt):
			continue
		for row in frappe.get_all(dt, fields=list(fields)):
			names.update(v for v in row.values() if v)
	return names


def _gate(doc, rules):
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch or frappe.flags.hs_skip_doc_rules or frappe.flags.in_import:
		return
	# journals the app posts itself (cheques, LC margins and trust receipts) have their own record as the supporting document
	if doc.flags.get("hs_system_entry") or _app_journal(doc):
		return
	missing = []
	for r in rules:
		if effective(r.level) != "Block" or not applies(r, doc):
			continue
		if attached(doc.doctype, doc.name, r.document_type):
			continue
		wv = approved_waiver(doc.doctype, doc.name, r.document_type)
		if wv:
			if frappe.db.get_value("Document Waiver", wv, "status") == "Approved":
				frappe.db.set_value("Document Waiver", wv, {"status": "Used", "used_on": frappe.utils.now_datetime()})
			continue
		missing.append(r)
	if missing:
		rows = "".join(f"<li><b>{_(r.document_type)}</b>{' — ' + _(r.note) if r.note else ''}</li>" for r in missing)
		frappe.throw(
			_("Attach the document below with its type (Documents on the form), or request an exception from the {0}:").format(
				_(missing[0].approver_role or default_approver(doc.doctype))) + f"<ul>{rows}</ul>",
			title=_("Document needed"), exc=DocumentNeeded)


def before_submit(doc, method=None):
	rules = [r for r in rules_for(doc.doctype) if r.event == "On submit"]
	if rules:
		_gate(doc, rules)


def validate(doc, method=None):
	if doc.is_new():
		return
	rules = [r for r in rules_for(doc.doctype) if r.event == "When status changes to" and r.when_field]
	rules = [r for r in rules if str(doc.get(r.when_field) or "") == str(r.when_value) and doc.has_value_changed(r.when_field)]
	if rules:
		_gate(doc, rules)


def file_after_insert(doc, method=None):
	"""A document that arrives after an exception closes it."""
	if not (doc.get("hs_document_type") and doc.attached_to_doctype and doc.attached_to_name):
		return
	for wv in frappe.get_all("Document Waiver", filters={"reference_doctype": doc.attached_to_doctype, "reference_name": doc.attached_to_name,
		"document_type": doc.hs_document_type, "status": ["in", ["Pending", "Approved", "Used", "Overdue"]]}, pluck="name"):
		frappe.db.set_value("Document Waiver", wv, "status", "Received")


def file_on_update(doc, method=None):
	if doc.has_value_changed("hs_document_type"):
		file_after_insert(doc)


def notify(waiver, subject, user):
	if not user or user in ("Administrator", "Guest"):
		return
	frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "reference_type": "Document Waiver", "reference_name": waiver.name,
		"description": subject, "date": today(), "priority": "Medium"}).insert(ignore_permissions=True)


def waiver_alerts():
	"""Daily: exceptions whose document is still not on file after the date promised."""

	if doc_level() != "Full":
		return
	for w in frappe.get_all("Document Waiver", filters={"status": ["in", ["Approved", "Used"]], "due_date": ["<", today()]}, fields=["name", "requested_by"]):
		frappe.db.set_value("Document Waiver", w.name, "status", "Overdue")
		notify(frappe._dict(name=w.name), _("Document promised under exception {0} is overdue").format(w.name), w.requested_by)


def seed():
	"""Document types and the default rules (existing sites keep their own)."""
	for dt, typ, *_rest in DEFAULT_RULES:
		if not frappe.db.exists("Hipersign Document Type", typ):
			frappe.get_doc({"doctype": "Hipersign Document Type", "document_type_name": typ}).insert(ignore_permissions=True)
	for typ in EXTRA_TYPES:
		if not frappe.db.exists("Hipersign Document Type", typ):
			frappe.get_doc({"doctype": "Hipersign Document Type", "document_type_name": typ}).insert(ignore_permissions=True)
	if frappe.db.count("Hipersign Document Rule"):
		return
	for dt, typ, level, amt, event, wf, wv, ret, why in DEFAULT_RULES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		if wf and not meta.has_field(wf):
			continue
		frappe.get_doc({"doctype": "Hipersign Document Rule", "reference_doctype": dt, "document_type": typ, "level": level, "min_amount": amt,
			"amount_field": "base_grand_total" if meta.has_field("base_grand_total") else ("total_debit" if meta.has_field("total_debit") else "base_amount"),
			"event": event, "when_field": wf, "when_value": wv, "only_returns": ret, "note": why, "active": 1,
			"approver_role": "Accounts Manager" if typ in ("Customer KYC documents", "Advance payment") else default_approver(dt)}).insert(ignore_permissions=True)
	frappe.cache.delete_value("hs_doc_rules")


@frappe.whitelist()
def missing_count():
	return len(missing_rows(limit=500))


def missing_rows(doctype=None, document_type=None, limit=2000):
	"""Records that are missing a Required or Block document (for the report and the workspace)."""
	out = []
	for dt in ({doctype} if doctype else {r.reference_doctype for r in frappe.get_all("Hipersign Document Rule", filters={"active": 1}, fields=["reference_doctype"])}):
		rules = [r for r in rules_for(dt) if effective(r.level) in ("Block", "Required") and (not document_type or r.document_type == document_type)]
		if not rules or not frappe.db.table_exists(dt):
			continue
		meta = frappe.get_meta(dt)
		filters = {"docstatus": ["<", 2]}
		if meta.is_submittable:
			filters["docstatus"] = 1
		fields = ["name"] + [f for f in ("customer", "supplier", "party", "party_name", "customer_name", "supplier_name", "posting_date", "transaction_date",
			"base_grand_total", "is_return", "total_debit", "company", "status", "hs_delivery_status") if meta.has_field(f)]
		since = add_days(today(), -120)
		date_field = "posting_date" if meta.has_field("posting_date") else "transaction_date" if meta.has_field("transaction_date") else "creation"
		filters[date_field] = [">=", since]
		app_journals = _app_journal_names() if dt == "Journal Entry" else set()
		for d in frappe.get_all(dt, filters=filters, fields=fields, limit=limit, order_by="creation desc"):
			if d.name in app_journals:
				continue
			for r in rules:
				if not applies(r, d):
					continue
				if r.event == "When status changes to" and str(d.get(r.when_field) or "") != str(r.when_value):
					continue
				if attached(dt, d.name, r.document_type):
					continue
				wv = frappe.db.get_value("Document Waiver", {"reference_doctype": dt, "reference_name": d.name, "document_type": r.document_type,
					"status": ["not in", ["Rejected", "Received"]]}, ["name", "status", "due_date"], as_dict=True)
				out.append(frappe._dict(reference_doctype=dt, reference_name=d.name, party=d.get("customer_name") or d.get("supplier_name") or d.get("party_name")
					or d.get("customer") or d.get("supplier") or d.get("party") or "", date=d.get(date_field), amount=d.get("base_grand_total") or d.get("total_debit"),
					document_type=r.document_type, level=effective(r.level), note=r.note, waiver=wv.name if wv else None,
					waiver_status=wv.status if wv else None, due=wv.due_date if wv else None, company=d.get("company")))
	return out
