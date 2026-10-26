"""Daily reminders: lead follow-ups, proof of export (0% VAT), late import shipments."""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, today

from hipersign_trading.utils import settings
from hipersign_trading.features import feature_on


def _todo(doctype, name, user, text, date=None):
	if not user or frappe.db.exists(
		"ToDo", {"reference_type": doctype, "reference_name": name, "status": "Open", "allocated_to": user}
	):
		return
	frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": user,
			"reference_type": doctype,
			"reference_name": name,
			"description": text,
			"date": date or today(),
			"priority": "High",
		}
	).insert(ignore_permissions=True)


def _users_with_role(role):
	return [
		u.parent
		for u in frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
		if u.parent not in ("Administrator", "Guest") and frappe.db.get_value("User", u.parent, "enabled")
	]


def lead_follow_up_reminders():
	if not feature_on("crm"):
		return
	leads = frappe.get_all(
		"Lead",
		filters={
			"hs_next_follow_up": ["<=", today()],
			"hs_pipeline_stage": ["not in", ["Won", "Lost"]],
			"status": ["not in", ["Converted", "Do Not Contact"]],
		},
		fields=["name", "lead_name", "company_name", "lead_owner", "hs_next_follow_up", "hs_next_action"],
	)
	for d in leads:
		_todo(
			"Lead",
			d.name,
			d.lead_owner,
			_("Follow up {0}: {1}").format(d.company_name or d.lead_name, d.hs_next_action or _("next step")),
			d.hs_next_follow_up,
		)


def proof_of_export_alerts():
	if not feature_on("exports"):
		return
	s = settings()
	alert_after = s.proof_alert_days or 45
	rows = frappe.get_all(
		"Export Shipment",
		filters={"shipped_on": ["is", "set"], "proof_of_export_on": ["is", "not set"], "docstatus": ["<", 2]},
		fields=["name", "customer_name", "shipped_on", "proof_due_on"],
	)
	finance = _users_with_role("Accounts Manager")
	for r in rows:
		if date_diff(today(), r.shipped_on) >= alert_after:
			for u in finance:
				_todo(
					"Export Shipment",
					r.name,
					u,
					_("Proof of export for {0} ({1}) is due by {2} — without it the sale must be taxed at 5%.").format(
						r.name, r.customer_name, frappe.format_value(r.proof_due_on, {"fieldtype": "Date"})
					),
				)


def late_import_shipment_alerts():
	if not feature_on("imports"):
		return
	rows = frappe.get_all(
		"Import Shipment",
		filters={"eta": ["<", today()], "status": ["in", ["Booked", "Shipped", "In Transit"]]},
		fields=["name", "eta", "owner"],
	)
	logistics = _users_with_role("Logistics Coordinator") or _users_with_role("Purchase Manager")
	for r in rows:
		for u in logistics:
			_todo("Import Shipment", r.name, u, _("{0} is past its ETA — get a revised ETA from the forwarder.").format(r.name))


def cheque_alerts():
	"""Cheques to deposit (date reached) and issued cheques about to be presented."""
	if not feature_on("pdc"):
		return
	if not frappe.db.table_exists("Post Dated Cheque"):
		return
	s = settings()
	ahead = add_days(today(), s.get("pdc_alert_days") or 2)
	finance = _users_with_role("Accounts User") or _users_with_role("Accounts Manager")
	for r in frappe.get_all("Post Dated Cheque", filters={"status": "In Hand", "cheque_date": ["<=", today()]},
			fields=["name", "cheque_no", "party_name", "amount", "cheque_date"]):
		for u in finance:
			_todo("Post Dated Cheque", r.name, u, _("Deposit cheque {0} from {1} — cheque date {2} reached.").format(
				r.cheque_no, r.party_name, frappe.format_value(r.cheque_date, {"fieldtype": "Date"})))
	for r in frappe.get_all("Post Dated Cheque", filters={"status": "Issued", "cheque_date": ["<=", ahead]},
			fields=["name", "cheque_no", "party_name", "amount", "cheque_date"]):
		for u in _users_with_role("Accounts Manager"):
			_todo("Post Dated Cheque", r.name, u, _("Cheque {0} to {1} for {2} can be presented on {3} — keep funds in the bank.").format(
				r.cheque_no, r.party_name, frappe.format_value(r.amount, {"fieldtype": "Currency"}), frappe.format_value(r.cheque_date, {"fieldtype": "Date"})))


