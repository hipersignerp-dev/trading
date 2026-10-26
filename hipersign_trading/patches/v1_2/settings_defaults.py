"""v1.2: give the new Hipersign Settings their default values on sites upgraded from 1.0 / 1.1."""

import frappe

NEW = {
	"advance_before_delivery": 1, "collection_stage_1": 7, "collection_stage_2": 21, "collection_stage_3": 45, "collection_hold_days": 60,
	"kyc_block_orders": 1, "kyc_alert_days": 30, "lc_alert_days": 14, "lock_filed_periods": 1, "vat_due_day": 28, "revaluation_reminder": 1,
	"reorder_history_days": 60, "reorder_cover_days": 60, "reorder_safety_factor": 0.5, "intercompany_markup": 8,
}


def execute():
	frappe.reload_doc("hipersign_trading", "doctype", "hipersign_settings")
	for field, value in NEW.items():
		if frappe.db.get_single_value("Hipersign Settings", field) in (None, "", 0):
			frappe.db.set_single_value("Hipersign Settings", field, value)
