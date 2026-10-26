"""Send documents by WhatsApp (click-to-chat with an expiring PDF link) and log every send."""

import frappe
from frappe import _
from frappe.utils import add_days, get_url, today
from urllib.parse import urlencode

from hipersign_trading.utils import settings

PARTY_FIELD = {
	"Quotation": ("Customer", "party_name"),
	"Sales Order": ("Customer", "customer"),
	"Sales Invoice": ("Customer", "customer"),
	"Delivery Note": ("Customer", "customer"),
	"Purchase Order": ("Supplier", "supplier"),
	"Export Shipment": ("Customer", "customer"),
	"Lead": ("Lead", "name"),
}


def _mobile(doc):
	if doc.doctype == "Lead":
		return doc.mobile_no or doc.phone
	m = doc.get("contact_mobile")
	if m:
		return m
	party_type, field = PARTY_FIELD.get(doc.doctype, (None, None))
	if party_type and doc.get(field) and frappe.db.exists(party_type, doc.get(field)):
		return frappe.db.get_value(party_type, doc.get(field), "mobile_no")
	return None


@frappe.whitelist()
def whatsapp_link(doctype, name, print_format=None):
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("print" if doctype != "Lead" else "read")
	days = settings().whatsapp_link_expiry_days or 7
	url = ""
	if doctype != "Lead":
		key = doc.get_document_share_key(expires_on=add_days(today(), days))
		params = {"doctype": doctype, "name": name, "key": key}
		if print_format:
			params["format"] = print_format
		url = get_url("/api/method/frappe.utils.print_format.download_pdf?" + urlencode(params))
	mobile = "".join(ch for ch in (_mobile(doc) or "") if ch.isdigit())
	title = doc.get("customer_name") or doc.get("supplier_name") or doc.get("company_name") or doc.get("lead_name") or ""
	msg = _("Dear {0}, please find {1} {2} from {3}.").format(
		title, _(doctype).lower(), name, frappe.defaults.get_global_default("company") or ""
	)
	if url:
		msg += "\n" + url + "\n" + _("(link valid for {0} days)").format(days)
	return {"mobile": mobile, "message": msg, "url": url}


@frappe.whitelist()
def log_send(doctype, name, channel, to=None):
	frappe.get_doc(doctype, name).add_comment(
		"Info", _("Sent by {0} to {1} — {2}").format(channel, to or _("contact"), frappe.session.user)
	)
	return True