def employee_document_alerts():
	"""Passport, visa, Emirates ID and labour card expiring soon — expired documents block WPS salary."""
	if not feature_on("hr"):
		return
	from hipersign_trading.constants import EMPLOYEE_DOCS

	meta = frappe.get_meta("Employee")
	limit = add_days(today(), settings().get("doc_expiry_alert_days") or 60)
	hr = _users_with_role("HR Manager") or _users_with_role("HR User")
	for field, label in EMPLOYEE_DOCS.items():
		if not meta.has_field(field):
			continue
		for e in frappe.get_all("Employee", filters={"status": "Active", field: ["between", ["2000-01-01", limit]]}, fields=["name", "employee_name", field]):
			left = date_diff(e[field], today())
			text = (_("{0}'s {1} expired {2} days ago — renew now.") if left < 0 else _("{0}'s {1} expires in {2} days — start the renewal.")).format(
				e.employee_name, label, abs(left))
			for u in hr:
				_todo("Employee", e.name, u, text)


# ---------------------------------------------------------------- v1.2
def collection_reminders():
	"""Move overdue invoices through the collection stages and give the accountant a ToDo for each new stage.

	An invoice with a promise to pay dated today or later is left alone until that date.
	"""
	if not feature_on("advances"):
		return
	from frappe.utils import date_diff, getdate

	s = settings()
	if not frappe.get_meta("Sales Invoice").has_field("hs_collection_stage"):
		return
	stages = [(int(s.get("collection_stage_1") or 7), "Friendly reminder"), (int(s.get("collection_stage_2") or 21), "Second reminder"),
		(int(s.get("collection_stage_3") or 45), "Final notice")]
	if int(s.get("collection_hold_days") or 0):
		stages.append((int(s.collection_hold_days), "Hold new orders"))
	accounts = _users_with_role("Accounts User") or _users_with_role("Accounts Manager")
	for inv in frappe.get_all("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", today()], "is_return": 0},
			fields=["name", "customer_name", "due_date", "outstanding_amount", "hs_collection_stage", "hs_promise_date"]):
		if inv.hs_promise_date and getdate(inv.hs_promise_date) >= getdate(today()):
			continue
		late = date_diff(today(), inv.due_date)
		stage = None
		for days, name in stages:
			if late >= days:
				stage = name
		if not stage or stage == inv.hs_collection_stage:
			continue
		frappe.db.set_value("Sales Invoice", inv.name, {"hs_collection_stage": stage, "hs_last_reminder": today()}, update_modified=False)
		for u in accounts:
			_todo("Sales Invoice", inv.name, u, _("{0}: {1} to {2} — {3} outstanding, {4} days overdue. Send it from the invoice (Send → WhatsApp / Email).").format(
				stage, inv.name, inv.customer_name, frappe.format_value(inv.outstanding_amount, {"fieldtype": "Currency"}), late))


def kyc_alerts():
	"""Trade licences expiring soon or expired — the customer's new orders are blocked once it expires."""
	if not feature_on("kyc"):
		return
	s = settings()
	limit = add_days(today(), s.get("kyc_alert_days") or 30)
	for doctype, role, name_field in [("Customer", "Sales Manager", "customer_name"), ("Supplier", "Purchase Manager", "supplier_name")]:
		meta = frappe.get_meta(doctype)
		if not meta.has_field("hs_trade_licence_expiry"):
			continue
		users = _users_with_role(role) + _users_with_role("Accounts Manager")
		for p in frappe.get_all(doctype, filters={"disabled": 0, "hs_trade_licence_expiry": ["between", ["2000-01-01", limit]]}, fields=["name", name_field, "hs_trade_licence_expiry", "hs_kyc_status"]):
			left = date_diff(p.hs_trade_licence_expiry, today())
			if left < 0 and p.hs_kyc_status in ("Verified", "Pending"):
				frappe.db.set_value(doctype, p.name, "hs_kyc_status", "Expired", update_modified=False)
			text = (_("{0}'s trade licence expired {1} days ago — new orders are blocked until a renewed copy is on file.") if left < 0
				else _("{0}'s trade licence expires in {1} days — ask for the renewed copy.")).format(p.get(name_field), abs(left))
			for u in set(users):
				_todo(doctype, p.name, u, text)


