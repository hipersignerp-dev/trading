"""v1.5 — Test Centre (the demo-site test scripts with their results) and the Add-ons & Pricing catalogue."""

import json
import os

import frappe
from frappe import _

HERE = os.path.dirname(os.path.dirname(__file__))


def _load(name):
	with open(os.path.join(HERE, name), encoding="utf-8") as f:
		return json.load(f)


@frappe.whitelist()
def get_tests():
	tests = _load("test_scripts.json")
	res = {r.test_id: r for r in frappe.get_all("Hipersign Test Result", fields=["test_id", "result", "notes", "modified_by", "modified"])}
	for t in tests:
		r = res.get(t["id"])
		t["result"] = r.result if r else "Not run"
		t["notes"] = r.notes if r else ""
		t["by"] = frappe.get_cached_value("User", r.modified_by, "full_name") if r else ""
		t["on"] = str(r.modified)[:10] if r else ""
	return tests


@frappe.whitelist()
def set_result(test_id, result, notes=None):
	if result not in ("Not run", "Pass", "Fail", "Blocked"):
		frappe.throw(_("Unknown result"))
	# v1.6.0 (TST-01): any desk user records results — HR, driver-office and other roles had no permission on the doctype
	if frappe.session.user == "Guest" or frappe.get_cached_value("User", frappe.session.user, "user_type") != "System User":
		frappe.throw(_("Only desk users can record test results."), frappe.PermissionError)
	if not frappe.db.exists("Hipersign Test Result", test_id):
		doc = frappe.new_doc("Hipersign Test Result")
		doc.test_id = test_id
	else:
		doc = frappe.get_doc("Hipersign Test Result", test_id)
	doc.result = result
	if notes is not None:
		doc.notes = notes
	doc.flags.ignore_permissions = True
	doc.save()
	return {"test_id": test_id, "result": result}


@frappe.whitelist()
def reset_results():
	frappe.only_for(["System Manager", "Managing Director"])
	for n in frappe.get_all("Hipersign Test Result", pluck="name"):
		frappe.delete_doc("Hipersign Test Result", n, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_addons():
	d = _load("addons.json")
	d["can_rate"] = bool({"System Manager", "Managing Director"} & set(frappe.get_roles()))
	return d
