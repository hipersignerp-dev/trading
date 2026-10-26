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
			shp = frappe.db.get_value("Delivery Note", dn, "hs_export_shipment")
			if shp:
				doc.hs_export_shipment = shp
				break
