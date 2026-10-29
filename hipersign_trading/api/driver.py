"""Driver web app (/driver): today's stops, start trip, proof of delivery with signature, photo and GPS.

Drivers log in with the “Driver” role (no desk access). A driver sees Delivery Notes assigned to the
Driver record linked to their user (Driver › Hipersign user). Dispatchers (Stock User / Stock Manager)
see every open delivery.
"""

import base64

import frappe
from frappe import _
from frappe.utils import now_datetime, today
from frappe.utils.file_manager import save_file

from hipersign_trading.utils import has_any_role

OPEN = ["Ready to Dispatch", "Out for Delivery"]


def _driver():
	return frappe.db.get_value("Driver", {"hs_user": frappe.session.user}, ["name", "full_name"], as_dict=True)


def _allowed(dn=None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in"), frappe.PermissionError)
	dispatcher = has_any_role("Stock User", "Stock Manager", "Delivery Manager", "Logistics Coordinator")
	drv = _driver()
	if not dispatcher and not drv:
		frappe.throw(_("Your user is not linked to a driver. Ask the dispatcher to set Driver › Hipersign user."), frappe.PermissionError)
	if dn and not dispatcher:
		assigned = frappe.db.get_value("Delivery Note", dn, "hs_driver")
		if assigned and assigned != drv.name:
			frappe.throw(_("This delivery is assigned to another driver."), frappe.PermissionError)
	return drv, dispatcher


@frappe.whitelist()
def my_stops():
	drv, dispatcher = _allowed()
	filters = {"docstatus": 1, "is_return": 0, "hs_delivery_status": ["in", OPEN]}
	if not dispatcher:
		filters["hs_driver"] = ["in", [drv.name, "", None]]
	stops = frappe.get_all(
		"Delivery Note",
		filters=filters,
		fields=["name", "customer", "customer_name", "posting_date", "shipping_address_name", "address_display", "contact_display",
			"contact_mobile", "hs_delivery_status", "hs_driver"],
		order_by="posting_date asc",
		limit=50,
	)
	# v1.5.6 (DRV-01): a delivery whose order still waits for its advance is not offered to the driver
	from hipersign_trading.overrides.advances import on_hold

	def held(dn):
		return any(on_hold(so) for so in set(frappe.get_all("Delivery Note Item", filters={"parent": dn}, pluck="against_sales_order")) if so)

	stops = [s for s in stops if not held(s.name)]
	for s in stops:
		s["items"] = frappe.get_all("Delivery Note Item", filters={"parent": s.name}, fields=["item_code", "item_name", "qty", "uom"], order_by="idx")
	done = frappe.get_all(
		"Delivery Note",
		filters={"docstatus": 1, "hs_delivery_status": "Delivered", "hs_pod_time": [">=", today()], **({} if dispatcher else {"hs_driver": drv.name})},
		fields=["name", "customer_name", "hs_received_by"],
	)
	return {"driver": drv.full_name if drv else _("Dispatcher"), "stops": stops, "done": done}


@frappe.whitelist()
def start_trip(dn):
	drv, _d = _allowed(dn)
	doc = frappe.get_doc("Delivery Note", dn)
	doc.db_set({"hs_delivery_status": "Out for Delivery", "hs_driver": doc.hs_driver or (drv.name if drv else None)})
	doc.add_comment("Info", _("Out for delivery — {0} (driver app)").format(drv.full_name if drv else frappe.session.user))
	return "ok"


def _attach(dn, data_url, name):
	if not data_url or "," not in data_url:
		return None
	content = base64.b64decode(data_url.split(",", 1)[1])
	if len(content) > 4 * 1024 * 1024:
		frappe.throw(_("The photo is too large — retake it at a lower resolution."))
	f = save_file(name, content, "Delivery Note", dn, is_private=1)
	return f.file_url


@frappe.whitelist()
def confirm_delivery(dn, received_by, signature, photo=None, gps=None, checked=None):
	drv, _d = _allowed(dn)
	if not (received_by or "").strip():
		frappe.throw(_("Enter the receiver's name."))
	if not signature or not signature.startswith("data:image"):
		frappe.throw(_("The receiver must sign."))
	doc = frappe.get_doc("Delivery Note", dn)
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted delivery note can be delivered."))
	photo_url = _attach(dn, photo, f"{dn}-photo.jpg") if photo else None
	_attach(dn, signature, f"{dn}-signature.png")
	doc.db_set(
		{
			"hs_delivery_status": "Delivered",
			"hs_received_by": received_by.strip(),
			"hs_pod_signature": signature,
			"hs_pod_photo": photo_url,
			"hs_pod_gps": (gps or "")[:60],
			"hs_pod_time": now_datetime(),
			"hs_driver": doc.hs_driver or (drv.name if drv else None),
		}
	)
	doc.add_comment("Info", _("Delivered — received by {0}{1} (driver app)").format(received_by, ", GPS " + gps if gps else ""))
	return "ok"


@frappe.whitelist()
def report_failure(dn, reason):
	_allowed(dn)
	doc = frappe.get_doc("Delivery Note", dn)
	doc.db_set({"hs_delivery_status": "Failed", "hs_failed_reason": reason})
	doc.add_comment("Info", _("Delivery failed — {0} (driver app)").format(reason))
	for u in frappe.get_all("Has Role", filters={"role": "Stock Manager", "parenttype": "User"}, pluck="parent"):
		if u not in ("Administrator", "Guest"):
			frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "reference_type": "Delivery Note", "reference_name": dn,
				"description": _("Delivery {0} failed: {1}").format(dn, reason), "priority": "High"}).insert(ignore_permissions=True)
	return "ok"
