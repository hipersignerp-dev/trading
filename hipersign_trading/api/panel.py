"""v1.6.0: the record panel — the prototype's side panel that opens over a page instead of the full form.

get_panel(doctype, name) returns a description of the panel; public/js/hs_panel.js draws it. Every panel has a title,
the record type and status, header facts, a progress line where the record has stages, sections (label / value
pairs or tables), the approval card, the documents box, the history and the next-step buttons. The data is read with
the user's own permissions; the buttons only call ERPNext's own "make" methods or the whitelisted actions below,
which check permissions again.

A value in facts and sections is a string, or a dict: {"link": [doctype, name], "label": …} opens that record's
panel, {"pill": label, "tone": …} is a status badge, {"bar": percent} is a progress bar, {"money": amount,
"currency": …} is an amount.
"""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, fmt_money, formatdate, get_datetime, getdate, money_in_words, today

PANELS = ("Lead", "Quotation", "Sales Order", "Customer", "Sales Invoice", "Delivery Note", "Item", "Purchase Order", "Supplier",
	"Import Shipment", "Letter of Credit", "Purchase Receipt")

STATUS_TONE = {
	"Draft": "grey", "To Deliver and Bill": "blue", "To Deliver": "blue", "To Bill": "blue", "Completed": "green", "Closed": "grey",
	"Cancelled": "red", "On Hold": "orange", "Open": "blue", "Ordered": "green", "Lost": "red", "Expired": "grey", "Partially Ordered": "blue",
	"Paid": "green", "Unpaid": "orange", "Overdue": "red", "Partly Paid": "blue", "Return": "grey", "Credit Note Issued": "grey",
	"Submitted": "blue", "To Bill ": "blue", "Won": "green", "New": "blue", "Contacted": "blue", "Qualified": "blue", "Proposal": "violet",
	"Negotiation": "orange", "Return Issued": "grey", "Partly Billed": "blue", "Pending Sales Manager": "orange",
	"Pending Finance Manager": "orange", "Rejected": "red", "Approved": "green", "Pending Purchase Manager": "orange",
	"To Receive and Bill": "blue", "To Receive": "blue", "Received": "green", "In Transit": "blue", "Booked": "grey",
	"Under Customs Clearance": "orange", "Cleared": "green", "Received at Warehouse": "green", "Issued": "blue", "Accepted": "violet",
}


# ---------------------------------------------------------------- value helpers
def link(doctype, name, label=None):
	return {"link": [doctype, name], "label": label or name} if name else ""


def pill(label, tone=None):
	return {"pill": _(label), "tone": tone or STATUS_TONE.get(label, "grey")} if label else ""


def money(v, currency=None):
	return {"money": flt(v), "currency": currency}


def d(v):
	return formatdate(v, "dd MMM yyyy") if v else ""


def dt(v):
	return get_datetime(v).strftime("%d %b %Y %H:%M") if v else ""


def bar(pct):
	return {"bar": round(flt(pct), 1)}


def kv(*pairs):
	return [[_(label), value] for label, value in pairs if value not in (None, "", [])]


def section(title, rows=None, cols=None, kind="kv", sub=None, actions=None, total=None):
	s = {"title": _(title), "kind": kind, "sub": sub, "actions": actions or []}
	if kind == "kv":
		s["rows"] = rows or []
	else:
		s["cols"] = [_(c) for c in cols]
		s["rows"] = rows or []
		s["total"] = total
	return s


def progress(steps, current, done=None):
	"""steps: labels; current: index of the step in progress (len(steps) when everything is done)."""
	return {"steps": [_(s) for s in steps], "current": current}


def act(label, kind="default", **kw):
	"""A button. kw: make=<method> (ERPNext mapper, opens the new draft), route=[…], action=<name> (server action below),
	client=<name> (a dialog in hs_panel.js), confirm=<text>."""
	return dict(label=_(label), kind=kind, **kw)


def _wf_state(doc):
	return doc.get("workflow_state") or None


def _status(doc):
	st = _wf_state(doc) if doc.docstatus == 0 and _wf_state(doc) else doc.get("status")
	if doc.docstatus == 2:
		st = "Cancelled"
	return st or ("Draft" if doc.docstatus == 0 else "Submitted")


def _history(doc, limit=12):
	rows = [[dt(doc.creation), _("Created by {0}").format(frappe.utils.get_fullname(doc.owner))]]
	for c in frappe.get_all("Comment", filters={"reference_doctype": doc.doctype, "reference_name": doc.name,
			"comment_type": ["in", ["Comment", "Info", "Workflow", "Submitted", "Cancelled", "Edit", "Attachment"]]},
			fields=["creation", "comment_type", "content", "comment_email", "owner"], order_by="creation asc", limit=40):
		text = frappe.utils.strip_html(c.content or "").strip() or _(c.comment_type)
		who = frappe.utils.get_fullname(c.owner)
		rows.append([dt(c.creation), f"{text} — {who}" if c.comment_type in ("Comment", "Submitted", "Cancelled", "Workflow") else text])
	if doc.docstatus == 1 and not any("ubmitted" in r[1] for r in rows):
		rows.append([dt(doc.modified), _("Submitted")])
	return rows[-limit:]


def _approval(doc):
	"""The approval card while the record waits in a Hipersign workflow."""
	state = _wf_state(doc)
	if not state or doc.docstatus != 0 or not state.startswith("Pending"):
		return None
	reason = doc.get("hs_approval_reason") or ""
	from frappe.model.workflow import get_transitions

	try:
		transitions = [t.action for t in get_transitions(doc)]
	except Exception:
		transitions = []
	return {"state": _(state), "waiting_for": _(state.replace("Pending ", "")), "reason": reason, "actions": transitions}


def _documents(doc):
	try:
		from hipersign_trading.doc_rules import checklist
		from hipersign_trading.features import doc_level

		if doc_level() == "Off":
			return None
		rules = checklist(doc)
	except Exception:
		return None
	if not rules:
		return None
	return [{"type": _(r["document_type"]), "raw": r["document_type"], "level": r["level"], "attached": bool(r["attached"]),
		"waiver": (r["waiver"] or {}).get("name") if r["waiver"] else None, "note": _(r["note"]) if r.get("note") else ""} for r in rules]


def _base(doc, title, subtitle):
	return {
		"doctype": doc.doctype, "name": doc.name, "title": title, "subtitle": subtitle, "status": pill(_status(doc)),
		"facts": [], "progress": None, "sections": [], "approval": _approval(doc), "documents": _documents(doc),
		"history": _history(doc), "actions": [], "can_edit": bool(frappe.has_permission(doc.doctype, "write", doc)),
		"docstatus": doc.docstatus, "unread": _unread(doc),
	}


def _unread(doc):
	try:
		return frappe.db.count("Communication", {"reference_doctype": doc.doctype, "reference_name": doc.name, "seen": 0, "sent_or_received": "Received"})
	except Exception:
		return 0


def _items_rows(doc, extra=None):
	rows = []
	for i, it in enumerate(doc.get("items") or [], 1):
		r = [i, link("Item", it.item_code, it.item_name or it.item_code), it.uom or it.stock_uom, flt(it.qty), money(it.rate, doc.currency),
			f"{flt(it.discount_percentage):g}%" if flt(it.discount_percentage) else "—", money(it.net_amount or it.amount, doc.currency)]
		if extra:
			r += extra(it)
		rows.append(r)
	return rows


def _totals(doc):
	return section("Totals", kv(
		("Net total", money(doc.net_total, doc.currency)),
		(_("VAT") + (f" {flt(doc.total_taxes_and_charges / doc.net_total * 100, 1):g}%" if flt(doc.net_total) else ""), money(doc.total_taxes_and_charges, doc.currency)),
		("Grand total", money(doc.rounded_total or doc.grand_total, doc.currency)),
		("In words", doc.get("in_words") or money_in_words(doc.rounded_total or doc.grand_total, doc.currency)),
	))


