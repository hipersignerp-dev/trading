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
		# v1.8.3 (prototype p20): chart style, brand colour, graph bands, the user's chart types
		try:
			from hipersign_trading.api.look import boot_look, chart_types

			info["look"] = boot_look()
			info["chart_types"] = chart_types()
		except Exception:
			frappe.log_error(title="Hipersign look (boot)")
		info["sidebar"] = "Hipersign ERP"
		info["home_workspace"] = "Hipersign Trading"  # only a fallback when Hipersign Home cannot open (v1.8.4: retired, see hs_nav)
		info["home_page"] = "hipersign-home" if frappe.db.exists("Page", "hipersign-home") and frappe.get_cached_doc("Page", "hipersign-home").is_permitted() else None
		info["demo_site"] = bool(frappe.conf.get("hipersign_demo_site"))
		info["deal_demo"] = bool(info["demo_site"] and s.get("deal_demo") and "System Manager" in frappe.get_roles())
		from hipersign_trading.navigation import NAV_BADGES, sub_items

		info["nav_sub"] = sub_items()
		info["nav_badges"] = list(NAV_BADGES)
		# v1.8.0: the menu builder's changes for this user (role > company > site) on top of the feature packs
		try:
			from hipersign_trading.menu import boot as menu_boot

			menu_boot(bootinfo, info)
		except Exception:
			frappe.log_error(title="Hipersign menu builder (boot)")
		# v1.8.3: super admins, the licence, and Frappe/ERPNext pop-ups only where the licence allows them
		try:
			from hipersign_trading.licence import boot_popups, is_super_admin

			boot_popups(bootinfo)
			info["super_admin"] = is_super_admin()
		except Exception:
			frappe.log_error(title="Hipersign licence (boot)")
		bootinfo.hipersign = info
		from hipersign_trading.demo_access import boot as demo_boot

		demo_boot(bootinfo)
	except Exception:
		frappe.log_error(title="Hipersign boot info")


# ---------------------------------------------------------------- v1.8.4 (#29): only the Hipersign app on the apps screen
APP = "hipersign_trading"


def _only_ours():
	"""Everyone but Hipersign's super admins sees only the Hipersign app (Hipersign Settings › only Hipersign tiles)."""
	try:
		from hipersign_trading.licence import is_super_admin

		if is_super_admin():
			return False
		s = frappe.get_cached_doc("Hipersign Settings")
		return s.get("only_hipersign_tiles") is None or bool(s.get("only_hipersign_tiles"))
	except Exception:
		return False


def only_hipersign_app(bootinfo):
	"""extend_bootinfo: ERPNext, Frappe HR and Framework leave the apps screen (/desk) and the sidebar's app switcher;
	their screens stay reachable through the Hipersign menu and links, with the usual permissions."""
	if not _only_ours():
		return
	for a in bootinfo.get("app_data") or []:
		if a.get("app_name") != APP:
			a["on_apps_screen"] = False


@frappe.whitelist()
def get_apps():
	"""Replaces frappe.apps.get_apps (the apps list the desk asks for) with the same filter."""
	from frappe.apps import get_apps as frappe_get_apps

	apps = frappe_get_apps()
	if _only_ours():
		apps = [a for a in apps if a.get("name") == APP] or apps
	return apps
