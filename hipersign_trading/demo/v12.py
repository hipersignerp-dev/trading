"""v1.2 demo data: master-record details, KYC, advances and payment schedules, collections, purchase requests and
supplier quotations, stock reservation and picking, letters of credit and guarantees, VAT return filing,
month-end revaluation, and group companies with an inter-company invoice.

Every step is idempotent and runs in its own savepoint (see demo/__init__.py → run).
"""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, today

from hipersign_trading.demo import data as D


def _demo():
	from hipersign_trading import demo

	return demo


# ------------------------------------------------------------------ masters
def v12_masters(c):
	from hipersign_trading.api.serials import warranty_days

	g = _demo().get_or_insert
	if not frappe.db.exists("Sales Person", "Sales Team"):
		g({"doctype": "Sales Person", "sales_person_name": "Sales Team", "is_group": 1, "parent_sales_person": ""}, {"name": "Sales Team"})
	for p in D.SALES_PERSONS:
		g({"doctype": "Sales Person", "sales_person_name": p, "parent_sales_person": "Sales Team", "is_group": 0}, {"name": p})
	for t in D.TERRITORIES:
		g({"doctype": "Territory", "territory_name": t, "parent_territory": "All Territories", "is_group": 0}, {"name": t})
	for u in ["Carton", "Bundle", "Kg"]:
		g({"doctype": "UOM", "uom_name": u}, {"name": u})

	for code, (brand, model, puom, conv, kg, months, moq, lead, supplier) in D.ITEM_MASTER.items():
		if not frappe.db.exists("Item", code):
			continue
		g({"doctype": "Brand", "brand": brand}, {"name": brand})
		it = frappe.get_doc("Item", code)
		it.brand, it.hs_model = brand, model
		it.weight_per_unit, it.weight_uom = kg, "Kg"
		it.min_order_qty = moq
		if lead:
			it.lead_time_days = lead
		if months and not it.warranty_period:
			it.warranty_period = str(warranty_days(months))
		if puom != it.stock_uom and conv > 1:
			if not any(r.uom == puom for r in it.uoms):
				it.append("uoms", {"uom": puom, "conversion_factor": conv})
			it.purchase_uom = puom
		if frappe.db.exists("Supplier", supplier):
			row = next((r for r in it.item_defaults if r.company == c.company), None) or it.append("item_defaults", {"company": c.company})
			row.default_supplier = supplier
		it.save()

	for name, (web, sp, lic, auth, exp, status) in D.CUSTOMER_MASTER.items():
		if not frappe.db.exists("Customer", name):
			continue
		cu = frappe.get_doc("Customer", name)
		city = frappe.db.get_value("Address", cu.customer_primary_address, "city") if cu.customer_primary_address else None
		country = frappe.db.get_value("Address", cu.customer_primary_address, "country") if cu.customer_primary_address else None
		cu.territory = (D.EXPORT_TERRITORY.get(country, "Rest of World") if cu.get("hs_market") == "Export"
			else D.EMIRATE_TERRITORY.get(city, "Northern Emirates"))
		cu.website = web or cu.website
		if not cu.get("sales_team"):
			cu.append("sales_team", {"sales_person": sp, "allocated_percentage": 100})
		cu.hs_trade_licence_no, cu.hs_licence_authority, cu.hs_trade_licence_expiry = lic, auth, c.d(exp)
		cu.hs_kyc_status = status
		if status == "Blocked":
			cu.hs_kyc_notes = "Trade licence expired — renewal copy requested on WhatsApp"
		cu.save()

	for name, (lead, web, reg, exp) in D.SUPPLIER_MASTER.items():
		if not frappe.db.exists("Supplier", name):
			continue
		s = frappe.get_doc("Supplier", name)
		s.hs_lead_time_days, s.website = lead, web
		s.hs_trade_licence_no, s.hs_trade_licence_expiry, s.hs_kyc_status = reg, c.d(exp), "Verified"
		s.save()


