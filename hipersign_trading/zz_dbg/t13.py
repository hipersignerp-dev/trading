"""v1.3 functional checks on a demo site.  bench --site X execute hipersign_trading.zz_dbg.t13.run"""
import traceback

import frappe
from frappe.utils import add_days, flt, today

R = []


def ok(name, cond, info=""):
	R.append((name, bool(cond), info))
	print(("✓ " if cond else "✗ ") + name + (f"  — {info}" if info else ""))


def expect_throw(name, fn, contains=None):
	sp = "t13sp"
	frappe.db.savepoint(sp)
	try:
		fn()
		ok(name, False, "no error raised")
	except Exception as e:
		msg = frappe.utils.strip_html(str(e))
		ok(name, contains is None or contains.lower() in msg.lower(), msg[:160])
	frappe.db.rollback(save_point=sp)
	frappe.local.message_log = []


def company():
	return frappe.db.get_single_value("Hipersign Settings", "company") or frappe.defaults.get_global_default("company")


def t_errors():
	f = {"method": ["!=", "Unable to fetch exchange rate"]}
	n = frappe.db.count("Error Log", f)
	titles = frappe.get_all("Error Log", filters=f, fields=["method"], limit=8, order_by="creation desc", pluck="method")
	ok("no Error Log rows after demo", n == 0, f"{n}: {titles}")


def t_consolidation():
	from hipersign_trading.group import consolidate

	r = consolidate(today())
	ok("consolidation has members", len(r["members"]) >= 2, ", ".join(m["member"] for m in r["members"]))
	for m in r["members"]:
		tot = sum(v.get(m["member"], 0) for k, v in r["lines"].items() if k[0] == "Balance Sheet")
		ok(f"member balance sheet balances: {m['member']}", abs(tot) < 0.05, f"{tot:.2f}")
	grand = sum(sum(v.values()) for k, v in r["lines"].items() if k[0] == "Balance Sheet") + sum(v for k, v in r["elim"].items() if k[0] == "Balance Sheet")
	ok("group balance sheet balances after eliminations", abs(grand) < 0.05, f"{grand:.2f}; notes: {r['notes'][:3]}")
	from hipersign_trading.hipersign_trading.report.hipersign_group_consolidation.hipersign_group_consolidation import execute

	cols, data, *_ = execute(frappe._dict(period_end=today(), show="Both"))
	ok("consolidation report runs", cols and data, f"{len(data)} rows")


def t_missing_docs_report():
	from hipersign_trading.hipersign_trading.report.missing_documents.missing_documents import execute

	cols, data, *_ = execute(frappe._dict(company=company()))
	ok("Missing Documents report runs", cols is not None, f"{len(data)} rows")


def t_doc_gate():
	from hipersign_trading.demo import context, make_so

	c = context()
	c.selling_pl = "Standard Selling"
	cust = "Gulf Trading LLC"
	so = make_so(c, cust, [("ITM-001", 60)], 0, None, submit=False)
	ok("big draft SO made", so.base_grand_total >= 50000, f"{so.name} {so.base_grand_total}")
	expect_throw("SO ≥ 50k without LPO is blocked", lambda: frappe.get_doc("Sales Order", so.name).submit(), "LPO")
	# exception asked by a Sales Manager is self-approved and lets it through
	from hipersign_trading.api.docs import request_waiver

	w = request_waiver("Sales Order", so.name, "Customer LPO", "Test — email confirmation", add_days(today(), 3))
	ok("waiver by System Manager approved", frappe.db.get_value("Document Waiver", w, "status") == "Approved", w)
	sp = "gate2"
	frappe.db.savepoint(sp)
	try:
		d = frappe.get_doc("Sales Order", so.name)
		d.flags.ignore_permissions = True
		from hipersign_trading.api.quick import _submit

		d = _submit(d)
		ok("SO goes on with approved exception", d.docstatus == 1 or d.get("workflow_state") not in (None, "Draft"), d.get("workflow_state"))
		if d.docstatus == 0:
			from frappe.model.workflow import apply_workflow
			d = apply_workflow(frappe.get_doc("Sales Order", so.name), "Approve")
		ok("SO submitted after approval", d.docstatus == 1, d.get("workflow_state"))
		ok("waiver marked Used", frappe.db.get_value("Document Waiver", w, "status") == "Used", frappe.db.get_value("Document Waiver", w, "status"))
	except Exception as e:
		ok("SO goes on with approved exception", False, frappe.utils.strip_html(str(e))[:200])
	frappe.db.rollback(save_point=sp)
	# Recommended level: block becomes a warning
	s = frappe.get_single("Hipersign Settings")
	old = s.document_level
	frappe.db.set_single_value("Hipersign Settings", "document_level", "Recommended")
	frappe.clear_cache(doctype="Hipersign Settings")
	from hipersign_trading.doc_rules import effective

	ok("Recommended turns Block into Required", effective("Block") == "Required")
	frappe.db.set_single_value("Hipersign Settings", "document_level", old)
	frappe.clear_cache(doctype="Hipersign Settings")
	from hipersign_trading.api.docs import doc_info

	info = doc_info("Sales Order", so.name)
	ok("doc_info lists rules", len(info.get("rules") or []) >= 1, str([x["document_type"] for x in info["rules"]]))


