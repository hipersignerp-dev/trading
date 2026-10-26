"""Documents box on the forms: what the record needs, attaching with a type, asking for an exception."""

import frappe
from frappe import _
from frappe.utils import add_days, today

from hipersign_trading.doc_rules import checklist, default_approver, rules_for


@frappe.whitelist()
def doc_info(doctype, name):
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	files = frappe.get_all("File", filters={"attached_to_doctype": doctype, "attached_to_name": name},
		fields=["name", "file_name", "file_url", "hs_document_type", "creation", "owner"], order_by="creation desc")
	from hipersign_trading.features import doc_level

	return {"rules": checklist(doc), "files": files, "level": doc_level()}


@frappe.whitelist()
def set_file_type(file, document_type):
	f = frappe.get_doc("File", file)
	if f.attached_to_doctype:
		frappe.get_doc(f.attached_to_doctype, f.attached_to_name).check_permission("write")
	f.hs_document_type = document_type or None
	f.save(ignore_permissions=True)
	return f.name


@frappe.whitelist()
def request_waiver(doctype, name, document_type, reason, due_date=None):
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	rule = next((r for r in rules_for(doctype) if r.document_type == document_type), None)
	open_ = frappe.db.get_value("Document Waiver", {"reference_doctype": doctype, "reference_name": name, "document_type": document_type,
		"status": ["in", ["Pending", "Approved"]]})
	if open_:
		return open_
	from hipersign_trading.utils import settings

	w = frappe.get_doc({"doctype": "Document Waiver", "reference_doctype": doctype, "reference_name": name, "document_type": document_type,
		"rule": rule.name if rule else None, "approver_role": (rule.approver_role if rule else None) or default_approver(doctype),
		"reason": reason, "due_date": due_date or add_days(today(), settings().get("waiver_days") or 7)})
	w.insert(ignore_permissions=True)
	if w.approver_role in frappe.get_roles():
		w.approve(_("Approved by the requester, who holds the approving role"))
	else:
		from hipersign_trading.doc_rules import notify

		for u in [x.parent for x in frappe.get_all("Has Role", filters={"role": w.approver_role, "parenttype": "User"}, fields=["parent"])]:
			if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled"):
				notify(w, _("Exception requested: {0} for {1} {2}").format(document_type, doctype, name), u)
	return w.name


@frappe.whitelist()
def ruled_doctypes(doctype, txt, searchfield, start, page_len, filters):
	dts = sorted({r.reference_doctype for r in frappe.get_all("Hipersign Document Rule", fields=["reference_doctype"])})
	return [[d] for d in dts if txt.lower() in d.lower()][int(start): int(start) + int(page_len)]


@frappe.whitelist()
def document_types():
	return frappe.get_all("Hipersign Document Type", pluck="name", order_by="name asc")
