"""The prototype's top bar (v1.5.4; v1.5.6 adds scope and period, search, the grouped bell and Switch user).

Scope: the whole group, one country or one company. The user's Company default always names a company that keeps its
own books, so new documents and ERPNext reports follow the top bar; the wider scope (group or country) is kept in the
user default "hs_scope" and read by the Hipersign pages. Period: this month, last month or year to date.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, today

from hipersign_trading.utils import user_company

PERIODS = ("month", "last_month", "ytd")


# ---------------------------------------------------------------- scope and period
def _companies():
	rows = frappe.get_list("Company", fields=["name", "country", "default_currency", "is_group"], order_by="lft asc", limit_page_length=100)
	return [r for r in rows if not r.is_group]


def get_scope(user=None):
	scope = frappe.defaults.get_user_default("hs_scope", user=user) or ""
	company = user_company(user)
	if scope == "group" or scope.startswith("country:"):
		return scope, company
	return "company:" + (company or ""), company


def scope_companies(scope=None):
	"""The companies a scope covers, limited to those the user may read."""
	scope = scope or get_scope()[0]
	cos = _companies()
	if scope == "group":
		return [c.name for c in cos]
	if scope.startswith("country:"):
		country = scope.split(":", 1)[1]
		return [c.name for c in cos if c.country == country]
	name = scope.split(":", 1)[1] if ":" in scope else scope
	return [name] if any(c.name == name for c in cos) else [c.name for c in cos][:1]


def get_period(user=None):
	p = frappe.defaults.get_user_default("hs_period", user=user)
	return p if p in PERIODS else "month"


@frappe.whitelist()
def topbar():
	user = frappe.session.user
	cos = _companies()
	countries = []
	for c in cos:
		if c.country and c.country not in countries:
			countries.append(c.country)
	scope, company = get_scope()
	return {
		"unread": frappe.db.count("Notification Log", {"for_user": user, "read": 0}),
		"companies": [c.name for c in cos],
		"company_rows": [{"name": c.name, "country": c.country, "currency": c.default_currency} for c in cos],
		"countries": countries,
		"company": company,
		"scope": scope,
		"period": get_period(),
		"language": frappe.db.get_value("User", user, "language") or frappe.local.lang,
		"switch": switch_info(),
	}


@frappe.whitelist(methods=["POST"])
def set_company(company):
	return set_scope("company:" + (company or ""))["company"]


@frappe.whitelist(methods=["POST"])
def set_scope(scope):
	"""Group, a country or a company. A company scope also becomes the user's Company default (one row only:
	the database compares keys without case, so a stray "company" row used to make reports follow another company)."""
	cos = _companies()
	if scope == "group":
		if len(cos) < 2:
			frappe.throw(_("There is only one company."))
	elif scope.startswith("country:"):
		if not any(c.country == scope.split(":", 1)[1] for c in cos):
			frappe.throw(_("No company in {0}").format(scope.split(":", 1)[1]))
	elif scope.startswith("company:"):
		company = scope.split(":", 1)[1]
		if not company or not frappe.db.exists("Company", company):
			frappe.throw(_("Company {0} not found").format(company))
		frappe.get_doc("Company", company).check_permission("read")
		frappe.defaults.clear_user_default("Company")
		frappe.defaults.set_user_default("Company", company)
	else:
		frappe.throw(_("Unknown scope {0}").format(scope))
	if scope.startswith("country:"):
		# documents need a company: the first one in that country, unless the current one is already there
		current = user_company()
		in_country = scope_companies(scope)
		if current not in in_country and in_country:
			frappe.defaults.clear_user_default("Company")
			frappe.defaults.set_user_default("Company", in_country[0])
	frappe.defaults.set_user_default("hs_scope", scope)
	return {"scope": scope, "company": user_company()}


@frappe.whitelist(methods=["POST"])
def set_period(period):
	if period not in PERIODS:
		frappe.throw(_("Unknown period {0}").format(period))
	frappe.defaults.set_user_default("hs_period", period)
	return period


@frappe.whitelist(methods=["POST"])
def set_language(language):
	if language not in ("en", "ar"):
		frappe.throw(_("Language must be English or Arabic"))
	frappe.db.set_value("User", frappe.session.user, "language", language)
	frappe.clear_cache(user=frappe.session.user)
	return language


# ---------------------------------------------------------------- search
# (doctype, label, fields searched besides the name, title field, extra text field)
SEARCH = [
	("Customer", "Customer", ["customer_name", "tax_id"], "customer_name", "territory"),
	("Supplier", "Supplier", ["supplier_name", "tax_id"], "supplier_name", "country"),
	("Item", "Item", ["item_name", "description"], "item_name", "item_group"),
	("Lead", "Lead", ["company_name", "lead_name", "mobile_no", "email_id"], "company_name", "lead_name"),
	("Quotation", "Quotation", ["customer_name", "party_name"], "customer_name", "status"),
	("Sales Order", "Sales order", ["customer_name", "po_no"], "customer_name", "status"),
	("Purchase Order", "Purchase order", ["supplier_name"], "supplier_name", "status"),
	("Import Shipment", "Import shipment", ["supplier", "bl_no", "container_no"], "supplier", "status"),
	("Export Shipment", "Export shipment", ["customer"], "customer", "status"),
	("Delivery Note", "Delivery note", ["customer_name", "po_no"], "customer_name", "status"),
	("Sales Invoice", "Invoice", ["customer_name", "po_no"], "customer_name", "status"),
	("Purchase Invoice", "Supplier bill", ["supplier_name", "bill_no"], "supplier_name", "status"),
	("Payment Entry", "Payment", ["party_name", "reference_no"], "party_name", "payment_type"),
	("Post Dated Cheque", "Cheque", ["party", "cheque_no"], "party", "status"),
	("Employee", "Employee", ["employee_name"], "employee_name", "designation"),
	("Asset", "Asset", ["asset_name"], "asset_name", "asset_category"),
	("Serial No", "Serial number", [], "item_name", "status"),
]


@frappe.whitelist()
def search(q, limit=12):
	"""Records by number and name, the prototype's way: type label + number — name. Only what the user may read."""
	from hipersign_trading.utils import can_read

	q = (q or "").strip()
	limit = min(cint(limit) or 12, 30)
	if len(q) < 2:
		return []
	out = []
	like = f"%{q}%"
	for dt, label, fields, title, extra in SEARCH:
		if len(out) >= limit or not frappe.db.exists("DocType", dt) or not can_read(dt):
			continue
		meta = frappe.get_meta(dt)
		fields = [f for f in fields if meta.has_field(f)]
		want = ["name"] + [f for f in (title, extra) if f and meta.has_field(f)]
		or_filters = [[dt, "name", "like", like]] + [[dt, f, "like", like] for f in fields]
		filters = {"docstatus": ["<", 2]} if meta.is_submittable else {}
		if meta.has_field("disabled"):
			filters["disabled"] = 0
		try:
			rows = frappe.get_list(dt, filters=filters, or_filters=or_filters, fields=list(dict.fromkeys(want)),
				order_by="modified desc", limit_page_length=3)
		except Exception:
			continue
		for r in rows:
			name_txt = r.get(title) if title and r.get(title) and r.get(title) != r.name else ""
			out.append({"doctype": dt, "type": _(label), "name": r.name, "title": name_txt or "", "extra": str(r.get(extra) or "") if extra else ""})
	return out[:limit]


