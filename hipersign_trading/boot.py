"""Boot info for the desk: feature switches, document level, form modes, set-up state."""

import frappe


def boot_session(bootinfo):
	if frappe.session.user == "Guest" or not frappe.db.exists("DocType", "Hipersign Settings"):
		return
	try:
		from hipersign_trading.api.quick import form_modes
		from hipersign_trading.features import boot_info

		info = boot_info()
		info["form_modes"] = form_modes()
		info["ruled_doctypes"] = sorted({r.reference_doctype for r in frappe.get_all("Hipersign Document Rule", filters={"active": 1}, fields=["reference_doctype"])})
		s = frappe.get_cached_doc("Hipersign Settings")
		info["price_list_items_only"] = bool(s.get("price_list_items_only"))
		info["bank_charges_account"] = s.get("bank_charges_account")
		info["is_system_manager"] = "System Manager" in frappe.get_roles()
		# v1.4 look & menus
		info["theme"] = s.get("desk_theme") or "Hipersign"
		info["keep_sidebar"] = bool(s.get("keep_hipersign_sidebar", 1))
		info["open_home"] = bool(s.get("open_home_after_login"))
		info["sidebar"] = "Hipersign ERP"
		info["home_workspace"] = "Hipersign Trading"
		bootinfo.hipersign = info
	except Exception:
		frappe.log_error(title="Hipersign boot info")
