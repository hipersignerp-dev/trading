"""v1.8.2 demo data: each demo user works in their own company, as on the prototype (p19 scopeAllowed — only the
Administrator, the Managing Director and the group owner see the whole group). Users with an employee record already get
this from HRMS; the others get a Company user permission here. Skips what is already there."""

import frappe

HDT, GDI, HLI = "Hipersign Demo Trading LLC", "Golden Dragon Interiors LLC", "Hipersign Lighting Industries FZE"
# user (before @demo.hipersignerp.com) → company
SCOPE = {
	"fatima.alzaabi": HDT, "rahul.nair": HDT, "joseph.dsouza": HDT, "lina.farah": HDT, "sara.alhashimi": HDT,
	"wang.lei": GDI, "ahmed.raza": GDI, "liu.yang": GDI,
	"chen.hao": HLI, "li.na": HLI,
}


def demo_scope(c):
	for key, co in SCOPE.items():
		user = f"{key}@demo.hipersignerp.com"
		if not frappe.db.exists("User", user) or not frappe.db.exists("Company", co):
			continue
		if frappe.db.exists("User Permission", {"user": user, "allow": "Company"}):
			continue
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Company", "for_value": co, "apply_to_all_doctypes": 1,
			"is_default": 1}).insert(ignore_permissions=True)
		frappe.defaults.set_user_default("company", co, user)


STEPS = [demo_scope]
