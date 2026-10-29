"""v1.5.6: one company default per user.

The top bar wrote "Company" while older code and set-up wrote "company". The database compares the keys without
case, so a user could carry two different companies and reports followed one, the top bar the other.
Keep one value per user, preferring a company that keeps its own books (not a group parent), newest first, and
remove the rest.
"""

import frappe


def execute():
	rows = frappe.db.sql(
		"""select name, parent, defkey, defvalue from `tabDefaultValue`
		where lower(defkey) = 'company' and parent not in ('__default', '__global')
		order by parent, modified desc, creation desc""",
		as_dict=True,
	)
	by_user = {}
	for r in rows:
		by_user.setdefault(r.parent, []).append(r)
	for user, vals in by_user.items():
		def rank(r):
			is_group = frappe.db.get_value("Company", r.defvalue, "is_group")
			return (is_group is None, bool(is_group))  # existing books company, then group, then unknown

		keep = sorted(vals, key=rank)[0]  # stable: newest first within a rank
		if frappe.db.get_value("Company", keep.defvalue, "is_group") is None:
			keep = None
		for r in vals:
			if keep and r.name == keep.name:
				if r.defkey != "Company":
					frappe.db.set_value("DefaultValue", r.name, "defkey", "Company", update_modified=False)
			else:
				frappe.db.delete("DefaultValue", {"name": r.name})
	frappe.clear_cache()
