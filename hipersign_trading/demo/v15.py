"""v1.5 demo data: the conversations of the prototype's Messages screen, kept as comments on the records they are about."""

import frappe
from frappe.utils import add_days, get_datetime, today

from hipersign_trading.demo import user_email


def _mention(key):
	email = user_email(key)
	name = frappe.db.get_value("User", email, "full_name") or email
	return f'<span class="mention" data-id="{email}" data-value="{name}" data-denotation-char="@">﻿<span contenteditable="false"><span class="ql-mention-denotation-char">@</span>{name}</span>﻿</span>'


def _say(doctype, name, key, days, time, html):
	if not name or not frappe.db.exists(doctype, name):
		return
	if frappe.db.exists("Comment", {"reference_doctype": doctype, "reference_name": name, "content": html}):
		return
	email = user_email(key)
	full = frappe.db.get_value("User", email, "full_name") or email
	c = frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": doctype, "reference_name": name,
		"content": html, "comment_email": email, "comment_by": full}).insert(ignore_permissions=True)
	when = get_datetime(f"{add_days(today(), days)} {time}:00")
	frappe.db.set_value("Comment", c.name, {"owner": email, "creation": when, "modified": when}, update_modified=False)


COMPANY = {
	"name": "Hipersign Demo Trading LLC", "name_ar": "هايبرساين ديمو للتجارة ذ.م.م", "trn": "100384927150003",
	"line1": "Office 1204, Al Quoz Business Tower", "city": "Dubai", "phone": "+971 4 000 1204", "email": "info@hipersigndemo.ae",
}


def v15_company_identity(c):
	"""The prototype's company details on the demo company: TRN, Arabic name and address on every print."""
	co = frappe.get_doc("Company", c.company)
	co.tax_id = co.tax_id or COMPANY["trn"]
	if co.meta.has_field("company_name_in_arabic") and not co.get("company_name_in_arabic"):
		co.company_name_in_arabic = COMPANY["name_ar"]
	co.phone_no = co.phone_no or COMPANY["phone"]
	co.email = co.email or COMPANY["email"]
	co.flags.ignore_mandatory = True
	co.save(ignore_permissions=True)
	if not frappe.db.exists("Dynamic Link", {"link_doctype": "Company", "link_name": c.company, "parenttype": "Address"}):
		frappe.get_doc({"doctype": "Address", "address_title": c.company, "address_type": "Billing", "address_line1": COMPANY["line1"],
			"city": COMPANY["city"], "country": "United Arab Emirates", "phone": COMPANY["phone"], "email_id": COMPANY["email"],
			"is_your_company_address": 1, "is_primary_address": 1,
			"links": [{"link_doctype": "Company", "link_name": c.company}]}).insert(ignore_permissions=True)


def v15_conversations(c):
	shp = frappe.db.get_value("Import Shipment", {"status": "Under Customs Clearance"}) or frappe.db.get_value("Import Shipment", {"status": "Arrived at Port"})
	if shp:
		_say("Import Shipment", shp, "logi", -2, "10:02", f"Shipment {shp} is at Jebel Ali. Customs is holding it — the certificate of origin is missing.")
		_say("Import Shipment", shp, "pm", -2, "11:15", f"I have asked the supplier to courier the original. {_mention('logi')} please chase the clearing agent for a provisional release.")
		_say("Import Shipment", shp, "sm", -1, "09:40", "Two customer orders depend on these units. Any revised ETA I can share?")
		_say("Import Shipment", shp, "logi", 0, "08:30", f"The clearing agent expects release within 2 working days once the CoO arrives. {_mention('sm')} please inform the customer.")
	inv = frappe.db.get_value("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", today()], "is_return": 0},
		["name", "customer_name"], order_by="due_date asc", as_dict=True)
	if inv:
		_say("Sales Invoice", inv.name, "acc", -1, "12:01", f"{inv.name} for {inv.customer_name} is overdue. {_mention('sales')} can you call the customer today?")
		_say("Sales Invoice", inv.name, "sales", 0, "10:15", "Called their accounts team — they promise a transfer this week. I'll follow up on Thursday.")
	qtn = frappe.db.get_value("Quotation", {"docstatus": ["<", 2]}, ["name", "party_name"], order_by="transaction_date desc", as_dict=True)
	if qtn:
		_say("Quotation", qtn.name, "sales", -1, "14:02", f"{_mention('sm')} can I offer 8% on the readers? They are comparing with another supplier.")
		_say("Quotation", qtn.name, "sm", -1, "14:10", "Max 6% without approval. Above that send it through the system — it will come to me.")
	po = frappe.db.get_value("Purchase Order", {"workflow_state": ["like", "Pending%"]}) if frappe.get_meta("Purchase Order").has_field("workflow_state") else None
	if po:
		_say("Purchase Order", po, "buyer", -1, "09:05", f"Raised for the Q4 stock plan — {_mention('pm')} please approve so the supplier can confirm the production slot.")
	so = frappe.db.get_value("Sales Order", {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]}, "name", order_by="delivery_date asc")
	if so:
		_say("Sales Order", so, "whm", -1, "16:20", "Picked and packed — waiting for the truck slot tomorrow morning.")
		_say("Sales Order", so, "sm", 0, "08:55", f"Thanks. {_mention('logi')} please share the driver's number with the customer once it leaves.")


STEPS = [v15_company_identity, v15_conversations]
