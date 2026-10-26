"""Company compliance (Phase 3): licences and certificates of each company, and statutory deadlines.

Daily: every Company Document gets its status (Valid → Due for renewal → Expired); on the reminder
days (Hipersign Settings, e.g. 60, 30, 7 and 0 days before expiry) the responsible person gets a
ToDo and an email, and the same for Company Deadlines (7, 3 and 0 days before). Each stage is sent
once. A deadline that repeats creates the next one when it is marked done.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, today

from hipersign_trading.features import feature_on
from hipersign_trading.utils import settings

# starting document types by country: (name, country, authority, renew before days, expires)
COMPANY_DOC_TYPES = [
	("Trade licence", "United Arab Emirates", "Department of Economy & Tourism", 60, 1),
	("Chamber of commerce membership", "United Arab Emirates", "Dubai Chamber", 30, 1),
	("VAT registration certificate", "United Arab Emirates", "Federal Tax Authority", 0, 0),
	("Corporate tax registration", "United Arab Emirates", "Federal Tax Authority", 0, 0),
	("Establishment card", "United Arab Emirates", "General Directorate of Residency (GDRFA)", 30, 1),
	("Civil defence certificate", "United Arab Emirates", "Civil Defence", 30, 1),
	("Tenancy contract (Ejari)", "United Arab Emirates", "Dubai Land Department", 60, 1),
	("Customs code", "United Arab Emirates", "Dubai Customs", 30, 1),
	("Commercial registration (CR)", "Saudi Arabia", "Ministry of Commerce", 60, 1),
	("Zakat & VAT certificate", "Saudi Arabia", "ZATCA", 30, 1),
	("GOSI certificate", "Saudi Arabia", "GOSI", 30, 1),
	("Certificate of incorporation", "United Kingdom", "Companies House", 0, 0),
	("Confirmation statement", "United Kingdom", "Companies House", 30, 1),
	("Business registration certificate", "Hong Kong", "Inland Revenue Department", 30, 1),
	("GST registration", "India", "GSTN", 0, 0),
	("Import Export Code (IEC)", "India", "DGFT", 0, 0),
	("Shops & establishment licence", "India", "State labour department", 60, 1),
]


def _days(key, default):
	raw = settings().get(key) or default
	try:
		return sorted({int(x) for x in str(raw).replace(" ", "").split(",") if x != ""}, reverse=True)
	except ValueError:
		return [int(x) for x in default.split(",")]


def _remind(doctype, name, user, subject, message):
	if not user or user in ("Administrator", "Guest"):
		user = _fallback_user()
	if not user:
		return
	if not frappe.db.exists("ToDo", {"reference_type": doctype, "reference_name": name, "status": "Open", "allocated_to": user, "description": subject}):
		frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "reference_type": doctype, "reference_name": name, "description": subject,
			"date": today(), "priority": "High"}).insert(ignore_permissions=True)
	if settings().get("compliance_email"):
		email = frappe.db.get_value("User", user, "email")
		if email and not frappe.flags.mute_emails:
			frappe.sendmail(recipients=[email], subject=subject, message=message, reference_doctype=doctype, reference_name=name, delayed=True)
	frappe.get_doc(doctype, name).add_comment("Info", _("Reminder sent to {0}: {1}").format(user, subject))


def _fallback_user():
	for role in ("Managing Director", "Accounts Manager", "System Manager"):
		users = [u.parent for u in frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
			if u.parent not in ("Administrator", "Guest") and frappe.db.get_value("User", u.parent, "enabled")]
		if users:
			return users[0]
	return None


def company_document_alerts():
	if not feature_on("codocs"):
		return
	from hipersign_trading.hipersign_trading.doctype.company_document.company_document import status_of

	stages = _days("compliance_reminder_days", "60,30,7,0")
	for d in frappe.get_all("Company Document", fields=["name", "company", "document_type", "expiry_date", "responsible_user", "renewal_status", "last_reminder", "status"]):
		doc = frappe.get_doc("Company Document", d.name)
		st = status_of(doc)
		if st != d.status:
			frappe.db.set_value("Company Document", d.name, "status", st, update_modified=False)
		if not d.expiry_date or d.renewal_status in ("Submitted to authority", "Renewed") and st == "Valid":
			continue
		left = date_diff(d.expiry_date, today())
		stage = next((s for s in sorted(stages) if left <= s), None)
		if left < 0:
			stage = "expired"
		if stage is None or str(stage) == (d.last_reminder or ""):
			continue
		if stage == "expired":
			subject = _("{0} of {1} has expired ({2})").format(_(d.document_type), d.company, frappe.format(d.expiry_date, "Date"))
		else:
			subject = _("{0} of {1} expires in {2} days ({3}) — start the renewal").format(_(d.document_type), d.company, left, frappe.format(d.expiry_date, "Date"))
		_remind("Company Document", d.name, d.responsible_user, subject, subject + "<br><br>" + _("Open it in Hipersign ERP → Company Compliance."))
		frappe.db.set_value("Company Document", d.name, "last_reminder", str(stage), update_modified=False)


def deadline_alerts():
	if not feature_on("codocs"):
		return
	stages = _days("deadline_reminder_days", "7,3,0")
	for d in frappe.get_all("Company Deadline", filters={"status": "Open"}, fields=["name", "company", "title", "due_date", "responsible_user", "last_reminder"]):
		left = date_diff(d.due_date, today())
		stage = "overdue" if left < 0 else next((s for s in sorted(stages) if left <= s), None)
		if stage is None or str(stage) == (d.last_reminder or ""):
			continue
		subject = (_("Overdue: {0} — {1} (was due {2})") if stage == "overdue" else _("Due in {3} days: {0} — {1} ({2})")).format(
			_(d.title), d.company, frappe.format(d.due_date, "Date"), left)
		_remind("Company Deadline", d.name, d.responsible_user, subject, subject)
		frappe.db.set_value("Company Deadline", d.name, "last_reminder", str(stage), update_modified=False)


def seed():
	for name, country, authority, before, expires in COMPANY_DOC_TYPES:
		if not frappe.db.exists("Company Document Type", name):
			frappe.get_doc({"doctype": "Company Document Type", "document_type_name": name, "country": country if frappe.db.exists("Country", country) else None,
				"authority": authority, "renew_before_days": before, "has_expiry": expires}).insert(ignore_permissions=True)
