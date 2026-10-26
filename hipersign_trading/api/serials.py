"""Serial number look-up: who bought it, on which delivery, and is it still under warranty."""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, getdate, today


def _delivery_of(serial_no):
	"""Latest outward delivery of a serial — v15 keeps it in Serial and Batch Bundles."""
	if frappe.db.table_exists("Serial and Batch Bundle"):
		rows = frappe.db.sql(
			"""
			select b.voucher_type, b.voucher_no, b.posting_datetime
			from `tabSerial and Batch Entry` e
			join `tabSerial and Batch Bundle` b on b.name = e.parent
			where e.serial_no = %s and b.docstatus = 1 and b.is_cancelled = 0
				and b.type_of_transaction = 'Outward' and b.voucher_type in ('Delivery Note', 'Sales Invoice')
			order by b.posting_datetime desc limit 1""",
			serial_no,
			as_dict=True,
		)
		if rows:
			r = rows[0]
			party = frappe.db.get_value(r.voucher_type, r.voucher_no, ["customer", "posting_date"], as_dict=True)
			if party:
				return frappe._dict(voucher_type=r.voucher_type, voucher_no=r.voucher_no, customer=party.customer, date=party.posting_date)
	sn = frappe.db.get_value("Serial No", serial_no, ["delivery_document_type", "delivery_document_no", "delivery_date", "customer"], as_dict=True) if frappe.get_meta("Serial No").has_field("delivery_document_no") else None
	if sn and sn.delivery_document_no:
		return frappe._dict(voucher_type=sn.delivery_document_type, voucher_no=sn.delivery_document_no, customer=sn.customer, date=sn.delivery_date)
	return None


def _receipt_of(serial_no):
	if not frappe.db.table_exists("Serial and Batch Bundle"):
		return None
	rows = frappe.db.sql(
		"""
		select b.voucher_type, b.voucher_no, date(b.posting_datetime) as date
		from `tabSerial and Batch Entry` e join `tabSerial and Batch Bundle` b on b.name = e.parent
		where e.serial_no = %s and b.docstatus = 1 and b.is_cancelled = 0 and b.type_of_transaction = 'Inward'
		order by b.posting_datetime asc limit 1""",
		serial_no,
		as_dict=True,
	)
	return rows[0] if rows else None


def serial_info(serial_no):
	if not serial_no or not frappe.db.exists("Serial No", serial_no):
		return None
	sn = frappe.get_doc("Serial No", serial_no)
	item = frappe.get_cached_value("Item", sn.item_code, ["item_name", "warranty_period"], as_dict=True)
	dl, rc = _delivery_of(serial_no), _receipt_of(serial_no)
	until = sn.get("warranty_expiry_date")
	if not until and dl and item.warranty_period:
		until = add_days(dl.date, int(item.warranty_period))
	status = "In stock" if sn.status == "Active" else sn.status
	if dl and sn.status != "Active":
		status = "Under warranty" if until and getdate(until) >= getdate(today()) else "Warranty expired"
	claims = frappe.get_all(
		"Warranty Claim", filters={"serial_no": serial_no}, fields=["name", "status", "complaint_date", "complaint"], order_by="complaint_date desc"
	)
	return frappe._dict(
		serial_no=serial_no,
		item_code=sn.item_code,
		item_name=item.item_name,
		warehouse=sn.get("warehouse"),
		received=rc,
		delivery=dl,
		customer=dl.customer if dl else None,
		warranty_days=item.warranty_period,
		warranty_until=until,
		status=status,
		claims=claims,
	)


@frappe.whitelist()
def lookup(serial_no):
	serial_no = (serial_no or "").strip().upper()
	info = serial_info(serial_no)
	if not info:
		frappe.throw(_("Serial number {0} was not found.").format(serial_no))
	if not frappe.has_permission("Serial No", "read"):
		# portal customers may only see their own units
		from erpnext.controllers.website_list_for_contact import get_customers_suppliers

		customers, _s = get_customers_suppliers("Delivery Note", frappe.session.user)
		if info.customer not in (customers or []):
			frappe.throw(_("Not permitted"), frappe.PermissionError)
	return info


def customer_units(customer):
	"""Serialised units delivered to a customer, newest first (for the portal warranty page)."""
	if not frappe.db.table_exists("Serial and Batch Bundle"):
		return []
	rows = frappe.db.sql(
		"""
		select e.serial_no, b.item_code, b.voucher_no, date(b.posting_datetime) as delivered
		from `tabSerial and Batch Entry` e
		join `tabSerial and Batch Bundle` b on b.name = e.parent
		join `tabDelivery Note` dn on dn.name = b.voucher_no and b.voucher_type = 'Delivery Note'
		where dn.customer = %s and dn.docstatus = 1 and b.docstatus = 1 and b.is_cancelled = 0
			and b.type_of_transaction = 'Outward'
		order by b.posting_datetime desc limit 500""",
		customer,
		as_dict=True,
	)
	for r in rows:
		days = frappe.get_cached_value("Item", r.item_code, "warranty_period")
		r.item_name = frappe.get_cached_value("Item", r.item_code, "item_name")
		r.warranty_until = add_days(r.delivered, int(days)) if days else None
		r.active = bool(r.warranty_until and getdate(r.warranty_until) >= getdate(today()))
	return rows


def warranty_days(months):
	"""ERPNext stores the warranty period in days."""
	return (getdate(add_months("2026-01-01", months)) - getdate("2026-01-01")).days