# ------------------------------------------------------------------ advances & payment schedules
def _so_with_terms(c, customer, lines, days_ago, po_no, template):
	demo = _demo()
	items_, cur, fx = demo.so_lines(c, customer, lines)
	so = frappe.get_doc({"doctype": "Sales Order", "customer": customer, "company": c.company, "po_no": po_no, "currency": cur,
		"conversion_rate": fx, "selling_price_list": c.get("selling_pl") or "Standard Selling", "price_list_currency": "AED", "plc_conversion_rate": 1,
		"ignore_pricing_rule": 1, "delivery_date": c.d(-days_ago + 10), "payment_terms_template": template, "items": items_})
	for i in so.items:
		i.delivery_date = c.d(-days_ago + 10)
	demo.backdate(so, c.d(-days_ago))
	so.insert()
	so.submit()
	return so


def v12_advances(c):
	for term in ("Advance 30%", "Advance 50%"):
		if frappe.db.exists("Payment Term", term):
			frappe.db.set_value("Payment Term", term, "hs_is_advance", 1)
	if frappe.db.exists("Sales Order", {"po_no": "FB/PO/0951"}):
		return
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from hipersign_trading.overrides.advances import position, refresh

	# 1. Future Build — 30% advance received, order released for delivery
	so = _so_with_terms(c, "Future Build", [("ITM-004", 20), ("ITM-010", 200)], 4, "FB/PO/0951", "30% advance, balance net 30")
	required, _received = position(so)
	pe = get_payment_entry("Sales Order", so.name, party_amount=required)
	pe.posting_date = c.d(-3)
	pe.reference_no, pe.reference_date = "TT/FB/0951", c.d(-3)
	pe.paid_amount = pe.received_amount = required
	if pe.references:
		pe.references[0].allocated_amount = required
	pe.insert()
	pe.submit()
	refresh(so.name)
	c.adv_so = so.name
	# 2. Al Noor — 50% advance terms, nothing received yet: delivery is on hold (test ADV-01)
	so2 = _so_with_terms(c, "Al Noor LLC", [("ITM-011", 50)], 4, "ANL/PO/7802", "50% advance, 50% on delivery")
	refresh(so2.name)
	c.held_so = so2.name


# ------------------------------------------------------------------ collections
def v12_collections(c):
	for name, days, text in D.DUNNING_TYPES:
		if not frappe.db.exists("Dunning Type", {"dunning_type": name, "company": c.company}):
			d = frappe.get_doc({"doctype": "Dunning Type", "dunning_type": name, "company": c.company, "dunning_fee": 0, "rate_of_interest": 0,
				"is_default": 1 if days == 7 else 0})
			if d.meta.has_field("dunning_letter_text"):
				d.append("dunning_letter_text", {"language": "en", "is_default_language": 1, "body_text": text,
					"closing_text": "If you have already paid, please ignore this reminder and send us the payment reference."})
			d.insert()
	inv = _demo().invoice_of("Gulf Projects", "GP-2026-311")
	if inv and not frappe.db.get_value("Sales Invoice", inv, "hs_promise_date"):
		out = flt(frappe.db.get_value("Sales Invoice", inv, "outstanding_amount"))
		frappe.db.set_value("Sales Invoice", inv, {"hs_promise_date": c.d(5), "hs_promise_amount": round(out / 2, -2),
			"hs_collection_note": "Ravi confirmed half by transfer next week, balance with the next project payment"}, update_modified=False)
	from hipersign_trading.tasks import collection_reminders

	collection_reminders()


