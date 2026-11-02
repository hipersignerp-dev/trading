"""Helpers available inside the Hipersign print formats (Jinja)."""

import frappe
from frappe import _
from frappe.utils import flt


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


# ---------------------------------------------------------------- v1.8.0: manufacturing prints (English + Chinese)
# Code 128 (set B) bar widths, values 0–106 (106 = stop, with its final bar)
_C128 = ("212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 "
	"221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 "
	"112133 112331 132131 113123 113321 133121 313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 "
	"111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 "
	"411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112").split()


def hs_barcode(text, height=34, module=1.4, width=None):
	"""A Code 128 (B) barcode as inline SVG — the job ticket, the job cards and the finished-goods label carry one
	(width: the printed width in px, the bars scaled to it)."""
	text = "".join(ch for ch in str(text or "") if 32 <= ord(ch) <= 126)
	codes = [104] + [ord(ch) - 32 for ch in text]
	check = (codes[0] + sum(i * c for i, c in enumerate(codes[1:], 1))) % 103
	codes += [check, 106]
	x, bars = 10 * module, []
	for c in codes:
		for i, w in enumerate(_C128[c]):
			w = int(w) * module
			if i % 2 == 0:
				bars.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{height}"/>')
			x += w
	full = x + 10 * module
	w = flt(width) or full
	return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{(height + 13) * w / full:.0f}" viewBox="0 0 {full:.2f} {height + 13}" class="bc">'
		f'<rect width="100%" height="100%" fill="#fff"/><g fill="#0f1b3d">{"".join(bars)}</g>'
		f'<text x="{full / 2:.2f}" y="{height + 11}" font-size="10" text-anchor="middle" font-family="monospace" fill="#0f1b3d">{frappe.utils.escape_html(text)}</text></svg>')


def hs_qr(text, size=96):
	"""A QR code as inline SVG (pyqrcode ships with Frappe)."""
	import pyqrcode

	rows = [r for r in pyqrcode.create(str(text or ""), error="M").text(quiet_zone=2).splitlines() if r.strip()]
	n = len(rows)
	cell = size / n
	rects = "".join(f'<rect x="{x * cell:.2f}" y="{y * cell:.2f}" width="{cell + 0.05:.2f}" height="{cell + 0.05:.2f}"/>' for y, r in enumerate(rows)
		for x, ch in enumerate(r) if ch == "1")
	return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}"><rect width="100%" height="100%" fill="#fff"/><g fill="#0f1b3d">{rects}</g></svg>'


def _zh(code):
	return frappe.db.get_value("Item", code, "hs_item_name_zh") or ""


def hs_company_zh(company):
	return (company and frappe.db.get_value("Company", company, "hs_company_name_zh")) or ""


def hs_job_ticket(wo):
	"""The work order for the shop floor: product, the operations with workstation (English + Chinese), standard minutes,
	operator, done and scrap with the job card's barcode, and the pick list of components."""
	from hipersign_trading.api import manufacturing as M

	w = frappe.get_doc("Work Order", wo) if isinstance(wo, str) else wo
	f = M.wo_fig(w.name)
	ops = []
	for o in f.ops:
		ws = M.ws_rates(o.ws)
		opr = frappe.db.get_value("Employee", o.jc.hs_operator, "employee_name") if o.jc and o.jc.hs_operator else ""
		ops.append(frappe._dict(no=o.idx * 10, name=o.op, ws=ws.workstation_name, ws_zh=ws.get("hs_name_zh") or "", minutes=o.mins_unit * f.qty, operator=opr,
			done=o.done if o.jc else None, scrap=o.scrap if o.jc else None, jc=o.jc.name if o.jc else ""))
	comps = [frappe._dict(code=r.item_code, name=M.item_info(r.item_code).item_name, zh=_zh(r.item_code), qty=flt(r.required_qty), uom=frappe.db.get_value("Item", r.item_code, "stock_uom"),
		issued=flt(r.transferred_qty)) for r in w.required_items]
	so = frappe.db.get_value("Sales Order", w.sales_order, ["name", "customer_name"], as_dict=True) if w.sales_order else None
	return frappe._dict(name=w.name, item=w.production_item, item_name=f.item_name, zh=_zh(w.production_item), bom=w.bom_no, qty=f.qty, due=f.due, start=f.start,
		so=so, ops=ops, comps=comps, barcode=hs_barcode(w.name, 40, 1.5), company=w.company, state=f.state, supervisor=frappe.utils.get_fullname(w.owner))