def letter_of_credit_alerts():
	"""LCs about to expire and trust receipt loans about to fall due."""
	if not feature_on("lc"):
		return
	if not frappe.db.table_exists("Letter of Credit"):
		return
	limit = add_days(today(), settings().get("lc_alert_days") or 14)
	users = _users_with_role("Accounts Manager") + _users_with_role("Purchase Manager")
	for lc in frappe.get_all("Letter of Credit", filters={"status": ["in", ["Applied", "Issued"]], "expiry_date": ["<=", limit]},
			fields=["name", "lc_number", "party_name", "expiry_date"]):
		for u in set(users):
			_todo("Letter of Credit", lc.name, u, _("LC {0} for {1} expires on {2} — ship and present documents in time, or ask the bank for an amendment.").format(
				lc.lc_number or lc.name, lc.party_name, frappe.format_value(lc.expiry_date, {"fieldtype": "Date"})))
	for lc in frappe.get_all("Letter of Credit", filters={"trust_receipt": 1, "tr_repaid_on": ["is", "not set"], "tr_due": ["<=", limit]},
			fields=["name", "lc_number", "tr_amount", "tr_due"]):
		for u in _users_with_role("Accounts Manager"):
			_todo("Letter of Credit", lc.name, u, _("Trust receipt on LC {0} ({1}) is due on {2} — keep funds in the bank.").format(
				lc.lc_number or lc.name, frappe.format_value(lc.tr_amount, {"fieldtype": "Currency"}), frappe.format_value(lc.tr_due, {"fieldtype": "Date"})))


def advance_due_alerts():
	"""Confirmed orders still waiting for their advance — remind the order's owner and the Sales Manager."""
	if not feature_on("advances"):
		return
	if not frappe.get_meta("Sales Order").has_field("hs_advance_status"):
		return
	managers = _users_with_role("Sales Manager")
	for so in frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["not in", ["Closed", "Completed", "On Hold"]],
			"hs_advance_status": ["in", ["Waiting", "Part received"]], "per_delivered": ["<", 100]}, fields=["name", "customer_name", "owner", "hs_advance_required"]):
		for u in set([so.owner] + managers):
			if u in ("Administrator", "Guest"):
				continue
			_todo("Sales Order", so.name, u, _("Advance of {0} not received from {1} — the order cannot be delivered until it is. Send the proforma on WhatsApp.").format(
				frappe.format_value(so.hs_advance_required, {"fieldtype": "Currency"}), so.customer_name))


def tax_return_alerts():
	"""VAT returns due within 7 days that are not filed yet, and periods that ended with no return prepared."""
	if not frappe.db.table_exists("Tax Return"):
		return
	finance = _users_with_role("Accounts Manager") or _users_with_role("Accounts User")
	for r in frappe.get_all("Tax Return", filters={"status": ["in", ["Prepared", "Pending Finance Manager", "Approved"]], "due_date": ["<=", add_days(today(), 7)]},
			fields=["name", "title", "status", "due_date"]):
		for u in finance:
			_todo("Tax Return", r.name, u, _("{0} is due on {1} and is still {2}.").format(r.title, frappe.format_value(r.due_date, {"fieldtype": "Date"}), _(r.status)))


def revaluation_reminder():
	"""First of the month: open foreign-currency receivables or payables should be revalued at last month's closing rate."""
	if not feature_on("fx"):
		return
	from frappe.utils import add_months, get_first_day, get_last_day

	if not settings().get("revaluation_reminder"):
		return
	month_end = get_last_day(add_months(today(), -1))
	for company, currency in frappe.get_all("Company", fields=["name", "default_currency"], as_list=True):
		fc = frappe.db.sql("""select count(*) from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
			where gle.company=%s and gle.is_cancelled=0 and acc.account_type in ('Receivable','Payable','Bank')
			and gle.account_currency <> %s and gle.posting_date <= %s""", (company, currency, month_end))[0][0]
		if not fc or frappe.db.exists("Exchange Rate Revaluation", {"company": company, "posting_date": ["between", [get_first_day(month_end), month_end]], "docstatus": 1}):
			continue
		for u in _users_with_role("Accounts Manager"):
			_todo("Company", company, u, _("Revalue {0}'s foreign-currency balances at the {1} closing rate: Exchange Rate Revaluation → posting date {1} → Get entries → Submit → Make journal entries (they reverse on the 1st).").format(
				company, frappe.format_value(month_end, {"fieldtype": "Date"})))
