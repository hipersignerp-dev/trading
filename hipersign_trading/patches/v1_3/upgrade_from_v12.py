"""Sites upgraded from v1.2 had every module on: keep it that way (Enterprise pack, full document rules), no set-up wizard."""

import frappe


def execute():
	frappe.reload_doc("hipersign_trading", "doctype", "hipersign_settings")
	from hipersign_trading.features import FEATURES, field

	s = frappe.get_single("Hipersign Settings")
	if s.setup_done:
		return
	for k in FEATURES:
		s.set(field(k), 1)
	s.company_mode = "Group" if frappe.db.count("Company") > 1 else "Single company"
	s.feature_pack, s.document_level, s.setup_done = "Enterprise", "Full", 1
	s.pdc_post_on_receipt = 0  # cheques already in hand were not posted when received — keep v1.2 behaviour until switched on
	s.flags.ignore_mandatory = True
	frappe.flags.hs_no_effects = True
	s.save(ignore_permissions=True)
	frappe.flags.hs_no_effects = False
