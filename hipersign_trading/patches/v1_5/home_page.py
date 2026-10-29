"""v1.5.6: users open Hipersign Home.

Earlier demo loads set each user's default workspace to an older Hipersign workspace; a user whose role cannot open
it (a buyer and Hipersign Warehouse) saw "Not permitted" after logging in. Those defaults are cleared, so the desk
opens and the Hipersign menu takes the user to Hipersign Home.
"""

import frappe

OLD = ("Hipersign Trading", "Hipersign Sales", "Hipersign Warehouse", "Hipersign Finance", "Hipersign HR", "Hipersign Documents")


def execute():
	if not frappe.get_meta("User").has_field("default_workspace"):
		return
	frappe.db.sql("update `tabUser` set default_workspace = null where default_workspace in %(old)s", {"old": OLD})
	frappe.cache.delete_key("home_page")