# ---------------------------------------------------------------- the grouped bell
@frappe.whitelist()
def bell():
	"""The prototype's notification panel: mentions, emails, WhatsApp, email review, approvals, lead follow-ups, high alerts."""
	user = frappe.session.user
	groups = []

	def group(key, label, items, route):
		if items:
			groups.append({"key": key, "label": label, "items": items[:3], "count": len(items), "unread": sum(1 for i in items if i.get("unread")), "route": route})

	logs = frappe.get_all("Notification Log", filters={"for_user": user}, fields=["name", "subject", "type", "document_type", "document_name", "read", "creation", "email_content"],
		order_by="creation desc", limit_page_length=60)
	logs = [l for l in logs if "demo data loaded" not in (l.subject or "").lower()]
	mention = [l for l in logs if l.type == "Mention"]

	def item(l):
		return {"title": frappe.utils.strip_html(l.subject or "")[:120], "text": frappe.utils.strip_html(l.email_content or "")[:90],
			"doctype": l.document_type, "name": l.document_name, "unread": not l.read, "log": l.name}

	group("mentions", _("Mentions"), [item(l) for l in mention], ["hipersign-messages"])
	if frappe.db.exists("DocType", "Communication"):
		comms = frappe.get_all("Communication", filters={"sent_or_received": "Received", "communication_type": "Communication", "seen": 0,
			"creation": [">=", add_days(today(), -30)]}, fields=["name", "subject", "sender", "reference_doctype", "reference_name", "communication_medium"],
			order_by="creation desc", limit_page_length=20)
		emails = [c for c in comms if (c.communication_medium or "Email") == "Email" and c.reference_doctype]
		review = [c for c in comms if (c.communication_medium or "Email") == "Email" and not c.reference_doctype]
		group("emails", _("Emails"), [{"title": _("New email from {0}").format(c.sender), "text": c.subject or "", "doctype": c.reference_doctype,
			"name": c.reference_name, "unread": True} for c in emails], ["hipersign-messages"])
		if "System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles():
			group("review", _("Email review"), [{"title": _("Incoming message needs review"), "text": c.subject or c.sender, "doctype": "Communication",
				"name": c.name, "unread": True} for c in review], ["List", "Communication"])
	if frappe.db.exists("DocType", "WhatsApp Message"):
		try:
			wa = frappe.get_all("WhatsApp Message", filters={"type": "Incoming", "creation": [">=", add_days(today(), -7)]},
				fields=["name", "message", "from", "reference_doctype", "reference_name"], order_by="creation desc", limit_page_length=10)
			group("whatsapp", _("WhatsApp"), [{"title": _("WhatsApp from {0}").format(w.get("from")), "text": (w.message or "")[:90],
				"doctype": w.reference_doctype or "WhatsApp Message", "name": w.reference_name or w.name, "unread": True} for w in wa], ["hipersign-messages"])
		except Exception:
			pass
	try:
		from hipersign_trading.api.approvals import pending

		appr = pending(user_company(), mine=True)
		group("approvals", _("Approvals"), [{"title": _("{0} {1} awaits you").format(a.get("type") or _(a.get("doctype")), a.get("name")), "text": a.get("reason") or a.get("description") or "",
			"doctype": a.get("doctype"), "name": a.get("name"), "unread": True} for a in appr], ["hipersign-approvals"])
	except Exception:
		frappe.clear_last_message()
	if frappe.get_meta("Lead").has_field("hs_next_follow_up"):
		filters = {"hs_next_follow_up": ["<=", today()], "hs_pipeline_stage": ["not in", ["Won", "Lost"]]}
		roles = set(frappe.get_roles())
		if not roles & {"Sales Manager", "System Manager", "Managing Director"}:
			filters["lead_owner"] = user
		leads = frappe.get_list("Lead", filters=filters, fields=["name", "company_name", "lead_name", "hs_next_follow_up", "hs_next_action"],
			order_by="hs_next_follow_up asc", limit_page_length=20) if frappe.has_permission("Lead") else []
		group("leads", _("Lead follow-ups"), [{"title": _("Follow up {0}").format(l.company_name or l.lead_name),
			"text": "{0} · {1}".format(l.hs_next_action or _("Follow-up"), frappe.format(l.hs_next_follow_up, "Date")), "doctype": "Lead", "name": l.name,
			"unread": True} for l in leads], ["List", "Lead"])
	try:
		from hipersign_trading.alerts import can_see, evaluate

		high = [a for a in evaluate(user_company()) if a["status"] == "Open" and a["severity"] == "High" and can_see(a)]
		group("alerts", _("High alerts"), [{"title": a["title"], "text": _(a["category"]), "doctype": a.get("doctype"), "name": a.get("name"),
			"unread": True} for a in high], ["hipersign-alerts"])
	except Exception:
		frappe.clear_last_message()
	others = [item(l) for l in logs if l.type != "Mention"][:10]
	group("other", _("Other notifications"), others, ["List", "Notification Log"])
	return {"groups": groups, "unread": frappe.db.count("Notification Log", {"for_user": user, "read": 0})}


