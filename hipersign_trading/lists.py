"""Editable drop-down lists (Phase 1).

The values live in Hipersign List Value; the app writes them into the options of the custom
Select fields that use the list, so every form shows the current active values. Deactivated
values disappear from the drop-down but stay on old documents. Lists that already are masters in
ERPNext (Lead Source, Customer Group, Territory, UOM, Mode of Payment, Incoterm, Item Group…) are
edited where they live and are listed on the Hipersign Lists page.
"""

import frappe

# list: (custom fields using it, starting values, the field may be left empty)
LISTS = {
	"Payment method": (
		[("Customer", "hs_default_payment_method"), ("Sales Order", "hs_payment_method")],
		["Advance TT", "LC at sight", "LC 60 days", "Open account 30 days", "Cash against documents"],
		True,
	),
	"Shipment mode": ([("Customer", "hs_default_mode"), ("Sales Order", "hs_shipment_mode"), ("Purchase Order", "hs_shipment_mode")], ["Sea", "Air", "Land"], True),
	"Lost reason": (
		[("Lead", "hs_lost_reason")],
		["Price — chose a cheaper offer", "Chose a competitor", "No budget", "Project cancelled or postponed", "No response", "Delivery time too long", "Other"],
		True,
	),
	"Return reason": (
		[("Sales Invoice", "hs_return_reason"), ("Purchase Invoice", "hs_return_reason")],
		["Damaged in transit", "Wrong item supplied", "Defective — under warranty", "Customer cancelled", "Excess quantity", "Price difference"],
		True,
	),
}

ERPNEXT_MASTERS = [
	("Lead Source", "Lead source"), ("Customer Group", "Customer group"), ("Supplier Group", "Supplier group"), ("Territory", "Territory"),
	("Item Group", "Item group"), ("UOM", "Unit of measure"), ("Mode of Payment", "Payment mode"), ("Incoterm", "Incoterm"),
	("Payment Terms Template", "Payment terms"), ("Designation", "Designation"), ("Department", "Department"), ("Brand", "Brand"),
	("Hipersign Document Type", "Document type"), ("Company Document Type", "Company document type"),
]


def values(list_name, active_only=True):
	filters = {"list_name": list_name}
	if active_only:
		filters["active"] = 1
	return frappe.get_all("Hipersign List Value", filters=filters, order_by="position asc, creation asc", pluck="value")


def apply(list_name=None):
	"""Write the active values into the Select options of every field that uses the list."""
	for name in [list_name] if list_name else list(LISTS):
		if name not in LISTS:
			continue
		fields, _, optional = LISTS[name]
		vals = values(name)
		for dt, fieldname in fields:
			cf = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, ["name", "fieldtype"], as_dict=True)
			if not cf or cf.fieldtype != "Select":
				continue
			# keep values still used on documents so they render, even when deactivated
			in_use = [v for v in values(name, active_only=False) if v not in vals and used_on(dt, fieldname, v)]
			options = ("\n" if optional else "") + "\n".join(vals + in_use)
			frappe.db.set_value("Custom Field", cf.name, "options", options, update_modified=False)
			frappe.clear_cache(doctype=dt)


def seed():
	"""Create the starting values once (existing sites keep their own)."""
	for name, (_, start, __) in LISTS.items():
		if frappe.db.exists("Hipersign List Value", {"list_name": name}):
			continue
		for i, v in enumerate(start):
			d = frappe.get_doc({"doctype": "Hipersign List Value", "list_name": name, "value": v, "position": (i + 1) * 10, "active": 1})
			d.flags.hs_no_apply = True
			d.insert(ignore_permissions=True)
	apply()


def used_on(dt, fieldname, value):
	if not frappe.db.has_column(dt, fieldname):
		return False
	return bool(frappe.db.exists(dt, {fieldname: value}))


def used(list_name, value):
	return any(used_on(dt, f, value) for dt, f in LISTS.get(list_name, ([], [], True))[0])
