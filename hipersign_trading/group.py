"""Group companies and consolidation (Phase 4).

Each country runs its own site; the group site holds a Hipersign Group Member per company:
a company on this site, or another site reached with an API key. Every night (or with
“Sync trial balance”) the member's trial balance up to a date is copied into a Group Trial Balance.

The Hipersign Group Consolidation report translates every member into the presentation currency —
income and expenses at the average rate of the year, assets and liabilities at the closing rate,
share capital and opening retained earnings at the rate at the start of the year — puts the
difference into the translation reserve (CTA), removes inter-company balances (accounts ticked
“Inter-company” on the Account) and shows the minority (non-controlling) share for members owned
less than 100%.
"""

import frappe
import requests
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, now_datetime, today

RE_KEY = "__retained__"


def _short(account, company):
	abbr = frappe.get_cached_value("Company", company, "abbr") if company and frappe.db.exists("Company", company) else None
	if abbr and account.endswith(" - " + abbr):
		return account[: -len(" - " + abbr)]
	return account.rsplit(" - ", 1)[0] if " - " in account else account


def trial_balance(company, period_end):
	"""Leaf-account trial balance for the financial year to period_end, in the company currency."""
	from erpnext.accounts.utils import get_fiscal_year

	period_end = getdate(period_end)
	try:
		fy_start = getdate(get_fiscal_year(period_end, company=company)[1])
	except Exception:
		fy_start = getdate(f"{period_end.year}-01-01")
	accounts = frappe.get_all("Account", filters={"company": company, "is_group": 0},
		fields=["name", "account_name", "root_type", "report_type", "account_type", "hs_intercompany"] if frappe.get_meta("Account").has_field("hs_intercompany")
		else ["name", "account_name", "root_type", "report_type", "account_type"])
	gl = frappe.qb.DocType("GL Entry")
	from frappe.query_builder.functions import Sum

	def sums(cond):
		q = (frappe.qb.from_(gl).select(gl.account, Sum(gl.debit).as_("dr"), Sum(gl.credit).as_("cr"))
			.where((gl.company == company) & (gl.is_cancelled == 0)).where(cond).groupby(gl.account))
		return {r[0]: (flt(r[1]), flt(r[2])) for r in q.run()}

	before = sums(gl.posting_date < fy_start)
	during = sums((gl.posting_date >= fy_start) & (gl.posting_date <= period_end))
	ic = intercompany_sums(company, fy_start, period_end)
	rows, prior_pl = [], 0.0
	for a in accounts:
		b = before.get(a.name, (0, 0))
		d = during.get(a.name, (0, 0))
		if a.report_type == "Profit and Loss":
			prior_pl += b[0] - b[1]
			opening = 0.0
		else:
			opening = b[0] - b[1]
		closing = opening + d[0] - d[1]
		if not (opening or d[0] or d[1]):
			continue
		row = {"account": a.name, "account_name": _short(a.name, company), "root_type": a.root_type, "report_type": a.report_type,
			"opening": round(opening, 2), "debit": round(d[0], 2), "credit": round(d[1], 2), "closing": round(closing, 2),
			"period_movement": round(d[0] - d[1], 2), "is_intercompany": 1 if a.get("hs_intercompany") else 0}
		# v1.5.6 (GRP-03): the part of an ordinary account that comes from trading with a group company is split off as
		# its own inter-company row, so the consolidation eliminates it (the FZE sale and purchase used to stay in).
		part = ic.get(a.name)
		if part and not row["is_intercompany"]:
			ic_open, ic_dr, ic_cr = part if a.report_type != "Profit and Loss" else (0.0, part[1], part[2])
			ic_close = ic_open + ic_dr - ic_cr
			if abs(ic_close) > 0.004 or abs(ic_dr - ic_cr) > 0.004:
				rows.append({**row, "opening": round(ic_open, 2), "debit": round(ic_dr, 2), "credit": round(ic_cr, 2),
					"closing": round(ic_close, 2), "period_movement": round(ic_dr - ic_cr, 2), "is_intercompany": 1})
				for k, v in (("opening", ic_open), ("debit", ic_dr), ("credit", ic_cr), ("closing", ic_close), ("period_movement", ic_dr - ic_cr)):
					row[k] = round(row[k] - v, 2)
		rows.append(row)
	if abs(prior_pl) > 0.004:
		rows.append({"account": RE_KEY, "account_name": "Retained earnings (prior years)", "root_type": "Equity", "report_type": "Balance Sheet",
			"opening": round(prior_pl, 2), "debit": 0, "credit": 0, "closing": round(prior_pl, 2), "period_movement": 0, "is_intercompany": 0})
	return {"company": company, "currency": frappe.get_cached_value("Company", company, "default_currency"), "year_start": str(fy_start),
		"period_end": str(period_end), "rows": rows}


