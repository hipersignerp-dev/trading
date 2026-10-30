"""First-run set-up and the Load demo data button."""

import frappe
from frappe import _



@frappe.whitelist()
def complete_setup(company_mode, pack, company=None):
	"""The two install questions: single company or group, and which pack."""
	frappe.only_for("System Manager")
	from hipersign_trading.features import apply_effects, apply_pack

	if company_mode not in ("Single company", "Group"):
		frappe.throw(_("Choose single company or group"))
	s = apply_pack(pack, company_mode, save=False)
	if company:
		s.company = company
	s.setup_done = 1
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)
	apply_effects(s)
	# v1.6.0 (PDC-04): on a new site the company exists only now — the cheque holding accounts (and the bilingual print
	# formats) were set up on install, before there was a company, so received cheques were never posted on receipt
	from hipersign_trading.setup import default_print_formats, ensure_cheque_accounts

	ensure_cheque_accounts()
	default_print_formats()
	frappe.db.commit()
	return {"pack": pack, "company_mode": company_mode}


@frappe.whitelist()
def apply_pack(pack):
	frappe.only_for("System Manager")
	from hipersign_trading.features import apply_pack as ap

	s = ap(pack, save=False)
	s.setup_done = 1
	s.flags.ignore_mandatory = True
	s.save(ignore_permissions=True)
	return pack


def demo_allowed():
	if frappe.conf.get("hipersign_demo_site"):
		return True, ""
	if frappe.db.get_default("hs_demo_loaded"):
		return True, ""
	n = frappe.db.count("Sales Invoice", {"docstatus": 1}) + frappe.db.count("Purchase Invoice", {"docstatus": 1})
	if n:
		return False, _("This site already has {0} submitted invoices — demo data is only loaded on a new or demo site.").format(n)
	return True, ""


@frappe.whitelist()
def demo_status():
	ok, why = demo_allowed()
	return {"allowed": ok, "why": why, "loaded": bool(frappe.db.get_default("hs_demo_loaded")), "running": bool(frappe.cache.get_value("hs_demo_running"))}


@frappe.whitelist()
def load_demo(confirm=None):
	frappe.only_for("System Manager")
	ok, why = demo_allowed()
	if not ok:
		frappe.throw(why)
	if (confirm or "").strip().upper() != "DEMO":
		frappe.throw(_("Type DEMO to confirm"))
	if frappe.cache.get_value("hs_demo_running"):
		frappe.throw(_("Demo data is already loading — check back in a few minutes."))
	frappe.cache.set_value("hs_demo_running", 1, expires_in_sec=3600)
	frappe.enqueue("hipersign_trading.demo.load_from_button", queue="long", timeout=3600, user=frappe.session.user)
	return _("Loading demo data in the background — it takes a few minutes. You will get a notification when it is done.")
