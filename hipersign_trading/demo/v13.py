"""v1.3 demo data: set-up (Enterprise group), external documents and exceptions, company compliance,
group consolidation, a short customer transfer settled with bank charges, a Wholesale price list,
form-mode defaults."""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

from hipersign_trading.demo import backdate, user_email


def v13_setup(c):
	from hipersign_trading.features import apply_effects, apply_pack

	s = apply_pack("Enterprise", "Group", save=False)
	s.setup_done = 1
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)
	apply_effects(frappe.get_single("Hipersign Settings"))


def _pdf(name):
	"""A small but valid one-page PDF (ERPNext checks uploaded PDFs) with the document's name on it."""
	text = name.replace("\\", "").replace("(", "").replace(")", "").encode("latin-1", "replace")
	stream = b"BT /F1 14 Tf 60 760 Td (Hipersign demo document: " + text + b") Tj ET"
	objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
		b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
		b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
	out, offsets = b"%PDF-1.4\n", []
	for i, o in enumerate(objs, 1):
		offsets.append(len(out))
		out += str(i).encode() + b" 0 obj\n" + o + b"\nendobj\n"
	xref = len(out)
	out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % x for x in offsets)
	out += b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
	return out


def _attach(doctype, docname, document_type, file_name):
	if frappe.db.exists("File", {"attached_to_doctype": doctype, "attached_to_name": docname, "hs_document_type": document_type}):
		return
	f = frappe.get_doc({"doctype": "File", "file_name": file_name, "attached_to_doctype": doctype, "attached_to_name": docname, "is_private": 1,
		"content": _pdf(file_name), "hs_document_type": document_type})
	f.insert(ignore_permissions=True)


def v13_documents(c):
	"""Typed documents on most records, a few missing (Document Centre), one exception pending and one used."""
	for so in frappe.get_all("Sales Order", filters={"docstatus": 1, "company": c.company}, fields=["name", "po_no", "customer"], order_by="creation asc"):
		if so.po_no and so.customer not in ("Gulf Projects",):
			_attach("Sales Order", so.name, "Customer LPO", f"LPO {so.po_no}.pdf")
	for pi in frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "company": c.company, "is_return": 0}, fields=["name", "bill_no"], order_by="creation asc"):
		_attach("Purchase Invoice", pi.name, "Supplier invoice", f"Supplier invoice {pi.bill_no or pi.name}.pdf")
	for po in frappe.get_all("Purchase Order", filters={"docstatus": 1, "company": c.company}, pluck="name", order_by="creation asc")[:-2]:
		_attach("Purchase Order", po, "Supplier order confirmation", f"Order confirmation {po}.pdf")
	for pr in frappe.get_all("Purchase Receipt", filters={"docstatus": 1, "company": c.company}, pluck="name", order_by="creation asc")[1:]:
		_attach("Purchase Receipt", pr, "Supplier delivery note", f"Supplier DN {pr}.pdf")
	for dn in frappe.get_all("Delivery Note", filters={"docstatus": 1, "company": c.company, "hs_delivery_status": "Delivered"}, pluck="name", order_by="creation asc")[1:]:
		_attach("Delivery Note", dn, "Signed delivery note", f"Signed DN {dn}.pdf")
	for lc in frappe.get_all("Letter of Credit", filters={"status": ["not in", ["Applied", "Cancelled"]]}, fields=["name", "lc_number"]):
		_attach("Letter of Credit", lc.name, "Bank's LC copy", f"LC {lc.lc_number or lc.name} MT700.pdf")
	for s_ in frappe.get_all("Import Shipment", filters={"status": ["in", ["Cleared", "Received at Warehouse"]]}, fields=["name", "bill_of_entry"]):
		_attach("Import Shipment", s_.name, "Bill of entry", f"BOE {s_.bill_of_entry or s_.name}.pdf")
	for s_ in frappe.get_all("Import Shipment", filters={"status": ["not in", ["Booked"]]}, fields=["name", "bl_awb"])[:-1]:
		_attach("Import Shipment", s_.name, "Bill of lading / AWB", f"BL {s_.bl_awb or s_.name}.pdf")
	# a big draft order without the customer's LPO: an exception is waiting for the Sales Manager
	draft = frappe.get_all("Sales Order", filters={"docstatus": 0, "company": c.company, "base_grand_total": [">=", 50000]}, pluck="name", limit=1)
	if not draft:
		from hipersign_trading.demo import make_so

		so = make_so(c, "Gulf Trading LLC", [("ITM-001", 45), ("ITM-004", 20)], 1, "GTL/PO/0919", submit=False)
		draft = [so.name]
	if draft and not frappe.db.exists("Document Waiver", {"reference_name": draft[0]}):
		frappe.get_doc({"doctype": "Document Waiver", "reference_doctype": "Sales Order", "reference_name": draft[0], "document_type": "Customer LPO",
			"reason": "Customer's procurement is issuing the LPO this week; they confirmed the order by email and need delivery on Thursday.",
			"due_date": add_days(today(), 5), "approver_role": "Sales Manager", "requested_by": user_email("sales")}).insert(ignore_permissions=True)


