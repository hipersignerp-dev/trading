"""v1.7.0 demo data: service, registration (Mulkiya) and insurance dates on the vehicles and the forklift, and a
custodian on each asset, so Fixed Assets shows its Maintenance & renewals tab. Every step skips what is already there."""

import frappe

# asset name contains → (plate, next service, registration expiry, insurance end) as days from today
ASSETS = {
	"Hiace": ("DXB 4471", -3, 22, 140),
	"Urvan": ("DXB 8820", 25, 190, 18),
	"Forklift": (None, 9, None, 260),
}


def v170_assets(c):
	if not frappe.get_meta("Asset").has_field("hs_next_service"):
		return
	emps = [e.name for e in frappe.get_all("Employee", filters={"company": c.company, "status": "Active"}, order_by="name asc", limit=6)] \
		if frappe.db.table_exists("Employee") else []
	for i, a in enumerate(frappe.get_all("Asset", filters={"company": c.company, "docstatus": 1}, fields=["name", "asset_name", "custodian", "hs_next_service"])):
		vals = {}
		for key, (plate, svc, reg, ins) in ASSETS.items():
			if key in a.asset_name and not a.hs_next_service:
				vals.update({"hs_plate_no": plate, "hs_next_service": c.d(svc), "hs_registration_expiry": c.d(reg) if reg is not None else None,
					"insurance_end_date": c.d(ins)})
		if not a.custodian and emps:
			vals["custodian"] = emps[i % len(emps)]
		if vals:
			frappe.db.set_value("Asset", a.name, {k: v for k, v in vals.items() if v is not None or k != "hs_plate_no"}, update_modified=False)


STEPS = [v170_assets]
