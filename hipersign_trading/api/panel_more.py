"""v1.7.0: record panels for the rest of the prototype's drawers — export shipment, payment, journal, purchase bill /
debit note, employee, payroll run, expense claim, employee advance, leave, bank guarantee, fixed asset, purchase request,
RFQ, cheque, warranty claim, pick list, delivery trip, stock entry, company document and deadline, tax return.

Same shape as api/panel.py (the builders there are reused); registered into panel.BUILDERS at import.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today

from hipersign_trading.api.panel import _base, _can, _company_currency, _contact, _items_rows, _status, act, bar, d, kv, link, money, pill, progress, section


def _edit(p, doc, kind="default"):
	if p["can_edit"] and doc.docstatus == 0:
		return [act("Edit", kind=kind, route=["Form", doc.doctype, doc.name])]
	return []


def _full(doc):
	return act("Open full form", route=["Form", doc.doctype, doc.name])


def _submit(p, doc, label="Submit"):
	if doc.docstatus == 0 and frappe.has_permission(doc.doctype, "submit", doc) and not doc.get("workflow_state"):
		return [act(label, kind="primary", action="hs_submit", confirm=_("Submit {0}? It cannot be edited afterwards.").format(doc.name))]
	return []


# ---------------------------------------------------------------- Export shipment
EXP_STEPS = ["Booked", "Packed", "Export Declaration", "Customs Cleared", "Shipped", "Delivered", "Documents Complete"]


def export_shipment(doc):
	p = _base(doc, f"{doc.name} · " + _("{0} shipment").format(_(doc.mode or "Export")), doc.customer_name or doc.customer)
	p["status"] = pill(doc.status, "green" if doc.status == "Documents Complete" else "blue")
	if doc.status in EXP_STEPS:
		p["progress"] = progress(["Booked", "Packed", "Declaration", "Cleared", "Shipped", "Delivered", "Documents"],
			len(EXP_STEPS) if doc.status == "Documents Complete" else EXP_STEPS.index(doc.status))
	ccy = _company_currency(doc.company)
	so = frappe.db.get_value("Sales Order", doc.sales_order, ["grand_total", "currency"], as_dict=True) if doc.sales_order else None
	p["facts"] = kv(("Order", link("Sales Order", doc.sales_order)), ("Value", money(so.grand_total, so.currency) if so else ""), ("Incoterm", " ".join(x for x in [doc.incoterm, doc.named_place] if x)),
		("Route", " → ".join(x for x in [doc.port_of_loading, doc.destination] if x)), ("ETD", d(doc.etd)), ("ETA", d(doc.eta)))
	req = [x for x in doc.documents if x.required]
	got = [x for x in req if x.received]
	p["sections"] = [
		section("Shipment", kv(("Forwarder", doc.forwarder), ("BL / AWB / CMR", doc.bl_awb_cmr), ("Export declaration", doc.declaration_no), ("Certificate of origin", doc.coo_no),
			("Shipped", d(doc.shipped_on)), ("Delivered", d(doc.delivered_on)), ("Delivery note", link("Delivery Note", doc.delivery_note)), ("Invoice", link("Sales Invoice", doc.sales_invoice)))),
		section("Export documents", kind="table", sub=_("{0} of {1} required received").format(len(got), len(req)), cols=["Document", "Required", "Reference", "Received"],
			rows=[[_(x.document_type), _("Yes") if x.required else _("No"), x.reference_no or "—", pill(d(x.received_on) or _("Received"), "green") if x.received else pill("Pending", "orange")]
				for x in doc.documents]),
		section("Proof of export (0% VAT)", kv(("Due by", d(doc.proof_due_on)), ("Received", pill(d(doc.proof_of_export_on), "green") if doc.proof_of_export_on else pill("Pending", "red")))),
	]
	if doc.charges:
		p["sections"].append(section("Export charges", kind="table", cols=["Charge", "Supplier", "Amount"],
			rows=[[_(c.charge_type or ""), c.get("supplier") or "—", money(c.get("base_amount") or c.amount, ccy)] for c in doc.charges], total=money(doc.total_charges, ccy)))
	if flt(doc.net_sales):
		p["sections"].append(section("Margin", kv(("Net sales", money(doc.net_sales, ccy)), ("Landed cost of goods", money(doc.cost_of_goods, ccy)),
			("Export charges", money(doc.total_charges, ccy)), ("Gross profit", money(doc.gross_profit, ccy)), ("Margin", f"{flt(doc.margin_pct):.1f}%"))))
	if doc.re_export_of:
		p["sections"].append(section("Re-export", kv(("Of import", link("Import Shipment", doc.re_export_of)), ("Duty refund estimate", money(doc.duty_refund_estimate, ccy)),
			("Refund status", _(doc.duty_refund_status or "Not claimed")))))
	acts = []
	if p["can_edit"]:
		acts.append(act("Edit", route=["Form", "Export Shipment", doc.name]))
		if not doc.delivery_note and doc.sales_order:
			acts.append(act("Pack — create delivery note", kind="primary", action="hs_docmethod", args={"method": "make_delivery_note"}))
		elif doc.delivery_note and not doc.sales_invoice:
			acts.append(act("Create export invoice", action="hs_docmethod", args={"method": "make_sales_invoice"}))
		if doc.status != "Documents Complete":
			nxt = EXP_STEPS[EXP_STEPS.index(doc.status) + 1] if doc.status in EXP_STEPS else None
			if nxt:
				acts.append(act(_("Mark {0}").format(_(nxt)), kind="primary" if doc.delivery_note else "default", action="hs_docmethod", args={"method": "advance"}))
	p["actions"] = acts
	return p


# ---------------------------------------------------------------- Payment, journal, purchase bill
def payment_entry(doc):
	recv = doc.payment_type == "Receive"
	p = _base(doc, f"{doc.name} — {doc.party_name or doc.party or ''}", _("Receipt") if recv else _("Payment") if doc.payment_type == "Pay" else _("Internal transfer"))
	cur = doc.paid_from_account_currency if recv else doc.paid_to_account_currency
	p["facts"] = kv(("Amount", money(doc.received_amount if recv else doc.paid_amount, doc.paid_to_account_currency if recv else doc.paid_from_account_currency)),
		("Date", d(doc.posting_date)), ("Mode", doc.mode_of_payment), ("Reference", " · ".join(x for x in [doc.reference_no, d(doc.reference_date)] if x)),
		("Account", doc.paid_to if recv else doc.paid_from), ("Unallocated", money(doc.unallocated_amount, cur) if flt(doc.unallocated_amount) else ""))
	p["sections"] = [
		section("Party", kv(("Party", link(doc.party_type, doc.party, doc.party_name) if doc.party_type in ("Customer", "Supplier", "Employee") else doc.party), ("Party type", _(doc.party_type or "")),
			("Contact", _contact(doc.get("contact_person"))), ("Remarks", (doc.remarks or "")[:200]))),
		section("Allocated to", kind="table", cols=["Document", "Due", "Total", "Allocated"],
			rows=[[link(r.reference_doctype, r.reference_name), d(r.due_date), money(r.total_amount, cur), money(r.allocated_amount, cur)] for r in doc.references]),
	]
	if doc.deductions:
		p["sections"].append(section("Deductions & charges", kind="table", cols=["Account", "Amount"], rows=[[r.account, money(r.amount)] for r in doc.deductions]))
	p["actions"] = _edit(p, doc) + _submit(p, doc) + [act("Receipt", print_format="Standard")] if doc.docstatus == 1 else _edit(p, doc) + _submit(p, doc)
	return p


def journal_entry(doc):
	ccy = _company_currency(doc.company)
	p = _base(doc, f"{doc.name} — {doc.title or _(doc.voucher_type)}", _(doc.voucher_type))
	p["facts"] = kv(("Date", d(doc.posting_date)), ("Total", money(doc.total_debit, ccy)), ("Reference", doc.cheque_no), ("Balanced", pill("Yes", "green") if abs(flt(doc.difference)) < 0.01 else pill(_("Out by {0}").format(doc.difference), "red")))
	p["sections"] = [
		section("Lines", kind="table", cols=["Account", "Party", "Cost centre", "Debit", "Credit"],
			rows=[[r.account, link(r.party_type, r.party) if r.party_type and r.party else "—", r.cost_center or "—", money(r.debit_in_account_currency, r.account_currency) if flt(r.debit) else "—",
				money(r.credit_in_account_currency, r.account_currency) if flt(r.credit) else "—"] for r in doc.accounts]),
		section("Memo", kv(("Remark", (doc.user_remark or doc.remark or "")[:300]), ("Status", pill(_status(doc))))),
	]
	p["actions"] = _edit(p, doc) + _submit(p, doc, "Post")
	return p


def purchase_invoice(doc):
	ret = bool(doc.is_return)
	p = _base(doc, f"{doc.name} — {doc.supplier_name}", _("Debit note") if ret else _("Supplier bill"))
	pos = sorted({i.purchase_order for i in doc.items if i.purchase_order})
	prs = sorted({i.purchase_receipt for i in doc.items if i.purchase_receipt})
	p["facts"] = kv(("Supplier", link("Supplier", doc.supplier, doc.supplier_name)), ("Bill no.", " · ".join(x for x in [doc.bill_no, d(doc.bill_date)] if x)),
		("Due", d(doc.due_date)), ("Total", money(doc.rounded_total or doc.grand_total, doc.currency)), ("Outstanding", money(doc.outstanding_amount, doc.currency) if doc.docstatus == 1 else ""))
	p["sections"] = [
		section("Bill", kv(("Posting date", d(doc.posting_date)), ("Purchase orders", ", ".join(pos)), ("Goods receipts", ", ".join(prs)),
			("Against bill", link("Purchase Invoice", doc.return_against) if ret else ""), ("Currency", doc.currency), ("Status", pill(_status(doc))))),
		section("Items", kind="table", cols=["#", "Item", "UOM", "Qty", "Rate", "Disc", "Net"], rows=_items_rows(doc)),
		section("Totals", kv(("Net total", money(doc.net_total, doc.currency)), ("VAT", money(doc.total_taxes_and_charges, doc.currency)),
			("Grand total", money(doc.rounded_total or doc.grand_total, doc.currency)))),
	]
	acts = _edit(p, doc)
	if doc.docstatus == 1 and flt(doc.outstanding_amount) > 0 and not ret and _can("Payment Entry"):
		acts.append(act("Pay supplier", kind="primary", make="hipersign_trading.api.panel.pay_purchase_invoice"))
	if doc.docstatus == 1 and not ret and _can("Purchase Invoice"):
		acts.append(act("Return / debit note", make="erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_debit_note",
			confirm=_("Create a draft debit note against {0}?").format(doc.name)))
	p["actions"] = acts
	return p


# ---------------------------------------------------------------- People
def employee(doc):
	p = _base(doc, doc.employee_name, " · ".join(x for x in [doc.designation, (doc.department or "").rsplit(" - ", 1)[0], doc.name] if x))
	p["status"] = pill(doc.status, "green" if doc.status == "Active" else "grey")
	t = getdate(today())
	years = date_diff(t, doc.date_of_joining) / 365.25 if doc.date_of_joining else 0
	base = frappe.db.get_value("Salary Structure Assignment", {"employee": doc.name, "docstatus": 1}, "base", order_by="from_date desc") if frappe.db.table_exists("Salary Structure Assignment") else 0
	basic = flt(doc.get("hs_basic_salary")) or flt(base) * 0.6
	grat = 0 if years < 1 else basic / 30 * (21 * min(years, 5) + 30 * max(0, years - 5))
	ccy = _company_currency(doc.company)
	p["facts"] = kv(("Joined", f"{d(doc.date_of_joining)} · {years:.1f} " + _("yrs")), ("Gross / month", money(base, ccy) if base else ""), ("Mobile", doc.cell_number),
		("Email", doc.company_email or doc.personal_email), ("Reports to", link("Employee", doc.reports_to)), ("Leave approver", doc.get("leave_approver")))

	def exp(v):
		if not v:
			return ""
		left = date_diff(v, t)
		return pill(f"{d(v)} · " + (_("expired") if left < 0 else _("{0} days").format(left)), "red" if left < 0 else "orange") if left <= 60 else d(v)

	p["sections"] = [
		section("Salary", kv(("Basic", money(doc.get("hs_basic_salary"), ccy) if doc.get("hs_basic_salary") else ""), ("Housing", money(doc.get("hs_housing_allowance"), ccy) if doc.get("hs_housing_allowance") else ""),
			("Transport", money(doc.get("hs_transport_allowance"), ccy) if doc.get("hs_transport_allowance") else ""), ("Gross", money(base, ccy) if base else ""),
			("Bank / WPS", " · ".join(x for x in [doc.get("bank_name"), doc.get("hs_wps_routing_code")] if x)))),
		section("Documents", kv(("Visa", exp(doc.get("hs_visa_expiry"))), ("Emirates ID", " · ".join(x for x in [doc.get("hs_emirates_id")] if x)), ("Emirates ID expiry", exp(doc.get("hs_emirates_id_expiry"))),
			("Labour card", exp(doc.get("hs_labour_card_expiry"))), ("Passport", " · ".join(x for x in [doc.passport_number] if x)), ("Passport expiry", exp(doc.valid_upto)))),
		section("End-of-service gratuity", kv(("Service", f"{years:.1f} " + _("years")), ("Basic for gratuity", money(basic, ccy)), ("Accrued gratuity", money(grat, ccy)),
			("Rule", _("21 days' basic per year for the first 5 years, 30 days after")))),
	]
	leaves = frappe.get_all("Leave Application", filters={"employee": doc.name, "docstatus": ["<", 2]}, fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
		order_by="from_date desc", limit=8) if frappe.db.table_exists("Leave Application") else []
	if leaves:
		p["sections"].append(section("Leave history", kind="table", cols=["Request", "Type", "From", "To", "Days", "Status"],
			rows=[[link("Leave Application", x.name), _(x.leave_type), d(x.from_date), d(x.to_date), flt(x.total_leave_days), pill(x.status)] for x in leaves]))
	acts = [act("Edit", route=["Form", "Employee", doc.name])] if p["can_edit"] else []
	slip = frappe.db.get_value("Salary Slip", {"employee": doc.name, "docstatus": 1}, "name", order_by="start_date desc") if frappe.db.table_exists("Salary Slip") else None
	if slip:
		acts.append(act("Last payslip", route=["Form", "Salary Slip", slip]))
	if _can("Leave Application"):
		acts.append(act("Leave request", kind="primary", route=["Form", "Leave Application", "new"], options={"employee": doc.name}))
	p["actions"] = acts
	return p


def payroll_entry(doc):
	ccy = _company_currency(doc.company)
	p = _base(doc, f"{doc.name} — " + _("payroll {0}").format(frappe.utils.formatdate(doc.start_date, "MMM yyyy")), doc.company)
	slips = frappe.get_all("Salary Slip", filters={"payroll_entry": doc.name, "docstatus": ["<", 2]}, fields=["name", "employee_name", "gross_pay", "total_deduction", "net_pay", "docstatus"],
		order_by="employee_name asc")
	p["facts"] = kv(("Period", f"{d(doc.start_date)} – {d(doc.end_date)}"), ("Employees", len(slips)), ("Gross", money(sum(flt(s.gross_pay) for s in slips), ccy)),
		("Net (WPS)", money(sum(flt(s.net_pay) for s in slips), ccy)), ("Posting date", d(doc.posting_date)))
	p["sections"] = [section("Lines", kind="table", cols=["Employee", "Gross", "Deductions", "Net", "Slip"],
		rows=[[s.employee_name, money(s.gross_pay, ccy), money(s.total_deduction, ccy), money(s.net_pay, ccy), link("Salary Slip", s.name)] for s in slips],
		total=money(sum(flt(s.net_pay) for s in slips), ccy))]
	acts = _edit(p, doc)
	if doc.docstatus == 1:
		acts.append(act("WPS salary file (SIF)", kind="primary", url=f"/api/method/hipersign_trading.api.wps.download_sif?payroll_entry={frappe.utils.quote(doc.name)}"))
	p["actions"] = acts + _submit(p, doc, "Submit for approval")
	return p


def expense_claim(doc):
	ccy = _company_currency(doc.company)
	p = _base(doc, f"{doc.name} — " + _("expense claim"), doc.employee_name)
	st = "Paid" if doc.status == "Paid" else doc.approval_status if doc.docstatus == 0 else doc.status
	p["status"] = pill(st)
	p["progress"] = progress(["Submitted", "Approved", "Paid"], 3 if doc.status == "Paid" else 2 if doc.docstatus == 1 else 0 if doc.approval_status != "Approved" else 1)
	vat = sum(flt(t.tax_amount) for t in doc.get("taxes") or [])
	p["facts"] = kv(("Employee", link("Employee", doc.employee, doc.employee_name)), ("Date", d(doc.posting_date)), ("Claimed", money(doc.total_claimed_amount, ccy)),
		("Approver", frappe.utils.get_fullname(doc.expense_approver) if doc.expense_approver else ""), ("Project / cost centre", doc.get("cost_center")))
	p["sections"] = [section("Expenses", kind="table", sub=_("VAT recovered {0}").format(frappe.utils.fmt_money(vat, currency=ccy)) if vat else None,
		cols=["Date", "Type", "Description", "Amount"], rows=[[d(e.expense_date), _(e.expense_type), (e.description or "")[:60], money(e.amount, ccy)] for e in doc.expenses],
		total=money(doc.total_claimed_amount, ccy))]
	acts = _edit(p, doc)
	if doc.docstatus == 0 and frappe.has_permission("Expense Claim", "submit", doc):
		acts += [act("Reject", action="hs_claim", args={"decision": "Rejected"}), act("Approve", kind="primary", action="hs_claim", args={"decision": "Approved"},
			confirm=_("Approve and submit {0}?").format(doc.name))]
	if doc.docstatus == 1 and doc.status != "Paid" and _can("Payment Entry"):
		acts.append(act("Pay employee", kind="primary", make="hipersign_trading.api.panel_more.pay_expense_claim"))
	p["actions"] = acts
	return p


def employee_advance(doc):
	ccy = _company_currency(doc.company)
	p = _base(doc, f"{doc.name} — " + _("employee advance"), doc.employee_name)
	p["facts"] = kv(("Employee", link("Employee", doc.employee, doc.employee_name)), ("Purpose", doc.purpose), ("Amount", money(doc.advance_amount, ccy)),
		("Paid", money(doc.paid_amount, ccy)), ("Settled by claims", money(doc.claimed_amount, ccy)), ("Returned", money(doc.return_amount, ccy)))
	p["actions"] = _edit(p, doc) + _submit(p, doc, "Approve")
	return p


def leave_application(doc):
	p = _base(doc, f"{doc.name} — {doc.employee_name}", _(doc.leave_type))
	p["status"] = pill(doc.status)
	p["facts"] = kv(("Employee", link("Employee", doc.employee, doc.employee_name)), ("From", d(doc.from_date)), ("To", d(doc.to_date)), ("Days", flt(doc.total_leave_days)),
		("Balance before", flt(doc.leave_balance) if doc.get("leave_balance") is not None else ""), ("Reason", doc.description), ("Approver", frappe.utils.get_fullname(doc.leave_approver) if doc.leave_approver else ""))
	acts = _edit(p, doc)
	if doc.docstatus == 0 and doc.status == "Open" and frappe.has_permission("Leave Application", "submit", doc):
		acts += [act("Reject", action="hs_leave", args={"decision": "Rejected"}), act("Approve", kind="primary", action="hs_leave", args={"decision": "Approved"})]
	p["actions"] = acts
	return p


# ---------------------------------------------------------------- Finance & assets
def bank_guarantee(doc):
	p = _base(doc, f"{doc.name} — " + (doc.bank_guarantee_number or _("bank guarantee")), _("{0} guarantee").format(_(doc.bg_type or "")))
	left = date_diff(doc.end_date, today()) if doc.end_date else None
	p["facts"] = kv(("Amount", money(doc.amount)), ("Bank", doc.bank), ("Beneficiary", doc.customer or doc.supplier), ("Valid from", d(doc.start_date)),
		("Valid until", pill(d(doc.end_date) + (" · " + _("expired") if left < 0 else f" · {left} " + _("days")), "red" if left < 0 else "orange") if left is not None and left <= 30 else d(doc.end_date)),
		("Margin", money(doc.margin_money) if doc.get("margin_money") else ""))
	p["sections"] = [section("Details", kv(("Reference", f"{doc.reference_doctype or ''} {doc.reference_docname or ''}".strip()), ("Project", doc.get("project")),
		("Charges", money(doc.charges) if doc.get("charges") else ""), ("Fixed deposit", doc.get("fixed_deposit_number")), ("Notes", (doc.get("more_information") or "")[:300])))]
	p["actions"] = _edit(p, doc) + _submit(p, doc)
	return p


def asset(doc):
	ccy = _company_currency(doc.company)
	p = _base(doc, doc.asset_name + (f" · {doc.hs_plate_no}" if doc.get("hs_plate_no") else ""), f"{doc.name} · {_(doc.asset_category or '')}")
	t = getdate(today())
	cust = frappe.db.get_value("Employee", doc.custodian, "employee_name") if doc.custodian else ""
	p["facts"] = kv(("Location", doc.location), ("Custodian", cust), ("Purchased", d(doc.purchase_date)), ("Cost", money(doc.net_purchase_amount or doc.gross_purchase_amount, ccy)),
		("Net book value", money(doc.value_after_depreciation, ccy)), ("Status", pill(doc.status)))

	def due(v):
		if not v:
			return ""
		left = date_diff(v, t)
		return pill(f"{d(v)} · " + (_("overdue") if left < 0 else _("{0} days").format(left)), "red" if left < 0 else "orange") if left <= 30 else d(v)

	p["sections"] = [section("Maintenance", kv(("Next service", due(doc.get("hs_next_service"))), ("Registration (Mulkiya)", due(doc.get("hs_registration_expiry"))),
		("Insurance until", due(doc.get("insurance_end_date"))), ("Insurer", doc.get("insurer")), ("Policy", doc.get("policy_number"))))]
	sched = frappe.db.sql("""select ds.schedule_date, ds.depreciation_amount, ds.accumulated_depreciation_amount, ds.journal_entry from `tabDepreciation Schedule` ds
		join `tabAsset Depreciation Schedule` ads on ads.name = ds.parent where ads.asset = %s and ads.docstatus = 1 order by ds.schedule_date""", doc.name, as_dict=True) \
		if frappe.db.table_exists("Depreciation Schedule") else []
	if sched:
		near = [s for s in sched if abs(date_diff(s.schedule_date, t)) <= 100][:6] or sched[:6]
		p["sections"].append(section("Depreciation schedule", kind="table", sub=_("{0} of {1} months posted").format(len([s for s in sched if s.journal_entry]), len(sched)),
			cols=["Month", "Depreciation", "Accumulated", "Entry"], rows=[[d(s.schedule_date), money(s.depreciation_amount, ccy), money(s.accumulated_depreciation_amount, ccy),
				link("Journal Entry", s.journal_entry) if s.journal_entry else pill("Planned", "grey")] for s in near]))
	moves = frappe.db.sql("""select am.name, am.transaction_date, am.purpose, ami.target_location, ami.to_employee from `tabAsset Movement` am join `tabAsset Movement Item` ami on ami.parent = am.name
		where ami.asset = %s and am.docstatus = 1 order by am.transaction_date desc limit 5""", doc.name, as_dict=True) if frappe.db.table_exists("Asset Movement") else []
	if moves:
		p["sections"].append(section("Movements", kind="table", cols=["Date", "Purpose", "To"], rows=[[d(m.transaction_date), _(m.purpose), m.target_location or m.to_employee or ""] for m in moves]))
	acts = [act("Edit", route=["Form", "Asset", doc.name])] if p["can_edit"] else []
	if doc.docstatus == 1:
		if _can("Asset Movement"):
			acts.append(act("Transfer", route=["Form", "Asset Movement", "new"], options={"purpose": "Transfer", "company": doc.company}))
		if _can("Asset Repair"):
			acts.append(act("Record service", kind="primary", route=["Form", "Asset Repair", "new"], options={"asset": doc.name, "company": doc.company}))
	p["actions"] = acts + _submit(p, doc)
	return p


def post_dated_cheque(doc):
	ccy = _company_currency(doc.company)
	recv = doc.direction == "Received"
	p = _base(doc, f"{doc.name} — " + (_("cheque received from {0}") if recv else _("cheque issued to {0}")).format(doc.party_name or doc.party), _("Post-dated cheque"))
	p["status"] = pill(doc.status, {"In Hand": "blue", "Deposited": "violet", "Cleared": "green", "Bounced": "red", "Issued": "blue"}.get(doc.status))
	steps = ["In Hand", "Deposited", "Cleared"] if recv else ["Issued", "Cleared"]
	if doc.status in steps:
		p["progress"] = progress(steps, len(steps) if doc.status == "Cleared" else steps.index(doc.status))
	p["facts"] = kv(("Cheque no.", doc.cheque_no), ("Cheque date", d(doc.cheque_date)), ("Amount", money(doc.amount, ccy)), ("Drawn on", doc.drawn_on), ("Bank account", doc.bank_account),
		("Against", link(doc.reference_doctype, doc.reference_name) if doc.reference_doctype and doc.reference_name else ""))
	p["sections"] = [section("Dates & entries", kv(("Received", d(doc.received_on)), ("Deposited", d(doc.deposited_on)), ("Cleared", d(doc.cleared_on)), ("Bounced", d(doc.bounced_on)),
		("Payment", link("Payment Entry", doc.payment_entry)), ("Receipt entry", link("Journal Entry", doc.receipt_entry)), ("Clearing entry", link("Journal Entry", doc.clearing_entry)),
		("Remarks", doc.remarks)))]
	acts = [act("Edit", route=["Form", "Post Dated Cheque", doc.name])] if p["can_edit"] else []
	if p["can_edit"] and recv and doc.status == "In Hand":
		acts.append(act("Deposit", kind="primary", action="hs_docmethod", args={"method": "deposit"}))
	if p["can_edit"] and doc.status in ("Deposited", "Issued"):
		acts.append(act("Mark cleared", kind="primary", action="hs_docmethod", args={"method": "clear"}))
	p["actions"] = acts
	return p


def tax_return(doc):
	ccy = _company_currency(doc.company)
	p = _base(doc, f"{doc.name} — {doc.title or _(doc.tax_type)}", doc.company)
	p["status"] = pill(doc.status)
	steps = ["Prepared", "Pending Finance Manager", "Approved", "Submitted", "Paid"]
	if doc.status in steps:
		p["progress"] = progress(["Draft", "Finance review", "Approved", "Filed", "Paid"], len(steps) if doc.status == "Paid" else steps.index(doc.status))
	p["facts"] = kv(("Period", f"{d(doc.period_from)} – {d(doc.period_to)}"), ("Due", d(doc.due_date)), ("EmaraTax reference", doc.emaratax_reference), ("Paid", d(doc.paid_on)))
	if doc.tax_type == "VAT 201":
		p["sections"] = [section("VAT 201", kv(("Standard-rated sales", money(doc.standard_rated_sales, ccy)), ("Output VAT", money(doc.output_vat, ccy)),
			("Zero-rated sales", money(doc.zero_rated_sales, ccy)), ("Exempt sales", money(doc.exempt_sales, ccy)), ("Reverse charge VAT", money(doc.reverse_charge_vat, ccy)),
			("Standard-rated expenses", money(doc.standard_rated_expenses, ccy)), ("Input VAT", money(doc.input_vat, ccy)), ("Net VAT payable", money(doc.net_vat, ccy))))]
	else:
		p["sections"] = [section("Corporate tax", kv(("Accounting profit", money(doc.accounting_profit, ccy)), ("Adjustments", money(doc.adjustments, ccy)),
			("Taxable income", money(doc.taxable_income, ccy)), ("Small business relief", _("Yes") if doc.small_business_relief else _("No")),
			("Threshold", money(doc.ct_threshold, ccy)), ("Tax payable", money(doc.tax_payable, ccy))))]
	acts = [act("Open full form", kind="primary" if doc.status in ("Prepared", "Approved", "Submitted") else "default", route=["Form", "Tax Return", doc.name])]
	p["actions"] = acts
	return p


# ---------------------------------------------------------------- Buying & stock
def material_request(doc):
	p = _base(doc, f"{doc.name} — " + _("purchase request") if doc.material_request_type == "Purchase" else f"{doc.name} — " + _(doc.material_request_type), frappe.utils.get_fullname(doc.owner))
	p["facts"] = kv(("Requested", d(doc.transaction_date)), ("Required by", d(doc.schedule_date)), ("Warehouse", doc.set_warehouse), ("Ordered", bar(doc.per_ordered)),
		("Reason", doc.get("terms") and frappe.utils.strip_html(doc.terms)[:160]))
	p["sections"] = [section("Items", kind="table", cols=["#", "Item", "Qty", "UOM", "Required by", "Ordered"],
		rows=[[i, link("Item", it.item_code, it.item_name), flt(it.qty), it.uom, d(it.schedule_date), flt(it.ordered_qty)] for i, it in enumerate(doc.items, 1)])]
	acts = _edit(p, doc) + _submit(p, doc)
	if doc.docstatus == 1 and flt(doc.per_ordered) < 100 and doc.status not in ("Stopped", "Cancelled"):
		if _can("Request for Quotation"):
			acts.append(act("Request quotations", make="erpnext.stock.doctype.material_request.material_request.make_request_for_quotation"))
		if _can("Purchase Order"):
			acts.append(act("Order directly", kind="primary", make="erpnext.stock.doctype.material_request.material_request.make_purchase_order"))
	p["actions"] = acts
	return p


def request_for_quotation(doc):
	p = _base(doc, f"{doc.name} — " + _("request for quotation"), ", ".join(s.supplier for s in doc.suppliers[:3]))
	quotes = frappe.db.sql("""select sq.name, sq.supplier, sq.grand_total, sq.currency, sq.status, sq.transaction_date from `tabSupplier Quotation` sq
		join `tabSupplier Quotation Item` sqi on sqi.parent = sq.name where sqi.request_for_quotation = %s and sq.docstatus < 2 group by sq.name""", doc.name, as_dict=True)
	p["facts"] = kv(("Date", d(doc.transaction_date)), ("Reply by", d(doc.get("schedule_date"))), ("Suppliers", len(doc.suppliers)), ("Quotations received", len(quotes)))
	p["sections"] = [
		section("Items", kind="table", cols=["#", "Item", "Qty", "UOM"], rows=[[i, link("Item", it.item_code, it.item_name), flt(it.qty), it.uom] for i, it in enumerate(doc.items, 1)]),
		section("Suppliers & quotations", kind="table", cols=["Supplier", "Quotation", "Total", "Status"],
			rows=[[link("Supplier", s.supplier)] + next(([link("Supplier Quotation", q.name), money(q.grand_total, q.currency), pill(q.status)] for q in quotes if q.supplier == s.supplier),
				["—", "—", pill("Awaiting reply", "orange")]) for s in doc.suppliers]),
	]
	acts = _edit(p, doc) + _submit(p, doc, "Send")
	if doc.docstatus == 1 and _can("Supplier Quotation"):
		acts.append(act("Record quotation", route=["Form", "Supplier Quotation", "new"]))
	if len(quotes) > 1:
		acts.append(act("Compare quotations", kind="primary", route=["query-report", "Supplier Quotation Comparison"], options={"request_for_quotation": doc.name, "company": doc.company}))
	p["actions"] = acts
	return p


def stock_entry(doc):
	p = _base(doc, f"{doc.name} — " + _(doc.stock_entry_type or doc.purpose), d(doc.posting_date))
	p["facts"] = kv(("Purpose", _(doc.purpose)), ("From", doc.from_warehouse), ("To", doc.to_warehouse), ("Value", money(doc.total_outgoing_value or doc.total_incoming_value)), ("Remarks", doc.remarks))
	p["sections"] = [section("Items", kind="table", cols=["#", "Item", "Qty", "From", "To", "Batch / serial"],
		rows=[[i, link("Item", it.item_code, it.item_name), flt(it.qty), it.s_warehouse or "—", it.t_warehouse or "—", (it.batch_no or it.serial_no or "").replace("\n", ", ")[:50]]
			for i, it in enumerate(doc.items, 1)])]
	p["actions"] = _edit(p, doc) + _submit(p, doc)
	return p


def pick_list(doc):
	p = _base(doc, f"{doc.name} — " + _("pick list"), doc.customer or "")
	sos = sorted({l.sales_order for l in doc.locations if l.sales_order})
	p["facts"] = kv(("Sales orders", ", ".join(sos)), ("Warehouse", doc.parent_warehouse), ("Picker", doc.get("hs_picker") or ""), ("Status", pill(doc.status)))
	p["sections"] = [section("Locations", kind="table", cols=["#", "Item", "Qty", "Picked", "Warehouse", "Batch / serial"],
		rows=[[i, link("Item", l.item_code, l.item_name), flt(l.qty), flt(l.picked_qty), l.warehouse, (l.batch_no or l.serial_no or "").replace("\n", ", ")[:50]] for i, l in enumerate(doc.locations, 1)])]
	acts = _edit(p, doc) + _submit(p, doc, "Confirm picked")
	if doc.docstatus == 1 and _can("Delivery Note"):
		acts.append(act("Create delivery note", kind="primary", make="erpnext.stock.doctype.pick_list.pick_list.create_delivery_note"))
	p["actions"] = acts
	return p


def delivery_trip(doc):
	p = _base(doc, f"{doc.name} — " + (doc.driver_name or _("delivery trip")), " · ".join(x for x in [doc.vehicle, d(doc.departure_time)] if x))
	done = len([s for s in doc.delivery_stops if s.visited])
	p["progress"] = progress(["Planned", "On the road", "Completed"], 3 if doc.status == "Completed" else 1 if doc.status == "In Transit" else 0)
	p["facts"] = kv(("Driver", doc.driver_name), ("Vehicle", doc.vehicle), ("Departure", frappe.utils.format_datetime(doc.departure_time, "dd MMM HH:mm") if doc.departure_time else ""),
		("Stops", f"{done} / {len(doc.delivery_stops)} " + _("delivered")), ("Distance", f"{flt(doc.get('total_distance')):g} km" if doc.get("total_distance") else ""))
	p["sections"] = [section("Stops", kind="table", cols=["#", "Customer", "Delivery note", "Address", "Status"],
		rows=[[i, s.customer, link("Delivery Note", s.delivery_note), (s.customer_address or "")[:40], pill("Delivered", "green") if s.visited else pill("Pending", "orange")]
			for i, s in enumerate(doc.delivery_stops, 1)])]
	p["actions"] = _edit(p, doc) + _submit(p, doc, "Dispatch") + [act("Driver app", url="/driver")]
	return p


def warranty_claim(doc):
	p = _base(doc, f"{doc.name} — {doc.customer_name or doc.customer}", _("Warranty claim"))
	p["status"] = pill(doc.status, {"Open": "orange", "Work In Progress": "blue", "Closed": "green", "Cancelled": "grey"}.get(doc.status))
	p["facts"] = kv(("Serial no.", doc.serial_no), ("Item", link("Item", doc.item_code, doc.item_name)), ("Reported", d(doc.complaint_date)),
		("Warranty", pill(_(doc.warranty_amc_status or ""), "green" if doc.warranty_amc_status == "Under Warranty" else "orange") if doc.warranty_amc_status else ""),
		("Warranty until", d(doc.warranty_expiry_date)), ("Contact", doc.contact_display))
	p["sections"] = [section("Complaint", kv(("Issue", frappe.utils.strip_html(doc.complaint or "")[:400]), ("Resolution", frappe.utils.strip_html(doc.resolution_details or "")[:400]),
		("Resolved", d(doc.resolution_date)), ("Resolved by", doc.resolved_by)))]
	p["actions"] = [act("Edit", kind="primary", route=["Form", "Warranty Claim", doc.name])] if p["can_edit"] else []
	return p


# ---------------------------------------------------------------- Compliance
def company_document(doc):
	p = _base(doc, f"{_(doc.document_type)} — {doc.company}", doc.authority or "")
	left = date_diff(doc.expiry_date, today()) if doc.expiry_date else None
	tone = "red" if left is not None and left < 0 else "orange" if left is not None and left <= 60 else "green"
	p["status"] = pill(doc.status or ("Expired" if tone == "red" else "Valid"), tone)
	p["facts"] = kv(("Number", doc.document_number), ("Issued", d(doc.issue_date)),
		("Expires", pill(f"{d(doc.expiry_date)} · " + (_("{0} days ago").format(-left) if left < 0 else _("{0} days").format(left)), tone) if left is not None else _("No expiry")),
		("Owner", frappe.utils.get_fullname(doc.responsible_user) if doc.responsible_user else ""), ("Renewal", _(doc.renewal_status or "")),
		("Renewal cost", money(doc.renewal_cost) if doc.renewal_cost else ""))
	p["sections"] = [section("Notes", kv(("Notes", doc.notes), ("Last reminder", d(doc.last_reminder)), ("File", _("On file") if doc.attachment else _("Missing"))))]
	acts = [act("Edit", route=["Form", "Company Document", doc.name])] if p["can_edit"] else []
	if doc.attachment:
		acts.append(act("Open file", url=doc.attachment))
	if p["can_edit"] and left is not None and left <= 60:
		acts.append(act("Start renewal", kind="primary", action="hs_setval", args={"field": "renewal_status", "value": "In progress"}))
	p["actions"] = acts
	return p


def company_deadline(doc):
	left = date_diff(doc.due_date, today()) if doc.due_date else None
	p = _base(doc, doc.title, f"{doc.company} · {_(doc.category or '')}")
	p["status"] = pill("Done", "green") if doc.status == "Done" else pill("Overdue", "red") if left is not None and left < 0 else pill("Open", "blue")
	p["facts"] = kv(("Due", d(doc.due_date)), ("Repeats", _(doc.repeat or "")), ("Owner", frappe.utils.get_fullname(doc.responsible_user) if doc.responsible_user else ""),
		("Done on", d(doc.done_on)), ("Next deadline", link("Company Deadline", doc.next_deadline)), ("Notes", doc.notes))
	acts = [act("Edit", route=["Form", "Company Deadline", doc.name])] if p["can_edit"] else []
	if p["can_edit"] and doc.status != "Done":
		acts.append(act("Mark done", kind="primary", action="hs_setval", args={"field": "status", "value": "Done"}))
	p["actions"] = acts
	return p


BUILDERS = {"Export Shipment": export_shipment, "Payment Entry": payment_entry, "Journal Entry": journal_entry, "Purchase Invoice": purchase_invoice,
	"Employee": employee, "Payroll Entry": payroll_entry, "Expense Claim": expense_claim, "Employee Advance": employee_advance, "Leave Application": leave_application,
	"Bank Guarantee": bank_guarantee, "Asset": asset, "Post Dated Cheque": post_dated_cheque, "Tax Return": tax_return, "Material Request": material_request,
	"Request for Quotation": request_for_quotation, "Stock Entry": stock_entry, "Pick List": pick_list, "Delivery Trip": delivery_trip, "Warranty Claim": warranty_claim,
	"Company Document": company_document, "Company Deadline": company_deadline}

MAKERS = {
	"erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_debit_note",
	"erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
	"erpnext.stock.doctype.material_request.material_request.make_purchase_order",
	"erpnext.stock.doctype.pick_list.pick_list.create_delivery_note",
	"hipersign_trading.api.panel_more.pay_expense_claim",
}

DOC_METHODS = {("Export Shipment", "advance"), ("Export Shipment", "make_delivery_note"), ("Export Shipment", "make_sales_invoice"),
	("Post Dated Cheque", "deposit"), ("Post Dated Cheque", "clear")}
SET_VALUES = {("Company Document", "renewal_status", "In progress"), ("Company Deadline", "status", "Done")}


def pay_expense_claim(source_name):
	from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

	return get_payment_entry_for_employee("Expense Claim", source_name)


def action(doc, action, args):
	"""The actions behind these panels' buttons (called from panel.action)."""
	if action == "hs_submit":
		doc.check_permission("submit")
		if doc.get("workflow_state"):
			frappe.throw(_("{0} follows an approval workflow — use its approval buttons.").format(doc.name))
		doc.submit()
		return {"message": _("{0} submitted").format(doc.name)}
	if action == "hs_docmethod":
		m = args.get("method")
		if (doc.doctype, m) not in DOC_METHODS:
			frappe.throw(_("Not allowed"))
		doc.check_permission("write")
		r = getattr(doc, m)()
		if m.startswith("make_") and r:
			dt = "Delivery Note" if m == "make_delivery_note" else "Sales Invoice"
			return {"message": _("{0} created").format(r), "route": ["Form", dt, r]}
		return {"message": _("{0} updated").format(doc.name)}
	if action == "hs_setval":
		key = (doc.doctype, args.get("field"), args.get("value"))
		if key not in SET_VALUES:
			frappe.throw(_("Not allowed"))
		doc.check_permission("write")
		doc.set(key[1], key[2])
		if key == ("Company Deadline", "status", "Done") and doc.meta.has_field("done_on"):
			doc.done_on = today()
		doc.save()
		return {"message": _("{0} updated").format(doc.name)}
	if action == "hs_claim" and doc.doctype == "Expense Claim":
		doc.check_permission("submit")
		dec = args.get("decision")
		if dec not in ("Approved", "Rejected"):
			frappe.throw(_("Unknown decision"))
		doc.approval_status = dec
		cc = doc.get("cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center")
		for e in doc.expenses:
			if not e.get("cost_center"):
				e.cost_center = cc
			if dec == "Approved" and not flt(e.sanctioned_amount):
				e.sanctioned_amount = e.amount
		doc.save()
		doc.submit()
		return {"message": _("{0} {1}").format(doc.name, _(dec.lower()))}
	if action == "hs_leave" and doc.doctype == "Leave Application":
		doc.check_permission("submit")
		dec = args.get("decision")
		if dec not in ("Approved", "Rejected"):
			frappe.throw(_("Unknown decision"))
		doc.status = dec
		doc.save()
		doc.submit()
		return {"message": _("{0} {1}").format(doc.name, _(dec.lower()))}
	return None