def intercompany_sums(company, fy_start, period_end):
	"""Per account: (opening, debit, credit) of entries with group companies, i.e. internal customers and suppliers.

	Balance-sheet accounts count the party's entries (receivable, payable); income and expense accounts count the
	lines of invoices made to an internal customer or from an internal supplier. VAT stays: it is real tax.
	"""
	out = {}
	party_rows = frappe.db.sql(
		"""select gle.account,
			sum(case when gle.posting_date < %(start)s then gle.debit - gle.credit else 0 end),
			sum(case when gle.posting_date >= %(start)s then gle.debit else 0 end),
			sum(case when gle.posting_date >= %(start)s then gle.credit else 0 end)
		from `tabGL Entry` gle
		where gle.company = %(company)s and gle.is_cancelled = 0 and gle.posting_date <= %(end)s and (
			(gle.party_type = 'Customer' and gle.party in (select name from `tabCustomer` where is_internal_customer = 1))
			or (gle.party_type = 'Supplier' and gle.party in (select name from `tabSupplier` where is_internal_supplier = 1)))
		group by gle.account""",
		{"company": company, "start": fy_start, "end": period_end},
	)
	for acc, o, dr, cr in party_rows:
		out[acc] = (flt(o), flt(dr), flt(cr))
	pl_rows = frappe.db.sql(
		"""select gle.account, 0, sum(gle.debit), sum(gle.credit)
		from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
		where gle.company = %(company)s and gle.is_cancelled = 0 and acc.report_type = 'Profit and Loss'
			and gle.posting_date between %(start)s and %(end)s and (
			(gle.voucher_type = 'Sales Invoice' and gle.voucher_no in (select name from `tabSales Invoice` where is_internal_customer = 1))
			or (gle.voucher_type = 'Purchase Invoice' and gle.voucher_no in (select name from `tabPurchase Invoice` where is_internal_supplier = 1)))
		group by gle.account""",
		{"company": company, "start": fy_start, "end": period_end},
	)
	for acc, o, dr, cr in pl_rows:
		out[acc] = (flt(o), flt(dr), flt(cr))
	return out


def sync_member(member, period_end=None):
	m = frappe.get_doc("Hipersign Group Member", member)
	period_end = str(getdate(period_end or today()))
	try:
		if m.company:
			tb = trial_balance(m.company, period_end)
		else:
			secret = m.get_password("api_secret", raise_exception=False)
			r = requests.get(m.site_url + "/api/method/hipersign_trading.api.group.trial_balance",
				params={"company": m.remote_company, "period_end": period_end},
				headers={"Authorization": f"token {m.api_key}:{secret}"}, timeout=60)
			r.raise_for_status()
			tb = r.json()["message"]
		name = frappe.db.get_value("Group Trial Balance", {"member": m.name, "period_end": period_end})
		doc = frappe.get_doc("Group Trial Balance", name) if name else frappe.new_doc("Group Trial Balance")
		doc.update({"member": m.name, "period_end": period_end, "currency": tb.get("currency") or m.currency, "year_start": tb.get("year_start"),
			"synced_on": now_datetime()})
		doc.set("accounts", tb["rows"])
		doc.save(ignore_permissions=True)
		msg = _("{0}: {1} accounts up to {2}").format(m.name, len(tb["rows"]), frappe.format(period_end, "Date"))
		m.db_set({"last_sync": now_datetime(), "sync_status": msg})
		return msg
	except Exception as e:
		m.db_set({"last_sync": now_datetime(), "sync_status": _("Failed: {0}").format(str(e)[:300])})
		frappe.log_error(title=f"Hipersign group sync: {m.name}")
		raise


def sync_all():
	from hipersign_trading.features import feature_on
	from hipersign_trading.utils import settings

	if not feature_on("group") or not settings().get("group_sync_daily"):
		return
	for m in frappe.get_all("Hipersign Group Member", filters={"active": 1}, pluck="name"):
		try:
			sync_member(m, today())
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()


# ---------------------------------------------------------------- translation
def rate(from_cur, to_cur, date):
	if from_cur == to_cur:
		return 1.0
	from erpnext.setup.utils import get_exchange_rate

	r = flt(get_exchange_rate(from_cur, to_cur, str(getdate(date))))
	if not r:
		inv = flt(get_exchange_rate(to_cur, from_cur, str(getdate(date))))
		r = 1 / inv if inv else 0
	if not r:
		r = _nearest_rate(from_cur, to_cur, date)
	return r or 1.0


def _nearest_rate(from_cur, to_cur, date):
	"""v1.6.0 (GRP-03): no rate on or before the date (e.g. the year start for equity) — use the nearest stored one,
	either way, rather than translating at 1."""
	for f, t, inv in ((from_cur, to_cur, False), (to_cur, from_cur, True)):
		row = frappe.db.sql("""select exchange_rate from `tabCurrency Exchange` where from_currency = %s and to_currency = %s
			order by abs(datediff(date, %s)) asc limit 1""", (f, t, getdate(date)))
		if row and flt(row[0][0]):
			return 1 / flt(row[0][0]) if inv else flt(row[0][0])
	return 0


