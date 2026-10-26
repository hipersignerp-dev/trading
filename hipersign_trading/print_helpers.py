"""Helpers available inside the Hipersign print formats (Jinja)."""

import frappe


def hs_company(company=None):
	company = company or frappe.defaults.get_global_default("company")
	c = frappe.get_cached_doc("Company", company) if company else None
	address = ""
	if c:
		addr = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
			"parent",
		)
		if addr:
			a = frappe.get_cached_doc("Address", addr)
			address = ", ".join(x for x in [a.address_line1, a.address_line2, a.city, a.country] if x)
	return frappe._dict(
		name=company or "",
		name_ar=(c and c.get("company_name_in_arabic")) or "",
		trn=(c and c.tax_id) or "",
		address=address,
		logo="/assets/hipersign_trading/images/hipersign-logo.png",
	)


def hs_arabic_name(item_code):
	return frappe.db.get_value("Item", item_code, "hs_item_name_ar") or ""


def hs_party_contact(doc):
	name = doc.get("contact_display") or ""
	mobile = doc.get("contact_mobile") or ""
	return frappe._dict(name=name, mobile=mobile, email=doc.get("contact_email") or "")


def hs_default_bank(currency=None, company=None):
	filters = {"is_company_account": 1, "disabled": 0}
	if company:
		filters["company"] = company
	rows = frappe.get_all(
		"Bank Account",
		filters=filters,
		fields=["bank", "account_name", "iban", "is_default", "account"],
		order_by="is_default desc",
	)
	if currency:
		for r in rows:
			acc_cur = r.account and frappe.db.get_value("Account", r.account, "account_currency")
			if acc_cur == currency:
				return r
	return rows[0] if rows else frappe._dict()


def hs_is_export(customer):
	return frappe.db.get_value("Customer", customer, "hs_market") == "Export"


def hs_serials(row):
	"""Serial numbers of a transaction row as a compact string (bundle in v15+, text field before)."""
	serials = []
	if row.get("serial_and_batch_bundle") and frappe.db.table_exists("Serial and Batch Entry"):
		serials = frappe.get_all("Serial and Batch Entry", filters={"parent": row.serial_and_batch_bundle}, pluck="serial_no", order_by="serial_no")
	elif row.get("serial_no"):
		serials = [s.strip() for s in row.serial_no.split("\n") if s.strip()]
	serials = [s for s in serials if s]
	if len(serials) > 6:
		return f"{serials[0]} → {serials[-1]} ({len(serials)} units)"
	return ", ".join(serials)


def hs_warranty_months(item_code):
	days = frappe.get_cached_value("Item", item_code, "warranty_period")
	return round(int(days) / 30.4) if days else 0