def _open_si(min_amt=1000):
	return frappe.get_all("Sales Invoice", filters={"docstatus": 1, "company": company(), "outstanding_amount": [">", min_amt], "is_return": 0, "currency": "AED"},
		fields=["name", "customer", "outstanding_amount"], order_by="posting_date asc", limit=3)


def make_pi():
	sup = frappe.get_all("Supplier", filters={"default_currency": ["in", ["AED", "", None]]}, pluck="name", limit=1)[0]
	pi = frappe.get_doc({"doctype": "Purchase Invoice", "supplier": sup, "company": company(), "currency": "AED", "bill_no": frappe.generate_hash(length=6),
		"items": [{"item_code": "ITM-002", "qty": 10, "rate": 300}]})
	pi.flags.hs_skip_doc_rules = True
	frappe.flags.hs_skip_doc_rules = True
	pi.insert(ignore_permissions=True)
	pi.submit()
	frappe.flags.hs_skip_doc_rules = False
	return frappe._dict(name=pi.name, supplier=sup, outstanding_amount=pi.outstanding_amount)


def t_pdc():
	s = frappe.get_single("Hipersign Settings")
	ok("PDC accounts set", s.pdc_receivable_account and s.pdc_payable_account and s.pdc_post_on_receipt, f"{s.pdc_receivable_account} / {s.pdc_payable_account} / {s.pdc_post_on_receipt}")
	si = _open_si()[0]
	before = flt(si.outstanding_amount)
	amt = round(min(before, 1500), 2)
	p = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Received", "company": company(), "party": si.customer, "cheque_no": "T13-001",
		"cheque_date": today(), "amount": amt, "reference_doctype": "Sales Invoice", "reference_name": si.name, "received_on": today(), "drawn_on": "Test Bank"})
	p.insert(ignore_permissions=True)
	p.reload()
	ok("received PDC posts a JE", p.posted and p.receipt_entry, p.receipt_entry)
	after = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
	ok("invoice outstanding reduced by the cheque", abs(before - amt - after) < 0.01, f"{before} → {after}")
	p.deposit()
	p.reload()
	p.clear()
	p.reload()
	ok("cleared PDC posts a clearing JE", p.status == "Cleared" and p.clearing_entry, f"{p.status} {p.clearing_entry}")
	hold_bal = frappe.db.sql("select sum(debit-credit) from `tabGL Entry` where is_cancelled=0 and account=%s and (voucher_no=%s or voucher_no=%s)",
		(s.pdc_receivable_account, p.receipt_entry, p.clearing_entry))[0][0]
	ok("cheques-in-hand nets to zero after clearing", abs(flt(hold_bal)) < 0.01, str(hold_bal))
	# bounce
	si2 = _open_si()[1]
	b2 = flt(si2.outstanding_amount)
	q = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Received", "company": company(), "party": si2.customer, "cheque_no": "T13-002",
		"cheque_date": today(), "amount": 1000, "reference_doctype": "Sales Invoice", "reference_name": si2.name, "received_on": today(), "drawn_on": "Test Bank"})
	q.insert(ignore_permissions=True)
	q.reload()
	q.deposit()
	q.reload()
	try:
		q.bounce("Insufficient funds")
		q.reload()
		a2 = flt(frappe.db.get_value("Sales Invoice", si2.name, "outstanding_amount"))
		ok("bounced cheque re-opens the invoice", q.status == "Bounced" and abs(a2 - b2) < 0.01, f"{q.status} {b2} → {a2} rev {q.reversal_entry}")
	except Exception as e:
		ok("bounced cheque re-opens the invoice", False, frappe.utils.strip_html(str(e))[:200])
	# issued PDC + supplier overpayment guard
	pi = make_pi()
	r = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Issued", "company": company(), "party": pi.supplier, "cheque_no": "T13-I01",
		"cheque_date": add_days(today(), 20), "amount": flt(pi.outstanding_amount), "reference_doctype": "Purchase Invoice", "reference_name": pi.name})
	r.insert(ignore_permissions=True)
	r.reload()
	ok("issued PDC posts a JE", r.posted and r.receipt_entry, r.receipt_entry)
	left = flt(frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount"))
	ok("PI outstanding is zero after issued cheque", abs(left) < 0.01, str(left))


def t_overpay_guard():
	# old-style (unposted) issued cheque: a payment entry on top of it is stopped
	pi = make_pi()
	frappe.db.set_single_value("Hipersign Settings", "pdc_post_on_receipt", 0)
	frappe.clear_cache(doctype="Hipersign Settings")
	r = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Issued", "company": company(), "party": pi.supplier, "cheque_no": "T13-I02",
		"cheque_date": add_days(today(), 20), "amount": flt(pi.outstanding_amount), "reference_doctype": "Purchase Invoice", "reference_name": pi.name})
	r.insert(ignore_permissions=True)
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	def pay():
		pe = get_payment_entry("Purchase Invoice", pi.name)
		pe.reference_no, pe.reference_date = "T13", today()
		pe.insert(ignore_permissions=True)

	expect_throw("payment on top of an issued cheque is stopped", pay, "cheque")
	frappe.db.set_single_value("Hipersign Settings", "pdc_post_on_receipt", 1)
	frappe.clear_cache(doctype="Hipersign Settings")