def average_rate(from_cur, to_cur, start, end):
	if from_cur == to_cur:
		return 1.0
	d, vals = getdate(start), []
	while d <= getdate(end):
		vals.append(rate(from_cur, to_cur, min(get_last_day(d), getdate(end))))
		d = add_months(get_first_day(d), 1)
	return sum(vals) / len(vals) if vals else rate(from_cur, to_cur, end)


def consolidate(period_end, currency=None):
	"""Translated, eliminated group figures: lines by account name, a column per member."""
	from hipersign_trading.utils import settings

	currency = currency or settings().get("group_currency") or "AED"
	period_end = getdate(period_end)
	members, lines, notes, elim = [], {}, [], {}
	for m in frappe.get_all("Hipersign Group Member", filters={"active": 1}, fields=["name", "currency", "ownership_pct", "is_parent"], order_by="is_parent desc, member_name asc"):
		tbn = frappe.db.get_value("Group Trial Balance", {"member": m.name, "period_end": ["<=", period_end]}, "name", order_by="period_end desc")
		if not tbn:
			notes.append(_("{0}: no trial balance synced up to {1}").format(m.name, frappe.format(period_end, "Date")))
			continue
		tb = frappe.get_doc("Group Trial Balance", tbn)
		cur = tb.currency or m.currency
		ys = tb.year_start or f"{getdate(tb.period_end).year}-01-01"
		cl, av, hi = rate(cur, currency, tb.period_end), average_rate(cur, currency, ys, tb.period_end), rate(cur, currency, ys)
		if getdate(tb.period_end) != period_end:
			notes.append(_("{0}: latest trial balance is up to {1}").format(m.name, frappe.format(tb.period_end, "Date")))
		col = {"member": m.name, "currency": cur, "closing_rate": cl, "average_rate": av, "historical_rate": hi, "own": flt(m.ownership_pct or 100) / 100,
			"ic": {"Asset": 0.0, "Liability": 0.0, "Income": 0.0, "Expense": 0.0, "Equity": 0.0}, "profit": 0.0, "profit_local": 0.0}
		bs_total = 0.0
		for r in tb.accounts:
			if r.report_type == "Profit and Loss":
				amt = flt(r.period_movement or r.closing) * av
				col["profit"] += -amt
				col["profit_local"] += -flt(r.period_movement or r.closing)
			elif r.root_type == "Equity":
				amt = flt(r.closing) * hi
			else:
				amt = flt(r.closing) * cl
			key = (r.report_type, r.root_type, r.account_name)
			if r.is_intercompany:
				col["ic"][r.root_type] = col["ic"].get(r.root_type, 0) + amt
				elim[key] = elim.get(key, 0) - amt
			lines.setdefault(key, {})[m.name] = lines.get(key, {}).get(m.name, 0) + amt
			if r.report_type != "Profit and Loss":
				bs_total += amt
		# balance sheet: assets (Dr +) + liabilities/equity (Cr −) + profit for the year (Cr) must be zero; the rest is translation
		cta = round(-(bs_total - col["profit"]), 2)  # v1.5.6: no 2.9e-10 left over from the translation
		col["cta"] = cta
		lines.setdefault(("Balance Sheet", "Equity", "Current year profit"), {})[m.name] = -col["profit"]
		lines.setdefault(("Balance Sheet", "Equity", "Translation reserve (CTA)"), {})[m.name] = cta
		members.append(col)
	# minority interests
	for c in members:
		if c["own"] < 0.9999:
			net_assets = -sum(v.get(c["member"], 0) for k, v in lines.items() if k[1] == "Equity")
			nci = round(net_assets * (1 - c["own"]), 2)
			c["nci"] = nci
			c["nci_profit"] = round(c["profit"] * (1 - c["own"]), 2)
			notes.append(_("{0} is {1}% owned — minority share of net assets {2}, of profit {3}").format(
				c["member"], round(c["own"] * 100, 2), frappe.format(nci, {"fieldtype": "Currency", "options": currency}), frappe.format(c["nci_profit"], {"fieldtype": "Currency", "options": currency})))
	ic_mismatch = round(sum(sum(c["ic"].values()) for c in members), 2)
	if abs(ic_mismatch) > 0.004:
		elim[("Balance Sheet", "Equity", "Inter-company difference")] = ic_mismatch
	if members and abs(ic_mismatch) > 1:
		notes.append(_("Inter-company balances do not agree by {0} — check the accounts ticked Inter-company").format(
			frappe.format(ic_mismatch, {"fieldtype": "Currency", "options": currency})))
	return {"currency": currency, "members": members, "lines": lines, "elim": elim, "notes": notes, "ic_mismatch": ic_mismatch}