def _address(name):
	if not name:
		return ""
	a = frappe.db.get_value("Address", name, ["address_title", "city", "country"], as_dict=True)
	place = ", ".join(dict.fromkeys(y for y in [a.city, a.country] if y)) if a else ""
	return " — ".join(x for x in [a.address_title, place] if x) if a else name


def _contact(name):
	if not name:
		return ""
	c = frappe.db.get_value("Contact", name, ["full_name", "mobile_no", "phone"], as_dict=True)
	return " · ".join(x for x in [c.full_name, c.mobile_no or c.phone] if x) if c else name


def _can(doctype, ptype="create"):
	return bool(frappe.has_permission(doctype, ptype))


# ---------------------------------------------------------------- the panels
def lead(doc):
	from hipersign_trading.api.crm import STAGES

	stage = doc.get("hs_pipeline_stage") or "New"
	p = _base(doc, doc.company_name or doc.lead_name, _("Lead"))
	p["status"] = pill(stage)
	p["facts"] = kv(
		("Contact", doc.lead_name), ("Mobile / WhatsApp", doc.mobile_no or doc.whatsapp_no), ("Email", doc.email_id),
		("Emirate", doc.get("hs_emirate") or doc.city), ("Source", doc.get("utm_source") or doc.get("source")),
		("Interested in", doc.get("hs_interested_in")), ("Estimated value", money(doc.get("hs_estimated_value")) if doc.get("hs_estimated_value") else ""),
		("Probability", f"{cint(doc.get('hs_probability'))}%"), ("Expected close", d(doc.get("hs_expected_close"))),
		("Owner", frappe.utils.get_fullname(doc.lead_owner) if doc.lead_owner else ""), ("Next follow-up", d(doc.get("hs_next_follow_up"))),
		("Next action", doc.get("hs_next_action")),
	)
	steps = list(STAGES) + ["Won"]
	p["progress"] = progress(steps, len(steps) if stage == "Won" else (steps.index(stage) if stage in steps else 0))
	if stage == "Lost":
		p["facts"].append([_("Lost reason"), doc.get("hs_lost_reason") or ""])
	quotes = frappe.get_all("Quotation", filters={"party_name": doc.name, "quotation_to": "Lead"}, fields=["name", "transaction_date", "grand_total", "status", "currency"],
		order_by="creation desc", limit=10)
	if quotes:
		p["sections"].append(section("Quotations", cols=["Quotation", "Date", "Value", "Status"], kind="table",
			rows=[[link("Quotation", q.name), d(q.transaction_date), money(q.grand_total, q.currency), pill(q.status)] for q in quotes]))
	p["sections"].append(section("Activity", sub=_("Calls, meetings and messages — newest last"), kind="kv", rows=[],
		actions=[act("Log activity", client="log_activity")]))
	acts = []
	if stage not in ("Won", "Lost") and p["can_edit"]:
		nxt = steps[steps.index(stage) + 1] if stage in steps and steps.index(stage) + 1 < len(steps) - 1 else None
		if nxt:
			acts.append(act("→ " + _(nxt), action="lead_stage", args={"stage": nxt}))
		acts += [act("Won", action="lead_stage", args={"stage": "Won"}), act("Lost", client="lead_lost")]
	if _can("Quotation") and stage != "Lost":
		acts.append(act("Create quotation", kind="primary", make="erpnext.crm.doctype.lead.lead.make_quotation"))
	p["actions"] = acts
	return p


def quotation(doc):
	p = _base(doc, f"{doc.name} — {doc.customer_name or doc.party_name}", _("Quotation"))
	party = link("Customer" if doc.quotation_to == "Customer" else "Lead", doc.party_name, doc.customer_name or doc.party_name)
	p["sections"] = [
		section("Customer", kv(("Customer", party), ("Contact person", _contact(doc.contact_person)), ("Address", _address(doc.customer_address)),
			("TRN", frappe.db.get_value("Customer", doc.party_name, "tax_id") if doc.quotation_to == "Customer" else ""))),
		section("Quotation", kv(("Quotation date", d(doc.transaction_date)), ("Valid till", d(doc.valid_till)),
			("Subject", doc.get("hs_subject")), ("Enquiry", " · ".join(x for x in [doc.get("hs_enquiry_ref"), d(doc.get("hs_enquiry_date"))] if x)),
			("Prepared by", frappe.utils.get_fullname(doc.owner)), ("Payment terms", doc.payment_terms_template),
			("Delivery period", doc.get("hs_delivery_period")), ("Warranty", f"{doc.get('hs_warranty_months')} {_('months')}" if doc.get("hs_warranty_months") not in (None, "", "0") else ""),
			("Currency", doc.currency), ("Estimated margin", f"{flt(doc.get('hs_estimated_margin'), 1)}%" if doc.get("hs_estimated_margin") else ""),
			("Status", pill(_status(doc))))),
		section("Lines", kind="table", cols=["#", "Item / service", "UOM", "Qty", "Rate", "Disc", "Net"], rows=_items_rows(doc)),
		_totals(doc),
	]
	orders = frappe.get_all("Sales Order Item", filters={"prevdoc_docname": doc.name, "docstatus": ["<", 2]}, pluck="parent", distinct=True)
	if orders:
		p["facts"] = kv(("Sales order", link("Sales Order", orders[0])))
	acts = []
	if doc.docstatus == 0 and p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Quotation", doc.name]))
	if doc.docstatus == 1 and doc.status not in ("Lost", "Ordered", "Expired") and p["can_edit"]:
		acts.append(act("Lost", client="quote_lost"))
	if doc.docstatus == 1 and doc.status not in ("Lost", "Ordered") and _can("Sales Order"):
		acts.append(act("Make sales order", kind="primary", make="erpnext.selling.doctype.quotation.quotation.make_sales_order"))
	p["actions"] = acts
	return p


