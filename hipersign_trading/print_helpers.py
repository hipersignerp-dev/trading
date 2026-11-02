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
			parts = []
			for x in [a.address_line1, a.address_line2, a.city, a.country]:
				x = (x or "").strip()
				if x == "United Arab Emirates":
					x = "UAE"  # as printed on the prototype's documents
				if x and x not in parts:
					parts.append(x)
			address = ", ".join(parts)
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
	for r in rows:  # SWIFT / BIC sits on the Bank master
		r.swift = (r.bank and frappe.db.get_value("Bank", r.bank, "swift_number")) or ""
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


# ---------------------------------------------------------------- v1.8.0: project prints
def hs_project_info(project):
	"""The project block on the project prints: client, consultant, contract, retention, advance, revised value, terms."""
	if not project or not frappe.db.exists("Project", project):
		return frappe._dict()
	p = frappe.get_doc("Project", project)
	cust = frappe.db.get_value("Customer", p.customer, ["customer_name", "tax_id"], as_dict=True) if p.customer else None
	vo = sum(frappe.utils.flt(v.amount) for v in frappe.get_all("Variation Order", filters={"project": project, "status": "Approved"}, fields=["amount"]))
	return frappe._dict(name=p.name, title=p.project_name, client=(cust and cust.customer_name) or p.customer or "", client_trn=(cust and cust.tax_id) or "",
		consultant=p.get("hs_consultant") or "", location=p.get("hs_location") or "", contract=frappe.utils.flt(p.get("hs_contract_value")), variations=vo,
		revised=frappe.utils.flt(p.get("hs_contract_value")) + vo, retention=frappe.utils.flt(p.get("hs_retention_pct")), advance=frappe.utils.flt(p.get("hs_advance_pct")),
		dlp=p.get("hs_dlp_months") or 12, terms=p.get("hs_payment_terms") or "", pm=p.get("hs_project_manager") or "", qs=p.get("hs_quantity_surveyor") or "",
		start=p.expected_start_date, finish=p.expected_end_date, programme_days=frappe.utils.date_diff(p.expected_end_date, p.expected_start_date) if p.expected_start_date and p.expected_end_date else 0,
		company=p.company)


def hs_boq_sections(doc):
	"""The BOQ lines grouped by section, with each section's total."""
	out = []
	for r in doc.get("items") or []:
		if not out or out[-1].code != r.section:
			out.append(frappe._dict(code=r.section, name=r.section_name or "", lines=[], total=0))
		out[-1].lines.append(r)
		out[-1].total += frappe.utils.flt(r.amount)
	return out
