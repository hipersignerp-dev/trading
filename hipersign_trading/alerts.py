"""v1.5 — Insights & Alerts: deterministic rules over live ERPNext data (no AI model).

Each rule returns alerts shaped as
  {key, title, severity (High / Medium / Low), category, evidence [[label, value]], consequence, recommendation,
   doctype, name}
`key` is stable for the underlying situation, so marking an alert actioned or dismissed (Hipersign Alert State) sticks
until the situation changes.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, fmt_money, formatdate, getdate, today

from hipersign_trading.utils import can_read, settings

SEV_ORDER = {"High": 0, "Medium": 1, "Low": 2}
CATEGORIES = [
	"Customs documents", "Stock", "Slow-moving stock", "Receivables", "Cheques", "VAT", "Margin", "Employee documents",
	"Letters of credit", "Bank guarantees", "Company compliance", "KYC & licences", "Document exceptions",
]


def _m(v, company=None):
	cur = frappe.get_cached_value("Company", company, "default_currency") if company else None
	return f"{cur or 'AED'} {fmt_money(flt(v), precision=2)}"


def _d(v):
	return formatdate(v) if v else "—"


def _has(dt):
	return frappe.db.exists("DocType", dt) and frappe.db.table_exists(dt)


def _co(filters, company):
	if company:
		filters["company"] = company
	return filters


def rule_customs(company):
	out = []
	for s in frappe.get_all("Import Shipment", filters=_co({"status": ["in", ["Arrived at Port", "Under Customs Clearance"]]}, company),
			fields=["name", "status", "eta", "company", "goods_value"]):
		missing = frappe.get_all("Shipment Document", filters={"parent": s.name, "parenttype": "Import Shipment", "required": 1, "received": 0}, pluck="document_type")
		if not missing:
			continue
		sup = frappe.db.get_value("Import Shipment PO", {"parent": s.name}, "supplier")
		out.append(dict(key=f"customs:{s.name}:{','.join(sorted(missing))}", severity="High", category="Customs documents",
			title=_("{0} is missing {1}").format(s.name, ", ".join(_(m).lower() for m in missing)),
			evidence=[[_("Status"), _(s.status)], [_("ETA"), _d(s.eta)], [_("Supplier"), sup or "—"]],
			consequence=_("Goods are at port — each day without clearance adds demurrage and storage."),
			recommendation=_("Chase the supplier for the original document and send it to the customs broker."),
			doctype="Import Shipment", name=s.name))
	return out


def rule_receivables(company):
	out = []
	for si in frappe.get_all("Sales Invoice", filters=_co({"docstatus": 1, "outstanding_amount": [">", 0.5], "due_date": ["<", add_days(today(), -14)], "is_return": 0}, company),
			fields=["name", "customer_name", "outstanding_amount", "due_date", "company", "hs_promise_date"], order_by="due_date asc", limit=40):
		days = date_diff(today(), si.due_date)
		if si.hs_promise_date and getdate(si.hs_promise_date) >= getdate(today()):
			continue
		out.append(dict(key=f"ar:{si.name}", severity="High" if days > 60 else "Medium", category="Receivables",
			title=_("{0} — {1} overdue {2} days").format(si.customer_name, si.name, days),
			evidence=[[_("Outstanding"), _m(si.outstanding_amount, si.company)], [_("Due"), _d(si.due_date)]],
			consequence=_("Cash collection is behind plan."),
			recommendation=_("Call the customer and hold new orders until paid."), doctype="Sales Invoice", name=si.name))
	return out


def rule_cheques(company):
	out = []
	for p in frappe.get_all("Post Dated Cheque", filters=_co({"status": "Bounced"}, company), fields=["name", "cheque_no", "party_name", "amount", "cheque_date", "company"]):
		out.append(dict(key=f"pdc-bounce:{p.name}", severity="High", category="Cheques",
			title=_("Cheque {0} from {1} bounced").format(p.cheque_no, p.party_name),
			evidence=[[_("Amount"), _m(p.amount, p.company)], [_("Cheque date"), _d(p.cheque_date)]],
			consequence=_("The invoice is unpaid again and the customer's credit risk has increased."),
			recommendation=_("Collect a replacement cheque or transfer and hold new orders until settled."), doctype="Post Dated Cheque", name=p.name))
	for p in frappe.get_all("Post Dated Cheque", filters=_co({"status": "In Hand", "direction": "Received", "cheque_date": ["<=", add_days(today(), 2)]}, company),
			fields=["name", "cheque_no", "party_name", "amount", "cheque_date", "company"]):
		out.append(dict(key=f"pdc-deposit:{p.name}", severity="Medium", category="Cheques",
			title=_("Cheque {0} from {1} is ready to deposit").format(p.cheque_no, p.party_name),
			evidence=[[_("Amount"), _m(p.amount, p.company)], [_("Cheque date"), _d(p.cheque_date)]],
			consequence=_("A cheque deposited late delays cash and may go stale after six months."),
			recommendation=_("Deposit it at the bank and mark it Deposited."), doctype="Post Dated Cheque", name=p.name))
	return out


def rule_stock(company):
	out = []
	if not _has("Item Reorder"):
		return out
	wh_filter = {"company": company} if company else {}
	whs = set(frappe.get_all("Warehouse", filters=wh_filter, pluck="name"))
	for r in frappe.get_all("Item Reorder", fields=["parent", "warehouse", "warehouse_reorder_level"]):
		if r.warehouse not in whs or not flt(r.warehouse_reorder_level):
			continue
		b = frappe.db.get_value("Bin", {"item_code": r.parent, "warehouse": r.warehouse}, ["actual_qty", "projected_qty"], as_dict=True) or frappe._dict(actual_qty=0, projected_qty=0)
		if flt(b.projected_qty) > flt(r.warehouse_reorder_level):
			continue
		name = frappe.get_cached_value("Item", r.parent, "item_name")
		out_of = flt(b.actual_qty) <= 0
		out.append(dict(key=f"stock:{r.parent}:{r.warehouse}:{'out' if out_of else 'low'}", severity="High" if out_of else "Medium", category="Stock",
			title=_("{0} is {1} in {2}").format(name, _("out of stock") if out_of else _("below reorder level"), r.warehouse),
			evidence=[[_("In stock"), frappe.format(b.actual_qty, "Float")], [_("Projected"), frappe.format(b.projected_qty, "Float")],
				[_("Reorder level"), frappe.format(r.warehouse_reorder_level, "Float")]],
			consequence=_("Orders for this item will wait for stock."),
			recommendation=_("Raise a purchase order — Smart Reorder suggests quantities by supplier."), doctype="Item", name=r.parent))
	return out


def rule_slow_moving(company):
	out = []
	since = add_days(today(), -90)
	wh_filter = {"company": company} if company else {}
	whs = frappe.get_all("Warehouse", filters=wh_filter, pluck="name")
	if not whs:
		return out
	bins = frappe.get_all("Bin", filters={"warehouse": ["in", whs], "actual_qty": [">", 0]}, fields=["item_code", "warehouse", "actual_qty", "stock_value"])
	for b in bins:
		moved = frappe.db.exists("Stock Ledger Entry", {"item_code": b.item_code, "warehouse": b.warehouse, "actual_qty": ["<", 0], "posting_date": [">=", since], "is_cancelled": 0})
		if moved:
			continue
		first_in = frappe.get_all("Stock Ledger Entry", filters={"item_code": b.item_code, "warehouse": b.warehouse, "is_cancelled": 0},
			pluck="posting_date", order_by="posting_date asc", limit=1)
		first_in = first_in[0] if first_in else None
		if first_in and getdate(first_in) > getdate(since):
			continue
		out.append(dict(key=f"slow:{b.item_code}:{b.warehouse}", severity="Low", category="Slow-moving stock",
			title=_("{0} has not moved for 90 days in {1}").format(frappe.get_cached_value("Item", b.item_code, "item_name"), b.warehouse),
			evidence=[[_("Quantity"), frappe.format(b.actual_qty, "Float")], [_("Stock value"), _m(b.stock_value, company)]],
			consequence=_("Cash is tied up in stock that is not selling."),
			recommendation=_("Offer it in the next promotion or move it to a branch that sells it."), doctype="Item", name=b.item_code))
	return out[:20]


def rule_margin(company):
	out = []
	target = flt(settings().get("target_margin")) or 20
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	from frappe.query_builder.functions import Sum

	q = (frappe.qb.from_(sii).join(si).on(si.name == sii.parent)
		.select(sii.item_code, Sum(sii.base_net_amount).as_("sales"), Sum(sii.incoming_rate * sii.stock_qty).as_("cost"))
		.where((si.docstatus == 1) & (si.is_return == 0) & (si.posting_date >= add_days(today(), -60))).groupby(sii.item_code))
	if company:
		q = q.where(si.company == company)
	for item, sales, cost in q.run():
		sales, cost = flt(sales), flt(cost)
		if sales <= 0 or cost <= 0:
			continue
		m = (sales - cost) / sales * 100
		if m >= target:
			continue
		out.append(dict(key=f"margin:{item}:{round(m)}", severity="High" if m < target / 2 else "Medium", category="Margin",
			title=_("{0} sold at {1}% margin — target {2}%").format(frappe.get_cached_value("Item", item, "item_name"), round(m, 1), round(target)),
			evidence=[[_("Sales (60 days)"), _m(sales, company)], [_("Landed cost"), _m(cost, company)]],
			consequence=_("Profit is lower than planned on this item."),
			recommendation=_("Check discounts given and the landed cost; raise the list price if needed."), doctype="Item", name=item))
	return out


def rule_vat(company):
	out = []
	if not _has("Tax Return"):
		return out
	for t in frappe.get_all("Tax Return", filters=_co({"status": ["not in", ["Submitted", "Paid", "Rejected"]], "due_date": ["<=", add_days(today(), 7)]}, company),
			fields=["name", "title", "status", "due_date", "tax_type"]):
		out.append(dict(key=f"vat:{t.name}:{t.status}", severity="High", category="VAT",
			title=_("{0} is due on {1}").format(t.title or t.name, _d(t.due_date)),
			evidence=[[_("Status"), _(t.status)], [_("Return"), _(t.tax_type)]],
			consequence=_("A late return or payment brings FTA penalties."),
			recommendation=_("Approve the return and file it on EmaraTax."), doctype="Tax Return", name=t.name))
	return out


def rule_employee_docs(company):
	out = []
	meta = frappe.get_meta("Employee") if _has("Employee") else None
	if not meta:
		return out
	fields = [(f, label) for f, label in (("hs_emirates_id_expiry", _("Emirates ID")), ("hs_visa_expiry", _("residence visa")), ("hs_labour_card_expiry", _("labour card")))
		if meta.has_field(f)]
	for e in frappe.get_all("Employee", filters=_co({"status": "Active"}, company), fields=["name", "employee_name", "designation"] + [f for f, _l in fields]):
		for f, label in fields:
			exp = e.get(f)
			if not exp:
				continue
			days = date_diff(exp, today())
			if days > 45:
				continue
			out.append(dict(key=f"emp:{e.name}:{f}:{exp}", severity="High" if days <= 21 else "Medium", category="Employee documents",
				title=_("{0}'s {1} expires in {2} days").format(e.employee_name, label, days) if days >= 0 else _("{0}'s {1} expired {2} days ago").format(e.employee_name, label, -days),
				evidence=[[_("Employee"), f"{e.employee_name} · {e.designation or ''}"], [_("Expiry"), _d(exp)]],
				consequence=_("An expired visa, Emirates ID or labour card can lead to fines and blocks WPS salary payments."),
				recommendation=_("Start the renewal with the PRO now."), doctype="Employee", name=e.name))
	return out


def rule_lc(company):
	out = []
	for lc in frappe.get_all("Letter of Credit", filters=_co({"status": ["in", ["Issued", "Documents Presented", "Accepted"]], "expiry_date": ["<=", add_days(today(), 14)]}, company),
			fields=["name", "lc_number", "expiry_date", "status", "amount", "currency"]):
		out.append(dict(key=f"lc:{lc.name}:{lc.expiry_date}", severity="High", category="Letters of credit",
			title=_("{0} expires {1} — {2}").format(lc.lc_number or lc.name, _d(lc.expiry_date), _("documents not yet presented") if lc.status == "Issued" else _(lc.status).lower()),
			evidence=[[_("Amount"), f"{lc.currency} {fmt_money(flt(lc.amount), precision=2)}"], [_("Status"), _(lc.status)]],
			consequence=_("After expiry the bank will not pay under the LC."),
			recommendation=_("Present the documents or ask the bank for an amendment."), doctype="Letter of Credit", name=lc.name))
	return out


def rule_bg(company):
	out = []
	if not _has("Bank Guarantee"):
		return out
	for bg in frappe.get_all("Bank Guarantee", filters=_co({"docstatus": 1, "end_date": ["between", [add_days(today(), -30), add_days(today(), 30)]]}, company),
			fields=["name", "bank_guarantee_number", "end_date", "amount", "name_of_beneficiary"]):
		out.append(dict(key=f"bg:{bg.name}:{bg.end_date}", severity="Medium", category="Bank guarantees",
			title=_("Guarantee {0} for {1} ends {2}").format(bg.bank_guarantee_number or bg.name, bg.name_of_beneficiary or "", _d(bg.end_date)),
			evidence=[[_("Amount"), _m(bg.amount, company)], [_("Ends"), _d(bg.end_date)]],
			consequence=_("The beneficiary may call the guarantee or the bank keeps charging commission."),
			recommendation=_("Ask the beneficiary to release it or extend it with the bank."), doctype="Bank Guarantee", name=bg.name))
	return out


def rule_company_docs(company):
	out = []
	if not _has("Company Document"):
		return out
	for d in frappe.get_all("Company Document", filters=_co({"status": ["in", ["Expired", "Due for renewal"]]}, company),
			fields=["name", "document_type", "company", "expiry_date", "status", "responsible_user"]):
		days = date_diff(d.expiry_date, today()) if d.expiry_date else 0
		out.append(dict(key=f"codoc:{d.name}:{d.expiry_date}:{d.status}", severity="High" if d.status == "Expired" or days <= 7 else "Medium", category="Company compliance",
			title=_("{0} — {1} expired {2} days ago").format(_(d.document_type), d.company, -days) if days < 0 else _("{0} — {1} expires in {2} days").format(_(d.document_type), d.company, days),
			evidence=[[_("Expiry"), _d(d.expiry_date)], [_("Responsible"), (frappe.get_cached_value("User", d.responsible_user, "full_name") or d.responsible_user) if d.responsible_user else "—"]],
			consequence=_("Trading with an expired licence brings fines and can block customs and bank services."),
			recommendation=_("Start or finish the renewal and record the new expiry date."), doctype="Company Document", name=d.name))
	if _has("Company Deadline"):
		for d in frappe.get_all("Company Deadline", filters=_co({"status": "Open", "due_date": ["<=", add_days(today(), 7)]}, company), fields=["name", "title", "due_date", "company"]):
			days = date_diff(d.due_date, today())
			out.append(dict(key=f"deadline:{d.name}:{d.due_date}", severity="High", category="Company compliance",
				title=_("{0} due {1}").format(d.title, _d(d.due_date)) if days >= 0 else _("{0} overdue since {1}").format(d.title, _d(d.due_date)),
				evidence=[[_("Company"), d.company], [_("Due"), _d(d.due_date)]],
				consequence=_("A missed statutory deadline brings penalties."), recommendation=_("Complete it and mark it done."), doctype="Company Deadline", name=d.name))
	return out


def rule_kyc(company):
	out = []
	if not frappe.get_meta("Customer").has_field("hs_trade_licence_expiry"):
		return out
	for c in frappe.get_all("Customer", filters={"disabled": 0, "is_internal_customer": 0}, fields=["name", "customer_name", "hs_trade_licence_expiry", "hs_kyc_status"]):
		expired = c.hs_trade_licence_expiry and getdate(c.hs_trade_licence_expiry) < getdate(today())
		if not expired and c.hs_kyc_status != "Blocked":
			continue
		out.append(dict(key=f"kyc:{c.name}:{c.hs_trade_licence_expiry}:{c.hs_kyc_status}", severity="High", category="KYC & licences",
			title=_("{0} — trade licence expired on {1}").format(c.customer_name, _d(c.hs_trade_licence_expiry)) if expired else _("{0} — KYC blocked").format(c.customer_name),
			evidence=[[_("KYC status"), _(c.hs_kyc_status or "Pending")], [_("Licence expiry"), _d(c.hs_trade_licence_expiry)]],
			consequence=_("New orders for this customer cannot be confirmed."),
			recommendation=_("Ask the customer for the renewed licence and update KYC."), doctype="Customer", name=c.name))
	return out


def rule_waivers(company):
	out = []
	if not _has("Document Waiver"):
		return out
	from hipersign_trading.api.approvals import waiver_open

	for w in frappe.get_all("Document Waiver", filters={"status": ["in", ["Overdue", "Pending"]]}, fields=["name", "status", "reference_doctype", "reference_name", "document_type", "due_date", "approver_role"]):
		if w.status == "Pending" and not waiver_open(w):
			continue  # v1.5.6: its record has moved on
		out.append(dict(key=f"waiver:{w.name}:{w.status}", severity="High" if w.status == "Overdue" else "Medium", category="Document exceptions",
			title=_("{0} for {1} {2} — {3}").format(_(w.document_type), _(w.reference_doctype), w.reference_name, _("overdue") if w.status == "Overdue" else _("waiting for the {0}").format(_(w.approver_role))),
			evidence=[[_("Status"), _(w.status)], [_("Document due"), _d(w.due_date)]],
			consequence=_("The record went ahead without its document.") if w.status == "Overdue" else _("The record is waiting for the exception to be decided."),
			recommendation=_("Attach the document to the record.") if w.status == "Overdue" else _("Approve or reject the exception."), doctype="Document Waiver", name=w.name))
	return out


RULES = [rule_customs, rule_stock, rule_slow_moving, rule_receivables, rule_cheques, rule_vat, rule_margin, rule_employee_docs,
	rule_lc, rule_bg, rule_company_docs, rule_kyc, rule_waivers]


# v1.5.6 (SET-05): a switched-off feature raises no alerts
RULE_FEATURE = {"rule_customs": "imports", "rule_cheques": "pdc", "rule_lc": "lc", "rule_bg": "lc", "rule_employee_docs": "hr",
	"rule_company_docs": "codocs", "rule_kyc": "kyc"}


def evaluate(company=None):
	from hipersign_trading.features import feature_on

	out = []
	for rule in RULES:
		if RULE_FEATURE.get(rule.__name__) and not feature_on(RULE_FEATURE[rule.__name__]):
			continue
		frappe.db.savepoint("hs_alert_rule")
		try:
			out.extend(rule(company))
		except Exception:
			frappe.db.rollback(save_point="hs_alert_rule")
			frappe.log_error(title=f"Hipersign alert rule {rule.__name__}")
	states = {}
	if _has("Hipersign Alert State"):
		states = {r.alert_key: r for r in frappe.get_all("Hipersign Alert State", fields=["alert_key", "status", "note", "modified_by", "modified"])}
	for a in out:
		st = states.get(a["key"])
		a["status"] = st.status if st else "Open"
		a["state_note"] = st.note if st else None
	out.sort(key=lambda a: (SEV_ORDER.get(a["severity"], 9), a["category"], a["title"]))
	return out


def can_see(a):
	try:
		return can_read(a["doctype"], a["name"])
	except Exception:
		return False


@frappe.whitelist()
def get_alerts(company=None):
	alerts = [a for a in evaluate(company or None) if can_see(a)]
	return {"alerts": alerts, "rules": len(RULES), "categories": CATEGORIES}


@frappe.whitelist()
def set_state(key, status, note=None):
	if status not in ("Open", "Actioned", "Dismissed"):
		frappe.throw(_("Unknown status"))
	name = frappe.db.get_value("Hipersign Alert State", {"alert_key": key})
	if status == "Open":
		if name:
			frappe.delete_doc("Hipersign Alert State", name, ignore_permissions=True)
		return "Open"
	doc = frappe.get_doc("Hipersign Alert State", name) if name else frappe.new_doc("Hipersign Alert State")
	doc.alert_key, doc.status, doc.note = key, status, note
	doc.flags.ignore_permissions = True
	doc.save()
	return status
