import frappe
from frappe import _
from frappe.utils import getdate

from hipersign_trading.api.serials import serial_info


def validate(doc, method=None):
	"""Fill customer, item and warranty status from the serial number."""
	if not doc.get("serial_no"):
		return
	info = serial_info(doc.serial_no)
	if not info:
		return
	doc.item_code = doc.item_code or info.item_code
	if info.customer and not doc.customer:
		doc.customer = info.customer
	if info.warranty_until:
		if doc.meta.has_field("warranty_expiry_date"):
			doc.warranty_expiry_date = info.warranty_until
		in_warranty = getdate(info.warranty_until) >= getdate(doc.complaint_date or frappe.utils.today())
		doc.warranty_amc_status = "Under Warranty" if in_warranty else "Out of Warranty"
	if doc.get("hs_resolution") == "Replace" and doc.get("hs_replacement_serial") == doc.serial_no:
		frappe.throw(_("The replacement serial must be a different unit."))
