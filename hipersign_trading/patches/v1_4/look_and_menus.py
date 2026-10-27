"""v1.4: the prototype's look and menu on sites upgraded from 1.3 (new sites get the same on install)."""

import frappe


def execute():
	frappe.reload_doc("hipersign_trading", "doctype", "hipersign_settings")
	from hipersign_trading.navigation import ensure_defaults

	ensure_defaults()