@frappe.whitelist(methods=["POST"])
def mark_all_read():
	frappe.db.set_value("Notification Log", {"for_user": frappe.session.user, "read": 0}, "read", 1, update_modified=False)
	return 0


# ---------------------------------------------------------------- Switch user (demo sites)
DEMO_DOMAIN = "demo.hipersignerp.com"
VIEWER_ROLE = "Demo Viewer"


def is_demo_site():
	return bool(frappe.conf.get("hipersign_demo_site"))


def original_user():
	return frappe.session.data.get("impersonated_by") or frappe.session.user


def demo_users():
	domain = (frappe.db.get_single_value("Hipersign Settings", "demo_user_domain") if frappe.get_meta("Hipersign Settings").has_field("demo_user_domain") else None) or DEMO_DOMAIN
	rows = frappe.get_all("User", filters={"enabled": 1, "name": ["like", f"%@{domain}"]}, fields=["name", "full_name", "user_type"], order_by="full_name asc")
	viewers = set(frappe.get_all("Has Role", filters={"role": VIEWER_ROLE, "parenttype": "User"}, pluck="parent"))
	rows = [r for r in rows if r.name not in viewers]
	return [{"user": r.name, "full_name": r.full_name, "role": role_label(r.name), "portal": r.user_type == "Website User"} for r in rows]