# ------------------------------------------------------------------ purchase requests & supplier quotations
def v12_purchasing(c):
	if frappe.db.exists("Material Request", {"title": ["like", "%Ceiling speakers restock%"]}):
		return
	mr = frappe.get_doc({"doctype": "Material Request", "material_request_type": "Purchase", "company": c.company, "title": "Ceiling speakers restock",
		"transaction_date": c.d(-6), "schedule_date": c.d(40),
		"items": [{"item_code": "ITM-006", "qty": 2000, "schedule_date": c.d(40), "warehouse": c.wh("Main Warehouse")},
			{"item_code": "ITM-002", "qty": 1000, "schedule_date": c.d(40), "warehouse": c.wh("Main Warehouse")}]})
	mr.insert()
	mr.submit()
	from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

	rfq = make_request_for_quotation(mr.name)
	rfq.transaction_date = c.d(-5)
	rfq.message_for_supplier = "Please quote your best FOB price and production lead time for the items below."
	rfq.set("suppliers", [])
	for sup in ("Shenzhen Brightway Electronics", "Global Supplies Co. Ltd"):
		rfq.append("suppliers", {"supplier": sup, "email_id": frappe.db.get_value("Supplier", sup, "email_id"), "send_email": 0})
	rfq.insert()
	rfq.submit()
	from erpnext.buying.doctype.request_for_quotation.request_for_quotation import make_supplier_quotation_from_rfq

	for sup, factor, lead in (("Shenzhen Brightway Electronics", 0.94, 40), ("Global Supplies Co. Ltd", 0.98, 30)):
		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=sup)
		sq.transaction_date, sq.valid_till = c.d(-2), c.d(28)
		cur = frappe.db.get_value("Supplier", sup, "default_currency") or "AED"
		sq.currency = cur
		sq.conversion_rate = 1 if cur == "AED" else D.FX[cur]
		for row in sq.items:
			cost = flt(frappe.db.get_value("Item", row.item_code, "valuation_rate"))
			row.rate = flt(cost * factor / sq.conversion_rate, 2)
			if row.meta.has_field("lead_time_days"):
				row.lead_time_days = lead
		sq.insert()
		sq.submit()


# ------------------------------------------------------------------ reservations & picking
def v12_reservations(c):
	ss = frappe.get_meta("Stock Settings")
	if ss.has_field("enable_stock_reservation"):
		frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", 1)
	so_name = c.get("adv_so") or frappe.db.get_value("Sales Order", {"po_no": "FB/PO/0951", "docstatus": 1})
	if not so_name:
		return
	if frappe.db.table_exists("Stock Reservation Entry") and not frappe.db.exists("Stock Reservation Entry", {"voucher_no": so_name}):
		so = frappe.get_doc("Sales Order", so_name)
		for i in so.items:
			if not i.warehouse:
				i.db_set("warehouse", frappe.db.get_value("Item Default", {"parent": i.item_code, "company": c.company}, "default_warehouse"))
		so.reload()
		so.create_stock_reservation_entries()
	if not frappe.db.exists("Pick List Item", {"sales_order": so_name}):
		from erpnext.selling.doctype.sales_order.sales_order import create_pick_list

		pl = create_pick_list(so_name)
		pl.insert()


# ------------------------------------------------------------------ letters of credit & bank guarantees
def _account(c, name, root_type, account_type=""):
	acc = frappe.db.get_value("Account", {"company": c.company, "account_name": name, "is_group": 0})
	if acc:
		return acc
	like = "%Current Assets%" if root_type == "Asset" else "%Current Liabilities%"
	parent = frappe.db.get_value("Account", {"company": c.company, "root_type": root_type, "is_group": 1, "account_name": ["like", like]}) or frappe.db.get_value(
		"Account", {"company": c.company, "root_type": root_type, "is_group": 1}, order_by="lft desc")
	return frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent, "company": c.company, "root_type": root_type,
		"account_type": account_type}).insert().name


