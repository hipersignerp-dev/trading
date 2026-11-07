"""v1.8.3: the Super Admin page — only Hipersign's super admins (the site config's hipersign_super_admins,
or Administrator when it is not set). The licence: users and companies allowed, which modules may be switched on, and whether the
client's admins see Frappe and ERPNext pop-ups."""

import json

import frappe
from frappe import _

from hipersign_trading.licence import LICENCE, NOT_COUNTED_ROLES, counted_users, get_licence, is_super_admin, super_admins, usage


def _only_super_admin():
	if not is_super_admin():
		frappe.throw(_("Only Hipersign's super admins can open this page."), frappe.PermissionError)


@frappe.whitelist()
def get_state():
	_only_super_admin()
	from hipersign_trading.features import FEATURES, GROUPS, feature_on

	lic = get_licence()
	counted = set(counted_users())
	users = frappe.get_all("User", filters={"name": ["not in", ["Guest"]], "user_type": ["in", ["System User", "Website User"]]},
		fields=["name", "full_name", "enabled", "user_type", "last_active"], order_by="enabled desc, full_name asc", limit=500)
	roles = {}
	for r in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ["in", [u.name for u in users]]}, fields=["parent", "role"], limit=20000):
		roles.setdefault(r.parent, []).append(r.role)
	admins = super_admins()
	for u in users:
		rs = roles.get(u.name, [])
		u.counted = u.name in counted
		u.why = (_("Super admin") if u.name in admins else _("Portal customer") if u.user_type == "Website User"
			else _("Disabled") if not u.enabled else _("Driver only") if rs and not set(rs) - NOT_COUNTED_ROLES
			else _("No roles") if not u.counted else "")
		u.roles = [r for r in rs if r not in ("All", "Guest", "Desk User")][:6]
	allowed = lic.get("licensed_features")
	try:
		allowed = json.loads(allowed) if allowed and allowed.strip().startswith("[") else [k.strip() for k in (allowed or "").split(",") if k.strip()]
	except Exception:
		allowed = []
	return {
		"licence": {k: lic.get(k) for k in ("licensee", "valid_until", "max_users", "max_companies", "limit_features", "show_frappe_popups_to_all", "notes")},
		"licensed_features": allowed,
		"features": [{"key": k, "label": _(f[0]), "group": _(f[1]), "desc": _(f[2]), "on": feature_on(k)} for k, f in FEATURES.items()],
		"groups": [_(g) for g in GROUPS],
		"usage": usage(),
		"users": users,
		"companies": frappe.get_all("Company", fields=["name", "country", "default_currency"], order_by="creation asc"),
		"super_admins": sorted(admins),
		"in_site_config": bool(frappe.conf.get("hipersign_super_admins")),
	}


@frappe.whitelist(methods=["POST"])
def save(values):
	_only_super_admin()
	from hipersign_trading.features import FEATURES

	v = json.loads(values) if isinstance(values, str) else values
	doc = frappe.get_doc(LICENCE)
	for k in ("licensee", "valid_until", "notes"):
		if k in v:
			doc.set(k, v.get(k) or None)
	for k in ("max_users", "max_companies"):
		if k in v:
			doc.set(k, max(0, frappe.utils.cint(v.get(k))))
	for k in ("limit_features", "show_frappe_popups_to_all"):
		if k in v:
			doc.set(k, 1 if v.get(k) else 0)
	if "licensed_features" in v:
		keys = [k for k in (v.get("licensed_features") or []) if k in FEATURES]
		doc.licensed_features = json.dumps(keys)
	doc.save(ignore_permissions=True)
	frappe.clear_cache()
	# modules taken out of the licence are switched off in Hipersign Settings too (no data is deleted)
	if doc.limit_features:
		s = frappe.get_doc("Hipersign Settings")
		s.flags.ignore_mandatory = True
		s.save(ignore_permissions=True)
	return get_state()
