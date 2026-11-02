"""v1.8.0: the new Manufacturing switch follows the pack — on for Enterprise sites (Enterprise has every feature) and the
Manufacturer pack, off otherwise, so an upgraded site keeps its pack name instead of turning "Custom"."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Hipersign Settings") or not frappe.get_meta("Hipersign Settings").has_field("feat_manufacturing"):
		return
	pack = frappe.db.get_single_value("Hipersign Settings", "feature_pack")
	frappe.db.set_single_value("Hipersign Settings", "feat_manufacturing", 1 if pack in ("Enterprise", "Manufacturer") else 0)