def v13_compliance(c):
	md, fin, hr = user_email("md"), user_email("fin"), user_email("hr")
	trn = frappe.get_cached_value("Company", c.company, "tax_id") or "100384927150003"
	cos = [c.company] + [x for x in frappe.get_all("Company", pluck="name") if x != c.company]
	plan = [
		# document type, days to expiry (None = no expiry), responsible, number, renewal status
		("Trade licence", 21, md, "DED-1048823", "In progress"),
		("Chamber of commerce membership", 140, fin, "DCCI-311902", ""),
		("Establishment card", -6, hr, "2/3/40418877", ""),
		("Civil defence certificate", 9, md, "CD-DXB-72215", "Submitted to authority"),
		("Tenancy contract (Ejari)", 75, fin, "EJ-2025-0918821", ""),
		("Customs code", 300, fin, "AE-1188034", ""),
		("VAT registration certificate", None, fin, trn, ""),
		("Corporate tax registration", None, fin, f"CT-{trn}", ""),
	]
	for typ, days_, who, no, ren in plan:
		if frappe.db.exists("Company Document", {"company": c.company, "document_type": typ}):
			continue
		exp = add_days(today(), days_) if days_ is not None else None
		frappe.get_doc({"doctype": "Company Document", "company": c.company, "document_type": typ, "document_number": no,
			"issue_date": add_days(exp, -365) if exp else add_days(today(), -500), "expiry_date": exp, "responsible_user": who, "renewal_status": ren or None}).insert(ignore_permissions=True)
	for co in cos[1:]:
		if frappe.get_cached_value("Company", co, "is_group"):
			continue
		country = frappe.get_cached_value("Company", co, "country")
		typ = "Trade licence" if country == "United Arab Emirates" else "Commercial registration (CR)" if country == "Saudi Arabia" else "Trade licence"
		if not frappe.db.exists("Company Document", {"company": co, "document_type": typ}):
			frappe.get_doc({"doctype": "Company Document", "company": co, "document_type": typ, "document_number": f"{frappe.get_cached_value('Company', co, 'abbr')}-LIC-2026",
				"issue_date": add_days(today(), -320), "expiry_date": add_days(today(), 45), "responsible_user": md}).insert(ignore_permissions=True)
	# statutory deadlines
	month_end = get_last_day(today())
	for title, cat, due, rep, who in [
		("VAT return (FTA) for last month", "VAT return", add_days(get_first_day(add_months(today(), 1)), 27), "Monthly", fin),
		("WPS salary file to the bank", "WPS salary file", add_days(get_first_day(add_months(today(), 1)), 2), "Monthly", hr),
		("Corporate tax return", "Corporate tax", getdate(f"{getdate(today()).year + 1}-09-30"), "Yearly", fin),
		("ESR / UBO register update", "ESR / UBO", add_days(today(), 2), "Yearly", md),
		("Audited accounts to the free zone", "Audit", add_days(month_end, 60), "Yearly", fin),
	]:
		if not frappe.db.exists("Company Deadline", {"company": c.company, "title": title, "status": "Open"}):
			frappe.get_doc({"doctype": "Company Deadline", "company": c.company, "title": title, "category": cat, "due_date": due, "repeat": rep,
				"responsible_user": who}).insert(ignore_permissions=True)
	from hipersign_trading.compliance import company_document_alerts, deadline_alerts

	frappe.flags.mute_emails = True
	company_document_alerts()
	deadline_alerts()