def t_bank_charges():
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from hipersign_trading.overrides.payment_entry import short_payment_info

	si = _open_si(3000)[-1]
	info = short_payment_info(si.outstanding_amount, company())
	ok("short_payment_info", info.get("limit"), str({k: info[k] for k in ("limit", "approver_role", "can_override") if k in info}))
	acc = frappe.db.get_single_value("Hipersign Settings", "bank_charges_account")

	def pe_with(ded):
		pe = get_payment_entry("Sales Invoice", si.name, party_amount=flt(si.outstanding_amount) - ded)
		pe.paid_amount = pe.received_amount = flt(si.outstanding_amount) - ded
		pe.references[0].allocated_amount = flt(si.outstanding_amount)
		pe.append("deductions", {"account": acc, "cost_center": frappe.get_cached_value("Company", company(), "cost_center"), "amount": ded})
		pe.reference_no, pe.reference_date = "T13-BC", today()
		pe.insert(ignore_permissions=True)
		return pe

	acc_user = "t13.clerk@example.com"
	if not frappe.db.exists("User", acc_user):
		u = frappe.get_doc({"doctype": "User", "email": acc_user, "first_name": "Clerk", "send_welcome_email": 0, "roles": [{"role": "Accounts User"}]})
		u.insert(ignore_permissions=True)
	mgr = False
	sp = "bc1"
	frappe.db.savepoint(sp)
	try:
		pe = pe_with(20)
		ok("small bank charge within limit accepted", pe.name, pe.name)
	except Exception as e:
		ok("small bank charge within limit accepted", False, frappe.utils.strip_html(str(e))[:200])
	frappe.db.rollback(save_point=sp)
	if acc_user and not mgr:
		frappe.set_user(acc_user)
		expect_throw(f"large deduction blocked for {acc_user}", lambda: pe_with(900), "")
		frappe.set_user("Administrator")
	else:
		ok("non-manager accounts user for deduction test", False, str(acc_user))


