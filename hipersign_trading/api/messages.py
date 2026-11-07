"""v1.5 — Messages: the conversations kept on orders, shipments, invoices and leads, in one inbox.

A conversation is a record: its comments (with @mentions), the emails sent and received on it, and the WhatsApp sends
logged by Hipersign. Writing here adds a comment to the record — mentions notify the person, as on the form.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime, strip_html_tags

from hipersign_trading.utils import can_read

RECORD_TYPES = ["Sales Order", "Quotation", "Purchase Order", "Import Shipment", "Sales Invoice", "Delivery Note", "Export Shipment",
	"Lead", "Customer", "Supplier", "Purchase Invoice", "Payment Entry", "Letter of Credit", "Post Dated Cheque", "Document Waiver",
	"Hipersign Conversation"]  # v1.8.4 (#32): messages that are not on a record
CONV = "Hipersign Conversation"


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
	return {"conversations": out[:80], "types": [t for t in RECORD_TYPES if t != CONV]}


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
	out = {"doctype": doctype, "name": name, "title": title, "items": items}
	if doctype == CONV:  # v1.8.4 (#32): who is in it, and the record it is about (if any)
		c = frappe.get_doc(CONV, name)
		from hipersign_trading.hipersign_trading.doctype.hipersign_conversation.hipersign_conversation import people

		out["people"] = [_who(u) for u in sorted(people(c))]
		if c.linked_doctype and c.linked_name:
			out["linked"] = [c.linked_doctype, c.linked_name]
	return out


@frappe.whitelist()
def post(doctype, name, text):
	if not (text or "").strip():
		frappe.throw(_("Write a message first"))
	frappe.get_doc(doctype, name).check_permission("read")
	from frappe.desk.form.utils import add_comment

	add_comment(doctype, name, frappe.utils.escape_html(text).replace("\n", "<br>") if "<" not in text else text,
		frappe.session.user, frappe.get_cached_value("User", frappe.session.user, "full_name") or frappe.session.user)
	if doctype == CONV and not frappe.flags.hs_msg_start:  # v1.8.4: a reply in a conversation reaches the others in it
		from hipersign_trading.hipersign_trading.doctype.hipersign_conversation.hipersign_conversation import people

		_notify(sorted(people(frappe.get_doc(CONV, name))), CONV, name, text)
	return thread(doctype, name)


# ---------------------------------------------------------------- v1.8.4 (#32, #33): New message — people first, a record optional
SEARCH = [  # (doctype, icon, friendly name, extra fields to search)
	("Sales Order", "sell", "Sales order", ["customer_name"]),
	("Quotation", "file-text", "Quotation", ["customer_name"]),
	("Sales Invoice", "receipt", "Invoice", ["customer_name"]),
	("Delivery Note", "truck", "Delivery", ["customer_name"]),
	("Purchase Order", "shopping-cart", "Purchase order", ["supplier_name"]),
	("Purchase Invoice", "receipt", "Supplier bill", ["supplier_name"]),
	("Import Shipment", "ship", "Import shipment", []),
	("Export Shipment", "ship", "Export shipment", []),
	("Payment Entry", "credit-card", "Payment", ["party_name"]),
	("Lead", "user-plus", "Lead", ["lead_name", "company_name"]),
	("Customer", "users", "Customer", ["customer_name"]),
	("Supplier", "building", "Supplier", ["supplier_name"]),
	("Item", "package", "Item", ["item_name"]),
	("Project", "folder", "Project", ["project_name"]),
	("Letter of Credit", "landmark", "Letter of credit", []),
]


@frappe.whitelist()
def search_records(txt=""):
	"""One search box across the main records: by number or name, only what the user may read."""
	txt = (txt or "").strip()
	out = []
	for dt, icon, label, extra in SEARCH:
		if not frappe.db.exists("DocType", dt) or not frappe.has_permission(dt, "read"):
			continue
		meta = frappe.get_meta(dt)
		tf = meta.title_field if meta.title_field and meta.has_field(meta.title_field) else None
		fields = ["name"] + ([tf] if tf else []) + [f for f in extra if meta.has_field(f) and f != tf]
		ors = [[dt, f, "like", f"%{txt}%"] for f in fields] if txt else None
		try:
			rows = frappe.get_list(dt, fields=list(dict.fromkeys(fields)), or_filters=ors, order_by="modified desc", limit_page_length=4 if txt else 2)
		except Exception:
			continue
		for r in rows:
			sub = next((r.get(f) for f in fields[1:] if r.get(f) and r.get(f) != r.name), "")
			out.append({"doctype": dt, "name": r.name, "label": _(label), "icon": icon, "title": r.get(tf) or r.name, "sub": sub or ""})
		if len(out) >= 24:
			break
	return out


@frappe.whitelist()
def search_people(txt=""):
	"""Colleagues who can log in to the desk."""
	txt = (txt or "").strip()
	f = {"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest", frappe.session.user]]}
	ors = [["full_name", "like", f"%{txt}%"], ["name", "like", f"%{txt}%"]] if txt else None
	rows = frappe.get_all("User", filters=f, or_filters=ors, fields=["name", "full_name", "user_image"], order_by="full_name asc", limit=12)
	return [{"user": r.name, "name": r.full_name or r.name, "image": r.user_image} for r in rows]


def _notify(users, doctype, name, text):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	users = [u for u in users if u and u != frappe.session.user and frappe.db.get_value("User", u, "enabled")]
	if not users:
		return
	who = frappe.get_cached_value("User", frappe.session.user, "full_name") or frappe.session.user
	enqueue_create_notification(users, frappe._dict(type="Mention", document_type=doctype, document_name=name, from_user=frappe.session.user,
		subject=_("{0} sent you a message").format(frappe.bold(who)), email_content=strip_html_tags(text or "")[:500]))


@frappe.whitelist()
def start(text, people=None, doctype=None, name=None, title=None):
	"""New message: to people, on a record, or both. With a record it is a comment on that record (as before) and the
	people picked are notified; without one it starts a private conversation between the people picked."""
	import json

	if not strip_html_tags(text or "").strip():
		frappe.throw(_("Write a message first"))
	people = json.loads(people) if isinstance(people, str) and people.startswith("[") else (people or [])
	people = [p for p in people if p and frappe.db.exists("User", p)]
	if doctype and name:
		out = post(doctype, name, text)
		_notify(people, doctype, name, text)
		return out
	if not people:
		frappe.throw(_("Pick at least one person, or a record to write on"))
	names = [frappe.get_cached_value("User", u, "full_name") or u for u in [frappe.session.user] + people]
	c = frappe.get_doc({"doctype": CONV, "title": (title or "").strip() or ", ".join(names[:4]) + (" +{0}".format(len(names) - 4) if len(names) > 4 else ""),
		"participants": "\n".join(sorted(set(people + [frappe.session.user])))}).insert(ignore_permissions=True)
	frappe.flags.hs_msg_start = True
	out = post(CONV, c.name, text)
	frappe.flags.hs_msg_start = False
	_notify(people, CONV, c.name, text)
	return out