def v13_group(c):
	"""Group members for the companies on this site, synced so the consolidation report has figures."""
	from hipersign_trading.demo.data import GROUP
	from hipersign_trading.group import sync_member

	own = {name: pct for name, abbr, cur, country, pct, *_ in GROUP["companies"]}
	holding = GROUP["holding"][0]
	members = [(c.company, 100, 0)] + [(n, p, 0) for n, p in own.items()]
	if frappe.db.exists("Company", holding):
		members.append((holding, 100, 1))
	for name, pct, parent in members:
		if not frappe.db.exists("Company", name):
			continue
		if not frappe.db.exists("Hipersign Group Member", name):
			frappe.get_doc({"doctype": "Hipersign Group Member", "member_name": name, "company": name, "ownership_pct": pct, "is_parent": parent,
				"country": frappe.get_cached_value("Company", name, "country"), "currency": frappe.get_cached_value("Company", name, "default_currency")}).insert(ignore_permissions=True)
		sync_member(name, today())


def v13_bank_charges(c):
	"""A customer's transfer arrived AED 25 short — booked as bank charges, the invoice is paid in full."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	s = frappe.get_single("Hipersign Settings")
	acc = s.bank_charges_account
	if not acc or frappe.db.exists("Payment Entry Deduction", {"account": acc, "description": "Bank charges deducted from the customer's transfer"}):
		return
	si = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "company": c.company, "outstanding_amount": [">", 2000], "is_return": 0, "currency": "AED"},
		fields=["name", "outstanding_amount"], order_by="posting_date asc", limit=1)
	if not si:
		return
	out = flt(si[0].outstanding_amount)
	pe = get_payment_entry("Sales Invoice", si[0].name, party_amount=out - 25)
	pe.paid_amount = pe.received_amount = out - 25
	pe.references[0].allocated_amount = out
	pe.append("deductions", {"account": acc, "cost_center": frappe.get_cached_value("Company", c.company, "cost_center"), "amount": 25,
		"description": "Bank charges deducted from the customer's transfer"})
	pe.reference_no, pe.reference_date = "TT/BNK/55120", add_days(today(), -1)
	backdate(pe, add_days(today(), -1))
	pe.insert(ignore_permissions=True)
	pe.submit()


def v13_price_lists(c):
	"""A Wholesale price list (10% below standard selling) given to the wholesale customers."""
	std = c.get("selling_pl") or frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	if not frappe.db.exists("Price List", "Wholesale"):
		frappe.get_doc({"doctype": "Price List", "price_list_name": "Wholesale", "currency": "AED", "selling": 1, "enabled": 1}).insert(ignore_permissions=True)
	if not frappe.db.count("Item Price", {"price_list": "Wholesale"}):
		for ip in frappe.get_all("Item Price", filters={"price_list": std}, fields=["item_code", "price_list_rate"], order_by="item_code asc"):
			frappe.get_doc({"doctype": "Item Price", "price_list": "Wholesale", "item_code": ip.item_code, "price_list_rate": flt(ip.price_list_rate * 0.9, 2)}).insert(ignore_permissions=True)
	for cust in frappe.get_all("Customer", filters={"customer_group": "Wholesale", "is_internal_customer": 0}, pluck="name"):
		frappe.db.set_value("Customer", cust, "default_price_list", "Wholesale")


def v13_lc_margins(c):
	"""The cash margin the bank blocked on each issued LC; released on the one already paid."""
	for name in frappe.get_all("Letter of Credit", filters={"status": ["not in", ["Applied", "Cancelled"]], "margin_amount": [">", 0], "company": c.company},
			pluck="name", order_by="creation asc"):
		lc = frappe.get_doc("Letter of Credit", name)
		if not lc.margin_entry:
			lc.flags.ignore_permissions = True
			je = frappe.get_doc("Journal Entry", lc.make_margin_entry())
			je.posting_date = lc.issue_date or je.posting_date
			je.save(ignore_permissions=True)
			je.submit()
			lc.reload()
		if lc.status in ("Paid", "Expired") and not lc.margin_release_entry:
			je = frappe.get_doc("Journal Entry", lc.make_margin_release_entry())
			je.posting_date = lc.paid_on or je.posting_date
			je.save(ignore_permissions=True)
			je.submit()


def v13_form_modes(c):
	s = frappe.get_single("Hipersign Settings")
	if s.form_modes:
		return
	for dt, role, mode in [("Quotation", "Sales User", "Quick"), ("Sales Order", "Sales User", "Quick"), ("Payment Entry", "Accounts User", "Quick"),
		("Purchase Order", "Purchase User", "Standard")]:
		s.append("form_modes", {"document_type": dt, "role": role, "mode": mode})
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)


STEPS = [v13_setup, v13_price_lists, v13_documents, v13_compliance, v13_group, v13_bank_charges, v13_lc_margins, v13_form_modes]
