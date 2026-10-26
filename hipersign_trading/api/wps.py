"""UAE Wage Protection System (WPS) salary information file (SIF) from a Payroll Entry.

Needs the Frappe HR app (hrms) for Salary Slips. Employee bank details come from
Employee › IBAN (or Bank A/C No.) and Employee › WPS routing code; the employer's
MOHRE establishment ID and bank routing code come from Hipersign Settings.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from hipersign_trading.utils import has_any_role, settings

FIXED = ("basic", "housing", "transport")


def _require_hrms():
	if not frappe.db.exists("DocType", "Salary Slip"):
		frappe.throw(_("Install the Frappe HR app (hrms) to run payroll and WPS files."))


def sif_lines(payroll_entry):
	_require_hrms()
	s = settings()
	pe = frappe.get_doc("Payroll Entry", payroll_entry)
	slips = frappe.get_all("Salary Slip", filters={"payroll_entry": payroll_entry, "docstatus": 1},
		fields=["name", "employee", "start_date", "end_date", "payment_days", "leave_without_pay", "gross_pay", "net_pay"])
	if not slips:
		frappe.throw(_("Submit the salary slips of {0} first.").format(payroll_entry))
	lines, total, missing = [], 0, []
	for sl in slips:
		e = frappe.db.get_value("Employee", sl.employee, ["employee_name", "hs_labour_card_no", "hs_wps_routing_code", "iban", "bank_ac_no"], as_dict=True)
		acct = (e.iban or e.bank_ac_no or "").replace(" ", "")
		if not (e.hs_labour_card_no and e.hs_wps_routing_code and acct):
			missing.append(e.employee_name)
			continue
		earnings = frappe.get_all("Salary Detail", filters={"parent": sl.name, "parentfield": "earnings"}, fields=["salary_component", "amount"])
		fixed = sum(flt(x.amount) for x in earnings if any(k in x.salary_component.lower() for k in FIXED))
		variable = max(0, flt(sl.net_pay) - fixed)
		net = flt(sl.net_pay)
		total += net
		lines.append(",".join([
			"EDR", e.hs_labour_card_no.zfill(14), e.hs_wps_routing_code, acct,
			getdate(sl.start_date).strftime("%Y-%m-%d"), getdate(sl.end_date).strftime("%Y-%m-%d"),
			str(int(flt(sl.payment_days))), f"{min(fixed, net):.2f}", f"{variable:.2f}", str(int(flt(sl.leave_without_pay))),
		]))
	if missing:
		frappe.throw(_("Add labour card no., WPS routing code and IBAN for: {0}").format(", ".join(missing)), title=_("WPS details missing"))
	now = now_datetime()
	lines.append(",".join([
		"SCR", (s.get("wps_employer_id") or "").zfill(13), s.get("wps_bank_routing") or "", now.strftime("%Y-%m-%d"), now.strftime("%H%M"),
		getdate(pe.end_date).strftime("%m%Y"), str(len(lines)), f"{total:.2f}", "AED", payroll_entry,
	]))
	return lines


@frappe.whitelist()
def download_sif(payroll_entry):
	if not has_any_role("HR Manager", "Accounts Manager"):
		frappe.throw(_("Only the HR Manager or Finance Manager can download the WPS file."), frappe.PermissionError)
	lines = sif_lines(payroll_entry)
	pe = frappe.get_doc("Payroll Entry", payroll_entry)
	employer = (settings().get("wps_employer_id") or "0").zfill(13)
	frappe.response.filename = f"{employer}{getdate(pe.end_date).strftime('%y%m%d')}{now_datetime().strftime('%H%M%S')}.SIF"
	frappe.response.filecontent = "\r\n".join(lines) + "\r\n"
	frappe.response.type = "download"