def sales_order(doc):
	export = bool(doc.get("hs_is_export"))
	p = _base(doc, f"{doc.name} — {doc.customer_name}", _("Export sales order") if export else _("Sales order"))
	st = _status(doc)
	steps = ["Draft", "Approval", "Delivery", "Invoice", "Payment", "Completed"]
	if doc.docstatus == 0:
		cur = 1 if (_wf_state(doc) or "").startswith("Pending") else 0
	elif flt(doc.per_delivered) < 100:
		cur = 2
	elif flt(doc.per_billed) < 100:
		cur = 3
	else:
		paid = not frappe.db.exists("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "name": ["in", _invoices_of_order(doc.name) or [""]]})
		cur = 6 if paid else 4
	p["progress"] = progress(steps, cur)
	tax_id = frappe.db.get_value("Customer", doc.customer, "tax_id")
	p["sections"] = [
		section("Customer", kv(("Customer", link("Customer", doc.customer, doc.customer_name)), ("TRN", tax_id or (_("Outside UAE") if export else "")),
			("Contact person", _contact(doc.contact_person)), ("Customer's PO", " · ".join(x for x in [doc.po_no, d(doc.po_date)] if x)),
			("Billing address", _address(doc.customer_address)), ("Shipping address", _address(doc.shipping_address_name))),
			actions=[act("Edit details", route=["Form", "Sales Order", doc.name])] if doc.docstatus == 0 and p["can_edit"] else []),
		section("Order", kv(("Order date & time", dt(f"{doc.transaction_date} {doc.get('transaction_time') or '00:00:00'}") if doc.get("transaction_time") else d(doc.transaction_date)),
			("Delivery date", d(doc.delivery_date)), ("Sales person", ", ".join(s.sales_person for s in doc.get("sales_team") or []) or frappe.utils.get_fullname(doc.owner)),
			("Payment terms", doc.payment_terms_template), ("Source warehouse", doc.set_warehouse or _("Any — chosen at delivery")),
			("Export terms", " · ".join(x for x in [doc.get("incoterm"), doc.get("named_place"), doc.get("hs_payment_method"), doc.get("hs_shipment_mode")] if x) if export else ""),
			(_("Total in {0}").format(doc.currency), money(doc.rounded_total or doc.grand_total, doc.currency)),
			("% delivered", bar(doc.per_delivered)), ("% billed", bar(doc.per_billed)), ("Status", pill(st)))),
		section("Items", kind="table", cols=["#", "Item", "UOM", "Qty", "Rate", "Disc", "Net", "Delivered", "Billed", "Pending"],
			rows=_items_rows(doc, lambda it: [flt(it.delivered_qty), money(it.billed_amt, doc.currency), flt(it.qty) - flt(it.delivered_qty)])),
		_totals(doc),
	]
	if doc.get("payment_schedule"):
		p["sections"].append(section("Payment schedule", kind="table", cols=["Payment term", "Due date", "%", "Amount"],
			rows=[[r.payment_term or r.description or "", d(r.due_date), f"{flt(r.invoice_portion):g}%", money(r.payment_amount, doc.currency)] for r in doc.payment_schedule]))
	if doc.get("terms"):
		p["sections"].append(section("Terms & remarks", kv(("Terms", frappe.utils.strip_html(doc.terms)[:600]))))
	links = []
	for dn in frappe.get_all("Delivery Note Item", filters={"against_sales_order": doc.name, "docstatus": 1}, pluck="parent", distinct=True):
		links.append(["Delivery note", link("Delivery Note", dn)])
	for si in _invoices_of_order(doc.name):
		links.append(["Invoice", link("Sales Invoice", si)])
	if links:
		p["facts"] = links
	acts = []
	if doc.docstatus == 0 and p["can_edit"]:
		acts.append(act("Edit", kind="primary", route=["Form", "Sales Order", doc.name]))
	if doc.docstatus == 1 and st not in ("Closed", "Completed", "On Hold"):
		shipment = frappe.db.get_value("Export Shipment", {"sales_order": doc.name, "docstatus": ["<", 2]}) if export and frappe.db.table_exists("Export Shipment") else None
		if shipment:
			p["facts"] = (p.get("facts") or []) + [[_("Export shipment"), link("Export Shipment", shipment)]]
		elif export and _can("Export Shipment"):
			acts.append(act("Book export shipment", kind="primary" if flt(doc.per_delivered) == 0 else "default", action="book_export"))
		if flt(doc.per_delivered) < 100 and _can("Delivery Note"):
			acts.append(act("Create delivery note", kind="primary" if (not export or shipment) else "default", make="erpnext.selling.doctype.sales_order.sales_order.make_delivery_note"))
		if flt(doc.per_billed) < 100 and _can("Sales Invoice"):
			acts.append(act("Create invoice", kind="primary" if flt(doc.per_delivered) >= 100 else "default", make="erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice"))
		if flt(doc.advance_paid) < flt(doc.grand_total) and flt(doc.per_billed) == 0 and _can("Payment Entry"):
			acts.append(act("Receive advance", client="receive_advance"))
	p["actions"] = acts
	return p


def _invoices_of_order(so):
	return frappe.get_all("Sales Invoice Item", filters={"sales_order": so, "docstatus": 1}, pluck="parent", distinct=True)


def customer(doc):
	from erpnext.selling.doctype.customer.customer import get_customer_outstanding

	company = _company()
	p = _base(doc, doc.customer_name, _("Customer"))
	p["status"] = pill("Disabled" if doc.disabled else (doc.get("hs_kyc_status") or "Active"), "red" if doc.disabled else
		{"Verified": "green", "Pending": "orange", "Expired": "red", "Blocked": "red"}.get(doc.get("hs_kyc_status"), "green"))
	limit = next((flt(r.credit_limit) for r in doc.get("credit_limits") or [] if r.company == company), 0)
	try:
		outstanding = flt(get_customer_outstanding(doc.name, company, ignore_outstanding_sales_order=True)) if frappe.has_permission("Sales Invoice") else None
	except Exception:
		outstanding = None
	open_orders = frappe.db.count("Sales Order", {"customer": doc.name, "docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]}) if frappe.has_permission("Sales Order") else None
	cur = frappe.get_cached_value("Company", company, "default_currency") if company else None
	p["facts"] = kv(
		("Customer code", doc.name), ("Group", doc.customer_group), ("City", doc.get("hs_emirate") or doc.get("hs_country_city")), ("TRN", doc.tax_id),
		("Payment terms", doc.payment_terms), ("Credit limit", money(limit, cur) if limit else _("No limit")),
		("Outstanding", money(outstanding, cur) if outstanding is not None else ""), ("Open orders", open_orders if open_orders is not None else ""),
		("Available credit", money(limit - flt(outstanding), cur) if limit and outstanding is not None else ""),
	)
	p["sections"].append(section("Customer details", kv(("Customer type", _(doc.customer_type)), ("Market", _(doc.get("hs_market") or "")),
		("Territory", doc.territory), ("Billing currency", doc.default_currency or cur), ("Price list", doc.default_price_list), ("Website", doc.website),
		("Lead source", doc.get("hs_lead_source")), ("Trade licence", " · ".join(x for x in [doc.get("hs_trade_licence_no"), d(doc.get("hs_trade_licence_expiry"))] if x)))))
	contacts = frappe.db.sql("""select c.name, c.full_name, c.mobile_no, c.email_id, c.designation from `tabContact` c
		join `tabDynamic Link` l on l.parent = c.name and l.parenttype = 'Contact' where l.link_doctype = 'Customer' and l.link_name = %s
		order by c.is_primary_contact desc, c.creation asc limit 10""", doc.name, as_dict=True)
	if contacts:
		p["sections"].append(section("Contacts", kind="table", cols=["Name", "Mobile / email"],
			rows=[[" · ".join(x for x in [c.full_name, c.designation] if x), " · ".join(x for x in [c.mobile_no, c.email_id] if x)] for c in contacts],
			actions=[act("Add contact", client="new_contact")]))
	addrs = frappe.db.sql("""select a.name, a.address_title, a.address_type, a.address_line1, a.city from `tabAddress` a
		join `tabDynamic Link` l on l.parent = a.name and l.parenttype = 'Address' where l.link_doctype = 'Customer' and l.link_name = %s
		order by a.is_primary_address desc limit 10""", doc.name, as_dict=True)
	if addrs:
		p["sections"].append(section("Addresses", kind="table", cols=["Address", "Type"],
			rows=[[" — ".join(x for x in [a.address_title, a.address_line1, a.city] if x), _(a.address_type)] for a in addrs],
			actions=[act("Add address", client="new_address")]))
	if frappe.has_permission("Quotation"):
		q = frappe.get_all("Quotation", filters={"party_name": doc.name, "quotation_to": "Customer", "docstatus": ["<", 2]},
			fields=["name", "transaction_date", "grand_total", "status", "currency"], order_by="transaction_date desc", limit=8)
		if q:
			p["sections"].append(section("Quotations", kind="table", cols=["Quotation", "Date", "Value", "Status"],
				rows=[[link("Quotation", x.name), d(x.transaction_date), money(x.grand_total, x.currency), pill(x.status)] for x in q]))
	if frappe.has_permission("Sales Invoice"):
		inv = frappe.get_all("Sales Invoice", filters={"customer": doc.name, "docstatus": 1, "outstanding_amount": ["!=", 0]},
			fields=["name", "due_date", "outstanding_amount", "currency"], order_by="due_date asc", limit=10)
		if inv:
			p["sections"].append(section("Open invoices", kind="table", cols=["Invoice", "Due", "Outstanding"],
				rows=[[link("Sales Invoice", x.name), {"pill": d(x.due_date), "tone": "red"} if x.due_date and getdate(x.due_date) < getdate(today()) else d(x.due_date),
					money(x.outstanding_amount, x.currency)] for x in inv]))
	if frappe.has_permission("Sales Order"):
		so = frappe.get_all("Sales Order", filters={"customer": doc.name, "docstatus": ["<", 2]}, fields=["name", "transaction_date", "status", "grand_total", "currency"],
			order_by="transaction_date desc", limit=8)
		if so:
			p["sections"].append(section("Orders", kind="table", cols=["Order", "Date", "Value", "Status"],
				rows=[[link("Sales Order", x.name), d(x.transaction_date), money(x.grand_total, x.currency), pill(x.status)] for x in so]))
	acts = []
	if p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Customer", doc.name]))
		acts.append(act("Credit limit", client="credit_limit"))
	if _can("Quotation"):
		acts.append(act("Quick quote", client="quick_doc", args={"doctype": "Quotation"}))
	if _can("Sales Order"):
		acts.append(act("Quick order", kind="primary", client="quick_doc", args={"doctype": "Sales Order"}))
	p["actions"] = acts
	return p


def sales_invoice(doc):
	ret = bool(doc.is_return)
	p = _base(doc, f"{doc.name} — {doc.customer_name}", _("Credit note") if ret else _("Tax invoice"))
	so = sorted({i.sales_order for i in doc.items if i.sales_order})
	dns = sorted({i.delivery_note for i in doc.items if i.delivery_note})
	paid = flt(doc.rounded_total or doc.grand_total) - flt(doc.outstanding_amount)
	p["sections"] = [
		section("Customer", kv(("Customer", link("Customer", doc.customer, doc.customer_name)), ("Customer TRN", doc.get("tax_id") or frappe.db.get_value("Customer", doc.customer, "tax_id")),
			("Contact person", _contact(doc.contact_person)), ("Billing address", _address(doc.customer_address)),
			("Shipping address", _address(doc.shipping_address_name)), ("Place of supply", doc.get("place_of_supply")))),
		section("Invoice", kv(("Posting date", d(doc.posting_date)), ("Due date", d(doc.due_date)), ("Payment terms", doc.payment_terms_template),
			("Customer's PO", doc.po_no), ("Sales order", ", ".join(so)), ("Delivery notes", ", ".join(dns)),
			("Against invoice", link("Sales Invoice", doc.return_against) if ret else ""), ("Reason", doc.get("hs_return_reason") if ret else ""),
			("Currency", doc.currency), ("Status", pill(_status(doc))))),
		section("Items", kind="table", cols=["#", "Item", "UOM", "Qty", "Rate", "Disc", "Net"], rows=_items_rows(doc)),
		section("Totals", kv(("Net total", money(doc.net_total, doc.currency)), ("VAT", money(doc.total_taxes_and_charges, doc.currency)),
			("Grand total", money(doc.rounded_total or doc.grand_total, doc.currency)), ("In words", doc.get("in_words")),
			("Paid", money(paid, doc.currency) if doc.docstatus == 1 and not ret else ""),
			("Outstanding", money(doc.outstanding_amount, doc.currency) if doc.docstatus == 1 else ""))),
	]
	pays = frappe.db.sql("""select pe.name, pe.posting_date, pe.mode_of_payment, r.allocated_amount from `tabPayment Entry Reference` r
		join `tabPayment Entry` pe on pe.name = r.parent where r.reference_doctype = 'Sales Invoice' and r.reference_name = %s and pe.docstatus = 1
		order by pe.posting_date""", doc.name, as_dict=True) if frappe.has_permission("Payment Entry") else []
	if pays:
		p["sections"].append(section("Payments", kind="table", cols=["Receipt", "Date", "Mode", "Amount"],
			rows=[[link("Payment Entry", x.name), d(x.posting_date), x.mode_of_payment or "", money(x.allocated_amount, doc.currency)] for x in pays]))
	acts = [act("Tax invoice (EN/AR)", print_format="Hipersign Tax Invoice")]
	if doc.docstatus == 0 and p["can_edit"]:
		acts.insert(0, act("Edit", route=["Form", "Sales Invoice", doc.name]))
	if doc.docstatus == 1 and flt(doc.outstanding_amount) > 0 and _can("Payment Entry"):
		acts.append(act("Record payment", kind="primary", client="record_payment"))
	p["actions"] = acts
	return p


def delivery_note(doc):
	p = _base(doc, f"{doc.name} — {doc.customer_name}", _("Delivery note"))
	so = sorted({i.against_sales_order for i in doc.items if i.against_sales_order})
	billed = flt(doc.per_billed)
	steps = ["Pick", "Pack", "Delivery note", "Delivered", "Invoiced"]
	pod = doc.get("hs_delivery_status") == "Delivered" or doc.get("hs_pod_time")
	cur = 2 if doc.docstatus == 0 else (4 if billed >= 100 else 3 if not pod else 4)
	p["progress"] = progress(steps, 5 if billed >= 100 and pod else cur)
	p["sections"] = [
		section("Delivery", kv(("Customer", link("Customer", doc.customer, doc.customer_name)), ("Sales order", ", ".join(so)),
			("Posting date", d(doc.posting_date)), ("Shipping address", _address(doc.shipping_address_name)), ("Contact person", _contact(doc.contact_person)),
			("Driver", doc.driver_name or doc.get("hs_driver")), ("Vehicle", doc.vehicle_no), ("Delivery status", pill(doc.get("hs_delivery_status")) if doc.get("hs_delivery_status") else ""),
			("Received by", " · ".join(x for x in [doc.get("hs_received_by"), dt(doc.get("hs_pod_time"))] if x)), ("Delivery trip", link("Delivery Trip", doc.get("delivery_trip"))),
			("% billed", bar(billed)), ("Status", pill(_status(doc))))),
		section("Items", kind="table", cols=["#", "Item", "UOM", "Qty", "Warehouse", "Serial / batch"],
			rows=[[i, link("Item", it.item_code, it.item_name), it.uom, flt(it.qty), it.warehouse, (it.serial_no or it.batch_no or "").replace("\n", ", ")[:80]]
				for i, it in enumerate(doc.items, 1)]),
	]
	acts = [act("Delivery note", print_format="Hipersign Delivery Note")]
	if doc.docstatus == 0 and p["can_edit"]:
		acts.insert(0, act("Edit", route=["Form", "Delivery Note", doc.name]))
	if doc.docstatus == 1 and billed < 100 and doc.status not in ("Closed",) and _can("Sales Invoice"):
		acts.append(act("Create invoice", kind="primary", make="erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice"))
	p["actions"] = acts
	return p


def item(doc):
	from hipersign_trading.utils import valuation_rate

	p = _base(doc, doc.item_name, _("Item") if doc.is_stock_item else _("Service"))
	p["status"] = pill("Disabled" if doc.disabled else "Active", "red" if doc.disabled else "green")
	sell = flt(frappe.db.get_value("Item Price", {"item_code": doc.name, "selling": 1, "price_list": frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"}, "price_list_rate"))
	val = valuation_rate(doc.name) if doc.is_stock_item else flt(doc.valuation_rate)
	reorder = next((r.warehouse_reorder_level for r in doc.get("reorder_levels") or []), None)
	p["facts"] = kv(("Item code", doc.name), ("Arabic description", doc.get("hs_item_name_ar")), ("Category", doc.item_group), ("HS code", doc.customs_tariff_number),
		("Country of origin", doc.country_of_origin), ("Barcode", (doc.get("barcodes") or [{}])[0].get("barcode") if doc.get("barcodes") else ""),
		("Reorder level", reorder), ("Standard selling rate", money(sell) if sell else ""), ("Valuation (landed) rate", money(val) if val else ""),
		("Margin at list price", f"{flt((sell - val) / sell * 100, 1)}%" if sell and val else ""))
	p["sections"].append(section("Item details", kv(("Brand · model", " · ".join(x for x in [doc.brand, doc.get("hs_model")] if x)),
		("Description", frappe.utils.strip_html(doc.description or "")[:300] if doc.description != doc.item_name else ""), ("Sales unit", doc.sales_uom or doc.stock_uom),
		("Purchase unit", doc.purchase_uom or doc.stock_uom), ("Weight", f"{flt(doc.weight_per_unit):g} {doc.weight_uom or ''}" if doc.weight_per_unit else ""),
		("Warranty", f"{doc.warranty_period} {_('days')}" if doc.warranty_period else ""), ("Minimum order", doc.min_order_qty or ""),
		("Lead time", f"{doc.lead_time_days} {_('days')}" if doc.lead_time_days else ""),
		("Default supplier", next((r.default_supplier for r in doc.get("item_defaults") or [] if r.default_supplier), "")))))
	if doc.is_stock_item and frappe.has_permission("Bin"):
		bins = frappe.get_all("Bin", filters={"item_code": doc.name, "actual_qty": ["!=", 0]}, fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty"], order_by="actual_qty desc")
		p["sections"].append(section("Stock by warehouse", kind="table", cols=["Warehouse", "Qty", "Reserved", "On order"],
			rows=[[b.warehouse, flt(b.actual_qty), flt(b.reserved_qty), flt(b.ordered_qty)] for b in bins]))
	if frappe.has_permission("Sales Invoice"):
		r = frappe.db.sql("""select sum(i.stock_qty) qty, sum(i.base_net_amount) amt from `tabSales Invoice Item` i join `tabSales Invoice` s on s.name = i.parent
			where s.docstatus = 1 and s.is_return = 0 and i.item_code = %s and s.posting_date >= date_sub(curdate(), interval 60 day)""", doc.name, as_dict=True)[0]
		if flt(r.qty):
			avg = flt(r.amt) / flt(r.qty)
			p["sections"].append(section("Last 60 days", kv(("Qty sold", flt(r.qty)), ("Average selling rate", money(avg)),
				("Margin", f"{flt((avg - val) / avg * 100, 1)}%" if avg and val else ""))))
	acts = []
	if p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Item", doc.name]))
	if doc.is_stock_item:
		acts.append(act("Stock ledger", route=["query-report", "Stock Ledger"], options={"item_code": doc.name}))
	if doc.is_purchase_item and _can("Purchase Order"):
		acts.append(act("Create PO", kind="primary", client="quick_doc", args={"doctype": "Purchase Order", "item": doc.name}))
	p["actions"] = acts
	return p


# ---------------------------------------------------------------- purchasing (v1.6.0 step 2)
def _company_currency(company):
	return frappe.get_cached_value("Company", company, "default_currency")


def purchase_order(doc):
	ccy = _company_currency(doc.company)
	foreign = doc.currency != ccy
	ship = None
	if frappe.db.table_exists("Import Shipment PO"):
		sh = frappe.get_all("Import Shipment PO", filters={"purchase_order": doc.name, "parenttype": "Import Shipment"}, pluck="parent", order_by="creation desc", limit=1)
		if sh:
			ship = frappe.db.get_value("Import Shipment", sh[0], ["name", "status", "eta", "bl_awb", "mode", "port_of_loading", "port_of_discharge", "bill_of_entry"], as_dict=True)
	lc = frappe.db.get_value("Letter of Credit", {"purchase_order": doc.name, "status": ["!=", "Cancelled"]}, ["name", "lc_number", "status", "amount", "currency", "expiry_date"],
		as_dict=True) if frappe.db.table_exists("Letter of Credit") and frappe.has_permission("Letter of Credit") else None
	country = frappe.db.get_value("Supplier", doc.supplier, "country")
	p = _base(doc, f"{doc.name} — {doc.supplier_name}", _("Import purchase order") if ship or foreign else _("Purchase order"))
	receipts = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": doc.name, "docstatus": 1}, pluck="parent", distinct=True)
	bills = frappe.get_all("Purchase Invoice Item", filters={"purchase_order": doc.name, "docstatus": 1}, pluck="parent", distinct=True)
	unpaid = frappe.db.exists("Purchase Invoice", {"name": ["in", bills or [""]], "outstanding_amount": [">", 0]})
	steps = ["Draft", "Approval", "Ordered"] + (["Shipment"] if ship else []) + ["Received", "Billed", "Paid"]
	if doc.docstatus == 0:
		cur = 1 if (_wf_state(doc) or "").startswith("Pending") else 0
	elif flt(doc.per_received) < 100:
		cur = steps.index("Shipment") if ship and ship.status not in ("Cleared", "Received at Warehouse") else steps.index("Received")
	elif flt(doc.per_billed) < 100:
		cur = steps.index("Billed")
	else:
		cur = len(steps) if not unpaid else steps.index("Paid")
	p["progress"] = progress(steps, cur)
	facts = []
	if ship:
		facts.append([_("Import shipment"), link("Import Shipment", ship.name)])
	if lc:
		facts.append([_("Letter of credit"), link("Letter of Credit", lc.name, lc.lc_number or lc.name)])
	facts += [[_("Goods receipt"), link("Purchase Receipt", r)] for r in receipts[:3]] + [[_("Supplier bill"), link("Purchase Invoice", b)] for b in bills[:3]]
	p["facts"] = facts
	p["sections"] = [
		section("Supplier", kv(("Supplier", link("Supplier", doc.supplier, doc.supplier_name)), ("Country", country), ("Contact person", _contact(doc.contact_person)),
			("Supplier address", _address(doc.supplier_address)), ("Supplier's confirmation", " · ".join(x for x in [doc.get("order_confirmation_no"), d(doc.get("order_confirmation_date"))] if x))),
			actions=[act("Edit details", route=["Form", "Purchase Order", doc.name])] if doc.docstatus == 0 and p["can_edit"] else []),
		section("Order", kv(("Order date", d(doc.transaction_date)), ("Expected", d(doc.schedule_date)), ("Payment terms", doc.payment_terms_template),
			("Incoterm", " · ".join(x for x in [doc.get("incoterm"), doc.get("named_place")] if x)), ("Receive into", doc.set_warehouse),
			("Currency & rate", f"{doc.currency} · 1 = {flt(doc.conversion_rate, 4):g} {ccy}" if foreign else ""),
			(_("Total in {0}").format(doc.currency), money(doc.rounded_total or doc.grand_total, doc.currency)),
			(_("Total in {0}").format(ccy) if foreign else "", money(doc.base_rounded_total or doc.base_grand_total, ccy) if foreign else ""),
			("% received", bar(doc.per_received)), ("% billed", bar(doc.per_billed)), ("Status", pill(_status(doc))))),
		section("Items", kind="table", cols=["#", "Item", "UOM", "Qty", "Rate", "Disc", "Net", "Received", "Pending"],
			rows=_items_rows(doc, lambda it: [flt(it.received_qty), flt(it.qty) - flt(it.received_qty)])),
		_totals(doc),
	]
	if ship:
		p["sections"].append(section("Import shipment", kv(("Shipment", link("Import Shipment", ship.name)), ("Status", pill(ship.status)), ("Mode", _(ship.mode or "")),
			("Route", " → ".join(x for x in [ship.port_of_loading, ship.port_of_discharge] if x)), ("ETA", d(ship.eta)), ("BL / AWB", ship.bl_awb),
			("Bill of entry", ship.bill_of_entry))))
	if lc:
		p["sections"].append(section("Letter of credit", kv(("LC", link("Letter of Credit", lc.name, lc.lc_number or lc.name)), ("Status", pill(lc.status)),
			("Amount", money(lc.amount, lc.currency)), ("Expiry", d(lc.expiry_date)))))
	if doc.get("payment_schedule"):
		p["sections"].append(section("Payment schedule", kind="table", cols=["Payment term", "Due date", "%", "Amount"],
			rows=[[r.payment_term or r.description or "", d(r.due_date), f"{flt(r.invoice_portion):g}%", money(r.payment_amount, doc.currency)] for r in doc.payment_schedule]))
	acts = [act("Purchase order", print_format="Hipersign Purchase Order")]
	if doc.docstatus == 0 and p["can_edit"]:
		acts.insert(0, act("Edit", kind="primary", route=["Form", "Purchase Order", doc.name]))
	if doc.docstatus == 1 and _status(doc) not in ("Closed", "Completed", "On Hold"):
		blocked = ship and ship.status not in ("Cleared", "Received at Warehouse")
		if flt(doc.per_received) < 100 and _can("Purchase Receipt"):
			acts.append(act("Receive goods", kind="default" if blocked else "primary", make="erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
				confirm=_("Shipment {0} is “{1}” — goods can be received only after customs clearance. Try anyway?").format(ship.name, _(ship.status)) if blocked else None))
		if flt(doc.per_billed) < 100 and _can("Purchase Invoice"):
			acts.append(act("Create supplier bill", kind="primary" if flt(doc.per_received) >= 100 else "default",
				make="erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice"))
		if not ship and foreign and frappe.db.table_exists("Import Shipment") and _can("Import Shipment"):
			acts.append(act("Book import shipment", action="book_import"))
	p["actions"] = acts
	return p


def supplier(doc):
	p = _base(doc, doc.supplier_name, _("Supplier"))
	p["status"] = pill("Disabled" if doc.disabled else (doc.get("hs_kyc_status") or "Active"), "red" if doc.disabled else
		{"Verified": "green", "Pending": "orange", "Expired": "red", "Blocked": "red"}.get(doc.get("hs_kyc_status"), "green"))
	company = _company()
	ccy = _company_currency(company)
	open_po = frappe.get_all("Purchase Order", filters={"supplier": doc.name, "docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive", "To Bill"]]},
		fields=["name", "transaction_date", "schedule_date", "grand_total", "currency", "per_received", "status"], order_by="transaction_date desc", limit=10) \
		if frappe.has_permission("Purchase Order") else []
	bills = frappe.get_all("Purchase Invoice", filters={"supplier": doc.name, "docstatus": 1, "outstanding_amount": ["!=", 0]},
		fields=["name", "posting_date", "due_date", "outstanding_amount", "currency", "conversion_rate", "bill_no"], order_by="due_date asc", limit=10) \
		if frappe.has_permission("Purchase Invoice") else []
	payable = sum(flt(b.outstanding_amount) * flt(b.conversion_rate or 1) for b in bills)
	p["facts"] = kv(("Country", doc.country), ("Currency", doc.default_currency), ("Payment terms", doc.payment_terms),
		("Incoterm", doc.get("hs_incoterm")), ("Lead time", f"{cint(doc.get('hs_lead_time_days'))} {_('days')}" if doc.get("hs_lead_time_days") else ""),
		("TRN", doc.tax_id), ("Payable", money(payable, ccy) if bills else ""), ("Open orders", len(open_po) or ""))
	p["sections"].append(section("Supplier", kv(("Type", _(doc.get("hs_supplier_kind") or doc.supplier_group or "")), ("Primary contact", _contact(doc.supplier_primary_contact)),
		("Address", _address(doc.supplier_primary_address)), ("Website", doc.website), ("Trade licence", doc.get("hs_trade_licence_no")),
		("Licence expiry", d(doc.get("hs_trade_licence_expiry"))))))
	if open_po:
		p["sections"].append(section("Open purchase orders", kind="table", cols=["PO", "Date", "Expected", "Value", "Received", "Status"],
			rows=[[link("Purchase Order", r.name), d(r.transaction_date), d(r.schedule_date), money(r.grand_total, r.currency), bar(r.per_received), pill(r.status)] for r in open_po]))
	if bills:
		p["sections"].append(section("Bills to pay", kind="table", cols=["Bill", "Supplier ref", "Due", "Outstanding"],
			rows=[[link("Purchase Invoice", b.name), b.bill_no or "", d(b.due_date), money(b.outstanding_amount, b.currency)] for b in bills]))
	acts = []
	if p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Supplier", doc.name]))
	if _can("Purchase Order"):
		acts.append(act("New purchase order", kind="primary", client="quick_doc", args={"doctype": "Purchase Order", "party": doc.name}))
	p["actions"] = acts
	return p


def _company():
	from hipersign_trading.utils import user_company

	return user_company()


# ---------------------------------------------------------------- imports, LCs and receipts (v1.6.0 step 7)
SHIP_STEPS = ["Booked", "Shipped", "In Transit", "Arrived at Port", "Under Customs Clearance", "Cleared", "Received at Warehouse"]
LC_STEPS = ["Applied", "Issued", "Documents Presented", "Accepted", "Paid"]


def _days(v):
	if not v:
		return ""
	n = date_diff(v, today())
	return _("in {0} days").format(n) if n > 0 else _("today") if n == 0 else _("{0} days ago").format(-n)


def _per_received(po):
	return flt(frappe.db.get_value("Purchase Order", po, "per_received"))


def import_shipment(doc):
	ccy = _company_currency(doc.company)
	suppliers = sorted({r.supplier for r in doc.purchase_orders if r.supplier})
	p = _base(doc, f"{doc.name} — {', '.join(suppliers)}" if suppliers else doc.name, _("Import shipment"))
	p["status"] = pill(doc.status)
	idx = SHIP_STEPS.index(doc.status) if doc.status in SHIP_STEPS else 0
	p["progress"] = progress(SHIP_STEPS, len(SHIP_STEPS) if doc.status == "Received at Warehouse" else idx)
	prs = doc.purchase_receipts() if doc.purchase_orders else []
	lcs = frappe.get_all("Letter of Credit", filters={"status": ["!=", "Cancelled"], "import_shipment": doc.name}, fields=["name", "lc_number"]) \
		if frappe.has_permission("Letter of Credit") else []
	late = bool(doc.eta) and getdate(doc.eta) < getdate(today()) and idx < SHIP_STEPS.index("Arrived at Port")
	eta = f"{d(doc.eta)} · {_days(doc.eta)}" if doc.eta and idx < SHIP_STEPS.index("Arrived at Port") else d(doc.eta)
	p["facts"] = kv(("Mode", _(doc.mode or "")), ("Route", " → ".join(x for x in [doc.port_of_loading, doc.port_of_discharge] if x)),
		("ETA", pill(eta, "red") if late else eta), ("Goods value", money(doc.goods_value, ccy)),
		("Landed charges", money(doc.total_charges, ccy) if doc.total_charges else ""))
	for l in lcs:
		p["facts"].append([_("Letter of credit"), link("Letter of Credit", l.name, l.lc_number or l.name)])
	p["facts"] += [[_("Goods receipt"), link("Purchase Receipt", r)] for r in prs[:3]]
	p["sections"] = [
		section("Transport", kv(("BL / AWB", doc.bl_awb), ("Vessel / flight", doc.vessel_flight), ("Shipping line", doc.shipping_line),
			("Forwarder", link("Supplier", doc.forwarder)), ("Containers", doc.containers or ""), ("Insurance policy", doc.insurance_policy),
			("ETD", d(doc.etd)), ("ETA", d(doc.eta)), ("Arrived", d(doc.arrived_on)), ("Cleared", d(doc.cleared_on)), ("Bill of entry", doc.bill_of_entry))),
		section("Purchase orders", kind="table", cols=["PO", "Supplier", "Value", _("In {0}").format(ccy), "Received"],
			rows=[[link("Purchase Order", r.purchase_order), r.supplier or "", money(r.grand_total, r.currency), money(r.base_grand_total, ccy),
				bar(_per_received(r.purchase_order))] for r in doc.purchase_orders]),
	]
	if doc.documents:
		got = sum(1 for x in doc.documents if x.received)
		p["sections"].append(section("Shipping documents", kind="table", cols=["Document", "Required", "Received", "Reference"],
			sub=_("{0} of {1} received").format(got, len(doc.documents)),
			rows=[[_(x.document_type), _("Yes") if x.required else "—", pill("Received", "green") if x.received else pill("Missing", "red" if x.required else "grey"),
				" · ".join(y for y in [x.reference_no, d(x.received_on)] if y)] for x in doc.documents]))
	if doc.charges:
		p["sections"].append(section("Landed charges", kind="table", cols=["Charge", "Provider", "Amount", "Bill"],
			rows=[[_(c.charge_type or ""), c.provider or "", money(c.amount, ccy), link("Purchase Invoice", c.purchase_invoice)] for c in doc.charges],
			total=money(doc.total_charges, ccy)))
	acts = []
	if p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Import Shipment", doc.name]))
		if idx < len(SHIP_STEPS) - 2:
			nxt = SHIP_STEPS[idx + 1]
			acts.append(act(_("Mark {0}").format(_(nxt)), kind="primary", action="ship_next", args={"status": nxt}))
	if doc.status in ("Cleared", "Received at Warehouse") and _can("Purchase Receipt"):
		for po in [r.purchase_order for r in doc.purchase_orders if _per_received(r.purchase_order) < 100][:2]:
			acts.append(act(_("Receive {0}").format(po), kind="primary", make="erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt", source=po))
	if doc.landed_cost_voucher:
		acts.append(act("Landed cost", route=["Form", "Landed Cost Voucher", doc.landed_cost_voucher]))
	elif prs and doc.charges and p["can_edit"]:
		acts.append(act("Create landed cost", action="ship_lcv"))
	p["actions"] = acts
	return p


def letter_of_credit(doc):
	ccy = _company_currency(doc.company)
	party = doc.party_name or doc.supplier or doc.customer
	p = _base(doc, " — ".join(x for x in [doc.lc_number or doc.name, party] if x), _("{0} letter of credit").format(_(doc.lc_type or "Import")))
	p["status"] = pill(doc.status)
	if doc.status in LC_STEPS:
		p["progress"] = progress(LC_STEPS, len(LC_STEPS) if doc.status == "Paid" else LC_STEPS.index(doc.status))
	left = date_diff(doc.expiry_date, today()) if doc.expiry_date else None
	expiry = d(doc.expiry_date)
	if left is not None and left <= 15 and doc.status not in ("Paid", "Cancelled", "Expired"):
		expiry = pill(f"{expiry} · {_days(doc.expiry_date)}", "red" if left < 0 else "orange")
	foreign = doc.currency and doc.currency != ccy
	p["facts"] = kv(("Amount", money(doc.amount, doc.currency)), (_("In {0}").format(ccy), money(doc.base_amount, ccy) if foreign and doc.base_amount else ""),
		("Issuing bank", doc.issuing_bank), ("Tenor", _(doc.tenor or "")), ("Expiry", expiry), ("Maturity", d(doc.maturity_date)))
	p["sections"] = [
		section("Parties", kv(("Supplier", link("Supplier", doc.supplier)), ("Customer", link("Customer", doc.customer)),
			("Purchase order", link("Purchase Order", doc.purchase_order)), ("Sales order", link("Sales Order", doc.sales_order)),
			("Import shipment", link("Import Shipment", doc.import_shipment)), ("Bank account", doc.bank_account))),
		section("Terms", kv(("LC number", doc.lc_number), ("Tolerance", f"±{flt(doc.tolerance_pct):g}%" if doc.tolerance_pct else ""),
			("Exchange rate", f"{flt(doc.exchange_rate, 4):g}" if foreign and doc.exchange_rate else ""), ("Issued", d(doc.issue_date)),
			("Latest shipment", d(doc.latest_shipment_date)), ("Expiry", d(doc.expiry_date)), ("Bank charges", money(doc.charges, ccy) if doc.charges else ""))),
		section("Documents & payment", kv(("Documents presented", d(doc.documents_presented_on)), ("Discrepancies", doc.discrepancies),
			("Accepted", d(doc.accepted_on)), ("Maturity", d(doc.maturity_date)), ("Paid", d(doc.paid_on)))),
		section("Cash margin", kv(("Margin", f"{flt(doc.margin_pct):g}% · {fmt_money(doc.margin_amount, currency=ccy)}" if doc.margin_amount else ""),
			("Margin entry", link("Journal Entry", doc.margin_entry)), ("Released by", link("Journal Entry", doc.margin_release_entry)))),
	]
	if doc.trust_receipt:
		p["sections"].append(section("Trust receipt loan", kv(("Amount", money(doc.tr_amount, ccy)), ("From", d(doc.tr_start)),
			("Days", doc.tr_days or ""), ("Rate", f"{flt(doc.tr_rate):g}%" if doc.tr_rate else ""), ("Due", d(doc.tr_due)),
			("Interest", money(doc.tr_interest, ccy) if doc.tr_interest else ""), ("Repaid", d(doc.tr_repaid_on)), ("Loan entry", link("Journal Entry", doc.tr_entry)))))
	acts = []
	if p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Letter of Credit", doc.name]))
		if doc.status in LC_STEPS[:-1]:
			nxt = LC_STEPS[LC_STEPS.index(doc.status) + 1]
			acts.append(act(_("Mark {0}").format(_(nxt)), kind="primary", action="lc_next", args={"status": nxt}))
		if flt(doc.margin_amount) > 0 and not doc.margin_entry:
			acts.append(act("Block margin", action="lc_margin"))
		if doc.margin_entry and not doc.margin_release_entry and doc.status in ("Paid", "Expired", "Cancelled"):
			acts.append(act("Release margin", action="lc_margin_release"))
		if doc.trust_receipt and not doc.tr_entry:
			acts.append(act("Book trust receipt", action="lc_tr"))
	p["actions"] = acts
	return p


def _receipt_items(doc):
	"""Rejected and batch / serial columns only when some line has them, so the table fits the panel."""
	rej = any(flt(it.rejected_qty) for it in doc.items)
	bs = any(it.batch_no or it.serial_no for it in doc.items)
	cols = ["#", "Item", "UOM", "Accepted"] + (["Rejected"] if rej else []) + ["Rate", "Amount"] + (["Batch / serial"] if bs else [])
	rows = []
	for i, it in enumerate(doc.items, 1):
		r = [i, link("Item", it.item_code, it.item_name), it.uom, flt(it.qty)] + ([flt(it.rejected_qty) or "—"] if rej else [])
		r += [money(it.rate, doc.currency), money(it.amount, doc.currency)] + ([(it.batch_no or it.serial_no or "").replace("\n", ", ")[:60]] if bs else [])
		rows.append(r)
	return section("Items", kind="table", cols=cols, rows=rows, total=money(doc.total, doc.currency))


def purchase_receipt(doc):
	p = _base(doc, f"{doc.name} — {doc.supplier_name}", _("Goods receipt"))
	pos = sorted({i.purchase_order for i in doc.items if i.purchase_order})
	ship = frappe.get_all("Import Shipment PO", filters={"purchase_order": ["in", pos], "parenttype": "Import Shipment"}, pluck="parent", limit=1) \
		if pos and frappe.db.table_exists("Import Shipment PO") else []
	billed = flt(doc.per_billed)
	lcv = frappe.get_all("Landed Cost Purchase Receipt", filters={"receipt_document": doc.name, "docstatus": 1}, pluck="parent", limit=1)
	steps = ["Draft", "Received"] + (["Landed cost"] if ship else []) + ["Billed"]
	if doc.docstatus == 0:
		cur = 0
	elif ship and not lcv:
		cur = steps.index("Landed cost")
	else:
		cur = steps.index("Billed") if billed < 100 else len(steps)
	p["progress"] = progress(steps, cur)
	rejected = sum(flt(i.rejected_qty) for i in doc.items)
	p["facts"] = kv(("Supplier", link("Supplier", doc.supplier, doc.supplier_name)), ("Received on", d(doc.posting_date)),
		("Warehouse", doc.set_warehouse or (doc.items[0].warehouse if doc.items else "")), ("Supplier delivery note", doc.get("supplier_delivery_note")),
		("Rejected qty", pill(f"{rejected:g}", "red") if rejected else ""), ("Value", money(doc.rounded_total or doc.grand_total, doc.currency)))
	p["facts"] += [[_("Purchase order"), link("Purchase Order", po)] for po in pos[:3]]
	if ship:
		p["facts"].append([_("Import shipment"), link("Import Shipment", ship[0])])
	if lcv:
		p["facts"].append([_("Landed cost"), link("Landed Cost Voucher", lcv[0])])
	p["sections"] = [
		_receipt_items(doc),
		section("Billing", kv(("% billed", bar(billed)), ("Status", pill(_status(doc))))),
	]
	acts = []
	if doc.docstatus == 0 and p["can_edit"]:
		acts.append(act("Edit", kind="primary", route=["Form", "Purchase Receipt", doc.name]))
	if doc.docstatus == 1 and billed < 100 and doc.status != "Closed" and _can("Purchase Invoice"):
		acts.append(act("Create supplier bill", kind="primary", make="erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice"))
	if doc.docstatus == 1 and not doc.is_return and _can("Purchase Receipt"):
		acts.append(act("Return to supplier", make="erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_return",
			confirm=_("Create a draft return to {0} for this receipt?").format(doc.supplier_name)))
	p["actions"] = acts
	return p


BUILDERS = {"Lead": lead, "Quotation": quotation, "Sales Order": sales_order, "Customer": customer, "Sales Invoice": sales_invoice,
	"Delivery Note": delivery_note, "Item": item, "Purchase Order": purchase_order, "Supplier": supplier,
	"Import Shipment": import_shipment, "Letter of Credit": letter_of_credit, "Purchase Receipt": purchase_receipt}


# ---------------------------------------------------------------- API
@frappe.whitelist()
def get_panel(doctype, name):
	if doctype not in BUILDERS:
		frappe.throw(_("No panel for {0}").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	p = BUILDERS[doctype](doc)
	p["sections"] = [s for s in p["sections"] if s and (s["kind"] != "kv" or s["rows"] or s["actions"])]
	return p


@frappe.whitelist(methods=["POST"])
def make(method, source_name):
	"""Run one of ERPNext's whitelisted "make" mappers named by a panel button and return the new draft."""
	if method not in MAKERS:
		frappe.throw(_("Not allowed"))
	fn = frappe.get_attr(method)
	doc = fn(source_name)
	return doc.as_dict() if hasattr(doc, "as_dict") else doc


MAKERS = {
	"erpnext.crm.doctype.lead.lead.make_quotation",
	"erpnext.selling.doctype.quotation.quotation.make_sales_order",
	"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
	"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
	"erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
	"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
	"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
	"hipersign_trading.api.panel.pay_sales_invoice",
	"hipersign_trading.api.panel.pay_purchase_invoice",
	"erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
	"erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_return",
}


def pay_sales_invoice(source_name):
	"""A draft receipt for the invoice's outstanding amount (the Finance page's Receive button)."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	return get_payment_entry("Sales Invoice", source_name)


def pay_purchase_invoice(source_name):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	return get_payment_entry("Purchase Invoice", source_name)


@frappe.whitelist(methods=["POST"])
def action(doctype, name, action, args=None):
	"""Server actions behind panel buttons."""
	args = frappe.parse_json(args) if isinstance(args, str) else (args or {})
	doc = frappe.get_doc(doctype, name)
	if action == "lead_stage" and doctype == "Lead":
		doc.check_permission("write")
		stage = args.get("stage")
		from hipersign_trading.api.crm import STAGES

		if stage not in list(STAGES) + ["Won", "Lost"]:
			frappe.throw(_("Unknown stage {0}").format(stage))
		doc.hs_pipeline_stage = stage
		if stage == "Lost":
			doc.hs_lost_reason = args.get("reason") or doc.get("hs_lost_reason")
		doc.save()
		doc.add_comment("Comment", _("Stage → {0}").format(_(stage)) + (f" — {args.get('note')}" if args.get("note") else ""))
		return {"message": _("{0} moved to {1}").format(doc.company_name or doc.name, _(stage))}
	if action == "quote_lost" and doctype == "Quotation":
		doc.check_permission("write")
		from erpnext.selling.doctype.quotation.quotation import Quotation  # noqa: F401

		reason = args.get("reason") or _("Other")
		if not frappe.db.exists("Quotation Lost Reason", reason):
			frappe.get_doc({"doctype": "Quotation Lost Reason", "order_lost_reason": reason}).insert(ignore_permissions=True)
		doc.declare_enquiry_lost([{"lost_reason": reason}], [], detailed_reason=args.get("note"))
		return {"message": _("{0} marked as lost").format(doc.name)}
	if action == "book_export" and doctype == "Sales Order":
		doc.check_permission("read")
		frappe.has_permission("Export Shipment", "create", throw=True)
		es = frappe.get_doc({"doctype": "Export Shipment", "company": doc.company, "sales_order": doc.name, "status": "Booked",
			"incoterm": doc.get("incoterm"), "named_place": doc.get("named_place"), "mode": doc.get("hs_shipment_mode")})
		es.insert()
		return {"message": _("Export shipment {0} booked").format(es.name), "route": ["Form", "Export Shipment", es.name]}
	if action == "book_import" and doctype == "Purchase Order":
		doc.check_permission("read")
		frappe.has_permission("Import Shipment", "create", throw=True)
		sh = frappe.get_doc({"doctype": "Import Shipment", "company": doc.company, "status": "Booked",
			"purchase_orders": [{"purchase_order": doc.name}]})
		sh.insert()
		return {"message": _("Import shipment {0} booked").format(sh.name), "route": ["Form", "Import Shipment", sh.name]}
	if action == "ship_next" and doctype == "Import Shipment":
		doc.check_permission("write")
		st = args.get("status")
		if st not in SHIP_STEPS or SHIP_STEPS.index(st) != SHIP_STEPS.index(doc.status) + 1:
			frappe.throw(_("{0} cannot move to {1}").format(doc.name, _(st or "")))
		doc.status = st
		doc.save()
		return {"message": _("{0} is now {1}").format(doc.name, _(st))}
	if action == "ship_lcv" and doctype == "Import Shipment":
		doc.check_permission("write")
		lcv = doc.make_landed_cost_voucher()
		return {"message": _("Landed cost voucher {0} created").format(lcv), "route": ["Form", "Landed Cost Voucher", lcv]}
	if action == "lc_next" and doctype == "Letter of Credit":
		doc.check_permission("write")
		st = args.get("status")
		if st not in LC_STEPS or doc.status not in LC_STEPS or LC_STEPS.index(st) != LC_STEPS.index(doc.status) + 1:
			frappe.throw(_("{0} cannot move to {1}").format(doc.lc_number or doc.name, _(st or "")))
		doc.status = st
		field = {"Documents Presented": "documents_presented_on", "Accepted": "accepted_on", "Paid": "paid_on", "Issued": "issue_date"}.get(st)
		if field and not doc.get(field):
			doc.set(field, today())
		doc.save()
		return {"message": _("{0} is now {1}").format(doc.lc_number or doc.name, _(st))}
	if action in ("lc_margin", "lc_margin_release", "lc_tr") and doctype == "Letter of Credit":
		je = {"lc_margin": doc.make_margin_entry, "lc_margin_release": doc.make_margin_release_entry, "lc_tr": doc.make_trust_receipt_entry}[action]()
		return {"message": _("Journal entry {0} created").format(je), "route": ["Form", "Journal Entry", je]}
	frappe.throw(_("Unknown action"))
