"""Price-list item filter on quotations, orders and invoices."""

import frappe


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def items_in_price_list(doctype, txt, searchfield, start, page_len, filters):
	"""Items with a price in the selected list (sales items only); everything when the list is empty or the user ticked All items."""
	filters = frappe._dict(filters or {})
	pl = filters.get("price_list")
	item = frappe.qb.DocType("Item")
	q = (frappe.qb.from_(item).select(item.name, item.item_name, item.item_group)
		.where(item.disabled == 0).where(item.has_variants == 0)
		.where((item.name.like(f"%{txt}%")) | (item.item_name.like(f"%{txt}%")) | (item.description.like(f"%{txt}%"))))
	if filters.get("is_sales_item"):
		q = q.where(item.is_sales_item == 1)
	if filters.get("is_purchase_item"):
		q = q.where(item.is_purchase_item == 1)
	if pl and not filters.get("all_items"):
		ip = frappe.qb.DocType("Item Price")
		q = q.where(item.name.isin(frappe.qb.from_(ip).select(ip.item_code).where(ip.price_list == pl)))
	return q.orderby(item.name).limit(int(page_len)).offset(int(start)).run()


@frappe.whitelist()
def price_list_info(price_list):
	return {"items": frappe.db.count("Item Price", {"price_list": price_list}), "currency": frappe.db.get_value("Price List", price_list, "currency")}