def v12_trade_finance(c):
	s = frappe.get_single("Hipersign Settings")
	s.lc_margin_account = s.lc_margin_account or _account(c, "LC Margin Deposits", "Asset")
	s.trust_receipt_account = s.trust_receipt_account or _account(c, "Trust Receipt Loans", "Liability")
	s.save()
	if frappe.db.exists("Letter of Credit", {"lc_number": "ENBD-ILC-26-0418"}):
		return
	po_eur = frappe.db.get_value("Purchase Order", {"supplier": "EuroSafe Systems GmbH", "docstatus": 1}, ["name", "currency", "grand_total", "conversion_rate"], as_dict=True)
	if po_eur:
		frappe.get_doc({"doctype": "Letter of Credit", "lc_type": "Import", "supplier": "EuroSafe Systems GmbH", "purchase_order": po_eur.name,
			"company": c.company, "issuing_bank": "Emirates NBD", "lc_number": "ENBD-ILC-26-0418", "currency": po_eur.currency,
			"amount": po_eur.grand_total, "exchange_rate": po_eur.conversion_rate, "margin_pct": 10, "tolerance_pct": 5,
			"issue_date": c.d(-24), "latest_shipment_date": c.d(-5), "expiry_date": c.d(10), "tenor": "At sight", "status": "Issued",
			"charges": 1850, "remarks": "Documents: commercial invoice, packing list, certificate of origin, air waybill"}).insert()
	po_usd = frappe.db.get_value("Purchase Order", {"supplier": "Global Supplies Co. Ltd", "docstatus": 1, "per_received": ["<", 100]},
		["name", "currency", "grand_total", "conversion_rate"], as_dict=True)
	if po_usd:
		frappe.get_doc({"doctype": "Letter of Credit", "lc_type": "Import", "supplier": "Global Supplies Co. Ltd", "purchase_order": po_usd.name,
			"import_shipment": frappe.db.get_value("Import Shipment", {"bl_awb": "MSKU-YTN-2210377"}), "company": c.company, "issuing_bank": "Mashreq Bank",
			"lc_number": "MSQ-ILC-26-1107", "currency": po_usd.currency, "amount": po_usd.grand_total, "exchange_rate": po_usd.conversion_rate,
			"margin_pct": 15, "issue_date": c.d(-45), "latest_shipment_date": c.d(-30), "expiry_date": c.d(15), "tenor": "Usance 90 days",
			"status": "Accepted", "documents_presented_on": c.d(-6), "accepted_on": c.d(-4), "trust_receipt": 1, "tr_days": 90, "tr_rate": 7.25,
			"charges": 2400}).insert()
	if not frappe.db.exists("Bank Guarantee", {"bank_guarantee_number": "ENBD-PB-26-0091"}):
		bg = frappe.get_doc({"doctype": "Bank Guarantee", "bg_type": "Providing", "customer": "Dubai Municipality Projects",
			"amount": 92000, "start_date": c.d(-20), "validity": 365, "end_date": add_days(c.d(-20), 365), "bank": "Emirates NBD",
			"bank_guarantee_number": "ENBD-PB-26-0091", "name_of_beneficiary": "Dubai Municipality", "margin_money": 9200, "charges": 650})
		bg.insert()
		bg.submit()


# ------------------------------------------------------------------ VAT return filing
def v12_tax_returns(c):
	last_end = get_last_day(add_months(today(), -1))
	start = get_first_day(last_end)
	if frappe.db.exists("Tax Return", {"company": c.company, "tax_type": "VAT 201", "period_from": start}):
		return
	r = frappe.get_doc({"doctype": "Tax Return", "tax_type": "VAT 201", "company": c.company, "period_from": start, "period_to": last_end})
	r.insert()
	r.send_for_approval()


# ------------------------------------------------------------------ month-end revaluation
def v12_revaluation(c):
	month_end = get_last_day(add_months(today(), -1))
	for cur, rate in D.FX_MONTH_END.items():
		if not frappe.db.exists("Currency Exchange", {"from_currency": cur, "to_currency": "AED", "date": month_end}):
			frappe.get_doc({"doctype": "Currency Exchange", "date": month_end, "from_currency": cur, "to_currency": "AED", "exchange_rate": rate,
				"for_buying": 1, "for_selling": 1}).insert()
	for cur, rate in D.FX_TODAY.items():
		if not frappe.db.exists("Currency Exchange", {"from_currency": cur, "to_currency": "AED", "date": today()}):
			frappe.get_doc({"doctype": "Currency Exchange", "date": today(), "from_currency": cur, "to_currency": "AED", "exchange_rate": rate,
				"for_buying": 1, "for_selling": 1}).insert()
	co = frappe.get_doc("Company", c.company)
	if not co.get("unrealized_exchange_gain_loss_account") and co.get("exchange_gain_loss_account"):
		frappe.db.set_value("Company", c.company, "unrealized_exchange_gain_loss_account", co.exchange_gain_loss_account)
	if frappe.db.exists("Exchange Rate Revaluation", {"company": c.company, "posting_date": month_end}):
		return
	err = frappe.get_doc({"doctype": "Exchange Rate Revaluation", "company": c.company, "posting_date": month_end})
	try:
		rows = err.get_accounts_data() or []
	except frappe.ValidationError:
		frappe.clear_last_message()
		rows = []  # no foreign-currency balances at month end
	if rows:
		err.set("accounts", rows)
		err.insert()  # left as a draft for the Finance Manager to review and submit (test FX-01)


