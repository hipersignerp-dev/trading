import frappe


def validate(doc, method=None):
	"""Keep the delivery status in step with the proof of delivery."""
	if not doc.meta.has_field("hs_delivery_status"):
		return
	if doc.get("hs_received_by") and doc.get("hs_pod_signature"):
		doc.hs_delivery_status = "Delivered"
	elif not doc.get("hs_delivery_status"):
		doc.hs_delivery_status = "Ready to Dispatch"


def on_submit(doc, method=None):
	if doc.get("hs_export_shipment"):
		shp = frappe.get_doc("Export Shipment", doc.hs_export_shipment)
		if not shp.delivery_note:
			shp.db_set("delivery_note", doc.name)
		shp.mark_document("Packing List")
