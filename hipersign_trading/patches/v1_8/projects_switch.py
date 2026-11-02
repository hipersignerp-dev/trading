"""v1.8.0: the new Projects switch follows the pack — on for Enterprise sites (Enterprise has every feature), off otherwise,
so an upgraded site keeps its pack name instead of turning "Custom"."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Hipersign Settings") or not frappe.get_meta("Hipersign Settings").has_field("feat_projects"):
		return
	pack = frappe.db.get_single_value("Hipersign Settings", "feature_pack")
	frappe.db.set_single_value("Hipersign Settings", "feat_projects", 1 if pack in ("Enterprise", "Contractor") else 0)