# ------------------------------------------------------------------ group companies & inter-company
def _company(name, abbr, currency, country, parent=None, is_group=0):
	if frappe.db.exists("Company", name):
		return frappe.get_doc("Company", name)
	return frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbr, "default_currency": currency, "country": country,
		"is_group": is_group, "parent_company": parent, "create_chart_of_accounts_based_on": "Standard Template",
		"chart_of_accounts": "Standard"}).insert()


def v12_group(c):
	holding, habbr = D.GROUP["holding"]
	_company(holding, habbr, "AED", "United Arab Emirates", is_group=1)
	main = frappe.get_doc("Company", c.company)
	if main.parent_company != holding:
		main.parent_company = holding
		main.hs_ownership_pct, main.hs_group_role, main.hs_licence_no = 100, "Mainland trading — imports, local sales and exports", "DED 845512"
		main.save()
	for name, abbr, cur, country, own, partner, role, lic in D.GROUP["companies"]:
		co = _company(name, abbr, cur, country, parent=holding)
		co.hs_ownership_pct, co.hs_minority_partner, co.hs_group_role, co.hs_licence_no = own, partner, role, lic
		co.save()
	fze = D.GROUP["companies"][0][0]
	# FZE as an inter-company customer of the LLC, and the LLC as an inter-company supplier of the FZE
	if not frappe.db.exists("Customer", fze):
		frappe.get_doc({"doctype": "Customer", "customer_name": fze, "customer_type": "Company", "customer_group": "Wholesale", "territory": "Dubai",
			"is_internal_customer": 1, "represents_company": fze, "companies": [{"company": c.company}], "hs_market": "Local",
			"hs_kyc_status": "Verified", "payment_terms": "Net 60 days"}).insert()
	if not frappe.db.exists("Supplier", c.company):
		frappe.get_doc({"doctype": "Supplier", "supplier_name": c.company, "supplier_group": "Goods Suppliers", "country": "United Arab Emirates",
			"is_internal_supplier": 1, "represents_company": c.company, "companies": [{"company": fze}], "hs_kyc_status": "Verified"}).insert()
	pl = "Inter-company"
	if not frappe.db.exists("Price List", pl):
		frappe.get_doc({"doctype": "Price List", "price_list_name": pl, "currency": "AED", "buying": 1, "selling": 1, "enabled": 1}).insert()
	if frappe.db.exists("Sales Invoice", {"customer": fze, "docstatus": 1}):
		return
	markup = flt(frappe.db.get_single_value("Hipersign Settings", "intercompany_markup") or 8)
	si = frappe.get_doc({"doctype": "Sales Invoice", "customer": fze, "company": c.company, "selling_price_list": pl, "currency": "AED",
		"posting_date": c.d(-9), "set_posting_time": 1, "due_date": c.d(51), "taxes_and_charges": c.get("local_tax") or frappe.db.get_single_value("Hipersign Settings", "local_tax_template"),
		"remarks": f"Inter-company services at cost + {markup:g}%",
		"items": [{"item_code": "SRV-005", "qty": 40, "rate": flt(90 * (1 + markup / 100), 2)}, {"item_code": "SRV-004", "qty": 2, "rate": flt(380 * (1 + markup / 100), 2)}]})
	si.set_missing_values()
	si.set("taxes", [])
	if si.taxes_and_charges:
		si.append_taxes_from_master()
	si.insert()
	si.submit()
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice

	pi = make_inter_company_purchase_invoice(si.name)
	pi.posting_date, pi.set_posting_time, pi.bill_no, pi.bill_date = c.d(-8), 1, si.name, c.d(-9)
	pi.insert()
	pi.submit()
