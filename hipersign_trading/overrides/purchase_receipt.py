"""Goods cannot be received before the import shipment is cleared by customs."""

import frappe
from frappe import _

from hipersign_trading.utils import settings

CLEARED = ("Cleared", "Received at Warehouse")


def _shipments(doc):
	pos = {i.purchase_order for i in doc.items if i.purchase_order}
	if doc.get("hs_import_shipment"):
		return [doc.hs_import_shipment]
	if not pos:
		return []
	return list(
		{
			r.parent
			for r in frappe.get_all(
				"Import Shipment PO", filters={"purchase_order": ["in", list(pos)]}, fields=["parent"]
			)
		}
	)


def validate(doc, method=None):
	if not settings().block_receipt_before_clearance:
		return
	for name in _shipments(doc):
		status = frappe.db.get_value("Import Shipment", name, "status")
		if status not in CLEARED:
			frappe.throw(
				_("Import shipment {0} is “{1}”. Goods can be received only after customs clearance.").format(
					name, status
				),
				title=_("Not cleared yet"),
			)
		if not doc.hs_import_shipment:
			doc.hs_import_shipment = name


def on_submit(doc, method=None):
	for name in _shipments(doc):
		shp = frappe.get_doc("Import Shipment", name)
		if shp.status == "Cleared" and shp.all_pos_received():
			shp.status = "Received at Warehouse"
			shp.save(ignore_permissions=True)