def hs_bom_print(doc):
	from hipersign_trading.api import manufacturing as M

	q = flt(doc.quantity) or 1
	lines = []
	for r in doc.items:
		sub = M.bom_of(r.item_code)
		unit = M.std(r.item_code).total if sub else (flt(r.rate) or M.leaf_cost(r.item_code))
		per = flt(r.qty) / q
		lines.append(frappe._dict(code=r.item_code, name=r.item_name, zh=_zh(r.item_code), qty=per, unit=unit, cost=per * unit, sub=bool(sub), uom=r.uom))
	ops = [frappe._dict(no=o.idx * 10, name=o.operation, ws=M.ws_rates(o.workstation).workstation_name, ws_zh=M.ws_rates(o.workstation).get("hs_name_zh") or "",
		minutes=flt(o.time_in_mins) / q) for o in doc.operations]
	s = M.std_of_bom(doc.name) if doc.docstatus == 1 else frappe._dict(mat=sum(x.cost for x in lines), lab=0, ovh=flt(doc.operating_cost) / q, total=flt(doc.total_cost) / q)
	ver = doc.name.split("-")[-1]
	return frappe._dict(lines=lines, ops=ops, std=s, zh=_zh(doc.item), version=int(ver) if ver.isdigit() else 1,
		state="Active" if doc.is_active and doc.is_default else "Superseded" if not doc.is_active else "Alternate", approver=frappe.utils.get_fullname(doc.owner))


def hs_qc_print(doc):
	"""The test certificate: product, batch and work order, AQL result and the tests with specification and result."""
	wo = doc.get("hs_work_order")
	batch = doc.get("batch_no") or ""
	if not batch and wo:
		batch = frappe.db.sql("""select sed.batch_no from `tabStock Entry Detail` sed join `tabStock Entry` se on se.name = sed.parent where se.work_order = %s and se.docstatus = 1
			and se.purpose = 'Manufacture' and sed.is_finished_item = 1 and ifnull(sed.batch_no, '') != '' order by se.posting_date asc limit 1""", wo)
		batch = batch[0][0] if batch else ""
	tests = [frappe._dict(test=r.specification, spec=r.value or "", result=r.reading_value or r.reading_1 or _("Pass")) for r in doc.readings]
	return frappe._dict(zh=_zh(doc.item_code), batch=batch, wo=wo, tests=tests, inspector=frappe.utils.get_fullname(doc.inspected_by) if doc.inspected_by else "",
		passed=(doc.get("hs_result") or doc.status) in ("Accepted", "Accepted with deviation"))


def hs_fg_label(wo):
	"""The carton label: item (English + Chinese), batch, serial numbers, quantity per carton, a QR code and a barcode."""
	w = frappe.get_doc("Work Order", wo) if isinstance(wo, str) else wo
	se = frappe.db.sql("""select sed.batch_no, se.hs_serial_from, se.posting_date from `tabStock Entry Detail` sed join `tabStock Entry` se on se.name = sed.parent
		where se.work_order = %s and se.docstatus = 1 and se.purpose = 'Manufacture' and sed.is_finished_item = 1 order by se.posting_date desc limit 1""", w.name, as_dict=True)
	today = frappe.utils.getdate()
	from hipersign_trading.api.manufacturing import batch_code

	code = batch_code(w.production_item)
	batch = (se[0].batch_no if se else "") or f"B{today.strftime('%y%m')}-{code}-{w.name[-2:]}"
	serial = (se[0].hs_serial_from if se else "") or f"HLI-{code}-{today.strftime('%y%m%d')}0001"
	per = 1
	for r in w.required_items:
		if "carton" in (frappe.db.get_value("Item", r.item_code, "item_name") or "").lower() and flt(r.required_qty):
			per = max(1, round(flt(w.qty) / flt(r.required_qty)))
	addr = frappe.db.get_value("Dynamic Link", {"link_doctype": "Company", "link_name": w.company, "parenttype": "Address"}, "parent")
	city = frappe.db.get_value("Address", addr, "city") if addr else ""
	zone = "KEZAD" if addr and "KEZAD" in (frappe.db.get_value("Address", addr, "address_line1") or "") else ""
	return frappe._dict(item=w.production_item, name=w.item_name or frappe.db.get_value("Item", w.production_item, "item_name"), zh=_zh(w.production_item), batch=batch,
		maker=" · ".join(x for x in [w.company, ", ".join(y for y in [zone, city] if y)] if x).upper(),
		serial=serial, per=per, qr=hs_qr(serial, 104), barcode=hs_barcode(f"{w.production_item}-{batch}", 38, 1.3), company=w.company,
		date=se[0].posting_date if se else today)
