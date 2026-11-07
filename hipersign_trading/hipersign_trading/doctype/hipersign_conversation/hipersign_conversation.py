import frappe
from frappe.model.document import Document


class HipersignConversation(Document):
	pass


def people(doc):
	return {p.strip() for p in (doc.get("participants") or "").replace(",", "\n").split("\n") if p.strip()} | {doc.owner}


def has_permission(doc, ptype=None, user=None, debug=False):
	"""v1.8.4: a conversation is private to its people (not even a System Manager reads someone else's)."""
	user = user or frappe.session.user
	if user == "Administrator" and ptype == "delete":
		return True
	if doc.is_new():
		return True
	return user in people(doc)


def query_conditions(user=None):
	user = user or frappe.session.user
	u = frappe.db.escape(user)
	like = frappe.db.escape(f"%\n{user}\n%")
	return (f"(`tabHipersign Conversation`.owner = {u} or "
		f"concat('\n', replace(ifnull(`tabHipersign Conversation`.participants, ''), ',', '\n'), '\n') like {like})")