# the prototype's role names, most senior first (the top bar shows the first one the user has)
ROLE_LABELS = [
	("Managing Director", "Managing Director"), ("Accounts Manager", "Finance Manager"), ("Sales Manager", "Sales Manager"),
	("Purchase Manager", "Purchase Manager"), ("Stock Manager", "Warehouse Manager"), ("HR Manager", "HR Manager"),
	("Logistics Coordinator", "Logistics"), ("Accounts User", "Accountant"), ("Sales User", "Sales Executive"),
	("Purchase User", "Buyer"), ("Stock User", "Storekeeper"), ("Driver", "Driver"), ("Customer", "Customer (portal)"),
	(VIEWER_ROLE, "View-only demo"), ("System Manager", "Administrator"),
]


def role_label(user):
	roles = set(frappe.get_roles(user))
	for role, label in ROLE_LABELS:
		if role in roles:
			return _(label)
	return ""


def can_switch(orig=None):
	orig = orig or original_user()
	if not is_demo_site():
		return False
	roles = set(frappe.get_roles(orig))
	return orig == "Administrator" or bool(roles & {"System Manager", VIEWER_ROLE})


def switch_info():
	if not can_switch():
		return None
	orig = original_user()
	return {"users": demo_users(), "original": orig, "current": frappe.session.user, "switched": orig != frappe.session.user}


@frappe.whitelist(methods=["POST"])
def switch_user(user):
	"""Open the desk as a demo user (demo sites only). Logged like Frappe's impersonation, but without notifying
	or emailing the demo user each time, and "Back to …" returns to the original login."""
	orig = original_user()
	if not can_switch(orig):
		frappe.throw(_("Switching user is available on demo sites only."), frappe.PermissionError)
	allowed = {u["user"] for u in demo_users()} | {orig}
	if user not in allowed:
		frappe.throw(_("{0} is not a demo user.").format(user), frappe.PermissionError)
	frappe.get_doc({"doctype": "Activity Log", "user": user, "status": "Success", "operation": "Impersonate",
		"subject": _("{0} switched to {1} (demo)").format(orig, user)}).insert(ignore_permissions=True, ignore_links=True)
	data = frappe.local.session_obj.data.data
	frappe.local.login_manager.login_as(user, session_end=data.get("session_end"), audit_user=data.get("audit_user"))
	if user != orig:
		frappe.local.session_obj.set_impersonated(orig)
	return {"user": user, "home": "/app/hipersign-home"}
