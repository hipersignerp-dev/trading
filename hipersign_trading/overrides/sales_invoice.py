import frappe

from hipersign_trading.utils import is_export_customer, settings


def validate(doc, method=None):
	export = is_export_customer(doc.customer)
	doc.hs_zero_rated = 1 if export else 0
	s = settings()
	template = s.export_tax_template if export else None
	if template and doc.taxes_and_charges != template:
		doc.taxes_and_charges = template
		doc.set("taxes", [])
		doc.append_taxes_from_master()
		doc.calculate_taxes_and_totals()
	if export and not doc.hs_export_shipment:
		dns = {i.delivery_note for i in doc.items if i.delivery_note}
		for dn in dns:
			# v1.5.6 (EXP-02): also a delivery note made from the order rather than from the shipment
			shp = frappe.db.get_value("Delivery Note", dn, "hs_export_shipment") or frappe.db.get_value(
				"Export Shipment", {"delivery_note": dn, "docstatus": ["<", 2]}, "name")
			if shp:
				doc.hs_export_shipment = shp
				break


def link_export_shipment(doc, method=None):
	"""v1.5.6 (EXP-02): an export invoice made outside the shipment still completes the shipment's invoice step."""
	if doc.is_return or not doc.get("hs_export_shipment") or not frappe.db.exists("Export Shipment", doc.hs_export_shipment):
		return
	if not frappe.db.get_value("Export Shipment", doc.hs_export_shipment, "sales_invoice"):
		frappe.db.set_value("Export Shipment", doc.hs_export_shipment, "sales_invoice", doc.name)