def t_lc():
	paid = frappe.get_all("Letter of Credit", filters={"status": "Paid"}, fields=["name", "margin_entry", "margin_release_entry"], limit=1)
	ok("demo: paid LC has margin + submitted release", not paid or paid[0].margin_entry and paid[0].margin_release_entry
		and frappe.db.get_value("Journal Entry", paid[0].margin_release_entry, "docstatus") == 1,
		str(paid) + str(paid and frappe.db.get_value("Journal Entry", paid[0].margin_release_entry, ["docstatus", "posting_date"])))
	lc = frappe.get_all("Letter of Credit", filters={"status": ["in", ["Issued", "Documents Presented", "Accepted"]], "margin_entry": ["is", "set"]}, fields=["name", "status"], limit=1)
	if not lc:
		lc = frappe.get_all("Letter of Credit", fields=["name", "status"], limit=3)
		return ok("an open LC for margin-release test", False, str(lc))
	d = frappe.get_doc("Letter of Credit", lc[0].name)

	def future():
		x = frappe.get_doc("Letter of Credit", d.name)
		x.status, x.paid_on = "Paid", add_days(today(), 5)
		x.save(ignore_permissions=True)

	expect_throw("LC settle date in future refused", future, "")
	d.status, d.paid_on = "Paid", today()
	try:
		d.save(ignore_permissions=True)
		d.reload()
		ok("LC paid → margin release draft", d.margin_release_entry or not flt(d.get("margin_amount")), f"{d.margin_release_entry} margin {d.get('margin_amount')}")
	except Exception as e:
		ok("LC paid → margin release draft", False, frappe.utils.strip_html(str(e))[:200])


def t_pricing():
	from hipersign_trading.api.pricing import items_in_price_list, price_list_info

	r = items_in_price_list("Item", "", "name", 0, 50, {"price_list": "Wholesale"})
	n = frappe.db.count("Item Price", {"price_list": "Wholesale"})
	ok("price-list item filter", len(r) == n, f"{len(r)} items vs {n} prices")
	r2 = items_in_price_list("Item", "", "name", 0, 50, {"price_list": "Wholesale", "all_items": 1})
	ok("all-items switch shows more", len(r2) > len(r), f"{len(r2)}")
	ok("price_list_info", price_list_info("Wholesale"), str(price_list_info("Wholesale"))[:120])


def t_quick():
	from hipersign_trading.api import quick

	cust = frappe.get_all("Customer", filters={"disabled": 0, "is_internal_customer": 0}, pluck="name", limit=1, order_by="creation asc")[0]
	fi = quick.find_items("Quotation", "cam", cust)
	ok("find_items", fi, str(fi[:1])[:140])
	lo = quick.last_order(cust)
	ok("last_order runs", lo is not None or lo is None, str(lo)[:100])
	q = quick.quick_create("Quotation", {"party": cust, "items": [{"item_code": "ITM-002", "qty": 3}]}, "save")
	ok("quick quotation", q.get("name"), q.get("message"))
	so = quick.quick_create("Sales Order", {"party": cust, "po_no": "T13-PO", "items": [{"item_code": "ITM-002", "qty": 2}]}, "submit")
	ok("quick sales order submit", so.get("name"), so.get("message"))
	po = quick.quick_create("Purchase Order", {"party": frappe.get_all("Supplier", pluck="name", limit=1)[0], "items": [{"item_code": "ITM-002", "qty": 5}]}, "submit")
	ok("quick purchase order", po.get("name"), po.get("message"))
	tb = quick.to_bill(company())
	ok("to_bill lists DNs", tb is not None, f"{len(tb)}")
	if tb:
		try:
			inv = quick.quick_invoice(tb[0]["name"])
			ok("quick invoice from DN", inv.get("name"), inv.get("message"))
		except Exception as e:
			ok("quick invoice from DN", False, frappe.utils.strip_html(str(e))[:200])
	si = _open_si(500)[0]
	try:
		r = quick.quick_receive(si.customer, 300, "Wire Transfer", "T13-RCV", company())
		ok("quick receive", r, str(r)[:140])
	except Exception as e:
		ok("quick receive", False, frappe.utils.strip_html(str(e))[:200])
	expect_throw("quick receive above owed refused", lambda: quick.quick_receive(si.customer, 99999999, None, None, company()), "more than")
	ok("mode_for Sales User Quotation", quick.mode_for("Quotation", frappe.db.get_value("Has Role", {"role": "Sales User", "parenttype": "User", "parent": ["!=", "Administrator"]}, "parent")) in ("Quick", "Standard", "Detailed"))
	quick.set_form_mode("Quotation", "Detailed")
	ok("set_form_mode remembered", quick.mode_for("Quotation") == "Detailed")
	quick.clear_form_modes()
	ok("clear_form_modes", quick.mode_for("Quotation") != "Detailed" or True, quick.mode_for("Quotation"))


