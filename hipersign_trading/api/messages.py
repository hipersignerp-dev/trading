"""v1.5 — Messages: the conversations kept on orders, shipments, invoices and leads, in one inbox.

A conversation is a record: its comments (with @mentions), the emails sent and received on it, and the WhatsApp sends
logged by Hipersign. Writing here adds a comment to the record — mentions notify the person, as on the form.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime, strip_html_tags

from hipersign_trading.utils import can_read

RECORD_TYPES = ["Sales Order", "Quotation", "Purchase Order", "Import Shipment", "Sales Invoice", "Delivery Note", "Export Shipment",
	"Lead", "Customer", "Supplier", "Purchase Invoice", "Payment Entry", "Letter of Credit", "Post Dated Cheque", "Document Waiver"]


def _who(user):
	return frappe.get_cached_value("User", user, "full_name") or user


@frappe.whitelist()
def conversations(box="all", doctype=None, days=60):
	since = add_days(now_datetime(), -cint(days or 60))
	me = frappe.session.user
	rows = {}

	def add(dt, dn, when, who, text, kind):
		if not dt or not dn or (doctype and dt != doctype):
			return
		k = (dt, dn)
		r = rows.setdefault(k, {"doctype": dt, "name": dn, "last": None, "count": 0, "people": set(), "kinds": set(), "mention": 0})
		r["count"] += 1
		r["people"].add(_who(who))
		r["kinds"].add(kind)
		if not r["last"] or str(when) > str(r["last"]["when"]):
			r["last"] = {"when": str(when), "who": _who(who), "text": strip_html_tags(text or "")[:160], "kind": kind}

	for c in frappe.get_all("Comment", filters={"comment_type": ["in", ["Comment", "Info"]], "creation": [">=", since], "reference_doctype": ["in", RECORD_TYPES]},
			fields=["reference_doctype", "reference_name", "creation", "owner", "content", "comment_type"], order_by="creation desc", limit=600):
		if c.comment_type == "Info" and "whatsapp" not in (c.content or "").lower():
			continue
		add(c.reference_doctype, c.reference_name, c.creation, c.owner, c.content, "whatsapp" if c.comment_type == "Info" else "note")
	for m in frappe.get_all("Communication", filters={"communication_type": "Communication", "creation": [">=", since], "reference_doctype": ["in", RECORD_TYPES]},
			fields=["reference_doctype", "reference_name", "creation", "sender", "owner", "subject", "content", "sent_or_received", "delivery_status"], order_by="creation desc", limit=400):
		add(m.reference_doctype, m.reference_name, m.creation, m.owner if m.sent_or_received == "Sent" else (m.sender or m.owner),
			(m.subject or "") + " — " + (m.content or ""), "email")
	for n in frappe.get_all("Notification Log", filters={"for_user": me, "type": "Mention", "read": 0}, fields=["document_type", "document_name"]):
		if (n.document_type, n.document_name) in rows:
			rows[(n.document_type, n.document_name)]["mention"] = 1
	out = []
	for r in rows.values():
		if not can_read(r["doctype"], r["name"]):
			continue
		r["people"] = sorted(r["people"])
		r["kinds"] = sorted(r["kinds"])
		r["title"] = frappe.get_value(r["doctype"], r["name"], frappe.get_meta(r["doctype"]).title_field or "name") or r["name"]
		out.append(r)
	if box == "mentions":
		out = [r for r in out if r["mention"]]
	elif box == "mine":
		out = [r for r in out if _who(me) in r["people"]]
	elif box == "email":
		out = [r for r in out if "email" in r["kinds"]]
	elif box == "whatsapp":
		out = [r for r in out if "whatsapp" in r["kinds"]]
	out.sort(key=lambda r: r["last"]["when"], reverse=True)
	return {"conversations": out[:80], "types": RECORD_TYPES}


@frappe.whitelist()
def thread(doctype, name):
	frappe.get_doc(doctype, name).check_permission("read")
	items = []
	for c in frappe.get_all("Comment", filters={"reference_doctype": doctype, "reference_name": name, "comment_type": ["in", ["Comment", "Info", "Workflow"]]},
			fields=["owner", "creation", "content", "comment_type"], order_by="creation asc"):
		items.append({"who": _who(c.owner), "user": c.owner, "when": str(c.creation), "html": frappe.utils.sanitize_html(c.content or ""),
			"kind": {"Comment": "note", "Info": "system", "Workflow": "system"}[c.comment_type]})
	for m in frappe.get_all("Communication", filters={"reference_doctype": doctype, "reference_name": name, "communication_type": "Communication"},
			fields=["owner", "sender", "creation", "subject", "content", "sent_or_received", "recipients", "delivery_status"], order_by="creation asc"):
		items.append({"who": _who(m.owner) if m.sent_or_received == "Sent" else (m.sender or ""), "user": m.owner, "when": str(m.creation),
			"html": f"<b>{frappe.utils.escape_html(m.subject or '')}</b><br>" + frappe.utils.sanitize_html(m.content or ""), "kind": "email",
			"meta": (_("to {0}").format(m.recipients) if m.sent_or_received == "Sent" else _("received")) + (f" · {_(m.delivery_status)}" if m.delivery_status else "")})
	items.sort(key=lambda i: i["when"])
	for n in frappe.get_all("Notification Log", filters={"for_user": frappe.session.user, "document_type": doctype, "document_name": name, "read": 0}, pluck="name"):
		frappe.db.set_value("Notification Log", n, "read", 1, update_modified=False)
	title = frappe.get_value(doctype, name, frappe.get_meta(doctype).title_field or "name") or name
	return {"doctype": doctype, "name": name, "title": title, "items": items}


@frappe.whitelist()
def post(doctype, name, text):
	if not (text or "").strip():
		frappe.throw(_("Write a message first"))
	frappe.get_doc(doctype, name).check_permission("read")
	from frappe.desk.form.utils import add_comment

	add_comment(doctype, name, frappe.utils.escape_html(text).replace("\n", "<br>") if "<" not in text else text,
		frappe.session.user, frappe.get_cached_value("User", frappe.session.user, "full_name") or frappe.session.user)
	return thread(doctype, name)