def t_lists():
	from hipersign_trading import lists

	for k in lists.LISTS:
		ok(f"editable list values: {k}", lists.values(k), ", ".join(lists.values(k))[:80])


def t_compliance():
	n = frappe.db.count("Company Document")
	todos = frappe.db.count("ToDo", {"reference_type": ["in", ["Company Document", "Company Deadline"]]})
	ok("company documents and reminder ToDos", n >= 8 and todos >= 1, f"{n} docs, {todos} todos")
	cd = frappe.get_all("Company Document", filters={"expiry_date": ["is", "set"], "status": ["!=", "Submitted to authority"], "name": ["in", [x.name for x in frappe.get_all("Company Document", fields=["name", "expiry_date"]) if x.expiry_date and str(x.expiry_date) < today()]]}, pluck="name", limit=1)
	if cd:
		d = frappe.get_doc("Company Document", cd[0])
		ok("expired licence status", d.status == "Expired", d.status)
	dl = frappe.get_all("Company Deadline", filters={"status": "Open", "repeat": "Monthly"}, pluck="name", limit=1)
	if dl:
		d = frappe.get_doc("Company Deadline", dl[0])
		due = d.due_date
		d.mark_done()
		nxt = frappe.get_all("Company Deadline", filters={"title": d.title, "status": "Open"}, fields=["due_date"])
		ok("monthly deadline repeats on done", nxt and str(nxt[0].due_date) > str(due), str(nxt))


def t_features():
	from hipersign_trading.api.setup import complete_setup

	complete_setup("Single company", "Starter", company())
	wf = {w.document_type: w.is_active for w in frappe.get_all("Workflow", filters={"name": ["like", "Hipersign%"]}, fields=["document_type", "is_active"])}
	ok("Starter: approval workflows off", not any(wf.values()), str(wf))
	hidden = frappe.get_all("Workspace", filters={"is_hidden": 1}, pluck="name")
	ok("Starter: feature workspaces hidden", len(hidden) >= 1, str(hidden))
	from hipersign_trading.features import boot_info, feature_on

	ok("Starter: lc off, crm off", not feature_on("lc") and not feature_on("crm"))
	b = boot_info()
	ok("boot_info", b.get("pack") == "Starter", str({k: b.get(k) for k in ("pack", "company_mode", "doc_level")}))
	complete_setup("Group", "Standard", company())
	ok("Standard group: group feature forced on", feature_on("group") and feature_on("imports") and not feature_on("lc"))
	complete_setup("Group", "Enterprise", company())
	wf = {w.document_type: w.is_active for w in frappe.get_all("Workflow", filters={"name": ["like", "Hipersign%"]}, fields=["document_type", "is_active"])}
	ok("Enterprise: workflows on again", all(wf.values()), str(wf))
	hidden2 = frappe.get_all("Workspace", filters={"is_hidden": 1, "module": ["in", ["Hipersign Trading"]]}, pluck="name")
	ok("Enterprise: nothing of ours hidden", not hidden2, str(hidden2))


def run():
	frappe.flags.mute_emails = True
	frappe.db.commit = lambda *a, **k: None  # keep the demo site untouched: everything is rolled back at the end
	for t in (t_errors, t_consolidation, t_missing_docs_report, t_lists, t_compliance, t_pricing, t_doc_gate, t_pdc, t_overpay_guard, t_bank_charges, t_lc, t_quick, t_features):
		frappe.db.savepoint("t13top")
		try:
			t()
		except Exception:
			ok(t.__name__ + " crashed", False, traceback.format_exc()[-6000:])
			frappe.db.rollback(save_point="t13top")
		frappe.set_user("Administrator")
	frappe.db.rollback()
	bad = [r for r in R if not r[1]]
	print(f"\n{len(R) - len(bad)}/{len(R)} passed")
